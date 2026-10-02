"""只监听本机的对话入口，使用标准库，无需安装 Web 框架。

conversation 是页面中的连续对话；每个完整问题有独立 LangGraph thread。
澄清 resume 同一个 thread；完成后的追问开新 thread。完整历史交给预算管理器，
短对话保留原文，长对话压缩旧轮次；历史摘要不能替代本轮业务工具的结果。
"""

import argparse
import json
import re
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ..main_agent.runtime import locked
from ..settings import PROJECT_DIR
from .business_knowledge import BASE, DOCUMENTS, SKILLS, search_business_knowledge
from .catalog import KNOWLEDGE
from .context_memory import history_from_conversation
from .data import formatted, number
from .flow_trace import flow_payload, node_payload
from .parallel_agent import ENGINE, SOURCE_REVISION, execute
from .parallel_trace import progress_jobs, read_events, render_html
from .run_control import ControlConflict, RunControl
from .streaming import iter_sse
from .usage import capacity, collect, summarize

ID = re.compile(r"[a-f0-9]{16}")


def read_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def save_json(path, value):
    # 同一会话外层持有锁；临时文件+rename使浏览器刷新不会读到半份JSON。
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    temp.replace(path)


def asks_to_view_details(text):
    """保守识别页面导航。改变日期/筛选/指标的业务请求仍交给 Agent。"""
    return (
        len(text) <= 100
        and bool(re.search(r"明细|表格", text))
        and bool(re.search(r"在哪|哪里|没看到|展开|怎么看|看不到", text))
        and not re.search(
            r"查[询数]|重新|分析|筛选|改成|今天|昨天|上周|本周|按|\d{4}-|"
            r"保费|商户|新商|老商|订单|渗透率|渠道|来源|地区|品类|险种",
            text,
        )
    )


