# 第 3 章实验学习入口：用户记忆与知识库

> 状态：环境准备完成，学习结论均为 `待验证`。Codex 跑过的命令只算环境诊断，不算用户完成实验。

## 你从这里开始

本章不是“照着 12 个 README 把命令敲一遍”。我们要反复练习同一个实验闭环：

1. Codex 先解释本实验要区分的机制和观测指标。
2. 你在不知道结果的前提下写预测，并说明理由。
3. 你亲手运行一个最小对照，描述实际现象，不急着下结论。
4. Codex 帮你核对代码路径、指标、混淆变量和反例。
5. 你用自己的话解释结果；确认理解后才进入下一个实验。

每次记录使用 [实验记录模板](实验记录模板.md)。实验编号按官方 3-1 → 3-12 保留；3-1 和 3-2 虽共用项目，但分别学习“怎么评估”和“怎么表示”。

## 本地入口

- 官方网页：[第 3 章配套实验](https://bojieli.github.io/ai-agent-book/chapter3/)
- 官方验收账本：[EXPERIMENT_LEDGER](https://bojieli.github.io/ai-agent-book/chapter3/EXPERIMENT_LEDGER/)
- 本地官方仓库：`资料/本地资料/深入理解AI-Agent/`
- 当前固定提交：`edaec1b725f2cd23504875df647318e0a1b0ca7c`
- 统一环境：官方仓库根目录 `.venv`，Python 3.12.13，按 `uv.lock` 安装 `ch3 + dev`

每次开始前先运行：

```bash
cd "/Users/gaoronghui/Documents/agent_learning/2-进行中/深入理解AI-Agent/实验/chapter3-memory-rag-labs"
python3 preflight.py
```

进入官方仓库并激活环境：

```bash
cd "/Users/gaoronghui/Documents/agent_learning/2-进行中/深入理解AI-Agent/资料/本地资料/深入理解AI-Agent"
source .venv/bin/activate
```

本地 Ollama 命令统一绕过 macOS 系统代理：

```bash
export NO_PROXY=127.0.0.1,localhost
export no_proxy=127.0.0.1,localhost
```

不加这两行时，`curl` 可能正常，但 Python `httpx` / `ollama` 客户端会得到 HTTP 502。

## 三种证据等级

| 等级 | 能证明什么 | 不能证明什么 |
| --- | --- | --- |
| A：代码/离线冒烟 | 依赖可导入、入口能运行、机制或确定性逻辑存在 | 真实模型效果、完整数据效果、官方实验通过 |
| B：受控教学实验 | 在小型固定数据上改变一个变量，观察方向和失败样例 | 对生产数据或完整基准的普遍结论 |
| C：官方完整验收 | 满足账本规定的数据、模型、规模、独立 Judge、原始 receipts 与哈希 | 仍不能自动证明外部业务效果 |

初始克隆自带的 `validation/latest.json` 指向作者历史运行；准备阶段又在 3-3、3-5 下生成了 Codex 本地诊断 run，因此现在必须根据 run id、Git 状态和 receipts 分辨来源，不能把任一指针直接当成“你已复现”。我们自己的完整运行也必须保留 `validation/runs/<run-id>/`，并检查 `status`、输入哈希、receipts 和是否发生了代理回退。

## 12 个实验的教学路线

| 编号 | 这次真正要学会什么 | 核心对照与指标 | 当前准备边界 |
| --- | --- | --- | --- |
| 3-1 | 先定义“记忆好”再实现系统；三层能力不是同一难度 | 三层各 20 例；逐会话只保留记忆状态；新问题；独立 Judge | 60 个 YAML 已齐；Layer 1 中文单例和 Layer 3 三会话单例已实时运行；完整 campaign 与独立 Judge 未做 |
| 3-2 | 表示能力、维护成本和检索质量之间的取舍 | 四种格式使用相同用例、生成器、回答器、Judge；比较分数、token、延迟和具体记忆文件 | Layer 3 同一案例的四种格式已用 Kimi K2.6 跑完；结果是中文教学对照，不是官方完整验收 |
| 3-3 | 隐私检测不能只看“识别率”，还要看残余泄漏和可用性 | regex vs 本地 LLM vs hybrid；precision/recall、leakage、utility、latency | Ollama `qwen3:0.6b` 已存在；1 例真实本地 campaign 通过准备性检查 |
| 3-4 | 稠密向量解决语义匹配；ANN 是速度/召回/更新能力的工程权衡 | 相同真实向量与查询；精确检索作真值；ANNOY vs HNSW | Qwen3-Embedding 与 MiniLM 已缓存；HNSW 正常；本机 ANNOY 自查询损坏，结果须标不可信 |
| 3-5 | 从倒排索引、TF、IDF、长度归一化理解 BM25，而不是把它当库函数 | 手算样例 + 标注语料；精确词与同义词失败对照 | 完全本地，benchmark 已通过准备性检查 |
| 3-6 | 稀疏、稠密、融合、重排各解决什么问题，新增阶段不保证单调变好 | sparse / dense / RRF / weighted / rerank 消融；Recall、MRR、nDCG、延迟 | MiniLM 与 BGE reranker 已缓存；4 查询全流水线冒烟成功，且观察到重排可能降分 |
| 3-7 | RAPTOR 与 GraphRAG 分别给知识增加什么结构 | Intel 真文档；概念/细节与关系/多跳查询；构建/查询指标 | Intel PDF/TXT 与 MiniLM 已就绪；实时层次摘要、关系抽取和独立 Judge 缺 Ark + Moonshot Key |
| 3-8 | Agentic RAG 的收益来自“根据缺口继续搜”，代价是搜索次数和延迟 | one-shot vs ReAct 多轮；简单/复杂题分层；证据召回、答案 Judge、引用、延迟 | 288 篇法律语料和离线分解检索已通；实时 ReAct/Judge 缺 Key |
| 3-9 | 对话历史分块后，一次向量检索为什么会漏掉跨会话实体 | fixed-window + 单次查询 vs Agent 多轮 `search_user_memory`；三层记忆用例 | 60 例和离线多轮检索演示已通；完整层级评估缺 Key |
| 3-10 | 分块前加“本块在全文中的语境”改变的是索引表示，不是查询 | plain vs live contextual prefix；BM25/dense/hybrid Recall、MRR、索引成本 | Qwen3-Embedding 已缓存；官方仓库未提交默认 `document_store.json`，需有 Key 后现场生成，不能拿手写前缀冒充验收 |
| 3-11 | 原文片段和结构化记忆卡是互补的两层记忆 | plain vs contextual RAG vs contextual + Advanced JSON Cards；冲突与主动服务用例 | 离线词法代理已通；实时 prefixes/cards、检索服务和独立 Judge 缺 Key |
| 3-12 | “从数据发现因子”与“按预设字段抽取”是两件事；训练/留出必须隔离 | CAIL 真数据；发现→抽取→聚类→留出建议→独立 Judge | 官方 420 条固定样本已在仓库；原始 CAIL ZIP 未下载，实时 Ark/Moonshot 调用缺 Key；最后做 |

## 为什么这套顺序有效

- 3-1 先确立测量标准，否则后面的“更好”没有定义。
- 3-2 再改变记忆表示，只动一个主要自变量。
- 3-3 单独研究写入日志前的安全边界。
- 3-4、3-5 分别拆开语义检索和词法检索，3-6 才有资格讨论融合与重排。
- 3-7 把扁平块升级为结构；3-8 再让 Agent 决定何时继续检索。
- 3-9、3-10 将前面的 Agentic 与 contextual 技术分别迁移回用户记忆，3-11 才做组合消融。
- 3-12 的数据、调用次数和推理链最大，最后做，避免一开始把“跑大任务”误当“懂机制”。

## 当前缺少的外部条件

正式教学样例已选定 Kimi K2.6 作为固定的记忆写入器和回答器；本地 `qwen3:0.6b` 只保留为免费管道冒烟后备。Kimi Key 已写入 Git 忽略的本地密钥文件，并已完成本页所列单例运行。官方完整 campaign 仍需要独立 Judge；不能用同一 Kimi 模型自问自评后声称满足原验收。

不要把 Key 发在对话里。本章密钥统一放在实验目录的 `secrets/keys.env`，该文件已被 Git 忽略；空模板和说明位于 `secrets/`。

磁盘当前余量较小。依赖和三组常用本地模型已经准备，BGE-M3（约 2.3 GB）、CAIL 原始压缩包以及额外大模型不会提前下载；到对应实验时先重新检查空间。

## 第一关

- [3-1 与 3-2 详细机制图：Prompt、触发、上下文、四种记忆结构](3-1与3-2详细机制图.md)
- [可选概览图](assets/chapter3-memory-experiment-map.png)

### 3-1：固定记忆方法，改变能力场景

先统一使用最易阅读的 `enhanced_notes`，各跑一例，查看每轮完整 memory state：

1. Layer 1：`layer1_04_airline_booking`（一次长会话后的精确信息回忆）
2. Layer 2：`layer2_01_multiple_vehicles`（两个会话中的多实体消歧）
3. Layer 3：`layer3_01_travel_coordination`（三个会话之间的主动风险关联）

运行器会在每一轮更新前暂停，让用户先预测；更新后打印完整记忆状态；最后只用最终记忆回答新问题。当前默认使用经人工核对的中文教学副本、等价中文 Prompt 和 Kimi K2.6；可用 `--language en` 切回官方英文 YAML 与官方 Prompt。中文运行改变了语言、Token 和模型难度，加上当前没有独立 Judge，因此产物明确标记为 `teaching_proxy`，不能验收官方 3-1。

先用文本编辑器打开实验目录下的 `secrets/keys.env`，只把第一行改成：

```dotenv
MOONSHOT_API_KEY=你自己的Kimi_API_Key
```

不要把 Key 发到对话里。文件已在本机创建，并被 Git 忽略。

再检查 Kimi 账号是否可以调用目标模型：

```bash
cd "/Users/gaoronghui/Documents/agent_learning/2-进行中/深入理解AI-Agent/实验/chapter3-memory-rag-labs"
"/Users/gaoronghui/Documents/agent_learning/2-进行中/深入理解AI-Agent/资料/本地资料/深入理解AI-Agent/.venv/bin/python" local_memory_walkthrough.py --check
```

第一例由用户亲手运行：

如果想先只看完整中文对话，不显示最终考题、不调用 Kimi：

```bash
"/Users/gaoronghui/Documents/agent_learning/2-进行中/深入理解AI-Agent/资料/本地资料/深入理解AI-Agent/.venv/bin/python" local_memory_walkthrough.py \
  --case layer1_04_airline_booking \
  --replay-only
```

看完后再进入真正的记忆生成：

```bash
"/Users/gaoronghui/Documents/agent_learning/2-进行中/深入理解AI-Agent/资料/本地资料/深入理解AI-Agent/.venv/bin/python" local_memory_walkthrough.py \
  --case layer1_04_airline_booking \
  --mode enhanced_notes \
  --show-conversation
```

这两条命令默认使用 `--provider kimi --model kimi-k2.6`。只想验证管道时，可以显式切回免费本地模型：

```bash
"/Users/gaoronghui/Documents/agent_learning/2-进行中/深入理解AI-Agent/资料/本地资料/深入理解AI-Agent/.venv/bin/python" local_memory_walkthrough.py \
  --provider ollama \
  --model qwen3:0.6b \
  --check
```

若希望把原始 112 条消息也全部打印到终端，追加 `--show-conversation`；否则直接从运行器给出的 YAML 路径查看原文。

#### YAML 是什么

YAML 是人类可读的结构化数据文件，在这个实验里相当于一张“考试卷”，不是执行逻辑。一个文件包含：

```text
test_id                用例编号
conversation_histories 一段或多段历史会话
user_question           隔离原始会话后的新问题
expected_behavior       期望回答要点
evaluation_criteria     评分标准
```

第一个案例：

- 官方英文考卷：`chapter3/user-memory-evaluation/test_cases/layer1/04_airline_booking.yaml`
- 本地中文教学副本：`cases_zh/layer1/04_airline_booking.yaml`

#### 3-1/3-2 源码阅读顺序

1. `chapter3/user-memory-evaluation/test_cases/layer1/04_airline_booking.yaml`：先看清实验输入和标准答案。
2. `chapter3/user-memory/run_evaluation.py`：核心受控实验；`memory_prompt()` 生成记忆，`answer_prompt()` 只根据记忆回答，主循环逐会话替换 memory state。
3. `local_memory_walkthrough.py`：教学包装层；加入中文副本、预测暂停、逐轮记忆打印和 Kimi 调用。
4. `chapter3/user-memory/memory_manager.py`：四种记忆结构的存储、更新、删除和查询实现。
5. `chapter3/user-memory/conversational_agent.py` 与 `background_memory_processor.py`：完整示例系统中“回答读记忆”和“后台写记忆”的分工。
6. `chapter3/user-memory-evaluation/evaluator.py`：独立 Judge 和分数是怎样得到的。

先读 1→2→3 就能看懂我们现在要跑的教学实验；4→5 是更完整的 Agent 系统，6 是评估层。

### 3-2：固定同一场景，改变记忆表示

完成三层体验后，再固定 `layer2_01_multiple_vehicles`，依次将 `--mode` 改成：

- `notes`
- `enhanced_notes`
- `json_cards`
- `advanced_json_cards`

这才是本章针对记忆表示的四方案受控比较。它更接近多臂比较，不是严格意义上逐项移除组件的经典消融；真正典型的组件消融会在 3-6 比较 sparse / dense / fusion / reranker。

### 已运行：一个 Layer 3 案例 × 四种记忆方式

2026-08-22 固定中文 `layer3_01_travel_coordination`、Kimi K2.6 和同一组 Prompt，完整运行三段会话：护照续期、达美航班、Chase 信用卡。每条链路都按 `M0 + H1 → M1；M1 + H2 → M2；M2 + H3 → M3；M3 + Q → A` 执行。

- [四种记忆方式对比报告](reports/layer3_01_travel_coordination-zh/00-四种记忆方式对比报告.md)
- [Notes 完整对话与记忆](reports/layer3_01_travel_coordination-zh/01-notes.md)
- [Enhanced Notes 完整对话与记忆](reports/layer3_01_travel_coordination-zh/02-enhanced-notes.md)
- [JSON Cards 完整对话与记忆](reports/layer3_01_travel_coordination-zh/03-json-cards.md)
- [Advanced JSON Cards 完整对话与记忆](reports/layer3_01_travel_coordination-zh/04-advanced-json-cards.md)

当前只确认产物已生成并逐源核对，不把它记成用户已经学会。自动 Judge 与 Writer/Answerer 使用同一模型，Enhanced Notes 的 4/4/4/4 还漏检了两处无原文依据的内容；报告因此同时保留自动分数和人工逐源核对。

### 已运行：3-1 Layer 2 多车辆消歧

2026-08-22 固定 `layer2_01_multiple_vehicles + Enhanced Notes + Kimi K2.6`，运行两段中文历史会话（100 / 94 条消息）。M1 同时建立 Honda 和 Tesla，M2 正确保留 Honda 已预约、Tesla 未预约；最终回答也呈现了两车状态，并询问是否协助安排 Tesla。同模型 Judge 给出 4/3/2/2、无幻觉、核心未通过，但人工逐条复核认为这是把话术显式性误判为能力缺失：回答已经以等价方式完成消歧，应判核心通过，较合理的人工参考分为 4/4/3/3。

- [完整 194 条对话、M1/M2、最终回答与分层分析](reports/layer2_01_multiple_vehicles-zh/01-enhanced-notes完整记录与分析.md)

案例自身还存在日期文字矛盾：`2024-11-24` 实际为星期日，但 YAML 同时称其为星期五/黑色星期五。运行忠实保留基准文字，不用星期几评价记忆能力。
