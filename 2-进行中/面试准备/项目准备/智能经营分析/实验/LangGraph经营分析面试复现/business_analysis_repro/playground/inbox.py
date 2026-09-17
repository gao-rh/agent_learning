"""持久化消息收件箱。发送、插入和取消是三个不同操作。

本类只负责有序存取，不判断自然语言、不执行模型、不持有会话文件锁。
"""
import json
import time

from .run_control import ControlConflict


class Inbox:
    def __init__(self, control):
        self.control = control
        with control.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS inbox_messages(
                  seq INTEGER PRIMARY KEY AUTOINCREMENT, cid TEXT, mid TEXT,
                  target TEXT, text TEXT, delivery TEXT, status TEXT,
                  reply TEXT DEFAULT '', decision TEXT DEFAULT '{}', created REAL,
                  UNIQUE(cid,mid));
                CREATE INDEX IF NOT EXISTS inbox_pending ON inbox_messages(cid,status,seq);
            """)
            # 不知道进程崩溃前远端请求是否执行过，不能自动付费重放。
            db.execute("UPDATE inbox_messages SET status='interrupted' "
                       "WHERE status IN ('queued','processing','dispatched')")

    def rows(self, cid):
        with self.control.db() as db:
            rows = db.execute("SELECT m.*,EXISTS(SELECT 1 FROM runs r "
                              "WHERE r.cid=m.cid AND r.rid=m.mid) AS has_run "
                              "FROM inbox_messages m WHERE cid=? ORDER BY seq DESC LIMIT 200",
                              (cid,)).fetchall()
            return [dict(r) for r in reversed(rows)]

    def enqueue(self, cid, mid, text, expected=None):
        with self.control.db() as db:
            old = db.execute("SELECT * FROM inbox_messages WHERE cid=? AND mid=?",
                             (cid, mid)).fetchone()
            if old:
                if old["text"] != text:
                    raise ControlConflict("同一消息ID不能提交不同文字")
                return dict(old)
            if db.execute("SELECT 1 FROM runs WHERE cid=? AND rid=?", (cid, mid)).fetchone():
                raise ControlConflict("消息ID已被其他请求使用")
            active = db.execute("SELECT rid FROM runs WHERE cid=? AND status IN "
                                "('running','cancelling')", (cid,)).fetchone()
            if active and expected and active["rid"] != expected:
                raise ControlConflict("当前任务已改变，请刷新后发送；文字尚未入队")
            count = db.execute("SELECT COUNT(*) FROM inbox_messages WHERE cid=? "
                               "AND status IN ('queued','processing','dispatched')", (cid,)).fetchone()[0]
            if count >= 32:
                raise ControlConflict("最多保留32条待处理消息，请等待或处理已有消息")
            db.execute("INSERT INTO inbox_messages(cid,mid,target,text,delivery,status,created) "
                       "VALUES(?,?,?,?,'queue','queued',?)",
                       (cid, mid, active["rid"] if active else expected, text, time.time()))
            return dict(db.execute("SELECT * FROM inbox_messages WHERE cid=? AND mid=?",
                                   (cid, mid)).fetchone())

    def promote(self, cid, mid, expected):
        with self.control.db() as db:
            row = db.execute("SELECT * FROM inbox_messages WHERE cid=? AND mid=?",
                             (cid, mid)).fetchone()
            if not row:
                raise ControlConflict("没有找到这条排队消息")
            if row["status"] not in {"queued", "interrupted", "failed"}:
                return dict(row)  # 已处理或处理中，重复点击不重复消费
            if db.execute("SELECT 1 FROM runs WHERE cid=? AND rid=?", (cid, mid)).fetchone():
                raise ControlConflict("这条消息对应的执行已结束或中断，请恢复到输入框重新发送")
            active = db.execute("SELECT rid,status FROM runs WHERE cid=? AND status IN "
                                "('running','cancelling')", (cid,)).fetchone()
            if active and active["rid"] != expected:
                raise ControlConflict("当前任务已改变，请刷新后再插入")
            if active and active["status"] == "cancelling":
                raise ControlConflict("当前任务正在停止，消息会在结束后按队列处理")
            target = active["rid"] if active else row["target"]
            db.execute("UPDATE inbox_messages SET status='queued',delivery=?,target=? "
                       "WHERE cid=? AND mid=?", ("steer" if active else "queue", target, cid, mid))
            token = self.control.tokens.get((cid, target))
            if token:
                token.inbox_ready.set()
            return dict(db.execute("SELECT * FROM inbox_messages WHERE cid=? AND mid=?",
                                   (cid, mid)).fetchone())

    def claim_insertions(self, token):
        with self.control.db() as db:
            rows = db.execute("SELECT * FROM inbox_messages WHERE cid=? AND target=? "
                              "AND status='queued' AND delivery='steer' ORDER BY seq LIMIT 8",
                              (token.cid, token.rid)).fetchall()
            for row in rows:
                db.execute("UPDATE inbox_messages SET status='processing' WHERE seq=?", (row["seq"],))
            remains = db.execute("SELECT 1 FROM inbox_messages WHERE cid=? AND target=? "
                                 "AND status='queued' AND delivery='steer'",
                                 (token.cid, token.rid)).fetchone()
            if not remains:
                token.inbox_ready.clear()  # 与 enqueue/promote 同锁，不丢唤醒
            return [dict(r) for r in rows]

    def apply(self, rows, decision, failed=False):
        with self.control.db() as db:
            for index, row in enumerate(rows):
                db.execute("UPDATE inbox_messages SET status=?,reply=?,decision=? WHERE seq=?",
                           ("failed" if failed else "applied",
                            decision["reply"] if index == len(rows)-1 else "",
                            json.dumps(decision, ensure_ascii=False), row["seq"]))

    def take_idle(self, cid):
        with self.control.db() as db:
            if db.execute("SELECT 1 FROM pending_requests WHERE cid=? "
                          "AND status IN ('queued','starting')", (cid,)).fetchone():
                return None
            if db.execute("SELECT 1 FROM runs WHERE cid=? AND status IN ('running','cancelling')",
                          (cid,)).fetchone():
                return None
            if db.execute("SELECT 1 FROM inbox_messages WHERE cid=? AND status='dispatched'",
                          (cid,)).fetchone():
                return None
            row = db.execute("SELECT * FROM inbox_messages WHERE cid=? AND status='queued' "
                             "ORDER BY seq LIMIT 1", (cid,)).fetchone()
            if not row:
                return None
            db.execute("UPDATE inbox_messages SET status='dispatched' WHERE seq=?", (row["seq"],))
            return dict(row)

    def finish_idle(self, cid, mid, failed=False):
        with self.control.db() as db:
            db.execute("UPDATE inbox_messages SET status=?,decision=? WHERE cid=? AND mid=?",
                       ("failed" if failed else "applied", '{"action":"next_turn"}', cid, mid))
