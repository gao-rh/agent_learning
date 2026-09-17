"""v4：父图拥有计划，分支只拿自己的 job，结果用 job_id 合并。

先读本文件，再读 parallel_model.py 的 Prompt，最后读 parallel_agent.py。
State 是程序数据；模型不能自行设置 job_id、状态、重试次数或可信结果。
旧版 RootState / 七节点实验不改，方便对照阅读和回放旧任务。
"""

from copy import deepcopy
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import Field

from ..main_agent.state import StrictModel
from .agent import TimeSpec


class MetricRequest(StrictModel):
    metric_id: str
    intent: Literal["query", "analysis", "knowledge"] = "query"
    period: TimeSpec | None = None
    group_by: list[str] = Field(default_factory=list, max_length=3)
    filters: dict[str, list[str]] = Field(default_factory=dict)


class BatchResolution(StrictModel):
    outcome: Literal["ready", "clarify", "unsupported", "catalog", "reply"]
    requests: list[MetricRequest] = Field(default_factory=list, max_length=20)
    question: str = ""
    decomposition: str = Field(
        default="", description="简述拆分依据、同查/分查关系；不写模型内部推理。"
    )


def merge_results(left: dict, right: dict) -> dict:
    """并行节点不能一起覆盖同一个普通字典字段，必须声明 reducer。

    不原地修改输入。相同 job 的相同写入可重放；相同 ID 的冲突结果拒绝，
    不能采用“谁最后返回就听谁的”。重新理解时由父节点显式清空结果。
    """
    if right.get("__reset__") is True:
        if len(right) != 1:
            raise ValueError("reset 必须是独立父节点更新")
        return {}
    merged = deepcopy(left)
    for job_id, value in right.items():
        if job_id in merged and merged[job_id] != value:
            raise ValueError(f"同一子任务发生冲突写入：{job_id}")
        merged[job_id] = deepcopy(value)
    return merged


class BatchState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    request_start: int  # 本版完整需求在messages中的起点；之前的旧范围保留作历史
    response_kind: str  # conversation / business，普通对话不冒充经过数据证据复核
    context_memory: dict  # 本轮使用的历史摘要与业务条件；不是新的业务证据
    engine_version: str
    reference_date: str
    task_revision: int
    task: dict | None  # 给后续对话的计划摘要，包含 jobs；不是一个单指标 task
    jobs: list[dict]  # 稳定顺序的可信计划；job_id / task 均由程序生成
    job_results: Annotated[dict, merge_results]
    status: str  # running / waiting_user / completed / partial / failed / cancelled
    pending_question: str | None
    clarification_count: int
    answer: str
    result: dict | None  # 有序汇总（含失败条目），不是任意一个分支的结果
    draft_reply: dict | None
    validation: dict | None
    repair_count: int
    draft_note_revision: int
    steering_messages: list[dict]
    steering_notes: list[str]


class WorkerState(TypedDict):
    job: dict  # Send 的局部输入；没有别的指标结果和整段聊天历史
