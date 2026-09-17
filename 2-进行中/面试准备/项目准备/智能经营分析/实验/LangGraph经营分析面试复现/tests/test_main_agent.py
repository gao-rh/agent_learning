"""主图的确定性验收：用可控模型制造真实模型不一定碰到的失败。

这些测试验证图、准入、重试、恢复和证据边界，不声称验证了 Kimi 的理解能力。
真实 Kimi 的验收另外运行，保存在 .runs/main-agent 中。
"""

import json

import pytest

from business_analysis_repro.main_agent.capabilities import analysis_agent, query_agent
from business_analysis_repro.main_agent.model import KimiModel, ModelFailure
from business_analysis_repro.main_agent.runtime import execute, locked
from business_analysis_repro.main_agent.state import Proposal, Reply, Verdict
from business_analysis_repro.main_agent.trace import Trace


def proposal(**updates):
    return {
        "intent": "query",
        "business": "准时保",
        "metric": "premium",
        "period": {"mode": "calendar", "unit": "week", "offset": -1},
        **updates,
    }


class ScriptedModel:
    """不是自然语言模型，只按用例注入明确的提议和错误。"""

    model_name = "deterministic-test-double"

    def __init__(self, proposals=None, bad_replies=0, reject_count=0, failure_stage=None):
        self.proposals = list(proposals or [proposal()])
        self.bad_replies = bad_replies
        self.reject_count = reject_count
        self.failure_stage = failure_stage
        self.calls = []

    def complete(self, stage, instruction, payload, schema):
        self.calls.append(stage)
        if stage == self.failure_stage:
            raise ModelFailure("模拟模型故障")
        if stage == "understand_request":
            return Proposal.model_validate(self.proposals.pop(0))
        if stage == "compose_reply":
            evidence = payload["evidence"]
            text = "模拟数据。" + "；".join(f"{k}：{v}" for k, v in evidence["facts"].items())
            if self.bad_replies:
                self.bad_replies -= 1
                text += "凭空增加 999999999 元。"
            return Reply(text=text, evidence_ids=[evidence["evidence_id"]])
        if self.reject_count:
            self.reject_count -= 1
            return Verdict(passed=False, issues=["模拟语义校验失败"])
        return Verdict(passed=True, issues=[])


def run(tmp_path, model=None, thread_id="case", **kwargs):
    model = model or ScriptedModel()
    return execute(
        output_dir=tmp_path,
        thread_id=thread_id,
        model_factory=lambda trace, **_: model,
        question="受控测试问题",
        reference_date="2026-09-01",
        **kwargs,
    )


def events(directory):
    return [json.loads(line) for line in (directory / "trace.jsonl").read_text().splitlines()]


def node_names(directory):
    return [
        e["name"]
        for e in events(directory)
        if e["kind"] == "span_start" and e.get("category") == "node"
    ]


@pytest.mark.parametrize(
    "intent,node",
    [("query", "run_query"), ("analysis", "run_analysis"), ("knowledge", "consult_knowledge")],
)
def test_three_routes_and_evidence(tmp_path, intent, node):
    state, directory = run(tmp_path, ScriptedModel([proposal(intent=intent)]))
    assert state["status"] == "completed"
    assert node_names(directory) == ["understand_request", node, "compose_reply", "validate_reply"]
    assert state["result"]["source"] == intent
    assert state["result"]["evidence_id"] in state["answer"]
    assert state["validation"]["passed"] is True
    if intent == "query":
        assert state["result"]["total"] == 56000
    if intent == "analysis":
        result = state["result"]
        assert result["baseline"]["total"] == 70000
        assert result["channel_deltas"] == {"App": -10500, "小程序": -3500}
        assert result["facts"]["变动率"] == "-20.0%"


def test_resume_new_runtime_uses_saved_state(tmp_path):
    state, directory = run(tmp_path, ScriptedModel([proposal(business=None)]))
    assert state["status"] == "waiting_user"
    assert state["result"] is None
    assert node_names(directory) == ["understand_request", "clarify"]
    # execute 已关闭 SQLite；第二次重新建 Graph/checkpointer，验证真实的磁盘恢复。
    resumed, _ = execute(
        output_dir=tmp_path,
        thread_id="case",
        answer="准时保",
        model_factory=lambda *a, **k: ScriptedModel(),
    )
    assert resumed["status"] == "completed"
    assert resumed["reference_date"] == "2026-09-01"
    assert resumed["task_revision"] == 2
    assert resumed["clarification_count"] == 1
    assert len(resumed["messages"]) == 3
    assert len({e["run_id"] for e in events(directory)}) == 2
    assert any(e.get("status") == "interrupted" for e in events(directory))
    assert node_names(directory).count("run_query") == 1


def test_clarification_cap_prevents_infinite_loop(tmp_path):
    model = ScriptedModel([proposal(business=None)] * 4)
    state, directory = run(tmp_path, model)
    for _ in range(3):
        state, _ = execute(
            output_dir=tmp_path,
            thread_id="case",
            answer="继续",
            model_factory=lambda *a, **k: model,
        )
    assert state["status"] == "failed"
    assert "澄清上限" in state["answer"]
    assert "run_query" not in node_names(directory)


@pytest.mark.parametrize("bad_replies,expected", [(1, "completed"), (2, "failed")])
def test_reply_repair_is_bounded_without_refetch(tmp_path, bad_replies, expected):
    state, directory = run(tmp_path, ScriptedModel(bad_replies=bad_replies))
    assert state["status"] == expected
    assert state["repair_count"] == 1
    assert node_names(directory).count("run_query") == 1
    assert node_names(directory).count("compose_reply") == 2
    assert "999999999" not in state["answer"]


