# 阅读快照：2026-09-07；保留完整原文件，仅增加讲解注释。
# 原文件：/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/capabilities.py
# 原文件 SHA-256：242a974866933637100ffdd06c4e75fc5c88aa0ca85281bbcc5a9e401e78c808
# 本副本用于阅读，不作为可独立运行的脚本；运行请使用原包的 python -m 入口。
# 搜索“剩余阅读”可定位还没按执行顺序讲完的部分；下文行号均指原文件。
# 配套摘要：../代码阅读摘要.md。注释是 Codex 的源码解读，不代表已验收你的理解。

"""取数 Agent、分析 Agent：这版按用户要求，各封装成一个普通函数。

函数不调用 LLM，也不自行安排下一节点。它们接收标准 task，返回统一结果。
数据完全合成：用于验证编排、计算和追溯，不能当成公司的业务结论。
以后换成 API/真正的 Agent，只要维持这个输入输出契约，父图不必重写。
"""

import hashlib
import json
import sqlite3
from datetime import date, timedelta

from .catalog import BUSINESS_LINES, METRICS, metric_snapshot, query_execution

BUSINESSES = list(BUSINESS_LINES)


class AdmissionError(ValueError):
    """不支持或不允许的请求直接拒绝，不能当成瞬时故障反复重试。"""


# ── 程序准入｜原文件 22–39 行 ──
# 取数与分析都检查本地业务白名单、指标和日期范围。这里尚未接入真实用户权限系统。
def admit(task: dict, allowed_businesses=tuple(BUSINESSES)):
    """代码准入，两个函数均调用。权限来自应用配置，不接受模型自报权限。

    这是本地白名单模拟，尚未对接真实身份认证/权限服务。
    日期上限和数据覆盖检查独立于自然语言理解，防止模型漏写约束。
    """
    if task.get("business") not in BUSINESSES:
        raise AdmissionError("本实验只支持准时保、运费险。")
    if task["business"] not in allowed_businesses:
        raise AdmissionError("当前实验身份没有该业务的查询权限。")
    if task.get("metric") not in METRICS:
        raise AdmissionError("本实验只支持保费收入、保单量。")
    start, end = date.fromisoformat(task["start_date"]), date.fromisoformat(task["end_date"])
    reference = date.fromisoformat(task["reference_date"])
    if start > end or (end - start).days >= 31:
        raise AdmissionError("一次查询需要有效的日期范围，且最多 31 天。")
    if start < date(2026, 1, 1) or end > min(reference, date(2026, 12, 31)):
        raise AdmissionError("模拟数据仅覆盖 2026 年，且不查询基准日之后的数据。")


# ── 证据标识与结果信封｜原文件 42–60 行 ──
# ID 用查询 task 的摘要生成，便于关联任务范围；它不是数据内容校验和或平台签名。
# 统一结果包含 facts、scope、task_revision、evidence_id 等，父图才能用同一规则检查。
def _identity(task, source):
    # 确定性证据 ID 与查询范围绑定，恢复/同参数重查不会伪造一个不同来源。
    raw = json.dumps(task, sort_keys=True, ensure_ascii=False).encode()
    return source + "-" + hashlib.sha256(raw).hexdigest()[:12]


def _result(task, source, facts, **extra):
    return {
        "source": source,
        "status": "ok",
        "synthetic": True,
        "task_revision": task["revision"],
        "evidence_id": _identity(task, source),
        "scope": task.copy(),
        "facts": facts,
        "limitations": ["全部为模拟数据。"],
        "metric_definition": metric_snapshot(task["metric"], task.get("business")),
        **extra,
    }


