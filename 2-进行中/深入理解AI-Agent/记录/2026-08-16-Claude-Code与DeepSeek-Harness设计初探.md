# 2026-08-16 Claude Code 与 DeepSeek Harness 设计初探

## 原始问题

> 我有一个重要 todo，就是学习一下 Claude Code 和 DeepSeek Harness 两个 Harness 的设计。可以先简单调研，然后给一个简单介绍。

## 用户理解

- 用户已把“学习两个 Harness 的设计”确认为重要待办。
- 用户尚未给出对两者架构的具体理解；本记录不预设已经理解。

## Codex 反馈

### 先给结论

Claude Code 和 DeepSeek Harness 都在做同一件事：把“只会生成文字的模型”变成“能在真实环境中完成任务的 Agent”。两者的设计重心不同：

- **Claude Code** 更像一个成熟、强约定的 coding-agent 产品：先把默认的编码循环、工具、权限、上下文和人机交互做好，再通过 `CLAUDE.md`、Skills、Hooks、MCP、Subagents 等表面扩展。
- **DeepSeek Harness** 更像一个开源的 Agent Harness 操作系统/元框架：不把 Agent Loop 当成不可替换的核心，而是连模型适配器、工具注册表、会话日志和 Agent Loop 自身都做成插件。

### 共同骨架

```text
用户任务
  → Harness 组装规则、历史、工具和当前状态
  → 模型决定回答或调用工具
  → Harness 审批并执行工具
  → 结果写回轨迹
  → 模型继续决策
  → 验证、停止或请求人介入
```

关键分工仍是：模型主要负责“下一步想做什么”，Harness 负责“给它看什么、允许做什么、如何真正执行、如何保存和恢复”。

### Claude Code：产品化的动态编码循环

1. **Agent Loop 是认知主干**
   
   官方将其概括为“收集上下文 → 行动 → 验证”的循环。不是外部程序写死每个步骤，而是模型根据每次工具结果动态决定下一步；用户可以在中途打断或追加纠偏。

2. **开箱即用的编码工具带**
   
   内置文件读写、搜索、Shell/Git/测试执行、Web 和代码智能等能力，工具结果会回到循环作为新观测。这是它能从“建议怎么改”跨到“实际修改并跑测试”的关键。

3. **分层的上下文工程**
   
   `CLAUDE.md` 和 auto memory 提供持久规则/项目知识；Skills 的完整内容按需加载；MCP 工具定义可延迟发现；上下文接近上限时先清理旧工具输出，必要时再压缩对话。Subagent 还可以把独立工作隔离到另一个上下文窗口。

4. **权限、检查点和人在环**
   
   不同 permission mode 决定文件修改和命令是自动执行还是先询问；本地文件改动可通过 checkpoint 撤销，对外部系统的副作用无法靠 checkpoint 恢复，所以仍需执行前审批。

5. **将扩展分成不同机制**
   
   项目规则用 `CLAUDE.md`，可复用流程用 Skills，外部系统接入用 MCP，确定性生命周期动作用 Hooks，上下文隔离/并行分工用 Subagents 或 Workflows。这是“用稳定核心支持多种工作流”的路线。

### DeepSeek Harness：一切都是插件

1. **Cordis 插件树是真正的主干**
   
   插件向共享 `Context` 贡献 Service、类型化事件和可逆副作用。依赖通过服务接口声明，而不是直接导入具体实现；插件卸载时，它注册的工具、监听器和服务也随之撤销。因此连 Agent Loop 都只是可替换默认实现，不是特权核心。

2. **Profile + Bundle + Patch 负责组装产品**
   
   运行时从空树开始，按序叠加 base bundle、Web 或 headless bundle、用户 patch 和命令行 overlay。模型适配器、工具、持久化、沙箱、审批、UI 都是可组合层。

3. **事件溯源的会话与执行流**
   
   一个 step 是“一次模型请求 + 它调用的工具”，一个 turn 可含多个 step。`turn/*`、`step/*`、用户/助手消息、工具调用/结果都写成持久 SessionEvent。它设立了很强的不变式：**模型可见的内容必须已记录，并能从日志重建**。因此恢复、fork、回放、UI 和遥测可从同一事件流派生。

