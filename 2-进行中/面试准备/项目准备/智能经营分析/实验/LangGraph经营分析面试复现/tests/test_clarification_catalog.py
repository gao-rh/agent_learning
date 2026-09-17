from business_analysis_repro.clarification_catalog import (
    DIMENSIONS,
    METRIC_CATALOG,
    find_metric_candidates,
    query_metric,
    query_metric_range,
    resolve_dimension_scope,
    resolve_metric_selection,
)

EXPECTED_METRICS = {
    "timely_delivery_premium_income",
    "cancellation_insurance_premium_income",
    "food_assurance_premium_income",
    "order_penetration_rate",
    "customer_penetration_rate",
}


def test_catalog_has_five_metrics_three_scopes_and_full_august() -> None:
    assert set(METRIC_CATALOG) == EXPECTED_METRICS
    assert set(DIMENSIONS) == {"overall", "merchant", "channel"}

    expected_dates = {f"2026-08-{day:02d}" for day in range(1, 32)}
    for metric in METRIC_CATALOG.values():
        assert set(metric["values"]) == expected_dates
        for daily_values in metric["values"].values():
            assert set(daily_values) == {"overall", "merchant", "channel"}
            assert set(daily_values["merchant"]) == {
                "连锁商家",
                "中小商家",
                "新入驻商家",
            }
            assert set(daily_values["channel"]) == {"App", "API"}


def test_amount_breakdowns_sum_to_overall() -> None:
    for metric in METRIC_CATALOG.values():
        if metric["value_type"] != "amount":
            continue
        for daily_values in metric["values"].values():
            assert round(sum(daily_values["merchant"].values()), 2) == daily_values["overall"]
            assert round(sum(daily_values["channel"].values()), 2) == daily_values["overall"]


def test_metric_aliases_resolve_all_five_metrics() -> None:
    assert find_metric_candidates("准时宝保费收入") == ["timely_delivery_premium_income"]
    assert find_metric_candidates("取消险保费收入") == ["cancellation_insurance_premium_income"]
    assert find_metric_candidates("安心吃保费收入") == ["food_assurance_premium_income"]
    assert find_metric_candidates("订单渗透率") == ["order_penetration_rate"]
    assert find_metric_candidates("客户渗透率") == ["customer_penetration_rate"]
    assert find_metric_candidates("保费") == [
        "timely_delivery_premium_income",
        "food_assurance_premium_income",
        "cancellation_insurance_premium_income",
    ]
    # Collective language is intentionally left to Kimi, not enumerated as local phrases.
    assert resolve_metric_selection("三种 保费") == []


def test_scope_resolution_uses_the_business_dictionary() -> None:
    assert resolve_dimension_scope("App渠道") == ("channel", "App")
    assert resolve_dimension_scope("按商家拆分") == ("merchant", None)
    assert resolve_dimension_scope("连锁商家") == ("merchant", "连锁商家")


def test_query_supports_merchant_channel_and_rate_metrics() -> None:
    merchant_result = query_metric(
        "cancellation_insurance_premium_income",
        "2026-08-15",
        "merchant",
        "连锁商家",
    )
    channel_result = query_metric(
        "food_assurance_premium_income",
        "2026-08-20",
        "channel",
        "API",
    )
    rate_result = query_metric(
        "customer_penetration_rate",
        "2026-08-31",
        "overall",
    )

    assert merchant_result["status"] == "ok"
    assert merchant_result["dimension_value"] == "连锁商家"
    assert merchant_result["value"] > 0
    assert channel_result["status"] == "ok"
    assert channel_result["dimension_value"] == "API"
    assert channel_result["value"] > 0
    assert rate_result["status"] == "ok"
    assert rate_result["unit"] == "%"
    assert 0 < rate_result["value"] < 100


def test_range_query_sums_amounts_and_averages_rates() -> None:
    amount_result = query_metric_range(
        "timely_delivery_premium_income",
        "2026-08-23",
        "2026-08-29",
        "channel",
        "App",
    )
    rate_result = query_metric_range(
        "order_penetration_rate",
        "2026-08-23",
        "2026-08-29",
        "overall",
    )

    assert amount_result["status"] == "ok"
    assert amount_result["day_count"] == 7
    assert amount_result["aggregation"] == "sum"
    assert amount_result["value"] == round(
        sum(item["value"] for item in amount_result["daily_values"]),
        2,
    )
    assert rate_result["status"] == "ok"
    assert rate_result["aggregation"] == "average"
    assert rate_result["value"] == round(
        sum(item["value"] for item in rate_result["daily_values"]) / 7,
        2,
    )
