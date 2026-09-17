# 2026-08-29 LangGraph Studio 本地调试

## 原始问题

- LangGraph Studio 是否收费，免费时再尝试。
- 完成本地 Studio 配置，查看 Graph 拓扑和执行过程，同时暂不启用 LangSmith 云端 Trace。
- 逐块理解重构后的 Clarification Agent、Tool Loop、Interrupt、受控执行和最终回答代码。

## 用户理解

- Studio 如果也要付费，本阶段就不使用；如果免费，可以用它辅助观察 LangGraph。
- 当前优先需要本地调试和可视化，不需要把执行数据上传到 LangSmith。
- 仅把“近一周”硬编码为连续 7 天不能从根本上解决自然语言时间理解；应判断失败来自模型理解、Prompt/Schema，还是 Tool 契约。
- 用户确认日期口径：近一周为包含参考日的滚动 7 天；上周为上一自然周（周一至周日）；本周为本周一至参考日。
- 用户进一步追问：澄清完成、交给所谓 `Code Agent` 前做了哪些验证，以及执行后怎样返回结果。
- 用户否定通过 `AFFIRMATIVE_WORDS`、日期短语正则和固定问句模板补洞，要求信任 Kimi 的语义理解；Clarification Agent 的核心应是把诉求明确为指标、时间、周期和内容，时间边界通过 week/month/year 加 offset 的日历 Tool 确定，并尽量一次问完。

## Codex 反馈

- Studio 和本地 `langgraph dev` 可以免费使用；Kimi 模型调用费用与 Studio 独立。
- 已通过 `langgraph.json` 注册 `business_analysis`，安装本地开发 CLI，并实际启动本地服务。
- 已在 Studio 页面验证服务为 `Connected`，完整拓扑包含澄清、三类意图路由、工具执行、回答生成和安全失败节点。
- 首次在 Studio `Chat` 模式运行暴露出输入 Schema 缺口：Studio 传入 `messages`，原 Graph 入口只读取 `raw_query`，因此在 `understand_request` 抛出 `KeyError('raw_query')`。
- 已增加 `prepare_input` 节点，将 CLI/Graph 模式的 `raw_query` 与 Studio Chat 的最后一条用户消息归一化，并补齐可复现的初始 State；无网络测试为 `21 passed`。
- `LANGSMITH_TRACING=false`；页面缺少 API Key 的提示只影响 LangSmith 云端 Runs，不影响本地 Graph 和 Interact。
- Studio 页面只是前端；`127.0.0.1:2024` 的 `langgraph dev` 才是本地执行服务。该前台进程退出后页面仍能打开，但连接状态会变为断开。
- Studio 实跑暴露出第二个缺口：用户在日期澄清中回复“近一周的”后，旧 State 只有单日字段，日期解析失败并重复追问到第 4 轮。
- 已增加受控日期范围 State 和范围查询 Tool：近一周按参考日向前 6 天到参考日，共 7 天；金额聚合为合计，比例聚合为平均。直接请求和 interrupt 恢复路径均有无网络测试，当前共 `24 passed`。
- 上述“近一周”规则只能作为临时止血，不视为自然语言时间理解已经完成。
- 旧线程 State 证明 Kimi 能把用户口误“取消闲的保费”映射为取消险指标，但日期始终没有进入确认 State。现有代码没有保存 Kimi 的原始 `ClarificationResolution`，因此无法从历史 State 区分“模型未输出日期表达”与“模型输出后被单日解析器丢弃”。
- 当前 Kimi 理解节点没有接收 Tool 描述；Graph 在条件确认后确定性调用 Tool。因此旧失败不能归因于 Tool description 写法，但旧 Tool/State 只有单日契约，确实使日期范围即使被模型理解也无法执行。
- 根本改造候选：让 Kimi 输出统一 `TimeSpec`（原文、单日/绝对范围/相对范围、数量、单位、方向、置信状态），确定性日历层换算和校验 ISO 起止日期，范围 Tool 只消费标准日期；同时把模型解析结果和 grounding 错误写入 State 供 Studio 回溯。
- 重构前代码没有独立 `Code Agent`：`prepare_clarification` 只检查必需 State 字段是否齐全，随后按意图路由到 `query_data / data_knowledge / data_analysis`，由节点直接调用受控本地 Tool。执行结果写入 `state.result` 后，再由 `generate_answer` 调用 Kimi 包装成自然语言。
- 重构前执行校验分散在目录 grounding、缺失字段检查和 Tool 内部校验中；没有独立的 `ValidatedQueryPlan`。重构后虽增加统一 `submit_clarification` 门槛，但仍没有执行后结果验证节点或最终答案一致性校验，复杂 `data_analysis` 仍是占位实现。
- 环境配置成功只代表准备完成，不代表用户已经理解 Studio 的 State、Interrupt 和本地执行记录。
- 2026-08-30 已将旧混合澄清器重构为单个 Clarification Agent：Kimi 读取完整 messages，只能调用 `resolve_business_period` 或 `submit_clarification`；删除确认词表、自然语言日期正则、固定澄清问句和本地“确认快速路径”。
- 新日历 Tool 接收 `mode(exact/calendar/rolling) + unit(day/week/month/year) + offset`，工具只做确定性日期计算，不负责理解用户原话。已用本地测试固定用户确认的三个口径：滚动一周、本周、上周。
- 新 `submit_clarification` 将模型决策限制为 `ready / needs_clarification`。`needs_clarification` 必须一次给出问题和全部未决字段；`ready` 的查询/分析必须带有效指标目录、维度和来自日历 ToolMessage 的起止日期，否则错误返回模型重试。
- 当前拓扑为 `prepare_input → clarification_agent ↔ clarification_tools → apply_clarification_decision → ask_human/三类执行节点 → generate_answer`。这保留模型语义自主性，同时由外层 Graph 控制执行门槛。
- 本地无付费验证为 `27 passed in 1.10s`，Ruff 通过；没有发起重构后的真实 Kimi 调用，因此不能把 stub 测试写成 Kimi 已正确理解“确认”“三种保费”或“近一周”。
- 代码导读采用三层边界：Kimi 负责自然语言语义与工具选择；LangGraph 负责 State、节点、循环、路由与中断恢复；普通 Python/Tool 负责日期计算、目录约束和执行。理解检查等待用户按一次真实输入复述 State 与 Message 的变化。

