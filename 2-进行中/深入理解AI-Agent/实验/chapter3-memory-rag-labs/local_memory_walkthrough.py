#!/usr/bin/env python3
"""Interactive walkthrough for Chapter 3 Experiments 3-1 and 3-2.

This is a teaching proxy, not canonical experiment evidence. English mode
reuses the official prompts and YAML cases. Chinese mode uses a fixed reviewed
translation while preserving the official source as provenance. Neither mode
pretends that the same writer/answerer model is an independent judge.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from ollama import Client as OllamaClient
from openai import OpenAI


LAB_DIR = Path(__file__).resolve().parent
TOPIC_DIR = LAB_DIR.parents[1]
BOOK_REPO = TOPIC_DIR / "资料" / "本地资料" / "深入理解AI-Agent"
CHAPTER = BOOK_REPO / "chapter3"
CASES_DIR = CHAPTER / "user-memory-evaluation" / "test_cases"
ZH_CASES_DIR = LAB_DIR / "cases_zh"
OFFICIAL_RUNNER = CHAPTER / "user-memory" / "run_evaluation.py"
MODES = ("notes", "enhanced_notes", "json_cards", "advanced_json_cards")
PROVIDERS = ("kimi", "ollama")
LANGUAGES = ("zh", "en")
DEFAULT_MODELS = {"kimi": "kimi-k2.6", "ollama": "qwen3:0.6b"}
KIMI_ENDPOINT = "https://api.moonshot.cn/v1"
ENV_FILE = LAB_DIR / "secrets" / "keys.env"


def load_official_runner():
    spec = importlib.util.spec_from_file_location("official_ch3_memory_runner", OFFICIAL_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import official runner: {OFFICIAL_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODE_INSTRUCTIONS_ZH = {
    "notes": (
        "将记忆保存为最小、可独立理解的事实笔记数组。把复杂陈述拆成原子事实；"
        "保留精确姓名、标识符和日期。"
    ),
    "enhanced_notes": (
        "将记忆保存为带上下文的段落数组。每个段落必须保留理解该事实所需的"
        "实体、事件、时间、状态和关系。"
    ),
    "json_cards": (
        "将记忆保存为按类别、子类别、键和值组织的分层 JSON 对象。"
        "保留不同实体之间的区分以及历史状态。"
    ),
    "advanced_json_cards": (
        "将记忆保存为卡片数组。每张卡片必须包含 category、card_key、backstory、"
        "person、relationship、timestamp、status 和 facts 对象。遇到冲突指令时，"
        "按时间顺序保留不同版本，不要静默合并。"
    ),
}


def cases_dir(language: str) -> Path:
    return ZH_CASES_DIR if language == "zh" else CASES_DIR


def load_cases(language: str) -> list[dict[str, Any]]:
    cases = []
    for path in sorted(cases_dir(language).glob("layer*/*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["_path"] = str(path)
        cases.append(data)
    return cases


def find_case(test_id: str, language: str) -> dict[str, Any]:
    for case in load_cases(language):
        if case.get("test_id") == test_id:
            return case
    raise ValueError(
        f"unknown {language} test id: {test_id}; use --list --language {language} "
        "to inspect available cases"
    )


def print_case_list(language: str) -> None:
    current_layer = None
    for case in load_cases(language):
        if case["category"] != current_layer:
            current_layer = case["category"]
            print(f"\n{current_layer}")
        print(f"  {case['test_id']}: {case['title']}")


def memory_prompt_zh(
    mode: str,
    memory: Any,
    history: dict[str, Any],
    session_index: int,
) -> list[dict[str, str]]:
    system = (
        "你是一名长期记忆写入器。只选择可能帮助未来助手的事实，但必须保留精确值、"
        "事实所属对象、事件状态、日期、来源和关系。更新记忆时，不得丢失仍然有效的旧事实。"
        "不要回答对话中的问题。只返回 JSON，格式为 {\"memory\": ...}。"
        + MODE_INSTRUCTIONS_ZH[mode]
    )
    lines = [
        f"会话 ID：{history.get('conversation_id', '')}",
        f"时间：{history.get('timestamp', '')}",
    ]
    for message in history.get("messages", []):
        role = "用户" if message.get("role") == "user" else "助手"
        lines.append(f"{role}：{message.get('content', '')}")
    user = (
        f"记忆模式：{mode}\n会话序号：{session_index}\n\n"
        "当前记忆状态（这是从更早会话中保留下来的全部信息）：\n"
        f"{json.dumps(memory, ensure_ascii=False)}\n\n"
        "新会话（分析本次会话，然后生成完整的新记忆状态）：\n"
        + "\n".join(lines)
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def answer_prompt_zh(mode: str, memory: Any, question: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "你是一个处于全新会话中的助手。下面提供的长期记忆是你了解该用户的唯一来源；"
                "你无法访问先前的原始对话。请准确回答，处理歧义，关联不同会话，并主动提醒"
                "重要风险。不得编造事实。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"记忆模式：{mode}\n长期记忆：\n"
                f"{json.dumps(memory, ensure_ascii=False)}\n\n用户问题：\n{question}"
            ),
        },
    ]


def judge_prompt_zh(case: dict[str, Any], answer: str) -> list[dict[str, str]]:
    histories = []
    for history in case["conversation_histories"]:
        lines = [
            f"会话 ID：{history.get('conversation_id', '')}",
            f"时间：{history.get('timestamp', '')}",
        ]
        for message in history.get("messages", []):
            role = "用户" if message.get("role") == "user" else "助手"
            lines.append(f"{role}：{message.get('content', '')}")
        histories.append("\n".join(lines))
    source = "\n\n".join(histories)
    system = (
        "你是记忆助手的严格评审。只能使用权威对话原文作为事实依据。"
        "分别对精确性、召回度、推理和主动性打 1 至 4 分。任何实质性的无依据"
        "或与原文矛盾的事实都触发幻觉一票否决。只返回 JSON。"
    )
    user = f"""权威对话原文：
{source}

