# 2026-08-28 E1：Kimi Tool Calling 准备

## 原始问题

用户确认大模型 API 继续使用此前的 Kimi，并希望先做最简单的工具使用/Function Calling，同时询问初始默认有哪些工具可选。

## 用户理解

- 用户主动纠正：当前还不能算完整 Workflow，更接近最简单的工具使用。
- 当前待确认假设：模型或框架是否会提供一组默认工具。
- 用户在看到完整机器执行结果后反馈：目前还不能读懂实现代码，需要从入口开始逐行理解主循环、消息变化和各层职责。
- 用户初步复述：开始时有 System Prompt、User Prompt 和工具定义；Kimi 返回 Function Calling；应用执行所有工具并回传结果；Kimi 再生成最终结果。随后追问当前通用的执行日志追溯方法。

## Codex 反馈

严格来说，本实验是一个 **Tool Calling Loop**，不是经营分析 Workflow：

```text
用户问题
→ 应用把 Tool 定义和 messages 发给 Kimi
→ Kimi 选择是否调用 Tool，并生成函数名与 JSON 参数
→ Python 根据函数名执行本地函数
→ 应用把 ToolMessage 追加回 messages
→ Kimi 根据工具结果生成最终回复
```

普通 Kimi Chat Completions 和 LangChain Agent 都没有自动注入的业务工具：

- 不传 `tools`：模型可用工具为 0；
- 传入哪些 Tool：模型本轮只能从这些 Tool 中选择；
- `tool_choice` 省略时等于 `auto`，模型可以调用，也可以不调用；
- Kimi 官方 `web-search`、`date`、`code-runner` 等仍需应用显式接入，不属于普通请求的默认工具；
- 模型只生成调用意图和参数，真正执行 Python 函数的是应用代码。

逐行导读先按运行顺序拆解 `tool_calling_demo.py`。核心观察对象是 `messages`：初始包含
`SystemMessage + HumanMessage`，第一次 Kimi 调用后追加带 `tool_calls` 的 `AIMessage`，
本地执行后追加匹配同一 `tool_call_id` 的 `ToolMessage`，第二次调用后追加最终 `AIMessage`。
暂不把机器运行成功提升为用户已理解。

对用户复述的严格校准：`messages` 初始只有 `SystemMessage + HumanMessage`，工具定义通过
`bind_tools` 作为模型请求的 `tools` 参数提供，不是第三条消息；应用是在遍历本轮
`tool_calls`，不是持续轮询外部状态；第二次 Kimi 调用负责根据 `ToolMessage` 综合生成自然语言答案。
执行追溯需要区分结构化日志、LangChain Callback、LangGraph Stream、Checkpoint、分布式 Trace
和可视化界面，Studio 只是其中的调试展示层。

官方依据：

