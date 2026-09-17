"""上下文预算/事实保留/缓存/故障边界的离线回归，不依赖模型表现。"""
import json
from copy import deepcopy
from functools import partial

import pytest

from business_analysis_repro.main_agent.model import ModelFailure
from business_analysis_repro.playground.context_memory import (
    ContextMemory,
    ContextPolicy,
    business_anchor,
    history_from_conversation,
    tokens,
)
from business_analysis_repro.playground.parallel_agent import execute
from business_analysis_repro.playground.parallel_state import BatchResolution
from business_analysis_repro.playground.parallel_trace import Trace, render_html
from business_analysis_repro.playground.run_control import RunCancelled
from business_analysis_repro.playground.server import ChatStore
from business_analysis_repro.playground.usage import summarize

POLICY = ContextPolicy(trigger_tokens=3000, target_tokens=2000, recent_tokens=700,
                       summary_tokens=300, batch_tokens=5000)
TASK = {"jobs": [{"job_id": "r1-test", "name": "放心吃净保费规模", "task": {
    "metric_id": "demo_metric_fx_premium", "intent": "query",
    "start_date": "2026-08-24", "end_date": "2026-08-30",
    "filters": {"merchant_age": ["new_merchant"]}, "group_by": []}}]}


class SummaryModel:
    def __init__(self, trace, **_kwargs):
        self.trace, self.inputs = trace, []

    def complete(self, stage, instruction, payload, schema):
        assert stage == "compress_context"
        self.inputs.append(deepcopy(payload))
        self.trace.event("model_request", stage, model="offline")
        self.trace.event("model_response", stage, usage={
            "input_tokens": 100, "output_tokens": 20, "total_tokens": 120})
        return schema(summary="用户此前查过放心吃净保费，只看新商；喜欢简洁回答。旧结果不是新证据。")


def history(n=12):
    rows = [{"question": f"第{i}轮闲聊", "task": None,
             "answer": "普通历史问答，保留原记录。" * 30} for i in range(n)]
    rows[0] = {"question": "查上周放心吃净保费，只看新商", "task": deepcopy(TASK),
               "answer": "模拟结果。"}
    return rows


def manager(tmp_path, policy=POLICY, factory=SummaryModel):
    trace = Trace(tmp_path / "trace", "context-test")
    model = factory(trace)
    return ContextMemory(model, trace, tmp_path / "memory.json", policy), trace, model


def test_short_history_is_complete_and_has_no_summary_charge(tmp_path):
    memory, trace, model = manager(tmp_path)
    rows = history(5)
    rows[1:]=[{"question": str(i), "task": None, "answer": "你好"} for i in range(4)]
    original = deepcopy(rows)
    current = [{"role": "human", "content": "改成本周"}]
    result = memory.prepare(rows, current)
    assert result["conversation_context"] == original
    assert len(result["conversation_context"]) == 5
    assert not model.inputs and summarize(trace.read())["calls"] == 0
    assert rows == original and current[0]["content"] == "改成本周"


def test_long_history_preserves_anchor_and_recent_raw_and_limits_budget(tmp_path):
    memory, trace, model = manager(tmp_path)
    rows, current = history(), [{"role": "human", "content": "改成本周，取消新商筛选"}]
    original = deepcopy(rows)
    result = memory.prepare(rows, current)
    assert model.inputs
    assert result["conversation_context"][-1] == rows[-1]
    assert result["conversation_memory"]["business_anchor"]["task"] == TASK
    assert tokens(result) < POLICY.target_tokens
    assert rows == original
    # 当前需求未进入摘要；精确字段来自原任务，不是摘要生成的结果。
    assert "取消新商筛选" not in json.dumps(model.inputs, ensure_ascii=False)
    assert summarize(trace.read())["total_tokens"] == 120 * len(model.inputs)
    page = render_html(trace.read(), "context-test")
    assert "本轮模型记住了什么" in page and "单独保留的业务条件" in page


def test_restart_reuses_summary_and_incremental_compaction_reads_only_new_prefix(tmp_path):
    memory, trace, model = manager(tmp_path)
    rows = history()
    memory.prepare(rows, [])
    covered = memory.cache["covered_turns"]
    cached = deepcopy(memory.cache)
    fresh = ContextMemory(model, trace, tmp_path / "memory.json", POLICY)
    model.inputs.clear()
    fresh.prepare(rows + [{"question": "谢谢", "task": None, "answer": "不客气"}], [])
    assert not model.inputs
    assert fresh.cache == cached
    extended = rows + history()[1:]
    fresh.prepare(extended, [])
    assert model.inputs and model.inputs[0]["previous_summary"] == cached["summary"]
    assert model.inputs[0]["new_turns"][0] == extended[covered]


def test_changed_or_cancelled_history_invalidates_summary(tmp_path):
    memory, _trace, model = manager(tmp_path)
    rows = history()
    memory.prepare(rows, [])
    model.inputs.clear()
    rows[0]["question"] = "改查商户数"
    rows[0]["task"] = None
    result = memory.prepare(rows, [])
    assert model.inputs[0]["previous_summary"] == ""
    assert result["conversation_memory"]["business_anchor"] is None
    model.inputs.clear()
    result = memory.prepare([], [])
    assert result["conversation_memory"]["summary"] == ""
    assert result["conversation_context"] == []


def test_latest_task_replaces_conditions_but_casual_chat_does_not_erase_it(tmp_path):
    rows = history()
    new_task = deepcopy(TASK)
    new_task["jobs"][0]["task"]["filters"] = {}
    rows += [{"question": "取消新商筛选", "task": new_task, "answer": "完成"},
             {"question": "你好", "task": None, "answer": "你好"},
             {"question": "未完成任务", "task": TASK, "answer": "", "cancelled": True}]
    memory, _, _ = manager(tmp_path)
    result = memory.prepare(rows, [])
    assert result["conversation_memory"]["business_anchor"]["task"] == new_task
    assert business_anchor(rows)["task"] == new_task