问题：{case['user_question']}
待评回答：{answer}
评估标准：{case['evaluation_criteria']}
期望行为：{case.get('expected_behavior', '')}

严格返回：
{{"dimensions": {{"precision": {{"score": 1, "reasoning": "...", "evidence": []}},
"recall": {{"score": 1, "reasoning": "...", "evidence": []}},
"reasoning": {{"score": 1, "reasoning": "...", "evidence": []}},
"proactivity": {{"score": 1, "reasoning": "...", "evidence": []}}}},
"hallucination": {{"detected": false, "claims": [], "reasoning": "..."}},
"overall_reasoning": "..."}}

分数尺度：4 分=完全满足具体标准；3 分=满足核心要求，只有轻微缺陷；
2 分=存在实质性遗漏；1 分=未命中或与核心要求矛盾。若有多个实体都可能
匹配，有针对性地追问澄清是正确行为。
"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def create_client(provider: str, host: str, endpoint: str):
    if provider == "ollama":
        return OllamaClient(host=host)

    load_dotenv(ENV_FILE, override=False)
    api_key = os.getenv("MOONSHOT_API_KEY")
    if not api_key:
        raise RuntimeError(
            f"MOONSHOT_API_KEY is missing. Fill it locally in {ENV_FILE}; "
            "never paste the key into chat."
        )
    return OpenAI(api_key=api_key, base_url=endpoint, timeout=600, max_retries=3)


def chat(
    provider: str,
    client: Any,
    model: str,
    messages: list[dict[str, str]],
    json_mode: bool,
) -> tuple[str, dict[str, Any]]:
    started = time.perf_counter()
    if provider == "ollama":
        response = client.chat(
            model=model,
            messages=messages,
            format="json" if json_mode else None,
            think=False,
            options={"temperature": 0, "seed": 37, "num_ctx": 40960},
        )
        receipt = {
            "provider": provider,
            "model_requested": model,
            "model_returned": response.model,
            "created_at": str(response.created_at),
            "done_reason": response.done_reason,
            "prompt_tokens": response.prompt_eval_count,
            "completion_tokens": response.eval_count,
            "latency_seconds": round(time.perf_counter() - started, 3),
        }
        return response.message.content or "", receipt

    request: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_completion_tokens": 16384 if json_mode else 4096,
    }
    if json_mode:
        request["response_format"] = {"type": "json_object"}
    # K2.6 supports both modes. Disabling hidden reasoning makes this extraction
    # exercise cheaper and easier to reproduce while retaining JSON Mode.
    if model == "kimi-k2.6":
        request["extra_body"] = {"thinking": {"type": "disabled"}}
    response = client.chat.completions.create(**request)
    choice = response.choices[0]
    usage = response.usage.model_dump() if response.usage else {}
    receipt = {
        "provider": provider,
        "request_id": response.id,
        "model_requested": model,
        "model_returned": response.model,
        "created": response.created,
        "finish_reason": choice.finish_reason,
        "usage": usage,
        "latency_seconds": round(time.perf_counter() - started, 3),
    }
    if choice.finish_reason == "length":
        raise RuntimeError(f"{provider} response was truncated at the output-token limit")
    return choice.message.content or "", receipt