- [Kimi Tool Calls](https://platform.kimi.ai/docs/guide/use-kimi-api-to-complete-tool-calls)
- [Kimi Tool Choice](https://platform.kimi.ai/docs/guide/use-tool-choice)
- [Kimi 官方工具](https://platform.kimi.ai/docs/guide/use-official-tools)

## E1a 实验设计

### 只验证什么

验证 Kimi 能在两个候选本地工具中选择正确工具，并完成一次“模型 → Tool → 模型”的闭环。暂不加入 LangGraph、数据库、RAG、checkpoint 或 LangSmith。

### 模拟语料

```text
metric_id: premium_income
标准名: 保费收入
定义: 指定日期内成功承保订单对应的保费金额合计
2026-08-01 模拟值: 128000.00 元
```

### 初始只给两个工具

| Tool | 输入 | 返回 | 适用问题 |
| --- | --- | --- | --- |
| `get_metric_value` | `metric_name`, `date` | 标准指标、日期、数值、单位 | 用户询问某日指标数值 |
| `get_metric_definition` | `metric_name` | 标准指标和业务定义 | 用户询问指标口径 |

不加入联网搜索、代码执行、时间、数据库和官方工具，避免同时改变多个变量。

### 固定查询

> 查询 2026-08-01 的保费收入，并告诉我数据值。

### 唯一主要变量

`tool_choice="auto"` 下，Kimi 是否选择 `get_metric_value`，而不是 `get_metric_definition` 或直接编造答案。

### 预期轨迹

```text
HumanMessage
→ AIMessage(tool_calls=[get_metric_value(...)])
→ Python 执行 get_metric_value
→ ToolMessage(tool_call_id=...)
→ AIMessage(最终回答)
```

### 费用预估

- 新增案例：1 个；
- 模型请求：预计 2 次；
- 本地 Tool 执行：1 次，不产生模型费用；
- 预计总输入：约 1,500～3,000 Tokens；
- 预计总输出：约 100～500 Tokens；
- 按当前 Kimi K2.6 非缓存输入 ¥6.50/MTok、输出 ¥27/MTok 粗估，本次约 ¥0.01～0.04；实际以 API usage 为准。

### 验收证据

1. 打印第一轮 `AIMessage.tool_calls`；
2. 打印 Python 实际执行的工具名和参数；
3. 打印与 Tool Call ID 对应的 `ToolMessage`；
4. 打印最终回答和两次请求的 Token usage；
5. 用户能指出每一步由 Kimi、LangChain、Python 中哪一层负责。

## 发散联想

- 如果只给一个 Tool 并设置 `required`，只能证明模型能生成参数，不能证明它会在多个工具之间正确选择。
- 如果第一步就加入十几个工具，失败时无法区分是 Tool 描述、工具数量、模型选择还是执行器的问题。
- 经营分析项目后续可以把这两个粗粒度 Tool 拆成指标检索、指标确认、受控查询和证据校验，但不能提前塞进 E1a。

## 结论状态

- Kimi 本机配置：待验证（Codex 机器真实调用已通过，用户独立执行尚未完成）
- “默认业务工具”概念：待继续
- E1a Tool Calling Loop：待验证（代码与机器链路已通过，等待用户运行和解释）
- LangSmith 完整 Trace：待继续（用户决定当前暂缓，先用本地输出与 Studio 学习）

## 实现与机器验证

用户随后明确要求先由 Codex 写出代码并完成机器测试，再交给用户独立执行。因此本轮固定实验变量后实现：

- `metric_tools.py`：两个基于模拟数据的本地 Tool 与工具注册表；
- `tool_calling_demo.py`：手写 Kimi → Python Tool → Kimi 循环，逐步打印责任边界；
- `test_metric_tools.py`：验证固定值、指标定义、未知日期和 Tool Call ID 回传；
- LangSmith：加入一个父 Trace、两次模型子调用和 Tool 子调用的命名与标签。

2026-08-28 Codex 机器实际运行结果：

```text
用户问题: 查询 2026-08-01 的保费收入，并告诉我数据值。
第 1 次 Kimi 请求: 选择 get_metric_value
参数: {"metric_name": "保费收入", "date": "2026-08-01"}
Python Tool 返回: 128000.0 元
第 2 次 Kimi 请求: 最终回答“2026-08-01 的保费收入为 128,000 元。”
模型请求: 2 次
本地工具执行: 1 次
Tokens: 输入 533，输出 53，合计 586
pytest: 8 passed
Ruff: All checks passed
```

这证明当前机器、当前 Kimi 密钥和 Tool Loop 代码可以走完整链路；不证明用户已能独立搭建或解释。
LangSmith API Key 当前缺失，所以远端 Trace 还没有伪装成“已验证”。

## 后续动作

1. 用户运行固定案例，只执行 1 个 Case，并解释谁选择工具、谁执行工具、为何回传 `tool_call_id`。
2. 用户确认理解后，把同一循环迁移成 LangGraph 节点与条件边。
3. Graph 可运行后接入 Studio，观察节点、状态、条件边与执行路径。
4. 需要跨运行检索、对比或评测时，再决定是否开启 LangSmith。
