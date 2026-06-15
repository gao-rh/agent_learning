---
type: project-log
status: draft
tags: [business-analysis, knowledge-base, knowledge-graph, structured-extraction, graphrag, semantic-layer, rag]
created: 2026-06-14
updated: 2026-06-14
source:
  - 30-projects/经营分析AI知识库建设方案.md
  - 30-projects/经营分析AI知识库行业对标调研.md
  - https://microsoft.github.io/graphrag/
  - https://www.microsoft.com/en-us/research/project/graphrag/
  - https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_kg_builder.html
  - https://developers.llamaindex.ai/python/examples/query_engine/knowledge_graph_rag_query_engine/
  - https://docs.datahub.com/docs/glossary/business-glossary
  - https://docs.open-metadata.org/v1.12.x/how-to-guides/data-governance/glossary
  - https://docs.getdbt.com/docs/build/semantic-models
  - https://docs.getdbt.com/docs/build/about-metricflow
  - https://docs.unstructured.io/open-source/core-functionality/chunking
  - https://www.anthropic.com/engineering/contextual-retrieval
  - https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/verified-query-repository
  - https://docs.databricks.com/aws/en/genie/set-up
  - https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-prepare-data-ai
related:
  - 30-projects/经营分析AI知识库建设方案.md
  - 30-projects/经营分析AI知识库行业对标调研.md
---

# 经营分析 AI 知识库数据处理与知识建模调研

## 这次要回答的核心问题

你现在真正要解决的不是“要不要上 RAG”或者“要不要接 Agent”，而是：

```text
会议纪要、周报、数据代码、数据文档、碎片资料
到底要怎么清洗？
处理成什么结构？
哪些东西进向量库？
哪些东西进结构化库？
哪些东西进知识图谱？
最后怎么喂给大模型？
```

本调研的结论是：

> 你们应该做结构化表达，也应该做知识图谱，但不是一上来做“大而全的企业知识图谱”。更合理的是做一个 **经营分析领域的轻量知识图谱 + 结构化知识对象 + 证据 chunk + 语义查询资产** 的组合。

换句话说：

```text
原文不是知识库，只是证据源。
chunk 不是知识库，只是检索单元。
结构化对象才是可复用知识。
知识图谱负责把对象之间的关系连起来。
大模型最终拿到的是：结构化事实 + 关系路径 + 原文证据 + 查询结果 + 不确定性。
```

## 行业资料给出的关键启发

| 资料/产品 | 对数据处理的启发 |
| --- | --- |
| Microsoft GraphRAG | 从原始文本中抽取知识图谱，做层级社区摘要，再用于全局性问题和跨文档理解。它强调普通向量 RAG 对“整批资料有什么主题/关系”这类问题不够。 |
| Neo4j GraphRAG / KG Builder | 非结构化文本可以抽取为节点和关系，但 Neo4j 也明确这类自动构图仍偏实验，需要 schema、校验和人工治理。 |
| LlamaIndex KnowledgeGraph / PropertyGraph | GraphRAG 有两种路线：从文档构图，或利用已有知识图谱；也支持 schema-guided extraction，即先定义允许的实体和关系再抽取。 |
| DataHub / OpenMetadata | 企业数据知识不是文档堆，而是 glossary、terms、datasets、columns、owner、lineage、quality、usage 等元数据关系。 |
| dbt Semantic Layer / MetricFlow | 指标要被处理成 semantic model：entities、dimensions、measures、metrics，之后才能稳定生成查询。 |
| Anthropic Contextual Retrieval | chunk 要补文档上下文，结合 embedding + BM25 + rerank，不能裸切文本。 |
| Snowflake Cortex Analyst VQR | 高质量问数系统需要 verified questions + verified SQL，把人工确认过的问题和 SQL 作为可复用资产。 |
| Databricks Genie Space | 业务空间需要 trusted assets、example SQL、instructions、可信数据集，不是把整个数仓开放给聊天框。 |
| Power BI Prep data for AI | 为 AI 准备数据需要 AI schema、verified answers、AI instructions，核心是减少歧义并让回答 grounded。 |

这些资料共同指向一个结论：

> “AI 可用知识库”的建设重点不是存储，而是把原始资料加工成可治理、可检索、可组合、可验证的知识表示。

## 本文档定位：调研报告，不是最终执行方案

这份文档应该作为方案讨论的第一步，而不是直接定稿。

建议后续讨论按三步走：

| 阶段 | 产出 | 作用 |
| --- | --- | --- |
| 1. 调研报告 | 行业方法、关键概念、可处理成哪些知识表示 | 先建立共同认知，避免一上来争论工具。 |
| 2. 方案选型 | 对比若干候选路线：轻量 RAG、结构化对象、知识图谱、语义层、Verified SQL | 明确每条路线的成本、收益和风险。 |
| 3. 执行方案 | 选定第一期范围、对象 schema、存储位置、抽取流程、审核机制 | 形成真正可落地的实施计划。 |

所以本文档里出现的“建议”都应理解为候选判断，最终还需要结合你们现有平台能力、人员投入、业务优先级一起敲定。

## 从调研报告推导出的候选路线

### 路线 A：文档 RAG 优先

```text
原文 -> SourceCard -> EvidenceChunk -> 向量库/全文索引 -> LLM 引用回答
```

| 项目 | 说明 |
| --- | --- |
| 适合 | 快速做报告/会议/文档问答。 |
| 处理成什么 | 带 metadata 的文档卡片和证据 chunk。 |
| 存哪里 | 原文库、向量知识库、全文索引、metadata 表。 |
| 优点 | 快、成本低、能马上检索历史资料。 |
| 缺点 | 很难稳定回答口径、取数、归因链路、历史复盘。 |
| 对你们是否够用 | 不够，只能作为底层证据检索能力。 |

### 路线 B：结构化对象优先

```text
原文 -> SourceCard -> EvidenceChunk -> KnowledgeObject -> 结构化库 + 向量库
```

| 项目 | 说明 |
| --- | --- |
| 适合 | 从会议纪要、周报、SQL、文档中抽取可复用知识。 |
| 处理成什么 | `MetricDefinition`、`SQLTemplate`、`MetricMovement`、`Hypothesis`、`ActionRecommendation` 等对象。 |
| 存哪里 | 结构化数据库为主，向量库保存原文证据 chunk。 |
| 优点 | 可治理、可审核、可复用，能区分事实/假设/建议。 |
| 缺点 | 前期 schema 设计和抽取校验成本高。 |
| 对你们是否够用 | 可以作为第一期主路线。 |

### 路线 C：轻量知识图谱 + 结构化对象

```text
原文
-> EvidenceChunk
-> KnowledgeObject
-> Node/Edge
-> 图谱检索 + 向量检索 + 结构化查询
```

| 项目 | 说明 |
| --- | --- |
| 适合 | 需要回答“指标、表、事件、假设、建议之间有什么关系”。 |
| 处理成什么 | 结构化对象 + 关系边，例如 `Metric MEASURED_BY SQLTemplate`、`Hypothesis SUPPORTED_BY EvidenceChunk`。 |
| 存哪里 | 结构化库 + 图数据库或 nodes/edges 关系表 + 向量库。 |
| 优点 | 支持归因链路、血缘、历史类似案例、建议复盘。 |
| 缺点 | 图谱 schema 和实体对齐要求高，不能全自动放飞。 |
| 对你们是否够用 | 更适合目标状态；第一期可以做轻量版本。 |

