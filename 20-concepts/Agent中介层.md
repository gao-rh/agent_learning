---
type: concept
status: stable-draft
tags: [ai-agent, agent-runtime, openclaw, codex]
created: 2026-06-14
updated: 2026-06-14
source:
  - 10-sources/courses/李宏毅机器学习2026/2026-06-13-Agent到底是什么.md
  - 00-inbox/2026-06-13-openclaw中介层讨论日志.md
related:
  - 20-concepts/OpenClaw是什么.md
  - 20-concepts/Agent当前回合上下文包.md
  - 20-concepts/Agent执行循环.md
---

# Agent 中介层

## 一句话理解

Agent 是人和大模型之间的协调层：它把人的目标转成模型能处理的上下文，再把模型的判断转成工具、文件、消息和外部系统里的真实动作。

## 核心机制

```text
人 / 渠道 / 工作目标
-> Agent Runtime
-> 大模型 / 工具 / 电脑 / 外部系统
```

大模型提供基础智能，Agent Runtime 负责：

| 能力 | 说明 |
| --- | --- |
| 渠道 / Channel | 从聊天、CLI、App、Webhook 等地方接收任务。 |
| 拼上下文 | 把规则、历史、记忆、文件、工具定义组织成模型输入。 |
| 调模型 | 让 GPT、Claude、Gemini 等模型理解任务并决定下一步。 |
| 执行工具 | 把模型的 tool call 转成真实文件、Shell、Web、MCP、消息动作。 |
| 管状态 | 维护 session、tasks、compaction、memory。 |
| 控风险 | 通过 sandbox、approval、tool policy 限制危险动作。 |

## 例子

OpenClaw 更像 gateway-first 的个人 Agent Runtime：它连接聊天渠道、长期记忆、任务、自动化和电脑能力。

Codex 更像 coding-first 的软件工程 Agent Runtime：它连接代码仓库、文件编辑、shell、测试和 PR 流程。

它们都不是模型本身，而是围绕模型建立的工作流系统。

## 常见误区

| 误区 | 更准确的理解 |
| --- | --- |
| Agent 就是大模型 | 大模型是 Agent 的智能核心，但 Agent 还包含渠道、上下文、工具、记忆、权限和 Runtime。 |
| OpenClaw / Codex 的聪明都来自自己 | 基础智能主要来自底层模型；系统价值来自把模型接入真实工作流。 |
| 有 System Prompt 就等于有 Agent | System Prompt 只是上下文的一部分；完整 Agent 还要能执行工具、管理状态和权限。 |

## 和其他概念的关系

- [[Agent当前回合上下文包]]：中介层给模型准备的输入。
- [[Agent执行循环]]：中介层把模型输出转成真实动作的过程。
- [[OpenClaw是什么]]：OpenClaw 是这种中介层的一种具体实现。

## 自测问题

1. 为什么说 Agent 是中介层，而不是模型本身？
2. 如果去掉 Runtime，只剩模型，会失去哪些能力？
3. OpenClaw 和 Codex 在中介层职责上有什么共同点？
