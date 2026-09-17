"""Synthetic metric catalog used by the clarification workflow."""

import re
from datetime import date, timedelta
from typing import Any

from langchain_core.tools import tool

from business_analysis_repro.synthetic_data import (
    build_premium_values,
    build_rate_values,
)

METRIC_CATALOG: dict[str, dict[str, Any]] = {
    "timely_delivery_premium_income": {
        "canonical_name": "准时保保费收入",
        "product_name": "准时保",
        "product_aliases": {"准时保", "准时宝", "B准", "b准"},
        "metric_aliases": {"保费", "保费情况", "保费收入"},
        "definition": "指定日期内准时保成功承保订单对应的保费金额合计",
        "unit": "元",
        "value_type": "amount",
        "values": build_premium_values(
            base=158000.0,
            daily_growth=0.004,
            phase=0,
            total_overrides={"2026-08-28": 186500.0, "2026-08-29": 191200.0},
            channel_overrides={
                "2026-08-28": {"App": 121000.0, "API": 65500.0},
                "2026-08-29": {"App": 124700.0, "API": 66500.0},
            },
        ),
    },
    "cancellation_insurance_premium_income": {
        "canonical_name": "取消险保费收入",
        "product_name": "取消险",
        "product_aliases": {"取消险", "取消保险"},
        "metric_aliases": {"保费", "保费情况", "保费收入"},
        "definition": "指定日期内取消险成功承保订单对应的保费金额合计",
        "unit": "元",
        "value_type": "amount",
        "values": build_premium_values(
            base=96000.0,
            daily_growth=0.0032,
            phase=2,
        ),
    },
    "food_assurance_premium_income": {
        "canonical_name": "安心吃保费收入",
        "product_name": "安心吃",
        "product_aliases": {"安心吃", "食安险"},
        "metric_aliases": {"保费", "保费情况", "保费收入"},
        "definition": "指定日期内安心吃成功承保订单对应的保费金额合计",
        "unit": "元",
        "value_type": "amount",
        "values": build_premium_values(
            base=126000.0,
            daily_growth=0.0036,
            phase=4,
        ),
    },
    "order_penetration_rate": {
        "canonical_name": "订单渗透率",
        "product_name": "整体业务",
        "product_aliases": {"订单", "保单"},
        "metric_aliases": {"渗透率", "订单渗透率"},
        "definition": "指定范围内成功承保订单数除以符合投保条件的订单数",
        "unit": "%",
        "value_type": "rate",
        "values": build_rate_values(base_percent=24.8, daily_change=0.055, phase=1),
    },
    "customer_penetration_rate": {
        "canonical_name": "客户渗透率",
        "product_name": "整体业务",
        "product_aliases": {"客户", "用户"},
        "metric_aliases": {"渗透率", "客户渗透率", "用户渗透率"},
        "definition": "指定范围内发生成功承保行为的客户数除以符合投保条件的客户数",
        "unit": "%",
        "value_type": "rate",
        "values": build_rate_values(base_percent=17.6, daily_change=0.042, phase=3),
    },
}

DIMENSIONS: dict[str, dict[str, Any]] = {
    "overall": {"label": "整体", "aliases": {"整体", "汇总", "总计", "不拆分"}},
    "merchant": {"label": "商家", "aliases": {"商家", "按商家", "分商家"}},
    "channel": {"label": "渠道", "aliases": {"渠道", "按渠道", "分渠道"}},
}

DIMENSION_VALUE_ALIASES: dict[str, dict[str, str]] = {
    "merchant": {
        "连锁商家": "连锁商家",
        "连锁": "连锁商家",
        "中小商家": "中小商家",
        "中小": "中小商家",
        "新入驻商家": "新入驻商家",
        "新商家": "新入驻商家",
    },
    "channel": {
        "app": "App",
        "api": "API",
    },
}


def find_metric_candidates(text: str) -> list[str]:
    """Return catalog metric IDs supported by product and metric words in the text."""
    normalized = text.strip().lower()
    scored: list[tuple[int, str]] = []
    for metric_id, metric in METRIC_CATALOG.items():
        canonical_name = str(metric["canonical_name"]).lower()
        product_match = any(str(alias).lower() in normalized for alias in metric["product_aliases"])
        metric_match = any(str(alias).lower() in normalized for alias in metric["metric_aliases"])
        score = 3 if canonical_name in normalized else int(product_match) + int(metric_match)
        if score > 0:
            scored.append((score, metric_id))
    if not scored:
        return []

    highest_score = max(score for score, _ in scored)
    return [
        metric_id for score, metric_id in sorted(scored, reverse=True) if score == highest_score
    ]


def resolve_metric_selection(text: str) -> list[str]:
    """Resolve metrics explicitly named by product or canonical name, without guessing intent."""
    candidates = find_metric_candidates(text)
    if len(candidates) == 1:
        return candidates
    if not candidates:
        return []

    normalized = re.sub(r"\s+", "", text.strip().lower())
    selected: list[str] = []
    for metric_id in candidates:
        metric = METRIC_CATALOG[metric_id]
        product_is_explicit = any(
            str(alias).lower() in normalized for alias in metric["product_aliases"]
        )
        canonical_is_explicit = str(metric["canonical_name"]).lower() in normalized
        if product_is_explicit or canonical_is_explicit:
            selected.append(metric_id)
    return selected if len(selected) >= 2 else []


