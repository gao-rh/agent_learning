# LangGraph 经营分析面试复现

> 当前入口更新：2026-10-02。聊天主链路为 analysis-v5：多指标并行、简易分析、真实正文流式、队列插入/停止、上下文压缩、Trace 与用量统计；另有隔离澄清实验及固定结果查看器。下文 E1/E2 等保留历史日期，不代表当前整套验收状态。业务数据模拟，LangSmith 云端追踪关闭。

## 当前实现入口

- [项目介绍：架构、能力、存储与运行](../../记录/2026-09-09-智能经营分析复现总览与能力缺口-v1.md)
- [最新测试报告：C01 AI用户多轮试跑](测试报告-v3-2026-10-02-17-10-19.md)
- [经营分析聊天试玩](business_analysis_repro/playground/README.md)
- [固定案例查看器](business_analysis_repro/case_viewer/README.md)

## 现在从这里复现

在本目录执行，前三条不请求模型：

```bash
.venv/bin/python -m business_analysis_repro doctor
.venv/bin/python -m business_analysis_repro prepare
.venv/bin/python -m business_analysis_repro demo
.venv/bin/python -m business_analysis_repro.playground --open
```

`prepare` 提前建立固定数据；`demo` 使用真实当前主图/查询/分析/checkpoint，仅以脚本替换模型，不验证自然语言能力。它会返回四场景 Trace 路径。最后一条启动聊天服务，发送问题后才调用 Kimi。常驻进程是否加载当前源码，以 `doctor` 的指纹检查为准。

回归按范围执行 `python -m business_analysis_repro test mechanism|lab|viewer|all`（实际命令选择其中一项）；新实验可先 `inspect-batch <目录>` 检查冻结版本。上一版全套 282 项离线测试通过，本次相关离线回归 92 项通过，完整上一轮实模结果见[测试报告 v2](测试报告-v2-2026-10-02-02-48-37.md)，新流程 C01 试跑见[最新测试报告](测试报告-v3-2026-10-02-17-10-19.md)。以后报告统一命名为 `测试报告-v版本-YYYY-MM-DD-HH-MM-SS.md`；首页只链接最新一份，每份记录本次对错、逐题原因与建议。测试交接已结束，不继续追加。

早期教学入口：[七节点主 Agent](business_analysis_repro/main_agent/README.md)。后面的目标、目录和 E1/E2 记录属于早期阶段；当前代码布局和执行链路以项目介绍为准。

<span id="ai-user-tests"></span>

## 后续多轮测试

2026-10-02 起，新的多轮实模测试统一用 AI 模拟用户，调用独立的 Kimi 用户角色，根据助手实际回复继续对话。初始需求来自案例；后续回复由模型生成，不再直接发送预设句子。用户角色只看到自己的业务设定和实际对话，评审标准与助手内部状态不进入它的上下文。

```bash
./运行多轮测试.command prepare .runs/ai-user-c01 --kind complex --cases C01
./运行多轮测试.command run .runs/ai-user-c01 --case C01 --live
./运行多轮测试.command summary .runs/ai-user-c01
```

`prepare` 与 `summary` 不请求模型；`run --live` 会付费，先说明本次案例和预算。`--kind query|complex|knowledge` 选择原有执行器；默认每例最多 6 轮，整个批次最多 30 次请求（助手、AI 用户、重试与摘要合计），另有 Token 和估算费用上限。复杂实验仍止于计划，知识实验止于语义任务，查数实验才执行支持的本地模拟查询。可用 `step` 每次推进一轮观察，不需要手写回复。

做不了的部分要明确说明具体缺口，并请用户选择接受部分、替代或结束；保留原始诉求与实际选择，不要求缺口项填全执行字段。评分差异保留后继续观察对话；运行异常、预算耗尽或轮数耗尽会明确停止。AI 用户说“结束”不代表测试通过，动态对话按实际需求和结果审阅，不机械套用旧固定回复的逐轮标准。

