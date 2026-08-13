---
type: source
status: active
tags: [job-search, recruitment, agent, rag, ai-application, backend, data-engineering]
created: 2026-07-11
updated: 2026-08-14
source_type: official-career-sites
source_url:
  - https://jobs.bytedance.com/experienced/position
  - https://careers.tencent.com/search.html
  - https://talent.baidu.com/jobs/social-list
  - https://zhaopin.meituan.com/web/social
  - https://zhaopin.jd.com/web/job/job_info_list/3
  - https://careers.pddglobalhr.com/jobs
  - https://hr.xiaomi.com/website/opportunities.html
  - https://talent.didiglobal.com/social/list
related:
  - 10-sources/interviews/2026-07-05-面试题目汇总.md
  - 00-inbox/2026-07-06-图解系统学习讨论记录.md
---

# 中国互联网 AI 与 Agent 招聘市场调研

## 基本信息

- 调研日期：2026-07-11。
- 主要范围：中国大陆社会招聘；校园招聘和实习只用于观察岗位命名趋势。
- 个人背景视角：工作 1 年、大数据开发背景、正在补操作系统和后端基础，预计约 3 个月后开始投递。固定偏好是 `直接 Agent 开发 > 大模型应用后端 / Agent 全栈 > 数据 + Agent 兜底`，传统数据开发不作为主投方向。
- 数据来源：优先使用公司官方招聘网站；第三方招聘页只用于发现线索，不作为“岗位仍可投”的唯一证据。
- 统计单位：官网当前展示的职位条目或关键词命中结果，不等于真实招聘 HC。一个 JD 可能招多人，也可能只是长期挂岗。
- 相关笔记：[面试题目汇总](../2026-07-05-面试题目汇总.md) · [操作系统学习讨论记录](../../../../已完成/Agent基础课程/记录/2026-07-06-图解系统学习讨论记录.md)。

## 一句话结论

中国大厂已经形成了真实且数量可观的 Agent 工程岗位族；当前最值得主投的是直接负责 `Planning / Tool / MCP / Memory / Harness / Eval + 生产后端` 的岗位，数据能力只作为已有工程优势，不再决定求职方向。

## 核心结论

1. **Agent 已经是正式岗位族，不只是 JD 加分项。** 字节、腾讯、百度、美团、京东、拼多多、小米、滴滴和 DeepSeek 都能在官网找到直接以 Agent、智能体、Harness 或大模型应用命名的岗位。
2. **“大模型应用开发”最常被放在后端、平台或算法岗位下面。** 常见名称包括 `Agent技术研发工程师`、`AI Agent工程师`、`大模型应用开发工程师`、`智能体平台工程师`、`AI产品研发工程师`、`Agent Harness工程师`。
3. **AI 全栈岗位真实存在，但“全栈”不一定等于传统前后端全栈。** 当前官网出现了小米的“Agent 全栈开发工程师”、美团的“全栈 Agent Builder”、百度的“全栈研发工程师”、DeepSeek 的“全栈开发/算法”招聘序列。它们更强调从需求、Agent、工具、数据、后端到交付的端到端能力，前端只是其中一部分。
4. **有适合低年限候选人的社会招聘样本，但必须持续核验。** 零一万物当前“AI Agent 工程师”明确要求 1–3 年；腾讯“AI 应用开发工程师-Agent方向”要求 1 年以上；拼多多 Agent 后端要求 2 年以上。上一版作为标杆的滴滴 1–3 年“大模型工程”已在 2026-07-11 明确显示结束，说明静态清单会很快过期。
5. **大数据开发不是需要抛弃的旧背景。** AI 数据链路、数据 Agent、RAG 数据工程、向量检索、评测数据、Agent 数据飞轮、Text-to-SQL 都直接复用数据开发能力。
6. **语言不是最稳定的分界线。** 应用岗位经常写“Python/Go/Java/C++ 至少一种”；真正反复出现的是系统设计、分布式、高可用、工具调用、上下文、评测和业务落地。
7. **北京是岗位中心，上海、深圳、杭州是第二梯队。** 拼多多当前 Agent 岗集中在上海；字节、百度、腾讯、滴滴和美团主要集中在北京，同时向上海、深圳、杭州扩散。

## 调研口径与限制

### 为什么不能直接给出“全国一共有多少个 Agent 岗”

各官网的搜索机制不同：

| 官网类型 | 典型表现 | 可否直接横向比较 |
| --- | --- | --- |
| 标题精确或较精确匹配 | 拼多多、小米 | 可以作为该官网内部观察，但仍不等于 HC |
| 同时搜索标题和 JD 正文 | 美团、字节 | 命中数会被正文中的 Agent 放大 |
| 全球岗位、社招和实习混合 | 腾讯 | 需要再按地区和招聘类型清洗 |
| 动态页面或结果无法稳定抓取 | 阿里、蚂蚁、快手等 | 只能记录入口与已验证样本，不能伪造总数 |

因此本报告把数字分成三类：

- `官网总职位`：当前招聘站展示的全部岗位条目。
- `关键词命中`：输入 Agent 后官网返回的结果，可能包含产品、运营、算法和正文命中。
- `已验证技术岗下限`：逐条确认的目标技术岗位，真实数量只会更多，不会更少。

## 官网数量观察

> 下表只用于感知规模，不用于计算“Agent 岗市场份额”。

| 公司 | 官网观察 | 口径说明 | 可得出的结论 |
| --- | ---: | --- | --- |
| 小米 | 社招 1881；Agent 命中 48 | 已选择“社招”后搜索 Agent，标题匹配质量较高 | Agent 已形成工程、全栈、平台、评测、产品多个岗位族 |
| 拼多多 | 全站 877；Agent 命中 14 | 当前 14 条中多数标题直接含 Agent，主要在上海 | 数量不如头部平台多，但目标技术岗密度高 |
| 京东 | Agent 结果至少 10 条，官网显示第 2 页 | 第一页多数是 Agent 开发、后端、软件、算法岗位 | 京东零售、京东健康、京东科技均在招 |
| 腾讯 | 全站 2337；Agent 命中 159 | 全球、社招、实习混合，不能直接当中国社招数 | 中国区已有元宝、混元、微信搜索、腾讯视频等多个 Agent 方向 |
| 美团 | 全站 2262；Agent 命中 183 | 搜索同时命中标题和 JD 正文，包含产品与运营 | Agent 已深入基础研发平台、业务研发和商业智能 |
| 字节 | Agent 命中 1895；大模型应用命中 1908；火山方舟命中 116 | 搜索标题与正文并覆盖全部职类，三组数字都明显偏宽，不能相加 | 已验证岗位分布在 Dev Infra、Data AML、飞书、产品研发和工程架构等不同组织与业务场景 |
| 阿里云 | Agent 搜索显示 62；第一页稳定展示 10 条，第二页异常为空 | 首页 10 条中 5 条技术、5 条秒悟运营；不把 62 当可投技术岗数量 | 已深读 3 个技术岗，其中 AI 原生全栈明确 1 年以上 |
| 蚂蚁集团 | Agent 命中 29；技术类 20 | 官方招聘 API 当前可复核；20 个技术命中含开发 7、算法 11、数据 1 和无线端 1 | 2 年经验开发岗集中在 CodeFuse、资金安全和智能体安全 |
| 百度 | 全站 1585 | 本轮未获得可比的 Agent 精确命中数 | 已逐条验证全栈研发、智能体后端、AI 产品研发、AI Search 等岗位 |
| 滴滴 | Agent 命中 13；当前已验证技术岗 8 | 官网列表可稳定展示 ID 与更新时间 | 当前新岗位直接覆盖 Agent 开发、Infra、测试和质量；旧 1–3 年大模型工程已结束 |
| 零一万物 | 全站 49；Agent 命中 20；首屏已验证 6 个技术岗 | 官网可按 Agent 检索，结果混有产品、销售和实习 | 1–3 年 AI Agent、AI 全栈、智能体算法、评测同时存在 |
| DeepSeek | 当前列表至少 5 个目标技术方向 | 稳定岗位 UUID，但列表不展示发布日期 | Agent 后端、Harness、Infra、AI Search、Code Agent 数据链路完整 |
| Dify/LangGenius | 当前 5 个开放岗位，其中 R&D 3 个 | 中国/远程；职位页显示最近发布于 2026-03-07 | Backend Engineer 是典型“标题不写 Agent、实际建设 Agent 平台”的 P1 岗 |

