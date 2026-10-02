"""独立的时间视图小样例：生成模拟保费，并按澄清参数预览结果。

不调用模型，不接入现有实验运行器，不改变历史成绩。
只有可加总金额使用 sum；去重商户数和渗透率不能照搬这个聚合。
"""

import calendar
import json
from datetime import date, timedelta
from pathlib import Path


def preview_time_views(start: str, end: str, views: list[dict]) -> dict:
    """范围包含首尾日期；月份选择对每个自然年分别生效。

    工具接收通用参数，不认识题目编号、险种别名或标准答案。
    示例数据为范围内每天实收保费 100 元，每一行都明确标为模拟。
    """
    lower, upper = date.fromisoformat(start), date.fromisoformat(end)
    if lower > upper:
        raise ValueError("起始日期不能晚于结束日期")
    if (upper - lower).days > 36525:
        raise ValueError("小样例只支持最多约100年的范围")
    facts = [
        {"day": lower + timedelta(days=i), "premium_yuan": 100}
        for i in range((upper - lower).days + 1)
    ]
    outputs = []
    for view in views:
        kind = view["kind"]
        if kind not in {"month", "year", "annual_months"}:
            raise ValueError("只支持按月、按年、每年指定月份累计")
        months = view.get("months", [])
        if kind == "annual_months" and (
            not months or any(type(m) is not int or m not in range(1, 13) for m in months)
        ):
            raise ValueError("累计月份必须是1至12的非空列表")
        buckets = {}
        for row in facts:
            day = row["day"]
            if kind == "annual_months" and day.month not in months:
                continue
            label = day.strftime("%Y-%m") if kind == "month" else str(day.year)
            bucket = buckets.setdefault(label, {"label": label, "amount_yuan": 0, "days": 0})
            bucket["amount_yuan"] += row["premium_yuan"]
            bucket["days"] += 1
            bucket.setdefault("covered_start", day.isoformat())
            bucket["covered_end"] = day.isoformat()
        for bucket in buckets.values():
            year = int(bucket["label"][:4])
            expected_months = ([int(bucket["label"][5:])] if kind == "month" else
                               sorted(set(months)) if kind == "annual_months" else
                               list(range(1, 13)))
            expected_days = sum(calendar.monthrange(year, month)[1] for month in expected_months)
            bucket["partial"] = bucket["days"] < expected_days
        outputs.append({"view": view, "rows": list(buckets.values())})
    return {"synthetic": True, "period": {"start": start, "end": end},
            "fact_rows": len(facts), "data_rule": "范围内每日模拟实收保费100元",
            "outputs": outputs}


def main():
    result = preview_time_views("2021-01-01", "2026-08-31", [
        {"kind": "month"}, {"kind": "year"},
        {"kind": "annual_months", "months": list(range(1, 8))},
    ])
    monthly, yearly, selected = [entry["rows"] for entry in result["outputs"]]
    # 检查跨年、闰年、末年不足整年，以及同一份事实的聚合一致性。
    assert result["fact_rows"] == 2069
    assert [len(monthly), len(yearly), len(selected)] == [68, 6, 6]
    assert sum(row["amount_yuan"] for row in monthly) == sum(row["amount_yuan"] for row in yearly)
    assert next(row for row in monthly if row["label"] == "2024-02")["amount_yuan"] == 2900
    assert yearly[-1]["amount_yuan"] == 24300 and yearly[-1]["partial"]
    assert selected[-1]["amount_yuan"] == 21200 and not selected[-1]["partial"]
    # 指定月份不必连续，不能错误地把2月一起算进1月和3月。
    discontinuous = preview_time_views("2026-01-01", "2026-03-31", [
        {"kind": "annual_months", "months": [1, 3]},
    ])
    assert discontinuous["outputs"][0]["rows"][0]["amount_yuan"] == 6200
    output = Path(".runs/clarification-document-examples/time-view-preview.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(output), "fact_rows": result["fact_rows"],
                      "output_rows": [len(monthly), len(yearly), len(selected)],
                      "checks": "passed", "model_calls": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
