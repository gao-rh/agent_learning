---
type: concept
status: draft
tags: [ai-agent, skill, context-engineering, openclaw]
created: 2026-06-13
updated: 2026-06-13
source:
  - local: openclaw skills --help
  - local: openclaw skills info skill-creator
  - local: /opt/homebrew/lib/node_modules/openclaw/skills/skill-creator/SKILL.md
  - https://developers.openai.com/codex/skills
  - https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
  - https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
  - https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
related:
  - 20-concepts/Agent执行循环.md
  - 20-concepts/OpenClaw是什么.md
  - 20-concepts/Sub-agent与Session Span.md
---

# Skill 是什么

## 一句话理解

Skill 是给 Agent 使用的可复用能力包：它把某类任务的流程、规则、工具使用方法、参考资料和脚本封装起来，让通用 Agent 在特定场景里更像专家。

## 1. 什么是 Skill

Skill 不是模型能力本身，也不是简单的一条 prompt。

更准确地说：

```text
Skill = 触发条件 + 操作流程 + 工具说明 + 参考资料 + 可执行资源
```

它解决的是：模型很聪明，但每次都从零想流程会浪费上下文、容易不稳定、容易忘记细节。Skill 把稳定做法沉淀成一个可被 Agent 按需加载的能力包。

## 2. Skill 的结构

不同系统实现会有差异，但常见结构类似：

| 组成 | 是否必需 | 作用 |
| --- | --- | --- |
| `SKILL.md` | 必需 | Skill 的入口说明，告诉 Agent 什么时候用、怎么用。 |
| Frontmatter | 必需 | 元数据，例如 `name`、`description`，用于检索和触发。 |
| Markdown body | 必需 | 具体工作流程、注意事项、工具调用规则、判断标准。 |
| `scripts/` | 可选 | 可执行脚本，用于稳定、重复、容易出错的操作。 |
| `references/` | 可选 | 详细文档、API、schema、业务规则，按需加载。 |
| `assets/` | 可选 | 模板、图片、字体、样例文件、项目脚手架等输出资源。 |

一个典型结构：

```text
skill-name/
├── SKILL.md
├── scripts/
├── references/
└── assets/
```

## 3. Skill 解决什么问题

| 问题 | Skill 的作用 |
| --- | --- |
| 每次都要重新解释流程 | 把稳定流程写进 `SKILL.md`。 |
| Agent 知道工具但不会正确用 | 给出工具使用顺序、参数、边界和失败恢复方式。 |
| 任务需要领域知识 | 把 schema、业务规则、术语、API 文档放进 references。 |
| 操作需要可靠性 | 用 scripts 固化容易出错的步骤。 |
| 上下文太容易膨胀 | 用渐进加载，只在触发时加载 Skill，详细资料按需读。 |
| 多个 Agent/项目重复做同类事 | 把经验封装成可复用能力包。 |

所以 Skill 的核心价值不是“让模型知道更多”，而是让 Agent **更稳定地按正确流程做事**。

## 4. 如何写好一个 Skill

### 4.1 先写触发条件

一个好 skill 要先说清楚什么时候用，什么时候不用。

| 好写法 | 差写法 |
| --- | --- |
| “Use when editing PowerPoint decks or exporting PPTX.” | “Helps with presentations.” |
| “Use when controlling web pages with browser automation.” | “Browser stuff.” |

触发条件越清楚，Agent 越不容易误加载或漏加载。

### 4.2 只写模型不知道但必须知道的东西

Skill 会占上下文。不要把通识内容写进去。

应该写：

- 本系统特有流程。
- 工具调用顺序。
- 易错点。
- 项目/公司/领域规则。
- 明确的完成标准。

不应该写：

- 大量背景科普。
- 和任务无关的 README。
- 模型本来就知道的常识。
- 重复的长篇示例。

### 4.3 按自由度选择表达方式

| 任务类型 | 适合写法 |
| --- | --- |
| 开放任务 | 原则、判断标准、少量例子。 |
| 半固定流程 | 步骤清单、伪代码、参数说明。 |
| 高风险/易错任务 | 固定脚本、严格参数、失败处理。 |

### 4.4 用渐进披露控制上下文

Skill 不应该一加载就塞进所有资料。

```text
SKILL.md：只放核心流程和导航
references/：放详细文档，按需读取
scripts/：放可执行稳定逻辑
assets/：放输出模板和资源
```

这样做的目标是：Agent 先知道怎么走，再按需读取细节。

### 4.5 写失败处理和边界

好 skill 要告诉 Agent：

- 什么时候停止并问用户。
- 什么时候不要继续重试。
- 哪些操作需要确认。
- 哪些文件/权限不能碰。
- 成功完成的标准是什么。

## 好 Skill 的判断标准

| 标准 | 问题 |
| --- | --- |
| 可触发 | Agent 能判断什么时候该用它吗？ |
| 可执行 | 它给了足够具体的步骤吗？ |
| 可复用 | 下次同类任务还能用吗？ |
| 可控 | 它限制了权限、范围和失败重试吗？ |
| 省上下文 | 它只加载必要信息吗？ |
| 有资产 | 需要脚本/模板时是否已经放进 `scripts/` 或 `assets/`？ |

## 写好 Skill 的研究建议

### 1. 先从失败案例反推

不要一开始就写“理想流程”。先收集 3-5 次真实失败：

