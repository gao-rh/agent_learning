---
type: concept
status: draft
tags: [ai-agent, openclaw, memory, context-engineering]
created: 2026-06-13
updated: 2026-06-13
source:
  - 00-inbox/2026-06-13-agent到底是什么原始课堂记录.md
related:
  - 20-concepts/记忆搜索总览.md
  - 20-concepts/关键词检索-FTS倒排索引与BM25.md
  - 20-concepts/OpenClaw是什么.md
  - 20-concepts/Agent执行循环.md
---

# OpenClaw 记忆机制

## 一句话理解

OpenClaw 的记忆不是模型参数里的“真正记住”，而是 Runtime 把历史、文件、摘要、索引和检索结果管理起来，并在需要时注入当前回合上下文。

## 需要理解的问题

| 问题 | 暂定理解 |
| --- | --- |
| 记忆保存在哪里？ | 已确认：默认是 agent workspace 里的 Markdown 文件，核心包括 `MEMORY.md`、`memory/YYYY-MM-DD.md`，可选 `DREAMS.md`；搜索索引存在 SQLite 库里。 |
| 记忆什么时候写入？ | 用户假设：重要信息需要保存或用户显式要求时写入；已确认：Dreaming 的 deep 阶段、`memory promote --apply`、compaction 前的 memory flush 也可能写入或促进写入。 |
| 记忆怎么搜索？ | 已确认：默认 builtin backend 会把 memory 文件切块，关键词走 SQLite FTS5/BM25，语义走 embedding/vector search，通常再做 hybrid merge。 |
| 记忆怎么进入上下文？ | Runtime 检索相关记忆后，把摘要或原文片段注入当前上下文包。 |
| 记忆和上下文的区别是什么？ | 记忆是可被检索的外部存储；上下文是本轮模型实际看到的信息。 |
| 记忆如何隔离？ | 需要区分 agent、profile、workspace、channel、session、user。 |

## 文件层：长期记忆与短期记忆

| 文件/目录 | 作用 | 是否默认进入上下文 |
| --- | --- | --- |
| `MEMORY.md` | 长期记忆。保存耐久事实、偏好、长期决策、稳定总结。 | 主私聊 session 启动时会加载，但可能受 bootstrap 预算截断。 |
| `memory/YYYY-MM-DD.md` | 每日工作层。保存详细日志、观察、临时上下文、还没提炼的内容。 | 普通回合不自动全量注入，主要通过 `memory_search` / `memory_get` 按需读取；今天和昨天的 notes 在部分启动/重置路径可被加载。 |
| `DREAMS.md` | Dreaming 的人类可读回顾、REM/Deep 等阶段输出。 | 不是普通长期记忆主体；更像复盘界面。 |
| SQLite index | 检索索引，不是给人直接维护的记忆正文。 | 不直接注入；只返回搜索命中的片段。 |

我的理解是：`MEMORY.md` 不是“所有记忆”，而是“会被优先带入上下文的精炼长期记忆”。详细材料更适合放在 `memory/*.md`，让搜索工具按需找。

## 关键词搜索：不是 grep，而是 FTS5/BM25

| 问题 | 结论 |
| --- | --- |
| 是不是 Linux `grep`？ | 基于当前安装包和文档，默认 builtin memory search 不是 shell 调用 `grep`。 |
| 用什么做关键词搜索？ | SQLite FTS5 full-text index，排序使用 BM25。 |
| 中文怎么办？ | 默认 tokenizer 是 `unicode61`，配置可改 `store.fts.tokenizer = "trigram"` 以改善 CJK。短 CJK 查询还会补 `LIKE` 子串匹配。 |
| FTS 失败怎么办？ | 代码里有 fallback：FTS5 `MATCH` 失败时会退到 `LIKE`；没有 embedding provider 时也会用 lexical ranking 排序。 |

核心差别：索引是在检索之前提前建立的。建索引阶段会读完整 memory 文件、切 chunk、分词，并记录“token -> chunk_id”的倒排索引；查询阶段不是重新读所有 chunk，而是用查询 token 直接查这张索引表，再取命中的 chunk 正文。

这可以理解为一次预处理：

```text
建索引阶段：读全文 -> 切 chunk -> 分词 -> 记录 token 出现在哪些 chunk
查询阶段：输入 token -> 查倒排索引 -> 得到候选 chunk -> 排序 -> 返回片段
```

具体路径：

| 层级 | 本机路径/配置 | 说明 |
| --- | --- | --- |
| 文档 | `/opt/homebrew/lib/node_modules/openclaw/docs/concepts/memory-builtin.md` | 明确写到 keyword search via FTS5/BM25。 |
| 配置 | `agents.defaults.memorySearch.store.fts.tokenizer` | 可配置 `unicode61` / `trigram`。 |
| Schema | `/opt/homebrew/lib/node_modules/openclaw/dist/engine-storage-CqisZTAP.js` | 创建 `chunks` 表和 `chunks_fts` FTS5 虚拟表。 |
| 写入索引 | `/opt/homebrew/lib/node_modules/openclaw/dist/manager-tSoEFIOd.js` | `writeChunks(...)` 同时写 `chunks` 与 `chunks_fts`。 |
| 搜索查询 | `/opt/homebrew/lib/node_modules/openclaw/dist/manager-tSoEFIOd.js` | `searchKeyword(...)` 使用 `chunks_fts MATCH ?` 和 `bm25(chunks_fts)`。 |

关键词搜索流程可以理解为：

```text
用户查询
-> 提取 token / 构造 FTS query
-> 查询 chunks_fts
-> bm25 计算关键词相关性
-> 返回 chunk 的 path、line range、snippet、score
```

## 语义搜索：embedding + vector search

