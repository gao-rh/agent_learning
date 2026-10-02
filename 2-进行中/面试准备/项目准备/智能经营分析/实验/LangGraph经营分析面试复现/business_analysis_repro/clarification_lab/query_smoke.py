"""一次只运行一轮的实验控制入口；标准答案在执行结束后才供评审读取。"""

import argparse
import hashlib
import json
import uuid
from copy import deepcopy
from pathlib import Path

from ..experiment_support import write_snapshot
from ..main_agent.runtime import locked
from ..playground.server import ChatStore, read_json, save_json
from ..playground.usage import summarize
from ..settings import get_kimi_settings
from .experiment import manifest
from .knowledge import FIXTURES
from .query_runtime import make_executor, seed_database


def frozen_manifest():
    result = manifest()
    root = Path(__file__).resolve().parents[1]
    for relative in ("playground/server.py", "playground/context_memory.py", "playground/usage.py",
                     "playground/trace.py", "playground/run_control.py", "playground/inbox.py",
                     "playground/steering.py", "main_agent/trace.py", "main_agent/runtime.py",
                     "main_agent/state.py", "settings.py"):
        result["sha256"][relative] = hashlib.sha256((root / relative).read_bytes()).hexdigest()
    return result


def configuration():
    settings = get_kimi_settings()
    return {"model": settings.model_name, "base_url": settings.base_url,
            "temperature": 0.6, "thinking": "disabled", "max_output_tokens": 1800}


def prepare(root, max_requests=30, max_turn_requests=6, all_cases=False, selected_cases=None):
    if not 1 <= max_requests <= (160 if all_cases else 30) or not 1 <= max_turn_requests <= 12:
        raise ValueError("批次预算不能超过小样本30次/全十二例160次；每轮最多12次")
    root = Path(root)
    if all_cases and selected_cases:
        raise ValueError("--all-cases 与 --cases 不能同时使用")
    ids = ([c["id"] for c in json.loads((FIXTURES / "simple_query_cases.json").read_text())["cases"]]
           if all_cases else ["Q09", "Q11"])
    if selected_cases:
        available = {c["id"] for c in json.loads((FIXTURES / "simple_query_cases.json").read_text())["cases"]}
        if set(selected_cases) - available or len(set(selected_cases)) != len(selected_cases):
            raise ValueError("未知或重复案例")
        ids = list(selected_cases)
    config = configuration()  # 配置失败时不留下半份目录。
    root.mkdir(parents=True, exist_ok=False)
    value = {"profile": "simple-query-suite-v2", "model": config,
        "manifest": frozen_manifest(), "case_ids": {key: uuid.uuid4().hex[:16] for key in ids},
        "limits": {"batch_requests": max_requests, "requests_per_turn": max_turn_requests, "estimated_input_per_request": 18000},
        "price": {"checked_at": "2026-09-30", "source": "https://platform.kimi.com/",
                  "cny_per_million": {"input": 6.5, "cache_read": 1.1, "output": 27}},
        "run_count_per_case": 1}
    seed_database(root / "synthetic.sqlite")
    write_snapshot(root, Path(__file__).resolve().parents[1], value["manifest"]["sha256"])
    save_json(root / "batch.json", value)
    return {"directory": str(root.resolve()), "cases": list(value["case_ids"]), "model_calls": 0}


def canonical(tasks):
    result = []
    for original in tasks:
        task = deepcopy(original)
        task["group_by"] = sorted(task["group_by"])
        task["filters"] = {k: sorted(v) for k, v in task["filters"].items()}
        task["required_predicates"] = sorted(task["required_predicates"], key=lambda x: x["field_id"])
        result.append(json.dumps(task, ensure_ascii=False, sort_keys=True))
    return sorted(result)


