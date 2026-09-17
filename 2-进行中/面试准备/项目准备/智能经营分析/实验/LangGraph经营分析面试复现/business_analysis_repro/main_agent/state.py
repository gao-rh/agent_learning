"""先读本文件：State 是程序数据，Proposal 才是让模型填写的结构。

TypedDict 描述图共享的字典；Pydantic 校验不可信的模型输出。
两者职责不同：TypedDict 本身不会在运行时拒绝错误字段。
"""

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    # 模型不能私自增加 status、permission 等字段。
    model_config = ConfigDict(extra="forbid")


class Period(StrictModel):
    """模型理解“上周”，代码计算真正的日期，不让模型做日历运算。"""

    mode: Literal["exact", "calendar", "rolling"]
    unit: Literal["day", "week", "month", "year"]
    offset: int = Field(default=0, ge=-12, le=0)
    exact_date: str | None = None


class Proposal(StrictModel):
    """只表达模型对用户意图的判断，不代表已经通过执行准入。"""

    intent: Literal["query", "analysis", "knowledge", "unsupported"]
    business: str | None = None
    metric: str | None = None
    period: Period | None = None
    clarification: str | None = None
    reason: str = ""


class Reply(StrictModel):
    text: str = Field(min_length=1, max_length=5000)
    evidence_ids: list[str]


class Verdict(StrictModel):
    passed: bool
    issues: list[str]


class RootState(TypedDict):
    """由我们定义的父图状态，没有任何字段会自动变成模型上下文。

    除 messages 外所有字段默认覆盖。节点只 return 更新，不原地改 state。
    messages 的 add_messages 按消息 ID 合并，避免恢复时重复追加同一条消息。
    不把 API key、客户端、权限服务、Trace 对象塞入可持久化的 State。
    """

    messages: Annotated[list[AnyMessage], add_messages]
    reference_date: str  # 一次任务冻结的北京时间基准日，恢复后不会漂移
    task_revision: int  # 每次重新理解任务递增，使旧证据失效
    task: dict | None  # 代码准入后的标准任务，函数只接收这个字段
    status: Literal["running", "waiting_user", "completed", "failed"]
    pending_question: str | None
    clarification_count: int
    result: dict | None  # 包含来源、模拟标识、事实、证据 ID 和错误
    draft_reply: dict | None
    validation: dict | None
    repair_count: int  # 最终回复最多重写一次；不影响取数次数
    capability_retry_count: int  # 结果契约不合格时，最多重新调用能力一次
    answer: str  # 只有校验完成，或确定性失败响应，才写入最终输出


def initial_state(question: str, reference_date: str) -> RootState:
    """初始化属于应用入口，不需要额外注册一个“初始化节点”。"""
    from langchain_core.messages import HumanMessage

    return {
        "messages": [HumanMessage(content=question)],
        "reference_date": reference_date,
        "task_revision": 0,
        "task": None,
        "status": "running",
        "pending_question": None,
        "clarification_count": 0,
        "result": None,
        "draft_reply": None,
        "validation": None,
        "repair_count": 0,
        "capability_retry_count": 0,
        "answer": "",
    }
