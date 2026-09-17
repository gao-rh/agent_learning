import json

from business_analysis_repro.metric_tools import get_metric_definition, get_metric_value
from business_analysis_repro.tool_calling_demo import execute_tool_call


def test_get_metric_value_returns_fixed_synthetic_value() -> None:
    result = get_metric_value.invoke({"metric_name": "保费收入", "date": "2026-08-01"})

    assert result == {
        "status": "ok",
        "metric_id": "premium_income",
        "metric_name": "保费收入",
        "date": "2026-08-01",
        "value": 128000.00,
        "unit": "元",
        "data_source": "synthetic_local_data",
    }


def test_get_metric_definition_returns_fixed_definition() -> None:
    result = get_metric_definition.invoke({"metric_name": "保费"})

    assert result["status"] == "ok"
    assert result["definition"] == "指定日期内成功承保订单对应的保费金额合计"


def test_unknown_date_is_explicitly_reported() -> None:
    result = get_metric_value.invoke({"metric_name": "保费收入", "date": "2026-08-02"})

    assert result["status"] == "not_found"
    assert result["available_dates"] == ["2026-08-01"]


def test_execute_tool_call_preserves_call_id_and_serializes_result() -> None:
    tool_message = execute_tool_call(
        {
            "name": "get_metric_value",
            "args": {"metric_name": "保费收入", "date": "2026-08-01"},
            "id": "call_test_001",
            "type": "tool_call",
        }
    )

    assert tool_message.name == "get_metric_value"
    assert tool_message.tool_call_id == "call_test_001"
    assert json.loads(str(tool_message.content))["value"] == 128000.00
