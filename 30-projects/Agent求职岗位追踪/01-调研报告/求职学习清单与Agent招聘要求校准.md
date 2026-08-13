---
type: source
status: active
tags: [job-search, agent, backend, learning-plan, recruitment]
created: 2026-07-11
updated: 2026-07-11
source_type: PDF清单与官方社会招聘JD
source_url: 字节跳动、阿里云、蚂蚁集团招聘官网
author: 用户计划 + Codex市场校准
related:
  - "[[中国互联网AI与Agent招聘市场调研]]"
---

# 求职学习清单与 Agent 招聘要求校准

## 基本信息

本笔记对照三份初始学习清单和 2026-07-11 当前社会招聘 JD：

1. [学习清单-社招-7.5.pdf](../04-参考资料/学习清单-社招-7.5.pdf)：计算机基础、后端、算法、大模型/RAG 的总体入口。
2. [后端&大模型&手撕算法每日清单.pdf](../04-参考资料/后端&大模型&手撕算法每日清单.pdf)：15 天后端、15 天大模型/RAG，以及持续 3–4 个月的算法练习。
3. [操作系统&计算机网络每日清单.pdf](../04-参考资料/操作系统&计算机网络每日清单.pdf)：7 天操作系统、7 天网络。

用户当前情况：操作系统已经学习约一周，并认为相对原计划超时。该判断暂时作为`用户假设`；是否真的超时，应看是否已经能解释核心机制并用于面试，而不是只看日历天数。

## 核心观点

原清单适合建立传统后端与大模型应用基础，但不能直接覆盖当前 Agent 岗位要求。当前招聘把下面几组能力放在同一个候选人画像里：

```text
Agent核心机制
+ 生产后端
+ RAG与知识工程
+ Eval/Trace/可观测性
+ 工具/MCP/权限与安全
+ 端到端产品交付
```

因此不建议把学习路线理解为严格串行的“操作系统全部学完 → MySQL/Redis全部学完 → RAG全部学完 → 最后才做 Agent”。更贴近岗位的方式是：系统基础达到面试可解释水平后，尽早进入一个生产型 Agent 项目，让后端、数据库、网络、评测和 Agent 机制围绕同一个系统继续补齐。

## 原清单结构

| 模块 | 原计划 | 优点 | 当前缺口 |
| --- | --- | --- | --- |
| 操作系统 | 内存、进程、调度、网络系统，约 7 天 | 覆盖面试重点；对并发、进程和服务端理解有帮助 | 不能无限深挖；应以能解释和排查为完成标准 |
| 计算机网络 | 基础、HTTP、TCP、IP，约 7 天 | 与后端连接管理、超时、重试、流式输出直接相关 | 需要和 Agent 长连接、SSE、流式响应、RPC、网关结合 |
| 后端 | MySQL 5 天、Redis 6 天、微服务等 4 天 | 补齐传统后端面试能力 | 偏八股；缺异步任务、消息队列、服务治理、可观测、Docker/K8s 的项目闭环 |
| RAG | 传统 RAG、KG/GraphRAG，约 6 天 | 是 Agent 应用的重要数据与知识基础 | 市场不再只招 RAG，需要和 Tool、Planning、Memory、Eval 组合 |
| 大模型应用 | 原理、部署、微调、提示、多模态，约 9 天 | 能建立大模型知识框架 | 缺 Agent Runtime、Harness、Context Engineering、MCP、权限、安全与成本治理 |
| 算法 | 每天约 2 题，持续 3–4 个月 | 符合大厂面试现实 | 应持续但不挤占项目与生产工程能力 |

## 当前招聘证据

### 字节跳动

