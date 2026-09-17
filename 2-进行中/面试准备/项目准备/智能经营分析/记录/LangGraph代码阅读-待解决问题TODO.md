# LangGraph 代码阅读：待解决问题 TODO

更新时间：2026-09-08。

## 本轮已确认的讨论方式

- 先按代码执行顺序，一块一块读完当前实现。用户最新要求：可以适度抽象，明确标注文件及代码行号范围，主要解释每块解决的问题和整体含义，由用户自行阅读源码；不再逐个展开普通 Python 语法。
- 2026-09-07 用户最新选择：查看较详细的摘要和带注释的代码，自行读完剩余部分；不要求继续逐块口头展开。
- 阅读中出现的延伸问题先记在本清单；读到直接相关的代码时，或者完成代码阅读后，再展开。
- 一两句话能说明的问题可以即时回答；预计需要超过约 200–300 字的问题先记 TODO，不打断代码主线。
- 清单记录不等于问题已解决。学习状态使用“待继续 / 待验证 / 已理解”；目前下列条目均为“待继续”。未勾选表示尚未完成讨论。
- 保留用户原始问法；整理后的问题与 Codex 建议的讨论位置均用于导航，不作为现有实现的事实或用户已确认的技术结论。

## 代码阅读位置

- 当前路径：[route_understanding()](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/graph.py:342) → run_analysis() → capabilities.analysis_agent()。LangGraph 由 runtime.py 第 117 行的 stream 迭代驱动，外层 main() 仍等待 execute() 返回。
- 上一块讲解：graph.py 第 101–186 行 understand_request()；随后讨论了节点上下文与工具能力草案，尚未实现工具调用循环。
- 上一轮按执行顺序讲解范围：graph.py 第 342–363、228–231、208–219 行；capabilities.py 的分析准备 161–184、准入 22–39、取数 89–158、结果封装 42–60、计算 185–209 行；catalog.py 第 94–119 行查询配置解析。沿本期/前期取数返回事实结果，并补充另一条 SQL 分支的用途。
- 自读接续位置：graph.py 第 238–264 行 compose_reply()，然后第 267–340 行 validate_reply() 与第 365–386 行 route_validation()，结合实际草稿重写回路阅读。澄清支线仍待补充；图结束后回到 runtime.py 第 122 行，execute() 返回后回到 __main__.py 第 53 行。
- 2026-09-07 已提供 [代码阅读摘要](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/代码阅读摘要.md) 和 [八个核心文件的完整注释副本](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/阅读版/README.md)，覆盖回答生成、校验重写、保存返回、澄清恢复；由用户自读，尚未确认阅读完成。八份副本仅增注释，语法及 AST 一致性检查通过，本轮未新增模型调用。
- 用户理解状态：待继续；讲解覆盖范围不等于用户已掌握。
- 全局参考：[按执行顺序的代码导读](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/代码导读-按实际执行顺序.md)。

## 待解决问题

### Q01 SQLite 在当前实现中做什么

- [ ] 状态：待继续。
- 用户原话：“SQLite在里面是起到什么作用？”
- 已讲解范围：runtime.py 中 checkpoints.sqlite 保存 LangGraph 任务存档；capabilities.py 第 113–135 行则使用 SQLite 内存库装载模拟业务数据并执行参数化 SQL。两处用途已结合代码说明，用户理解状态仍待继续。
- 用户追加原话：“那checkpoint的SQL一般是什么样子的？”
- 追加核对：已只读检查 readable-analysis 的真实 SQLite 表及当前安装的 SqliteSaver 源码。checkpoints 表保存任务 ID、命名空间、存档 ID、父存档 ID、序列化类型、checkpoint BLOB 和 metadata BLOB；该案例的 checkpoint 类型为 msgpack，共 8 行。展示其建表、写入和查询最新存档的 SQL；writes 表细节仍留待相关恢复代码。
- 待讨论：沿源码识别 SQLite 的使用位置及各自职责，区分保存执行状态和模拟 SQL 查询等用途。
- 讨论触发：[runtime.execute()](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/runtime.py:78)；读到 [query_agent()](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/capabilities.py:89) 时补充对应部分。

### Q02 会话数据保存在哪里

- [ ] 状态：待继续。
- 用户原话：“我们的会话数据是保存在什么？”
- 本轮已讲解范围：当前任务目录中的 checkpoints.sqlite 是恢复执行所用的数据库；具体 State 字段、checkpoint 写入时机，以及 state.json / Trace 导出仍待后续代码解释。
- 待讨论：消息、State、checkpoint、最终回答和导出文件分别保存什么，恢复会话时读取哪一份。
- 讨论触发：[initial_state()](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/state.py:72)、[runtime.execute()](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/runtime.py:78) 及其保存结果部分。