### 路线 D：完整 GraphRAG

```text
原文 -> 自动抽取实体/关系/claims -> 社区发现 -> 社区摘要 -> local/global graph search
```

| 项目 | 说明 |
| --- | --- |
| 适合 | 大量叙事文本、跨文档主题总结、全局性问题。 |
| 处理成什么 | 自动抽取的实体、关系、claims、社区报告。 |
| 存哪里 | 图存储 + 文档索引 + 社区摘要表。 |
| 优点 | 适合问“最近整体发生了什么”“有哪些主题和关系”。 |
| 缺点 | 自动抽图谱容易实体混乱、关系误判；业务口径和 SQL 查询仍需结构化治理。 |
| 对你们是否够用 | 不建议第一期作为主路线；可以借鉴其 graph + summary 思想。 |

### 路线 E：语义层 / Verified SQL 优先

```text
指标平台 + 数据目录 + SQL
-> MetricDefinition / DatasetAsset / SQLTemplate
-> verified question + verified SQL
-> 问数 Agent
```

| 项目 | 说明 |
| --- | --- |
| 适合 | 高频问数、SQL 查询、指标口径查询。 |
| 处理成什么 | 语义指标、可信表、样例问题、验证 SQL、查询模板。 |
| 存哪里 | 指标平台/语义层、SQLTemplate registry、结构化库。 |
| 优点 | 问数准确率提升最明显。 |
| 缺点 | 不能覆盖会议纪要、周报归因、历史建议复盘。 |
| 对你们是否够用 | 必须做，但它只是经营分析知识库的一部分。 |

阶段性判断：

| 目标 | 候选路线 |
| --- | --- |
| 只想快速搜索文档 | 路线 A。 |
| 想把原始资料变成可复用知识 | 路线 B。 |
| 想回答为什么、关联什么、历史上怎么处理 | 路线 C。 |
| 想做跨文档全局理解和主题总结 | 路线 D 的思想可借鉴。 |
| 想优先解决问数准确率 | 路线 E。 |

对你们当前目标，更合理的讨论起点是：

```text
第一期：B + E，辅以轻量 C
第二期：强化 C
第三期：再评估是否需要 D 式 GraphRAG
```

这不是最终拍板，而是基于调研资料形成的候选路线。

## 每类原始资料的处理候选

这一节专门回答：针对某类资料，用什么方法处理，处理成什么样子，存到哪里。

### 会议纪要

会议纪要的性质是“过程性讨论材料”。它最重要的风险是：会上有人提出的猜测，会被模型误当成事实。

| 要包含的关键信息 | 说明 |
| --- | --- |
| 会议基本信息 | 会议时间、主题、业务域、参会角色、资料来源。 |
| 讨论议题 | 本次会议讨论了哪些业务问题。 |
| 决策 | 最终确认了什么，谁确认，是否已生效。 |
| 行动项 | 谁负责、做什么、截止时间、当前状态。 |
| 归因假设 | 大家认为某指标变化的可能原因。 |
| 待确认项 | 还没定、还需要数据或业务确认的问题。 |
| 业务事件 | 会上提到的活动、策略、版本、渠道变化。 |
| 原文证据 | 支撑某个决策/假设/行动项的原文片段。 |

建议结构：

```yaml
meeting_card:
  source_id: "meeting_2026_06_14_growth_review"
  title: "增长业务周复盘会"
  meeting_time: "2026-06-14 10:00"
  business_domain: ["增长", "新客", "渠道"]
  topics:
    - "新客转化率下降原因"
    - "渠道A投放策略调整"
  decisions:
    - decision_id: "dec_reduce_channel_a_low_quality_traffic"
      content: "暂停渠道A低质量人群包投放"
      status: "confirmed"
      owner: "增长运营"
  action_items:
    - action_item_id: "todo_check_channel_a_audience_change"
      assignee: "渠道运营"
      due_date: "2026-06-17"
      status: "open"
  hypotheses:
    - hypothesis_id: "hyp_channel_a_quality_drop"
      statement: "新客转化率下降可能来自渠道A流量质量下降"
      status: "pending_verification"
  evidence_chunk_ids:
    - "chunk_meeting_2026_06_14_004"
```

存储位置：

| 结构 | 存储位置 | 用途 |
| --- | --- | --- |
| 原始会议纪要 | 原文库 / 文档库 | 回溯原文。 |
| `MeetingCard`、`DecisionRecord`、`ActionItem`、`Hypothesis` | 结构化库 | 查询、审核、状态追踪。 |
| 会议原文片段 | 向量库 + 全文索引 | 作为回答证据。 |
| 会议-指标-假设-决策关系 | 知识图谱或 nodes/edges 表 | 用于归因链路和历史复盘。 |
| 待确认项 | 审核队列 / 任务表 | 防止未确认内容污染正式知识。 |

### 周报 / 专题报告

周报和专题报告是经营分析知识的主矿。它们应该被处理成“指标发生了什么、为什么、证据是什么、建议是什么、后续怎么验证”。

| 要包含的关键信息 | 说明 |
| --- | --- |
| 报告基本信息 | 标题、周期、业务域、作者、报告类型。 |
| 核心结论 | 本期最重要的经营判断。 |
| 指标波动 | 哪个指标、什么时间、涨跌多少、对比方式。 |
| 分维拆解 | 哪些渠道/区域/人群/商品贡献了变化。 |
| 业务事件 | 同期活动、策略、版本、外部因素。 |
| 归因假设 | 报告给出的原因判断。 |
| 数据证据 | 数值、图表、SQL、看板来源。 |
| 行动建议 | 做什么、为什么、预期影响、风险。 |
| 后续验证 | 下期要观察什么指标，建议是否有效。 |

建议结构：

```yaml
report_card:
  source_id: "weekly_2026_w24_growth"
  report_type: "weekly_report"
  title: "增长业务第24周周报"
  time_range:
    start: "2026-06-08"
    end: "2026-06-14"
  business_domain: ["增长", "新客"]
  key_conclusions:
    - "新客转化率环比下降，主要由渠道A贡献。"
  metric_movements:
    - movement_id: "move_new_user_cvr_2026w24"
      metric: "新客转化率"
      direction: "down"
      relative_change: "-8.4%"
      top_contributors:
        - dimension: "渠道"
          value: "渠道A"
          contribution: "62%"
  hypotheses:
    - statement: "渠道A流量质量下降导致整体转化下降"
      confidence: "medium"
      status: "partially_verified"
  recommendations:
    - "收缩渠道A低质量人群包投放，并观察次周留存。"
```

存储位置：

