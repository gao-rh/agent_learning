"""并行契约测试：运行真实 StateGraph/SQLite/数据函数；模型用确定性替身。

用同步事件证明重叠与进程共享上限，不靠“看起来更快”推断并发。
真实 Kimi 的自然语言/工具调用另用少量在线验收，不能由这些替身证明。
"""

import json
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.request import Request, urlopen

import pytest
from langchain_core.messages import AIMessage, AIMessageChunk

from business_analysis_repro.main_agent.state import Reply, Verdict
from business_analysis_repro.playground import catalog, server
from business_analysis_repro.playground.agent import TimeSpec
from business_analysis_repro.playground.data import query_agent
from business_analysis_repro.playground.parallel_agent import execute, make_jobs, summary_cards
from business_analysis_repro.playground.parallel_model import ParallelModel
from business_analysis_repro.playground.parallel_state import (
    BatchResolution,
    MetricRequest,
    merge_results,
)
from business_analysis_repro.playground.parallel_trace import Trace, read_events, render_html

IDS = list(catalog.METRICS)


def request(metric_id=IDS[0], **kwargs):
    return MetricRequest(
        metric_id=metric_id, period=TimeSpec(mode="calendar", unit="week", offset=-1), **kwargs
    )


def planner(requests=None, proposals=None, date_passed=True):
    responses = list(
        proposals or [BatchResolution(outcome="ready", requests=requests or [request()])]
    )

    class FakeModel:
        def __init__(self, trace, max_calls):
            self.trace = trace

        def resolve(self, payload):
            self.trace.event("test_payload", "resolve", payload=payload)
            return responses.pop(0) if len(responses) > 1 else responses[0]

        def complete(self, stage, instruction, payload, schema):
            if stage == "compose_batch":
                return Reply(
                    text="这是模拟数据的描述性比较；失败项以表格为准，不能证明业务因果。",
                    evidence_ids=payload["evidence_ids"],
                )
            if stage == "validate_dates" and not date_passed:
                return Verdict(passed=False, issues=["上周应为自然周，请核对日期。"])
            return Verdict(passed=True, issues=[])

    return FakeModel


def test_global_five_across_two_graphs_and_trace_isolation(tmp_path):
    lock, five_started, release = threading.Lock(), threading.Event(), threading.Event()
    current = peak = 0
    calls = Counter()

    def blocking_query(task, trace=None):
        nonlocal current, peak
        with lock:
            current += 1
            peak = max(peak, current)
            calls[(trace.thread_id, task["metric_id"])] += 1
            if current == 5:
                five_started.set()
        try:
            assert release.wait(10), "父测试未及时释放并行分支"
            return query_agent(task, trace)
        finally:
            with lock:
                current -= 1

    # 两轮父图各有6个任务，最多12个可运行，但整个进程最多放行5个。
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                execute,
                tmp_path,
                f"thread-{i}",
                "六指标查询",
                model_factory=planner([request(mid) for mid in IDS[:6]]),
                capabilities={"query": blocking_query},
            )
            for i in range(2)
        ]
        try:
            assert five_started.wait(10), "未形成5个真实重叠的分支"
            with lock:
                assert current == peak == 5
        finally:
            release.set()
        runs = [f.result(timeout=25) for f in futures]
    assert peak == 5 and len(calls) == 12 and set(calls.values()) == {1}
    for state, folder in runs:
        assert state["status"] == "completed"
        assert len(state["jobs"]) == len(state["job_results"]) == 6
        assert [c["name"] for c in state["result"]["cards"]] == [j["name"] for j in state["jobs"]]
        events = read_events(folder / "trace.jsonl")
        assert [e["seq"] for e in events] == list(range(1, len(events) + 1))
        starts = {e["span_id"]: e for e in events if e["kind"] == "span_start"}
        for event in events:
            if (
                event.get("job_id")
                and event["kind"] == "span_start"
                and event["category"] == "tool"
            ):
                assert starts[event["parent_span_id"]]["job_id"] == event["job_id"]
        gather = [e for e in events if e["kind"] == "span_start" and e["name"] == "gather_results"]
        assert len(gather) == 1
        assert gather[0]["seq"] > max(
            e["seq"] for e in events if e["kind"] == "job_status" and e["status"] == "ok"
        )


