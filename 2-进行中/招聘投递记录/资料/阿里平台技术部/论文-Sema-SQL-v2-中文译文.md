# Sema-SQL：利用大语言模型扩展关系查询

原文：Yin Lin、Tianjing Zeng、Zhongjun Ding、Rong Zhu、Bolin Ding、H. V. Jagadish、Jingren Zhou。单位：Alibaba Group；H. V. Jagadish 为 University of Michigan。

个人学习用 · 中文翻译：Codex，2026-09-05，依据 arXiv v2。正文包含摘要、正文 1—8、公式、3 个算法、5 张表和图注，参考文献保留英文。“我们”指原作者。原图直接嵌入，图内英文保留。

先看方法与学习重点：[三篇论文解读](论文三篇-问题方法验证与DataAgent学习解读.md)。

## 摘要

关系数据库擅长结构化数据分析，但实际查询越来越需要超出标准 SQL 的能力，例如在不一致的名称之间进行实体语义匹配、提取数据库模式中没有显式存储的信息，以及分析非结构化文本。虽然 Text-to-SQL 系统支持用自然语言查询，但它们仍受限于关系运算，不能利用现代大语言模型的语义推理能力。另一方面，近期的语义算子系统通过语义连接、映射、聚合等 LLM 驱动操作扩展了关系代数，却要求用户手工构建复杂查询流水线。

为填补这一空缺，我们提出 Sema-SQL：自动生成将关系运算与 LLM 语义推理相结合的高效查询，从而回答自然语言问题。我们形式化定义混合关系代数（Hybrid Relational Algebra，HRA），以声明式抽象统一传统关系算子和 LLM 用户定义函数（UDF）。

系统自动完成三个关键环节：（1）通过上下文学习生成 HRA 查询，并为 LLM UDF 给出精确的自然语言规格；（2）通过基于成本的变换和 UDF 改写优化查询；（3）通过高效执行算法，尤其是智能分批，将语义连接中的 LLM 调用次数平均减少约 93%。在已有基准及其扩展上的广泛实验表明，该设计显著扩展了查询能力。

## 1. 引言

关系数据库系统长期以来一直是结构化数据存储和管理的主流范式。业务分析师、数据科学家和决策者经常需要复杂数据库查询，但其中许多人缺少所需的技术技能。近年来，数据库自然语言接口成为重要研究方向，大语言模型尤其在 SQL 生成方面展现出潜力（Gao 等，2024；Pourreza 与 Rafiei，2023；Wang 等，2025；Pourreza 等，2025；Talaei 等，2024）。

这些方法能否真正处理用户在现实中提出的复杂问题？BIRD 和 Spider 等公认的 Text-to-SQL 基准受关系代数表达能力限制，并假设回答问题所需的全部信息都包含在原数据库模式中。然而，许多实际问题超出了这些能力。

考虑以下由真实用户问题简化得到的例子。图 1(a) 中，一家 IT 供应商希望按客户查询销售收入，需要对两张表进行非等值连接。标准 SQL 的字符串相等匹配会失败；传统相似性方法往往对参数敏感、扩展性不足，而且只能处理语法层面的相似性。图 1(b) 中，一位体育记者分析 NBA 球员的选秀年份与首次获得 MVP 的年份之差，但数据库缺少选秀年份。传统 SQL 遵循封闭世界假设，不能回答需要模式之外信息的问题。图 1(c) 中，一位餐厅老板想从自由文本评论中总结顾客最喜欢的菜，这要求提取语义并分析情感，超出只处理结构化数值或类别的标准 SQL 能力。

**图 1：动机示例——用 LLM 能力扩展关系查询。**

