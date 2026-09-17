"""A model-driven LangGraph clarification and execution workflow."""

import json
from collections.abc import Callable
from datetime import date
from typing import Annotated, Any, Literal, TypedDict

from langchain.tools import ToolRuntime, tool
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt

from business_analysis_repro.calendar_tools import resolve_business_period
from business_analysis_repro.clarification_catalog import (
    DIMENSION_VALUE_ALIASES,
    DIMENSIONS,
    METRIC_CATALOG,
    get_clarified_metric_knowledge,
    query_clarified_metric_range,
)
from business_analysis_repro.settings import create_kimi_model

Intent = Literal["query_data", "data_knowledge", "data_analysis"]
DecisionStatus = Literal["ready", "needs_clarification"]
UnresolvedField = Literal["intent", "metric", "dimension", "time", "content"]

DEFAULT_REFERENCE_DATE = "2026-08-28"
MAX_CLARIFICATION_ROUNDS = 5
MAX_AGENT_STEPS = 12


class ClarificationState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    raw_query: str
    reference_date: str
    request: dict[str, Any] | None
    pending_question: str | None
    unresolved_fields: list[UnresolvedField]
    clarification_rounds: int
    max_clarification_rounds: int
    agent_steps: int
    token_usage: dict[str, int]
    result: dict[str, Any] | None
    tool_executions: int
    status: str
    failure_reason: str | None
    final_answer: str | None


def _json_payload(content: Any) -> dict[str, Any]:
    if isinstance(content, dict):
        return content
    if isinstance(content, str):
        try:
            value = json.loads(content)
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            return {}
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                value = block.get("text") or block.get("content")
                parsed = _json_payload(value)
                if parsed:
                    return parsed
    return {}


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") in {None, "text"}:
                text = block.get("text") or block.get("content")
                if text:
                    parts.append(str(text))
        return "\n".join(parts).strip()
    return str(content).strip()


def _add_usage(current: dict[str, int], usage: dict[str, int] | None) -> dict[str, int]:
    updated = dict(current)
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        updated[key] = updated.get(key, 0) + int((usage or {}).get(key, 0))
    return updated


def initial_state(question: str, *, reference_date: str) -> ClarificationState:
    return {
        "messages": [HumanMessage(content=question)],
        "raw_query": question,
        "reference_date": reference_date,
        "request": None,
        "pending_question": None,
        "unresolved_fields": [],
        "clarification_rounds": 0,
        "max_clarification_rounds": MAX_CLARIFICATION_ROUNDS,
        "agent_steps": 0,
        "token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        "result": None,
        "tool_executions": 0,
        "status": "clarifying",
        "failure_reason": None,
        "final_answer": None,
    }


def prepare_graph_input(state: ClarificationState) -> dict[str, Any]:
    """Normalize CLI raw_query and Studio content-block messages."""
    raw_query = (state.get("raw_query") or "").strip()
    if not raw_query:
        for message in reversed(state.get("messages", [])):
            if isinstance(message, HumanMessage):
                raw_query = _message_text(message.content)
                if raw_query:
                    break

    if not raw_query:
        return {
            "status": "failed",
            "failure_reason": "缺少用户问题：请填写 raw_query 或发送一条用户消息",
        }

    normalized = initial_state(
        raw_query,
        reference_date=state.get("reference_date") or DEFAULT_REFERENCE_DATE,
    )
    if state.get("messages"):
        normalized.pop("messages")
    return normalized


def _periods_from_messages(messages: list[BaseMessage]) -> set[tuple[str, str]]:
    periods: set[tuple[str, str]] = set()
    for message in messages:
        if not isinstance(message, ToolMessage) or message.name != "resolve_business_period":
            continue
        payload = _json_payload(message.content)
        if payload.get("status") == "ok" and payload.get("start_date") and payload.get("end_date"):
            periods.add((str(payload["start_date"]), str(payload["end_date"])))
    return periods


