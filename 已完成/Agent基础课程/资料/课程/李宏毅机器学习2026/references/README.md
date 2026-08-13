---
type: reference-index
status: active
tags: [machine-learning, ai-agent, 李宏毅, references]
created: 2026-06-19
updated: 2026-06-19
origin_type: 课程整理
origin: 李宏毅机器学习2026
---

# 课程参考资料索引

这个目录集中登记李宏毅机器学习 2026 课程的核心参考资料、官方网站、课程材料和补充资料。

原则：

- 这里记录“资料从哪里来、有什么用、对应哪一节课”。
- 大 PDF 不直接提交到 Git，只记录官方 URL、本地路径和摘要。
- 课程笔记引用这里的资料卡，而不是在每篇笔记里散落一堆链接。
- 只有对理解课程有明确帮助的资料才放进来。

## 官方课程入口

| 资料 | 类型 | 链接 | 用途 |
| --- | --- | --- | --- |
| Machine Learning 2026 Spring | 官方课程页 | https://speech.ee.ntu.edu.tw/~hylee/ml/2026-spring.php | 课程总入口，查看课程内容、视频、PPT、PDF、作业。 |

## 第一节：Agent 到底是什么

| 资料 | 类型 | 链接 / 路径 | 状态 | 用途 |
| --- | --- | --- | --- | --- |
| 解剖小龍蝦：以 OpenClaw 為例介紹 AI Agent 的運作原理 | 官方 PDF | https://speech.ee.ntu.edu.tw/~hylee/ml/ml2026-course-data/intro.pdf | 核心参考 | 第一节主参考。知识分享的主线应优先参考这份 PDF。 |
| intro.pdf | 本地 PDF | `../../../../学习资料/Agent/参考资料/李宏毅机器学习2026/course-data/intro.pdf` | 已归档 | 第一节主参考，60 页。 |
| 解剖小龍蝦：以 OpenClaw 為例介紹 AI Agent 的運作原理 | 官方视频 | https://www.youtube.com/watch?v=2rcJdFuNbZQ | 核心参考 | 需要回看老师原始讲法时使用。 |
| 语言模型基本原理 | 背景视频 | https://youtu.be/TigfpYPJk1s | 补充参考 | PDF 第 2 页提到的前置背景，用于理解 LLM 基本原理。 |

## 第二节：AI Agent - 2

这些资料先登记，后续第二节再正式整理。第一节可以轻量提到，但不要提前展开。

| 资料 | 类型 | 链接 | 状态 | 用途 |
| --- | --- | --- | --- | --- |
| Context Engineering 基本概念解说 | 官方视频 | https://youtu.be/urwDLyNa9FU | 待学习 | 第二节主题之一。第一节只保留“上下文工程”作为后续专题。 |
| AI Agent 之间可以有什么样的互动 | 官方视频 | https://youtu.be/mmPmNezjCi0 | 待学习 | 第二节主题之一。第一节不展开多 Agent 协作。 |
| AI Agent 对工作带来的冲击：以学术研究为例 | 官方视频 | https://youtu.be/VqB8zMujdjM | 待学习 | 第二节主题之一。第一节不展开职业/组织影响。 |
| AI Agent - 2 PDF | 官方 PDF / 本地 PDF | https://speech.ee.ntu.edu.tw/~hylee/ml/ml2026-course-data/agent_era.pdf / `../../../../学习资料/Agent/参考资料/李宏毅机器学习2026/course-data/agent_era.pdf` | 已整理 | 第二节核心 PDF，Context Engineering 笔记已整理。 |
| AI Agent - 2 PPTX | 官方 PPTX / 本地 PPTX | https://speech.ee.ntu.edu.tw/~hylee/ml/ml2026-course-data/agent_era.pptx / `../../../../学习资料/Agent/参考资料/李宏毅机器学习2026/course-data/agent_era.pptx` | 已下载 | 第二节可编辑课件。 |

## 第一节讲课主线

从 PDF 抽取出的主线如下，后续整理主文档时优先参考这个顺序：

1. 过去 AI 只动口不动手。
2. OpenClaw 作为 AI Agent 示例，但课程主旨是解释 AI Agent 运作原理。
3. OpenClaw 是 AI Agent 中“不太 AI 的部分”，语言模型才是智能来源。
4. 语言模型本质上是文字接龙；一次调用就是输入 prompt，返回 response。
5. 语言模型输入输出长度有限，也不会天然记住自己是谁。
6. Agent 通过 system prompt / 身份文件 / 用户文件 / 记忆文件让模型“知道自己是谁”。
7. Agent 通过工具调用使用电脑。
8. `exec` 等强工具带来能力，也带来风险，需要权限和防御。
9. Agent 可以用工具创造新工具。
10. Sub-agent 是特殊工具，用来拆任务、隔离上下文。
11. Skill 是工作的 SOP，按需读取，是一种 Context Engineering。
12. 长期运行会遇到 context window 不够的问题。
13. Memory 通过外部文件和检索进入当前上下文。
14. Heartbeat 让 Agent 定时工作。
15. Context Compression 让 Agent 可以长时间执行。
16. Agent 的能力很强，但还不成熟，需要安全环境、检查和教导。

## 补充产品与官方资料

这些资料不是第一节原始材料，但可以用于补充“当前有哪些 Agent，以及各自特点”。

| 资料 | 类型 | 链接 | 用途 |
| --- | --- | --- | --- |
| Claude Code Docs | 官方文档 | https://code.claude.com/docs/en/overview | 对比 coding agent 的工具、权限、session、skills、hooks、scheduled tasks。 |
| OpenAI Codex | 官方文档 | https://developers.openai.com/codex | 对比 Codex 的软件工程 agent 形态。 |
| Gemini CLI announcement | 官方博客 | https://blog.google/innovation-and-ai/technology/developers-tools/introducing-gemini-cli-open-source-ai-agent/ | 对比 terminal agent / open-source AI agent。 |

## 待补资料

| 资料 | 需要补什么 |
| --- | --- |
| OpenClaw 官方仓库 / 文档 | 需要确认官方稳定入口，再登记。 |
| AutoGPT 官方仓库 / 文档 | 用于解释早期 autonomous agent 为什么没有成为日常生产工具。 |
| Skill 安全相关资料 | 用于补充“Skill 是 SOP，但也可能是攻击面”。 |
