"""复杂提交接口的离线机制回归；脚本响应不计作模型能力成绩。"""

from copy import deepcopy
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from business_analysis_repro.complex_lab import runtime
from business_analysis_repro.complex_lab.contract import Plan, normalize_plan, reply_text, validate
from business_analysis_repro.complex_lab.knowledge import ComplexKnowledge


@pytest.fixture
def plan():
    return Plan.model_validate(
        {
            "outcome": "clarify",
            "revision": 1,
            "goal": "保费报告写入Wiki，先确认缺口处理",
            "requirements": [
                {
                    "id": "R1",
                    "label": "放心吃实收保费",
                    "metric_id": "cx_fx_premium",
                    "status": "active",
                }
            ],
            "tasks": [
                {
                    "id": "T1",
                    "requirement_ids": ["R1"],
                    "metric_id": "cx_fx_premium",
                    "period": {"start": "2026-08-01", "end": "2026-08-31"},
                    "views": [{"kind": "month"}],
                }
            ],
            "questions": [{"id": "Q1", "owner": "user", "text": "是否接受合计替代？"}],
            "delivery": [{"type": "report"}, {"type": "wiki"}],
        }
    )


@pytest.fixture
def knowledge():
    k = ComplexKnowledge()
    k.tools()["get_metric_definition"](metric_id="cx_fx_premium")
    return k


def test_questions_are_the_display_and_validation_source(plan, knowledge):
    plan.tasks[0].definition_version = "v1"
    plan.question = "另一个旧问句"
    normalized, audit = normalize_plan(plan, knowledge)
    assert normalized.question == "是否接受合计替代？"
    assert validate(normalized, knowledge, 1)["accepted"]
    assert audit["reply"]["before"] == "另一个旧问句"
    assert plan.question == "另一个旧问句"  # 保留原提交。


def test_questions_are_deduplicated_and_internal_owners_are_not_asked(plan):
    question_type = type(plan.questions[0])
    plan.questions += [
        question_type(id="Q2", text=" 是否接受合计替代？ ", owner="user"),
        question_type(id="Q3", text="何时补齐资产？", owner="knowledge_owner"),
        question_type(id="Q4", text="是否支持发布？", owner="system_capability"),
        question_type(id="Q5", text="统计到哪天？", owner="user"),
    ]
    assert reply_text(plan) == "是否接受合计替代？\n\n统计到哪天？"


def test_legacy_explanation_remains_supported(plan, knowledge):
    plan.questions = []
    plan.question = "资产缺失，暂时无法执行。"
    plan.outcome = "blocked"
    normalized, _ = normalize_plan(plan, knowledge)
    assert normalized.question == plan.question
    assert validate(normalized, knowledge, 1)["accepted"]


def test_internal_question_cannot_substitute_for_user_reply(plan, knowledge):
    plan.questions[0].owner = "knowledge_owner"
    normalized, _ = normalize_plan(plan, knowledge)
    assert normalized.question == ""
    assert "没有给出待确认/阻断说明" in validate(normalized, knowledge, 1)["errors"]


def test_unique_observed_version_binds_both_periods_without_business_edits(plan, knowledge):
    plan.tasks[0].comparison_period = plan.tasks[0].period.model_copy(
        update={"start": "2026-07-01", "end": "2026-07-31"}
    )
    plan.tasks[0].comparison_mode = "same_definition"
    original = plan.model_dump()
    normalized, audit = normalize_plan(plan, knowledge)
    assert normalized.tasks[0].definition_version == normalized.tasks[0].baseline_version == "v1"
    assert {b["field"] for b in audit["version_bindings"]} == {
        "definition_version",
        "baseline_version",
    }
    assert plan.model_dump() == original
    for field in ("requirements", "delivery", "questions"):
        assert normalized.model_dump()[field] == original[field]
    task = normalized.tasks[0].model_dump()
    task.update(definition_version="", baseline_version="")
    assert task == original["tasks"][0]
    assert validate(normalized, knowledge, 1)["accepted"]


def test_catalog_or_search_hit_alone_cannot_bind_version(plan):
    k = ComplexKnowledge()
    k.tools()["search_metrics"](query="放心吃")
    normalized, audit = normalize_plan(plan, k)
    assert not normalized.tasks[0].definition_version
    assert "version_bindings" not in audit
    assert any("没有实际读取" in e for e in validate(normalized, k, 1)["errors"])


def test_multiple_versions_are_not_automatically_selected(plan):
    k = ComplexKnowledge()
    k.tools()["get_metric_definition"](metric_id="cx_cancel_rate")
    plan.tasks[0].metric_id = plan.requirements[0].metric_id = "cx_cancel_rate"
    normalized, audit = normalize_plan(plan, k)
    assert not normalized.tasks[0].definition_version  # 即使8月只有v2生效，也不猜比较策略。
    assert "version_bindings" not in audit
    assert any(
        "definition_version" in e and "v1,v2" in e for e in validate(normalized, k, 1)["errors"]
    )


@pytest.mark.parametrize(
    "start,end",
    [
        ("2020-12-01", "2020-12-31"),
        ("2026-08-31", "2026-08-01"),
        ("not-a-date", "2026-08-31"),
        ("2026-09-01", "2026-09-30"),
    ],
)
def test_version_is_not_bound_outside_observed_coverage(plan, knowledge, start, end):
    plan.tasks[0].period.start, plan.tasks[0].period.end = start, end
    normalized, audit = normalize_plan(plan, knowledge)
    assert not normalized.tasks[0].definition_version
    assert "version_bindings" not in audit


