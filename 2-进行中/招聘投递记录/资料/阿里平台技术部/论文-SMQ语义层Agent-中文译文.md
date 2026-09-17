# 面向异构企业数据库的语义层介导自然语言转 SQL 智能体

原题：A Semantic-Layer-Mediated Agent for Natural Language to SQL over Heterogeneous Enterprise Databases

作者：Ha Jeong Kim、Saksonita Khoeurn、Ye Ji Yoon。

作者单位：DAQUV Corp.（韩国首尔）；忠北国立大学管理信息系统系与 BigDataLabs, Co., Ltd.（韩国清州）。Ha Jeong Kim 与 Saksonita Khoeurn 为共同第一作者，Saksonita Khoeurn 为通讯作者。

个人学习用 · 中文翻译：Codex，2026-09-05。正文保留论文的章节、公式、代码与实验表；“我们”指原作者。原图直接嵌入，图内英文保留。

先看方法与学习重点：[三篇论文解读](论文三篇-问题方法验证与DataAgent学习解读.md)。

## 摘要

在真实企业数据库上将自然语言转换为 SQL（NL2SQL），仍然明显比在学术基准上更困难：数据库模式包含数百张物理表，字段名称含义不直观，不同引擎采用不同 SQL 方言，一个分析问题就可能要求嵌套聚合、时间窗口逻辑和多表连接。直接把原始数据库模式作为文本提示给大型语言模型（LLM），会让模型一次面对所有这些复杂性，生成的查询因而容易出错。

本文提出一种由语义层介导的 NL2SQL 智能体架构，将用户意图与物理执行解耦。智能体通过一种紧凑的中间表示——语义模型查询（Semantic Model Query，SMQ）——在经过整理的语义层上进行推理，而不是直接针对原始表编写 SQL。确定性引擎把 SMQ 编译为符合目标方言的 SQL，随后由智能体检查、组合并执行这些 SQL。

系统遵循每步调用一个工具的“思考—行动”循环，在 SQLite、BigQuery 和 Snowflake 后端之间路由执行，并被封装为端到端评测框架。以 Gemini 3 Pro 为基础模型时，系统在包含 547 项任务的 Spider2-snow 基准上取得 94.15% 的执行准确率。该基准是一组在 Snowflake 上执行的真实企业 NL2SQL 任务。该成绩位列官方榜单第三，显著高于仅利用数据库模式的基线。

本文介绍组件设计、SMQ 表示、智能体探索策略和按后端划分的结果，并讨论把语义层作为 LLM 智能体上下文来源时，模型质量与评测集过拟合之间的矛盾。

关键词：Text-to-SQL、NL2SQL、大语言模型智能体、语义层、中间表示、工具使用、企业数据库。

## I. 引言

将自然语言问题转换为可执行 SQL，长期以来都是降低数据访问门槛的重要目标。近期大语言模型在 Spider [2]、BIRD [3] 等学术基准上表现良好。这些基准中的数据库模式相对较小，问题往往可以较直接地映射为单条查询。企业环境的差异不仅在规模，也在问题性质。

Spider2 [1] 正是为刻画这一差距而提出。其任务涉及生产数仓，包含数百个字段、难懂的命名、方言特有函数；参考答案经常由数十行 SQL 组成，使用公共表表达式（CTE）、窗口函数和多步聚合。

Spider2 上公开报告的准确率远低于 Spider 上接近饱和的成绩。这说明，把数据库模式放入提示词，再要求模型生成 SQL，无法直接迁移到真实工作负载。

我们认为困难有两个独立来源。第一个是语义落地（grounding）：模型必须从大量缺乏自解释能力的表和字段中，确定哪些物理元素相关，以及它们如何连接。第二个是查询组合（composition）：在正确的构建块已知之后，模型必须把它们组合成正确且符合方言的 SQL。

将这两个问题混在一次自由生成中，会使简单提示方案非常脆弱：一个错误字段名或连接条件就能使整条查询失败，而且模型缺少可以据以恢复的结构化操作对象。

本文介绍 spider2-daquv-quvi 的架构。它在 LLM 与数据库之间引入语义层，将语义落地与查询组合分开。语义层是对各数据库经过整理、面向业务的描述：它将表封装成语义模型，公开有名称的维度、度量和指标，同时保存可读描述与对应的物理字段表达式。

