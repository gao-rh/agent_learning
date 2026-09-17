#!/usr/bin/env python3
"""Export one four-mode memory campaign as readable Markdown documents."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


LAB_DIR = Path(__file__).resolve().parent
MODES = ("notes", "enhanced_notes", "json_cards", "advanced_json_cards")
MODE_LABELS = {
    "notes": "Notes（原子事实笔记）",
    "enhanced_notes": "Enhanced Notes（上下文段落）",
    "json_cards": "JSON Cards（分层键值卡）",
    "advanced_json_cards": "Advanced JSON Cards（带来源与状态的完整卡片）",
}
MODE_FILENAMES = {
    "notes": "01-notes.md",
    "enhanced_notes": "02-enhanced-notes.md",
    "json_cards": "03-json-cards.md",
    "advanced_json_cards": "04-advanced-json-cards.md",
}

CORE_AUDIT = {
    "notes": {
        "护照到期风险": ("✓", "日期和返程后 27 天均正确"),
        "立即加急续期": ("△", "只说‘如时间允许，考虑’，行动强度不足"),
        "更新达美预订": ("✗", "只有联系达美确认政策，没有要求用新护照号码更新 DELTA-JMK892"),
        "Priority Pass": ("✓", "提醒设置数字卡"),
        "AmEx/Chase 保险限制": ("△", "识别机票不受 Chase 保障，但扩大成‘整个行程不覆盖’"),
    },
    "enhanced_notes": {
        "护照到期风险": ("✓", "日期、返程日和缓冲期均正确"),
        "立即加急续期": ("✓", "明确建议本周立即提交，且保留 2–3 周"),
        "更新达美预订": ("✓", "含 DELTA-JMK892、新护照号码和 72 小时窗口"),
        "Priority Pass": ("✓", "提醒启用应用内数字卡"),
        "AmEx/Chase 保险限制": ("△", "没有明确说明 Chase 不覆盖机票，反而无依据地称公司负责机票保障"),
    },
    "json_cards": {
        "护照到期风险": ("△", "到期日和 27 天正确，但把更新预订的 72 小时错绑成续护照截止日"),
        "立即加急续期": ("△", "要求立即紧急续签，但没有给出原文中的 2–3 周，且夸大时间压力"),
        "更新达美预订": ("✗", "未要求拿到新护照后更新 DELTA-JMK892"),
        "Priority Pass": ("✓", "提醒下载数字卡"),
        "AmEx/Chase 保险限制": ("✓", "正确区分机票与其他用 Chase 支付的旅行开支"),
    },
    "advanced_json_cards": {
        "护照到期风险": ("✓", "护照到期日和约一个月缓冲正确"),
        "立即加急续期": ("✓", "明确立即加急并给出 2–3 周"),
        "更新达美预订": ("△", "提到新护照到手后更新机票，但航班记忆已丢失，未给确认号和 72 小时窗口"),
        "Priority Pass": ("✗", "信用卡会话没有写进记忆"),
        "AmEx/Chase 保险限制": ("✗", "信用卡会话没有写进记忆"),
    },
}

SOURCE_AUDIT = {
    "notes": "未通过：新增‘护照更新证明/紧急旅行文件’这一无来源备选，并把 11 月下旬到 1 月中旬的 2–3 周加急说成赶不上；保险范围也被扩大。",
    "enhanced_notes": "最佳但不是干净通过：核心行动覆盖最完整；不过‘羽田机场可用 Priority Pass’和‘机票保障由公司负责’均无原文依据，同模型 Judge 漏检。",
    "json_cards": "未通过：把‘起飞前 72 小时可更新达美预订中的护照号’错绑成‘续护照截止日’，又把风险升级为 Delta 很可能拒绝登机。",
    "advanced_json_cards": "未通过：M2、M3 没有吸收航班和信用卡会话，最终自然漏掉 DELTA-JMK892、Priority Pass 和保险限制。",
}


def scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).replace("\n", " ")


def render_tree(value: Any, indent: int = 0) -> list[str]:
    prefix = "  " * indent
    lines: list[str] = []
    if isinstance(value, dict):
        if not value:
            return [f"{prefix}- （空对象）"]
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}- **{key}**")
                lines.extend(render_tree(item, indent + 1))
            else:
                lines.append(f"{prefix}- **{key}**：{scalar(item)}")
        return lines
    if isinstance(value, list):
        if not value:
            return [f"{prefix}- （空列表）"]
        for index, item in enumerate(value, start=1):
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}- **记忆项 {index}**")
                lines.extend(render_tree(item, indent + 1))
            else:
                lines.append(f"{prefix}- {scalar(item)}")
        return lines
    return [f"{prefix}- {scalar(value)}"]


def render_conversation(history: dict[str, Any]) -> list[str]:
    lines = [
        f"- 对话编号：`{history.get('conversation_id', '')}`",
        f"- 时间：`{history.get('timestamp', '')}`",
        f"- 消息数：{len(history.get('messages', []))}",
        "",
    ]
    for message in history.get("messages", []):
        role = "用户" if message.get("role") == "user" else "助手"
        lines.append(f"**{role}：** {message.get('content', '')}")
        lines.append("")
    return lines


def usage(receipt: dict[str, Any] | None) -> tuple[int, float]:
    if not receipt:
        return 0, 0.0
    raw_usage = receipt.get("usage") or {}
    tokens = int(raw_usage.get("total_tokens") or 0)
    if not tokens:
        tokens = int(receipt.get("prompt_tokens") or 0) + int(receipt.get("completion_tokens") or 0)
    return tokens, float(receipt.get("latency_seconds") or 0.0)


def mode_metrics(result: dict[str, Any]) -> dict[str, Any]:
    writer_tokens = 0
    writer_latency = 0.0
    memory_chars = []
    for state in result["memory_states"]:
        tokens, latency = usage(state.get("receipt"))
        writer_tokens += tokens
        writer_latency += latency
        memory_chars.append(len(json.dumps(state["memory"], ensure_ascii=False)))
    answer_tokens, answer_latency = usage(result.get("answer_receipt"))
    judge_tokens, judge_latency = usage(result.get("judge_receipt"))
    return {
        "writer_tokens": writer_tokens,
        "answer_tokens": answer_tokens,
        "judge_tokens": judge_tokens,
        "total_tokens": writer_tokens + answer_tokens + judge_tokens,
        "writer_latency": writer_latency,
        "answer_latency": answer_latency,
        "judge_latency": judge_latency,
        "total_latency": writer_latency + answer_latency + judge_latency,
        "memory_chars": memory_chars,
    }


def render_judge(result: dict[str, Any]) -> list[str]:
    judge = result.get("judge") or {}
    raw = result.get("judge_raw") or {}
    lines = [
        f"- 是否通过核心维度：**{'Yes' if judge.get('passed') else 'No'}**",
        f"- 奖励值：`{judge.get('reward')}`",
        f"- 幻觉一票否决：`{judge.get('hallucination_veto')}`",
        "",
        "| 维度 | 分数 | Judge 理由 |",
        "| --- | ---: | --- |",
    ]
    labels = {"precision": "精确性", "recall": "召回度", "reasoning": "推理", "proactivity": "主动性"}
    for name in ("precision", "recall", "reasoning", "proactivity"):
        detail = (raw.get("dimensions") or {}).get(name) or {}
        reason = str(detail.get("reasoning", "")).replace("\n", " ")
        score = (judge.get("scores") or {}).get(name, detail.get("score", ""))
        lines.append(f"| {labels[name]} | {score} | {reason} |")
    hallucination = raw.get("hallucination") or {}
    if hallucination.get("claims"):
        lines.extend(["", "**Judge 标记的无依据事实：**"])
        lines.extend(f"- {claim}" for claim in hallucination["claims"])
    lines.extend(["", f"**总体理由：** {raw.get('overall_reasoning', '')}"])
    return lines


def render_mode_document(
    mode: str,
    case: dict[str, Any],
    result: dict[str, Any],
) -> str:
    metrics = mode_metrics(result)
    lines = [
        f"# {MODE_LABELS[mode]}：三会话完整记录",
        "",
        "> 证据等级：中文受控教学实验。Writer、Answerer 和 Judge 都使用 Kimi K2.6，因此 Judge 仅是按官方规则的参考分，不是独立官方验收。",
        "",
        "## 实验设置",
        "",
        f"- 用例：`{case['test_id']}`",
        f"- 记忆方式：`{mode}`",
        f"- 会话数：{len(case['conversation_histories'])}",
        "- 链路：`M0 + H1 → M1；M1 + H2 → M2；M2 + H3 → M3；M3 + Q → A`",
        "- 隔离规则：后续 Writer 只获得上一版记忆和当前新会话，不重放更早原始会话。",
        "",
    ]
    for index, history in enumerate(case["conversation_histories"], start=1):
        lines.extend([f"## 会话 {index}：{history.get('conversation_id', '')}", ""])
        lines.extend(render_conversation(history))
        lines.extend([f"## 会话 {index} 后的完整记忆 M{index}", ""])
        lines.extend(render_tree(result["memory_states"][index - 1]["memory"]))
        receipt = result["memory_states"][index - 1].get("receipt") or {}
        tokens, latency = usage(receipt)
        lines.extend(["", f"Writer 调用：`{tokens} tokens`，`{latency:.3f}s`。", ""])

    lines.extend(
        [
            "## 全新会话中的最终问题",
            "",
            f"> {case['user_question']}",
            "",
            "## Agent 最终回答",
            "",
            result.get("answer", ""),
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
    lines.extend(
        [
            "",
            "## 人工逐源核对核心行动",
            "",
            "| 核心行动 | 结论 | 说明 |",
            "| --- | --- | --- |",
        ]
    )
    for label, (status, note) in CORE_AUDIT[mode].items():
        lines.append(f"| {label} | {status} | {note} |")
    lines.extend(["", f"**逐源结论：** {SOURCE_AUDIT[mode]}"])
    lines.extend(
        [
            "",
            "## 调用成本与延迟",
            "",
            f"- Writer 三轮：`{metrics['writer_tokens']} tokens`，`{metrics['writer_latency']:.3f}s`",
            f"- Answerer：`{metrics['answer_tokens']} tokens`，`{metrics['answer_latency']:.3f}s`",
            f"- Judge：`{metrics['judge_tokens']} tokens`，`{metrics['judge_latency']:.3f}s`",
            f"- 合计：`{metrics['total_tokens']} tokens`，`{metrics['total_latency']:.3f}s`",
            f"- M1/M2/M3 字符数：`{' / '.join(str(value) for value in metrics['memory_chars'])}`",
            "",
        ]
    )
    return "\n".join(lines)


def render_comparison(
    case: dict[str, Any],
    results: dict[str, dict[str, Any]],
) -> str:
    lines = [
        "# 三会话案例：四种记忆方式对比报告",
        "",
        "> 这是同一个 Layer 3 案例上的四臂受控教学对比。不是 60 例完整官方 campaign。",
        "",
        "## 四份完整记录",
        "",
    ]
    for mode in MODES:
        lines.append(f"- [{MODE_LABELS[mode]}]({MODE_FILENAMES[mode]})")
    lines.extend(
        [
            "",
            "## 官方如何评估",
            "",
            "- `precision`：人名、数字、日期、所属对象和关系是否精确。",
            "- `recall`：回答当前问题所需的关键信息是否齐全。",
            "- `reasoning`：是否正确处理跨会话联系、时间、归属和冲突。",
            "- `proactivity`：是否给出有用且有依据的下一步建议或风险提醒。",
            "- `hallucination veto`：任何实质性无依据/矛盾事实使整体奖励归零。",
            "- 核心通过条件：无幻觉，且 precision、recall、reasoning 均不低于 3 分；proactivity 作为诊断维度。",
            "",
            "## 实测结果",
            "",
            "| 记忆方式 | 精确 | 召回 | 推理 | 主动 | 幻觉否决 | 通过 | M3字符 | 总Token | 总延迟(s) |",
            "| --- | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: |",
        ]
    )
    metrics_by_mode = {}
    for mode in MODES:
        result = results[mode]
        metrics = mode_metrics(result)
        metrics_by_mode[mode] = metrics
        judge = result.get("judge") or {}
        scores = judge.get("scores") or {}
        lines.append(
            f"| {MODE_LABELS[mode]} | {scores.get('precision', '')} | {scores.get('recall', '')} | "
            f"{scores.get('reasoning', '')} | {scores.get('proactivity', '')} | "
            f"{'Yes' if judge.get('hallucination_veto') else 'No'} | "
            f"{'Yes' if judge.get('passed') else 'No'} | {metrics['memory_chars'][-1]} | "
            f"{metrics['total_tokens']} | {metrics['total_latency']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## 最终回答的人工逐源核对",
            "",
            "> `✓` = 正确完成；`△` = 提到但不完整或夹带错误；`✗` = 遗漏。这里核对的是官方期望的五项核心行动，不是关键词匹配。",
            "",
            "| 记忆方式 | 护照到期风险 | 立即加急续期 | 更新达美预订 | Priority Pass | AmEx/Chase保险 |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for mode in MODES:
        marks = [status for status, _ in CORE_AUDIT[mode].values()]
        lines.append(f"| {MODE_LABELS[mode]} | {' | '.join(marks)} |")
    lines.extend(["", "### 逐条结论", ""])
    for mode in MODES:
        lines.append(f"- **{MODE_LABELS[mode]}**：{SOURCE_AUDIT[mode]}")
    lines.extend(
        [
            "",
            "## 记忆本身怎么变",
            "",
            "| 方式 | 实际生成结构 | M1 → M2 → M3 | 信息保留 | 主要失败形态 |",
            "| --- | --- | --- | --- | --- |",
            "| Notes | 对象数组；每项含 entity / attribute / value / date / source / session_id | 60 → 118 → 167 条；M3 32,582 字符 | 三轮核心事实大多仍在 | 模型把‘原子笔记’实现成了字段齐全的小对象，不做价值取舍、状态爆炸；答案又从冗余事实中推出无来源备选 |",
            "| Enhanced Notes | 上下文段落字符串数组 | 8 → 10 → 13 段；M3 2,872 字符 | 三轮核心事实保留最好 | 段落会捆绑多个事实；最终回答仍能越过记忆自行补出无来源内容 |",
            "| JSON Cards | 一个层级对象，按 identity / travel / credit_cards 等类别嵌套 | M3 为 6 个顶层类别；6,508 字符 | 三轮信息基本都在 | 字段命名造成语义错绑：`passport_update_deadline` 被理解成续护照截止日；还写入了不存在的公司刷卡政策 |",
            "| Advanced JSON Cards | 卡片数组；每张含 category / card_key / backstory / person / relationship / timestamp / status / facts | 始终 2 张卡；M3 2,414 字符 | 只保留第一轮护照信息 | 后两轮 Writer 原样返回旧卡，结构完整但发生整轮漏记 |",
            "",
            "这里最关键的分离是：**记忆里有没有事实**，和 **Answerer 有没有正确使用事实**，是两个不同的能力。Enhanced Notes 的保险限制已经在 M3 中，最终回答却没有正确表达；JSON Cards 的 72 小时事实也在 M3 中，但字段归属使 Answerer 用错了。",
        ]
    )
    lines.extend(
        [
            "",
            "## 实验标准内部冲突",
            "",
            "权威对话原文说护照加急处理是 **2–3 周**；评估标准却要求回答“即使加急也需要 **5–7 周**”。"
            "Judge 又被要求只以原对话为权威来源。因此这一时间数字不应用来区分四种记忆方式的优劣。",
            "",
            "## 简要分析",
            "",
            "1. **本例最好的表示是 Enhanced Notes，但没有任何一条链路得到人工意义上的干净通过。** 它以约 Notes 的十一分之一 M3 字符数保住了三轮核心信息，官方规则 Judge 给了 4/4/4/4；人工核对仍发现两处无来源补充。",
            "2. **结构越复杂不等于记忆越好。** Advanced Cards 有来源、状态等字段，却把后两轮整轮漏掉；JSON Cards 保住了事实，却把 72 小时绑定给了错误动作。Schema 只能约束形状，不能保证抽取和使用语义。",
            "3. **Notes 的问题正是你刚才指出的：它更像全量会话索引，不像经过价值判断的长期记忆。** 167 条、3.26 万字符让噪声和成本同步增长，本例总 Token 也是 Enhanced Notes 的约 2.9 倍。",
            "4. **官方评估直接看最终回答，而不直接奖励‘记忆长得漂亮’。** 所以应同时做两种诊断：先看 M1/M2/M3 的事实生存与归属，再看最终回答的精确、召回、推理和主动性。只看总分定位不了错误发生在哪一层。",
            "5. **同模型 Judge 不能当最终裁判。** 它给 Enhanced Notes 满分却漏检无来源陈述；它还在 Advanced Cards 的回答中指控了实际不存在的‘5–7 周’。这些分数仅用于复现官方评分流程。",
            "",
            "隐私保护没有列入本次主评估：官方这一案例的核心标准就是最终问答的 precision、recall、reasoning、proactivity 与幻觉否决。本报告只保留实验边界说明，不额外给隐私打分。",
            "",
            "## 证据边界",
            "",
            "- 四种方式使用同一中文案例、同一 Kimi K2.6 Writer/Answerer/Judge，因此适合做内部对照。",
            "- 中文翻译会改变 Token 和模型难度，不能与官方英文 campaign 直接比分。",
            "- Judge 与 Writer/Answerer 使用同一模型，不算独立 Judge；分数只是按官方规则的参考结果。",
            "- 只跑了一个 Layer 3 案例，不能推广到官方三层 60 例。",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="导出四种记忆方式的 Markdown 全记录")
    parser.add_argument(
        "--case",
        type=Path,
        default=LAB_DIR / "cases_zh" / "layer3" / "01_travel_coordination.yaml",
    )
    parser.add_argument("--results-dir", type=Path, default=LAB_DIR / "results")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=LAB_DIR / "reports" / "layer3_01_travel_coordination-zh",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    case = yaml.safe_load(args.case.read_text(encoding="utf-8"))
    results = {}
    for mode in MODES:
        path = args.results_dir / f"{case['test_id']}--{mode}--zh.json"
        results[mode] = json.loads(path.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for mode in MODES:
        output = args.output_dir / MODE_FILENAMES[mode]
        output.write_text(render_mode_document(mode, case, results[mode]) + "\n", encoding="utf-8")
    comparison = args.output_dir / "00-四种记忆方式对比报告.md"
    comparison.write_text(render_comparison(case, results) + "\n", encoding="utf-8")
    print(f"READY: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