def resolve_dimension(text: str) -> str | None:
    normalized = text.strip().lower()
    for dimension_id, dimension in DIMENSIONS.items():
        if any(str(alias).lower() in normalized for alias in dimension["aliases"]):
            return dimension_id
    return None


def resolve_dimension_scope(text: str) -> tuple[str, str | None] | None:
    normalized = text.strip().lower()
    for dimension_id, aliases in DIMENSION_VALUE_ALIASES.items():
        for alias, canonical_value in aliases.items():
            if alias in normalized:
                return dimension_id, canonical_value
    dimension = resolve_dimension(text)
    return (dimension, None) if dimension else None


def query_metric(
    metric_id: str,
    date: str,
    dimension: str,
    dimension_value: str | None = None,
) -> dict[str, Any]:
    metric = METRIC_CATALOG.get(metric_id)
    if metric is None:
        return {"status": "not_found", "message": "模拟目录中不存在该指标"}

    dated_values = metric["values"].get(date)
    if dated_values is None:
        return {
            "status": "not_found",
            "metric_id": metric_id,
            "metric_name": metric["canonical_name"],
            "date": date,
            "message": "模拟目录中不存在该日期的数据",
        }

    value = dated_values.get(dimension)
    if value is None:
        return {
            "status": "not_found",
            "metric_id": metric_id,
            "metric_name": metric["canonical_name"],
            "date": date,
            "dimension": dimension,
            "message": "模拟目录中不支持该查询维度",
        }

    if dimension_value:
        if not isinstance(value, dict) or dimension_value not in value:
            return {
                "status": "not_found",
                "metric_id": metric_id,
                "metric_name": metric["canonical_name"],
                "date": date,
                "dimension": dimension,
                "dimension_value": dimension_value,
                "message": "模拟目录中不存在该维度值",
            }
        value = value[dimension_value]

    return {
        "status": "ok",
        "metric_id": metric_id,
        "metric_name": metric["canonical_name"],
        "date": date,
        "dimension": dimension,
        "dimension_label": DIMENSIONS[dimension]["label"],
        "dimension_value": dimension_value,
        "value": value,
        "unit": metric["unit"],
        "data_source": "synthetic_local_data",
    }


def query_metric_range(
    metric_id: str,
    start_date: str,
    end_date: str,
    dimension: str,
    dimension_value: str | None = None,
) -> dict[str, Any]:
    """Query an inclusive date range and aggregate according to metric value type."""
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError:
        return {"status": "invalid", "message": "日期范围必须使用ISO日期"}
    if start > end:
        return {"status": "invalid", "message": "开始日期不能晚于结束日期"}

    day_count = (end - start).days + 1
    if day_count > 31:
        return {"status": "invalid", "message": "单次模拟查询最多支持31天"}

    daily_results = [
        query_metric(
            metric_id,
            (start + timedelta(days=offset)).isoformat(),
            dimension,
            dimension_value,
        )
        for offset in range(day_count)
    ]
    failed_results = [item for item in daily_results if item["status"] != "ok"]
    if failed_results:
        return {
            "status": "not_found",
            "metric_id": metric_id,
            "start_date": start_date,
            "end_date": end_date,
            "message": "模拟目录中的日期范围数据不完整",
            "failed_dates": [item.get("date") for item in failed_results],
        }

    metric = METRIC_CATALOG[metric_id]
    values = [float(item["value"]) for item in daily_results]
    aggregation = "sum" if metric["value_type"] == "amount" else "average"
    aggregate_value = sum(values) if aggregation == "sum" else sum(values) / len(values)
    first = daily_results[0]
    return {
        "status": "ok",
        "metric_id": metric_id,
        "metric_name": metric["canonical_name"],
        "start_date": start_date,
        "end_date": end_date,
        "day_count": day_count,
        "dimension": dimension,
        "dimension_label": first["dimension_label"],
        "dimension_value": dimension_value,
        "aggregation": aggregation,
        "value": round(aggregate_value, 2),
        "unit": metric["unit"],
        "daily_values": [{"date": item["date"], "value": item["value"]} for item in daily_results],
        "data_source": "synthetic_local_data",
    }


@tool
def query_clarified_metric(
    metric_id: str,
    date: str,
    dimension: str,
    dimension_value: str | None = None,
) -> dict[str, Any]:
    """使用已确认的标准指标ID、日期和维度查询模拟业务数据。"""
    return query_metric(metric_id, date, dimension, dimension_value)


@tool
def query_clarified_metric_range(
    metric_id: str,
    start_date: str,
    end_date: str,
    dimension: str,
    dimension_value: str | None = None,
) -> dict[str, Any]:
    """使用已确认的标准指标ID、起止日期和维度查询模拟业务数据。"""
    return query_metric_range(
        metric_id,
        start_date,
        end_date,
        dimension,
        dimension_value,
    )


def get_metric_knowledge(metric_id: str) -> dict[str, Any]:
    metric = METRIC_CATALOG.get(metric_id)
    if metric is None:
        return {"status": "not_found", "message": "模拟目录中不存在该指标"}
    return {
        "status": "ok",
        "metric_id": metric_id,
        "metric_name": metric["canonical_name"],
        "definition": metric["definition"],
        "unit": metric["unit"],
        "supported_dimensions": [item["label"] for item in DIMENSIONS.values()],
        "data_source": "synthetic_local_data",
    }


@tool
def get_clarified_metric_knowledge(metric_id: str) -> dict[str, Any]:
    """使用已确认的标准指标ID查询模拟指标口径。"""
    return get_metric_knowledge(metric_id)
