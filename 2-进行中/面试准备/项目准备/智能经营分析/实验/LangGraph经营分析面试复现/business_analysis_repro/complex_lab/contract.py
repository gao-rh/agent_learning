"""复杂任务清单与通用准入。这里不能读取私有评审标准或按案例 ID 补答案。"""

from datetime import date
from typing import Literal

from pydantic import Field

from ..main_agent.state import StrictModel


class Range(StrictModel):
    start: str
    end: str


class View(StrictModel):
    kind: Literal["total", "month", "year", "annual_months", "quarter"]
    months: list[int] = Field(
        default_factory=list, description="annual_months对应每年选取的月份，如1至7月"
    )
    note: str = Field(default="", description="不完整年/季度、去重与比例聚合等说明")


class Requirement(StrictModel):
    id: str
    label: str
    metric_id: str | None = None
    views: list[View] = Field(default_factory=list)
    status: Literal["active", "pending", "gap", "superseded", "cancelled"]
    reason: str = ""
    replacement_ids: list[str] = Field(
        default_factory=list, description="指向用户已接受替代的需求ID；原缺口仍保留"
    )


class Predicate(StrictModel):
    field: str
    op: Literal["eq", "ne", "lt", "le", "gt", "ge"]
    value: str | int | float | bool


class Task(StrictModel):
    id: str
    requirement_ids: list[str] = Field(min_length=1)
    metric_id: str
    period: Range = Field(description="本期的独立起止日；比较请求不能把本期与基期合并成累计区间")
    comparison_period: Range | None = Field(default=None, description="比较基期的独立起止日")
    views: list[View] = Field(min_length=1)
    group_by: list[str] = Field(
        default_factory=list, description="一个任务内为组合分组；分别拆解要不同任务"
    )
    filters: dict[str, list[str]] = Field(
        default_factory=dict, description="该任务适用的全部筛选；共享渠道/地域逐任务落实，未修改条件保留"
    )
    predicates: list[Predicate] = Field(default_factory=list)
    population: str = Field(default="", description="总体/人群约束；不能从渠道曝光人群变成全平台")
    cohort_rule: str = Field(default="", description="分群事件、日期及固定/动态分群规则")
    definition_version: str = Field(default="", description="当期采用版本")
    baseline_version: str = Field(default="", description="有比较基期时写基期版本")
    comparison_mode: Literal["none", "historical_display", "same_definition"] = "none"
    recompute: bool = False
    purpose: str = Field(
        default="", description="取数/待检验因素/历史展示；不能写未经数据支持的结论"
    )


class Question(StrictModel):
    id: str
    text: str
    owner: Literal["user", "knowledge_owner", "system_capability"]
    affects: list[str] = Field(default_factory=list)


class Delivery(StrictModel):
    type: Literal["report", "chart", "wiki", "table"] = Field(
        description="report/chart/table是内容，wiki是发布目标；写Wiki时同时列出内容项"
    )
    status: Literal["planned", "blocked"] = "planned"
    note: str = ""


class Plan(StrictModel):
    outcome: Literal["clarify", "ready", "partial", "blocked"]
    revision: int = Field(ge=1)
    goal: str
    requirements: list[Requirement] = Field(default_factory=list, max_length=80)
    tasks: list[Task] = Field(default_factory=list, max_length=80)
    questions: list[Question] = Field(default_factory=list)
    question: str = Field(
        default="", description="可选说明；用户问句只写questions，程序直接展示，不要重复抄写"
    )
    delivery: list[Delivery] = Field(default_factory=list)
    knowledge_refs: list[str] = Field(default_factory=list)
    supersedes_revision: int | None = None
    changes: list[str] = Field(default_factory=list)


def reply_text(plan):
    """用户问句以结构化列表为准；旧question字段仍可作为说明。"""
    questions = list(
        dict.fromkeys(
            q.text.strip() for q in plan.questions if q.owner == "user" and q.text.strip()
        )
    )
    return "\n\n".join(questions) if questions else plan.question.strip()


def normalize_plan(plan, knowledge):
    """只补展示文本和已读单版本定义；不修改业务条件、替代或交付目标。"""
    normalized = plan.model_copy(deep=True)
    audit = {}
    reply = reply_text(plan)
    if reply != plan.question:
        normalized.question = reply
        audit["reply"] = {"before": plan.question, "after": reply, "from": "questions.owner=user"}

    definitions = {}
    received_sources = knowledge.received_knowledge_ids()
    for item in knowledge.observations:
        if item.get("tool") == "get_metric_definition":
            definition = item.get("result", {})
            mid = definition.get("metric_id") or item.get("arguments", {}).get("metric_id")
            source_id = definition.get("source", {}).get("id")
            if mid and definition.get("supported") and source_id in received_sources:
                definitions.setdefault(mid, []).append(definition)
    bindings = []
    for task in normalized.tasks:
        observed = definitions.get(task.metric_id, [])
        if not observed:
            continue
        versions = observed[0].get("versions", {})
        # 多版本意味着历史展示/同口径重算的业务选择；不能按最新版本猜。
        if len(versions) != 1 or any(d.get("versions") != versions for d in observed):
            continue
        version, details = next(iter(versions.items()))
        for field, bounds in (
            ("definition_version", task.period),
            ("baseline_version", task.comparison_period),
        ):
            if getattr(task, field) or not bounds:
                continue
            try:
                start, end = date.fromisoformat(bounds.start), date.fromisoformat(bounds.end)
                effective_start = date.fromisoformat(details["effective_from"])
                effective_end = date.fromisoformat(details["effective_to"] or "9999-12-31")
                covered = all(
                    date.fromisoformat(d["availability"]["start"])
                    <= start
                    <= end
                    <= date.fromisoformat(d["availability"]["end"])
                    for d in observed
                )
            except (ValueError, KeyError, TypeError):
                continue
            if covered and effective_start <= start <= end <= effective_end:
                setattr(task, field, version)
                bindings.append(
                    {
                        "task_id": task.id,
                        "metric_id": task.metric_id,
                        "field": field,
                        "before": "",
                        "after": version,
                        "source_id": observed[0]["source"]["id"],
                    }
                )
    if bindings:
        audit["version_bindings"] = bindings
    return normalized, audit