def test_summary_failure_uses_marked_excerpt_and_remains_accounted(tmp_path):
    class Broken(SummaryModel):
        def complete(self, *args):
            self.trace.event("model_request", "compress_context", model="offline")
            self.trace.event("model_error", "compress_context")
            raise ModelFailure("offline")
    memory, trace, _ = manager(tmp_path, factory=Broken)
    result = memory.prepare(history(), [])
    assert result["conversation_memory"]["degraded"]
    assert result["conversation_memory"]["business_anchor"]["task"] == TASK
    assert tokens(result) < POLICY.trigger_tokens
    assert summarize(trace.read())["usage_unknown_calls"] == 1


@pytest.mark.parametrize("exception", [RunCancelled])
def test_cancellation_during_summary_propagates(tmp_path, exception):
    class Cancelled(SummaryModel):
        def complete(self, *args):
            raise exception()
    memory, _, _ = manager(tmp_path, factory=Cancelled)
    with pytest.raises(exception):
        memory.prepare(history(), [])
    assert not (tmp_path / "memory.json").exists()


def test_huge_import_caps_extra_calls_and_marks_omissions(tmp_path):
    memory, trace, model = manager(tmp_path)
    result = memory.prepare(history(100), [])
    assert len(model.inputs) <= POLICY.max_summary_calls
    assert result["conversation_memory"]["degraded"]
    assert "未作语义摘要" in result["conversation_memory"]["summary"]
    assert trace.read()[-2 if trace.read()[-1]["kind"] == "span_end" else -1]["omitted_turns"] > 0


def test_single_huge_turn_is_marked_and_current_input_stays_untouched(tmp_path):
    memory, _, _ = manager(tmp_path)
    current = [{"role": "human", "content": "当前问题" * 1000}]
    before = deepcopy(current)
    result = memory.prepare([{"question": "历史", "task": TASK, "answer": "很长" * 20000}], current)
    assert result["conversation_context"][0]["excerpted"]
    assert result["conversation_memory"]["degraded"]
    assert result["conversation_memory"]["business_anchor"]["task"] == TASK
    assert current == before
    assert tokens(result) < POLICY.trigger_tokens


def test_corrupt_cache_rebuilds_from_source(tmp_path):
    (tmp_path / "memory.json").write_text("{broken")
    memory, trace, model = manager(tmp_path)
    memory.prepare(history(), [])
    assert model.inputs[0]["previous_summary"] == ""
    assert any(e["kind"] == "context_cache_invalid" for e in trace.read())


def test_clarifications_and_inserted_messages_survive_history_projection():
    state = {"turns": [{"thread_id": "task", "request_id": "r2", "question": "上周",
                       "task": TASK, "answer": "已查"}], "messages": [
        {"role": "user", "request_id": "r1", "content": "查放心吃净保费"},
        {"role": "assistant", "request_id": "r1", "thread_id": "task", "content": "哪段时间？"},
        {"role": "user", "request_id": "r2", "content": "上周"},
        {"role": "user", "request_id": "insert", "root_request_id": "r2", "content": "简短一些"},
        {"role": "assistant", "request_id": "insert", "root_request_id": "r2", "content": "好的"},
        {"role": "assistant", "request_id": "r2", "thread_id": "task", "content": "已查"}]}
    row = history_from_conversation(state)[0]
    assert [m["content"] for m in row["dialogue"]] == [m["content"] for m in state["messages"]]


def test_server_graph_integration_keeps_all_short_rounds_and_isolates_conversations(tmp_path):
    payloads = []

    class ReplyModel(SummaryModel):
        def resolve(self, payload):
            payloads.append(payload)
            return BatchResolution(outcome="reply", question="你好")
    store = ChatStore(tmp_path, executor=partial(execute, model_factory=ReplyModel))
    cid = "f" * 16
    for i in range(6):
        store.send(cid, f"普通消息{i}")
    assert len(payloads[-1]["conversation_context"]) == 5
    assert payloads[-1]["conversation_context"][0]["question"] == "普通消息0"
    assert len(store.get(cid)["messages"]) == 12
    store.send("e" * 16, "新会话")
    assert payloads[-1]["conversation_context"] == []
    assert payloads[-1]["conversation_memory"]["business_anchor"] is None


def test_knowledge_consultation_keeps_previous_data_scope_and_date_review_is_narrow(tmp_path):
    from business_analysis_repro.playground.context_memory import date_review_history
    rows = history()
    knowledge = deepcopy(TASK)
    knowledge["jobs"][0]["task"] = {"metric_id": "demo_metric_fx_premium", "intent": "knowledge"}
    rows += [{"question": "它的口径是什么", "task": knowledge, "answer": "这是口径"}]
    memory, _, _ = manager(tmp_path)
    result = memory.prepare(rows, [])
    mem = result["conversation_memory"]
    assert mem["business_anchor"]["task"] == knowledge
    assert mem["last_data_task"]["task"] == TASK
    assert date_review_history(result) == [{
        "metric_id": "demo_metric_fx_premium", "intent": "query",
        "start_date": "2026-08-24", "end_date": "2026-08-30"}]
    assert "filters" not in json.dumps(date_review_history(result))


def test_short_answer_is_not_truncated_at_1800_characters(tmp_path):
    memory, _, model = manager(tmp_path)
    text = "原文A" * 700
    result = memory.prepare([{"question": "解释", "task": None, "answer": text}], [])
    assert result["conversation_context"][0]["answer"] == text
    assert not model.inputs
