---
type: project
status: active
tags: [codex, skills, agent-skills, tooling, ai-agent]
created: 2026-06-21
updated: 2026-06-21
origin_type: 自主学习
origin: Agent与经营分析专题研究
repo:
---

# Codex Skills 生态调研报告

## 调研内容摘要

这次调研的核心结论：

1. **Codex Skill 的正式形态已经比较清楚**：一个 Skill 是包含 `SKILL.md` 的目录，可带 `scripts/`、`references/`、`assets/`。它适合沉淀“可重复任务流程”，不是泛泛的提示词收藏。
2. **优先学习官方 `openai/skills`**：这是当前最值得当作写法基准的仓库，包含 system、curated、experimental 三类 Skill。它比社区合集更适合学习 Codex 期望的结构、触发描述和渐进式加载方式。
3. **社区高星仓库很多，但质量差异大**：`addyosmani/agent-skills`、`kepano/obsidian-skills`、`Dimillian/Skills`、`VoltAgent/awesome-agent-skills`、`ComposioHQ/awesome-codex-skills` 都值得看，但要先审查 `SKILL.md`、脚本、安装方式和供应链风险。
4. **对当前学习 vault 最有用的方向**：Obsidian/Markdown、研究资料整理、GitHub 工作流、浏览器验证、PDF/文档处理、项目复盘、Codex 使用方法本身。
5. **不建议一口气安装大包**：Skill 数量过多会稀释触发匹配，官方文档也提到 Codex 初始上下文只会带入有限的 Skill 列表。更好的做法是按任务安装少量、试用、复盘，再沉淀为自己的 repo/global Skill。

## 先厘清：Skill、Plugin、MCP 的边界

| 对象 | 适合放什么 | 典型例子 | 使用建议 |
| --- | --- | --- | --- |
| `AGENTS.md` | 当前仓库的长期约定、目录规则、协作方式 | 本 vault 的学习工作流、笔记分层规则 | 仓库级默认行为放这里 |
| Skill | 可重复任务流程、领域方法、检查清单、辅助脚本 | PDF 处理、PR 评论处理、Obsidian 笔记整理 | 一个 Skill 只做一类任务 |
| Plugin | 可安装分发包，可包含多个 skills、MCP、app connector、hooks、assets | GitHub、Google Drive、Vercel、Figma 插件包 | 多个能力一起分发时使用 |
| MCP / Connector | 真实外部数据或动作能力 | GitHub、Google Drive、Sentry、Figma | 需要读写外部系统时使用 |
| Hook | 工具调用前后的机械约束 | 禁止危险命令、运行格式化检查 | 需要强制执行规则时使用 |

严格版理解：Skill 是“让 Codex 学会某类工作流”的最小可复用单元；Plugin 是“把能力打包安装”的分发单元。

## 官方基准：OpenAI / Codex Skills