def test_conflicting_observations_or_explicit_version_are_not_overwritten(plan, knowledge):
    changed = deepcopy(knowledge.observations[0])
    changed["result"]["versions"]["v1"]["rule"] = "另一份冲突定义"
    knowledge.observations.append(changed)
    normalized, audit = normalize_plan(plan, knowledge)
    assert not normalized.tasks[0].definition_version
    assert "version_bindings" not in audit
    plan.tasks[0].definition_version = "bad-version"
    normalized, _ = normalize_plan(plan, knowledge)
    assert normalized.tasks[0].definition_version == "bad-version"
    assert not validate(normalized, knowledge, 1)["accepted"]


def test_wiki_requires_content_but_does_not_force_every_delivery_to_be_report(plan, knowledge):
    plan.delivery = [d for d in plan.delivery if d.type == "wiki"]
    normalized, _ = normalize_plan(plan, knowledge)
    errors = validate(normalized, knowledge, 1)["errors"]
    assert len(errors) == 1 and "delivery仅列wiki" in errors[0]
    assert [d.type for d in normalized.delivery] == ["wiki"]  # 不替模型补交付目标。
    normalized.delivery.append(type(normalized.delivery[0])(type="table"))
    assert validate(normalized, knowledge, 1)["accepted"]


def scripted_run(tmp_path, monkeypatch, responses, limit):
    monkeypatch.setattr(runtime, "configuration", lambda: {"model": "offline-script"})
    directory = tmp_path / "batch"
    runtime.prepare(directory, selected_cases=["C01"])
    batch = runtime.read(directory / "batch.json")
    batch["limits"]["requests_per_turn"] = limit
    runtime.write(directory / "batch.json", batch)
    captured = []

    class Client:
        @property
        def bound(self):
            return self

        def bind_tools(self, schemas, **kwargs):
            assert {t["function"]["name"] for t in schemas} == {
                "search_metrics",
                "get_metric_definition",
                "search_dimensions",
                "search_dimension_values",
                "search_business_knowledge",
                "finish_plan",
            }
            return self

        def invoke(self, messages):
            captured.append([m.model_dump() for m in messages])
            return responses[len(captured) - 1]

    def factory(trace, max_calls):
        assert max_calls == limit
        return SimpleNamespace(model_name="offline-script", client=Client())

    runtime.run_turn(directory, "C01", model_factory=factory)
    return runtime.read(directory / "C01" / "turn-1.json"), captured


def tool_response(name, args, call_id):
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": call_id}],
        usage_metadata={"input_tokens": 100, "output_tokens": 5, "total_tokens": 105},
    )


def test_public_errors_return_to_model_and_corrected_submission_preserves_original(
    tmp_path, monkeypatch, plan
):
    bad = plan.model_dump()
    bad["delivery"] = [d for d in bad["delivery"] if d["type"] == "wiki"]
    corrected = deepcopy(bad)
    corrected["delivery"].append({"type": "report", "status": "planned"})
    record, captured = scripted_run(
        tmp_path,
        monkeypatch,
        [
            tool_response("get_metric_definition", {"metric_id": "cx_fx_premium"}, "read"),
            tool_response("finish_plan", bad, "first"),
            tool_response("finish_plan", corrected, "repair"),
        ],
        limit=3,
    )
    feedback = next(m for m in captured[2] if m.get("tool_call_id") == "first")["content"]
    assert "delivery仅列wiki" in feedback and "retry_instruction" in feedback
    assert "plan_normalization" in feedback
    assert record["validation"]["accepted"] and record["status"] == "waiting_review"
    assert record["answer"] == "是否接受合计替代？"
    assert record["resolver_result"]["tasks"][0]["definition_version"] == "v1"
    assert record["model_submissions"][0]["arguments"] == bad
    assert record["model_submissions"][1]["arguments"] == corrected
    assert record["model_submissions"][0]["program_normalization"]["plan"]["version_bindings"]
    assert "goldens" not in str(captured) and "final_metrics" not in str(captured)


def test_failed_submissions_stop_at_existing_budget_and_never_become_ready(
    tmp_path, monkeypatch, plan
):
    bad = plan.model_dump()
    bad["tasks"][0]["definition_version"] = "wrong"
    record, captured = scripted_run(
        tmp_path,
        monkeypatch,
        [
            tool_response("get_metric_definition", {"metric_id": "cx_fx_premium"}, "read"),
            tool_response("finish_plan", bad, "first"),
            tool_response("finish_plan", bad, "again"),
        ],
        limit=3,
    )
    assert len(captured) == 3 and len(record["model_submissions"]) == 2
    assert record["status"] == "execution_error" and not record["validation"]["accepted"]
    assert "达到上限" in record["error"]["message"]
    assert record["resolver_result"]["tasks"][0]["definition_version"] == "wrong"
    assert not record["validation"]["execution_enabled"]


def test_missing_predicate_feedback_names_task_metric_and_exact_required_rule(plan, knowledge):
    task = plan.tasks[0]
    task.metric_id = plan.requirements[0].metric_id = "cx_active_fx"
    knowledge.tools()["get_metric_definition"](metric_id=task.metric_id)
    original = plan.model_dump()
    result = validate(plan, knowledge, 1)
    feedback = "\n".join(result["errors"])
    assert "T1：指标必选规则未保留" in feedback
    assert "metric_id=cx_active_fx" in feedback
    assert "fx_open" in feedback and "valid" in feedback
    assert "predicates缺少=" in feedback
    assert plan.model_dump() == original  # 只报告缺项，不偷偷补业务条件。
