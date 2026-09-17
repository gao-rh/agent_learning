"""停止与换方向：真实图/SQLite/HTTP/SSE，模型和慢工具使用可控替身。

用 Event 固定竞态窗口，不靠更短的运行耗时推断正确性；不消耗 API。
"""
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from langchain_core.messages import AIMessage, AIMessageChunk

from business_analysis_repro.main_agent.state import Reply, Verdict
from business_analysis_repro.playground import catalog, data, parallel_model, server
from business_analysis_repro.playground.parallel_agent import execute
from business_analysis_repro.playground.parallel_model import ParallelModel
from business_analysis_repro.playground.parallel_state import BatchResolution, MetricRequest
from business_analysis_repro.playground.parallel_trace import Trace, read_events
from business_analysis_repro.playground.run_control import (
    ControlConflict,
    RunCancelled,
    RunControl,
    cancellable_query,
)
from business_analysis_repro.playground.streaming import iter_sse
from business_analysis_repro.playground.usage import summarize

CID, RID, NEW = "a" * 16, "b" * 16, "c" * 16
IDS = list(catalog.METRICS)


class Model:
    def __init__(self, trace, max_calls):
        self.trace = trace

    def resolve(self, payload):
        text = payload["messages"][-1]["content"]
        self.trace.event("test_context", "resolve", payload=payload)
        return BatchResolution(outcome="ready", requests=[
            MetricRequest(metric_id=mid, period={"mode": "calendar", "unit": "week", "offset": -1})
            for mid in (IDS[:8] if text == "旧任务" else IDS[:1])
        ])

    def complete(self, stage, instruction, payload, schema):
        if stage == "compose_batch":
            return Reply(text="模拟查询完成。", evidence_ids=payload["evidence_ids"])
        return Verdict(passed=True, issues=[])


def post(url, path, data):
    with urlopen(Request(url + path, data=json.dumps(data).encode(),
                         headers={"Content-Type": "application/json"}), timeout=15) as response:
        return response.status, json.load(response)


