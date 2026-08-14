---
type: project
status: active
tags: [codex, ai-agent, harness-engineering, mcp, plugins, hooks, skills]
created: 2026-06-21
updated: 2026-06-21
origin_type: 自主学习
origin: Agent与经营分析专题研究
repo:
---

# Codex 与 Agent 使用方法生态调研报告

## 调研内容摘要

这次调研的核心不应该是“找一批 Skill 装上”，而是理解别人如何把 **Agent 的外部环境** 做好。更准确的主线是：

> 更好地使用 Codex = 设计好 Codex 的 harness：上下文、规则、工具、权限、验证、记忆、自动化和反馈回路。

目前最值得学习的不是单个工具，而是这些层次：

| 层次 | 解决的问题 | 对 Codex 的对应物 |
| --- | --- | --- |
| 规则 / 上下文 | Agent 应该知道什么项目约定 | `AGENTS.md`、全局指导、repo 指导 |
| 可复用流程 | 同一类任务如何稳定执行 | Skills、Custom Prompts |
| 外部能力 | Agent 如何访问真实系统和数据 | MCP、Connectors、CLI、browser/computer use |
| 分发打包 | 一组能力如何复用给不同项目/团队 | Plugins、marketplace |
| 确定性控制 | 哪些规则不能只靠“请你记得” | Hooks、permissions、sandbox、rules |
| 编排 / harness | 如何让 Agent 跑在产品或自动化流程里 | Codex SDK、`codex exec`、OpenAI Agents SDK |
| 验证与反馈 | 如何避免“看起来完成了，其实没完成” | 测试、lint、browser check、CI、trace、review |
| 经验沉淀 | Agent 犯过的错如何不再重复 | 更新 `AGENTS.md`、Skill、hook、测试、文档 |

我的判断：你现在最应该学的是 **Harness Engineering / Context Engineering**，Skill 只是其中一块。

## 一句话框架

| 概念 | 一句话理解 | 什么时候用 |
| --- | --- | --- |
| `AGENTS.md` | 给 Agent 看的 README | 仓库规则、目录结构、测试命令、协作偏好 |
| Skill | 可按需加载的任务手册 | 重复任务、领域流程、文档模板、调研方法 |
| MCP | 标准化外部工具接口 | 需要访问 Figma、Sentry、GitHub、Docs、浏览器、数据库 |
| Plugin | 能力包 | 多个 Skill + MCP + hook + assets 一起分发 |
| Hook | 生命周期脚本 | 阻止危险操作、强制检查、记录日志、自动生成记忆 |
| Subagent | 隔离上下文的专门执行者 | 大任务拆分、并行审查、避免主线程污染 |
| SDK / Harness | 自己写 Agent 运行时 | 需要把 Agent 嵌入产品、CI、后台任务 |
| `codex exec` | 命令行自动化里的 Codex | CI、批处理、日志总结、结构化输出 |

## 关键发现

### 1. Harness 比模型选择更重要

OpenAI、Addy Osmani、HumanLayer、Martin Fowler 这些来源的共识很接近：Agent 的效果不只由模型决定，还由模型外面的约束和反馈决定。

可操作的理解：

- Agent 不知道项目规则 -> 写入 `AGENTS.md`。
- Agent 总是改错边界 -> 用架构文档、lint、测试约束。
- Agent 总是忘记流程 -> 写 Skill。
- Agent 总是做危险操作 -> 加 permission / sandbox / hook。
- Agent 总是“自称完成” -> 加真实验证：测试、浏览器、截图、CI、运行日志。
- Agent 长任务混乱 -> 拆成计划、执行、审查，或用 subagent / 文件化计划。

OpenAI 的 harness engineering 文章特别值得看：它强调把 repository knowledge 变成系统事实源，并用自定义 lint、结构测试、架构边界和“taste invariants”防止速度带来架构漂移。

### 2. `AGENTS.md` 是最基础的投资

官方 Codex manual 说明，Codex 会在运行开始时读取全局、项目和子目录里的 `AGENTS.md` / `AGENTS.override.md`，并按路径层级组合。`agents.md` 站点把它定义成给 coding agents 的开放格式，目前声称已有 60k+ 开源项目采用。

