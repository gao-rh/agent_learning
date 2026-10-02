"""简单查数补充集：只检查固定资料、生成审阅文档，不创建模型或运行业务图。"""

import argparse
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

from .contract import validate_submission
from .knowledge import FIXTURES, LabKnowledge


def load_suite():
    public = json.loads((FIXTURES / "simple_query_cases.json").read_text())
    private = json.loads((FIXTURES / "simple_query_rubrics.private.json").read_text())
    return public, private


def check_suite():
    """检查人工标准能否由公开目录表达；通过不等于模型通过用例。"""
    public, private = load_suite()
    cases = public["cases"]
    assert public["suite_id"] == private["suite_id"]
    assert len(cases) == 12 and len({c["id"] for c in cases}) == 12
    counts = Counter(c["category"] for c in cases)
    assert len(counts) == 6 and set(counts.values()) == {2}
    assert set(private["cases"]) == {c["id"] for c in cases}
    assert public["run_plan"]["repetitions_per_case"] == 1
    assert set(public["run_plan"]["initial_smoke_case_ids"]) <= set(private["cases"])
    assert "expected_tasks" not in json.dumps(public)
    knowledge = LabKnowledge()
    user_turns = ready_turns = expected_tasks = 0
    for case in cases:
        assert case["history"] == [] and case["knowledge_profile"] == "base"
        rubric = private["cases"][case["id"]]
        assert len(case["turns"]) == len(rubric["turns"])
        for i, (turn, expected) in enumerate(zip(case["turns"], rubric["turns"])):
            user_turns += 1
            assert turn["user_message"].strip()
            if i == 0:
                assert turn["advance_when"] == "start"
            else:
                previous = rubric["turns"][i-1]["expected_outcome"]
                assert turn["advance_when"] == ("after_clarification_question"
                    if previous == "clarify" else "after_query_completed")
            if expected["expected_outcome"] == "clarify":
                assert expected["must_ask"] and not expected["expected_tasks"]
                continue
            assert expected["expected_outcome"] == "ready" and expected["expected_tasks"]
            ready_turns += 1
            requests = deepcopy(expected["expected_tasks"])
            for request in requests:
                assert request["intent"] == "query" and request["comparison_period"] is None
                period = request["period"]
                request["period"] = {"mode": "range", "start_date": period["start"],
                                     "end_date": period["end"]}
            checked = validate_submission({"outcome": "ready", "requests": requests}, knowledge)
            assert checked["accepted"], (case["id"], i+1, checked["errors"])
            assert checked["normalized_tasks"] == expected["expected_tasks"]
            expected_tasks += len(requests)
    return {"status": "dataset_checked_only", "cases": len(cases),
            "categories": dict(counts), "user_turns": user_turns,
            "ready_turns": ready_turns, "expected_metric_tasks": expected_tasks,
            "model_calls": 0, "queries_executed": 0, "quality_evaluated": False}


