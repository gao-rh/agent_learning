"""不调用真实模型：验证知识隔离、真实resolve工具循环、语义边界和续轮输入。"""

import json
import socket
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessageChunk

from business_analysis_repro.clarification_lab.__main__ import check_pack, main, preview, review
from business_analysis_repro.clarification_lab.contract import validate_submission
from business_analysis_repro.clarification_lab.experiment import execute_turn, payload_for
from business_analysis_repro.clarification_lab.knowledge import LabKnowledge, get_case
from business_analysis_repro.playground import catalog
from business_analysis_repro.playground.parallel_model import ParallelModel, grounding_feedback
from business_analysis_repro.playground.parallel_state import MetricRequest
from business_analysis_repro.playground.trace import Trace


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("离线准备测试不得联网")
    monkeypatch.setattr(socket.socket, "connect", fail)
    monkeypatch.setattr(socket, "create_connection", fail)


def call(name, args, ident="c"):
    return {"name": name, "args": args, "id": ident}


def request(mid="lab_fx_gross_premium", **changes):
    return {"metric_id": mid, "intent": "query",
            "period": {"mode": "range", "start_date": "2026-07-01", "end_date": "2026-07-31"},
            **changes}


def model(tmp_path, responses, budget=8):
    class Client:
        def bind_tools(self, tools):
            self.tools = tools
            return self

        def stream(self, messages, **kwargs):
            seen.append(list(messages))
            if not responses:
                raise AssertionError("模型循环超过了替身脚本")
            response = responses.pop(0)
            yield response if isinstance(response, AIMessageChunk) else AIMessageChunk(
                content="", tool_calls=response, usage_metadata={
                    "input_tokens": 100, "output_tokens": 20, "total_tokens": 120})

    seen = []
    obj = object.__new__(ParallelModel)
    obj.trace = Trace(tmp_path, "offline-lab")
    obj.model_name, obj.max_calls = "offline-scripted-double", budget
    obj.client = SimpleNamespace(bound=Client())
    return obj, seen


def test_pack_and_control_pair():
    assert check_pack()["cases"] == 10
    assert payload_for(get_case("alias_unknown")) == payload_for(get_case("alias_defined"))
    before = json.dumps(catalog.KNOWLEDGE, sort_keys=True)
    a, b = LabKnowledge(), LabKnowledge("with_definition")
    assert not a.search_business_knowledge("下沉")["records"]
    assert b.search_business_knowledge("下沉")["records"][0]["id"] == "K-CITY-MAPPING"
    assert json.dumps(catalog.KNOWLEDGE, sort_keys=True) == before


def test_preview_excludes_answers_and_shows_only_actual_prefetched_knowledge():
    visible = preview(get_case("alias_unknown"))["sent_to_model_on_first_call"]
    assert "records" not in visible["payload"]
    assert "knowledge_profile" not in visible["payload"]
    assert "expected_tasks" not in json.dumps(visible)
    assert "这次按城市经营类型里的代理统计，月份和险种不变。" not in json.dumps(visible, ensure_ascii=False)
    defined = preview(get_case("alias_defined"))["sent_to_model_on_first_call"]
    assert visible["system"] == defined["system"]
    assert visible["payload"]["messages"] == defined["payload"]["messages"]
    assert visible["payload"]["conversation_context"] == defined["payload"]["conversation_context"]
    assert visible["payload"]["business_topic_hint"]["records"] == []
    assert defined["payload"]["business_topic_hint"]["records"][0]["id"] == "K-CITY-MAPPING"
    assert defined["payload"]["business_topic_hint"]["initiated_by"] == "program"


def test_prefetch_uses_latest_user_words_and_never_invents_a_missing_definition():
    messages = [{"role": "human", "content": "先看下沉"},
                {"role": "ai", "content": "按代理吗？"},
                {"role": "human", "content": "取消原范围，改成整体"}]
    knowledge = LabKnowledge("with_definition")
    context = knowledge.business_context(messages)
    assert context["query"] == messages[-1]["content"]
    assert "K-CITY-MAPPING" not in {r["id"] for r in context["records"]}
    observation = knowledge.observations[0]
    assert observation["arguments"]["query"] == messages[-1]["content"]
    assert observation["result"]["records"] == context["records"]
    assert LabKnowledge().business_context([{"role": "human", "content": "要下沉的"}])["records"] == []