def _validate_ready_request(
    decision: dict[str, Any],
    messages: list[BaseMessage],
) -> list[str]:
    errors: list[str] = []
    intent = decision.get("intent")
    metric_ids = list(dict.fromkeys(decision.get("metric_ids") or []))
    invalid_metric_ids = [metric_id for metric_id in metric_ids if metric_id not in METRIC_CATALOG]
    if intent not in {"query_data", "data_knowledge", "data_analysis"}:
        errors.append("ready状态必须提供有效intent")
    if not metric_ids:
        errors.append("ready状态必须至少提供一个metric_id")
    if invalid_metric_ids:
        errors.append(f"metric_id不在目录中：{invalid_metric_ids}")
    if not decision.get("request_summary"):
        errors.append("ready状态必须提供request_summary")

    if intent in {"query_data", "data_analysis"}:
        dimension = decision.get("dimension")
        start_date = decision.get("start_date")
        end_date = decision.get("end_date")
        if dimension not in DIMENSIONS:
            errors.append("数据查询或分析必须提供有效dimension")
        if not start_date or not end_date:
            errors.append("数据查询或分析必须提供start_date和end_date")
        else:
            try:
                start = date.fromisoformat(str(start_date))
                end = date.fromisoformat(str(end_date))
                if start > end:
                    errors.append("start_date不能晚于end_date")
            except ValueError:
                errors.append("日期必须为ISO格式")
            if (str(start_date), str(end_date)) not in _periods_from_messages(messages):
                errors.append("起止日期必须来自resolve_business_period工具结果")

        dimension_value = decision.get("dimension_value")
        if dimension == "overall" and dimension_value is not None:
            errors.append("overall维度不应提供dimension_value")
        if dimension in DIMENSION_VALUE_ALIASES and dimension_value is not None:
            valid_values = set(DIMENSION_VALUE_ALIASES[dimension].values())
            if dimension_value not in valid_values:
                errors.append(f"dimension_value不在{dimension}目录中")

    if intent == "data_analysis" and not decision.get("analysis_goal"):
        errors.append("数据分析必须提供analysis_goal")
    return errors


@tool
def submit_clarification(
    status: DecisionStatus,
    runtime: ToolRuntime,
    intent: Intent | None = None,
    metric_ids: list[str] | None = None,
    dimension: Literal["overall", "merchant", "channel"] | None = None,
    dimension_value: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    analysis_goal: str | None = None,
    request_summary: str | None = None,
    question: str | None = None,
    unresolved_fields: list[UnresolvedField] | None = None,
) -> dict[str, Any]:
    """提交澄清结论，并结束当前 Clarification Agent 循环。

    信息足够执行时提交 ready 和完整标准请求；仍有歧义时提交 needs_clarification，
    question 必须一次询问全部未决项。不要用自然语言回答来代替这个工具。
    """
    decision = {
        "status": status,
        "intent": intent,
        "metric_ids": list(dict.fromkeys(metric_ids or [])),
        "dimension": dimension,
        "dimension_value": dimension_value,
        "start_date": start_date,
        "end_date": end_date,
        "analysis_goal": analysis_goal,
        "request_summary": request_summary,
        "question": question,
        "unresolved_fields": unresolved_fields or [],
    }
    errors: list[str] = []
    if status == "needs_clarification":
        if not question:
            errors.append("needs_clarification必须提供question")
        if not unresolved_fields:
            errors.append("needs_clarification必须提供unresolved_fields")
    else:
        errors.extend(_validate_ready_request(decision, runtime.state["messages"]))
    return {
        "status": "invalid" if errors else "accepted",
        "errors": errors,
        "decision": decision,
    }


CLARIFICATION_TOOLS = [resolve_business_period, submit_clarification]


