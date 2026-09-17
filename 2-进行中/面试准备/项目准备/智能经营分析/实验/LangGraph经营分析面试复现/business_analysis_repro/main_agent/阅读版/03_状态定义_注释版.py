# 阅读快照：2026-09-07；保留完整原文件，仅增加讲解注释。
# 原文件：/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/state.py
# 原文件 SHA-256：c8087a720ff53bdd7ba37aff0fbb6725d775b402745e5b99625602606f2d65ee
# 本副本用于阅读，不作为可独立运行的脚本；运行请使用原包的 python -m 入口。
# 搜索“剩余阅读”可定位还没按执行顺序讲完的部分；下文行号均指原文件。
# 配套摘要：../代码阅读摘要.md。注释是 Codex 的源码解读，不代表已验收你的理解。

"""先读本文件：State 是程序数据，Proposal 才是让模型填写的结构。

TypedDict 描述图共享的字典；Pydantic 校验不可信的模型输出。
两者职责不同：TypedDict 本身不会在运行时拒绝错误字段。
"""

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field


# ── 模型输出的格式约束｜原文件 14–46 行 ──
# 这几个 Pydantic 类校验模型输出的字段和类型，不代表业务事实自动正确。
# Proposal 是理解提议；Reply 是草稿；Verdict 是模型复核意见。
class StrictModel(BaseModel):
    # 模型不能私自增加 status、permission 等字段。
    model_config = ConfigDict(extra="forbid")


# ── 把时间语义与日期计算分开｜原文件 19–25 行 ──
# 例如“上周”先表达为 calendar / week / -1；精确起止日期由 calendar_tools 计算。
class Period(StrictModel):
    """模型理解“上周”，代码计算真正的日期，不让模型做日历运算。"""

    mode: Literal["exact", "calendar", "rolling"]
    unit: Literal["day", "week", "month", "year"]
    offset: int = Field(default=0, ge=-12, le=0)
    exact_date: str | None = None


# ── 模型只填写提议｜原文件 28–36 行 ──
# 业务状态 status 不在 Proposal 里。模型不能凭一句“完成”直接结束整个任务。
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


# ── 共享工作数据｜原文件 49–69 行 ──
# RootState 是我们定义的字典结构；Root 只是主图的命名，不是额外的模型记忆。
# 节点读当前 State，返回需要更新的字段；框架再合并 patch 并按图路由。
# 传给节点的 State 与发给 Kimi 的 messages 是两件事，后者由 model.complete 的 payload 决定。
class RootState(TypedDict):
    """由我们定义的父图状态，没有任何字段会自动变成模型上下文。

    除 messages 外所有字段默认覆盖。节点只 return 更新，不原地改 state。
    messages 的 add_messages 按消息 ID 合并，避免恢复时重复追加同一条消息。
    不把 API key、客户端、权限服务、Trace 对象塞入可持久化的 State。
    """

    # ── 合并规则 ──
    # messages 用 add_messages 按 ID 合并；其余字段默认用新值覆盖旧值。
    # 当前 messages 只有问题及澄清问答；最终 answer 没有自动追加成 assistant 消息。
    messages: Annotated[list[AnyMessage], add_messages]
    reference_date: str  # 一次任务冻结的北京时间基准日，恢复后不会漂移
    task_revision: int  # 每次重新理解任务递增，使旧证据失效
    task: dict | None  # 代码准入后的标准任务，函数只接收这个字段
    # ── status 是程序控制信号 ──
    # running=执行中；waiting_user=缺信息等待；completed=校验通过；failed=明确失败。
    # 这些值由本项目代码选择，LangGraph 不会自动替我们判断业务完成。
    status: Literal["running", "waiting_user", "completed", "failed"]
    pending_question: str | None
    clarification_count: int
    # ── 从事实到最终输出 ──
    # result 是能力结果；draft_reply 是待检查文本；validation 记录问题及修复方向。
    # answer 是可交付回答或确定性失败说明。不要直接把 draft_reply 当最终结果返回。
    result: dict | None  # 包含来源、模拟标识、事实、证据 ID 和错误
    draft_reply: dict | None
    validation: dict | None
    repair_count: int  # 最终回复最多重写一次；不影响取数次数
    capability_retry_count: int  # 结果契约不合格时，最多重新调用能力一次
    answer: str  # 只有校验完成，或确定性失败响应，才写入最终输出


# ── 最初的 State｜原文件 72–90 行 ──
# 只在新任务创建时调用；resume 使用 SQLite 已保存状态，不重新初始化。
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
