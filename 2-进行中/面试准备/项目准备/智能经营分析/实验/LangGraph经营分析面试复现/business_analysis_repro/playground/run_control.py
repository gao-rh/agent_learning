"""单机运行控制：停止只写控制库，不等待 ChatStore 的整轮会话文件锁。

业务执行仍一次一轮。下一条输入先落盘；上一轮退出、释放会话锁后再启动。
不强杀线程，不自动恢复进程重启前的付费执行。
"""
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from functools import wraps
from pathlib import Path


class RunCancelled(Exception):
    """正常控制信号；必须先于普通失败、补查和重试处理。"""


class ControlConflict(RuntimeError):
    """目标过期、已有执行或已有下一条输入。"""


def check_cancel(trace):
    token = getattr(trace, "cancellation", None)
    if token:
        token.check()


class CancellationToken:
    def __init__(self, control, cid, rid, predecessor=None):
        self.control, self.cid, self.rid = control, cid, rid
        self.predecessor = predecessor
        self.requested = threading.Event()
        self._lock = threading.RLock()
        self.trace = None
        self.queries = {}
        self._cleanup_threads = []
        self._notified = False
        self.inbox_ready = threading.Event()
        self.steering = None

    def check(self):
        if self.requested.is_set():
            raise RunCancelled("用户已停止本轮执行")
        if self.steering:
            self.steering.check()
        if self.requested.is_set():
            raise RunCancelled("用户已停止本轮执行")

    def attach(self, trace):
        self.trace = trace
        self.control.bind_thread(self.cid, self.rid, trace.thread_id)
        trace.event("run_control", "run_registered", request_id=self.rid,
                    conversation_id=self.cid, predecessor=self.predecessor)
        if self.requested.is_set():
            self._notify()

    def _notify(self):
        with self._lock:
            if self.trace and not self._notified:
                self._notified = True
                self.trace.event("cancel_requested", "stop_run", request_id=self.rid,
                                 reason="用户明确停止或停止并发送")

    def signal(self):
        # 受理线程只做本地标记，取消接口在独立清理线程里运行。
        self.requested.set()
        self._notify()
        with self._lock:
            ids = list(self.queries)
        for qid in ids:
            self._schedule_cancel(qid)

    def _schedule_cancel(self, qid):
        with self._lock:
            q = self.queries.get(qid)
            if not q or q["sent"]:
                return
            q["sent"] = True
        def clean():
            try:
                result = q["cancel"]()
                payload = {"query_id": qid, "status": "requested", "result": result}
            except Exception as exc:  # noqa: BLE001 -- 平台取消失败只记状态，不阻塞主对话
                payload = {"query_id": qid, "status": "failed",
                           "error": type(exc).__name__}
            if self.trace:
                self.trace.event("query_cancel_result", "cancel_query", **payload)
        thread = threading.Thread(target=clean, daemon=True, name="query-cancel")
        with self._lock:
            q["cleanup"] = thread
            self._cleanup_threads.append(thread)
            # 与 finish_trace 互斥，避免它 join 一个登记了但尚未 start 的线程。
            thread.start()

    @contextmanager
    def query(self, spec, cancel=None, query_id=None):
        """模拟平台注册点。回调可注入真实/可控模拟取消；ID 迟到也补发取消。"""
        self.check()
        qid = query_id or "demo-query-" + uuid.uuid4().hex[:12]
        cancel = cancel or (lambda: {"accepted": True, "synthetic": True})
        q = {"cancel": cancel, "sent": False, "cleanup": None}
        with self._lock:
            self.queries[qid] = q
        if self.trace:
            self.trace.event("query_registered", "submit_query", query_id=qid,
                             scope=spec, synthetic=True)
        # signal 可能发生在第一次检查之后、ID 注册之前。
        if self.requested.is_set():
            self._schedule_cancel(qid)
        try:
            self.check()
            yield qid
            self.check()
        except Exception:
            self.check()  # 查询失败与取消并发时，取消优先，不自动重试。
            raise
        finally:
            with self._lock:
                self.queries.pop(qid, None)
            if self.trace:
                self.trace.event("query_finished", "query_returned", query_id=qid,
                                 cancelled=self.requested.is_set())

    def finish_trace(self):
        # 当前模拟取消是短操作；只等有限时间收集记录，不把远端取消当运行条件。
        with self._lock:
            threads = list(self._cleanup_threads)
        for thread in threads:
            thread.join(timeout=.1)