def compare(inspection, expected):
    actual = inspection.get("validation", {}).get("normalized_tasks", [])
    outcome = inspection.get("resolver_result", {}).get("outcome")
    submissions = inspection.get("model_submissions", [])
    raw_outcome = submissions[-1].get("outcome") if submissions else None
    expected_tasks = expected["expected_tasks"]
    if not inspection.get("resolver_result"):
        return {"grade": "failed", "failure_stage": "before_resolution_return",
                "actual_outcome": None, "model_final_outcome": raw_outcome,
                "expected_outcome": expected["expected_outcome"], "task_match": None,
                "mismatches": [], "expected_tasks": expected_tasks, "actual_tasks": [],
                "must_ask": expected["must_ask"], "latest_model_submission": submissions[-1] if submissions else None,
                "note": "本轮尚未返回理解结果；不得借用上轮checkpoint判断漏指标。原始模型提交见Trace。"}
    mismatches = []
    am = {t["metric_id"]: t for t in actual}
    em = {t["metric_id"]: t for t in expected_tasks}
    for mid in em.keys() - am.keys():
        mismatches.append({"type": "missing_metric", "metric_id": mid})
    for mid in am.keys() - em.keys():
        mismatches.append({"type": "unexpected_metric", "metric_id": mid})
    for mid in em.keys() & am.keys():
        for key in ("period", "comparison_period", "filters", "group_by", "required_predicates", "intent"):
            a, e = am[mid][key], em[mid][key]
            if key == "group_by":
                a, e = sorted(a), sorted(e)
            if a != e:
                mismatches.append({"metric_id": mid, "field": key, "expected": e, "actual": a})
    if expected.get("expected_time_expression") == "absolute" and submissions:
        for request in submissions[-1].get("requests", []):
            mode = (request.get("period") or {}).get("mode")
            if mode not in {"range", "exact"}:
                mismatches.append({"metric_id": request["metric_id"], "field": "time_expression",
                                   "expected": "absolute", "actual": mode})
    task_match = canonical(actual) == canonical(expected_tasks) and not mismatches
    valid = inspection.get("validation", {}).get("accepted", False)
    if outcome != expected["expected_outcome"] or raw_outcome != outcome:
        grade = "failed"
    elif outcome == "clarify":
        grade = "needs_question_review"
    else:
        grade = "task_matched" if task_match and valid else "failed"
    return {"grade": grade, "actual_outcome": outcome, "model_final_outcome": raw_outcome,
            "expected_outcome": expected["expected_outcome"], "task_match": task_match,
            "mismatches": mismatches, "expected_tasks": expected_tasks, "actual_tasks": actual,
            "must_ask": expected["must_ask"], "note": "结构匹配后仍需核对原始调用与查询结果，不能推算总体准确率。"}