def build_handbook():
    stats = check_suite()
    public, private = load_suite()
    knowledge = LabKnowledge()
    lines = ["# 简单查询与多轮追问测试集", "",
        "> 2026-09-29 · 初步测试集 v1 · 本文保存固定输入与标准；已运行完整十二例，八例完整通过、四例未通过，结果见[测试报告](首次试跑结果.md#full-20260930)。指标、维度与口径沿用隔离的合成实验知识。", "",
        "## 范围与规模", "",
        "六类、每类两例，共十二例、二十轮用户输入。每例先运行一次；澄清或续问产生的下一轮属于同一用例，不算重复测试。模型工具循环可能包含多次 API 请求，二十轮不等于二十次模型调用。", "",
        "全部为简单查数：最多三个指标、两个交叉分组，不做同比、归因、报告或开放分析。新增集不自动与原十例打包运行。", "",
        "首次走通建议只选 Q09（两轮澄清补充）和 Q11（四轮查询后修改），各一次，共六轮用户输入。完成并检查实际调用、Token 和费用后，再决定是否跑其余十例；不默认重复两遍。", "",
        "| 类别 | 两个例子 |", "| --- | --- |"]
    categories = list(dict.fromkeys(c["category"] for c in public["cases"]))
    for category in categories:
        links = [f"[{c['title']}](#{c['id'].lower()})" for c in public["cases"] if c["category"] == category]
        lines.append(f"| {category} | " + "；".join(links) + " |")
    lines += ["", "## 运行与判定规则", "",
        "1. 每例建立独立会话；同一例的所有轮次沿用同一会话。只发送当前消息，不能提前让模型看到后续补充。",
        "2. 澄清补充必须等真实问句出现并覆盖必要缺项后再发预设回复；漏问就记录失败，不能靠完整回复把答案补给模型。",
        "3. 查询后追问必须等上一轮模拟查询真实完成并保存任务、结果和回答后再发送。下一轮使用实际会话记录，不能把下方标准任务写成历史，也不能用固定‘已查完’替代完成链路。",
        "4. 若上一轮失败，保留首个偏差，后续标为受前置失败阻断；不能换成标准答案再声称整条链通过。",
        "5. 逐轮核对指标集合、日期、筛选、分组及每指标作用范围。条件新增、替换、撤销、任务切换分别核对；标准任务匹配仍需人工核查问句和程序有没有改写模型原始提交。",
        "6. 查数沿用当前知识约束。总保费不支持渠道、新老商；本集用活跃商户测试新老商，用加入商户测试渠道和来源，避免因用例本身超出能力产生假失败。", "",
        "## 十二个用例", ""]

    def describe_task(task):
        metric = knowledge.metrics[task["metric_id"]]
        period = task["period"]
        parts = [metric["name"], f"{period['start']} 至 {period['end']}"]
        filters = []
        for dim, values in task["filters"].items():
            definition = knowledge.DIMENSIONS[dim]
            names = {v["id"]: v["name"] for v in definition["values"]}
            filters.append(definition["name"] + "=" + "、".join(names[v] for v in values))
        parts.append("筛选：" + ("；".join(filters) if filters else "无额外筛选"))
        groups = [knowledge.DIMENSIONS[d]["name"] for d in task["group_by"]]
        parts.append(("交叉分组：" if len(groups) > 1 else "分组：") + " × ".join(groups)
                     if groups else "整体汇总，不分组")
        if task["required_predicates"]:
            rules = [p["field_id"] + (" <> " if p["operator"] == "ne" else " = ")
                     + str(p["value"]).lower() for p in task["required_predicates"]]
            parts.append("必选规则：" + "、".join(rules))
        return "；".join(parts) + "。"

    gates = {"start": "独立新会话", "after_clarification_question": "上一轮已正确提出澄清问题",
             "after_query_completed": "上一轮已实际查询完成并保存会话"}
    for case in public["cases"]:
        rubric = private["cases"][case["id"]]
        lines += [f'<a id="{case["id"].lower()}"></a>', "", f"### {case['id']} · {case['title']}", "",
                  f"类别：{case['category']}。观察点：{rubric['focus']}", ""]
        for i, (turn, expected) in enumerate(zip(case["turns"], rubric["turns"]), 1):
            lines += [f"**第 {i} 轮｜{gates[turn['advance_when']]}**", "",
                      "> " + turn["user_message"], ""]
            if expected["expected_outcome"] == "clarify":
                lines += ["应询问：" + "；".join(expected["must_ask"]) + "。本轮不取数。", ""]
            else:
                lines += ["应形成以下查数任务，不应再询问已明确条件：", ""]
                lines += ["- " + describe_task(t) for t in expected["expected_tasks"]]
                lines += [""]
            for field, label in [("expected_changes", "本轮改变"), ("must_retain", "必须保留"),
                                 ("forbidden", "典型失败")]:
                if expected[field]:
                    lines += [f"{label}：{expected[field]}", ""]
    lines += ["## 判分记录", "",
        "| 字段 | 记录内容 |", "| --- | --- |",
        "| 用例与轮次 | 用例ID、会话ID、当前轮次、前一轮完成状态 |",
        "| 信息有没有保存 | 实际历史、上一轮结构化任务、结果引用 |",
        "| 信息有没有传入 | 当前模型实际输入，不能只查数据库里有没有历史 |",
        "| 模型有没有正确使用 | 模型原始提交与程序处理后任务分别比较 |",
        "| 条件差异 | 漏指标、多查/错指标、漏/错筛选、漏/错分组、条件绑错指标、旧条件未撤销、日期错 |",
        "| 最早偏差 | 首先偏离预期的轮次及实际证据；下游受阻与独立失败分开 |",
        "| 用量 | 模型请求数、输入输出Token、未知usage；不把一轮聊天当成一次API调用 |", "",
        "支持两种结果：逐轮结果与整例结果。整例通过须所有轮次满足预期；不得把多轮当成互相独立的成功样本来放大通过率。十二例运行器已接入逐字段比对；完整结果另存，不将固定测试集改写为通过记录。", "",
        "## 测试集交付与执行边界", "",
        f"已检查 {stats['cases']} 个用例、{stats['user_turns']} 轮输入；其中 {stats['ready_turns']} 轮的 {stats['expected_metric_tasks']} 项标准任务均能用现有实验目录和语义契约表达。检查不代表模型正确率。", "",
        "- [用户消息与轮次顺序](fixtures/simple_query_cases.json)：给运行器读取；模型只接收当前消息及实际历史，不接收用例标题、类别、运行控制字段或未来轮次。",
        "- [逐轮标准与判定点](fixtures/simple_query_rubrics.private.json)：仅评审器和人工读取，禁止作为模型上下文。",
        "- [基础指标、维度与知识](案例与知识手册.md)：沿用同一目录；无需新增指标或为凑样本放宽支持范围。", "",
        "旧的澄清 run/resume 命令不支持这些 Q 编号。query_smoke 入口已接通十二例需要的九个指标及真实会话保存，整套各跑一次并保留失败；详见[测试报告](首次试跑结果.md#full-20260930)和[运行说明](README.md)。共运行十五轮，五轮受前置失败阻断；不能把未发送的轮次算成已验证。固定 JSON 中 dataset_ready_not_executed 是创建时状态，实际运行状态以独立结果记录为准。原网页及其知识目录未修改。", "",
        "对上轮最高值/某条结果的指代、长对话压缩、服务重启和中途插话暂不放入首批，先把条件继承的短链路走通。", "",
        "离线检查与重建本文（在实验根目录执行，不请求模型）：", "", "```bash",
        ".venv/bin/python -m business_analysis_repro.clarification_lab.simple_query_suite",
        ".venv/bin/python -m business_analysis_repro.clarification_lab.simple_query_suite --build-handbook",
        "```", ""]
    target = Path(__file__).with_name("简单查询与多轮追问测试集.md")
    target.write_text("\n".join(lines))
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="只校验测试集或生成人读文档，不运行模型与查询。")
    parser.add_argument("--build-handbook", action="store_true")
    args = parser.parse_args()
    print(build_handbook() if args.build_handbook else json.dumps(check_suite(), ensure_ascii=False, indent=2))
