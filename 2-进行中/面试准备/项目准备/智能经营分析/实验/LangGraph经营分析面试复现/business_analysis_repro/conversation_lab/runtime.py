"""新多轮实验入口：AI 用户驱动原执行器，不靠私有评分推进对话。"""

import hashlib
import json
from pathlib import Path

from ..experiment_support import write_snapshot
from ..main_agent.runtime import locked
from ..playground.usage import PRICE, summarize
from ..settings import get_kimi_settings
from .budget import events
from .simulator import decide

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).parent
BOUNDARIES = {
    "query": "执行支持的查询，数据来自本地模拟SQLite；不支持线上取数或Wiki发布。",
    "complex": "只确认复杂任务计划；不执行SQL、归因、报告生成或Wiki发布。",
    "knowledge": "只检索知识、澄清并形成语义任务；不查询业务数值。",
}


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else ({} if default is None else default)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def sources():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted([*HERE.glob("*.py"), HERE / "profiles.json"])}


def configuration():
    settings = get_kimi_settings()
    return {"model": settings.model_name, "base_url": settings.base_url,
            "temperature": 0.6, "thinking": "disabled", "max_output_tokens": 1800}


def public_cases(kind):
    from ..clarification_lab.knowledge import FIXTURES

    path = (ROOT / "complex_lab/fixtures/cases.json" if kind == "complex" else
            FIXTURES / ("simple_query_cases.json" if kind == "query" else "cases.json"))
    return read(path)["cases"]


def prepare(root, kind, cases, max_turns=6, max_requests=30):
    root = Path(root)
    if kind not in BOUNDARIES or not 1 <= max_turns <= 10 or not 1 <= max_requests <= 30:
        raise ValueError("未知实验类型；最多10轮/30次合计请求")
    if not cases or len(cases) > 10 or len(set(cases)) != len(cases):
        raise ValueError("明确选择1至10个不重复案例")
    public = {c["id"]: c for c in public_cases(kind)}
    if set(cases) - public.keys():
        raise ValueError("未知案例")
    model = configuration()
    profiles = read(HERE / "profiles.json")
    if kind == "query":
        from ..clarification_lab import query_smoke
        query_smoke.prepare(root, max_requests=max_requests, selected_cases=cases)
    elif kind == "complex":
        from ..complex_lab import runtime
        runtime.prepare(root, cases)
    else:
        from ..clarification_lab.experiment import manifest
        root.mkdir(parents=True, exist_ok=False)
        write(root / "batch.json", {"profile": "knowledge-ai-user-v1", "kind": kind,
                                    "case_ids": cases, "model": model, "manifest": manifest()})
    batch = read(root / "batch.json")
    frozen_profiles = {}
    for cid in cases:
        c = public[cid]
        frozen_profiles[cid] = {"initial_request": c["turns"][0]["user_message"] if kind == "query" else c["question"],
                                "preferences": profiles["common"], "facts": "", "agenda": [],
                                **profiles[kind].get(cid, {})}
    batch["simulation"] = {"protocol": "ai-user-v1", "model": model, "max_turns": max_turns,
        "manifest": sources(), "profiles": frozen_profiles,
        "boundary": BOUNDARIES[kind], "price_reference": PRICE,
        "limits": {"requests": max_requests, "tokens": 1200000, "estimated_cny": 8,
                   "input_bytes_per_request": 120000},
        "grading": "动态对话不套用固定回复的逐轮标准；公开契约检查后审阅实际记录。",
        "capability_policy": "不能完整完成时，明确具体缺口并取得用户选择；不要求缺口项具备完整执行字段。"}
    batch["kind"] = kind
    write(root / "batch.json", batch)
    hashes = batch["manifest"].get("sha256", batch["manifest"])
    write_snapshot(root, ROOT, {**hashes, **sources()})
    return {"directory": str(root.resolve()), "cases": cases, "kind": kind,
            "user_mode": "AI模拟用户", "model_calls": 0, "limits": batch["simulation"]["limits"]}


def record_path(root, kind, cid, number):
    return root / (f"{cid}-turn-{number}.json" if kind == "query" else f"{cid}/turn-{number}.json")


