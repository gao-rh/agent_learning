"""命令行默认只做离线准备。真实请求必须使用run/resume且显式指定--live。"""

import argparse
import json
import uuid
from pathlib import Path

from .contract import LabResolution, validate_submission
from .experiment import execute_turn, experiment_instruction, manifest, payload_for, write_json
from .knowledge import FIXTURES, LabKnowledge, get_case, load_public


def check_pack():
    """检查资料内部一致性，不评价真实模型效果。这里才允许读取人工标准。"""
    cases = load_public("cases.json")["cases"]
    rubric = json.loads((FIXTURES / "rubrics.private.json").read_text())["cases"]
    assert len(cases) == 10 and len({c["id"] for c in cases}) == 10
    assert set(rubric) == {c["id"] for c in cases}
    knowledge = LabKnowledge()
    for mid, metric in knowledge.metrics.items():
        assert metric["id"] == mid and metric["query_binding"]["execution_enabled"] is False
        assert "preset" not in metric
        for dim, ids in metric["dimensions"].items():
            assert set(ids) <= {v["id"] for v in knowledge.DIMENSIONS[dim]["values"]}
    for case in cases:
        lab = LabKnowledge(case["knowledge_profile"])
        expected = rubric[case["id"]]
        # 检查标准任务是否能表达；不把这份标准任务传给运行器或模型。
        for task in expected["expected_tasks"]:
            request = dict(task)
            for key in ("period", "comparison_period"):
                bounds = request[key]
                request[key] = ({"mode": "range", "start_date": bounds["start"],
                                 "end_date": bounds["end"]} if bounds else None)
            checked = validate_submission({"outcome": "ready", "requests": [request]}, lab)
            assert checked["accepted"], (case["id"], checked["errors"])
        text = json.dumps(payload_for(case), ensure_ascii=False)
        assert "expected_tasks" not in text and "fixed_reply" not in text
        if expected["fixed_reply"]:
            assert expected["fixed_reply"] not in text
    a, b = get_case("alias_unknown"), get_case("alias_defined")
    assert payload_for(a) == payload_for(b)
    assert LabKnowledge().search_business_knowledge("下沉")["records"] == []
    augmented = LabKnowledge("with_definition")
    assert len(augmented.records) == len(knowledge.records) + 1
    assert augmented.records[:-1] == knowledge.records
    # 缺定义组公开资料中不出现该映射词，包括枚举别名、工具说明与基础知识。
    assert "下沉" not in json.dumps(knowledge.snapshot(), ensure_ascii=False)
    assert len(knowledge.search_metrics("加入商户数")["candidates"]) >= 2
    return {"status": "offline_pack_checked", "cases": len(cases),
            "metrics": len(knowledge.metrics), "dimensions": len(knowledge.DIMENSIONS),
            "knowledge_records_base": len(knowledge.records), "overlay_records": 1,
            "model_calls": 0, "business_queries": 0, "model_quality": "not_tested"}


def preview(case):
    from langchain_core.utils.function_calling import convert_to_openai_tool

    from ..playground.parallel_model import FINISH

    knowledge = LabKnowledge(case["knowledge_profile"])
    tools = [convert_to_openai_tool(fn) for fn in knowledge.tools().values()]
    from ..experiment_support import source_bound_tool

    hint = knowledge.business_context(payload_for(case)["messages"])
    finish = {**FINISH, "function": {**FINISH["function"],
              "parameters": LabResolution.model_json_schema()}}
    tools.append(source_bound_tool(finish, knowledge))
    return {"sent_to_model_on_first_call": {"system": experiment_instruction(),
               "payload": {**payload_for(case), "business_topic_hint": hint}, "tools": tools},
            "available_via_tools_not_automatically_sent": knowledge.snapshot(),
            "manifest": manifest(), "model_calls": 0}


def usage_summary(events):
    requests = [e for e in events if e["kind"] == "model_request"]
    responses = [e for e in events if e["kind"] == "model_response"]
    usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    for event in responses:
        for field in usage:
            usage[field] += event.get("usage", {}).get(field, 0) or 0
    return {"model_requests": len(requests), "responses": len(responses), **usage,
            "usage_incomplete": len(responses) < len(requests)
                or any(not e.get("usage") for e in responses),
            "cost": "not_calculated", "business_queries": 0}


def run_turn(directory, case, turns, max_calls, model_factory=None, expected_model=None):
    from ..main_agent.runtime import locked

    with locked(directory):
        number = len(turns) // 2 + 1
        if (directory / f"turn-{number}.json").exists():
            raise ValueError("该轮已有结果，不能覆盖或重复发起付费调用；请新建实验")
        return _run_turn(directory, case, turns, max_calls, model_factory, expected_model)