| 结构 | 存储位置 | 用途 |
| --- | --- | --- |
| 原始周报/专题报告 | 原文库 | 溯源。 |
| `ReportCard`、`MetricMovement`、`BusinessEvent`、`Hypothesis`、`ActionRecommendation` | 结构化库 | 经营分析对象查询。 |
| 结论段、图表解释、建议段 | 向量库 + 全文索引 | 文档证据召回。 |
| 指标波动-事件-假设-建议关系 | 知识图谱 | 回答“为什么”和“历史上怎么处理”。 |
| 关键数值/指标快照 | 结构化库或指标快照表 | 复盘历史口径下的观察事实。 |

### 数据代码 / SQL

SQL 和数据代码不是普通文档，它们的核心价值是暴露真实取数路径和指标计算逻辑。

| 要包含的关键信息 | 说明 |
| --- | --- |
| 查询意图 | 这段 SQL 是为了回答什么业务问题。 |
| 输入表/字段 | `from`、`join`、字段引用。 |
| 指标计算逻辑 | `sum`、`count distinct`、`case when`、过滤条件。 |
| 维度和粒度 | 按天/周、渠道、城市、用户类型等。 |
| 参数 | 日期、业务线、渠道、版本等。 |
| 输出字段 | 查询结果返回什么。 |
| 安全规则 | 必须分区、只读、limit、禁止扫全表。 |
| 验证状态 | 是否人工确认、是否能执行、是否结果可信。 |

建议结构：

```yaml
sql_template:
  sql_template_id: "sql_new_user_cvr_by_channel"
  source_id: "git_sql_growth_dashboard_001"
  question_patterns:
    - "新客转化率按渠道怎么看"
    - "上周新客转化率渠道拆解"
  intent: "metric_breakdown"
  metrics: ["新客转化率"]
  dimensions: ["渠道"]
  input_assets:
    - dataset: "ads_growth_channel_daily"
      columns: ["dt", "channel", "new_user_converted_cnt", "new_user_visit_cnt"]
  parameters:
    - name: "start_date"
      type: "date"
    - name: "end_date"
      type: "date"
  output_schema:
    - name: "channel"
      type: "string"
    - name: "new_user_cvr"
      type: "decimal"
  safety_rules:
    - "must_include_dt_filter"
    - "readonly_only"
  verification:
    status: "confirmed"
    verified_by: "增长分析师"
```

存储位置：

| 结构 | 存储位置 | 用途 |
| --- | --- | --- |
| 原始 SQL / 代码 | Git / 原文库 | 溯源和版本管理。 |
| `SQLTemplate`、`MetricCalculation`、`DatasetUsage` | 结构化库 / SQL 模板库 | 问数、复用、校验。 |
| 表字段依赖、血缘边 | 知识图谱或血缘系统 | 找表、影响分析、查询校验。 |
| SQL 注释、说明文档 | 向量库 + 全文索引 | 语义检索和解释。 |
| verified question + verified SQL | Verified Query Repository | 提升高频问题稳定性。 |

### 数据文档

数据文档的价值是权威定义。它不应该只做 RAG，而应该变成语义资产。

| 要包含的关键信息 | 说明 |
| --- | --- |
| 业务术语 | 名称、别名、定义、反例、适用范围。 |
| 指标定义 | 公式、分子、分母、过滤条件、粒度、owner。 |
| 表说明 | 表名、业务名、用途、刷新频率、推荐状态。 |
| 字段说明 | 字段名、类型、枚举、含义、敏感等级。 |
| 口径版本 | valid_from、valid_to、变更原因、影响范围。 |
| 维护责任 | owner、审核人、更新时间。 |

建议结构：

```yaml
metric_definition:
  metric_id: "metric_new_user_cvr"
  name: "新客转化率"
  aliases: ["新用户转化率", "新客CVR"]
  formula:
    numerator: "完成关键行为的新客数"
    denominator: "访问新客数"
  filters:
    - "user_type = 'new'"
  grain: ["day", "week"]
  supported_dimensions: ["渠道", "城市", "端"]
  owner: "增长分析组"
  authority_source: "指标平台"
  valid_from: "2026-01-01"
  valid_to: null
  status: "confirmed"
```

存储位置：

| 结构 | 存储位置 | 用途 |
| --- | --- | --- |
| 原始数据文档 | 原文库 | 溯源。 |
| `BusinessTerm`、`MetricDefinition`、`DatasetAsset`、`ColumnAsset` | 指标平台/数据目录/结构化库 | 权威语义层。 |
| 术语-指标-表字段关系 | 知识图谱 | 消歧、口径解释、表字段关联。 |
| 文档段落 chunk | 向量库 + 全文索引 | 引用原文解释。 |
| 口径变更记录 | 结构化库 | 处理历史报告和版本差异。 |

### 各种琐碎数据

碎片资料的最大问题是来源、时间、可信度不稳定。它们不应该直接进入权威知识层。

| 要包含的关键信息 | 说明 |
| --- | --- |
| 来源 | 来自群聊、个人笔记、临时文档、截图还是口头整理。 |
| 时间 | 什么时候产生，是否仍有效。 |
| 涉及对象 | 涉及哪些指标、表、字段、业务事件。 |
| 内容类型 | 事实、猜测、建议、问题、踩坑、待办。 |
| 可信度 | low / medium / high。 |
| 处理状态 | 未处理、待确认、已升级、已丢弃。 |

建议结构：

```yaml
evidence_note:
  note_id: "frag_2026_06_14_001"
  source_type: "chat_fragment"
  captured_at: "2026-06-14"
  content: "有人反馈渠道A最近流量质量变差，可能影响新客转化。"
  related_entities:
    metrics: ["新客转化率"]
    channels: ["渠道A"]
  claim_type: "hypothesis_candidate"
  authority_level: "informal"
  confidence: "low"
  triage_status: "needs_review"
```

存储位置：

| 结构 | 存储位置 | 用途 |
| --- | --- | --- |
| 原始碎片 | Inbox / 原文库 | 保留线索。 |
| `EvidenceNote` | 结构化库 | 待处理和筛选。 |
| 碎片文本 chunk | 向量库，但低权重 | 补充召回，不作为权威证据。 |
| 被确认后的对象 | 结构化库 + 图谱 | 只有通过审核才升级。 |
| 无法确认的碎片 | 保留或丢弃 | 避免污染正式知识库。 |

## 最终应该处理成哪几层

建议你们把原始资料处理成 6 层，而不是只做一个向量库。

```text
L0 原始资料层 Raw Source
L1 文档画像层 Source Card
L2 证据片段层 Evidence Chunk
L3 结构化知识对象层 Knowledge Object
L4 关系图谱层 Domain Knowledge Graph
L5 大模型上下文包层 LLM Context Pack
```

### L0：原始资料层

目标：保留原文、原始文件、原始 SQL、原始会议纪要，保证可追溯。

不要在这一层做过度总结。所有后续抽取都要能回到原文。

| 字段 | 说明 |
| --- | --- |
| `source_id` | 全局唯一 ID。 |
| `source_type` | meeting / weekly_report / analysis_report / sql / code / data_doc / chat_fragment。 |
| `raw_uri` | 原文链接、文件路径、代码仓库链接。 |
| `raw_hash` | 原文 hash，用于判断是否变更。 |
| `created_at` | 原资料创建时间。 |
| `ingested_at` | 入库时间。 |
| `owner` | 资料负责人或来源团队。 |
| `access_scope` | 权限范围。 |