def test_retry_only_transient_job_and_keep_partial_results(tmp_path):
    calls = Counter()

    def unreliable(task, trace=None):
        mid = task["metric_id"]
        calls[mid] += 1
        if mid == IDS[0] and calls[mid] == 1:
            raise TimeoutError("测试：本分支第一次超时")
        if mid == IDS[1]:
            raise ValueError("测试：这个指标的证据不合法")
        return query_agent(task, trace)

    state, folder = execute(
        tmp_path,
        "partial-test",
        "三个指标",
        model_factory=planner([request(mid) for mid in IDS[:3]]),
        capabilities={"query": unreliable},
    )
    assert state["status"] == "partial"
    assert state["result"]["succeeded"] == 2 and state["result"]["failed"] == 1
    assert calls == {IDS[0]: 2, IDS[1]: 1, IDS[2]: 1}
    assert "未完成" in state["answer"] and "完成 2/3" in state["answer"]
    html = (folder / "trace.html").read_text()
    assert "重试中" in html or "retrying" in html
    assert "全链路" in html and "测试：这个指标的证据不合法" in html


def test_four_metric_analysis_keeps_all_groups_and_two_periods(tmp_path):
    mids = [m["id"] for m in catalog.METRICS.values() if "渗透率" in m["name"]]
    assert len(mids) == 4
    state, folder = execute(
        tmp_path,
        "four-rates",
        "四个渗透率，尽可能细",
        model_factory=planner(
            [
                request(mid, intent="analysis", group_by=list(catalog.METRICS[mid]["dimensions"]))
                for mid in mids
            ]
        ),
    )
    assert state["status"] == "completed"
    assert sorted(len(c["rows"]) for c in state["result"]["cards"]) == [12, 12, 18, 18]
    assert all(c["has_baseline"] for c in state["result"]["cards"])
    assert len(state["result"]["evidence_ids"]) == 4
    context = summary_cards(state["result"]["cards"])
    assert sum(c["breakdown"]["row_count"] for c in context) == 60
    assert all(c["breakdown"]["available"] for c in context)
    assert all(
        len(c["breakdown"]["largest_absolute_changes_not_causal_contributions"]) == 3
        for c in context
    )
    assert all(
        row["baseline"] != "分母为零，无法计算"
        for c in state["result"]["cards"]
        for row in c["rows"]
    )
    events = read_events(folder / "trace.jsonl")
    assert (
        sum(e["kind"] == "span_start" and e["name"] == "analysis.query_agent" for e in events) == 8
    )


def test_exact_dedup_different_scope_and_reducer():
    first = request(group_by=["merchant_age", "merchant_type"])
    duplicate = request(group_by=["merchant_type", "merchant_age"])
    other = request(filters={"merchant_age": ["new_merchant"]})
    # Use a metric known to support both dimensions.
    for r in [first, duplicate, other]:
        r.metric_id = "demo_metric_fx_order_rate"
    plan = BatchResolution(outcome="ready", requests=[first, duplicate, other])
    jobs = make_jobs(plan, "2026-09-01", 1)
    assert len(jobs) == 2 and jobs[0]["job_id"] != jobs[1]["job_id"]
    old = {"job-a": {"status": "ok"}}
    merged = merge_results(old, {"job-b": {"status": "failed"}})
    assert len(merged) == 2 and len(old) == 1
    assert merge_results(old, old) == old
    assert merge_results(old, {"__reset__": True}) == {}
    with pytest.raises(ValueError, match="冲突"):
        merge_results(old, {"job-a": {"status": "failed"}})


