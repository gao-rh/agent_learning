---
type: source
status: draft
tags: [machine-learning, ai-agent, context-engineering, 李宏毅]
created: 2026-06-21
updated: 2026-06-21
origin_type: 课程整理
origin: 李宏毅机器学习2026
source_type: course
source_url: https://speech.ee.ntu.edu.tw/~hylee/ml/ml2026-course-data/agent_era.pdf
author: 李宏毅
related:
  - "[[2026-06-13-Agent到底是什么]]"
  - "[[Agent当前回合上下文包]]"
  - "[[上下文拼接不等于模型记忆]]"
---

# Context Engineering

## 基本信息

| 项目 | 内容 |
| --- | --- |
| 课程 | 李宏毅机器学习 2026，AI Agent - 2 |
| 课件 | `学习资料/Agent/参考资料/李宏毅机器学习2026/course-data/agent_era.pdf` |
| 本笔记范围 | 课件第 1-33 页：Context Engineering |
| 不纳入本笔记的部分 | 第 34-43 页多 Agent 互动；第 44-61 页 AI Agent 对工作和学术研究的影响 |

## 一句话结论

Context Engineering 不是简单地“把 prompt 写好”，而是为每一轮模型调用设计一个长度合适、信息足够、噪声可控、可恢复、可执行的上下文包。

更具体地说：Agent 的历史轨迹、工具输出、文件、记忆、系统提示、任务目标、工具 schema 都可能成为上下文；工程问题是决定哪些内容要留在当前窗口里，哪些要压缩，哪些要放到外部存储，哪些按需读取，哪些根本不该给模型看。

## 核心观点

### 1. 语言模型“活在当下”

语言模型每次只根据当前输入生成输出。它不会天然记得完整历史，也不会自动知道过去工具调用、文件内容和任务目标。Agent 看起来能持续工作，是因为系统把必要历史和外部状态重新组织进当前输入。

这解释了 Context Engineering 的第一性问题：

> 当前这一轮，模型需要看到什么，才能做出正确下一步？

这个输入不能太短。太短会丢失任务目标、约束、证据、失败经验和工具结果。

这个输入也不能太长。太长会增加成本、推理延迟和注意力干扰，甚至让模型在无关信息里迷失。

### 2. 压缩不是“删掉旧东西”这么简单

课件把压缩分成几种形态：

| 手段 | 做法 | 价值 | 风险 |
| --- | --- | --- | --- |
| Summary | 用 LLM 把历史轨迹压成摘要 | 降低 token，占住主线 | 摘要可能漏掉关键状态 |
| Hard clear | 直接清掉历史 | 简单、便宜 | 很容易遗忘任务和约束 |
| 外部卸载 | 把大段工具输出写入文件，只在上下文保留路径或索引 | 可恢复，适合大日志、网页、PDF | 模型必须知道何时读回 |
| Subagent | 把子任务交给子 agent，主上下文只拿结果 | 隔离噪声，减少主干轨迹 | 子 agent 回传如果太粗，会漏掉推理证据 |
| 学到的压缩器 | 用训练或优化方法学习何时折叠历史 | 有机会比启发式更稳 | 需要数据、评测和训练成本 |

关键 caveat：压缩是有损操作。课程强调“模型不喜欢压缩”，因为压缩相当于抹除一部分历史。真正的问题不是“能不能压短”，而是“压短之后还能不能保留未来会用到的状态”。

ACON 的方向是用失败分析反复优化压缩指南，使摘要保留 credential、token state、authentication requirements、guardrails 等关键状态。SUPO 则把摘要策略纳入多轮工具使用的 RL 训练，让模型在长任务中学会同时优化工具行为和上下文管理。

### 3. 记忆是外部系统，不是模型权重

课程中的 memory 不是“模型真的记住了我”，而是把历史经验放到外部系统里，需要时再加载进当前上下文。

一个可操作的 memory 系统至少要回答四个问题：

