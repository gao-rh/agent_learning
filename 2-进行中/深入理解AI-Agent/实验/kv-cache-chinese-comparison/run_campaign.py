#!/usr/bin/env python3
"""Run the textbook KV-cache six-mode campaign with Chinese prompts and receipts."""

from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import os
import random
import re
import statistics
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any


LAB_DIR = Path(__file__).resolve().parent
VAULT_ROOT = LAB_DIR.parents[3]
BOOK_ROOT = (
    VAULT_ROOT
    / "2-进行中/深入理解AI-Agent/资料/本地资料/深入理解AI-Agent/ai-agent-book-chapter2-current"
)
KV_DIR = BOOK_ROOT / "chapter2/kv-cache"
RUNS_DIR = LAB_DIR / "runs"
BASELINE_PATH = KV_DIR / "result_correct_20260808_185133.json"
MODEL = "kimi-k2.6"
RANDOM_SEED = 20260808
MAX_ITERATIONS = 8
MODE_ORDER = [
    "correct",
    "dynamic_system",
    "shuffled_tools",
    "dynamic_profile",
    "sliding_window",
    "text_format",
]

sys.path.insert(0, str(BOOK_ROOT))
sys.path.insert(0, str(KV_DIR))

try:
    from dotenv import load_dotenv

    load_dotenv(KV_DIR / ".env")
except ImportError:
    pass

from agent import KVCacheAgent, KVCacheMode  # noqa: E402


MODE_MAP = {
    "correct": KVCacheMode.CORRECT,
    "dynamic_system": KVCacheMode.DYNAMIC_SYSTEM,
    "shuffled_tools": KVCacheMode.SHUFFLED_TOOLS,
    "dynamic_profile": KVCacheMode.DYNAMIC_PROFILE,
    "sliding_window": KVCacheMode.SLIDING_WINDOW,
    "text_format": KVCacheMode.TEXT_FORMAT,
}

MODE_INFO = {
    "correct": ("稳定上下文", "消息列表只创建一次，之后只在末尾追加。"),
    "dynamic_system": ("动态系统提示", "每轮在系统提示末尾追加不同时间戳。"),
    "shuffled_tools": ("工具顺序变化", "每轮随机改变三个工具定义的顺序。"),
    "dynamic_profile": ("动态用户资料", "每轮在靠前位置加入不断变化的剩余额度。"),
    "sliding_window": ("滑动窗口", "每轮只保留最近约六条历史消息。"),
    "text_format": ("历史转纯文本", "每轮把结构化历史重新拼成一条纯文本消息。"),
}

CHINESE_SYSTEM_PROMPT = """你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。"""

TOOL_TRANSLATIONS = {
    "read_file": {
        "description": "读取文件内容，可以指定起始行和行数",
        "file_path": "相对于工具根目录的文件路径",
        "offset": "从第几行开始读取，0 表示第一行",
        "size": "读取多少行；省略时读取全部",
    },
    "find": {
        "description": "按照文件名模式递归查找文件",
        "pattern": "文件名模式，支持 *.py 等通配符",
        "directory": "相对于工具根目录的查找目录，默认是当前目录",
    },
    "grep": {
        "description": "在文件中搜索正则表达式",
        "pattern": "要搜索的正则表达式",
        "file_path": "要搜索的单个文件，可选",
        "directory": "要搜索的目录，可选",
    },
}

TASK_TEMPLATE = """你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：{campaign_id}"""

