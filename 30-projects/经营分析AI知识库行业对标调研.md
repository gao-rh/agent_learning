---
type: project-log
status: draft
tags: [business-analysis, ai-agent, data-query, semantic-layer, rag, data-governance, benchmark]
created: 2026-06-13
updated: 2026-06-13
source:
  - 00-inbox/2026-06-13-当前上下文记忆摘要.md
  - 30-projects/经营分析AI知识库建设方案.md
  - https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
  - https://www.anthropic.com/engineering/code-execution-with-mcp
  - https://www.anthropic.com/engineering/contextual-retrieval
  - https://code.claude.com/docs/en/mcp
  - https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool
  - https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst
  - https://docs.snowflake.com/en/user-guide/views-semantic/overview
  - https://docs.databricks.com/aws/en/genie/
  - https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-semantic-models
  - https://docs.cloud.google.com/looker/docs/conversational-analytics-overview
  - https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-build-structured.html
  - https://developer.salesforce.com/docs/platform/hosted-mcp-servers/guide/tableau-next.html
  - https://docs.getdbt.com/docs/build/about-metricflow
  - https://docs.datahub.com/docs/glossary/business-glossary
  - https://bird-bench.github.io/
related:
  - 30-projects/经营分析AI知识库建设方案.md
  - 00-inbox/2026-06-13-经营分析Skill架构讨论日志.md
  - 20-concepts/记忆搜索总览.md
  - 20-concepts/Skill是什么.md
---

# 经营分析 AI 知识库行业对标调研

## 一句话结论

行业标杆的共同方向不是“把所有资料丢进向量库，让大模型自己理解”，而是：

```text
权威语义层 + 数据目录/血缘 + 结构化知识对象 + 混合检索 + 受控工具调用 + SQL/指标执行校验 + 引用证据 + 反馈评估
```

对你们当前场景，最应该借鉴的是 Anthropic 的 **just-in-time context / 工具化取数 / Contextual Retrieval** 思路，以及 Snowflake、Databricks、Power BI、Looker 反复强调的 **语义层和人工 curated 业务语义**。

最不应该照搬的是厂商的一体化产品形态：比如直接把系统做成一个“万能数据聊天框”，或者只靠 Text-to-SQL 连接数仓。经营分析问的是“为什么”和“怎么办”，不是只问“查一个数是多少”。

## 当前项目背景

你们要建设的是一个面向经营分析和数据查询的业务知识库。它要回答的不只是普通文档问答，而是：

| 典型问题 | 背后能力 |
| --- | --- |
| 这个指标为什么大幅下降？ | 指标口径、历史趋势、分维拆解、业务事件、历史类似案例、归因假设。 |
| 这个东西为什么会变成这样？ | 业务现象识别、同期事件关联、数据证据和报告/会议证据交叉验证。 |
| 我们想做得更好，能不能给点建议？ | 历史复盘、经营杠杆、行动建议、风险和验证指标。 |
| 帮我取数 / 查 SQL / 查口径 | 指标平台、数据目录、血缘、SQL 模板和只读查询能力。 |

已有条件：

| 已有条件 | 方案含义 |
| --- | --- |
| 指标口径平台有稳定 API | 指标定义应以现有平台为权威源，不另造一套口径。 |
| 数据目录和血缘系统有稳定 API | 表、字段、上下游、owner、刷新频率应优先调用现有系统。 |
| 已有多种查询方式，包括 SQL | Agent 应封装查询工具，而不是直接让模型自由拼 SQL。 |
| 有向量知识库平台，可能底层是 Milvus | 向量检索可作为召回层，但不能承载口径权威、SQL 校验和业务归因。 |
| 第一批资料是近期周报/报告，会议纪要从现在开始积累 | 应优先抽取 `MetricMovement`、`BusinessEvent`、`Hypothesis`、`ActionRecommendation` 和 `AnalysisCase`。 |

## 调研范围

本调研把行业资料分成 7 类：

| 类别 | 代表资料 | 重点看什么 |
| --- | --- | --- |
| Agent 工程 | Anthropic Claude Code、MCP、tool use、code execution、context engineering | 数据查询 Agent 应如何组织上下文、工具和执行环境。 |
| Text-to-SQL / 自然语言查询 | Snowflake Cortex Analyst、Databricks Genie、Bedrock structured KB | 如何把自然语言问题变成可执行查询。 |
| 语义层 | Looker LookML、Power BI semantic model、dbt MetricFlow、Tableau Semantics、ThoughtSpot Semantics | 如何让 AI 理解指标、维度、业务术语和口径。 |
| BI Copilot / 分析助手 | Power BI Copilot、Amazon Q in QuickSight、Tableau Pulse/Agent、ThoughtSpot Spotter | 如何提供问数、可视化、洞察摘要、异常解释。 |
| RAG / 知识检索 | Anthropic Contextual Retrieval、Bedrock KB、LlamaIndex structured + semantic data | 如何把文档证据和结构化数据结合。 |
| 数据治理 | DataHub、OpenMetadata、Unity Catalog、血缘和 glossary | 如何让 AI 知道“哪个数据可信、谁负责、是否过期”。 |
| 评估与基准 | BIRD、Spider、企业内部 golden set | 如何评估 NL2SQL、答案准确性、证据质量和业务可用性。 |

说明：用户口头提到的 `Cloud Code` 在本任务语境里更可能是 Anthropic 的 `Claude Code`，不是 Google Cloud Code 插件。

## 总体观察：行业标杆的共性

| 共性 | 代表厂商/资料 | 对你们的启发 |
| --- | --- | --- |
| 语义层是核心，不是可选项 | Snowflake Cortex Analyst、Databricks Genie、Power BI Copilot、Looker Conversational Analytics、Tableau Next、ThoughtSpot Spotter | 没有指标口径、维度、业务术语、样例问题和可信资产，问数准确率会很差。 |
| 数据查询要用工具执行，不靠模型“想答案” | Anthropic tool use / code execution、Cortex Analyst REST API、Bedrock GenerateQuery | 模型负责规划和生成结构化调用；真实查询由受控工具执行。 |
| 上下文要按需加载，而不是一次塞满 | Anthropic effective context engineering / Claude Code | 对大库、大表、大量报告，用 ID、路径、表名、SQL 模板等轻量引用，再按需加载。 |
| 文档 RAG 需要上下文增强和重排 | Anthropic Contextual Retrieval | 周报/会议纪要切 chunk 时要补充文档标题、时间、业务域、章节、指标等上下文。 |
| 一体化产品都强调 curated domain space | Databricks Genie Space、QuickSight Topic、Looker Explore/Data Agent | 不要开放全公司所有表；先给小业务方向建一个可控空间。 |
| 结果要可追踪、可解释、可回放 | OpenAI/Anthropic tracing 思路、BI 工具的 SQL/结果表/来源展示 | 经营分析不能只给结论，要能看到用的指标、SQL、数据表、报告证据。 |
| AI 不是数据治理替代品 | Power BI 明确提醒：模型/数据/用户不准备好会产生低质量甚至误导输出 | 先补语义、owner、状态、有效期、样例问题，再做聊天入口。 |

