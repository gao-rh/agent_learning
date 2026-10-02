# 澄清实验入口与准备说明

> 2026-09-30 · 十二例查数与四组知识对照已运行。当前先看[最新测试报告](../../测试报告-v2-2026-10-02-02-48-37.md)；以下是 9 月 30 日历史结果：查数八例完整通过、四例未通过；知识可检索不等于模型实际检索。原十例中的两个业务别名场景已测，其余八例尚未独立实跑。实验知识与原网页隔离。

看完整案例请打开[固定案例查看器](http://127.0.0.1:8788/)：支持多轮对话、实际调用流程、条件差异和 Token；[启动及复用说明](../case_viewer/README.md)。新增同格式实验后刷新即可，不需要重新生成网页。

新增复杂实验：[四例基线与字段提示对照](首次试跑结果.md#complex-20260930) · [复杂实验固定入口](../complex_lab/README.md) · [最新报告阅读页](http://127.0.0.1:8770/)。十类计划中本次只实现并测试了四类，其余六类见报告覆盖表。

先读[案例与知识手册](案例与知识手册.md)：它列出十个场景的前文、提问、固定回复、预期任务，以及本轮补充的全部指标、维度和定义。研究范围及来源见[原实验计划](/Users/gaoronghui/Documents/agent_learning/2-进行中/Data-Agent领域研究/记录/2026-09-29-澄清阶段实验计划与交接.md)。

新增审阅材料：[简单查询与多轮追问测试集](简单查询与多轮追问测试集.md)。补充漏指标、漏维度、误判指标、误判维度、澄清补充、查询后追问六类，每类两例，共十二例；测试集已完成离线资料校验；另有 `query_smoke` 入口接通十二例的模拟取数与真实会话续轮，不通过下面的旧 `run/resume` 命令运行。

## 原十例纯澄清入口：准备内容

| 内容 | 数量与作用 |
| --- | --- |
| 固定实验场景 | 10 个：4 个不该问、5 个需要问、1 个能力不支持 |
| 指标目录 | 12 个；包含总保费/净保费、三种渗透率、有效活跃总体、两种加入事件、曝光和订单 |
| 维度目录 | 12 个维度，各有完整模拟枚举；每指标允许的集合不同 |
| 业务知识 | 7 条基础定义 + 1 条仅对有定义组开放的映射 |
| 人工评审材料 | 固定回复、标准任务、问句应覆盖的问题、禁止行为，单独保存 |
| 实验入口 | 离线检查、列举场景、导出实际输入预览、显式开启的单例实模、固定对话续轮、结构比对 |
| 输出 | 原始工具轨迹、模型提交、程序校验、转换差异、Token、版本指纹和可读 Trace |

知识文件没有业务数值。原十例纯澄清入口只测任务条件；查询实验另建商户、订单汇总桶和加入事件三张合成表，由 SQL 实际计算。所有业务定义和数值都明确标注为模拟，不升格为公司口径。

## 实验设计中的三个重点

**同题知识对照。** “要下沉的”在两组中使用完全相同的提问和前文。指标目录、维度、工具描述、系统提示和提交结构都一致，只切换一条可检索知识。无定义组不存在隐藏别名；有定义组必须实际检索到映射，不能用“库里有”证明已经使用。

**模型答案与程序处理分开。** `model_submissions` 保存模型原始提交，`resolver_result` 保存原 v5 检索约束处理后的结果，`validation` 保存实验契约检查。例如模型提交 ready，但代码发现不支持的筛选并改成澄清，这不能记作模型正确判断。校验器只规范日期、检查目录约束，不根据标准答案填指标、补条件或修改比较期。`valid <> 0` 缺失就报错，不偷偷补上。

**不让固定用户回复掩盖漏问。** 实模首轮结束后先由人看问句。如果只问到指标、没有问时间，不能立即把包含两项的完整固定回复送进去，然后宣称一次问清。程序不自动模拟用户，也不自动给整个案例打“通过”。

“多指标作用域”场景将前文明确设为讨论中的候选口径，避免原本已经确认的条件又被人为要求澄清。允许合理的等价问法；能力不足时说明限制并询问替代方案，也可合理，不单凭 `clarify/unsupported` 的枚举名判错。

## 哪些内容由模型看到

| 层 | 保存位置 | 是否进入模型 |
| --- | --- | --- |
| 问题和允许的前文 | [cases.json](fixtures/cases.json) | 只选 question/history，去掉案例标题、分组名和来源标签 |
| 指标、维度、枚举、必选规则 | [catalog.json](fixtures/catalog.json) | 通过只读工具按需返回 |
| 基础业务定义 | [knowledge.json](fixtures/knowledge.json) | 通过业务知识工具返回 |
| 对照组映射 | [knowledge_with_definition.json](fixtures/knowledge_with_definition.json) | 仅有定义组可检索 |
| 标准任务、固定回复、判定规则 | [rubrics.private.json](fixtures/rubrics.private.json) | 不进入模型；仅离线资料检查和人工评审器读取 |
| 这份手册及案例手册 | Markdown | 含预期结果，不整篇放入模型上下文 |

可用工具只有五个：搜索指标、读取指标定义、搜索维度、搜索枚举、搜索业务知识。`finish_resolution` 是提交结构化决定的通道。没有查询、分析、认证或报告工具；尝试调用越界工具会记录并拒绝，不能真的执行。

## 相对原 v5 做了哪些最小调整

1. `ParallelModel.resolve` 增加可选的按调用注入参数：工具、目录、Prompt、输出结构和专题提示入口。原网页不传这些参数，继续使用原配置，不修改全局目录。
2. 实验扩展 `comparison_period`，用于记录用户确认的自选基期；扩展 `required_predicates`，用于显式保存定义中的非枚举规则。
3. 增加 `missing_items` 和 `knowledge_refs`，分别记录缺项归属及实际使用的知识；不要求模型输出内部思维链。
4. 只调整实验 Prompt 中与下游执行能力冲突的声明，并追加语义提交规则。原版 Prompt 保留不变。

因此，使用这条路径的基线应标为 **“v5 工具循环 + 隔离知识 + 实验语义契约”基线**，不能宣称是未经修改的原 v5 效果。知识对照组之间再保持这个组合完全一致。

扩展字段不会被正式查询器执行。实验的 `accepted=true` 表示当前语义结构合法，不表示原网页已经支持这些查询或比较。

## 不付费就能先做的检查

以下命令均在[实验根目录](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现)执行，使用现有虚拟环境，无需重新安装依赖。

```bash
cd '/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现'
.venv/bin/python -m business_analysis_repro.clarification_lab check
.venv/bin/python -m business_analysis_repro.clarification_lab list
```

导出某一场景的输入预览，不加载模型 Key，也不发请求：

```bash
.venv/bin/python -m business_analysis_repro.clarification_lab preview alias_unknown --output /tmp/clarification-preview.json
```

文件已存在时拒绝覆盖。预览中 `sent_to_model_on_first_call` 是首轮输入，`available_via_tools_not_automatically_sent` 是工具可查知识，两者分开，不能把整个预览文件直接发送给模型。

无网络离线测试：

```bash
.venv/bin/python -m pytest tests/test_clarification_lab.py -q
```

修改固定资料后，可以重建人读手册：

```bash
.venv/bin/python -m business_analysis_repro.clarification_lab.build_handbook
```

## 后续怎样跑一个真实案例

原十例已有两个别名场景运行；其他八例尚未执行。运行前需要先确认案例和实际模型配置，估算输入/输出 Token 与当前价格；不能把公开预览字符数当成供应商精确 Token 计数。

```bash
.venv/bin/python -m business_analysis_repro.clarification_lab run missing_slots --live
```

不带 `--live` 会拒绝。默认每案例最多 8 次模型请求，可用 `--max-calls` 明确设置（当前上限 20）；包含工具循环、重试和第二轮；当前模型参数沿用 v5，实际模型名与用量记录在输出和 Trace。命令返回独立运行目录。

先审阅首轮问题。确实问到必要缺项时，再把打印出来的真实目录填入下面命令：

```bash
.venv/bin/python -m business_analysis_repro.clarification_lab resume '<实际运行目录>' --live --question-reviewed --reply '放心吃餐饮订单渗透率，上周，整体看。'
.venv/bin/python -m business_analysis_repro.clarification_lab review '<实际运行目录>'
```

首轮诊断最多两次助手响应。需要更多轮次时记录现状并设计追加实验，不在原记录中无限试到成功。续轮保留原问题、原前文、实际澄清问题和用户回复；不自动混入其他案例的摘要或记忆。代码、知识、案例、依赖版本或模型变化时不能混在同一场实验里恢复。

这里的续轮是**实验运行器的固定对话回放**，不是在业务父图里执行到取数前再强行中断，也不是网页的消息队列或 LangGraph checkpoint 恢复测试。这个阶段刻意不进入业务父图，避免误取数。端到端网页暂停/恢复另测。

当前只提供单例入口，不自动批量运行十个案例，也没有跨独立运行目录的总预算仲裁。原计划的首轮总计 60 次请求需要后续批次执行器控制，不能把“每例最多 8 次”误称为“十例合计最多 60 次”。准备阶段不启动这批调用。

## 输出如何读

| 文件 | 看什么 |
| --- | --- |
| `trace.jsonl` | 实际模型输入、工具参数/返回、模型请求和响应、错误、停止边界 |
| `trace.html` | 现有可读 Trace 页；用浏览器打开；实验提交细节以 JSONL 与 turn 文件为准 |
| `turn-1.json`、`turn-2.json` | 模型原始提交、resolve 处理结果、实验契约检查三层；日期变化、本轮实际知识返回 |
| `session.json` | 该案例的固定输入、已发生对话、调用上限和版本，用于单例续轮 |
| `review-1.json` 等 | 与人工标准的结构比对，最终等级始终先标 `pending_human_review` |

日志中的替身 Token 只用于离线计数机制测试，不能当作真实 Kimi 消耗。真实运行发生错误且未返回 usage 时，标记统计不完整，不能当成免费。取消、执行稳定性、业务数值准确率、SQL 质量均不在本阶段判分范围。

## 准备阶段的离线验证与边界（历史记录）

- 资料检查通过：10 个场景、12 个指标、12 个维度、7+1 条知识；标准任务能被实验契约表达。
- 新增 18 项离线测试通过：禁网络、知识对照隔离、标准答案不进入输入、预览与实际输入一致、真实 resolve 循环、模型原始提交与程序拦截区分、条件继承、比较方向、必选规则、越界调用、累计预算、输出产物与重复调用保护等。
- 原有并行/聊天流式相关 24 项回归通过，使用模型替身。初次运行受沙箱本机端口和缺少 tokenizer 词表缓存影响；允许本机测试端口及公开词表下载后通过，没有调用模型 API。
- 原网页的知识目录没有切换，也没有重启当前 8787 服务；这套资料已接到独立实验入口。
- 未做真实模型基线，不能宣称“十个场景全过”或“澄清效果提升”。仍需审阅问句、记录首次偏差，再决定单项改进。

本轮没有建立向量库、模拟用户 Agent、公司平台连接或新产品工程。对本阶段而言，知识定义能被实际读取、任务条件能被完整表达和检查，是优先验证的三件事。

## 简单查数补充集的离线检查

```bash
.venv/bin/python -m business_analysis_repro.clarification_lab.simple_query_suite
```

该命令只验证十二例、二十轮输入及十八轮查数任务的标准条件是否与知识目录一致，不请求模型。初步运行安排为每例一次，先选“澄清日期后保留范围”和“查完后新增、替换、撤销条件”两例各一次；其余用例与第二次重复按诊断需要决定。新旧测试集不默认合并批跑，旧方案预算也不自动扩展到新用例。

## 简单查数入口：首批实跑与复现（9月29日记录）

已执行结果见[首次试跑报告](首次试跑结果.md)。本次 5 轮用户输入、28 次模型请求、4 次本地 SQL；两条多轮用例均未完整通过。查错月份、检索证据未补齐和实验校验器误拒绝分别归因，没有合成通过率。新增 6 项运行器测试与原 18 项实验测试合计 24 项通过。

`query_runtime.py` 复用实际 ChatStore、ContextMemory、v5 resolve，并使用独立 LangGraph/SQLite checkpoint；理解后由代码调用本地模拟查询。没有复用整个正式父图，尤其未接入正式 `validate_dates`。不测试网页流式、插话队列或分析。查询适配器当前仅支持所选两例用到的四个指标。

已完成的运行应直接阅读记录；下列命令供以后获准重跑时使用，会产生新的模型费用。以一个**全新的目录**为例，在实验根目录执行：

```bash
.venv/bin/python -m business_analysis_repro.clarification_lab.query_smoke prepare .runs/simple-query-next
.venv/bin/python -m business_analysis_repro.clarification_lab.query_smoke step .runs/simple-query-next --case Q09 --live
```

检查它确实追问了缺少的日期后，才执行下一轮。`--question-reviewed` 表示执行者已审阅实际问句，不能作为用户已验收的证据：

```bash
.venv/bin/python -m business_analysis_repro.clarification_lab.query_smoke step .runs/simple-query-next --case Q09 --live --question-reviewed
.venv/bin/python -m business_analysis_repro.clarification_lab.query_smoke step .runs/simple-query-next --case Q11 --live
.venv/bin/python -m business_analysis_repro.clarification_lab.query_smoke summary .runs/simple-query-next
```

每次 `step` 只处理一轮。Q11 后续也使用同一 `step` 命令，但必须先审阅前一轮成功；上一轮失败时程序直接阻止继续，不替换为标准历史。标准任务只在执行后用于评审。代码、知识或配置改变后不能续写同一批次，应保留失败并另起目录。

默认一批最多 30 次请求、单轮最多 6 次，重试也计数；单次输入估算上限 18,000 Token。`prepare --max-requests N --max-turn-requests M` 可降低或调整上限，硬上限分别为 30/8。这是这两例的串行批次预算，不是线上并发限流器。

离线检查（不调用模型 API）：

```bash
TIKTOKEN_CACHE_DIR=.runs/tokenizer-cache .venv/bin/python -m pytest tests/test_query_smoke.py tests/test_clarification_lab.py -q
```

Q 编号的逐轮文件是 `Q09-turn-1.json` 等，含模型条件比对、执行状态、真实查询及用量；同目录的 `summary.json` 汇总批次。任务目录内有 checkpoint、状态、JSONL 原始轨迹及 HTML Trace。原始失败记录保留，发现评审错误时另附 `*-audit.json`，不覆盖历史。


## 9月30日：完整十二例与知识对照

[9月30日历史结果](首次试跑结果.md#full-20260930)：十二个查数场景全部启动，八个完整通过，四个失败；实际十五轮，另五轮因前置失败未发送。同一道“下沉”问题分别跑原提示和追加检索指引下的有/无定义，共四组，含一次有效澄清后的回复。全轮次原始结果与失败均保留。

当前查询适配器覆盖这套十二例实际使用的九个指标。绝对年月使用 range、单日使用 exact，相对时间才用 calendar/rolling；本轮二十项 ready 请求均保留绝对时间表达。引用 ID 协议、澄清提交通道、追问删分组与业务术语未检索仍有失败，不表示全部能力完成。

新建完整批次的命令如下；本轮已经运行，不要为阅读报告再执行收费 step：

```bash
.venv/bin/python -m business_analysis_repro.clarification_lab.query_smoke prepare .runs/query-suite-new --all-cases --max-requests 160 --max-turn-requests 12
.venv/bin/python -m business_analysis_repro.clarification_lab.query_smoke step .runs/query-suite-new --case Q01 --live
```

一次 step 处理一个用户轮次，案例 ID 可选 Q01—Q12。多轮仍先检查前一轮成功再继续；澄清后续轮必须审阅实际问句。默认只准备 Q09/Q11，全部十二例需要显式 `--all-cases`。单轮硬上限现在是 12 次，完整查数批次硬上限 160 次；是请求预算，不代表正常情况下每轮需要这么多。

知识原版对照沿用旧入口（语义校验结束，不执行查询），分别建立独立目录；本轮每组最多 20 次请求：

```bash
.venv/bin/python -m business_analysis_repro.clarification_lab run alias_unknown --output .runs/alias-unknown-new --max-calls 20 --live
.venv/bin/python -m business_analysis_repro.clarification_lab run alias_defined --output .runs/alias-defined-new --max-calls 20 --live
```

本轮受提示引导的诊断脚本、追加提示和源码快照保存在 `.runs/knowledge-guided-20260930` 及 `.runs/run_knowledge_guided_20260930.py`，没有直接合入主 Agent 提示。它也未让有定义组完成主动检索，不能包装成已修复。

实验机制离线检查为 38 项通过；原网页没有重启。新增相对/绝对时间规则已写入源码提示与参数说明，不声称已经验证常驻网页进程加载了它。


## 2026-10-01：选题、冻结与来源协议

后续实验可以按问题选择少量题，新批次自动写入源码与资料快照：

```bash
.venv/bin/python -m business_analysis_repro.clarification_lab.query_smoke prepare .runs/source-next --cases Q05 Q12 --max-turn-requests 12
.venv/bin/python -m business_analysis_repro inspect-batch .runs/source-next
```

准备和检查不请求模型。默认仍选 Q09/Q11；`--cases` 与 `--all-cases` 互斥。小批次总请求上限仍为30次，每轮硬上限12次；需要全十二例另行确认后使用原全量入口。源码或资料变化仍拒绝混入旧批次。

`knowledge_refs` 现在仅允许从工具实际返回的来源中选择。引用指标ID/任务ID会被明确拒绝，并在本轮原预算内让模型重新提交；原始提交、错误、最终结果均保存。新增结果的 `source_protocol_corrections` 单列协议纠正次数，不能把辅助纠正后的通过称为模型首次提交正确。没有程序自动替换ID或补业务条件。

10 月 1 日实模结果见[当时测试报告](../../测试报告-v1-2026-10-01-15-55-30.md)；9月29日/30日的记录保持原成绩。


## 2026-10-02 最新复测

当前小知识库按本轮用户原话做程序预检索，保留实际结果与发起方；模型可继续按短语补查。公开任务校验在提交循环内反馈，业务请求只回普通正文时也继续要求结构化提交，日期与条件不会按私有答案补写。

最新五道简单题全部通过，Q11 四轮全部完成。有定义的下沉题正确使用代理筛选；无定义组澄清后多加分组，仍未通过。有无定义影响首请求实际上下文，本轮不再宣称首请求相同或检索由模型自主触发。具体对错与新记录见[最新报告](../../测试报告-v2-2026-10-02-02-48-37.md)。
