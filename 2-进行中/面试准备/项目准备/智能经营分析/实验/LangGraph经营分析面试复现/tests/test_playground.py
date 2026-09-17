"""试玩的业务边界与恢复验收；所有模型使用测试替身，不请求外部服务。"""

import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from business_analysis_repro.main_agent.state import Reply, Verdict
from business_analysis_repro.main_agent.trace import Trace
from business_analysis_repro.playground.agent import PlaygroundModel, Resolution, execute
from business_analysis_repro.playground.catalog import (
    DIMENSIONS,
    METRICS,
    ClarificationNeeded,
    search_dimension_values,
    search_dimensions,
    search_metrics,
    validate_task,
)
from business_analysis_repro.playground.data import analysis_agent, query_agent
from business_analysis_repro.playground.server import ChatStore


def task(mid="demo_metric_fx_order_rate", **updates):
    return {
        "intent": "query",
        "metric_id": mid,
        "metric": mid,
        "reference_date": "2026-09-01",
        "start_date": "2026-08-24",
        "end_date": "2026-08-30",
        "revision": 1,
        "filters": {},
        "group_by": [],
        **updates,
    }


@pytest.mark.parametrize("mid", METRICS)
def test_all_presets_and_group_reaggregation(mid):
    m = METRICS[mid]
    assert len(m["dimensions"]) == 3
    for d, values in m["dimensions"].items():
        assert set(values) <= {v["id"] for v in DIMENSIONS[d]["values"]}
    r = query_agent(task(mid, group_by=list(m["dimensions"])))
    p = m["preset"]
    assert r["numerator"] == p["current_numerator"]
    assert r["denominator"] == (p["current_denominator"] or 0)
    assert sum(g["numerator"] for g in r["groups"]) == r["numerator"]
    assert sum(g["denominator"] for g in r["groups"]) == r["denominator"]
    if m["aggregation"] == "ratio_of_sums":
        scale = 100 if m["unit"] == "%" else 1
        assert r["total"] == pytest.approx(
            p["current_numerator"] / p["current_denominator"] * scale
        )
    else:
        assert r["total"] == p["current_numerator"]
    assert r["query_execution"]["execution_status"] in {"sqlite_executed", "local_fixture_returned"}


def test_supported_value_filter_is_applied_and_unknown_is_not_ignored():
    base = task()
    new = query_agent({**base, "filters": {"merchant_age": ["new_merchant"]}})
    old = query_agent({**base, "filters": {"merchant_age": ["existing_merchant"]}})
    total = query_agent(base)
    assert new["numerator"] + old["numerator"] == total["numerator"]
    assert new["denominator"] + old["denominator"] == total["denominator"]
    with pytest.raises(ClarificationNeeded, match="不支持"):
        query_agent({**base, "group_by": ["source"]})
    with pytest.raises(ClarificationNeeded, match="只支持"):
        query_agent({**base, "filters": {"merchant_age": ["made-up"]}})


def test_same_global_dimension_does_not_imply_same_enum_support():
    with pytest.raises(ClarificationNeeded, match="只支持"):
        validate_task(task("demo_metric_cancel_order_rate", filters={"merchant_type": ["city"]}))
    assert validate_task(task(filters={"merchant_type": ["city"]}))
    found = search_dimension_values("demo_metric_cancel_order_rate", "城市商家", "merchant_type")
    assert found["candidates"][0]["supported"] is False


def test_search_preserves_ambiguous_metric_and_dimension_identity():
    assert search_metrics("准时宝保费")["exact_ambiguity"]
    names = {x["name"] for x in search_metrics("加入商户数")["candidates"] if x["score"] == 1}
    assert names == {"外卖险加入商户数", "放心吃餐饮加入商户数"}
    hit = search_dimension_values("demo_metric_fx_order_rate", "新商")["candidates"][0]
    assert hit["dimension_id"] == "merchant_age" and hit["id"] == "new_merchant"
    assert not search_dimensions("demo_metric_fx_order_rate", "获客来源")["candidates"][0][
        "supported"
    ]


def test_analysis_uses_prior_period_and_percentage_points():
    r = analysis_agent(
        task("demo_metric_cancel_order_rate", intent="analysis", group_by=["merchant_age"])
    )
    assert r["baseline"]["facts"]["期间"] == "2026-08-17 至 2026-08-23"
    assert r["facts"]["变动"] == "+1.25 个百分点"
    assert "新商前期" in r["facts"] and "新商变动" in r["facts"]
    assert "老商前期" in r["facts"] and "老商变动" in r["facts"]


def test_premium_and_average_premium_presets_use_same_atomic_total():
    for phase in ["baseline", "current"]:
        premium = METRICS["demo_metric_fx_premium"]["preset"][phase + "_numerator"]
        orders = METRICS["demo_metric_fx_net_orders"]["preset"][phase + "_numerator"]
        average = METRICS["demo_metric_fx_avg_premium"]["preset"]
        assert average[phase + "_numerator"] == premium
        assert average[phase + "_denominator"] == orders


