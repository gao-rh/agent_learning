import json
from collections.abc import Callable
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from business_analysis_repro.clarification_graph import (
    ClarificationState,
    build_clarification_graph,
    initial_state,
    prepare_graph_input,
)

TIMELY_PREMIUM = "timely_delivery_premium_income"
PREMIUM_METRICS = [
    "timely_delivery_premium_income",
    "cancellation_insurance_premium_income",
    "food_assurance_premium_income",
]


def action(name: str, args: dict[str, Any], call_id: str) -> dict[str, Any]:
    return {"name": name, "args": args, "id": call_id, "type": "tool_call"}


def model_action(name: str, args: dict[str, Any], call_id: str) -> dict[str, Any]:
    return {
        "messages": [AIMessage(content="", tool_calls=[action(name, args, call_id)])],
        "status": "clarifying",
    }


def payload(message: ToolMessage) -> dict[str, Any]:
    return json.loads(message.content) if isinstance(message.content, str) else message.content


def fixed_answer(state: ClarificationState) -> dict[str, Any]:
    result = state["result"]
    answer = json.dumps(result, ensure_ascii=False)
    return {
        "messages": [AIMessage(content=answer)],
        "final_answer": answer,
        "status": "completed",
    }


def calendar_then_ready(
    *,
    calendar_args: dict[str, Any],
    request_args: dict[str, Any],
) -> Callable[[ClarificationState], dict[str, Any]]:
    def scripted(state: ClarificationState) -> dict[str, Any]:
        latest = state["messages"][-1]
        if isinstance(latest, ToolMessage) and latest.name == "resolve_business_period":
            period = payload(latest)
            return model_action(
                "submit_clarification",
                {
                    "status": "ready",
                    **request_args,
                    "start_date": period["start_date"],
                    "end_date": period["end_date"],
                },
                "submit-ready",
            )
        return model_action(
            "resolve_business_period",
            calendar_args,
            "resolve-period",
        )

    return scripted


def interrupt_payload(result: dict[str, Any]) -> dict[str, Any]:
    return result["__interrupt__"][0].value


def test_prepare_graph_input_accepts_studio_content_blocks() -> None:
    prepared = prepare_graph_input(
        {
            "messages": [
                HumanMessage(
                    content=[{"type": "text", "text": "查询准时保保费收入，App渠道，今天。"}]
                )
            ]
        }
    )

    assert prepared["raw_query"] == "查询准时保保费收入，App渠道，今天。"
    assert prepared["reference_date"] == "2026-08-28"
    assert "messages" not in prepared


def test_complete_request_runs_model_tool_model_loop_without_clarification() -> None:
    clarifier = calendar_then_ready(
        calendar_args={"mode": "rolling", "unit": "week", "offset": 0},
        request_args={
            "intent": "query_data",
            "metric_ids": [TIMELY_PREMIUM],
            "dimension": "channel",
            "dimension_value": "App",
            "request_summary": "查询近一周App渠道的准时保保费收入",
        },
    )
    graph = build_clarification_graph(
        checkpointer=InMemorySaver(),
        clarification_node=clarifier,
        answer_node=fixed_answer,
    )
    result = graph.invoke(
        initial_state(
            "查询准时保保费收入，App渠道，近一周。",
            reference_date="2026-08-29",
        ),
        config={"configurable": {"thread_id": "direct-ready"}},
    )

    assert "__interrupt__" not in result
    assert result["status"] == "completed"
    assert result["clarification_rounds"] == 0
    assert result["request"]["start_date"] == "2026-08-23"
    assert result["request"]["end_date"] == "2026-08-29"
    assert result["result"]["day_count"] == 7
    assert result["tool_executions"] == 1
    tool_names = [message.name for message in result["messages"] if isinstance(message, ToolMessage)]
    assert tool_names == ["resolve_business_period", "submit_clarification"]