4. **Capability Seam 将接口、实现与模型工具拆开**
   
   一项能力被拆成 Service Definition、Service Provider 和 Consumer。例如替换文件系统/进程的 Provider，可以把 Bash、PTY 和 LSP 一起迁移到远程沙箱，不需要为每个上层工具各写一套。

5. **Agent Preset 产生不同 Harness 形态**
   
   官方当前内置四种组合：`standard` 是完整编码 Agent；`code`/PTC 让模型生成一段 TypeScript，在代码里组合多步工具调用；`minimal` 只留持久 Bash 与 `str_replace_editor`；`cordis`/创造模式用于检查运行时、试验插件和编写自定义 preset。

### 对比抓手

| 维度 | Claude Code | DeepSeek Harness |
| --- | --- | --- |
| 首要目标 | 默认就好用的编码 Agent 产品 | 可以重组、替换和研究的 Agent Harness 平台 |
| 核心抽象 | 收集上下文—行动—验证的 Agent Loop | Cordis Context 上的插件、Service、Event 与可逆 Effect |
| 扩展路线 | 在稳定的 coding harness 上加 Skills、Hooks、MCP、Subagents | 从组成 harness 的底层部件开始全面插件化 |
| 状态与回放 | 公开文档强调 session 继续/fork、context 压缩和 checkpoint | append-only SessionEvent 是模型历史、回放、fork、UI 和遥测的统一事实源 |
| 工具组合 | 模型通常逐步调用内置/MCP 工具 | 除原生调用外，PTC 模式可用一段 TypeScript 编排多步工具调用 |
| 当前成熟度 | 产品化成熟，但本轮主要能从公开行为文档学习 | 开源且内部架构可直接阅读，但官方明确标注 developer preview，可能有破坏性变更 |

### 这次调研的证据边界

- Claude Code 部分主要依据官方公开文档，因此是“可观察行为与公开扩展面”层级的设计概括，不是对其全部内部源码的还原。
- DeepSeek Harness 部分核对了官方仓库的架构文档、Cordis 入门和内置 Agent Preset；当前仓库版本为 `47f943859bef60e4160492346772ded9b24f765a`（当地时间 2026-08-13 的提交）。
- 本次没有实际运行两个系统，因此不对性能、稳定性或任务成功率做结论。

### 官方资料

- [Claude Code: How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)
- [Claude Code: Extend Claude Code](https://code.claude.com/docs/en/features-overview)
- [Claude Code: A harness for every task](https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code)
- [DeepSeek Harness 官方仓库](https://github.com/deepseek-ai/deepseek-harness)
- [DeepSeek Harness Architecture](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md)
- [Cordis Primer](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/cordis-primer.md)

## 发散联想

- Claude Code 适合研究“怎样做一个默认体验完整、能安全进入真实仓库的 Agent 产品”。
- DeepSeek Harness 适合研究“怎样把 Agent Runtime 拆成可替换的能力，并使其可回放、可定制、可试验”。
- PTC/Code Mode 是一个值得单独学的对比点：与“模型每次只调一个工具”相比，它把循环、分支、聚合和中间数据放进一次沙箱代码执行，可能节省模型往返和上下文，但也带来代码执行隔离与调试的新问题。

## 结论状态

- 问题：待继续
- 当前只完成轻量调研和学习地图，不等于已理解两个 Harness 的实现。

## 后续动作

- **已确认**：将“学习 Claude Code 与 DeepSeek Harness 的 Harness 设计”纳入高优先级学习待办。
- **Codex 建议，尚未确认**：后续用同一张表深读两者的 `Agent Loop / Context / Tools / Permission / Extension`，避免变成两份各说各话的功能清单。
- **Codex 建议，尚未确认**：深读时只做一个最小实验：用同一个仓库小任务观察两者的轨迹、工具展示、审批与验证行为；实验前由用户先预测差异。