启动脚本用同一份 `uv.lock` 在本地缓存准备依赖与 Python 字节码，避免 iCloud 占位造成读取阻塞；首次准备可能下载依赖，原 `.venv` 保留。

固定案例查看器标注每条消息是「测试初始需求」还是「AI 模拟用户」，并展示用户模型的实际输入、返回和用量。`simulation-summary.json` 分别统计助手与 AI 用户，合计不漏算。旧固定脚本和测试报告作为历史对照保留；旧入口不再运行新的多轮实模测试。

## 早期学习目标（保留历史）

使用完全脱敏的模拟指标与数据，逐步完成：

```text
LangChain Tool Loop
→ LangGraph 多节点与有限循环
→ data_agent + analysis_agent
→ checkpoint / interrupt / replay
→ LangSmith 完整 Trace
```

本目录是面试导向的小型学习复现，不是原公司项目源码，也不表示原项目使用了 LangChain 或 LangGraph。

## 已初始化环境

- Python 3.12，由 `.python-version` 固定；
- `uv` 项目与项目内 `.venv`；
- LangChain、LangGraph、LangSmith；
- LangChain OpenAI 兼容模型适配，默认接入 Kimi K2.6；
- LangGraph SQLite checkpointer；
- pytest 与 Ruff；
- 默认关闭 LangSmith tracing，防止在配置完成前意外上传内容。

## 目录

```text
.
├── .env.example
├── .python-version
├── business_analysis_repro/
│   ├── __init__.py
│   ├── calendar_tools.py
│   ├── clarification_catalog.py
│   ├── clarification_demo.py
│   ├── clarification_graph.py
│   ├── metric_tools.py
│   ├── settings.py
│   ├── smoke.py
│   ├── synthetic_data.py
│   └── tool_calling_demo.py
├── pyproject.toml
├── uv.lock
└── tests/
    ├── test_calendar_tools.py
    ├── test_clarification_catalog.py
    ├── test_clarification_graph.py
    ├── test_environment.py
    └── test_metric_tools.py
```

`smoke.py` 只验证 LangGraph 能在当前环境中编译和执行一个最小 Graph，不属于 E1 学习实验。

## 初始化或恢复环境

```bash
cd "/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现"
uv sync --frozen
```

如果当前机器没有本地 `.env`，先复制配置：

```bash
cp .env.example .env
```

不要提交 `.env`。所有发送给 LangSmith 的内容必须是模拟数据。

Kimi 配置使用：

```text
MOONSHOT_API_KEY=<只保存在忽略文件中>
MOONSHOT_BASE_URL=https://api.moonshot.cn/v1
MODEL_NAME=kimi-k2.6
```

当前机器的 `.env` 只引用既有本地密钥文件，不复制密钥。可使用以下命令做无网络预检：

```bash
uv run python -m business_analysis_repro.settings
```

## 验证环境

```bash
uv run python -m business_analysis_repro.smoke
uv run pytest -q
uv run ruff check .
```

### 2026-08-28 机器验证

以下 E2 真实调用是旧版混合澄清器的历史证据，不代表 2026-08-30 重构后的实现已经完成真实模型验收。

