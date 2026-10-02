"""复现入口：预检、提前造数、离线主图演示、分层回归、只读批次检查。

不另造业务执行器；demo 复用当前父图/数据/分析/checkpoint/Trace，只有模型被替换。
替身提出的计划单独标记，不读取实验标准答案，不冒充实模能力。
"""

import argparse
import json
import os
import subprocess
import sys
import uuid
from importlib.metadata import version
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

from .settings import PROJECT_DIR

TEST_GROUPS = {
    "mechanism": ["test_parallel_playground", "test_analysis_v5", "test_context_memory",
                  "test_stop_replace", "test_inbox", "test_reproduce"],
    "lab": ["test_clarification_lab", "test_query_smoke", "test_complex_lab", "test_conversation_lab"],
    "viewer": ["test_case_viewer", "test_case_timeline", "test_flow_trace"],
}


def doctor():
    from .playground.parallel_agent import ENGINE, SOURCE_REVISION
    from .settings import get_kimi_settings, get_langsmith_settings

    try:
        settings = get_kimi_settings(require_api_key=False)
        model = {"name": settings.model_name, "key_present": bool(settings.api_key),
                 "tracing_enabled": get_langsmith_settings(load_env=False).tracing_enabled}
    except RuntimeError as exc:
        model = {"configuration_error": str(exc)}
    try:
        with build_opener(ProxyHandler({})).open("http://127.0.0.1:8787/api/health", timeout=2) as r:
            health = json.loads(r.read())
        current = health.get("application") == "langgraph-playground" and health.get("source_revision") == SOURCE_REVISION
        service = {"reachable": True, "current_source": current, "loaded_revision": health.get("source_revision"),
                   "action": "可直接使用" if current else "常驻服务代码较旧；完成当前任务后重启聊天服务"}
    except (OSError, ValueError):
        service = {"reachable": False, "action": "需要聊天时再启动 playground"}
    return {"project": str(PROJECT_DIR), "python": sys.version.split()[0], "engine": ENGINE,
            "packages": {p: version(p) for p in ("langgraph", "langchain-core", "pydantic")},
            "model": model, "service": service, "source_revision": SOURCE_REVISION,
            "model_calls": 0, "note": "预检不验证密钥额度或模型响应；demo 无需密钥"}


def prepare():
    from .clarification_lab.synthetic_queries import DATA_VERSION, seed_database
    from .playground.fixtures import prepare_data

    main_data = prepare_data()
    folder = PROJECT_DIR / ".runs" / "fixtures" / DATA_VERSION
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "synthetic.sqlite"
    seed_database(path)
    return {"playground": main_data, "simple_query": {"database": str(path), "version": DATA_VERSION},
            "model_calls": 0, "note": "复杂实验只澄清；多年视图另用 time_view_preview，不宣称已集成"}