class ChatStore:
    def __init__(self, root, executor=execute):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.executor = executor
        self.control = RunControl(self.root)
        # 重启只恢复记录，不自动重跑已付费任务。JSON 仍由单会话执行独占写入。
        for old in self.control.recovered:
            directory = self.directory(old["cid"])
            with locked(directory):
                state = self.get(old["cid"])
                if state.get("active_request_id") == old["rid"]:
                    state["messages"].append({
                        "role": "assistant", "request_id": old["rid"],
                        "content": "服务重启，本轮执行已中断。输入记录已保留，请重新发送。",
                        "status": "interrupted",
                    })
                    state.update(active=None, active_request_id=None, pending=None)
                    save_json(directory / "conversation.json", state)

    def directory(self, cid):
        if not isinstance(cid, str) or not ID.fullmatch(cid):
            raise ValueError("无效会话ID")
        return self.root / cid

    def get(self, cid):
        return read_json(
            self.directory(cid) / "conversation.json",
            {"id": cid, "messages": [], "turns": [], "pending": None, "active": None},
        )

    def send(self, cid, text, request_id=None):
        self.directory(cid)
        if not isinstance(text, str) or not text.strip() or len(text) > 4000:
            raise ValueError("请输入1至4000字符的问题")
        rid = request_id or uuid.uuid4().hex[:16]
        if not isinstance(rid, str) or not ID.fullmatch(rid):
            raise ValueError("无效请求ID")
        token = self.control.claim(cid, rid, text)
        if token is None:
            return self.get(cid)
        try:
            result = self._send(cid, text, rid, token)
            # _send 的会话锁此时已释放。运行权直到这里才交还控制器；
            # 同时处理保存结果到退出之间到达的停止请求。
            with self.control.lock:
                if token.requested.is_set():
                    self._cancel_reply(result, rid)
                    with locked(self.directory(cid)):
                        save_json(self.directory(cid) / "conversation.json", result)
                final = next((m.get("status", "completed") for m in reversed(result["messages"])
                              if m.get("role") == "assistant" and m.get("request_id") == rid), "failed")
                self.control.finish(cid, rid, final)
            return result
        finally:
            # _send 返回时原会话文件锁已释放，下一条才能开始。
            self.control.finish(cid, rid, "failed")
            self._start_pending(cid)

    @staticmethod
    def _cancel_reply(state, rid):
        for message in state["messages"]:
            if message.get("role") == "assistant" and message.get("request_id") == rid:
                message.update(status="cancelled",
                    content="已停止本轮执行。部分过程保留在 Trace，未作为完整分析交付。",
                    result_cards=[])
        state["turns"] = [t for t in state["turns"] if t.get("request_id") != rid]
        state["pending"] = None

    def _start_pending(self, cid):
        pending = self.control.take_pending(cid)
        if not pending:
            self._start_inbox(cid)
            return
        def work():
            try:
                self.send(cid, pending["text"], pending["rid"])
            except Exception:  # noqa: BLE001 -- 后台交接失败必须落盘，不自动重放付费任务
                self.control.pending_failed(cid, pending["rid"])
        try:
            threading.Thread(target=work, name="replacement-run", daemon=True).start()
        except Exception:
            self.control.pending_failed(cid, pending["rid"])
            raise

    def receive(self, cid, text, mid, expected=None):
        """运行中只入队，立刻返回；用户主动提升后才在安全位置处理。"""
        self.directory(cid)
        if not isinstance(text, str) or not text.strip() or len(text) > 4000:
            raise ValueError("请输入1至4000字符的问题")
        if not isinstance(mid, str) or not ID.fullmatch(mid):
            raise ValueError("无效消息ID")
        row = self.control.inbox.enqueue(cid, mid, text, expected)
        self._start_inbox(cid)
        return row

    def insert(self, cid, mid, expected=None):
        self.directory(cid)
        row = self.control.inbox.promote(cid, mid, expected)
        self._start_inbox(cid)
        return row

    def _start_inbox(self, cid):
        row = self.control.inbox.take_idle(cid)
        if not row:
            return
        def work():
            failed = False
            try:
                self.send(cid, row["text"], row["mid"])
            except Exception:  # noqa: BLE001 -- 保留输入，禁止自动重放不确定的付费调用
                failed = True
            finally:
                self.control.inbox.finish_idle(cid, row["mid"], failed=failed)
                self._start_pending(cid)
        try:
            threading.Thread(target=work, name="queued-user-message", daemon=True).start()
        except Exception:
            self.control.inbox.finish_idle(cid, row["mid"], failed=True)
            raise

    def stop(self, cid, expected, text=None, rid=None):
        self.directory(cid)
        if not isinstance(expected, str) or not ID.fullmatch(expected):
            raise ValueError("无效目标请求ID")
        if text is not None:
            if not isinstance(text, str) or not text.strip() or len(text) > 4000:
                raise ValueError("请输入1至4000字符的问题")
            if not isinstance(rid, str) or not ID.fullmatch(rid) or rid == expected:
                raise ValueError("换方向需要一个新的请求ID")
        result = self.control.stop(cid, expected, text, rid)
        self._start_pending(cid)
        return result

    def _send(self, cid, text, request_id, cancel):
        if not isinstance(text, str) or not text.strip() or len(text) > 4000:
            raise ValueError("请输入1至4000字符的问题")
        directory = self.directory(cid)
        request_id = request_id or uuid.uuid4().hex[:16]
        if not isinstance(request_id, str) or not ID.fullmatch(request_id):
            raise ValueError("无效请求ID")
        with locked(directory):
            state = self.get(cid)
            # 网络超时后的同ID重发只读已有结果；不能再执行一次付费任务。
            if any(
                m.get("role") == "assistant" and m.get("request_id") == request_id
                for m in state["messages"]
            ):
                return state
            last = next(
                (m for m in reversed(state["messages"]) if m.get("role") == "assistant"), {}
            )
            if (
                not state.get("pending")
                and not state.get("active")
                and last.get("result_cards")
                and asks_to_view_details(text)
            ):
                events = read_events(directory / "tasks" / last["thread_id"] / "trace.jsonl")
                state["messages"].extend(
                    [
                        {"role": "user", "content": text, "request_id": request_id},
                        {
                            **last,
                            "content": "已展开上次结果的完整明细，没有重新取数。",
                            "view_only": True,
                            "usage": summarize([]),
                            "request_id": request_id,
                            "stream_after_seq": events[-1]["seq"] if events else 0,
                        },
                    ]
                )
                save_json(directory / "conversation.json", state)
                return state
            pending = state["pending"]
            tid = pending or uuid.uuid4().hex[:16]
            migration = {}
            if pending and self.executor is execute:
                previous = read_json(directory / "tasks" / pending / "state.json", {})
                if previous and previous.get("engine_version") != ENGINE:
                    # 不拿新版 schema 强行恢复旧 checkpoint。保留 v3 原轨迹，
                    # 带入旧问答和待澄清问题，在新任务里重新理解用户补充。
                    tid = uuid.uuid4().hex[:16]
                    history = previous.get("messages", [])[:]
                    if previous.get("pending_question"):
                        history.append(
                            {"role": "assistant", "content": previous["pending_question"]}
                        )
                    migration = {"initial_messages": history, "migrated_from": pending}
            context = history_from_conversation(state)
            if cancel.predecessor:
                old = self.control.row(cid, cancel.predecessor)
                saved = read_json(directory / "tasks" / (old["tid"] or "_") / "state.json", {})
                context.append({
                    "question": old["text"], "task": saved.get("task"), "answer": "",
                    "cancelled": True,
                    "note": "此前任务已停止。仅用于理解省略的指标/条件；以新输入为准，重新校验，不继承旧结论。",
                })
            events = read_events(directory / "tasks" / tid / "trace.jsonl")
            stream_after_seq = events[-1]["seq"] if events else 0
            request_meta = {"request_id": request_id, "stream_after_seq": stream_after_seq}
            state["messages"].append({"role": "user", "content": text, "request_id": request_id})
            state["active"] = tid
            state["active_request_id"] = request_id
            state["active_after_seq"] = stream_after_seq
            save_json(directory / "conversation.json", state)
            try:
                self.control.bind_thread(cid, request_id, tid)
                result, _ = self.executor(
                    directory / "tasks",
                    tid,
                    text,
                    resume=bool(pending) and not migration,
                    context=context,
                    context_cache_path=directory / "context-memory.json",
                    cancel=cancel,
                    **migration,
                )
                content = (
                    result.get("pending_question")
                    if result["status"] == "waiting_user"
                    else result.get("answer")
                )
                state["pending"] = tid if result["status"] == "waiting_user" else None
                if result["status"] in {"completed", "partial"}:
                    state["turns"].append(
                        {
                            "request_id": request_id,
                            "question": text,
                            "task": result.get("task"),
                            "answer": content,
                            "thread_id": tid,
                        }
                    )
                state["messages"].append(
                    {
                        "role": "assistant",
                        **request_meta,
                        "content": content or "本次没有可交付结果。",
                        "status": result["status"],
                        "response_kind": result.get("response_kind", "business"),
                        "trace": f"/trace/{cid}/{tid}",
                        "thread_id": tid,
                        "result_cards": (result.get("result") or {}).get("cards", []),
                    }
                )
            except Exception as exc:  # noqa: BLE001 -- 入口/节点统一失败边界，保留本地Trace
                # 已写入checkpoint的等待状态仍可恢复；配置/网络失败显示失败，不伪装回答。
                saved = read_json(directory / "tasks" / tid / "state.json", {})
                state["pending"] = tid if saved.get("status") == "waiting_user" else None
                state["messages"].append(
                    {
                        "role": "assistant",
                        **request_meta,
                        "content": f"执行未完成（{type(exc).__name__}），可查看记录并重新输入。",
                        "status": "failed",
                        "trace": f"/trace/{cid}/{tid}",
                        "thread_id": tid,
                    }
                )
            finally:
                # 插入消息在处理中保存在SQLite；结束时由唯一会话写入者归并到聊天记录。
                inserts = getattr(cancel.steering, "applied", [])
                added = []
                for item in inserts:
                    if any(m.get("request_id") == item["id"] for m in state["messages"]):
                        continue
                    added.append({"role": "user", "content": item["text"],
                                  "request_id": item["id"], "root_request_id": request_id})
                    if item["reply"]:
                        added.append({"role": "assistant", "content": item["reply"],
                                      "request_id": item["id"], "root_request_id": request_id,
                                      "status": "handled"})
                state["messages"][-1:-1] = added
                for turn in state["turns"]:
                    if turn.get("request_id") == request_id and inserts:
                        turn["question"] += "\n" + "\n".join(
                            i["text"] for i in inserts if i["action"] in {"continue", "revise"})
                # 每轮只累计本轮新增的Trace；澄清恢复不重复算上一轮费用。
                actual = read_events(directory / "tasks" / tid / "trace.jsonl")
                if state["messages"] and state["messages"][-1].get("role") == "assistant":
                    state["messages"][-1]["usage"] = summarize(
                        [e for e in actual if e["seq"] > stream_after_seq])
                    state["messages"][-1]["task_usage"] = summarize(actual)
                # 与停止受理共用短锁：已取消的结果不能在检查与保存之间偷偷发布。
                # 此处没有模型/平台调用，锁不跨整轮任务。
                with self.control.lock:
                    if cancel.requested.is_set():
                        self._cancel_reply(state, request_id)
                    state["active"] = None
                    state["active_request_id"] = None
                    state["active_after_seq"] = None
                    save_json(directory / "conversation.json", state)
            return state

    def progress(self, cid):
        state = self.get(cid)
        tid = state.get("active") or state.get("pending")
        if not tid:
            return {"active": False}
        path = self.directory(cid) / "tasks" / tid / "trace.jsonl"
        events = []
        if path.exists():
            for line in path.read_text().splitlines():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass  # 最后一条事件可能正写入。
        latest = next(
            (
                e
                for e in reversed(events)
                if e["kind"] == "span_start" and e.get("category") in {"tool", "node"}
            ),
            {},
        )
        return {
            "active": bool(state.get("active")),
            "step": latest.get("name"),
            "model_calls": sum(e["kind"] == "model_request" for e in events),
            "jobs": progress_jobs(events),
            "concurrency_limit": 5,
            "trace": f"/trace/{cid}/{tid}",
        }


