---
type: concept
status: draft
tags: [ai-agent, openclaw, agent-runtime, config]
created: 2026-06-13
updated: 2026-06-14
source:
  - 10-sources/courses/李宏毅机器学习2026/2026-06-13-Agent到底是什么.md
  - 00-inbox/2026-06-13-agent到底是什么原始课堂记录.md
  - 00-inbox/2026-06-13-openclaw中介层讨论日志.md
  - local: ~/.openclaw/openclaw.json
  - local: openclaw config schema
related:
  - 20-concepts/Agent中介层.md
  - 20-concepts/Agent执行循环.md
  - 20-concepts/OpenClaw长期运行机制.md
---

# OpenClaw 是什么

## 一句话理解

OpenClaw 是一个把聊天渠道、模型、记忆、工具、任务、权限和本地电脑能力组织起来的 Agent Runtime / 工程脚手架。

## 当前理解

不要把 OpenClaw 直接等同于“大模型本身”。更准确地说：

```text
人 / 通讯软件 -> OpenClaw Runtime -> 语言模型 / 工具 / 电脑 / 外部服务
```

语言模型提供基础智能；OpenClaw 负责把这些智能接入真实工作流。

从 Agent 定位看，OpenClaw 更像一个 gateway-first personal agent runtime：它强调多聊天渠道、长期在线、记忆、自动化和本机能力，而不是只围绕单个代码仓库工作。

## Config 的主要配置面

以本机 `OpenClaw 2026.5.12` 和 `~/.openclaw/openclaw.json` / config schema 为参考，OpenClaw 的 config 通常不是只配一个模型 key，而是配置整个 Agent 运行时。

| 配置面 | 作用 | 典型内容 |
| --- | --- | --- |
| `models` | 配置可用模型和 provider | provider、base URL、API key、模型列表、上下文窗口、成本、输入类型 |
| `agents` | 配置 agent 默认行为和工作区 | 默认模型、workspace、compaction、timeout、并发、subagents |
| `tools` | 配置全局工具能力和策略 | 工具 profile、web search、exec/media/messaging 等能力开关 |
| `channels` | 配置聊天渠道 | Feishu、QQBot、Telegram、Discord、Web UI 等 channel 的 token、策略、连接方式 |
| `gateway` | 配置 Gateway 服务 | 端口、绑定地址、auth、local/remote 模式、Tailscale/remote token |
| `skills` | 配置可安装/启用的技能 | skill entries、enabled、安装方式、各 skill 私有配置 |
| `plugins` | 配置插件系统 | plugin entries、enabled、插件参数，例如 moonshot、qqbot、feishu |
| `memory` | 配置记忆后端 | 记忆存储、检索、索引相关设置 |
| `mcp` | 配置 MCP 工具服务器 | MCP server 定义、外部工具桥接 |
| `messages` | 配置消息展示和队列行为 | 群聊回复可见性、ack、debounce、状态反应 |
| `commands` | 配置命令触发和权限 | chat command、owner gating、native command、restart |
| `approvals` | 配置审批流 | 执行命令、插件、外部动作是否需要转发审批 |
| `cron` | 配置定时任务 | job 并发、保留策略、delivery fallback |
| `hooks` | 配置内部/外部钩子 | boot、session memory、command logger、webhook automation |
| `session` | 配置会话隔离和历史策略 | DM scope、reset、delivery、session maintenance |
| `secrets` / `auth` | 配置凭据和认证 | SecretRef、provider credentials、profile failover |
| `logging` / `diagnostics` | 配置日志和诊断 | log level、redaction、trace、telemetry、debug cache |
| `browser` / `web` / `ui` | 配置浏览器、Web 通道和界面 | CDP、截图、heartbeat、reconnect、UI identity |
| `nodeHost` / `nodes` | 配置节点能力 | 本机能力暴露、多节点配对、远程节点调用 |
| `update` / `wizard` / `meta` | 配置更新和系统状态 | update channel、setup wizard state、版本写入记录 |

## 怎么理解这些配置

这些配置大致回答 8 个问题：

| 问题 | 对应配置 |
| --- | --- |
| 接哪个模型？ | `models`、`agents.defaults.model` |
| 用哪个工作区和上下文策略？ | `agents.defaults.workspace`、`compaction`、`session` |
| 能用哪些工具？ | `tools`、`skills`、`plugins`、`mcp` |
| 从哪些渠道和人交互？ | `channels`、`messages`、`web`、`ui` |
| Gateway 怎么运行？ | `gateway`、`nodeHost`、`nodes` |
| 如何记忆和检索？ | `memory`、`hooks.internal.session-memory` |
| 哪些动作需要权限？ | `approvals`、`commands`、`tools`、`gateway.auth` |
| 怎么自动化和长期运行？ | `cron`、`commitments`、`hooks` |

## 常用且重要的配置

刚开始不需要理解所有字段，优先看这些高频配置面。

### 1. 模型与 Agent 默认行为

| 配置 | 常用原因 | 典型调整 |
| --- | --- | --- |
| `models` | 决定 OpenClaw 能调用哪些模型 provider | 增加 provider、设置 base URL、模型 ID、上下文窗口 |
| `agents.defaults.model` | 决定默认 agent 用哪个模型 | 切换默认主模型，例如从便宜模型换到更强模型 |
| `agents.defaults.workspace` | 决定 agent 默认在哪个目录工作 | 指向自己的学习库、项目库或隔离 workspace |
| `agents.defaults.compaction` | 决定长对话怎么压缩上下文 | 学习/长期任务通常需要保守压缩，避免丢关键背景 |

这类配置最影响“Agent 聪不聪明、看不看得到你的项目、长对话会不会丢上下文”。