def demo(directory):
    from .playground.parallel_agent import execute
    from .playground.parallel_state import BatchResolution, MetricRequest
    from .playground.parallel_trace import read_events

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)

    def factory(scenario):
        class ScriptedModel:
            def __init__(self, trace, max_calls):
                self.trace, self.max_calls = trace, max_calls

            def resolve(self, payload):
                self.trace.event("scripted_decision", "demo_resolution", input=payload,
                                 note="固定脚本，非模型理解/检索验收")
                if scenario == "clarify" and len(payload["messages"]) == 1:
                    return BatchResolution(outcome="clarify", question="请补充日期。")
                period = {"mode": "range", "start_date": "2026-08-24", "end_date": "2026-08-30"}
                requests = [MetricRequest(metric_id="demo_metric_fx_premium", period=period)]
                if scenario == "parallel":
                    requests.append(MetricRequest(metric_id="demo_metric_fx_order_rate", period=period))
                if scenario == "analysis":
                    requests = [MetricRequest(metric_id="demo_metric_funnel_join", intent="analysis",
                                              period=period, group_by=["channel_l1"])]
                return BatchResolution(outcome="ready", requests=requests)

            def complete(self, stage, instruction, payload, schema):
                self.trace.event("scripted_decision", stage, input=payload)
                if stage == "analysis_decision":
                    evidence = payload["evidence"][-1]
                    if len(payload["evidence"]) == 1:
                        top = evidence["largest_changes_not_contributions"][0]["dimensions"]["channel_l1"]
                        return schema(action="compare", reason="演示：按已查变化选择补查来源",
                                      group_by=["source"], filters={"channel_l1": [top]},
                                      evidence_ids=[evidence["evidence_id"]])
                    return schema(action="finish", reason="已完成一次补查", finding="已取得两期来源比较。",
                                  evidence_ids=[evidence["evidence_id"]])
                if stage == "compose_batch":
                    return schema(text="离线演示：实际数值和查询范围见下方程序计算表。",
                                  evidence_ids=payload["evidence_ids"])
                return schema(passed=True, issues=[])

        return ScriptedModel

    rows = []
    for scenario, question in [("query", "查上周放心吃净保费规模"),
                               ("parallel", "查上周放心吃净保费规模和订单渗透率"),
                               ("clarify", "查放心吃净保费规模"),
                               ("analysis", "分析上周加入商户数的渠道变化，补查一次来源")]:
        state, folder = execute(directory, scenario, question, model_factory=factory(scenario))
        statuses = [state["status"]]
        if scenario == "clarify":
            if state["status"] != "waiting_user":
                raise RuntimeError("澄清演示未到达 interrupt")
            state, folder = execute(directory, scenario, "2026年8月24日至30日。", resume=True,
                                    model_factory=factory(scenario))
            statuses.append(state["status"])
        if state["status"] != "completed":
            raise RuntimeError(f"离线演示未完成：{scenario}")
        events = read_events(folder / "trace.jsonl")
        if any(e["kind"] == "model_request" for e in events):
            raise RuntimeError("离线演示出现真实模型请求事件")
        rows.append({"scenario": scenario, "statuses": statuses, "jobs": len(state["jobs"]),
                     "trace": str(folder / "trace.html"), "state": str(folder / "state.json"),
                     "queries": sum(e["kind"] == "span_start" and e.get("name") in
                                    {"query_agent", "analysis.query_agent"} for e in events)})
    result = {"directory": str(directory.resolve()), "scenarios": rows, "model_calls": 0,
              "model_quality_evaluated": False, "note": "实际主图/SQLite/分析/恢复已运行；自然语言由脚本替代"}
    (directory / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


def inspect_batch(directory):
    """只读版本与进度。历史成绩继续由各运行器和固定查看器解释。"""
    directory = Path(directory)
    config = json.loads((directory / "batch.json").read_text())
    frozen = config["manifest"]
    if config.get("kind") == "complex":
        from .complex_lab.runtime import sources
        current = sources()
    elif isinstance(config.get("case_ids"), dict):
        from .clarification_lab.query_smoke import frozen_manifest
        current = frozen_manifest()
    else:
        from .clarification_lab.experiment import manifest
        current = manifest()
    expected, actual = frozen.get("sha256", frozen), current.get("sha256", current)
    changed = sorted(k for k in expected.keys() | actual.keys() if expected.get(k) != actual.get(k))
    model_calls = 0
    trace_files = list(directory.glob("*/trace.jsonl")) + list(directory.glob("conversations/*/tasks/*/trace.jsonl"))
    for path in trace_files:
        for line in path.read_text().splitlines():
            if line.strip():
                model_calls += json.loads(line).get("kind") == "model_request"
    return {"directory": str(directory.resolve()), "cases": list(config.get("case_ids", [])),
            "source_matches": frozen == current, "changed_files": changed,
            "snapshot_available": (directory / "source-snapshot.zip").is_file(),
            "recorded_model_calls": model_calls, "limits": config.get("limits"),
            "action": "使用对应运行器逐轮继续" if frozen == current else "只读旧记录；新实验另建目录",
            "model_calls": 0}


def main():
    parser = argparse.ArgumentParser(description="经营分析复现；不含付费执行命令。")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("doctor", "prepare"):
        sub.add_parser(name)
    p = sub.add_parser("demo")
    p.add_argument("--output", type=Path, default=None)
    p = sub.add_parser("test")
    p.add_argument("group", choices=[*TEST_GROUPS, "all"], default="mechanism", nargs="?")
    p = sub.add_parser("inspect-batch")
    p.add_argument("directory", type=Path)
    args = parser.parse_args()
    os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(PROJECT_DIR / ".runs" / "tokenizer-cache"))
    if args.command == "test":
        files = ["tests/" + n + ".py" for n in TEST_GROUPS[args.group]] if args.group != "all" else ["tests"]
        raise SystemExit(subprocess.run([sys.executable, "-m", "pytest", *files, "-q"], cwd=PROJECT_DIR, check=False).returncode)
    if args.command == "demo":
        result = demo(args.output or PROJECT_DIR / ".runs" / "reproduction" / uuid.uuid4().hex[:16])
    elif args.command == "inspect-batch":
        result = inspect_batch(args.directory)
    else:
        result = {"doctor": doctor, "prepare": prepare}[args.command]()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