- Python：3.12.13；
- LangChain：1.3.18；
- LangGraph：1.2.11；
- LangSmith：0.11.2；
- LangGraph SQLite checkpoint：3.1.1；
- 最小 Graph smoke：通过；
- Kimi 本机配置预检：`kimi-k2.6`、国内 Endpoint、API Key 存在、LangSmith tracing 关闭；
- E1 真实 Kimi 请求：通过，2 次模型请求、1 次本地工具执行；
- Kimi 选择：`get_metric_value(metric_name="保费收入", date="2026-08-01")`；
- 工具模拟结果：`128000.0 元`；Kimi 最终回答：`128,000 元`；
- 本次用量：输入 533 Tokens、输出 53 Tokens、合计 586 Tokens；
- LangSmith 埋点：已加入；本机缺少 LangSmith API Key，尚未验证远端 Trace；
- E2 真实澄清 Graph：通过，用户只回复一次 `确认`，2 次 Kimi 请求、1 次本地 Tool 执行；
- E2 已确认条件：`准时保保费收入`、`整体`、`2026-08-28`；
- E2 模拟结果：`186500.0 元`；总用量：输入 464、输出 71、合计 535 Tokens；
- E2 SQLite Checkpoint：9 个 StateSnapshot，最终状态 `completed`；
- E2 无歧义直达查询：真实 Kimi 通过，`clarification_rounds=0`，App 渠道次日结果
  `124700.0 元`，输入 469、输出 83、合计 552 Tokens；
- E2 扩展目录真实 Kimi 查询：取消险保费收入、连锁商家、2026-08-15，0 轮澄清，
  结果 `43445.79 元`，输入 474、输出 91、合计 565 Tokens；
- E2 多指标自由文本澄清：用户回复 `三种 保费`，Kimi 解析为 3 个受控指标 ID，
  1 轮澄清后执行 3 次 Tool；输入 1426、输出 202、合计 1628 Tokens；
- 当时 pytest：`21 passed`（含 Studio Chat 消息入口适配）；
- Ruff：`All checks passed`。

真实 Kimi 调用证明当前机器上的 Tool Loop 可以运行，但不等于用户已经独立完成或理解 E1。

### 2026-08-30 Clarification Agent 重构验证

- 删除确认词表、本地确认快速路径和自然语言日期正则；
- 合并旧 `understand / prepare / interpret / apply` 双重理解链，改为单个 Kimi Clarification Agent；
- 日历语义通过 `resolve_business_period(mode, unit, offset, exact_date)` 工具确定起止日期；
- `submit_clarification` 只接受 `ready` 或 `needs_clarification` 两类结构化决策；
- 运行时会拒绝没有日历 Tool 证据的查询/分析请求，并把校验错误作为 ToolMessage 退回模型修正；
- 本地无付费测试：`27 passed in 1.10s`；
- Ruff：`All checks passed`；
- 未发起重构后的真实 Kimi 调用，因此模型对自然语言的实际识别效果仍为待验证。

## E1 模型选择

沿用此前实验使用的 Kimi K2.6 国内 API。为了让最小 Tool Calling 轨迹更短、更容易观察，E1 默认关闭 thinking；不设置 K2.6 不兼容的自定义 temperature。

## E1：运行完整 Tool Calling Loop

应用显式注册两个本地业务工具；Kimi 与 LangChain 不会自动提供它们：

| 工具 | 用途 |
| --- | --- |
| `get_metric_value` | 查询某日业务指标数值 |
| `get_metric_definition` | 查询指标定义或统计口径 |

`metric_tools.py` 定义 Tool，`tool_calling_demo.py` 手写执行以下循环：

```text
用户问题
→ 应用把 messages + tools 发给 Kimi
→ Kimi 返回 ToolCall（只生成工具名和参数）
→ Python 根据注册表执行本地函数
→ 应用把 ToolMessage 发回 Kimi
→ Kimi 结合工具结果生成最终回答
```

运行固定案例：

```bash
cd "/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现"
uv run python -m business_analysis_repro.tool_calling_demo
```

也可以传入自己的问题：

```bash
uv run python -m business_analysis_repro.tool_calling_demo "保费收入的业务口径是什么？"
```

这仍是手写 Tool Loop，不是 LangGraph Workflow；后面的 E2 已开始使用 LangGraph 节点、条件边、
`interrupt` 和 Checkpoint。

## E2：运行模型驱动澄清 Graph

E2 将口语请求映射为一个标准请求：意图、指标 ID、维度、起止日期和请求内容。澄清不是必经环节；
Kimi 结合完整对话判断信息是否足够，信息不足时由它生成一个一次性覆盖全部未决项的问题。

