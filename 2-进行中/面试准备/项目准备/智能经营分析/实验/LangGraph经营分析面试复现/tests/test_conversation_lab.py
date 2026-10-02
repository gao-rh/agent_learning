"""验证多轮恢复、角色隔离与合计预算；替身结果不代表模型能力。"""

import json
import socket
from copy import deepcopy
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from business_analysis_repro.case_viewer.repository import Repository, public_case
from business_analysis_repro.clarification_lab import query_smoke
from business_analysis_repro.clarification_lab.contract import LabResolution
from business_analysis_repro.clarification_lab.knowledge import FIXTURES
from business_analysis_repro.complex_lab import runtime as complex_runtime
from business_analysis_repro.complex_lab.knowledge import ComplexKnowledge
from business_analysis_repro.conversation_lab import runtime
from business_analysis_repro.conversation_lab.budget import BudgetExceeded, BudgetTrace

USAGE = {"input_tokens": 100, "output_tokens": 10, "total_tokens": 110}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("离线检查禁止联网")
    monkeypatch.setattr(socket.socket, "connect", deny)
    for module in (runtime, query_smoke, complex_runtime):
        monkeypatch.setattr(module, "configuration", lambda: {"model": "fake"})


def user_model(decisions, captured):
    iterator = iter(decisions)

    class User:
        model_name = "fake"

        def __init__(self, trace, **kwargs):
            self.trace = trace

        def complete(self, stage, instruction, payload, schema):
            captured.append(deepcopy(payload))
            self.trace.event("model_request", stage, model="fake", messages=[{"role": "human", "content": json.dumps(payload, ensure_ascii=False)}])
            decision = schema.model_validate(next(iterator))
            self.trace.event("model_response", stage, usage=USAGE, content=decision.model_dump_json())
            return decision

    return User


def query_model():
    # 标准答案只供这个离线助手替身，绝不进入用户模型输入。
    rows = json.loads((FIXTURES / "simple_query_rubrics.private.json").read_text())["cases"]["Q09"]["turns"]
    inputs = []

    class Assistant:
        def __init__(self, trace, **kwargs):
            self.trace = trace

        def resolve(self, payload, **kwargs):
            inputs.append(payload)
            row = deepcopy(rows[len(inputs) - 1])
            for task in row["expected_tasks"]:
                p = task["period"]
                task["period"] = {"mode": "range", "start_date": p["start"], "end_date": p["end"]}
            proposal = LabResolution(outcome=row["expected_outcome"], requests=row["expected_tasks"],
                                     question="请补充需要查哪一个月。" if len(inputs) == 1 else "")
            self.trace.event("model_request", "scripted", model="fake", messages=[])
            self.trace.event("model_response", "scripted", usage=USAGE)
            with self.trace.span("tool", "finish_resolution", proposal.model_dump()):
                pass
            return proposal

    return Assistant, inputs


def test_ai_reply_continues_after_failed_review_and_reuses_checkpoint(tmp_path):
    root = tmp_path / "batch"
    runtime.prepare(root, "query", ["Q09"])
    assistant, inputs = query_model()
    captured = []
    actual_reply = "我需要2026年7月；双指标、安徽和专送范围都保留。"
    user = user_model([{"action": "reply", "message": actual_reply, "agenda_cursor": 0},
                       {"action": "finish", "message": "可以了。", "agenda_cursor": 0, "stop_reason": "收到两项模拟查询结果"}], captured)
    runtime.step(root, "Q09", assistant, user)
    first = runtime.read(root / "Q09-turn-1.json")
    first["review"]["grade"] = "failed"
    runtime.write(root / "Q09-turn-1.json", first)
    final = runtime.run(root, "Q09", assistant, user)
    second = runtime.read(root / "Q09-turn-2.json")
    assert second["question"] == actual_reply and second["thread_id"] == first["thread_id"]
    assert len(second["queries"]) == 2
    assert inputs[-1]["messages"][-1]["content"] == actual_reply
    assert captured[0]["dialogue"][-1]["content"] == first["answer"]
    assert not any(k in json.dumps(captured) for k in ("expected_tasks", "must_ask", "review", "goldens", "normalized_tasks"))
    assert final["usage"]["calls"] == 4
    assert final["assistant_usage"]["calls"] == final["simulated_user_usage"]["calls"] == 2
    assert final["grade"] == "pending_record_review"
    assert runtime.step(root, "Q09", assistant, user)["finished"] and len(captured) == 2
    data = public_case(Repository(tmp_path).case("batch", "Q09"))
    assert data["turns"][1]["input_origin"] == "simulated_user"
    assert data["turns"][1]["expected"] == {} and data["simulation"]["finished"]
    assert data['usage']['calls']==4 and data['assistant_usage']['calls']==2 and data['simulation']['user_usage']['calls']==2
    assert not any(f["type"] == "decision" for t in data["turns"] for f in t["findings"])


