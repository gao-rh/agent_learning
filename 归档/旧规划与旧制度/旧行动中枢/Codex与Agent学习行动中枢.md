---
type: project
status: unconfirmed
tags: [codex, ai-agent, learning-system, todo, ai-draft]
created: 2026-06-21
updated: 2026-08-13
---

# Codex 与 Agent 学习行动中枢

> 状态说明（2026-08-13）：本页为 AI 生成且未经用户确认的方案，不代表当前承诺或真实执行顺序。在新的 2–3 个月规划确认前，仅作为历史草案和候选项池。

## 先看这里

这个页面只回答一个问题：

> 我接下来该做什么，才能更会用 Codex、更理解 Agent？

不要在这里堆资料。资料放到 [阅读资料](Codex与Agent阅读索引.md)，稳定理解沉淀到 `笔记/`，实验和方法分别放到 `40-code-labs/`、`50-systems/`。

## 当前主线

### 2026-08-11 优先级切换

到 2026-08-31 前，北极星从“按教材完整学习”切换为“形成可投递、可面试、可证明的 Agent 求职闭环”。

执行规则：

1. 边投边补，不等学完所有课程再投递。
2. 学习只保留三类：面试高频、目标 JD 明确要求、能立即转化为项目证据。
3. 只打磨一个主 Agent 项目；不再平行开新课、新仪表盘或大型 Vault 整理。
4. 每天必须同时有对外输出（投递/内推/约聊）和内部补强（项目/面试），不用纯学习代替求职进展。

[查看 8·31 前求职冲刺计划](Agent求职岗位追踪/2026-08-11-8月31日前求职冲刺计划.md)

| 顺序 | 主线 | 要得到什么 |
| --- | --- | --- |
| 1 | 形成可投递材料 | 完成 Agent 主线简历、项目证据和 3 分钟自我介绍 |
| 2 | 形成可面试能力 | 围绕目标 JD 准备 Agent、后端、项目深挖和算法高频题 |
| 3 | 用一个主项目证明 | 展示 Tool/Workflow、Memory/RAG、Eval/Trace 中的关键闭环 |

从 2026-07-27 起，以李博杰《深入理解 AI Agent》作为 Agent 学习主教材。先把这条线跑通：

```text
第 1 章 Agent / ReAct / Harness -> 第 2-3 章 Context / Memory -> 第 4-5 章 Tool / Coding Agent -> 评估与进化
```

## 当前重点

| 优先级 | 状态 | 要做什么 | 下一步动作 | 产出 |
| --- | --- | --- | --- | --- |
| P0 | Doing | 8·31 前 Agent 求职冲刺 | 用 45 分钟盘点现有简历、可展示项目、可联系内推和可投岗位 | `30-projects/Agent求职岗位追踪/2026-08-11-8月31日前求职冲刺计划.md` |
| P0 | Done | 学《深入理解 AI Agent》第 2 章 | 已按重点路线完成 2-1→2-9 主线，并形成“稳定前缀—规则—安全—按需加载—显式状态—压缩”的上下文生命周期 | `90-reviews/2026-08-10-深入理解AI-Agent-第2章里程碑复盘.md` |
| P0 | Next | 把现有 Agent 成果打磨成一个主项目 | 在现有项目中选 1 个，列出场景、架构、Agent 机制、工程难点、数据指标和演示缺口 | 主项目 README + 可演示版本 + 面试讲稿 |
| P0 | Next | 生成定向投递包 | 先完成一版 Agent 主线简历和 3 分钟自我介绍，再针对 P0/P1 岗位微调 | 简历 + 自我介绍 + 项目讲稿 |
| P1 | Later | 学《深入理解 AI Agent》第 3 章 | 只在目标 JD 或主项目需要 Memory/RAG 时定向学习 | 第 3 章学习日志 + Agent 核心笔记 |

暂停项：

| 事项 | 为什么先暂停 |
| --- | --- |
| 按教材章节完整推进 | 8·31 前只学能立即支持岗位、项目或面试的部分 |
| 大量扩展阅读清单 | 现在的问题是收敛，不是资料不够 |
| 做网页 dashboard | MD 版还没跑顺，先不要增加维护成本 |
| 研究所有 Skill / Plugin | 先理解边界，再决定装什么 |
| 大规模重构 Vault | 当前目录结构够用，缺的是行动层 |

## 待办池

只放近期可能推进的任务。超过 7 个就要复盘。

| ID | 状态 | 类型 | 任务 | 下一步动作 | 产出位置 |
| --- | --- | --- | --- | --- | --- |
| LA-001 | Later | 系统优化 | 验证行动中枢是否真的好用 | 8·31 后再复盘系统本身 | 本页 |
| LA-002 | Later | 概念 | Harness Engineering 是什么 | 仅在主项目或目标面试需要时定向读 | `笔记/Harness Engineering是什么.md` |
| LA-003 | Later | 系统规则 | Codex 使用最佳实践 | 8·31 后再做通用规则整理 | `50-systems/Codex使用最佳实践.md` |
| LA-004 | Next | 实验 | 复盘最小 Agent tool loop | 做完 2-1 后，对照两个实现的 messages 变化 | `40-code-labs/minimal-agent-tool-loop/` |
| LA-005 | Later | 概念 | MCP、CLI、Connector、Plugin 的区别 | 等 Harness 概念卡完成后再做 | `笔记/MCP与普通工具调用的区别.md` |
| LA-006 | Done | 阅读+实验 | 《深入理解 AI Agent》第 2 章 | 完成里程碑复盘的 7 道主动回忆题，答错部分再回看 | `90-reviews/2026-08-10-深入理解AI-Agent-第2章里程碑复盘.md` |
| LA-007 | Doing | 项目+求职 | 8·31 前 Agent 求职冲刺 | 45 分钟完成简历、项目、内推联系人和目标岗位的现状盘点 | `30-projects/Agent求职岗位追踪/2026-08-11-8月31日前求职冲刺计划.md` |

## 阅读入口

当前主教材优先，官方文章用于交叉校准：

| 顺序 | 材料 | 读它是为了什么 | 读完做什么 |
| --- | --- | --- | --- |
| 1 | [《深入理解 AI Agent》](../10-sources/books/2026-07-27-深入理解AI-Agent-学习入口.md) | 建立 Agent 全书主线，并用配套实验验证 | 持续更新学习过程、核心笔记与代码实验 |
| 2 | [OpenAI: Harness Engineering](https://openai.com/index/harness-engineering/) | 用官方工程实践交叉校准书中的 Harness 框架 | 写 `Harness Engineering是什么.md` |
| 3 | [OpenAI Codex Best Practices](https://developers.openai.com/codex/learn/best-practices) | 校准 Codex 官方推荐的使用方式 | 写 `Codex使用最佳实践.md` |

完整资料池在：[阅读资料](Codex与Agent阅读索引.md)。

## 什么时候复盘

出现下面任一情况，就先复盘本页：

- 我说“有点乱”“不知道接下来干啥”。
- `Doing` 超过 3 个。
- `Next` 超过 7 个。
- 连续新增资料，但没有产出概念卡、实验或系统规则。

复盘只做三件事：

1. 选出 1-3 个真正要做的任务。
2. 把其他任务移到 `Later`。
3. 给每个保留任务写清楚下一步动作。

## 相关资料

- [阅读资料](Codex与Agent阅读索引.md)
- [Codex Skills 生态调研报告](Codex%20Skills生态调研报告.md)
- [Codex 与 Agent 使用方法生态调研报告](Codex与Agent使用方法生态调研报告.md)
- [agent-learning-vault Skill](../.agents/skills/agent-learning-vault/SKILL.md)