def pause(message: str, enabled: bool) -> None:
    if enabled:
        input(f"\n{message}\n写完后按回车继续……")


def print_conversation(history: dict[str, Any]) -> None:
    print("\n--- 当前原始会话 ---")
    for message in history.get("messages", []):
        role = {"user": "用户", "assistant": "助手"}.get(
            str(message.get("role", "")), str(message.get("role", ""))
        )
        print(f"{role}：{message.get('content', '')}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="第 3 章 3-1/3-2 逐轮记忆教学运行器")
    parser.add_argument("--case", help="测试用例 test_id")
    parser.add_argument("--mode", choices=MODES, default="enhanced_notes", help="记忆表示方式")
    parser.add_argument("--provider", choices=PROVIDERS, default="kimi", help="模型提供方")
    parser.add_argument("--model", help="模型名称；默认 Kimi K2.6，Ollama 后备为 qwen3:0.6b")
    parser.add_argument(
        "--language",
        choices=LANGUAGES,
        default="zh",
        help="教学案例与 Prompt 语言；默认中文，英文用于对照官方原始案例",
    )
    parser.add_argument("--host", default="http://127.0.0.1:11434", help="Ollama 地址")
    parser.add_argument("--endpoint", default=KIMI_ENDPOINT, help="Kimi OpenAI-compatible API 地址")
    parser.add_argument("--list", action="store_true", help="列出所选语言已准备的用例后退出")
    parser.add_argument("--check", action="store_true", help="只检查本地模型和官方文件，不运行用例")
    parser.add_argument(
        "--replay-only",
        action="store_true",
        help="只回放完整历史对话，不显示考题、不调用模型",
    )
    parser.add_argument("--show-conversation", action="store_true", help="在每轮打印完整原始会话")
    parser.add_argument("--no-pause", action="store_true", help="关闭预测/观察暂停，仅用于诊断")
    parser.add_argument(
        "--judge",
        action="store_true",
        help="使用官方四维度规则追加一次 Judge；默认与生成模型相同，不算独立验收",
    )
    parser.add_argument("--output", type=Path, help="指定结果 JSON；默认写入实验目录 results/")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.model = args.model or DEFAULT_MODELS[args.provider]
    if args.list:
        print_case_list(args.language)
        return 0

    if not OFFICIAL_RUNNER.is_file() or not CASES_DIR.is_dir():
        raise RuntimeError("official Chapter 3 source is missing; run preflight.py first")

    if args.replay_only:
        if not args.case:
            raise SystemExit("--case is required with --replay-only")
        case = find_case(args.case, args.language)
        print("=" * 72)
        print("对话回放：不显示最终考题和评分标准，不调用模型")
        print(f"用例: {case['test_id']} · {case['title']}")
        print(f"语言: {'中文教学副本' if args.language == 'zh' else '官方英文原文'}")
        print("=" * 72)
        for index, history in enumerate(case["conversation_histories"], start=1):
            print(f"\n### 会话 {index}/{len(case['conversation_histories'])}")
            print(f"对话编号：{history.get('conversation_id')}")
            print(f"时间：{history.get('timestamp')}")
            print(f"消息数：{len(history.get('messages', []))}")
            print_conversation(history)
        print("\n回放结束。现在先不看考题，请根据未来复用价值判断哪些信息应进入长期记忆。")
        return 0

    # Python HTTP clients may otherwise inherit the macOS system proxy for localhost.
    os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
    os.environ.setdefault("no_proxy", "127.0.0.1,localhost")
    client = create_client(args.provider, args.host, args.endpoint)
    if args.check:
        if args.provider == "ollama":
            model_info = client.show(args.model)
            details = model_info.details
            family = details.get("family", "unknown") if isinstance(details, dict) else details.family
            print(f"model family: {family}")
        else:
            available = {model.id for model in client.models.list().data}
            if args.model not in available:
                raise RuntimeError(
                    f"{args.model} is not returned by the account's model list; "
                    f"available examples: {sorted(available)[:10]}"
                )
        print(f"READY: {args.provider} / {args.model}")
        print(f"official runner: {OFFICIAL_RUNNER}")
        print(f"official English cases: {len(load_cases('en'))}")
        print(f"reviewed Chinese teaching cases: {len(load_cases('zh'))}")
        return 0

    if not args.case:
        raise SystemExit("--case is required unless --list or --check is used")

    official = load_official_runner()
    case = find_case(args.case, args.language)
    interactive = not args.no_pause
    histories = case["conversation_histories"]
    memory = official.initial_memory(args.mode)
    states = []

    print("=" * 72)
    print("受控教学实验：不是官方验收证据，也没有独立 LLM Judge")
    print(f"用例: {case['test_id']} · {case['title']}")
    print(f"层级: {case['category']}  会话数: {len(histories)}  记忆模式: {args.mode}")
    print(f"语言: {'中文教学副本' if args.language == 'zh' else '官方英文原文'}")
    print(f"模型: {args.provider} / {args.model}")
    print(f"原始 YAML: {case['_path']}")
    print("=" * 72)

    for index, history in enumerate(histories, start=1):
        print(f"\n### 会话 {index}/{len(histories)}")
        print(f"conversation_id={history.get('conversation_id')}")
        print(f"timestamp={history.get('timestamp')}")
        print(f"messages={len(history.get('messages', []))}")
        if args.show_conversation:
            print_conversation(history)

        pause(
            "预测：处理本轮后，哪些事实必须进入记忆？哪些旧事实应保留、更新或淘汰？",
            interactive,
        )
        prompt = (
            memory_prompt_zh(args.mode, memory, history, index)
            if args.language == "zh"
            else official.memory_prompt(args.mode, memory, history, index)
        )
        raw, receipt = chat(args.provider, client, args.model, prompt, json_mode=True)
        parsed = official.parse_json(raw)
        memory = parsed.get("memory", parsed)
        state = {
            "session_index": index,
            "conversation_id": history.get("conversation_id"),
            "memory": memory,
            "receipt": receipt,
            "isolation": {
                "prior_raw_histories_supplied": 0,
                "current_memory_supplied": True,
                "new_history_supplied": history.get("conversation_id"),
            },
        }
        states.append(state)
        print("\n--- AI 生成的新记忆状态 ---")
        print(json.dumps(memory, ensure_ascii=False, indent=2))
        pause(
            "观察：先只描述它新增、保留、改写或丢失了什么，不急着评价好坏。",
            interactive,
        )

    print("\n### 全新会话中的最终问题")
    print(case["user_question"])
    pause("预测：只看最终记忆，Agent 应该回答哪些要点？", interactive)
    answer, answer_receipt = chat(
        args.provider,
        client,
        args.model,
        answer_prompt_zh(args.mode, memory, case["user_question"])
        if args.language == "zh"
        else official.answer_prompt(args.mode, memory, case["user_question"]),
        json_mode=False,
    )
    print("\n--- Agent 最终回答 ---")
    print(answer)
    print("\n--- 官方期望行为（回答后才展示）---")
    print(case.get("expected_behavior", ""))
    print("\n--- 官方评估标准 ---")
    print(case.get("evaluation_criteria", ""))

    judge_raw = None
    judge = None
    judge_receipt = None
    if args.judge:
        judge_text, judge_receipt = chat(
            args.provider,
            client,
            args.model,
            judge_prompt_zh(case, answer)
            if args.language == "zh"
            else official.judge_prompt(case, answer),
            json_mode=True,
        )
        judge_raw = official.parse_json(judge_text)
        judge = official.judge_summary(judge_raw)
        print("\n--- 官方规则 Judge 摘要（同模型，非独立）---")
        print(json.dumps(judge, ensure_ascii=False, indent=2))

    result = {
        "evidence_level": "teaching_proxy",
        "canonical_experiment_pass": False,
        "reason": "same model writes memory and answers; no independent external LLM judge",
        "created_at": datetime.now().astimezone().isoformat(),
        "case_source": case["_path"],
        "official_source": case.get("translated_from", case["_path"]),
        "language": args.language,
        "test_id": case["test_id"],
        "layer": case["category"],
        "title": case["title"],
        "mode": args.mode,
        "provider": args.provider,
        "model": args.model,
        "memory_states": states,
        "question": case["user_question"],
        "answer": answer,
        "answer_receipt": answer_receipt,
        "judge_method": "official_four_dimension_rubric_same_model_reference"
        if args.judge
        else None,
        "judge_independent": False if args.judge else None,
        "judge": judge,
        "judge_raw": judge_raw,
        "judge_receipt": judge_receipt,
        "expected_behavior": case.get("expected_behavior"),
        "evaluation_criteria": case.get("evaluation_criteria"),
    }
    output = args.output or LAB_DIR / "results" / (
        f"{case['test_id']}--{args.mode}--{args.language}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n教学结果已保存：{output}")
    print("下一步不是看一个总分，而是逐轮定位事实在哪个 memory state 中丢失或变形。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
