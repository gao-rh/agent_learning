"""消息排队与安全位置插入：使用 Event 固定调用窗口，真实图和 SQLite，不消耗 API。"""
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, AIMessageChunk
from test_stop_replace import CID, IDS, NEW, RID, Model

from business_analysis_repro.main_agent.state import Verdict
from business_analysis_repro.playground import server
from business_analysis_repro.playground.data import query_agent
from business_analysis_repro.playground.parallel_agent import execute
from business_analysis_repro.playground.parallel_model import ParallelModel
from business_analysis_repro.playground.parallel_state import BatchResolution, MetricRequest
from business_analysis_repro.playground.parallel_trace import Trace, read_events
from business_analysis_repro.playground.run_control import ControlConflict, RunControl
from business_analysis_repro.playground.steering import MessageDecision, Steering


def wait_for(fn):
    until = time.monotonic() + 10
    while time.monotonic() < until:
        if result := fn():
            return result
        threading.Event().wait(.01)
    raise AssertionError("等待状态超时")


def task_state(root, result):
    tid = result["messages"][-1]["thread_id"]
    directory = root / CID / "tasks" / tid
    return json.loads((directory / "state.json").read_text()), read_events(directory / "trace.jsonl")


def harness(root, action="continue", fail=False):
    entered, release, handled = threading.Event(), threading.Event(), threading.Event()
    calls, decisions = [], []

    class TestModel(Model):
        def resolve(self, payload):
            latest = payload["messages"][-1]["content"]
            count = 2 if "两个指标" in latest else 1
            return BatchResolution(outcome="ready", requests=[MetricRequest(
                metric_id=mid, period={"mode": "calendar", "unit": "week",
                                      "offset": 0 if "本周" in latest else -1})
                for mid in IDS[:count]])

        def complete(self, stage, instruction, payload, schema):
            if stage == "validate_dates":
                self.trace.event("test_dates", stage, user_messages=payload["user_messages"])
            if stage == "handle_inbox":
                assert payload["observed_progress"]["queries_returned"] == 1
                assert "active_calls" in payload["observed_progress"]
                decisions.extend(payload["messages"])
                handled.set()
                if fail:
                    raise RuntimeError("模拟决策失败")
                return MessageDecision(action=action, reply="收到，按最新信息处理。",
                    instructions="只写三句话" if action == "continue" else "",
                    updated_request=payload["messages"][-1]["text"] if action == "revise" else "")
            return super().complete(stage, instruction, payload, schema)

    def slow_query(task, trace=None):
        calls.append(task.copy())
        # 真正的 cancellable_query 缓存已返回结果，在下个边界才处理插入。
        result = query_agent(task, trace)
        if len(calls) == 1:
            entered.set()
            assert release.wait(10)
        return result

    store = server.ChatStore(root, executor=partial(execute, model_factory=TestModel,
                                                   capabilities={"query": slow_query}))
    return store, entered, release, handled, calls, decisions


def test_default_queue_runs_later_in_order_without_cancellation(tmp_path):
    store, entered, release, handled, calls, _ = harness(tmp_path)
    with ThreadPoolExecutor() as pool:
        run = pool.submit(store.send, CID, "查上周一个指标", RID)
        try:
            assert entered.wait(10)
            first = store.receive(CID, "查本周一个指标", NEW, RID)
            store.receive(CID, "查上周一个指标", "d" * 16, RID)
            assert first["delivery"] == "queue"
            assert not handled.is_set()
            assert len(calls) == 1
            assert store.control.status(CID)["active"]["status"] == "running"
        finally:
            release.set()
        assert run.result(timeout=10)["messages"][-1]["status"] == "completed"
    wait_for(lambda: all(r["status"] == "applied" for r in store.control.inbox.rows(CID)))
    assistants = [m for m in store.get(CID)["messages"] if m["role"] == "assistant"]
    assert [m["request_id"] for m in assistants] == [RID, NEW, "d" * 16]
    assert len({m["thread_id"] for m in assistants}) == 3
    assert not handled.is_set() and len(calls) == 3