## 发散联想

- Studio 解决的是开发期的单次运行观察和交互调试；LangSmith Trace 更适合跨运行检索、对比、评测和线上监控。
- 完整 messages 只记录对话内容；Checkpoint 还要保存 Graph State、执行位置和恢复所需元数据。后续应通过一次 `interrupt` 恢复实验验证这个区别。

## 结论状态

- Studio 免费性与本地连通：已理解
- Studio Chat 首条消息的输入适配：待验证（机器测试通过，等待用户真实运行）
- “近一周”由 Kimi 选择 `rolling + week + 0`：待验证（确定性日历计算已通过机器测试，模型选择尚未实跑）
- 模型驱动澄清与日期 Tool 契约：待验证（结构重构与 27 个本地测试通过，等待用户真实运行）
- 在 Studio 中独立运行并解释节点、State、Interrupt：待验证
- Studio 本地记录与 LangSmith 云端 Trace 的能力边界：待继续
- 重构后代码的逐块调用关系：待继续（已开始导读，等待用户复述和追问）

## 后续动作

1. 用户在 Studio 新建 Chat，输入“查询准时保保费收入，App渠道，近一周”，观察 Kimi 是否调用 `resolve_business_period(rolling, week, 0)` 后提交 ready。
2. 再输入“看看B准的保费”，观察 Kimi 是否把所有未决项合并成一个问题；恢复时只回复“确认”，检查是否由模型而非本地词表继承提案。
3. 用户用自己的话解释 Interact、Graph、Interrupt、Checkpoint 与 Trace 的区别。
4. 完成后再进入两个工具 Agent 的多 Agent 编排。