### L1：文档画像层 Source Card

目标：先给每份资料建“身份证”，让系统知道这份资料是什么、讲什么、可信度如何。

每份会议纪要、周报、文档、SQL 文件都应该生成一张 `SourceCard`。

```yaml
source_card:
  source_id: "weekly_2026_06_01_growth"
  source_type: "weekly_report"
  title: "增长业务 2026-06-01 周报"
  time_range:
    start: "2026-05-25"
    end: "2026-05-31"
  business_domain: ["增长", "新客", "渠道"]
  mentioned_metrics: ["新客转化率", "渠道ROI", "新客留存"]
  mentioned_assets: ["ads_growth_channel_daily"]
  authority_level: "weekly_business_review"
  status: "active"
  summary: "本周新客转化率下降，主要讨论渠道A流量质量和投放策略变化。"
  extraction_status: "processed"
```

这一层解决两个问题：

1. 检索时先过滤资料范围，而不是全库乱搜。
2. 大模型看到 chunk 前，知道来源背景。

### L2：证据片段层 Evidence Chunk

目标：为 RAG 提供可引用证据，但 chunk 必须带上下文。

错误做法：

```text
按 500 字切分，直接 embedding。
```

推荐做法：

```text
按文档结构切分：标题、章节、表格、代码块、决策段、结论段。
给每个 chunk 加 context header。
同时建向量索引 + 全文索引 + metadata filter。
```

`EvidenceChunk` 示例：

```yaml
chunk:
  chunk_id: "chunk_weekly_2026_06_01_003"
  source_id: "weekly_2026_06_01_growth"
  chunk_type: "metric_analysis"
  title_path: ["经营周报", "新客增长", "渠道转化分析"]
  context_header: |
    来源：增长业务 2026-06-01 周报
    周期：2026-05-25 至 2026-05-31
    业务域：增长 / 新客 / 渠道
    相关指标：新客转化率、渠道ROI
    片段类型：指标波动解释
  text: "本周新客转化率下降 8.4%，主要受渠道A流量质量下降影响..."
  entities:
    metrics: ["新客转化率", "渠道ROI"]
    dimensions: ["渠道"]
    events: ["渠道A投放策略调整"]
  authority_level: "weekly_business_review"
  confidence: 0.78
```

这一层适合回答：

| 问题 | 依赖 |
| --- | --- |
| 周报里当时怎么说？ | EvidenceChunk。 |
| 有没有报告证据？ | EvidenceChunk + SourceCard。 |
| 哪段原文支持这个判断？ | EvidenceChunk 的 source 和 text。 |

但它不适合直接承担：

| 不适合 | 原因 |
| --- | --- |
| 指标口径权威定义 | chunk 可能来自旧报告，口径可能过期。 |
| SQL 生成 | chunk 缺少结构化表字段和查询规则。 |
| 归因事实判断 | chunk 只是证据，不等于事实。 |

### L3：结构化知识对象层

目标：把原文中的可复用知识抽成标准对象。

这是你们知识库最重要的一层。

建议第一版至少抽取 12 类对象：

| 对象 | 作用 | 主要来源 |
| --- | --- | --- |
| `BusinessTerm` | 业务术语和同义词 | 数据文档、指标平台、会议、周报。 |
| `MetricDefinition` | 指标定义、公式、适用范围 | 指标平台、数据文档、SQL。 |
| `DimensionDefinition` | 维度定义和枚举 | 数据文档、SQL、口径文档。 |
| `DatasetAsset` | 表资产、可信度、刷新频率 | 数据目录、代码、SQL。 |
| `ColumnAsset` | 字段含义、类型、质量 | 数据目录、代码、数据文档。 |
| `SQLTemplate` | 可复用查询模板 | SQL、数据代码、历史查询。 |
| `MetricMovement` | 指标波动事实 | 周报、报告、看板摘要。 |
| `BusinessEvent` | 活动、策略、版本、渠道变化 | 周报、会议纪要、运营记录。 |
| `Hypothesis` | 归因假设 | 周报、专题分析、会议讨论。 |
| `DecisionRecord` | 业务决策 | 会议纪要、复盘报告。 |
| `ActionRecommendation` | 行动建议 | 周报、复盘、会议 action。 |
| `AnalysisCase` | 历史分析案例 | 专题分析、复盘、周报。 |

其中，最关键的是把“事实”和“判断”分开。

| 类型 | 示例 | 处理方式 |
| --- | --- | --- |
| 稳定事实 | 指标定义、字段含义、表 owner | 可以进入权威结构化库，但需要 owner 和版本。 |
| 观察事实 | 某周指标下降 8.4% | 可以结构化，但必须带时间、口径、来源。 |
| 归因假设 | 下降可能来自渠道A流量质量 | 不能当事实，必须标注 status、confidence、证据和反证。 |
| 决策/建议 | 收缩某渠道投放 | 需要记录提出时间、适用条件、是否执行、后续效果。 |

### L4：关系图谱层

目标：把结构化知识对象之间的关系连起来，用于跨文档追踪、归因链路、影响分析和 GraphRAG。

建议做轻量领域知识图谱，而不是一开始做全公司知识图谱。

图谱里的节点不应该是“所有句子”，而应该是重要业务对象：

```text
Metric
Dimension
Dataset
Column
SQLTemplate
Report
Meeting
BusinessEvent
MetricMovement
Hypothesis
Decision
ActionRecommendation
AnalysisCase
Team / Owner
```

图谱里的关系示例：

| 关系 | 含义 |
| --- | --- |
| `DEFINES` | 文档定义了某个指标/术语。 |
| `MENTIONS` | 报告/会议提到了某个指标/事件。 |
| `MEASURED_BY` | 指标由某张表或 SQL 模板计算。 |
| `USES_DATASET` | SQL 模板使用某张表。 |
| `USES_COLUMN` | SQL 模板使用某个字段。 |
| `HAS_DIMENSION` | 指标可按某维度拆解。 |
| `UPSTREAM_OF` | 表/字段血缘关系。 |
| `OBSERVED_IN` | 指标波动来自某份周报/报告。 |
| `OCCURRED_DURING` | 业务事件发生在某个时间段。 |
| `CANDIDATE_CAUSE_OF` | 某业务事件可能导致某指标波动。 |
| `SUPPORTED_BY` | 假设被某证据支持。 |
| `CONTRADICTED_BY` | 假设被某证据反驳。 |
| `RECOMMENDS` | 某分析案例/会议提出某行动建议。 |
| `VALIDATED_BY` | 建议或假设被后续数据验证。 |
| `OWNED_BY` | 指标/表/文档由某团队负责。 |

关系命名要特别谨慎。

不建议直接写：

```text
BusinessEvent CAUSES MetricMovement
```

因为业务归因往往不是确定因果。第一版更建议写：

```text
BusinessEvent CANDIDATE_CAUSE_OF MetricMovement
Hypothesis SUPPORTED_BY EvidenceChunk
Hypothesis CONTRADICTED_BY EvidenceChunk
```

这样可以保留业务判断的不确定性。

### L5：大模型上下文包层

目标：不是把知识库整体给大模型，而是按问题动态组装上下文包。