@pytest.mark.parametrize("action", ["continue", "reply", "stop", "revise", "failure"])
def test_insert_is_main_agent_decision_in_same_task(tmp_path, action):
    store, entered, release, handled, calls, decisions = harness(
        tmp_path, "reply" if action == "failure" else action, fail=action == "failure")
    with ThreadPoolExecutor() as pool:
        run = pool.submit(store.send, CID, "查上周一个指标", RID)
        try:
            assert entered.wait(10)
            before = store.control.status(CID)["active"]
            text = "查本周一个指标" if action == "revise" else "只写三句话"
            store.receive(CID, text, NEW, RID)
            store.insert(CID, NEW, RID)
            store.insert(CID, NEW, RID)  # 双击幂等
            assert not handled.is_set()  # 当前工具尚未返回，不能谎称已处理
        finally:
            release.set()
        result = run.result(timeout=10)
    state, events = task_state(tmp_path, result)
    assert handled.is_set() and len(decisions) == 1
    assert sum(e["kind"] == "execution_start" for e in events) == 1
    assert result["messages"][-1]["thread_id"] == before["tid"]
    assert not any(e["kind"] == "cancel_requested" for e in events) or action == "stop"
    if action == "revise":
        assert state["task_revision"] == 2 and len(calls) == 2
        assert calls[-1]["start_date"] == "2026-08-31"
        assert next(iter(state["job_results"].values()))["result"]["scope"]["start_date"] == "2026-08-31"
        assert [e for e in events if e["kind"] == "test_dates"][-1]["user_messages"] == ["查本周一个指标"]
        assert len(state["messages"]) >= 2  # 历史仍留存，但不与新范围一起校验
    else:
        assert state["task_revision"] == 1 and len(calls) == 1
    if action == "continue":
        assert state["steering_notes"] == ["只写三句话"]
    if action == "stop":
        assert state["status"] == "cancelled"
        assert not any(e.get("name") == "compose_reply" for e in events)
    else:
        assert state["status"] == "completed"
    row = store.control.inbox.rows(CID)[0]
    assert row["status"] == ("failed" if action == "failure" else "applied")


def test_revise_add_metric_reuses_compatible_data_in_same_trace(tmp_path):
    store, entered, release, _, _, _ = harness(tmp_path, "revise")
    with ThreadPoolExecutor() as pool:
        run = pool.submit(store.send, CID, "查上周一个指标", RID)
        try:
            assert entered.wait(10)
            store.receive(CID, "查上周两个指标", NEW, RID)
            store.insert(CID, NEW, RID)
        finally:
            release.set()
        result = run.result(timeout=10)
    state, events = task_state(tmp_path, result)
    assert state["status"] == "completed" and state["task_revision"] == 2
    assert len(state["result"]["cards"]) == 2
    assert sum(e["kind"] == "query_reused" for e in events) == 1
    assert sum(e["kind"] == "query_registered" for e in events) == 2
    for outcome in state["job_results"].values():
        assert outcome["result"]["task_revision"] == 2


def test_inbox_fifo_idempotence_isolation_and_restart(tmp_path):
    control = RunControl(tmp_path)
    token = control.claim(CID, RID, "任务")
    box = control.inbox
    row = box.enqueue(CID, NEW, "补充", RID)
    assert box.enqueue(CID, NEW, "补充", RID) == row
    with pytest.raises(ControlConflict):
        box.enqueue(CID, NEW, "不同文字", RID)
    with pytest.raises(ControlConflict):
        box.promote("e" * 16, NEW, RID)
    with pytest.raises(ControlConflict):
        box.promote(CID, NEW, "f" * 16)
    box.enqueue(CID, "d" * 16, "再补充", RID)
    box.promote(CID, "d" * 16, RID)
    box.promote(CID, NEW, RID)
    assert [r["text"] for r in box.claim_insertions(token)] == ["补充", "再补充"]
    assert not token.inbox_ready.is_set()
    box.enqueue(CID, "e" * 16, "尚在排队", RID)
    recovered = RunControl(tmp_path)
    assert [r["status"] for r in recovered.inbox.rows(CID)] == ["interrupted"] * 3
    assert recovered.inbox.take_idle(CID) is None  # 重启不自动产生付费调用
    assert [r["text"] for r in recovered.inbox.rows(CID)] == ["补充", "再补充", "尚在排队"]


def test_late_insert_becomes_one_followup_not_lost(tmp_path):
    store = server.ChatStore(tmp_path, executor=partial(execute, model_factory=Model))
    # 无活动任务时，发送会立即领取为普通下一轮；重复发送和插入均不重复执行。
    store.receive(CID, "查指标", NEW, RID)
    store.receive(CID, "查指标", NEW, RID)
    wait_for(lambda: store.control.inbox.rows(CID)[0]["status"] == "applied")
    store.insert(CID, NEW, RID)
    assert len(store.get(CID)["turns"]) == 1


