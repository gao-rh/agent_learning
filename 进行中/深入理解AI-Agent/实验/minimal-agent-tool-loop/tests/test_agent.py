import json

from agent import TOOLS, execute_tool


def test_time_tool_returns_requested_timezone():
    result = json.loads(
        execute_tool("get_current_time", '{"timezone": "Asia/Shanghai"}')
    )
    assert result["timezone"] == "Asia/Shanghai"
    assert result["datetime"]
    assert result["day_of_week"]


def test_time_tool_rejects_unknown_timezone():
    result = json.loads(
        execute_tool("get_current_time", '{"timezone": "Mars/Olympus"}')
    )
    assert "error" in result


def test_invalid_json_becomes_tool_error():
    result = json.loads(execute_tool("get_current_time", "not-json"))
    assert "Invalid tool arguments" in result["error"]


def test_unknown_tool_becomes_tool_error():
    result = json.loads(execute_tool("delete_everything", "{}"))
    assert result == {"error": "Unknown tool: delete_everything"}


def test_tool_schemas_require_arguments():
    schemas = {tool["function"]["name"]: tool["function"] for tool in TOOLS}
    assert schemas["get_current_time"]["parameters"]["required"] == ["timezone"]
    assert schemas["get_weather"]["parameters"]["required"] == ["city", "unit"]

