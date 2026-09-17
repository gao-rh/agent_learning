# 2026-08-25 Dash 数据与 Agent 架构

## 原始问题

- Ashpreet Bedi 的 Dash 是什么？
- Dash 有哪些值得学习的内容，是否已被广泛应用？
- 介绍 Dash 的数据架构和 Agent 架构。

## 用户理解

- 待用户用自己的话复述 Dash 中一次数据问答的完整链路。
- 待用户区分业务数据、Knowledge、Learnings 和会话/用户记忆。

## Codex 反馈

- Dash 是基于 Agno 的自学习 Data Agent 参考实现，核心价值在上下文、权限、知识写回和评测闭环，不是“三个 Agent”这个数量。
- 数据层区分 `public` 业务数据和 `dash` Agent 管理的派生资产；正式 Knowledge、自动 Learnings、session/history 和用户记忆另有不同的语义与可信度。
- Agent 层由 Leader 路由和综合，Analyst 负责只读 SQL 与分析，Engineer 负责在 `dash` schema 生产可复用视图和汇总表。
- 当前源码中 Analyst 使用 PostgreSQL 只读事务配置；Engineer 对 `public` 的写防护主要是 SQLAlchemy 正则拦截，不应误认为数据库角色级硬隔离。
- 记录依据为 Dash 官方仓库 `main` 分支提交 `6d86fca8e85b17349238389f5fad92d15e8f633f`，2026-08-25 核对远端无差异。

## 发散联想

- Dash 的 Knowledge / Learnings 区分可用来检查 Data Agent 中“已确认指标口径”和“Agent 候选经验”是否被错误混合。
- 重复分析从临时 SQL 晋升为视图/汇总表，展示了“记住答案”与“沉淀可复用数据资产”的差异。

## 结论状态

- Dash 数据架构与 Agent 架构：待继续

## 后续动作

- 由用户选一个具体问题，用自己的话说明它在 Leader、Analyst/Engineer、Knowledge/Learnings 和 PostgreSQL 之间如何流转。
- 待复述后，再对照用户的智能经营分析 Agent，只记录用户确认的映射关系。
