# 2026-08-28 LangGraph 面试复现学习与实验计划

> 计划状态：复现深度已确认选择 B“面试完整型”；实验结果均尚未发生。日历排期为 AI 建议，按有效学习日推进，待结合实际可用时间调整。

## 原始问题

用户希望为了 Agent 开发面试，使用 LangChain、LangGraph、LangSmith 对智能经营分析项目做脱敏复现。学习路径需要明确：先读哪些官方文档，读完做什么实验，实验完成后如何继续；最低要能够独立创建一个多节点、多 Agent 的流程，跑完一次带循环的完整执行，并查看完整 Trace。

## 用户理解

- 目标不是把原项目所有业务细节和生产能力重新开发一遍。
- 需要通过真实编码加深对 LangChain、LangGraph、LangSmith 的理解，而不只是简单调用框架。
- 用户已明确选择 B“面试完整型”复现。

## 已确认事实

1. 原项目真实使用公司内部 Agent 平台，LangChain/LangGraph 只能表述为离职后的等价学习复现，不能倒写成原项目技术栈。
2. 本地复现只使用模拟指标库、模拟业务事件、模拟查询 Tool 和模拟数据。
3. 第一阶段最低验收是：多节点、至少两个真正的工具 Agent、一条有限循环、一次完整执行、一个可展开的 LangSmith Trace。
4. 本仓库可以承载面试导向的小型学习复现；若扩展为正式服务、复杂 UI 或生产平台，则必须迁移到独立仓库和独立任务。

## 未知项

- 实验使用哪个真实模型 Provider 及 API Key；前两个实验不依赖该决定。
- 每天实际可投入多少时间；当前仅按 10 个有效学习日设计。
- LangSmith 账号、API Key 和数据区域是否已经准备好。
- 是否需要在第一版加入显式 Subgraph；先跑通普通 Agent Node 后再判断。

## 本次关键问题

复现应该做到什么深度，才能既支撑面试追问，又不发展成偏离目标的正式产品开发？

## 方案比较

| 方案 | 范围 | 代价 | 结论 |
| --- | --- | --- | --- |
| A 极速演示型 | 单图、少量 Tool、仅 Trace | 3～4 个有效学习日，深入追问较弱 | 未选 |
| B 面试完整型 | 多节点、双 Agent、循环、持久化、Trace、约 10 个评测案例 | 7～10 个有效学习日 | 用户已选 |
| C 工程强化型 | 增加 API、部署、数据库、并发和监控 | 2～3 周，容易偏离面试目标 | 未选 |

## 用户决定

> 已确认选择 B“面试完整型”。

## Codex 反馈

本次不应从“多 Agent”概念反推架构。更严格的设计是：顶层 LangGraph 控制确定性阶段，只有需要模型反复选择 Tool 的节点才使用 LangChain Agent。这样既能形成真实的多 Agent 流程，也能在面试中解释为什么没有把澄清、校验和报告格式保护全部交给模型。

### 第一阶段目标架构

```text
START
  → plan_request（结构化 LLM Node）
  → data_agent（Agent Loop：指标检索 / 查询 Tool）
  → evidence_validator（确定性 Node）
      ├─ 证据失败且未超限 → data_agent
      ├─ 指标歧义 → interrupt → resume
      └─ 证据通过 → analysis_agent
  → analysis_agent（Agent Loop：下拆 / 漏斗 Tool）
  → report_generator（结构化 LLM Node）
  → report_validator（确定性 Node）
      ├─ 失败且未超限 → analysis_agent 或 report_generator
      └─ 通过 → END
```

其中只有 `data_agent` 和 `analysis_agent` 必须实现完整的“模型 → Tool → ToolMessage → 模型”循环。规划和报告节点虽然调用 LLM，但若没有自主 Tool 循环，不能为了包装而称为 Agent。

## 必须掌握的知识边界

| 模块 | 必须会实现 | 必须会解释 | 第一阶段不要求 |
| --- | --- | --- | --- |
| LangChain | Message、Tool、结构化输出、`create_agent`、Tool Loop | 模型只提出调用，代码执行 Tool；schema 与业务校验的边界 | RAG、复杂 middleware、所有 Provider |
| LangGraph | State、reducer、Node、Edge、条件路由、循环、`Command`、checkpoint、interrupt | Workflow 与 Agent、状态增量、有限循环、恢复与幂等 | 正式部署、大规模并行 |
| Multi-agent | 两个 Tool Agent 嵌入顶层 Graph，并限制各自 Tool/上下文 | 为什么拆 Agent；Node、Agent、Subgraph 的区别 | 多层 Supervisor、Handoff 网络 |
| LangSmith | Project、Trace、Run、tag、metadata、完整调用树 | Trace 与 checkpoint 的区别；怎样从 Trace 定位失败 | 在线监控和告警 |
| 评测 | 约 10 个脱敏 Case、确定性路径/指标/澄清 evaluator | 最终答案正确不等于执行轨迹正确 | 大规模 LLM Judge |