def cancellable_query(fn):
    @wraps(fn)
    def wrapped(task, trace=None):
        token = getattr(trace, "cancellation", None)
        if not token:
            return fn(task, trace)
        token.check()
        if token.steering:
            cached = token.steering.reuse(task)
            if cached is not None:
                return cached
        with token.query({k: task.get(k) for k in
                          ("metric_id", "start_date", "end_date", "group_by", "filters")}) as qid:
            result = fn(task, trace)
            result["query_id"] = qid
            if token.steering:
                token.steering.remember(task, result)
            return result
    return wrapped


class RunControl:
    """一个 ChatStore 一个控制器；SQLite 持久化，RLock 只保护短控制操作。"""
    def __init__(self, root):
        self.path = Path(root) / "run-control.sqlite"
        self.lock = threading.RLock()
        self.tokens = {}
        with self.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs(
                  cid TEXT, rid TEXT, tid TEXT, text TEXT, status TEXT,
                  cancel_requested INTEGER DEFAULT 0, predecessor TEXT,
                  updated REAL, PRIMARY KEY(cid,rid));
                CREATE UNIQUE INDEX IF NOT EXISTS one_active ON runs(cid)
                  WHERE status IN ('running','cancelling');
                CREATE TABLE IF NOT EXISTS pending_requests(
                  cid TEXT, rid TEXT, expected TEXT, text TEXT, status TEXT,
                  created REAL, PRIMARY KEY(cid,rid));
                CREATE UNIQUE INDEX IF NOT EXISTS one_pending ON pending_requests(cid)
                  WHERE status IN ('queued','starting');
            """)
            self.recovered = [dict(r) for r in db.execute(
                "SELECT * FROM runs WHERE status IN ('running','cancelling')")]
            db.execute("UPDATE runs SET status='interrupted' "
                       "WHERE status IN ('running','cancelling')")
            db.execute("UPDATE pending_requests SET status='interrupted' "
                       "WHERE status IN ('queued','starting','started')")
        from .inbox import Inbox
        self.inbox = Inbox(self)

    @contextmanager
    def db(self):
        with self.lock:
            db = sqlite3.connect(self.path, timeout=5)
            db.row_factory = sqlite3.Row
            try:
                with db:
                    yield db
            finally:
                db.close()

    def row(self, cid, rid):
        with self.db() as db:
            row = db.execute("SELECT * FROM runs WHERE cid=? AND rid=?", (cid, rid)).fetchone()
            return dict(row) if row else None

    def claim(self, cid, rid, text):
        with self.db() as db:
            previous = db.execute("SELECT * FROM runs WHERE cid=? AND rid=?", (cid, rid)).fetchone()
            if previous:
                if previous["text"] != text:
                    raise ControlConflict("同一请求ID的文字不能改变")
                return None
            queued = db.execute("SELECT mid FROM inbox_messages WHERE cid=? AND status='dispatched'",
                                (cid,)).fetchone()
            if queued and queued["mid"] != rid:
                raise ControlConflict("已有排队消息正在启动，请稍后发送")
            if db.execute("SELECT 1 FROM runs WHERE cid=? AND status IN ('running','cancelling')",
                          (cid,)).fetchone():
                raise ControlConflict("本轮仍在执行；请通过消息队列发送，可选择立即插入")
            pending = db.execute("SELECT * FROM pending_requests WHERE cid=? "
                                 "AND status IN ('queued','starting')", (cid,)).fetchone()
            if pending and pending["rid"] != rid:
                raise ControlConflict("已有一条待启动问题，请等待它开始")
            if pending and pending["text"] != text:
                raise ControlConflict("待启动问题与请求ID不匹配")
            predecessor = pending["expected"] if pending else None
            if not predecessor:
                stopped = db.execute("SELECT rid,status FROM runs WHERE cid=? "
                                     "ORDER BY updated DESC LIMIT 1", (cid,)).fetchone()
                predecessor = stopped["rid"] if stopped and stopped["status"] == "cancelled" else None
            db.execute("INSERT INTO runs(cid,rid,text,status,predecessor,updated) "
                       "VALUES(?,?,?,'running',?,?)", (cid, rid, text, predecessor, time.time()))
            if pending:
                db.execute("UPDATE pending_requests SET status='started' WHERE cid=? AND rid=?",
                           (cid, rid))
            token = CancellationToken(self, cid, rid, predecessor)
            self.tokens[(cid, rid)] = token
            return token

    def bind_thread(self, cid, rid, tid):
        with self.db() as db:
            db.execute("UPDATE runs SET tid=? WHERE cid=? AND rid=?", (tid, cid, rid))

    def finish(self, cid, rid, status):
        with self.db() as db:
            db.execute("UPDATE runs SET status=?,updated=? WHERE cid=? AND rid=? "
                       "AND status IN ('running','cancelling')",
                       (status, time.time(), cid, rid))
            db.execute("UPDATE pending_requests SET status='completed' WHERE cid=? AND rid=? "
                       "AND status='started'", (cid, rid))
            self.tokens.pop((cid, rid), None)

    def stop(self, cid, expected, text=None, rid=None):
        """expected 是网页看见的 active_request_id；不是随时变化的“最新任务”。"""
        token = None
        with self.db() as db:
            if rid:
                existing = db.execute("SELECT * FROM pending_requests WHERE cid=? AND rid=?",
                                      (cid, rid)).fetchone()
                if existing:
                    if existing["text"] != text or existing["expected"] != expected:
                        raise ControlConflict("相同请求ID不能提交不同的新问题")
                    return self.status(cid)
                if db.execute("SELECT 1 FROM runs WHERE cid=? AND rid=?", (cid, rid)).fetchone():
                    raise ControlConflict("新请求ID已被使用")
            old = db.execute("SELECT * FROM runs WHERE cid=? AND rid=?", (cid, expected)).fetchone()
            if not old:
                raise ControlConflict("目标执行不存在，请刷新查看当前任务")
            active = db.execute("SELECT rid FROM runs WHERE cid=? "
                                "AND status IN ('running','cancelling')", (cid,)).fetchone()
            if active and active["rid"] != expected:
                raise ControlConflict("页面中的任务已经结束，当前是另一项任务；请刷新")
            latest = db.execute("SELECT rid FROM runs WHERE cid=? ORDER BY updated DESC LIMIT 1",
                                (cid,)).fetchone()
            if not active and latest and latest["rid"] != expected:
                raise ControlConflict("目标已过期，不能基于旧任务覆盖后续对话；请刷新")
            if rid:
                if db.execute("SELECT 1 FROM pending_requests WHERE cid=? "
                              "AND status IN ('queued','starting')", (cid,)).fetchone():
                    raise ControlConflict("已有一条待启动问题，未覆盖它；请等待它开始")
                db.execute("INSERT INTO pending_requests VALUES(?,?,?,?,'queued',?)",
                           (cid, rid, expected, text, time.time()))
            if old["status"] in {"running", "cancelling"}:
                db.execute("UPDATE runs SET cancel_requested=1,status='cancelling',updated=? "
                           "WHERE cid=? AND rid=?", (time.time(), cid, expected))
                token = self.tokens.get((cid, expected))
                # 在事务锁内先设置内存标记，发布检查不可能看到“数据库已取消，内存未取消”。
                if token:
                    token.requested.set()
        if token:
            token.signal()
        return self.status(cid)

    def take_pending(self, cid):
        with self.db() as db:
            if db.execute("SELECT 1 FROM runs WHERE cid=? AND status IN ('running','cancelling')",
                          (cid,)).fetchone():
                return None
            row = db.execute("SELECT * FROM pending_requests WHERE cid=? AND status='queued'",
                             (cid,)).fetchone()
            if not row:
                return None
            db.execute("UPDATE pending_requests SET status='starting' WHERE cid=? AND rid=?",
                       (cid, row["rid"]))
            return dict(row)

    def pending_failed(self, cid, rid):
        with self.db() as db:
            db.execute("UPDATE pending_requests SET status='interrupted' WHERE cid=? AND rid=?",
                       (cid, rid))

    def status(self, cid):
        with self.db() as db:
            active = db.execute("SELECT * FROM runs WHERE cid=? "
                                "AND status IN ('running','cancelling')", (cid,)).fetchone()
            pending = db.execute("SELECT * FROM pending_requests WHERE cid=? "
                                 "ORDER BY created DESC LIMIT 1", (cid,)).fetchone()
            latest = db.execute("SELECT * FROM runs WHERE cid=? ORDER BY updated DESC LIMIT 1",
                                (cid,)).fetchone()
            return {"active": dict(active) if active else None,
                    "pending_request": dict(pending) if pending else None,
                    "latest": dict(latest) if latest else None,
                    "inbox": self.inbox.rows(cid)}

    def cancelled(self, cid, rid):
        row = self.row(cid, rid)
        return bool(row and row["cancel_requested"])