- [豆包大模型Agent算法工程师-火山方舟](https://jobs.bytedance.com/experienced/position/7601812921946491189/detail)：Managed-Agent、方舟自有 Harness、Built-in Tools、Context、多 Agent、MCP/A2A、端到端 Eval。
- [Agent算法工程师-AI Platform](https://jobs.bytedance.com/experienced/position/7599598898747656453/detail)：任务规划、工具调用、上下文、Agentic RL、Self-Evolving Agent，并落地智能客服。
- [大模型应用架构师-Dev Infra](https://jobs.bytedance.com/experienced/position/7615515849081145653/detail)：Agent 效果、效率、成本，以及 Coding/GUI 场景评测。

### 阿里云

- [AI原生全栈工程师-Agent开发](https://careers.aliyun.com/off-campus/position-detail?lang=zh&positionId=100015603017)：**1 年以上**，建设企业级 Agent 标准产品底座；要求 Planning、Memory、知识工程、多 Agent、RAG、MCP、Eval、Harness 和至少一种 Python/Go/Java/TypeScript。
- [AI Agent研发工程师-AI搜索](https://careers.aliyun.com/off-campus/position-detail?lang=zh&positionId=100011023003)：Agentic Search、Deep Research、Runtime、Workflow、Tool Registry、Memory Store、GraphRAG、评测与可观测；岗位偏 5 年以上。
- [AI Agent应用工程师-专有云](https://careers.aliyun.com/off-campus/position-detail?lang=zh&positionId=100015523003)：ToB 私有化交付，强调 Runtime、编排、工具、知识、权限、安全、运维、回放和评估；岗位偏 5 年以上。

### 蚂蚁集团

- [研发 Agent 平台工程师](https://talent.antgroup.com/off-campus-position?positionId=25071705769373)：**2 年以上**，CodeFuse IDE、Agent SDK/Runtime、Skill、MCP、Connector、Memory、日志排障、可观测与评测；同时重视 TypeScript/Node.js、React 和复杂交互。
- [安全Agent工程师](https://talent.antgroup.com/off-campus-position?positionId=260707010772161)：**2 年以上**，资金安全领域的记忆、推理、工具编排、反思纠错、SDK/API、观测和自动评测。
- [智能化工程师-Agent安全](https://talent.antgroup.com/off-campus-position?positionId=26042709798863)：**2 年以上**，Agent 核心模块、全链路追踪、回测、安全与工程化；明确要求数据结构、算法、网络和操作系统基础。

## 招聘要求反推的学习重点

| 优先级 | 学习重点 | 为什么 |
| --- | --- | --- |
| P0 | Agent 核心闭环：Planning、Tool Calling、MCP、Memory、Context、Workflow | 三家岗位反复出现，是真正的直接目标能力 |
| P0 | 生产后端：API、异步任务、数据库、缓存、错误恢复、并发、高可用 | Agent 岗不是只调模型 API；稳定执行与状态管理是核心 |
| P0 | Eval、Trace、回放、Bad Case、成本和延迟 | 字节、阿里、蚂蚁都把评测与可观测写进核心职责 |
| P1 | RAG 与知识工程 | 仍然重要，但应作为 Agent 的一个工具和数据能力，不再单独作为主线 |
| P1 | AI Coding / Harness / Agent Runtime | 字节火山方舟、阿里 AI 原生全栈、蚂蚁 CodeFuse 都是明确招聘方向 |
| P1 | 操作系统和网络的面试级理解 | 蚂蚁 2 年岗直接点名；后端稳定性、流式输出、并发与排障也依赖它们 |
| P2 | 模型微调、Agentic RL、SFT | 算法岗权重高；对当前“Agent 后端”目标是理解与加分，不是首要门槛 |
| 持续项 | 手撕算法 | 保持面试通过率，但不应吞掉项目和工程实践时间 |

## 对“操作系统已经超时一周”的判断

### 用户假设

操作系统原计划 7 天左右，现在已学习一周，感觉超时。

### Codex 评估

这不一定是无效超时。现有学习记录已经覆盖内存、进程/线程、调度、IPC、同步互斥、死锁、Socket、页置换、inode 和文件系统，已经跨过了最重要的一批面试主题。

真正需要控制的是继续深挖的边际收益。可以把操作系统阶段的完成标准改成：

1. 能用自己的话解释重点机制，而不是继续追求完整读完所有材料。
2. 能回答进程/线程、虚拟内存、上下文切换、锁、死锁、文件系统与 IO 的典型面试题。
3. 能把其中至少三项连接到后端或 Agent 服务，例如并发、进程隔离、超时、文件描述符、流式输出和资源泄漏。

达到这三点后即可把主力转向网络、后端与 Agent 工程；操作系统改成面试前滚动复习。

## 轻量方向调整

这不是新的详细日程，只是顺序校准：

1. 操作系统停止扩展新分支，补齐主动回忆；网络优先完成 HTTP、TCP、连接与超时。
2. 不等待所有 MySQL/Redis 八股学完，尽早启动一个包含后端服务、工具调用、状态、RAG、Eval/Trace 的 Agent 项目。
3. MySQL、Redis、消息队列、Docker/K8s 围绕项目按需补齐，再回到八股做面试化整理。
4. 算法维持长期小剂量；不要用“每天必须两题”挤压 Agent 项目闭环。

## 我的问题

1. 当前操作系统内容中，哪些已经能脱离资料复述，哪些只是看过？
2. 第一个 Agent 项目更适合落在研发效能、业务助手还是知识问答场景？
3. Python、Java、Go、TypeScript 中，哪两种语言最适合作为“Agent 实现 + 生产后端”的组合？

## 可提炼的概念

- Agent Runtime 与普通后端服务的差异。
- Harness、Workflow、Agent Framework 的边界。
- Agent Eval 与传统接口测试的差异。
- Context Engineering 与 RAG 的关系。

## 主动回忆

合上资料后回答：

1. 为什么当前 Agent 岗不能只学 RAG？
2. Agent 生产化最常见的五类工程问题是什么？
3. 字节火山方舟、阿里云全栈 Agent、蚂蚁 CodeFuse 分别在做什么业务？
4. 操作系统学到什么程度可以从主线转为滚动复习？
5. 当前清单中最应该增加的三个主题是什么？