大模型最终应该拿到类似这样的 `ContextPack`：

```yaml
context_pack:
  question: "为什么上周新客转化率下降？"
  intent: "explain_metric_movement"
  confirmed_facts:
    - type: "MetricDefinition"
      name: "新客转化率"
      formula: "新客完成关键行为人数 / 新客访问人数"
      source: "指标平台"
    - type: "MetricMovement"
      metric: "新客转化率"
      time_range: "2026-05-25 至 2026-05-31"
      change: "-8.4%"
      source_sql: "..."
  graph_context:
    - path: "新客转化率 -> HAS_DIMENSION -> 渠道"
    - path: "渠道A投放策略调整 -> CANDIDATE_CAUSE_OF -> 新客转化率下降"
    - path: "假设H1 -> SUPPORTED_BY -> 周报片段C3"
  evidence_chunks:
    - chunk_id: "chunk_weekly_2026_06_01_003"
      text: "本周新客转化率下降 8.4%，主要受渠道A流量质量下降影响..."
      source: "增长业务 2026-06-01 周报"
  query_results:
    - sql_id: "query_123"
      result_summary: "渠道A贡献了 62% 的下降。"
      sql: "..."
  uncertainty:
    - "渠道A投放人群包是否变化尚未确认。"
  answer_constraints:
    - "区分事实、假设和建议。"
    - "所有结论必须引用证据。"
    - "不确定时说明待验证项。"
```

## 要不要做知识图谱

### 结论

要做，但要分阶段做。

第一版不要做“全量、完美、本体化”的知识图谱，而要做：

```text
经营分析任务导向的轻量属性图谱
```

也就是：

1. 节点只收关键业务对象。
2. 关系只收经营分析会用到的关系。
3. 每条关系都带来源、时间、置信度、状态。
4. 图谱服务于检索、归因、溯源和上下文组装，而不是为了画一张复杂大图。

### 为什么需要知识图谱

普通向量 RAG 擅长找相似片段，但不擅长稳定回答这些问题：

| 问题 | 为什么图谱有价值 |
| --- | --- |
| 这个指标和哪些维度/表/SQL 有关？ | 这是实体关系查询，不是相似度查询。 |
| 这次下降和哪些业务事件可能有关？ | 需要时间关系和事件-指标关系。 |
| 历史上类似下降发生过几次？原因分别是什么？ | 需要跨报告连接 `MetricMovement`、`Hypothesis`、`AnalysisCase`。 |
| 这个表是否可信？上游来自哪里？影响哪些指标？ | 需要数据血缘和资产关系。 |
| 某个建议后来有没有验证有效？ | 需要连接建议、执行记录、后续指标变化。 |
| 这个结论是事实、假设还是会议讨论？ | 需要关系和状态建模。 |

Microsoft GraphRAG 的核心启发也是这个：当问题不是找一段相似文本，而是要理解整个私有语料中的主题、实体和关系时，图结构会比纯文本片段更有效。

### 什么时候不需要知识图谱

不是所有东西都应该进图谱。

| 不建议进图谱 | 原因 |
| --- | --- |
| 每一句会议原话 | 噪声太高，边太多，维护成本爆炸。 |
| 所有聊天碎片 | 大量低可信内容会污染图谱。 |
| 未确认的个人判断 | 可以做 evidence 或 hypothesis，但不能直接当事实边。 |
| 一次性临时数据 | 如果没有复用价值，不必结构化。 |
| 大段文本内容 | 文本留在 chunk 和原文层，图谱只存对象和关系。 |

### 知识图谱第一版范围

建议第一版只做 5 类子图：

| 子图 | 节点 | 关系 | 价值 |
| --- | --- | --- | --- |
| 指标语义图 | Metric、Dimension、BusinessTerm | HAS_DIMENSION、ALIAS_OF、DERIVED_FROM | 查口径、消歧、指标拆解。 |
| 数据资产图 | Dataset、Column、SQLTemplate、Metric | MEASURED_BY、USES_DATASET、USES_COLUMN、UPSTREAM_OF | 找表、找字段、SQL 生成和校验。 |
| 经营事件图 | BusinessEvent、MetricMovement、Report | OCCURRED_DURING、OBSERVED_IN、MENTIONS | 指标变化和业务事件关联。 |
| 归因假设图 | Hypothesis、EvidenceChunk、MetricMovement | CANDIDATE_CAUSE_OF、SUPPORTED_BY、CONTRADICTED_BY | 回答“为什么”。 |
| 行动复盘图 | ActionRecommendation、Decision、AnalysisCase、MetricMovement | RECOMMENDS、VALIDATED_BY、FOLLOWED_BY | 回答“怎么办”和“历史上怎么做”。 |

## 要不要做结构化表达

### 结论

必须做。结构化表达比知识图谱更基础。

知识图谱是“关系层”，但图谱里的节点从哪里来？来自结构化抽取。

如果不先做结构化对象，直接让 LLM 从原文生成图谱，会出现：

| 问题 | 后果 |
| --- | --- |
| 实体不统一 | `GMV`、`成交额`、`支付金额` 被混淆。 |
| 关系过度断言 | “可能导致”被写成“导致”。 |
| 没有状态 | 会议猜测被当成已确认事实。 |
| 没有版本 | 旧口径污染新口径。 |
| 没有来源 | 结论无法追溯。 |
| 没有 owner | 后续无法维护。 |

所以顺序应该是：

```text
原文 -> 结构化对象 -> 关系图谱 -> 检索/上下文包
```

而不是：

```text
原文 -> 直接自动生成大图谱
```

### 结构化表达应该长什么样

建议所有抽取结果都用 JSON/YAML schema 管理，并带统一元数据。

统一元数据：

```yaml
metadata:
  object_id: "..."
  object_type: "MetricMovement"
  source_ids: ["weekly_2026_06_01_growth"]
  evidence_chunk_ids: ["chunk_weekly_2026_06_01_003"]
  business_domain: ["增长", "新客"]
  authority_level: "weekly_business_review"
  status: "draft | pending_review | confirmed | deprecated | contradicted"
  confidence: "low | medium | high"
  valid_from: "2026-05-25"
  valid_to: null
  owner: "增长分析组"
  created_at: "2026-06-14"
  updated_at: "2026-06-14"
```

#### MetricDefinition

```yaml
metric_definition:
  metric_id: "metric_new_user_conversion_rate"
  name: "新客转化率"
  aliases: ["新用户转化率", "新客CVR"]
  description: "新客在指定周期内完成关键行为的比例。"
  formula:
    numerator: "完成关键行为的新客数"
    denominator: "访问新客数"
    expression: "new_user_converted_cnt / new_user_visit_cnt"
  grain: ["day", "week"]
  dimensions: ["渠道", "城市", "端", "人群包"]
  filters:
    - "user_type = 'new'"
  owner: "增长分析组"
  authority_source: "指标平台"
  status: "confirmed"
```

#### DatasetAsset