### Q03 LangGraph Agent 整体有哪些存储

- [ ] 状态：待继续。
- 用户原话：“在这个LangGraph Agent里面的一个体系，它有哪些数据储存的东西啊？”
- 用户追加原话：“State是存放在SQLite里面，那轨迹呢？轨迹是JSON的形式吗？轨迹其实还挺长的。”
- 用户追加原话：“换到新的节点的时候，之前的轨迹会一起丢给新的节点吗。”“那每个节点的上下文是什么？”
- 上下文解释范围：七个节点均接收当时的完整 State；模型输入由每次 model.complete() 的提示词、输出 Schema 和显式 payload 重新构造。understand_request 传本任务对话、日期基准及业务/指标目录；compose_reply 传本任务对话、facts/limitations/evidence_id/source 和 validation_feedback；validate_reply 在程序检查通过后传对话、facts、limitations 和草稿文本。其余四个节点当前不调用模型。Trace 日志不会自动成为模型上下文；重写分支当前没有把上一版草稿传回 compose_reply。此补充未改变按执行顺序阅读的位置，理解状态仍待继续。
- 追加核对：State 运行时由程序持有，checkpoint 是写入 SQLite 的持久化存档；自定义 Trace 由 trace.py 逐行追加到 trace.jsonl，再生成 trace.html。readable-analysis 的原始 Trace 有 56 条事件、181303 字节，包含模型请求/响应、节点输入输出和多次 State 快照等重复信息。state.json 是最后状态的可读导出，checkpoints.json 是存档历史的可读导出。用户理解状态仍待继续。
- 待讨论：读完当前代码后，汇总实际使用的存储和未实现部分，再讨论会话状态、业务结果、知识、记忆、缓存、配置和 Trace 的关系。
- 讨论触发：读完 runtime.py、state.py、catalog.py、capabilities.py、trace.py 后统一整理。

### Q04 临时取数结果、Excel 和较大结果放在哪里

- [ ] 状态：待继续。
- 用户原话：“就是我们查出来的临时结果是储存在Excel里面的。我们如果比较大的话，我们放在哪个里面呢？”
- 事实边界：“临时结果储存在 Excel”先保留为用户当前说法，不能据此认定当前实验或原项目已经这样实现；讨论时对照源码区分内存结果、持久化结果和用户导出文件。
- 当前实验核对：query_agent 返回的 rows 是 Python 列表，连同汇总、配置快照等装入 result；分析结果还包含本期和前期结果，随后进入 State 并可随 checkpoint 和 Trace 持久化。当前没有写入 Excel；大结果的外部存储和引用设计仍待继续。
- 待讨论：较大结果怎样存放、如何在 State 中引用、如何供后续分析和用户下载。
- 讨论触发：[query_agent()](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/capabilities.py:89)、[analysis_agent()](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/capabilities.py:161) 的返回结果，以及 runtime.py 保存 State 的部分。

### Q05 是否使用 ES，它处在什么位置

- [ ] 状态：待继续。
- 用户原话：“然后我们有没有ES这种储存的东西？”
- 待讨论：核对当前实验是否接入 ES；需要时再解释 ES 与数据库、文件存储、检索组件的职责。
- 讨论触发：读到 [knowledge_lookup()](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/capabilities.py:212) 和 catalog.py，或完成整体存储梳理后。
- 术语说明：暂按常见缩写理解为 Elasticsearch；正式讨论时结合上下文核对。

### Q06 LangGraph / LangChain 是否支持简易向量数据库

- [ ] 状态：待继续。
- 用户原话：“然后LangGraph Langchain内部支持简易的向量数据库吗？向量数据库吗？”
- 待讨论：区分框架提供的接口、内存中的向量检索实现、外接向量数据库，以及是否需要单独的 embedding 模型和持久化。
- 讨论触发：知识检索部分或代码整体阅读结束后；届时核对实际依赖版本及官方资料。

### Q07 10 个会话怎样使用 TPM / RPM 配额

- [ ] 状态：待继续。
- 用户原话：“然后如果是10个会话，你只使用它的一个TPM和RPM？”
- 整理后的待讨论问题：10 个会话是否共享同一账号或 Key 所属配额；限额按什么范围计算；一次用户请求内的多次模型调用怎样计入。
- 延伸边界：区分本地 max-model-calls 调用预算与供应商 TPM、RPM、并发限额，不把它们当成同一个限制。
- 本轮补充范围：model.complete() 按本任务 Trace 中的 model_request 数量检查调用预算，并对可重试故障/结构错误最多尝试两次（含首次）。多会话的供应商共享配额及限流策略仍待继续，不作为已完成讨论。
- 讨论触发：[KimiModel.complete()](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/model.py:50) 中调用预算、模型请求和重试部分。

