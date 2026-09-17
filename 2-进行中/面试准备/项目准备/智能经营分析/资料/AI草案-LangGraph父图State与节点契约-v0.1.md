# AI 草案：LangGraph 父图 State 与节点契约 v0.1

> 日期：2026-09-06。状态：AI 草案 / 待确认。基于[已确认的粗粒度技术方向](../记录/2026-09-06-LangGraph技术架构方向确认.md)细化，仅讨论父图。本轮未编写产品代码，未调用模型或执行数据查询。

## 本块需要确定的边界

父图保存用户任务、子能力的交付结果和回复校验状态；分析假设、查询批次和接口重试过程分别归对应子图保存。

此次新增的 task_id、task_revision、status、字段写入责任和结果类型是待确认建议，不反向标记为此前已经确认。

## RootState 字段与写入责任

| 字段 | 保存内容 | 更新者 | 生命周期与规则 |
| --- | --- | --- | --- |
| messages | 用户与助手对话 | 应用输入、对话输出节点 | 会话级，按消息 ID 合并；模型仅读取必要上下文 |
| task_id | 当前业务任务标识 | 请求初始化代码 | 每个任务唯一；同一任务的澄清恢复保持不变 |
| task_revision | 当前任务范围版本 | 任务更新代码 | 指标、时间或业务范围变更时推进，用于判断旧结果是否仍可用 |
| task | 目标、业务对象、时间、主要意图与交付要求 | understand_request 提议，validate_task 校验后接纳 | 不包含权限或预算的最终决定 |
| status | 当前任务阶段 | 路由与控制代码 | 用于展示与检查，不直接接受模型任意填写 |
| result | 子能力交付的结构化结果或异常 | 包装节点、知识节点 | 带来源与任务版本；新调用开始时避免误用旧结果 |
| pending_question | 缺失条件、问题及请求来源 | 澄清准备节点 | 回答处理完成后清除；暂停点由运行时检查点记录 |
| draft_reply | 完整待交付回复 | compose_reply | 基于当前版本的结果生成；对应结果失效时同步失效 |
| validation | 对当前回复的校验结果、问题与责任模块 | validate_reply | 与具体回复绑定；回复修改后重新校验 |
| repair_count | 当前任务已执行的返修次数 | 返修控制代码 | 重新调用子图不重置全任务返修上限 |

表中“写入责任”是设计约定，需要代码只接纳相应字段来落实；类型标注本身不构成权限保护。

```python
# 概念伪代码；结构与字段仍待确认。
TaskSpec = {
    "primary_intent": "query | analysis | knowledge",
    "goal": "用户希望解决的问题",
    "scope": {...},              # 业务对象、指标、时间与必要约束
    "deliverable": "交付要求",
}

CapabilityResult = {
    "task_id": "...",
    "task_revision": 1,
    "source": "query | analysis | knowledge",
    "status": "ok | partial | need_clarification | failed",
    "payload": {...},            # 数据引用、知识证据或报告
    "issues": [...],             # 缺失条件、错误、已知限制
}

ValidationResult = {
    "status": "passed | needs_repair | failed",
    "issues": [...],
    "repair_target": "reply | query | analysis | knowledge | none",
}
```

一次能力调用的状态与整个用户任务的阶段分开：例如 QueryGraph 返回 need_clarification 后，父图可进入 waiting_user；进入该状态前仍须生成问题并实际触发暂停。

## 节点输入输出

| 节点 | 读取 | 返回的字段更新 / 行为 | 实现性质 |
| --- | --- | --- | --- |
| prepare_request | 新请求、会话上下文 | 初始化任务执行字段，保留需要的会话信息 | 代码 |
| understand_request | messages、task、必要知识 | 候选 task、缺失条件 | 模型提出结构化内容 |
| validate_task | 候选 task、可信运行上下文 | 接纳规范任务，或形成澄清 / 能力限制 | 代码准入，必要的知识核实由工具完成 |
| clarify | pending_question | interrupt 暂停；回答校验后更新任务并清除问题 | 公共澄清逻辑；模型可以负责问题表达 |
| query_wrapper | task 与必要反馈 | QueryGraph 输出映射为 result | 状态转换与子图调用 |
| analysis_wrapper | task、可复用证据与反馈 | AnalysisGraph 最终输出映射为 result | 状态转换与子图调用 |
| knowledge_tools | task 与可信调用身份 | 带来源的知识 result | 受控工具调用 |
| handle_result | result、当前 task_revision | 继续回复、准备澄清，或调整 / 停止 | 代码分类，复杂解释可调用模型 |
| compose_reply | 当前 task、result、相关对话 | draft_reply | 模型 |
| validate_reply | draft_reply、result、task | validation | 代码检查 + 模型辅助检查 |
| route_repair | validation、repair_count、任务预算 | 推进计数，选择允许的责任模块 | 代码；不得无限返修 |

候选 task 与已接纳 task 在实现时需要明确区分，例如单独字段或节点间专用输入；不能让未校验提议覆盖执行中的规范任务后就被下游使用。这里先确定该责任边界，暂不扩张字段数量。

## 建议的阶段枚举与路由

```text
understanding → executing → responding → validating → completed
      │             │                        │
      └→ waiting_user ←───────────────────────┘（仅需要用户补充时）
              │
              └→ 补充后恢复原任务阶段

任一阶段确认无法继续 → 生成边界说明 → stopped
```

status 是便于观察的阶段字段，实际条件路由仍要检查 task、result、validation 与预算，不只依据一个字符串决定是否放行。

规则建议：

1. result.status=ok，且结果适用于当前任务版本：进入 compose_reply。
2. result.status=partial：只有已有证据能支持有限回答时才生成回复，并明确缺失部分；不能当作完整成功。
3. result.status=need_clarification：准备问题并暂停；回答后只恢复需要补充的任务，不重新完成所有步骤。
4. result.status=failed：只允许在可恢复且未超限时重做，否则生成限制说明。不能把失败解释成空数据。
5. validation.status=passed：交付当前已校验回复。
6. validation.status=needs_repair：依据错误来源返修，并保留全任务返修计数。
7. 无法形成有效回复时，以代码可构造的最小失败说明结束；不得为了生成失败说明又进入无限校验循环。

## 一条用于确认方向的例子

用户问：“分析上周保费为什么下降。”

1. 父图形成主要意图为 analysis 的 task，确定业务对象和比较周期等必要范围。
2. analysis_wrapper 传入 AnalysisTask，分析子图自己查证是否下降、取数与下钻。
3. 分析子图如果中途澄清，未完成的调用通过检查点暂停；应用展示问题，同任务恢复，不伪造一个已完成 result。
4. 分析子图结束后返回 ok 或 partial 的报告结果、证据与限制。
5. 父图组织完整回复，然后检查指标名称、数字和论据。
6. 如果只是报告把标准指标名改成了不准确口语，返修回复；如果基础查询不适用于目标业务，带反馈回到相应责任模块。

## 本轮未定

- 新业务任务、连续追问和对已有任务范围的修改，如何分别建立 task_id / task_revision。
- 复合请求如何组合多个能力结果；当前单个 result 是一次调用的抽象，不能直接当作多个并发结果的最终容器。
- 返修携带哪些可复用证据，哪些结果必须失效，如何保存返修历史。
- TaskSpec 与错误类型的完整字段、权限实现、预算持久化以及具体最大次数。
- 父图和子图共同处理的澄清格式，以及子图暂停时如何向界面投影状态。

本轮的核心待确认点：是否按字段责任表划分父图的状态，而把分析细节和查询细节留在各自子图中。

[返回项目入口](../README.md)