```yaml
dataset_asset:
  dataset_id: "ads_growth_channel_daily"
  name: "ads_growth_channel_daily"
  business_name: "增长渠道日汇总表"
  description: "按日、渠道聚合的新客增长核心指标表。"
  owner: "增长数据组"
  refresh_frequency: "daily"
  partition_keys: ["dt"]
  trust_level: "recommended"
  warning: "T+1 更新，上午 10 点前数据可能不完整。"
  upstream_assets: ["dwd_user_behavior_di", "dim_channel"]
  downstream_metrics: ["新客转化率", "渠道ROI"]
```

#### SQLTemplate

```yaml
sql_template:
  sql_template_id: "sql_new_user_cvr_by_channel_wow"
  question_patterns:
    - "上周新客转化率按渠道变化"
    - "新客转化率渠道分解"
  intent: "metric_breakdown"
  metrics: ["metric_new_user_conversion_rate"]
  dimensions: ["渠道"]
  parameters:
    - name: "start_date"
      type: "date"
      required: true
    - name: "end_date"
      type: "date"
      required: true
  sql: |
    SELECT
      channel,
      SUM(new_user_converted_cnt) / NULLIF(SUM(new_user_visit_cnt), 0) AS new_user_cvr
    FROM ads_growth_channel_daily
    WHERE dt BETWEEN {{start_date}} AND {{end_date}}
    GROUP BY channel
  safety_rules:
    - "must_include_partition_filter"
    - "readonly_only"
  verified_by: "增长分析组"
  status: "confirmed"
```

#### MetricMovement

```yaml
metric_movement:
  movement_id: "move_new_user_cvr_2026w22"
  metric_id: "metric_new_user_conversion_rate"
  time_range:
    start: "2026-05-25"
    end: "2026-05-31"
  comparison:
    type: "wow"
    previous_start: "2026-05-18"
    previous_end: "2026-05-24"
  direction: "down"
  absolute_change: "-1.8pp"
  relative_change: "-8.4%"
  top_dimensions:
    - dimension: "渠道"
      value: "渠道A"
      contribution: "62%"
  source_ids: ["weekly_2026_06_01_growth"]
  status: "confirmed"
```

#### Hypothesis

```yaml
hypothesis:
  hypothesis_id: "hyp_channel_a_quality_drop_2026w22"
  statement: "新客转化率下降可能主要来自渠道A流量质量下降。"
  target_movement_id: "move_new_user_cvr_2026w22"
  candidate_causes:
    - "event_channel_a_targeting_change_2026_06_03"
  supporting_evidence:
    - evidence_id: "chunk_weekly_2026_06_01_003"
      claim: "周报提到渠道A贡献了主要降幅。"
    - evidence_id: "query_123"
      claim: "分渠道拆解显示渠道A贡献 62% 降幅。"
  counter_evidence:
    - evidence_id: "query_124"
      claim: "其他渠道变化不明显。"
  status: "partially_verified"
  confidence: "medium"
  open_questions:
    - "渠道A投放人群包是否发生变化？"
```

#### ActionRecommendation

```yaml
action_recommendation:
  action_id: "action_reduce_low_quality_channel_a_2026w22"
  recommendation: "收缩渠道A低质量人群包投放，并观察新客转化率和次周留存。"
  based_on_hypothesis: "hyp_channel_a_quality_drop_2026w22"
  expected_impact: "提升新客转化率，可能短期降低拉新规模。"
  risks:
    - "短期新客量下降"
    - "渠道ROI 波动"
  validation_metrics:
    - "新客转化率"
    - "渠道ROI"
    - "新客次周留存"
  status: "proposed"
```

## 处理规则补充：抽取注意事项

### 会议纪要的抽取注意事项

会议纪要是“过程性资料”，不能直接当事实。

处理目标：

```text
从一堆讨论中抽出：议题、决策、待确认项、行动项、归因假设、业务事件。
```

处理成：

| 对象 | 字段 |
| --- | --- |
| `MeetingCard` | 会议主题、时间、参会方、业务域、核心议题、结论摘要。 |
| `DecisionRecord` | 决策内容、背景、证据、负责人、状态。 |
| `ActionItem` | 谁、做什么、截止时间、当前状态。 |
| `Hypothesis` | 会上提出的原因猜测、支持证据、待验证问题。 |
| `BusinessEvent` | 提到的活动、策略、版本、渠道变化。 |

关键规则：

| 规则 | 原因 |
| --- | --- |
| 会议里的“有人认为”默认是 hypothesis，不是 fact。 | 避免模型把猜测当结论。 |
| 会议里的“决定”也要有状态。 | 决定可能后续被取消或未执行。 |
| 行动项必须有 owner 和 due date。 | 否则后续无法追踪是否验证。 |
| 会议纪要 chunk 要保留说话上下文。 | 避免断章取义。 |

### 周报的抽取注意事项

周报是经营分析知识的核心来源。

处理目标：

```text
把周报处理成一组指标波动、原因解释、证据、建议和待跟踪项。
```

处理成：

| 对象 | 字段 |
| --- | --- |
| `ReportCard` | 周期、业务域、核心结论、涉及指标、重要事件。 |
| `MetricMovement` | 指标、时间、涨跌幅、分维贡献、数据来源。 |
| `Hypothesis` | 归因假设、支持证据、反证、置信度。 |
| `BusinessEvent` | 同期活动、策略、渠道、版本变化。 |
| `ActionRecommendation` | 建议、适用条件、风险、验证指标。 |
| `FollowUpSignal` | 后续是否验证、下周要观察什么。 |

周报抽取时要特别注意：

| 注意点 | 说明 |
| --- | --- |
| 时间范围必须明确 | 周报标题日期不一定等于数据周期。 |
| 指标口径要回连指标平台 | 周报里写的指标名可能是简称。 |
| 结论和证据分开 | “下降来自渠道A”是结论，“渠道A贡献62%”是证据。 |
| 建议和效果分开 | 建议不等于已验证有效。 |

### 数据代码 / SQL 的抽取注意事项

SQL 和代码是“真实取数路径”的重要来源，但不适合直接给大模型全文阅读。

处理目标：

```text
把代码和 SQL 解析成数据资产依赖、指标计算逻辑、查询模板和安全规则。
```

处理成：

| 对象 | 字段 |
| --- | --- |
| `SQLTemplate` | 查询意图、参数、SQL、依赖表、输出字段、适用场景。 |
| `MetricCalculation` | 指标公式、聚合方式、过滤条件、维度粒度。 |
| `DatasetUsage` | 哪些 SQL/任务使用了哪些表字段。 |
| `LineageEdge` | 输入表、输出表、字段级映射。 |
| `DataQualityWarning` | 延迟、缺失、异常值、废弃字段。 |

SQL 处理建议：

| 步骤 | 内容 |
| --- | --- |
| SQL parser | 抽取 `from/join/select/where/group by/order by`。 |
| 表字段对齐 | 对齐数据目录里的表和字段。 |
| 指标识别 | 识别 `sum/count distinct/case when` 对应的指标逻辑。 |
| 参数化 | 把日期、业务线、渠道等变成模板参数。 |
| 安全校验 | 标注必须分区、只读、limit、禁止扫明细。 |
| 人工验证 | 高频 SQL 模板进入 verified query repository。 |

### 数据文档的抽取注意事项

数据文档通常是权威定义来源。

处理目标：