# ── 模拟业务数据｜原文件 63–86 行 ──
# 数值由固定日期/渠道公式产生。实验验证的是真实代码执行，不是线上经营结论。
def _rows(task):
    """每个日期生成 App/小程序两行，固定公式便于独立计算期望值。

    2026-08-24 起，App 从 6000 降为 4500，小程序从 4000 降为 3500。
    所以上周(08-24~08-30)总额 56,000，相比前一周 70,000 下降 20%。
    数据只体现渠道上的贡献分解，不能证明为什么渠道发生下降。
    """
    day = date.fromisoformat(task["start_date"])
    end = date.fromisoformat(task["end_date"])
    factor = 1 if task["business"] == "准时保" else 2
    rows = []
    while day <= end:
        values = (4500, 3500) if day >= date(2026, 8, 24) else (6000, 4000)
        for channel, value in zip(["App", "小程序"], values, strict=True):
            amount = value * factor
            rows.append(
                {
                    "date": day.isoformat(),
                    "channel": channel,
                    "value": amount if task["metric"] == "premium" else amount // 10,
                }
            )
        day += timedelta(days=1)
    return rows


# ── 取数函数｜原文件 89–158 行 ──
# 输入标准 task → 准入 → 查询配置 → 本地执行 → 检查行数/数值 → 返回事实和明细。
# 没有 LLM；日志里出现 tool 不意味着模型选择了工具。
def query_agent(task: dict, *, allowed_businesses=tuple(BUSINESSES)) -> dict:
    """取数函数：准入 → 合成数据读取 → 完整性检查 → 带来源的结果。"""
    admit(task, allowed_businesses)
    # 查询方式来自指标配置，不接受模型临时编造 dataset_id、表名或 SQL。
    execution = query_execution(task)
    # ── 指标平台模拟分支｜原文件 94–112 行 ──
    # 按配置好的 dataset_id、业务线 ID、平台指标 ID 组装并消费请求参数。
    # 数据由本地函数返回，没有访问公司指标平台。
    if execution["method"] == "metric_platform":
        # 模拟平台也实际消费组装后的请求参数；不能只展示一份未使用的请求。
        params = execution["parameters"]
        if (
            params["dataset_id"] != "demo_ds_insurance_daily"
            or params["metric_id"] != "demo_platform_premium_amount"
        ):
            raise AdmissionError("模拟平台不支持这个数据集与指标组合。")
        by_id = {value: key for key, value in BUSINESS_LINES.items()}
        rows = _rows(
            {
                "business": by_id[params["business_line_id"]],
                "metric": "premium",
                "start_date": params["start_date"],
                "end_date": params["end_date"],
            }
        )
        execution["request"] = execution["parameters"].copy()
        execution["execution_status"] = "local_fixture_returned"
    # ── SQL 分支｜原文件 113–135 行 ──
    # 在 SQLite 内存库建模拟表、装数据、执行参数化模板 SQL。
    # 这是实际 SQL 执行，但这份内存数据库不是保存会话 checkpoint 的文件数据库。
    else:
        # 真正执行参数化 SQL，但库和数据都只在本地。先装载固定合成数据，
        # 再执行配置中的只读模板；用户输入只作为绑定参数，不做 SQL 字符串拼接。
        with sqlite3.connect(":memory:") as db:
            db.row_factory = sqlite3.Row
            db.execute(
                "CREATE TABLE demo_insurance_daily (business_line_id TEXT, "
                "biz_date TEXT, channel TEXT, policy_count INTEGER)"
            )
            seed = _rows(task)
            db.executemany(
                "INSERT INTO demo_insurance_daily VALUES (?, ?, ?, ?)",
                [
                    (BUSINESS_LINES[task["business"]], r["date"], r["channel"], r["value"])
                    for r in seed
                ],
            )
            rows = [
                dict(row)
                for row in db.execute(execution["sql_template"], execution["parameters"]).fetchall()
            ]
        execution["executed_sql"] = execution["sql_template"]
        execution["execution_status"] = "sqlite_executed"
    # ── 结果完整性与汇总｜原文件 136–158 行 ──
    # 检查每天两个渠道、数值非负，再汇总金额/保单量，保存 query_execution。
    # rows 直接放入结果并进入 State；没有写 Excel，也没有结果 ID 对应的外部存储。
    days = (date.fromisoformat(task["end_date"]) - date.fromisoformat(task["start_date"])).days + 1
    # 这里是真检查，不由模型口头宣称“数据完整”。
    if len(rows) != days * 2 or any(row["value"] < 0 for row in rows):
        raise ValueError("模拟数据完整性检查失败。")
    totals = {c: sum(r["value"] for r in rows if r["channel"] == c) for c in ["App", "小程序"]}
    total = sum(totals.values())
    metric = METRICS[task["metric"]]
    return _result(
        task,
        "query",
        {
            "业务": task["business"],
            "标准指标": metric["name"],
            "期间": f"{task['start_date']} 至 {task['end_date']}",
            "合计": f"{total:,} {metric['unit']}",
        },
        total=total,
        totals_by_channel=totals,
        checks={"complete": True, "truncated": False, "row_count": len(rows)},
        # 小样本便于观察，真正大表应落外部存储，State 中保留引用和摘要。
        rows=rows,
        query_execution=execution,
    )


