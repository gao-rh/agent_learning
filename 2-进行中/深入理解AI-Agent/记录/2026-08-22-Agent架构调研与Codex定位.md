# 2026-08-22 Agent架构调研与 Codex 定位

## 原始问题

现在的 Agent 架构有哪些？Codex 用的是 ReAct、Plan-and-Execute，还是其他架构？希望得到充分调研后、尽可能最新且代表广泛工程实践的回答。

## 用户理解

- 用户假设：ReAct 和 Plan-and-Execute 可能是用来判定一个 Agent 属于哪种整体架构的互斥选项。
- 用户追问教材“上下文”一节中的 Agent“状态栏”机制，并描述为：Harness 向当前模型调用注入运行状态，复杂任务时状态栏会包含 Todo/Plan。查证后，这个描述与教材的 System Hint / Agent Status Bar 机制基本一致；`preamble` 和 `phase: "commentary"` 是 Codex 初次回答时错误引入的另一套机制。
- 用户尚未表达对这些概念的稳定结论。
- 用户已明确决定：Agent 架构模式是后续必须重点学习的内容，其中必须包括 Anthropic 和 Google 的分类。

## Codex 反馈

### 已调研事实

- ReAct 原论文指的是“推理轨迹与环境动作交错生成”，它首先是一种控制/提示模式，不是一套完整的生产运行时架构。
- 当前主流工程资料普遍区分预定代码路径的 workflow 与由模型动态决定工具和步骤的 agent，并强调两者可以组合。
- 常见组合模式包括：顺序链、路由、并行 fan-out/fan-in、动态规划与执行、评估者-优化者循环、中央编排者-工作者、handoff/群聊、人在回路。
- 2026-08-19 的 OpenAI 官方文章把 Codex 公开定位为一个由 open-source harness 驱动的 Agent 循环：管理上下文和会话状态、调用工具、流式事件、沙箱/审批边界与跨轮工作。
- OpenAI 已公开 GPT-5.6 的 Multi-agent beta：根 Agent 可以生成并行子 Agent、分配边界清晰的工作并汇总结果。
- 新的生产架构越来越把“模型”、“harness/控制循环”、“session/持久状态”、“tools/sandbox”视为可独立演进的层，而不是只用 ReAct 一个词概括整个系统。

### Codex 概括

- ReAct、Plan-and-Execute、Reflection 更适合叫“控制策略/编排模式”；完整 Agent 架构还要包含 harness、state/context、tools/sandbox、memory/retrieval、guardrails/approval、observability/evals。
- 当前最具代表性的生产形态不是单一论文标签，而是“确定性 workflow/graph + 局部动态 Agent tool loop + 必要时的评审、记忆、人工审批和子 Agent”的混合架构。
- Codex 的公开行为可以说是 ReAct-like：它会在工具调用与观察结果之间反复循环；但不应据此断言它就是论文原版 ReAct。它还会规划、重规划、验证，并在适合时进行多 Agent 分工，因此更准确的名称是“harness 管理的混合型工具 Agent”。

### 未知/待验证

- OpenAI 并未公开当前 Codex 模型在每一轮内部究竟采用哪种专有 planner/search/reasoning 算法；不能把可观察的工具循环等同于未公开的模型内部实现。
- 没有可靠、统一的全行业“Agent 架构市场份额”数据；“广泛使用”只能根据 OpenAI、Anthropic、Google、LangGraph、AutoGen 等官方文档中的模式收敛来判断，不能伪装成精确排名。

### 本轮追问：Agent 状态栏与 commentary phase

- 教材原文确实使用 **Agent Status Bar**，实验目录同时称它为 **System Hint**：Harness 保存结构化真实状态，每次调用模型前把当前状态渲染成临时消息，追加到上下文末尾。
- 教材状态栏可包含时间戳、工具调用计数器、Todo 列表、详细错误、当前目录和系统环境；复杂任务自动建 Todo 只是其中一种功能。
- 教材 Todo 项使用 `pending / in_progress / completed / cancelled` 四态；这四态属于 Todo item，不是整个 Agent 唯一的生命周期状态。
- 更通用的工程表达是 `agent state`、`task state`、`runtime state`、`state snapshot`、`dynamic state summary` 或 `runtime context injection`；`Agent Status Bar` 是该教材可以成立的形象名称，但不是统一标准术语。
- `preamble` 是 Agent 在工具调用前发送给用户的一小段可见说明；`phase: "commentary"` 是 assistant 中间消息的协议标签。二者都不等于教材的 System Hint / Agent Status Bar。
- Codex 当前会话在功能上也接收宿主注入的环境与运行上下文，并可维护外部 Plan；但不能据此断言 Codex Desktop 与教材实验一样使用临时 `role=user` 消息实现。

## 发散联想

- MCP、A2A、Function Calling 是协议/接口或动作机制，不是与 ReAct 同层级的完整架构。
- RAG、长期记忆、Skills 主要解决“给当前一步什么上下文”，也不直接决定控制流属于 ReAct 还是 Plan-and-Execute。
- CodeAct/程序化工具调用正在上升：让模型写一段受控代码组合多个工具调用，适合边界明确的 tool-heavy 子流程，但不适合需要每步新鲜模型判断的开放任务。

## 结论状态

- 问题：待继续

原因：本轮完成了资料调研和 Codex 答案，但用户尚未用自己的话确认对“控制策略 vs. 完整架构”的理解。

## 后续动作

- 后续必须安排 Agent 架构模式专题学习：必须覆盖 Anthropic 和 Google ADK 的分类，并对齐两套术语及其与 ReAct、Plan-and-Execute、Codex Harness 的层级关系。
- 实践时可用同一个小任务对照跑三种控制流：纯 tool loop、显式 Plan-and-Execute、外层 planner + 内层 tool loop，比较成功率、工具调用数、重规划能力、延迟和 token 成本。

## 本轮主要来源

- OpenAI, *Codex as a platform: build on the open agent harness*, 2026-08-19.
- OpenAI, *Multi-agent* 与 *Using GPT-5.6*, 当日查阅。
- Anthropic, *Building effective agents*, 2024-12-19（页面已指向 2026 年当前架构文章）。
- Anthropic, *Scaling Managed Agents: Decoupling the brain from the hands*, 2026-04-08.
- Google Developers, *Developer’s guide to multi-agent patterns in ADK*, 2025-12-16.
- Yao et al., *ReAct: Synergizing Reasoning and Acting in Language Models*, ICLR 2023.
- LangGraph 当前官方文档：Agent = Model + Harness，以及工具循环/图编排说明。