```text
抽取业务术语、指标定义、字段定义、表说明、口径限制和版本变化。
```

处理成：

| 对象 | 字段 |
| --- | --- |
| `BusinessTerm` | 术语、定义、同义词、反例、owner。 |
| `MetricDefinition` | 指标名、公式、粒度、过滤条件、适用范围。 |
| `DatasetAsset` | 表名、业务含义、owner、刷新频率、推荐状态。 |
| `ColumnAsset` | 字段名、类型、枚举、含义、敏感等级。 |
| `DefinitionChangeLog` | 口径变更时间、变更原因、影响范围。 |

关键规则：

| 规则 | 原因 |
| --- | --- |
| 文档抽取结果要和指标平台/数据目录对齐。 | 防止另造一套权威源。 |
| 旧口径不能删除，要标记 valid_to。 | 历史报告可能使用旧口径。 |
| 同义词要显式建模。 | 业务问题里经常使用简称和俗称。 |

### 各种琐碎数据的抽取注意事项

琐碎数据不要一开始就正式入库。

处理目标：

```text
先变成待处理证据，再决定是否升级为正式知识。
```

处理成：

| 去向 | 条件 |
| --- | --- |
| `EvidenceChunk` | 有来源、有时间、有参考价值，但未确认。 |
| `Hypothesis` | 明确表达了某种原因判断，但证据不足。 |
| `IssueAndPitfall` | 反复出现的踩坑、注意事项。 |
| `ActionRecommendation` | 明确可执行建议。 |
| 丢弃 | 无来源、无时间、不可复用。 |

建议为碎片资料加一个 triage 状态：

```yaml
triage_status: "unprocessed | useful_evidence | needs_review | promoted | discarded"
```

## 推荐的数据处理流水线

### Step 1：采集与登记

输入：会议纪要、周报、SQL、代码、文档、碎片资料。

输出：`RawSource`。

必须做：

| 动作 | 说明 |
| --- | --- |
| 保存原文 | 不要只保存抽取结果。 |
| 生成 source_id | 后续所有对象都引用 source_id。 |
| 记录 hash | 支持增量更新和变更检测。 |
| 记录权限和 owner | 后续用于过滤和治理。 |

### Step 2：解析与结构切分

输入：RawSource。

输出：文档结构树。

不同材料用不同 parser：

| 类型 | 解析重点 |
| --- | --- |
| 文档/周报 | 标题、章节、段落、表格、图片说明。 |
| 会议纪要 | 议题、发言、结论、行动项。 |
| SQL | 表、字段、条件、聚合、join、输出。 |
| 代码 | 输入输出表、任务依赖、调用链。 |

### Step 3：生成 SourceCard

输入：文档结构树。

输出：SourceCard。

用途：

| 用途 | 说明 |
| --- | --- |
| 检索过滤 | 按业务域、时间、类型、权威级别过滤。 |
| 抽取路由 | 周报走周报 extractor，SQL 走 SQL extractor。 |
| 上下文增强 | 给 chunk 加 context header。 |

### Step 4：Evidence Chunk 构建

输入：文档结构树 + SourceCard。

输出：EvidenceChunk。

建议：

| 规则 | 说明 |
| --- | --- |
| 结构优先 | 按章节/表格/议题切，不按固定字数粗暴切。 |
| 上下文补全 | 每个 chunk 带文档标题、时间、业务域、章节路径。 |
| chunk 类型化 | conclusion / metric_analysis / decision / action_item / sql / glossary。 |
| 保留原文位置 | page、section、line、paragraph id。 |

### Step 5：结构化抽取

输入：EvidenceChunk + SourceCard。

输出：KnowledgeObject。

推荐做多个 extractor，而不是一个大 prompt：

| Extractor | 输出对象 |
| --- | --- |
| `metric_definition_extractor` | MetricDefinition、DimensionDefinition。 |
| `data_asset_extractor` | DatasetAsset、ColumnAsset。 |
| `sql_template_extractor` | SQLTemplate、DatasetUsage、MetricCalculation。 |
| `weekly_report_extractor` | MetricMovement、BusinessEvent、Hypothesis、ActionRecommendation。 |
| `meeting_extractor` | MeetingCard、DecisionRecord、ActionItem、Hypothesis。 |
| `glossary_extractor` | BusinessTerm、Alias、DefinitionChangeLog。 |

### Step 6：实体对齐与去重

这是非常关键的一步。

输入：新抽取对象 + 已有对象。

输出：归一化对象。

要解决：

| 问题 | 例子 |
| --- | --- |
| 同义词 | GMV、成交额、支付金额是否同一个？ |
| 名称冲突 | “转化率”在不同业务域口径不同。 |
| 表别名 | 报告里写“渠道日表”，真实表名是 `ads_growth_channel_daily`。 |
| 指标版本 | 旧新口径是否同时存在。 |
| 事件合并 | 同一个活动在多份资料里被不同名称提到。 |

方法：

```text
规则匹配 + embedding 召回 + LLM 判断 + 人工确认
```

高风险对象必须人工确认：

| 必须确认 | 原因 |
| --- | --- |
| 指标定义 | 错了会影响所有回答。 |
| 可信表 | 错表会导致数据错误。 |
| SQL 模板 | 错 SQL 会直接产生错误数据。 |
| 关键归因结论 | 会影响业务判断。 |

### Step 7：关系抽取与图谱入库

输入：结构化对象。

输出：图谱节点和边。

注意：

| 规则 | 说明 |
| --- | --- |
| 先对象，后关系 | 不要直接从原文生成任意关系。 |
| 关系带证据 | 每条边都要能回到 source/chunk。 |
| 关系带状态 | candidate / confirmed / deprecated。 |
| 因果关系保守命名 | 用 candidate cause，不轻易写 causes。 |

### Step 8：索引构建

建议至少建 4 种索引：

| 索引 | 内容 | 用途 |
| --- | --- | --- |
| 全文索引 | chunk、指标名、表名、术语、SQL | 精确匹配指标、字段、表名。 |
| 向量索引 | chunk、SourceCard、AnalysisCase | 模糊语义检索。 |
| 结构化索引 | object_id、type、time、domain、status | 过滤和查询。 |
| 图索引 | node、edge、path | 关系追踪和 GraphRAG。 |

### Step 9：人工审核与发布

不同对象用不同审核等级：

| 对象 | 审核要求 |
| --- | --- |
| MetricDefinition | 必须 owner 确认。 |
| DatasetAsset 推荐状态 | 数据 owner 或分析 owner 确认。 |
| SQLTemplate | 分析师验证可执行和结果正确。 |
| Hypothesis | 可以低门槛入库，但状态必须是 pending/partially_verified。 |
| ActionRecommendation | 需要标注是否已执行和是否验证。 |
| EvidenceChunk | 可自动入库，但低权威来源检索时降权。 |

### Step 10：提供给大模型

提供方式不是“把库全部塞进去”，而是根据问题类型组装不同上下文。

