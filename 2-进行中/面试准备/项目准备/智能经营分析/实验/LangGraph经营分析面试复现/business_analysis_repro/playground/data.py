"""可复算的模拟取数和分析；不连接公司平台，不让模型做聚合。

每个指标有两个预设周总量。按其三个合法维度生成小型日粒度立方体，
金额/计数求和；比例和单均值必须先汇总分子分母再除，不能平均每日比率。
"""

import hashlib
import itertools
import json
import sqlite3
from datetime import date, timedelta

from .catalog import DIMENSIONS, METRICS, ClarificationNeeded, enum_name, validate_task
from .run_control import cancellable_query


def distribute(total, weights):
    """整数最大余数分配：切分后仍精确等于预设总量，避免计数出现半个商户。"""
    denominator = sum(weights)
    parts = [total * w // denominator for w in weights]
    order = sorted(range(len(weights)), key=lambda i: -(total * weights[i] % denominator))
    for i in order[: total - sum(parts)]:
        parts[i] += 1
    return parts


def fixture_rows(metric, start, end):
    dims = list(metric["dimensions"])
    combos = list(itertools.product(*metric["dimensions"].values()))
    # 两个层级同时存在时，只生成真实的父子组合。
    combos = [
        c
        for c in combos
        if not {"channel_l1", "channel_l2"}.issubset(dims)
        or c[dims.index("channel_l1")]
        == DIMENSIONS["channel_l2"]["parent_values"][c[dims.index("channel_l2")]]
    ]
    day = start
    while day <= end:
        phase = "current" if day >= date(2026, 8, 24) else "baseline"
        preset = metric["preset"]
        # 周预设可不是7的倍数，按周内日序分配余数，整周依然精确闭合。
        n_week, d_week = preset[phase + "_numerator"], preset[phase + "_denominator"]
        n_day = n_week // 7 + (day.weekday() < n_week % 7)
        d_day = d_week // 7 + (day.weekday() < d_week % 7) if d_week else None
        weights = [
            1 + int(hashlib.sha256((phase + repr(c)).encode()).hexdigest()[:4], 16) % 5
            for c in combos
        ]
        nums = distribute(n_day, weights)
        if d_day is not None:
            # 分母由分子+剩余量组成，保持比例<=100%，且各组权重不同。
            rest = distribute(d_day - n_day, list(reversed(weights))) if d_day >= n_day else None
            dens = (
                [n + r for n, r in zip(nums, rest)]
                if rest is not None
                else distribute(d_day, weights)
            )
        else:
            dens = [0] * len(combos)
        for c, n, denominator in zip(combos, nums, dens):
            yield {
                "metric_id": metric["id"],
                "biz_date": day.isoformat(),
                **dict(zip(dims, c)),
                "numerator": n,
                "denominator": denominator,
            }
        day += timedelta(days=1)


def number(metric, numerator, denominator):
    if metric["aggregation"] == "sum":
        return numerator
    return numerator / denominator * (100 if metric["unit"] == "%" else 1) if denominator else None


def formatted(metric, value, signed=False):
    if value is None:
        return "分母为零，无法计算"
    decimals = 4 if metric["unit"] == "元/单" else 2 if metric["unit"] == "%" else 0
    return format(value, ("+" if signed else "") + f",.{decimals}f") + " " + metric["unit"]


def query_agent(task, trace=None):
    # 下方定义完成后加包装器；直接调用和分析内部调用共用取消机制。
    metric = validate_task(task)
    start, end = date.fromisoformat(task["start_date"]), date.fromisoformat(task["end_date"])
    if start > end or (end - start).days >= 31:
        raise ClarificationNeeded("本地试玩每次支持1至31天，请缩短日期范围。")
    if start < date(2026, 1, 1) or end > min(
        date(2026, 12, 31), date.fromisoformat(task["reference_date"])
    ):
        raise ClarificationNeeded("模拟数据覆盖2026年且不超过日期基准日，请调整日期。")
    rows = list(fixture_rows(METRICS[task["metric_id"]], start, end))
    filters = task.get("filters", {})
    params = {
        "metric_id": metric["id"],
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }
    sql = "SELECT * FROM demo_metric_daily WHERE metric_id=:metric_id AND biz_date BETWEEN :start_date AND :end_date"
    # 列名只能来自指标白名单；枚举始终用绑定参数，不把模型文本拼进SQL。
    for dim, ids in filters.items():
        names = [f"{dim}_{i}" for i in range(len(ids))]
        params.update(zip(names, ids))
        sql += f" AND {dim} IN (" + ",".join(":" + n for n in names) + ")"
    execution = {**metric["query"], "parameters": params, "synthetic": True}
    if execution["method"] == "sql":
        columns = ["metric_id", "biz_date", *metric["dimensions"], "numerator", "denominator"]
        with sqlite3.connect(":memory:") as db:
            db.row_factory = sqlite3.Row
            db.execute("CREATE TABLE demo_metric_daily (" + ",".join(columns) + ")")
            db.executemany(
                "INSERT INTO demo_metric_daily VALUES (" + ",".join("?" for _ in columns) + ")",
                [[r[c] for c in columns] for r in rows],
            )
            rows = [dict(r) for r in db.execute(sql, params)]
        execution.update(executed_sql=sql, execution_status="sqlite_executed")
    else:
        request = {
            **params,
            "filters": filters,
            "dataset_id": execution["dataset_id"],
            "platform_metric_id": execution["platform_metric_id"],
        }
        rows = [r for r in rows if all(r[d] in ids for d, ids in request["filters"].items())]
        execution.update(request=request, execution_status="local_fixture_returned")
    numerator = sum(r["numerator"] for r in rows)
    denominator = sum(r["denominator"] for r in rows)
    total = number(metric, numerator, denominator)
    groups = {}
    for r in rows:
        key = tuple(r[d] for d in task.get("group_by", []))
        pair = groups.setdefault(key, [0, 0])
        pair[0] += r["numerator"]
        pair[1] += r["denominator"]
    breakdown = (
        [
            {
                "dimensions": dict(zip(task.get("group_by", []), key)),
                "numerator": n,
                "denominator": den,
                "value": number(metric, n, den),
            }
            for key, (n, den) in groups.items()
        ]
        if task.get("group_by")
        else []
    )
    facts = {
        "标准指标": metric["name"],
        "指标ID": metric["id"],
        "期间": f"{start} 至 {end}",
        "筛选条件": "；".join(
            DIMENSIONS[d]["name"] + "=" + "/".join(enum_name(d, v) for v in ids)
            for d, ids in filters.items()
        )
        or "全部合法枚举",
        "统计方式": "分子汇总÷分母汇总" if metric["aggregation"] != "sum" else "日计数或金额累计",
        "结果": formatted(metric, total),
    }
    if metric["aggregation"] != "sum":
        facts.update(分子合计=f"{numerator:,}", 分母合计=f"{denominator:,}")
    for g in breakdown:
        label = " / ".join(enum_name(d, v) for d, v in g["dimensions"].items())
        facts[label] = formatted(metric, g["value"])
    return {
        "source": "query",
        "status": "ok",
        "synthetic": True,
        "scope": task.copy(),
        "task_revision": task["revision"],
        "metric_definition": metric,
        "evidence_id": "demo-"
        + hashlib.sha256(json.dumps(task, sort_keys=True).encode()).hexdigest()[:12],
        "facts": facts,
        "total": total,
        "numerator": numerator,
        "denominator": denominator,
        "groups": breakdown,
        "query_execution": execution,
        "checks": {"complete": bool(rows), "row_count": len(rows)},
        "limitations": [
            "全部为人工模拟数据；ID和支持矩阵为本地演示配置。",
            "渠道与分组变化不能证明业务因果。",
        ],
    }


query_agent = cancellable_query(query_agent)


def analysis_agent(task, trace=None):
    days = (date.fromisoformat(task["end_date"]) - date.fromisoformat(task["start_date"])).days + 1
    previous = {
        **task,
        "start_date": (date.fromisoformat(task["start_date"]) - timedelta(days=days)).isoformat(),
        "end_date": (date.fromisoformat(task["start_date"]) - timedelta(days=1)).isoformat(),
    }

    def fetch(spec):
        if trace is None:
            return query_agent(spec)
        trace.check_cancel()
        with trace.span("tool", "analysis.query_agent", spec) as span:
            result = query_agent(spec, trace=trace)
            trace.check_cancel()
            span["result"] = result
            return result

    current, baseline = fetch(task), fetch(previous)
    m = METRICS[task["metric_id"]]
    delta = (
        current["total"] - baseline["total"]
        if current["total"] is not None and baseline["total"] is not None
        else None
    )
    facts = {
        **current["facts"],
        "对比期间": baseline["facts"]["期间"],
        "前期结果": formatted(m, baseline["total"]),
    }
    if m["unit"] == "%":
        facts["变动"] = f"{delta:+.2f} 个百分点" if delta is not None else "无法比较"
    else:
        facts["变动"] = formatted(m, delta, signed=True)
        facts["变动率"] = (
            f"{delta / baseline['total'] * 100:+.2f}%"
            if baseline["total"] and delta is not None
            else "前期为零，无法计算"
        )
    # “按新老商看变化”需要同组前后对比，仅列本期分组不能回答变化问题。
    # 用编码元组对齐两期，避免因为返回顺序变化而配错组。
    baseline_groups = {tuple(sorted(g["dimensions"].items())): g for g in baseline["groups"]}
    for group in current["groups"]:
        old = baseline_groups.get(tuple(sorted(group["dimensions"].items())))
        label = " / ".join(enum_name(d, v) for d, v in group["dimensions"].items())
        old_value = old["value"] if old else None
        change = (
            group["value"] - old_value
            if group["value"] is not None and old_value is not None
            else None
        )
        facts[label + "前期"] = formatted(m, old_value)
        facts[label + "变动"] = (
            (f"{change:+.2f} 个百分点" if change is not None else "无法比较")
            if m["unit"] == "%"
            else formatted(m, change, signed=True)
        )
    return {
        **current,
        "source": "analysis",
        "facts": facts,
        "current": current,
        "baseline": baseline,
        "evidence_id": current["evidence_id"] + "-comparison",
    }