| 问题 | 说明 |
| --- | --- |
| 何时保存 | 什么时候把一次经验、偏好、错误、代码片段或结论写入记忆 |
| 保存什么 | 保存原文、摘要、结构化字段、标签、时间、关系，还是文件路径 |
| 何时读取 | 当前任务是否需要历史事实、用户偏好、项目决策、旧错误 |
| 如何读取 | 关键词检索、向量检索、图关系、时间过滤、工具按行读取 |

A-MEM、Mem0、Memory OS 这类方向都在处理长期记忆问题。共同趋势是：不要只把对话历史堆进窗口，而要把记忆组织成可检索、可更新、可关联的外部结构。

### 4. 过滤比“全塞进去”更重要

过滤的核心是：模型不需要看全部资料，只需要看与当前动作相关的部分。

例子：

| 场景 | 粗糙做法 | 更好的 Context Engineering |
| --- | --- | --- |
| 读日志 debug | 把整个 log 塞给模型 | `Read(log, "bug fixing")`，只取和 bug 有关片段 |
| 读 memory | 一次性注入所有记忆 | 先搜索，再读取精确文件和行 |
| 工具很多 | 所有工具 schema 都放进 prompt | 先让模型描述需要什么能力，再按需加载工具 |
| MCP 生态 | 所有 MCP server 和 tool 都给模型 | 工具发现、语义路由、逐步扩展能力 |

这和我们平时使用 Codex 很接近：先 `rg` 搜相关文件，再 `sed` 读局部，而不是把整个仓库塞进上下文。

### 5. Tool schema 本身也是上下文负担

工具越多，模型越强，也越容易选错工具。每个工具的名称、描述、参数 schema 都占 token；上百个工具会把上下文推向“工具菜单污染”。

MCP-Zero 的方向是主动工具发现：不要预先把所有工具都塞进 prompt，而是让模型先说明自己需要什么能力，再通过语义路由找到相关 server/tool。MCP 官方文档则把 MCP 定位为 AI 应用连接外部数据源、工具和工作流的开放标准。

这里要注意一个张力：

- 动态增删工具可以减少上下文负担。
- 但 Manus 的实践提醒：中途改变工具定义会破坏 KV cache，也可能让历史动作引用的工具在当前上下文里消失，造成混乱。

所以更成熟的做法可能不是简单 remove tools，而是：

1. 稳定工具定义和 prompt 前缀。
2. 用工具搜索或路由选择候选工具。
3. 在执行状态中 mask 或约束当前可选动作。
4. 把工具调用历史保持可解释。

### 6. Agentic Context Engineering：让 Agent 自己维护上下文

课件后半提出一个更强的方向：把上下文维护本身也交给 Agent。

这包括：

| 方向 | 核心想法 |
| --- | --- |
| Dynamic Cheatsheet | 保存未来能复用的策略、代码和关键发现 |
| ACE | 把上下文视为会演化的 playbook，通过生成、反思、整理持续更新 |
| Recursive Language Models | 大部分内容放在硬盘，只把 metadata 和当前需要的片段放进上下文 |

这和“长期学习系统”很像：不是每次从零开始，而是把有效策略沉淀成可检索、可复用的结构。

但课程最后问“把一切交给 LLM?” 这是一个重要提醒。上下文维护可以越来越 agentic，但不能完全无约束。否则会出现错误记忆、错误摘要、错误工具选择、错误自我强化。

## 当前技术手段图谱

| 技术手段 | 解决的问题 | 你需要掌握的前置知识 |
| --- | --- | --- |
| Prompt / system prompt 设计 | 明确角色、边界、输出格式、任务目标 | prompt 结构、指令优先级、few-shot |
| Context window 管理 | 控制当前输入长度和内容密度 | token、上下文窗口、lost-in-the-middle |
| Summarization / compaction | 长任务历史压缩 | 摘要评估、状态保真、失败分析 |
| Retrieval / RAG | 从外部知识库取相关片段 | chunking、embedding、BM25、reranking |
| Memory | 保存跨轮次经验和偏好 | 检索、结构化存储、时间和关系建模 |
| File system as context | 大内容外部化，按需读回 | 文件路径、索引、可恢复压缩 |
| Tool routing | 从大量工具中选当前需要的工具 | tool schema、function calling、MCP |
| Subagent | 子任务隔离和自主压缩 | 任务拆解、边界定义、结果验收 |
| Prompt caching / KV cache | 降低长上下文成本和延迟 | Transformer 推理、KV cache、稳定前缀 |
| Evaluation | 判断上下文策略是否真的有效 | 成功率、token 成本、延迟、错误恢复 |