def test_mismatched_evidence_not_accepted_and_input_not_mutated(tmp_path):
    def bad_query(task, trace=None):
        result = query_agent(task, trace)
        result["scope"]["revision"] += 1
        return result

    state, _ = execute(
        tmp_path, "wrong-scope", "查询", model_factory=planner(), capabilities={"query": bad_query}
    )
    assert state["status"] == "failed"
    assert state["jobs"][0]["task"]["revision"] == 1
    assert state["result"]["succeeded"] == 0
    assert not state["result"]["evidence_ids"]


def test_clarification_resume_same_checkpoint_and_no_stale_results(tmp_path):
    model = planner(
        proposals=[
            BatchResolution(outcome="clarify", question="要查哪个期间？"),
            BatchResolution(outcome="ready", requests=[request(IDS[0]), request(IDS[1])]),
        ]
    )
    first, folder = execute(tmp_path, "resume-batch", "查两个指标", model_factory=model)
    assert first["status"] == "waiting_user" and not first["job_results"]
    second, _ = execute(tmp_path, "resume-batch", "上周", resume=True, model_factory=model)
    assert second["status"] == "completed" and second["task_revision"] == 2
    assert second["clarification_count"] == 1 and len(second["job_results"]) == 2
    events = read_events(folder / "trace.jsonl")
    assert len({e["run_id"] for e in events}) == 2


@pytest.mark.parametrize("invalid", ["dimension", "date"])
def test_parent_clarifies_before_any_query(tmp_path, invalid):
    req = request(
        "demo_metric_fx_order_rate", group_by=["source"] if invalid == "dimension" else []
    )
    state, folder = execute(
        tmp_path,
        "invalid-" + invalid,
        "问题",
        model_factory=planner([req], date_passed=invalid != "date"),
    )
    assert state["status"] == "waiting_user"
    assert not any(e["kind"] == "job_status" for e in read_events(folder / "trace.jsonl"))


def test_summary_failure_preserves_verified_tables(tmp_path):
    Base = planner()

    class SummaryFailure(Base):
        def complete(self, stage, *args):
            if stage == "compose_batch":
                raise TimeoutError("模拟摘要超时")
            return super().complete(stage, *args)

    state, _ = execute(tmp_path, "summary-down", "查值", model_factory=SummaryFailure)
    assert state["status"] == "completed"
    assert state["validation"]["summary_fallback"]
    assert "文字摘要暂不可用" in state["answer"]
    assert state["result"]["cards"][0]["facts"]["结果"]


def test_existing_v3_pending_migrates_without_modifying_checkpoint(tmp_path, monkeypatch):
    cid, old_tid = "a" * 16, "b" * 16
    folder = tmp_path / cid / "tasks" / old_tid
    folder.mkdir(parents=True)
    old = {
        "messages": [{"type": "human", "content": "四个渗透率都要"}],
        "status": "waiting_user",
        "pending_question": "旧版只能选一个",
    }
    (folder / "state.json").write_text(json.dumps(old))
    (folder / "checkpoints.sqlite").write_bytes(b"old-checkpoint-preserved")
    recorded = {}

    def fake_execute(output, tid, text, **kwargs):
        recorded.update(tid=tid, text=text, **kwargs)
        return {"status": "completed", "answer": "已完成", "task": {}}, output / tid

    monkeypatch.setattr(server, "execute", fake_execute)
    store = server.ChatStore(tmp_path, executor=fake_execute)
    server.save_json(
        tmp_path / cid / "conversation.json",
        {"id": cid, "messages": [], "turns": [], "pending": old_tid, "active": None},
    )
    state = store.send(cid, "现在把这些都分析一下，上周，尽可能细")
    assert recorded["tid"] != old_tid and recorded["migrated_from"] == old_tid
    assert not recorded["resume"]
    assert recorded["initial_messages"][-1]["content"] == "旧版只能选一个"
    assert state["pending"] is None
    assert (folder / "checkpoints.sqlite").read_bytes() == b"old-checkpoint-preserved"
    assert json.loads((folder / "state.json").read_text()) == old


