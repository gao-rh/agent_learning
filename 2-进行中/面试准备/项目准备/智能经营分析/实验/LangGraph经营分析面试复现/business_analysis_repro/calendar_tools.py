"""Deterministic calendar calculation exposed to the clarification agent."""

from calendar import monthrange
from datetime import date, timedelta
from typing import Any, Literal

from langchain.tools import ToolRuntime, tool

PeriodMode = Literal["exact", "calendar", "rolling"]
PeriodUnit = Literal["day", "week", "month", "year"]


def _shift_month(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 + months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def _shift_year(value: date, years: int) -> date:
    day = min(value.day, monthrange(value.year + years, value.month)[1])
    return date(value.year + years, value.month, day)


def calculate_business_period(
    *,
    reference_date: str,
    mode: PeriodMode,
    unit: PeriodUnit,
    offset: int = 0,
    exact_date: str | None = None,
) -> dict[str, Any]:
    """Convert a model-selected time specification into inclusive ISO boundaries."""
    reference = date.fromisoformat(reference_date)

    if mode == "exact":
        if unit != "day" or exact_date is None:
            raise ValueError("exact模式要求unit=day并提供exact_date")
        selected = date.fromisoformat(exact_date)
        start = end = selected
    elif mode == "calendar":
        if exact_date is not None:
            raise ValueError("calendar模式不使用exact_date")
        if unit == "day":
            start = end = reference + timedelta(days=offset)
        elif unit == "week":
            anchor = reference + timedelta(weeks=offset)
            start = anchor - timedelta(days=anchor.weekday())
            end = reference if offset == 0 else start + timedelta(days=6)
        elif unit == "month":
            anchor = _shift_month(reference, offset)
            start = anchor.replace(day=1)
            end = (
                reference
                if offset == 0
                else anchor.replace(day=monthrange(anchor.year, anchor.month)[1])
            )
        else:
            anchor = _shift_year(reference, offset)
            start = date(anchor.year, 1, 1)
            end = reference if offset == 0 else date(anchor.year, 12, 31)
    else:
        if exact_date is not None:
            raise ValueError("rolling模式不使用exact_date")
        if unit == "day":
            end = reference + timedelta(days=offset)
            start = end
        elif unit == "week":
            end = reference + timedelta(weeks=offset)
            start = end - timedelta(days=6)
        elif unit == "month":
            end = _shift_month(reference, offset)
            start = _shift_month(end, -1) + timedelta(days=1)
        else:
            end = _shift_year(reference, offset)
            start = _shift_year(end, -1) + timedelta(days=1)

    return {
        "status": "ok",
        "reference_date": reference_date,
        "mode": mode,
        "unit": unit,
        "offset": offset,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }


@tool
def resolve_business_period(
    mode: PeriodMode,
    unit: PeriodUnit,
    runtime: ToolRuntime,
    offset: int = 0,
    exact_date: str | None = None,
) -> dict[str, Any]:
    """把已经理解出的时间语义换算为闭区间日期。

    用法：calendar 表示日历周期，rolling 表示截至基准日的滚动周期，exact 表示明确日期。
    unit 可为 day/week/month/year，offset=0 表示当前周期，-1 表示上一周期，1 表示下一周期。
    例如“本周”使用 calendar+week+0，“上周”使用 calendar+week-1，
    “近一周”使用 rolling+week+0。不要把用户原话直接作为参数，也不要自行计算起止日期。
    """
    return calculate_business_period(
        reference_date=runtime.state["reference_date"],
        mode=mode,
        unit=unit,
        offset=offset,
        exact_date=exact_date,
    )