def test_complex_gap_can_be_confirmed_without_complete_gap_fields(tmp_path):
    root = tmp_path / "batch"
    runtime.prepare(root, "complex", ["C01"])
    gold = complex_runtime.read(complex_runtime.FIXTURES / "goldens.private.json")["C01"]
    plans = deepcopy(gold)
    needed = {r['metric_id'] for plan in gold for r in plan['requirements'] if r.get('metric_id')}
    for plan in plans:
        plan['knowledge_refs'] = [ref for ref in plan['knowledge_refs'] if ref in {'SYN-' + mid for mid in needed}]
        for r in plan["requirements"]:
            if r["status"] == "gap":
                r.update(metric_id=None, views=[])
    knowledge = ComplexKnowledge()
    turns = iter(plans)
    captured_assistant = []

    class Client:
        def __init__(self):
            self.calls = 0

        @property
        def bound(self):
            return self

        def bind_tools(self, *args, **kwargs):
            return self

        def invoke(self, messages):
            self.calls += 1
            captured_assistant.append(messages[-1].content)
            calls = ([{"id": "d" + str(i), "name": "get_metric_definition", "args": {"metric_id": mid}}
                      for i, mid in enumerate(knowledge.metrics) if mid in needed] if self.calls == 1 and len(messages) == 2 else
                     [{"id": "finish", "name": "finish_plan", "args": next(turns)}])
            return AIMessage(content="", tool_calls=calls, usage_metadata=USAGE)

    assistant = lambda trace, max_calls: SimpleNamespace(model_name="fake", client=Client())
    user_inputs = []
    reply = "接受餐饮准时宝合计替代；商家付费和平台付费保留为缺口。先确认可做部分，不发布Wiki。"
    user = user_model([{"action": "reply", "message": reply, "agenda_cursor": 0},
                       {"action": "finish", "message": "这样可以。", "agenda_cursor": 0, "stop_reason": "已确认部分计划与具体缺口"}], user_inputs)
    final = runtime.run(root, "C01", assistant, user)
    assert final["cases"]["C01"]["turns"] == 2
    second = runtime.read(root / "C01/turn-2.json")
    assert second["question"] == reply and second["validation"]["accepted"]
    assert second["resolver_result"]["outcome"] == "partial"
    assert "不执行SQL" in second["answer"] and "Wiki发布" in second["answer"]
    assert "做不了/缺口" in user_inputs[0]["dialogue"][-1]["content"]
    assert "previous_plan" in str(captured_assistant)
    data = public_case(Repository(tmp_path).case("batch", "C01"))
    assert data["status"] == "pending" and data["turns"][1]["expected"] == {}
    assert final["grade"] != "passed"


def test_knowledge_multi_turn_displays_actual_filter_choice(tmp_path):
    root = tmp_path / "batch"
    runtime.prepare(root, "knowledge", ["alias_unknown"])
    captured = []
    proposals = iter([LabResolution(outcome="clarify", question="下沉具体指哪个筛选范围？"),
                      LabResolution(outcome="ready", requests=[{"metric_id": "lab_fx_gross_premium", "period": {"mode": "range", "start_date": "2026-07-01", "end_date": "2026-07-31"}, "filters": {"city_operation": ["agency"]}}])])

    class Assistant:
        model_name = "fake"

        def __init__(self, trace, **kwargs):
            self.trace = trace

        def resolve(self, payload, **kwargs):
            captured.append(payload)
            return next(proposals)

    user_inputs = []
    user = user_model([{"action": "reply", "message": "本次指代理范围，仍整体汇总。", "agenda_cursor": 0},
                       {"action": "finish", "message": "已确认。", "agenda_cursor": 0, "stop_reason": "确认语义任务"}], user_inputs)
    final = runtime.run(root, "alias_unknown", Assistant, user)
    assert final["cases"]["alias_unknown"]["turns"] == 2
    assert captured[-1]["messages"][-1]["content"] == "本次指代理范围，仍整体汇总。"
    assert "城市经营类型=代理" in user_inputs[-1]["dialogue"][-1]["content"]


def test_shared_budget_counts_user_retries_before_next_request(tmp_path):
    runtime.prepare(tmp_path / "batch", "complex", ["C01"], max_requests=2)
    root = tmp_path / "batch"
    a = BudgetTrace(root / "C01", "assistant", root, 8)
    u = BudgetTrace(root / "simulated-users/C01/after-1", "user", root, 2)
    a.event("model_request", "assistant", messages=[])
    u.event("model_request", "simulate_user", messages=[])
    with pytest.raises(BudgetExceeded, match="合计"):
        u.event("model_request", "retry", messages=[])
    assert len([e for e in u.read() if e["kind"] == "model_request"]) == 1


def test_interrupted_user_call_is_not_automatically_recharged(tmp_path):
    root = tmp_path / "batch"
    runtime.prepare(root, "query", ["Q09"])
    assistant, _ = query_model()
    runtime.step(root, "Q09", assistant)
    path = root / "simulated-users/Q09/session.json"
    session = runtime.read(path)
    session["stage"] = "simulating_user"
    runtime.write(path, session)
    user = user_model([], [])
    stopped = runtime.step(root, "Q09", assistant, user)
    assert stopped["finished"] and "不自动重复付费" in stopped["stop_reason"]


def test_source_drift_is_checked_before_any_actor_call(tmp_path, monkeypatch):
    root = tmp_path / "batch"
    runtime.prepare(root, "query", ["Q09"])
    monkeypatch.setattr(query_smoke, "frozen_manifest", dict)
    with pytest.raises(ValueError, match="被测源码"):
        runtime.step(root, "Q09", user_factory=user_model([], []))
    assert not list(root.glob("simulated-users/*/after-*/trace.jsonl"))