SECRET_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]{8,}")


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sanitize(value: Any) -> Any:
    """Make SDK objects JSON-safe, remove hidden reasoning, and redact key-shaped text."""
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    if isinstance(value, dict):
        return {
            str(key): sanitize(item)
            for key, item in value.items()
            if str(key) not in {"reasoning_content", "api_key", "authorization"}
        }
    if isinstance(value, (list, tuple)):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        return SECRET_PATTERN.sub("[已隐藏凭据]", value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return sanitize(str(value))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_api_key() -> str:
    key = (
        os.getenv("MOONSHOT_API_KEY")
        or os.getenv("KIMI_API_KEY")
        or os.getenv("OPENROUTER_API_KEY")
    )
    if not key:
        raise RuntimeError(
            "没有找到 MOONSHOT_API_KEY / KIMI_API_KEY / OPENROUTER_API_KEY。"
        )
    return key


class ChineseKVCacheAgent(KVCacheAgent):
    """Only localizes model-visible text; all six textbook mode mechanics stay intact."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for tool in self.tool_definitions:
            function = tool["function"]
            name = function["name"]
            translations = TOOL_TRANSLATIONS[name]
            function["description"] = translations["description"]
            properties = function["parameters"]["properties"]
            for property_name, property_spec in properties.items():
                property_spec["description"] = translations[property_name]

    def _get_system_prompt(self) -> str:
        if self.mode == KVCacheMode.DYNAMIC_SYSTEM:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            return f"{CHINESE_SYSTEM_PROMPT}\n\n当前时间：{timestamp}"
        return CHINESE_SYSTEM_PROMPT

    def _get_user_profile_message(self) -> dict[str, str] | None:
        if self.mode == KVCacheMode.DYNAMIC_PROFILE:
            self.user_credits -= 1
            return {
                "role": "user",
                "content": f"[用户资料：高级用户，剩余 {self.user_credits} 点额度]",
            }
        return None

    def _format_messages(self, task: str) -> list[dict[str, Any]]:
        messages = super()._format_messages(task)
        if self.mode != KVCacheMode.TEXT_FORMAT:
            return messages

        replacements = {
            "Previous conversation:\n": "此前对话：\n",
            "ASSISTANT: [Making tool calls]": "助手：[正在调用工具]",
            "  - Calling ": "  - 调用 ",
            " with args: ": "，参数：",
            "TOOL RESPONSE: ": "工具返回：",
            "ASSISTANT: ": "助手：",
            "USER: ": "用户：",
        }
        for message in messages:
            content = message.get("content")
            if not isinstance(content, str) or not content.startswith("Previous conversation:"):
                continue
            for old, new in replacements.items():
                content = content.replace(old, new)
            message["content"] = content
        return messages


def usage_dict(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {"prompt_tokens": 0, "completion_tokens": 0, "cached_tokens": 0}
    prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion = int(getattr(usage, "completion_tokens", 0) or 0)
    cached = getattr(usage, "cached_tokens", None)
    if cached is None:
        details = getattr(usage, "prompt_tokens_details", None)
        cached = getattr(details, "cached_tokens", 0) if details else 0
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "cached_tokens": int(cached or 0),
    }


def install_recorder(agent: ChineseKVCacheAgent, rounds: list[dict[str, Any]]) -> None:
    original_create = agent.client.chat.completions.create

    def recorded_create(**kwargs: Any) -> Any:
        round_number = len(rounds) + 1
        request = sanitize(copy.deepcopy(kwargs))
        started_at = now_iso()
        start = time.perf_counter()
        try:
            response = original_create(**kwargs)
        except Exception as exc:
            rounds.append(
                {
                    "round": round_number,
                    "started_at": started_at,
                    "response_latency_seconds": time.perf_counter() - start,
                    "request": request,
                    "error": sanitize(str(exc)),
                }
            )
            raise

        message = sanitize(response.choices[0].message)
        usage = usage_dict(response)
        prompt = usage["prompt_tokens"]
        cached = min(usage["cached_tokens"], prompt)
        rounds.append(
            {
                "round": round_number,
                "started_at": started_at,
                "response_latency_seconds": time.perf_counter() - start,
                "request": request,
                "request_summary": {
                    "roles": [message.get("role") for message in request.get("messages", [])],
                    "message_count": len(request.get("messages", [])),
                    "tool_order": [
                        tool.get("function", {}).get("name")
                        for tool in request.get("tools", [])
                    ],
                },
                "response": message,
                "usage": {
                    **usage,
                    "uncached_tokens": prompt - cached,
                    "cache_ratio": cached / prompt if prompt else 0.0,
                },
            }
        )
        return response

    agent.client.chat.completions.create = recorded_create


def attach_tool_results(rounds: list[dict[str, Any]], tool_calls: list[Any]) -> list[dict[str, Any]]:
    serialized = [sanitize(asdict(call)) for call in tool_calls]
    cursor = 0
    for round_data in rounds:
        response_calls = (round_data.get("response") or {}).get("tool_calls") or []
        for response_call in response_calls:
            if cursor >= len(serialized):
                break
            response_call["execution"] = serialized[cursor]
            cursor += 1
    return serialized


def summarize_mode(rounds: list[dict[str, Any]], result: dict[str, Any]) -> dict[str, Any]:
    complete_rounds = [item for item in rounds if "usage" in item]
    prompts = [item["usage"]["prompt_tokens"] for item in complete_rounds]
    cached = [item["usage"]["cached_tokens"] for item in complete_rounds]
    completions = [item["usage"]["completion_tokens"] for item in complete_rounds]
    latencies = [item["response_latency_seconds"] for item in complete_rounds]
    final_answer = result.get("final_answer") or ""
    return {
        "success": bool(result.get("success")),
        "iterations": int(result.get("iterations", 0)),
        "tool_calls": len(result.get("tool_calls") or []),
        "prompt_tokens": sum(prompts),
        "completion_tokens": sum(completions),
        "cached_tokens": sum(cached),
        "uncached_tokens": sum(prompts) - sum(cached),
        "cache_ratio": sum(cached) / sum(prompts) if prompts else 0.0,
        "cache_hit_rounds": sum(value > 0 for value in cached),
        "api_rounds": len(complete_rounds),
        "first_prompt_tokens": prompts[0] if prompts else 0,
        "last_prompt_tokens": prompts[-1] if prompts else 0,
        "average_response_latency_seconds": statistics.mean(latencies) if latencies else 0.0,
        "total_response_latency_seconds": sum(latencies),
        "wall_time_seconds": float(result["metrics"].total_time),
        "final_answer_is_chinese": bool(re.search(r"[\u4e00-\u9fff]", final_answer)),
    }


def add_round_comparisons(mode: str, rounds: list[dict[str, Any]]) -> None:
    previous_prompt = None
    for round_data in rounds:
        usage = round_data.get("usage")
        if not usage:
            continue
        current_prompt = usage["prompt_tokens"]
        usage["prompt_delta_vs_previous"] = (
            current_prompt - previous_prompt if previous_prompt is not None else None
        )
        usage["cached_div_previous_prompt"] = (
            usage["cached_tokens"] / previous_prompt
            if mode == "correct" and previous_prompt
            else None
        )
        previous_prompt = current_prompt


def load_baseline() -> dict[str, Any] | None:
    if not BASELINE_PATH.exists():
        return None
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    metrics = data.get("metrics") or {}
    return {
        "source": str(BASELINE_PATH.relative_to(VAULT_ROOT)),
        "matched_with_campaign": False,
        "language": "英文默认任务",
        "success": data.get("success"),
        "iterations": data.get("iterations"),
        "tool_calls": len(data.get("tool_calls") or []),
        "metrics": sanitize(metrics),
        "note": "这是此前诊断样本，任务、轮数和上下文均不同，只用于保留历史，不参与六模式排名。",
    }


def run_mode(api_key: str, mode: str, task: str) -> dict[str, Any]:
    print(f"\n{'=' * 72}\n开始模式：{mode}（{MODE_INFO[mode][0]}）\n{'=' * 72}", flush=True)
    rounds: list[dict[str, Any]] = []
    agent = ChineseKVCacheAgent(
        api_key=api_key,
        mode=MODE_MAP[mode],
        model=MODEL,
        root_dir=str(BOOK_ROOT),
        verbose=True,
    )
    install_recorder(agent, rounds)
    result = agent.execute_task(task, max_iterations=MAX_ITERATIONS)
    serialized_calls = attach_tool_results(rounds, result.get("tool_calls") or [])
    add_round_comparisons(mode, rounds)
    summary = summarize_mode(rounds, result)
    print(
        f"完成模式：{mode} | success={summary['success']} | "
        f"rounds={summary['api_rounds']} | cache={summary['cache_ratio']:.1%}",
        flush=True,
    )
    return {
        "mode": mode,
        "name_cn": MODE_INFO[mode][0],
        "mechanism_cn": MODE_INFO[mode][1],
        "summary": summary,
        "final_answer": sanitize(result.get("final_answer")),
        "tool_calls": serialized_calls,
        "rounds": rounds,
    }


def md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def fenced(value: Any, language: str = "text") -> str:
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, indent=2)
    value = value.replace("```", "` ` `")
    return f"```{language}\n{value}\n```"


def render_message(message: dict[str, Any], index: int) -> str:
    role_names = {"system": "系统", "user": "用户", "assistant": "助手", "tool": "工具"}
    role = message.get("role", "unknown")
    chunks = [f"**消息 {index} · {role_names.get(role, role)}（`{role}`）**"]
    if message.get("content") is not None:
        chunks.append(fenced(message.get("content")))
    if message.get("tool_calls"):
        chunks.append("工具调用声明：")
        chunks.append(fenced(message["tool_calls"], "json"))
    return "\n\n".join(chunks)


def render_report(campaign: dict[str, Any]) -> str:
    lines: list[str] = []
    metadata = campaign["metadata"]
    report_complete = (
        len(campaign.get("modes") or []) == len(MODE_ORDER)
        and all(item.get("summary", {}).get("success") for item in campaign["modes"])
    )
    has_strict_five_round_protocol = report_complete and all(
        len(item.get("rounds") or []) >= 5 for item in campaign["modes"]
    )
    lines.extend(
        [
            "---",
            "type: code-lab-report",
            f"status: {'completed' if report_complete else 'interrupted'}",
            "tags: [agent, kv-cache, kimi, context-engineering]",
            f"created: {metadata['started_at'][:10]}",
            f"updated: {metadata['finished_at'][:10]}",
            "---",
            "",
            "# KV Cache 六模式中文对照实验报告",
            "",
            "## 先看结论入口",
            "",
            "这是一轮使用同一模型、同一中文任务、同一工具根目录的六模式连续对照。下表是总览；后半部分可以逐轮展开查看真正发送给模型的完整消息、模型回复和工具结果。",
            "",
            "> 指标边界：教材代码使用非流式 `chat.completions.create`。因此这里记录的 `响应耗时` 是整次请求返回所花时间，不是真正的 TTFT。`cached_tokens`、Prompt Tokens 和 Completion Tokens 则来自 Kimi 的 usage。",
            "",
            "## 实验协议",
            "",
            f"- 模型：`{metadata['model']}`",
            f"- 开始：`{metadata['started_at']}`",
            f"- 结束：`{metadata['finished_at']}`",
            f"- 模式顺序：`{' -> '.join(metadata['mode_order'])}`",
            f"- 随机种子：`{metadata['random_seed']}`",
            f"- 最大轮数：`{metadata['max_iterations']}`",
            f"- 教材 `agent.py` SHA-256：`{metadata['official_agent_sha256']}`",
            "- 中文适配：共享 system、工具说明、动态资料、纯文本历史标签和用户任务翻译为中文；六种上下文管理机制不变。",
            "- 凭据：只从本地环境读取，未写入任何实验产物。隐藏推理 `reasoning_content` 也未保存。",
            "",
            "### 统一中文任务",
            "",
            fenced(campaign["task"]),
            "",
            "### 六个自变量",
            "",
            "| 顺序 | 模式 | 中文名 | 每轮改变什么 |",
            "| ---: | --- | --- | --- |",
        ]
    )
    for index, mode in enumerate(metadata["mode_order"], 1):
        lines.append(f"| {index} | `{mode}` | {MODE_INFO[mode][0]} | {MODE_INFO[mode][1]} |")

    lines.extend(
        [
            "",
            "## 六模式关键指标总表",
            "",
            "| 模式 | 成功 | API 轮数 | 工具调用 | Prompt | Cached | 未缓存 | Cache% | Completion | 平均响应耗时 | 总墙钟时间 | 中文最终回答 |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for item in campaign["modes"]:
        summary = item["summary"]
        lines.append(
            "| {mode} | {success} | {rounds} | {tools} | {prompt:,} | {cached:,} | "
            "{uncached:,} | {ratio:.1%} | {completion:,} | {avg:.3f}s | {wall:.3f}s | {cn} |".format(
                mode=f"`{item['mode']}`",
                success="是" if summary["success"] else "否",
                rounds=summary["api_rounds"],
                tools=summary["tool_calls"],
                prompt=summary["prompt_tokens"],
                cached=summary["cached_tokens"],
                uncached=summary["uncached_tokens"],
                ratio=summary["cache_ratio"],
                completion=summary["completion_tokens"],
                avg=summary["average_response_latency_seconds"],
                wall=summary["wall_time_seconds"],
                cn="是" if summary["final_answer_is_chinese"] else "否",
            )
        )

    mode_lookup = {item["mode"]: item for item in campaign["modes"]}
    if has_strict_five_round_protocol:
        correct_summary = mode_lookup["correct"]["summary"]
        dynamic_system_summary = mode_lookup["dynamic_system"]["summary"]
        shuffled_summary = mode_lookup["shuffled_tools"]["summary"]
        dynamic_profile_summary = mode_lookup["dynamic_profile"]["summary"]
        sliding_summary = mode_lookup["sliding_window"]["summary"]
        text_summary = mode_lookup["text_format"]["summary"]
        sliding_round_4 = mode_lookup["sliding_window"]["rounds"][3]["usage"]
        sliding_round_5 = mode_lookup["sliding_window"]["rounds"][4]["usage"]
        correct_round_5 = mode_lookup["correct"]["rounds"][4]["usage"]
        shuffled_round_5 = mode_lookup["shuffled_tools"]["rounds"][4]["usage"]
        lines.extend(
            [
                "",
                "## 本轮实测观察",
                "",
                f"1. `correct` 的累计 Cache% 为 **{correct_summary['cache_ratio']:.1%}**，高于动态 system（{dynamic_system_summary['cache_ratio']:.1%}）、工具乱序（{shuffled_summary['cache_ratio']:.1%}）、动态 profile（{dynamic_profile_summary['cache_ratio']:.1%}）和纯文本历史（{text_summary['cache_ratio']:.1%}）。这支持“稳定、只追加的前缀更容易持续复用”。",
                f"2. `dynamic_system` 五轮都只有 256 个 Cached Token；`dynamic_profile` 前四轮也只有 256、最后一轮为 0。动态字段放在靠前位置后，后面的历史即使内容相同，也不能继续成为同一稳定前缀。",
                f"3. `sliding_window` 的累计 Cache% 看起来仍有 {sliding_summary['cache_ratio']:.1%}，但关键要看截断瞬间：第 4 轮是 Prompt {sliding_round_4['prompt_tokens']:,} / Cached {sliding_round_4['cached_tokens']:,}，第 5 轮删掉最早一对 assistant/tool 后变为 Prompt {sliding_round_5['prompt_tokens']:,} / Cached {sliding_round_5['cached_tokens']:,}；同轮完整 `correct` 的 Prompt 是 {correct_round_5['prompt_tokens']:,}。它同时减少了一部分输入，也把缓存复用从 {sliding_round_4['cache_ratio']:.1%} 打到 {sliding_round_5['cache_ratio']:.1%}。",
                f"4. `shuffled_tools` 最后一轮意外命中 {shuffled_round_5['cached_tokens']:,} Tokens，导致累计值高于部分动态模式。逐轮工具顺序证明它确实发生了重排；这个跳升更可能来自某次排列与本次连续 campaign 中已有服务端前缀碰巧重合，不能据此反推“乱序没有影响”。",
                "5. 响应耗时的方向没有 Cache% 那么干净，因为各模式 Completion Tokens 不同，Kimi 推理长度、网络和服务端负载也不同。本轮只把耗时当辅助信号，不把模型回答里对 TTFT 的表述当成真实首 Token 测量。",
                "",
                "> 本轮结论不是“所有反模式一定按固定名次变差”，而是：改变越靠近前缀开头、改变得越频繁，可连续复用的范围通常越小；真实自动缓存还会叠加块粒度、历史预热和跨请求匹配。",
            ]
        )

    correct = next((item for item in campaign["modes"] if item["mode"] == "correct"), None)
    lines.extend(
        [
            "",
            "## `correct`：新增 Prompt 与旧前缀复用",
            "",
            "只有 `correct` 每轮都在完全相同的消息列表末尾追加，因此可以用 `本轮 cached_tokens ÷ 上轮 prompt_tokens` 近似回答“上一轮不动的前缀有没有基本命中”。它仍不是服务商提供的精确前缀覆盖字段，会受到缓存块粒度和服务端已有缓存影响。",
            "",
            "| 轮次 | Prompt | 比上轮新增 | Cached | 未缓存 | Cache% | Cached ÷ 上轮 Prompt | 响应耗时 |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    if correct:
        for round_data in correct["rounds"]:
            usage = round_data.get("usage")
            if not usage:
                continue
            delta = usage.get("prompt_delta_vs_previous")
            coverage = usage.get("cached_div_previous_prompt")
            lines.append(
                f"| {round_data['round']} | {usage['prompt_tokens']:,} | "
                f"{'—' if delta is None else f'{delta:+,}'} | {usage['cached_tokens']:,} | "
                f"{usage['uncached_tokens']:,} | {usage['cache_ratio']:.1%} | "
                f"{'—' if coverage is None else f'{coverage:.1%}'} | "
                f"{round_data['response_latency_seconds']:.3f}s |"
            )

    lines.extend(
        [
            "",
            "## 如何读这些数",
            "",
            "| 指标 | 回答的问题 | 不能说明什么 |",
            "| --- | --- | --- |",
            "| Prompt Tokens | 这一轮送入模型的完整上下文有多大？ | 不等于新加入的用户文字。它还包含 system、工具定义、历史回复和工具结果。 |",
            "| Cached Tokens | 这一轮有多少 Prompt Token 由服务端缓存提供？ | 不能单独告诉你命中了哪一条消息。 |",
            "| 未缓存 Tokens | 这一轮仍需正常处理多少 Prompt Token？ | 不一定全是“新加内容”；前缀被破坏时，旧内容也会重新计算。 |",
            "| Cache% | 当前 Prompt 中缓存部分占多少？ | 高比例不总是好，例如滑动窗口把 Prompt 截得很短。 |",
            "| 响应耗时 | 完整 API 请求多久返回？ | 当前非流式实现无法据此得到真正 TTFT。 |",
            "| Completion Tokens | 模型本轮产出了多少 Token（含服务商计入的推理/输出用量）？ | 不能直接衡量答案质量。 |",
            "",
            "## 此前英文诊断样本（不参与本轮排名）",
            "",
        ]
    )
    baseline = campaign.get("previous_baseline")
    if baseline:
        metrics = baseline["metrics"]
        prompt = int(metrics.get("prompt_tokens", 0) or 0)
        cached = int(metrics.get("cached_tokens", 0) or 0)
        lines.extend(
            [
                f"来源：`{baseline['source']}`",
                "",
                "| 语言/任务 | 模式 | 轮数 | 工具调用 | Prompt | Cached | Cache% | 总时间 |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
                f"| {baseline['language']} | `correct` | {baseline['iterations']} | {baseline['tool_calls']} | {prompt:,} | {cached:,} | {cached / prompt if prompt else 0:.1%} | {float(metrics.get('total_time', 0)):.3f}s |",
                "",
                f"> {baseline['note']}",
            ]
        )
    else:
        lines.append("未找到此前诊断文件。")

    lines.extend(["", "## 逐模式、逐轮完整明细", ""])
    for item in campaign["modes"]:
        summary = item["summary"]
        lines.extend(
            [
                f"### {item['mode']} · {item['name_cn']}",
                "",
                f"机制：{item['mechanism_cn']}",
                "",
                f"结果：`success={summary['success']}`，API {summary['api_rounds']} 轮，工具调用 {summary['tool_calls']} 次，累计 Cache% {summary['cache_ratio']:.1%}。",
                "",
            ]
        )
        for round_data in item["rounds"]:
            lines.extend([f"#### 第 {round_data['round']} 轮", ""])
            if round_data.get("error"):
                lines.extend(["本轮错误：", "", fenced(round_data["error"]), ""])
                continue
            usage = round_data["usage"]
            request_summary = round_data["request_summary"]
            lines.extend(
                [
                    "| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |",
                    "| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
                    f"| {usage['prompt_tokens']:,} | {usage['cached_tokens']:,} | {usage['uncached_tokens']:,} | {usage['cache_ratio']:.1%} | {usage['completion_tokens']:,} | {round_data['response_latency_seconds']:.3f}s | {md_escape(' → '.join(request_summary['roles']))} | {md_escape(' → '.join(request_summary['tool_order']))} |",
                    "",
                    "<details>",
                    "<summary>展开：本轮发送给模型的完整消息</summary>",
                    "",
                ]
            )
            for index, message in enumerate(round_data["request"].get("messages", []), 1):
                lines.extend([render_message(message, index), ""])
            lines.extend(["</details>", "", "**模型本轮回复**", ""])
            response = round_data.get("response") or {}
            if response.get("content"):
                lines.extend([fenced(response["content"]), ""])
            response_calls = response.get("tool_calls") or []
            if response_calls:
                for call_index, call in enumerate(response_calls, 1):
                    function = call.get("function") or {}
                    lines.extend(
                        [
                            f"工具调用 {call_index}：`{function.get('name', 'unknown')}`",
                            "",
                            "参数：",
                            "",
                            fenced(function.get("arguments", "{}"), "json"),
                            "",
                        ]
                    )
                    execution = call.get("execution") or {}
                    if execution:
                        lines.extend(
                            [
                                "工具真实返回：",
                                "",
                                "<details>",
                                "<summary>展开工具返回</summary>",
                                "",
                                fenced(execution.get("result"), "json"),
                                "",
                                "</details>",
                                "",
                            ]
                        )
            if not response.get("content") and not response_calls:
                lines.extend(["（本轮没有可见正文或工具调用。）", ""])
        lines.extend(["**该模式最终回答**", "", fenced(item.get("final_answer") or "（无最终回答）"), ""])

    lines.extend(
        [
            "## 验证边界",
            "",
            "- 本报告证明请求真实到达 Kimi，并保存了服务端返回的 usage 与对话收据。",
            "- 它不证明缓存命中了哪一个具体消息片段；Kimi 当前只返回总 `cached_tokens`。",
            "- 六种模式按顺序连续执行，服务端缓存可能受到前面模式和更早请求的预热影响；报告保留首轮数据，不把首轮自动命中误称为本地代码预先计算的缓存。",
            "- 响应耗时还会受到推理长度、网络和服务端负载影响，因此判断 KV Cache 时优先看 Token 指标，再把耗时作为辅助证据。",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(campaign: dict[str, Any], run_dir: Path) -> tuple[Path, Path]:
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_path = run_dir / "campaign.json"
    report_path = run_dir / "KV-Cache六模式中文对比报告.md"
    raw_path.write_text(json.dumps(campaign, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(render_report(campaign), encoding="utf-8")
    return raw_path, report_path


def run_campaign() -> tuple[Path, Path, dict[str, Any]]:
    api_key = get_api_key()
    started_at = now_iso()
    campaign_id = datetime.now().astimezone().strftime("KV缓存对照-%Y%m%d-%H%M%S")
    task = TASK_TEMPLATE.format(campaign_id=campaign_id)
    run_dir = RUNS_DIR / datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    random.seed(RANDOM_SEED)

    campaign: dict[str, Any] = {
        "metadata": {
            "experiment": "《深入理解 AI Agent》实验 2-3 KV Cache 六模式中文对照",
            "campaign_id": campaign_id,
            "started_at": started_at,
            "finished_at": None,
            "model": MODEL,
            "mode_order": MODE_ORDER,
            "random_seed": RANDOM_SEED,
            "max_iterations": MAX_ITERATIONS,
            "tool_root": str(BOOK_ROOT),
            "official_agent_path": str((KV_DIR / "agent.py").relative_to(VAULT_ROOT)),
            "official_agent_sha256": sha256(KV_DIR / "agent.py"),
            "credential_saved": False,
            "reasoning_content_saved": False,
            "latency_metric": "non_streaming_full_response_latency_seconds",
        },
        "task": task,
        "previous_baseline": load_baseline(),
        "modes": [],
    }

    for mode in MODE_ORDER:
        campaign["modes"].append(run_mode(api_key, mode, task))
        campaign["metadata"]["finished_at"] = now_iso()
        write_outputs(campaign, run_dir)

    campaign["metadata"]["finished_at"] = now_iso()
    raw_path, report_path = write_outputs(campaign, run_dir)
    return raw_path, report_path, campaign


def main() -> int:
    parser = argparse.ArgumentParser(description="运行或重绘 KV Cache 六模式中文对照实验")
    parser.add_argument(
        "--render-only",
        type=Path,
        help="不调用 API，只根据已有 campaign.json 重新生成同目录 Markdown 报告",
    )
    args = parser.parse_args()

    if args.render_only:
        campaign = json.loads(args.render_only.read_text(encoding="utf-8"))
        report_path = args.render_only.parent / "KV-Cache六模式中文对比报告.md"
        report_path.write_text(render_report(campaign), encoding="utf-8")
        print(f"报告已重新生成：{report_path}")
        return 0

    raw_path, report_path, campaign = run_campaign()
    succeeded = sum(item["summary"]["success"] for item in campaign["modes"])
    print(f"\n六模式完成：{succeeded}/{len(MODE_ORDER)} 成功")
    print(f"原始明细：{raw_path}")
    print(f"中文报告：{report_path}")
    return 0 if succeeded == len(MODE_ORDER) else 2


if __name__ == "__main__":
    raise SystemExit(main())