def test_real_resolve_loop_stops_at_semantic_submission(tmp_path):
    obj, seen = model(tmp_path, [
        [call("get_metric_definition", {"metric_id": "lab_fx_gross_premium"})],
        [call("finish_resolution", {"outcome": "ready", "requests": [request()]})]])
    result = execute_turn(obj, get_case("explicit_month"))
    assert len(seen) == 2
    expected_input = preview(get_case("explicit_month"))["sent_to_model_on_first_call"]
    assert seen[0][0].content == expected_input["system"]
    assert json.loads(seen[0][1].content) == expected_input["payload"]
    assert result["validation"]["accepted"]
    assert result["validation"]["execution_enabled"] is False
    assert result["validation"]["normalized_tasks"][0]["metric_id"] == "lab_fx_gross_premium"
    assert result["resolver_result"]["requests"][0]["period"]["mode"] == "range"
    assert result["boundary_violations"] == []
    assert all(e["name"] not in {"query_agent", "analysis_agent", "compose_batch"}
               for e in obj.trace.read())


def test_business_only_entry_returns_missing_submission_to_model_without_filling_answer(tmp_path):
    obj, seen = model(tmp_path, [
        AIMessageChunk(content="请告诉我下沉是什么意思。", usage_metadata={
            "input_tokens": 100, "output_tokens": 20, "total_tokens": 120}),
        [call("finish_resolution", {"outcome": "clarify", "question": "下沉在本次任务指哪些城市或经营类型？"})],
    ])
    result = execute_turn(obj, get_case("alias_unknown"))
    assert len(seen) == 2
    assert "尚未完成" in seen[1][-1].content and "finish_resolution" in seen[1][-1].content
    assert result["resolver_result"]["outcome"] == "clarify"
    assert len(result["model_submissions"]) == 1
    assert any(e["kind"] == "model_response" and e.get("content") == "请告诉我下沉是什么意思。"
               for e in obj.trace.read())
    assert result["validation"]["normalized_tasks"] == []


def test_public_missing_date_is_returned_inside_loop_and_does_not_invent_period(tmp_path):
    obj, seen = model(tmp_path, [
        [call("get_metric_definition", {"metric_id":"lab_fx_gross_premium"})],
        [call("finish_resolution", {"outcome":"ready", "requests":[request(period=None)]})],
        [call("finish_resolution", {"outcome":"clarify", "question":"请补充查询日期。"})],
    ])
    result = execute_turn(obj, get_case("explicit_month"))
    feedback = seen[-1][-1].content
    assert "metric_id=lab_fx_gross_premium" in feedback and "period缺少当期" in feedback
    assert result["model_submissions"][0]["arguments"]["requests"][0]["period"] is None
    assert result["resolver_result"]["outcome"] == "clarify"
    assert len(result["model_submissions"]) == 2


def test_invalid_source_is_recorded_then_corrected_with_observed_id(tmp_path):
    obj, seen = model(tmp_path, [
        [call("get_metric_definition", {"metric_id": "lab_fx_gross_premium"})],
        [call("finish_resolution", {"outcome": "ready", "requests": [request()],
                                    "knowledge_refs": ["not-read-source"]})],
        [call("finish_resolution", {"outcome": "ready", "requests": [request()],
                                    "knowledge_refs": ["SYN-lab_fx_gross_premium"]})]])
    result = execute_turn(obj, get_case("explicit_month"))
    assert result["validation"]["accepted"]
    assert len(result["model_submissions"]) == 2
    assert result["model_submissions"][0]["arguments"]["knowledge_refs"] == ["not-read-source"]
    assert "未读取的来源" in seen[-1][-1].content
    finish = obj.client.bound.tools[-1]
    assert finish["function"]["parameters"]["properties"]["knowledge_refs"]["items"]["enum"] == ["K-PREMIUM", "SYN-lab_fx_gross_premium"]