## Anthropic / Claude 相关资料重点

### 1. Effective Context Engineering：按需上下文，而不是预先塞满

Anthropic 在 context engineering 文档中强调一种 `just-in-time` 思路：Agent 维护轻量引用，例如文件路径、存储查询、网页链接，再在运行时用工具动态加载需要的数据。文档还明确提到 Claude Code 用这种方式在大型数据库上做复杂数据分析。

来源：[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

对经营分析的启发：

| 可借鉴点 | 具体落地 |
| --- | --- |
| 不要把所有报告、表结构、血缘、SQL 一次性塞进 prompt | 先召回候选指标/表/报告/案例 ID，再按任务继续加载详情。 |
| 把上下文分成 lightweight reference 和 full payload | 例如先给 `metric_id/table_id/report_id/sql_template_id`，需要时再展开。 |
| 查询过程可以多轮工具调用 | 先查口径，再查数据目录，再生成 SQL，再执行，再查历史归因案例。 |
| 上下文窗口是公共资源 | 只放当前问题真正需要的证据，不把整篇周报和所有字段都塞进去。 |

不能照搬：

| 不能照搬点 | 原因 |
| --- | --- |
| 直接让通用 coding agent 接生产数仓 | 经营分析场景涉及口径、权限、成本和误导风险，需要只读工具、审计和审批。 |
| 把文件路径式上下文直接等同于业务知识库 | Claude Code 面向开发文件很自然；经营分析还需要指标、血缘、报告、会议、业务事件等对象化。 |

### 2. MCP：标准化外部工具连接

Claude Code 文档把 MCP 描述为连接外部工具、数据源、数据库和 API 的开放标准。Claude Code 通过 MCP server 访问 issue tracker、监控面板、数据库和各种工具。

来源：[Connect Claude Code to tools via MCP](https://code.claude.com/docs/en/mcp)

对经营分析的启发：

| 可借鉴点 | 具体落地 |
| --- | --- |
| 把已有系统封装成工具 | `metric_platform.get_metric`、`data_catalog.search_assets`、`lineage.get_upstream`、`sql.run_readonly`、`report.search_cases`。 |
| 工具边界比 prompt 更重要 | 每个工具明确输入、输出、权限、是否只读、是否可执行、是否需要审批。 |
| 可以把查询能力从模型里拆出来 | 模型不直接访问数据库连接串，只调用受控工具。 |
| MCP 可作为未来统一接入规范 | 先内部函数/API 封装，后续可升级为 MCP server。 |

不能照搬：

| 不能照搬点 | 原因 |
| --- | --- |
| 一开始就追求“接入几百个 MCP 工具” | 工具多会增加选择错误和权限风险。第一期应限制在 8-12 个高价值只读工具。 |
| 认为 MCP 本身解决业务语义 | MCP 只解决“怎么连接工具”，不解决“哪个指标才是对的”。 |

### 3. Code Execution with MCP：让工具过滤数据，减少模型上下文负担

Anthropic 的 code execution with MCP 文章强调：代码执行可以按需加载工具、在数据进入模型前过滤数据，并在一次工具调用中执行复杂逻辑，还带来安全和状态管理收益。

来源：[Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)

对经营分析的启发：

| 可借鉴点 | 具体落地 |
| --- | --- |
| 大表不要直接给模型 | 让 SQL/代码工具先聚合、过滤、抽样、计算异常，再把小结果给模型解释。 |
| 复杂分析可以放在 sandbox / job 里执行 | 例如同比环比、贡献度拆解、漏斗分解、异常检测、TopN 归因候选。 |
| 模型看结构化结果，不看原始海量数据 | 输出 `result_table + chart_spec + sql + warning + provenance`。 |

不能照搬：

| 不能照搬点 | 原因 |
| --- | --- |
| 让模型在沙箱里任意写脚本访问内部数据 | 需要查询模板、资源限额、行数限制、成本控制和数据脱敏。 |
| 只靠 code execution 做分析 | 经营分析还要解释业务事件、历史案例、会议结论，代码只能解决一部分计算。 |

### 4. Contextual Retrieval：给 chunk 补上下文

Anthropic 的 Contextual Retrieval 提出 Contextual Embeddings 和 Contextual BM25，并称可显著降低检索失败率。核心思想是：chunk 本身常常缺少文档级上下文，所以在索引前给 chunk 加上文档背景、章节、含义，再做 embedding 和 BM25。

来源：[Contextual Retrieval in AI Systems](https://www.anthropic.com/engineering/contextual-retrieval)

对经营分析的启发：

| 可借鉴点 | 具体落地 |
| --- | --- |
| 周报 chunk 不能只按字数切 | 每个 chunk 需要带 `报告标题、周期、业务域、指标、章节、结论类型`。 |
| 关键词检索和向量检索要结合 | 指标名、表名、字段名、活动名适合 BM25；模糊业务问题适合 embedding。 |
| 需要 rerank 和 metadata filter | 先过滤时间、业务域、状态、权威等级，再 rerank。 |
| chunk 要保留可引用来源 | 回答“为什么”时必须能追到报告、会议和 SQL。 |

不能照搬：

| 不能照搬点 | 原因 |
| --- | --- |
| 只做 chunk 级 RAG | 经营分析需要结构化对象：指标波动、业务事件、假设、行动建议，不只是片段。 |
| 认为检索准确就等于分析准确 | 检索到正确资料后，还需要取数验证、口径校验和业务判断。 |

### 5. Tool Use / Code Execution：工具调用是 Agent 循环的基本形态

Claude API 的 tool use 文档说明：模型根据用户请求和工具描述选择工具，并返回结构化调用；客户端或服务端执行工具后，把结果再送回模型。Claude code execution tool 则支持数据分析、可视化、复杂计算、文件处理等。

来源：

- [Tool use with Claude](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview)
- [Code execution tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool)

对经营分析的启发：

| 可借鉴点 | 具体落地 |
| --- | --- |
| Agent 回答数据问题应有显式步骤 | 问题理解 -> 查口径 -> 找数据 -> 生成/选择 SQL -> 执行 -> 分析 -> 引用。 |
| 工具输出要结构化 | 不要只返回一段文字，应返回 `data`, `sql`, `source`, `warnings`, `confidence`。 |
| 失败也要结构化 | 例如 `metric_not_found`、`ambiguous_metric`、`table_untrusted`、`sql_validation_failed`。 |

不能照搬：

| 不能照搬点 | 原因 |
| --- | --- |
| 模型自由决定是否查口径 | 对经营分析，凡涉及指标、SQL、结论，都应强制先查权威源。 |
| 工具描述写得很宽泛 | 宽泛工具会让模型错误选择。需要窄工具、明确 schema 和返回格式。 |

## 数据查询与 BI 标杆

### 1. Snowflake Cortex Analyst

Cortex Analyst 是 Snowflake Cortex 的托管 LLM 能力，面向 Snowflake 内结构化数据，支持业务用户用自然语言提问并获得答案，也可通过 REST API 集成到应用。Snowflake 还提供 Semantic View，用于定义表、关系、计算和指标，并可供 Cortex Analyst 自然语言查询。

来源：

- [Cortex Analyst](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst)
- [Semantic views overview](https://docs.snowflake.com/en/user-guide/views-semantic/overview)

核心做法：

| 模块 | 做法 |
| --- | --- |
| 数据边界 | 主要围绕 Snowflake 内结构化数据。 |
| 语义建模 | 用 semantic model / semantic view 描述表、join、指标、同义词和业务术语。 |
| 查询方式 | 自然语言 -> text-to-SQL -> Snowflake 执行 -> 返回答案。 |
| 产品形态 | REST API，可嵌入业务应用。 |
| 可靠性抓手 | 通过语义模型约束可查询对象，减少直接裸连全库。 |

可以借鉴：

| 可借鉴点 | 你们怎么用 |
| --- | --- |
| 先建小业务方向的语义视图 | 从核心 20-50 个问题反推第一批指标、维度、表、join 和 SQL 模板。 |
| 自然语言查询基于语义模型，而不是全库 schema | 只把可信表、可信字段、可信指标暴露给 Agent。 |
| API 化 | 你们可以把数据查询能力做成内部 `analysis_query` 服务，而不是只做聊天 UI。 |

不能照搬：

| 不能照搬点 | 原因 |
| --- | --- |
| 假设数据都在一个 Snowflake 里 | 你们已有指标平台、数据目录、血缘、SQL 体系，来源是多系统。 |
| 把问题缩窄成 Text-to-SQL | 经营分析还需要周报、会议、业务事件和行动建议。 |
| 只让语义模型回答“查数” | 老板常问的是“为什么”和“怎么办”，需要分析案例和业务知识对象。 |

### 2. Databricks AI/BI Genie

Databricks Genie Space 是一个 domain-specific 自然语言数据聊天界面。用户提问后，Genie 返回 SQL、结果表和可视化。Databricks 明确要求数据分析师为每个 space 配置 Unity Catalog 数据集、样例 SQL、业务语义表达和组织术语说明。

来源：[Genie Spaces](https://docs.databricks.com/aws/en/genie/)

核心做法：

| 模块 | 做法 |
| --- | --- |
| 空间划分 | 每个 Genie Space 对应一个领域或主题。 |
| 人工配置 | 分析师配置数据集、样例 SQL、业务语义和说明。 |
| 输出 | SQL、结果表、图表。 |
| 治理底座 | Unity Catalog 管理数据资产和权限。 |

可以借鉴：

| 可借鉴点 | 你们怎么用 |
| --- | --- |
| 以“小业务方向”建 domain space | 非常适合你们已确定的小业务范围。 |
| 样例 SQL 是核心语义资产 | 从历史查询和周报取数 SQL 抽取高频模板。 |
| 业务术语说明要由分析师维护 | 不要指望模型自动从表名猜业务语义。 |
| 输出 SQL 和结果表 | 让用户能审计结果来源，而不是只看自然语言结论。 |

不能照搬：

| 不能照搬点 | 原因 |
| --- | --- |
| Genie 偏数据问答和 BI 结果 | 你们还要管理报告结论、会议决策、业务假设和建议。 |
| 依赖 Unity Catalog 全栈 | 你们已有数据目录和血缘系统，应复用现有 API。 |

### 3. Microsoft Fabric / Power BI Copilot

Microsoft 明确提醒：使用 Copilot 查询 Power BI semantic model 前，必须先准备好数据、语义模型和用户；否则输出可能低质量、不准确甚至误导。Copilot 可辅助开发语义模型、生成/解释 DAX、消费语义模型，但仍要求用户验证生成内容。

来源：[Use Copilot with Semantic Models in Power BI](https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-semantic-models)

核心做法：

| 模块 | 做法 |
| --- | --- |
| 语义模型 | Power BI semantic model 是 Copilot 数据问答的基础。 |
| 开发辅助 | Copilot 帮助写 DAX、解释 DAX、生成描述。 |
| 消费问答 | 用户可向语义模型提自然语言问题。 |
| 风险提示 | 未准备好模型/数据/用户时，输出会误导。 |
| 校验机制 | DAX parser 等后处理降低幻觉，但仍需人工验证。 |

可以借鉴：

| 可借鉴点 | 你们怎么用 |
| --- | --- |
| 把“数据、模型、用户准备度”作为上线门槛 | 不要先做全量入口，先做小范围试点和问题集。 |
| 给生成的 SQL/指标解释加 parser/validator | SQL 语法、表权限、字段存在性、分区条件、结果行数都要校验。 |
| 明确提示用户验证高风险结论 | 对建议类、归因类回答标注证据级别和待验证项。 |

不能照搬：

| 不能照搬点 | 原因 |
| --- | --- |
| 以报表消费为中心 | 你们目标是经营分析 Agent，不只是 Power BI 报表问答。 |
| 把语义模型局限在 BI 模型 | 你们还需要报告、会议、SQL 模板、业务事件和历史案例。 |

### 4. Google Looker Conversational Analytics

Looker Conversational Analytics 使用 Gemini for Google Cloud 解释自然语言，并基于 Looker semantic model / LookML 作为事实来源。Google 强调 LookML 中定义的收入、流失等业务指标可以帮助回答保持准确和一致。

来源：[Conversational Analytics in Looker overview](https://docs.cloud.google.com/looker/docs/conversational-analytics-overview)

核心做法：

| 模块 | 做法 |
| --- | --- |
| 事实来源 | LookML semantic model。 |
| 业务定义 | 指标、字段、计算逻辑在 LookML 中集中定义。 |
| 查询入口 | Conversational Analytics / API。 |
| 目标 | 用自然语言获得一致、准确的数据答案。 |

可以借鉴：

| 可借鉴点 | 你们怎么用 |
| --- | --- |
| 语义层是 AI 的 source of truth | 指标平台和数据目录应成为 Agent 的事实底座。 |
| 用业务定义消除同名指标歧义 | 对“收入”“转化”“有效用户”等必须建 glossary 和适用场景。 |
| 支持 API 化 | 未来可以把经营分析能力嵌入 IM、门户或报告系统。 |

不能照搬：

| 不能照搬点 | 原因 |
| --- | --- |
| 假设 LookML 已覆盖所有业务定义 | 你们需要从已有指标平台、周报、会议和 SQL 里逐步抽取。 |
| 只服务标准 BI 问数 | 经营分析还要沉淀归因、复盘和建议。 |

### 5. Amazon Bedrock Knowledge Bases + QuickSight Q / Amazon Q

Bedrock Knowledge Bases 支持连接结构化数据源，把自然语言转换为适合数据源的查询语言，再检索相关数据并生成回答。QuickSight Q / Amazon Q in QuickSight 则通过 Topic、字段说明、同义词和自然语言友好配置，让业务用户问数、生成可视化和摘要。

来源：

- [Bedrock Knowledge Bases for structured data](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-build-structured.html)
- [Making QuickSight topics natural-language-friendly](https://docs.aws.amazon.com/quick/latest/userguide/topics-natural-language.html)
- [Generative BI with QuickSight](https://docs.aws.amazon.com/quick/latest/userguide/quicksight-gen-bi.html)

核心做法：

| 模块 | 做法 |
| --- | --- |
| Structured KB | 自然语言 -> 查询语言 -> 数据源检索 -> 生成回答。 |
| Topic | 给数据集和字段补充业务说明、同义词、字段角色。 |
| BI 体验 | 问答、视觉对象生成、dashboard executive summary、data story。 |

可以借鉴：

| 可借鉴点 | 你们怎么用 |
| --- | --- |
| Topic 化 | 按小业务方向定义“经营分析 Topic”，限制数据集、指标和术语。 |
| 字段自然语言友好化 | 数据目录字段说明不够时，要补业务别名、常见问法、反例。 |
| 结构化数据和知识库可在同一 agent workflow 里结合 | 先查报告证据，再查实时指标，或反过来。 |

不能照搬：

| 不能照搬点 | 原因 |
| --- | --- |
| 把 structured KB 当成完整经营分析系统 | 它主要解决查结构化数据，不解决历史业务判断的可信沉淀。 |
| 先做漂亮 dashboard/story | 第一阶段更缺的是口径、数据可信度、问题集和证据链。 |

### 6. Tableau Next / Tableau Pulse / Tableau Agent

Tableau Next 强调 API-first analytics、统一数据层和 trusted semantics。Salesforce 的 Hosted MCP Servers 文档中，Tableau Analytics Agent 可以对目标 semantic model 执行自然语言问题，解释问题、选择指标和维度、执行分析，并返回结构化结果和摘要。Tableau Pulse 则偏自动洞察，关注 driver、trend、outlier 和自然语言解释。

来源：

- [Tableau Next MCP Server](https://developer.salesforce.com/docs/platform/hosted-mcp-servers/guide/tableau-next.html)
- [Tableau Pulse](https://www.tableau.com/products/tableau-pulse)
- [Tableau Semantics](https://www.tableau.com/products/tableau-semantics)

核心做法：

| 模块 | 做法 |
| --- | --- |
| 语义层 | Tableau Semantics / Data 360。 |
| Agent 工具化 | MCP server 暴露分析工具，输入自然语言和目标语义模型。 |
| 结构化输出 | interpreted question、data used、computed results、narrative summary。 |
| 主动洞察 | Pulse 自动检测趋势、异常和驱动因素。 |

可以借鉴：

| 可借鉴点 | 你们怎么用 |
| --- | --- |
| 输出必须结构化 | 每次分析都返回“解释后的问题、使用的数据、计算结果、自然语言摘要”。 |
| `readOnly` / `openWorld=false` 这类工具标注很重要 | 经营分析查询工具应默认只读、封闭世界、可审计。 |
| 主动洞察适合后续版本 | 第一版先做问答，第二版可做周报自动异常发现。 |

不能照搬：

| 不能照搬点 | 原因 |
| --- | --- |
| 直接追求 agentic analytics 全体验 | 对你们来说，先把“可信数据 + 解释证据 + SQL 校验”做好更关键。 |
| 认为 semantic layer 可以自动生成后无人维护 | 语义层需要 owner、版本、审核和业务反馈。 |

### 7. ThoughtSpot Spotter / Spotter Semantics

ThoughtSpot Spotter 把自然语言问题转换成 ThoughtSpot search tokens，而不是直接生成 SQL。其宣传重点是用语义层、搜索 token、聚合感知和建模语言降低 Text-to-SQL 的不确定性。

来源：

- [Introducing Spotter](https://www.thoughtspot.com/blog/introducing-spotter-ai-analyst)
- [Spotter Semantics](https://www.thoughtspot.com/product/spotter-semantics)

核心做法：

| 模块 | 做法 |
| --- | --- |
| 中间表示 | 自然语言 -> search tokens / TML -> 查询。 |
| 语义层 | Spotter Semantics 管理业务上下文。 |
| 目标 | 让自然语言分析更确定、更可解释。 |

可以借鉴：

| 可借鉴点 | 你们怎么用 |
| --- | --- |
| 不要让模型一步到 SQL | 可以先生成 `MetricQueryPlan`：指标、维度、过滤、时间、排序、对比方式，再转 SQL。 |
| 用中间表示做校验和解释 | 用户能看到“我理解你要查什么”，减少误查。 |
| 聚合感知 | 优先用 ADS/汇总表和可信指标表，避免扫明细表。 |

不能照搬：

| 不能照搬点 | 原因 |
| --- | --- |
| 完全避开 SQL | 你们已有 SQL 查询体系，SQL 仍是重要执行层。 |
| 只关注问数体验 | 经营分析的重点是从问数走向归因和建议。 |

## 数据治理与语义层标杆

### 1. dbt Semantic Layer / MetricFlow

MetricFlow 负责 SQL 构造，并定义 dbt semantic models 和 metrics 的规格。它让指标和语义模型在 dbt 项目中声明，再由工具生成查询。

来源：[About MetricFlow](https://docs.getdbt.com/docs/build/about-metricflow)

可借鉴：

| 可借鉴点 | 你们怎么用 |
| --- | --- |
| 指标定义代码化/配置化 | 指标平台若已有 API，可同步生成内部 `MetricDefinition` 配置快照。 |
| 指标查询不要每次从零生成 SQL | 用指标定义 + 维度 + 时间粒度生成规范 SQL。 |
| 指标层和数仓表解耦 | 用户问“GMV”，Agent 不应直接暴露底层复杂表结构。 |

不能照搬：

| 不能照搬点 | 原因 |
| --- | --- |
| 必须迁移到 dbt | 你们已有指标平台，重点是接入和抽象，不是换技术栈。 |
| 只建 metrics，不建归因知识 | dbt 主要解决指标计算，不解决经营解释。 |

### 2. DataHub / Business Glossary

DataHub 的 Business Glossary 提供共享业务词表，并把 terms 关联到物理数据资产；term 和 term group 可以有 owner、文档和层级关系，也支持在 Git 中管理。

来源：[DataHub Business Glossary](https://docs.datahub.com/docs/glossary/business-glossary)

可借鉴：

| 可借鉴点 | 你们怎么用 |
| --- | --- |
| 建共享业务词表 | “新客”“有效订单”“GMV”“转化率”等都应有定义、别名、反例和 owner。 |
| 术语关联数据资产 | 术语不仅是文档，要挂到指标、表、字段、SQL 模板。 |
| Git/变更流程 | 重要定义需要 review，不应让 LLM 自动修改权威口径。 |

不能照搬：

| 不能照搬点 | 原因 |
| --- | --- |
| 只做 glossary UI | AI 需要工具化 API、结构化返回和上下文组装。 |
| 把 glossary 当成一次性文档整理 | 词表会随业务演进，需要版本和 owner。 |

### 3. OpenMetadata / 数据目录 / 血缘

OpenMetadata 把数据资产、数据质量、血缘、owner、glossary、tags、policies 等组织成统一 metadata 图谱。对经营分析 Agent 来说，关键不是 UI，而是让 Agent 知道“表是否可信、字段含义是什么、上游怎么来、下游谁在用、是否有质量风险”。

来源：

- [OpenMetadata glossary](https://docs.open-metadata.org/v1.12.x/how-to-guides/data-governance/glossary)
- [OpenMetadata lineage](https://docs.open-metadata.org/v1.11.x/how-to-guides/data-lineage)

可借鉴：

| 可借鉴点 | 你们怎么用 |
| --- | --- |
| 数据目录是 Agent 选表前置步骤 | `find_dataset` 返回 owner、业务域、刷新频率、质量、血缘、推荐级别。 |
| 血缘用于解释和风险判断 | 指标异常时可追上游表、任务、来源变化。 |
| 数据质量信号参与排序 | 不要只按名字相似度选表，应优先可信表。 |

不能照搬：

| 不能照搬点 | 原因 |
| --- | --- |
| 另建一套目录系统 | 你们已有数据目录/血缘 API，优先复用。 |
| 让 Agent 直接遍历全量 lineage 图 | 要针对问题做局部展开，避免上下文爆炸。 |

## Text-to-SQL 与评估资料

### 1. BIRD / Spider 的启发

BIRD benchmark 强调 Text-to-SQL 不只要正确，还要高效，并引入外部知识证据；Spider 强调跨数据库和复杂 SQL 泛化。

来源：

- [BIRD benchmark](https://bird-bench.github.io/)
- [Spider](https://yale-lily.github.io/spider)

可借鉴：

| 可借鉴点 | 你们怎么用 |
| --- | --- |
| Text-to-SQL 评估不能只看语法 | 要看执行结果、查询成本、是否使用可信表、是否符合口径。 |
| 外部知识很重要 | 业务规则、口径说明、字段含义、周报结论都可能影响 SQL。 |
| 需要内部 golden set | 公开 benchmark 不代表你们业务可用。 |

不能照搬：

| 不能照搬点 | 原因 |
| --- | --- |
| 用公开 benchmark 成绩证明内部可用 | 企业数据有口径、权限、表可信度、中文业务术语和历史习惯。 |
| 只评估 SQL exact match | 同一问题可能有多种 SQL；更应评估执行结果和业务解释。 |

### 2. 推荐的内部评估集

第一版不需要大而全，建议先建 80-150 条高质量样例：

| 样例类型 | 数量建议 | 标准答案 |
| --- | --- | --- |
| 指标口径查询 | 20-30 | 正确指标定义、公式、适用范围、来源。 |
| 数据表/字段发现 | 15-20 | 推荐表、字段、owner、刷新频率、为什么可信。 |
| 取数 / SQL | 20-30 | SQL、执行结果、使用表、分区、口径说明。 |
| 指标波动解释 | 15-25 | 计算结果、相关维度、历史案例、证据和不确定性。 |
| 建议类问题 | 10-20 | 建议、证据、风险、验证指标、不能确定的部分。 |

评估维度：

| 维度 | 说明 |
| --- | --- |
| Intent accuracy | 是否理解用户真正要问的是口径、取数、解释、建议还是报告问答。 |
| Metric correctness | 是否使用正确指标和口径版本。 |
| Asset correctness | 是否选择可信表/字段，而不是名字相似但错误的表。 |
| SQL validity | SQL 是否能执行、是否符合语法、是否有分区/时间过滤。 |
| Result correctness | 执行结果是否和人工标准一致。 |
| Evidence quality | 是否引用报告、会议、指标平台、数据目录、SQL 结果等证据。 |
| Uncertainty handling | 不确定时是否追问、标注待确认，而不是硬编。 |
| Cost and latency | 是否避免扫大表、是否控制查询成本。 |
| Business usefulness | 答案是否对经营决策有帮助，而不是只复述数据。 |

## 标杆方案对比总表

| 标杆 | 核心能力 | 最值得借鉴 | 不能照搬 |
| --- | --- | --- | --- |
| Anthropic Claude Code / MCP | Agent 工具调用、按需上下文、代码执行、外部系统连接 | just-in-time context、MCP 工具化、代码/SQL 执行前过滤 | 直接让 coding agent 自由连生产数仓 |
| Anthropic Contextual Retrieval | 给 chunk 增加上下文，混合检索和 rerank | 周报/会议 chunk 必须补时间、业务域、指标、章节 | 只做 chunk RAG，不做结构化知识对象 |
| Snowflake Cortex Analyst | 自然语言问 Snowflake 数据，依赖语义模型 | 语义模型 + REST API + text-to-SQL 执行 | 假设数据都在一个数仓，忽视报告/会议知识 |
| Databricks Genie | domain-specific 数据聊天空间 | 小业务方向 space、样例 SQL、业务术语人工配置 | 只做数据问答，不做归因和建议 |
| Power BI Copilot | 基于 semantic model 的 BI copilot | 明确模型/数据/用户准备度；DAX/查询校验 | 以报表消费为中心 |
| Looker Conversational Analytics | 基于 LookML semantic model 的自然语言分析 | 语义层是 source of truth | 假设 LookML 已经覆盖一切 |
| Bedrock KB / QuickSight Q | structured KB、Topic、生成式 BI | Topic 化、字段自然语言友好化 | 把 structured KB 当完整经营分析系统 |
| Tableau Next / Pulse | trusted semantics、MCP agent、主动洞察 | 结构化输出、只读工具、异常洞察 | 过早追求完整 agentic analytics 平台 |
| ThoughtSpot Spotter | search tokens / semantic layer / 聚合感知 | 自然语言先转中间表示，再执行查询 | 完全回避 SQL 或只做问数 |
| dbt MetricFlow | 指标语义模型和 SQL 构造 | 指标查询规范化、指标与底层表解耦 | 迁移技术栈或只做指标层 |
| DataHub / OpenMetadata | glossary、lineage、owner、metadata graph | 业务词表、资产关联、质量和血缘信号 | 只做目录 UI，不做 Agent API |

## 对你们的推荐方案

### 1. 产品定位

第一阶段建议定位为：

```text
经营分析 Agent 的可信知识与取数底座
```

不要定位为：

```text
万能企业知识库
万能问数机器人
自动生成经营建议的黑盒大模型
```

因为你们真正要解决的是：

| 目标 | 关键问题 |
| --- | --- |
| 查得准 | 指标口径、表、字段、SQL 不能错。 |
| 解释有证据 | 归因要能回到数据、报告、会议、历史案例。 |
| 建议可验证 | 建议要带适用条件、风险和验证指标。 |
| 可持续维护 | 业务定义、表可信度、案例经验会变化。 |

### 2. 推荐总体架构

```text
用户问题
  ↓
意图识别与任务路由
  ├─ 指标口径查询
  ├─ 数据资产发现
  ├─ 取数 / SQL 查询
  ├─ 指标波动解释
  ├─ 报告/会议问答
  └─ 建议生成 / 专题分析
  ↓
工具调用层
  ├─ 指标平台 API
  ├─ 数据目录 API
  ├─ 血缘 API
  ├─ SQL 只读执行器
  ├─ 报告/周报检索
  ├─ 会议纪要检索
  ├─ 历史案例/Playbook 检索
  └─ 业务事件/指标波动库
  ↓
知识组装层
  ├─ 结构化事实
  ├─ SQL 执行结果
  ├─ 文档证据片段
  ├─ 历史案例
  ├─ 不确定性/冲突
  └─ 引用来源
  ↓
回答生成与校验
  ├─ 结论
  ├─ 证据
  ├─ SQL/数据来源
  ├─ 风险与假设
  └─ 下一步建议
```

### 3. 第一版知识对象

优先抽取这 8 类，和现有方案保持一致：

| 知识对象 | 来源 | 用途 |
| --- | --- | --- |
| `MetricDefinition` | 指标平台、口径文档 | 查口径、生成 SQL、解释指标。 |
| `DatasetAsset` / `ColumnAsset` | 数据目录、血缘系统 | 选表、选字段、解释数据来源。 |
| `SQLTemplate` | 历史 SQL、查询日志、报告取数 | 复用稳定查询路径。 |
| `ReportCard` | 周报、专题报告 | 提供报告级摘要、时间范围、核心结论。 |
| `MetricMovement` | 周报、报告、看板摘要 | 记录某指标在某周期的变化。 |
| `BusinessEvent` | 周报、会议、运营记录 | 解释指标变化的候选原因。 |
| `Hypothesis` | 分析报告、复盘、会议讨论 | 记录归因假设、证据和反证。 |
| `ActionRecommendation` | 报告建议、复盘结论、会议 action | 生成建议时复用。 |

### 4. 第一版工具清单

建议不要超过 12 个工具：

| 工具 | 输入 | 输出 | 备注 |
| --- | --- | --- | --- |
| `classify_business_question` | 用户问题 | intent、所需信息、是否需追问 | 可先由模型完成，但输出结构化。 |
| `metric_search` | 指标名/别名/业务描述 | 候选指标、口径、owner、状态 | 调指标平台。 |
| `metric_get_definition` | metric_id | 完整定义、公式、维度、有效期 | 权威源。 |
| `asset_search` | 业务实体/字段/指标 | 表、字段、可信度、owner、刷新频率 | 调数据目录。 |
| `lineage_get` | 表/字段/指标 ID | 上下游、依赖、影响范围 | 调血缘系统。 |
| `sql_template_search` | 意图、指标、维度 | SQL 模板、参数、使用条件 | 从历史 SQL 抽取。 |
| `sql_generate_plan` | 指标、维度、过滤、时间 | 中间查询计划 | 先生成计划，不直接生成 SQL。 |
| `sql_validate` | SQL / query plan | 语法、表字段、权限、成本、风险 | 必须有。 |
| `sql_execute_readonly` | 已验证 SQL | 结果表、行数、耗时、SQL、来源 | 只读、限额。 |
| `knowledge_search` | 问题、metadata filter | 报告/会议/案例片段 | Hybrid search。 |
| `case_search` | 指标波动/业务问题 | 历史案例、结论、证据、后续效果 | 支撑“为什么”。 |
| `answer_audit_log` | 本次工具链路 | trace、引用、用户反馈 | 用于评估和复盘。 |

### 5. 典型任务流程

#### 流程 A：查指标口径

```text
用户：GMV 这里按什么口径算？
  ↓
metric_search("GMV")
  ↓
如果多个 GMV：按业务域/时间/报表上下文澄清
  ↓
metric_get_definition(metric_id)
  ↓
返回：定义、公式、粒度、过滤条件、适用范围、owner、更新时间、来源链接
```

回答要求：

| 必须包含 | 不能做 |
| --- | --- |
| 权威来源、版本、适用范围、owner | 不要根据周报片段自己总结口径。 |
| 与相似指标区别 | 不要把 GMV、支付金额、收入混为一谈。 |

#### 流程 B：取数 / 数据查询

```text
用户：看一下上周新客转化率按渠道的变化
  ↓
metric_search("新客转化率")
  ↓
asset_search(metric.related_assets)
  ↓
sql_template_search(metric_id, dims=["渠道"], time="上周")
  ↓
sql_generate_plan
  ↓
sql_validate
  ↓
sql_execute_readonly
  ↓
返回：结果表、SQL、口径、分区条件、注意事项
```

回答要求：

| 必须包含 | 不能做 |
| --- | --- |
| 指标口径、时间范围、维度、SQL 或查询计划、结果表 | 不要只给自然语言“看起来下降了”。 |
| 数据延迟/刷新时间 | 不要忽略数据未更新的风险。 |

#### 流程 C：解释指标为什么下降

```text
用户：这个指标为什么上周下降这么多？
  ↓
确认指标和时间范围
  ↓
查口径和历史趋势
  ↓
分维拆解：渠道/区域/用户/商品/活动/版本
  ↓
检索同期 BusinessEvent / 周报 / 会议 / 历史案例
  ↓
形成候选 Hypothesis
  ↓
用数据验证或标注待验证
  ↓
返回：最可能原因、证据、反证、不确定性、下一步验证
```

回答结构建议：

| 模块 | 内容 |
| --- | --- |
| 结论摘要 | 最可能的 1-3 个原因，按证据强弱排序。 |
| 数据证据 | 指标变化、贡献度、分维结果、SQL 来源。 |
| 业务证据 | 周报、会议、活动、策略变更、历史案例。 |
| 反证/不确定性 | 哪些可能原因被排除，哪些还缺数据。 |
| 下一步 | 建议继续查什么、谁确认、如何验证。 |

#### 流程 D：生成经营建议

```text
用户：那我们怎么做得更好？
  ↓
先复述当前已确认问题
  ↓
检索历史类似案例和 action recommendation
  ↓
结合当前指标拆解和业务事件
  ↓
输出建议、适用条件、预期影响、风险、验证指标
```

回答要求：

| 必须包含 | 不能做 |
| --- | --- |
| 建议的证据来源和适用条件 | 不要给泛泛运营建议。 |
| 验证指标和观察窗口 | 不要把建议说成确定有效。 |
| 风险和副作用 | 不要只写收益。 |

## 第一阶段建设路线

### Phase 0：定义评估问题集

时间建议：1 周。

产出：

| 产出 | 内容 |
| --- | --- |
| 老板/业务高频问题 50 条 | 覆盖口径、取数、下降原因、建议、报告问答。 |
| 核心指标 20-30 个 | 指标名、别名、公式、owner、常用维度。 |
| 核心数据资产 20-50 张表 | 推荐表、禁用表、字段说明、刷新频率。 |
| 黄金答案样例 30-50 条 | 用来评估第一版 Agent。 |

验收标准：

| 标准 | 说明 |
| --- | --- |
| 问题覆盖真实场景 | 不要编 demo 问题。 |
| 每个问题有标准答案或人工评审口径 | 否则无法判断是否进步。 |

### Phase 1：可信语义底座

时间建议：2-3 周。

产出：

| 产出 | 内容 |
| --- | --- |
| `MetricDefinition` 同步 | 从指标平台同步核心指标。 |
| `DatasetAsset` 同步 | 从数据目录同步核心表和字段。 |
| `BusinessGlossary` | 业务术语、别名、反例、owner。 |
| `SQLTemplate` 初版 | 高频取数 SQL 模板 20-50 条。 |
| `ReportCard` 初版 | 近期周报/报告结构化摘要。 |

验收标准：

| 标准 | 说明 |
| --- | --- |
| Agent 能查准口径 | 核心指标准确率接近 100%。 |
| Agent 能推荐可信表 | 不只按表名相似度，而按权威和使用场景。 |
| 每个结论能回源 | 指标平台、数据目录、报告链接可追溯。 |

### Phase 2：受控数据查询 Agent

时间建议：2-4 周。

产出：

| 产出 | 内容 |
| --- | --- |
| 查询计划中间表示 | `MetricQueryPlan`，先解释意图再转 SQL。 |
| SQL validator | 语法、字段、权限、成本、分区、limit。 |
| 只读 SQL executor | 限额、审计、结果表、SQL 回传。 |
| 查询 trace | 保存工具调用链路和结果。 |

验收标准：

| 标准 | 说明 |
| --- | --- |
| SQL 可执行率 | 核心问题集 >= 90%。 |
| 结果正确率 | 人工评审 >= 80%，逐步提升。 |
| 高风险问题能追问 | 指标/时间/业务域不明确时不硬查。 |

### Phase 3：经营解释与建议

时间建议：3-6 周。

产出：

| 产出 | 内容 |
| --- | --- |
| `MetricMovement` 抽取 | 从周报/报告抽取指标变化。 |
| `BusinessEvent` 抽取 | 活动、策略、版本、渠道变化等。 |
| `Hypothesis` 抽取 | 归因假设、证据、反证、状态。 |
| `ActionRecommendation` 抽取 | 建议、适用条件、风险、验证指标。 |
| 分析 Playbook | 流量、转化、留存、交易等常见分析流程。 |

验收标准：

| 标准 | 说明 |
| --- | --- |
| 能解释历史已知案例 | 对过去周报中的波动，Agent 能复原主要原因和证据。 |
| 建议不泛泛 | 建议必须绑定证据、适用条件和验证指标。 |
| 不确定性表达清楚 | 缺数据、冲突证据、待确认项不能伪装成结论。 |

## 建议的数据结构草案

### MetricQueryPlan

```yaml
question: "上周新客转化率按渠道变化"
intent: "metric_query"
metric:
  id: "metric_new_user_conversion_rate"
  name: "新客转化率"
time_range:
  grain: "day"
  start: "2026-06-01"
  end: "2026-06-07"
dimensions:
  - name: "渠道"
filters:
  - field: "user_type"
    op: "="
    value: "new"
comparison:
  type: "wow"
preferred_assets:
  - "ads_xxx_daily"
risk_checks:
  - "metric_definition_confirmed"
  - "asset_trusted"
  - "partition_filter_required"
```

### AnalysisEvidencePack

```yaml
question: "为什么上周新客转化率下降？"
metric_evidence:
  - metric_id: "metric_new_user_conversion_rate"
    movement: "-8.4%"
    source_sql: "..."
dimension_breakdown:
  - dimension: "渠道"
    top_contributor: "渠道A"
    contribution: "62%"
business_events:
  - event: "渠道A投放策略调整"
    date: "2026-06-03"
    source: "周报链接"
historical_cases:
  - case_id: "case_2026_04_channel_quality_drop"
    similarity: 0.82
hypotheses:
  - hypothesis: "渠道A流量质量下降导致整体转化率下降"
    support: ["渠道A贡献主要降幅", "同期投放策略调整"]
    counter_evidence: ["其他渠道基本稳定"]
    confidence: "medium"
open_questions:
  - "需确认渠道A投放人群包是否变化"
```

## 可借鉴与不可借鉴清单

### 强烈建议借鉴

| 借鉴项 | 来源 | 为什么重要 |
| --- | --- | --- |
| just-in-time context | Anthropic Claude Code | 大量报告、表结构、SQL 不能一次塞给模型。 |
| MCP / 工具化接入 | Anthropic MCP | 已有指标平台、目录、血缘、SQL 系统应成为工具。 |
| Contextual Retrieval | Anthropic | 周报/会议 chunk 必须带上下文，否则检索和引用质量差。 |
| Domain-specific space | Databricks Genie、QuickSight Topic | 小业务方向先做封闭空间，准确率和维护性更好。 |
| Semantic model/source of truth | Snowflake、Looker、Power BI | 口径一致性是数据问答的生命线。 |
| 中间查询表示 | ThoughtSpot、语义层产品 | 先生成查询计划，再生成 SQL，便于校验和解释。 |
| SQL/parser/validator | Power BI、Text-to-SQL 工程实践 | 降低幻觉、错表、扫大表和口径错误。 |
| 结构化输出和 trace | Tableau MCP、Agent SDK 思路 | 经营分析需要审计、复盘和持续评估。 |

### 谨慎借鉴

| 借鉴项 | 风险 | 正确姿势 |
| --- | --- | --- |
| Text-to-SQL | 容易错表、错口径、扫大表 | 基于语义层和 SQL 模板，强制校验。 |
| 自动生成建议 | 容易泛化和过度自信 | 建议必须绑定证据、适用条件、验证指标。 |
| 自动抽取会议结论 | 会议噪声大，未必是事实 | 标注 `待确认` / `已确认` / `已废弃`。 |
| 主动异常洞察 | 指标多时噪声很大 | 先覆盖核心指标，后续再扩展。 |
| 多 Agent | 容易增加复杂度 | 先用单 Agent + 工具路由；复杂专题再拆子 Agent。 |

### 不建议照搬

| 不建议项 | 原因 |
| --- | --- |
| 只建 Milvus 向量库 | 向量库不能保证口径、表可信度、SQL 正确性和业务判断。 |
| 直接开放全库问数 | 准确率、权限、成本和误导风险都不可控。 |
| 只做一个聊天框 | 经营分析需要结构化工具链、证据链和工作流，不是 UI 问答。 |
| 让模型直接写 SQL 并执行 | 必须有查询计划、validator、限额、只读、审计和人工兜底。 |
| 把周报/会议原文当权威事实 | 这些是过程性证据，要抽取状态和置信度。 |
| 以公开 Text-to-SQL benchmark 作为上线依据 | 内部业务口径和数据复杂度不同，必须有内部评估集。 |

## 下周分享建议结构

如果要做 20-30 分钟分享，建议按这个顺序：

| 页 | 标题 | 核心内容 |
| --- | --- | --- |
| 1 | 我们要解决的不是“文档问答” | 典型经营问题：为什么下降、怎么办、怎么取数。 |
| 2 | 行业共识：AI 问数靠语义层和工具，不靠裸模型 | 标杆总览表。 |
| 3 | Anthropic 给我们的工程启发 | just-in-time context、MCP、code execution、contextual retrieval。 |
| 4 | 数据查询标杆怎么做 | Snowflake、Databricks、Power BI、Looker。 |
| 5 | 语义层和治理为什么是底座 | 指标、术语、数据目录、血缘、质量、owner。 |
| 6 | 为什么不能只做 Milvus / RAG | 向量库能召回资料，但不能保证口径和执行正确。 |
| 7 | 推荐总体架构 | 用户问题 -> 工具调用 -> 知识组装 -> 回答校验。 |
| 8 | 第一版怎么落地 | Phase 0-3 路线。 |
| 9 | 评估标准 | golden set、SQL 正确、证据质量、业务有用性。 |
| 10 | 需要业务团队配合什么 | 核心问题、指标、可信表、样例 SQL、周报/会议沉淀。 |

## 给管理层的表达版本

可以这样讲：

> 行业里现在成熟的 AI 数据查询方案，不是让大模型直接读数据库，也不是把文档全部向量化后搜索。真正可用的方案都有一个共同特点：先把指标、维度、表、字段、口径、血缘和业务术语做成可信语义层，再让 AI 通过受控工具去查数据、执行 SQL、引用报告证据，最后给出可追溯的解释和建议。
>
> 所以我们的第一阶段重点不是做一个炫酷聊天框，而是建设经营分析 Agent 的可信底座：核心指标、可信表、SQL 模板、周报案例、业务事件、归因假设和建议库。这样后面无论接入 IM、报表系统还是自动周报，都有同一套可信知识和工具能力。

## 待确认问题

| 问题 | 为什么重要 |
| --- | --- |
| 小业务方向的核心指标列表是什么？ | 决定第一批 `MetricDefinition` 和评估集。 |
| 老板最常问的 20-50 个问题是什么？ | 决定产品是否真的有用。 |
| 指标平台 API 返回哪些字段？ | 决定能否直接作为权威语义源。 |
| 数据目录/血缘 API 能查到什么粒度？ | 决定 Agent 选表、解释血缘和风险提示能力。 |
| 向量知识库平台支持 metadata filter / rerank 吗？ | 决定是否需要单独补全文检索和重排层。 |
| SQL 查询执行是否能做只读、限额、审计？ | 决定能否安全上线自然语言取数。 |
| 周报里的建议有没有后续效果记录？ | 决定建议库能否学习“什么建议有效”。 |

## 资料索引

### Anthropic / Claude

| 资料 | 重点 |
| --- | --- |
| [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) | just-in-time context；Claude Code 复杂数据分析。 |
| [Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp) | 工具按需加载、进入模型前过滤数据、复杂逻辑一次执行。 |
| [Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval) | Contextual Embeddings、Contextual BM25、rerank。 |
| [Claude Code MCP](https://code.claude.com/docs/en/mcp) | Claude Code 通过 MCP 连接工具、数据库、API。 |
| [Claude tool use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview) | 模型返回结构化工具调用，应用执行后回填结果。 |
| [Claude code execution tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool) | 数据分析、可视化、计算、文件处理和安全沙箱。 |
| [Building effective agents](https://www.anthropic.com/research/building-effective-agents) | workflow/agent 模式、工具设计、prompt 和 eval。 |
| [Writing effective tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents) | 工具描述、工具选择、工具评估。 |

### 数据查询 / BI

| 资料 | 重点 |
| --- | --- |
| [Snowflake Cortex Analyst](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst) | 托管 text-to-SQL，REST API，回答结构化数据业务问题。 |
| [Snowflake Semantic Views](https://docs.snowflake.com/en/user-guide/views-semantic/overview) | 表、join、计算、指标的语义视图。 |
| [Databricks Genie Spaces](https://docs.databricks.com/aws/en/genie/) | domain-specific chat，Unity Catalog，样例 SQL，业务语义。 |
| [Power BI Copilot semantic models](https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-semantic-models) | 未准备好 semantic model 会产生低质/误导输出。 |
| [Looker Conversational Analytics](https://docs.cloud.google.com/looker/docs/conversational-analytics-overview) | LookML semantic model 是 source of truth。 |
| [Amazon Bedrock structured data KB](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-build-structured.html) | 自然语言转结构化查询并检索数据。 |
| [QuickSight natural-language-friendly topics](https://docs.aws.amazon.com/quick/latest/userguide/topics-natural-language.html) | Topic、字段说明、同义词和自然语言友好配置。 |
| [Tableau Next MCP server](https://developer.salesforce.com/docs/platform/hosted-mcp-servers/guide/tableau-next.html) | 面向 semantic model 的自然语言分析工具，结构化输出。 |
| [Tableau Pulse](https://www.tableau.com/products/tableau-pulse) | 自动检测 driver、trend、outlier 并自然语言解释。 |
| [ThoughtSpot Spotter](https://www.thoughtspot.com/blog/introducing-spotter-ai-analyst) | 自然语言转 search tokens，减少直接 Text-to-SQL 不确定性。 |

### 语义层 / 治理 / 评估

| 资料 | 重点 |
| --- | --- |
| [dbt MetricFlow](https://docs.getdbt.com/docs/build/about-metricflow) | 定义 semantic models 和 metrics，负责 SQL 构造。 |
| [DataHub Business Glossary](https://docs.datahub.com/docs/glossary/business-glossary) | 共享业务词表、关联数据资产、owner、层级关系。 |
| [OpenMetadata Glossary](https://docs.open-metadata.org/v1.12.x/how-to-guides/data-governance/glossary) | 术语、层级、关联关系。 |
| [OpenMetadata Lineage](https://docs.open-metadata.org/v1.11.x/how-to-guides/data-lineage) | 数据血缘、可追溯性和影响分析。 |
| [BIRD benchmark](https://bird-bench.github.io/) | Text-to-SQL 不只看正确，还看效率和外部知识。 |
| [Spider benchmark](https://yale-lily.github.io/spider) | 跨数据库复杂 Text-to-SQL 评估。 |
