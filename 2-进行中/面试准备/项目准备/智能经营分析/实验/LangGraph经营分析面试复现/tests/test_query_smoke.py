"""实验连接机制的离线检查；脚本模型只能证明持久化/查询/预算，不能证明模型能力。"""

import json
import socket
from copy import deepcopy
from pathlib import Path

import pytest

from business_analysis_repro.clarification_lab import query_smoke
from business_analysis_repro.clarification_lab.contract import LabResolution
from business_analysis_repro.clarification_lab.knowledge import FIXTURES, LabKnowledge
from business_analysis_repro.clarification_lab.query_runtime import BudgetExceeded, LimitedTrace


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("离线测试禁止联网")
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(query_smoke, "configuration", lambda: {"model": "offline"})


def scripted(case_id, modify=None):
    expected = json.loads((FIXTURES / "simple_query_rubrics.private.json").read_text())["cases"][case_id]["turns"]
    replies = []
    for row in expected:
        requests = deepcopy(row["expected_tasks"])
        for request in requests:
            period = request["period"]
            request["period"] = {"mode": "range", "start_date": period["start"], "end_date": period["end"]}
        replies.append({"outcome": row["expected_outcome"], "requests": requests,
                        "question": "请确认：" + "、".join(row["must_ask"]) if row["must_ask"] else ""})
    if modify:
        modify(replies)
    inputs = []

    class Model:
        def __init__(self, trace, **kwargs):
            self.trace = trace

        def resolve(self, payload, **kwargs):
            inputs.append(deepcopy(payload))
            self.trace.event("model_request", "scripted", model="offline", messages=[])
            proposal = LabResolution.model_validate(replies.pop(0))
            self.trace.event("model_response", "scripted", usage={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15})
            with self.trace.span("tool", "finish_resolution", proposal.model_dump()):
                pass
            return proposal

    return Model, inputs


def test_clarification_resumes_same_checkpoint_and_runs_real_local_sql(tmp_path):
    root = tmp_path / "batch"
    query_smoke.prepare(root)
    factory, inputs = scripted("Q09")
    first = query_smoke.step(root, "Q09", model_factory=factory)
    assert first["status"] == "waiting_user" and not first["queries"]
    with pytest.raises(ValueError, match="审阅"):
        query_smoke.step(root, "Q09", model_factory=factory)
    second = query_smoke.step(root, "Q09", question_reviewed=True, model_factory=factory)
    assert second["review"]["grade"] == "task_matched"
    assert first["thread_id"] == second["thread_id"]
    assert len(inputs[-1]["messages"]) == 3
    assert "安徽" in inputs[-1]["messages"][0]["content"]
    assert inputs[-1]["messages"][-1]["content"] == "2026年7月。"
    gross, net = second["queries"]
    assert gross["rows"][0]["value"] > net["rows"][0]["value"]
    assert len(gross["rows"]) == 2


def test_completed_queries_feed_actual_saved_tasks_into_next_turn(tmp_path):
    root = tmp_path / "batch"
    query_smoke.prepare(root)
    factory, inputs = scripted("Q11")
    records = [query_smoke.step(root, "Q11", model_factory=factory) for _ in range(4)]
    assert all(r["review"]["grade"] == "task_matched" for r in records)
    assert len({r["conversation_id"] for r in records}) == 1
    assert len({r["thread_id"] for r in records}) == 4
    first_state = json.loads(Path(records[0]["state_file"]).read_text())
    assert inputs[1]["conversation_memory"]["business_anchor"]["task"] == first_state["task"]
    assert len(inputs[3]["conversation_context"]) == 3
    assert "merchant_age" in inputs[3]["conversation_memory"]["business_anchor"]["task"]["jobs"][0]["task"]["filters"]
    assert "merchant_age" not in records[3]["review"]["actual_tasks"][0]["filters"]
    assert len(records[0]["queries"][0]["rows"]) == 2
    assert records[1]["queries"][0]["rows"] == [{"merchant_age": "new", "value": 60}]
    assert records[1]["queries"][1]["rows"] == [{"merchant_age": "new", "value": 30}]
    assert len(records[3]["queries"][0]["rows"]) == 2


def test_semantically_wrong_but_valid_result_stops_followups(tmp_path):
    root = tmp_path / "batch"
    query_smoke.prepare(root)
    factory, _ = scripted("Q11", lambda rows: rows[0]["requests"][0].update(filters={}))
    record = query_smoke.step(root, "Q11", model_factory=factory)
    assert record["status"] == "completed"
    assert record["review"]["grade"] == "failed"
    assert record["review"]["mismatches"][0]["field"] == "filters"
    with pytest.raises(ValueError, match="上轮失败"):
        query_smoke.step(root, "Q11", model_factory=factory)