## 网络资料补充：2025-2026 的新趋势

这些不是课程原文，而是补充材料。

### Manus 的工程经验

Manus 的文章把 Context Engineering 讲得更工程化，重点包括：

| 实践 | 含义 |
| --- | --- |
| Design around KV-cache | 保持 prompt 前缀稳定、上下文 append-only、必要时显式 cache breakpoint |
| Mask, don't remove | 不要频繁增删工具定义；通过状态机或约束控制当前可选动作 |
| Use the file system as context | 把文件系统当作可恢复的外部上下文，而不是把所有内容放进窗口 |
| Manipulate attention through recitation | 反复更新 todo，把任务目标推到近期上下文，降低跑偏 |
| Keep the wrong stuff in | 保留失败轨迹和错误输出，让模型避免重复犯错 |
| Don't get few-shotted | 太整齐的历史模式可能让 Agent 机械模仿，导致僵化 |

这个补充能帮我们修正一个直觉：Context Engineering 不只是“压缩”，还包括缓存效率、工具稳定性、错误恢复和注意力引导。

### 论文方向

| 方向 | 代表资料 | 关键点 |
| --- | --- | --- |
| 上下文压缩 | ACON、SUPO | 不只是摘要，而是保留任务状态、工具历史和未来依赖 |
| 自适应记忆 | Dynamic Cheatsheet、A-MEM、Mem0 | 保存可复用策略、代码、偏好和结构化记忆 |
| 工具发现 | MCP-Zero、MCP | 大工具生态下，按需发现和路由工具 |
| 上下文自进化 | ACE | 把上下文当作会演化的 playbook，而不是一次性 prompt |

## 我是否真的学明白：自测题

详细参考答案见：[[2026-06-21-Context-Engineering-自测题答案]]

### A. 基础复述

1. 用一句话解释 Context Engineering，不能使用“写 prompt”这几个字。
2. 为什么说语言模型“活在当下”？
3. 当前回合上下文包里可能包含哪些东西？至少列 6 类。
4. 为什么上下文不能太短？为什么也不能太长？
5. Context Engineering 和 Prompt Engineering 的差别是什么？

### B. 机制区分

6. Summary、Hard clear、外部卸载三者有什么区别？
7. 为什么“把历史总结一下”可能会让 Agent 变笨？
8. Subagent 为什么可以看作一种自主压缩？
9. Memory 和 RAG 有什么重叠？有什么不同？
10. 为什么工具 schema 太多会污染上下文？
11. MCP-Zero 解决的是“工具不会用”还是“工具太多不知道该看哪些”？请解释。
12. 为什么 Manus 说不要随便 remove tools，而是 mask tools？

### C. 设计判断

13. 如果 Agent 正在 debug，一个 5 MB 日志文件应该怎么进入上下文？
14. 如果 Agent 要记住用户长期偏好，应该直接把所有历史聊天塞进 prompt 吗？为什么？
15. 一个长任务执行 50 轮后开始跑偏，你会用哪些上下文工程手段把它拉回来？
16. 什么情况下应该压缩？什么情况下不应该压缩？
17. 什么信息必须高保真保留，不能只靠摘要？
18. 如果工具调用失败了，错误栈应该删掉吗？为什么？

### D. 迁移到自己的学习系统

