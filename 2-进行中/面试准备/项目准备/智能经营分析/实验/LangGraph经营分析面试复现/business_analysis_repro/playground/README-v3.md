> 历史快照：这是升级并行前的 v3 说明，当前入口见 README.md；下面行号反映当时文件。

# 经营分析对话试玩 v3

> 小型学习实验；名称和部分口径参考你保存的原文。全部业务数字、指标 ID、数据集 ID、表名与支持矩阵均为演示配置，不连接公司环境。用户独立运行与理解仍为待验证。

## 先运行

已经启动的入口：[打开本机试玩](http://127.0.0.1:8787/)。

下次可双击 [启动经营分析试玩.command](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/启动经营分析试玩.command)。也可以在实验根目录运行：

```bash
.venv/bin/python -m business_analysis_repro.playground --open
```

使用现有 `.venv` 和 `settings.py`，密钥仍从原本的本机配置读取。浏览指标面板不调用模型；点击“发送”才调用 Kimi K2.6。不开启 LangSmith 云端 tracing。前台启动时按 Ctrl+C 停止；本次由后台进程保持服务。

日期基准固定为 **2026-09-01**：“上周”为 08-24 至 08-30，“前一周”为 08-17 至 08-23。程序可生成 2026 年内、截至基准日的模拟日数据，单次最多 31 天；其他日期沿用两段预设模式，不表示存在真实历史数据。

修改 Python 或 `knowledge.json` 后需要**重启服务**；网页 HTML 修改后刷新即可。执行日志记录进程加载时的文件版本。不要仅刷新页面就以为 Python 已更新。

## 可以怎么试

| 输入 | 预期行为 |
| --- | --- |
| 查询上周放心吃净保费规模 | 查到模拟合计 56,000 元 |
| 接着说“那新商呢？” | 继承指标和日期，增加商户新老=新商的真实查询条件 |
| 上周准时宝保费是多少？ | 澄清商家付费或平台采购；回复“商家付费的”后恢复原任务 |
| 上周加入商户数是多少？ | 区分流量漏斗的外卖险加入商户数与放心吃餐饮加入商户数 |
| 查询上周放心吃餐饮订单渗透率，按获客来源拆解 | 提示该演示指标不支持来源，给出可选维度 |
| 然后回复“改成按新老商拆解” | 按商户新老分组，不能继续使用已取消的来源条件 |
| 查询上周城市商家的取消险餐饮订单渗透率 | 提示本指标只开放 KA/CKA；城市商家在全局字典存在，在本指标不开放 |
| 上周外卖险加入商户数，险种是放心吃，来源是电销 | 搜索两个枚举，正确绑定到险种与来源，两个条件都进入查询 |
| 分析上周取消险餐饮订单渗透率与前一周的变化，按新老商看 | 计算总量与各组前后值、百分点变化 |
| 上周放心吃净保费规模，配送方式选无人机 | 不存在的枚举进入澄清 |
| 放心吃单均保费的口径是什么？ | 走知识分支，无需取数或填写日期 |

这些是代表性例子；确定性代码会拦截提交计划中的非法 ID、维度、枚举和范围。自然语言解析仍依赖模型，不能把已测案例通过等同于所有表达都不会遗漏条件。

## 当前 20 个指标

本期模拟预设合计对应 **2026-08-24 至 08-30，未加筛选**。各指标恰好开放三个维度，同一维度在不同指标下允许的枚举也不同。

| 标准名称 | 本期模拟值 | 三个支持维度 | 本地取数路径 |
| --- | ---: | --- | --- |
| 放心吃餐饮净投保订单量 | 56,000 单 | 商户新老、外卖商户类型、主营一级品类 | 平台模拟 |
| 放心吃餐饮可投保订单量 | 70,000 单 | 商户新老、主营一级品类、二级品类 | SQL |
| 外卖餐饮订单量 | 80,000 单 | 外卖商户类型、主营一级品类、地区 | 平台模拟 |
| 放心吃餐饮订单渗透率 | 80.00 % | 商户新老、外卖商户类型、主营一级品类 | SQL |
| 放心吃餐饮可投保订单渗透率 | 80.00 % | 商户新老、外卖商户类型、主营一级品类 | 平台模拟 |
| 取消险餐饮订单渗透率 | 31.25 % | 商户新老、外卖商户类型、主营一级品类 | SQL |
| 准时宝餐饮订单渗透率（商家付费） | 42.86 % | 商户新老、外卖商户类型、主营一级品类 | 平台模拟 |
| 外部入口曝光UV | 112,000 人次 | 险种、一级渠道、获客来源 | SQL |
| 外部入口点击UV | 22,400 人次 | 险种、一级渠道、二级渠道 | 平台模拟 |
| 详情页曝光 | 16,800 人次 | 险种、二级渠道、获客来源 | SQL |
| 详情页点击 | 11,200 人次 | 险种、获客来源、用户类型 | 平台模拟 |
| 外卖险加入商户数 | 5,600 户次 | 险种、一级渠道、获客来源 | SQL |
| 放心吃餐饮加入商户数 | 2,800 户次 | 商户新老、外卖商户类型、主营一级品类 | 平台模拟 |
| 外部入口点击率 | 20.00 % | 险种、一级渠道、获客来源 | SQL |
| 放心吃净保费规模 | 56,000 元 | 商户新老、主营一级品类、三级配送方式 | 平台模拟 |
| B端准时宝净实收保费（商家付费） | 35,000 元 | 外卖商户类型、主营一级品类、获客来源 | SQL |
| B端准时宝净实收保费（平台采购） | 28,000 元 | 外卖商户类型、地区、是否预约单 | 平台模拟 |
| 取消险净实收保费 | 17,500 元 | 商户新老、主营一级品类、三级配送方式 | SQL |
| 【放心吃】单均保费 | 1.0000 元/单 | 商户新老、主营一级品类、三级配送方式 | 平台模拟 |
| 放心吃退出商户数 | 840 户次 | 退出类型、外卖商户类型、商户新老 | SQL |

右侧面板会随指标展示具体可用枚举；完整配置在 [knowledge.json](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/playground/knowledge.json)。

保费链路的总体预设已核对：放心吃净投保订单 56,000 单，净保费 56,000 元，单均保费 1.0000 元/单。非取消订单基数为 70,000 单，订单渗透率 80%，所以 1 × 80% × 70,000 = 56,000。非取消基数与可投保量在这个小样本中恰好相等，**这两个业务口径并不相同**。

每个指标的分组是独立的模拟立方体，仅保证各自分组和筛选可回算、比例按分子分母汇总。不同指标的维度集合和模拟覆盖范围可能不同；本版没有建立可跨指标、跨维度联查的统一事实表，不能把不同范围的漏斗值直接相除。

## 维度与枚举字典

[完整指标 × 维度矩阵](指标维度矩阵.md) 列出20个指标与14个候选维度；点击交叉点的数量可查看该指标实际允许的枚举。

下表是全局候选字典，不等于每个指标都支持全部维度和枚举。

| 维度 | 全局候选枚举 | 含义及来源边界 |
| --- | --- | --- |
| 险种 `insurance_type` | 放心吃、准时宝、取消险 | 投保的保险产品。 |
| 获客来源 `source` | 商家端APP、电销、地推、自然访问 | 从哪里获得客户；与 APP 内的栏位分开。 |
| 用户类型 `user_type` | 新客、老客、回流客 | 新客=首次产生该指标事件的客户；老客=已有历史事件；回流客=间隔后再次产生事件。本实验为模拟标签。 |
| 商户经营一级品类 `category_l1` | 餐饮、休闲娱乐、生活服务 | 商户经营品类的第一层。 |
| 二级品类 `category_l2` | 餐饮/火锅、餐饮/快餐小吃、休闲娱乐/KTV、休闲娱乐/密室、生活服务/美容美发 | 商户经营品类的第二层；枚举名称保留父类路径，避免同名误配。 |
| 地区 `region` | 华东、华南、华北 | 商户归属的经营区域，不支持城市或省份层级。 |
| 商户新老 `merchant_age` | 新商、老商 | 报告口径：新商=入驻不超过30天；老商=入驻超过30天。 |
| 外卖商户类型 `merchant_type` | KA（大连锁）、CKA（小连锁）、城市商家 | 与新商/老商不同的经营规模分类。 |
| 主营一级品类 `takeaway_category` | 美食、甜点、饮品 | 原始评测材料中的外卖品类枚举；不要与餐饮/娱乐经营大类混为一套。 |
| 一级渠道 `channel_l1` | 开门营业、钱包、金刚位、商家成长、主动触达、PC、其他 | 原始材料的一级渠道分类，包含APP入口及PC等；获客source单独定义。 |
| 二级渠道 `channel_l2` | 钱包-首页banner、钱包-我的保障 | 报告给出的钱包下二级入口示例；不是完整40多项枚举。 |
| 三级配送方式 `delivery_method` | 快送、经济送、商家自配送 | 维度名称来自Skill材料；以下枚举为本地模拟子集，未核实公司完整编码。 |
| 是否预约单 `reserved` | 预约单、即时单 | 维度名称来自Skill材料，本地用是/否模拟编码。 |
| 退出类型 `exit_type` | 主动退出、被动退出 | WBR中区分主动退出与被动退出；模拟数据不代表真实原因。 |

特别保留三类差异：商户新老与 KA/CKA/城市商家分开；获客来源与 APP 栏位渠道分开；原材料的“主营一级品类（美食/甜点/饮品）”与本轮补充的“经营一级品类（餐饮/娱乐/生活服务）”分开。经营一级品类当前仅在候选字典中，未给指标开放，询问时应说明支持范围。

配送方式、预约单这两个**维度名称**在原材料里出现过；本次枚举编码和部分枚举是演示补充。电销/商家端 APP 来自你的口述；地区、用户类型等是补充的模拟维度。字段里保留定义与来源提示，不能将这些配置当成公司实际完整字典。

## 模型到底拿到了什么知识

模型首先看到工具描述及理解任务的要求，不会一次收到整批公司报告。它在需要时调用：

1. `search_metrics`：通过名称、别名、子串和相似度召回候选 ID/标准名称/摘要。
2. `get_metric_definition`：按精确 ID 读取模拟目录的定义、单位、支持维度、枚举范围以及 SQL/平台配置。
3. `search_dimensions`：查维度名字，并返回该指标是否支持。
4. `search_dimension_values`：查枚举与所属维度，包括“全局存在、本指标不支持”的情况。
5. `finish_resolution`：提交结构化意图、指标、时间、分组和筛选；由程序检查后才能进入取数。

这是真实 Kimi Tool Calling：模型返回 `tool_calls`，程序运行函数，结果以 `ToolMessage` 回到同一次循环。取数 Agent、分析 Agent 仍是普通 Python 函数；外层 LangGraph 控制七个节点。没有接向量库、ES 或线上指标平台，搜索是本地小目录匹配。

程序计算日期后，会在取数前增加一次日期语义复核，对照原始问题检查已经展开的本期/前期日期；它是辅助检查，不能保证所有模型误解都被识别。查值与分析时，代码负责聚合；模型负责组织回答，程序核对事实值、证据 ID 和模拟标识，再用模型做辅助语义检查。只允许一次回答重写，理解节点的澄清分支最多四轮、每次理解最多八轮模型工具循环、每个任务最多二十四次模型请求。

## 按执行顺序读代码

| 文件／行范围 | 解决的问题 |
| --- | --- |
| [server.py](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/playground/server.py:219)，219–234 行 | argparse 设置端口和输出目录，启动本地 HTTP 服务 |
| [server.py](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/playground/server.py:158)，158–216 行 | 网页请求如何到达后端，如何返回对话与 Trace |
| [server.py](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/playground/server.py:37)，37–140 行 | 对话目录、串行锁、完成后的连续追问与澄清恢复 |
| [agent.py](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/playground/agent.py:543)，543–593 行 | 建立 SQLite checkpointer，运行图，保存 State 和 Trace |
| [agent.py](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/playground/agent.py:206)，206–540 行 | 七个节点、条件边、interrupt、取数分析分派、回答检查 |
| [agent.py](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/playground/agent.py:88)，88–203 行 | Kimi 工具循环：请求、ToolCall、程序执行、ToolMessage、准入 |
| [catalog.py](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/playground/catalog.py:38)，38–149 行 | 候选召回、精确查询、维度/枚举白名单 |
| [data.py](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/playground/data.py:84)，84–251 行 | SQL/平台模拟取数、比例重算、前后期与同组比较 |
| [trace.py](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/playground/trace.py:25)，25–122 行 | 把实际日志整理成人能逐步阅读的工具与节点回放 |

完整拓扑会写入每次运行的 `graph.mmd`。主路径仍是：

```text
理解问题 → 取数 / 分析 / 查口径 → 组织回答 → 检查回答 → 结束
   ↓                                          ↓
澄清暂停 → 用户补充 → 重新理解             最多重写一次
```

取数或分析过程中发现参数范围不支持，也会回到澄清；运行错误结束并保留记录。旧版 [main_agent 代码与阅读版](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/README.md) 没有改写，之前逐段讲解和带注释副本仍对应 v2。

## 对话、State 与 Trace 在哪里

```text
.runs/playground/<conversation_id>/
  conversation.json                 # 网页消息、最近任务与等待状态
  tasks/<thread_id>/
    checkpoints.sqlite              # LangGraph 的状态历史、interrupt 恢复位置
    state.json                      # 本任务最后 State 的可读导出
    trace.jsonl                     # 逐事件日志，包含模型请求/响应与工具调用
    trace.html                      # 无需模型生成的可读回放
    graph.mmd                       # 本次主图拓扑
```

同一次澄清继续原 `thread_id`。已经答完后的新问题使用新 `thread_id`，显式带入最近三个已完成任务的摘要。网页刷新会从本机保存的会话恢复消息；“新对话”换一个 conversation ID。

点击每条回复下的“查看这次执行回放”，先看七节点步骤和工具卡片，需要时再展开输入、工具返回、模型对话与 State 变化。原始日志不会自动拼到每个节点的模型上下文中，也不记录模型不可见的内部思考。

目前监听本机 127.0.0.1，未实现账号权限与十会话并发压测。它是供你亲自提问和阅读代码的实验入口。

## 原始资料入口

[多指标并行改造方案（AI 草案，尚未实现）](多指标并行改造方案-草案.md)：记录本轮“四个指标都要”的请求、当前单指标限制，以及 Send 分发、结果合并、部分失败和并行 Trace 的改造方式。

[资料回忆与配置依据](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/playground/资料回忆与配置依据.md) 按保费、渗透率、漏斗、商户生命周期和赔付成本整理原文入口，说明哪些进了试玩、哪些只是资料线索。

## 验证

- 全部本地测试：93 项通过，包括旧实验回归；Ruff 通过。
- 第一轮真实 Kimi：8 组、11 轮输入；状态与 11 项实际计划/执行断言通过。56 次模型请求，输入 76,123 Tokens、输出 3,294 Tokens。
- 原始证据：[验证结果](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/.runs/playground-verification-v1/verification.json)、[语义条件与调用用量核对](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/.runs/playground-verification-v1/audit.json)。
- 网页补测和最终可读回放验收记录见 [验收记录](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/playground/验收记录.md)。机器验证不等于用户已经掌握。

离线验证不消费模型额度：

```bash
.venv/bin/pytest -q
.venv/bin/ruff check business_analysis_repro/playground tests/test_playground.py
```

接口使用方式参考 [LangChain 模型与工具](https://docs.langchain.com/oss/python/langchain/models)、[消息与 ToolMessage](https://docs.langchain.com/oss/python/langchain/messages)、[Kimi 工具调用说明](https://platform.kimi.ai/docs/guide/use-kimi-api-to-complete-tool-calls)。