def test_interrupted_dispatched_message_cannot_silently_reuse_old_run_id(tmp_path):
    control = RunControl(tmp_path)
    control.inbox.enqueue(CID, NEW, "原问题")
    control.inbox.take_idle(CID)
    control.claim(CID, NEW, "原问题")
    recovered = RunControl(tmp_path)
    assert recovered.inbox.rows(CID)[0]["has_run"]
    with pytest.raises(ControlConflict, match="恢复到输入框"):
        recovered.inbox.promote(CID, NEW, None)


def test_five_occupied_model_slots_release_before_main_inbox_call(tmp_path):
    control = RunControl(tmp_path)
    token = control.claim(CID, RID, "任务")
    trace = Trace(tmp_path / "trace", "five-models")
    trace.cancellation = token
    entered, release = threading.Event(), threading.Event()
    lock = threading.Lock()
    calls = []

    class Client:
        def invoke(self, messages):
            payload = json.loads(messages[-1].content)
            with lock:
                calls.append(payload)
                if len(calls) == 5:
                    entered.set()
            if "current_request" in payload:
                answer = MessageDecision(action="reply", reply="五个调用已返回，正在继续。")
            else:
                assert release.wait(10)
                answer = Verdict(passed=True, issues=[])
            return AIMessage(content=answer.model_dump_json(), usage_metadata={
                "input_tokens": 10, "output_tokens": 5, "total_tokens": 15})

    model = object.__new__(ParallelModel)
    model.trace, model.max_calls, model.model_name, model.client = trace, 40, "offline", Client()
    token.steering = Steering(token, model, trace, "任务")
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(model.complete, "test", "复核", {"index": i}, Verdict) for i in range(5)]
        try:
            assert entered.wait(10)
            control.inbox.enqueue(CID, NEW, "进度如何", RID)
            control.inbox.promote(CID, NEW, RID)
        finally:
            release.set()
        assert all(f.result(timeout=10).passed for f in futures)
    assert len(calls) == 6
    assert control.inbox.rows(CID)[0]["status"] == "applied"
    assert sum(e["kind"] == "model_response" for e in trace.read()) == 6


def test_supplement_during_stream_rewrites_reply_without_querying_again(tmp_path):
    entered, release = threading.Event(), threading.Event()
    payloads = []

    class Client:
        def invoke(self, messages):
            decision = MessageDecision(action="continue", reply="好，改成三句话。", instructions="只写三句话")
            return AIMessage(content=decision.model_dump_json(), usage_metadata={
                "input_tokens": 10, "output_tokens": 5, "total_tokens": 15})

        def stream(self, messages, **_):
            payload = json.loads(messages[-1].content)
            payloads.append(payload)
            if len(payloads) == 1:
                entered.set()
                assert release.wait(10)
                text = "旧版长摘要。"
            else:
                assert payload["user_supplements"] == ["只写三句话"]
                text = "按三句话要求生成的模拟查询摘要。"
            yield AIMessageChunk(content=text, usage_metadata={
                "input_tokens": 10, "output_tokens": 5, "total_tokens": 15})

    class TestModel(ParallelModel):
        def __init__(self, trace, max_calls):
            self.trace, self.max_calls, self.model_name = trace, max_calls, "offline"
            client = Client()
            self.client = SimpleNamespace(invoke=client.invoke, bound=client)

        resolve = Model.resolve

        def complete(self, stage, instruction, payload, schema):
            if stage in {"compose_batch", "handle_inbox"}:
                return super().complete(stage, instruction, payload, schema)
            return Model.complete(self, stage, instruction, payload, schema)

    store = server.ChatStore(tmp_path, executor=partial(execute, model_factory=TestModel))
    with ThreadPoolExecutor() as pool:
        run = pool.submit(store.send, CID, "查指标", RID)
        try:
            assert entered.wait(10)
            store.receive(CID, "只写三句话", NEW, RID)
            store.insert(CID, NEW, RID)
        finally:
            release.set()
        result = run.result(timeout=10)
    state, events = task_state(tmp_path, result)
    assert len(payloads) == 2 and state["status"] == "completed"
    assert "按三句话" in state["answer"] and "旧版" not in state["answer"]
    assert sum(e["kind"] == "query_registered" for e in events) == 1
    assert sum(e["kind"] == "model_response" for e in events) == 3  # 包括被替换的草稿
    assert state["task_revision"] == 1