| 失败类型 | Skill 里应该补什么 |
| --- | --- |
| Agent 不知道该用这个 skill | 改 `description` 和触发条件。 |
| Agent 用了 skill 但走错步骤 | 在 `SKILL.md` 补操作顺序和完成标准。 |
| Agent 每次都写重复代码 | 抽到 `scripts/`。 |
| Agent 需要查大量细节 | 放到 `references/`，在 `SKILL.md` 写何时读取。 |
| Agent 误用工具或越权 | 加边界、权限、停止条件。 |

### 2. 把 description 当成入口路由器

Skill 能否被正确触发，主要取决于 `name` 和 `description`。写 description 时要回答：

```text
Use when ...
Especially when ...
Do not use when ...
```

它不是宣传文案，而是给 Agent 的路由规则。

### 3. 保持一个 Skill 只做一件事

OpenAI Codex 文档也强调：每个 skill 应该聚焦一个 job。一个 skill 同时管“写代码、查资料、发消息、部署、复盘”，通常会变成模糊的大杂烩。

更好的拆法：

| 差拆法 | 好拆法 |
| --- | --- |
| `project-helper` | `gh-fix-ci`、`write-release-note`、`deploy-vercel` |
| `study-assistant` | `lecture-capture`、`concept-card-builder`、`weekly-review` |
| `browser-tools` | `browser-login-check`、`web-ui-regression-test` |

### 4. 控制上下文，不要堆材料

Skill 是 context engineering，不是资料仓库。Anthropic 的建议很关键：context window 是公共资源，只写模型真正需要、且当前任务会用到的东西。

优先级：

```text
必须每次都知道 -> SKILL.md
偶尔才需要 -> references/
能稳定执行 -> scripts/
输出模板资源 -> assets/
```

### 5. 区分 instruction、script、reference

| 内容类型 | 适合放哪里 | 判断标准 |
| --- | --- | --- |
| 判断原则、流程、边界 | `SKILL.md` | Agent 每次使用 skill 都要看。 |
| 大段 API 文档、schema、例子 | `references/` | 只有特定分支才需要。 |
| 稳定可执行步骤 | `scripts/` | 重复、易错、需要确定性。 |
| 模板、图片、样例文件 | `assets/` | 用作输出资源，不必读进上下文。 |

### 6. 用最小可用 Skill 迭代

不要试图一次写完“完美 skill”。更稳的流程：

```text
写最小 SKILL.md
-> 用真实任务测试
-> 记录 Agent 走偏点
-> 补触发条件、边界、例子或脚本
-> 再测试
```

### 7. 给 Skill 写“停止条件”

好 skill 不只告诉 Agent 做什么，也告诉它什么时候停。

常见停止条件：

- 缺少账号、权限、文件、token。
- 出现 2FA、验证码、人工确认。
- 连续重试仍失败。
- 操作会影响外部世界。
- 任务范围超出 skill 原本目标。

### 8. 测试触发，而不只是测试执行

一个 skill 有两类测试：

| 测试 | 看什么 |
| --- | --- |
| 触发测试 | 该用时会不会用，不该用时会不会误用。 |
| 执行测试 | 用了之后是否能稳定完成任务。 |

触发测试可以准备一组 prompts：

```text
应该触发的 5 个 prompt
不应该触发的 5 个 prompt
边界模糊的 5 个 prompt
```

## 需要深入思考的问题

| 问题 | 为什么重要 |
| --- | --- |
| 这个 skill 解决的是知识问题、流程问题，还是工具使用问题？ | 决定该写 instruction、reference 还是 script。 |
| 触发条件是否足够窄？ | 过宽会误触发，过窄会漏触发。 |
| 哪些内容必须进上下文，哪些只需要路径/索引？ | 直接影响 token 成本和注意力。 |
| 这件事是否需要确定性？ | 需要确定性就应该考虑脚本。 |
| 失败时 Agent 应该重试、降级、问用户，还是停止？ | 决定 skill 的可靠性。 |
| 这个 skill 是否会扩大权限面？ | 涉及安全、凭据、外部写入。 |
| 是否应该拆成多个 micro-skills？ | 防止一个大 skill 变成混乱上下文包。 |
| 如何判断 skill 真的有用？ | 需要真实任务、失败率、节省时间、输出质量来评估。 |
| Sub-agent 能否/是否应该使用这个 skill？ | 涉及上下文隔离和资源隔离。 |
| 这个 skill 的经验什么时候应该沉淀进 Memory，什么时候应该写进 Skill？ | Memory 记录偏好和经验，Skill 记录可复用流程。 |

## 和 Tool / Prompt / Memory 的区别

| 概念 | 作用 | 类比 |
| --- | --- | --- |
| Tool | 让 Agent 能做某个动作 | 手和工具箱 |
| Skill | 告诉 Agent 怎么把工具用于某类任务 | 操作手册和工作流 |
| Prompt | 当前回合给模型的指令和上下文 | 临时任务说明 |
| Memory | 保存过去经验和用户偏好 | 长期笔记 |

## 我的判断

Skill 是把“做过一次的经验”变成“下次可复用的能力”的机制。它本质上是 context engineering：用小而清楚的说明，把模型从通用助手约束成某个场景里的可靠执行者。

## 自测问题

1. Skill 和 Tool 的区别是什么？
2. 为什么 Skill 不应该写得越长越好？
3. 什么内容应该放在 `SKILL.md`，什么内容应该放在 `references/`？
4. 什么时候应该把流程写成脚本而不是自然语言说明？
