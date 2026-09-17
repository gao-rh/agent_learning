"""流式传输契约：真实图/HTTP/SSE/SQLite，替身模型，不消耗 API。

用 Event 阻塞最后一块：客户端先收到正文时 POST 必须仍未结束。
重连读游标、澄清追加日志、草稿撤回、查看已有明细均有独立边界断言。
"""

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.request import Request, urlopen

import pytest
from langchain_core.messages import AIMessageChunk

from business_analysis_repro.main_agent.model import ModelFailure
from business_analysis_repro.main_agent.state import Reply, Verdict
from business_analysis_repro.playground import server
from business_analysis_repro.playground.parallel_agent import execute
from business_analysis_repro.playground.parallel_model import ParallelModel
from business_analysis_repro.playground.parallel_state import BatchResolution, MetricRequest
from business_analysis_repro.playground.parallel_trace import Trace, read_events
from business_analysis_repro.playground.streaming import iter_sse, public_event, tail_events

CID, RID = "a" * 16, "b" * 16


def read_frame(stream):
    frame = {}
    while line := stream.readline().decode():
        if line == "\n":
            if "data" in frame:
                frame["data"] = json.loads(frame["data"])
                return frame
            frame = {}
        elif ": " in line:
            key, value = line.rstrip("\n").split(": ", 1)
            frame[key] = value
    return None


