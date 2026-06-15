---
type: project-log
status: draft
tags: [business-analysis, knowledge-base, data-processing, research-report, knowledge-graph, structured-extraction, rag]
created: 2026-06-14
updated: 2026-06-14
source:
  - https://microsoft.github.io/graphrag/
  - https://microsoft.github.io/graphrag/index/default_dataflow/
  - https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_kg_builder.html
  - https://developers.llamaindex.ai/python/framework/module_guides/indexing/lpg_index_guide/
  - https://www.anthropic.com/engineering/contextual-retrieval
  - https://docs.unstructured.io/open-source/core-functionality/chunking
  - https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/verified-query-repository
  - https://docs.databricks.com/aws/en/genie/set-up
  - https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-prepare-data-ai
  - https://docs.getdbt.com/docs/build/semantic-models
  - https://docs.datahub.com/docs/glossary/business-glossary
  - https://docs.open-metadata.org/v1.12.x/how-to-guides/data-governance/glossary
related:
  - 30-projects/经营分析AI知识库建设方案.md
  - 30-projects/经营分析AI知识库行业对标调研.md
  - 30-projects/经营分析AI知识库数据处理与知识建模调研.md
---

# 经营分析 AI 知识库数据处理方法调研报告

## 0. 这份报告应该回答什么

你现在要做的不是直接选一个技术名词，而是回答：

1. 对会议纪要、周报、SQL/代码、数据文档、碎片资料，业界通常怎么处理？
2. 这些资料最终应该被加工成什么“结果物”？
3. 每种方法适合什么场景，不适合什么场景？
4. 每种方法的优点、缺点、成本、风险是什么？
5. 处理后的结构应该存在哪里：向量库、全文索引、结构化库、知识图谱、指标平台、SQL 模板库，还是原文库？
6. 对我们这个经营分析场景，哪些方法应该优先试，哪些方法暂缓？

本报告不是最终实施方案，而是用于下一步一起讨论选型。

## 1. 执行摘要

### 1.1 总判断

经营分析知识库的数据处理不能只做“文档切片 + 向量化”。合理形态应该是：

```text
原文保留
-> 文档画像
-> 语义 chunk / 证据片段
-> 结构化知识对象
-> 业务关系图谱
-> 查询资产 / Verified SQL
-> 按问题组装给大模型
```

换句话说，最终不是一个库，而是一组互补的知识资产：

| 资产 | 作用 | 主要存储 |
| --- | --- | --- |
| 原文资产 | 保留证据和版本 | 原文库 / 文档库 / Git。 |
| 证据 chunk | 支撑检索和引用 | 向量库 + 全文索引 + metadata 表。 |
| 结构化对象 | 支撑查询、审核、复用 | 结构化数据库。 |
| 业务图谱 | 支撑关系追踪、归因、类似案例 | 图数据库或 nodes/edges 关系表。 |
| 语义层 | 支撑指标口径、维度、业务术语 | 指标平台 / 语义模型 / 结构化库。 |
| Verified SQL | 支撑高频问数稳定执行 | SQL 模板库 / verified query repository。 |

### 1.2 优先级判断

| 方法 | 是否建议第一期做 | 理由 |
| --- | --- | --- |
| 文档结构解析 + SourceCard | 必须做 | 没有来源、时间、类型、权威级别，后面无法治理。 |
| Contextual Chunk + Hybrid Search | 必须做 | 周报、会议、文档需要可检索、可引用。 |
| 结构化对象抽取 | 必须做 | 这是从“资料”变成“知识”的关键。 |
| 语义层 / 指标口径对象 | 必须做 | 问数和解释都绕不开指标定义。 |
| SQLTemplate / Verified SQL | 必须做一小批 | 高频取数问题不能每次重新生成 SQL。 |
| 轻量知识图谱 | 建议做试点 | 用于连接指标、事件、假设、建议和证据。 |
| 完整 GraphRAG | 暂缓 | 适合大规模叙事语料全局理解，但第一期成本和噪声较高。 |

## 2. 调研范围与评估维度

### 2.1 调研对象