官方资料阅读顺序见：[LangChain、LangGraph、LangSmith 官方学习索引](../../../../../2-进行中/面试准备/项目准备/智能经营分析/资料/2026-08-28-LangChain-LangGraph-LangSmith官方学习索引.md)。

## 固定学习循环

每个实验均执行以下步骤：

1. Codex 说明本实验只验证哪个机制，不扩展其他功能。
2. 展示固定语料、输入、预期路径、唯一主要变量和验收证据。
3. 用户先预测 State、消息或路由将怎样变化。
4. 用户亲自运行代码。
5. 用户描述实际现象和与预测不一致的位置。
6. Codex 纠错，补充严格定义、反例和面试追问。
7. 用户脱离代码解释机制；必要时做一个反例 Case。
8. 只有解释与证据均通过后，才把问题从“待继续/待验证”改为“已理解”。

## 实验路线

| 实验 | 先学什么 | 实验内容 | 主要输入 | 验收证据 | 状态 |
| --- | --- | --- | --- | --- | --- |
| E0 职责地图 | 官方索引第 0 组 | 画出 LangChain → LangGraph → LangSmith 的关系，并区分 Trace/checkpoint | 一次简单查数请求 | 用户能脱稿解释三个组件与两个“回溯”的区别 | 待继续 |
| E1 Tool Loop 解剖 | 第 1 组 | 先手写一次 Tool Calling 循环，再用 `create_agent` 跑同一 Tool | “查询 2026-08-01 的保费收入” | 能展示 `AIMessage.tool_calls`、匹配的 `ToolMessage` 和最终消息 | 待继续 |
| E2 纯多节点 Graph | 第 2 组 | 不使用真实模型，实现解析、路由、查询、校验、报告和有限重试 | 正常指标、非法指标各 1 条 | 能打印每个 Node 的 State 增量，并证明循环最多执行指定次数 | 待继续 |
| E3 多节点双 Agent | 第 3 组 | 把 `data_agent` 与 `analysis_agent` 嵌入顶层 Graph | “分析本周保费下降的主要原因” | 两个 Agent 各调用受限 Tool，父图完成查询—分析—报告闭环 | 待继续 |
| E4 暂停、恢复与回放 | 第 4 组 | SQLite checkpoint、指标歧义 interrupt、同线程 resume、失败 replay/fork | 一个命中两个候选指标的模糊表达 | 关闭并重新运行后可恢复；能列出历史 checkpoint 并形成不同分支 | 待继续 |
| E5 完整 Trace | 第 5 组前半 | 打开 LangSmith tracing，为节点和运行增加 tag/metadata，故意制造一次失败 | E3 正常 Case + E4 失败 Case | Trace 中能展开父图、两个 Agent、模型、Tool、校验和重试；用户能定位失败 Run | 待继续 |
| E6 小评测与面试复盘 | 第 5 组后半 | 约 10 个脱敏 Case，比较两版路由或 Prompt | 完全匹配、歧义、越界、固定分析、开放分析等 | 输出实验对比；完成 5 分钟架构讲解和关键追问 | 待继续 |

### E1 固定实验语料草案

模拟指标库只保留三个指标：

| metric_id | 标准名 | 别名 | 查询方式 |
| --- | --- | --- | --- |
| `premium_income` | 保费收入 | 保费、保费金额 | 内存数据 Tool |
| `order_count` | 投保订单量 | 订单数、投保量 | 内存数据 Tool |
| `refund_rate` | 退保率 | 退款率 | 内存数据 Tool |

固定查询：`查询 2026-08-01 的保费收入。`

E1 只观察 Tool Call 消息循环，不同时引入 LangGraph、持久化、RAG 或业务事件—指标校验。

### E2 固定循环草案

```text
parse_request → metric_lookup → query_metric → validate
                                         ↑        |
                                         └─ retry ┘
```

主要变量只有 `validation_passed` 和 `retry_count`；预期失败 Case 在达到最大重试次数后安全结束，不能形成无限循环。

### E3 多 Agent 验收定义

要称为“多节点双 Agent 已跑通”，必须同时提供以下证据：

1. 顶层 Graph 至少包含规划、数据 Agent、证据校验、分析 Agent、报告、报告校验节点。
2. `data_agent` 和 `analysis_agent` 具有不同的 System Prompt 与 Tool 集合。
3. 两个 Agent 均实际产生过 Tool Call，不是两个普通函数被改名为 Agent。
4. 至少一条路径发生过校验失败后回到上游的有限循环。
5. 最终输出中的标准指标名和数值能够追溯到结构化 `MetricEvidence`。

### E5 完整 Trace 验收定义

LangSmith 中至少能看到以下层级：

```text
root graph trace
├── plan_request / model run
├── data_agent
│   ├── model run
│   ├── search_metric tool run
│   ├── model run
│   └── query_metric tool run
├── evidence_validator
├── analysis_agent
│   ├── model run
│   └── breakdown 或 funnel tool run
├── report_generator / model run
└── report_validator
```

如果 Trace 只能看到最终输入输出、看不到 Agent 内部模型与 Tool Run，则不算完成。

## 规划窗口与里程碑

> 下列日历日期是 AI 建议；用户只确认了 B 的深度，尚未确认每天投入时长。

- 规划窗口：2026-08-28 至 2026-09-10，共 10 个有效学习日，允许不连续。
- 第 1 个检查点：有效学习日 1，完成 E0 与 E1；建议不晚于 2026-08-30。
- 第 2 个检查点：有效学习日 3，完成 E2；建议不晚于 2026-09-02。
- 第 3 个检查点：有效学习日 6，完成 E3；建议不晚于 2026-09-06。
- 最低目标检查点：有效学习日 9，完成 E4 与 E5；建议不晚于 2026-09-09。
- B 型完整验收：有效学习日 10，完成 E6 与面试复盘；建议 2026-09-10 检查。

## 对计划的影响

- 下一步不直接开发完整经营分析项目，先从 E0/E1 建立 Tool Loop 的可观察证据。
- 已按用户要求创建[LangGraph 经营分析面试复现](../../../../../2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/README.md)目录；当前只有环境配置、依赖锁定和无模型 smoke，不包含 E1 业务实现。
- 每个真实模型实验先运行 3～5 个代表性 Case；扩大到约 10 个评测 Case 前重新说明调用量和费用。
- 第一阶段实现达到 E5 后，先进行一次面试追问验收，再决定是否增加 Subgraph、并行分析或长期 Memory。

### 2026-08-28 环境准备记录

- 使用 `uv 0.10.9` 与 CPython 3.12.13 创建项目内 `.venv`；
- 已生成 `pyproject.toml` 与 `uv.lock`，安装 LangChain 1.3.18、LangGraph 1.2.11、LangSmith 0.11.2、LangGraph SQLite checkpoint 3.1.1；
- 已验证最小 LangGraph 编译与执行，输出 `environment_ready`；
- pytest 结果为 `1 passed`，Ruff 结果为 `All checks passed`；
- LangSmith tracing 默认关闭，没有产生外部 Trace；
- 本次状态仅为“环境准备已机器验证”，E0/E1 仍保持待继续。

## 发散联想

- 原项目的“澄清—执行—验证”可以自然映射为 Graph 的受控状态机，但不能因此推断原项目已经使用 LangGraph。
- “多 Agent”最有价值的学习点不是 Agent 数量，而是上下文隔离、Tool 权限、状态传递和失败边界。
- 指标选择事故适合用来演示：Tool 执行成功不等于业务目标正确；最终答案流畅也不等于执行轨迹可信。

## 结论状态

- B“面试完整型”复现深度：已理解
- 官方资料阅读顺序：待继续
- 多节点双 Agent 完整循环：待验证
- LangGraph checkpoint、interrupt 与 time travel：待继续
- LangSmith 完整 Trace：待验证

## 后续动作

1. 阅读官方资料索引第 0 组，共 3 个页面，只回答三个组件的职责和边界。
2. 用户用自己的话画出“模型/Tool—Graph—Trace/checkpoint”关系，不先写项目代码。
3. 开始 E1 前先确认模拟指标表、唯一查询和预期 Tool 消息序列。
4. 在已验证的复现目录中，由用户开始搭建 E1；环境 smoke 不计入 E1 学习完成。

## 下次只讨论什么

E0：LangChain、LangGraph、LangSmith 的职责，以及 LangSmith Trace 与 LangGraph checkpoint 的区别。