def validate(plan, knowledge, revision):
    """只校验公开能力、引用和内部关系；不判断是否完整回答当前用户需求。"""
    errors = []
    if plan.revision != revision:
        errors.append("任务版本与本轮编号不同")
    if revision > 1 and plan.supersedes_revision != revision - 1:
        errors.append("没有标记被本轮替代的旧版本")
    if set(plan.knowledge_refs) - knowledge.received_knowledge_ids():
        errors.append("引用了未实际读取的来源")
    requirements = {r.id: r for r in plan.requirements}
    if len(requirements) != len(plan.requirements) or len({t.id for t in plan.tasks}) != len(
        plan.tasks
    ):
        errors.append("需求或任务ID重复")
    if plan.outcome in {"ready", "partial"} and (plan.questions or not plan.tasks):
        errors.append("仍有待解决问题或没有当前任务")
    if plan.outcome == "ready" and any(r.status in {"pending", "gap"} for r in plan.requirements):
        errors.append("存在待确认或缺口需求，不能声明全部ready")
    if plan.outcome in {"clarify", "blocked"} and not reply_text(plan):
        errors.append("没有给出待确认/阻断说明")
    delivery_types = {d.type for d in plan.delivery}
    if "wiki" in delivery_types and not delivery_types & {"report", "chart", "table"}:
        errors.append("delivery仅列wiki发布目标，缺少内容项；请按用户要求另列report/chart/table")
    for r in plan.requirements:
        if set(r.replacement_ids) - set(requirements):
            errors.append(f"{r.id}的替代需求不存在")
    normalized = []
    for t in plan.tasks:
        prefix = t.id + "："
        m = knowledge.metrics.get(t.metric_id)
        if not m:
            errors.append(prefix + "指标不存在")
            continue
        if not m["supported"]:
            errors.append(prefix + "该指标能力明确不可用")
            continue
        if m["source"]["id"] not in knowledge.received_knowledge_ids():
            errors.append(prefix + "没有实际读取指标定义")
        if any(
            r not in requirements or requirements[r].status in {"gap", "cancelled", "superseded"}
            for r in t.requirement_ids
        ):
            errors.append(prefix + "任务引用了不存在或不可执行的需求")
        for bounds in (t.period, t.comparison_period):
            if bounds:
                try:
                    start, end = date.fromisoformat(bounds.start), date.fromisoformat(bounds.end)
                    if (
                        start > end
                        or bounds.start < m["availability"]["start"]
                        or bounds.end > m["availability"]["end"]
                    ):
                        errors.append(prefix + "期间倒置或超出资料覆盖")
                except ValueError:
                    errors.append(prefix + "日期格式错误")
        for d in set(t.group_by) | set(t.filters):
            if d not in m["dimensions"]:
                errors.append(prefix + "不支持维度 " + d)
        for d, values in t.filters.items():
            if not values or set(values) - set(m["dimensions"].get(d, [])):
                errors.append(prefix + "不支持枚举 " + d)
        actual = {(p.field, p.op, type(p.value).__name__, str(p.value)) for p in t.predicates}
        required = {
            (p["field"], p["op"], type(p["value"]).__name__, str(p["value"]))
            for p in m["mandatory_predicates"]
        }
        missing = [p for p in m["mandatory_predicates"]
                   if (p["field"], p["op"], type(p["value"]).__name__, str(p["value"]))
                   not in actual]
        if not required <= actual:
            errors.append(prefix + f"指标必选规则未保留（metric_id={t.metric_id}）；"
                          f"predicates缺少={missing}；请从已读定义逐项补入，不修改其他条件")
        if t.definition_version not in m["versions"]:
            errors.append(
                prefix + f"definition_version无效或为空（metric_id={t.metric_id}，"
                f"可选版本={','.join(m['versions'])}）；读取定义后按期间与比较口径选择"
            )
        if t.comparison_period and t.baseline_version not in m["versions"]:
            errors.append(
                prefix + f"baseline_version无效或为空（metric_id={t.metric_id}，"
                f"可选版本={','.join(m['versions'])}）；按基期与比较口径选择"
            )
        if t.comparison_mode == "same_definition" and (
            not t.comparison_period or t.definition_version != t.baseline_version
        ):
            errors.append(prefix + "同口径比较缺基期或版本不一致")
        for view in t.views:
            if view.kind == "annual_months" and (
                not view.months or set(view.months) - set(range(1, 13))
            ):
                errors.append(prefix + "每年累计月份不完整或无效")
        normalized.append(t.model_dump())
    return {
        "accepted": not errors,
        "semantic_only": True,
        "execution_enabled": False,
        "errors": errors,
        "normalized_tasks": normalized,
        "decision": plan.outcome,
        "business_accuracy": "not_evaluated",
    }