智能体不会先查看原始数据库模式，而是向语义层提交紧凑的结构化查询 SMQ。确定性引擎将每个 SMQ 编译为符合目标方言的 SQL 并返回。

智能体把这些编译片段作为经过验证的构建块：检查其中展示的物理表达式和连接模式，将其组合为最终查询；必要时添加 SMQ 编译器不支持的结构，如窗口函数或递归 CTE，随后在相应后端执行。

本文的贡献如下：

- 提出通过语义层及结构化中间表示 SMQ 介导 LLM 推理的 NL2SQL 系统架构，将模式落地与 SQL 组合解耦，见 III—IV 节。
- 设计每步使用一个工具的思考—行动循环：利用 SMQ 编译开展探索，直接 SQL 执行是唯一的终止动作；同时给出要求智能体遵守该流程的提示策略，见 V 节。
- 构建多后端执行与评测框架，将查询路由到 SQLite、BigQuery 和 Snowflake，并按 Spider2 协议评分，见 VI 节。
- 在 547 项任务的 Spider2-snow 上进行实验，报告 94.15% 的执行准确率、分后端结果和公开榜单比较，并讨论提高语义层质量与对评测集过拟合之间的实际矛盾，见 VII—VIII 节。

## II. 相关工作

**Text-to-SQL 基准。** Spider [2] 将跨领域、多表语义解析确立为标准任务；BIRD [3] 引入规模更大、数据更脏的数据库，并强调效率与外部知识。Spider2 [1] 进一步提高要求，涵盖 BigQuery、Snowflake 和本地引擎上的企业级数仓，以及较长、贴近实际的参考查询。本文采用其 Spider2-snow 分支评测。

**用于 Text-to-SQL 的 LLM 方法。** DIN-SQL [4]、DAIL-SQL [5] 和 C3 [6] 等提示与分解方法，通过模式链接、少样本示例选择和自我纠错改进单次生成。MAC-SQL [7]、CHESS [8] 等多智能体和流水线系统引入专门的分解、选择、优化角色以及模式裁剪阶段。

这些方法直接操作物理模式。我们的系统则通过经过整理的语义层进行推理，把编译得到的 SMQ→SQL 片段视作经过验证的落地证据，而不是要求模型从平铺的模式描述中回忆物理名称。

**语义层。** BI 语义层和指标框架，例如 dbt MetricFlow [10]，允许分析师只定义一次维度、度量与指标，再跨查询复用。我们把这一思路用作 LLM 的落地基础：语义层既是模型对数据的视图，也是可编译、符合方言的 SQL 的来源。

**LLM 智能体与工具使用。** ReAct [9] 的思考—行动范式将推理过程与工具调用交错执行。我们的智能体采用严格的每步单工具变体：一个工具用于探索，即 SMQ 编译；另一个工具用于 SQL 执行，作为唯一的终止动作。这种设计约束智能体的行动空间，减少错误传播。

## III. 系统架构

图 1 展示端到端架构。系统分为四层：（1）加载基准实例并驱动批量并行执行的编排层；（2）承载 LLM 智能体和语义层的 QUVI NL2SQL 服务；（3）确定性的 SMQ-to-SQL 引擎；（4）在正确数据库上运行最终 SQL 的多后端执行器。每个实例都是独立工作流，由实例标识和时间戳标记。

**图 1 图注译文：** 端到端架构。编排器将自然语言问题派发到 QUVI 服务，由该服务在语义层上运行智能体循环。引擎将 SMQ 编译为 SQL；最终 SQL 根据实例前缀路由到 SQLite、BigQuery 或 Snowflake 执行器。结果写入提交文件，由 Spider2 评测套件评分。

