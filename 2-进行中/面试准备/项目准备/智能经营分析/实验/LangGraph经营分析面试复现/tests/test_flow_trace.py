"""执行路线是原Trace的投影，不需要付费模型。覆盖并行归属与回放时刻边界。"""

import json
import threading
from copy import deepcopy
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest
from test_parallel_playground import planner, request

from business_analysis_repro.playground import server
from business_analysis_repro.playground.flow_trace import flow_payload, node_payload
from business_analysis_repro.playground.parallel_agent import execute
from business_analysis_repro.playground.parallel_trace import read_events

CID, TID = "a" * 16, "b" * 16


@pytest.fixture
def real_trace(tmp_path):
    ids = [
        "demo_metric_cancel_order_rate",
        "demo_metric_fx_order_rate",
        "demo_metric_timely_paid_order_rate",
        "demo_metric_fx_eligible_rate",
    ]
    model = planner([request(mid, intent="analysis", group_by=["merchant_age"]) for mid in ids])
    state, directory = execute(tmp_path / CID / "tasks", TID, "分析四个指标", model_factory=model)
    assert state["status"] == "completed"
    return read_events(directory / "trace.jsonl")


def test_four_analysis_branches_contain_eight_actual_queries(real_trace):
    run = flow_payload(real_trace, CID, TID)["runs"][0]
    assert run["stats"]["analysis"] == 4 and run["stats"]["queries"] == 8
    assert [p["kind"] for p in run["phases"]] == ["node", "parallel", "node", "node", "node"]
    assert len(run["phases"][1]["ids"]) == 4
    for n in run["nodes"]:
        if n["name"] == "analysis_agent":
            children = [c for c in run["nodes"] if c["parent"] == n["id"]]
            assert [c["label"] for c in children] == ["读取专题Skill", "取数 Agent · 本期", "取数 Agent · 对比期"]
            assert children[1]["period"] != children[2]["period"]
            assert "模型选择补查" in n["purpose"]
        assert "input" not in n and "output" not in n
    assert run["status"] == "completed"


def test_replay_never_returns_future_node_output(real_trace):
    start = next(
        e for e in real_trace if e["kind"] == "span_start" and e["name"] == "analysis_agent"
    )
    with pytest.raises(FileNotFoundError):
        node_payload(real_trace, start["span_id"], start["seq"] - 1)
    detail = node_payload(real_trace, start["span_id"], start["seq"])
    assert detail["input"]["intent"] == "analysis"
    assert detail["output"] is None and detail["finished"] is False
    assert node_payload(real_trace, start["span_id"])["finished"] is True
    prefix = [e for e in real_trace if e["seq"] <= start["seq"]]
    assert flow_payload(prefix, CID, TID, active=True)["runs"][0]["status"] == "running"
    assert flow_payload(prefix, CID, TID, active=False)["runs"][0]["status"] == "incomplete"


def test_failed_worker_does_not_look_successful(real_trace):
    events = deepcopy(real_trace)
    end = next(e for e in events if e["kind"] == "span_end" and e["name"] == "metric_worker")
    # worker捕获工具异常并返回outcome，因此它的span本身可能仍为ok。
    end["status"] = "ok"
    end["output"]["outcome"] = {"status": "failed", "error": {"message": "connection failed"}}
    run = flow_payload(events, CID, TID)["runs"][0]
    assert next(n for n in run["nodes"] if n["id"] == end["span_id"])["status"] == "failed"


def test_separate_runs_and_keep_rewrite_occurrences(real_trace):
    duplicate = deepcopy(real_trace)
    last = real_trace[-1]["seq"]
    for e in duplicate:
        e["seq"] += last
        e["run_id"] += "-resume"
        if e.get("span_id"):
            e["span_id"] += "-resume"
        if e.get("parent_span_id"):
            e["parent_span_id"] += "-resume"
        if e["kind"] == "execution_start":
            e["input"]["resume"] = True
    data = flow_payload(real_trace + duplicate, CID, TID)
    assert len(data["runs"]) == 2 and data["runs"][1]["resume"] is True
    assert data["runs"][0]["stats"]["queries"] == data["runs"][1]["stats"]["queries"] == 8
    # 同一轮的同名节点重复执行，应当保留每次出现，而不是按name覆盖。
    extra = deepcopy([e for e in real_trace if e.get("name") == "compose_reply"])
    for i, e in enumerate(extra):
        e["seq"] = last + i + 1
        e["span_id"] += "-rewrite"
    run = flow_payload(real_trace + extra, CID, TID)["runs"][0]
    assert sum(n["name"] == "compose_reply" for n in run["nodes"]) == 2


def test_detail_keeps_tool_model_events_but_only_received_stream_chunks(real_trace):
    start = next(
        e for e in real_trace if e["kind"] == "span_start" and e["name"] == "analysis_agent"
    )
    events = deepcopy(real_trace)
    for index, text in enumerate(["先收到", "后来收到"], 1):
        events.append(
            {
                **start,
                "kind": "answer_delta",
                "parent_span_id": start["span_id"],
                "seq": events[-1]["seq"] + 1,
                "delta": text,
            }
        )
    detail = node_payload(events, start["span_id"], events[-2]["seq"])
    assert detail["stream_text"] == "先收到"
    assert all(e["kind"] != "answer_delta" for e in detail["events"])


def test_http_route_is_read_only_and_escapes_via_json_text_content(tmp_path, real_trace):
    def forbidden(*args, **kwargs):
        raise AssertionError("追踪页面不得调用execute")

    store = server.ChatStore(tmp_path, executor=forbidden)
    http = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(store))
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{http.server_port}"
    folder = store.directory(CID) / "tasks" / TID
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "trace.jsonl"
    raw = "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in real_trace).encode()
    path.write_bytes(raw)
    try:
        with urlopen(url + f"/flow/{CID}/{TID}") as response:
            assert "逐步回放" in response.read().decode()
        with urlopen(url + f"/api/flow?id={CID}&task_id={TID}") as response:
            data = json.load(response)
        sid = data["runs"][0]["nodes"][1]["id"]
        with urlopen(url + f"/api/flow-node?id={CID}&task_id={TID}&span_id={sid}") as response:
            assert json.load(response)["finished"] is True
        with pytest.raises(HTTPError) as error:
            urlopen(url + "/flow/invalid/" + TID)
        assert error.value.code == 404
        with urlopen(url + f"/trace/{CID}/{TID}") as response:
            assert f"/flow/{CID}/{TID}" in response.read().decode()
        assert (
            path.read_bytes() == raw and not (store.directory(CID) / "conversation.json").exists()
        )
    finally:
        http.shutdown()
        http.server_close()
        thread.join(timeout=2)