| 类别 | 调研对象 | 重点 |
| --- | --- | --- |
| RAG / chunk | Anthropic Contextual Retrieval、Unstructured chunking | 怎么切片、补上下文、混合检索、rerank。 |
| GraphRAG / 知识图谱 | Microsoft GraphRAG、Neo4j KG Builder、LlamaIndex Property Graph | 怎么从文本抽实体关系，结果物是什么，适合什么问题。 |
| 语义层 / 问数 | Snowflake VQR、Databricks Genie、Power BI Prep data for AI、dbt Semantic Layer | 怎么把数据加工成 AI 可理解的指标、维度、SQL、指令和验证答案。 |
| 数据治理 | DataHub、OpenMetadata | 业务术语、数据资产、owner、血缘、审核如何组织。 |

### 2.2 评估维度

| 维度 | 问题 |
| --- | --- |
| 输入材料 | 适合处理会议、周报、SQL、数据文档还是碎片资料？ |
| 处理动作 | 是解析、清洗、切片、抽取、对齐、入图，还是生成 SQL 模板？ |
| 结果物 | 最终拿到什么结构？ |
| 存储位置 | 应该进向量库、结构化库、图谱、语义层还是原文库？ |
| 大模型使用方式 | 模型最终如何消费这些结果？ |
| 优点 | 能提升什么能力？ |
| 缺点 | 有什么成本、风险和盲区？ |
| 适用场景 | 哪类问题最适合？ |
| 不适用场景 | 哪类问题不要用它硬做？ |
| 第一版建议 | 对我们是否应该现在做？ |

## 3. 行业做法：他们把数据处理成什么

### 3.1 Anthropic Contextual Retrieval

Anthropic 的重点不是“结构化建模”，而是解决传统 RAG 切片丢上下文的问题。它的做法是在每个 chunk 前补一段简短上下文，然后同时做 embedding 和 BM25，再结合 rerank。Anthropic 在实验中报告：Contextual Embeddings + Contextual BM25 降低了 49% 的 top-20 检索失败率，加 rerank 后降低 67%。

来源：[Anthropic Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval)

| 项目 | 内容 |
| --- | --- |
| 输入 | 长文档、报告、知识库资料、代码库。 |
| 处理 | chunk 切分；为每个 chunk 生成 50-100 token 的上下文；建立向量索引和 BM25；可加 rerank。 |
| 结果物 | `contextualized_chunk`、embedding、BM25 index、rerank 后 top-k evidence。 |
| 实际结果 | 检索到的片段更知道自己来自哪个文档、哪个时间、哪个主题。 |
| 适用 | 周报、会议纪要、专题报告、数据文档的证据检索。 |
| 不适用 | 不能替代指标口径、SQL 校验、结构化归因。 |

对我们启发：

| 可借鉴 | 不能照搬 |
| --- | --- |
| 周报/会议 chunk 必须带来源、周期、业务域、章节、相关指标。 | 不能认为检索准就等于经营分析准。 |

### 3.2 Unstructured：先解析文档元素，再 chunk

Unstructured 的 chunking 文档强调：chunk 不是从纯文本随便按字符切，而是基于 partition 识别出的文档元素，尽量保留语义单元；表格会作为独立元素处理，`by_title` 策略会保留章节边界。

