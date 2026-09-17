#!/usr/bin/env python3
"""Export one Chapter 3 teaching result as a readable Markdown record."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from export_four_mode_markdown import render_conversation, render_judge, render_tree, usage


LAB_DIR = Path(__file__).resolve().parent


def total_usage(result: dict[str, Any]) -> tuple[int, float, int, float, int, float]:
    writer_tokens = 0
    writer_latency = 0.0
    for state in result["memory_states"]:
        tokens, latency = usage(state.get("receipt"))
        writer_tokens += tokens
        writer_latency += latency
    answer_tokens, answer_latency = usage(result.get("answer_receipt"))
    judge_tokens, judge_latency = usage(result.get("judge_receipt"))
    return (
        writer_tokens,
        writer_latency,
        answer_tokens,
        answer_latency,
        judge_tokens,
        judge_latency,
    )


def multiple_vehicle_analysis() -> list[str]:
    return [
        "## 分层诊断",
        "",
        "| 层次 | 观察 | 结论 |",
        "| --- | --- | --- |",
        "| Writer：M1 | 同时建立 2019 Honda Accord 与 2023 Tesla Model 3 两个实体，并保留各自归属 | 通过多实体写入 |",
        "| Writer：M2 | 明确写入 Honda 的 Firestone 预约，并明确写出 Tesla 本次未预约 | 关键状态与实体绑定正确 |",
        "| Answerer | 分别给出 Honda 已预约和 Tesla 未预约，末尾询问是否协助安排 Tesla | 功能上已经完成消歧；可以更显式，但不存在实质能力缺失 |",
        "| Judge | 精确性 4、召回 3、推理 2、主动性 2，判未通过 | 把话术顺序/措辞偏好误判成召回和推理失败，属于假阴性 |",
        "",
        "### 人工核心要点核对",
        "",
        "- [x] 识别并呈现 2019 Honda Accord。",
        "- [x] 识别并呈现 2023 Tesla Model 3。",
        "- [x] Honda：11 月 24 日上午 8 点，Firestone，30K 套餐，$369.99，确认号 FS-447291。",
        "- [x] Tesla：只讨论过 $29.99 轮胎换位，本次没有预约。",
        "- [x] 回答后询问是否需要为 Tesla 安排服务。",
        "- [x] 通过分别呈现两辆车并询问是否安排 Tesla，功能上处理了‘我的车’的歧义。",
        "- [ ] 可选改进：更显式地说‘您有两辆车’，并直接问‘您准备为哪辆车安排服务？’；这是表达增强，不是通过门槛。",
        "",
        "### 严格结论",
        "",
        "这次不是记忆失败，最终回答也应人工判为通过：两个实体和两种服务状态都存在于 M2；回答先完整呈现 Honda，再单列 Tesla 未预约，最后询问是否协助安排 Tesla，已经以等价方式完成了官方要求的‘呈现两辆车的信息，然后询问’。它没有逐字说‘你有两辆车/你指哪辆’，最多是显式性不足，不能据此把 recall、reasoning 降到 2 分。较合理的人工参考分是 precision 4、recall 4、reasoning 3、proactivity 3，无幻觉，核心通过。",
        "",
        "M1/M2 仍然保留了大量与当前服务问题无关的保险额度、青少年驾驶、网约车和索赔流程。这说明 Enhanced Notes 虽然正确完成实体绑定，但选择性仍不理想；答对多实体题不等于长期记忆已经精简。",
        "",
        "### 案例自身的事实边界",
        "",
        "原案例把 `2024-11-24` 同时称为‘星期五/黑色星期五’，但该日期实际是星期日。教学运行忠实保留案例文字，不用现实日历纠正基准；因此星期几不用于判断本次记忆能力。",
        "",
    ]


def render(case: dict[str, Any], result: dict[str, Any]) -> str:
    mode = result["mode"]
    message_count = sum(len(item["messages"]) for item in case["conversation_histories"])
    lines = [
        "# 3-1 Layer 2：多车辆消歧完整记录与分析",
        "",
        "> 中文受控教学实验。Writer、Answerer 和 Judge 均为 Kimi K2.6；不是独立官方验收。",
        "",
        "## 实验设置",
        "",
        f"- 用例：`{case['test_id']}`",
        f"- 记忆方式：`{mode}`",
        f"- 历史会话：{len(case['conversation_histories'])} 段，共 {message_count} 条消息",
        "- 链路：`M0 + H1 → M1；M1 + H2 → M2；M2 + Q → A`",
        "- 隔离规则：生成 M2 时不回看 H1；最终回答只读取 M2，不读取两段原始会话。",
        "",
        "## 本题可观察通过条件",
        "",
        "1. 同时识别 Honda Accord 与 Tesla Model 3。",
        "2. Honda 有已确认预约，Tesla 没有预约。",
        "3. 给出 Honda 的关键预约信息。",
        "4. 明确处理‘我的车’的歧义，并询问用户准备为哪辆车安排服务。",
        "",
    ]
    for index, history in enumerate(case["conversation_histories"], start=1):
        lines.extend([f"## 会话 {index}：{history['conversation_id']}", ""])
        lines.extend(render_conversation(history))
        lines.extend([f"## 会话 {index} 后的完整记忆 M{index}", ""])
        lines.extend(render_tree(result["memory_states"][index - 1]["memory"]))
        tokens, latency = usage(result["memory_states"][index - 1].get("receipt"))
        lines.extend(["", f"Writer 调用：`{tokens} tokens`，`{latency:.3f}s`。", ""])

    lines.extend(
        [
            "## 全新会话中的最终问题",
            "",
            f"> {case['user_question']}",
            "",
            "## Agent 最终回答",
            "",
            result["answer"],
            "",
            "## 官方期望行为",
            "",
            case.get("expected_behavior", ""),
            "",
            "## 官方评估标准",
            "",
            case.get("evaluation_criteria", ""),
            "",
            "## 官方规则 Judge 结果（同模型参考）",
            "",
        ]
    )
    lines.extend(render_judge(result))
    lines.extend([""] + multiple_vehicle_analysis())
    writer_t, writer_s, answer_t, answer_s, judge_t, judge_s = total_usage(result)
    lines.extend(
        [
            "## 调用成本与延迟",
            "",
            f"- Writer 两轮：`{writer_t} tokens`，`{writer_s:.3f}s`",
            f"- Answerer：`{answer_t} tokens`，`{answer_s:.3f}s`",
            f"- Judge：`{judge_t} tokens`，`{judge_s:.3f}s`",
            f"- 合计：`{writer_t + answer_t + judge_t} tokens`，`{writer_s + answer_s + judge_s:.3f}s`",
            "",
            "## 证据边界",
            "",
            "- 中文翻译改变了语言和 Token，不能与官方英文 campaign 直接比分。",
            "- Judge 与 Writer/Answerer 为同一模型，自动分数不是独立验收。",
            "- 只运行一个 Layer 2 案例，不能推广为该模式的平均能力。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="导出单案例完整 Markdown")
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    case = yaml.safe_load(args.case.read_text(encoding="utf-8"))
    result = json.loads(args.result.read_text(encoding="utf-8"))
    if case["test_id"] != result["test_id"]:
        raise RuntimeError("case/result test_id mismatch")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(case, result) + "\n", encoding="utf-8")
    print(f"READY: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
