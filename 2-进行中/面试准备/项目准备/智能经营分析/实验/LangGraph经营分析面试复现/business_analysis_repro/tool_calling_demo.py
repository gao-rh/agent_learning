"""Run an explicit Kimi -> local tool -> Kimi Tool Calling loop."""

import argparse
import json
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tracers.langchain import wait_for_all_tracers
from langsmith import traceable

from business_analysis_repro.metric_tools import TOOLS, TOOLS_BY_NAME
from business_analysis_repro.settings import create_kimi_model, ensure_langsmith_ready

DEFAULT_QUESTION = "查询 2026-08-01 的保费收入，并告诉我数据值。"
SYSTEM_PROMPT = """你是一个经营分析助手。
凡是涉及业务指标数值或定义，都必须先调用给定工具，禁止凭空编造。
根据用户意图选择最合适的工具。工具返回失败时，诚实说明没有查到。
最终回答要简洁，并明确日期、指标值和单位。"""


@dataclass(frozen=True)
class ToolLoopResult:
    messages: list[BaseMessage]
    model_calls: int
    tool_executions: int
    input_tokens: int
    output_tokens: int
    total_tokens: int


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _add_usage(ai_message: AIMessage, totals: dict[str, int]) -> None:
    usage = ai_message.usage_metadata or {}
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        totals[key] += int(usage.get(key, 0))


def execute_tool_call(tool_call: dict[str, Any]) -> ToolMessage:
    """Dispatch one model-produced ToolCall to a registered local Python tool."""
    tool_name = str(tool_call["name"])
    tool_call_id = str(tool_call["id"])
    arguments = tool_call.get("args", {})
    selected_tool = TOOLS_BY_NAME.get(tool_name)

    if selected_tool is None:
        result: Any = {
            "status": "error",
            "message": f"工具未注册：{tool_name}",
            "available_tools": sorted(TOOLS_BY_NAME),
        }
    else:
        result = selected_tool.invoke(
            arguments,
            config={
                "run_name": f"local_tool__{tool_name}",
                "tags": ["e1", "synthetic-data", "local-tool"],
            },
        )

    return ToolMessage(
        content=_json(result),
        tool_call_id=tool_call_id,
        name=tool_name,
    )


@traceable(
    name="e1_kimi_tool_calling_loop",
    run_type="chain",
    tags=["e1", "tool-calling", "synthetic-data"],
)
def _run_traced_tool_loop(question: str, max_model_calls: int) -> ToolLoopResult:
    """Run the traced body until Kimi returns a normal answer or the limit is reached."""
    model_with_tools = create_kimi_model().bind_tools(TOOLS, tool_choice="auto")
    messages: list[BaseMessage] = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=question),
    ]
    usage_totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    tool_executions = 0

    print("\n=== 0. 应用准备 ===")
    print(f"可用工具: {', '.join(sorted(TOOLS_BY_NAME))}")
    print(f"用户问题: {question}")

    for model_call_number in range(1, max_model_calls + 1):
        print(f"\n=== {model_call_number}. 应用调用 Kimi ===")
        ai_message = model_with_tools.invoke(
            messages,
            config={
                "run_name": f"kimi_tool_decision_round_{model_call_number}",
                "tags": ["e1", "kimi-k2.6", f"round-{model_call_number}"],
                "metadata": {
                    "experiment": "e1-tool-calling",
                    "data_classification": "synthetic",
                    "round": model_call_number,
                },
            },
        )
        messages.append(ai_message)
        _add_usage(ai_message, usage_totals)

        if not ai_message.tool_calls:
            print("Kimi 返回: 最终回答（本轮没有 ToolCall）")
            print(f"最终回答: {ai_message.content}")
            print("\n=== 汇总 ===")
            print(f"模型请求次数: {model_call_number}")
            print(f"本地工具执行次数: {tool_executions}")
            print(f"input_tokens: {usage_totals['input_tokens']}")
            print(f"output_tokens: {usage_totals['output_tokens']}")
            print(f"total_tokens: {usage_totals['total_tokens']}")
            return ToolLoopResult(
                messages=messages,
                model_calls=model_call_number,
                tool_executions=tool_executions,
                **usage_totals,
            )

        print(f"Kimi 返回: {len(ai_message.tool_calls)} 个 ToolCall")
        for tool_call in ai_message.tool_calls:
            print(
                "模型选择: "
                f"name={tool_call['name']}, args={_json(tool_call['args'])}, "
                f"id={tool_call['id']}"
            )
            print("Python 执行: 根据 name 在本地工具注册表中查找并调用函数")
            tool_message = execute_tool_call(tool_call)
            messages.append(tool_message)
            tool_executions += 1
            print(
                "工具返回: "
                f"name={tool_message.name}, id={tool_message.tool_call_id}, "
                f"content={tool_message.content}"
            )
            print("应用动作: 把 ToolMessage 追加到 messages，下一轮发回 Kimi")

    raise RuntimeError(f"超过最多 {max_model_calls} 次模型请求，Tool Calling Loop 未正常结束")


def run_tool_loop(question: str = DEFAULT_QUESTION, *, max_model_calls: int = 4) -> ToolLoopResult:
    """Load tracing configuration, run the loop, and flush background traces."""
    langsmith_settings = ensure_langsmith_ready()
    print(
        "LangSmith: "
        f"{'已开启' if langsmith_settings.tracing_enabled else '未开启'}, "
        f"project={langsmith_settings.project_name}"
    )
    result = _run_traced_tool_loop(question, max_model_calls)
    if langsmith_settings.tracing_enabled:
        wait_for_all_tracers()
        print("LangSmith: Trace 已提交，可在项目页面查看父子调用树")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行一次 Kimi Tool Calling 完整链路")
    parser.add_argument(
        "question",
        nargs="?",
        default=DEFAULT_QUESTION,
        help=f"用户问题（默认：{DEFAULT_QUESTION}）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_tool_loop(args.question)


if __name__ == "__main__":
    main()
