"""复现主链路、不可变数据与快照协议；不请求真实模型。"""

import json
import socket
import sqlite3
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from business_analysis_repro import reproduce
from business_analysis_repro.clarification_lab import query_smoke
from business_analysis_repro.experiment_support import source_bound_tool, validate_source_refs
from business_analysis_repro.playground import data, fixtures


def test_prepared_data_closes_connections_preserves_totals_and_rejects_edits(tmp_path):
    store = fixtures.prepare_data(tmp_path)
    path = Path(store["database"])
    modified = path.stat().st_mtime_ns
    assert fixtures.prepare_data(tmp_path) == store
    assert path.stat().st_mtime_ns == modified
    # 预设周的人工对照：净保费上周 56000，前周 70000。
    sql = "SELECT SUM(numerator) AS amount FROM demo_metric_daily WHERE metric_id=? AND biz_date BETWEEN ? AND ?"
    assert fixtures.read_rows(store, sql, ["demo_metric_fx_premium", "2026-08-24", "2026-08-30"])[0]["amount"] == 56000
    assert fixtures.read_rows(store, sql, ["demo_metric_fx_premium", "2026-08-17", "2026-08-23"])[0]["amount"] == 70000
    with sqlite3.connect(path) as db:
        db.execute("UPDATE demo_metric_daily SET numerator=0 WHERE metric_id='demo_metric_fx_premium'")
    with pytest.raises(ValueError, match="已被修改"):
        fixtures.prepare_data(tmp_path)


def test_concurrent_preparation_reuses_one_complete_database(tmp_path):
    with ThreadPoolExecutor(max_workers=5) as pool:
        stores = list(pool.map(lambda _: fixtures.prepare_data(tmp_path), range(5)))
    assert len({s["database_sha256"] for s in stores}) == 1
    assert all(s["rows"] == 110960 for s in stores)
    assert len(list(tmp_path.glob("*/synthetic.sqlite"))) == 1


def test_demo_runs_real_graph_analysis_and_interrupt_without_network(tmp_path, monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("离线复现禁止联网")
    monkeypatch.setattr(socket.socket, "connect", deny)
    local_store = fixtures.prepare_data(tmp_path / "fixtures")
    monkeypatch.setattr(data, "prepare_data", lambda: local_store)
    output = tmp_path / "demo"
    result = reproduce.demo(output)
    assert result["model_calls"] == 0 and not result["model_quality_evaluated"]
    assert len(result["scenarios"]) == 4
    assert result["scenarios"][2]["statuses"] == ["waiting_user", "completed"]
    state = json.loads((output / "analysis" / "state.json").read_text())
    investigation = next(iter(state["job_results"].values()))["result"]["investigation"]
    assert len(investigation["followup_results"]) == 1
    for row in result["scenarios"]:
        assert Path(row["trace"]).is_file()
        assert (Path(row["state"]).parent / "checkpoints.sqlite").is_file()
    with pytest.raises(FileExistsError):
        reproduce.demo(output)


def test_selected_query_cases_freeze_sources_and_private_review_without_secrets(tmp_path, monkeypatch):
    monkeypatch.setattr(query_smoke, "configuration", lambda: {"model": "offline"})
    root = tmp_path / "batch"
    result = query_smoke.prepare(root, selected_cases=["Q05", "Q12"])
    assert result["cases"] == ["Q05", "Q12"] and result["model_calls"] == 0
    with zipfile.ZipFile(root / "source-snapshot.zip") as archive:
        assert "clarification_lab/fixtures/simple_query_rubrics.private.json" in archive.namelist()
        assert not any(".env" in n or n.startswith(".runs") for n in archive.namelist())
    assert reproduce.inspect_batch(root)["source_matches"]
    with pytest.raises(ValueError, match="未知"):
        query_smoke.prepare(tmp_path / "bad", selected_cases=["Q99"])
    assert not (tmp_path / "bad").exists()


def test_source_schema_contains_only_observed_sources_and_does_not_mutate_original():
    from business_analysis_repro.clarification_lab.contract import LabResolution
    from business_analysis_repro.clarification_lab.knowledge import LabKnowledge

    knowledge = LabKnowledge()
    tool = {"function": {"parameters": LabResolution.model_json_schema()}}
    assert source_bound_tool(tool, knowledge)["function"]["parameters"]["properties"]["knowledge_refs"]["maxItems"] == 0
    knowledge.tools()["get_metric_definition"](metric_id="lab_fx_net_premium")
    refs = source_bound_tool(tool, knowledge)["function"]["parameters"]["properties"]["knowledge_refs"]
    assert refs["items"]["enum"] == ["SYN-lab_fx_net_premium"]
    assert "enum" not in tool["function"]["parameters"]["properties"]["knowledge_refs"]["items"]


def test_source_fallback_converts_only_observed_unique_definition_and_deduplicates():
    from business_analysis_repro.clarification_lab.contract import LabResolution
    from business_analysis_repro.clarification_lab.knowledge import LabKnowledge

    knowledge = LabKnowledge()
    knowledge.tools()["get_metric_definition"](metric_id="lab_fx_net_premium")
    raw = ["lab_fx_net_premium", "SYN-lab_fx_net_premium", "SYN-lab_fx_net_premium"]
    proposal = LabResolution(outcome="reply", knowledge_refs=raw)
    audit = validate_source_refs(proposal, knowledge)
    assert proposal.knowledge_refs == ["SYN-lab_fx_net_premium"]
    assert audit == {"before": raw, "after": proposal.knowledge_refs,
                     "mappings": [{"metric_id": "lab_fx_net_premium",
                                   "source_id": "SYN-lab_fx_net_premium"}]}


@pytest.mark.parametrize("ref", ["lab_fx_net_premium", "SYN-lab_fx_net_premium", "old-task-id"])
def test_source_fallback_rejects_unread_or_task_ids_without_changing_submission(ref):
    from business_analysis_repro.clarification_lab.contract import LabResolution
    from business_analysis_repro.clarification_lab.knowledge import LabKnowledge

    proposal = LabResolution(outcome="reply", knowledge_refs=[ref])
    with pytest.raises(ValueError, match="未读取的来源"):
        validate_source_refs(proposal, LabKnowledge())
    assert proposal.knowledge_refs == [ref]


def test_source_fallback_does_not_guess_between_two_observed_sources():
    from business_analysis_repro.clarification_lab.contract import LabResolution
    from business_analysis_repro.clarification_lab.knowledge import LabKnowledge

    knowledge = LabKnowledge()
    knowledge.tools()["get_metric_definition"](metric_id="lab_fx_net_premium")
    second = json.loads(json.dumps(knowledge.observations[0]))
    second["result"]["source"]["id"] = "another-definition-source"
    knowledge.observations.append(second)
    proposal = LabResolution(outcome="reply", knowledge_refs=["lab_fx_net_premium"])
    with pytest.raises(ValueError, match="未读取的来源"):
        validate_source_refs(proposal, knowledge)