对你的启发：

- 这个 vault 的 `AGENTS.md` 已经是正确方向。
- 后续不一定先做 Skill，很多稳定规则应先放在 `AGENTS.md`。
- 但 `AGENTS.md` 不应该无限膨胀；可重复任务流程应拆成 Skill。
- 子目录如果有特殊规则，可以用更近的 `AGENTS.md` 或 `AGENTS.override.md`。

建议本 vault 后续分层：

| 规则类型 | 放哪里 |
| --- | --- |
| 整个 vault 的目录分层、学习态度、命名规则 | 根目录 `AGENTS.md` |
| 某个课程或项目的专属规则 | 对应子目录 `AGENTS.md` |
| 临时覆盖 | `AGENTS.override.md`，用完删除 |
| 复杂工作流 | `.agents/skills/<skill-name>/SKILL.md` |
| 强制检查 | `.codex/hooks.json` 或 `.codex/config.toml` |

### 3. Skill 是“流程模块”，不是“能力越多越好”

官方 Codex Skills、Anthropic Agent Skills、Agent Skills specification 都强调 progressive disclosure：启动时只加载 name / description，命中后再加载完整说明，必要时再读 `references/`、`scripts/`、`assets/`。

对你最有价值的 Skill 类型不是通用大包，而是这些：

| Skill 候选 | 价值 |
| --- | --- |
| `agent-learning-vault` | 把 `Capture -> Understand -> Retrieve -> Build -> Teach -> Review` 固化成可调用流程 |
| `research-share-report` | 把调研报告固定成“摘要 + 表格 + 图 + 跳转 + 结论” |
| `obsidian-markdown-check` | 检查 Obsidian/GitHub 友好的 Markdown、图片相对路径、内链 |
| `codex-usage-review` | 固化本地 Codex token 使用量统计方法 |
| `github-release-sync` | 固化 meditation_app 的部署后 GitHub main 同步规则 |

可学习来源：

