"""有费用的十案例验收：运行前显式使用 --run-paid-cases。

复用已完成的同名案例，避免反复收费；需要重跑时用新的 --output-dir。
普通 pytest 永远不会导入并执行这里的付费调用。
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from ..settings import PROJECT_DIR
from .capabilities import query_agent
from .runtime import execute

CASES = [
    ("live-query-01", "查询准时保上周的保费收入", None, "completed", "query"),
    (
        "live-analysis-02",
        "分析准时保上周保费收入为什么下降，按渠道看一下",
        None,
        "completed",
        "analysis",
    ),
    ("live-knowledge-03", "保费收入的口径是什么？", None, "completed", "knowledge"),
    ("live-clarify-04", "上周保费收入是多少？", "准时保", "completed", "query"),
    ("live-clarify-05", "帮我查一下保费收入", "运费险，上周", "completed", "query"),
    ("live-unsupported-06", "查准时保上周的利润率", None, "failed", None),
    ("live-unsupported-07", "帮我订一张去北京的机票", None, "failed", None),
    ("live-range-08", "查准时保今年的保费收入", None, "failed", None),
    ("live-permission-09", "查询准时保上周保费收入", None, "failed", None),
    ("live-retry-10", "查询准时保昨天的保单量", None, "completed", "query"),
]


def read_events(directory):
    return [json.loads(line) for line in (directory / "trace.jsonl").read_text().splitlines()]


def cli(directory, command, text, thread_id):
    # 子进程结束后才进行 resume，实际验证跨进程恢复，不在同一 Python 对象上假装重启。
    args = [
        sys.executable,
        "-m",
        "business_analysis_repro.main_agent",
        command,
        text,
        "--thread-id",
        thread_id,
        "--output-dir",
        str(directory),
    ]
    if command == "run":
        args += ["--reference-date", "2026-09-01"]
    result = subprocess.run(args, capture_output=True, text=True, timeout=300, check=False)
    if result.returncode not in {0, 1, 2}:
        raise AssertionError(f"CLI 异常退出：{thread_id}，code={result.returncode}")
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-paid-cases", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_DIR / ".runs" / "main-agent")
    args = parser.parse_args()
    if not args.run_paid_cases:
        parser.error("这是付费验证；确认要运行后添加 --run-paid-cases。")
    summaries = []
    for thread_id, question, answer, expected, source in CASES:
        directory = args.output_dir / thread_id
        print(f"验证 {thread_id} ...", flush=True)
        if not (directory / "state.json").exists():
            if thread_id == "live-permission-09":
                execute(
                    output_dir=args.output_dir,
                    thread_id=thread_id,
                    question=question,
                    reference_date="2026-09-01",
                    graph_options={"allowed_businesses": ("运费险",)},
                )
            elif thread_id == "live-retry-10":
                attempts = []

                def transient_tool(task, _attempts=attempts, **kwargs):
                    _attempts.append(1)
                    if len(_attempts) == 1:
                        raise TimeoutError("验收主动注入的一次模拟取数超时；不是 Kimi 服务故障。")
                    return query_agent(task, **kwargs)

                execute(
                    output_dir=args.output_dir,
                    thread_id=thread_id,
                    question=question,
                    reference_date="2026-09-01",
                    graph_options={"query_fn": transient_tool},
                )
            else:
                cli(args.output_dir, "run", question, thread_id)
        state = json.loads((directory / "state.json").read_text())
        if answer and state["status"] == "waiting_user":
            assert state["result"] is None, "澄清之前不应取数"
            code = cli(args.output_dir, "resume", answer, thread_id)
            assert code == 0, f"恢复后没有完成：{thread_id}"
            state = json.loads((directory / "state.json").read_text())
        assert state["status"] == expected, (thread_id, state["status"], state["answer"])
        log = read_events(directory)
        nodes = [
            e["name"] for e in log if e["kind"] == "span_start" and e.get("category") == "node"
        ]
        if source:
            assert state["result"]["source"] == source
            assert state["validation"]["passed"] is True
            assert "模拟数据" in state["answer"]
            assert state["result"]["evidence_id"] in state["answer"]
        if answer:
            assert state["clarification_count"] == 1
            assert len({e["run_id"] for e in log}) == 2
            assert nodes.count("run_query") == 1
        if thread_id == "live-query-01":
            assert state["result"]["total"] == 56000
            assert state["task"]["start_date"] == "2026-08-24"
        if thread_id == "live-analysis-02":
            assert state["result"]["baseline"]["total"] == 70000
            assert state["result"]["facts"]["变动率"] == "-20.0%"
        if thread_id == "live-clarify-05":
            assert state["result"]["total"] == 112000
        if thread_id == "live-retry-10":
            assert state["result"]["total"] == 800
            assert any(e["kind"] == "tool_retry" for e in log)
        if thread_id == "live-permission-09":
            assert any("AdmissionError" in str(e) for e in log)
        usage = {
            key: sum(e.get("usage", {}).get(key, 0) for e in log if e["kind"] == "model_response")
            for key in ["input_tokens", "output_tokens"]
        }
        summaries.append(
            {
                "thread_id": thread_id,
                "question": question,
                "clarification_answer": answer,
                "expected_status": expected,
                "actual_status": state["status"],
                "passed": True,
                "model_calls": sum(e["kind"] == "model_request" for e in log),
                "usage": usage,
                "node_path": nodes,
                "answer": state["answer"],
                "trace": str((directory / "trace.html").resolve()),
                "injected_fixture": "permission-denied"
                if thread_id.endswith("09")
                else "one-tool-timeout"
                if thread_id.endswith("10")
                else None,
            }
        )
        # 逐案例保存，即使后面网络故障也不会丢失已经完成的验收记录。
        (args.output_dir / "live-verification.json").write_text(
            json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            f"  PASS · {state['status']} · {summaries[-1]['model_calls']} model calls", flush=True
        )
    print(
        json.dumps(
            {
                "passed": len(summaries),
                "cases": len(CASES),
                "model_calls": sum(s["model_calls"] for s in summaries),
                "usage": {
                    k: sum(s["usage"][k] for s in summaries)
                    for k in ["input_tokens", "output_tokens"]
                },
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