def catalog_payload():
    metrics = []
    for m in KNOWLEDGE["metrics"]:
        p = m["preset"]
        metrics.append(
            {
                **m,
                "preset_text": formatted(
                    m, number(m, p["current_numerator"], p["current_denominator"] or 0)
                ),
            }
        )
    return {**KNOWLEDGE, "metrics": metrics}


def make_handler(store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # 用户问题和模型消息只保存在会话及Trace，避免写到通用HTTP日志。

        def respond(self, data, status=200, content_type="application/json; charset=utf-8"):
            raw = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
            try:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError):
                pass  # 浏览器离开不撤销已经保存的执行结果。

        def stream(self, query):
            cid = query.get("id", [""])[0]
            request_id = query.get("request_id", [""])[0]
            store.directory(cid)
            if not ID.fullmatch(request_id):
                raise ValueError("无效请求ID")
            # 只接受本轮游标；不能用另一个任务的seq跳过本轮文字。
            cursor = self.headers.get("Last-Event-ID", "").split(":")
            after = (
                int(cursor[1])
                if (len(cursor) == 2 and cursor[0] == request_id and cursor[1].isdigit())
                else 0
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self.send_header("Connection", "close")
            self.end_headers()
            self.connection.settimeout(15)
            try:
                for chunk in iter_sse(store, cid, request_id, after):
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                pass  # SSE只订阅日志；真正执行的POST线程继续完成并保存。
            self.close_connection = True

        def do_GET(self):
            url = urlparse(self.path)
            try:
                if url.path in {"/usage", "/knowledge"}:
                    return self.respond(Path(__file__).with_name(
                        "usage.html" if url.path == "/usage" else "knowledge_view.html").read_bytes(),
                        content_type="text/html; charset=utf-8")
                if url.path == "/api/knowledge":
                    q = parse_qs(url.query).get("q", [""])[0]
                    return self.respond({"documents": search_business_knowledge(q)["candidates"] if q else DOCUMENTS,
                        "skills": {k: (BASE / "analysis_skills" / k / "SKILL.md").read_text() for k in sorted(SKILLS)}})
                if url.path == "/api/usage":
                    report = collect(store.root.parent if store.root.name == "playground" else store.root)
                    cid = parse_qs(url.query).get("id", [""])[0]
                    if cid:
                        store.directory(cid)
                        from .usage import add
                        report["conversation"] = add(r for r in report["turns"] if r["conversation_id"] == cid)
                    return self.respond(report)
                if url.path == "/api/capacity":
                    params = {k: float(v[0]) for k, v in parse_qs(url.query).items()}
                    return self.respond(capacity(**params))
                if url.path == "/":
                    return self.respond(
                        Path(__file__).with_name("parallel_chat.html").read_bytes(),
                        content_type="text/html; charset=utf-8",
                    )
                if url.path in {"/stream_chat.js", "/flow_trace.js", "/flow_trace.css"}:
                    return self.respond(
                        Path(__file__).with_name(url.path[1:]).read_bytes(),
                        content_type=(
                            "text/css" if url.path.endswith(".css") else "text/javascript"
                        )
                        + "; charset=utf-8",
                    )
                if url.path in {"/api/flow", "/api/flow-node"}:
                    query = parse_qs(url.query)
                    cid, tid = query.get("id", [""])[0], query.get("task_id", [""])[0]
                    if not ID.fullmatch(tid):
                        raise ValueError("无效任务ID")
                    events = read_events(store.directory(cid) / "tasks" / tid / "trace.jsonl")
                    if url.path.endswith("flow-node"):
                        cutoff = query.get("seq", [None])[0]
                        return self.respond(
                            node_payload(
                                events,
                                query.get("span_id", [""])[0],
                                int(cutoff) if cutoff is not None else None,
                            )
                        )
                    return self.respond(
                        flow_payload(events, cid, tid, store.get(cid).get("active") == tid)
                    )
                if url.path == "/api/events":
                    return self.stream(parse_qs(url.query))
                if url.path == "/api/control":
                    cid = parse_qs(url.query).get("id", [""])[0]
                    store.directory(cid)
                    return self.respond(store.control.status(cid))
                if url.path == "/api/health":
                    return self.respond(
                        {
                            "application": "langgraph-playground",
                            "ok": True,
                            "engine": ENGINE,
                            "source_revision": SOURCE_REVISION,
                            "max_concurrency": 5,
                            "streaming": "sse",
                            "cancellation": "cooperative-stop-and-replace",
                            "messages": "queue-and-steer",
                            "context": "budget-summary-v1",
                        }
                    )
                if url.path == "/api/catalog":
                    return self.respond(catalog_payload())
                if url.path in {"/api/conversation", "/api/progress"}:
                    cid = parse_qs(url.query).get("id", [""])[0]
                    return self.respond(
                        store.get(cid) if url.path.endswith("conversation") else store.progress(cid)
                    )
                parts = url.path.strip("/").split("/")
                if len(parts) == 3 and parts[0] == "flow" and ID.fullmatch(parts[2]):
                    path = store.directory(parts[1]) / "tasks" / parts[2] / "trace.jsonl"
                    if not path.exists():
                        raise FileNotFoundError(path)
                    return self.respond(
                        Path(__file__).with_name("flow_trace.html").read_bytes(),
                        content_type="text/html; charset=utf-8",
                    )
                if len(parts) == 3 and parts[0] == "trace" and ID.fullmatch(parts[2]):
                    path = store.directory(parts[1]) / "tasks" / parts[2] / "trace.html"
                    events = read_events(path.with_name("trace.jsonl"))
                    if any(e["kind"] == "execution_start" and e["name"] == ENGINE for e in events):
                        # 执行中也能追踪：只读日志投影，不调用模型、不写旧报告。
                        return self.respond(
                            render_html(events, parts[2], parts[1]).encode(),
                            content_type="text/html; charset=utf-8",
                        )
                    return self.respond(path.read_bytes(), content_type="text/html; charset=utf-8")
                return self.respond({"error": "未找到页面"}, 404)
            except (ValueError, TypeError, FileNotFoundError):
                return self.respond({"error": "未找到记录"}, 404)

        def do_POST(self):
            if self.path not in {"/api/message", "/api/stop", "/api/replace", "/api/inbox", "/api/insert"}:
                return self.respond({"error": "未找到接口"}, 404)
            # 本机应用也不接受其他网站代发付费模型请求。
            origin = self.headers.get("Origin")
            if origin and origin != f"http://{self.headers.get('Host')}":
                return self.respond({"error": "请求来源不匹配"}, 403)
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 20000:
                    raise ValueError("请求长度不正确")
                data = json.loads(self.rfile.read(length))
                cid = data.get("id") or uuid.uuid4().hex[:16]
                if self.path == "/api/inbox":
                    return self.respond(store.receive(cid, data["text"], data["message_id"],
                                                      data.get("expected_request_id")), 202)
                if self.path == "/api/insert":
                    return self.respond(store.insert(cid, data["message_id"],
                                                     data.get("expected_request_id")), 202)
                if self.path in {"/api/stop", "/api/replace"}:
                    replacement = self.path == "/api/replace"
                    return self.respond(store.stop(
                        cid, data["expected_request_id"],
                        data["text"] if replacement else None,
                        data["request_id"] if replacement else None,
                    ), 202)
                self.respond(store.send(cid, data["text"], data.get("request_id")))
            except (ValueError, KeyError, TypeError):
                self.respond({"error": "请检查输入内容和会话ID"}, 400)
            except ControlConflict as exc:
                self.respond({"error": str(exc)}, 409)
            except RuntimeError:
                self.respond({"error": "这个对话正在执行，请等本轮完成"}, 409)

    return Handler


def main():
    parser = argparse.ArgumentParser(description="本地LangGraph经营分析对话试玩")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_DIR / ".runs" / "playground")
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(ChatStore(args.output_dir)))
    print(f"经营分析试玩：http://127.0.0.1:{args.port}  · Ctrl+C停止", flush=True)
    if args.open:
        webbrowser.open(f"http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