def step(root, case_id, question_reviewed=False, model_factory=None, *, user_message=None,
         simulation_input=None):
    with locked(root):  # 小实验串行运行，批次上限检查不会与另一用例竞争。
        batch = read_json(root / "batch.json", {})
        if batch["manifest"] != frozen_manifest():
            raise ValueError("版本已改变，不能混入同一批次")
        if not model_factory and batch["model"] != configuration():
            raise ValueError("模型配置已改变")
        if case_id not in batch["case_ids"]:
            raise ValueError("该用例不在本批次冻结的运行清单中")
        public = json.loads((FIXTURES / "simple_query_cases.json").read_text())
        case = next(c for c in public["cases"] if c["id"] == case_id)
        adaptive = bool(batch.get("simulation"))
        if adaptive and (not simulation_input or not user_message):
            raise ValueError("AI用户批次必须由conversation_lab提供实际消息与来源")
        if not adaptive and (simulation_input or user_message is not None):
            raise ValueError("固定脚本批次不能混入动态用户输入")
        previous = sorted(p for p in root.glob(f"{case_id}-turn-*.json") if len(p.stem.split("-")) == 3)
        index = len(previous)
        if index >= (batch["simulation"]["max_turns"] if adaptive else len(case["turns"])):
            raise ValueError("用例已经结束，不重复付费运行")
        if previous and not adaptive:
            last = read_json(previous[-1], {})
            if last["review"]["grade"] == "failed":
                raise ValueError("上轮失败，后续阻断，先保留并诊断")
            if case["turns"][index]["advance_when"] == "after_clarification_question":
                if last["status"] != "waiting_user" or not question_reviewed:
                    raise ValueError("先审阅实际问句，再使用 --question-reviewed")
            elif last["status"] != "completed":
                raise ValueError("上一轮尚未实际查询完成")
        kwargs = {"model_factory": model_factory} if model_factory else {}
        executor = make_executor(root, **kwargs)
        store = ChatStore(root / "conversations", executor=executor)
        cid = batch["case_ids"][case_id]
        rid = hashlib.sha256(f"{cid}:{index}".encode()).hexdigest()[:16]
        # 只交给被测系统当前输入；不传未来轮次、用例类别或标准答案。
        question = user_message if adaptive else case["turns"][index]["user_message"]
        conversation = store.send(cid, question, request_id=rid)
        reply = conversation["messages"][-1]
        directory = root / "conversations" / cid / "tasks" / reply["thread_id"]
        state = read_json(directory / "state.json", {})
        # 到执行结束才读取人工标准；标准只能评价，不能修复 State 或改 SQL。
        expected = (None if adaptive else json.loads((FIXTURES / "simple_query_rubrics.private.json").read_text())["cases"][case_id]["turns"][index])
        # checkpoint可能停留在上轮澄清；评审只采用这次真实run_id内的事件。
        events = [json.loads(line) for line in (directory / "trace.jsonl").read_text().splitlines()]
        current = [e for e in events if e["run_id"] == events[-1]["run_id"]]
        inspected = [e for e in current if e["kind"] == "experiment_inspection"]
        inspection = inspected[-1] if inspected else {"model_submissions": [
            e["inputs"] for e in current if e["kind"] == "span_start"
            and e.get("category") == "tool" and e["name"] == "finish_resolution"]}
        review = ({"grade": "pending_human_review", "note": "动态用户实际选择需审阅，不套固定逐轮标准。"}
                  if adaptive else compare(inspection, expected))
        protocol_errors = [e for e in current if e["kind"] == "span_end"
                           and e.get("name") == "finish_resolution"
                           and "knowledge_refs" in str(e.get("output", {}).get("result", {}).get("error", ""))]
        if reply["status"] not in {"completed", "waiting_user"}:
            review["grade"] = "failed"
        record = {"case_id": case_id, "turn": index+1, "conversation_id": cid,
                  "thread_id": reply["thread_id"], "status": reply["status"],
                  "question": question, "answer": reply["content"],
                  "review": review, "usage": reply["usage"], "task_usage": reply["task_usage"],
                  "queries": (state.get("result") or {}).get("queries", []) if reply["status"] == "completed" else [],
                  "trace": str(directory / "trace.html"), "state_file": str(directory / "state.json"),
                  "previous_question_reviewed": question_reviewed,
                  "source_protocol_corrections": len(protocol_errors),
                  "source_protocol_errors": protocol_errors}
        if adaptive:
            record.update(input_origin=simulation_input["role"], simulated_user=simulation_input)
        save_json(root / f"{case_id}-turn-{index+1}.json", record)
        return record


def summary(root):
    rows = [read_json(p, {}) for p in sorted(root.glob("Q*-turn-*.json")) if len(p.stem.split("-")) == 3]
    events = []
    for path in root.glob("conversations/*/tasks/*/trace.jsonl"):
        events.extend(json.loads(line) for line in path.read_text().splitlines())
    result = {"turns": rows, "usage": summarize(events),
              "query_executions": sum(e["kind"] == "span_start" and e.get("name") == "query_local_simulation" for e in events)}
    save_json(root / "summary.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description="小样本查询实验，一次只处理一轮。")
    parser.add_argument("command", choices=["prepare", "step", "summary"])
    parser.add_argument("directory", type=Path)
    parser.add_argument("--case", choices=[f"Q{i:02}" for i in range(1, 13)])
    parser.add_argument("--question-reviewed", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--all-cases", action="store_true", help="显式创建全部十二例的批次")
    parser.add_argument("--cases", nargs="+", choices=[f"Q{i:02}" for i in range(1, 13)],
                        help="只冻结本次要测的案例；默认仍为 Q09/Q11")
    parser.add_argument("--max-requests", type=int, default=30)
    parser.add_argument("--max-turn-requests", type=int, default=6)
    args = parser.parse_args()
    if args.command == "prepare":
        value = prepare(args.directory, args.max_requests, args.max_turn_requests, args.all_cases, args.cases)
    elif args.command == "summary":
        value = summary(args.directory)
    else:
        if not args.live or not args.case:
            parser.error("step需要--live和--case；仅运行已授权的这一轮")
        public = json.loads((FIXTURES / "simple_query_cases.json").read_text())["cases"]
        if len(next(c for c in public if c["id"] == args.case)["turns"]) > 1 or read_json(args.directory / "batch.json", {}).get("simulation"):
            parser.error("新的多轮测试使用 python -m business_analysis_repro.conversation_lab run <目录> --case <案例> --live")
        value = step(args.directory, args.case, args.question_reviewed)
        summary(args.directory)
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