### 详细初始化岗位池

本次初始化不是把官网关键词命中全部抄入，而是建立了一个可去重、可追踪的目标岗位池：

| 指标 | 当前值 | 说明 |
| --- | ---: | --- |
| 详细岗位记录 | 73 | 72 个当前有效，1 个官网明确结束 |
| P0 直接 Agent 开发 | 37 | Agent 核心系统、后端、Harness、Runtime、全栈 Builder |
| P1 应用/平台/评测 | 31 | AI 应用、Agent Infra、AI Search、评测、平台后端 |
| P2 数据交叉兜底 | 4 | Code Agent 数据、知识底座、量化数据 Agent、研发效能度量 |
| 获得稳定明细的公司 | 11 | 字节、阿里云、蚂蚁、腾讯、滴滴、拼多多、百度、美团、零一万物、DeepSeek、Dify |
| 公司级扫描范围 | 29 | 其余公司保留官网入口和覆盖限制，不把动态页面当成“没有岗位” |

当前有效岗位的完整清单见：[Agent 当前岗位索引](../岗位追踪/岗位索引.md)。索引已把 `事业部/产品线` 与 `实际业务方向` 分开记录；官网未公开更高层组织时不做猜测。

本次详细初始化主体完成时，5 小时额度约增加 15 个百分点、周额度约增加 2 个百分点，符合事前预算。后续周更只深读新增或变化 JD，目标是把单次消耗控制在 5 小时额度 2%–6%、周额度约 1% 以内。

### 关于“数据开发有多少”

本轮不能负责任地给出 24 家公司的纯数据开发总数。原因是官网搜索会把“数据”和“开发”在 JD 正文中的出现也算进去。例如美团搜索“数据开发”返回 1196 条，但其中包含数据产品、数据分析、数据运营以及正文里提到数据开发的其他岗位，不能说美团有 1196 个数据开发岗。

可以确认的相对判断是：

- 在本轮已观察到的综合招聘官网中，传统数据开发仍是比“标题明确写 Agent”更大的岗位池。
- Agent 相关岗位增长快、战略权重高，但数量仍是技术岗位中的子集。
- 对当前用户而言，应先投直接 Agent 开发和应用后端；只有这类机会不足时，才使用 `AI Search、Agent 数据平台、Text-to-SQL` 承接已有大数据经验。

## 公司招聘全景

### 已获得较强当前岗位证据