def _clarification_system_prompt(state: ClarificationState) -> str:
    metrics = [
        {
            "metric_id": metric_id,
            "canonical_name": metric["canonical_name"],
            "product_name": metric["product_name"],
            "product_aliases": sorted(metric["product_aliases"]),
            "definition": metric["definition"],
        }
        for metric_id, metric in METRIC_CATALOG.items()
    ]
    dimension_values = {
        dimension: sorted(set(aliases.values()))
        for dimension, aliases in DIMENSION_VALUE_ALIASES.items()
    }
    context = {
        "reference_date": state["reference_date"],
        "metric_catalog": metrics,
        "dimensions": list(DIMENSIONS),
        "dimension_values": dimension_values,
    }
    return f"""你是经营分析系统的 Clarification Agent，只负责把完整对话变成可执行请求，不查询数据、不回答业务结果。

核心目标：明确用户的意图、标准指标、查询维度、时间起止和请求内容。

工作原则：
1. 根据整段对话理解语义，包括用户对上一轮提案的确认、否定、补充和修改；不要依赖固定确认词或固定时间短语。
2. 指标只能选择目录里的 metric_id。用户的集合式表达、多选表达和别名由你结合目录语义理解。
3. query_data 需要指标、维度和时间；data_analysis 还需要明确 analysis_goal；data_knowledge 只要求能确定指标和所问内容。
4. 所有将要执行的数据查询或分析，都必须先调用 resolve_business_period 获得 start_date/end_date。你负责理解时间语义，工具只负责确定性日历计算；不要自行计算日期。
5. 信息足够时，不要澄清，直接调用 submit_clarification(status=ready)。
6. 信息缺失或有真实歧义时，调用 submit_clarification(status=needs_clarification)，question 一次问完全部未决项；已经确认的内容不要重复问。
7. 用户对整体提案表示确认时，应结合上下文继承提案内容；用户只修改一项时，其余已明确内容继续有效。
8. 每次只调用一个工具。日历工具返回后再继续判断，最终必须调用 submit_clarification。

运行上下文：
{json.dumps(context, ensure_ascii=False)}"""


def clarification_agent(state: ClarificationState) -> dict[str, Any]:
    if state.get("status") == "failed":
        return {}
    if state.get("agent_steps", 0) >= MAX_AGENT_STEPS:
        return {
            "status": "failed",
            "failure_reason": "Clarification Agent超过最大工具循环次数",
        }

    model = create_kimi_model().bind_tools(CLARIFICATION_TOOLS)
    response = model.invoke(
        [SystemMessage(content=_clarification_system_prompt(state)), *state["messages"]],
        config={"run_name": "clarification_agent", "tags": ["e2", "clarification"]},
    )
    if not response.tool_calls:
        return {
            "messages": [response],
            "agent_steps": state.get("agent_steps", 0) + 1,
            "token_usage": _add_usage(state["token_usage"], response.usage_metadata),
            "status": "failed",
            "failure_reason": "Clarification Agent未调用约定工具",
        }
    return {
        "messages": [response],
        "agent_steps": state.get("agent_steps", 0) + 1,
        "token_usage": _add_usage(state["token_usage"], response.usage_metadata),
        "status": "clarifying",
    }


def _latest_tool_message(state: ClarificationState) -> ToolMessage | None:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, ToolMessage):
            return message
        if isinstance(message, HumanMessage):
            break
    return None


def apply_clarification_decision(state: ClarificationState) -> dict[str, Any]:
    tool_message = _latest_tool_message(state)
    payload = _json_payload(tool_message.content if tool_message else None)
    decision = payload.get("decision") or {}
    if payload.get("status") != "accepted" or not decision:
        return {
            "status": "failed",
            "failure_reason": "未获得有效的澄清决策",
        }

    if decision["status"] == "needs_clarification":
        if state.get("clarification_rounds", 0) >= state.get(
            "max_clarification_rounds", MAX_CLARIFICATION_ROUNDS
        ):
            return {
                "status": "failed",
                "failure_reason": "达到澄清安全上限，仍未形成可执行请求",
            }
        question = str(decision["question"])
        return {
            "messages": [AIMessage(content=question)],
            "pending_question": question,
            "unresolved_fields": decision.get("unresolved_fields") or [],
            "status": "waiting_for_user",
        }

    request = {
        key: decision.get(key)
        for key in (
            "intent",
            "metric_ids",
            "dimension",
            "dimension_value",
            "start_date",
            "end_date",
            "analysis_goal",
            "request_summary",
        )
    }
    return {
        "request": request,
        "pending_question": None,
        "unresolved_fields": [],
        "status": "ready",
    }