### 2. 渠道与消息通道

| 配置 | 常用原因 | 典型调整 |
| --- | --- | --- |
| `channels` | 决定从哪里和 Agent 对话 | QQBot、Feishu、Telegram、Discord、Web UI |
| `messages` | 决定消息如何展示和确认 | 群聊回复可见性、状态提示、消息队列体验 |
| `session` | 决定不同聊天对象/频道的会话隔离 | 私聊、群聊、不同 channel 是否共享上下文 |

这类配置最影响“从哪里唤起 Agent”和“不同渠道会不会串话”。

### 3. 工具、技能与插件

| 配置 | 常用原因 | 典型调整 |
| --- | --- | --- |
| `tools` | 控制全局工具能力 | 是否开启 web search、exec、media、messaging 等能力 |
| `skills` | 给 Agent 增加可复用能力包 | 启用 coding、notion、voice、tmux 等技能 |
| `plugins` | 接入更重的扩展能力 | QQBot、Feishu、Moonshot 等插件 |
| `mcp` | 接标准化外部工具服务器 | GitHub、Google Drive、数据库、自定义 MCP server |

这类配置最影响“Agent 能不能做事”。原则是：只开当前确实需要的工具，避免无意义扩大权限面。

### 4. Gateway 与长期运行

| 配置 | 常用原因 | 典型调整 |
| --- | --- | --- |
| `gateway` | 控制 OpenClaw 后台服务 | 端口、bind、auth、local/remote、Tailscale |
| `heartbeat` | 周期性唤醒主 session | 检查通知、follow-up、无事静默 |
| `cron` | 定时运行任务 | 每日总结、定时提醒、周期检查 |
| `hooks` | 在特定事件上自动触发逻辑 | 启动加载、session memory、command logger |
| `commitments` | 自动识别和跟进承诺 | 让 Agent 记得后续提醒或 check-in |

这类配置最影响“OpenClaw 是否像长期在线的个人 Agent”，而不是一次性 CLI。

### 5. 安全、权限与凭据

| 配置 | 常用原因 | 典型调整 |
| --- | --- | --- |
| `secrets` / `auth` | 管理 API key、token、凭据来源 | 用 SecretRef、环境变量、文件 provider 管理凭据 |
| `approvals` | 高风险动作前请求确认 | 执行命令、发消息、改外部系统前转人工批准 |
| `commands` | 控制聊天命令和 owner 权限 | 限制谁能触发敏感命令 |
| `tools` policy | 限制工具能力边界 | 禁用高风险工具，或只允许只读工具 |

这类配置最影响“会不会误操作、误发消息、泄露凭据”。如果不确定，优先保守。

### 6. 调试与维护

| 配置 | 常用原因 | 典型调整 |
| --- | --- | --- |
| `logging` | 排查 Agent 为什么没响应或工具失败 | 临时调高 log level，注意敏感信息 redaction |
| `diagnostics` | 深度排查 Gateway、插件、缓存问题 | 只在调试时开启 |
| `update` | 控制升级通道 | 稳定使用保守 channel，测试时再用新版本 |
| `meta` / `wizard` | 记录配置被哪个版本/向导改过 | 通常不手改，用来排错 |

这类配置平时不一定常改，但排错时很重要。

新手优先级可以这样排：

```text
1. models / agents.defaults.model
2. agents.defaults.workspace
3. channels / messages / session
4. tools / skills / plugins / mcp
5. gateway / cron / hooks
6. secrets / auth / approvals / commands
7. logging / diagnostics
```

## 和 System Prompt 的关系

Config 不是 System Prompt，但它会影响 System Prompt 和当前回合上下文包。

例如：

- `models` 决定调用哪个模型。
- `agents` 决定默认工作区、超时、并发和压缩策略。
- `tools` / `skills` / `plugins` 决定哪些工具会暴露给模型。
- `memory` / `hooks` 决定哪些历史信息可能被检索并注入上下文。
- `channels` / `messages` 决定用户从哪里进入、回复怎么展示。
- `approvals` / `commands` / `gateway` 决定哪些动作可以执行、是否需要确认。

所以可以把 OpenClaw config 理解成：**Runtime 如何拼装上下文、开放工具、接入入口、执行动作、保存状态的一组开关和参数。**

## 常见误区

| 误区 | 更准确的理解 |
| --- | --- |
| OpenClaw config 只是模型 API key | 它配置的是完整 Agent Runtime，包括模型、渠道、工具、记忆、权限、自动化。 |
| 配了工具，模型就能直接操作电脑 | Config 只是声明能力；真正执行仍要经过 Runtime、权限和工具服务器。 |
| System Prompt 决定一切 | System Prompt 只是上下文的一部分；很多能力由 Runtime 和 config 保证。 |
| 插件越多越好 | 插件越多，权限和安全边界越复杂，需要最小化启用。 |

## 我的判断

理解 OpenClaw 的关键不是看它“聪不聪明”，而是看它如何把模型智能工程化：渠道、上下文、工具、记忆、权限、任务和自动化是否能稳定协同。

如果把 Agent 理解成“模型 + Runtime + 工具 + 记忆 + 权限 + 触发机制”，OpenClaw 的重点就在 Runtime 这一层：它让模型能够从不同渠道被唤起、带着上下文调用工具、保存长期状态，并通过 heartbeat/cron/hooks 持续运行。

## 自测问题

1. OpenClaw config 和 System Prompt 有什么区别？
2. 如果一个 Agent 能从 QQ 收消息、调用模型、读文件、发回回复，至少涉及哪些配置面？
3. 为什么说工具是否可用不只取决于模型，还取决于 Runtime 和 config？
4. 为什么插件和 channel 越多，权限管理越重要？
