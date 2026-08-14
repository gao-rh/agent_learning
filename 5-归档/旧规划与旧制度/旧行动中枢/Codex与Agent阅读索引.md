---
type: project
status: active
tags: [codex, ai-agent, reading-list, index]
created: 2026-06-21
updated: 2026-08-09
---

# Codex 与 Agent 阅读索引

## 用法

这个页面是资料池，不是今日待办。

阅读顺序由 [当前学习计划](Codex与Agent学习行动中枢.md) 决定。这里负责保存候选材料、摘要、阅读理由和读完产出。

## P0：先读

| 状态 | 方向 | 材料 | 摘要 | 读完产出 |
| --- | --- | --- | --- | --- |
| Doing | Agent | [《深入理解 AI Agent：设计原理与工程实践》](../10-sources/books/2026-07-27-深入理解AI-Agent-学习入口.md) | 以 `Agent = LLM + 上下文 + 工具` 为主线，把 Context、Memory、Tool、Harness、评估和多 Agent 放进同一工程体系。第 2 章已按重点路线完成，收束为稳定前缀、Prompt 实验、注入防御、Skill 加载、显式状态和上下文压缩的生命周期。下一阶段进入第 3 章，先区分 Context、Session State、短期/长期 Memory 与 RAG。 | 第 3 章学习日志 + Agent 核心笔记 + 分章代码实验 |
| Next | Harness | [OpenAI: Harness Engineering](https://openai.com/index/harness-engineering/) | 讲 repository knowledge、架构边界、lint、测试和 taste invariants 如何成为 Agent 外部约束。 | `笔记/Harness Engineering是什么.md` |
| Next | Codex | [OpenAI Codex Best Practices](https://developers.openai.com/codex/learn/best-practices) | 官方建议如何给 Codex 提供上下文、计划、验证和项目规则。 | `50-systems/Codex使用最佳实践.md` |
| Next | Codex | [Codex Manual](https://developers.openai.com/codex/codex-manual.md) | Codex 的长文档入口，覆盖 AGENTS.md、Skills、Plugins、MCP、Hooks、exec、SDK、permissions。 | Codex 能力边界表 |
| Next | Codex | [AGENTS.md](https://agents.md/) | 给 coding agents 的开放项目说明格式，把项目约定变成 Agent 可读文件。 | `50-systems/AGENTS.md写法.md` |

## Agent / Harness / Context Engineering

| 状态 | 方向 | 材料 | 摘要 | 读完产出 |
| --- | --- | --- | --- | --- |
| Next | Agent | [12-factor-agents](https://github.com/humanlayer/12-factor-agents) | 面向可靠 LLM app / agent harness 的原则集合，强调上下文、控制流、状态和 human-in-loop。 | `笔记/12-factor-agents学习笔记.md` |
| Next | Harness | [HumanLayer: Harness Engineering for Coding Agents](https://www.humanlayer.dev/blog/skill-issue-harness-engineering-for-coding-agents) | 从 coding agent 用户视角解释 skills、MCP、subagents、hooks 如何组成 harness。 | `笔记/Coding Agent Harness组成.md` |
| Later | Harness | [Martin Fowler: Harness engineering for coding agent users](https://martinfowler.com/articles/harness-engineering.html) | 从软件工程实践角度讨论 coding agent 用户如何设计外部环境和反馈回路。 | 概念卡或 source note |
| Later | Harness | [Martin Fowler: Encoding Team Standards](https://martinfowler.com/articles/reduce-friction-ai/encoding-team-standards.html) | 讨论如何把团队标准编码成版本化 artifact，减少 AI 协作摩擦。 | `50-systems/Agent协作规范沉淀规则.md` |

## Skill / MCP / Plugin / Hook

| 状态 | 方向 | 材料 | 摘要 | 读完产出 |
| --- | --- | --- | --- | --- |
| Next | Skill | [OpenAI Skills 文档](https://developers.openai.com/codex/skills) | 官方说明 Skill 的结构、触发、渐进式加载和存放位置。 | 修订 `agent-learning-vault` |
| Later | Skill | [Anthropic: Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) | 解释 Skills 如何让 Agent 渐进式加载流程、脚本和参考资料。 | `笔记/Agent Skill是什么.md` |
| Next | MCP | [MCP Tools Spec](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) | 说明 MCP server 如何暴露工具、工具发现、工具调用和人类确认。 | `笔记/MCP工具协议.md` |
| Later | Plugin | [OpenAI Codex Plugins 文档](https://developers.openai.com/codex/plugins) | 说明 plugin 如何打包 skills、MCP、hooks、assets、apps。 | Plugin 选型判断 |

## Obsidian / PKM / AI-assisted Vault

| 状态 | 方向 | 材料 | 摘要 | 读完产出 |
| --- | --- | --- | --- | --- |
| Next | PKM | [Eric J. Ma: Mastering PKM with Obsidian and AI](https://ericmjl.github.io/blog/2026/3/6/mastering-personal-knowledge-management-with-obsidian-and-ai/) | 展示如何用纯文本 vault、结构化笔记类型和 agent skills 管理个人知识系统。 | `50-systems/AI辅助学习Vault工作流.md` |
| Next | PKM | [J.D. Wilkins: AI-powered Task System with Obsidian and Claude Code](https://www.jdhwilkins.com/how-i-built-an-ai-powered-task-system-with-obsidian-and-claude-code/) | 展示如何把 Obsidian 和 AI assistant 结合成任务管理系统。 | 行动中枢迭代规则 |
| Later | PKM | [Personal Knowledge Management with Zettelkasten and Obsidian](https://dev.to/yordiverkroost/personal-knowledge-management-with-zettelkasten-and-obsidian-20cj) | 区分文献笔记、永久笔记和地图页，强调从来源走向自己的表达。 | 来源笔记到概念卡流转规则 |

## 学习方法

| 状态 | 方向 | 材料 | 摘要 | 读完产出 |
| --- | --- | --- | --- | --- |
| Later | 学习方法 | [Forte Labs: PARA](https://fortelabs.com/blog/para/) | 按行动性组织信息：Projects、Areas、Resources、Archives。 | 本 vault 目录调整判断 |
| Next | 学习方法 | [Forte Labs: BASB / CODE](https://fortelabs.com/blog/basboverview/) | CODE = Capture、Organize、Distill、Express，强调知识要服务表达和使用。 | 学习输入到输出规则 |
| Next | 学习方法 | [Todoist: Getting Things Done](https://www.todoist.com/productivity-methods/getting-things-done) | GTD 把输入处理成项目、下一步动作、日程、参考或以后再说。 | 行动表 Clarify 规则 |
| Later | 学习方法 | [Osmosis: Active Recall and Spaced Repetition](https://www.osmosis.org/blog/easy-ways-to-integrate-active-recall-and-spaced-repetition-into-your-curriculum) | 主动回忆要求从记忆中取回答案，间隔重复要求按时间回看。 | 来源笔记自测模板 |