def ask_human(state: ClarificationState) -> dict[str, Any]:
    answer = interrupt(
        {
            "question": state["pending_question"],
            "unresolved_fields": state["unresolved_fields"],
            "round": state.get("clarification_rounds", 0) + 1,
        }
    )
    answer_text = answer if isinstance(answer, str) else json.dumps(answer, ensure_ascii=False)
    return {
        "messages": [HumanMessage(content=answer_text)],
        "pending_question": None,
        "unresolved_fields": [],
        "clarification_rounds": state.get("clarification_rounds", 0) + 1,
        "status": "clarifying",
    }


def _query_period(state: ClarificationState, metric_id: str, *, run_name: str) -> dict[str, Any]:
    request = state["request"]
    return query_clarified_metric_range.invoke(
        {
            "metric_id": metric_id,
            "start_date": request["start_date"],
            "end_date": request["end_date"],
            "dimension": request["dimension"],
            "dimension_value": request.get("dimension_value"),
        },
        config={"run_name": run_name, "tags": ["e2", "synthetic-data"]},
    )


def query_data_node(state: ClarificationState) -> dict[str, Any]:
    metric_ids = state["request"]["metric_ids"]
    results = [
        _query_period(state, metric_id, run_name="query_clarified_metric_range")
        for metric_id in metric_ids
    ]
    result: dict[str, Any] = (
        results[0]
        if len(results) == 1
        else {
            "status": "ok" if all(item["status"] == "ok" for item in results) else "partial",
            "metric_count": len(results),
            "results": results,
        }
    )
    return {
        "result": result,
        "tool_executions": state.get("tool_executions", 0) + len(results),
        "status": "executed",
    }


def data_knowledge_node(state: ClarificationState) -> dict[str, Any]:
    metric_ids = state["request"]["metric_ids"]
    results = [
        get_clarified_metric_knowledge.invoke(
            {"metric_id": metric_id},
            config={"run_name": "get_metric_knowledge", "tags": ["e2", "synthetic-data"]},
        )
        for metric_id in metric_ids
    ]
    return {
        "result": results[0] if len(results) == 1 else {"status": "ok", "results": results},
        "tool_executions": state.get("tool_executions", 0) + len(results),
        "status": "executed",
    }


def data_analysis_node(state: ClarificationState) -> dict[str, Any]:
    metric_ids = state["request"]["metric_ids"]
    evidence = [
        _query_period(state, metric_id, run_name="analysis_evidence_query")
        for metric_id in metric_ids
    ]
    return {
        "result": {
            "status": "ok" if all(item["status"] == "ok" for item in evidence) else "partial",
            "analysis_goal": state["request"]["analysis_goal"],
            "evidence": evidence[0] if len(evidence) == 1 else evidence,
            "message": "E2仅验证分析意图路由，复杂分析将在后续实验展开",
        },
        "tool_executions": state.get("tool_executions", 0) + len(evidence),
        "status": "executed",
    }