- [openai/skills](https://github.com/openai/skills)：官方结构基准。
- [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills)：Obsidian/Markdown/Bases/Canvas，高度相关。
- [Dimillian/Skills](https://github.com/Dimillian/Skills)：真实工程重复任务沉淀。
- [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills)：工程生命周期和质量门禁。

### 4. MCP 是工具接口，但不是所有工具都要 MCP 化

MCP 适合把外部系统标准化暴露给 Agent。官方 Codex manual 支持 STDIO 和 HTTP MCP servers，能设置 OAuth、bearer token、tool allow/deny list、per-tool approval mode、startup/tool timeout 等。MCP 官方 tools spec 也强调工具可被模型自动发现和调用，但应该有人类确认机制。

关键判断：

| 情况 | 更适合 |
| --- | --- |
| Agent 需要 Figma、Sentry、浏览器、私有文档、数据库 | MCP / Connector |
| Agent 只是需要 Git、gh、npm、pytest、ripgrep | 直接用 CLI，未必需要 MCP |
| 外部系统有权限/审计/结构化 API | MCP 很适合 |
| 只是几条固定命令 | Skill 或 `AGENTS.md` 即可 |
| 需要跨多个工具编排 | Skill 说明流程，MCP 提供工具 |

风险点：

- MCP server 的 tool description 会进入 Agent 上下文，可能变成 prompt injection 向量。
- STDIO MCP 可能通过 `npx` / `uvx` 在本机执行代码。
- 不要连接不可信 MCP；生产环境应有 allowlist、approval、最小权限、token 隔离。

### 5. Hook 是把“软规则”变成“硬约束”的位置

Codex Hooks 可以在生命周期里运行脚本，例如 `PreToolUse`、`PostToolUse`、`PermissionRequest`、`UserPromptSubmit`、`Stop`、`SessionStart` 等。官方文档给的典型用途包括：阻止粘贴 API key、记录日志、生成记忆、停止时跑验证、按目录注入提示。

适合 Hook 的事情：

| Hook 用途 | 示例 |
| --- | --- |
| 禁止危险操作 | 阻止 `rm -rf`、阻止改 `.env`、阻止提交大文件 |
| 自动检查 | Markdown lint、图片路径检查、禁止绝对本地图片路径 |
| 任务结束检查 | 如果改了前端，要求截图或 Playwright 检查 |
| 记忆生成 | Stop 后提取可复用经验，但要避免污染 |
| 成本/日志 | 记录 token、耗时、工具调用模式 |

不适合 Hook 的事情：

- 复杂推理。
- 大段解释。
- 需要用户判断的取舍。
- 不稳定、经常误杀的规则。

### 6. Plugin 是打包层，不是更高级的 Skill

Codex plugin 可以打包 skills、MCP config、hooks、assets、apps。官方文档的边界很清楚：本地反复迭代先用 Skill；要给团队、多个项目、workspace 共享，再做 Plugin。

对你当前阶段：

- 不急着写 Plugin。
- 先把 `agent-learning-vault` 和 `research-share-report` 做成 repo-scoped Skill。
- 如果多个 repo 都要复用，比如 Codex token monitor、GitHub release sync，再考虑个人 plugin。

可参考：

- [hashgraph-online/awesome-codex-plugins](https://github.com/hashgraph-online/awesome-codex-plugins)：Codex plugins 索引，适合发现模式。
- Codex 官方 plugin docs：理解 manifest、marketplace、bundled MCP/hooks。

### 7. SDK / Harness 是“自己构建 Agent 系统”的路线

这里要分两条：

| 路线 | 适合场景 | 学习对象 |
| --- | --- | --- |
| 使用 Codex 做自动化 | CI、批处理、日志总结、自动修复、结构化输出 | `codex exec`、Codex SDK、Codex GitHub Action |
| 自己构建 Agent 应用 | 产品内 agent、业务流程 agent、多 agent 协作 | OpenAI Agents SDK、12-factor agents、MCP |

Codex SDK / `codex exec` 的价值：

- 把 Codex 放进 CI 或脚本。
- 使用 JSONL 输出和 schema 输出。
- 在受控 sandbox 里运行。
- 让 Codex 生成 patch，再由另一个 job 开 PR，降低 token/secret 暴露风险。

OpenAI Agents SDK 的价值：

- 你自己管理 agent definitions、tools、handoffs、guardrails、state、observability。
- 当你要做“业务 Agent 产品”而不是“用 Codex 改代码”时更合适。

### 8. 规范文档和经验文档值得系统读

优先级建议：

| 优先级 | 资料 | 学什么 |
| --- | --- | --- |
| P0 | [OpenAI Codex Best Practices](https://developers.openai.com/codex/learn/best-practices) | Codex 官方推荐的提示、计划、AGENTS.md、配置 |
| P0 | [OpenAI Harness Engineering](https://openai.com/index/harness-engineering/) | repo knowledge、架构边界、lint/测试如何成为 agent 加速器 |
| P0 | [AGENTS.md](https://agents.md/) | 给 coding agents 的开放项目说明格式 |
| P0 | [Codex Manual](https://developers.openai.com/codex/codex-manual.md) | Codex 的 Skills、Plugins、MCP、Hooks、SDK、exec、permissions |
| P1 | [12-factor-agents](https://github.com/humanlayer/12-factor-agents) | 自己构建可靠 LLM app / agent harness 的原则 |
| P1 | [HumanLayer: Harness Engineering](https://www.humanlayer.dev/blog/skill-issue-harness-engineering-for-coding-agents) | Skills、MCP、subagents、hooks 作为 harness 配置面 |
| P1 | [Martin Fowler: Harness engineering for coding agent users](https://martinfowler.com/articles/harness-engineering.html) | 从用户侧理解 coding agent harness |
| P1 | [Martin Fowler: Encoding Team Standards](https://martinfowler.com/articles/reduce-friction-ai/encoding-team-standards.html) | 团队标准如何变成版本化 artifact |
| P1 | [Anthropic Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) | Skills 的渐进式披露、脚本、安全审查 |
| P2 | [MCP Tools Spec](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) | 工具发现、调用、人类确认、安全边界 |

## 仓库与资源快照

数据时间：2026-06-21 16:24 CST，星标会变化。

| 仓库 / 资源 | stars | 类型 | 用途 |
| --- | ---: | --- | --- |
| [openai/codex](https://github.com/openai/codex) | 92.4k | Codex CLI 开源仓库 | 理解 Codex CLI、SDK、issue/discussion |
| [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) | 87.5k | MCP servers 集合 | 看常见 MCP server 如何组织 |
| [openai/openai-agents-python](https://github.com/openai/openai-agents-python) | 27.3k | Agents SDK | 自建多 agent workflow |
| [humanlayer/12-factor-agents](https://github.com/humanlayer/12-factor-agents) | 23.4k | Agent 设计原则 | context/control/state/human-in-loop 思维 |
| [agentsmd/agents.md](https://github.com/agentsmd/agents.md) | 22.4k | AGENTS.md 标准 | 项目说明文档规范 |
| [openai/skills](https://github.com/openai/skills) | 22.6k | Codex Skills catalog | 学 Skill 结构 |
| [modelcontextprotocol/modelcontextprotocol](https://github.com/modelcontextprotocol/modelcontextprotocol) | 8.4k | MCP 规范文档 | 理解协议本身 |
| [DenisSergeevitch/agents-best-practices](https://github.com/DenisSergeevitch/agents-best-practices) | 2.0k | Provider-neutral Agent Skill | 学 harness 审计/设计框架 |
| [openai/codex-action](https://github.com/openai/codex-action) | 1.1k | GitHub Action | 学 CI 自动修复模式 |
| [hashgraph-online/awesome-codex-plugins](https://github.com/hashgraph-online/awesome-codex-plugins) | 0.5k | Codex plugin 索引 | 发现插件生态 |

## 从别人的经验里提炼出的原则

### 原则 1：把“提示词技巧”升级成“版本化 artifact”

不要把有效提示词留在聊天记录里。逐步沉淀成：

| 临时经验 | 长期 artifact |
| --- | --- |
| “下次整理笔记要区分用户假设和助手反馈” | `AGENTS.md` 或 `agent-learning-vault` Skill |
| “生成报告要先摘要再详情跳转” | `research-share-report` Skill |
| “图片路径不要改绝对路径” | `obsidian-markdown-check` hook / Skill |
| “发布后 GitHub main 必须对齐部署 commit” | repo-specific `AGENTS.md` 或 Skill |

### 原则 2：能用确定性工具验证，就不要只靠模型自评

Agent 最容易错在“看起来完成”。更好的验证层级：

1. 静态检查：lint、typecheck、Markdown link check。
2. 单元/集成测试：证明逻辑。
3. 真实运行：dev server、CLI command、browser screenshot。
4. 外部状态核对：GitHub、deployment、Sentry、logs。
5. 人类审查：高风险取舍、产品体验、业务含义。

### 原则 3：工具越强，边界越要窄

MCP、browser、computer use、GitHub connector、Google Drive connector 都能让 Agent 做真实动作。能力越强，越需要：

- 最小权限。
- 明确 approval mode。
- 限定工具 allowlist。
- 不把 token 暴露给不可信代码。
- 先读后写。
- 高风险操作拆成计划 + 确认 + 执行。

### 原则 4：上下文不是越多越好

12-factor agents 和 harness engineering 的共同点是“own your context”。对于 Codex 使用者，可以转成这些实践：

- `AGENTS.md` 写稳定规则，不写长篇背景故事。
- Skill 的 `description` 写清楚触发条件。
- 大段参考资料放 `references/`，需要时再读。
- 长任务用计划/文件化状态，避免主上下文混乱。
- 大任务让 subagent 做读-only 审查，主线程保留决策权。

### 原则 5：把 Agent 犯错当成系统缺口

每次 Codex 做错，不只修本次结果，还问一句：

| 错误类型 | 应沉淀到哪里 |
| --- | --- |
| 不懂仓库结构 | `AGENTS.md` / README / 架构图 |
| 漏跑测试 | `AGENTS.md` / hook / CI |
| 重复问同样信息 | Skill / template |
| 操作太危险 | permission / sandbox / hook |
| 工具选择错误 | Skill 说明 / MCP tool description / disable tools |
| 长任务跑偏 | plan / subagent / checkpoint |

## 对你当前最实用的路线图

### 阶段 1：读和整理

先读这些：

1. OpenAI Harness Engineering。
2. OpenAI Codex Best Practices。
3. AGENTS.md。
4. 12-factor-agents 的 factor 2、3、8、10、12。
5. Anthropic Agent Skills。
6. Codex Hooks / MCP / Plugins / SDK 文档。

产物：

- `20-concepts/Harness Engineering.md`
- `20-concepts/Context Engineering.md`
- `20-concepts/AGENTS.md 与 Skill 的边界.md`
- `20-concepts/MCP 与 Skill 的边界.md`

### 阶段 2：改造本 vault

建议做三个可执行 artifact：

| Artifact | 类型 | 作用 |
| --- | --- | --- |
| `agent-learning-vault` | repo Skill | 处理学习笔记、课程、概念沉淀、复盘 |
| `research-share-report` | repo Skill | 调研报告/分享稿标准流程 |
| `obsidian-markdown-check` | hook 或 Skill | 检查 Markdown、图片路径、Obsidian 兼容 |

### 阶段 3：建立 Codex 使用复盘机制

建议每周记录一次：

| 复盘问题 | 目的 |
| --- | --- |
| Codex 哪类任务做得最好？ | 找高 ROI 场景 |
| 哪类任务反复跑偏？ | 判断要不要写 Skill / Hook |
| 哪些上下文每次都要重复解释？ | 放进 AGENTS.md |
| 哪些错误应该被工具阻止？ | 写 hook 或测试 |
| 哪些外部数据经常需要查？ | 考虑 MCP / Connector |

### 阶段 4：再考虑插件和自动化

等前面稳定后，再做：

- 个人 Codex plugin：打包 vault skills + hooks。
- `codex exec` 自动化：定期生成复盘、统计 token、检查 Markdown。
- MCP：只给高频、可信、结构化外部系统接入。

## 推荐先做的下一步

我建议下一步不是安装一堆东西，而是创建一个 repo-scoped Skill：

```text
.agents/skills/agent-learning-vault/SKILL.md
```

它专门服务这个 vault，触发条件包括“整理学习笔记”“课程笔记”“调研报告”“概念沉淀”“复盘”。这会把你现在的 `AGENTS.md` 规则变成更可调用的工作流，同时保留 `AGENTS.md` 作为长期底座。

第二个再做：

```text
.agents/skills/research-share-report/SKILL.md
```

它负责你常做的调研/分享稿结构：摘要、表格、Mermaid、来源、结论、跳转。

## 资料来源

- [OpenAI: Harness engineering](https://openai.com/index/harness-engineering/)
- [OpenAI Codex Best Practices](https://developers.openai.com/codex/learn/best-practices)
- [OpenAI Codex Manual](https://developers.openai.com/codex/codex-manual.md)
- [OpenAI Codex Hooks](https://developers.openai.com/codex/hooks)
- [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents)
- [AGENTS.md](https://agents.md/)
- [Agent Skills specification](https://agentskills.io/specification)
- [Anthropic: Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [MCP Tools specification](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
- [HumanLayer: 12-factor-agents](https://github.com/humanlayer/12-factor-agents)
- [HumanLayer: Harness Engineering for Coding Agents](https://www.humanlayer.dev/blog/skill-issue-harness-engineering-for-coding-agents)
- [Martin Fowler: Harness engineering for coding agent users](https://martinfowler.com/articles/harness-engineering.html)
- [Martin Fowler: Encoding Team Standards](https://martinfowler.com/articles/reduce-friction-ai/encoding-team-standards.html)
- [Martin Fowler: The role of developer skills in agentic coding](https://martinfowler.com/articles/exploring-gen-ai/13-role-of-developer-skills.html)
- [openai/skills](https://github.com/openai/skills)
- [openai/codex-action](https://github.com/openai/codex-action)
- [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers)
- [hashgraph-online/awesome-codex-plugins](https://github.com/hashgraph-online/awesome-codex-plugins)