![图 1：动机示例——用 LLM 能力扩展关系查询。原论文图片](https://arxiv.org/html/2604.23477v2/motivating_examples.png)

为支持这类分析，新一类数据处理系统通过语义过滤、连接、映射、排序、分类和摘要等语义算子，将 LLM 能力引入关系代数。它们能以语义连接匹配实体，以语义映射从模型参数知识或外部知识中补充缺失信息，以语义摘要分析非结构化文本中的偏好。

但关键问题仍未解决：如何自动将自然语言问题转换为同时包含关系操作和语义操作的高效查询？现有方法存在互补的不足。混合问答系统直接让 LLM 对文本和关系数据作答，却不产生查询，因此难以核验答案与复现结果。语义算子系统则要求用户手工实现算子、构建查询并优化执行，同时具备数据库和 LLM 编程经验。

**我们的方法。** Sema-SQL 将关系运算与 LLM 语义推理结合起来回答关系数据上的自然语言问题。输入为自然语言问题、证据（外部知识）和关系数据库。系统先生成 HRA 声明式查询；HRA 是一种与具体数据库无关、纳入 LLM UDF 的形式化表示。随后，系统通过基于成本的变换和 UDF 改写编译出优化计划，最后使用语义算子的专用算法执行。[作者公开代码](https://github.com/semasql/SEMA-SQL)

**图 2：系统分为查询生成、查询优化、查询执行三个阶段。**

![图 2：系统分为查询生成、查询优化、查询执行三个阶段。原论文图片](https://arxiv.org/html/2604.23477v2/sema_system_new.png)

构建端到端系统要解决三个挑战。首先，LLM 不熟悉语义算子，难以判断何时需要它们、应处理哪些数据，以及如何精确写出 UDF 内的自然语言提示。我们的结构化提示框架提供紧凑语义模式、逐步算子分解，以及经过整理的说明与少样本例子。

其次，生成查询的执行效率可能不佳。固定规则改写并不考虑真实成本；由 LLM 改写计划又往往缺乏成本模型与形式化正确性保证。Sema-SQL 把通常比关系运算高几个数量级的 LLM 调用成本纳入优化，使用动态规划选择 UDF 位置，并以符号执行验证计划等价性。在可行时，还将 LLM UDF 改写为 SQL 表达式。

最后，语义算子的执行本身可能昂贵。例如，LOTUS 与 Palimpzest 的嵌套循环语义连接可能为每个行对调用一次模型。Sema-SQL 根据上下文长度和任务复杂度动态分组，一次调用找出两个批次间全部可匹配行对，在保持准确性的同时提高效率。

贡献总结：

- 提出 HRA，统一关系算子与基于 LLM 的语义操作，为自然语言自动生成查询提供声明式目标语言。
- 提供语义模式表示、问题分解和精确 UDF 合成方法，在语法有效性、语义正确性和可执行性三个标准下达到 93.3% 查询生成准确率；在需要超出关系运算的语义推理任务上，与依赖手工流水线的先进系统达到相近效果。
- 提出考虑 LLM 成本的优化框架，包括保持计划等价的 UDF 位置选择与 SQL 改写，使执行时间减少 28%、Token 消耗减少 21%。
- 提供语义算子专用执行算法，语义连接分批使 LLM 调用减少到原来的约 1/5—1/300，实验中没有准确率损失。

## 2. 混合关系代数

HRA 在关系代数中增加基于 LLM 的语义操作，以声明式形式表示结构化数据处理与语义推理的组合。

图 3 比较 LOTUS 程序与 HRA 如何表达 TAG 中的问题：“位于人口超过 200 万的县的学校，共有多少名考生？”这需要语义映射来取得加利福尼亚各县的人口。

**图 3(a)：LOTUS 专家编写程序。** 保留原代码；提示词的意思是“给出该县人口，只输出不含逗号的数字；给出你认为最可能的值”。

```python
scores_df = pd.read_csv("satscores.csv")
schools_df = pd.read_csv("schools.csv")
unique_counties = pd.DataFrame(schools_df["County"].unique(), columns=["County"])
unique_counties = unique_counties.sem_map(
    "What is the population of {County} in California? Answer with only the number without commas. Respond with your best guess."
)
counties_over_2m = set()
for _, row in unique_counties.iterrows():
    try:
        if int(re.findall(r"\d+", row._map)[-1]) > 2000000:
            counties_over_2m.add(row.County)
    except:
        pass
schools_df = schools_df[schools_df["County"].isin(counties_over_2m)]
merged = pd.merge(scores_df, schools_df, left_on="cds", right_on="CDSCode")
prediction = int(merged["NumTstTakr"].sum())
```

**图 3(b)：HRA 声明式表示。**

$$
\gamma_{\mathrm{SUM}(NumTstTakr)\rightarrow total\_test\_takers}
\left(satscores\bowtie_{cds=CDSCode}
\left(\sigma_{population>2000000}
\left(\Pi_{ExtractPopulation(County)\rightarrow population}(schools)\right)\right)\right)
$$

LOTUS 使用类似 Pandas 的 `sem_map` API。用户需要指定提示、解析结果、优化执行，例如先取不同的县名来避免重复调用。但这一专家程序仍可能不是最优：先执行连接可以在昂贵的 `sem_map` 之前过滤县（Glenn，2025）。这样的过程式表达使人和模型都难以写出最优分析程序。

HRA 使用紧凑代数形式，把语义运算表示为嵌入关系算子的函数符号，例如投影中的 `ExtractPopulation`。UDF 还可以作为连接中的二元谓词，判断两个名称是否指向同一实体；或者作为聚合函数，对一组文本做总结。

**定义：LLM 用户定义函数。** 设输入关系为 $T$，$C$ 是其中一组列，$T[C]$ 表示投影。LLM UDF $U_M^l$ 用模型 $M$ 计算自然语言表达式 $l$，并由 $T[C]$ 构造提示。模型诱导概率分布 $\Pr_M(y\mid l(T[C]))$，从输出空间 $\mathcal Y$ 返回结果 $y$。

例如，`SameEntity` 输入客户表和销售表的公司名称，输出布尔值。输入 “International Business Machines” 与 “IBM” 时，UDF 返回 True；语义连接输出所有被判为相同实体的行对。

**图 4：HRA 中的 LLM UDF 语义操作示例。**

![图 4：HRA 中的 LLM UDF 语义操作示例。原论文图片](https://arxiv.org/html/2604.23477v2/LLM_UDF.png)

**表 1：HRA 算子及其语义扩展。**

| 算子 | 表示 | LLM UDF 扩展 | 执行方式 |
| --- | --- | --- | --- |
| 选择 | $\sigma_\varphi(R)$ | 用户定义选择谓词 $R\to bool$ | 对不同输入求值，过滤，再与原关系连接 |
| 投影 | $\Pi_{col_1,\ldots}(R)$；$\Pi_{f:(col_1,\ldots)\to col_{new}}(R)$ | 用户定义变换 $R\to R'$ | 对不同输入生成值映射，连接回原关系，得到新列 |
| 连接 | $L\bowtie_\varphi R$ | 用户定义连接谓词 $L\times R\to bool$ | 对连接键自适应分批，求出批次间匹配对，再连接原表 |
| TopK | $\omega_{\triangleleft(col_1,\ldots)}(R)$；$\omega_{\triangleleft_k(col_1,\ldots)}(R)$ | 用户定义两两比较 $R\times R\to bool$ | 比较不同输入行对，汇总得到排序，再连接回原关系取前 k 项 |
| 聚合 | $\gamma_{agg(col)}(R)$；$\gamma_{\mathcal G;agg(col)}(R)$ | 用户定义聚合 $R\to R_A$ | 若存在分组键则先分组，对每组调用 UDF |

选择：对每行输入列计算自然语言条件，返回 True/False，由选择谓词过滤表。

投影：对每行执行自然语言指导的变换，返回一个或多个派生值 $\langle y_1,\ldots,y_k\rangle$，形成新列。

连接：对左右关系的每对行计算 $U_M^l(t_i[C_L],t_j[C_R])$，输出返回 True 的行对。

TopK：以 $U_M^l(t_i[C],t_j[C])$ 为比较器，判断 $t_i$ 是否排在 $t_j$ 之前，得到有序输出。

聚合：对一组行计算 $U_M^l(t_1[C],\ldots,t_k[C])\to y_{agg}$，按自然语言指令生成聚合结果。

## 3. 查询生成

从自然语言自动合成 HRA 查询面临三个技术挑战：为准确选算子与选数据而编码语义模式；把问题分解成与算子代数对应的组合步骤；合成准确表达意图且可以执行的 UDF。

Sema-SQL 不要求微调，而是通过三个上下文学习组件利用 LLM 的泛化能力：语义数据模型 $\mathcal S$ 编码列含义、关系和领域约束；问题分解 $\mathcal I$ 指定每一步的算子和参数；说明与示例 $\mathcal E$ 指导生成并整合 UDF。

**图 5：HRA 查询生成的提示模板。**

```text
任务：给定以下数据库模式和用户问题，按 HRA 文法生成查询。
[数据库模式] <semantic_data_model>
[问题] <user_question>, <question_decomposition>
[说明]
- 使用 HRA 文法
- 使用 LLM UDF 时遵循 <llm_udf_instructions>
[示例] ...
```

**问题 3.1：查询生成。** 给定自然语言问题 $q$ 和关系数据库 $D$，使用模型 $M_q$ 根据上述三个组件合成：

$$
\hat\phi=\arg\max_\phi\mathbb P_{M_q}(\phi\mid q,\mathcal S,\mathcal I,\mathcal E).
$$

生成结果应满足：

1. 语法有效：$\hat\phi\in\mathcal L(\mathcal G_{HRA})$ 且 $Parse(\hat\phi,\mathcal S)\ne\bot$。解析器同时核对语法与模式一致性。
2. 语义正确：$\hat\phi(D)=\phi^*(D)$。若没有标准查询 $\phi^*$，则用人工检查或预定义测试用例确认。
3. 可执行：$Execute(\hat\phi,D)\ne\bot$，即在目标数据库上没有运行时错误。

### 3.1. 语义数据模型

LLM 需要合适的模式表示来理解数据库结构与语义。常见 DDL 定义了表与列的结构属性，却缺少表和字段的自然语言解释。因此，不少 Text-to-SQL 系统增强了模式表示，BIRD 也提供描述文件解释缩写和术语。

Sema-SQL 使用分层 YAML 语义数据模型，为用户和 LLM 提供紧凑、结构化的表示。模型由数据库元数据及描述文件自动构建，包含三部分：

**（a）表模式。** 每张表和视图包含名称、描述和列规格。每列记录：元数据中的列名；SQL 类型（如 INTEGER、VARCHAR）；三个真实样本值，展示时间等数据的格式与模式；解释列含义和主键等约束的自然语言描述。

**（b）关系。** 明确描述外键约束和连接条件，既引导 LLM 选择有效连接路径，也使系统在具有合适关系约束时优先使用高效的结构化连接，而非昂贵的语义连接。

**（c）领域说明。** 包括应用相关计算规则和派生指标公式、自然语言到模式元素的语义映射（例如收入对应价格乘数量）、技术术语与业务概念定义。它帮助模型区分专门的业务规则和一般推理；用户可补充领域知识。

**模型过滤。** 生成查询时，系统从 $\mathcal S$ 选择回答当前问题所需的子集 $\mathcal S'$，以缩小上下文并改善准确性。LLM 根据列描述与样本理解语义，用领域说明对齐问题和模式术语，并识别计算规则需要的列。保留选中列及选择过程中引用的领域说明。

除了问题中显式出现的列，还要保留用于语义推断的实体标识。例如问题要求“来自德国的球员”，数据库没有国籍列时，系统保留球员的姓与名，供模型推断。在确定相关列后，抽取连接这些列所在表所需的最小关系集合，以获得有效连接路径。

### 3.2. 问题分解

我们把复杂问题分解成与算子代数对应的结构化推理步骤。受 ReAct 启发，向 LLM 提供算子文档和语义模型，让它反复选择算子及参数，直到满足查询意图。

算子文档包含语义描述、参数限制与例子。例如语义投影说明何时需要通过 LLM 推断隐含属性、源关系与输入列及输出列参数是什么，以及何时普通投影已经足够。

第一步识别计算目标，例如计数、平均、过滤、排名或存在性检查。目标充当终止条件：只有分解结果提供了与意图一致的输出，才停止组合算子。每一步根据语义模型选择算子并说明其应用方式；对于成本明显更高的语义算子，模型还必须解释必要性，鼓励只在缺少模式内信息或超出关系代数能力时调用。

对于人口超过 200 万的县的考生总数示例，步骤为：

1. 语义投影：为 `schools` 中每个县提取人口。理由是人口未存于数据库，需要从县名推断。
2. 选择：保留人口超过 2,000,000 的结果。
3. 连接：按 `cds = CDSCode` 与 `satscores` 连接。
4. 聚合：对 `NumTstTakr` 求和。

### 3.3. 说明与示例

仅有语义模型和分解还不够，还需要设计上下文说明与例子来保证 UDF 合成及整合。

**对比提示。** UDF 的自然语言表达式必须精确捕捉意图，因为它和输入数据共同生成真正执行的提示。含糊表达可能引发错误或不可解析输出。我们提供精确与含糊表达的成对示例：`is_R1_research_university` 对比 `is_prestigious`，`extract_population` 对比 `get_info`。需要整数等特定输出类型时，明确要求表达式包含类型约束。

**端到端查询示例。** 选取五个代表性问题—查询对，兼顾覆盖与提示长度；包含 2—6 个算子、最多四张表，合计覆盖全部算子类型。同时包含比较聚合（如两表均值比较）和多个语义操作组合等复杂模式。

## 4. 查询优化

生成查询可能执行低效。我们的成本框架同时考虑 LLM 与关系运算，并以符号执行验证变换前后的等价性。首先将 HRA 查询解析为逻辑计划，核对语法以及引用的表、列是否存在。

**定义：查询计划。** $\mathcal Q=(V,E,r)$ 是有根树，$V$ 是算子节点，$E$ 是从子节点流向父节点的数据流边，$r$ 产生最终结果。每个节点是关系算子或包含 LLM UDF 的语义算子。

计划的估计执行时间为：

$$
cost(\mathcal Q)=\sum_{v\in\mathbb D}cost_{sql}(v)+\sum_{v\in\mathbb M}cost_{llm}(v),
$$

其中 $\mathbb D$ 为关系算子集合，$\mathbb M$ 为语义算子集合。令 $\mathbb P(\mathcal Q)$ 为所有与原计划语义等价的计划，则目标为：

$$
\hat{\mathcal Q}=\arg\min_{\mathcal Q'\in\mathbb P(\mathcal Q)}cost(\mathcal Q').
$$

寻找最优计划是 NP-hard。传统 DBMS 启发式没有考虑 LLM 的独特成本。例如，普通谓词下推减少中间数据，但对昂贵语义谓词下推，可能需要给每个输入行调用 LLM，反而增加成本；延迟到较小的中间结果上执行可能更好。

我们的两个观察是：成熟的关系优化仍能减少关系运算成本；合理后移 LLM UDF 可以减少待处理数据。采用两阶段策略：先进行谓词下推、连接排序等关系优化，再在已优化的关系计划骨架上选择 LLM UDF 位置。比起联合搜索全部普通算子和昂贵算子，这缩小了搜索空间。

**问题：LLM UDF 位置选择。** 给定计划和语义算子集合，找到等价且成本更低的算子位置。图 6 的问题是“2008 年马来西亚大奖赛中有多少亚洲车手？”原计划先对所有车手国籍做语义判断；后移该判断后，只对参加指定比赛的车手调用模型。

**图 6：延迟 LLM 求值的查询优化示例。**

![图 6：延迟 LLM 求值的查询优化示例。原论文图片](https://arxiv.org/html/2604.23477v2/lazy.png)

**成本模型。** 一元算子的成本为 $cost(op_T)=\beta_{op}|T|$；二元算子为 $cost(op_{L,R})=\beta_{op}f(|L|,|R|)$。$f$ 由执行算法决定。$\beta$ 为平均每元组处理成本：关系操作包括 I/O、CPU、内存访问；语义操作依据输入输出 Token 和每 Token 推理时间估计。初始系数和选择率来自工作负载采样，用户可以根据实测修正。基数估计采用标准谓词独立假设。

**算法 1：延迟 LLM 求值。** 为清晰保留原递推，伪代码去掉了排版行号。

```text
输入：查询树 Q=(V,E,r)，语义算子集合 M
输出：cost*[r,M] 与对应优化计划
按后序遍历每个节点 v：
  若 v 为叶子：cost*[v,空集] ← 访问表的成本
  遍历 v 子树语义算子集合 M_v 的子集 S：
    S_v 表示紧邻 v 下方放置的算子子集，只考虑等价的合法位置
    若 v 是一元节点，子节点 c：
      cost*[v,S] ← min_{S_v⊆S}
        (cost*[c,S\S_v] + cost_{v,S}(S_v) + cost_S(v))
    若 v 是二元节点，子节点 l,r：
      将 S 不相交地划分成 S_l,S_r,S_v，取
      cost*[v,S] ← min
        (cost*[l,S_l] + cost*[r,S_r] + cost_{v,S}(S_v) + cost_S(v))
返回 cost*[r,M] 及相应计划
```

记忆表保存以节点 $v$ 为根、包含语义算子集合 $S$ 的子计划最小成本。自底向上处理；一元节点选择哪些算子移到其下方，二元节点还要在左右子树及当前位置间分配。$cost_S(v)$ 是该子树配置下节点本身的成本，$cost_{v,S}(S_v)$ 是在其下方执行这些语义算子的成本。原文给出的最坏复杂度为 $O(k2^m)$，其中 $k$ 是计划算子数，$m$ 是语义算子数。

为验证变换等价，我们使用符号执行及 Z3 等 SMT 求解器，将 LLM UDF 视为未解释函数，而无需真正执行查询。原文脚注说明：尽管 LLM 在实践中可能随机，为代数等价验证之目的，将其视作确定函数。

仍以图 6 为例，在聚合节点处比较语义选择继续留在子树，与移到聚合前两个合法方案，选择更低成本且等价者。图 7 验证 $\sigma_{llm}(T_d)\bowtie T_r=\sigma_{llm}(T_d\bowtie T_r)$：创建含符号单元格与行存在条件的符号表，对两个顺序分别执行选择和连接，比较输出及行存在条件。等价性验证通常不可判定；求解器确认等价时才采用，超时或 unknown 则回到原计划。

**图 7：计划等价性验证。**

![图 7：计划等价性验证。原论文图片](https://arxiv.org/html/2604.23477v2/symbolic.png)

**UDF 改写。** 一些 UDF 可转换为 SQL，消除运行时 LLM 调用，适用于独立处理每行且相同输入恒有相同输出的部分选择、投影。例如判断生日是否属于水瓶座，可以合成为 `strftime('%m-%d', dob) BETWEEN '01-20' AND '02-18'`。

系统向 LLM 提供自然语言表达式、输入列描述及样本，让其判断是否无状态、确定；若是则生成可替代的关系表达式，否则保留 UDF。评估表明，这常用于与现实常量比较或按规则分类的场景。

**其他优化机会。** 模型级联可按难度使用不同规模模型；代理模型可在昂贵模型之前过滤候选；提示优化可减少 Token；提示缓存可复用共享前缀的注意力状态，尤其适合重复执行相同 UDF。这些方法与本框架正交，集成留作未来工作。

## 5. 查询执行

Sema-SQL 通过 UDF 执行器将模型推理整合进数据库执行。遇到 $U_M^l(T[C])$ 时，执行器使用算子专用模板、自然语言表达式和输入数据构建提示。例如 `isAsian(nationality)` 对各个不同国籍构造“Japanese 是否满足 isAsian？回答 yes/no”之类的提示，并行调用模型，得到 `(nationality, prediction)` 对。再按国籍连接回原表，过滤后的关系流向下一个算子。

对于去重不改变语义的选择、投影、连接与 TopK，执行前先取得不同输入，避免重复调用。各算子的执行方式见表 1。

**语义连接的智能分批。** 传统嵌套循环枚举左右表全部不同连接键对，分别调用谓词，调用复杂度为 $O(|K_1||K_2|)$，对大表成本过高。

**算法 2：嵌套循环语义连接。**

```text
输入：关系 L、R，不同连接键 K1、K2，LLM UDF
J ← 空集
对 K1 中每个 k1：
  对 K2 中每个 k2：
    若 UDF(k1,k2) 返回 True：将 (k1,k2) 加入 J
返回匹配键对集合 J
```

朴素分批把左右全部键塞入一个提示，要求一次返回所有匹配对。它适合短文本、小关系和简单任务，但在超过有效上下文、成对推理过于复杂，或输出匹配结果过多难以解析时会失败。

**算法 3：智能分批语义连接。**

```text
输入：关系 L、R，不同连接键 K1、K2，LLM UDF
J ← 空集
s ← 从 K1 抽取 3 个样本 ∪ 从 K2 抽取 3 个样本
(b1,b2) ← 模型 Mb(s, |K1|, |K2|, UDF)
B1 ← 按 b1 对 K1 分批
B2 ← 按 b2 对 K2 分批
对 B1 中每个批次 B1_i：
  对 B2 中每个批次 B2_j：
    J_ij ← 以批量提示调用一次 UDF(B1_i,B2_j)
    J ← J ∪ J_ij
返回 J
```

模型 $M_b$ 根据三个因素选择批大小：任务是简单名称相似还是复杂语义推理；样本每行文本长度；两边关系基数。简单短文本可以用 10×10 等较大批次；复杂长文本可降到 1×1。批次对调用数量为 $O(\lceil|K_1|/b_1\rceil\lceil|K_2|/b_2\rceil)$。

例如，把七种 F1 车队国籍与 32 个赛道国家语义匹配，逐对需 224 次调用。模型选择两边批大小都为 10，则得到一批和四批：四次匹配加一次批大小决策，共五次，约减少到原来的 1/45。对于复杂文本任务则选择较小批次。算法在昂贵但准确的逐对处理与高效但易错的大批处理之间权衡。

## 6. 评估

**表 2：基线系统比较。** “自动生成”指从自然语言问题自动生成查询；不是说手工系统没有任何智能能力。

| 方法 | 输入接口 | 自动生成查询 | 查询计划优化 | 语义执行能力 |
| --- | --- | --- | --- | --- |
| Text2SQL | 自然语言 | 是，但仅传统 SQL | 无 | 无 |
| HQDL | LLM 扩展表与 SQL | 否 | 无 | 仅逐行推理，不支持语义连接和聚合 |
| BlendSQL | BlendSQL 查询 | 否 | 基于规则的变换 | LLMValidate、LLMMap、LLMQA、LLMJoin |
| LOTUS | Python API | 否 | 无逻辑计划优化 | sem_filter、sem_map、sem_topk、sem_join、sem_agg |
| Palimpzest | Python API | 否 | Cascades 风格优化 | sem_filter、sem_map、sem_join、sem_agg |
| Sema-SQL | 自然语言 | 是 | 延迟求值和 UDF 改写 | 选择、投影、连接、TopK、聚合中的 LLM UDF |

实验回答五个问题：RQ1，新系统能处理哪些传统查询难以处理的能力？RQ2，自动生成含 LLM UDF 查询有多可靠，各提示组件贡献如何？RQ3，优化减少多少执行时间和 Token？RQ4，智能分批相比嵌套循环的调用与性能如何？RQ5，生成、优化和执行阶段各消耗多少成本，影响因素是什么？

### 6.1. 实验设置

#### 6.1.1. 问题语料

我们在 TAG 上评估。TAG 从 BIRD 改写问题，使其需要世界知识或文本列上的语义推理，例如给加州学校问题增加“位于湾区”条件。它覆盖五个业务域：California Schools、Debit Card Specializing、Formula One、Codebase Community、European Football。数据库最多 13 个关系，最大 597.8 MB。原 TAG 含 60 个匹配、比较和排名问题，另有 20 个自由文本摘要聚合问题。

我们做两类扩展。第一，原 TAG 只有问题与答案，没有中间推理路径，因此请三位有经验的数据库专家构建标准分析查询，以独立评估查询与答案。第二，增加原基准缺少、实际分析常见的四类推理：超越字符串相等的语义连接、模式中未有类别的语义分类、自由文本信息抽取、借助外部知识的计算推理。每类增加十题，共四十题，加入多跳、子查询和多个 LLM 调用。扩展基准称为 TAG+，总计 120 题。

#### 6.1.2. 基线

Text2SQL 使用 BIRD 提示形式和少样本例子生成传统关系 SQL。

HQDL 使用 LLM 为缺失属性补值，再对扩充表构造 SQL；我们指定目标属性，沿用其提示，为每行调用模型。

BlendSQL 扩展 SQLite，支持逐行变换、聚合和表连接。我们为每题编写专家脚本；它使用谓词下推与延迟求值等规则，而非实际成本，并通过测试集验证查询等价。

LOTUS 基于 DataFrame，提供相对于昂贵“黄金算法”具有统计精度保证的算子实现。我们为每题手写 Python 程序。为关注执行准确率，关闭以精度换效率的算子级物理优化；它不支持逻辑计划优化。

Palimpzest 同样使用 DataFrame，但通过 Cascades 风格优化器探索质量、成本和时延的 Pareto 前沿。我们为每题编写程序，设置 `max_quality`，不施加成本或时延限制。

Sema-SQL 自动生成 HRA，经延迟求值、UDF 改写和智能分批等机制执行。

#### 6.1.3. 实现细节

除 LOTUS 和 Palimpzest 使用 Pandas DataFrame 外，其余使用 SQLite3。所有系统都用 GPT-5、Claude Sonnet 4.5、Gemini 3 和开源权重模型 Qwen3-256B 评估。每题最长一小时，API 错误或不符合格式的输出最多重试三次。未特别说明时温度为零；支持并发的 BlendSQL、LOTUS、Palimpzest、Sema-SQL 均将 LLM 并发度设为十。

### 6.2. 基线评估

#### 6.2.1. 端到端查询效果

表 3 给出按各系统自然语言或代码接口运行的执行准确率和 Token。客观题以结果与标准答案一致为正确；评论摘要、主观排名等题用 GPT-5 Judge 评估是否覆盖关键信息、推理是否合理。

LOTUS、Palimpzest、Sema-SQL 的语义算子最能满足任务需求。其中只有 Sema-SQL 自动生成流水线，另外两者依赖专家构建。Sema-SQL 在 Claude Sonnet 4.5 上最好；在 GPT-5 和 Gemini 3 上与手工系统相近；Qwen3-256B 为 76.7%。虽然增加了自动生成调用，Sema-SQL 的 Token 仍与另外两者具有可比性，得益于紧凑提示、优化和分批。

LOTUS 在需要参数知识的问题上受系统提示影响，并在大连接上因嵌套循环超时。Palimpzest 搭配 Gemini 3 的聚合有时只列高层信息，没有有效总结。BlendSQL 的大批量处理增加错误，且基于 LLMMap 的排序和摘要能力不足。HQDL 对大表逐行补全成本高，补全后再查询无法利用查询优化，且缺少跨行排名、聚合与连接推理。Text2SQL 在可用关系运算表达的题上较好，但不能处理执行期需要 LLM 推断的问题。

**表 3：TAG+ 执行准确率及平均 Token。** 保留全部 24 组结果。原表的最佳标记仅比较同一模型，不代表自动方法与手工方法的人工成本相等。

| 方法 | 自动 | 模型 | 执行准确率 | 平均 Token |
| --- | --- | --- | --- | --- |
| Text2SQL | 是 | Claude 4.5 Sonnet | 32.5% | 1781.2 |
| Text2SQL | 是 | GPT-5 | 34.2% | 3076.4 |
| Text2SQL | 是 | Gemini 3 | 25.0% | 4273.8 |
| Text2SQL | 是 | Qwen3-256B | 27.5% | 1836.3 |
| HQDL | 否 | Claude 4.5 Sonnet | 13.3% | 159126.9 |
| HQDL | 否 | GPT-5 | 12.5% | 92063.3 |
| HQDL | 否 | Gemini 3 | 12.5% | 268573.7 |
| HQDL | 否 | Qwen3-256B | 11.7% | 82597.6 |
| BlendSQL | 否 | Claude 4.5 Sonnet | 68.3% | 4214.8 |
| BlendSQL | 否 | GPT-5 | 65.0% | 4206.8 |
| BlendSQL | 否 | Gemini 3 | 70.0% | 3633.3 |
| BlendSQL | 否 | Qwen3-256B | 65.8% | 3179.5 |
| LOTUS | 否 | Claude 4.5 Sonnet | 80.0% | 19686.9 |
| LOTUS | 否 | GPT-5 | 90.8%（该模型最佳） | 31833.6 |
| LOTUS | 否 | Gemini 3 | 83.3%（该模型最佳） | 46940.2 |
| LOTUS | 否 | Qwen3-256B | 82.5% | 8218.8 |
| Palimpzest | 否 | Claude 4.5 Sonnet | 85.0% | 39428.6 |
| Palimpzest | 否 | GPT-5 | 85.0% | 33939.7 |
| Palimpzest | 否 | Gemini 3 | 77.5% | 35385.3 |
| Palimpzest | 否 | Qwen3-256B | 85.0%（该模型最佳） | 41723.5 |
| Sema-SQL | 是 | Claude 4.5 Sonnet | 89.2%（该模型最佳） | 29009.0 |
| Sema-SQL | 是 | GPT-5 | 83.3% | 35125.1 |
| Sema-SQL | 是 | Gemini 3 | 81.7% | 45664.4 |
| Sema-SQL | 是 | Qwen3-256B | 76.7% | 25394.8 |

#### 6.2.2. 错误分析

**表 4：Sema-SQL 按模型能力划分的错误。**

| 能力 / 错误类型 | Claude 4.5 | GPT-5 | Gemini 3 | Qwen3-256B |
| --- | --- | --- | --- | --- |
| 指令遵循 / 语法错误 | — | 3.3% | 1.7% | 1.7% |
| 指令遵循 / 解析错误 | 1.7% | 2.5% | 1.7% | 2.5% |
| 查询理解 / 意图偏离 | 1.7% | 0.8% | 4.2% | 5.0% |
| 查询理解 / UDF 错误 | 3.3% | 2.5% | 4.2% | 4.2% |
| 查询理解 / 关系逻辑错误 | — | 1.7% | — | 0.8% |
| 参数知识 / 事实错误 | 4.1% | 5.8% | 6.6% | 9.1% |
| 全部错误 | 10.8% | 16.7% | 18.3% | 23.3% |

指令遵循错误占 1.7%—5.8%。语法类含字段幻觉或无效 UDF，解析类指未产生正确结构的输出。Claude 最少，GPT-5 最多。

查询理解错误占 5.0%—10.0%。意图偏离例如数错对象或漏过滤；UDF 错误例如输入列选择或表达操作不对；关系错误涉及条件或连接。Qwen3-256B 的 10.0% 最高，作者认为任务微调可能有帮助。

参数知识错误占 4.1%—9.1%，反映世界知识缺口及推断质量。Qwen3-256B 的 9.1% 约为 Claude 的 2.2 倍，作者提出用检索增强或领域继续预训练改进。

### 6.3. Sema-SQL 性能分析

#### 6.3.1. 查询生成准确性

按问题 3.1 的语法、语义和可执行性评价，其中语义以生成查询与标准查询的执行结果比较。所有模型的查询生成准确率均超过 85%，Claude 4.5 Sonnet 最高 93.3%，Qwen3-256B 为 85.8%。解析器发现字段幻觉和解析失败，UDF 执行器发现类型/值不匹配等运行错误；错误消息被反馈用于有上限的重试。剩余多为意图理解歧义，提示可继续改进消歧和模式落地。

**图 8：查询生成准确率。**

![图 8：查询生成准确率，原论文图片](https://arxiv.org/html/2604.23477v2/piechart_reliability.png)

#### 6.3.2. 提示组件消融

我们用最好和最弱的两个模型，消融语义数据模型、问题分解与上下文示例。Qwen3-256B 最依赖数据库表示：移除语义模型表示（改用 BIRD 默认模式形式），或移除模型过滤，准确率各下降 24.2%。作者将其部分归因于较短有效上下文（约 32K）和较弱能力。缺少这些组件时，字段幻觉与算子误用增加。

Claude 最受益于上下文示例。问题分解对两个模型都重要：直接从问题映射到 HRA 容易漏计算步骤或选错语义算子，说明显式分解和详细算子文档的价值。

**图 9：查询生成组件消融。**

![图 9：查询生成组件消融，原论文图片](https://arxiv.org/html/2604.23477v2/combined_ablation_study.svg)

#### 6.3.3. 查询优化效果

120 条查询中有 33 条计划被优化，其余已经合适或含无法改写的 UDF。在 Claude 下，这些查询的平均时间从 62.9 秒降为 45.1 秒，下降 28%；平均 Token 从 31.5K 降为 25.0K，下降 21%。

延迟求值通过缩小输入减少调用。例如图 6 对应查询从 73 行降到 42 行。另一个同时含语义选择和语义连接的查询，则把选择放在连接之前，因为前者选择性更高且单行成本更低。

UDF 改写提供额外收益。判断县是否属于湾区的语义选择原本要 57 次调用；改写后变为 `County IN ('Alameda', 'Contra Costa', 'Marin', 'San Francisco', 'San Mateo', 'Santa Clara', 'Santa Cruz', 'Solano', 'Sonoma')`，在执行阶段消除这 57 次模型调用。

**图 10：有无查询优化的时间和 Token 对比。**

![图 10：有无查询优化的时间和 Token 对比，原论文图片](https://arxiv.org/html/2604.23477v2/boxplot_combined.svg)

#### 6.3.4. 语义连接的智能分批

在十条连接查询、Claude 4.5 Sonnet 设置上，智能分批相对嵌套循环将调用减少 93.3%，执行准确率维持 100%；其他模型表现类似。图中 `[L:R]` 表示每次处理左右两边多少条记录。

国籍—国家、队伍—国家等短上下文简单匹配使用大批次，部分任务一次处理整表，成本最多减少约两个数量级。帖子—评论、评论—标签等复杂推理使用小批次甚至逐条处理，避免朴素分批的精度退化。中等复杂度任务根据上下文和难度调整批大小。

第十条连接含一千多对比较，暴露嵌套循环的扩展性问题：LOTUS 超时，Palimpzest 有较高执行开销，而智能分批能够完成。

**图 11：语义连接算法对比。**

![图 11：语义连接算法对比，原论文图片](https://arxiv.org/html/2604.23477v2/llm_calls_comparison.svg)

#### 6.3.5. 成本分析

每题平均消耗 25K—46K Token。作者概括生成约占 60%—75%，执行约占 20%—35%，优化仅约 3%—8%。生成需要处理完整语义模型，随模式规模上升；13 张关系的欧洲足球数据库成本约为五张关系的借记卡数据库的 4.9 倍。优化主要分析 UDF 特性和根据样本合成 SQL，平均约两千 Token 以下；执行成本与数据量和文本上下文相关。

**表 5：每题各阶段平均 Token。**

| 阶段 | Claude Sonnet 4.5 | GPT-5 | Gemini 3 | Qwen3-256B |
| --- | --- | --- | --- | --- |
| 查询生成 | 18331.9 | 20813.4 | 25021.1 | 16774.4 |
| 查询优化 | 1609.0 | 2014.7 | 1347.2 | 1333.1 |
| 查询执行 | 9068.1 | 12297.0 | 19296.1 | 7287.3 |
| 合计 | 29009.0 | 35125.1 | 45664.4 | 25394.8 |

## 7. 相关工作

**混合问答。** 混合问答处理结构化和非结构化数据。LLM 擅长语义处理，却不保证精确运算的正确性；SQL 高效且可验证，却难以处理歧义和跨异构上下文推理。混合系统连接关系数据、自由文本、模型知识或知识库。表格 RAG 和多跳检索有所进展，但仍偏向逐项检索和简单过滤。本文研究需要协调关系运算与 LLM 推理的更丰富查询。

**语义算子系统。** 商业 DBMS 开始支持 SQL 执行中的模型推理；学术系统则通过声明式 API 扩展查询语言。BINDER 为 SQL、Python 提供模型推理接口；BlendSQL 以 SQLite 扩展支持多表推理。ZenDB、EVAPORATE、Galois、HQDL 将非结构化或半结构化资料提取为关系形式；SUQL 在 SQL 中加入自由文本总结与对话问答。

DocETL、Aryn、LOTUS、Palimpzest 和 ThalamusDB 为非结构化 AI 分析提供声明式算子，将抽取、分类、变换和连接等 LLM 操作纳入数据流水线。多数仍需人工组合查询；少数尝试自动合成的工作，支持算子类型或端到端覆盖有限。Sema-SQL 对关系与语义复合查询自动完成生成、优化和执行。

**语义查询优化。** 现有方案分四类：

1. 代理执行优化。LOTUS 用便宜方法近似昂贵的黄金算子，其他工作在昂贵 UDF 前加轻量代理过滤。但用户仍需手写计划，其连接顺序和算子位置会影响成本。
2. 固定规则。无论数据特点如何，都应用下推或延迟规则，可能遗漏机会，或在某些场景并不最优。
3. LLM 逻辑改写。DocETL 用 Agent 改写和验证，Aryn 经 Luna 生成计划并由人检查，Nirvana 用自然语言规则和成本感知物理优化选择模型。由于 LLM 不可靠，仍需额外验证。
4. 成本优化。Palimpzest 的 Abacus 通过采样估计成本、延迟和质量，以 Pareto 优化平衡目标。Sema-SQL 则先利用成熟 DBMS 优化，再在较易处理的搜索空间中放置昂贵 UDF。

## 8. 结论

本文提出 Sema-SQL，自动将自然语言问题转成结合关系运算和 LLM 语义推理的高效查询。HRA 以 LLM UDF 扩展关系代数。系统形成端到端流水线：上下文学习生成查询，纳入昂贵 LLM 调用的成本优化，以及包含智能分批连接的高效执行。实验表明，它相对基线显著扩展了查询能力。

## 参考文献（保留原文）

以下由本地原始 HTML 提取，保留 60 条书目信息，去除网页“Cited by”回链以便阅读。个别原始 URL 的拼写按作者文献表保留，并非译者逐条核验过的外部链接。

 1. S. Abiteboul, R. Hull, and V. Vianu (1995) Foundations of databases . Addison-Wesley .
 2. E. Anderson, J. Fritz, A. Lee, B. Li, M. Lindblad, H. Lindeman, A. Meyer, P. Parmar, T. Ranade, M. A. Shah, B. Sowell, D. Tecuci, V. Thapliyal, and M. Welsh (2024) The design of an llm-powered unstructured analytics system . CoRR abs/2409.00847 .
 3. Anthropic (2025) Introducing claude sonnet 4.5 . Note: https://www.anthropic.com/news/claude-sonnet-4-5 Model identifier: claude-sonnet-4-5-20250929. Accessed: 2026-01-03
 4. S. Arora, B. Yang, S. Eyuboglu, A. Narayan, A. Hojel, I. Trummer, and C. Ré (2023) Language models enable simple systems for generating structured views of heterogeneous data lakes . Proc. VLDB Endow. 17 ( 2 ), pp. 92–105 .
 5. B. Bamiduro and A. Challa Large language models for sentiment analysis with amazon redshift ml (preview). . Note: https://aws.amazon.com/blogs/big-data/large-language-models/-for-sentiment-analysis-with-amazon-redshift-ml-preview/
 6. A. Biswal, L. Patel, S. Jha, A. Kamsetty, S. Liu, J. E. Gonzalez, C. Guestrin, and M. Zaharia (2024) Text2SQL is not enough: unifying AI and databases with TAG . CoRR abs/2408.14717 .
 7. S. Chaudhuri and K. Shim (1996) Optimization of queries with user-defined predicates . In VLDB’96, Proceedings of 22th International Conference on Very Large Data Bases, September 3-6, 1996, Mumbai (Bombay), India , pp. 87–98 .
 8. P. B. Chen, Y. Zhang, and D. Roth (2024) Is table retrieval a solved problem? exploring join-aware multi-table retrieval . In Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers), ACL 2024, Bangkok, Thailand, August 11-16, 2024 , pp. 2687–2699 .
 9. W. Chen, H. Zha, Z. Chen, W. Xiong, H. Wang, and W. Y. Wang (2020) HybridQA: A dataset of multi-hop question answering over tabular and textual data . In Findings of the Association for Computational Linguistics: EMNLP 2020, Online Event, 16-20 November 2020 , Findings of ACL , Vol. EMNLP 2020 , pp. 1026–1036 .
 10. Z. Cheng, T. Xie, P. Shi, C. Li, R. Nadkarni, Y. Hu, C. Xiong, D. Radev, M. Ostendorf, L. Zettlemoyer, N. A. Smith, and T. Yu (2023) Binding language models in symbolic languages . In The Eleventh International Conference on Learning Representations, ICLR 2023, Kigali, Rwanda, May 1-5, 2023 ,
 11. V. Christophides, V. Efthymiou, T. Palpanas, G. Papadakis, and K. Stefanidis (2021) An overview of end-to-end entity resolution for big data . ACM Comput. Surv. 53 ( 6 ), pp. 127:1–127:42 .
 12. S. Chu, D. Li, C. Wang, A. Cheung, and D. Suciu (2017) Demonstration of the cosette automated SQL prover . In Proceedings of the 2017 ACM International Conference on Management of Data, SIGMOD Conference 2017, Chicago, IL, USA, May 14-19, 2017 , pp. 1591–1594 .
 13. Databricks AI functions on databricks. . Note: https://docs.databricks.com/en/index.html
 14. L. De Moura N. Bjørner et al. (2008) Z3 theorem prover . Microsoft Research . Note: Version 4.x External Links: Link
 15. G. DeepMind (2025) Gemini 3: introducing the latest gemini ai model from google . Note: https://blog.google/products/gemini/gemini-3/ Accessed: 2026-01-03
 16. Y. Gao, Y. Liu, X. Li, X. Shi, Y. Zhu, Y. Wang, S. Li, W. Li, Y. Hong, Z. Luo, J. Gao, L. Mou, and Y. Li (2024) XiYan-sql: A multi-generator ensemble framework for text-to-sql . CoRR abs/2411.08599 .
 17. I. Gim, G. Chen, S. Lee, N. Sarda, A. Khandelwal, and L. Zhong (2024) Prompt cache: modular attention reuse for low-latency inference . In Proceedings of the Seventh Annual Conference on Machine Learning and Systems, MLSys 2024, Santa Clara, CA, USA, May 13-16, 2024 , P. B. Gibbons, G. Pekhimenko, and C. D. Sa (Eds.) ,
 18. P. Glenn, P. Dakle, L. Wang, and P. Raghavan (2024) BlendSQL: A scalable dialect for unifying hybrid question answering in relational algebra . In Findings of the Association for Computational Linguistics, ACL 2024, Bangkok, Thailand and virtual meeting, August 11-16, 2024 , L. Ku, A. Martins, and V. Srikumar (Eds.) , pp. 453–466 .
 19. P. Glenn (2025) Language models, SQL, and types, oh my! . Note: https://parkervg.github.io/misc/2025/05/05/sql-llms.html Blog post
 20. Google BigFrames ai operator tutorial . Note: http://github.com/googleapis/python-bigquery-dataframes/blob/main/notebooks/experimental/ai_operators.ipynb
 21. Y. He, K. Ganjam, and X. Chu (2015) SEMA-JOIN: joining semantically-related tables using big table corpora . Proc. VLDB Endow. 8 ( 12 ), pp. 1358–1369 .
 22. J. Herzig, T. Müller, S. Krichene, and J. M. Eisenschlos (2021) Open domain question answering over tables via dense retrieval . In Proceedings of the 2021 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies, NAACL-HLT 2021, Online, June 6-11, 2021 , pp. 512–519 .
 23. S. Jo and I. Trummer (2024) ThalamusDB: approximate query processing on multi-modal data . Proc. ACM Manag. Data 2 ( 3 ), pp. 186 .
 24. J. Juravsky, B. C. A. Brown, R. Ehrlich, D. Y. Fu, C. Ré, and A. Mirhoseini (2024) Hydragen: high-throughput LLM inference with shared prefixes . CoRR abs/2402.05099 .
 25. D. Kang, E. Gan, P. Bailis, T. Hashimoto, and M. Zaharia (2020) Approximate selection with guarantees using proxies . Proc. VLDB Endow. 13 ( 11 ), pp. 1990–2003 . External Links: Link
 26. H. Köpcke and E. Rahm (2010) Frameworks for entity matching: A comparison . Data Knowl. Eng. 69 ( 2 ), pp. 197–210 .
 27. W. Kwon, Z. Li, S. Zhuang, Y. Sheng, L. Zheng, C. H. Yu, J. Gonzalez, H. Zhang, and I. Stoica (2023) Efficient memory management for large language model serving with pagedattention . In Proceedings of the 29th Symposium on Operating Systems Principles, SOSP 2023, Koblenz, Germany, October 23-26, 2023 , J. Flinn, M. I. Seltzer, P. Druschel, A. Kaufmann, and J. Mace (Eds.) , pp. 611–626 .
 28. J. Li, B. Hui, G. Qu, J. Yang, B. Li, B. Li, B. Wang, B. Qin, R. Geng, N. Huo, X. Zhou, C. Ma, G. Li, K. C. Chang, F. Huang, R. Cheng, and Y. Li (2023) Can LLM already serve as A database interface? A big bench for large-scale database grounded text-to-sqls . In Advances in Neural Information Processing Systems 36: Annual Conference on Neural Information Processing Systems 2023, NeurIPS 2023, New Orleans, LA, USA, December 10 - 16, 2023 ,
 29. Y. Lin, M. Hulsebos, R. Ma, S. Shankar, S. Zeighami, A. G. Parameswaran, and E. Wu (2024) Towards accurate and efficient document analytics with large language models . CoRR abs/2405.04674 .
 30. C. Liu, M. Russo, M. Cafarella, L. Cao, P. B. Chen, Z. Chen, M. Franklin, T. Kraska, S. Madden, R. Shahout, et al. (2025) Palimpzest: optimizing ai-powered analytics with declarative query processing . In Proceedings of the Conference on Innovative Database Research (CIDR) , pp. 2 .
 31. C. Liu, M. Russo, M. J. Cafarella, L. Cao, P. B. Chen, Z. Chen, M. J. Franklin, T. Kraska, S. Madden, and G. Vitagliano (2024) A declarative system for optimizing AI workloads . CoRR abs/2405.14696 .
 32. C. Liu, G. Vitagliano, B. Rose, M. Printz, D. A. Samson, and M. Cafarella (2025) PalimpChat: declarative and interactive ai analytics . In Companion of the 2025 International Conference on Management of Data , pp. 183–186 .
 33. S. Liu, J. Xu, W. Tjangnaka, S. J. Semnani, C. J. Yu, and M. Lam (2024) SUQL: conversational search over structured and unstructured data with large language models . In Findings of the Association for Computational Linguistics: NAACL 2024, Mexico City, Mexico, June 16-21, 2024 , pp. 4535–4555 .
 34. S. Liu, A. Biswal, A. Cheng, X. Mo, S. Cao, J. E. Gonzalez, I. Stoica, and M. Zaharia (2024) Optimizing LLM queries in relational workloads . CoRR abs/2403.05821 .
 35. Microsoft (2023) Uninterpreted functions and constants . Note: https://microsoft.github.io/z3guide/docs/logic/Uninterpreted-functions-andconstants/ Z3 Guide
 36. OpenAI (2025) GPT-5 . Note: https://openai.com/index/introducing-gpt-5/ Accessed: 2026-01-03
 37. L. Patel, S. Jha, M. Pan, H. Gupta, P. Asawa, C. Guestrin, and M. Zaharia (2025) Semantic operators and their optimization: enabling llm-based data processing with accuracy guarantees in lotus . Proceedings of the VLDB Endowment 18 ( 11 ), pp. 4171–4184 .
 38. PostgreSQL Global Development Group (2015) Using explain . PostgreSQL Global Development Group . Note: PostgreSQL Documentation, Version 9.0 External Links: Link
 39. M. Pourreza, H. Li, R. Sun, Y. Chung, S. Talaei, G. T. Kakkar, Y. Gan, A. Saberi, F. Ozcan, and S. Ö. Arik (2025) CHASE-SQL: multi-path reasoning and preference optimized candidate selection in text-to-sql . In The Thirteenth International Conference on Learning Representations, ICLR 2025, Singapore, April 24-28, 2025 ,
 40. M. Pourreza and D. Rafiei (2023) DIN-SQL: decomposed in-context learning of text-to-sql with self-correction . In Advances in Neural Information Processing Systems 36: Annual Conference on Neural Information Processing Systems 2023, NeurIPS 2023, New Orleans, LA, USA, December 10 - 16, 2023 ,
 41. M. Russo, S. Sudhir, G. Vitagliano, C. Liu, T. Kraska, S. Madden, and M. J. Cafarella (2025) Abacus: A cost-based optimizer for semantic operator systems . CoRR abs/2505.14661 .
 42. M. Saeed, N. D. Cao, and P. Papotti (2024) Querying large language models with SQL . In Proceedings 27th International Conference on Extending Database Technology, EDBT 2024, Paestum, Italy, March 25 - March 28 , pp. 365–372 .
 43. M. Schlaipfer, K. Rajan, A. Lal, and M. Samak (2017) Optimizing big-data queries using program synthesis . In Proceedings of the 26th Symposium on Operating Systems Principles, Shanghai, China, October 28-31, 2017 , pp. 631–646 .
 44. P. G. Selinger, M. M. Astrahan, D. D. Chamberlin, R. A. Lorie, and T. G. Price (1979) Access path selection in a relational database management system . In Proceedings of the 1979 ACM SIGMOD International Conference on Management of Data, Boston, Massachusetts, USA, May 30 - June 1 , pp. 23–34 .
 45. S. Shankar, T. Chambers, T. Shah, A. G. Parameswaran, and E. Wu (2025) DocETL: agentic query rewriting and evaluation for complex document processing . Proc. VLDB Endow. 18 ( 9 ), pp. 3035–3048 .
 46. Snowflake Large language model (llm) functions (snowflake cortex) | snowflake documentation. . Note: https://docs.snowflake.com/user-guide/snowflake-cortex/aisql
 47. A. Sukumaran LLM with vertex ai only using sql queries in bigquery . Note: https://cloud.google.com/blog/products/ai-machine-learning/llm-with-vertex-ai-only-using-sql-queries-in-bigquery
 48. J. Sun, G. Li, P. Zhou, Y. Ma, J. Xu, and Y. Li (2025) AgenticData: an agentic data analytics system for heterogeneous data . CoRR abs/2508.05002 .
 49. S. Talaei, M. Pourreza, Y. Chang, A. Mirhoseini, and A. Saberi (2024) CHESS: contextual harnessing for efficient SQL synthesis . CoRR abs/2405.16755 .
 50. Q. Team (2025) Qwen3 technical report . arXiv preprint arXiv:2505.09388 .
 51. M. Veanes, P. Grigorenko, P. de Halleux, and N. Tillmann (2009) Symbolic query exploration . In Formal Methods and Software Engineering, 11th International Conference on Formal Engineering Methods, ICFEM 2009, Rio de Janeiro, Brazil, December 9-12, 2009. Proceedings , Lecture Notes in Computer Science , Vol. 5885 , pp. 49–68 .
 52. B. Wang, C. Ren, J. Yang, X. Liang, J. Bai, L. Chai, Z. Yan, Q. Zhang, D. Yin, X. Sun, and Z. Li (2025) MAC-SQL: A multi-agent collaborative framework for text-to-sql . In Proceedings of the 31st International Conference on Computational Linguistics, COLING 2025, Abu Dhabi, UAE, January 19-24, 2025 , pp. 540–557 .
 53. S. Wu, S. Zhao, M. Yasunaga, K. Huang, K. Cao, Q. Huang, V. N. Ioannidis, K. Subbian, J. Y. Zou, and J. Leskovec (2024) STaRK: benchmarking LLM retrieval on textual and relational knowledge bases . In Advances in Neural Information Processing Systems 38: Annual Conference on Neural Information Processing Systems 2024, NeurIPS 2024, Vancouver, BC, Canada, December 10 - 15, 2024 ,
 54. C. Yan, Y. Lin, and Y. He (2023) Predicate pushdown for data science pipelines . Proc. ACM Manag. Data 1 ( 2 ), pp. 136:1–136:28 .
 55. Z. Yang, Z. Wang, Y. Huang, Y. Lu, C. Li, and X. S. Wang (2022) Optimizing machine learning inference queries with correlative proxy models . Proc. VLDB Endow. 15 ( 10 ), pp. 2032–2044 .
 56. S. Yao, J. Zhao, D. Yu, N. Du, I. Shafran, K. Narasimhan, and Y. Cao (2023) ReAct: synergizing reasoning and acting in language models . In International Conference on Learning Representations (ICLR) ,
 57. T. Yu, R. Zhang, K. Yang, M. Yasunaga, D. Wang, Z. Li, J. Ma, I. Li, Q. Yao, S. Roman, Z. Zhang, and D. R. Radev (2018) Spider: A large-scale human-labeled dataset for complex and cross-domain semantic parsing and text-to-sql task . In Proceedings of the 2018 Conference on Empirical Methods in Natural Language Processing, Brussels, Belgium, October 31 - November 4, 2018 , pp. 3911–3921 .
 58. M. Yue, J. Zhao, M. Zhang, L. Du, and Z. Yao (2023) Large language model cascades with mixture of thoughts representations for cost-efficient reasoning . CoRR abs/2310.03094 . External Links: Link , Document , 2310.03094
 59. F. Zhao, D. Agrawal, and A. E. Abbadi (2024) Hybrid querying over relational databases and large language models . CoRR abs/2408.00884 .
 60. J. Zhu, L. Chen, X. Ke, Z. Fang, T. Li, Y. Gao, and C. S. Jensen (2025) Beyond relational: semantic-aware multi-modal analytics with llm-native query optimization . External Links: 2511.19830 , Link


---

来源：[arXiv:2604.23477v2](https://arxiv.org/abs/2604.23477v2)，2026-05-14；[英文全文](https://arxiv.org/html/2604.23477v2)。原作者及单位见篇首。原文与本非官方中文改编采用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。版本、源码核验和实验口径见[独立附录](论文与产品-核验附录.md)。

[三篇论文解读](论文三篇-问题方法验证与DataAgent学习解读.md) · [返回资料入口](README.md)