来源：[Unstructured Chunking](https://docs.unstructured.io/open-source/core-functionality/chunking)

| 项目 | 内容 |
| --- | --- |
| 输入 | PDF、HTML、Word、报告等非结构化文档。 |
| 处理 | partition 成 Title、NarrativeText、Table 等元素，再合并成 chunk。 |
| 结果物 | `CompositeElement`、`Table`、`TableChunk` 等语义 chunk。 |
| 实际结果 | chunk 更像“一个完整段落/表格/章节内容”，而不是机械截断。 |
| 适用 | 周报、报告、数据文档的结构化解析。 |
| 不适用 | SQL 代码解析、指标口径权威治理。 |

对我们启发：

| 可借鉴 | 不能照搬 |
| --- | --- |
| 先把文档拆成标题、正文、表格、代码块、图表说明，再抽取知识。 | 不要只靠文档 parser，业务对象仍需 schema 抽取。 |

### 3.3 Microsoft GraphRAG

Microsoft GraphRAG 把原始文本处理成 TextUnits，再抽取 Entity、Relationship、Claim，做社区发现和社区摘要，用于 global/local/DRIFT search。它特别适合普通 RAG 不擅长的两类问题：跨资料“连点成线”和对大语料做整体理解。

来源：[GraphRAG](https://microsoft.github.io/graphrag/)、[GraphRAG Dataflow](https://microsoft.github.io/graphrag/index/default_dataflow/)

| 项目 | 内容 |
| --- | --- |
| 输入 | 大量叙事型私有文本。 |
| 处理 | TextUnit 切分；抽实体/关系/claims；实体合并；社区发现；社区摘要；embedding。 |
| 结果物 | `Document`、`TextUnit`、`Entity`、`Relationship`、`Covariate/Claim`、`Community`、`Community Report`。 |
| 实际结果 | 能回答“这批资料整体有哪些主题”“某实体周边发生了什么”“跨文档有哪些关系”。 |
| 适用 | 大量周报/会议/复盘文本的主题发现、跨文档关系发现。 |
| 不适用 | 直接做指标口径、SQL 查询、表字段治理。 |

对我们启发：

| 可借鉴 | 不能照搬 |
| --- | --- |
| 可以借鉴 `entity + relationship + claim + community summary` 的产物思路。 | 第一版不建议全量自动 GraphRAG，因为经营分析需要更严格的 schema、状态和人工确认。 |

### 3.4 Neo4j KG Builder / LlamaIndex Property Graph

Neo4j KG Builder 把 pipeline 拆成 Data loader、Text splitter、Chunk embedder、Schema builder、Entity/relation extractor、Graph pruner、Writer、Entity resolver。Neo4j 明确支持手工提供 schema 来约束 LLM 抽取，并有实体合并和图清理步骤。LlamaIndex Property Graph 也强调 labeled property graph 可以通过多种 retriever 查询节点和路径。

来源：[Neo4j KG Builder](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_kg_builder.html)、[LlamaIndex Property Graph](https://developers.llamaindex.ai/python/framework/module_guides/indexing/lpg_index_guide/)

| 项目 | 内容 |
| --- | --- |
| 输入 | 非结构化文本，也可以结合已有结构化数据。 |
| 处理 | schema-guided extraction、实体关系抽取、图清理、实体合并。 |
| 结果物 | 带 label 和属性的节点、关系、chunk-document lexical graph。 |
| 实际结果 | 可以查询“某指标关联哪些表、哪些报告、哪些假设、哪些证据”。 |
| 适用 | 经营分析对象之间的关系建模。 |
| 不适用 | 完全无 schema 的自由抽图，容易边混乱。 |

对我们启发：

| 可借鉴 | 不能照搬 |
| --- | --- |
| 第一版图谱要 schema-guided，只允许抽我们定义的节点和边。 | 不要让 LLM 自由发明实体类型和关系类型。 |

### 3.5 Snowflake Verified Query Repository

Snowflake Cortex Analyst 的 VQR 用“自然语言问题 + 已验证 SQL”提升结果准确性和可信度，且这些 verified queries 放在 semantic model YAML 里。它强调 SQL 要使用 semantic model 里的逻辑表和列名，而不是底层物理表名。

来源：[Snowflake Cortex Analyst VQR](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/verified-query-repository)

| 项目 | 内容 |
| --- | --- |
| 输入 | 高频自然语言问题、人工确认 SQL、语义模型。 |
| 处理 | 把问题和 SQL 配对，记录 verified_by、verified_at，放入 semantic model。 |
| 结果物 | `verified_queries`：问题、SQL、验证人、验证时间、onboarding 标记。 |
| 实际结果 | 相似问题不再每次从零生成 SQL，而是参考已验证查询。 |
| 适用 | 高频取数、指标查询、固定维度拆解。 |
| 不适用 | 解释“为什么”和“怎么办”的业务归因。 |

对我们启发：

| 可借鉴 | 不能照搬 |
| --- | --- |
| 建一个内部 Verified SQL / SQLTemplate 库。 | 不要只做 SQL 库，还要处理报告、会议、归因和建议。 |

### 3.6 Databricks Genie Space

Databricks Genie Space 是面向业务用户的自然语言数据问答空间。数据分析师为每个空间配置 Unity Catalog 数据、example SQL、instructions 和 trusted assets。官方还限制每个 Genie Space 可加入最多 30 个表或视图，体现了“封闭领域空间”的思路。

来源：[Databricks Genie Space](https://docs.databricks.com/aws/en/genie/set-up)

| 项目 | 内容 |
| --- | --- |
| 输入 | 可信表、样例 SQL、业务指令、权限配置。 |
| 处理 | 按业务主题建立 space；限制数据范围；补指令和样例。 |
| 结果物 | 可问数的业务数据空间。 |
| 实际结果 | 业务用户在限定主题内问数据，而不是开放全库。 |
| 适用 | 小业务方向的指标问答和数据探索。 |
| 不适用 | 全公司所有数据一口气开放，或无边界的经营建议。 |

对我们启发：

| 可借鉴 | 不能照搬 |
| --- | --- |
| 先做“小业务方向知识空间”，只放可信表、核心指标、样例 SQL。 | 不要试图第一期覆盖所有业务域和所有表。 |

### 3.7 Power BI Prep Data for AI

Power BI 的 Prep data for AI 不是让用户直接问模型，而是先准备 semantic model：AI data schemas、verified answers、AI instructions，以减少歧义，提升 grounded response。它也提醒 AI 输出具有不确定性，不能保证每次完全一致。

来源：[Power BI Prep Data for AI](https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-prepare-data-ai)

| 项目 | 内容 |
| --- | --- |
| 输入 | semantic model、报表 visual、业务说明、验证答案。 |
| 处理 | 配 AI schema、verified answers、AI instructions，测试后标记 approved。 |
| 结果物 | 更适合 Copilot 使用的语义模型。 |
| 实际结果 | 模型更能理解业务上下文，减少泛化、误读和不相关回答。 |
| 适用 | 指标/报表问答、固定口径解释。 |
| 不适用 | 没有语义模型和验证答案时直接开放给业务。 |

对我们启发：

| 可借鉴 | 不能照搬 |
| --- | --- |
| AI-ready data 需要 schema、verified answer、instructions、测试和审批。 | 不要认为“上传资料”就是 AI-ready。 |

### 3.8 DataHub / OpenMetadata / dbt Semantic Layer

DataHub 和 OpenMetadata 说明了业务 glossary 的价值：用共享词表定义业务概念，并把概念关联到物理数据资产。dbt Semantic Layer 则把 semantic model 作为 MetricFlow 的数据定义基础，包含 entities、dimensions、measures、metrics 等。

来源：[DataHub Business Glossary](https://docs.datahub.com/docs/glossary/business-glossary)、[OpenMetadata Glossary](https://docs.open-metadata.org/v1.12.x/how-to-guides/data-governance/glossary)、[dbt Semantic Models](https://docs.getdbt.com/docs/build/semantic-models)

| 项目 | 内容 |
| --- | --- |
| 输入 | 业务术语、指标定义、表字段、owner、血缘。 |
| 处理 | 建 glossary、term group、term relationship、asset tagging、semantic model。 |
| 结果物 | BusinessTerm、MetricDefinition、Dimension、Entity、Measure、DatasetAsset。 |
| 实际结果 | 让“新客”“转化率”“渠道”等业务词和真实数据资产建立稳定映射。 |
| 适用 | 指标口径、术语消歧、数据资产发现。 |
| 不适用 | 直接替代周报归因、会议行动项、历史案例总结。 |

对我们启发：

| 可借鉴 | 不能照搬 |
| --- | --- |
| 业务词表和指标语义层是经营分析知识库的底座。 | 不要只建 glossary UI，需要把它服务化给大模型调用。 |

## 4. 方法卡片：优缺点、场景和结果物

### 方法 1：文档结构解析 + 语义 chunk

| 项目 | 内容 |
| --- | --- |
| 适用输入 | 周报、专题报告、会议纪要、数据文档。 |
| 处理动作 | 解析标题、章节、段落、表格、代码块、图表说明；按语义单元切 chunk。 |
| 得到的结果 | `SourceCard`、`EvidenceChunk`、chunk metadata、原文位置。 |
| 存储位置 | 原文库；向量库；全文索引；metadata 表。 |
| 适用场景 | “找到某份周报怎么说”“引用某段会议证据”“检索文档中的字段说明”。 |
| 优点 | 快速可落地；保留证据；适合检索和引用。 |
| 缺点 | 只是证据层，不是知识层；无法稳定判断指标口径、SQL、归因。 |
| 第一版建议 | 必做，作为所有后续抽取的基础。 |

### 方法 2：Contextual Retrieval + Hybrid Search + Rerank

| 项目 | 内容 |
| --- | --- |
| 适用输入 | 所有文本型资料，尤其是周报/会议/文档。 |
| 处理动作 | 为 chunk 生成上下文说明；同时建向量和 BM25；检索后 rerank。 |
| 得到的结果 | 带文档背景的 evidence chunk 和更可靠的 top-k 证据。 |
| 存储位置 | 向量库；全文索引；rerank 服务；metadata 表。 |
| 适用场景 | 用户问模糊业务问题，需要找相关报告或会议证据。 |
| 优点 | 比裸向量检索更稳；能处理精确词和语义问题。 |
| 缺点 | 增加预处理成本和运行时 rerank 延迟；仍不能替代结构化对象。 |
| 第一版建议 | 必做，但只定位为“证据检索层”。 |

### 方法 3：结构化对象抽取

| 项目 | 内容 |
| --- | --- |
| 适用输入 | 周报、会议纪要、数据文档、SQL、复盘报告。 |
| 处理动作 | 用 schema 抽取指定对象，并保留来源、状态、置信度、owner。 |
| 得到的结果 | `MetricDefinition`、`MetricMovement`、`BusinessEvent`、`Hypothesis`、`ActionRecommendation`、`SQLTemplate`。 |
| 存储位置 | 结构化数据库；对象和证据的关系可进入图谱。 |
| 适用场景 | “这个指标为什么下降”“有哪些历史类似案例”“上次建议是什么”。 |
| 优点 | 可审核、可筛选、可复用；能区分事实、假设、建议。 |
| 缺点 | schema 设计要求高；抽取结果需要校验；自动化不会一次到位。 |
| 第一版建议 | 必做，先从周报和 SQL 抽取最有价值的对象。 |

### 方法 4：业务术语 / 指标语义层

| 项目 | 内容 |
| --- | --- |
| 适用输入 | 指标平台、数据文档、数据目录、口径文档。 |
| 处理动作 | 抽取业务术语、指标、维度、实体、度量、owner、版本、适用范围。 |
| 得到的结果 | `BusinessTerm`、`MetricDefinition`、`DimensionDefinition`、`DatasetAsset`、`ColumnAsset`。 |
| 存储位置 | 指标平台、数据目录、结构化库；关系可进图谱。 |
| 适用场景 | 查口径、消歧、生成 SQL 前确认指标和维度。 |
| 优点 | 解决问数准确性的底层问题；能对接已有权威系统。 |
| 缺点 | 不能直接解释经营变化；需要持续维护版本和 owner。 |
| 第一版建议 | 必做，并且以已有指标平台和数据目录为权威源。 |

### 方法 5：SQLTemplate / Verified SQL

| 项目 | 内容 |
| --- | --- |
| 适用输入 | 高频 SQL、历史查询、报表取数代码、分析脚本。 |
| 处理动作 | 解析 SQL；抽表字段依赖；参数化；人工验证；绑定自然语言问题。 |
| 得到的结果 | `SQLTemplate`、`VerifiedQuery`、`MetricCalculation`、`DatasetUsage`、输出 schema。 |
| 存储位置 | SQL 模板库；结构化库；Git；可关联到图谱和指标语义层。 |
| 适用场景 | 高频取数、固定指标拆解、同比环比、维度分解。 |
| 优点 | 避免每次从零生成 SQL；稳定性、可审计性高。 |
| 缺点 | 覆盖范围有限；业务变化后需要维护；不能直接处理开放式归因。 |
| 第一版建议 | 必做 20-50 条高频模板。 |

### 方法 6：轻量领域知识图谱

| 项目 | 内容 |
| --- | --- |
| 适用输入 | 已抽取的结构化对象、数据目录、指标平台、SQL 模板、报告案例。 |
| 处理动作 | 把对象变成节点；把业务关系变成边；每条边带来源、状态、置信度。 |
| 得到的结果 | 指标-维度-表-SQL-事件-假设-证据-建议之间的关系网络。 |
| 存储位置 | 图数据库，或第一版用 `nodes` / `edges` 关系表模拟。 |
| 适用场景 | 归因链路、历史类似案例、数据血缘、建议复盘。 |
| 优点 | 能回答“和什么有关”“证据链是什么”“历史上类似吗”。 |
| 缺点 | 实体对齐和关系质量是难点；自动抽取容易误连。 |
| 第一版建议 | 做小范围试点，先覆盖核心指标和周报案例。 |

### 方法 7：完整 GraphRAG

| 项目 | 内容 |
| --- | --- |
| 适用输入 | 大量叙事型文本，例如多年周报、会议、调研报告。 |
| 处理动作 | 自动抽实体、关系、claims；社区发现；社区报告；global/local search。 |
| 得到的结果 | GraphRAG 的实体、关系、claims、community reports。 |
| 存储位置 | 图存储；向量库；community report 表。 |
| 适用场景 | “这批资料整体有哪些主题”“最近两个月发生了哪些主线变化”。 |
| 优点 | 适合全局理解和跨文档发现。 |
| 缺点 | 成本高；自动构图噪声大；不擅长 SQL 和权威口径。 |
| 第一版建议 | 暂缓，不作为第一期主方案。 |

### 方法 8：数据目录 / 血缘 / glossary 治理

| 项目 | 内容 |
| --- | --- |
| 适用输入 | 数据目录、血缘系统、owner、质量信息、业务词表。 |
| 处理动作 | 将术语、表、字段、指标、owner、血缘、质量状态关联。 |
| 得到的结果 | `BusinessTerm -> Dataset/Column/Metric` 的治理关系。 |
| 存储位置 | 现有数据目录/血缘系统；结构化库缓存；图谱。 |
| 适用场景 | 判断哪个表可信、字段什么意思、数据从哪里来。 |
| 优点 | 能降低错表、错字段、旧口径风险。 |
| 缺点 | 不直接产生经营结论；依赖数据治理质量。 |
| 第一版建议 | 必须接入，但不要另造一套权威系统。 |

## 5. 按原始资料映射：处理成什么、存哪里

### 5.1 会议纪要

| 处理方法 | 得到的结果 | 存哪里 | 适用场景 | 风险 |
| --- | --- | --- | --- | --- |
| SourceCard | 会议时间、主题、业务域、参会方、权威等级 | 结构化库 | 过滤会议资料 | 会议标题不规范。 |
| EvidenceChunk | 带议题上下文的原文片段 | 向量库 + 全文索引 | 查原文证据 | 发言断章取义。 |
| 结构化抽取 | `DecisionRecord`、`ActionItem`、`Hypothesis`、`BusinessEvent` | 结构化库 | 查决策、行动项、待验证假设 | 猜测被当事实。 |
| 图谱关系 | 会议 -> 议题 -> 假设 -> 指标 -> 证据 | 图谱/edges 表 | 复盘某次决策链路 | 关系误连。 |

建议第一版结果样子：

```yaml
meeting_extraction:
  meeting_card: {...}
  decisions: [...]
  action_items: [...]
  hypotheses:
    - statement: "渠道A流量质量下降可能影响新客转化"
      status: "pending_verification"
      evidence_chunk_ids: [...]
  business_events: [...]
```

### 5.2 周报 / 专题报告

| 处理方法 | 得到的结果 | 存哪里 | 适用场景 | 风险 |
| --- | --- | --- | --- | --- |
| SourceCard | 报告周期、业务域、核心指标、作者 | 结构化库 | 按时间/业务域检索报告 | 报告周期和数据周期不同。 |
| EvidenceChunk | 结论段、指标解释段、建议段 | 向量库 + 全文索引 | 引用报告证据 | chunk 缺少图表上下文。 |
| 结构化抽取 | `MetricMovement`、`Hypothesis`、`ActionRecommendation`、`BusinessEvent` | 结构化库 | 解释指标变化、生成建议 | 归因没有后续验证。 |
| 图谱关系 | 指标波动 -> 候选原因 -> 证据 -> 建议 -> 后续结果 | 图谱/edges 表 | 找历史类似案例 | 因果关系过度断言。 |

建议第一版结果样子：

```yaml
report_extraction:
  report_card: {...}
  metric_movements:
    - metric: "新客转化率"
      direction: "down"
      relative_change: "-8.4%"
      top_contributors: [...]
  hypotheses: [...]
  recommendations: [...]
  follow_up_signals: [...]
```

### 5.3 数据代码 / SQL

| 处理方法 | 得到的结果 | 存哪里 | 适用场景 | 风险 |
| --- | --- | --- | --- | --- |
| SQL parser | 表、字段、join、where、group by、输出列 | 结构化库 | 理解取数逻辑 | 动态 SQL 解析困难。 |
| SQLTemplate | 参数化查询模板 | SQL 模板库 / Git | 高频取数 | 模板维护成本。 |
| Verified SQL | 自然语言问题 + 人工验证 SQL | Verified Query Repository | 稳定回答高频问题 | 覆盖不足。 |
| LineageEdge | SQL -> 表字段 -> 指标 | 图谱/血缘系统 | 影响分析、错表防控 | 字段级血缘成本高。 |

建议第一版结果样子：

```yaml
verified_query:
  question: "上周新客转化率按渠道变化"
  sql_template_id: "sql_new_user_cvr_by_channel"
  verified_by: "增长分析师"
  input_assets: [...]
  output_schema: [...]
  safety_rules: ["must_include_partition", "readonly"]
```

### 5.4 数据文档

| 处理方法 | 得到的结果 | 存哪里 | 适用场景 | 风险 |
| --- | --- | --- | --- | --- |
| Glossary 抽取 | 业务术语、别名、反例、owner | 术语库/结构化库 | 术语消歧 | 术语过期。 |
| MetricDefinition | 指标公式、维度、过滤条件、版本 | 指标平台/结构化库 | 查口径、生成 SQL | 和权威平台冲突。 |
| DatasetAsset | 表说明、owner、刷新频率、推荐状态 | 数据目录/结构化库 | 找可信表 | 文档和实际表不一致。 |
| ColumnAsset | 字段含义、枚举、敏感等级 | 数据目录/结构化库 | 字段理解 | 字段说明不完整。 |

建议第一版结果样子：

```yaml
metric_definition:
  name: "新客转化率"
  aliases: [...]
  formula: {...}
  supported_dimensions: [...]
  owner: "增长分析组"
  authority_source: "指标平台"
  status: "confirmed"
```

### 5.5 琐碎数据

| 处理方法 | 得到的结果 | 存哪里 | 适用场景 | 风险 |
| --- | --- | --- | --- | --- |
| Inbox 捕获 | 原始碎片、来源、时间 | 原文库/inbox | 不丢线索 | 噪声很大。 |
| EvidenceNote | 低权威证据卡片 | 结构化库 | 后续筛选 | 污染正式知识。 |
| 低权重 chunk | 可召回文本片段 | 向量库低权重分区 | 补充线索 | 模型误信。 |
| 审核升级 | 转成 Hypothesis / Issue / BusinessEvent | 结构化库 + 图谱 | 有价值经验沉淀 | 需要人工。 |

建议第一版结果样子：

```yaml
evidence_note:
  content: "有人反馈渠道A最近流量质量变差"
  claim_type: "hypothesis_candidate"
  authority_level: "informal"
  triage_status: "needs_review"
```

## 6. 方案选项

### 选项 1：轻量 RAG 方案

| 项目 | 内容 |
| --- | --- |
| 做什么 | SourceCard + contextual chunk + hybrid search。 |
| 产出 | 可检索、可引用的文档证据库。 |
| 优点 | 快，适合下周先演示资料问答。 |
| 缺点 | 无法稳定做问数、归因、建议复盘。 |
| 适合 | 第一阶段快速验证资料检索价值。 |
| 不适合 | 作为完整经营分析知识库。 |

### 选项 2：结构化对象优先方案

| 项目 | 内容 |
| --- | --- |
| 做什么 | 从周报、会议、SQL、文档抽取标准对象。 |
| 产出 | `MetricDefinition`、`MetricMovement`、`Hypothesis`、`SQLTemplate` 等。 |
| 优点 | 真正把资料变成知识，可审核可复用。 |
| 缺点 | schema 和审核机制需要投入。 |
| 适合 | 你们当前最核心的“处理成什么样子”问题。 |
| 不适合 | 只想快速做搜索框。 |

### 选项 3：结构化对象 + 轻量图谱方案

| 项目 | 内容 |
| --- | --- |
| 做什么 | 在结构化对象基础上建立关键关系边。 |
| 产出 | 经营分析图谱：指标、事件、假设、证据、建议、SQL、表。 |
| 优点 | 能支持“为什么”“相关证据是什么”“历史类似案例”。 |
| 缺点 | 实体对齐、关系质量、图谱维护有成本。 |
| 适合 | 目标状态，但第一期应缩小范围。 |
| 不适合 | 没有结构化对象基础时直接开做。 |

### 选项 4：完整 GraphRAG 方案

| 项目 | 内容 |
| --- | --- |
| 做什么 | 全量文本自动构图、社区摘要、GraphRAG 查询。 |
| 产出 | 实体关系图、claims、community reports。 |
| 优点 | 适合跨大量资料做全局主题发现。 |
| 缺点 | 不稳定、成本高、业务 schema 弱、对 SQL/指标帮助有限。 |
| 适合 | 第二阶段以后做探索。 |
| 不适合 | 第一版核心建设。 |

### 选项 5：语义层 + Verified SQL 优先方案

| 项目 | 内容 |
| --- | --- |
| 做什么 | 核心指标、可信表、SQL 模板、verified query。 |
| 产出 | 高频问数能力。 |
| 优点 | 对“查数准”最直接。 |
| 缺点 | 不解决会议、周报、归因和建议沉淀。 |
| 适合 | 如果第一期最痛的是取数和口径。 |
| 不适合 | 如果第一期重点是历史经营分析知识复用。 |

## 7. 我的阶段性建议

不是最终方案，但作为讨论起点，我建议：

```text
第一期采用：选项 2 为主，结合选项 1 和选项 5，再小范围试点选项 3。
```

也就是：

1. 所有资料先做 `SourceCard + EvidenceChunk`，建立证据层。
2. 周报优先抽 `MetricMovement / Hypothesis / ActionRecommendation / BusinessEvent`。
3. SQL 优先抽 `SQLTemplate / VerifiedQuery / DatasetUsage`。
4. 数据文档优先抽 `BusinessTerm / MetricDefinition / DatasetAsset / ColumnAsset`。
5. 会议纪要只抽 `DecisionRecord / ActionItem / Hypothesis / BusinessEvent`，并全部标状态。
6. 图谱先只连 5 类关系：指标-表、SQL-表、指标波动-假设、假设-证据、建议-验证指标。

第一期不要做：

| 暂缓项 | 原因 |
| --- | --- |
| 全量 GraphRAG | 成本高、噪声大，不解决问数。 |
| 全公司知识图谱 | 范围太大，维护不可控。 |
| 全自动归因 | 经营因果必须保守，先用 hypothesis。 |
| 所有碎片资料升级为正式知识 | 会污染知识库。 |

## 8. 下一步讨论建议

为了把调研变成最终方案，建议下一步不再空谈技术，而是拿样本做一次“处理试验”：

| 样本 | 数量 | 目标 |
| --- | --- | --- |
| 周报 | 1-2 篇 | 看 `MetricMovement / Hypothesis / Recommendation` 是否能抽准。 |
| 会议纪要 | 1 篇 | 看能否区分决策、行动项、假设、待确认项。 |
| SQL | 3-5 条 | 看能否抽成可复用 SQLTemplate。 |
| 数据文档 | 1 份 | 看能否抽 BusinessTerm、MetricDefinition、DatasetAsset。 |
| 碎片资料 | 5-10 条 | 看 triage 规则是否够用。 |

试验后我们再一起判断：

1. 哪些结构字段有用？
2. 哪些字段太重，可以删？
3. 哪些对象必须人工确认？
4. 哪些对象可以自动入库？
5. 图谱第一版到底连哪些边？
6. 第一阶段的验收标准是什么？

## 9. 调研报告应有的标准结构

以后这类调研报告建议固定包含：

| 模块 | 作用 |
| --- | --- |
| 背景和问题定义 | 说明为什么调研、要解决什么问题。 |
| 调研范围和资料来源 | 说明看了哪些标杆、为什么选它们。 |
| 评估维度 | 说明怎么比较，不只罗列资料。 |
| 标杆案例拆解 | 每个案例讲做法、产物、适用场景和限制。 |
| 方法卡片 | 每种方法讲输入、处理、结果、存储、优缺点。 |
| 业务映射 | 映射到你们的会议、周报、SQL、数据文档、碎片资料。 |
| 方案选项 | 给出 3-5 个可选路线，不直接拍板。 |
| 阶段性建议 | 说明当前更偏向哪条路线，为什么。 |
| 风险和约束 | 说明成本、维护、准确性、审核、权限风险。 |
| 待讨论问题 | 留给后续共同敲定。 |

这份报告按这个结构重写，后续可以继续作为最终方案讨论的底稿。