| 来源 | 当前信号 | 价值 | 备注 |
| --- | --- | --- | --- |
| [OpenAI Codex Skills 文档](https://developers.openai.com/codex/skills) | 官方文档 | 解释 Skill 结构、触发、保存位置、渐进式加载 | 作为规则源 |
| [openai/skills](https://github.com/openai/skills) | GitHub API：约 22.6k stars，2026-06-17 push | 官方 Skill catalog | 最值得学习结构 |
| [Agent Skills specification](https://agentskills.io/specification) | 开放规范 | 定义 `SKILL.md` frontmatter、目录结构、脚本/引用/资产 | 跨 Codex、Claude Code、Cursor 等生态 |
| Codex 当前本机环境 | 本机约 152 个可发现 `SKILL.md` | 已经装有不少 OpenAI curated / plugin skills | 可优先学习已安装的 Skill |

官方 Skill 的要点：

| 机制 | 关键点 | 对我们自建 Skill 的启发 |
| --- | --- | --- |
| 渐进式加载 | 启动时只看 name、description、path，命中后再读完整 `SKILL.md` | description 要写清楚触发条件 |
| 必需文件 | `SKILL.md`，frontmatter 至少有 `name` 和 `description` | 不要把 Skill 写成散文 |
| 可选资源 | `scripts/`、`references/`、`assets/` | 大段参考资料和可执行步骤要外置 |
| 安装方式 | 官方建议用 `$skill-installer` 安装 curated / experimental skills | 少量按需安装，不要全量堆叠 |
| 分发方式 | 本地 Skill 适合个人/仓库，Plugin 适合团队/市场分发 | vault 专属能力先做 Skill，成熟后再考虑 plugin |

## 官方 curated Skill 清单里值得优先看的

| Skill | 解决的问题 | 学习价值 | 对我的建议 |
| --- | --- | --- | --- |
| `openai-docs` | 查询 OpenAI / Codex 官方文档 | 学习“先查权威来源再回答”的 Skill 写法 | 已经很适合当前 Codex 学习 |
| `migrate-to-codex` | 从其他 agent 配置迁移到 Codex | 学习迁移类 Skill 如何拆流程、先扫描再写入 | 可用于理解 Codex 配置面 |
| `gh-address-comments` | 处理 GitHub PR review comments | 学习外部 CLI + 用户确认 + 修复闭环 | 适合真实项目协作 |
| `gh-fix-ci` | 调查 GitHub Actions 失败 | 学习如何拉日志、定位失败、先总结再修复 | 很适合工程项目 |
| `playwright` / `playwright-interactive` | 浏览器自动化、截图、UI 调试 | 学习“真实运行验证”的 Skill | 前端/网页任务必备 |
| `pdf` | 阅读、生成、检查 PDF | 学习文档类任务如何做视觉验证 | 适合报告、资料处理 |
| `security-threat-model` | repo 级威胁建模 | 学习高风险任务如何要求证据、边界和假设 | 适合安全/架构学习 |
| `sentry` | 读取生产错误和事件 | 学习只读 observability workflow | 适合线上问题排查 |
| `yeet` | stage、commit、push、PR 一条龙 | 学习发布流程 Skill | 只在明确要求时触发 |

## 社区高星与代表性仓库

数据时间：2026-06-21 16:21 CST，主要来自 GitHub API 和仓库 README。星标会变化，以下作为选型快照。

| 仓库 | stars | 类型 | 亮点 | 风险/注意 |
| --- | ---: | --- | --- | --- |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | 64.3k | 工程生命周期 Skill pack | 覆盖 spec、plan、build、test、review、ship、webperf、simplify 等 24 个技能；强调质量门禁 | README 主要面向多 agent，Codex 安装需要按实际路径适配；不要全量照搬 |
| [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) | 36.3k | Obsidian 专用 Skill pack | Markdown、Bases、JSON Canvas、Obsidian CLI、网页清洗 | 和本 vault 高相关；安装前先审查是否会改 Obsidian 特有语法 |
| [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) | 23.7k | 文件化计划 Skill | 把长任务计划写入 Markdown 文件，避免上下文丢失 | 可能和 Codex 自带 plan 工具重叠；适合研究其状态持久化思路 |
| [openai/skills](https://github.com/openai/skills) | 22.6k | 官方 catalog | 官方 system / curated skills，最接近 Codex 设计预期 | individual skill license 要看对应目录 |
| [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) | 26.0k | 索引/awesome list | 收录 1000+ agent skills，按来源和领域分类 | README 明确说未安全审计；适合发现，不适合直接安装 |
| [ComposioHQ/awesome-codex-skills](https://github.com/ComposioHQ/awesome-codex-skills) | 14.0k | Codex skills awesome list | 面向 Codex CLI/API 自动化场景 | license 未明确；当索引用 |
| [heilcheng/awesome-agent-skills](https://github.com/heilcheng/awesome-agent-skills) | 5.7k | 教程/目录 | 更偏学习入口，覆盖 Codex、Claude、Copilot、MCP | 需要二次筛选 |
| [Dimillian/Skills](https://github.com/Dimillian/Skills) | 3.7k | 个人工程实践 Skill pack | Apple 平台、GitHub、React performance、review swarm、bug hunt、项目 Skill audit | 很适合学习“真实工程师把重复工作沉淀成 Skill”的写法 |

## 对你最值得优先学习的 Skill 类型

| 优先级 | Skill 类型 | 为什么适合你 | 推荐来源 |
| --- | --- | --- | --- |
| P0 | Codex 自身学习 / 官方文档 | 你经常会问 Codex 能力边界、配置、插件、Skill 区别 | `openai-docs`、官方文档、`openai/skills` |
| P0 | Obsidian / Markdown vault | 当前 `agent_learning` 就是长期学习 vault | `kepano/obsidian-skills`，再做自己的 vault Skill |
| P0 | 研究资料整理 | 你常做 AI Agent / 业务分析调研，需要摘要、来源、图表、跳转 | 自建 `research-report` 或基于现有 docs/pdf skills |
| P1 | GitHub 工作流 | PR、CI、评论处理很适合 Skill 化 | `gh-fix-ci`、`gh-address-comments`、`Dimillian/Skills` 的 GitHub skill |
| P1 | 浏览器验证 | 以后做网页、资料抽取、UI 验证会常用 | `playwright`、browser / chrome skills |
| P1 | PDF / 文档处理 | 论文、报告、分享材料会用到 | `pdf`、documents、presentations |
| P2 | 工程质量门禁 | 当你做真实项目时，review/test/security/perf Skill 很有价值 | `addyosmani/agent-skills`、OpenAI security skills |
| P2 | 文件化计划 / 长任务状态 | 长任务中断后恢复、跨线程继续 | `planning-with-files`，但要和 Codex 自带 plan/goal 区分 |

## 不建议优先安装的类型

| 类型 | 原因 | 更好的做法 |
| --- | --- | --- |
| 超大 awesome list 全量安装 | 会污染 Skill 匹配，且安全/质量不均 | 当索引用，按需挑单个 Skill |
| 带大量脚本但说明不清的 Skill | 可能执行网络、文件、token、环境操作 | 先读 `SKILL.md`、`scripts/`、license |
| 泛泛的“best practices”大杂烩 | 容易变成另一个 AGENTS.md，触发边界不清 | 拆成具体任务 Skill |
| 与现有 Codex skill 重复的 Skill | 同名或相似 Skill 会让选择变混乱 | 保留一个更可信的版本 |

## 安装与审查建议

优先顺序：

1. 先看官方 curated skill：`$skill-installer <skill-name>`。
2. 第三方仓库先用 GitHub CLI 或手动方式预览，不直接运行脚本。
3. 只把稳定、经常用、边界清楚的 Skill 放到全局。
4. 和某个 repo 强绑定的 Skill 放到该 repo 的 `.agents/skills/`。
5. 安装后新开线程测试触发是否准确。

GitHub CLI 已经支持 agent skill 管理，`gh skill` 可发现、安装、更新、pin 版本，并支持 `--agent codex`。它还强调第三方 Skill 可能包含 prompt injection、隐藏指令或恶意脚本，所以安装前应预览。

推荐审查清单：

| 检查项 | 要看什么 |
| --- | --- |
| Frontmatter | `name` 是否规范，`description` 是否说明何时使用 |
| 触发边界 | 是否明确“不该什么时候触发” |
| 脚本 | 是否访问网络、token、home 目录、SSH key、浏览器 profile |
| 写入范围 | 是否会改全局配置、删除文件、提交代码 |
| 依赖 | 是否要求 npm/pip/curl/install 脚本 |
| license | 能否在个人/团队场景使用 |
| 维护状态 | 最近 push、issue、release、fork/stars 是否合理 |
| 与现有 Skill 冲突 | 是否和已安装 Skill 同名或功能重叠 |

## 可以马上做的三件事

### 1. 建一个 vault 专属 Skill

建议名称：`agent-learning-vault`

用途：把当前 `AGENTS.md` 的学习规则升级成可显式调用的工作流 Skill，但不要替代 `AGENTS.md`。它可以专门处理：

- 课程/讲座原始记录进入 `00-inbox/`
- 调研报告进入 `30-projects/`
- 确认后的概念进入 `20-concepts/`
- DeepMe / 认知迭代进入 `60-cognition/`
- 分享稿使用“摘要 + 图表 + 跳转”的结构
- 区分 `用户假设`、`助手反馈`、`待确认`、`已确认`

### 2. 选 3 个第三方 Skill 做拆解学习

| 拆解对象 | 学什么 |
| --- | --- |
| `openai-docs` | 如何把权威来源、fallback、边界不确定性写进 Skill |
| `kepano/obsidian-skills` | 如何让 agent 遵守 Obsidian Markdown / Bases / Canvas 语法 |
| `Dimillian/Skills` 的 `project-skill-audit` 或 review 类 Skill | 如何从真实重复工作反推“该写什么 Skill” |

### 3. 建一张个人 Skill 候选池

| 候选 Skill | 先做 instruction-only 还是带脚本 | 触发词 | 成熟后放哪里 |
| --- | --- | --- | --- |
| `agent-learning-vault` | instruction-only | “整理笔记”“学习 vault”“课程笔记”“调研报告” | repo `.agents/skills/` |
| `research-share-report` | instruction-only + optional Mermaid templates | “调研”“分享报告”“摘要+跳转” | repo `.agents/skills/` |
| `codex-usage-review` | script | “统计 token”“Codex 使用量” | global / personal |
| `obsidian-markdown-check` | script | “检查 Obsidian 预览”“图片路径” | repo `.agents/skills/` |
| `github-release-sync` | instruction + script | meditation_app 发布同步 | 对应 repo `.agents/skills/` |

## 我的判断

如果目标是“更好地使用 Codex”，不要先追求安装最多 Skill。更高收益的路线是：

1. **读官方 `openai/skills` 的写法**，掌握 Codex 如何选择 Skill。
2. **从你真实高频任务里抽 3 个 Skill**：学习笔记整理、调研报告、Codex/GitHub 工作流。
3. **每次 Codex 做错一类重复任务，就把修正沉淀进对应 Skill 或 AGENTS.md**。
4. **第三方 Skill 先当范例库**，确认结构、脚本和依赖后再安装。

对当前 vault 来说，最值得先做的是 `agent-learning-vault` 和 `research-share-report` 两个 repo-scoped skills。它们不需要复杂脚本，但能显著降低每次重新说明规则的成本。

## 资料来源

- [OpenAI Codex Skills 文档](https://developers.openai.com/codex/skills)
- [OpenAI Codex Plugins 文档](https://developers.openai.com/codex/plugins)
- [openai/skills](https://github.com/openai/skills)
- [Agent Skills specification](https://agentskills.io/specification)
- [GitHub Changelog: Manage agent skills with GitHub CLI](https://github.blog/changelog/2026-04-16-manage-agent-skills-with-github-cli/)
- [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills)
- [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills)
- [Dimillian/Skills](https://github.com/Dimillian/Skills)
- [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills)
- [ComposioHQ/awesome-codex-skills](https://github.com/ComposioHQ/awesome-codex-skills)
- [heilcheng/awesome-agent-skills](https://github.com/heilcheng/awesome-agent-skills)