def test_metric_source_fallback_preserves_raw_submission_and_records_conversion(tmp_path):
    refs = ["lab_fx_gross_premium", "SYN-lab_fx_gross_premium"]
    obj, _ = model(tmp_path, [
        [call("get_metric_definition", {"metric_id": "lab_fx_gross_premium"})],
        [call("finish_resolution", {"outcome": "ready", "requests": [request()],
                                    "knowledge_refs": refs})]])
    result = execute_turn(obj, get_case("explicit_month"))
    assert result["validation"]["accepted"]
    assert result["model_submissions"][0]["arguments"]["knowledge_refs"] == refs
    assert result["resolver_result"]["knowledge_refs"] == ["SYN-lab_fx_gross_premium"]
    finish = next(e for e in obj.trace.read()
                  if e["kind"] == "span_end" and e.get("name") == "finish_resolution")
    assert finish["output"]["result"]["source_reference_normalization"]["before"] == refs


def test_program_clarification_is_not_misreported_as_model_decision(tmp_path):
    obj, _ = model(tmp_path, [[
        call("get_metric_definition", {"metric_id": "lab_fx_gross_premium"}, "definition"),
        call("search_dimension_values", {"metric_id": "lab_fx_gross_premium",
            "query": "无人机配送", "dimension_id": "delivery"}, "enum")],
        [call("finish_resolution", {"outcome": "ready", "requests": [request()]})]])
    result = execute_turn(obj, get_case("unsupported_enum"))
    # 模型试图丢掉筛选直接执行，原v5代码拦截后改为澄清；必须保留这次模型错误。
    assert result["model_submissions"][0]["arguments"]["outcome"] == "ready"
    assert result["resolver_result"]["outcome"] == "clarify"
    assert not result["validation"]["accepted"]


def test_user_reply_preserves_original_input_and_total_budget(tmp_path):
    question = "请选具体渗透率指标及时间范围。"
    obj, _seen = model(tmp_path, [
        [call("finish_resolution", {"outcome": "clarify", "question": question})],
        [call("get_metric_definition", {"metric_id": "lab_fx_order_rate"})],
        [call("finish_resolution", {"outcome": "ready", "requests": [request(
            "lab_fx_order_rate", period={"mode": "calendar", "unit": "week", "offset": -1})]})]])
    case = get_case("missing_slots")
    first = execute_turn(obj, case)
    assert not first["validation"]["accepted"]
    turns = [{"role": "ai", "content": question},
             {"role": "human", "content": "放心吃餐饮订单渗透率，上周，整体看。"}]
    second = execute_turn(obj, case, turns)
    assert second["validation"]["normalized_tasks"][0]["period"] == {
        "start": "2026-08-24", "end": "2026-08-30"}
    assert second["actual_input"]["messages"] == [{"role": "human", "content": case["question"]}, *turns]
    assert len([e for e in obj.trace.read() if e["kind"] == "model_request"]) == 3


def test_grounding_is_still_enforced_before_finish(tmp_path):
    obj, seen = model(tmp_path, [
        [call("get_metric_definition", {"metric_id": "lab_fx_gross_premium"}, "definition"),
         call("finish_resolution", {"outcome": "ready", "requests": [request()]}, "finish")],
        [call("finish_resolution", {"outcome": "ready", "requests": [request()]})]])
    assert execute_turn(obj, get_case("explicit_month"))["validation"]["accepted"]
    feedback = seen[-1][-1].content
    assert "缺少指标定义证据：metric_id=lab_fx_gross_premium" in feedback
    assert "get_metric_definition" in feedback
    assert "本次提交前" in feedback and "无需重复检索" in feedback


