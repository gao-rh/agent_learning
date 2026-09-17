"""Deterministic local tools backed by fully synthetic business data."""

from typing import Any

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

SYNTHETIC_METRICS: dict[str, dict[str, Any]] = {
    "premium_income": {
        "canonical_name": "保费收入",
        "aliases": {"保费收入", "保费", "保费金额", "premium_income"},
        "definition": "指定日期内成功承保订单对应的保费金额合计",
        "unit": "元",
        "values": {"2026-08-01": 128000.00},
    }
}


class MetricValueInput(BaseModel):
    """Arguments accepted by the metric value tool."""

    metric_name: str = Field(description="业务指标名称，例如：保费收入")
    date: str = Field(description="查询日期，格式必须为 YYYY-MM-DD")


class MetricDefinitionInput(BaseModel):
    """Arguments accepted by the metric definition tool."""

    metric_name: str = Field(description="需要查询业务口径的指标名称，例如：保费收入")


def _find_metric(metric_name: str) -> tuple[str, dict[str, Any]] | None:
    normalized_name = metric_name.strip().lower()
    for metric_id, metric in SYNTHETIC_METRICS.items():
        aliases = {str(alias).lower() for alias in metric["aliases"]}
        if normalized_name in aliases:
            return metric_id, metric
    return None


def _not_found(metric_name: str) -> dict[str, Any]:
    return {
        "status": "not_found",
        "metric_name": metric_name,
        "message": "模拟数据中没有这个指标",
        "supported_metrics": [metric["canonical_name"] for metric in SYNTHETIC_METRICS.values()],
    }


@tool(args_schema=MetricValueInput)
def get_metric_value(metric_name: str, date: str) -> dict[str, Any]:
    """查询指定日期的业务指标数值；用户询问具体数值时使用。"""
    match = _find_metric(metric_name)
    if match is None:
        return _not_found(metric_name)

    metric_id, metric = match
    value = metric["values"].get(date)
    if value is None:
        return {
            "status": "not_found",
            "metric_id": metric_id,
            "metric_name": metric["canonical_name"],
            "date": date,
            "message": "模拟数据中没有这个日期的指标值",
            "available_dates": sorted(metric["values"]),
        }

    return {
        "status": "ok",
        "metric_id": metric_id,
        "metric_name": metric["canonical_name"],
        "date": date,
        "value": value,
        "unit": metric["unit"],
        "data_source": "synthetic_local_data",
    }


@tool(args_schema=MetricDefinitionInput)
def get_metric_definition(metric_name: str) -> dict[str, Any]:
    """查询业务指标的定义或统计口径；用户询问指标含义时使用。"""
    match = _find_metric(metric_name)
    if match is None:
        return _not_found(metric_name)

    metric_id, metric = match
    return {
        "status": "ok",
        "metric_id": metric_id,
        "metric_name": metric["canonical_name"],
        "definition": metric["definition"],
        "unit": metric["unit"],
        "data_source": "synthetic_local_data",
    }


TOOLS: tuple[BaseTool, ...] = (get_metric_value, get_metric_definition)
TOOLS_BY_NAME: dict[str, BaseTool] = {registered_tool.name: registered_tool for registered_tool in TOOLS}