def test_one_question_contains_all_unresolved_fields_then_model_handles_confirmation() -> None:
    question = (
        "请确认：指标是否为准时保保费收入，查询范围是否按整体汇总，"
        "查询时间是否为今天？如有调整请一起说明。"
    )

    def scripted(state: ClarificationState) -> dict[str, Any]:
        latest = state["messages"][-1]
        human_count = sum(isinstance(message, HumanMessage) for message in state["messages"])
        if human_count == 1:
            return model_action(
                "submit_clarification",
                {
                    "status": "needs_clarification",
                    "question": question,
                    "unresolved_fields": ["metric", "dimension", "time"],
                },
                "submit-question",
            )
        if isinstance(latest, HumanMessage):
            assert latest.content == "确认"
            return model_action(
                "resolve_business_period",
                {"mode": "calendar", "unit": "day", "offset": 0},
                "resolve-confirmed-day",
            )
        assert isinstance(latest, ToolMessage)
        period = payload(latest)
        return model_action(
            "submit_clarification",
            {
                "status": "ready",
                "intent": "query_data",
                "metric_ids": [TIMELY_PREMIUM],
                "dimension": "overall",
                "start_date": period["start_date"],
                "end_date": period["end_date"],
                "request_summary": "查询今天整体准时保保费收入",
            },
            "submit-confirmed",
        )

    graph = build_clarification_graph(
        checkpointer=InMemorySaver(),
        clarification_node=scripted,
        answer_node=fixed_answer,
    )
    config = {"configurable": {"thread_id": "semantic-confirmation"}}
    interrupted = graph.invoke(
        initial_state("看看B准的保费", reference_date="2026-08-28"),
        config=config,
    )

    first = interrupt_payload(interrupted)
    assert first["question"] == question
    assert first["unresolved_fields"] == ["metric", "dimension", "time"]

    result = graph.invoke(Command(resume="确认"), config=config)
    assert result["status"] == "completed"
    assert result["clarification_rounds"] == 1
    assert result["request"]["metric_ids"] == [TIMELY_PREMIUM]
    assert result["request"]["dimension"] == "overall"
    assert result["request"]["start_date"] == "2026-08-28"


def test_model_can_interpret_collective_metric_reply_without_local_phrase_rules() -> None:
    def scripted(state: ClarificationState) -> dict[str, Any]:
        latest = state["messages"][-1]
        human_count = sum(isinstance(message, HumanMessage) for message in state["messages"])
        if human_count == 1:
            return model_action(
                "submit_clarification",
                {
                    "status": "needs_clarification",
                    "question": "请确认要查哪几个保费指标，并补充查询时间。",
                    "unresolved_fields": ["metric", "time"],
                },
                "submit-metric-question",
            )
        if isinstance(latest, HumanMessage):
            assert latest.content == "三种保费，近一周"
            return model_action(
                "resolve_business_period",
                {"mode": "rolling", "unit": "week", "offset": 0},
                "resolve-collective-period",
            )
        period = payload(latest)
        return model_action(
            "submit_clarification",
            {
                "status": "ready",
                "intent": "query_data",
                "metric_ids": PREMIUM_METRICS,
                "dimension": "overall",
                "start_date": period["start_date"],
                "end_date": period["end_date"],
                "request_summary": "查询近一周整体三种保费收入",
            },
            "submit-collective",
        )

    graph = build_clarification_graph(
        checkpointer=InMemorySaver(),
        clarification_node=scripted,
        answer_node=fixed_answer,
    )
    config = {"configurable": {"thread_id": "collective-metrics"}}
    graph.invoke(
        initial_state("查询整体保费", reference_date="2026-08-29"),
        config=config,
    )
    result = graph.invoke(Command(resume="三种保费，近一周"), config=config)

    assert result["status"] == "completed"
    assert result["request"]["metric_ids"] == PREMIUM_METRICS
    assert result["result"]["metric_count"] == 3
    assert result["tool_executions"] == 3


def test_ready_request_without_calendar_evidence_is_rejected_and_returned_to_model() -> None:
    def scripted(state: ClarificationState) -> dict[str, Any]:
        latest = state["messages"][-1]
        if isinstance(latest, HumanMessage):
            return model_action(
                "submit_clarification",
                {
                    "status": "ready",
                    "intent": "query_data",
                    "metric_ids": [TIMELY_PREMIUM],
                    "dimension": "overall",
                    "start_date": "2026-08-28",
                    "end_date": "2026-08-28",
                    "request_summary": "查询今天整体准时保保费收入",
                },
                "premature-submit",
            )
        if isinstance(latest, ToolMessage) and latest.name == "submit_clarification":
            rejected = payload(latest)
            assert rejected["status"] == "invalid"
            assert any("resolve_business_period" in error for error in rejected["errors"])
            return model_action(
                "resolve_business_period",
                {"mode": "calendar", "unit": "day", "offset": 0},
                "corrected-period",
            )
        period = payload(latest)
        return model_action(
            "submit_clarification",
            {
                "status": "ready",
                "intent": "query_data",
                "metric_ids": [TIMELY_PREMIUM],
                "dimension": "overall",
                "start_date": period["start_date"],
                "end_date": period["end_date"],
                "request_summary": "查询今天整体准时保保费收入",
            },
            "corrected-submit",
        )

    graph = build_clarification_graph(
        checkpointer=InMemorySaver(),
        clarification_node=scripted,
        answer_node=fixed_answer,
    )
    result = graph.invoke(
        initial_state("查询今天整体准时保保费收入", reference_date="2026-08-28"),
        config={"configurable": {"thread_id": "calendar-validation"}},
    )

    assert result["status"] == "completed"
    submit_messages = [
        payload(message)
        for message in result["messages"]
        if isinstance(message, ToolMessage) and message.name == "submit_clarification"
    ]
    assert [message["status"] for message in submit_messages] == ["invalid", "accepted"]
