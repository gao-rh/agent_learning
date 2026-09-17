# 2026-09-06 LangGraph 技术架构方向确认

> 状态：粗粒度技术方向已确认；详细字段、节点契约和实现仍待逐块确认与验证。这是拟采用的 LangGraph 设计，不是原生产系统的实现证据，也不代表用户已完成相关学习。

## 用户原话与确认范围

用户提出：

> 你再生成一个LangGraph的实现的话，它的技术架构的设计，就是状态什么，就是接近于伪代码一个程度吧你可以先做的粗力度一点，我先确认一下方向对不对，然后再做更细力度的。

Codex 给出父图、分析子图、共享取数子图各自的 State、流程与恢复方式后，用户确认：

> 我觉得没问题。

此次确认适用于该轮粗粒度设计。后续新增的字段、枚举、预算数值、存储选型和节点实现不随之自动成为已确认内容。

## 已确认的技术方向

| 图 | 职责 | 结束边界 |
| --- | --- | --- |
| RootGraph 父图 | 请求理解、任务范围、能力路由、最终回复与校验 | 本次请求完成或明确停止 |
| AnalysisGraph 分析子图 | 查证事实、选择方法、规划取数、计算、下钻与报告 | 分析完成，或返回已有结论与限制 |
| QueryGraph 共享取数子图 | 查询准入、工具执行、受限修复与数据检查 | 返回可用数据或明确错误 |

- 主 Agent 对应父图中的理解请求、组织回复等节点，不要求把主角色的全部逻辑放进一个函数。
- 父图和分析子图可复用同一个 QueryGraph 定义，各次查询保存独立状态。
- 分析子图内部管理多轮查询和分析，不要求每轮退出子图、返回父图再重新调度。
- 模型提出目标或动作，代码检查参数、权限、预算与允许的路由，图运行时执行。
- 每张图有自己的 State；包装节点负责父子图的输入输出转换。
- 大表和报告文件留在相应存储中，State 保存引用、必要摘要、查询参数和检查信息。
- 最终校验覆盖主 Agent 已经组织好的完整回复。表达问题限次返修；数据或分析问题带反馈交回责任模块。
- 取数子图不直接问用户；它返回缺失条件或明确错误，由调用方决定澄清、调整或停止。
- 分析中途需要澄清时，在分析子图内暂停，应用统一显示问题；补充后恢复原任务。
- 用户身份、权限服务、工具连接和全任务预算通过可信运行上下文提供。局部分析轮次、查询尝试次数与全任务预算分开。

## 粗粒度 State 基线

```python
# 概念伪代码；类型尚未实现。
class RootState:
    messages: list[Message]
    task: TaskSpec
    result: CapabilityResult
    draft_reply: str
    validation: ValidationResult
    repair_count: int
    pending_question: Clarification | None

class AnalysisState:
    task: AnalysisTask
    method: AnalysisMethod
    pending_queries: list[QuerySpec]
    evidence: dict[QueryId, DataRef]
    decision: AnalysisDecision
    round_count: int
    report: AnalysisReport | None
    pending_question: Clarification | None

class QueryState:
    query: QuerySpec
    resolved_query: ResolvedQuery
    data: DataRef | None
    checks: DataCheckResult
    attempt_count: int
    error: QueryError | None
```

消息按消息合并规则更新；查询证据按查询 ID 合并；普通任务字段按明确的覆盖规则更新。每个节点只返回自己的字段更新，模型只读取当前步骤所需的上下文。

## 粗粒度执行流程

```text
父图
prepare_request → understand_request → validate_task
  ├─ 缺条件 → 澄清并更新任务 → validate_task
  ├─ 直接查数 → query_wrapper
  ├─ 经营分析 → analysis_wrapper
  ├─ 知识咨询 → knowledge_tools
  └─ 无法支持 → 能力限制说明
                         ↓
                   handle_result
                         ↓
                   compose_reply
                         ↓
                   validate_reply
  ├─ 通过 → END
  ├─ 表达问题 → 限次返修
  ├─ 数据或分析问题 → 带反馈交回责任模块
  └─ 无法修复 → 说明限制并结束

分析子图
prepare_analysis → decide_next_step → validate_action
  ├─ 需要数据 → execute_query_batch → 合并结果或错误 → decide_next_step
  ├─ 需要计算 → calculation_tools → decide_next_step
  ├─ 缺条件 → 澄清并暂停 → 更新条件 → decide_next_step
  ├─ 证据足够 → write_report → END
  └─ 达到上限或无法继续 → summarize_partial_result → END

取数子图
resolve_query → validate_query → execute_query → check_data
  ├─ 数据检查通过 → 返回数据、参数与检查信息 → END
  ├─ 可恢复 → 在次数和预算内重试或修正；修改查询需再次准入
  └─ 不支持、缺条件、权限不足或无法修复 → 返回明确错误 → END
```

取数返回缺失条件时，handle_result 或分析子图中的决策节点将其转为待澄清状态；暂停不作为分析子图已完成处理。

## 暂停与返修的区别

- 中途澄清：使用检查点和 interrupt 暂停，同一 thread_id 下通过 Command(resume=...) 恢复未完成任务。暂停节点会重执行，因此副作用需隔离或保证幂等。
- 已结束子图的返修：携带反馈和仍然适用的证据重新调用。不能把一次新的调用声称为自动恢复到已结束子图的内部步骤；复用与失效规则待细化。

## 新旧资料关系

- [2026-08-28 整体拓扑架构规划讨论](../../../../../5-归档/智能经分与智能质检/2026-09-08/智能经营分析/记录/2026-08-28-整体拓扑架构规划讨论.md)保留早期讨论，不改写历史确认。
- [成熟 Data Agent 主体架构调研](../../../../../5-归档/智能经分与智能质检/2026-09-08/智能经营分析/记录/2026-08-30-成熟Data-Agent主体架构调研.md)提供公开案例与历史设计讨论；本轮采用可在分析子图内复用受控查询能力的分工。
- [v4 讨论图预览](/Users/gaoronghui/.codex/visualizations/2026/09/05/01a072a4-f534-7953-9fb5-72e11916db44/data-agent-architecture-v4-preview.html)位于当前电脑的 Codex 图目录，属于本地展示资料。历史项目版本号与此图的 v4 无关。
- 图中没有单独绘出的能力探索、上下文记忆及复合请求细节，不应视为已决定删除；按后续节点设计明确。

## 下一块与未决事项

- 第一块细化为[父图 State 与节点契约 v0.1 草案](../资料/AI草案-LangGraph父图State与节点契约-v0.1.md)。本次“没问题”不覆盖该草案中新增的详细设计。
- 待定：任务与会话的生命周期、复合请求执行计划、澄清次数、返修次数与任务预算、父子图字段映射、证据复用条件、取消和进程恢复的落地方式。
- 下次检查：下次讨论父图设计时；未另定日期。
- 尚未实现或运行本文伪代码。

## 已查阅的官方机制说明

本会话前一轮已查阅，具体框架行为仍以实际锁定版本为准。

- [Graph API：State、节点、条件边与 reducer](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [Subgraphs：父子图通信与状态](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)
- [Interrupts：暂停、恢复与重执行](https://docs.langchain.com/oss/python/langgraph/interrupts)

[返回项目入口](../README.md)
