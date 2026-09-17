# 2026-08-22 Codex 与 Claude 记忆结构调研

## 原始问题

> 翻译 OpenAI 官方的 Memories 页面，了解 Codex 的整个记忆结构，并同时调研 Claude 的对应机制。

## 用户理解

- 用户希望先看中文翻译，再理解 Codex 与 Claude 的整体记忆结构。
- 用户尚未对两者的机制提出具体假设；本记录不预设用户已理解。

## Codex 反馈

### 1. 先分清四种容易被统称为“记忆”的东西

| 层级 | 作用 | 是否跨会话 |
| --- | --- | --- |
| 当前 context | 本次推理正在使用的消息、文件、工具结果和指令 | 否，需要 resume、compaction 或其他持久层帮助延续 |
| session / rollout | 持久化的会话与工具轨迹，用于恢复、审计和后续提取 | 可以被继续或后处理 |
| 长期 memory | 从历史任务中提取的可复用偏好、事实、决策与教训 | 是 |
| 持久指令 | `AGENTS.md` / `CLAUDE.md` 中人工维护的规则 | 是，但它不应与自动记忆混为一层 |

核心边界：记忆只是召回的 context，不是模型权重被重新训练，也不是必然执行的硬规则。

### 2. Codex 官方页面的主要事实

- ChatGPT Web 使用 ChatGPT memory；本地 Codex 客户端使用独立的本地 memory store 和控制项。
- 必须稳定生效的团队指导应该放在 `AGENTS.md` 或版本库文档里，memory 只是辅助召回层。
- 本地 memory 开启后，Codex 会在后台将符合条件的旧会话转换为本地记忆文件；活跃或太短的会话可能被跳过，生成存在延迟。
- 默认存储位置是 `~/.codex/memories/`；官方将其概括为 summaries、durable entries、recent inputs 和 supporting evidence。
- 单个会话可分别控制“是否使用旧记忆”和“是否成为未来记忆的输入”；单会话选项不会改变全局设置。
- 常用配置将生成与使用拆开：`generate_memories` 控制新对话是否进入生成候选，`use_memories` 控制未来会话是否注入旧记忆。

### 3. 当前本机 Codex 的可观察结构

```text
~/.codex/
├── sessions/                 # 原始任务 rollout / 事件轨迹
├── memories_1.sqlite        # 后台记忆任务和单线程阶段输出元数据
└── memories/
    ├── raw_memories.md      # 按 thread/task 组织的候选记忆集合
    ├── rollout_summaries/   # 每个历史任务的证据型摘要
    ├── MEMORY.md            # 跨任务归并后的可检索详细索引
    ├── memory_summary.md    # 高密度全局摘要，用于新任务快速定位
    └── extensions/           # 其他记忆来源与各自的合并规则
```

本机当前 `config.toml` 中 `features.memories`、`generate_memories` 和 `use_memories` 均为开启。这是 2026-08-22 的本机观察，不等于所有 Codex 安装的固定默认。

可观察的生成链可概括为：

```text
rollout/session
  → 单线程候选提取（raw_memory + rollout_summary）
  → 跨线程 consolidation
  → MEMORY.md + memory_summary.md
  → 新任务快速摘要 + 按需检索
```

官方页面没有承诺这些文件的内部 schema 永久稳定；它们应视为可检查的 generated state，而不是首选的手工编辑控制面。

### 4. Claude 需要分为三个产品层谈

#### Claude 应用

- 新版记忆以“分类的独立记忆条目”保存，对话中实时读写和更新。
- 每个 Project 有独立 memory space 和 project summary，与非 Project 对话分离。
- “搜索过去对话”是另一条 RAG 路径，调用时在对话中显示为工具调用；不要把它与已提取的 memory entry 混同。
- 用户可查看、修改、删除、暂停或重置记忆；Incognito chat 不进入聊天历史和记忆。

#### Claude Code

- 每次 session 从新 context window 开始，跨会话依靠两个互补机制：人写的 `CLAUDE.md` 与 Claude 写的 auto memory。
- `CLAUDE.md` 可按组织、用户、项目、本地和路径分层；它们是注入 context 的行为指导，不是强制配置。
- auto memory 按 Git 仓库分区，同一仓库的 worktree 共享，默认位于 `~/.claude/projects/<project>/memory/`。
- `MEMORY.md` 是索引，首 200 行或 25 KB（取先到者）每次启动加载；每条记忆可拆成独立 topic file，按需读取。
- 对话消息、工具调用和结果保存在 `~/.claude/projects/` 下的 JSONL session 中，用于 resume/fork/rewind，但这层不等于 auto memory。
- context 接近上限时先清理旧工具输出，再必要时摘要对话；根项目 `CLAUDE.md` 在 `/compact` 后重新注入。