![图 1：SMQ 语义层 Agent 端到端架构，原论文图片](https://arxiv.org/html/2606.31041v1/fig1.png)

下面是译者根据正文与图注整理的中文结构示意，未复刻原图布局：

```text
编排层：读取任务、分配工作流、并发执行
  ↓ 自然语言问题
QUVI 服务：智能体 + 语义模型
  ↔ SMQ-to-SQL 引擎：编译并返回 SQL / 预览
  ↓ 智能体组合的最终 SQL
多后端执行器：SQLite / BigQuery / Snowflake
  ↓ 查询结果、SQL 文件、运行记录
Spider2 评测
```

### III-A. 编排层

入口解析运行配置，包括数据库分支 lite/snow，以及实例选择条件：显式 ID、区间、前缀或全部实例。实例加载器读取 Spider2 实例文件，获得自然语言问题及元数据。执行服务通过线程池并行派发实例，并处理限流退避，例如 HTTP 429、单实例超时及有上限的重试。

系统为每个实例创建工作流标识，然后调用 NL2SQL 客户端。客户端按数据库用户进行身份验证，再将问题发送到 QUVI 服务。

### III-B. QUVI NL2SQL 服务

QUVI 承载智能体和语义层。收到问题后，它：（i）查找目标数据库的相关语义模型；（ii）运行 V 节介绍的思考—行动循环，生成 SMQ 和 SQL；（iii）将 SMQ 编译委托给引擎。

语义层按数据库组织为目录，包含源表定义、连接图、日期与时间骨架配置，以及每个语义模型对应的 YAML 文件。

### III-C. SMQ-to-SQL 引擎

独立引擎端点 `SmqToSql` 以确定性方式将 SMQ 编译成 SQL。它把引用的维度、度量或指标解析为物理字段表达式，根据连接图注入连接条件，生成目标方言的 SQL。

该组件是物理名称的权威来源：智能体最终查询使用的每个表名和字段表达式都取自编译器输出，而不是由模型凭空生成。

### III-D. 多后端执行器

自定义执行服务器提供统一端点，根据实例 ID 前缀选择后端，见表 I。各执行器持有相应的凭证和驱动，返回由“行字典”组成的结果列表；编排器将结果序列化到 SQL 文件和 CSV 中用于评分。

**表 I：按实例标识前缀进行后端路由。**

| 前缀 | 后端 | 执行器 |
| --- | --- | --- |
| `local*` | SQLite | `sqlite_executor` |
| `bq*`、`ga*` | BigQuery | `bigquery_executor` |
| `sf*`、`sf_bq*` | Snowflake | `snowflake_executor` |

## IV. 语义层与 SMQ

### IV-A. 语义模型

每张物理表由一个语义模型封装，获得业务名称，并公开有类型、有描述的数据元素。维度是分组或过滤键等聚合依据；度量是聚合目标；指标则是在度量和维度上预定义的聚合或派生计算。

关键在于，每个元素同时携带：（a）LLM 在语义落地时阅读的自然语言描述；（b）编译时使用的精确物理字段表达式 `expr`。

抽象名称和物理表达式因此保持分离，智能体可以围绕意图推理，由引擎负责物理映射。代码清单 1 展示了一个片段。

```yaml
- name: RetailAnalyticsSalesModel
  table: ..._snowflake('RETAIL_ANALYTICS_SALES')
  dimensions:
    - name: asin
      type: varchar
      description: Amazon Standard Identification Number
      expr: ASIN
  measures:
    - name: orderedRevenue
      type: float
      description: ordered revenue
      expr: ORDERED_REVENUE
```

**代码清单 1：** 语义模型片段。一个维度和一个度量，各自将描述与物理表达式配对。代码中的英文描述意为“亚马逊标准商品标识号”和“订单收入”。原文 `table` 行使用省略形式，并非完整可运行配置。

### IV-B. 连接图

模型间的连接在每个数据库的连接图中一次性声明为有类型的边，包含起始模型、目标模型、连接键以及给出左右表达式的 `on` 条件。表达式也可以包含对脏键执行 `TRIM` 等转换。

编译器查询此图并自动组装连接，因此对于已支持的情况，智能体无需重新发现连接条件。

### IV-C. 语义模型查询 SMQ

SMQ 是智能体与引擎之间的中间表示。它是紧凑的 JSON 对象，包含三个列表：`metrics` 表示查询目标；`filters` 表示 WHERE 条件；`group_by` 表示分组维度。

元素采用统一命名约定：维度和度量使用 `ModelName__elementName`，指标直接使用其名称。代码清单 2 展示示例。

SMQ 有意只覆盖常用分析核心：选择、过滤、分组和已声明连接。它不表达 CROSS JOIN、任意子查询、高级窗口函数或递归 CTE。这是设计上的取舍：SMQ 是探索和语义落地工具，SQL 的长尾复杂性由智能体在编译结果之上进行组合来处理。

```json
{
  "metrics": ["RetailAnalyticsSalesModel__orderedRevenue"],
  "filters": ["RetailAnalyticsSalesModel__period = 'DAILY'"],
  "group_by": ["RetailAnalyticsSalesModel__asin"]
}
```

**代码清单 2：** 一个 SMQ。引擎将其编译为符合方言的 SQL，并返回 SQL 和结果预览。

## V. 智能体工作流

### V-A. 思考—行动循环

智能体运行受约束的思考—行动循环。每一轮先生成内部推理块，然后恰好调用一个工具。系统提供三个工具：`getModelDataElements` 列出所选模型的指标与维度；`convertSmqToSql` 编译 SMQ 并返回 SQL 和五行结果预览；`execute` 执行最终 SQL。

每次响应只允许一个工具调用，可以收窄行动空间，使执行轨迹可审计。算法 1 概括如下。

**算法 1：语义层介导的 NL2SQL 智能体循环。**

```text
1. 输入：问题 q、目标数据库的语义模型 M、方言 d
2. E ← getModelDataElements(relevant(M, q))    // 发现元素
3. B ← 空集合                               // 已验证的 SQL 构建块
4. 重复：
5.     为某个中间结果编写 SMQ s
6.     (sql, preview) ← convertSmqToSql(s)
7.     B ← B ∪ {从 sql 中取得的表达式和表名}
8. 直到：构建块足以回答 q
9. 从 B 组合最终 SQL Q，加入 CTE、窗口函数或子查询
10. 返回 execute(Q)                         // 唯一的终止动作
```

### V-B. 用 SMQ 探索的约束

该提示策略的关键是：`convertSmqToSql` 用于探索，不直接产出最终答案。它揭示抽象元素如何映射到物理字段、目标方言语法和连接模式。智能体从编译结果中提取物理表名和字段表达式，再组装自己的最终查询，并应用超出 SMQ 表达范围的结构。

严格约束禁止在执行 SQL 中把语义模型名称当作物理表名称：只允许使用来自编译器输出的名称。系统禁止直接检查数据库模式，例如查询 `INFORMATION_SCHEMA`，迫使所有语义落地都经由语义层完成。唯一一次 `execute` 调用是终止动作，成功执行后工作流结束。

### V-C. 语义层介导为什么有帮助

这一设计同时处理 III 节提出的两种困难。语义落地变为对有描述、采用业务名称的元素进行引导式搜索，而非对平铺模式猜测；智能体采用的物理标识符已经由编译器验证。因此，组合错误主要局限于智能体自行添加的查询结构，较容易通过重新探索发现和修复。

## VI. 执行与评测框架

最终 SQL 被派发到后端执行器。返回行写入提交目录中的逐实例 SQL 文件和 CSV；同时保存可读的 Markdown 工具调用历史，供调试使用。

评分使用 Spider2 官方评测套件的两种模式：执行结果比较，即对照参考结果集检查提交结果；以及 SQL 比较。

服务端口、数据与语义层路径、超时、重试上限及凭证等配置集中在一个应用配置中，使同一框架可以在 SQLite、BigQuery 和 Snowflake 环境间运行，无需修改代码。

## VII. 评测

### VII-A. 实验设置

我们使用 Spider2-snow 进行评估。该基准包含 547 个在 Snowflake 上执行的企业 NL2SQL 实例，数据库来源覆盖 SQLite、BigQuery、GA4 和原生 Snowflake。

底层 LLM 为 Gemini 3 Pro（preview），通过语义层的 `smqThink` 智能体节点调用。温度为 0.1，扩展思考设为 high，输出预算 16,384 Token，每个实例最多进行 20 次 SMQ 迭代；SMQ→SQL 编译器具有确定性。

我们发现准确率对模型的思考配置较敏感：扩展思考帮助模型组合 Spider2-snow 所需的复杂多步 SQL，关闭该能力会明显降低准确率。

本文报告执行准确率：按照 Spider2 官方执行结果协议，如果执行查询得到的结果集与参考结果匹配，则该实例判为正确。

### VII-B. 总体结果

系统正确回答了 547 个实例中的 515 个，执行准确率为 94.15%。考虑到 Spider2 的参考查询较长、涉及多步操作并依赖特定方言，该结果表明，语义层介导与强推理模型、精心整理的逐库语义层相结合，可以在真实企业模式上提供有效的语义落地。

### VII-C. 分后端结果

表 II 按实例类别分解准确率。除原生 Snowflake 类别外，每个数据库来源类别的准确率均超过 94%。原生 Snowflake 的准确率为 55.6%，同时也是最小的类别，只有 18 个实例，因此方差最高。

特定后端的方言处理能力和各数据库语义层的成熟度，而非智能体循环本身，是剩余失败的主要因素。

**表 II：Spider2-snow 按数据库来源类别划分的执行准确率，基础模型为 Gemini 3 Pro。**

| 实例类别（来源） | 正确数 / 总数 | 准确率 |
| --- | --- | --- |
| `sf_local`（SQLite 来源） | 131 / 135 | 97.0% |
| `sf_ga`（GA4 来源） | 24 / 25 | 96.0% |
| `sf_bq`（BigQuery 来源） | 350 / 369 | 94.9% |
| `sf`（原生 Snowflake） | 10 / 18 | 55.6% |
| 合计 | 515 / 547 | 94.15% |

### VII-D. 与已发表方法比较

表 III 将本文结果与 Spider2 官方榜单 [12] 的条目比较。直接基于原始模式的通用智能体和提示流水线在这一基准上表现仍较低：采用 GPT-4o 的 DAIL-SQL 达到约 2.2%；Spider-Agent 随基础模型不同约为 23%—26%；ReFoRCE 达到约 31.3%。本文系统在榜单中以 QUVI-3 + Gemini-3-pro-preview 名义列出，达到 94.15%，为第三高的条目。

相对于仅模式基线的较大差距，与本文的核心观点一致：利用整理过的语义层介导 LLM，对企业 NL2SQL 很关键。但必须指出，语义层包含逐数据库的领域知识，而零样本基线无法访问这些知识。因此，比较反映的是整个系统——语义层加智能体——的价值，而非 LLM 本身的差异。

**表 III：Spider2-snow 已发表方法的准确率比较，数据来自论文引用的榜单。**

| 方法 | 准确率 |
| --- | --- |
| DAIL-SQL + GPT-4o | 2.20% |
| Spider-Agent + o1-preview | 23.58% |
| Spider-Agent + Claude-4-Sonnet | 25.78% |
| ReFoRCE + o1-preview | 31.26% |
| 本文（QUVI-3 + Gemini 3 Pro） | 94.15% |

### VII-E. 失败模式

从保存的执行轨迹看，反复出现的失败包括：（i）SMQ 编译能力缺口，例如所引用模型缺少必要连接关系，编译器无法组装片段；（ii）复杂查询中由智能体编写部分的组合错误，例如嵌套时间窗口、精确舍入和排名语义；（iii）语义层定义不充分，例如参考查询需要的某个字段尚未公开为有描述的数据元素。

第一类和第三类需要改进语义层，而不是修改智能体，这也是下文讨论的出发点。

## VIII. 讨论

### VIII-A. 语义层质量是关键影响因素

由于语义落地由语义层承担，系统准确率很大程度上受制于各数据库模型对数据的描述质量和连接声明的完整性。

实践中，补充缺失元素、改进描述、声明连接边等语义模型优化，可以直接提高对应数据库上的准确率。因此，语义层成为主要维护对象。

### VIII-B. 过拟合的矛盾

围绕评测集整理语义层会带来类似古德哈特定律的风险：原本简洁、可泛化的描述，可能逐渐变成冗长文本，实际编码了已知问题的预期答案。

这种上下文可以提高基准准确率，却降低系统面对未见问题和模式变更时的稳健性，类似于对奖励代理指标的过度优化。

因此，我们把语义层当作需要评审的代码：描述应编码可复用的模式知识，而非针对某道题的提示；连接、表达式等结构信息应存入有类型的字段，而非散文说明。

如何量化并约束这种取舍——也就是获得一种不依赖下游任务准确率的构造上下文内在质量信号——仍是开放问题和未来方向。

### VIII-C. 局限

SMQ 有意只覆盖常见分析核心，最复杂的查询仍依赖智能体自行编写 SQL，其正确性不由引擎保证。

实验只使用 Spider2-snow 一个基准，并依据执行结果匹配评分；这种方式在边界情况下可能高估或低估正确性。小样本类别的分后端结果方差较高。

最后，准确率与每个数据库手工编写的语义层成熟度交织在一起，而不同数据库的语义层成熟度并不相同。

## IX. 结论

本文提出一种语义层介导的 NL2SQL 智能体架构，将模式落地与 SQL 组合解耦。

通过在 LLM 与数据库之间引入经过整理的语义层和紧凑的 SMQ 中间表示，并在受约束的每步单工具循环中，利用确定性 SMQ→SQL 编译提供经验证的构建块，系统在 547 项任务的 Spider2-snow 上达到 94.15% 的执行准确率，位列官方榜单第三，显著高于仅模式基线。

结果表明，通过结构化、面向业务的层来介导 LLM 推理，是企业 NL2SQL 的有效策略。仍待解决的核心挑战是持续维护语义层质量，同时避免针对评测集过拟合。

## 参考文献

以下保留原文作者、题名、年份、编号和书目信息，以便检索；没有把文献表中的历史年份改成当前年份。

1. F. Lei, J. Chen, Y. Ye, R. Cao, et al., “Spider 2.0: Evaluating language models on real-world enterprise text-to-SQL workflows,” in Proc. Int. Conf. Learning Representations (ICLR), 2025.
2. T. Yu, R. Zhang, K. Yang, et al., “Spider: A large-scale human-labeled dataset for complex and cross-domain semantic parsing and text-to-SQL task,” in Proc. Conf. Empirical Methods in Natural Language Processing (EMNLP), 2018, pp. 3911–3921.
3. J. Li, B. Hui, G. Qu, et al., “Can LLM already serve as a database interface? A big bench for large-scale database grounded text-to-SQLs (BIRD),” in Advances in Neural Information Processing Systems (NeurIPS), 2023.
4. M. Pourreza and D. Rafiei, “DIN-SQL: Decomposed in-context learning of text-to-SQL with self-correction,” in Advances in Neural Information Processing Systems (NeurIPS), 2023.
5. D. Gao, H. Wang, Y. Li, et al., “Text-to-SQL empowered by large language models: A benchmark evaluation,” Proc. VLDB Endowment, vol. 17, no. 5, pp. 1132–1145, 2024.
6. X. Dong, C. Zhang, Y. Ge, et al., “C3: Zero-shot text-to-SQL with ChatGPT,” arXiv:2307.07306, 2023.
7. B. Wang, C. Ren, J. Yang, et al., “MAC-SQL: A multi-agent collaborative framework for text-to-SQL,” in Proc. Int. Conf. Computational Linguistics (COLING), 2025.
8. S. Talaei, M. Pourreza, Y.-C. Chang, et al., “CHESS: Contextual harnessing for efficient SQL synthesis,” arXiv:2405.16755, 2024.
9. S. Yao, J. Zhao, D. Yu, et al., “ReAct: Synergizing reasoning and acting in language models,” in Proc. Int. Conf. Learning Representations (ICLR), 2023.
10. dbt Labs, “dbt Semantic Layer and MetricFlow,” Technical documentation, 2024. [Online]. Available: https://docs.getdbt.com/docs/build/about-metricflow
11. M. Deng, A. Ramachandran, C. Xu, et al., “ReFoRCE: A text-to-SQL agent with self-refinement, consensus enforcement, and column exploration,” arXiv:2502.00675, 2025.
12. XLang Lab, “Spider 2.0 leaderboard,” 2026. [Online]. Available: https://spider2-sql.github.io/

---

## 术语速查



| 英文 | 本译文用语 | 解释 |
| --- | --- | --- |
| schema | 数据库模式 | 表、字段、类型和关系等结构 |
| grounding | 语义落地 | 将问题中的概念对应到可验证的数据元素 |
| composition | 查询组合 | 将已知片段组合为完整 SQL |
| dimension | 维度 | 分组或过滤依据 |
| measure | 度量 | 聚合目标；此处按本文定义使用 |
| metric | 指标 | 预定义聚合或派生计算 |
| semantic layer | 语义层 | 业务概念与数据映射的逻辑层 |
| intermediate representation | 中间表示 | 连接意图生成与编译执行的结构化表达 |
| harness | 执行与评测框架 | 承担任务运行、结果保存与验证的外围工程 |
| time spine | 时间骨架 | 用于时间相关计算的连续时间结构 |

来源：[arXiv:2606.31041v1](https://arxiv.org/abs/2606.31041v1)，2026-06-30；[英文全文](https://arxiv.org/html/2606.31041v1)。原作者及单位见篇首。原文与本非官方中文改编采用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。版本、实验口径与译者核验见[独立附录](论文与产品-核验附录.md)。

[返回资料入口](README.md) · [语义层领域解读](2026-09-05-面向Agent的语义层-概念与前沿研究.md) · [工作前景调研](2026-09-05-语义层与Agent数据基础设施-职业前景调研.md)