def render_plan(record, boundary):
    """展示实际提交的计划与缺口，不补任务、不编造业务回答。"""
    plan = record.get("resolver_result", {})
    labels = {"active": "可支持", "pending": "待确认", "gap": "做不了/缺口",
              "superseded": "已替代", "cancelled": "已取消"}
    rows = [boundary]
    for req in plan.get("requirements", []):
        rows.append(f"{req['label']}：{labels.get(req['status'], req['status'])}" +
                    (f"；{req['reason']}" if req.get("reason") else ""))
    rows.extend(render_tasks(record, "complex"))
    for delivery in plan.get("delivery", []):
        rows.append(f"交付计划 {delivery['type']}：{delivery['status']}；{delivery.get('note', '')}")
    if plan.get("question"):
        rows.append(plan["question"])
    return "\n".join(rows)


def render_tasks(record, kind):
    catalog = read(ROOT / ("complex_lab" if kind == "complex" else "clarification_lab") / "fixtures/catalog.json")
    names = {m["id"]: m["name"] for m in catalog["metrics"]}
    dimensions = catalog["dimensions"]
    tasks = record.get("validation", {}).get("normalized_tasks", [])
    rows = []
    for task in tasks:
        fields = [names.get(task["metric_id"], "未识别指标")]
        for key, label in (("period", "期间"), ("comparison_period", "基期")):
            if task.get(key):
                fields.append(label + json.dumps(task[key], ensure_ascii=False))
        for dim, values in task.get("filters", {}).items():
            d = dimensions.get(dim, {})
            enums = {v["id"]: v["name"] for v in d.get("values", [])}
            fields.append(d.get("name", dim) + "=" + "、".join(enums.get(v, v) for v in values))
        fields.append("分组=" + ("、".join(dimensions.get(d, {}).get("name", d) for d in task.get("group_by", [])) or "整体汇总"))
        if task.get("views"):
            view_names = {"month": "按月", "year": "按年", "annual_months": "每年指定月份累计", "total": "合计", "quarter": "按季度"}
            fields.append("展示=" + "、".join(view_names[v["kind"]] + (str(v["months"]) if v.get("months") else "") for v in task["views"]))
        for key, label in (("population", "人群"), ("cohort_rule", "分群规则"), ("definition_version", "口径版本"), ("baseline_version", "基期版本")):
            if task.get(key):
                fields.append(label + "=" + task[key])
        rows.append("；".join(fields))
    return rows


def review(record):
    failed = record.get("status") == "execution_error" or record.get("validation", {}).get("accepted") is False
    return {"grade": "failed" if failed else "pending_human_review", "checks": [],
            "note": "按原始需求、AI用户实际选择与助手实际结果审阅；用户结束不等于测试通过。能力缺口应明确告知并确认。"}


def assistant_turn(root, batch, cid, session, pending, model_factory=None):
    kind = batch["kind"]
    number = session["turns"] + 1
    meta = pending["origin"]
    if kind == "query":
        from ..clarification_lab.query_smoke import step
        return step(root, cid, model_factory=model_factory, user_message=pending["message"],
                    simulation_input=meta)
    if kind == "complex":
        from ..complex_lab.runtime import run_turn
        run_turn(root, cid, reply=pending["message"] if number > 1 else None,
                 model_factory=model_factory, simulation_input=meta)
    else:
        from ..clarification_lab.__main__ import run_turn
        case = next(c for c in public_cases(kind) if c["id"] == cid)
        history = session["dialogue"][session["background_size"] + 1:]
        history = [{"role": "human" if m["role"] == "user" else "ai", "content": m["content"]}
                   for m in history]
        if number > 1:
            history.append({"role": "human", "content": pending["message"]})
        run_turn(root / cid, case, history, max_calls=8, model_factory=model_factory)
    path = record_path(root, kind, cid, number)
    result = read(path)
    result.update({"question": pending["message"], "input_origin": meta["role"], "simulated_user": meta})
    result["answer"] = (render_plan(result, batch["simulation"]["boundary"]) if kind == "complex" else
                        "\n".join([batch["simulation"]["boundary"], *render_tasks(result, kind),
                                   result.get("resolver_result", {}).get("question", "")]))
    write(path, result)
    write(root / cid / f"review-{number}.json", review(result))
    return result