19. 在 `agent_learning` 里，哪些内容应该进入当前上下文，哪些应该只作为 Obsidian 文件长期保存？
20. 我们现在使用的 `00-inbox -> 10-sources -> 20-concepts` 工作流，哪里体现了 Context Engineering？
21. Codex 读仓库时为什么先 `rg` 再局部读文件，而不是直接读全仓库？
22. 如果要给自己做一个“学习助理 Agent”，它需要哪些 memory？哪些 memory 不该自动保存？
23. 你怎么判断一个笔记应该变成稳定概念卡，而不是继续留在 source note？

### E. 高阶反思

24. “上下文越长越好”这句话错在哪里？
25. “模型窗口变成 100 万 token 后，Context Engineering 就不重要了”这句话错在哪里？
26. Context Engineering 和模型训练/微调是什么关系？什么时候改上下文，什么时候改模型？
27. Agentic Context Engineering 的风险是什么？
28. 如果一个 Agent 自己总结自己的历史，它最容易犯什么错误？你如何评估？
29. 你能设计一个小实验，比较“全量历史”“摘要历史”“文件卸载 + 按需读取”三种策略吗？
30. 用自己的话解释：为什么 Context Engineering 是 Agent 的核心技术，而不是边角优化？

## 参考答案要点

### 最低合格线

如果能回答下面 5 点，说明主线已经抓住：

1. Context Engineering 是选择、组织、压缩、检索、加载当前模型输入的工程。
2. Agent 的连续性来自外部状态和上下文重建，不是模型天然记忆。
3. 长上下文有成本、延迟和注意力干扰，不等于更聪明。
4. 记忆、文件、工具、摘要、Subagent 都是上下文管理手段。
5. 压缩和过滤必须可恢复、可验证，否则会丢掉未来关键状态。

### 扎实掌握线

如果还能讲清下面 5 点，说明理解比较扎实：

1. 摘要不是万能压缩，状态保真比语言流畅更重要。
2. 工具 schema 也是上下文成本，工具发现和工具路由是必要能力。
3. 文件系统可以作为外部上下文，用路径、索引和按需读取避免不可逆压缩。
4. Prompt caching / KV cache 要求稳定前缀和 append-only 轨迹，随意改上下文结构会增加成本。
5. Agent 自己维护上下文需要评估和边界，否则会形成错误记忆或错误自我强化。

## 后续学习路线

| 优先级 | 主题 | 为什么要学 |
| --- | --- | --- |
| 1 | Token、context window、lost-in-the-middle | 理解为什么“长”不等于“好” |
| 2 | RAG：chunking、BM25、embedding、reranking | 理解外部知识如何进入当前上下文 |
| 3 | Memory：长期记忆、时间、图关系 | 理解 Agent 如何跨会话延续 |
| 4 | Tool calling / MCP | 理解工具 schema 为什么也是上下文 |
| 5 | KV cache / prompt caching | 理解生产 Agent 的成本和延迟优化 |
| 6 | Context compression evaluation | 学会判断摘要有没有丢关键状态 |
| 7 | Agent eval：长任务成功率、错误恢复 | 判断上下文工程是否真的提升能力 |

## 参考资料

- 李宏毅机器学习 2026：`agent_era.pdf`
- Manus, Context Engineering for AI Agents: Lessons from Building Manus, 2025-07-18: https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus
- ACON: Optimizing Context Compression for Long-horizon LLM Agents: https://arxiv.org/abs/2510.00615
- SUPO: Scaling LLM Multi-turn RL with End-to-end Summarization-based Context Management: https://arxiv.org/abs/2510.06727
- MCP-Zero: Active Tool Discovery for Autonomous LLM Agents: https://arxiv.org/abs/2506.01056
- ACE: Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models: https://arxiv.org/abs/2510.04618
- Dynamic Cheatsheet: Test-Time Learning with Adaptive Memory: https://arxiv.org/abs/2504.07952
- A-MEM: Agentic Memory for LLM Agents: https://arxiv.org/abs/2502.12110
- Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory: https://arxiv.org/abs/2504.19413
- Model Context Protocol docs: https://modelcontextprotocol.io/docs/getting-started/intro
- Claude tool use docs: https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview
