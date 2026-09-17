# LangChain、LangGraph、LangSmith 官方学习索引

> 核对日期：2026-08-28。本文只保存本次面试复现直接需要的官方资料，不追求完整覆盖框架所有功能。框架 API 可能更新，真正编码前仍需核对对应页面。

## 使用方式

每组资料都按以下顺序学习：

1. 带着该组的“读完必须回答”阅读，不做无目的通读。
2. 关闭文档，用自己的话回答问题并画出关键流程。
3. 在写代码前预测节点、状态或消息将怎样变化。
4. 用户亲自运行并描述现象，Codex 再纠错和补充边界。
5. 命令成功只表示“已运行”，不等于“已理解”。

## 第 0 组：先建立三个产品的职责地图

| 官方资料 | 只需要重点看什么 | 读完必须回答 |
| --- | --- | --- |
| [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) | LangGraph 定位、核心能力、与 LangChain/LangSmith 的关系 | 为什么 LangGraph 不是模型框架？什么任务值得用它？ |
| [LangChain Agents](https://docs.langchain.com/oss/python/langchain/agents) | Agent、模型、Tool、Agent Loop；`create_agent` 与 LangGraph 的关系 | `create_agent` 帮你预置了什么？为什么复杂流程仍可能需要显式 Graph？ |
| [LangSmith tracing quickstart](https://docs.langchain.com/langsmith/observability-quickstart) | Trace、嵌套 Run、输入输出和 Tool/模型调用 | LangSmith 看见了什么？它能不能代替 LangGraph checkpoint？ |

对应动作：不用写业务代码，先把“模型与 Tool → Graph 执行 → Trace 观测”画成一张图。

## 第 1 组：LangChain 最小基础

| 官方资料 | 只需要重点看什么 | 暂时跳过什么 |
| --- | --- | --- |
| [Messages](https://docs.langchain.com/oss/python/langchain/messages) | `HumanMessage`、`AIMessage`、`ToolMessage`、`tool_calls`、`tool_call_id` | 多模态 content block 细节 |
| [Models](https://docs.langchain.com/oss/python/langchain/models) | `invoke`、Tool Calling、结构化输出 | Embedding、向量库和复杂 Provider 配置 |
| [Tools](https://docs.langchain.com/oss/python/langchain/tools) | `@tool`、参数 schema、描述如何影响选择、Tool 输出 | Server 专属高级 Runtime 字段 |
| [Structured output](https://docs.langchain.com/oss/python/langchain/structured-output) | Pydantic schema、ProviderStrategy/ToolStrategy 的基本区别、校验失败 | 高级错误定制和复杂联合 schema |

读完必须回答：

1. 模型提出 Tool Call 后，谁真正执行 Python 函数？
2. `AIMessage.tool_calls` 和 `ToolMessage.tool_call_id` 为什么必须对应？
3. Tool 的参数校验、业务校验和模型判断分别位于哪一层？
4. 什么时候应该返回结构化对象，而不是自由文本？

对应实验：手写一次 Tool Loop，再用 `create_agent` 运行同一组 Tool，比较框架替你做掉了哪些工作。

### 已选模型 Provider：Kimi

E1 使用此前实验已采用的 Kimi K2.6 国内 API。补充阅读：

- [Kimi API 快速开始](https://platform.kimi.com/docs/overview)：只看 OpenAI 兼容接口、`MOONSHOT_API_KEY`、模型和 Endpoint；
- [Kimi Tool Calls](https://platform.kimi.ai/docs/guide/use-kimi-api-to-complete-tool-calls)：重点看完整 Tool Call 六步链路和 `tool_call_id`；
- [Kimi Tool Choice](https://platform.kimi.ai/docs/guide/use-tool-choice)：理解 `auto`、`required`、`none`；
- [Kimi K2.6](https://platform.kimi.com/docs/guide/kimi-k2-6-quickstart)：重点看禁用 thinking 与 Tool Use 参数兼容性。

E1 不使用 Kimi 官方工具，先由本地 Python 提供两个模拟指标 Tool，以便完整观察“模型提出调用—应用执行—结果回填”。

## 第 2 组：LangGraph 状态与流程控制

| 官方资料 | 只需要重点看什么 | 读完必须回答 |
| --- | --- | --- |
| [Graph API overview](https://docs.langchain.com/oss/python/langgraph/graph-api) | State、Node、Edge、reducer、conditional edge、`Command`、`Send` | State 是数据库还是一次执行的共享快照？Node 应返回完整 State 还是增量？ |
| [Use the Graph API](https://docs.langchain.com/oss/python/langgraph/use-graph-api) | 顺序、分支、循环、并行、状态更新 | 普通 Edge、conditional edge 和 `Command(goto=...)` 如何选？ |
| [Workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents) | Workflow 与 Agent、routing、parallelization、orchestrator-worker | 哪些经营分析步骤必须确定，哪些才适合交给 Agent？ |

对应实验：先不调用真实模型，使用纯 Python 节点实现“解析 → 路由 → 查询 → 校验 → 报告”，并构造一次校验失败后的有限重试循环。

## 第 3 组：多节点、多 Agent 组合

| 官方资料 | 阅读目的 | 当前结论 |
| --- | --- | --- |
| [Multi-agent overview](https://docs.langchain.com/oss/python/langchain/multi-agent/index) | 理解 subagents、handoffs、router、skills、custom workflow 的差异 | 多 Agent 不是目标本身；只有上下文、Tool 或责任确实需要隔离时才拆 |
| [Custom workflow](https://docs.langchain.com/oss/python/langchain/multi-agent/custom-workflow) | 学会在 LangGraph Node 内嵌 LangChain Agent | 本次经营分析复现的主模式 |
| [Subagents](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents) | 理解主 Agent 把子 Agent 当 Tool 调用的模式 | 作为对比学习，不作为第一版主结构 |
| [Subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs) | 理解子图的状态隔离、持久化和可观测性 | 第一版跑通后，再决定是否把两个 Agent 提升为显式子图 |

本次第一版采用：

- 顶层 `StateGraph` 负责确定性的阶段控制和失败循环；
- `data_agent` 只拥有指标检索与查询 Tool；
- `analysis_agent` 只拥有下拆与漏斗分析 Tool；
- 规划、证据校验、报告生成和报告校验先作为普通 Node；
- 只有真正发生“模型 → Tool → 结果 → 模型”的循环才称为 Agent。

## 第 4 组：持久化、暂停恢复与回放

| 官方资料 | 重点 | 对应验收 |
| --- | --- | --- |
| [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | checkpoint、thread、state history、SQLite 与 Postgres saver 定位 | 能解释 `thread_id` 如何关联状态，能列出同一线程的历史 checkpoint |
| [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) | `interrupt()`、`Command(resume=...)`、恢复时节点重新执行、幂等副作用 | 指标歧义时暂停，使用相同线程恢复，且不会重复产生不可控副作用 |
| [Time travel](https://docs.langchain.com/oss/python/langgraph/use-time-travel) | replay 与 fork | 从校验前 checkpoint 重放，并修改指标选择形成另一条分支 |
| [Streaming](https://docs.langchain.com/oss/python/langgraph/streaming) | `updates`、`values`、子图事件 | 可选；先能打印节点更新，不要求先做 UI |

## 第 5 组：LangSmith Trace 与评测

| 官方资料 | 重点 | 对应验收 |
| --- | --- | --- |
| [Observability concepts](https://docs.langchain.com/langsmith/observability-concepts) | Project、Trace、Run、Thread、tag、metadata | 能从一次 Trace 还原父图、两个 Agent、模型和 Tool 调用 |
| [Tracing quickstart](https://docs.langchain.com/langsmith/observability-quickstart) | 开启 tracing、查看嵌套 Run | 能打开真实 Trace，定位一次耗时或错误发生在哪个 Run |
| [Evaluation](https://docs.langchain.com/langsmith/evaluation) | dataset、evaluator、experiment、offline/online evaluation | 用约 10 个脱敏案例运行一次离线实验，先使用确定性 evaluator |
| [Evaluate an LLM application](https://docs.langchain.com/langsmith/evaluate-llm-application) | `evaluate()`、输入输出 schema、比较实验 | 第一阶段 Trace 跑通后再学，不作为启动前置 |

## 当前不作为前置的内容

- Deep Agents、完整 Handoff 框架和复杂 Supervisor；
- 正式部署、LangGraph Server、多租户和鉴权；
- 长期 Memory Store、复杂上下文工程；
- 向量数据库、完整 RAG、MCP；
- 在线评测、告警和大规模并发；
- 前端聊天界面。

这些内容可以用于回答生产化追问，但不能阻塞第一条多节点、多 Agent、带循环和 Trace 的链路。

## 数据与费用边界

- 所有上传 LangSmith 的输入、输出和 metadata 必须是脱敏模拟数据，不使用公司原始名称、数据、Prompt 或内部接口信息。
- 前两个实验优先使用纯 Python 或 Fake/Mock Model；开始真实模型实验前，先说明新增案例数、预计模型调用次数、Token 和费用范围。
- 第一轮真实模型只跑 3～5 个代表性 Case；完整批量评测必须再次明确确认。
