"""把固定实验资料生成为人阅读的手册；手册含标准答案，绝不作为模型输入。"""

import json
from pathlib import Path

from .knowledge import FIXTURES, load_public


def build():
    catalog = load_public("catalog.json")
    cases = load_public("cases.json")["cases"]
    rubrics = json.loads((FIXTURES / "rubrics.private.json").read_text())["cases"]
    records = load_public("knowledge.json")["records"]
    records += load_public("knowledge_with_definition.json")["records"]
    metrics = {m["id"]: m for m in catalog["metrics"]}
    dimensions = catalog["dimensions"]
    labels = {"ready": "直接形成语义任务", "clarify": "向用户澄清", "unsupported": "说明能力边界"}
    lines = ["# 澄清实验：案例与知识手册", "",
        "> 2026-09-29 · ID、目录和新增定义均为合成实验配置，不作为生产知识。本文含固定回复和标准答案，不能整篇放入被测模型上下文。真实模型尚未运行。", "",
        "先看十个场景，再核对指标、维度和知识。运行方式见[实验入口](README.md)。", "",
        "## 十个场景总览", "", "| 场景 | 首轮应做什么 | 是否有固定回复 |",
        "| --- | --- | --- |"]
    for case in cases:
        rubric = rubrics[case["id"]]
        lines.append(f"| [{case['title']}](#{case['id']}) | {labels[rubric['first_decision']]} | "
                     + ("有，先人工审阅问题" if rubric["fixed_reply"] else "无") + " |")
    lines += ["", "四个无需询问、五个需要澄清、一个能力边界场景。十个单次运行只用于诊断，不形成稳定准确率。", "",
              "## 逐个场景怎样试", "", "以下‘形成任务’只指语义可表达，执行开关始终关闭，不会得到业务数字。"]

    def date_label(value):
        return value["start"] if value["start"] == value["end"] else value["start"] + " 至 " + value["end"]

    for case in cases:
        rubric = rubrics[case["id"]]
        lines += ["", f'<a id="{case["id"]}"></a>', f"### {case['title']}", "",
                  f"命令中使用的场景名：`{case['id']}`。", "", "**前文：**", ""]
        for message in case["history"]:
            lines.append("- " + ("用户：" if message["role"] == "user" else "助手：") + message["content"])
        if not case["history"]:
            lines.append("无前文，每次从独立会话开始。")
        condition = "基础目录与7条模拟知识"
        if case["knowledge_profile"] == "with_definition":
            condition += "，额外开放一条有版本的业务映射"
        lines += ["", "**本轮输入：** " + case["question"], "", "**可用知识：** " + condition + "。",
                  "", "**预期行为：** " + labels[rubric["first_decision"]]]  # 这里只供审阅者阅读
        if rubric["question_topics"]:
            lines += ["", "应覆盖的实质问题：" + "；".join(rubric["question_topics"]) + "。"]
        if rubric["fixed_reply"]:
            lines += ["", "**预设回复：** " + rubric["fixed_reply"], "",
                      "实际问句覆盖必要歧义后才提供这条回复；漏问时记录遗漏，不用完整回复替模型补救。"]
        if rubric["expected_tasks"]:
            lines += ["", "**最终任务必须保留：**", ""]
        for task in rubric["expected_tasks"]:
            detail = [metrics[task["metric_id"]]["name"], "当期 " + date_label(task["period"])]
            if task["comparison_period"]:
                detail.append("基期 " + date_label(task["comparison_period"]))
            for dimension, values in task["filters"].items():
                names = [next(v["name"] for v in dimensions[dimension]["values"] if v["id"] == value)
                         for value in values]
                detail.append(dimensions[dimension]["name"] + "=" + "、".join(names))
            if not task["filters"]:
                detail.append("无额外筛选")
            detail.append("整体汇总，不分组")
            for predicate in task["required_predicates"]:
                operator = "<>" if predicate["operator"] == "ne" else "="
                detail.append(f"必选 {predicate['field_id']} {operator} {str(predicate['value']).lower()}")
            lines.append("- " + "；".join(detail) + "。")
        if not rubric["expected_tasks"]:
            lines += ["", "保留无人机配送原要求，说明目录不支持；不能丢掉条件后查整体。允许明确说明边界后询问替代方案，不机械按outcome名称判分。"]
        if rubric["required_knowledge_refs"]:
            lines += ["", "须实际取得并引用知识：" + "、".join(rubric["required_knowledge_refs"]) + "。"]
        lines += ["", "研究线索：`" + case["source_case"] + "`，详见原计划。当前问法与对话背景是人工构造。"]

    lines += ["", "## 模拟指标目录", "",
        "不准备业务数值、可执行SQL或线上凭据；查询绑定统一为mock_metadata_only。支持日期为2026-01-01至2026-08-31，基准日2026-09-01。", "",
        "| 指标 | 实验ID | 单位 | 支持维度 |", "| --- | --- | --- | --- |"]
    for metric in metrics.values():
        lines.append(f"| {metric['name']} | `{metric['id']}` | {metric['unit']} | "
                     + "、".join(dimensions[d]["name"] for d in metric["dimensions"]) + " |")
    for metric in metrics.values():
        lines += ["", "### " + metric["name"], "", metric["definition"], "",
                  "别名：" + "、".join(metric["aliases"]) + "。"]
    lines += ["", "## 维度和完整枚举", "", "全局存在某个维度，不代表每个指标都支持。", "",
              "| 维度 | 定义 | 枚举 |", "| --- | --- | --- |"]
    for dimension in dimensions.values():
        lines.append(f"| {dimension['name']} | {dimension['definition']} | "
                     + "、".join(v["name"] for v in dimension["values"]) + " |")
    lines += ["", "原试玩新商按入驻时间，本实验新注册商户按平台注册时间，两套目录不能混用。城市等级和经营类型分别存在；配送枚举中没有无人机，也不以其他值替代它。", "",
              "## 可检索业务知识", "", "版本均为2026-09-29.1，仅对本模拟业务生效；时间窗口2026-01-01至2026-09-01。来源为人工构造。"]
    for record in records:
        lines += ["", "### " + record["title"] + " · " + record["id"], "", record["text"], "",
                  "检索词：" + "、".join(record["terms"]) + "。"]
        if record["id"] == "K-CITY-MAPPING":
            lines += ["", "仅有定义组开放。缺定义组的目录、枚举别名、工具描述和基础知识均无此映射。"]
    lines += ["", "## 审阅与判定", "",
        "先看是否该问，再看问句是否覆盖必要缺项，最后核对回复后有没有丢失指标、时间、人群、否定条件或比较方向。", "",
        "程序的accepted=true仅表示语义契约可接受；exact_task_match=true只表示标准任务的结构匹配。问句清楚、没有不必要追问、依据充分等仍须人工审阅。", "",
        "多指标作用域场景将前文明示为候选口径，避免把已经完全确认的条件人为要求重复澄清。没有改写历史案例。", "",
        "缺知识与能力不支持分别记录；失败原始轨迹保留，不能修改答案后覆盖旧结果。"]
    target = Path(__file__).with_name("案例与知识手册.md")
    target.write_text("\n".join(lines) + "\n")
    return target


if __name__ == "__main__":
    print(build())