def test_http_stop_five_branches_then_replace_no_old_tail(tmp_path):
    five, release, new_done = threading.Event(), threading.Event(), threading.Event()
    lock = threading.Lock()
    started, completed = [], []
    new_started_after = []

    def slow_query(task, trace=None):
        with lock:
            started.append(task["metric_id"])
            if len(started) == 5:
                five.set()
        assert release.wait(10)
        with lock:
            completed.append(task["metric_id"])
        # 模拟已发出的工具在取消后正常返回，worker 仍必须丢弃它的交付结果。
        return {"late": True}

    def executor(root, tid, text, **kwargs):
        if text == "旧任务":
            return execute(root, tid, text, model_factory=Model,
                           capabilities={"query": slow_query}, **kwargs)
        with lock:
            new_started_after.append(len(completed))
        try:
            return execute(root, tid, text, model_factory=Model, **kwargs)
        finally:
            new_done.set()

    store = server.ChatStore(tmp_path, executor=executor)
    http = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(store))
    threading.Thread(target=http.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{http.server_port}"
    try:
        with ThreadPoolExecutor() as pool:
            old = pool.submit(post, url, "/api/message",
                              {"id": CID, "request_id": RID, "text": "旧任务"})
            try:
                assert five.wait(10)
                body = {"id": CID, "expected_request_id": RID,
                        "request_id": NEW, "text": "改查一个指标"}
                code, control = post(url, "/api/replace", body)
                assert code == 202 and not old.done()
                assert control["pending_request"]["text"] == "改查一个指标"
                assert control["active"]["status"] == "cancelling"
                assert post(url, "/api/replace", body)[0] == 202  # 相同请求幂等
                with pytest.raises(HTTPError) as err:
                    post(url, "/api/replace", {**body, "request_id": "d" * 16})
                assert err.value.code == 409
                assert not new_started_after
                assert store.control.status(CID)["pending_request"]["status"] == "queued"
            finally:
                release.set()
            assert old.result(timeout=15)[1]["messages"][-1]["status"] == "cancelled"
            assert new_done.wait(15)
        # 完成事件在 executor 返回前触发；等控制器终态，不重新发请求。
        with store.control.lock:
            pass
        for _ in range(100):
            state = store.get(CID)
            if any(m.get("request_id") == NEW and m.get("role") == "assistant"
                   for m in state["messages"]):
                break
            threading.Event().wait(.02)
        assert len(started) == 5  # 后三个仍排队的工具从未执行
        assert new_started_after == [5]  # 必须等全部旧分支退出
        assistants = [m for m in state["messages"] if m["role"] == "assistant"]
        assert [m["status"] for m in assistants] == ["cancelled", "completed"]
        assert assistants[0]["result_cards"] == []
        assert [t["request_id"] for t in state["turns"]] == [NEW]
        old_events = read_events(tmp_path / CID / "tasks" / assistants[0]["thread_id"] / "trace.jsonl")
        assert sum(e["kind"] == "job_status" and e.get("status") == "cancelled"
                   for e in old_events) == 8
        assert not any(e.get("name") == "compose_reply" for e in old_events)
        new_events = read_events(tmp_path / CID / "tasks" / assistants[1]["thread_id"] / "trace.jsonl")
        context = next(e["conversation_context"] for e in new_events if e["kind"] == "execution_start")
        assert context[-1]["cancelled"] and context[-1]["answer"] == ""
        assert context[-1]["question"] == "旧任务"
        frames = list(iter_sse(store, CID, RID, poll_interval=.001))
        assert not any(b"event: update" in f for f in frames)
        assert any(b"event: done" in f for f in frames)
    finally:
        release.set()
        http.shutdown()
        http.server_close()


def test_stop_during_resolve_does_not_call_date_review(tmp_path):
    entered, release = threading.Event(), threading.Event()
    calls = []

    class Slow(Model):
        def resolve(self, payload):
            entered.set()
            assert release.wait(10)
            return super().resolve(payload)

        def complete(self, *args):
            calls.append(args[0])
            return super().complete(*args)

    store = server.ChatStore(tmp_path, executor=partial(execute, model_factory=Slow))
    with ThreadPoolExecutor() as pool:
        run = pool.submit(store.send, CID, "查指标", RID)
        try:
            assert entered.wait(10)
            store.stop(CID, RID)
        finally:
            release.set()
        assert run.result(timeout=10)["messages"][-1]["status"] == "cancelled"
    assert calls == []


def test_analysis_stops_between_two_period_queries(tmp_path, monkeypatch):
    control = RunControl(tmp_path)
    token = control.claim(CID, RID, "分析")
    trace = Trace(tmp_path / "trace", "two-period")
    trace.cancellation = token
    token.attach(trace)
    entered, release = threading.Event(), threading.Event()
    calls = []

    @cancellable_query
    def slow_query(spec, trace=None):
        calls.append(spec["start_date"])
        entered.set()
        assert release.wait(10)
        return {}

    monkeypatch.setattr(data, "query_agent", slow_query)
    task = {"metric_id": IDS[0], "start_date": "2026-08-24", "end_date": "2026-08-30"}
    with ThreadPoolExecutor() as pool:
        run = pool.submit(data.analysis_agent, task, trace)
        try:
            assert entered.wait(10)
            control.stop(CID, RID)
        finally:
            release.set()
        with pytest.raises(RunCancelled):
            run.result(timeout=10)
    token.finish_trace()
    assert calls == ["2026-08-24"]  # 返回本期查询就停，不等分析函数查完前期
    assert sum(e["kind"] == "query_cancel_result" for e in trace.read()) == 1


@pytest.mark.parametrize("stream", [False, True])
def test_cancelled_model_still_records_usage_and_does_not_call_tools(tmp_path, stream):
    control = RunControl(tmp_path)
    token = control.claim(CID, RID, "请求")
    trace = Trace(tmp_path / "trace", "test-model")
    trace.cancellation = token
    token.attach(trace)
    entered, release = threading.Event(), threading.Event()
    calls = []

    class Client:
        def bind_tools(self, *_):
            return self

        def invoke(self, *_):
            calls.append("invoke")
            entered.set()
            assert release.wait(10)
            return AIMessage(content="", tool_calls=[{
                "name": "search_metrics", "args": {"query": "保费"}, "id": "call-1"}],
                usage_metadata={"input_tokens": 10, "output_tokens": 8, "total_tokens": 18})

        def stream(self, *_args, **_kwargs):
            calls.append("stream")
            yield AIMessageChunk(content="已经到达的草稿")
            entered.set()
            assert release.wait(10)
            yield AIMessageChunk(content="取消后才返回的草稿",
                usage_metadata={"input_tokens": 10, "output_tokens": 8, "total_tokens": 18})

    model = object.__new__(ParallelModel)
    model.trace, model.max_calls, model.model_name = trace, 10, "offline"
    model.client = SimpleNamespace(bound=Client())
    with ThreadPoolExecutor() as pool:
        if stream:
            run = pool.submit(model.complete, "compose_batch", "回答", {"evidence_ids": []}, Reply)
        else:
            run = pool.submit(model.resolve, {"messages": []})
        try:
            assert entered.wait(10)
            control.stop(CID, RID)
        finally:
            release.set()
        with pytest.raises(RunCancelled):
            run.result(timeout=10)
    assert len(calls) == 1
    events = trace.read()
    assert sum(e["kind"] == "model_response" for e in events) == 1
    assert summarize(events)["total_tokens"] == 18
    assert not any(e["kind"] == "span_start" and e["name"] == "search_metrics" for e in events)
    assert not any(e["kind"] == "model_error" for e in events)


def test_cancel_while_waiting_model_slot_does_not_count_unsent_request(tmp_path, monkeypatch):
    control = RunControl(tmp_path)
    token = control.claim(CID, RID, "请求")
    trace = Trace(tmp_path / "trace", "queued-model")
    trace.cancellation = token
    token.attach(trace)
    entered, release = threading.Event(), threading.Event()

    class Slot:
        def __enter__(self):
            entered.set()
            assert release.wait(10)

        def __exit__(self, *_):
            return False

    class Client:
        def bind_tools(self, *_):
            return self

        def invoke(self, *_):
            pytest.fail("排队中取消后不应发出请求")

    monkeypatch.setattr(parallel_model, "MODEL_SLOTS", Slot())
    model = object.__new__(ParallelModel)
    model.trace, model.max_calls, model.model_name = trace, 10, "offline"
    model.client = SimpleNamespace(bound=Client())
    with ThreadPoolExecutor() as pool:
        run = pool.submit(model.resolve, {"messages": []})
        try:
            assert entered.wait(10)
            control.stop(CID, RID)
        finally:
            release.set()
        with pytest.raises(RunCancelled):
            run.result(timeout=10)
    assert summarize(trace.read())["calls"] == 0


@pytest.mark.parametrize("fails", [False, True])
def test_query_cancel_once_success_or_failure_then_exit(tmp_path, fails):
    control = RunControl(tmp_path)
    token = control.claim(CID, RID, "请求")
    trace = Trace(tmp_path / "trace", "query")
    token.attach(trace)
    called, release, entered = threading.Event(), threading.Event(), threading.Event()
    count = []

    def cancel():
        count.append(1)
        called.set()
        if fails:
            raise TimeoutError("模拟取消接口失败")
        return {"accepted": True}

    def query():
        with token.query({}, cancel=cancel, query_id="platform-123"):
            entered.set()
            assert release.wait(10)

    with ThreadPoolExecutor() as pool:
        run = pool.submit(query)
        try:
            assert entered.wait(10)
            control.stop(CID, RID)
            control.stop(CID, RID)
            assert called.wait(5)
        finally:
            release.set()
        with pytest.raises(RunCancelled):
            run.result(timeout=10)
    token.finish_trace()
    results = [e for e in trace.read() if e["kind"] == "query_cancel_result"]
    assert count == [1] and len(results) == 1
    assert results[0]["status"] == ("failed" if fails else "requested")


def test_query_id_registered_after_stop_gets_cancelled(tmp_path):
    control = RunControl(tmp_path)
    token = control.claim(CID, RID, "请求")
    called = threading.Event()

    class LateTrace:
        thread_id = "late"

        def event(self, kind, *_args, **_kwargs):
            if kind == "query_registered":
                control.stop(CID, RID)  # 固定在 ID 注册与工具执行之间

    token.attach(LateTrace())
    with pytest.raises(RunCancelled), token.query({}, cancel=lambda: called.set()):
        pytest.fail("取消后不能启动查询工具")
    assert called.wait(5)


def test_control_isolation_stale_request_and_latest_predecessor(tmp_path):
    control = RunControl(tmp_path)
    first = control.claim(CID, RID, "旧")
    other = control.claim("d" * 16, RID, "另一会话")
    control.stop(CID, RID, "新", NEW)
    assert first.requested.is_set() and not other.requested.is_set()
    control.finish(CID, RID, "cancelled")
    pending = control.take_pending(CID)
    assert pending["rid"] == NEW and control.take_pending(CID) is None
    token = control.claim(CID, NEW, "新")
    assert token.predecessor == RID
    with pytest.raises(ControlConflict):
        control.stop(CID, RID)
    assert not token.requested.is_set()
    control.finish(CID, NEW, "completed")
    with pytest.raises(ControlConflict):
        control.stop(CID, RID, "过期替换", "e" * 16)
    latest = control.claim(CID, "f" * 16, "正常下一轮")
    assert latest.predecessor is None  # 不翻出更老的已取消问题


def test_restart_keeps_pending_text_but_does_not_auto_execute(tmp_path):
    store = server.ChatStore(tmp_path)
    store.control.claim(CID, RID, "旧")
    store.directory(CID).mkdir()
    server.save_json(store.directory(CID) / "conversation.json", {
        "id": CID, "messages": [{"role": "user", "content": "旧", "request_id": RID}],
        "turns": [], "active": "d" * 16, "active_request_id": RID, "pending": None})
    store.control.stop(CID, RID, "重启后仍应能找回的文字", NEW)

    def forbidden(*_args, **_kwargs):
        pytest.fail("重启不能自动重放付费任务")

    restarted = server.ChatStore(tmp_path, executor=forbidden)
    status = restarted.control.status(CID)
    assert status["active"] is None
    assert status["pending_request"]["status"] == "interrupted"
    assert status["pending_request"]["text"] == "重启后仍应能找回的文字"
    assert restarted.get(CID)["messages"][-1]["status"] == "interrupted"
    assert restarted.get(CID)["active"] is None


def test_cancel_just_after_final_save_before_execution_exit(tmp_path):
    # 这个窗口以前会过早交还运行权，导致新任务拿不到尚未释放的文件锁。
    saved, release = threading.Event(), threading.Event()

    class PausingStore(server.ChatStore):
        def _send(self, *args):
            result = super()._send(*args)
            if args[2] == RID:
                saved.set()
                assert release.wait(10)
            return result

    store = PausingStore(tmp_path, executor=partial(execute, model_factory=Model))
    with ThreadPoolExecutor() as pool:
        run = pool.submit(store.send, CID, "正常查询", RID)
        try:
            assert saved.wait(10)
            assert store.control.status(CID)["active"]["rid"] == RID
            store.stop(CID, RID)
        finally:
            release.set()
        state = run.result(timeout=10)
    assert state["messages"][-1]["status"] == "cancelled"
    assert store.get(CID)["turns"] == []
    assert store.control.status(CID)["active"] is None