def test_missing_enum_feedback_identifies_second_metric_and_repair_succeeds(tmp_path):
    first, second = "lab_active_merchants", "lab_active_fx_open"
    requests = [request(mid, filters={"province": ["anhui"]}, group_by=["merchant_age"],
        required_predicates=[{"field_id": "valid", "operator": "ne", "value": 0}]
        + ([{"field_id": "fx_open", "operator": "eq", "value": True}] if mid == second else []))
        for mid in (first, second)]
    finish = {"outcome": "ready", "requests": requests}
    obj, seen = model(tmp_path, [
        [call("get_metric_definition", {"metric_id": first}, "first-definition"),
         call("get_metric_definition", {"metric_id": second}, "second-definition"),
         call("search_dimension_values", {"metric_id": first, "dimension_id": "province",
                                           "query": "anhui"}, "first-enum")],
        [call("finish_resolution", finish)],
        [call("search_dimension_values", {"metric_id": second, "dimension_id": "province",
                                           "query": "anhui"}, "missing-enum")],
        [call("finish_resolution", finish)],
    ])
    result = execute_turn(obj, get_case("explicit_month"))
    feedback = seen[2][-1].content
    assert f"metric_id={second}，dimension_id=province，value=anhui" in feedback
    assert first not in feedback and "缺少指标定义证据" not in feedback
    assert 'search_dimension_values({"metric_id": "lab_active_fx_open", ' in feedback
    assert '"dimension_id": "province", "query": "anhui"' in feedback
    assert result["validation"]["accepted"]
    assert len(result["model_submissions"]) == 2
    assert result["model_submissions"][0]["arguments"] == finish
    assert result["model_submissions"][1]["arguments"] == finish


def test_feedback_lists_all_gaps_once_and_keeps_metric_boundaries():
    a = MetricRequest(metric_id="metric-a", filters={"province": ["anhui", "jiangsu"]})
    b = MetricRequest(metric_id="metric-b", filters={"province": ["anhui"]})
    feedback = grounding_feedback([a, a, b], {"metric-a"}, {("metric-a", "province", "anhui")})
    assert feedback.count("缺少指标定义证据：metric_id=metric-b") == 1
    assert feedback.count("metric_id=metric-a，dimension_id=province，value=jiangsu") == 1
    assert feedback.count("metric_id=metric-b，dimension_id=province，value=anhui") == 1
    assert "metric_id=metric-a，dimension_id=province，value=anhui" not in feedback
    assert grounding_feedback([a], {"metric-a"}, {
        ("metric-a", "province", "anhui"), ("metric-a", "province", "jiangsu")}) == ""
    assert "requests 为空" in grounding_feedback([], set(), set())


def test_query_tool_is_unavailable_and_attempt_is_reported(tmp_path):
    obj, _ = model(tmp_path, [
        [call("query_agent", {"sql": "SELECT anything"})],
        [call("get_metric_definition", {"metric_id": "lab_fx_gross_premium"})],
        [call("finish_resolution", {"outcome": "ready", "requests": [request()]})]])
    result = execute_turn(obj, get_case("explicit_month"))
    assert result["boundary_violations"] == ["query_agent"]
    assert not result["validation"]["accepted"]


@pytest.mark.parametrize("predicate,accepted", [([], False),
    ([{"field_id": "valid", "operator": "ne", "value": 0}], True),
    ([{"field_id": "valid", "operator": "ne", "value": False}], False)])
def test_population_rule_never_silently_added(predicate, accepted):
    proposal = {"outcome": "ready", "requests": [request("lab_active_merchants",
        required_predicates=predicate)]}
    checked = validate_submission(proposal, LabKnowledge())
    assert checked["accepted"] is accepted
    assert checked["normalized_tasks"][0]["required_predicates"] == predicate


def test_comparison_is_explicit_and_preserves_direction():
    proposal = {"outcome": "ready", "requests": [request("lab_takeaway_orders", intent="analysis",
        period={"mode": "exact", "exact_date": "2026-08-31"},
        comparison_period={"mode": "exact", "exact_date": "2026-08-24"})]}
    checked = validate_submission(proposal, LabKnowledge())
    assert checked["accepted"]
    assert checked["normalized_tasks"][0]["comparison_period"]["start"] == "2026-08-24"
    del proposal["requests"][0]["comparison_period"]
    assert not validate_submission(proposal, LabKnowledge())["accepted"]


def test_unsupported_enum_and_unreceived_reference_rejected():
    proposal = {"outcome": "ready", "requests": [request(filters={"delivery": ["drone"]})],
                "knowledge_refs": ["K-CITY-MAPPING"]}
    checked = validate_submission(proposal, LabKnowledge("with_definition"))
    assert not checked["accepted"]
    assert any("未实际收到" in e for e in checked["errors"])
    assert any("枚举不支持" in e for e in checked["errors"])


