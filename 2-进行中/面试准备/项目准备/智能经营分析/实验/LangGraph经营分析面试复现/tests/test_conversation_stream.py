"""普通对话和业务工具共用原生模型流；固定返回边界以排除事后拆字。"""
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.request import Request, urlopen

import pytest
from langchain_core.messages import AIMessageChunk
from test_streaming_playground import CID, RID, read_frame

from business_analysis_repro.main_agent.model import ModelFailure
from business_analysis_repro.playground import server
from business_analysis_repro.playground.parallel_agent import execute
from business_analysis_repro.playground.parallel_model import ParallelModel
from business_analysis_repro.playground.parallel_trace import Trace, read_events
from business_analysis_repro.playground.streaming import public_event
from business_analysis_repro.playground.usage import summarize, task_kind


@pytest.mark.parametrize("history", [[], [{"question": "查上周保费", "task": {"jobs": []}, "answer": "旧结果"}]])
def test_greeting_visible_before_model_finishes_and_does_not_force_tools(tmp_path, history):
    release = threading.Event()
    payloads = []

    class Client:
        def bind_tools(self, *_):
            return self

        def stream(self, messages, **kwargs):
            payloads.append(json.loads(messages[-1].content))
            assert kwargs["stream_usage"]
            yield AIMessageChunk(content="你好，")
            assert release.wait(10)
            yield AIMessageChunk(content="有什么可以帮你？", usage_metadata={
                "input_tokens": 20, "output_tokens": 8, "total_tokens": 28})

    class Model(ParallelModel):
        def __init__(self, trace, max_calls):
            self.trace, self.max_calls, self.model_name = trace, max_calls, "offline"
            self.client = SimpleNamespace(bound=Client())

    store = server.ChatStore(tmp_path, executor=partial(execute, model_factory=Model))
    directory = store.directory(CID)
    directory.mkdir()
    (directory/"conversation.json").write_text(json.dumps({"messages": [], "turns": history, "pending": None}))
    http = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(store))
    threading.Thread(target=http.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{http.server_port}"

    def send():
        with urlopen(Request(url+"/api/message", data=json.dumps({
            "id": CID, "request_id": RID, "text": "你好"}).encode(),
            headers={"Content-Type": "application/json"}), timeout=15) as r:
            return json.load(r)

    try:
        with ThreadPoolExecutor() as pool:
            running = pool.submit(send)
            try:
                with urlopen(url+f"/api/events?id={CID}&request_id={RID}", timeout=15) as stream:
                    while f := read_frame(stream):
                        if f.get("data", {}).get("type") == "answer_delta":
                            assert f["data"]["delta"] == "你好，"
                            break
                    else:
                        pytest.fail("没有收到模型未完成时的正文片段")
                assert not running.done()
            finally:
                release.set()
            result = running.result(timeout=15)
        message = result["messages"][-1]
        assert message["content"] == "你好，有什么可以帮你？"
        assert message["response_kind"] == "conversation"
        ev = read_events(directory/"tasks"/message["thread_id"]/"trace.jsonl")
        assert summarize(ev)["calls"] == 1 and summarize(ev)["total_tokens"] == 28
        assert task_kind(ev, "你好") == "conversation"
        assert not any(e["name"] in {"search_metrics", "finish_resolution", "compose_batch"} for e in ev)
        assert payloads[0]["conversation_context"] == history
    finally:
        release.set()
        http.shutdown()
        http.server_close()


def make_model(path, client):
    model = object.__new__(ParallelModel)
    model.client = SimpleNamespace(bound=client)
    model.trace = Trace(path, "stream-resolve")
    model.max_calls, model.model_name = 40, "offline"
    return model


def test_partial_tool_json_never_becomes_body_and_plan_waits_for_full_arguments(tmp_path):
    class Client:
        calls = 0

        def bind_tools(self, *_):
            return self

        def stream(self, *_args, **_kwargs):
            self.calls += 1
            name = "get_metric_definition" if self.calls == 1 else "finish_resolution"
            mid = "demo_metric_fx_premium"
            args = ({"metric_id": mid} if self.calls == 1 else {"outcome": "ready", "requests": [
                {"metric_id": mid, "period": {"mode": "calendar", "unit": "week", "offset": -1}}]})
            raw = json.dumps(args)
            yield AIMessageChunk(content="", tool_call_chunks=[{
                "index": 0, "id": "call-"+str(self.calls), "name": name, "args": raw[:15]}])
            assert not any(e["kind"] == "span_start" and e["name"] == name for e in model.trace.read())
            yield AIMessageChunk(content="", tool_call_chunks=[{
                "index": 0, "id": None, "name": None, "args": raw[15:]}])

    model = make_model(tmp_path, Client())
    proposal = model.resolve({"messages": [{"role": "human", "content": "查询上周放心吃净保费规模"}]})
    assert proposal.outcome == "ready" and len(proposal.requests) == 1
    ev = model.trace.read()
    assert sum(e["kind"] == "model_request" for e in ev) == 2
    assert not any((public_event(e) or {}).get("type") == "answer_delta" for e in ev)


@pytest.mark.parametrize("error_class", [ConnectionError, type("OpenAIConnectionError", (Exception,), {})])
def test_resolve_stream_failure_discards_partial_text_then_retries(tmp_path, monkeypatch, error_class):
    monkeypatch.setattr("business_analysis_repro.playground.parallel_model.time.sleep", lambda _: None)

    class Client:
        calls = 0

        def bind_tools(self, *_):
            return self

        def stream(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                yield AIMessageChunk(content="丢弃的半句")
                raise error_class("offline failure")
            yield AIMessageChunk(content="你好！")

    model = make_model(tmp_path, Client())
    assert model.resolve({"messages": []}).question == "你好！"
    assert sum(e["kind"] == "answer_reset" for e in model.trace.read()) == 1
    assert summarize(model.trace.read())["calls"] == 2


def test_empty_no_tool_response_does_not_loop_ten_times(tmp_path):
    class Client:
        def bind_tools(self, *_):
            return self

        def stream(self, *_args, **_kwargs):
            yield AIMessageChunk(content="")

    model = make_model(tmp_path, Client())
    with pytest.raises(ModelFailure):
        model.resolve({"messages": []})
    assert summarize(model.trace.read())["calls"] == 1


def test_clarification_question_streams_before_tool_arguments_finish(tmp_path):
    entered, release = threading.Event(), threading.Event()

    class Client:
        def bind_tools(self, *_):
            return self

        def stream(self, *_args, **_kwargs):
            yield AIMessageChunk(content="", tool_call_chunks=[{
                "index": 0, "id": "clarify", "name": "finish_resolution",
                "args": '{"outcome":"clarify","question":"请确认'}])
            entered.set()
            assert release.wait(10)
            yield AIMessageChunk(content="", tool_call_chunks=[{
                "index": 0, "id": None, "name": None, "args": '保费指标和日期。","requests":[]}'}])

    model = make_model(tmp_path, Client())
    with ThreadPoolExecutor() as pool:
        task = pool.submit(model.resolve, {"messages": []})
        try:
            assert entered.wait(10)
            ev = model.trace.read()
            assert [e["delta"] for e in ev if e["kind"] == "answer_delta"] == ["请确认"]
            assert not any(e["kind"] == "model_response" for e in ev)
            assert not any(e["kind"] == "span_start" and e["name"] == "finish_resolution" for e in ev)
            assert not task.done()
        finally:
            release.set()
        proposal = task.result(timeout=10)
    assert proposal.outcome == "clarify" and proposal.question == "请确认保费指标和日期。"