#### Claude API / Managed Agents

- Messages API memory tool 是客户端文件工具：Claude 请求 `view/create/replace/insert/delete/rename`，应用自己执行并管理存储；记忆不是 Anthropic 自动替 API 用户建好的数据库。
- Managed Agents 另有 workspace-scoped memory store，作为目录挂载到 session sandbox，支持读写权限、版本轨迹和 API/Console 管理。

### 5. Codex 与 Claude Code 的主要差异

| 维度 | Codex 本地 memory | Claude Code auto memory |
| --- | --- | --- |
| 写入时机 | 符合条件的旧会话在线程空闲后由后台提取与合并 | Claude 在当前 session 中直接读写 memory files |
| 组织范围 | 当前可观察结构是一个 Codex home 下的全局库，再按工作区/任务索引 | 每个 Git 仓库一个 auto-memory 目录，worktree 共享 |
| 启动读取 | 全局高密度摘要 + 按任务需要查详细证据 | `MEMORY.md` 有明确 200 行 / 25 KB 启动上限，topic files 按需读 |
| 人工稳定规则 | `AGENTS.md` | `CLAUDE.md` / `.claude/rules/` |
| 与 context 压缩的关系 | 长期 memory 与当前 context compaction 是不同链路 | auto memory/CLAUDE.md 与 context compaction 分层，根 `CLAUDE.md` 压缩后重注入 |
| 可观察性 | 纯文本文件 + SQLite 任务元数据 + rollout 证据 | 纯文本 Markdown auto memory + JSONL session |

### 6. Codex 记忆提取与计费

- 记忆提取和全局归并需要调用模型，因此会消耗 Token/计算量，并占用 Codex 使用额度。OpenAI 文档明确说明，当 Codex 剩余 rate-limit 百分比低于设定阈值时，后台可以跳过记忆生成，以避免在接近限额时继续消耗 quota。
- 使用 ChatGPT 账号套餐登录 Codex 时，这部分计入套餐的 Codex 共享使用额度/限额，官方未列出独立的“memory 提取费”；不会因为开启 memory 就另生成一笔 API Token 账单。
- 使用 API Key 运行 Codex 时，官方规则是按 Codex 实际使用的 Token 和对应 API 模型价格付费；记忆提取/归并用到的模型 Token 因此会进入 API 计费。
- 已有记忆被注入未来任务时也会占据输入 context；在 API Key 模式下它属于输入 Token，在套餐模式下则反映在 Codex 任务的共享用量中。
- 官方目前没有公开每次记忆提取的固定 Token 数或单独用量明细；具体消耗会受 rollout 长度、是否被跳过、提取模型和归并频率影响。

### 证据边界

- Codex 内部文件的具体实现可能随版本变化；本记录把官方稳定说明与 2026-08-22 本机观察分开。
- Claude 应用正在从 legacy daily summary 迁移到新的 categorized entries；实际账号看到的设置界面决定其所处版本。
- 本次为官方文档与本机结构调研，没有对两个产品执行可控写入/冲突更新实验，不对召回率或冲突处理质量下结论。

### 官方资料

- [OpenAI: Memories](https://learn.chatgpt.com/docs/customization/memories?surface=app)
- [Claude Code: How Claude remembers your project](https://code.claude.com/docs/en/memory)
- [Claude Code: How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)
- [Claude Help Center: Chat search and memory](https://support.claude.com/en/articles/11817273-use-claude-s-chat-search-and-memory-to-build-on-previous-context)
- [Claude Platform: Memory tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)
- [Claude Platform: Managed Agents memory](https://platform.claude.com/docs/en/managed-agents/memory)

## 发散联想

- 两者都在走“小索引常驻 + 详细文件按需读取 + 原会话轨迹另存”的路线，而不是把全部历史永久塞进 context window。
- Codex 更像“会话后的异步 ETL + 跨任务归并”；Claude Code 更像“Agent 在当前工具循环内自己维护项目笔记”。这是结构化解释，不是官方术语。
- 真正要实验的不是“文件在不在”，而是写入选择、错误更新、冲突保留、证据回溯和召回失败。

## 结论状态

- Codex 官方 memory 页面的主要含义：待继续
- Codex 本地文件分层与生成链：待继续
- Claude 应用、Claude Code 与 Claude API memory 的产品边界：待继续
- 两者记忆质量与冲突处理的实测对比：待验证

## 后续动作

- 先由用户用自己的话区分 `session/rollout`、`compaction`、`long-term memory` 和 `AGENTS.md/CLAUDE.md`。
- 若需实验，再设计同一组“稳定偏好 + 临时任务事实 + 后续冲突修正”的对话，对比 Codex 和 Claude Code 的写入、更新、删除和新会话召回。