## 前面已展开、以后再收束的问题

### Q08 多用户、多会话与连续追问

- [ ] 状态：待继续。
- 来源：前几轮关于 user_id、thread_id、执行资源、任务结束后的续聊和暂停恢复的讨论。
- 已有 Codex 解释，但不视为用户已确认理解；读到 State、checkpoint、Command(resume=...) 时结合真实代码再收束。
- 代码现状与拟议的多人服务设计需要继续分开。

### Q09 30 多用户、最多 10 个并发会话的资源估算

- [ ] 状态：待继续。
- 用户已给约束：30 多个用户，同时使用最多约 10 个会话。
- 前文的服务器配置属于基于外部 Kimi API、轻量取数编排的起步估算；没有对当前实现完成 10 并发压测，也不是已确认部署计划。
- 讨论触发：完整代码阅读后，再结合真实数据规模、模型配额和响应时间要求讨论。

## 从简化实现到真实 Agent：后续设计问题

以下是用户在阅读 understand_request 和节点上下文时提出的方向。当前仅记录和解释，尚未改动实验代码，也不是已确认的正式实施方案。代码阅读仍从 route_understanding() 继续。

### Q10 怎样把简化函数替换成模型工具调用循环

- [ ] 状态：待继续。
- 用户原话：“没有模型使用工具的地方吗？其实我觉得你是做成这样，是因为我们目前先简化，把几个节点去简略成这个，然后分析的其实也是类似的。”
- 本轮核对：当前 main_agent 包中没有 bind_tools / tool_calls / ToolNode 循环。模型返回结构化 Proposal / Reply / Verdict，取数和分析由 Python 调用普通函数；Trace 中 category=tool 不代表调用由模型决定。
- Codex 说明：LangGraph 的节点可以封装完整 Agent。可由外层图控制流程，内层模型提出工具调用，代码校验并执行，工具结果返回模型；确定的步骤仍可直接使用代码。
- 待讨论：取数与分析各暴露哪些工具、哪些步骤固定、哪些由模型选择；工具循环如何写入消息、State 和 Trace；循环与调用预算怎样约束。
- 讨论触发：读完 run_query / run_analysis 及其函数实现后，再讨论最小替换方案。
- 官方参考：[自定义工作流中嵌入 Agent](https://docs.langchain.com/oss/python/langchain/multi-agent/custom-workflow)、[模型与工具循环](https://docs.langchain.com/oss/python/langgraph/workflows-agents)。

#### 本轮工具清单建议（AI 草案，尚未实现）

- 用户原话：“你觉得我们需要哪些工具？”
- 建议围绕现有指标查询、口径解释、环比及渠道分析，先组织五项能力；前四项可暴露给模型，日期计算先保留为代码直接调用的辅助函数。

| 能力 | 主要输入 | 主要输出 |
| --- | --- | --- |
| search_metrics | 用户指标表达、业务范围 | 候选标准名称、指标 ID、别名、口径摘要、适用范围及来源 |
| get_metric_definition | 选定的指标 ID、必要的业务范围 | 平台权威口径、单位、时间口径、可用维度、版本和来源 |
| query_metric | 指标 ID、时间范围、维度、过滤条件 | 结果引用、必要预览/摘要、行数、范围、来源及完整性信息 |
| compare_results | 两份同口径结果引用、分解维度 | 差额、变化率、渠道贡献等由代码计算的事实；不自动证明因果 |
| resolve_period（复用现有日期函数） | 时间语义、固定日期基准 | 明确的起止日期；可在固定流程或取数工具内部直接调用 |

- 指标身份先消歧；get_metric_definition 及 query_metric 的执行需要代码检查业务适用性和范围，不能依赖模型记得检查。
- query_metric 内部按配置分派指标平台或参数化 SQL。数据集 ID、业务线映射、表名和模板由配置解析，并保留执行快照与 Trace；当前草案不增加任意 SQL 或任意 Python 执行工具。
- result_id / 结果引用是后续设计建议，需要配套结果存储和当前用户/任务归属检查；当前函数结果返回不等于已完成该存储实现。
- 涉及分析方法、活动及业务背景文档时，再增加 search_business_knowledge；Excel 导出等产物工具在相关需求和存储问题讨论时补充。
- 澄清沿现有 interrupt 节点处理；身份、权限、checkpoint、Trace 作为程序基础设施，不暴露为让模型决定是否执行的工具。
- 官方参考：[LangChain 工具定义与运行上下文注入](https://docs.langchain.com/oss/python/langchain/tools)。

### Q11 指标知识检索、候选消歧与平台权威口径

- [ ] 状态：待继续。
- 用户原话：“然后指标知识这个应该是要去检索这个，然后把这个拼到上下文里面，就是要从我们的知识库里面检索这个知识，以及调用对应的工具去查询对应的指标。就是先用模糊匹配去从我们知识库匹配到对应的指标名和指标ID，然后用指标ID去线上平台去获取这个指标的口径。”
- 待讨论链路：提取用户的指标表达 → 检索候选名称/ID → 结合业务与口径消歧 → 通过选定 ID 获取平台口径 → 有数值需求时执行指标查询 → 将带来源的证据交给回答。
- Codex 补充：模糊匹配用于召回候选，不能把相似度最高直接视为适用指标；要判断业务、粒度、时间口径等，必要时澄清。指标解析应供知识、取数、分析共享，不只放在 consult_knowledge 分支。
- 事实边界：当前实现只查本地模拟目录；平台接口是否提供这些字段、哪个系统是权威来源，需结合真实接口确认。
- 讨论触发：capabilities.py / catalog.py 阅读结束后，与 understand_request 当前直接选择小目录 key 的简化一并比较。

### Q12 回答上下文、Agent 消息连续性与 KV Cache

- [ ] 状态：待继续。
- 用户原话：“生成回答的这个上下文应该也带了几分吧，因为有KV Cache，所以我们应该尽量的都联系起来。一般的设计是怎么设计的？”
- 术语边界：保留原始转写“几分”，不擅自改成特定技术字段；本轮讨论明确部分是回答上下文的连续性与 KV Cache。
- Codex 说明：同一个工具调用循环应保留 assistant 的 tool_calls 和对应 ToolMessage，让模型利用工具结果。独立回答节点则需要用户问题、已澄清约束、指标口径、数据与计算证据和来源；不能只剩孤立数字。重写可同时传旧草稿和具体反馈，当前实验尚未这样做。
- 缓存说明：Kimi 对重复初始上下文自动尝试缓存；稳定的系统提示、工具定义等前缀有利于命中。缓存是计算复用，不是会话持久化；需要的上下文仍由请求提供，也不能因缓存而假定历史不再占上下文窗口或无需筛选。
- 待讨论：同一 Agent 连续生成最终回答与独立 compose_reply 的取舍；跨节点共享哪些事实，哪些执行日志留在 Trace；稳定前缀、动态内容和检索证据的组织；通过真实 usage 验证缓存命中与效果。
- 讨论触发：读到 compose_reply()、model.complete() 的消息构造后展开；涉及验证缓存效果的额外模型调用单独说明。
- 官方参考：[Kimi 上下文缓存及工具消息说明](https://www.kimi.ai/help/kimi-api/api-troubleshooting)。

## 2026-09-08 新增：工具失败与共享鉴权 Token

### Q13 工具调用失败、鉴权失败时怎样恢复

- [ ] 状态：待继续。
- 用户原话：“里面再加一个工具调用失败或者健全相关的一些失败问题怎么办？”
- 术语说明：保留转写“健全”，结合后文 Token 暂按“鉴权”理解。
- 待讨论：区分参数错误、超时、网络错误、限流、平台故障、Token 过期和权限不足；哪些由代码有限重试，哪些需要模型修正参数，哪些应停止或请用户补充。
- 并行关联：多个分支一起失败时如何避免重试放大；怎样保留成功结果、只重试失败任务，并把部分失败准确交付给用户。查询若创建平台异步任务，还要区分重复提交与轮询已有任务。
- Trace 关联：记录失败类别、次数、耗时及恢复结果，关联原工具调用与重试；不记录 Token 明文、认证请求头或刷新凭据。
- 讨论触发：结合 playground 的指标 worker、工具执行封装与 Trace，和 Q07 的限流预算一起展开。本轮只记录问题，未修改运行代码。

### Q14 多用户共用、每 24 小时刷新的查询 Token 怎样管理

- [ ] 状态：待继续。
- 用户原话：“我们查询工具需要有一个健全的Token，这个Token是每24小时刷新，每个人每个用户不是独立的，这个是怎么去做的呢？”
- 用户提供的条件：查询工具需要 Token，每 24 小时刷新，多用户共用；这是待对接平台的描述，不表示本地模拟查询已经实现该鉴权。
- 待核对的接口事实：24 小时是有效期还是固定轮换时间；是否有自动换取/刷新接口；能否提前获取；新 Token 生效后旧 Token 是否立即失效；平台怎样返回过期、撤销和权限不足。不能由“每天刷新”推定存在 OAuth refresh_token。
- Codex 初步设计草案：工具客户端调用服务端统一的 TokenProvider，按平台/服务身份管理凭据和到期时间；接口允许时在到期前刷新，请求时再检查有效性。单进程可用受控内存缓存，多进程/多实例需共享存储或凭据服务，并协调唯一刷新者；并发失败先检查是否已有更新版本，防止大家同时刷新、旧请求覆盖新 Token。
- 失败恢复草案：确认是 Token 失效时，由代码获取可用 Token 后对安全的只读查询最多补试一次；刷新持续失败则有界停止并报告平台鉴权不可用。权限不足不能靠重复刷新解决，超时/限流/平台故障另设重试策略。
- 权限与上下文边界：共享平台凭据与访问者身份分开；仍需校验每个用户可查的指标、业务线与数据范围。Token 由工具执行层注入，不放入模型提示词、业务 State、checkpoint 或 Trace 明文。
- 官方参考：[Bearer Token 错误语义，RFC 6750 第 3.1 节](https://www.rfc-editor.org/rfc/rfc6750.html#section-3.1)。该规范区分 invalid_token 与 insufficient_scope；真实平台是否采用这些状态码仍需核对。
- 讨论触发：与 Q13 一起沿“工具调用 → 用户权限校验 → 获取 Token → 平台请求 → 分类恢复 → Trace”展开。此项未实现，用户理解与具体方案均待继续。

## 2026-09-07 试玩实现补充

- Q10–Q12 继续保持 `待继续`。上文“当前代码”指此前逐段阅读的 `main_agent` v2，不据此覆盖旧阅读记录。
- 按用户要求新增独立的 [playground 试玩入口](../实验/LangGraph经营分析面试复现/business_analysis_repro/playground/README.md)：20 个模拟指标、每指标三个维度、不同枚举白名单；理解节点里已有真实模型工具循环，取数和分析仍为普通函数。
- 用户希望参考此前公司材料，并提醒保费等资料不止两份。检索入口与事实/模拟配置边界见 [资料回忆与配置依据](../实验/LangGraph经营分析面试复现/business_analysis_repro/playground/资料回忆与配置依据.md)。
- 后续结合用户亲自试玩，继续讨论：模型是否保留所有查询条件、自然周与滚动期间的区别、工具消息怎样回到上下文、同名指标怎样消歧。机器运行和检查通过不改变用户的理解状态。

## 2026-09-07 多指标并行实现补充

- 用户已明确要求实现多指标并行，上限5，并将何时同查、何时拆开写入Prompt；已在独立的playground v4模块实现，不覆盖旧v2阅读副本。
- 代码与验证入口：[并行实现与验收](../实验/LangGraph经营分析面试复现/business_analysis_repro/playground/并行实现与验收.md)。机器测试110项通过，四指标、七指标、维度澄清与并行Trace已验证；用户独立理解仍为待验证。
- Q07（TPM/RPM）仍为待继续：当前共享并发名额不等于每分钟额度；Q09的生产资源与十会话容量仍未验收。后续读到Send、reducer和worker再讨论分支输入、结果汇总、部分失败与日志锁。


## 2026-09-07 流式输出与实际分支补充

- 用户原话：“流式输出实现一下……刚才问的问题是走的分析Agent还是取数Agent？好像只走了取数Agent。”保留为用户待核对的判断。
- 实际Trace显示原任务为4个analysis分支，各调用两期query，共8次取数。分析能力仍是普通Python函数，不是自主下钻的模型循环。
- 已增加真实Kimi正文流、实时分支状态、提前显示完整表格、刷新恢复和已有明细导航；机器验证116项通过，另用2个真实案例验证查数/分析，详见[流式输出实现与验收](../实验/LangGraph经营分析面试复现/business_analysis_repro/playground/流式输出实现与验收.md)。
- 用户独立运行与理解状态仍为待验证。后续读到stream_reply/iter_sse时，再讨论“State的checkpoint、Trace中的文字片段、页面草稿”三者的区别；现有Q07/Q09/Q10–Q12状态不变。


## 2026-09-09 逐项解答已提供

按用户要求，Q01–Q14 已分别整理为 [相对完整的解答文档](2026-09-09-LangGraph待解决问题逐项解答.md)，另补规划、流式与费用/容量问题。文档说明当前代码、一般设计和未实现范围。提供解答不等于用户已理解，原条目学习状态保持待继续；后续由用户读完后提问。