def generate_answer(state: ClarificationState) -> dict[str, Any]:
    response = create_kimi_model().invoke(
        [
            SystemMessage(
                content=(
                    "你是经营分析助手。只能依据已确认请求和模拟工具结果回答。"
                    "简洁说明标准指标、维度、时间范围和结果，不得补充工具未返回的事实。"
                )
            ),
            HumanMessage(
                content=json.dumps(
                    {"request": state["request"], "result": state["result"]},
                    ensure_ascii=False,
                )
            ),
        ],
        config={"run_name": "generate_clarified_answer", "tags": ["e2", "final-answer"]},
    )
    answer = _message_text(response.content)
    return {
        "messages": [response],
        "final_answer": answer,
        "token_usage": _add_usage(state["token_usage"], response.usage_metadata),
        "status": "completed",
    }


def safe_fail(state: ClarificationState) -> dict[str, Any]:
    answer = f"本次请求无法安全执行：{state.get('failure_reason') or '未形成有效请求'}。"
    return {
        "messages": [AIMessage(content=answer)],
        "final_answer": answer,
        "status": "failed",
    }


def route_after_agent(state: ClarificationState) -> str:
    return "safe_fail" if state.get("status") == "failed" else "clarification_tools"


def route_after_tools(state: ClarificationState) -> str:
    message = _latest_tool_message(state)
    if message is None:
        return "safe_fail"
    if message.name != "submit_clarification":
        return "clarification_agent"
    payload = _json_payload(message.content)
    return (
        "apply_clarification_decision"
        if payload.get("status") == "accepted"
        else "clarification_agent"
    )


def route_after_decision(state: ClarificationState) -> str:
    if state.get("status") == "failed":
        return "safe_fail"
    if state.get("status") == "waiting_for_user":
        return "ask_human"
    intent = (state.get("request") or {}).get("intent")
    return {
        "query_data": "query_data",
        "data_knowledge": "data_knowledge",
        "data_analysis": "data_analysis",
    }.get(intent, "safe_fail")


Node = Callable[[ClarificationState], dict[str, Any]]


def build_clarification_graph(
    *,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
    clarification_node: Node = clarification_agent,
    answer_node: Node = generate_answer,
):
    builder = StateGraph(ClarificationState)
    builder.add_node("prepare_input", prepare_graph_input)
    builder.add_node("clarification_agent", clarification_node)
    builder.add_node(
        "clarification_tools",
        ToolNode(CLARIFICATION_TOOLS, handle_tool_errors=True),
    )
    builder.add_node("apply_clarification_decision", apply_clarification_decision)
    builder.add_node("ask_human", ask_human)
    builder.add_node("query_data", query_data_node)
    builder.add_node("data_knowledge", data_knowledge_node)
    builder.add_node("data_analysis", data_analysis_node)
    builder.add_node("generate_answer", answer_node)
    builder.add_node("safe_fail", safe_fail)

    builder.add_edge(START, "prepare_input")
    builder.add_edge("prepare_input", "clarification_agent")
    builder.add_conditional_edges(
        "clarification_agent",
        route_after_agent,
        {
            "clarification_tools": "clarification_tools",
            "safe_fail": "safe_fail",
        },
    )
    builder.add_conditional_edges(
        "clarification_tools",
        route_after_tools,
        {
            "clarification_agent": "clarification_agent",
            "apply_clarification_decision": "apply_clarification_decision",
            "safe_fail": "safe_fail",
        },
    )
    builder.add_conditional_edges(
        "apply_clarification_decision",
        route_after_decision,
        {
            "ask_human": "ask_human",
            "query_data": "query_data",
            "data_knowledge": "data_knowledge",
            "data_analysis": "data_analysis",
            "safe_fail": "safe_fail",
        },
    )
    builder.add_edge("ask_human", "clarification_agent")
    builder.add_edge("query_data", "generate_answer")
    builder.add_edge("data_knowledge", "generate_answer")
    builder.add_edge("data_analysis", "generate_answer")
    builder.add_edge("generate_answer", END)
    builder.add_edge("safe_fail", END)
    return builder.compile(checkpointer=checkpointer)


# Agent Server supplies persistence when loaded through langgraph.json.
graph = build_clarification_graph()