def test_trace_escapes_untrusted_text_and_incomplete_live_line(tmp_path):
    path = tmp_path / "trace.jsonl"
    event = {
        "seq": 1,
        "kind": "execution_start",
        "name": "parallel-v4",
        "input": {"text": "</pre><script>alert(1)</script>"},
    }
    path.write_text(json.dumps(event) + '\n{"seq":')
    events = read_events(path)
    assert len(events) == 1
    html = render_html(events, "test")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


@pytest.mark.parametrize(
    ("tool", "query", "dimension", "expected"),
    [
        ("search_dimension_values", "外卖商户类型", "merchant_type", "ready"),
        ("search_dimension_values", "城市商家", "merchant_type", "clarify"),
        ("search_dimension_values", "星际商户", "merchant_type", "clarify"),
        ("search_dimensions", "获客来源", None, "clarify"),
    ],
)
def test_native_tool_grounding_directory_browse_vs_unsupported(
    tmp_path, tool, query, dimension, expected
):
    mid = "demo_metric_cancel_order_rate"
    tool_args = {"metric_id": mid, "query": query}
    if dimension:
        tool_args["dimension_id"] = dimension
    responses = [
        [
            {"name": "get_metric_definition", "args": {"metric_id": mid}, "id": "definition"},
            {"name": tool, "args": tool_args, "id": "lookup"},
        ],
        [
            {
                "name": "finish_resolution",
                "args": BatchResolution(outcome="ready", requests=[request(mid)]).model_dump(),
                "id": "finish",
            }
        ],
    ]
    messages_seen = []

    class Client:
        def bind_tools(self, tools):
            return self

        def stream(self, messages, **kwargs):
            response = self.invoke(messages)
            yield AIMessageChunk(content=response.content, tool_calls=response.tool_calls)

        def invoke(self, messages):
            messages_seen.append(list(messages))
            return AIMessage(content="", tool_calls=responses.pop(0))

    model = object.__new__(ParallelModel)
    model.client = SimpleNamespace(bound=Client())
    model.trace = Trace(tmp_path, "tool-grounding")
    model.max_calls, model.model_name = 40, "test-double"
    proposal = model.resolve({"messages": [{"role": "human", "content": query}]})
    assert proposal.outcome == expected
    assert {m.tool_call_id for m in messages_seen[-1] if m.type == "tool"} == {
        "definition",
        "lookup",
    }


def test_catalog_exact_enum_ids_still_respect_metric_support():
    supported = catalog.search_dimension_values("demo_metric_timely_paid_premium", "city")
    unsupported = catalog.search_dimension_values("demo_metric_cancel_order_rate", "city")
    assert supported["candidates"][0]["score"] == 1
    assert supported["candidates"][0]["supported"] is True
    assert unsupported["candidates"][0]["score"] == 1
    assert unsupported["candidates"][0]["supported"] is False


def test_http_conversation_delivers_parallel_cards_and_trace(tmp_path):
    mids = [m["id"] for m in catalog.METRICS.values() if "渗透率" in m["name"]]
    factory = planner(
        [
            request(mid, intent="analysis", group_by=list(catalog.METRICS[mid]["dimensions"]))
            for mid in mids
        ]
    )
    store = server.ChatStore(tmp_path, executor=partial(execute, model_factory=factory))
    http = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(store))
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{http.server_port}"
    try:
        payload = json.dumps({"id": "d" * 16, "text": "四指标分析"}).encode()
        with urlopen(
            Request(
                url + "/api/message", data=payload, headers={"Content-Type": "application/json"}
            ),
            timeout=10,
        ) as reply:
            conversation = json.load(reply)
        message = conversation["messages"][-1]
        assert message["status"] == "completed"
        assert len(message["result_cards"]) == 4
        assert sum(len(c["rows"]) for c in message["result_cards"]) == 60
        with urlopen(url + message["trace"], timeout=10) as reply:
            html = reply.read().decode()
        assert "拆解与并行计划" in html and "全链路" in html
        with urlopen(url + "/api/health", timeout=10) as reply:
            assert json.load(reply)["max_concurrency"] == 5
    finally:
        http.shutdown()
        http.server_close()
        thread.join(timeout=2)