class FakeModel:
    def __init__(self, resolutions):
        self.resolutions = list(resolutions)

    def resolve(self, payload):
        return Resolution.model_validate(self.resolutions.pop(0))

    def complete(self, stage, instruction, payload, schema):
        if stage == "compose_reply":
            return Reply(
                text="模拟数据。\n" + "\n".join(f"{k}：{v}" for k, v in payload["facts"].items()),
                evidence_ids=[payload["evidence_id"]],
            )
        return Verdict(passed=True, issues=[])


def ready(**updates):
    return {
        "outcome": "ready",
        "metric_id": "demo_metric_fx_order_rate",
        "period": {"mode": "calendar", "unit": "week", "offset": -1},
        **updates,
    }


def test_seven_node_execution_and_cross_process_style_resume(tmp_path):
    model = FakeModel([{"outcome": "clarify", "question": "查新商还是老商？"}])
    paused, folder = execute(tmp_path, "test", "查渗透率", model_factory=lambda *a, **k: model)
    assert paused["status"] == "waiting_user"
    model = FakeModel([ready(filters={"merchant_age": ["new_merchant"]})])
    done, _ = execute(tmp_path, "test", "新商", resume=True, model_factory=lambda *a, **k: model)
    assert done["status"] == "completed" and done["task_revision"] == 2
    assert done["task"]["filters"] == {"merchant_age": ["new_merchant"]}
    assert (folder / "trace.html").stat().st_size > 1000
    log = [json.loads(x) for x in (folder / "trace.jsonl").read_text().splitlines()]
    assert len({x["run_id"] for x in log}) == 2


def test_invalid_plan_enters_clarification_without_query(tmp_path):
    model = FakeModel([ready(group_by=["source"])])
    state, folder = execute(tmp_path, "invalid", "按来源看", model_factory=lambda *a, **k: model)
    assert state["status"] == "waiting_user"
    log = [json.loads(x) for x in (folder / "trace.jsonl").read_text().splitlines()]
    assert not any(e["kind"] == "span_start" and e["name"] == "run_query" for e in log)


def test_semantic_time_mismatch_is_stopped_before_query(tmp_path):
    class ReviewModel(FakeModel):
        def complete(self, stage, instruction, payload, schema):
            if stage == "validate_interpretation":
                assert payload["planned_periods"]["本期"]["start_date"] == "2026-08-19"
                assert payload["calendar_reference"]["上周"]["start_date"] == "2026-08-24"
                return Verdict(passed=False, issues=["上周应为8月24至30日，请确认自然周。"])
            return super().complete(stage, instruction, payload, schema)

    model = ReviewModel([ready(period={"mode": "rolling", "unit": "week", "offset": -1})])
    state, folder = execute(
        tmp_path, "wrong-date", "查上周渗透率", model_factory=lambda *a, **k: model
    )
    assert state["status"] == "waiting_user"
    events = [json.loads(l) for l in (folder / "trace.jsonl").read_text().splitlines()]
    assert not any(e["kind"] == "span_start" and e["name"] == "run_query" for e in events)


def test_conversation_new_turn_uses_context_and_distinct_task(tmp_path):
    calls = []

    def fake_execute(folder, tid, text, **kwargs):
        calls.append((tid, kwargs))
        return {"status": "completed", "answer": "模拟回答", "task": task()}, folder / tid

    store = ChatStore(tmp_path, executor=fake_execute)
    cid = "a" * 16
    store.send(cid, "看新商")
    store.send(cid, "那老商呢")
    assert calls[0][0] != calls[1][0]
    assert calls[1][1]["context"][0]["question"] == "看新商"
    assert len(store.get(cid)["messages"]) == 4
    assert store.get("b" * 16)["messages"] == []


def test_real_tool_protocol_keeps_tool_results_and_blocks_silent_drop(tmp_path):
    responses = [
        ("search_metrics", {"query": "放心吃餐饮订单渗透率"}),
        ("get_metric_definition", {"metric_id": "demo_metric_fx_order_rate"}),
        ("search_dimensions", {"metric_id": "demo_metric_fx_order_rate", "query": "获客来源"}),
        ("finish_resolution", ready()),
    ]
    calls = []

    class Client:
        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            calls.append(list(messages))
            name, args = responses.pop(0)
            return AIMessage(
                content="", tool_calls=[{"name": name, "args": args, "id": str(len(calls))}]
            )

    model = object.__new__(PlaygroundModel)
    model.client = SimpleNamespace(bound=Client())
    model.trace = Trace(tmp_path, "test")
    model.max_calls = 24
    model.model_name = "test-double"
    resolution = model.resolve({"messages": ["按来源看渗透率"]})
    assert resolution.outcome == "clarify"
    assert "不支持" in resolution.question
    assert any(m.type == "tool" for m in calls[-1])