def _run_turn(directory, case, turns, max_calls, model_factory=None, expected_model=None):
    # 隔离的本地日志；不会构建graph，不能路由到取数、分析、认证或生成报告。
    from langsmith import tracing_context

    from ..playground.parallel_model import ParallelModel
    from ..playground.trace import Trace

    batch = directory.parent / "batch.json"
    if batch.exists() and json.loads(batch.read_text()).get("simulation"):
        from ..conversation_lab.budget import BudgetTrace
        trace = BudgetTrace(directory, directory.name, directory.parent, max_calls)
    else:
        trace = Trace(directory, directory.name)
    active_manifest = manifest()
    model = None
    try:
        model = (model_factory or ParallelModel)(trace, max_calls=max_calls)
        if expected_model and model.model_name != expected_model:
            raise ValueError("续轮模型已改变，请新建实验")
        with tracing_context(enabled=False):
            result = execute_turn(model, case, turns)
        result["status"] = "waiting_review"  # 自动契约通过仍不是业务正确性通过。
    except Exception as exc:  # noqa: BLE001 -- 实验边界保留失败记录，不伪造成功输出
        trace.event("experiment_error", "turn_failed", error_type=type(exc).__name__)
        result = {"status": "execution_error", "error_type": type(exc).__name__,
                  "note": "未生成标准答案或伪造任务，原始调用见trace.jsonl"}
    number = len(turns) // 2 + 1
    result["usage"] = usage_summary([e for e in trace.read() if e["run_id"] == trace.run_id])
    result["run_id"] = trace.run_id
    result["model"] = getattr(model, "model_name", "not_started")
    result["turn_number"] = number
    result["case_id"] = case["id"]
    write_json(directory / f"turn-{number}.json", result)
    write_json(directory / "session.json", {"case": case, "turns": turns,
        "turn_number": number, "max_calls": max_calls, "manifest": active_manifest,
        "last_result": result})
    trace.render()
    return result


def review(directory):
    # 与运行器分开加载人工标准，结果不再回灌给模型。
    session = json.loads((directory / "session.json").read_text())
    rubric = json.loads((FIXTURES / "rubrics.private.json").read_text())["cases"][session["case"]["id"]]
    result = session["last_result"]
    tasks = result.get("validation", {}).get("normalized_tasks", [])

    def canonical(items):
        # 只规范集合顺序，不补漏字段或改条件；基准、当期和每指标条件保留。
        normalized = []
        for task in items:
            item = dict(task)
            item["filters"] = {k: sorted(v) for k, v in item["filters"].items()}
            item["group_by"] = sorted(item["group_by"])
            item["required_predicates"] = sorted(item["required_predicates"], key=lambda p: p["field_id"])
            normalized.append(json.dumps(item, ensure_ascii=False, sort_keys=True))
        return sorted(normalized)

    is_ready = result.get("resolver_result", {}).get("outcome") == "ready"
    first_path = directory / "turn-1.json"
    first = json.loads(first_path.read_text()) if first_path.exists() else result
    output = {"case": session["case"]["title"], "turn_number": session["turn_number"],
        "expected_first_decision": rubric["first_decision"],
        "actual_decision": result.get("resolver_result", {}).get("outcome"),
        "first_actual_decision": first.get("resolver_result", {}).get("outcome"),
        "exact_task_match": canonical(tasks) == canonical(rubric["expected_tasks"]) if is_ready else None,
        "contract_accepted": result.get("validation", {}).get("accepted", False),
        "required_knowledge_cited": set(rubric["required_knowledge_refs"]) <=
            set(result.get("resolver_result", {}).get("knowledge_refs", [])),
        "question_topics_for_human_review": rubric["question_topics"],
        "forbidden_behaviors_for_human_review": rubric["forbidden_behaviors"],
        "final_grade": "pending_human_review",
        "note": "结构匹配不是整体通过；须查看首轮问句、实际知识返回、恢复及范围。"}
    write_json(directory / f"review-{session['turn_number']}.json", output)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description="澄清实验：check/list/preview无网络；run/resume需--live。")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check")
    commands.add_parser("list")
    p = commands.add_parser("preview")
    p.add_argument("case")
    p.add_argument("--output", type=Path)
    p = commands.add_parser("run")
    p.add_argument("case")
    p.add_argument("--live", action="store_true")
    p.add_argument("--output", type=Path)
    p.add_argument("--max-calls", type=int, default=8, choices=range(1, 21))
    p = commands.add_parser("resume")
    p.add_argument("directory", type=Path)
    p.add_argument("--live", action="store_true")
    p.add_argument("--reply", required=True)
    p.add_argument("--question-reviewed", action="store_true",
        help="已人工确认问句覆盖必要歧义，才提供预设回复，防止给遗漏问题补答案")
    p = commands.add_parser("review")
    p.add_argument("directory", type=Path)
    args = parser.parse_args(argv)
    if args.command == "check":
        result = check_pack()
    elif args.command == "list":
        result = [{"id": c["id"], "场景": c["title"], "问题": c["question"]}
                  for c in load_public("cases.json")["cases"]]
    elif args.command == "preview":
        result = preview(get_case(args.case))
        if args.output:
            # 防止覆盖别人的已有实验输入。
            with args.output.open("x") as handle:
                json.dump(result, handle, ensure_ascii=False, indent=2)
            result = {"preview": str(args.output), "model_calls": 0}
    elif args.command == "review":
        result = review(args.directory)
    else:
        if not args.live:
            parser.error("真实模型入口必须显式添加--live；先用preview检查输入并确认本轮费用预算。")
        if args.command == "run":
            directory = args.output or Path(".runs/clarification-lab") / uuid.uuid4().hex[:12]
            case = get_case(args.case)
            directory.mkdir(parents=True, exist_ok=False)
            turns, max_calls = [], args.max_calls
        else:
            parser.error("新的多轮测试使用 business_analysis_repro.conversation_lab 的 prepare/run；不再投喂预设回复。")
        result = run_turn(directory, case, turns, max_calls)
        result = {"directory": str(directory), "status": result["status"],
                  "proposal": result.get("resolver_result"), "usage": result["usage"]}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