| 问题类型 | 上下文包 |
| --- | --- |
| 查口径 | MetricDefinition + BusinessTerm + authority source。 |
| 找表 | DatasetAsset + ColumnAsset + lineage + usage examples。 |
| 取数 | MetricDefinition + SQLTemplate + DatasetAsset + validator result。 |
| 解释下降 | MetricMovement + graph neighborhood + EvidenceChunk + query result + Hypothesis。 |
| 做建议 | AnalysisCase + ActionRecommendation + validation history + current metric evidence。 |
| 查历史类似案例 | MetricMovement similarity + graph path + report evidence。 |

## 推荐技术形态

第一版可以这样落地：

| 层 | 技术形态 | 说明 |
| --- | --- | --- |
| 原文层 | 对象存储 / 文档库 / Git | 保存原文和版本。 |
| SourceCard / KnowledgeObject | Postgres / MySQL / 文档数据库 | 结构化对象和状态。 |
| EvidenceChunk | 文档库 + 全文索引 + 向量库 | 支持 hybrid retrieval。 |
| 图谱层 | Neo4j / NebulaGraph / PostgreSQL graph-like tables | 第一版可先用关系表模拟，复杂后再上图数据库。 |
| 语义查询资产 | 指标平台 + SQLTemplate 表 | 对接已有指标平台。 |
| 服务层 | retrieval API / context builder API | 给大模型提供上下文包。 |

如果团队不确定是否立刻上图数据库，建议：

```text
先按图谱模型设计 schema。
第一版用关系表存 nodes/edges。
当关系查询、路径查询、可视化和 GraphRAG 需求变强时，再迁移到图数据库。
```

## 最小可行版本

不要一开始处理所有资料。建议第一期只做：

| 范围 | 数量 |
| --- | --- |
| 核心指标 | 20-30 个。 |
| 可信数据表 | 20-50 张。 |
| 周报/报告 | 最近 2-3 个月。 |
| 会议纪要 | 从现在开始积累，先不补历史。 |
| SQL 模板 | 20-50 条高频查询。 |
| 老板/业务问题 | 50 条。 |
| 历史分析案例 | 10-20 个。 |

第一期必须产出的知识对象：

```text
MetricDefinition
DatasetAsset
ColumnAsset
SQLTemplate
ReportCard
MetricMovement
BusinessEvent
Hypothesis
ActionRecommendation
AnalysisCase
```

第一期必须产出的关系：

```text
Metric MEASURED_BY SQLTemplate
SQLTemplate USES_DATASET Dataset
Dataset HAS_COLUMN Column
Metric HAS_DIMENSION Dimension
Report OBSERVED MetricMovement
MetricMovement HAS_CANDIDATE_CAUSE Hypothesis
Hypothesis SUPPORTED_BY EvidenceChunk
Hypothesis RELATED_TO BusinessEvent
ActionRecommendation BASED_ON Hypothesis
```

## 判断标准：什么资料值得结构化

不是所有资料都值得高成本处理。

| 问题 | 如果答案是“是”，就值得结构化 |
| --- | --- |
| 以后会被反复问到吗？ | 是。 |
| 会影响指标口径或 SQL 结果吗？ | 是。 |
| 能解释业务变化原因吗？ | 是。 |
| 能帮助生成可执行建议吗？ | 是。 |
| 能连接多个资料来源吗？ | 是。 |
| 需要追踪状态或验证结果吗？ | 是。 |

如果只是一次性背景信息，保留为 evidence chunk 即可。

## 最容易踩的坑

| 坑 | 后果 | 避免方式 |
| --- | --- | --- |
| 原文直接向量化 | 检索到片段但无法判断真假、新旧、权威性。 | 先做 SourceCard 和 metadata。 |
| 自动抽图谱但不设 schema | 图谱边混乱，维护成本高。 | schema-guided extraction。 |
| 把假设当事实 | 大模型输出错误归因。 | 区分 fact / observation / hypothesis / recommendation。 |
| 没有实体对齐 | 同一个指标多套名称，检索和查询混乱。 | 术语库 + alias + 人工确认。 |
| 没有版本时间 | 旧口径污染新问题。 | valid_from / valid_to。 |
| 没有 SQL verified asset | 每次重新生成 SQL，准确率不稳定。 | 建 SQLTemplate / verified query。 |
| 只做图谱不做 chunk | 缺少原文证据，回答不可引用。 | 图谱 + evidence chunk 并存。 |
| 只做 chunk 不做结构化对象 | 无法稳定查口径、查表、做归因链路。 | 抽取 KnowledgeObject。 |

## 下一步待讨论决策点

这份调研报告之后，不应该直接进入开发。建议先讨论这些问题，再定最终执行方案。

| 决策点 | 可选项 | 影响 |
| --- | --- | --- |
| 第一版主路线 | A 文档 RAG / B 结构化对象 / C 轻量图谱 / E 语义层问数 | 决定第一期投入重点。 |
| 图谱范围 | 不做图谱 / nodes-edges 关系表 / 图数据库 | 决定后续归因链路和历史复盘能力。 |
| 结构化对象范围 | 只做指标和 SQL / 加周报对象 / 加会议和建议对象 | 决定能否回答“为什么”和“怎么办”。 |
| 审核机制 | 全自动 / 关键对象人工确认 / 全量人工确认 | 决定准确性和维护成本。 |
| 向量库角色 | 主知识库 / 证据检索层 / 仅作为辅助召回 | 决定系统是否会过度依赖相似度。 |
| 指标平台关系 | 复制一份指标定义 / 只缓存快照 / 实时调用权威 API | 决定口径一致性。 |
| SQL 处理方式 | 每次生成 / 模板优先 / Verified SQL 优先 | 决定问数稳定性和安全性。 |
| 会议纪要处理深度 | 只入 chunk / 抽取 action 和 hypothesis / 抽取后进入图谱 | 决定会议资料是否能复用为经营判断。 |
| 周报处理深度 | 只做摘要 / 抽取指标波动和归因 / 抽取后续验证 | 决定历史报告能否形成经验库。 |

我建议下一步先围绕一个具体样本讨论，例如：

```text
拿 1 篇周报 + 1 篇会议纪要 + 3 条 SQL + 1 份数据文档，
手工跑一遍抽取流程，
看最终对象结构是否符合你们真实使用方式。
```

这样能比抽象讨论更快判断哪些字段有用、哪些字段太重、哪些必须人工确认。

## 调研阶段性结论

最终建议：

1. **要做结构化表达**，这是基础，不做结构化就没有稳定知识库。
2. **要做知识图谱**，但第一版做轻量领域图谱，不做大而全企业图谱。
3. **不要把所有原文直接丢向量库**，原文只作为 evidence 和 trace。
4. **周报和会议要重点抽取经营分析对象**：指标波动、业务事件、假设、建议、决策、后续验证。
5. **SQL 和代码要抽成查询资产**：表字段依赖、指标计算逻辑、SQLTemplate、verified query。
6. **数据文档要抽成权威语义资产**：BusinessTerm、MetricDefinition、DatasetAsset、ColumnAsset。
7. **大模型最终消费的是 ContextPack**：结构化事实、图谱路径、证据 chunk、SQL 结果和不确定性，而不是原文集合。

一句话：

> 你们要建的不是“文档知识库”，而是一个把原始业务材料加工成 **证据、对象、关系、查询资产** 的经营分析知识工厂。
