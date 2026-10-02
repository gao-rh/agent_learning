"""实验语义契约：显式比较期和必选谓词，不扩展正式查询器的执行能力。

验证只读模型输出和公开目录，从不读案例标准答案；错误只报告，不补答案。
"""

from datetime import date
from typing import Literal

from pydantic import Field, StrictBool, StrictInt, StrictStr

from ..calendar_tools import calculate_business_period
from ..main_agent.state import StrictModel
from ..playground.agent import TimeSpec
from ..playground.parallel_state import BatchResolution, MetricRequest


class Predicate(StrictModel):
    field_id: str
    operator: Literal["eq", "ne"]
    value: StrictBool | StrictInt | StrictStr


class MissingItem(StrictModel):
    field: str
    reason: str
    owner: Literal["user", "knowledge_owner", "system_capability"]


class LabRequest(MetricRequest):
    comparison_period: TimeSpec | None = Field(default=None, description="明确的基期；分析比较时必填")
    required_predicates: list[Predicate] = Field(default_factory=list,
        description="从所选指标定义中读到的必选业务规则，不是任意SQL")


class LabResolution(BatchResolution):
    requests: list[LabRequest] = Field(default_factory=list, max_length=20)
    missing_items: list[MissingItem] = Field(default_factory=list)
    knowledge_refs: list[str] = Field(default_factory=list,
        description="本轮实际读取并用于决定的来源ID：业务知识记录id或指标定义source.id")


def resolve_period(spec: TimeSpec | None, reference_date: str):
    if spec is None:
        return None
    if spec.mode == "range":
        if not spec.start_date or not spec.end_date or spec.exact_date or spec.offset:
            raise ValueError("range必须只提供明确起止日期")
        start, end = spec.start_date, spec.end_date
    else:
        if spec.start_date or spec.end_date:
            raise ValueError("非range不接受起止日期")
        resolved = calculate_business_period(reference_date=reference_date, mode=spec.mode,
            unit=spec.unit, offset=spec.offset, exact_date=spec.exact_date)
        start, end = resolved["start_date"], resolved["end_date"]
    start, end = date.fromisoformat(start).isoformat(), date.fromisoformat(end).isoformat()
    if start > end:
        raise ValueError("起止日期倒置")
    return {"start": start, "end": end}


def predicate_key(predicate):
    # bool 与 int 在Python中可能相等，类型也必须参与业务规则比较。
    return (predicate["field_id"], predicate["operator"],
            type(predicate["value"]).__name__, str(predicate["value"]))


def validate_submission(proposal, knowledge):
    raw = LabResolution.model_validate(proposal.model_dump() if hasattr(proposal, "model_dump") else proposal)
    errors, tasks, transforms = [], [], []
    if raw.outcome == "ready" and not raw.requests:
        errors.append("ready没有任务")
    if raw.outcome == "ready" and raw.missing_items:
        errors.append("仍有未解决条件，不能ready")
    if raw.outcome in {"clarify", "unsupported"} and not raw.question.strip():
        errors.append("没有向用户解释等待或不支持的原因")
    unknown_refs = set(raw.knowledge_refs) - knowledge.received_knowledge_ids()
    if unknown_refs:
        errors.append("引用了本轮未实际收到的业务知识：" + ",".join(sorted(unknown_refs)))
    # clarify的候选不当成可执行任务，不把不完整候选误判成任务失败。
    if raw.outcome == "ready":
        for i, request in enumerate(raw.requests):
            prefix = f"任务{i+1}（metric_id={request.metric_id}）："
            if request.metric_id not in knowledge.metrics:
                errors.append(f"任务{i+1}指标不存在")
                continue
            metric = knowledge.metrics[request.metric_id]
            task = request.model_dump()
            try:
                for field in ("period", "comparison_period"):
                    task[field] = resolve_period(getattr(request, field), knowledge.catalog["reference_date"])
                    transforms.append({"request": i, "field": field,
                        "before": request.model_dump()[field], "after": task[field]})
                    if task[field] and (task[field]["start"] < metric["availability"]["start"]
                                       or task[field]["end"] > metric["availability"]["end"]):
                        errors.append(f"任务{i+1}时间超出模拟目录范围")
                if request.intent != "knowledge" and task["period"] is None:
                    errors.append(prefix + "period缺少当期；用户未给日期时提交clarify询问日期，不能ready")
                if request.intent == "analysis" and task["comparison_period"] is None:
                    errors.append(prefix + "comparison_period缺少显式基期")
                if request.intent != "analysis" and task["comparison_period"] is not None:
                    errors.append(f"任务{i+1}非比较任务却包含基期")
            except (ValueError, TypeError) as exc:
                errors.append(f"任务{i+1}日期无效：{exc}")
            for dimension in set(request.group_by) | set(request.filters):
                if dimension not in metric["dimensions"]:
                    errors.append(f"任务{i+1}不支持维度{dimension}")
            for dimension, values in request.filters.items():
                if not values or any(v not in metric["dimensions"].get(dimension, []) for v in values):
                    errors.append(f"任务{i+1}枚举不支持：{dimension}")
            declared = {predicate_key(p) for p in task["required_predicates"]}
            required = {predicate_key(p) for p in metric["mandatory_predicates"]}
            if declared != required:
                errors.append(prefix + "required_predicates与已读定义不一致；"
                              f"要求={metric['mandatory_predicates']}，实际={task['required_predicates']}")
            tasks.append(task)
    return {"accepted": raw.outcome == "ready" and not errors,
            "semantic_only": True, "execution_enabled": False,
            "errors": errors, "normalized_tasks": tasks, "transformations": transforms,
            "decision": raw.outcome, "business_accuracy": "not_evaluated"}