def test_actual_knowledge_return_not_presence_counts(tmp_path):
    obj, _ = model(tmp_path, [[
        call("get_metric_definition", {"metric_id": "lab_fx_gross_premium"}, "definition"),
        call("search_business_knowledge", {"query": "下沉"}, "knowledge"),
        call("search_dimension_values", {"metric_id": "lab_fx_gross_premium", "query": "代理",
                                        "dimension_id": "city_operation"}, "enum")],
        [call("finish_resolution", {"outcome": "ready", "requests": [request(
            filters={"city_operation": ["agency"]})], "knowledge_refs": ["K-CITY-MAPPING"]})]])
    result = execute_turn(obj, get_case("alias_defined"))
    assert result["validation"]["accepted"]
    assert any(o["tool"] == "search_business_knowledge" for o in result["knowledge_observations"])
    assert result["actual_input"]["conversation_context"] == get_case("alias_defined")["history"]


def test_budget_stops_before_another_model_request(tmp_path):
    obj, _ = model(tmp_path, [[call("get_metric_definition", {"metric_id": "lab_fx_gross_premium"})]], budget=1)
    with pytest.raises(Exception, match="调用上限"):
        execute_turn(obj, get_case("explicit_month"))
    assert len([e for e in obj.trace.read() if e["kind"] == "model_request"]) == 1


def test_live_is_explicit_and_check_has_no_network():
    with pytest.raises(SystemExit):
        main(["run", "explicit_month"])
    main(["check"])


def test_semantically_valid_but_wrong_scope_fails_independent_comparison(tmp_path):
    # 两指标各自合法，但给外卖订单添加过滤属于悄悄改了需求；契约不能独自发现。
    tasks = [request("lab_insurance_orders", period={"mode": "calendar", "unit": "week", "offset": -1},
                     filters={"order_status": ["non_cancelled"]}),
             request("lab_takeaway_orders", period={"mode": "calendar", "unit": "week", "offset": -1},
                     filters={"order_status": ["non_cancelled"]})]
    checked = validate_submission({"outcome": "ready", "requests": tasks}, LabKnowledge())
    assert checked["accepted"]
    (tmp_path / "session.json").write_text(json.dumps({"case": get_case("filter_scope"),
        "turn_number": 2, "last_result": {"validation": checked,
        "resolver_result": {"outcome": "ready", "knowledge_refs": []}}}))
    report = review(tmp_path)
    assert report["exact_task_match"] is False
    assert report["final_grade"] == "pending_human_review"


def test_single_case_artifacts_and_duplicate_turn_guard(tmp_path):
    from business_analysis_repro.clarification_lab.__main__ import run_turn

    def factory(trace, max_calls):
        obj, _ = model(tmp_path, [
            [call("get_metric_definition", {"metric_id": "lab_fx_gross_premium"})],
            [call("finish_resolution", {"outcome": "ready", "requests": [request()]})]])
        obj.trace, obj.max_calls = trace, max_calls
        return obj

    result = run_turn(tmp_path, get_case("explicit_month"), [], 8, factory)
    assert result["validation"]["accepted"]
    assert result["usage"]["model_requests"] == 2
    assert result["usage"]["total_tokens"] == 240
    assert (tmp_path / "trace.html").exists()
    assert (tmp_path / "turn-1.json").exists()
    assert review(tmp_path)["exact_task_match"] is True
    with pytest.raises(ValueError, match="不能覆盖"):
        run_turn(tmp_path, get_case("explicit_month"), [], 8, factory)


def test_model_change_rejected_before_api_call(tmp_path):
    from business_analysis_repro.clarification_lab.__main__ import run_turn

    def factory(trace, max_calls):
        return SimpleNamespace(trace=trace, model_name="changed-model")

    result = run_turn(tmp_path, get_case("explicit_month"), [], 8, factory,
                      expected_model="original-model")
    assert result["status"] == "execution_error"
    assert result["usage"]["model_requests"] == 0