# ── 分析函数｜原文件 161–209 行 ──
# 输入一个标准 task，计算前一等长期间，再顺序查询本期和前期。
# 随后用 Python 算差额、变动率、渠道变化，返回结果给主图。这里没有开放分析循环。
def analysis_agent(task: dict, *, allowed_businesses=tuple(BUSINESSES), trace=None) -> dict:
    """分析函数：本期/前一等长期间取数 → 代码计算差额和渠道贡献。

    本版只做固定的环比与渠道分解，尚未实现开放分析循环。
    内部也调用同一个 query_agent，因此仍然经过相同准入检查。
    """
    admit(task, allowed_businesses)
    start, end = date.fromisoformat(task["start_date"]), date.fromisoformat(task["end_date"])
    days = (end - start).days + 1
    previous = {
        **task,
        "start_date": (start - timedelta(days=days)).isoformat(),
        "end_date": (start - timedelta(days=1)).isoformat(),
    }

    def fetch(spec):
        if trace is None:
            return query_agent(spec, allowed_businesses=allowed_businesses)
        with trace.span("tool", "analysis.query_agent", spec) as span:
            value = query_agent(spec, allowed_businesses=allowed_businesses)
            span["result"] = value
            return value

    # ── 真正执行两次取数｜原文件 184 行 ──
    # Python 先求 fetch(task)，再求 fetch(previous)，因此两次查询是顺序执行。
    current, baseline = fetch(task), fetch(previous)
    # ── 代码负责运算｜原文件 185–209 行 ──
    # 差额=本期-前期；变动率=差额/前期，前期为零时明确无法计算。
    # 主要渠道按绝对变化最大选择，只说明变化集中在哪里，不说明为什么下降。
    # 完整 channel_deltas 保存在结果里，但 facts 只给主要渠道名称；回答模型看的是 facts。
    delta = current["total"] - baseline["total"]
    pct = delta / baseline["total"] * 100 if baseline["total"] else None
    channel_deltas = {
        c: current["totals_by_channel"][c] - baseline["totals_by_channel"][c]
        for c in current["totals_by_channel"]
    }
    main_channel = max(channel_deltas, key=lambda c: abs(channel_deltas[c]))
    facts = {
        **{k: current["facts"][k] for k in ["业务", "标准指标", "期间"]},
        "本期合计": current["facts"]["合计"],
        "对比期间": baseline["facts"]["期间"],
        "前期合计": baseline["facts"]["合计"],
        "变动": f"{delta:+,} {METRICS[task['metric']]['unit']}",
        "变动率": f"{pct:+.1f}%" if pct is not None else "基数为零，无法计算",
        "主要变动渠道": main_channel if delta else "总额没有变化",
    }
    return _result(
        task,
        "analysis",
        facts,
        current=current,
        baseline=baseline,
        channel_deltas=channel_deltas,
        limitations=["全部为模拟数据。", "渠道贡献分解不证明业务因果，需要额外业务证据。"],
    )


# ── 口径查询分支｜原文件 212–217 行 ──
# 只读两个本地指标的名称/定义；尚未实现检索候选、模糊消歧或平台权威口径查询。
def knowledge_lookup(task: dict) -> dict:
    """最小本地知识查询；只解释目录中已定义的两项指标。"""
    if task["metric"] not in METRICS:
        raise AdmissionError("知识目录中没有该指标。")
    item = METRICS[task["metric"]]
    return _result(task, "knowledge", {"标准指标": item["name"], "口径": item["definition"]})