def test_semantic_judge_can_trigger_repair(tmp_path):
    state, directory = run(tmp_path, ScriptedModel(reject_count=1))
    assert state["status"] == "completed"
    assert state["repair_count"] == 1
    assert node_names(directory).count("run_query") == 1


@pytest.mark.parametrize(
    "updates",
    [
        {"intent": "unsupported"},
        {"metric": "利润率"},
        {"business": "未知业务"},
        {"period": {"mode": "calendar", "unit": "year", "offset": 0}},
        {"period": {"mode": "exact", "unit": "day", "offset": 0, "exact_date": "2027-01-01"}},
    ],
)
def test_unsupported_and_query_admission(tmp_path, updates):
    state, _ = run(tmp_path, ScriptedModel([proposal(**updates)]))
    assert state["status"] == "failed"
    assert not state["validation"]["passed"]
    assert "本次未完成" in state["answer"]


@pytest.mark.parametrize("intent", ["query", "analysis"])
def test_both_capabilities_enforce_permissions(tmp_path, intent):
    state, directory = run(
        tmp_path,
        ScriptedModel([proposal(intent=intent)]),
        graph_options={"allowed_businesses": ("运费险",)},
    )
    assert state["status"] == "failed"
    assert any("AdmissionError" in str(e) for e in events(directory))
    assert not any(e["kind"] == "tool_retry" for e in events(directory))


@pytest.mark.parametrize("failures,expected", [(1, "completed"), (2, "failed")])
def test_only_transient_tool_errors_retry(tmp_path, failures, expected):
    calls = []

    def tool(task, **kwargs):
        calls.append(task)
        if len(calls) <= failures:
            raise TimeoutError("模拟取数超时")
        return query_agent(task, **kwargs)

    state, _ = run(tmp_path, graph_options={"query_fn": tool})
    assert state["status"] == expected
    assert len(calls) == 2


@pytest.mark.parametrize("bad_count,expected", [(1, "completed"), (2, "failed")])
def test_stale_result_reinvokes_capability_bounded(tmp_path, bad_count, expected):
    calls = []

    def tool(task, **kwargs):
        calls.append(task)
        result = query_agent(task, **kwargs)
        if len(calls) <= bad_count:
            result["task_revision"] -= 1
        return result

    state, directory = run(tmp_path, graph_options={"query_fn": tool})
    assert state["status"] == expected
    assert state["capability_retry_count"] == 1
    assert node_names(directory).count("run_query") == 2


@pytest.mark.parametrize("stage", ["understand_request", "compose_reply", "validate_reply"])
def test_model_failure_does_not_deliver_unchecked_draft(tmp_path, stage):
    state, directory = run(tmp_path, ScriptedModel(failure_stage=stage))
    assert state["status"] == "failed"
    assert "本次未完成" in state["answer"]
    assert any(e["kind"] == "node_error" for e in events(directory))


def test_trace_tree_checkpoint_and_html_escaping(tmp_path):
    _, directory = run(tmp_path)
    log = events(directory)
    starts = {e["span_id"] for e in log if e["kind"] == "span_start"}
    assert all(e["parent_span_id"] in starts for e in log if e.get("parent_span_id"))
    assert len([e for e in log if e["kind"] == "span_end"]) == len(starts)
    history = json.loads((directory / "checkpoints.json").read_text())
    assert len(history) >= 5
    assert history[0]["state"]["status"] == "completed"
    trace = Trace(directory, "case", secrets=("some-private-value",))
    trace.event(
        "test",
        "escaping",
        text="<script>alert(1)</script> some-private-value",
        api_key="another-private-value",
    )
    trace.render()
    raw = (directory / "trace.jsonl").read_text()
    page = (directory / "trace.html").read_text()
    assert "some-private-value" not in raw and "another-private-value" not in raw
    # 新报告把数据安全嵌入 application/json，再用转义后的 DOM 展示正文。
    assert "<script>alert" not in page and "\\u003cscript\\u003e" in page


def test_same_thread_overwrite_and_invalid_resume_blocked(tmp_path):
    run(tmp_path)
    with pytest.raises(ValueError, match="已存在"):
        run(tmp_path)
    with pytest.raises(ValueError, match="没有等待"):
        execute(
            output_dir=tmp_path,
            thread_id="case",
            answer="继续",
            model_factory=lambda *a, **k: ScriptedModel(),
        )
    with pytest.raises(ValueError, match="thread_id"):
        run(tmp_path, thread_id="../escape")


def test_thread_lock_blocks_concurrent_writer(tmp_path):
    with locked(tmp_path), pytest.raises(RuntimeError, match="另一个进程"), locked(tmp_path):
        pass


def test_model_budget_survives_reopening_trace(tmp_path):
    trace = Trace(tmp_path, "budget")
    trace.event("model_request", "prior")
    # 绕过客户端初始化，不读取本机密钥，也不允许发出网络请求。
    model = object.__new__(KimiModel)
    model.trace = Trace(tmp_path, "budget")
    model.max_calls = 1
    with pytest.raises(ModelFailure, match="上限"):
        model.complete("test", "test", {}, Proposal)


def test_analysis_queries_previous_range_through_same_admission():
    task = {
        "business": "准时保",
        "metric": "premium",
        "intent": "analysis",
        "start_date": "2026-01-01",
        "end_date": "2026-01-07",
        "reference_date": "2026-09-01",
        "revision": 1,
    }
    with pytest.raises(ValueError, match="2026"):
        analysis_agent(task)
