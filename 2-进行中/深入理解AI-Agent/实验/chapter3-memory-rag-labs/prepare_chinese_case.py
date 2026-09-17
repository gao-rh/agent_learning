#!/usr/bin/env python3
"""Create a fixed Chinese teaching copy of one official Chapter 3 YAML case."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

import local_memory_walkthrough as walkthrough


LAB_DIR = Path(__file__).resolve().parent
DEFAULT_SOURCE = (
    walkthrough.CASES_DIR / "layer3" / "01_travel_coordination.yaml"
)
DEFAULT_OUTPUT = LAB_DIR / "cases_zh" / "layer3" / "01_travel_coordination.yaml"
DEFAULT_RECEIPT = LAB_DIR / "results" / "translation" / "layer3_01_travel_coordination.json"
DEFAULT_CACHE = LAB_DIR / "results" / "translation" / "layer3_01_travel_coordination.cache.json"


def translate_object(client: Any, model: str, payload: Any, label: str) -> tuple[Any, dict[str, Any]]:
    messages = [
        {
            "role": "system",
            "content": (
                "你是技术基准数据的严格翻译员。将 JSON 中所有供人阅读的英文文本"
                "翻译为简体中文，但不得添加、删除、总结或纠正原文。必须原样保留"
                "JSON 结构、字段名、role 值、ID、时间戳、人名、航班号、预订号、"
                "证件号、会员号、卡号、电话、邮箱、地址编号、金额、日期和所有数字。"
                "原文若存在矛盾或事实问题，必须忠实保留，不要替它修正。"
                "只返回 JSON。"
            ),
        },
        {
            "role": "user",
            "content": f"翻译区块：{label}\n\n{json.dumps(payload, ensure_ascii=False)}",
        },
    ]
    raw, receipt = walkthrough.chat("kimi", client, model, messages, json_mode=True)
    return json.loads(raw), receipt


def flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return "\n".join(flatten_text(item) for item in value.values())
    if isinstance(value, list):
        return "\n".join(flatten_text(item) for item in value)
    return str(value)


def numeric_tokens(value: Any) -> set[str]:
    # Punctuation belongs to a numeric token only when followed by another digit.
    # This keeps 12/26, 2-3 and 25,000 intact without treating sentence-final
    # punctuation in "130." as part of the number.
    return set(re.findall(r"\d+(?:[,:./-]\d+)*", flatten_text(value)))


def validate_translation(source: dict[str, Any], translated: dict[str, Any]) -> None:
    source_histories = source["conversation_histories"]
    translated_histories = translated["conversation_histories"]
    if len(source_histories) != len(translated_histories):
        raise RuntimeError("translation changed the number of sessions")

    for index, (before, after) in enumerate(zip(source_histories, translated_histories), start=1):
        if before["conversation_id"] != after["conversation_id"]:
            raise RuntimeError(f"session {index} conversation_id changed")
        if before["timestamp"] != after["timestamp"]:
            raise RuntimeError(f"session {index} timestamp changed")
        before_messages = before["messages"]
        after_messages = after["messages"]
        if len(before_messages) != len(after_messages):
            raise RuntimeError(f"session {index} message count changed")
        if [item["role"] for item in before_messages] != [item["role"] for item in after_messages]:
            raise RuntimeError(f"session {index} role sequence changed")

    source_numbers = numeric_tokens(source)
    translated_numbers = numeric_tokens(translated)
    missing_numbers = []
    for token in sorted(source_numbers - translated_numbers):
        # Natural Chinese renders short ranges such as 15-22 as "15 日至 22 日".
        range_match = re.fullmatch(r"(\d{1,2})-(\d{1,2})", token)
        if range_match and all(part in translated_numbers for part in range_match.groups()):
            continue
        missing_numbers.append(token)
    if missing_numbers:
        raise RuntimeError(f"translation lost numeric tokens: {missing_numbers}")

    translated_text = flatten_text(translated)
    source_text = flatten_text(source)
    # Preserve identifiers generically instead of hard-coding one teaching case.
    # This catches mixed letter/digit IDs such as FS-447291, VINs and emails;
    # plain numeric values are already covered by numeric_tokens().
    critical_literals = sorted(
        set(re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", source_text))
        | {
            token
            for token in re.findall(r"\b[A-Za-z0-9][A-Za-z0-9-]{3,}\b", source_text)
            if re.search(r"[A-Z]", token) and re.search(r"\d", token)
        }
    )
    missing = [value for value in critical_literals if value not in translated_text]
    if missing:
        raise RuntimeError(f"translation lost critical literals: {missing}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="生成固定中文教学案例")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--model", default="kimi-k2.6")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source = yaml.safe_load(args.source.read_text(encoding="utf-8"))
    client = walkthrough.create_client("kimi", "", walkthrough.KIMI_ENDPOINT)
    cache = {"translations": {}, "receipts": {}}
    if args.cache.is_file():
        cache = json.loads(args.cache.read_text(encoding="utf-8"))

    def cached_translation(payload: Any, label: str) -> Any:
        if label in cache["translations"]:
            return cache["translations"][label]
        translated_block, block_receipt = translate_object(client, args.model, payload, label)
        cache["translations"][label] = translated_block
        cache["receipts"][label] = block_receipt
        args.cache.parent.mkdir(parents=True, exist_ok=True)
        args.cache.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return translated_block

    top_payload = {
        "title": source["title"],
        "description": source["description"],
        "user_question": source["user_question"],
        "evaluation_criteria": source["evaluation_criteria"],
        "expected_behavior": source.get("expected_behavior", ""),
    }
    translated_top = cached_translation(top_payload, "top-level")

    translated_histories = []
    for index, history in enumerate(source["conversation_histories"], start=1):
        translated_history = cached_translation(history, f"session-{index}")
        translated_histories.append(translated_history)

    translated = {
        "test_id": source["test_id"],
        "category": source["category"],
        "title": translated_top["title"],
        "description": translated_top["description"],
        "language": "zh-CN",
        "translation_status": "kimi-k2.6-translated-and-mechanically-verified",
        "translated_from": str(args.source),
        "conversation_histories": translated_histories,
        "user_question": translated_top["user_question"],
        "evaluation_criteria": translated_top["evaluation_criteria"],
        "expected_behavior": translated_top["expected_behavior"],
    }
    validate_translation(source, translated)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        yaml.safe_dump(translated, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(
        json.dumps(
            {
                "source": str(args.source),
                "output": str(args.output),
                "model": args.model,
                "validation": "passed",
                "receipts": [
                    {"block": label, **cache["receipts"][label]}
                    for label in (
                        "top-level",
                        *(f"session-{index}" for index in range(1, len(translated_histories) + 1)),
                    )
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"READY: {args.output}")
    message_counts = ",".join(str(len(item["messages"])) for item in translated_histories)
    print(f"sessions={len(translated_histories)} messages={message_counts} validation=passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