def test_request_budget_counts_before_api_call(tmp_path):
    for i in range(5):
        trace = LimitedTrace(tmp_path / "conversations" / "cid" / "tasks" / str(i), str(i), tmp_path)
        for _ in range(6):
            trace.event("model_request", "scripted", messages=[])
        with pytest.raises(BudgetExceeded):
            trace.event("model_request", "scripted", messages=[])
    other = LimitedTrace(tmp_path / "conversations" / "cid" / "tasks" / "extra", "extra", tmp_path)
    with pytest.raises(BudgetExceeded):
        other.event("model_request", "scripted", messages=[])
    assert not other.read()


def test_received_metric_source_is_a_valid_reference_but_unread_source_is_not():
    knowledge = LabKnowledge()
    assert "SYN-lab_active_merchants" not in knowledge.received_knowledge_ids()
    knowledge.tools()["get_metric_definition"](metric_id="lab_active_merchants")
    assert "SYN-lab_active_merchants" in knowledge.received_knowledge_ids()
    assert "SYN-lab_active_fx_open" not in knowledge.received_knowledge_ids()


def test_failed_resume_does_not_grade_previous_checkpoint_as_current_output(tmp_path):
    root = tmp_path / "batch"
    query_smoke.prepare(root)
    factory, _ = scripted("Q09")
    first = query_smoke.step(root, "Q09", model_factory=factory)
    assert first["status"] == "waiting_user"

    class FailsAfterSubmission(factory):
        def resolve(self, payload, **kwargs):
            super().resolve(payload, **kwargs)
            raise BudgetExceeded("simulate retrieval limit after model submission")

    second = query_smoke.step(root, "Q09", question_reviewed=True, model_factory=FailsAfterSubmission)
    assert second["review"]["grade"] == "failed"
    assert second["review"]["actual_outcome"] is None
    assert second["review"]["model_final_outcome"] == "ready"
    assert second["review"]["mismatches"] == []
    assert second["review"]["task_match"] is None


@pytest.mark.parametrize("case_id", [f"Q{i:02}" for i in range(1, 13)])
def test_full_suite_can_execute_declared_tasks_without_network(tmp_path, case_id):
    root = tmp_path / "full"
    query_smoke.prepare(root, max_requests=160, max_turn_requests=12, all_cases=True)
    factory, _ = scripted(case_id)
    cases = json.loads((FIXTURES / "simple_query_cases.json").read_text())["cases"]
    case = next(c for c in cases if c["id"] == case_id)
    for turn in case["turns"]:
        row = query_smoke.step(root, case_id, model_factory=factory,
                               question_reviewed=turn["advance_when"] == "after_clarification_question")
        assert row["review"]["grade"] in {"task_matched", "needs_question_review"}
        if row["status"] == "completed":
            assert row["queries"] and all(q["rows"] for q in row["queries"])


def test_query_ratio_uses_correct_numerator_denominator_and_deduplicates(tmp_path):
    import sqlite3

    from business_analysis_repro.clarification_lab.query_runtime import query_local, seed_database
    from business_analysis_repro.playground.trace import Trace
    dbfile = tmp_path / "facts.sqlite"
    seed_database(dbfile)
    # 人工算得出的固定对照；不从 SQL 表达式反向生成期望值。
    with sqlite3.connect(dbfile) as db:
        db.execute("DELETE FROM orders")
        for status, eligible, fx, cancel, count in [
            ("non_cancelled", 1, 1, 0, 10), ("non_cancelled", 1, 0, 1, 90),
            ("cancelled", 0, 0, 0, 100), ("cancelled", 1, 1, 0, 20),
        ]:
            db.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?)",
                ("2026-07-15", "anhui", "old", "ka", "food", status, eligible, fx, cancel, count))
        db.execute("DELETE FROM join_events")
        for mid in ["a", "a", "b"]:
            db.execute("INSERT INTO join_events VALUES (?,?,?,?,?)",
                       (mid, "2026-07-15", "fx", "wallet", "app"))
    trace = Trace(tmp_path / "trace", "test")
    task = {"intent": "query", "period": {"start": "2026-07-01", "end": "2026-07-31"},
            "group_by": [], "filters": {}, "required_predicates": []}
    for mid, expected in [("lab_fx_order_rate", 10), ("lab_fx_eligible_rate", 25),
                          ("lab_cancel_order_rate", 90/220*100),
                          ("lab_takeaway_orders", 220), ("lab_join_funnel", 2)]:
        result = query_local(dbfile, {**task, "metric_id": mid}, trace)
        assert result["rows"][0]["value"] == pytest.approx(expected)


def test_absolute_query_cannot_pass_evaluation_using_relative_parameters(tmp_path):
    root = tmp_path / "date"
    query_smoke.prepare(root)
    def relative_same_month(rows):
        for request in rows[0]["requests"]:
            request["period"] = {"mode": "calendar", "unit": "month", "offset": -2}
    factory, _ = scripted("Q11", relative_same_month)
    row = query_smoke.step(root, "Q11", model_factory=factory)
    assert row["status"] == "completed"  # 日期可算对，但没有遵守用户指定的表达约束。
    assert row["review"]["grade"] == "failed"
    assert all(m["field"] == "time_expression" for m in row["review"]["mismatches"])