def test_http_true_chunks_before_completion_disconnect_resume_and_dedup(tmp_path):
    release = threading.Event()
    calls = []

    class StreamClient:
        def stream(self, messages, **kwargs):
            calls.append("compose")
            assert kwargs["stream_usage"] is True
            yield AIMessageChunk(content="这段正文先出现，")
            assert release.wait(8), "测试须先收到流式文字再释放模型"
            yield AIMessageChunk(content="随后才生成完毕。")
            yield AIMessageChunk(
                content="",
                response_metadata={"finish_reason": "stop"},
                usage_metadata={"input_tokens": 10, "output_tokens": 8, "total_tokens": 18},
            )

    class Model(ParallelModel):
        def __init__(self, trace, max_calls):
            self.trace, self.max_calls, self.model_name = trace, max_calls, "offline-stream"
            self.client = SimpleNamespace(bound=StreamClient())

        def resolve(self, payload):
            return BatchResolution(
                outcome="ready",
                requests=[
                    MetricRequest(
                        metric_id="demo_metric_cancel_order_rate",
                        intent="analysis",
                        period={"mode": "calendar", "unit": "week", "offset": -1},
                        group_by=["merchant_age"],
                    )
                ],
            )

        def complete(self, stage, instruction, payload, schema):
            if stage == "compose_batch":
                return super().complete(stage, instruction, payload, schema)
            return Verdict(passed=True, issues=[])

    store = server.ChatStore(tmp_path, executor=partial(execute, model_factory=Model))
    http = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(store))
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{http.server_port}"

    def post():
        req = Request(
            url + "/api/message",
            data=json.dumps({"id": CID, "text": "分析上周变化", "request_id": RID}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(req, timeout=10) as response:
            return json.load(response)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            result = pool.submit(post)
            events = []
            with urlopen(url + f"/api/events?id={CID}&request_id={RID}", timeout=10) as response:
                while frame := read_frame(response):
                    events.append(frame)
                    if frame.get("data", {}).get("type") == "answer_delta":
                        break
            assert not result.done(), "不是等待整段完成后才把文字拆块发送"
            assert events[-1]["data"]["delta"] == "这段正文先出现，"
            cards = [e["data"]["card"] for e in events if e.get("data", {}).get("type") == "card"]
            assert cards and cards[0]["intent"] == "analysis" and cards[0]["has_baseline"]
            assert len(cards[0]["rows"]) == 2
            # 关闭SSE后POST还在执行；原游标重连只补读后续块。
            last_id = events[-1]["id"]
            req = Request(
                url + f"/api/events?id={CID}&request_id={RID}", headers={"Last-Event-ID": last_id}
            )
            with urlopen(req, timeout=10) as response:
                release.set()
                remaining = []
                while frame := read_frame(response):
                    remaining.append(frame)
                    if frame["event"] == "done":
                        break
            assert [
                e["data"]["delta"]
                for e in remaining
                if e.get("data", {}).get("type") == "answer_delta"
            ] == ["随后才生成完毕。"]
            state = result.result(timeout=5)
            assert state["messages"][-1]["status"] == "completed"
            assert "这段正文先出现，随后才生成完毕。" in state["messages"][-1]["content"]
            assert remaining[-1]["data"] == state
            assert state["active_request_id"] is None
            assert post() == state
            assert calls == ["compose"], "订阅、重连、重复POST均不得重复生成"
            trace = read_events(
                tmp_path / CID / "tasks" / state["messages"][-1]["thread_id"] / "trace.jsonl"
            )
            assert (
                sum(
                    e["kind"] == "model_response" and e["usage"].get("total_tokens") == 18
                    for e in trace
                )
                == 1
            )
    finally:
        release.set()
        http.shutdown()
        http.server_close()
        thread.join(timeout=2)


def make_model(tmp_path, client):
    model = object.__new__(ParallelModel)
    model.trace = Trace(tmp_path, "test-stream")
    model.client = SimpleNamespace(bound=client)
    model.max_calls, model.model_name = 40, "offline"
    return model


def test_failed_prefix_retracted_before_retry_and_evidence_bound(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "business_analysis_repro.playground.parallel_model.time.sleep", lambda _: None
    )

    class Client:
        calls = 0

        def stream(self, messages, **kwargs):
            self.calls += 1
            if self.calls == 1:
                yield AIMessageChunk(content="不能保留的半截草稿")
                raise ConnectionError("mock disconnect")
            yield AIMessageChunk(content="重试后的完整回答")

    model = make_model(tmp_path, Client())
    reply = model.complete("compose_batch", "总结", {"evidence_ids": ["trusted-result"]}, Reply)
    assert reply.text == "重试后的完整回答" and reply.evidence_ids == ["trusted-result"]
    events = model.trace.read()
    kinds = [e["kind"] for e in events if e["kind"].startswith("answer_")]
    assert kinds == [
        "answer_start",
        "answer_delta",
        "answer_reset",
        "answer_start",
        "answer_delta",
        "answer_end",
    ]
    assert sum(e["kind"] == "model_request" for e in events) == 2


def test_nonretryable_stream_error_does_not_consume_second_call(tmp_path):
    class Client:
        def stream(self, *args, **kwargs):
            raise ValueError("invalid model configuration")
            yield  # pragma: no cover

    model = make_model(tmp_path, Client())
    with pytest.raises(ModelFailure):
        model.complete("compose_batch", "", {"evidence_ids": []}, Reply)
    assert sum(e["kind"] == "model_request" for e in model.trace.read()) == 1
    assert any(e["kind"] == "answer_reset" for e in model.trace.read())


def test_tail_preserves_partial_utf8_and_does_not_resend_old_rows(tmp_path):
    path = tmp_path / "trace.jsonl"
    first = json.dumps({"seq": 1, "delta": "中"}, ensure_ascii=False).encode() + b"\n"
    second = json.dumps({"seq": 2, "delta": "文"}, ensure_ascii=False).encode() + b"\n"
    cut = second.index("文".encode()) + 1
    path.write_bytes(first + second[:cut])
    rows, offset = tail_events(path, 0)
    assert rows == [{"seq": 1, "delta": "中"}] and offset == len(first)
    with path.open("ab") as handle:
        handle.write(second[cut:])
    rows, offset = tail_events(path, offset)
    assert rows == [{"seq": 2, "delta": "文"}] and offset == len(first + second)
    assert tail_events(path, offset)[0] == []


def test_clarification_resume_floor_and_live_payload_filter(tmp_path):
    store = server.ChatStore(tmp_path)
    directory = store.directory(CID)
    trace = Trace(directory / "tasks" / ("c" * 16), "c" * 16)
    trace.event("answer_delta", "compose_batch", delta="上一轮不能重放")
    floor = trace.seq
    trace.event("state_snapshot", "values", state={"private": "raw-state"})
    trace.event("model_request", "resolve", messages=["raw-prompt"])
    trace.event("answer_start", "compose_batch", attempt=1)
    trace.event("answer_delta", "compose_batch", delta="本轮文字")
    state = store.get(CID)
    state["messages"].append(
        {
            "role": "assistant",
            "request_id": RID,
            "thread_id": "c" * 16,
            "stream_after_seq": floor,
            "content": "本轮文字",
        }
    )
    server.save_json(directory / "conversation.json", state)
    raw = b"".join(iter_sse(store, CID, RID)).decode()
    assert "本轮文字" in raw and "上一轮不能重放" not in raw
    assert "raw-state" not in raw and "raw-prompt" not in raw
    assert "event: done" in raw
    assert public_event({"kind": "model_response", "content": "internal JSON"}) is None


def test_show_details_is_navigation_only_and_real_query_still_executes(tmp_path):
    calls = []

    def executor(root, tid, text, **kwargs):
        calls.append(text)
        return {
            "status": "completed",
            "answer": "结果",
            "task": {},
            "result": {
                "cards": [
                    {
                        "job_id": "job1",
                        "name": "测试指标",
                        "intent": "analysis",
                        "status": "ok",
                        "rows": [{"group": "新商", "current": "10%"}],
                    }
                ]
            },
        }, root / tid

    store = server.ChatStore(tmp_path, executor=executor)
    first = store.send(CID, "分析上周", "1" * 16)
    original = first["messages"][-1]
    state = store.send(CID, "好，12行明细我咋没看到呢？展展开在哪里去了呢？", RID)
    assert len(calls) == 1
    assert state["messages"][-1]["view_only"] is True
    assert state["messages"][-1]["thread_id"] == original["thread_id"]
    assert state["messages"][-1]["result_cards"] == original["result_cards"]
    assert len(state["turns"]) == 1
    store.send(CID, "重新查询上周明细并展开", "2" * 16)
    assert len(calls) == 2
    store.send(CID, "查询今天老商的表格，展开看看", "3" * 16)
    assert len(calls) == 3