程序不再判断 `确认`、`1`、`三种保费`、`近一周` 等自然语言。Kimi 负责语义理解，代码只保留：

- 指标、维度和值必须属于业务目录；
- 时间语义必须先调用日历工具换算为确定的 ISO 起止日期；
- `ready` 请求必须满足对应意图的执行条件；
- `interrupt` 暂停和恢复，以及最大轮数/工具循环安全上限。

```text
prepare_input
→ clarification_agent (Kimi)
↔ clarification_tools
   ├── resolve_business_period
   └── submit_clarification
→ needs_clarification: ask_human (interrupt) → clarification_agent
→ ready: query_data / data_knowledge / data_analysis
→ generate_answer
```

这采用了主流 Tool Use 的共同模式：模型依据工具描述和 JSON Schema 选择工具，应用执行并返回
ToolMessage，模型再继续决策。参考 [Kimi 工具调用](https://platform.kimi.com/docs/api/tool-use)、
[Anthropic 工具定义建议](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools) 和
[LangGraph ToolNode](https://docs.langchain.com/oss/python/langchain/tools)。

运行固定案例：

```bash
uv run python -m business_analysis_repro.clarification_demo
```

第一次提示后可回复：

```text
确认
```

也可以只说要修改的部分，例如 `App渠道，明天`。这些确认、继承和修改关系均由 Kimi 根据完整对话理解，
不是 Python 的字符串判断；最终 State 只保存标准请求和 ISO 起止日期。

完整且无歧义的请求不会出现澄清提示，可直接验证：

```bash
uv run python -m business_analysis_repro.clarification_demo \
  "查询准时保保费收入，App渠道，明天。"
```

Graph 使用本地 `clarification_checkpoints.sqlite3` 保存 State；该文件已被 Git 忽略。默认实验基准日固定为
`2026-08-28`，以保证测试可复现。澄清安全上限为 5 轮，Clarification Agent 工具循环上限为 12 步。

### E2 合成指标数据范围

`synthetic_data.py` 使用固定公式生成可复现的合成数据，不会在每次运行时随机变化。当前数据范围是
2026-08-01 至 2026-08-31，共 31 天。

| 标准指标 | 单位 |
| --- | --- |
| 准时保保费收入 | 元 |
| 取消险保费收入 | 元 |
| 安心吃保费收入 | 元 |
| 订单渗透率 | % |
| 客户渗透率 | % |

当前支持三种查询范围：

| 查询范围 | 可选值 |
| --- | --- |
| 整体 | 不拆分 |
| 商家 | 连锁商家、中小商家、新入驻商家 |
| 渠道 | App、API |

三个金额指标满足：整体金额等于商家拆分之和，也等于渠道拆分之和。两个渗透率是比例指标，
各维度百分比不能直接相加。自然语言时间由 Kimi 转成日历工具参数，而不是本地短语表。当前确认口径是：
`rolling + week + 0` 表示包含参考日的滚动 7 天，`calendar + week + 0` 表示本周一到参考日，
`calendar + week + -1` 表示上一自然周。金额范围按天求和，比例范围按天求平均；单次查询最多 31 天。

可用下面的完整请求验证新增指标和商家维度：

```bash
uv run python -m business_analysis_repro.clarification_demo \
  "查询取消险保费收入，连锁商家，8月15日。" \
  --reference-date 2026-08-29
```

多指标自由文本澄清可这样验证：

```bash
uv run python -m business_analysis_repro.clarification_demo \
  "查询8月15日整体保费。" \
  --reference-date 2026-08-29
```

提示候选指标后，可以自然回复 `三种 保费`、`全部都查` 或其他等价表达；这些表达由 Kimi 解释，
不是本地字符串规则。

日期范围可以直接验证：

```bash
uv run python -m business_analysis_repro.clarification_demo \
  "查询准时保保费收入，App渠道，近一周。" \
  --reference-date 2026-08-29
```

如果 Kimi 将“近一周”理解为 `rolling + week + 0`，日历 Tool 会返回 `2026-08-23` 至
`2026-08-29`。这正是需要在 Studio Trace 中由用户观察和验证的模型行为。

## 本地 LangGraph Studio

项目根目录的 `langgraph.json` 将 `business_analysis` 注册为 Studio 可加载的 Graph：

```text
business_analysis_repro/clarification_graph.py:graph
```

启动本地开发服务器：

```bash
cd "/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现"
LANGGRAPH_CLI_NO_ANALYTICS=1 uv run langgraph dev --no-browser --no-reload
```

该命令启动的是前台本地开发服务：终端必须保持运行；关闭终端或按 `Ctrl+C` 后，Studio 会显示断开。
然后打开终端输出的 Studio URL。当前机器已验证：

- 本地 API 位于 `http://127.0.0.1:2024`；
- Studio 显示 `Connected`，能够加载 `business_analysis` 的节点和条件边；
- 本地服务使用 `auth=noop`，未配置 LangSmith control plane key；
- `LANGSMITH_TRACING=false`，不会把业务输入、State 或 Tool 结果作为 LangSmith Trace 上传；
- Studio 顶部的“缺少 LangSmith API Key”提示只影响云端 Runs，不影响本地图和本地 Interact。

Studio 有两种等价入口：

- `Chat` 模式发送一条用户消息；
- `Graph` 模式在 Input 中只填写 `raw query`。

`prepare_input` 节点负责把两种输入归一化为同一套初始 State。第一次学习运行可在 `Chat` 模式发送：

```text
查询准时保保费收入，App渠道，明天。
```

这会触发真实 Kimi API 调用。运行后切到 `Graph`，观察经过的节点、每一步 State 变化和最终输出，
再换成需要澄清的输入验证 `ask_human` 中断：

```text
查询今天的保费。
```

Studio 的本地执行视图适合当前单次调试；跨运行检索、线上监控和集中评测仍属于 LangSmith 云端 Trace 的能力。

## 可选：以后开启 LangSmith Trace

当前学习阶段不启用 LangSmith，保持：

```text
LANGSMITH_TRACING=false
```

LangSmith 埋点代码暂时保留；关闭开关时不会上传 Trace，也不影响 Tool Loop 和后续
LangGraph 执行。等需要跨运行检索、对比或评测时，再考虑启用以下配置。

1. 登录 [LangSmith](https://smith.langchain.com)，在 Settings → API Keys 创建 API Key；
2. 在被 Git 忽略的本地 `.env` 中填写：

```text
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<你的 LangSmith API Key>
LANGSMITH_PROJECT=business-analysis-langgraph-interview-repro
```

3. 先检查配置，再运行同一个案例：

```bash
uv run python -m business_analysis_repro.settings
uv run python -m business_analysis_repro.tool_calling_demo
```

第一次成功上传后，LangSmith 会自动创建指定 Project。进入该 Project 的 Tracing 页面，应能看到：

```text
e1_kimi_tool_calling_loop                 # 父 Trace
├── kimi_tool_decision_round_1            # 第一次模型调用
├── local_tool__get_metric_value          # 本地 Tool 执行
└── kimi_tool_decision_round_2            # 第二次模型调用与最终回答
```

代码会在退出前等待 Trace 上传完成。若开启追踪却没有配置 API Key，会在产生 Kimi 费用之前报出明确错误。
本学习复现只向 LangSmith 发送脱敏模拟数据。

## 早期 E2 下一步边界（保留历史，不是当前待办）

下一步由用户在 Studio 新线程运行重构后的 E2，重点观察
`clarification_agent → resolve_business_period → clarification_agent → submit_clarification`，再用含歧义输入验证
`ask_human` 的 interrupt/resume。完成这两个真实模型案例后，再讨论执行计划验证和后续 Agent 拆分。