| 问题 | 结论 |
| --- | --- |
| 是否向量化？ | 是。OpenClaw 会把记忆 chunk 做 embedding，并把向量存入 SQLite。 |
| 用什么 embedding？ | 由 `agents.defaults.memorySearch.provider` 决定，可用 `openai`、`gemini`、`github-copilot`、`voyage`、`mistral`、`deepinfra`、`bedrock`、`ollama`、`local` 等。 |
| 默认如何存向量？ | `chunks.embedding` 存 JSON 字符串；如果 sqlite-vec 可用，还会写入 `chunks_vec` 虚拟表。 |
| 如何搜索向量？ | 查询时先对 query 做 `embedQuery`，再用 sqlite-vec 的 `vec_distance_cosine(...)` 做 KNN；如果 sqlite-vec 不可用，则在进程内遍历 `chunks.embedding` 用 cosine similarity 算相似度。 |
| 向量库在哪？ | 默认 SQLite 文件：`~/.openclaw/memory/{agentId}.sqlite`。 |

具体路径：

| 层级 | 本机路径/配置 | 说明 |
| --- | --- | --- |
| 文档 | `/opt/homebrew/lib/node_modules/openclaw/docs/concepts/memory-search.md` | 描述 vector search + BM25 search 并行后 merge。 |
| 文档 | `/opt/homebrew/lib/node_modules/openclaw/docs/reference/memory-config.md` | provider、batch、embedding cache、sqlite-vec、store path 等配置。 |
| Provider 解析 | `/opt/homebrew/lib/node_modules/openclaw/dist/memory-search-Dn2Ao10S.js` | 解析 `provider`、`model`、`queryInputType`、`documentInputType`、hybrid 权重等。 |
| Embedding 实现 | `/opt/homebrew/lib/node_modules/openclaw/dist/memory-core-host-engine-embeddings-B41PUaLw.js` | local embedding、remote `/embeddings` 请求、batch embedding 等。 |
| 向量表 | `/opt/homebrew/lib/node_modules/openclaw/dist/manager-tSoEFIOd.js` | 创建 `chunks_vec`：`CREATE VIRTUAL TABLE ... USING vec0(... embedding FLOAT[dims])`。 |
| 向量查询 | `/opt/homebrew/lib/node_modules/openclaw/dist/manager-tSoEFIOd.js` | `searchVector(...)` 使用 `vec_distance_cosine`；fallback 用 `cosineSimilarity(...)`。 |

语义搜索流程可以理解为：

```text
memory 文件
-> listMemoryFiles 找到 MEMORY.md / memory/*.md / extraPaths
-> chunkMarkdown 切成 chunk
-> embedBatch / embedBatchInputs 生成 chunk 向量
-> 写入 chunks.embedding；若 sqlite-vec 可用，写入 chunks_vec

用户查询
-> embedQuery 生成 query 向量
-> sqlite-vec KNN / fallback cosine similarity
-> 返回语义相近 chunk
```

## Hybrid Search：关键词和语义合并

默认不是二选一，而是混合检索：

```text
query
├─ 关键词路径：FTS5 + BM25
└─ 语义路径：embedding + vector search
        ↓
weighted merge
        ↓
可选 temporal decay / MMR
        ↓
top results
```

默认配置中，hybrid 权重大致是：

| 配置 | 默认值 | 含义 |
| --- | --- | --- |
| `query.hybrid.enabled` | `true` | 开启关键词 + 向量混合搜索。 |
| `query.hybrid.vectorWeight` | `0.7` | 语义相似度权重。 |
| `query.hybrid.textWeight` | `0.3` | 关键词匹配权重。 |
| `query.hybrid.candidateMultiplier` | `4` | 候选池放大倍数。 |
| `query.hybrid.mmr.enabled` | `false` | 是否做多样性重排，减少重复片段。 |
| `query.hybrid.temporalDecay.enabled` | `false` | 是否让旧 memory 逐渐降权；`MEMORY.md` 等 evergreen 文件不衰减。 |

## 当前本机的一个异常点

我在本机执行 `openclaw memory --help`、`openclaw memory search --help` 时，CLI 打印的是全局 help，而不是 docs 里描述的 memory 子命令 help。这说明至少当前 shell 里可用的 CLI 入口和 docs/插件暴露之间可能有版本、插件加载或命令注册差异。

但这不影响对默认 builtin 实现路径的判断：安装包里的 docs 和 dist 代码都能确认 `memory-core` 的索引/检索机制。

## 后续重点

- OpenClaw 的 `memory` config 控制哪些内容。
- `hooks.internal.session-memory` 如何工作。
- session history、长期 memory、workspace 文件三者如何区分。
- 搜索记忆时如何决定 scope。
- 记忆注入是否会被截断、压缩或排序。
- 如何避免错误记忆、过期记忆、跨场景污染。
- 为什么当前 CLI help 没有暴露 docs 中的 `openclaw memory` 子命令，需要以后结合实际运行状态再确认。

## 常见误区

| 误区 | 更准确的理解 |
| --- | --- |
| Agent 记住了 = 模型权重变了 | 通常不是，而是外部记忆被检索并注入上下文。 |
| 记忆越多越好 | 记忆太多会带来噪声、过期信息和隐私风险。 |
| 所有历史都应该进上下文 | 应该只注入和当前任务相关的内容。 |
| 搜索到的记忆一定正确 | 仍需要时间、来源和置信度判断。 |

## 自测问题

1. 记忆和当前上下文有什么区别？
2. 为什么长期记忆需要 scope 隔离？
3. 什么样的信息应该写入长期记忆，什么只应该留在 session history？
4. 如果记忆检索错了，会怎样影响 Agent 回答？
