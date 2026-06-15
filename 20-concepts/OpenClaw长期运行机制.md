---
type: concept
status: stable-draft
tags: [openclaw, ai-agent, automation, heartbeat, hooks, cron]
created: 2026-06-14
updated: 2026-06-14
source:
  - 10-sources/courses/李宏毅机器学习2026/2026-06-13-Agent到底是什么.md
  - 00-inbox/2026-06-13-agent到底是什么原始课堂记录.md
  - https://docs.openclaw.ai/automation
  - https://docs.openclaw.ai/gateway/heartbeat
  - https://docs.openclaw.ai/automation/hooks
related:
  - 20-concepts/OpenClaw是什么.md
  - 20-concepts/Agent执行循环.md
---

# OpenClaw 长期运行机制

## 一句话理解

OpenClaw 不只是等用户发消息的聊天工具；它可以通过 Heartbeat、Cron、Hooks、Webhooks 等机制被时间或事件触发，成为长期在线的 Agent Runtime。

## 四类触发

| 触发方式 | 含义 | 适合场景 |
| --- | --- | --- |
| 用户消息 | 用户主动发起任务。 | 对话、问答、写代码、整理笔记。 |
| Heartbeat | 周期性唤醒主 session。 | 检查通知、follow-up、无事静默。 |
| Cron | 精确定时任务。 | 日报、提醒、周期任务。 |
| Hooks | 内部事件触发。 | `/new`、`/reset`、compaction、gateway startup。 |
| Webhooks | 外部 HTTP 请求触发。 | 第三方系统唤醒 Agent。 |

## Heartbeat

Heartbeat 不是普通网络 ping。OpenClaw 里它更像一次周期性的主会话 agent turn：

```text
定时器触发
-> Runtime 拼装 heartbeat 上下文
-> 模型检查是否有需要提醒或处理的事
-> 无事：HEARTBEAT_OK 静默
-> 有事：通知、检查、执行或排队
```

它适合近似周期检查，不适合必须准点执行的任务。

## Cron

Cron 适合精确时间和独立后台任务，例如每天 9 点发日报、20 分钟后提醒、每周跑一次分析。它更像调度器，会创建可审计的任务记录。

## Hooks

Hooks 是事件驱动扩展点。它们不是按时间触发，而是当 Gateway、session、message 或 agent/tool 生命周期事件发生时触发。

OpenClaw 至少要区分：

| 类型 | 说明 |
| --- | --- |
| Internal hooks | Gateway 内部事件脚本，例如 `/new`、`/reset`、compaction、gateway startup。 |
| Plugin hooks | 插件 SDK 里的 typed hooks，可更深地介入 prompt、tool、message、finalization。 |
| Webhooks | 外部 HTTP 入口，名字像 hook，但属于外部触发。 |

## 常见误区

| 误区 | 更准确的理解 |
| --- | --- |
| Heartbeat = 一直让模型思考 | Heartbeat 是低频、可静默的周期性唤醒。 |
| Cron 和 Heartbeat 一样 | Cron 准点执行；Heartbeat 近似周期检查。 |
| Hooks 和 Webhooks 是一回事 | Hooks 是内部事件机制；Webhooks 是外部 HTTP 入口。 |
| 自动化越多越好 | 自动化越多，越需要权限、日志和失败处理。 |

## 自测问题

1. Heartbeat 和 cron 最大区别是什么？
2. 为什么 hooks 是事件驱动，而不是时间驱动？
3. 哪些任务应该用 Heartbeat，哪些应该用 Cron？
