"""指标元数据与人类可读回放的契约测试；不发出模型请求。"""

import json

import pytest
from test_main_agent import ScriptedModel, events, proposal, run

from business_analysis_repro.main_agent.capabilities import AdmissionError, query_agent
from business_analysis_repro.main_agent.catalog import METRIC_CATALOG, metric_snapshot
from business_analysis_repro.main_agent.trace_report import report_data


def task(metric):
    return {
        "intent": "query",
        "metric": metric,
        "business": "准时保",
        "start_date": "2026-08-24",
        "end_date": "2026-08-30",
        "reference_date": "2026-09-01",
        "revision": 1,
    }


@pytest.mark.parametrize(
    "metric,method,total", [("premium", "metric_platform", 56000), ("policy_count", "sql", 5600)]
)
def test_query_uses_config_and_carries_actual_execution(metric, method, total):
    result = query_agent(task(metric))
    definition, execution = result["metric_definition"], result["query_execution"]
    assert result["total"] == total
    assert definition["aliases"] and definition["metric_id"].startswith("demo_")
    assert execution["metric_id"] == definition["metric_id"]
    assert execution["method"] == method
    assert execution["parameters"]["business_line_id"] == "demo_biz_timely"
    if method == "sql":
        assert execution["execution_status"] == "sqlite_executed"
        assert "FROM demo_insurance_daily" in execution["executed_sql"]
        assert ":start_date" in execution["executed_sql"]
        assert "2026-08-24" not in execution["executed_sql"]
        assert definition["query"]["dataset_id"] is None
    else:
        assert execution["execution_status"] == "local_fixture_returned"
        assert execution["request"]["dataset_id"] == definition["query"]["dataset_id"]
        assert execution["request"]["metric_id"] == definition["query"]["platform_metric_id"]


def test_snapshot_does_not_change_when_catalog_changes(monkeypatch):
    snapshot = metric_snapshot("premium", "准时保")
    monkeypatch.setitem(METRIC_CATALOG["premium"]["query"], "dataset_id", "changed_after_run")
    assert snapshot["query"]["dataset_id"] == "demo_ds_insurance_daily"


def test_bad_platform_dataset_is_not_silently_ignored(monkeypatch):
    monkeypatch.setitem(METRIC_CATALOG["premium"]["query"], "dataset_id", "wrong-dataset")
    with pytest.raises(AdmissionError, match="数据集与指标组合"):
        query_agent(task("premium"))


def test_sql_permissions_are_checked_before_execution():
    with pytest.raises(AdmissionError, match="权限"):
        query_agent(task("policy_count"), allowed_businesses=("运费险",))


def test_report_groups_events_by_actual_nodes_and_keeps_sources(tmp_path):
    state, directory = run(tmp_path, ScriptedModel([proposal(intent="analysis")]))
    log = events(directory)
    report = report_data(log, "case")
    assert len(log) > len(report["steps"]) * 5
    assert [s["node"] for s in report["steps"]] == [
        "understand_request",
        "run_analysis",
        "compose_reply",
        "validate_reply",
    ]
    assert report["steps"][0]["next"] == "取数并完成分析"
    assert len(report["metrics"]) == 1
    assert len(report["queries"]) == 2
    assert {q["total"] for q in report["queries"]} == {56000, 70000}
    assert report["answer"] == state["answer"]
    assert any(c["field"] == "任务类型" for c in report["steps"][0]["changes"])
    assert any(c["field"] == "回答草稿" for c in report["steps"][2]["changes"])
    assert any(c["field"] == "最终交付" for c in report["steps"][3]["changes"])


def test_legacy_trace_does_not_inherit_current_catalog(tmp_path):
    _, directory = run(tmp_path)
    # 模拟上一版本：删除当时根本没有写过的配置快照，再生成回放。
    log = [e for e in events(directory) if e["kind"] != "metric_resolution"]

    def remove_metadata(value):
        if isinstance(value, dict):
            for key in ["metric_definition", "query_execution"]:
                value.pop(key, None)
            for item in value.values():
                remove_metadata(item)
        elif isinstance(value, list):
            for item in value:
                remove_metadata(item)

    remove_metadata(log)
    report = report_data(log, "legacy")
    assert report["metrics"] == [] and report["queries"] == []
    assert len(report["steps"]) == 4
    assert "demo_ds_insurance_daily" not in json.dumps(report["metrics"])


def test_handled_failure_is_not_presented_as_success(tmp_path):
    _, directory = run(tmp_path, ScriptedModel(failure_stage="compose_reply"))
    report = report_data(events(directory), "case")
    step = next(s for s in report["steps"] if s["node"] == "compose_reply")
    assert step["tone"] == "bad"
    assert step["outcome"] == "执行失败"
    assert "失败" in step["title"]
    assert report["status"] == "failed"


def test_tool_retry_is_visible_without_reading_raw_events(tmp_path):
    attempts = []

    def transient(task, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise TimeoutError("模拟超时")
        return query_agent(task, **kwargs)

    _, directory = run(tmp_path, graph_options={"query_fn": transient})
    report = report_data(events(directory), "case")
    step = next(s for s in report["steps"] if s["node"] == "run_query")
    assert "程序实际重试了 1 次" in "".join(step["notes"])
    assert step["outcome"] == "完成"