| 公司 | 当前主要方向 | 主要城市 | 经验信号 | 观察结论 | 官网入口 |
| --- | --- | --- | --- | --- | --- |
| 字节跳动 | AI Coding/GUI Agent、AI 助手、Office Agent、代码质量与风控 Agent | 北京、深圳；更广搜索另见上海、杭州 | Data AML 样本明确 1 年以上；架构岗强调服务端与系统设计 | 不是“没有岗位”，而是岗位分散在 Dev Infra、Data AML、飞书及工程架构等组织，标题未必写 Agent | [社会招聘](https://jobs.bytedance.com/experienced/position) |
| 阿里云 | AI 原生全栈、Agentic Search、专有云 Agent、海外 Agent | 北京、杭州、成都、西安、上海 | AI 原生全栈明确 1 年以上；AI Search/专有云偏 5 年以上 | 当前三家重点公司中，对低年限 Agent 全栈候选人最清晰的直接入口 | [Agent 社招搜索](https://careers.aliyun.com/off-campus/position-list?lang=zh&search=Agent) |
| 蚂蚁集团 | CodeFuse 研发 Agent、资金安全 Agent、智能体安全、评测、研发效能 | 杭州、北京、成都 | 2 年开发岗、3 年算法/评测岗、5 年架构岗均存在 | 业务场景最鲜明，金融安全、AI Coding、研发效能和垂类评测是主线 | [蚂蚁社招](https://talent.antgroup.com/off-campus?search=Agent) |
| 腾讯 | 元宝 Agent 架构、混元 Harness、微信搜索 Agent、视频生成 Agent | 北京、深圳、广州 | 1 年以上、2 年以上、3 年以上均有 | 产品线多，岗位从应用工程到算法训练分层明显 | [Agent 搜索](https://careers.tencent.com/search.html?keyword=Agent) |
| 百度 | 全栈研发、智能体后端、AI 产品研发、应用算法、AI Search | 北京为主，另有上海、深圳、成都 | 工程岗本科起；算法岗常要求硕士或模型训练经验 | “AI 产品研发工程师”是典型的隐藏应用开发名称 | [社会招聘](https://talent.baidu.com/jobs/social-list) |
| 美团 | Agent 工程、商业智能、全栈 Builder、平台、Harness、应用算法 | 北京、上海 | 高级岗较多，部分岗位未公开固定年限 | 适合作为市场基准；基础平台和商业智能结合紧密 | [Agent 搜索](https://zhaopin.meituan.com/web/social?keyword=Agent) |
| 京东 | Agent 开发、架构、后端、软件工程、大模型应用算法 | 北京为主，少量广东 | 当前列表未稳定展示统一年限 | 零售、健康、科技同时招，岗位标题非常直接 | [Agent 搜索](https://zhaopin.jd.com/web/job/job_info_list/3?jobSearch=Agent&jobTypeJson=&workCityJson=&dCode=) |
| 拼多多 | Agent 后端、Agent 开发、智能体平台、Agentic RL、代码智能体 | 上海 | 后端代表岗要求 2 年以上 | 数量不大但非常集中，后端与平台岗位质量高 | [Agent 搜索入口](https://careers.pddglobalhr.com/jobs) |
| 小米 | Agent 工程、全栈、框架、平台、评测、产品 | 北京、上海、深圳、南京 | 从工程师到 Tech Lead 均有 | “全栈”和“评测工程师”命名最明确的一家公司 | [Agent 社招搜索](https://hr.xiaomi.com/website/opportunities.html?project=%E7%A4%BE%E6%8B%9B&q=Agent) |
| 滴滴 | Agent 核心开发、测试 Agent、Agent Infra、质量效能 Agent | 北京、杭州、上海 | 当前技术结果多未固定年限；旧 1–3 年岗位已结束 | 新发布“AI Agent 开发工程师”直接做 Planning、MCP、Memory、LangGraph 和高并发后端 | [Agent 搜索](https://talent.didiglobal.com/social/list/1) |
| DeepSeek | 服务端、全栈、AI Search、Agent Harness、Agent Infra、Agent 数据 | 北京、杭州 | 官网不统一写年限，不从岗位页推断实际录取难度 | 岗位名覆盖从应用、数据到运行时的完整链路 | [官方招聘](https://talent.deepseek.com/) |
| 华为 | AI 应用专家、大模型架构、训练/推理、云与行业解决方案 | 北京、深圳、东莞等 | 专家和架构岗位偏多 | 适合关注 AI 平台、企业应用和交付，纯应用初级岗较少 | [AI 社招专区](https://career.huawei.com/reccampportal/portal5/social-recruitment-ai.html) |
| 零一万物 | AI Agent 工程、AI 全栈、智能体算法、知识底座、Agent 评测 | 北京 | 直接 Agent 岗明确 1–3 年；专家岗同时存在 | 当前 AI 原生公司中对低年限最清晰的样本之一 | [Agent 搜索](https://01ai.jobs.feishu.cn/index/position/list) |
| Dify/LangGenius | Agent/Workflow 平台后端、前端与工程管理 | 中国/远程、苏州 | 详情页未展示统一年限 | Backend Engineer 标题不写 Agent，但工作对象就是 AI 应用与工作流平台 | [Open Roles](https://join.dify.ai/roles.html) |

### 官网可访问，但本轮无法稳定获得可比数量

| 公司 | 当前可确认方向 | 调研限制 | 官网入口 |
| --- | --- | --- | --- |
| 快手 | 可灵、推荐/商业化 AI、大模型应用 | 官网岗位 API 本轮未稳定返回数据，不能据此判断数量少 | [快手社招](https://zhaopin.kuaishou.cn/recruit/e/#/official/social/) |
| 小红书 | 搜索推荐、内容 AI、社区与商业化研发 | 官网可访问，未取得可复核的 Agent 技术岗明细 | [小红书招聘](https://hr.xiaohongshu.com/) |
| 网易 | 游戏 AI、内容与研发效能、传统服务端和数据岗位 | 官网可访问，未取得可比的 Agent 搜索结果 | [网易社招](https://hr.163.com/job-list.html) |
| 携程 | 旅行搜索、智能客服、推荐与数据智能具备应用场景 | 招聘官网可访问，岗位数据动态加载 | [携程招聘](https://careers.ctrip.com/) |
| 哔哩哔哩 | 内容理解、推荐、创作工具、社区后端 | 官网可访问，未验证到当前明确 Agent 社招样本 | [B站招聘](https://jobs.bilibili.com/) |
| 科大讯飞 | 星火大模型、数字员工、行业智能体、政企交付 | 产品方向明确，但本轮未稳定访问社会招聘列表 | [科大讯飞官网](https://www.iflytek.com/) |
| 商汤科技 | 日日新大模型、办公 Agent、代码与行业应用、AI Infra | 官网展示产品方向，当前招聘详情页未稳定访问 | [商汤官网](https://www.sensetime.com/cn/index) |
| 月之暗面 | Kimi、长上下文、搜索与 Agentic 应用 | 官方招聘站可访问，岗位列表为动态页面 | [Moonshot 招聘](https://careers.kimi.com/) |
| MiniMax | 模型与应用、MiniMax Agent、AI 原生产品 | 官网将社招跳转到动态招聘系统，未取得可比数量 | [MiniMax 招聘](https://www.minimax.io/careers) |
| 智谱 | 算法/研发、MaaS、AutoGLM、AI 解决方案 | 官网只稳定展示岗位大类和城市 | [智谱加入我们](https://www.zhipuai.cn/zh/joinus) |
| 百川智能 | 医疗大模型、行业应用、模型与工程 | 官网有加入入口，未获得稳定职位明细 | [百川智能](https://www.baichuan-ai.com/) |
| 阶跃星辰 | 基础模型、多模态、语音与应用 | 本轮未发现稳定的官方社会招聘列表入口 | [阶跃星辰](https://www.stepfun.com/) |
| 联想 | 企业 Agent、AI 工程化、RAG 后端、端侧 AI | 官网可搜索，但检索结果混有较早岗位；不把旧发布日期当当前新增 | [联想招聘](https://jobs.lenovo.com/zh_CN/careers/SearchJobs) |
| 面壁智能 | 端侧模型、GUI Agent、Agent 平台、端侧部署 | 官网只提供 `career@modelbest.cn` 加入入口，未展示结构化社招列表 | [面壁智能](https://www.modelbest.cn/) |
| RAGFlow / InfiniFlow | RAG 引擎、混合检索、Agent 编排、MCP | 官方产品与开源入口可访问，未发现稳定招聘列表 | [RAGFlow](https://ragflow.io/) · [InfiniFlow](https://infiniflow.org/) |

> “无法稳定获得数量”不等于没有岗位，只表示本轮不能用官网证据做可靠统计。投递前应重新打开官网核对。


### 2026-08-04 增量观察：腾讯新增 GameAgent 后台与微信 AI 助手 Harness/Memory

本轮腾讯官方招聘 API 返回 Agent 搜索 172 条。新增高相关技术岗显示，Agent 工程继续向两个方向细化：

| 方向 | 新证据 | 对求职准备的含义 |
| --- | --- | --- |
| GameAgent 后台基础设施 | TEG「AI后台开发工程师」写明 2 年以上，负责 GameAgent 后台系统核心框架、智能 NPC/UGC 等 LLM 驱动业务落地，并要求 Agent Runtime、记忆管理、编排管理和多智能体协作 | 作品需要有真实后端框架、并发稳定性和运行时抽象，不应只停留在聊天 Demo |
| 微信 AI 助手 Harness/Memory | WXG 新增「微信-大模型算法研究员-Agent方向」与「微信小微-大模型算法研究员-Harness合版与记忆方向」，覆盖自动化评测、自进化、跨会话记忆、任务编排和执行上下文管理 | 即使主投后端，也要能解释 Harness、Memory 生命周期、Eval 信号如何驱动 Agent 迭代 |


### 2026-08-07 增量观察：腾讯小程序 Agent 与企业 Managed Agents 继续工程化

本轮是当月第一个周五，全量覆盖 29 家官网入口；除腾讯官方招聘 API 外，多数官网仍只能确认入口可达或动态壳页可达，不能据此推断岗位关闭。腾讯 `Agent` 搜索返回 176 条，本轮新增和变化的高相关技术岗显示 Agent 工程继续从单点应用向运行框架、企业托管智能体和垂直业务 Agent 扩散：

| 方向 | 新证据 | 对求职准备的含义 |
| --- | --- | --- |
| 小程序 Agent 框架 | WXG「微信小程序-AI Agent 开发工程师-小工具」负责 Agent 开发框架、Multi-Agent 分布式架构、沙箱/云环境、消息链路、数据存储和训练基础设施 | 直接 Agent 后端作品要展示运行框架、任务链路、状态存储、沙箱和稳定性，而不是只做模型调用 |
| Coding Agent 与评测 | WXG「微信小程序-AI Agent 算法工程师-Coding方向」覆盖需求建模、任务规划、记忆管理、调试修复、自动化评测、回归验证和 Agent RL | Code Agent 方向需要把任务完成率、工具调用准确率、修改成功率和回归验证做成可观测指标 |
| 企业 Managed Agents | CSIG「企业智能体-全栈开发工程师-WorkBuddy」要求 Managed Agents 编排、运行、治理、评测、Agent Runtime、沙箱隔离、MCP/A2A/ACP、OpenTelemetry Trace 和 Agent Eval | Agent 平台岗正在强调企业级部署、多租户隔离、开放协议、评测和工程 Harness，可作为项目架构标杆 |
| AIOps 与业务 Agent | 腾讯云智能运维、腾讯营销数据产品和视频号直播新增 Agent 岗位，覆盖根因分析、智能修复建议、广告数据产品和主播侧创作效率 | Agent 已继续进入运维、营销数据和内容创作链路；数据产品 Agent 仍作为 P2 兜底，不改变直接 Agent 后端优先级 |


### 2026-08-11 增量观察：Agent Infra 与企业协同 Agent 继续拆到运行底座

本轮按核心 11 家 + 轮换 C 组覆盖；腾讯官方招聘 API 返回 `Agent` 搜索 187 条，是唯一可稳定进行 ID 级增量比较的来源。新增和变化的技术 JD 继续强化“Agent 不是应用壳，而是可运行、可评测、可隔离的平台系统”：

| 方向 | 新证据 | 对求职准备的含义 |
| --- | --- | --- |
| Agent Infra / 沙盒评测底座 | TEG「Agent Infra高级研发工程师」负责大模型 Agent 评估、强化学习和数据制造所需的大规模沙盒平台，支持训练/研究 Agent 框架、自动化评估、实验复现和高并发任务执行 | 项目应补上沙盒执行、Trace、评测任务调度、并发稳定性和结果复现能力；这比单次 Agent 调用更接近平台岗 |
| 企业协同 Agent | 企业微信和 WorkBuddy/CodeBuddy 岗位继续强调 Multi-Agent、工具调用、上下文管理、人机协同接管、MCP、多端全栈、可观测性和私有化/多租户交付 | Agent 后端作品可以优先选择“企业协同/研发效能”场景，展示工具协议、状态机、权限隔离、任务接管和服务治理 |
| 岗位画像分化 | 企业微信「Agent应用」偏算法和后训练，WorkBuddy C 端全栈偏 5 年以上，混元/TEG Infra 偏后端平台 | 对一年经验候选人，仍应优先投直接 Agent 后端/Runtime/平台岗；算法后训练和 5 年以上全栈架构更多作为能力趋势观察 |



### 2026-08-14 增量观察：京东进入可结构化增量，腾讯继续补 Agent 运行与测试底座

本轮按核心 11 家 + 轮换 A 组覆盖。腾讯官方招聘 API 返回 `Agent` 搜索 188 条；京东官方 AJAX 返回 `Agent` 搜索 18 条，并能直接读取列表中的职责与要求。本轮新增证据显示，Agent 工程继续向三类系统扩散：

| 方向 | 新证据 | 对求职准备的含义 |
| --- | --- | --- |
| 低年限 Agent 系统部署 | 京东科技「AI agent开发工程师」写明至少 1 年 AI Agent 系统部署与架构设计经验，负责 RWA 金融资产场景的多智能体、自我演进、合规审查与风险评估 | 这是比负责人岗更值得优先关注的低年限入口；项目要能展示 Agent 系统部署、架构设计、多智能体和业务风控约束 |
| Agent 运行与内容生产底座 | 腾讯轻量云 OpenClaw、腾讯视频 Agent 技术负责人和微信基础 Agent 后端继续强调 OpenClaw、Harness、工作流、插件/工具接入、记忆、评测和服务治理 | Agent 项目应包含工具协议、状态/记忆、任务编排、评测与高可用后端，而不是只展示一次模型调用 |
| 研发质效 / Testing Harness | 腾讯金融科技 AI 测试、腾讯云 AI Agent 测试和京东 Agent Infra 都把 Test Harness、多 Agent、Skill/MCP、Context Learning、缺陷修复与质量闭环写进职责 | Eval/Trace/回放/质量指标已经是 Agent 工程岗位的硬信号，应作为作品和面试讲述的核心模块 |


### 2026-08-01 增量观察：腾讯把 Agent 核心组件拆到 Memory、Eval Infra 与游戏提效

本轮腾讯官方招聘 API 返回 Agent 搜索 169 条。新增和变化的高相关技术岗显示，Agent 岗位继续从应用交付拆到更具体的核心组件与生产基础设施：

| 方向 | 新证据 | 对求职准备的含义 |
| --- | --- | --- |
| Agent Memory | TEG「AI记忆系统研发专家/工程师」写明 1 年以上，负责 core/episodic/semantic/procedural memory、写入整合检索 pipeline、生命周期管理、多智能体记忆协作与评估 | 作品需要把 Memory 做成可解释、可检索、可评估的状态系统，而不是只把聊天历史塞进 prompt |
| Agent 评测与运行底座 | 混元新增「Agent评测Infra工程师」，并更新 Harness Engineer，强调沙盒、依赖、网络、并发调度、Tracing、Observability、Eval Pipeline 和 Regression | Agent 后端项目应包含 Trace、回放、自动评测、失败归因和稳定运行环境 |
| 游戏研发提效 Agent | IEG「三角洲行动」岗位写明 1 年以上大型项目研发经验，直接做 AI Agent 基础设施、调度稳定性和提效功能开发 | 低年限候选人可以用“真实研发流程提效 Agent”作为比泛化聊天助手更贴近岗位的作品方向 |


### 2026-07-28 增量观察：腾讯 Agent 要求继续向 Harness、评测和开放生态细化

本轮腾讯官方招聘 API 仍返回 Agent 搜索 164 条。新增入池的高相关技术岗不再只是“做一个 Agent 应用”，而是继续细分到 Agent Harness 算法、游戏 Agent 评测和 WorkBuddy 开放生态：

| 方向 | 新证据 | 对求职准备的含义 |
| --- | --- | --- |
| Agent Harness 算法 | 微信读书/输入法/秒剪「大模型算法研究员-Agent方向」写明 2 年以上，覆盖几十轮/上百轮工具调用稳定性、Long Context、Memory、Post-Training、Planning、Reflection 和 Skill 自动抽取 | 即使主投后端，也要理解 Harness、Memory 生命周期、Skill 组合和长任务评测，否则很难和算法/平台团队协作 |
| Agent 评测工程 | 轻游 AI Agent「资深游戏测试工程师-Agent评测」要求 Benchmark、自动化评测基座、分级指标、LLM-as-Judge 和缺陷定界 | 作品里应有可复现的 Eval/Trace/Badcase 流程，而不是只展示一次成功运行 |
| Agent 开放生态 | WorkBuddy「开放生态高级开发工程师」负责 Agent/Skill/Connector、SDK/API、插件安全规范、生态治理和评测准入 | Agent 平台岗正在强调外部系统连接、插件治理、版本管理和能力准入，MCP/Skill/Connector 是可迁移能力 |


### 2026-07-27 增量观察：腾讯 Agent 从办公/研发效能扩散到社交、视频与游戏生产

本轮腾讯官方招聘 API 返回 Agent 搜索 164 条。新增或变化的高相关技术岗显示，Agent 工程正在继续向 QQ 社交、腾讯视频内容创作、轻游戏/小游戏生产链路，以及腾讯云 AgentRuntime 平台扩散。

| 方向 | 新证据 | 对求职准备的含义 |
| --- | --- | --- |
| 社交产品 Agent | PCG/QQ「AI应用开发工程师-Agent方向」写明 1 年以上，职责包含 Planning、长期记忆、多 Agent、Durable Execution、沙箱、Skills 与 MCP | 低年限候选人的项目应从 Demo 升级到可持久执行、可评测、可观测的 Agent 后端系统 |
| 内容与游戏生产 Agent | 腾讯视频、轻游戏、微信小游戏岗位覆盖 Workflow/DAG、多 Agent、自动玩游戏、创意工作流与游戏研发流程 Agentic 改造 | Agent 已进入多媒体和游戏生产链路，工具调用、上下文工程和工作流抽象比单点 Prompt 更重要 |
| AgentRuntime / Harness | 腾讯云 AgentRuntime 负责人、沙箱方向和微信 Harness 同步更新 | 沙箱、快照/fork、Skill/MCP、Eval Loop、Trace、运行环境与资源隔离仍是平台岗核心 |


### 2026-07-21 增量观察：腾讯 Agent 平台岗位继续扩散

本轮腾讯官方招聘 API 返回 Agent 搜索 153 条。新增入池的技术岗主要集中在企业微信、微信基础、腾讯云 CodeBuddy/WorkBuddy、AgentRuntime 沙箱和 Harness/Eval：

| 方向 | 新证据 | 对求职准备的含义 |
| --- | --- | --- |
| 企业微信 Agent Framework | 2 年以上「企业微信-AI Agent开发工程师-平台框架/应用」要求 Multi-Agent、MCP、A2A、FunctionCall、任务调度、上下文管理和工程化性能优化 | 项目中应能展示框架接口、工具协议、异步调度和稳定性，而不只是 Prompt/RAG |
| 微信生态 Agent 后端 | 「微信基础-大模型应用开发工程师」不限年限，职责明确写 Agent 系统、长上下文、多模态交互和亿级用户高并发 | 低年限候选人应把高并发后端、上下文管理和 Agent workflow 放进同一个作品 |
| Agent Runtime / Harness / Eval | 腾讯云沙箱、CodeBuddy/WorkBuddy 测评、混元 Harness 和 OpenClaw 同时更新或新增 | Harness、Trace、Eval、Sandbox、可观测性已经成为 Agent 工程核心要求 |

本轮没有把产品、实习、海外、销售、运营、纯模型训练或传统数据开发岗位写入有效索引。

### 2026-07-17 增量观察：腾讯 Agent 岗位继续工程化

本轮腾讯官方招聘 API 可稳定返回 Agent 搜索列表，当前搜索结果为 155 条。新增或更新的高相关技术岗集中在三类场景：

| 方向 | 新证据 | 对求职准备的含义 |
| --- | --- | --- |
| 内容创作 Agent | 腾讯视频 AI Agent 工程师更新为 1 年以上 AI 应用开发经验，要求 Go/Python、高并发服务、Workflow/DAG、多 Agent、Function Calling、MCP 和可观测性 | 低年限候选人应优先准备“Agent + 生产后端 + 可观测性”的完整项目，而不是只做 Prompt/RAG Demo |
| Agent Harness / Code Agent | 混元 Harness JD 明确点名 Cursor / Claude Code / Codex 重度编程经验，以及 tracing、eval、debugging、regression | Code Agent 使用体感、失败模式分析和评测回归能力正在进入工程岗位画像 |
| 垂直研发效能 Agent | UE 游戏研发 Agent、企业微信端侧 Agent、DataBuddy 数据智能 Agent 新增 | Agent Runtime 正在向游戏引擎、企业协作端侧、多端/Browser/Computer Use 和数据智能平台扩散 |

### 字节跳动：按组织与业务方向拆解

字节不是没有相关岗位。上一轮只保留了公司级搜索结果，没有把动态详情稳定写入岗位池，因此造成了“有市场信号、没有具体岗位”的错觉。本轮已逐条打开官网职责确认：

| 官网组织口径 | 实际业务方向 | 当前岗位 | 城市 | 核心工作 | 判断 |
| --- | --- | --- | --- | --- | --- |
| Dev Infra；更高层事业部未公开 | AI Coding / GUI 质量场景 | [大模型应用架构师-Dev Infra](https://jobs.bytedance.com/experienced/position/7615515849081145653/detail) | 深圳 | Agent 工程化，解决效果、效率与成本；Coding/GUI 评测和线上优化 | 直接做 Agent 工程问题，但偏架构与资深服务端，列 P1 挑战岗 |
| Data AML | AI 助手、智能对话与任务规划 | [大模型应用算法工程师（AI助手方向）-Data AML](https://jobs.bytedance.com/experienced/position/7577319763785894149/detail) | 北京 | 对话理解、RAG、工具调用、上下文、ReAct/Plan-and-Execute/Multi-Agent、评测 | 明确要求 1 年以上大模型应用算法经验；方向很直接，但算法要求重 |
| 飞书 | Office Agent：文档、表格、PPT | [大模型应用算法工程师-飞书文档](https://jobs.bytedance.com/experienced/position/7530854460059404552/detail) | 深圳 | Python、工具调用、代码执行、Agentic SFT/RL、评测与业务落地 | 业务场景最清晰；硕士要求，偏应用算法而非后端主线 |
| 产品研发和工程架构 | AI Coding：代码质量与质量风控 | [大模型应用架构师（代码质量/质量风控）](https://jobs.bytedance.com/experienced/position/7633446676003506485/detail) | 深圳 | Agent 效果/效率/成本、Coding/风控评测、架构/策略/数据优化 | 服务端架构型岗位，和后端能力高度相关，但候选人画像偏资深 |
| AI Platform | 智能客服 Agent 与 Self-Evolving Agent | [Agent算法工程师-AI Platform](https://jobs.bytedance.com/experienced/position/7599598898747656453/detail) | 深圳 | Agent 架构、工具、上下文、编排、Agentic RL、Self-Improving、评测 | 方向直接但属于算法岗，更适合作为能力趋势和挑战岗 |
| 火山引擎 / 火山方舟 | Managed-Agent 与 Agent Harness | [豆包大模型Agent算法工程师-火山方舟](https://jobs.bytedance.com/experienced/position/7601812921946491189/detail) | 深圳 | 自有 Harness、Built-in Tools、Context、多 Agent、MCP/A2A、端到端 Eval | 当前字节最明确的 Harness 岗，方向极相关但偏算法与前沿工程 |

这里的 `Agent 1895`、`大模型应用 1908`、`火山方舟 116` 都是官网全文搜索命中，不是技术岗数量，更不是招聘人数。对单个岗位的判断以“组织 + 业务场景 + 职责”三者为准，而不是以检索词为准。

### 阿里云：企业级 Agent 产品与交付

阿里云官网用 `Agent` 搜索显示 62 个命中，但当前第一页只稳定展示 10 条、第二页异常显示空列表。第一页是 5 条技术岗和 5 条“秒悟”产品运营岗，因此 62 只能作为官网搜索信号，不能当作当前可投技术岗数量。本轮逐条确认了三个代表技术岗：

| 事业部/产品线 | 业务方向 | 岗位 | 城市 | 年限 | 判断 |
| --- | --- | --- | --- | --- | --- |
| 云智能集团 | 企业级 Agent 标准产品底座、AI 原生全栈 | [AI原生全栈工程师-Agent开发](https://careers.aliyun.com/off-campus/position-detail?lang=zh&positionId=100015603017) | 北京/杭州/成都/西安 | **1 年以上** | 当前三家重点公司里最匹配用户年限的直接 Agent 岗；要求 Planning、Memory、知识工程、多 Agent、RAG、MCP、Eval、Harness |
| 云智能集团 | Agentic Search、Deep Research、通用 Agent 平台 | [AI Agent研发工程师-AI搜索](https://careers.aliyun.com/off-campus/position-detail?lang=zh&positionId=100011023003) | 北京/杭州 | 5–8 年，优秀者可放宽 | Runtime、Workflow、Tool Registry、Memory Store、GraphRAG、评测、可观测和分布式后端非常完整，但明显偏资深 |
| 云智能集团 | 政企、教育、金融、企业办公的私有化 Agent | [AI Agent应用工程师-专有云](https://careers.aliyun.com/off-campus/position-detail?lang=zh&positionId=100015523003) | 北京/杭州 | 5 年以上 | 强调 Agent Runtime、编排、工具、权限、安全、运维、回放和 ToB 交付，是企业级 Agent 产品架构岗 |

第一页另外还能确认 `海外业务-AI Agent研发工程师` 和 `ATH事业群-AI Agent研发工程师-AI搜索` 两条技术岗位元数据，但本轮未把未展开的详情写进量化岗位池。

### 蚂蚁集团：金融安全、AI Coding 与垂类评测

蚂蚁官网前端当前在浏览器中加载异常，但官方招聘 API 可返回同一社会招聘数据。本轮 `Agent` 搜索得到 29 条命中，其中技术类 20 条：开发 7、算法 11、数据 1，另有一条无线端技术岗；5 条职位从 2 年经验起。下面只列与目标最相关的技术岗：

| 事业部/产品线 | 业务方向 | 岗位 | 城市 | 年限 | 判断 |
| --- | --- | --- | --- | --- | --- |
| CodeFuse 产品线；具体事业部未公开 | AI 原生 IDE、研发 Agent 平台、SDK/Runtime | [研发 Agent 平台工程师](https://talent.antgroup.com/off-campus-position?positionId=25071705769373) | 杭州 | **2 年以上** | MCP、Skill、Connector、Memory、日志排障、可观测和 Eval 很匹配；同时要求 TypeScript/Node.js、React 和复杂前端/IDE 能力 |
| 资金安全；具体事业部未公开 | 支付与资金安全的可靠 Agent | [安全Agent工程师](https://talent.antgroup.com/off-campus-position?positionId=260707010772161) | 杭州 | **2 年以上** | 记忆、推理、工具编排、反思纠错、SDK/API、观测与自动评测；金融安全背景是加分项而非唯一入口 |
| 智能体安全；具体事业部未公开 | 智能体安全架构和核心能力交付 | [智能化工程师-Agent安全](https://talent.antgroup.com/off-campus-position?positionId=26042709798863) | 杭州/成都 | **2 年以上** | 明确要求 Agent 落地、Context/Prompt、工具调用、Java/Python/JS，以及操作系统、网络、算法基础 |
| 垂类大模型；具体事业部未公开 | 金融、医疗、小程序/APP Agent 评测 | [大模型 Benchmark 与评测体系工程师/专家](https://talent.antgroup.com/off-campus-position?positionId=26012608542168) | 北京/杭州 | 3 年以上 | 自动化评测、错误归因、Benchmark、长程记忆、UI 理解、任务规划与工具调用，偏算法评测 |
| 具体事业部未公开 | Agent 后训练、多智能体、Deep Research | [智能体算法专家/工程师](https://talent.antgroup.com/off-campus-position?positionId=25070405541401) | 杭州/北京 | 3 年以上；博士或优秀硕士 | 纯算法研究权重高，不作为 Agent 后端主投，但能说明 Agentic RL/Multi-Agent 的趋势 |
| 研发效能；具体事业部未公开 | 基于 Agent 的 DevOps 架构 | [Agent研发架构师](https://talent.antgroup.com/off-campus-position?positionId=260617010533160) | 杭州 | 5 年以上 | 研发效能平台、CI/CD、自动化测试和全局架构，作为资深趋势岗 |
| 研发效能度量；具体事业部未公开 | AI Coding 度量与数据 Agent | [Agent研发工程师（度量方向）](https://talent.antgroup.com/off-campus-position?positionId=260618010534590) | 北京 | 3–5 年数据研发 | 与用户当前大数据背景最接近，但属于 P2 兜底，不改变直接 Agent 主线 |

三家公司共同说明：招聘方已经把 `Agent核心机制 + 后端工程 + Eval/Trace + 业务场景` 合并成一个候选人画像。详细的学习清单校准见[求职学习清单与 Agent 招聘要求校准](求职学习清单与Agent招聘要求校准.md)。

## 当前代表岗位明细

| 公司 | 岗位 | 主分类 | 城市 | 年限/学历 | 核心职责与要求 | 与当前背景的关系 |
| --- | --- | --- | --- | --- | --- | --- |
| 零一万物 | [AI Agent 工程师](https://01ai.jobs.feishu.cn/index/position/7641848138185705755/detail) | 直接 Agent 开发 | 北京 | **1–3 年；本科+** | LangGraph/OpenClaw、Python/JS，有实际 Agent 项目经验 | 当前最明确的低年限主投样本 |
| 滴滴 | [AI Agent 开发工程师](https://talent.didiglobal.com/social/p/65072) | 直接 Agent 开发 | 北京 | 未写固定年限；本科+；**3 个 HC** | Planning、任务拆解、MCP、Memory、LangChain/LangGraph、高并发高可用；Python/Java/Go | 职责与目标高度一致，当前优先级最高 |
| DeepSeek | [服务端开发工程师-Agent 后端方向](https://app.mokahr.com/social-recruitment/high-flyer/140576#/job/2eb2e75d-29f3-47b5-bb10-39f12547d398) | Agent 后端 | 北京、杭州 | 全职/实习；未固定年限 | Agent 执行环境快照、框架接入、稳定评测、Agent 数据；强调计算机基础和编程 | 不要求把数据作为主线，直接做 Agent 后端 |
| 拼多多 | [Agent开发工程师](https://careers.pddglobalhr.com/jobs/detail?code=T023916) | 直接 Agent 开发 | 上海 | 未写固定年限；本科+ | 规划、记忆、工具、反思、多 Agent、FastAPI、Docker/K8s、Eval/Observability | 技术栈最完整，适合作为三个月后的挑战岗 |
| 拼多多 | [商业化-Agent后端开发工程师](https://careers.pddglobalhr.com/jobs/detail?code=T024178) | Agent 后端 | 上海 | 2 年+；本科+ | RAG、Tool-use、Memory、Planning、高并发分布式；Java/C++/Go/Python | 年限略差一年，但生产后端经验可支撑挑战 |
| 拼多多 | [电商-Agent后端工程师](https://careers.pddglobalhr.com/jobs/detail?code=T024133) | Agent 后端 | 上海 | 未写固定年限 | 多 Agent 分层架构、RAG、缓存、SLA、BadCase 干预；Python/Java | 直接做业务 Agent 与后端，不是桥接岗 |
| 腾讯 | [AI应用开发工程师-Agent方向](https://careers.tencent.com/search.html?keyword=Agent) | 直接 Agent 开发 | 深圳 | **1 年+** | Planning、长期记忆、多 Agent、RAG、Durable Execution、沙箱、Skill/MCP、评测 | 当前大厂中低年限最值得关注的岗位之一 |
| 腾讯 | [混元 AI Agent Harness Engineer](https://careers.tencent.com/search.html?keyword=Agent) | Agent Harness | 北京、深圳 | 2 年+ | Tracing、Observability、自动 Eval、A/B、回归、调试、评测和数据管道 | 说明 Harness 是真实工程岗位，不只是概念 |
| 腾讯 | [腾讯云乐享-全栈Agent研发工程师](https://careers.tencent.com/search.html?keyword=Agent) | Agent 全栈 | 深圳 | 3 年+ | Context Management、前后端、模型集成、性能监控、端到端交付 | “AI 全栈”岗位的直接证据 |
| 百度 | [DuMate_全栈研发工程师](https://talent.baidu.com/jobs/social-list) | Agent 全栈/平台 | 北京 | 官网未固定年限；**10 个 HC** | Agent、Skill、Memory、Trace、平台稳定性与端到端研发 | 岗位数量明确，偏平台和产品交付 |
| 美团 | [智能体（Agent）工程师](https://zhaopin.meituan.com/web/social?keyword=Agent) | 直接 Agent 开发 | 北京 | 官网未固定年限 | Harness、上下文治理、工具编排、长程规划、自我纠错、规模化落地 | 作为内部市场基准，职责非常接近目标画像 |
| 美团 | [到餐-全栈 Agent Builder](https://zhaopin.meituan.com/web/social?keyword=Agent) | Agent 全栈 | 北京 | 官网未固定年限 | 商业模式、产品定义、技术架构和端到端 Agent 构建 | 证明全栈兴趣存在明确岗位承载 |
| DeepSeek | [Agent Harness 团队-研发/工程](https://app.mokahr.com/social-recruitment/high-flyer/140576#/job/8d40c764-d2b2-49b1-826c-e3f2adb75c01) | Agent Harness | 北京、杭州 | 工程方向未写年限；知名高校本科+ | Context、Memory、Subagent、多 Agent、Skills、MCP、评测和 AI Coding | 方向极匹配但候选人要求高，作为强挑战岗 |
| Dify | [Backend Engineer](https://join.dify.ai/roles.html) | AI 应用平台后端 | 中国/远程 | 官网未固定年限 | 建设 AI 工作流和 Agent 应用平台，开源产品交付 | 标题不含 Agent，但实际工作非常贴近 Agent 平台 |

### 已失效但值得保留的岗位信号

- 滴滴[高级研发工程师-大模型工程](https://talent.didiglobal.com/social/p/61344)曾明确要求 1–3 年后端经验，但 2026-07-11 已显示“已结束”。它仍证明低年限大模型应用后端真实存在，但不再列为可投岗位。
- 上一版保存的若干百度详情 UUID 本次未稳定回显完整 JD，已从推荐表移除；只有当前列表仍可见的职位才计入有效池。

## 岗位命名词典

### 最值得直接搜索的名称

| 岗位名称 | 实际工作重点 | 常见公司样本 |
| --- | --- | --- |
| Agent开发工程师 / AI Agent工程师 | Agent 核心模块、工具调用、流程编排、业务落地 | 京东、拼多多、小米、美团、腾讯 |
| Agent技术研发工程师 | Runtime、执行引擎、平台能力、开发者体验 | 字节 |
| Agent架构研发工程师 | 任务规划、工具、记忆、多 Agent、架构演进 | 字节、腾讯 |
| 大模型应用开发工程师 | RAG、Agent、服务化、业务系统集成 | 京东、滴滴、百度 |
| AI产品研发工程师 | 从文档/数据到 RAG/Agent，再到部署交付 | 百度 |
| Agent Harness工程师 | 运行控制、上下文、调度、评测、Trace、调试、可靠性 | 字节、腾讯、DeepSeek |
| 智能体平台工程师 / Agent平台研发 | 多租户平台、Agent 配置、Skill/插件、调度与治理 | 拼多多、小米、美团 |
| Agent全栈开发 / 全栈Agent Builder | 端到端交付 Agent 产品，可能包含界面但不止前端 | 小米、美团、百度、DeepSeek |
| 数据Agent / Agent数据平台 | Text-to-SQL、数据检索分析、数据飞轮、评测数据 | 滴滴、美团、DeepSeek |
| AI Search / RAG研发 | 向量检索、搜索问答、知识工程、检索引擎 | 百度、DeepSeek、字节 |
| Agent评测工程师 | Eval 数据集、任务完成率、工具调用准确率、回归与监控 | 小米、腾讯、字节、百度 |

### 标题不写 Agent，但职责实际属于 Agent/RAG 的名称

- AI 产品研发工程师。
- 大模型工程 / 大模型应用工程。
- AI 应用研发工程师。
- 后端研发工程师—大模型应用方向。
- 智能搜索 / AI Search 引擎研发。
- 知识工程 / 企业知识库研发。
- 数据智能 / 商业智能工程师。
- 研发效能 AI 工程师。
- 大模型平台研发 / AI 平台研发。
- 生成式 AI 应用工程师。

### “AI 全栈”到底是什么意思

市场里的“全栈”至少有三种含义：

| 类型 | 覆盖范围 | 是否一定要求复杂前端 |
| --- | --- | --- |
| AI 系统全栈 | 数据/RAG → Agent → 服务 → 部署 → Eval | 不一定 |
| 产品交付全栈 | 需求 → 原型 → 后端/Agent → 简单界面 → 用户反馈 | 通常需要能做界面，但不必是前端专家 |
| 传统 Web 全栈 | React/Vue → API → 数据库 → 部署 | 是，但这不是多数 Agent 全栈岗的唯一含义 |

因此，用户关于“全栈好像没有明确岗位”的观察应修正为：**统一名称确实不多，但岗位明确存在，而且更多被写成 AI 应用研发、产品研发、Agent Builder 或端到端研发。**

## 招聘要求归纳

以下计数来自 72 个当前有效岗位。只统计本轮官网列表或详情页中**明确出现**的能力；官网只展示标题而未展开要求时不会推断，因此这些数字是可验证下限，不是市场真实比例。

### 这类岗位每天实际在做什么

| 工作块 | 具体产出 | 不是在做什么 |
| --- | --- | --- |
| Agent 核心执行 | 任务规划与拆解、Tool/Function Calling、MCP/Skill、Memory、Context、多 Agent、异常恢复 | 不是只调用一次模型 API |
| 生产后端 | Agent 服务、任务调度、状态持久化、缓存/MQ/RPC、并发与 SLA、成本和延迟优化 | 不是只写 Prompt Demo |
| RAG 与知识 | 文档解析、切分、混合检索、Rerank、权限、证据引用、知识更新 | 不是把文档塞进向量库就结束 |
| Harness 与平台 | Runtime、沙箱/快照、长任务、Trace、回放、调试工具、开发者平台 | 不等同于纯模型推理 Infra |
| 评测与质量 | 任务成功率、工具调用准确率、回归、LLM-as-Judge、BadCase 归因、安全与成本门禁 | 不是上线后凭主观体验判断 |
| 产品交付 | 将业务流程拆成 Agent 可执行步骤，和算法/产品/前端协作，从原型走到线上 | 不要求人人都是传统前端专家 |

### 能力出现次数

| 能力标签 | 明确出现 | 读法 |
| --- | ---: | --- |
| Agent 核心开发 | 65/72 | 几乎全部目标岗都不是“AI 沾边岗” |
| 产品化/业务落地 | 64/72 | 招聘方普遍要求从方案到线上闭环 |
| 后端工程 | 30/72 | 直接出现服务端、平台、高并发或稳定性职责；部分全栈/平台岗未重复打 Backend 标签 |
| Eval / 评测 | 37/72 | 已成为 Agent 工程主能力，不只是测试团队工作 |
| Tool / Function Calling | 34/72 | 最普遍的 Agent 执行机制 |
| Planning | 28/72 | 复杂任务拆解与长程执行反复出现 |
| RAG | 26/72 | 仍是应用岗位的重要组成，但不是全部 |
| Memory | 24/72 | 长短期记忆、会话状态和生命周期管理 |
| 分布式系统 | 15/72 | 平台、后端和高并发岗尤其集中 |
| Multi-Agent | 16/72 | 多智能体已进入产品工程，而非只停留在论文 |
| Observability / Trace | 15/72 | 调试、回放、监控和失败归因 |
| Agent 平台 | 11/72 | Runtime、编排、开发平台和基础设施 |
| Skill | 12/72 | 与 Tool、MCP、插件一起形成新的工程接口 |
| Context Engineering | 16/72 | 上下文构建、压缩、治理和长任务管理 |
| 高可用 | 9/72 | 生产后端的明确要求 |
| Harness | 8/72 | 字节、阿里、腾讯、DeepSeek、美团等已直接用作岗位名或职责 |
| MCP | 10/72 | 已从生态概念进入大厂 JD |
| 测试开发 | 6/72 | Agent 自动化测试、评测和 CI/CD |
| 高并发 | 6/72 | 大厂业务 Agent 的典型工程门槛 |

### 编程语言与全栈

| 能力 | 明确出现 | 结论 |
| --- | ---: | --- |
| Python | 16/72 | Agent 框架和快速原型最常直接点名；实际需求只会更高 |
| Go | 7/72 | 腾讯、滴滴、阿里和蚂蚁的生产 Agent 服务均有出现 |
| Java | 8/72 | 拼多多、滴滴、阿里、蚂蚁的企业后端并未因为 AI 放弃 Java |
| 前端 | 4/72 | 该标签只统计明确 Frontend；CodeFuse、AI 原生全栈等岗位另以 React/TypeScript/Fullstack 标注 |
| 明确写“全栈” | 6/72 | 岗位真实存在，但数量明显少于 Agent 后端/平台 |
| Docker / Kubernetes | 详情页明确 2/72 | 只代表本轮明确打标签的下限；平台与后端岗位仍普遍强调部署和运行环境 |

语言不是岗位族的核心边界。更稳定的候选人画像是：能用 Python 完成 Agent 机制与原型，同时至少能用 Java 或 Go 中的一种承担生产后端；具体语言可随团队变化。

### 经验与学历

| 层级 | 常见要求 | 对当前状态的含义 |
| --- | --- | --- |
| 1–3 年工程岗 | 当前明确样本是零一万物 AI Agent 工程师；腾讯另有 1 年以上样本 | 应作为三个月后重点搜索区间 |
| 2–3 年 Agent 后端 | 已有生产后端经验，同时要求 Agent/RAG 实践 | 可以挑战，不要只因差 1 年自动放弃 |
| 3–5 年高级岗 | 要求独立负责模块、系统设计或从 0 到 1 产品 | 作为能力标杆和少量挑战岗 |
| 5 年以上/专家 | 平台架构、跨团队推进、团队或方向负责人 | 暂不作为主投 |
| 模型算法岗 | 硕士/博士更常见，要求 PyTorch、训练、RLHF/RL、论文 | 除非后续转向算法，否则只作市场参照 |

当前 72 条中，33 条完全未公开固定年限或只写了模糊经验信号，2 条明确不限年限，12 条直接写 3 年以上，另有 2 条写 3–5 年或 3 年以上专项经验；7 条直接写 2 年以上，4 条直接写 5 年以上，另有 1 条写 5–8 年；还有 7 条以高级、资深、专家或负责人标注。可明确看作低年限入口的有 4 条：1–3 年、1 年以上、字节 Data AML 的 1 年以上大模型应用算法经验，以及阿里云 AI 原生全栈的 1 年以上智能体研发经验。学历方面 52 条列表页没有给出可核对信息，不能把“未展示”理解为“不限学历”。

## 大数据开发背景的价值

这一节只解释已有经验如何转化，不代表求职方向。主投仍是直接 Agent 开发；只有 P0/P1 机会不足时，才考虑 P2 数据交叉岗。

### 可以直接迁移的能力

| 原有能力 | Agent/RAG 岗中的对应价值 |
| --- | --- |
| 离线/实时数据链路 | RAG 数据摄取、知识更新、评测数据生成、Agent 数据飞轮 |
| Spark/Flink/Kafka | 大规模数据预处理、实时反馈、事件驱动 Agent、链路稳定性 |
| 数仓与 SQL | Text-to-SQL、数据 Agent、指标语义、分析类 Agent |
| 分布式系统经验 | Agent 平台、任务调度、缓存、消息队列、高可用服务 |
| 数据质量与监控 | RAG 召回质量、评测集、线上 Bad case、可观测性 |
| 业务数据理解 | 能把 AI 做进真实业务，而不是停留在聊天 Demo |

### 仅作为兜底的交叉岗位

1. AI Search / RAG 检索研发。
2. Agent 数据平台 / 数据飞轮工程师。
3. 数据 Agent / Text-to-SQL 工程师。
4. 大模型数据工程师。

大模型应用后端、Agent 平台、Harness 和 Agent 评测不再归入“桥接岗”，它们是直接目标岗位。

### 不应误判的地方

- 只会传统数仓开发并不会自动匹配 Agent 岗，需要补上工具调用、上下文、评测与服务化证据。
- 不必把自己包装成大模型训练算法工程师；应用后端岗位并不要求所有人都会预训练和 RLHF。
- Python/Java 都不是单独的核心竞争力，招聘方更看能否完成可靠的端到端系统。

## 与当前状态相关的岗位分层

### 三个月后重点关注

- 1–3 年 Agent 工程 / 大模型应用后端。
- 直接写 Agent 开发、Agent 后端、Harness、Runtime 的岗位。
- 不限年限或未写固定年限的 Agent 工程师。
- Agent 全栈、AI 应用平台后端、Agent 评测工程。
- 强调 Go/Java/Python 任选一种、后端基础和快速学习能力的岗位。

### 可以挑战

- 2 年以上 Agent 后端，例如拼多多商业化 Agent 后端、腾讯元宝 Agent 架构。
- 3 年以上但职责高度贴合的 Agent 核心开发、大模型应用后端和全栈 Agent。
- 标题写“高级”，但 JD 没有明确要求独立带团队或 5 年以上经验的岗位。

### 机会不足时再考虑

- AI Search / RAG 检索研发。
- Code Agent 数据、Agent 数据平台、Text-to-SQL。
- 评测数据、知识底座和数据飞轮，但岗位主要职责必须仍服务 Agent 产品。

### 暂不作为主投

- 5 年以上架构师、负责人、Tech Lead。
- 以预训练、后训练、Agentic RL、模型结构创新为主的算法岗。
- 强制要求硕博、顶会论文和大规模训练经验的研究岗。
- 纯前端、纯产品经理，以及与 Agent 应用工程无明显关系的传统数据岗。

## 建议保存的搜索关键词

不能只搜 `Agent`。后续刷新岗位时，每家公司至少轮流搜索：

```text
Agent
智能体
大模型应用
AI应用
生成式AI
AI后端
AI产品研发
Agent平台
大模型平台
Harness
RAG
知识工程
AI Search
数据Agent
Text-to-SQL
Agent评测
大模型数据工程
研发效能AI
AI全栈
Agent Builder
```

组合搜索时优先使用：

```text
Agent + 后端
大模型应用 + 研发
RAG + 工程师
智能体 + 平台
Agent + 评测
数据 + Agent
AI + 全栈
```

## 对未来三个月的简短建议

这不是详细学习计划，只是由招聘要求反推的优先级：

1. 操作系统已经覆盖了主要主题，不需要因“原计划 7 天”而焦虑；达到能复述、能回答面试题、能联系后端场景后，就转成滚动复习。网络优先补 HTTP、TCP、连接、超时与流式输出。
2. 不必等 MySQL/Redis 八股全部完成才做 Agent。尽早用一个生产型 Agent 项目把工具调用、MCP、Memory、Context、RAG、Eval/Trace 和后端可靠性串起来。
3. 项目必须有可复现的评测、日志/Trace、失败案例、成本和延迟指标，不能只展示“模型能回答问题”。
4. 前端补到能够独立交付和演示即可；如果重点挑战蚂蚁 CodeFuse，则 TypeScript/Node.js/React 的优先级会上升。
5. Python 用于 Agent 生态与原型，Java 或 Go 保留一种生产后端能力；算法题持续小剂量，不挤压项目闭环。具体校准见[求职学习清单与 Agent 招聘要求校准](求职学习清单与Agent招聘要求校准.md)。

## 当前最值得先看的官网入口

按与当前目标的相关性排序：

1. [阿里云 AI 原生全栈工程师-Agent开发](https://careers.aliyun.com/off-campus/position-detail?lang=zh&positionId=100015603017)：明确 1 年以上，企业级 Agent 产品底座，当前与用户年限和目标最贴近。
2. [蚂蚁研发 Agent 平台工程师](https://talent.antgroup.com/off-campus-position?positionId=25071705769373)：2 年以上，CodeFuse、Runtime、MCP、Skill、Memory、可观测与评测；全栈/IDE 要求较强。
3. [蚂蚁安全Agent工程师](https://talent.antgroup.com/off-campus-position?positionId=260707010772161)：2 年以上，直接做资金安全场景的可靠 Agent、SDK/API、观测和自动评测。
4. [字节豆包大模型Agent算法工程师-火山方舟](https://jobs.bytedance.com/experienced/position/7601812921946491189/detail)：Managed-Agent、Harness、MCP/A2A 和端到端 Eval，方向最直接但偏算法/前沿工程。
5. [字节 Agent算法工程师-AI Platform](https://jobs.bytedance.com/experienced/position/7599598898747656453/detail)：智能客服、Agentic RL、Self-Evolving Agent，作为算法挑战岗和趋势样本。
6. [零一万物 AI Agent 工程师](https://01ai.jobs.feishu.cn/index/position/7641848138185705755/detail)：明确 1–3 年，直接 Agent 应用研发。
7. [滴滴 AI Agent 开发工程师](https://talent.didiglobal.com/social/p/65072)：当前可申请，3 个 HC，职责覆盖 MCP、Memory、LangGraph 和高并发后端。
8. [腾讯 Agent 搜索](https://careers.tencent.com/search.html?keyword=Agent)：重点看 1 年以上 AI 应用开发、元宝、混元 Harness、协作工具和腾讯视频。
9. [拼多多 Agent 开发工程师](https://careers.pddglobalhr.com/jobs/detail?code=T023916)：未固定年限，Agent 机制和部署要求完整。
10. [DeepSeek Agent 后端](https://app.mokahr.com/social-recruitment/high-flyer/140576#/job/2eb2e75d-29f3-47b5-bb10-39f12547d398)：全职/实习合并招聘，直接建设 Agent 执行与评测后端。

## 宏观参考

- [新华社：互联网企业云端招聘活动](https://www.xinhuanet.com/tech/20260703/8e658de8864c4e6e96df04d35ce93ed4/c.html)：披露腾讯、字节等公司的总体岗位规模，并提到大模型应用、AI 搜索与 Agent 岗位。这里的数字是企业总招聘需求，不是 Agent 岗数量。
- [中国经济网：2026 春招 AI 岗位占比提升](https://www.ce.cn/xwzx/gnsz/gdxw/202603/t20260311_2818417.shtml)：用于观察行业趋势，不替代官网当前 JD。

## 刷新方法

招聘信息变化快。本报告采用“详细初始化 + 每周增量 + 每月全量复核”：

1. 每周二、周五 02:00 固定扫描 11 家核心公司，并轮换 6 家观察公司。
2. 列表阶段只读取岗位 ID、标题、城市、部门、更新时间和链接；新增或变化时才深读 JD。
3. 同一岗位 ID 比较标准化内容指纹；要求变化不重复算新增。
4. 官网明确结束时关闭；普通访问失败连续两次才进入疑似关闭。
5. 每月第一个周五检查全部 29 家公司，重新校准数量和要求趋势。
6. 每次最多深读 10 个新增/变化 JD，P2 数据交叉岗最多 2 个。

## 主动回忆

1. 为什么不能把官网 Agent 搜索结果数直接当成 Agent 开发岗位数？
2. “AI 全栈”与传统 Web 全栈最大的区别是什么？
3. 哪三类岗位最能复用大数据开发经验？
4. 为什么评测、Trace 和失败案例已经成为 Agent 岗的高频要求？
5. 哪些岗位名称没有写 Agent，但实际上属于大模型应用开发？