def step(root, cid, assistant_factory=None, user_factory=None):
    root = Path(root)
    with locked(root / "simulated-users"):
        batch = read(root / "batch.json")
        config = batch.get("simulation", {})
        if config.get("protocol") != "ai-user-v1" or config["manifest"] != sources():
            raise ValueError("不是AI用户批次或测试源码已变化；请新建批次")
        if cid not in batch["case_ids"]:
            raise ValueError("案例不在冻结清单中")
        if not user_factory and config["model"] != configuration():
            raise ValueError("AI用户模型配置已变化")
        # 在任何付费请求之前核对被测实现/公开资料；不因评分失败截断对话。
        if batch["kind"] == "complex":
            from ..complex_lab.runtime import sources as native_sources
        elif batch["kind"] == "query":
            from ..clarification_lab.query_smoke import frozen_manifest as native_sources
        else:
            from ..clarification_lab.experiment import manifest as native_sources
        if batch["manifest"] != native_sources():
            raise ValueError("被测源码/资料已变化；请新建批次")
        folder = root / "simulated-users" / cid
        path = folder / "session.json"
        profile = config["profiles"][cid]
        spec = next(c for c in public_cases(batch["kind"]) if c["id"] == cid)
        background = [{"role": "user" if m["role"] in {"user", "human"} else "assistant", "content": m["content"]}
                      for m in spec.get("history", [])]
        session = read(path, {"turns": 0, "cursor": 0, "dialogue": background,
                              "background_size": len(background), "finished": False,
                              "pending": {"message": profile["initial_request"], "origin": {"role": "fixture_user"}}})
        if session["finished"]:
            return session
        if not session.get("pending"):
            decision_path = folder / f"after-{session['turns']}" / "decision.json"
            actor = read(decision_path)
            if not actor:
                if session.get("stage") == "simulating_user":
                    session.update(finished=True, stop_reason="AI用户调用被中断；保留记录，不自动重复付费")
                    write(path, session)
                    return session
                session["stage"] = "simulating_user"
                write(path, session)
                actor = decide(root, cid, session["turns"], profile, session["dialogue"], session["cursor"],
                               config["boundary"], model_factory=user_factory)
                write(decision_path, actor)
            session["last_user_decision"] = actor
            if actor["status"] != "completed":
                session.update(finished=True, stop_reason="AI用户调用失败或预算耗尽", stage="stopped")
            elif actor["decision"]["action"] == "finish":
                session.update(finished=True, stop_reason=actor["decision"]["stop_reason"], stage="stopped")
            elif session["turns"] >= config["max_turns"]:
                session.update(finished=True, stop_reason="达到助手轮数上限，AI用户仍想继续；未完成", stage="stopped")
            else:
                session["cursor"] = actor["decision"]["agenda_cursor"]
                session["pending"] = {"message": actor["decision"]["message"], "origin": actor}
                session["stage"] = "user_ready"
            write(path, session)
            if session["finished"]:
                return session
        target = record_path(root, batch["kind"], cid, session["turns"] + 1)
        # 崩溃后已有落盘结果则接着使用；付费调用中断且没有完整结果时明确停住。
        record = read(target)
        if not record:
            if session.get("stage") == "assistant_running":
                session.update(finished=True, stop_reason="助手调用被中断；保留Trace，不自动重复付费")
                write(path, session)
                return session
            session["stage"] = "assistant_running"
            write(path, session)
            try:
                record = assistant_turn(root, batch, cid, session, session["pending"], assistant_factory)
            except Exception as exc:  # noqa: BLE001 -- 实验边界落盘并停止，不重复付费
                session.update(finished=True, stop_reason="助手执行失败，保留原始记录", error_type=type(exc).__name__)
                write(path, session)
                return session
        session["dialogue"].extend([{"role": "user", "content": session["pending"]["message"]},
                                  {"role": "assistant", "content": record["answer"]}])
        session.update(turns=session["turns"] + 1, pending=None, stage="assistant_finished")
        if record["status"] not in {"completed", "waiting_user", "waiting_review"}:
            session.update(finished=True, stop_reason="助手运行异常，尚未完成对话")
        write(path, session)
        return session


def run(root, cid, assistant_factory=None, user_factory=None):
    while True:
        session = step(root, cid, assistant_factory, user_factory)
        if session["finished"]:
            return summary(root)


def summary(root):
    root = Path(root)
    batch = read(root / "batch.json")
    all_events = events(root)
    actor_events = [e for p in root.glob("simulated-users/*/after-*/trace.jsonl")
                    for e in read_lines(p)]
    actor_ids = {e["run_id"] for e in actor_events}
    value = {"protocol": "ai-user-v1", "usage": summarize(all_events),
             "assistant_usage": summarize([e for e in all_events if e["run_id"] not in actor_ids]),
             "simulated_user_usage": summarize(actor_events),
             "cases": {cid: read(root / "simulated-users" / cid / "session.json") for cid in batch["case_ids"]},
             "grade": "pending_record_review", "note": "按实际对话审阅；停止原因不作为通过率。"}
    write(root / "simulation-summary.json", value)
    return value


def read_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]
