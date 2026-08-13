---
type: code-lab-report
status: completed
tags: [agent, kv-cache, kimi, context-engineering]
created: 2026-08-08
updated: 2026-08-08
---

# KV Cache 六模式中文对照实验报告

## 先看结论入口

这是一轮使用同一模型、同一中文任务、同一工具根目录的六模式连续对照。下表是总览；后半部分可以逐轮展开查看真正发送给模型的完整消息、模型回复和工具结果。

> 指标边界：教材代码使用非流式 `chat.completions.create`。因此这里记录的 `响应耗时` 是整次请求返回所花时间，不是真正的 TTFT。`cached_tokens`、Prompt Tokens 和 Completion Tokens 则来自 Kimi 的 usage。

## 实验协议

- 模型：`kimi-k2.6`
- 开始：`2026-08-08T19:23:41+08:00`
- 结束：`2026-08-08T19:29:27+08:00`
- 模式顺序：`correct -> dynamic_system -> shuffled_tools -> dynamic_profile -> sliding_window -> text_format`
- 随机种子：`20260808`
- 最大轮数：`8`
- 教材 `agent.py` SHA-256：`9f33f25affbc51d06e419e3bc9f56431ddeb3a3576692588559cc914635cf84c`
- 中文适配：共享 system、工具说明、动态资料、纯文本历史标签和用户任务翻译为中文；六种上下文管理机制不变。
- 凭据：只从本地环境读取，未写入任何实验产物。隐藏推理 `reasoning_content` 也未保存。

### 统一中文任务

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

### 六个自变量

| 顺序 | 模式 | 中文名 | 每轮改变什么 |
| ---: | --- | --- | --- |
| 1 | `correct` | 稳定上下文 | 消息列表只创建一次，之后只在末尾追加。 |
| 2 | `dynamic_system` | 动态系统提示 | 每轮在系统提示末尾追加不同时间戳。 |
| 3 | `shuffled_tools` | 工具顺序变化 | 每轮随机改变三个工具定义的顺序。 |
| 4 | `dynamic_profile` | 动态用户资料 | 每轮在靠前位置加入不断变化的剩余额度。 |
| 5 | `sliding_window` | 滑动窗口 | 每轮只保留最近约六条历史消息。 |
| 6 | `text_format` | 历史转纯文本 | 每轮把结构化历史重新拼成一条纯文本消息。 |

## 六模式关键指标总表

| 模式 | 成功 | API 轮数 | 工具调用 | Prompt | Cached | 未缓存 | Cache% | Completion | 平均响应耗时 | 总墙钟时间 | 中文最终回答 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `correct` | 是 | 4 | 3 | 6,641 | 2,816 | 3,825 | 42.4% | 1,479 | 9.117s | 36.473s | 是 |
| `dynamic_system` | 是 | 4 | 3 | 7,026 | 1,024 | 6,002 | 14.6% | 2,139 | 15.318s | 61.280s | 是 |
| `shuffled_tools` | 是 | 4 | 3 | 6,950 | 256 | 6,694 | 3.7% | 2,463 | 19.564s | 78.267s | 是 |
| `dynamic_profile` | 是 | 4 | 3 | 6,706 | 1,024 | 5,682 | 15.3% | 1,678 | 13.756s | 55.033s | 是 |
| `sliding_window` | 是 | 4 | 3 | 6,755 | 2,560 | 4,195 | 37.9% | 1,936 | 15.736s | 62.953s | 是 |
| `text_format` | 是 | 4 | 3 | 6,497 | 1,115 | 5,382 | 17.2% | 1,462 | 13.058s | 52.245s | 是 |

## `correct`：新增 Prompt 与旧前缀复用

只有 `correct` 每轮都在完全相同的消息列表末尾追加，因此可以用 `本轮 cached_tokens ÷ 上轮 prompt_tokens` 近似回答“上一轮不动的前缀有没有基本命中”。它仍不是服务商提供的精确前缀覆盖字段，会受到缓存块粒度和服务端已有缓存影响。

| 轮次 | Prompt | 比上轮新增 | Cached | 未缓存 | Cache% | Cached ÷ 上轮 Prompt | 响应耗时 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 603 | — | 256 | 347 | 42.5% | — | 3.176s |
| 2 | 926 | +323 | 512 | 414 | 55.3% | 84.9% | 2.061s |
| 3 | 1,823 | +897 | 512 | 1,311 | 28.1% | 55.3% | 3.394s |
| 4 | 3,289 | +1,466 | 1,536 | 1,753 | 46.7% | 84.3% | 27.836s |

## 如何读这些数

| 指标 | 回答的问题 | 不能说明什么 |
| --- | --- | --- |
| Prompt Tokens | 这一轮送入模型的完整上下文有多大？ | 不等于新加入的用户文字。它还包含 system、工具定义、历史回复和工具结果。 |
| Cached Tokens | 这一轮有多少 Prompt Token 由服务端缓存提供？ | 不能单独告诉你命中了哪一条消息。 |
| 未缓存 Tokens | 这一轮仍需正常处理多少 Prompt Token？ | 不一定全是“新加内容”；前缀被破坏时，旧内容也会重新计算。 |
| Cache% | 当前 Prompt 中缓存部分占多少？ | 高比例不总是好，例如滑动窗口把 Prompt 截得很短。 |
| 响应耗时 | 完整 API 请求多久返回？ | 当前非流式实现无法据此得到真正 TTFT。 |
| Completion Tokens | 模型本轮产出了多少 Token（含服务商计入的推理/输出用量）？ | 不能直接衡量答案质量。 |

## 此前英文诊断样本（不参与本轮排名）

来源：`学习资料/Agent/参考资料/深入理解AI-Agent/ai-agent-book-chapter2-current/chapter2/kv-cache/result_correct_20260808_185133.json`

| 语言/任务 | 模式 | 轮数 | 工具调用 | Prompt | Cached | Cache% | 总时间 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 英文默认任务 | `correct` | 13 | 31 | 381,511 | 287,438 | 75.3% | 108.648s |

> 这是此前诊断样本，任务、轮数和上下文均不同，只用于保留历史，不参与六模式排名。

## 逐模式、逐轮完整明细

### correct · 稳定上下文

机制：消息列表只创建一次，之后只在末尾追加。

结果：`success=True`，API 4 轮，工具调用 3 次，累计 Cache% 42.4%。

#### 第 1 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 603 | 256 | 347 | 42.5% | 66 | 3.176s | system → user | read_file → find → grep |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。
```

**消息 2 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

</details>

**模型本轮回复**

工具调用 1：`find`

参数：

```json
{"pattern": "*.py", "directory": "chapter2/kv-cache"}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "pattern": "*.py",
  "directory": "chapter2/kv-cache",
  "matches": [
    "chapter2/kv-cache/agent.py",
    "chapter2/kv-cache/main.py",
    "chapter2/kv-cache/tests/conftest.py",
    "chapter2/kv-cache/tests/manual/_bootstrap.py",
    "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py",
    "chapter2/kv-cache/tests/manual/check_cache_invalidation.py",
    "chapter2/kv-cache/tests/manual/check_cached_tokens.py",
    "chapter2/kv-cache/tests/manual/check_completion.py",
    "chapter2/kv-cache/tests/manual/check_tool_calling.py",
    "chapter2/kv-cache/tests/manual/check_ttft.py",
    "chapter2/kv-cache/tests/manual/demo_quick.py",
    "chapter2/kv-cache/tests/test_error_handling.py",
    "chapter2/kv-cache/tests/test_file_range.py",
    "chapter2/kv-cache/tests/test_interactive.py",
    "chapter2/kv-cache/tests/test_message_flow.py",
    "chapter2/kv-cache/tests/test_negative_size.py",
    "chapter2/kv-cache/tests/test_tools.py"
  ],
  "count": 17,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 2 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 926 | 512 | 414 | 55.3% | 71 | 2.061s | system → user → assistant → tool | read_file → find → grep |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。
```

**消息 2 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

**消息 3 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "find_0",
    "function": {
      "arguments": "{\"pattern\": \"*.py\", \"directory\": \"chapter2/kv-cache\"}",
      "name": "find"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 4 · 工具（`tool`）**

```text
{"pattern": "*.py", "directory": "chapter2/kv-cache", "matches": ["chapter2/kv-cache/agent.py", "chapter2/kv-cache/main.py", "chapter2/kv-cache/tests/conftest.py", "chapter2/kv-cache/tests/manual/_bootstrap.py", "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py", "chapter2/kv-cache/tests/manual/check_cache_invalidation.py", "chapter2/kv-cache/tests/manual/check_cached_tokens.py", "chapter2/kv-cache/tests/manual/check_completion.py", "chapter2/kv-cache/tests/manual/check_tool_calling.py", "chapter2/kv-cache/tests/manual/check_ttft.py", "chapter2/kv-cache/tests/manual/demo_quick.py", "chapter2/kv-cache/tests/test_error_handling.py", "chapter2/kv-cache/tests/test_file_range.py", "chapter2/kv-cache/tests/test_interactive.py", "chapter2/kv-cache/tests/test_message_flow.py", "chapter2/kv-cache/tests/test_negative_size.py", "chapter2/kv-cache/tests/test_tools.py"], "count": 17, "truncated": false, "success": true}
```

</details>

**模型本轮回复**

工具调用 1：`read_file`

参数：

```json
{"file_path": "chapter2/kv-cache/main.py", "offset": 0, "size": 80}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "path": "chapter2/kv-cache/main.py",
  "content": "\"\"\"\nMain script to demonstrate KV cache importance\nRuns the ReAct agent with different implementations and compares performance\n\"\"\"\n\nimport os\nimport sys\nimport glob\nimport json\nimport argparse\nimport logging\nfrom typing import Dict, List, Any\nfrom datetime import datetime\nfrom dataclasses import asdict\n\ntry:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n\nfrom agent import KVCacheAgent, KVCacheMode, AgentMetrics, compare_implementations\n\n# Default model (Moonshot / Kimi). The whole current Kimi family (k2.5/k2.6/\n# k2.7/k3) reports cached_tokens for automatic prefix caching AND reasons, so it\n# only accepts temperature=1 (agent.py handles that automatically). kimi-k2.6 has\n# the lightest reasoning footprint of the cache-reporting models, giving the\n# cleanest TTFT while still exposing the prefix-cache hit metric this demo needs.\n# (The non-reasoning moonshot-v1-* models do NOT report cached_tokens, so they\n# cannot demonstrate the cache effect.)\nDEFAULT_MODEL = \"kimi-k2.6\"\nDEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), \"../..\"))\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format='%(asctime)s - %(levelname)s - %(message)s',\n    handlers=[\n        logging.FileHandler('kv_cache_demo.log'),\n        logging.StreamHandler()\n    ]\n)\nlogger = logging.getLogger(__name__)\n\n\n# ---------------------------------------------------------------------------\n# Metrics helpers (shared by live comparison and offline report)\n# ---------------------------------------------------------------------------\n\ndef _coerce_metrics(metrics: Any) -> Dict[str, Any]:\n    \"\"\"Normalize a stored metrics value into a plain dict.\n\n    Handles both formats found in result files:\n      - dict: produced by --compare (asdict) and by the fixed --mode path\n      - str : legacy single-mode files that stored repr(AgentMetrics(...))\n              because json.dump used default=str\n    \"\"\"\n    if isinstance(metrics, dict):\n        return metrics\n    if isinstance(metrics, str) and metrics.startswith(\"AgentMetrics(\"):\n        # Safe eval: only AgentMetrics is exposed, no builtins.\n        try:\n            obj = eval(metrics, {\"__builtins__\": {}}, {\"AgentMetrics\": AgentMetrics})\n            return asdict(obj)\n        except Exception as e:  # pragma: no cover - defensive\n            logger.warning(f\"Could not parse legacy metrics string: {e}\")\n    return {}\n\n\ndef _avg_ttft(m: Dict[str, Any]) -> float:\n    \"\"\"Average TTFT across iterations, falling back to first-iteration TTFT.\"\"\"\n    lst = m.get(\"ttft_per_iteration\") or []\n    return sum(lst) / len(lst) if lst else float(m.get(\"ttft\", 0.0) or 0.0)\n\n\ndef _hit_rate(m: Dict[str, Any]) -> float:\n    total = (m.get(\"cache_hits\", 0) or 0) + (m.get(\"cache_misses\", 0) or 0)\n    return (m.get(\"cache_hits\", 0) or 0) / total * 100 if total else 0.0\n\n\n",
  "total_lines": 548,
  "lines_read": 80,
  "offset": 0,
  "end_line": 80,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 3 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1,823 | 512 | 1,311 | 28.1% | 127 | 3.394s | system → user → assistant → tool → assistant → tool | read_file → find → grep |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。
```

**消息 2 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

**消息 3 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "find_0",
    "function": {
      "arguments": "{\"pattern\": \"*.py\", \"directory\": \"chapter2/kv-cache\"}",
      "name": "find"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 4 · 工具（`tool`）**

```text
{"pattern": "*.py", "directory": "chapter2/kv-cache", "matches": ["chapter2/kv-cache/agent.py", "chapter2/kv-cache/main.py", "chapter2/kv-cache/tests/conftest.py", "chapter2/kv-cache/tests/manual/_bootstrap.py", "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py", "chapter2/kv-cache/tests/manual/check_cache_invalidation.py", "chapter2/kv-cache/tests/manual/check_cached_tokens.py", "chapter2/kv-cache/tests/manual/check_completion.py", "chapter2/kv-cache/tests/manual/check_tool_calling.py", "chapter2/kv-cache/tests/manual/check_ttft.py", "chapter2/kv-cache/tests/manual/demo_quick.py", "chapter2/kv-cache/tests/test_error_handling.py", "chapter2/kv-cache/tests/test_file_range.py", "chapter2/kv-cache/tests/test_interactive.py", "chapter2/kv-cache/tests/test_message_flow.py", "chapter2/kv-cache/tests/test_negative_size.py", "chapter2/kv-cache/tests/test_tools.py"], "count": 17, "truncated": false, "success": true}
```

**消息 5 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "read_file_1",
    "function": {
      "arguments": "{\"file_path\": \"chapter2/kv-cache/main.py\", \"offset\": 0, \"size\": 80}",
      "name": "read_file"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 6 · 工具（`tool`）**

```text
{"path": "chapter2/kv-cache/main.py", "content": "\"\"\"\nMain script to demonstrate KV cache importance\nRuns the ReAct agent with different implementations and compares performance\n\"\"\"\n\nimport os\nimport sys\nimport glob\nimport json\nimport argparse\nimport logging\nfrom typing import Dict, List, Any\nfrom datetime import datetime\nfrom dataclasses import asdict\n\ntry:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n\nfrom agent import KVCacheAgent, KVCacheMode, AgentMetrics, compare_implementations\n\n# Default model (Moonshot / Kimi). The whole current Kimi family (k2.5/k2.6/\n# k2.7/k3) reports cached_tokens for automatic prefix caching AND reasons, so it\n# only accepts temperature=1 (agent.py handles that automatically). kimi-k2.6 has\n# the lightest reasoning footprint of the cache-reporting models, giving the\n# cleanest TTFT while still exposing the prefix-cache hit metric this demo needs.\n# (The non-reasoning moonshot-v1-* models do NOT report cached_tokens, so they\n# cannot demonstrate the cache effect.)\nDEFAULT_MODEL = \"kimi-k2.6\"\nDEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), \"../..\"))\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format='%(asctime)s - %(levelname)s - %(message)s',\n    handlers=[\n        logging.FileHandler('kv_cache_demo.log'),\n        logging.StreamHandler()\n    ]\n)\nlogger = logging.getLogger(__name__)\n\n\n# ---------------------------------------------------------------------------\n# Metrics helpers (shared by live comparison and offline report)\n# ---------------------------------------------------------------------------\n\ndef _coerce_metrics(metrics: Any) -> Dict[str, Any]:\n    \"\"\"Normalize a stored metrics value into a plain dict.\n\n    Handles both formats found in result files:\n      - dict: produced by --compare (asdict) and by the fixed --mode path\n      - str : legacy single-mode files that stored repr(AgentMetrics(...))\n              because json.dump used default=str\n    \"\"\"\n    if isinstance(metrics, dict):\n        return metrics\n    if isinstance(metrics, str) and metrics.startswith(\"AgentMetrics(\"):\n        # Safe eval: only AgentMetrics is exposed, no builtins.\n        try:\n            obj = eval(metrics, {\"__builtins__\": {}}, {\"AgentMetrics\": AgentMetrics})\n            return asdict(obj)\n        except Exception as e:  # pragma: no cover - defensive\n            logger.warning(f\"Could not parse legacy metrics string: {e}\")\n    return {}\n\n\ndef _avg_ttft(m: Dict[str, Any]) -> float:\n    \"\"\"Average TTFT across iterations, falling back to first-iteration TTFT.\"\"\"\n    lst = m.get(\"ttft_per_iteration\") or []\n    return sum(lst) / len(lst) if lst else float(m.get(\"ttft\", 0.0) or 0.0)\n\n\ndef _hit_rate(m: Dict[str, Any]) -> float:\n    total = (m.get(\"cache_hits\", 0) or 0) + (m.get(\"cache_misses\", 0) or 0)\n    return (m.get(\"cache_hits\", 0) or 0) / total * 100 if total else 0.0\n\n\n", "total_lines": 548, "lines_read": 80, "offset": 0, "end_line": 80, "truncated": false, "success": true}
```

</details>

**模型本轮回复**

工具调用 1：`grep`

参数：

```json
{"pattern": "class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens", "file_path": "chapter2/kv-cache/agent.py"}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "pattern": "class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens",
  "matches": [
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 3,
      "line": "Demonstrates the importance of KV cache through correct and incorrect implementations."
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 33,
      "line": "chat models do NOT reason (and also do not report cached_tokens).\"\"\""
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 59,
      "line": "class KVCacheMode(Enum):"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 61,
      "line": "CORRECT = \"correct\"  # Correct implementation with stable context"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 62,
      "line": "DYNAMIC_SYSTEM = \"dynamic_system\"  # Changing system prompt with timestamp"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 63,
      "line": "SHUFFLED_TOOLS = \"shuffled_tools\"  # Shuffling tool order each request"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 64,
      "line": "DYNAMIC_PROFILE = \"dynamic_profile\"  # Changing user profile with credits"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 65,
      "line": "SLIDING_WINDOW = \"sliding_window\"  # Only keeping recent 6 messages"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 66,
      "line": "TEXT_FORMAT = \"text_format\"  # Formatting messages as plain text"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 91,
      "line": "cached_tokens: int = 0"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 357,
      "line": "def __init__(self, api_key: str, mode: KVCacheMode = KVCacheMode.CORRECT,"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 486,
      "line": "if self.mode == KVCacheMode.DYNAMIC_SYSTEM:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 497,
      "line": "if self.mode == KVCacheMode.SHUFFLED_TOOLS:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 505,
      "line": "if self.mode == KVCacheMode.DYNAMIC_PROFILE:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 514,
      "line": "\"\"\"Format messages based on mode - recreated each iteration for incorrect modes\"\"\""
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 517,
      "line": "# Add system prompt (changes each time for DYNAMIC_SYSTEM mode)"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 528,
      "line": "if self.mode == KVCacheMode.SLIDING_WINDOW:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 540,
      "line": "elif self.mode == KVCacheMode.TEXT_FORMAT:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 575,
      "line": "# For CORRECT, DYNAMIC_SYSTEM, SHUFFLED_TOOLS, DYNAMIC_PROFILE modes"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 646,
      "line": "# CORRECT mode: Build messages once on first iteration, then keep appending"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 649,
      "line": "# INCORRECT modes: Recreate entire messages list from history each iteration"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 654,
      "line": "if self.mode == KVCacheMode.CORRECT:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 655,
      "line": "# Correct mode: Build messages once, then keep using same list"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 659,
      "line": "# Incorrect modes: Recreate messages from history each iteration"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 671,
      "line": "# Add tools for all modes (TEXT_FORMAT still needs tools to work)"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 672,
      "line": "# TEXT_FORMAT only affects how conversation history is formatted, not tool availability"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 706,
      "line": "# The cached_tokens field appears directly in the usage object"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 708,
      "line": "if hasattr(usage, 'cached_tokens'):"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 710,
      "line": "cached = usage.cached_tokens if usage.cached_tokens is not None else 0"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 711,
      "line": "self.metrics.cached_tokens += cached"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 720,
      "line": "if details and hasattr(details, 'cached_tokens'):"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 721,
      "line": "cached = details.cached_tokens if details.cached_tokens is not None else 0"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 722,
      "line": "self.metrics.cached_tokens += cached"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 883,
      "line": "logger.info(f\"Cached Tokens: {metrics.cached_tokens}\")"
    }
  ],
  "files_searched": 1,
  "match_count": 34,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 4 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 3,289 | 1,536 | 1,753 | 46.7% | 1,215 | 27.836s | system → user → assistant → tool → assistant → tool → assistant → tool | read_file → find → grep |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。
```

**消息 2 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

**消息 3 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "find_0",
    "function": {
      "arguments": "{\"pattern\": \"*.py\", \"directory\": \"chapter2/kv-cache\"}",
      "name": "find"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 4 · 工具（`tool`）**

```text
{"pattern": "*.py", "directory": "chapter2/kv-cache", "matches": ["chapter2/kv-cache/agent.py", "chapter2/kv-cache/main.py", "chapter2/kv-cache/tests/conftest.py", "chapter2/kv-cache/tests/manual/_bootstrap.py", "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py", "chapter2/kv-cache/tests/manual/check_cache_invalidation.py", "chapter2/kv-cache/tests/manual/check_cached_tokens.py", "chapter2/kv-cache/tests/manual/check_completion.py", "chapter2/kv-cache/tests/manual/check_tool_calling.py", "chapter2/kv-cache/tests/manual/check_ttft.py", "chapter2/kv-cache/tests/manual/demo_quick.py", "chapter2/kv-cache/tests/test_error_handling.py", "chapter2/kv-cache/tests/test_file_range.py", "chapter2/kv-cache/tests/test_interactive.py", "chapter2/kv-cache/tests/test_message_flow.py", "chapter2/kv-cache/tests/test_negative_size.py", "chapter2/kv-cache/tests/test_tools.py"], "count": 17, "truncated": false, "success": true}
```

**消息 5 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "read_file_1",
    "function": {
      "arguments": "{\"file_path\": \"chapter2/kv-cache/main.py\", \"offset\": 0, \"size\": 80}",
      "name": "read_file"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 6 · 工具（`tool`）**

```text
{"path": "chapter2/kv-cache/main.py", "content": "\"\"\"\nMain script to demonstrate KV cache importance\nRuns the ReAct agent with different implementations and compares performance\n\"\"\"\n\nimport os\nimport sys\nimport glob\nimport json\nimport argparse\nimport logging\nfrom typing import Dict, List, Any\nfrom datetime import datetime\nfrom dataclasses import asdict\n\ntry:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n\nfrom agent import KVCacheAgent, KVCacheMode, AgentMetrics, compare_implementations\n\n# Default model (Moonshot / Kimi). The whole current Kimi family (k2.5/k2.6/\n# k2.7/k3) reports cached_tokens for automatic prefix caching AND reasons, so it\n# only accepts temperature=1 (agent.py handles that automatically). kimi-k2.6 has\n# the lightest reasoning footprint of the cache-reporting models, giving the\n# cleanest TTFT while still exposing the prefix-cache hit metric this demo needs.\n# (The non-reasoning moonshot-v1-* models do NOT report cached_tokens, so they\n# cannot demonstrate the cache effect.)\nDEFAULT_MODEL = \"kimi-k2.6\"\nDEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), \"../..\"))\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format='%(asctime)s - %(levelname)s - %(message)s',\n    handlers=[\n        logging.FileHandler('kv_cache_demo.log'),\n        logging.StreamHandler()\n    ]\n)\nlogger = logging.getLogger(__name__)\n\n\n# ---------------------------------------------------------------------------\n# Metrics helpers (shared by live comparison and offline report)\n# ---------------------------------------------------------------------------\n\ndef _coerce_metrics(metrics: Any) -> Dict[str, Any]:\n    \"\"\"Normalize a stored metrics value into a plain dict.\n\n    Handles both formats found in result files:\n      - dict: produced by --compare (asdict) and by the fixed --mode path\n      - str : legacy single-mode files that stored repr(AgentMetrics(...))\n              because json.dump used default=str\n    \"\"\"\n    if isinstance(metrics, dict):\n        return metrics\n    if isinstance(metrics, str) and metrics.startswith(\"AgentMetrics(\"):\n        # Safe eval: only AgentMetrics is exposed, no builtins.\n        try:\n            obj = eval(metrics, {\"__builtins__\": {}}, {\"AgentMetrics\": AgentMetrics})\n            return asdict(obj)\n        except Exception as e:  # pragma: no cover - defensive\n            logger.warning(f\"Could not parse legacy metrics string: {e}\")\n    return {}\n\n\ndef _avg_ttft(m: Dict[str, Any]) -> float:\n    \"\"\"Average TTFT across iterations, falling back to first-iteration TTFT.\"\"\"\n    lst = m.get(\"ttft_per_iteration\") or []\n    return sum(lst) / len(lst) if lst else float(m.get(\"ttft\", 0.0) or 0.0)\n\n\ndef _hit_rate(m: Dict[str, Any]) -> float:\n    total = (m.get(\"cache_hits\", 0) or 0) + (m.get(\"cache_misses\", 0) or 0)\n    return (m.get(\"cache_hits\", 0) or 0) / total * 100 if total else 0.0\n\n\n", "total_lines": 548, "lines_read": 80, "offset": 0, "end_line": 80, "truncated": false, "success": true}
```

**消息 7 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "grep_2",
    "function": {
      "arguments": "{\"pattern\": \"class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens\", \"file_path\": \"chapter2/kv-cache/agent.py\"}",
      "name": "grep"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 8 · 工具（`tool`）**

```text
{"pattern": "class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens", "matches": [{"file": "chapter2/kv-cache/agent.py", "line_num": 3, "line": "Demonstrates the importance of KV cache through correct and incorrect implementations."}, {"file": "chapter2/kv-cache/agent.py", "line_num": 33, "line": "chat models do NOT reason (and also do not report cached_tokens).\"\"\""}, {"file": "chapter2/kv-cache/agent.py", "line_num": 59, "line": "class KVCacheMode(Enum):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 61, "line": "CORRECT = \"correct\"  # Correct implementation with stable context"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 62, "line": "DYNAMIC_SYSTEM = \"dynamic_system\"  # Changing system prompt with timestamp"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 63, "line": "SHUFFLED_TOOLS = \"shuffled_tools\"  # Shuffling tool order each request"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 64, "line": "DYNAMIC_PROFILE = \"dynamic_profile\"  # Changing user profile with credits"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 65, "line": "SLIDING_WINDOW = \"sliding_window\"  # Only keeping recent 6 messages"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 66, "line": "TEXT_FORMAT = \"text_format\"  # Formatting messages as plain text"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 91, "line": "cached_tokens: int = 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 357, "line": "def __init__(self, api_key: str, mode: KVCacheMode = KVCacheMode.CORRECT,"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 486, "line": "if self.mode == KVCacheMode.DYNAMIC_SYSTEM:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 497, "line": "if self.mode == KVCacheMode.SHUFFLED_TOOLS:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 505, "line": "if self.mode == KVCacheMode.DYNAMIC_PROFILE:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 514, "line": "\"\"\"Format messages based on mode - recreated each iteration for incorrect modes\"\"\""}, {"file": "chapter2/kv-cache/agent.py", "line_num": 517, "line": "# Add system prompt (changes each time for DYNAMIC_SYSTEM mode)"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 528, "line": "if self.mode == KVCacheMode.SLIDING_WINDOW:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 540, "line": "elif self.mode == KVCacheMode.TEXT_FORMAT:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 575, "line": "# For CORRECT, DYNAMIC_SYSTEM, SHUFFLED_TOOLS, DYNAMIC_PROFILE modes"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 646, "line": "# CORRECT mode: Build messages once on first iteration, then keep appending"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 649, "line": "# INCORRECT modes: Recreate entire messages list from history each iteration"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 654, "line": "if self.mode == KVCacheMode.CORRECT:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 655, "line": "# Correct mode: Build messages once, then keep using same list"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 659, "line": "# Incorrect modes: Recreate messages from history each iteration"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 671, "line": "# Add tools for all modes (TEXT_FORMAT still needs tools to work)"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 672, "line": "# TEXT_FORMAT only affects how conversation history is formatted, not tool availability"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 706, "line": "# The cached_tokens field appears directly in the usage object"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 708, "line": "if hasattr(usage, 'cached_tokens'):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 710, "line": "cached = usage.cached_tokens if usage.cached_tokens is not None else 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 711, "line": "self.metrics.cached_tokens += cached"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 720, "line": "if details and hasattr(details, 'cached_tokens'):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 721, "line": "cached = details.cached_tokens if details.cached_tokens is not None else 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 722, "line": "self.metrics.cached_tokens += cached"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 883, "line": "logger.info(f\"Cached Tokens: {metrics.cached_tokens}\")"}], "files_searched": 1, "match_count": 34, "truncated": false, "success": true}
```

</details>

**模型本轮回复**

```text
根据以上三步工具返回的结果，现对本轮 KV 缓存对照实验（编号：KV缓存对照-20260808-192341）作如下总结。

---

### 1. 实验目的
本实验旨在 **通过正确与错误的实现对比，演示 KV Cache（特别是自动前缀缓存）对 ReAct Agent 性能的重要性**。  
项目围绕一个 `KVCacheAgent` 展开，在 Moonshot/Kimi 系列模型（如 `kimi-k2.6`）上运行。这些模型会在返回的 `usage` 对象中暴露 `cached_tokens` 指标，从而可以直接观测前缀缓存是否命中；而老版非推理模型不报告该字段，无法完成本演示。

### 2. 六种实验模式
代码中通过 `KVCacheMode` 枚举定义了 6 种模式，其中 `CORRECT` 为正确实现，其余 5 种为会人为破坏前缀缓存的"错误"实现：

| 模式 | 说明 |
|------|------|
| **CORRECT** | 正确实现：首次构建消息列表后持续复用，保持上下文完全稳定，有利于前缀缓存命中。 |
| **DYNAMIC_SYSTEM** | 动态系统提示：每次请求都在系统提示中注入变化的内容（如时间戳），导致前缀不断变化。 |
| **SHUFFLED_TOOLS** | 乱序工具：每次请求打乱可用工具的排列顺序，使工具定义部分的前缀无法复用。 |
| **DYNAMIC_PROFILE** | 动态用户画像：在用户信息中插入变化字段（如积分余额），破坏前缀稳定性。 |
| **SLIDING_WINDOW** | 滑动窗口：只保留最近 6 条消息，导致历史上下文被截断，每次迭代需要重新构建消息序列。 |
| **TEXT_FORMAT** | 纯文本格式：将对话历史格式化为纯文本，改变消息结构，使缓存键无法匹配。 |

核心差异体现在消息构造逻辑上：  
- **CORRECT**：`Build messages once on first iteration, then keep appending`（首次构建后持续追加）。  
- **其余模式**：`Recreate entire messages list from history each iteration`（每次迭代从历史重新创建完整消息列表）。

### 3. 最值得比较的指标
从 `main.py` 与 `agent.py` 的代码证据来看，最值得重点对比的指标有：

1. **`cached_tokens`（缓存 Token 数）**  
   直接由模型在 `usage` 或 `details` 中返回，是前缀缓存命中效果的"金标准"。该值越高，说明越多输入被缓存复用。

2. **TTFT（Time To First Token，首 token 延迟）**  
   代码中专门计算了 `ttft_per_iteration` 及其平均值。KV Cache 命中率高时，模型无需重复计算前缀的 Key/Value，首包延迟会显著降低。

3. **缓存命中率（`cache_hits / (cache_hits + cache_misses)`）**  
   `main.py` 中定义了 `_hit_rate` 辅助函数，用于统计缓存命中比例，与 `cached_tokens` 互为印证。

---

**结论**：本实验通过 6 种消息构造策略的对照，量化了"不稳定前缀"对 KV 缓存的破坏作用；最值得关注的比较指标是 **`cached_tokens`** 与 **`ttft`**，二者能最直接地反映前缀缓存是否生效以及对用户体验（首包延迟）的影响。
```

**该模式最终回答**

```text
根据以上三步工具返回的结果，现对本轮 KV 缓存对照实验（编号：KV缓存对照-20260808-192341）作如下总结。

---

### 1. 实验目的
本实验旨在 **通过正确与错误的实现对比，演示 KV Cache（特别是自动前缀缓存）对 ReAct Agent 性能的重要性**。  
项目围绕一个 `KVCacheAgent` 展开，在 Moonshot/Kimi 系列模型（如 `kimi-k2.6`）上运行。这些模型会在返回的 `usage` 对象中暴露 `cached_tokens` 指标，从而可以直接观测前缀缓存是否命中；而老版非推理模型不报告该字段，无法完成本演示。

### 2. 六种实验模式
代码中通过 `KVCacheMode` 枚举定义了 6 种模式，其中 `CORRECT` 为正确实现，其余 5 种为会人为破坏前缀缓存的"错误"实现：

| 模式 | 说明 |
|------|------|
| **CORRECT** | 正确实现：首次构建消息列表后持续复用，保持上下文完全稳定，有利于前缀缓存命中。 |
| **DYNAMIC_SYSTEM** | 动态系统提示：每次请求都在系统提示中注入变化的内容（如时间戳），导致前缀不断变化。 |
| **SHUFFLED_TOOLS** | 乱序工具：每次请求打乱可用工具的排列顺序，使工具定义部分的前缀无法复用。 |
| **DYNAMIC_PROFILE** | 动态用户画像：在用户信息中插入变化字段（如积分余额），破坏前缀稳定性。 |
| **SLIDING_WINDOW** | 滑动窗口：只保留最近 6 条消息，导致历史上下文被截断，每次迭代需要重新构建消息序列。 |
| **TEXT_FORMAT** | 纯文本格式：将对话历史格式化为纯文本，改变消息结构，使缓存键无法匹配。 |

核心差异体现在消息构造逻辑上：  
- **CORRECT**：`Build messages once on first iteration, then keep appending`（首次构建后持续追加）。  
- **其余模式**：`Recreate entire messages list from history each iteration`（每次迭代从历史重新创建完整消息列表）。

### 3. 最值得比较的指标
从 `main.py` 与 `agent.py` 的代码证据来看，最值得重点对比的指标有：

1. **`cached_tokens`（缓存 Token 数）**  
   直接由模型在 `usage` 或 `details` 中返回，是前缀缓存命中效果的"金标准"。该值越高，说明越多输入被缓存复用。

2. **TTFT（Time To First Token，首 token 延迟）**  
   代码中专门计算了 `ttft_per_iteration` 及其平均值。KV Cache 命中率高时，模型无需重复计算前缀的 Key/Value，首包延迟会显著降低。

3. **缓存命中率（`cache_hits / (cache_hits + cache_misses)`）**  
   `main.py` 中定义了 `_hit_rate` 辅助函数，用于统计缓存命中比例，与 `cached_tokens` 互为印证。

---

**结论**：本实验通过 6 种消息构造策略的对照，量化了"不稳定前缀"对 KV 缓存的破坏作用；最值得关注的比较指标是 **`cached_tokens`** 与 **`ttft`**，二者能最直接地反映前缀缓存是否生效以及对用户体验（首包延迟）的影响。
```

### dynamic_system · 动态系统提示

机制：每轮在系统提示末尾追加不同时间戳。

结果：`success=True`，API 4 轮，工具调用 3 次，累计 Cache% 14.6%。

#### 第 1 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 621 | 256 | 365 | 41.2% | 105 | 4.881s | system → user | read_file → find → grep |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。

当前时间：2026-08-08 19:24:17.962752
```

**消息 2 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

</details>

**模型本轮回复**

```text
正在执行第 1 步：查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
```

工具调用 1：`find`

参数：

```json
{"pattern": "*.py", "directory": "chapter2/kv-cache"}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "pattern": "*.py",
  "directory": "chapter2/kv-cache",
  "matches": [
    "chapter2/kv-cache/agent.py",
    "chapter2/kv-cache/main.py",
    "chapter2/kv-cache/tests/conftest.py",
    "chapter2/kv-cache/tests/manual/_bootstrap.py",
    "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py",
    "chapter2/kv-cache/tests/manual/check_cache_invalidation.py",
    "chapter2/kv-cache/tests/manual/check_cached_tokens.py",
    "chapter2/kv-cache/tests/manual/check_completion.py",
    "chapter2/kv-cache/tests/manual/check_tool_calling.py",
    "chapter2/kv-cache/tests/manual/check_ttft.py",
    "chapter2/kv-cache/tests/manual/demo_quick.py",
    "chapter2/kv-cache/tests/test_error_handling.py",
    "chapter2/kv-cache/tests/test_file_range.py",
    "chapter2/kv-cache/tests/test_interactive.py",
    "chapter2/kv-cache/tests/test_message_flow.py",
    "chapter2/kv-cache/tests/test_negative_size.py",
    "chapter2/kv-cache/tests/test_tools.py"
  ],
  "count": 17,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 2 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 983 | 256 | 727 | 26.0% | 108 | 3.935s | system → assistant → tool → user | read_file → find → grep |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。

当前时间：2026-08-08 19:24:22.846156
```

**消息 2 · 助手（`assistant`）**

```text
正在执行第 1 步：查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
```

工具调用声明：

```json
[
  {
    "id": "find_0",
    "function": {
      "arguments": "{\"pattern\": \"*.py\", \"directory\": \"chapter2/kv-cache\"}",
      "name": "find"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 3 · 工具（`tool`）**

```text
{"pattern": "*.py", "directory": "chapter2/kv-cache", "matches": ["chapter2/kv-cache/agent.py", "chapter2/kv-cache/main.py", "chapter2/kv-cache/tests/conftest.py", "chapter2/kv-cache/tests/manual/_bootstrap.py", "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py", "chapter2/kv-cache/tests/manual/check_cache_invalidation.py", "chapter2/kv-cache/tests/manual/check_cached_tokens.py", "chapter2/kv-cache/tests/manual/check_completion.py", "chapter2/kv-cache/tests/manual/check_tool_calling.py", "chapter2/kv-cache/tests/manual/check_ttft.py", "chapter2/kv-cache/tests/manual/demo_quick.py", "chapter2/kv-cache/tests/test_error_handling.py", "chapter2/kv-cache/tests/test_file_range.py", "chapter2/kv-cache/tests/test_interactive.py", "chapter2/kv-cache/tests/test_message_flow.py", "chapter2/kv-cache/tests/test_negative_size.py", "chapter2/kv-cache/tests/test_tools.py"], "count": 17, "truncated": false, "success": true}
```

**消息 4 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

</details>

**模型本轮回复**

```text
正在执行第 2 步：读取 `chapter2/kv-cache/main.py` 的前 80 行。
```

工具调用 1：`read_file`

参数：

```json
{"file_path": "chapter2/kv-cache/main.py", "offset": 0, "size": 80}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "path": "chapter2/kv-cache/main.py",
  "content": "\"\"\"\nMain script to demonstrate KV cache importance\nRuns the ReAct agent with different implementations and compares performance\n\"\"\"\n\nimport os\nimport sys\nimport glob\nimport json\nimport argparse\nimport logging\nfrom typing import Dict, List, Any\nfrom datetime import datetime\nfrom dataclasses import asdict\n\ntry:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n\nfrom agent import KVCacheAgent, KVCacheMode, AgentMetrics, compare_implementations\n\n# Default model (Moonshot / Kimi). The whole current Kimi family (k2.5/k2.6/\n# k2.7/k3) reports cached_tokens for automatic prefix caching AND reasons, so it\n# only accepts temperature=1 (agent.py handles that automatically). kimi-k2.6 has\n# the lightest reasoning footprint of the cache-reporting models, giving the\n# cleanest TTFT while still exposing the prefix-cache hit metric this demo needs.\n# (The non-reasoning moonshot-v1-* models do NOT report cached_tokens, so they\n# cannot demonstrate the cache effect.)\nDEFAULT_MODEL = \"kimi-k2.6\"\nDEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), \"../..\"))\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format='%(asctime)s - %(levelname)s - %(message)s',\n    handlers=[\n        logging.FileHandler('kv_cache_demo.log'),\n        logging.StreamHandler()\n    ]\n)\nlogger = logging.getLogger(__name__)\n\n\n# ---------------------------------------------------------------------------\n# Metrics helpers (shared by live comparison and offline report)\n# ---------------------------------------------------------------------------\n\ndef _coerce_metrics(metrics: Any) -> Dict[str, Any]:\n    \"\"\"Normalize a stored metrics value into a plain dict.\n\n    Handles both formats found in result files:\n      - dict: produced by --compare (asdict) and by the fixed --mode path\n      - str : legacy single-mode files that stored repr(AgentMetrics(...))\n              because json.dump used default=str\n    \"\"\"\n    if isinstance(metrics, dict):\n        return metrics\n    if isinstance(metrics, str) and metrics.startswith(\"AgentMetrics(\"):\n        # Safe eval: only AgentMetrics is exposed, no builtins.\n        try:\n            obj = eval(metrics, {\"__builtins__\": {}}, {\"AgentMetrics\": AgentMetrics})\n            return asdict(obj)\n        except Exception as e:  # pragma: no cover - defensive\n            logger.warning(f\"Could not parse legacy metrics string: {e}\")\n    return {}\n\n\ndef _avg_ttft(m: Dict[str, Any]) -> float:\n    \"\"\"Average TTFT across iterations, falling back to first-iteration TTFT.\"\"\"\n    lst = m.get(\"ttft_per_iteration\") or []\n    return sum(lst) / len(lst) if lst else float(m.get(\"ttft\", 0.0) or 0.0)\n\n\ndef _hit_rate(m: Dict[str, Any]) -> float:\n    total = (m.get(\"cache_hits\", 0) or 0) + (m.get(\"cache_misses\", 0) or 0)\n    return (m.get(\"cache_hits\", 0) or 0) / total * 100 if total else 0.0\n\n\n",
  "total_lines": 548,
  "lines_read": 80,
  "offset": 0,
  "end_line": 80,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 3 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1,917 | 256 | 1,661 | 13.4% | 249 | 9.611s | system → assistant → tool → assistant → tool → user | read_file → find → grep |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。

当前时间：2026-08-08 19:24:26.782500
```

**消息 2 · 助手（`assistant`）**

```text
正在执行第 1 步：查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
```

工具调用声明：

```json
[
  {
    "id": "find_0",
    "function": {
      "arguments": "{\"pattern\": \"*.py\", \"directory\": \"chapter2/kv-cache\"}",
      "name": "find"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 3 · 工具（`tool`）**

```text
{"pattern": "*.py", "directory": "chapter2/kv-cache", "matches": ["chapter2/kv-cache/agent.py", "chapter2/kv-cache/main.py", "chapter2/kv-cache/tests/conftest.py", "chapter2/kv-cache/tests/manual/_bootstrap.py", "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py", "chapter2/kv-cache/tests/manual/check_cache_invalidation.py", "chapter2/kv-cache/tests/manual/check_cached_tokens.py", "chapter2/kv-cache/tests/manual/check_completion.py", "chapter2/kv-cache/tests/manual/check_tool_calling.py", "chapter2/kv-cache/tests/manual/check_ttft.py", "chapter2/kv-cache/tests/manual/demo_quick.py", "chapter2/kv-cache/tests/test_error_handling.py", "chapter2/kv-cache/tests/test_file_range.py", "chapter2/kv-cache/tests/test_interactive.py", "chapter2/kv-cache/tests/test_message_flow.py", "chapter2/kv-cache/tests/test_negative_size.py", "chapter2/kv-cache/tests/test_tools.py"], "count": 17, "truncated": false, "success": true}
```

**消息 4 · 助手（`assistant`）**

```text
正在执行第 2 步：读取 `chapter2/kv-cache/main.py` 的前 80 行。
```

工具调用声明：

```json
[
  {
    "id": "read_file_1",
    "function": {
      "arguments": "{\"file_path\": \"chapter2/kv-cache/main.py\", \"offset\": 0, \"size\": 80}",
      "name": "read_file"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 5 · 工具（`tool`）**

```text
{"path": "chapter2/kv-cache/main.py", "content": "\"\"\"\nMain script to demonstrate KV cache importance\nRuns the ReAct agent with different implementations and compares performance\n\"\"\"\n\nimport os\nimport sys\nimport glob\nimport json\nimport argparse\nimport logging\nfrom typing import Dict, List, Any\nfrom datetime import datetime\nfrom dataclasses import asdict\n\ntry:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n\nfrom agent import KVCacheAgent, KVCacheMode, AgentMetrics, compare_implementations\n\n# Default model (Moonshot / Kimi). The whole current Kimi family (k2.5/k2.6/\n# k2.7/k3) reports cached_tokens for automatic prefix caching AND reasons, so it\n# only accepts temperature=1 (agent.py handles that automatically). kimi-k2.6 has\n# the lightest reasoning footprint of the cache-reporting models, giving the\n# cleanest TTFT while still exposing the prefix-cache hit metric this demo needs.\n# (The non-reasoning moonshot-v1-* models do NOT report cached_tokens, so they\n# cannot demonstrate the cache effect.)\nDEFAULT_MODEL = \"kimi-k2.6\"\nDEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), \"../..\"))\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format='%(asctime)s - %(levelname)s - %(message)s',\n    handlers=[\n        logging.FileHandler('kv_cache_demo.log'),\n        logging.StreamHandler()\n    ]\n)\nlogger = logging.getLogger(__name__)\n\n\n# ---------------------------------------------------------------------------\n# Metrics helpers (shared by live comparison and offline report)\n# ---------------------------------------------------------------------------\n\ndef _coerce_metrics(metrics: Any) -> Dict[str, Any]:\n    \"\"\"Normalize a stored metrics value into a plain dict.\n\n    Handles both formats found in result files:\n      - dict: produced by --compare (asdict) and by the fixed --mode path\n      - str : legacy single-mode files that stored repr(AgentMetrics(...))\n              because json.dump used default=str\n    \"\"\"\n    if isinstance(metrics, dict):\n        return metrics\n    if isinstance(metrics, str) and metrics.startswith(\"AgentMetrics(\"):\n        # Safe eval: only AgentMetrics is exposed, no builtins.\n        try:\n            obj = eval(metrics, {\"__builtins__\": {}}, {\"AgentMetrics\": AgentMetrics})\n            return asdict(obj)\n        except Exception as e:  # pragma: no cover - defensive\n            logger.warning(f\"Could not parse legacy metrics string: {e}\")\n    return {}\n\n\ndef _avg_ttft(m: Dict[str, Any]) -> float:\n    \"\"\"Average TTFT across iterations, falling back to first-iteration TTFT.\"\"\"\n    lst = m.get(\"ttft_per_iteration\") or []\n    return sum(lst) / len(lst) if lst else float(m.get(\"ttft\", 0.0) or 0.0)\n\n\ndef _hit_rate(m: Dict[str, Any]) -> float:\n    total = (m.get(\"cache_hits\", 0) or 0) + (m.get(\"cache_misses\", 0) or 0)\n    return (m.get(\"cache_hits\", 0) or 0) / total * 100 if total else 0.0\n\n\n", "total_lines": 548, "lines_read": 80, "offset": 0, "end_line": 80, "truncated": false, "success": true}
```

**消息 6 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

</details>

**模型本轮回复**

```text
正在执行第 3 步：在 `chapter2/kv-cache/agent.py` 中搜索六种模式和缓存指标的关键代码。
```

工具调用 1：`grep`

参数：

```json
{"pattern": "class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens", "file_path": "chapter2/kv-cache/agent.py"}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "pattern": "class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens",
  "matches": [
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 3,
      "line": "Demonstrates the importance of KV cache through correct and incorrect implementations."
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 33,
      "line": "chat models do NOT reason (and also do not report cached_tokens).\"\"\""
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 59,
      "line": "class KVCacheMode(Enum):"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 61,
      "line": "CORRECT = \"correct\"  # Correct implementation with stable context"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 62,
      "line": "DYNAMIC_SYSTEM = \"dynamic_system\"  # Changing system prompt with timestamp"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 63,
      "line": "SHUFFLED_TOOLS = \"shuffled_tools\"  # Shuffling tool order each request"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 64,
      "line": "DYNAMIC_PROFILE = \"dynamic_profile\"  # Changing user profile with credits"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 65,
      "line": "SLIDING_WINDOW = \"sliding_window\"  # Only keeping recent 6 messages"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 66,
      "line": "TEXT_FORMAT = \"text_format\"  # Formatting messages as plain text"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 91,
      "line": "cached_tokens: int = 0"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 357,
      "line": "def __init__(self, api_key: str, mode: KVCacheMode = KVCacheMode.CORRECT,"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 486,
      "line": "if self.mode == KVCacheMode.DYNAMIC_SYSTEM:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 497,
      "line": "if self.mode == KVCacheMode.SHUFFLED_TOOLS:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 505,
      "line": "if self.mode == KVCacheMode.DYNAMIC_PROFILE:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 514,
      "line": "\"\"\"Format messages based on mode - recreated each iteration for incorrect modes\"\"\""
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 517,
      "line": "# Add system prompt (changes each time for DYNAMIC_SYSTEM mode)"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 528,
      "line": "if self.mode == KVCacheMode.SLIDING_WINDOW:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 540,
      "line": "elif self.mode == KVCacheMode.TEXT_FORMAT:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 575,
      "line": "# For CORRECT, DYNAMIC_SYSTEM, SHUFFLED_TOOLS, DYNAMIC_PROFILE modes"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 646,
      "line": "# CORRECT mode: Build messages once on first iteration, then keep appending"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 649,
      "line": "# INCORRECT modes: Recreate entire messages list from history each iteration"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 654,
      "line": "if self.mode == KVCacheMode.CORRECT:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 655,
      "line": "# Correct mode: Build messages once, then keep using same list"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 659,
      "line": "# Incorrect modes: Recreate messages from history each iteration"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 671,
      "line": "# Add tools for all modes (TEXT_FORMAT still needs tools to work)"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 672,
      "line": "# TEXT_FORMAT only affects how conversation history is formatted, not tool availability"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 706,
      "line": "# The cached_tokens field appears directly in the usage object"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 708,
      "line": "if hasattr(usage, 'cached_tokens'):"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 710,
      "line": "cached = usage.cached_tokens if usage.cached_tokens is not None else 0"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 711,
      "line": "self.metrics.cached_tokens += cached"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 720,
      "line": "if details and hasattr(details, 'cached_tokens'):"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 721,
      "line": "cached = details.cached_tokens if details.cached_tokens is not None else 0"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 722,
      "line": "self.metrics.cached_tokens += cached"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 883,
      "line": "logger.info(f\"Cached Tokens: {metrics.cached_tokens}\")"
    }
  ],
  "files_searched": 1,
  "match_count": 34,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 4 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 3,505 | 256 | 3,249 | 7.3% | 1,677 | 42.845s | system → assistant → tool → assistant → tool → assistant → tool → user | read_file → find → grep |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。

当前时间：2026-08-08 19:24:36.396704
```

**消息 2 · 助手（`assistant`）**

```text
正在执行第 1 步：查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
```

工具调用声明：

```json
[
  {
    "id": "find_0",
    "function": {
      "arguments": "{\"pattern\": \"*.py\", \"directory\": \"chapter2/kv-cache\"}",
      "name": "find"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 3 · 工具（`tool`）**

```text
{"pattern": "*.py", "directory": "chapter2/kv-cache", "matches": ["chapter2/kv-cache/agent.py", "chapter2/kv-cache/main.py", "chapter2/kv-cache/tests/conftest.py", "chapter2/kv-cache/tests/manual/_bootstrap.py", "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py", "chapter2/kv-cache/tests/manual/check_cache_invalidation.py", "chapter2/kv-cache/tests/manual/check_cached_tokens.py", "chapter2/kv-cache/tests/manual/check_completion.py", "chapter2/kv-cache/tests/manual/check_tool_calling.py", "chapter2/kv-cache/tests/manual/check_ttft.py", "chapter2/kv-cache/tests/manual/demo_quick.py", "chapter2/kv-cache/tests/test_error_handling.py", "chapter2/kv-cache/tests/test_file_range.py", "chapter2/kv-cache/tests/test_interactive.py", "chapter2/kv-cache/tests/test_message_flow.py", "chapter2/kv-cache/tests/test_negative_size.py", "chapter2/kv-cache/tests/test_tools.py"], "count": 17, "truncated": false, "success": true}
```

**消息 4 · 助手（`assistant`）**

```text
正在执行第 2 步：读取 `chapter2/kv-cache/main.py` 的前 80 行。
```

工具调用声明：

```json
[
  {
    "id": "read_file_1",
    "function": {
      "arguments": "{\"file_path\": \"chapter2/kv-cache/main.py\", \"offset\": 0, \"size\": 80}",
      "name": "read_file"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 5 · 工具（`tool`）**

```text
{"path": "chapter2/kv-cache/main.py", "content": "\"\"\"\nMain script to demonstrate KV cache importance\nRuns the ReAct agent with different implementations and compares performance\n\"\"\"\n\nimport os\nimport sys\nimport glob\nimport json\nimport argparse\nimport logging\nfrom typing import Dict, List, Any\nfrom datetime import datetime\nfrom dataclasses import asdict\n\ntry:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n\nfrom agent import KVCacheAgent, KVCacheMode, AgentMetrics, compare_implementations\n\n# Default model (Moonshot / Kimi). The whole current Kimi family (k2.5/k2.6/\n# k2.7/k3) reports cached_tokens for automatic prefix caching AND reasons, so it\n# only accepts temperature=1 (agent.py handles that automatically). kimi-k2.6 has\n# the lightest reasoning footprint of the cache-reporting models, giving the\n# cleanest TTFT while still exposing the prefix-cache hit metric this demo needs.\n# (The non-reasoning moonshot-v1-* models do NOT report cached_tokens, so they\n# cannot demonstrate the cache effect.)\nDEFAULT_MODEL = \"kimi-k2.6\"\nDEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), \"../..\"))\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format='%(asctime)s - %(levelname)s - %(message)s',\n    handlers=[\n        logging.FileHandler('kv_cache_demo.log'),\n        logging.StreamHandler()\n    ]\n)\nlogger = logging.getLogger(__name__)\n\n\n# ---------------------------------------------------------------------------\n# Metrics helpers (shared by live comparison and offline report)\n# ---------------------------------------------------------------------------\n\ndef _coerce_metrics(metrics: Any) -> Dict[str, Any]:\n    \"\"\"Normalize a stored metrics value into a plain dict.\n\n    Handles both formats found in result files:\n      - dict: produced by --compare (asdict) and by the fixed --mode path\n      - str : legacy single-mode files that stored repr(AgentMetrics(...))\n              because json.dump used default=str\n    \"\"\"\n    if isinstance(metrics, dict):\n        return metrics\n    if isinstance(metrics, str) and metrics.startswith(\"AgentMetrics(\"):\n        # Safe eval: only AgentMetrics is exposed, no builtins.\n        try:\n            obj = eval(metrics, {\"__builtins__\": {}}, {\"AgentMetrics\": AgentMetrics})\n            return asdict(obj)\n        except Exception as e:  # pragma: no cover - defensive\n            logger.warning(f\"Could not parse legacy metrics string: {e}\")\n    return {}\n\n\ndef _avg_ttft(m: Dict[str, Any]) -> float:\n    \"\"\"Average TTFT across iterations, falling back to first-iteration TTFT.\"\"\"\n    lst = m.get(\"ttft_per_iteration\") or []\n    return sum(lst) / len(lst) if lst else float(m.get(\"ttft\", 0.0) or 0.0)\n\n\ndef _hit_rate(m: Dict[str, Any]) -> float:\n    total = (m.get(\"cache_hits\", 0) or 0) + (m.get(\"cache_misses\", 0) or 0)\n    return (m.get(\"cache_hits\", 0) or 0) / total * 100 if total else 0.0\n\n\n", "total_lines": 548, "lines_read": 80, "offset": 0, "end_line": 80, "truncated": false, "success": true}
```

**消息 6 · 助手（`assistant`）**

```text
正在执行第 3 步：在 `chapter2/kv-cache/agent.py` 中搜索六种模式和缓存指标的关键代码。
```

工具调用声明：

```json
[
  {
    "id": "grep_2",
    "function": {
      "arguments": "{\"pattern\": \"class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens\", \"file_path\": \"chapter2/kv-cache/agent.py\"}",
      "name": "grep"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 7 · 工具（`tool`）**

```text
{"pattern": "class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens", "matches": [{"file": "chapter2/kv-cache/agent.py", "line_num": 3, "line": "Demonstrates the importance of KV cache through correct and incorrect implementations."}, {"file": "chapter2/kv-cache/agent.py", "line_num": 33, "line": "chat models do NOT reason (and also do not report cached_tokens).\"\"\""}, {"file": "chapter2/kv-cache/agent.py", "line_num": 59, "line": "class KVCacheMode(Enum):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 61, "line": "CORRECT = \"correct\"  # Correct implementation with stable context"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 62, "line": "DYNAMIC_SYSTEM = \"dynamic_system\"  # Changing system prompt with timestamp"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 63, "line": "SHUFFLED_TOOLS = \"shuffled_tools\"  # Shuffling tool order each request"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 64, "line": "DYNAMIC_PROFILE = \"dynamic_profile\"  # Changing user profile with credits"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 65, "line": "SLIDING_WINDOW = \"sliding_window\"  # Only keeping recent 6 messages"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 66, "line": "TEXT_FORMAT = \"text_format\"  # Formatting messages as plain text"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 91, "line": "cached_tokens: int = 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 357, "line": "def __init__(self, api_key: str, mode: KVCacheMode = KVCacheMode.CORRECT,"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 486, "line": "if self.mode == KVCacheMode.DYNAMIC_SYSTEM:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 497, "line": "if self.mode == KVCacheMode.SHUFFLED_TOOLS:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 505, "line": "if self.mode == KVCacheMode.DYNAMIC_PROFILE:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 514, "line": "\"\"\"Format messages based on mode - recreated each iteration for incorrect modes\"\"\""}, {"file": "chapter2/kv-cache/agent.py", "line_num": 517, "line": "# Add system prompt (changes each time for DYNAMIC_SYSTEM mode)"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 528, "line": "if self.mode == KVCacheMode.SLIDING_WINDOW:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 540, "line": "elif self.mode == KVCacheMode.TEXT_FORMAT:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 575, "line": "# For CORRECT, DYNAMIC_SYSTEM, SHUFFLED_TOOLS, DYNAMIC_PROFILE modes"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 646, "line": "# CORRECT mode: Build messages once on first iteration, then keep appending"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 649, "line": "# INCORRECT modes: Recreate entire messages list from history each iteration"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 654, "line": "if self.mode == KVCacheMode.CORRECT:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 655, "line": "# Correct mode: Build messages once, then keep using same list"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 659, "line": "# Incorrect modes: Recreate messages from history each iteration"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 671, "line": "# Add tools for all modes (TEXT_FORMAT still needs tools to work)"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 672, "line": "# TEXT_FORMAT only affects how conversation history is formatted, not tool availability"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 706, "line": "# The cached_tokens field appears directly in the usage object"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 708, "line": "if hasattr(usage, 'cached_tokens'):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 710, "line": "cached = usage.cached_tokens if usage.cached_tokens is not None else 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 711, "line": "self.metrics.cached_tokens += cached"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 720, "line": "if details and hasattr(details, 'cached_tokens'):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 721, "line": "cached = details.cached_tokens if details.cached_tokens is not None else 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 722, "line": "self.metrics.cached_tokens += cached"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 883, "line": "logger.info(f\"Cached Tokens: {metrics.cached_tokens}\")"}], "files_searched": 1, "match_count": 34, "truncated": false, "success": true}
```

**消息 8 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

</details>

**模型本轮回复**

```text
根据前三步已收集的工具结果，现直接给出第 4 步总结。

---

## KV 缓存对照实验总结（编号：KV缓存对照-20260808-192341）

### 一、实验目的
本项目通过运行同一个 ReAct Agent 的**正确实现**与**五种常见错误实现**，演示 **KV Cache（前缀缓存）** 对推理延迟和缓存效率的影响。实验选用支持自动前缀缓存且能返回 `cached_tokens` 的模型（如默认的 `kimi-k2.6`），利用其暴露的缓存命中指标，量化“稳定上下文”与“不稳定上下文”之间的性能差距。

### 二、六种实验模式（定义于 `agent.py` 的 `KVCacheMode`）
| 模式 | 名称 | 核心行为 |
|---|---|---|
| 1 | **CORRECT**（正确模式） | System prompt、工具、用户资料保持稳定；消息列表在首轮构建后持续追加，最大化前缀缓存命中。 |
| 2 | **DYNAMIC_SYSTEM**（动态系统提示） | 每次请求修改 system prompt（例如加入时间戳），导致前缀不断变化，缓存失效。 |
| 3 | **SHUFFLED_TOOLS**（打乱工具顺序） | 每次请求重新排列工具定义的顺序，改变输入前缀。 |
| 4 | **DYNAMIC_PROFILE**（动态用户资料） | 每次变更用户 profile（如 credits），使上下文前缀发生变化。 |
| 5 | **SLIDING_WINDOW**（滑动窗口） | 仅保留最近 6 条消息，历史前缀被截断，无法利用完整前缀缓存。 |
| 6 | **TEXT_FORMAT**（纯文本格式） | 将对话历史格式化为纯文本而非保持结构化消息，改变输入表示形式。 |

> 代码逻辑差异：`CORRECT` 模式“一次构建、持续追加”；其余五种错误模式均“每次迭代从历史重新创建整个消息列表”，从而破坏前缀一致性。

### 三、最值得比较的指标
1. **`cached_tokens`（缓存命中 token 数）**  
   直接来自模型返回的 `usage.cached_tokens`，反映有多少输入 token 命中了前缀缓存。这是判断 KV Cache 是否生效的**最直接证据**。

2. **TTFT（Time To First Token，首 token 延迟）**  
   衡量用户感知延迟。缓存命中越高，模型复用已计算的 KV，TTFT 通常越低；反之则显著上升。

3. **缓存命中率（Cache Hit Rate）**  
   由 `cache_hits / (cache_hits + cache_misses)` 计算，用于量化整体缓存效率。

### 结论
本实验的核心看点是：**`CORRECT` 模式因保持消息前缀稳定，能获得高 `cached_tokens` 和低 TTFT；而其余五种模式因不断扰动前缀、截断历史或变更格式，导致前缀缓存失效，TTFT 增加、缓存 token 数减少。** 这直观证明了在多轮 ReAct 推理中维护稳定上下文对 KV Cache 性能的决定性作用。
```

**该模式最终回答**

```text
根据前三步已收集的工具结果，现直接给出第 4 步总结。

---

## KV 缓存对照实验总结（编号：KV缓存对照-20260808-192341）

### 一、实验目的
本项目通过运行同一个 ReAct Agent 的**正确实现**与**五种常见错误实现**，演示 **KV Cache（前缀缓存）** 对推理延迟和缓存效率的影响。实验选用支持自动前缀缓存且能返回 `cached_tokens` 的模型（如默认的 `kimi-k2.6`），利用其暴露的缓存命中指标，量化“稳定上下文”与“不稳定上下文”之间的性能差距。

### 二、六种实验模式（定义于 `agent.py` 的 `KVCacheMode`）
| 模式 | 名称 | 核心行为 |
|---|---|---|
| 1 | **CORRECT**（正确模式） | System prompt、工具、用户资料保持稳定；消息列表在首轮构建后持续追加，最大化前缀缓存命中。 |
| 2 | **DYNAMIC_SYSTEM**（动态系统提示） | 每次请求修改 system prompt（例如加入时间戳），导致前缀不断变化，缓存失效。 |
| 3 | **SHUFFLED_TOOLS**（打乱工具顺序） | 每次请求重新排列工具定义的顺序，改变输入前缀。 |
| 4 | **DYNAMIC_PROFILE**（动态用户资料） | 每次变更用户 profile（如 credits），使上下文前缀发生变化。 |
| 5 | **SLIDING_WINDOW**（滑动窗口） | 仅保留最近 6 条消息，历史前缀被截断，无法利用完整前缀缓存。 |
| 6 | **TEXT_FORMAT**（纯文本格式） | 将对话历史格式化为纯文本而非保持结构化消息，改变输入表示形式。 |

> 代码逻辑差异：`CORRECT` 模式“一次构建、持续追加”；其余五种错误模式均“每次迭代从历史重新创建整个消息列表”，从而破坏前缀一致性。

### 三、最值得比较的指标
1. **`cached_tokens`（缓存命中 token 数）**  
   直接来自模型返回的 `usage.cached_tokens`，反映有多少输入 token 命中了前缀缓存。这是判断 KV Cache 是否生效的**最直接证据**。

2. **TTFT（Time To First Token，首 token 延迟）**  
   衡量用户感知延迟。缓存命中越高，模型复用已计算的 KV，TTFT 通常越低；反之则显著上升。

3. **缓存命中率（Cache Hit Rate）**  
   由 `cache_hits / (cache_hits + cache_misses)` 计算，用于量化整体缓存效率。

### 结论
本实验的核心看点是：**`CORRECT` 模式因保持消息前缀稳定，能获得高 `cached_tokens` 和低 TTFT；而其余五种模式因不断扰动前缀、截断历史或变更格式，导致前缀缓存失效，TTFT 增加、缓存 token 数减少。** 这直观证明了在多轮 ReAct 推理中维护稳定上下文对 KV Cache 性能的决定性作用。
```

### shuffled_tools · 工具顺序变化

机制：每轮随机改变三个工具定义的顺序。

结果：`success=True`，API 4 轮，工具调用 3 次，累计 Cache% 3.7%。

#### 第 1 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 603 | 0 | 603 | 0.0% | 79 | 7.830s | system → user | find → read_file → grep |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。
```

**消息 2 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

</details>

**模型本轮回复**

工具调用 1：`find`

参数：

```json
{"pattern": "*.py", "directory": "chapter2/kv-cache"}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "pattern": "*.py",
  "directory": "chapter2/kv-cache",
  "matches": [
    "chapter2/kv-cache/agent.py",
    "chapter2/kv-cache/main.py",
    "chapter2/kv-cache/tests/conftest.py",
    "chapter2/kv-cache/tests/manual/_bootstrap.py",
    "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py",
    "chapter2/kv-cache/tests/manual/check_cache_invalidation.py",
    "chapter2/kv-cache/tests/manual/check_cached_tokens.py",
    "chapter2/kv-cache/tests/manual/check_completion.py",
    "chapter2/kv-cache/tests/manual/check_tool_calling.py",
    "chapter2/kv-cache/tests/manual/check_ttft.py",
    "chapter2/kv-cache/tests/manual/demo_quick.py",
    "chapter2/kv-cache/tests/test_error_handling.py",
    "chapter2/kv-cache/tests/test_file_range.py",
    "chapter2/kv-cache/tests/test_interactive.py",
    "chapter2/kv-cache/tests/test_message_flow.py",
    "chapter2/kv-cache/tests/test_negative_size.py",
    "chapter2/kv-cache/tests/test_tools.py"
  ],
  "count": 17,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 2 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 939 | 0 | 939 | 0.0% | 117 | 4.624s | system → assistant → tool → user | grep → read_file → find |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。
```

**消息 2 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "find_0",
    "function": {
      "arguments": "{\"pattern\": \"*.py\", \"directory\": \"chapter2/kv-cache\"}",
      "name": "find"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 3 · 工具（`tool`）**

```text
{"pattern": "*.py", "directory": "chapter2/kv-cache", "matches": ["chapter2/kv-cache/agent.py", "chapter2/kv-cache/main.py", "chapter2/kv-cache/tests/conftest.py", "chapter2/kv-cache/tests/manual/_bootstrap.py", "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py", "chapter2/kv-cache/tests/manual/check_cache_invalidation.py", "chapter2/kv-cache/tests/manual/check_cached_tokens.py", "chapter2/kv-cache/tests/manual/check_completion.py", "chapter2/kv-cache/tests/manual/check_tool_calling.py", "chapter2/kv-cache/tests/manual/check_ttft.py", "chapter2/kv-cache/tests/manual/demo_quick.py", "chapter2/kv-cache/tests/test_error_handling.py", "chapter2/kv-cache/tests/test_file_range.py", "chapter2/kv-cache/tests/test_interactive.py", "chapter2/kv-cache/tests/test_message_flow.py", "chapter2/kv-cache/tests/test_negative_size.py", "chapter2/kv-cache/tests/test_tools.py"], "count": 17, "truncated": false, "success": true}
```

**消息 4 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

</details>

**模型本轮回复**

工具调用 1：`read_file`

参数：

```json
{"file_path": "chapter2/kv-cache/main.py", "offset": 0, "size": 80}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "path": "chapter2/kv-cache/main.py",
  "content": "\"\"\"\nMain script to demonstrate KV cache importance\nRuns the ReAct agent with different implementations and compares performance\n\"\"\"\n\nimport os\nimport sys\nimport glob\nimport json\nimport argparse\nimport logging\nfrom typing import Dict, List, Any\nfrom datetime import datetime\nfrom dataclasses import asdict\n\ntry:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n\nfrom agent import KVCacheAgent, KVCacheMode, AgentMetrics, compare_implementations\n\n# Default model (Moonshot / Kimi). The whole current Kimi family (k2.5/k2.6/\n# k2.7/k3) reports cached_tokens for automatic prefix caching AND reasons, so it\n# only accepts temperature=1 (agent.py handles that automatically). kimi-k2.6 has\n# the lightest reasoning footprint of the cache-reporting models, giving the\n# cleanest TTFT while still exposing the prefix-cache hit metric this demo needs.\n# (The non-reasoning moonshot-v1-* models do NOT report cached_tokens, so they\n# cannot demonstrate the cache effect.)\nDEFAULT_MODEL = \"kimi-k2.6\"\nDEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), \"../..\"))\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format='%(asctime)s - %(levelname)s - %(message)s',\n    handlers=[\n        logging.FileHandler('kv_cache_demo.log'),\n        logging.StreamHandler()\n    ]\n)\nlogger = logging.getLogger(__name__)\n\n\n# ---------------------------------------------------------------------------\n# Metrics helpers (shared by live comparison and offline report)\n# ---------------------------------------------------------------------------\n\ndef _coerce_metrics(metrics: Any) -> Dict[str, Any]:\n    \"\"\"Normalize a stored metrics value into a plain dict.\n\n    Handles both formats found in result files:\n      - dict: produced by --compare (asdict) and by the fixed --mode path\n      - str : legacy single-mode files that stored repr(AgentMetrics(...))\n              because json.dump used default=str\n    \"\"\"\n    if isinstance(metrics, dict):\n        return metrics\n    if isinstance(metrics, str) and metrics.startswith(\"AgentMetrics(\"):\n        # Safe eval: only AgentMetrics is exposed, no builtins.\n        try:\n            obj = eval(metrics, {\"__builtins__\": {}}, {\"AgentMetrics\": AgentMetrics})\n            return asdict(obj)\n        except Exception as e:  # pragma: no cover - defensive\n            logger.warning(f\"Could not parse legacy metrics string: {e}\")\n    return {}\n\n\ndef _avg_ttft(m: Dict[str, Any]) -> float:\n    \"\"\"Average TTFT across iterations, falling back to first-iteration TTFT.\"\"\"\n    lst = m.get(\"ttft_per_iteration\") or []\n    return sum(lst) / len(lst) if lst else float(m.get(\"ttft\", 0.0) or 0.0)\n\n\ndef _hit_rate(m: Dict[str, Any]) -> float:\n    total = (m.get(\"cache_hits\", 0) or 0) + (m.get(\"cache_misses\", 0) or 0)\n    return (m.get(\"cache_hits\", 0) or 0) / total * 100 if total else 0.0\n\n\n",
  "total_lines": 548,
  "lines_read": 80,
  "offset": 0,
  "end_line": 80,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 3 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1,882 | 0 | 1,882 | 0.0% | 305 | 9.759s | system → assistant → tool → assistant → tool → user | find → grep → read_file |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。
```

**消息 2 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "find_0",
    "function": {
      "arguments": "{\"pattern\": \"*.py\", \"directory\": \"chapter2/kv-cache\"}",
      "name": "find"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 3 · 工具（`tool`）**

```text
{"pattern": "*.py", "directory": "chapter2/kv-cache", "matches": ["chapter2/kv-cache/agent.py", "chapter2/kv-cache/main.py", "chapter2/kv-cache/tests/conftest.py", "chapter2/kv-cache/tests/manual/_bootstrap.py", "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py", "chapter2/kv-cache/tests/manual/check_cache_invalidation.py", "chapter2/kv-cache/tests/manual/check_cached_tokens.py", "chapter2/kv-cache/tests/manual/check_completion.py", "chapter2/kv-cache/tests/manual/check_tool_calling.py", "chapter2/kv-cache/tests/manual/check_ttft.py", "chapter2/kv-cache/tests/manual/demo_quick.py", "chapter2/kv-cache/tests/test_error_handling.py", "chapter2/kv-cache/tests/test_file_range.py", "chapter2/kv-cache/tests/test_interactive.py", "chapter2/kv-cache/tests/test_message_flow.py", "chapter2/kv-cache/tests/test_negative_size.py", "chapter2/kv-cache/tests/test_tools.py"], "count": 17, "truncated": false, "success": true}
```

**消息 4 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "read_file_1",
    "function": {
      "arguments": "{\"file_path\": \"chapter2/kv-cache/main.py\", \"offset\": 0, \"size\": 80}",
      "name": "read_file"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 5 · 工具（`tool`）**

```text
{"path": "chapter2/kv-cache/main.py", "content": "\"\"\"\nMain script to demonstrate KV cache importance\nRuns the ReAct agent with different implementations and compares performance\n\"\"\"\n\nimport os\nimport sys\nimport glob\nimport json\nimport argparse\nimport logging\nfrom typing import Dict, List, Any\nfrom datetime import datetime\nfrom dataclasses import asdict\n\ntry:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n\nfrom agent import KVCacheAgent, KVCacheMode, AgentMetrics, compare_implementations\n\n# Default model (Moonshot / Kimi). The whole current Kimi family (k2.5/k2.6/\n# k2.7/k3) reports cached_tokens for automatic prefix caching AND reasons, so it\n# only accepts temperature=1 (agent.py handles that automatically). kimi-k2.6 has\n# the lightest reasoning footprint of the cache-reporting models, giving the\n# cleanest TTFT while still exposing the prefix-cache hit metric this demo needs.\n# (The non-reasoning moonshot-v1-* models do NOT report cached_tokens, so they\n# cannot demonstrate the cache effect.)\nDEFAULT_MODEL = \"kimi-k2.6\"\nDEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), \"../..\"))\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format='%(asctime)s - %(levelname)s - %(message)s',\n    handlers=[\n        logging.FileHandler('kv_cache_demo.log'),\n        logging.StreamHandler()\n    ]\n)\nlogger = logging.getLogger(__name__)\n\n\n# ---------------------------------------------------------------------------\n# Metrics helpers (shared by live comparison and offline report)\n# ---------------------------------------------------------------------------\n\ndef _coerce_metrics(metrics: Any) -> Dict[str, Any]:\n    \"\"\"Normalize a stored metrics value into a plain dict.\n\n    Handles both formats found in result files:\n      - dict: produced by --compare (asdict) and by the fixed --mode path\n      - str : legacy single-mode files that stored repr(AgentMetrics(...))\n              because json.dump used default=str\n    \"\"\"\n    if isinstance(metrics, dict):\n        return metrics\n    if isinstance(metrics, str) and metrics.startswith(\"AgentMetrics(\"):\n        # Safe eval: only AgentMetrics is exposed, no builtins.\n        try:\n            obj = eval(metrics, {\"__builtins__\": {}}, {\"AgentMetrics\": AgentMetrics})\n            return asdict(obj)\n        except Exception as e:  # pragma: no cover - defensive\n            logger.warning(f\"Could not parse legacy metrics string: {e}\")\n    return {}\n\n\ndef _avg_ttft(m: Dict[str, Any]) -> float:\n    \"\"\"Average TTFT across iterations, falling back to first-iteration TTFT.\"\"\"\n    lst = m.get(\"ttft_per_iteration\") or []\n    return sum(lst) / len(lst) if lst else float(m.get(\"ttft\", 0.0) or 0.0)\n\n\ndef _hit_rate(m: Dict[str, Any]) -> float:\n    total = (m.get(\"cache_hits\", 0) or 0) + (m.get(\"cache_misses\", 0) or 0)\n    return (m.get(\"cache_hits\", 0) or 0) / total * 100 if total else 0.0\n\n\n", "total_lines": 548, "lines_read": 80, "offset": 0, "end_line": 80, "truncated": false, "success": true}
```

**消息 6 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

</details>

**模型本轮回复**

工具调用 1：`grep`

参数：

```json
{"pattern": "class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens", "file_path": "chapter2/kv-cache/agent.py"}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "pattern": "class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens",
  "matches": [
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 3,
      "line": "Demonstrates the importance of KV cache through correct and incorrect implementations."
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 33,
      "line": "chat models do NOT reason (and also do not report cached_tokens).\"\"\""
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 59,
      "line": "class KVCacheMode(Enum):"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 61,
      "line": "CORRECT = \"correct\"  # Correct implementation with stable context"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 62,
      "line": "DYNAMIC_SYSTEM = \"dynamic_system\"  # Changing system prompt with timestamp"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 63,
      "line": "SHUFFLED_TOOLS = \"shuffled_tools\"  # Shuffling tool order each request"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 64,
      "line": "DYNAMIC_PROFILE = \"dynamic_profile\"  # Changing user profile with credits"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 65,
      "line": "SLIDING_WINDOW = \"sliding_window\"  # Only keeping recent 6 messages"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 66,
      "line": "TEXT_FORMAT = \"text_format\"  # Formatting messages as plain text"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 91,
      "line": "cached_tokens: int = 0"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 357,
      "line": "def __init__(self, api_key: str, mode: KVCacheMode = KVCacheMode.CORRECT,"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 486,
      "line": "if self.mode == KVCacheMode.DYNAMIC_SYSTEM:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 497,
      "line": "if self.mode == KVCacheMode.SHUFFLED_TOOLS:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 505,
      "line": "if self.mode == KVCacheMode.DYNAMIC_PROFILE:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 514,
      "line": "\"\"\"Format messages based on mode - recreated each iteration for incorrect modes\"\"\""
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 517,
      "line": "# Add system prompt (changes each time for DYNAMIC_SYSTEM mode)"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 528,
      "line": "if self.mode == KVCacheMode.SLIDING_WINDOW:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 540,
      "line": "elif self.mode == KVCacheMode.TEXT_FORMAT:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 575,
      "line": "# For CORRECT, DYNAMIC_SYSTEM, SHUFFLED_TOOLS, DYNAMIC_PROFILE modes"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 646,
      "line": "# CORRECT mode: Build messages once on first iteration, then keep appending"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 649,
      "line": "# INCORRECT modes: Recreate entire messages list from history each iteration"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 654,
      "line": "if self.mode == KVCacheMode.CORRECT:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 655,
      "line": "# Correct mode: Build messages once, then keep using same list"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 659,
      "line": "# Incorrect modes: Recreate messages from history each iteration"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 671,
      "line": "# Add tools for all modes (TEXT_FORMAT still needs tools to work)"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 672,
      "line": "# TEXT_FORMAT only affects how conversation history is formatted, not tool availability"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 706,
      "line": "# The cached_tokens field appears directly in the usage object"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 708,
      "line": "if hasattr(usage, 'cached_tokens'):"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 710,
      "line": "cached = usage.cached_tokens if usage.cached_tokens is not None else 0"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 711,
      "line": "self.metrics.cached_tokens += cached"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 720,
      "line": "if details and hasattr(details, 'cached_tokens'):"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 721,
      "line": "cached = details.cached_tokens if details.cached_tokens is not None else 0"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 722,
      "line": "self.metrics.cached_tokens += cached"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 883,
      "line": "logger.info(f\"Cached Tokens: {metrics.cached_tokens}\")"
    }
  ],
  "files_searched": 1,
  "match_count": 34,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 4 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 3,526 | 256 | 3,270 | 7.3% | 1,962 | 56.042s | system → assistant → tool → assistant → tool → assistant → tool → user | read_file → find → grep |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。
```

**消息 2 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "find_0",
    "function": {
      "arguments": "{\"pattern\": \"*.py\", \"directory\": \"chapter2/kv-cache\"}",
      "name": "find"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 3 · 工具（`tool`）**

```text
{"pattern": "*.py", "directory": "chapter2/kv-cache", "matches": ["chapter2/kv-cache/agent.py", "chapter2/kv-cache/main.py", "chapter2/kv-cache/tests/conftest.py", "chapter2/kv-cache/tests/manual/_bootstrap.py", "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py", "chapter2/kv-cache/tests/manual/check_cache_invalidation.py", "chapter2/kv-cache/tests/manual/check_cached_tokens.py", "chapter2/kv-cache/tests/manual/check_completion.py", "chapter2/kv-cache/tests/manual/check_tool_calling.py", "chapter2/kv-cache/tests/manual/check_ttft.py", "chapter2/kv-cache/tests/manual/demo_quick.py", "chapter2/kv-cache/tests/test_error_handling.py", "chapter2/kv-cache/tests/test_file_range.py", "chapter2/kv-cache/tests/test_interactive.py", "chapter2/kv-cache/tests/test_message_flow.py", "chapter2/kv-cache/tests/test_negative_size.py", "chapter2/kv-cache/tests/test_tools.py"], "count": 17, "truncated": false, "success": true}
```

**消息 4 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "read_file_1",
    "function": {
      "arguments": "{\"file_path\": \"chapter2/kv-cache/main.py\", \"offset\": 0, \"size\": 80}",
      "name": "read_file"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 5 · 工具（`tool`）**

```text
{"path": "chapter2/kv-cache/main.py", "content": "\"\"\"\nMain script to demonstrate KV cache importance\nRuns the ReAct agent with different implementations and compares performance\n\"\"\"\n\nimport os\nimport sys\nimport glob\nimport json\nimport argparse\nimport logging\nfrom typing import Dict, List, Any\nfrom datetime import datetime\nfrom dataclasses import asdict\n\ntry:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n\nfrom agent import KVCacheAgent, KVCacheMode, AgentMetrics, compare_implementations\n\n# Default model (Moonshot / Kimi). The whole current Kimi family (k2.5/k2.6/\n# k2.7/k3) reports cached_tokens for automatic prefix caching AND reasons, so it\n# only accepts temperature=1 (agent.py handles that automatically). kimi-k2.6 has\n# the lightest reasoning footprint of the cache-reporting models, giving the\n# cleanest TTFT while still exposing the prefix-cache hit metric this demo needs.\n# (The non-reasoning moonshot-v1-* models do NOT report cached_tokens, so they\n# cannot demonstrate the cache effect.)\nDEFAULT_MODEL = \"kimi-k2.6\"\nDEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), \"../..\"))\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format='%(asctime)s - %(levelname)s - %(message)s',\n    handlers=[\n        logging.FileHandler('kv_cache_demo.log'),\n        logging.StreamHandler()\n    ]\n)\nlogger = logging.getLogger(__name__)\n\n\n# ---------------------------------------------------------------------------\n# Metrics helpers (shared by live comparison and offline report)\n# ---------------------------------------------------------------------------\n\ndef _coerce_metrics(metrics: Any) -> Dict[str, Any]:\n    \"\"\"Normalize a stored metrics value into a plain dict.\n\n    Handles both formats found in result files:\n      - dict: produced by --compare (asdict) and by the fixed --mode path\n      - str : legacy single-mode files that stored repr(AgentMetrics(...))\n              because json.dump used default=str\n    \"\"\"\n    if isinstance(metrics, dict):\n        return metrics\n    if isinstance(metrics, str) and metrics.startswith(\"AgentMetrics(\"):\n        # Safe eval: only AgentMetrics is exposed, no builtins.\n        try:\n            obj = eval(metrics, {\"__builtins__\": {}}, {\"AgentMetrics\": AgentMetrics})\n            return asdict(obj)\n        except Exception as e:  # pragma: no cover - defensive\n            logger.warning(f\"Could not parse legacy metrics string: {e}\")\n    return {}\n\n\ndef _avg_ttft(m: Dict[str, Any]) -> float:\n    \"\"\"Average TTFT across iterations, falling back to first-iteration TTFT.\"\"\"\n    lst = m.get(\"ttft_per_iteration\") or []\n    return sum(lst) / len(lst) if lst else float(m.get(\"ttft\", 0.0) or 0.0)\n\n\ndef _hit_rate(m: Dict[str, Any]) -> float:\n    total = (m.get(\"cache_hits\", 0) or 0) + (m.get(\"cache_misses\", 0) or 0)\n    return (m.get(\"cache_hits\", 0) or 0) / total * 100 if total else 0.0\n\n\n", "total_lines": 548, "lines_read": 80, "offset": 0, "end_line": 80, "truncated": false, "success": true}
```

**消息 6 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "grep_2",
    "function": {
      "arguments": "{\"pattern\": \"class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens\", \"file_path\": \"chapter2/kv-cache/agent.py\"}",
      "name": "grep"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 7 · 工具（`tool`）**

```text
{"pattern": "class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens", "matches": [{"file": "chapter2/kv-cache/agent.py", "line_num": 3, "line": "Demonstrates the importance of KV cache through correct and incorrect implementations."}, {"file": "chapter2/kv-cache/agent.py", "line_num": 33, "line": "chat models do NOT reason (and also do not report cached_tokens).\"\"\""}, {"file": "chapter2/kv-cache/agent.py", "line_num": 59, "line": "class KVCacheMode(Enum):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 61, "line": "CORRECT = \"correct\"  # Correct implementation with stable context"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 62, "line": "DYNAMIC_SYSTEM = \"dynamic_system\"  # Changing system prompt with timestamp"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 63, "line": "SHUFFLED_TOOLS = \"shuffled_tools\"  # Shuffling tool order each request"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 64, "line": "DYNAMIC_PROFILE = \"dynamic_profile\"  # Changing user profile with credits"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 65, "line": "SLIDING_WINDOW = \"sliding_window\"  # Only keeping recent 6 messages"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 66, "line": "TEXT_FORMAT = \"text_format\"  # Formatting messages as plain text"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 91, "line": "cached_tokens: int = 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 357, "line": "def __init__(self, api_key: str, mode: KVCacheMode = KVCacheMode.CORRECT,"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 486, "line": "if self.mode == KVCacheMode.DYNAMIC_SYSTEM:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 497, "line": "if self.mode == KVCacheMode.SHUFFLED_TOOLS:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 505, "line": "if self.mode == KVCacheMode.DYNAMIC_PROFILE:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 514, "line": "\"\"\"Format messages based on mode - recreated each iteration for incorrect modes\"\"\""}, {"file": "chapter2/kv-cache/agent.py", "line_num": 517, "line": "# Add system prompt (changes each time for DYNAMIC_SYSTEM mode)"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 528, "line": "if self.mode == KVCacheMode.SLIDING_WINDOW:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 540, "line": "elif self.mode == KVCacheMode.TEXT_FORMAT:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 575, "line": "# For CORRECT, DYNAMIC_SYSTEM, SHUFFLED_TOOLS, DYNAMIC_PROFILE modes"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 646, "line": "# CORRECT mode: Build messages once on first iteration, then keep appending"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 649, "line": "# INCORRECT modes: Recreate entire messages list from history each iteration"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 654, "line": "if self.mode == KVCacheMode.CORRECT:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 655, "line": "# Correct mode: Build messages once, then keep using same list"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 659, "line": "# Incorrect modes: Recreate messages from history each iteration"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 671, "line": "# Add tools for all modes (TEXT_FORMAT still needs tools to work)"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 672, "line": "# TEXT_FORMAT only affects how conversation history is formatted, not tool availability"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 706, "line": "# The cached_tokens field appears directly in the usage object"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 708, "line": "if hasattr(usage, 'cached_tokens'):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 710, "line": "cached = usage.cached_tokens if usage.cached_tokens is not None else 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 711, "line": "self.metrics.cached_tokens += cached"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 720, "line": "if details and hasattr(details, 'cached_tokens'):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 721, "line": "cached = details.cached_tokens if details.cached_tokens is not None else 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 722, "line": "self.metrics.cached_tokens += cached"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 883, "line": "logger.info(f\"Cached Tokens: {metrics.cached_tokens}\")"}], "files_searched": 1, "match_count": 34, "truncated": false, "success": true}
```

**消息 8 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

</details>

**模型本轮回复**

```text
## 对照实验总结（实验编号：KV缓存对照-20260808-192341）

### 一、实验目的
本项目通过运行 **ReAct Agent** 的多种不同实现，**演示 KV Cache（自动前缀缓存）的重要性**。核心思路是：对比“正确维持上下文稳定”与“各种破坏前缀一致性”的做法，观察它们对缓存命中和推理性能的影响。

### 二、六种模式（`KVCacheMode`）
根据 `agent.py` 中的枚举定义与注释，六种模式如下：

| 模式 | 名称 | 行为特征 |
|------|------|----------|
| 1 | `CORRECT` | **正确实现**：保持上下文稳定，首次构建消息后持续追加，不破坏前缀一致性。 |
| 2 | `DYNAMIC_SYSTEM` | **动态系统提示**：每次请求的系统提示带时间戳，导致前缀不断变化。 |
| 3 | `SHUFFLED_TOOLS` | **乱序工具**：每次请求打乱工具定义顺序，使前缀内容发生变更。 |
| 4 | `DYNAMIC_PROFILE` | **动态用户画像**：每次改变用户资料/积分等前置信息，破坏缓存前缀。 |
| 5 | `SLIDING_WINDOW` | **滑动窗口**：仅保留最近 6 条消息，历史被截断，无法利用长前缀缓存。 |
| 6 | `TEXT_FORMAT` | **纯文本格式**：将对话历史格式化为纯文本，改变消息结构，导致前缀不一致。 |

关键实现差异：`CORRECT` 模式“首次构建消息列表后持续追加”，而其余五种错误模式则“每次迭代从历史重新创建整个消息列表”，从而无法命中前缀缓存。

### 三、最值得比较的指标
根据 `main.py` 的指标处理逻辑与 `agent.py` 的缓存采集逻辑，最核心的比较指标是：

1. **`cached_tokens`（缓存命中 token 数）**  
   直接从模型返回的 `usage.cached_tokens` 读取，是**最能量化 prefix cache 实际效果**的硬指标。实验选用的 `kimi-k2.6` 等模型之所以被推荐，正是因为它们会在响应中暴露该字段；不返回该字段的模型无法演示缓存差异。

2. **`TTFT`（Time To First Token，首 Token 延迟）**  
   `main.py` 专门计算了平均 TTFT（`_avg_ttft`）。前缀缓存命中越多，重复计算越少，首 token 返回就越快，这是用户体验层面的直接收益。

3. **`cache_hits / cache_misses`（缓存命中/未命中次数）**  
   配合计算命中率（`_hit_rate`），可辅助验证 `cached_tokens` 的趋势。

### 结论
该实验的本质是**通过控制消息列表的构造方式，来观察前缀缓存的命中情况**。`CORRECT` 模式作为基线，应表现出高 `cached_tokens` 和低 `TTFT`；其余五种模式因每次重塑前缀，预计缓存指标显著下降、延迟上升。
```

**该模式最终回答**

```text
## 对照实验总结（实验编号：KV缓存对照-20260808-192341）

### 一、实验目的
本项目通过运行 **ReAct Agent** 的多种不同实现，**演示 KV Cache（自动前缀缓存）的重要性**。核心思路是：对比“正确维持上下文稳定”与“各种破坏前缀一致性”的做法，观察它们对缓存命中和推理性能的影响。

### 二、六种模式（`KVCacheMode`）
根据 `agent.py` 中的枚举定义与注释，六种模式如下：

| 模式 | 名称 | 行为特征 |
|------|------|----------|
| 1 | `CORRECT` | **正确实现**：保持上下文稳定，首次构建消息后持续追加，不破坏前缀一致性。 |
| 2 | `DYNAMIC_SYSTEM` | **动态系统提示**：每次请求的系统提示带时间戳，导致前缀不断变化。 |
| 3 | `SHUFFLED_TOOLS` | **乱序工具**：每次请求打乱工具定义顺序，使前缀内容发生变更。 |
| 4 | `DYNAMIC_PROFILE` | **动态用户画像**：每次改变用户资料/积分等前置信息，破坏缓存前缀。 |
| 5 | `SLIDING_WINDOW` | **滑动窗口**：仅保留最近 6 条消息，历史被截断，无法利用长前缀缓存。 |
| 6 | `TEXT_FORMAT` | **纯文本格式**：将对话历史格式化为纯文本，改变消息结构，导致前缀不一致。 |

关键实现差异：`CORRECT` 模式“首次构建消息列表后持续追加”，而其余五种错误模式则“每次迭代从历史重新创建整个消息列表”，从而无法命中前缀缓存。

### 三、最值得比较的指标
根据 `main.py` 的指标处理逻辑与 `agent.py` 的缓存采集逻辑，最核心的比较指标是：

1. **`cached_tokens`（缓存命中 token 数）**  
   直接从模型返回的 `usage.cached_tokens` 读取，是**最能量化 prefix cache 实际效果**的硬指标。实验选用的 `kimi-k2.6` 等模型之所以被推荐，正是因为它们会在响应中暴露该字段；不返回该字段的模型无法演示缓存差异。

2. **`TTFT`（Time To First Token，首 Token 延迟）**  
   `main.py` 专门计算了平均 TTFT（`_avg_ttft`）。前缀缓存命中越多，重复计算越少，首 token 返回就越快，这是用户体验层面的直接收益。

3. **`cache_hits / cache_misses`（缓存命中/未命中次数）**  
   配合计算命中率（`_hit_rate`），可辅助验证 `cached_tokens` 的趋势。

### 结论
该实验的本质是**通过控制消息列表的构造方式，来观察前缀缓存的命中情况**。`CORRECT` 模式作为基线，应表现出高 `cached_tokens` 和低 `TTFT`；其余五种模式因每次重塑前缀，预计缓存指标显著下降、延迟上升。
```

### dynamic_profile · 动态用户资料

机制：每轮在靠前位置加入不断变化的剩余额度。

结果：`success=True`，API 4 轮，工具调用 3 次，累计 Cache% 15.3%。

#### 第 1 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 621 | 256 | 365 | 41.2% | 63 | 4.819s | system → user → user | read_file → find → grep |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。
```

**消息 2 · 用户（`user`）**

```text
[用户资料：高级用户，剩余 99 点额度]
```

**消息 3 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

</details>

**模型本轮回复**

工具调用 1：`find`

参数：

```json
{"pattern":"*.py","directory":"chapter2/kv-cache"}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "pattern": "*.py",
  "directory": "chapter2/kv-cache",
  "matches": [
    "chapter2/kv-cache/agent.py",
    "chapter2/kv-cache/main.py",
    "chapter2/kv-cache/tests/conftest.py",
    "chapter2/kv-cache/tests/manual/_bootstrap.py",
    "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py",
    "chapter2/kv-cache/tests/manual/check_cache_invalidation.py",
    "chapter2/kv-cache/tests/manual/check_cached_tokens.py",
    "chapter2/kv-cache/tests/manual/check_completion.py",
    "chapter2/kv-cache/tests/manual/check_tool_calling.py",
    "chapter2/kv-cache/tests/manual/check_ttft.py",
    "chapter2/kv-cache/tests/manual/demo_quick.py",
    "chapter2/kv-cache/tests/test_error_handling.py",
    "chapter2/kv-cache/tests/test_file_range.py",
    "chapter2/kv-cache/tests/test_interactive.py",
    "chapter2/kv-cache/tests/test_message_flow.py",
    "chapter2/kv-cache/tests/test_negative_size.py",
    "chapter2/kv-cache/tests/test_tools.py"
  ],
  "count": 17,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 2 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 941 | 256 | 685 | 27.2% | 80 | 2.704s | system → user → assistant → tool → user | read_file → find → grep |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。
```

**消息 2 · 用户（`user`）**

```text
[用户资料：高级用户，剩余 98 点额度]
```

**消息 3 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "find_0",
    "function": {
      "arguments": "{\"pattern\":\"*.py\",\"directory\":\"chapter2/kv-cache\"}",
      "name": "find"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 4 · 工具（`tool`）**

```text
{"pattern": "*.py", "directory": "chapter2/kv-cache", "matches": ["chapter2/kv-cache/agent.py", "chapter2/kv-cache/main.py", "chapter2/kv-cache/tests/conftest.py", "chapter2/kv-cache/tests/manual/_bootstrap.py", "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py", "chapter2/kv-cache/tests/manual/check_cache_invalidation.py", "chapter2/kv-cache/tests/manual/check_cached_tokens.py", "chapter2/kv-cache/tests/manual/check_completion.py", "chapter2/kv-cache/tests/manual/check_tool_calling.py", "chapter2/kv-cache/tests/manual/check_ttft.py", "chapter2/kv-cache/tests/manual/demo_quick.py", "chapter2/kv-cache/tests/test_error_handling.py", "chapter2/kv-cache/tests/test_file_range.py", "chapter2/kv-cache/tests/test_interactive.py", "chapter2/kv-cache/tests/test_message_flow.py", "chapter2/kv-cache/tests/test_negative_size.py", "chapter2/kv-cache/tests/test_tools.py"], "count": 17, "truncated": false, "success": true}
```

**消息 5 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

</details>

**模型本轮回复**

工具调用 1：`read_file`

参数：

```json
{"file_path":"chapter2/kv-cache/main.py","offset":0,"size":80}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "path": "chapter2/kv-cache/main.py",
  "content": "\"\"\"\nMain script to demonstrate KV cache importance\nRuns the ReAct agent with different implementations and compares performance\n\"\"\"\n\nimport os\nimport sys\nimport glob\nimport json\nimport argparse\nimport logging\nfrom typing import Dict, List, Any\nfrom datetime import datetime\nfrom dataclasses import asdict\n\ntry:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n\nfrom agent import KVCacheAgent, KVCacheMode, AgentMetrics, compare_implementations\n\n# Default model (Moonshot / Kimi). The whole current Kimi family (k2.5/k2.6/\n# k2.7/k3) reports cached_tokens for automatic prefix caching AND reasons, so it\n# only accepts temperature=1 (agent.py handles that automatically). kimi-k2.6 has\n# the lightest reasoning footprint of the cache-reporting models, giving the\n# cleanest TTFT while still exposing the prefix-cache hit metric this demo needs.\n# (The non-reasoning moonshot-v1-* models do NOT report cached_tokens, so they\n# cannot demonstrate the cache effect.)\nDEFAULT_MODEL = \"kimi-k2.6\"\nDEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), \"../..\"))\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format='%(asctime)s - %(levelname)s - %(message)s',\n    handlers=[\n        logging.FileHandler('kv_cache_demo.log'),\n        logging.StreamHandler()\n    ]\n)\nlogger = logging.getLogger(__name__)\n\n\n# ---------------------------------------------------------------------------\n# Metrics helpers (shared by live comparison and offline report)\n# ---------------------------------------------------------------------------\n\ndef _coerce_metrics(metrics: Any) -> Dict[str, Any]:\n    \"\"\"Normalize a stored metrics value into a plain dict.\n\n    Handles both formats found in result files:\n      - dict: produced by --compare (asdict) and by the fixed --mode path\n      - str : legacy single-mode files that stored repr(AgentMetrics(...))\n              because json.dump used default=str\n    \"\"\"\n    if isinstance(metrics, dict):\n        return metrics\n    if isinstance(metrics, str) and metrics.startswith(\"AgentMetrics(\"):\n        # Safe eval: only AgentMetrics is exposed, no builtins.\n        try:\n            obj = eval(metrics, {\"__builtins__\": {}}, {\"AgentMetrics\": AgentMetrics})\n            return asdict(obj)\n        except Exception as e:  # pragma: no cover - defensive\n            logger.warning(f\"Could not parse legacy metrics string: {e}\")\n    return {}\n\n\ndef _avg_ttft(m: Dict[str, Any]) -> float:\n    \"\"\"Average TTFT across iterations, falling back to first-iteration TTFT.\"\"\"\n    lst = m.get(\"ttft_per_iteration\") or []\n    return sum(lst) / len(lst) if lst else float(m.get(\"ttft\", 0.0) or 0.0)\n\n\ndef _hit_rate(m: Dict[str, Any]) -> float:\n    total = (m.get(\"cache_hits\", 0) or 0) + (m.get(\"cache_misses\", 0) or 0)\n    return (m.get(\"cache_hits\", 0) or 0) / total * 100 if total else 0.0\n\n\n",
  "total_lines": 548,
  "lines_read": 80,
  "offset": 0,
  "end_line": 80,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 3 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1,847 | 256 | 1,591 | 13.9% | 111 | 4.356s | system → user → assistant → tool → assistant → tool → user | read_file → find → grep |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。
```

**消息 2 · 用户（`user`）**

```text
[用户资料：高级用户，剩余 97 点额度]
```

**消息 3 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "find_0",
    "function": {
      "arguments": "{\"pattern\":\"*.py\",\"directory\":\"chapter2/kv-cache\"}",
      "name": "find"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 4 · 工具（`tool`）**

```text
{"pattern": "*.py", "directory": "chapter2/kv-cache", "matches": ["chapter2/kv-cache/agent.py", "chapter2/kv-cache/main.py", "chapter2/kv-cache/tests/conftest.py", "chapter2/kv-cache/tests/manual/_bootstrap.py", "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py", "chapter2/kv-cache/tests/manual/check_cache_invalidation.py", "chapter2/kv-cache/tests/manual/check_cached_tokens.py", "chapter2/kv-cache/tests/manual/check_completion.py", "chapter2/kv-cache/tests/manual/check_tool_calling.py", "chapter2/kv-cache/tests/manual/check_ttft.py", "chapter2/kv-cache/tests/manual/demo_quick.py", "chapter2/kv-cache/tests/test_error_handling.py", "chapter2/kv-cache/tests/test_file_range.py", "chapter2/kv-cache/tests/test_interactive.py", "chapter2/kv-cache/tests/test_message_flow.py", "chapter2/kv-cache/tests/test_negative_size.py", "chapter2/kv-cache/tests/test_tools.py"], "count": 17, "truncated": false, "success": true}
```

**消息 5 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "read_file_1",
    "function": {
      "arguments": "{\"file_path\":\"chapter2/kv-cache/main.py\",\"offset\":0,\"size\":80}",
      "name": "read_file"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 6 · 工具（`tool`）**

```text
{"path": "chapter2/kv-cache/main.py", "content": "\"\"\"\nMain script to demonstrate KV cache importance\nRuns the ReAct agent with different implementations and compares performance\n\"\"\"\n\nimport os\nimport sys\nimport glob\nimport json\nimport argparse\nimport logging\nfrom typing import Dict, List, Any\nfrom datetime import datetime\nfrom dataclasses import asdict\n\ntry:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n\nfrom agent import KVCacheAgent, KVCacheMode, AgentMetrics, compare_implementations\n\n# Default model (Moonshot / Kimi). The whole current Kimi family (k2.5/k2.6/\n# k2.7/k3) reports cached_tokens for automatic prefix caching AND reasons, so it\n# only accepts temperature=1 (agent.py handles that automatically). kimi-k2.6 has\n# the lightest reasoning footprint of the cache-reporting models, giving the\n# cleanest TTFT while still exposing the prefix-cache hit metric this demo needs.\n# (The non-reasoning moonshot-v1-* models do NOT report cached_tokens, so they\n# cannot demonstrate the cache effect.)\nDEFAULT_MODEL = \"kimi-k2.6\"\nDEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), \"../..\"))\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format='%(asctime)s - %(levelname)s - %(message)s',\n    handlers=[\n        logging.FileHandler('kv_cache_demo.log'),\n        logging.StreamHandler()\n    ]\n)\nlogger = logging.getLogger(__name__)\n\n\n# ---------------------------------------------------------------------------\n# Metrics helpers (shared by live comparison and offline report)\n# ---------------------------------------------------------------------------\n\ndef _coerce_metrics(metrics: Any) -> Dict[str, Any]:\n    \"\"\"Normalize a stored metrics value into a plain dict.\n\n    Handles both formats found in result files:\n      - dict: produced by --compare (asdict) and by the fixed --mode path\n      - str : legacy single-mode files that stored repr(AgentMetrics(...))\n              because json.dump used default=str\n    \"\"\"\n    if isinstance(metrics, dict):\n        return metrics\n    if isinstance(metrics, str) and metrics.startswith(\"AgentMetrics(\"):\n        # Safe eval: only AgentMetrics is exposed, no builtins.\n        try:\n            obj = eval(metrics, {\"__builtins__\": {}}, {\"AgentMetrics\": AgentMetrics})\n            return asdict(obj)\n        except Exception as e:  # pragma: no cover - defensive\n            logger.warning(f\"Could not parse legacy metrics string: {e}\")\n    return {}\n\n\ndef _avg_ttft(m: Dict[str, Any]) -> float:\n    \"\"\"Average TTFT across iterations, falling back to first-iteration TTFT.\"\"\"\n    lst = m.get(\"ttft_per_iteration\") or []\n    return sum(lst) / len(lst) if lst else float(m.get(\"ttft\", 0.0) or 0.0)\n\n\ndef _hit_rate(m: Dict[str, Any]) -> float:\n    total = (m.get(\"cache_hits\", 0) or 0) + (m.get(\"cache_misses\", 0) or 0)\n    return (m.get(\"cache_hits\", 0) or 0) / total * 100 if total else 0.0\n\n\n", "total_lines": 548, "lines_read": 80, "offset": 0, "end_line": 80, "truncated": false, "success": true}
```

**消息 7 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

</details>

**模型本轮回复**

工具调用 1：`grep`

参数：

```json
{"pattern":"class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens","file_path":"chapter2/kv-cache/agent.py"}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "pattern": "class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens",
  "matches": [
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 3,
      "line": "Demonstrates the importance of KV cache through correct and incorrect implementations."
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 33,
      "line": "chat models do NOT reason (and also do not report cached_tokens).\"\"\""
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 59,
      "line": "class KVCacheMode(Enum):"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 61,
      "line": "CORRECT = \"correct\"  # Correct implementation with stable context"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 62,
      "line": "DYNAMIC_SYSTEM = \"dynamic_system\"  # Changing system prompt with timestamp"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 63,
      "line": "SHUFFLED_TOOLS = \"shuffled_tools\"  # Shuffling tool order each request"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 64,
      "line": "DYNAMIC_PROFILE = \"dynamic_profile\"  # Changing user profile with credits"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 65,
      "line": "SLIDING_WINDOW = \"sliding_window\"  # Only keeping recent 6 messages"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 66,
      "line": "TEXT_FORMAT = \"text_format\"  # Formatting messages as plain text"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 91,
      "line": "cached_tokens: int = 0"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 357,
      "line": "def __init__(self, api_key: str, mode: KVCacheMode = KVCacheMode.CORRECT,"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 486,
      "line": "if self.mode == KVCacheMode.DYNAMIC_SYSTEM:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 497,
      "line": "if self.mode == KVCacheMode.SHUFFLED_TOOLS:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 505,
      "line": "if self.mode == KVCacheMode.DYNAMIC_PROFILE:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 514,
      "line": "\"\"\"Format messages based on mode - recreated each iteration for incorrect modes\"\"\""
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 517,
      "line": "# Add system prompt (changes each time for DYNAMIC_SYSTEM mode)"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 528,
      "line": "if self.mode == KVCacheMode.SLIDING_WINDOW:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 540,
      "line": "elif self.mode == KVCacheMode.TEXT_FORMAT:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 575,
      "line": "# For CORRECT, DYNAMIC_SYSTEM, SHUFFLED_TOOLS, DYNAMIC_PROFILE modes"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 646,
      "line": "# CORRECT mode: Build messages once on first iteration, then keep appending"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 649,
      "line": "# INCORRECT modes: Recreate entire messages list from history each iteration"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 654,
      "line": "if self.mode == KVCacheMode.CORRECT:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 655,
      "line": "# Correct mode: Build messages once, then keep using same list"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 659,
      "line": "# Incorrect modes: Recreate messages from history each iteration"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 671,
      "line": "# Add tools for all modes (TEXT_FORMAT still needs tools to work)"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 672,
      "line": "# TEXT_FORMAT only affects how conversation history is formatted, not tool availability"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 706,
      "line": "# The cached_tokens field appears directly in the usage object"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 708,
      "line": "if hasattr(usage, 'cached_tokens'):"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 710,
      "line": "cached = usage.cached_tokens if usage.cached_tokens is not None else 0"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 711,
      "line": "self.metrics.cached_tokens += cached"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 720,
      "line": "if details and hasattr(details, 'cached_tokens'):"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 721,
      "line": "cached = details.cached_tokens if details.cached_tokens is not None else 0"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 722,
      "line": "self.metrics.cached_tokens += cached"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 883,
      "line": "logger.info(f\"Cached Tokens: {metrics.cached_tokens}\")"
    }
  ],
  "files_searched": 1,
  "match_count": 34,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 4 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 3,297 | 256 | 3,041 | 7.8% | 1,424 | 43.143s | system → user → assistant → tool → assistant → tool → assistant → tool → user | read_file → find → grep |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。
```

**消息 2 · 用户（`user`）**

```text
[用户资料：高级用户，剩余 96 点额度]
```

**消息 3 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "find_0",
    "function": {
      "arguments": "{\"pattern\":\"*.py\",\"directory\":\"chapter2/kv-cache\"}",
      "name": "find"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 4 · 工具（`tool`）**

```text
{"pattern": "*.py", "directory": "chapter2/kv-cache", "matches": ["chapter2/kv-cache/agent.py", "chapter2/kv-cache/main.py", "chapter2/kv-cache/tests/conftest.py", "chapter2/kv-cache/tests/manual/_bootstrap.py", "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py", "chapter2/kv-cache/tests/manual/check_cache_invalidation.py", "chapter2/kv-cache/tests/manual/check_cached_tokens.py", "chapter2/kv-cache/tests/manual/check_completion.py", "chapter2/kv-cache/tests/manual/check_tool_calling.py", "chapter2/kv-cache/tests/manual/check_ttft.py", "chapter2/kv-cache/tests/manual/demo_quick.py", "chapter2/kv-cache/tests/test_error_handling.py", "chapter2/kv-cache/tests/test_file_range.py", "chapter2/kv-cache/tests/test_interactive.py", "chapter2/kv-cache/tests/test_message_flow.py", "chapter2/kv-cache/tests/test_negative_size.py", "chapter2/kv-cache/tests/test_tools.py"], "count": 17, "truncated": false, "success": true}
```

**消息 5 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "read_file_1",
    "function": {
      "arguments": "{\"file_path\":\"chapter2/kv-cache/main.py\",\"offset\":0,\"size\":80}",
      "name": "read_file"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 6 · 工具（`tool`）**

```text
{"path": "chapter2/kv-cache/main.py", "content": "\"\"\"\nMain script to demonstrate KV cache importance\nRuns the ReAct agent with different implementations and compares performance\n\"\"\"\n\nimport os\nimport sys\nimport glob\nimport json\nimport argparse\nimport logging\nfrom typing import Dict, List, Any\nfrom datetime import datetime\nfrom dataclasses import asdict\n\ntry:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n\nfrom agent import KVCacheAgent, KVCacheMode, AgentMetrics, compare_implementations\n\n# Default model (Moonshot / Kimi). The whole current Kimi family (k2.5/k2.6/\n# k2.7/k3) reports cached_tokens for automatic prefix caching AND reasons, so it\n# only accepts temperature=1 (agent.py handles that automatically). kimi-k2.6 has\n# the lightest reasoning footprint of the cache-reporting models, giving the\n# cleanest TTFT while still exposing the prefix-cache hit metric this demo needs.\n# (The non-reasoning moonshot-v1-* models do NOT report cached_tokens, so they\n# cannot demonstrate the cache effect.)\nDEFAULT_MODEL = \"kimi-k2.6\"\nDEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), \"../..\"))\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format='%(asctime)s - %(levelname)s - %(message)s',\n    handlers=[\n        logging.FileHandler('kv_cache_demo.log'),\n        logging.StreamHandler()\n    ]\n)\nlogger = logging.getLogger(__name__)\n\n\n# ---------------------------------------------------------------------------\n# Metrics helpers (shared by live comparison and offline report)\n# ---------------------------------------------------------------------------\n\ndef _coerce_metrics(metrics: Any) -> Dict[str, Any]:\n    \"\"\"Normalize a stored metrics value into a plain dict.\n\n    Handles both formats found in result files:\n      - dict: produced by --compare (asdict) and by the fixed --mode path\n      - str : legacy single-mode files that stored repr(AgentMetrics(...))\n              because json.dump used default=str\n    \"\"\"\n    if isinstance(metrics, dict):\n        return metrics\n    if isinstance(metrics, str) and metrics.startswith(\"AgentMetrics(\"):\n        # Safe eval: only AgentMetrics is exposed, no builtins.\n        try:\n            obj = eval(metrics, {\"__builtins__\": {}}, {\"AgentMetrics\": AgentMetrics})\n            return asdict(obj)\n        except Exception as e:  # pragma: no cover - defensive\n            logger.warning(f\"Could not parse legacy metrics string: {e}\")\n    return {}\n\n\ndef _avg_ttft(m: Dict[str, Any]) -> float:\n    \"\"\"Average TTFT across iterations, falling back to first-iteration TTFT.\"\"\"\n    lst = m.get(\"ttft_per_iteration\") or []\n    return sum(lst) / len(lst) if lst else float(m.get(\"ttft\", 0.0) or 0.0)\n\n\ndef _hit_rate(m: Dict[str, Any]) -> float:\n    total = (m.get(\"cache_hits\", 0) or 0) + (m.get(\"cache_misses\", 0) or 0)\n    return (m.get(\"cache_hits\", 0) or 0) / total * 100 if total else 0.0\n\n\n", "total_lines": 548, "lines_read": 80, "offset": 0, "end_line": 80, "truncated": false, "success": true}
```

**消息 7 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "grep_2",
    "function": {
      "arguments": "{\"pattern\":\"class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens\",\"file_path\":\"chapter2/kv-cache/agent.py\"}",
      "name": "grep"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 8 · 工具（`tool`）**

```text
{"pattern": "class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens", "matches": [{"file": "chapter2/kv-cache/agent.py", "line_num": 3, "line": "Demonstrates the importance of KV cache through correct and incorrect implementations."}, {"file": "chapter2/kv-cache/agent.py", "line_num": 33, "line": "chat models do NOT reason (and also do not report cached_tokens).\"\"\""}, {"file": "chapter2/kv-cache/agent.py", "line_num": 59, "line": "class KVCacheMode(Enum):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 61, "line": "CORRECT = \"correct\"  # Correct implementation with stable context"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 62, "line": "DYNAMIC_SYSTEM = \"dynamic_system\"  # Changing system prompt with timestamp"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 63, "line": "SHUFFLED_TOOLS = \"shuffled_tools\"  # Shuffling tool order each request"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 64, "line": "DYNAMIC_PROFILE = \"dynamic_profile\"  # Changing user profile with credits"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 65, "line": "SLIDING_WINDOW = \"sliding_window\"  # Only keeping recent 6 messages"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 66, "line": "TEXT_FORMAT = \"text_format\"  # Formatting messages as plain text"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 91, "line": "cached_tokens: int = 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 357, "line": "def __init__(self, api_key: str, mode: KVCacheMode = KVCacheMode.CORRECT,"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 486, "line": "if self.mode == KVCacheMode.DYNAMIC_SYSTEM:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 497, "line": "if self.mode == KVCacheMode.SHUFFLED_TOOLS:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 505, "line": "if self.mode == KVCacheMode.DYNAMIC_PROFILE:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 514, "line": "\"\"\"Format messages based on mode - recreated each iteration for incorrect modes\"\"\""}, {"file": "chapter2/kv-cache/agent.py", "line_num": 517, "line": "# Add system prompt (changes each time for DYNAMIC_SYSTEM mode)"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 528, "line": "if self.mode == KVCacheMode.SLIDING_WINDOW:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 540, "line": "elif self.mode == KVCacheMode.TEXT_FORMAT:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 575, "line": "# For CORRECT, DYNAMIC_SYSTEM, SHUFFLED_TOOLS, DYNAMIC_PROFILE modes"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 646, "line": "# CORRECT mode: Build messages once on first iteration, then keep appending"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 649, "line": "# INCORRECT modes: Recreate entire messages list from history each iteration"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 654, "line": "if self.mode == KVCacheMode.CORRECT:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 655, "line": "# Correct mode: Build messages once, then keep using same list"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 659, "line": "# Incorrect modes: Recreate messages from history each iteration"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 671, "line": "# Add tools for all modes (TEXT_FORMAT still needs tools to work)"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 672, "line": "# TEXT_FORMAT only affects how conversation history is formatted, not tool availability"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 706, "line": "# The cached_tokens field appears directly in the usage object"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 708, "line": "if hasattr(usage, 'cached_tokens'):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 710, "line": "cached = usage.cached_tokens if usage.cached_tokens is not None else 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 711, "line": "self.metrics.cached_tokens += cached"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 720, "line": "if details and hasattr(details, 'cached_tokens'):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 721, "line": "cached = details.cached_tokens if details.cached_tokens is not None else 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 722, "line": "self.metrics.cached_tokens += cached"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 883, "line": "logger.info(f\"Cached Tokens: {metrics.cached_tokens}\")"}], "files_searched": 1, "match_count": 34, "truncated": false, "success": true}
```

**消息 9 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

</details>

**模型本轮回复**

```text
## 实验总结（对照实验编号：KV缓存对照-20260808-192341）

### 1. 实验目的
根据 `main.py` 的注释与代码，本实验旨在**演示 KV Cache（键值缓存）的重要性**。它通过运行同一个 ReAct Agent 的**正确实现**与多种**错误实现**，对比不同上下文构造方式对模型推理性能的影响。核心思想是：当请求的前缀上下文保持稳定时，模型可以复用已计算的 KV Cache，从而减少重复计算、降低延迟。

### 2. 六种模式（来自 `agent.py` 的 `KVCacheMode` 枚举）
代码中精确定义了 6 种对照模式：

| 模式 | 代码定义 | 含义 |
|------|----------|------|
| **CORRECT** | `"correct"` | **正确实现**：保持上下文稳定，消息列表在首次迭代构建后持续追加，不改动前缀。 |
| **DYNAMIC_SYSTEM** | `"dynamic_system"` | **动态系统提示**：每次请求都在系统提示中注入时间戳等动态内容，导致前缀不断变化。 |
| **SHUFFLED_TOOLS** | `"shuffled_tools"` | **工具乱序**：每次请求打乱工具（functions）的定义顺序，破坏前缀一致性。 |
| **DYNAMIC_PROFILE** | `"dynamic_profile"` | **动态用户资料**：每次请求更新用户资料（如积分变化），使前缀内容发生变化。 |
| **SLIDING_WINDOW** | `"sliding_window"` | **滑动窗口**：只保留最近的 6 条消息，导致历史上下文被截断、前缀频繁变动。 |
| **TEXT_FORMAT** | `"text_format"` | **纯文本格式**：将对话历史格式化为纯文本字符串，而非结构化的消息对象，改变输入表示。 |

从 `agent.py` 的代码逻辑可见，`CORRECT` 模式的消息是**“Build once, then keep appending”**（一次构建，持续追加），而其余 5 种错误模式都是**“Recreate entire messages list from history each iteration”**（每次迭代从历史记录重新创建整个消息列表），这正是 KV Cache 失效的根本原因。

### 3. 最值得比较的指标
综合 `main.py` 的指标辅助函数与 `agent.py` 的指标采集逻辑，最值得关注的指标有三项：

- **`cached_tokens`（缓存 Token 数）**：直接来自 API 返回的 `usage.cached_tokens`，是**衡量 KV Cache 命中效果的最直接证据**。`CORRECT` 模式下该值应显著高于错误模式。
- **`ttft` / `ttft_per_iteration`（首 Token 时间）**：`main.py` 专门计算了平均 TTFT。KV Cache 命中越高，模型复用前缀计算结果，首 token 返回的延迟越低。
- **`cache_hits` / `cache_misses`（缓存命中/未命中）**：用于计算缓存命中率（hit rate），从宏观上验证缓存策略的有效性。

### 结论
本实验通过**一个正确基准（CORRECT）与五个错误变体**的对照，以 **`cached_tokens`** 为核心指标、以 **`ttft`** 为性能指标，直观证明了：**保持对话前缀的绝对稳定是触发 KV Cache、降低推理延迟的关键**。任何对系统提示、工具顺序、用户资料或消息格式的“微小”动态修改，都会导致前缀缓存失效，从而丧失 KV Cache 带来的性能收益。
```

**该模式最终回答**

```text
## 实验总结（对照实验编号：KV缓存对照-20260808-192341）

### 1. 实验目的
根据 `main.py` 的注释与代码，本实验旨在**演示 KV Cache（键值缓存）的重要性**。它通过运行同一个 ReAct Agent 的**正确实现**与多种**错误实现**，对比不同上下文构造方式对模型推理性能的影响。核心思想是：当请求的前缀上下文保持稳定时，模型可以复用已计算的 KV Cache，从而减少重复计算、降低延迟。

### 2. 六种模式（来自 `agent.py` 的 `KVCacheMode` 枚举）
代码中精确定义了 6 种对照模式：

| 模式 | 代码定义 | 含义 |
|------|----------|------|
| **CORRECT** | `"correct"` | **正确实现**：保持上下文稳定，消息列表在首次迭代构建后持续追加，不改动前缀。 |
| **DYNAMIC_SYSTEM** | `"dynamic_system"` | **动态系统提示**：每次请求都在系统提示中注入时间戳等动态内容，导致前缀不断变化。 |
| **SHUFFLED_TOOLS** | `"shuffled_tools"` | **工具乱序**：每次请求打乱工具（functions）的定义顺序，破坏前缀一致性。 |
| **DYNAMIC_PROFILE** | `"dynamic_profile"` | **动态用户资料**：每次请求更新用户资料（如积分变化），使前缀内容发生变化。 |
| **SLIDING_WINDOW** | `"sliding_window"` | **滑动窗口**：只保留最近的 6 条消息，导致历史上下文被截断、前缀频繁变动。 |
| **TEXT_FORMAT** | `"text_format"` | **纯文本格式**：将对话历史格式化为纯文本字符串，而非结构化的消息对象，改变输入表示。 |

从 `agent.py` 的代码逻辑可见，`CORRECT` 模式的消息是**“Build once, then keep appending”**（一次构建，持续追加），而其余 5 种错误模式都是**“Recreate entire messages list from history each iteration”**（每次迭代从历史记录重新创建整个消息列表），这正是 KV Cache 失效的根本原因。

### 3. 最值得比较的指标
综合 `main.py` 的指标辅助函数与 `agent.py` 的指标采集逻辑，最值得关注的指标有三项：

- **`cached_tokens`（缓存 Token 数）**：直接来自 API 返回的 `usage.cached_tokens`，是**衡量 KV Cache 命中效果的最直接证据**。`CORRECT` 模式下该值应显著高于错误模式。
- **`ttft` / `ttft_per_iteration`（首 Token 时间）**：`main.py` 专门计算了平均 TTFT。KV Cache 命中越高，模型复用前缀计算结果，首 token 返回的延迟越低。
- **`cache_hits` / `cache_misses`（缓存命中/未命中）**：用于计算缓存命中率（hit rate），从宏观上验证缓存策略的有效性。

### 结论
本实验通过**一个正确基准（CORRECT）与五个错误变体**的对照，以 **`cached_tokens`** 为核心指标、以 **`ttft`** 为性能指标，直观证明了：**保持对话前缀的绝对稳定是触发 KV Cache、降低推理延迟的关键**。任何对系统提示、工具顺序、用户资料或消息格式的“微小”动态修改，都会导致前缀缓存失效，从而丧失 KV Cache 带来的性能收益。
```

### sliding_window · 滑动窗口

机制：每轮只保留最近约六条历史消息。

结果：`success=True`，API 4 轮，工具调用 3 次，累计 Cache% 37.9%。

#### 第 1 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 603 | 256 | 347 | 42.5% | 76 | 4.571s | system → user | read_file → find → grep |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。
```

**消息 2 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

</details>

**模型本轮回复**

工具调用 1：`find`

参数：

```json
{"pattern": "*.py", "directory": "chapter2/kv-cache"}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "pattern": "*.py",
  "directory": "chapter2/kv-cache",
  "matches": [
    "chapter2/kv-cache/agent.py",
    "chapter2/kv-cache/main.py",
    "chapter2/kv-cache/tests/conftest.py",
    "chapter2/kv-cache/tests/manual/_bootstrap.py",
    "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py",
    "chapter2/kv-cache/tests/manual/check_cache_invalidation.py",
    "chapter2/kv-cache/tests/manual/check_cached_tokens.py",
    "chapter2/kv-cache/tests/manual/check_completion.py",
    "chapter2/kv-cache/tests/manual/check_tool_calling.py",
    "chapter2/kv-cache/tests/manual/check_ttft.py",
    "chapter2/kv-cache/tests/manual/demo_quick.py",
    "chapter2/kv-cache/tests/test_error_handling.py",
    "chapter2/kv-cache/tests/test_file_range.py",
    "chapter2/kv-cache/tests/test_interactive.py",
    "chapter2/kv-cache/tests/test_message_flow.py",
    "chapter2/kv-cache/tests/test_negative_size.py",
    "chapter2/kv-cache/tests/test_tools.py"
  ],
  "count": 17,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 2 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 936 | 256 | 680 | 27.4% | 84 | 2.972s | system → assistant → tool → user | read_file → find → grep |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。
```

**消息 2 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "find_0",
    "function": {
      "arguments": "{\"pattern\": \"*.py\", \"directory\": \"chapter2/kv-cache\"}",
      "name": "find"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 3 · 工具（`tool`）**

```text
{"pattern": "*.py", "directory": "chapter2/kv-cache", "matches": ["chapter2/kv-cache/agent.py", "chapter2/kv-cache/main.py", "chapter2/kv-cache/tests/conftest.py", "chapter2/kv-cache/tests/manual/_bootstrap.py", "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py", "chapter2/kv-cache/tests/manual/check_cache_invalidation.py", "chapter2/kv-cache/tests/manual/check_cached_tokens.py", "chapter2/kv-cache/tests/manual/check_completion.py", "chapter2/kv-cache/tests/manual/check_tool_calling.py", "chapter2/kv-cache/tests/manual/check_ttft.py", "chapter2/kv-cache/tests/manual/demo_quick.py", "chapter2/kv-cache/tests/test_error_handling.py", "chapter2/kv-cache/tests/test_file_range.py", "chapter2/kv-cache/tests/test_interactive.py", "chapter2/kv-cache/tests/test_message_flow.py", "chapter2/kv-cache/tests/test_negative_size.py", "chapter2/kv-cache/tests/test_tools.py"], "count": 17, "truncated": false, "success": true}
```

**消息 4 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

</details>

**模型本轮回复**

工具调用 1：`read_file`

参数：

```json
{"file_path": "chapter2/kv-cache/main.py", "offset": 0, "size": 80}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "path": "chapter2/kv-cache/main.py",
  "content": "\"\"\"\nMain script to demonstrate KV cache importance\nRuns the ReAct agent with different implementations and compares performance\n\"\"\"\n\nimport os\nimport sys\nimport glob\nimport json\nimport argparse\nimport logging\nfrom typing import Dict, List, Any\nfrom datetime import datetime\nfrom dataclasses import asdict\n\ntry:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n\nfrom agent import KVCacheAgent, KVCacheMode, AgentMetrics, compare_implementations\n\n# Default model (Moonshot / Kimi). The whole current Kimi family (k2.5/k2.6/\n# k2.7/k3) reports cached_tokens for automatic prefix caching AND reasons, so it\n# only accepts temperature=1 (agent.py handles that automatically). kimi-k2.6 has\n# the lightest reasoning footprint of the cache-reporting models, giving the\n# cleanest TTFT while still exposing the prefix-cache hit metric this demo needs.\n# (The non-reasoning moonshot-v1-* models do NOT report cached_tokens, so they\n# cannot demonstrate the cache effect.)\nDEFAULT_MODEL = \"kimi-k2.6\"\nDEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), \"../..\"))\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format='%(asctime)s - %(levelname)s - %(message)s',\n    handlers=[\n        logging.FileHandler('kv_cache_demo.log'),\n        logging.StreamHandler()\n    ]\n)\nlogger = logging.getLogger(__name__)\n\n\n# ---------------------------------------------------------------------------\n# Metrics helpers (shared by live comparison and offline report)\n# ---------------------------------------------------------------------------\n\ndef _coerce_metrics(metrics: Any) -> Dict[str, Any]:\n    \"\"\"Normalize a stored metrics value into a plain dict.\n\n    Handles both formats found in result files:\n      - dict: produced by --compare (asdict) and by the fixed --mode path\n      - str : legacy single-mode files that stored repr(AgentMetrics(...))\n              because json.dump used default=str\n    \"\"\"\n    if isinstance(metrics, dict):\n        return metrics\n    if isinstance(metrics, str) and metrics.startswith(\"AgentMetrics(\"):\n        # Safe eval: only AgentMetrics is exposed, no builtins.\n        try:\n            obj = eval(metrics, {\"__builtins__\": {}}, {\"AgentMetrics\": AgentMetrics})\n            return asdict(obj)\n        except Exception as e:  # pragma: no cover - defensive\n            logger.warning(f\"Could not parse legacy metrics string: {e}\")\n    return {}\n\n\ndef _avg_ttft(m: Dict[str, Any]) -> float:\n    \"\"\"Average TTFT across iterations, falling back to first-iteration TTFT.\"\"\"\n    lst = m.get(\"ttft_per_iteration\") or []\n    return sum(lst) / len(lst) if lst else float(m.get(\"ttft\", 0.0) or 0.0)\n\n\ndef _hit_rate(m: Dict[str, Any]) -> float:\n    total = (m.get(\"cache_hits\", 0) or 0) + (m.get(\"cache_misses\", 0) or 0)\n    return (m.get(\"cache_hits\", 0) or 0) / total * 100 if total else 0.0\n\n\n",
  "total_lines": 548,
  "lines_read": 80,
  "offset": 0,
  "end_line": 80,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 3 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1,846 | 512 | 1,334 | 27.7% | 185 | 6.297s | system → assistant → tool → assistant → tool → user | read_file → find → grep |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。
```

**消息 2 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "find_0",
    "function": {
      "arguments": "{\"pattern\": \"*.py\", \"directory\": \"chapter2/kv-cache\"}",
      "name": "find"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 3 · 工具（`tool`）**

```text
{"pattern": "*.py", "directory": "chapter2/kv-cache", "matches": ["chapter2/kv-cache/agent.py", "chapter2/kv-cache/main.py", "chapter2/kv-cache/tests/conftest.py", "chapter2/kv-cache/tests/manual/_bootstrap.py", "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py", "chapter2/kv-cache/tests/manual/check_cache_invalidation.py", "chapter2/kv-cache/tests/manual/check_cached_tokens.py", "chapter2/kv-cache/tests/manual/check_completion.py", "chapter2/kv-cache/tests/manual/check_tool_calling.py", "chapter2/kv-cache/tests/manual/check_ttft.py", "chapter2/kv-cache/tests/manual/demo_quick.py", "chapter2/kv-cache/tests/test_error_handling.py", "chapter2/kv-cache/tests/test_file_range.py", "chapter2/kv-cache/tests/test_interactive.py", "chapter2/kv-cache/tests/test_message_flow.py", "chapter2/kv-cache/tests/test_negative_size.py", "chapter2/kv-cache/tests/test_tools.py"], "count": 17, "truncated": false, "success": true}
```

**消息 4 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "read_file_1",
    "function": {
      "arguments": "{\"file_path\": \"chapter2/kv-cache/main.py\", \"offset\": 0, \"size\": 80}",
      "name": "read_file"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 5 · 工具（`tool`）**

```text
{"path": "chapter2/kv-cache/main.py", "content": "\"\"\"\nMain script to demonstrate KV cache importance\nRuns the ReAct agent with different implementations and compares performance\n\"\"\"\n\nimport os\nimport sys\nimport glob\nimport json\nimport argparse\nimport logging\nfrom typing import Dict, List, Any\nfrom datetime import datetime\nfrom dataclasses import asdict\n\ntry:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n\nfrom agent import KVCacheAgent, KVCacheMode, AgentMetrics, compare_implementations\n\n# Default model (Moonshot / Kimi). The whole current Kimi family (k2.5/k2.6/\n# k2.7/k3) reports cached_tokens for automatic prefix caching AND reasons, so it\n# only accepts temperature=1 (agent.py handles that automatically). kimi-k2.6 has\n# the lightest reasoning footprint of the cache-reporting models, giving the\n# cleanest TTFT while still exposing the prefix-cache hit metric this demo needs.\n# (The non-reasoning moonshot-v1-* models do NOT report cached_tokens, so they\n# cannot demonstrate the cache effect.)\nDEFAULT_MODEL = \"kimi-k2.6\"\nDEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), \"../..\"))\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format='%(asctime)s - %(levelname)s - %(message)s',\n    handlers=[\n        logging.FileHandler('kv_cache_demo.log'),\n        logging.StreamHandler()\n    ]\n)\nlogger = logging.getLogger(__name__)\n\n\n# ---------------------------------------------------------------------------\n# Metrics helpers (shared by live comparison and offline report)\n# ---------------------------------------------------------------------------\n\ndef _coerce_metrics(metrics: Any) -> Dict[str, Any]:\n    \"\"\"Normalize a stored metrics value into a plain dict.\n\n    Handles both formats found in result files:\n      - dict: produced by --compare (asdict) and by the fixed --mode path\n      - str : legacy single-mode files that stored repr(AgentMetrics(...))\n              because json.dump used default=str\n    \"\"\"\n    if isinstance(metrics, dict):\n        return metrics\n    if isinstance(metrics, str) and metrics.startswith(\"AgentMetrics(\"):\n        # Safe eval: only AgentMetrics is exposed, no builtins.\n        try:\n            obj = eval(metrics, {\"__builtins__\": {}}, {\"AgentMetrics\": AgentMetrics})\n            return asdict(obj)\n        except Exception as e:  # pragma: no cover - defensive\n            logger.warning(f\"Could not parse legacy metrics string: {e}\")\n    return {}\n\n\ndef _avg_ttft(m: Dict[str, Any]) -> float:\n    \"\"\"Average TTFT across iterations, falling back to first-iteration TTFT.\"\"\"\n    lst = m.get(\"ttft_per_iteration\") or []\n    return sum(lst) / len(lst) if lst else float(m.get(\"ttft\", 0.0) or 0.0)\n\n\ndef _hit_rate(m: Dict[str, Any]) -> float:\n    total = (m.get(\"cache_hits\", 0) or 0) + (m.get(\"cache_misses\", 0) or 0)\n    return (m.get(\"cache_hits\", 0) or 0) / total * 100 if total else 0.0\n\n\n", "total_lines": 548, "lines_read": 80, "offset": 0, "end_line": 80, "truncated": false, "success": true}
```

**消息 6 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

</details>

**模型本轮回复**

工具调用 1：`grep`

参数：

```json
{"pattern": "class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens", "file_path": "chapter2/kv-cache/agent.py"}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "pattern": "class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens",
  "matches": [
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 3,
      "line": "Demonstrates the importance of KV cache through correct and incorrect implementations."
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 33,
      "line": "chat models do NOT reason (and also do not report cached_tokens).\"\"\""
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 59,
      "line": "class KVCacheMode(Enum):"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 61,
      "line": "CORRECT = \"correct\"  # Correct implementation with stable context"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 62,
      "line": "DYNAMIC_SYSTEM = \"dynamic_system\"  # Changing system prompt with timestamp"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 63,
      "line": "SHUFFLED_TOOLS = \"shuffled_tools\"  # Shuffling tool order each request"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 64,
      "line": "DYNAMIC_PROFILE = \"dynamic_profile\"  # Changing user profile with credits"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 65,
      "line": "SLIDING_WINDOW = \"sliding_window\"  # Only keeping recent 6 messages"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 66,
      "line": "TEXT_FORMAT = \"text_format\"  # Formatting messages as plain text"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 91,
      "line": "cached_tokens: int = 0"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 357,
      "line": "def __init__(self, api_key: str, mode: KVCacheMode = KVCacheMode.CORRECT,"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 486,
      "line": "if self.mode == KVCacheMode.DYNAMIC_SYSTEM:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 497,
      "line": "if self.mode == KVCacheMode.SHUFFLED_TOOLS:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 505,
      "line": "if self.mode == KVCacheMode.DYNAMIC_PROFILE:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 514,
      "line": "\"\"\"Format messages based on mode - recreated each iteration for incorrect modes\"\"\""
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 517,
      "line": "# Add system prompt (changes each time for DYNAMIC_SYSTEM mode)"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 528,
      "line": "if self.mode == KVCacheMode.SLIDING_WINDOW:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 540,
      "line": "elif self.mode == KVCacheMode.TEXT_FORMAT:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 575,
      "line": "# For CORRECT, DYNAMIC_SYSTEM, SHUFFLED_TOOLS, DYNAMIC_PROFILE modes"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 646,
      "line": "# CORRECT mode: Build messages once on first iteration, then keep appending"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 649,
      "line": "# INCORRECT modes: Recreate entire messages list from history each iteration"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 654,
      "line": "if self.mode == KVCacheMode.CORRECT:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 655,
      "line": "# Correct mode: Build messages once, then keep using same list"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 659,
      "line": "# Incorrect modes: Recreate messages from history each iteration"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 671,
      "line": "# Add tools for all modes (TEXT_FORMAT still needs tools to work)"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 672,
      "line": "# TEXT_FORMAT only affects how conversation history is formatted, not tool availability"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 706,
      "line": "# The cached_tokens field appears directly in the usage object"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 708,
      "line": "if hasattr(usage, 'cached_tokens'):"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 710,
      "line": "cached = usage.cached_tokens if usage.cached_tokens is not None else 0"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 711,
      "line": "self.metrics.cached_tokens += cached"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 720,
      "line": "if details and hasattr(details, 'cached_tokens'):"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 721,
      "line": "cached = details.cached_tokens if details.cached_tokens is not None else 0"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 722,
      "line": "self.metrics.cached_tokens += cached"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 883,
      "line": "logger.info(f\"Cached Tokens: {metrics.cached_tokens}\")"
    }
  ],
  "files_searched": 1,
  "match_count": 34,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 4 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 3,370 | 1,536 | 1,834 | 45.6% | 1,591 | 49.105s | system → assistant → tool → assistant → tool → assistant → tool → user | read_file → find → grep |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。
```

**消息 2 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "find_0",
    "function": {
      "arguments": "{\"pattern\": \"*.py\", \"directory\": \"chapter2/kv-cache\"}",
      "name": "find"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 3 · 工具（`tool`）**

```text
{"pattern": "*.py", "directory": "chapter2/kv-cache", "matches": ["chapter2/kv-cache/agent.py", "chapter2/kv-cache/main.py", "chapter2/kv-cache/tests/conftest.py", "chapter2/kv-cache/tests/manual/_bootstrap.py", "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py", "chapter2/kv-cache/tests/manual/check_cache_invalidation.py", "chapter2/kv-cache/tests/manual/check_cached_tokens.py", "chapter2/kv-cache/tests/manual/check_completion.py", "chapter2/kv-cache/tests/manual/check_tool_calling.py", "chapter2/kv-cache/tests/manual/check_ttft.py", "chapter2/kv-cache/tests/manual/demo_quick.py", "chapter2/kv-cache/tests/test_error_handling.py", "chapter2/kv-cache/tests/test_file_range.py", "chapter2/kv-cache/tests/test_interactive.py", "chapter2/kv-cache/tests/test_message_flow.py", "chapter2/kv-cache/tests/test_negative_size.py", "chapter2/kv-cache/tests/test_tools.py"], "count": 17, "truncated": false, "success": true}
```

**消息 4 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "read_file_1",
    "function": {
      "arguments": "{\"file_path\": \"chapter2/kv-cache/main.py\", \"offset\": 0, \"size\": 80}",
      "name": "read_file"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 5 · 工具（`tool`）**

```text
{"path": "chapter2/kv-cache/main.py", "content": "\"\"\"\nMain script to demonstrate KV cache importance\nRuns the ReAct agent with different implementations and compares performance\n\"\"\"\n\nimport os\nimport sys\nimport glob\nimport json\nimport argparse\nimport logging\nfrom typing import Dict, List, Any\nfrom datetime import datetime\nfrom dataclasses import asdict\n\ntry:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n\nfrom agent import KVCacheAgent, KVCacheMode, AgentMetrics, compare_implementations\n\n# Default model (Moonshot / Kimi). The whole current Kimi family (k2.5/k2.6/\n# k2.7/k3) reports cached_tokens for automatic prefix caching AND reasons, so it\n# only accepts temperature=1 (agent.py handles that automatically). kimi-k2.6 has\n# the lightest reasoning footprint of the cache-reporting models, giving the\n# cleanest TTFT while still exposing the prefix-cache hit metric this demo needs.\n# (The non-reasoning moonshot-v1-* models do NOT report cached_tokens, so they\n# cannot demonstrate the cache effect.)\nDEFAULT_MODEL = \"kimi-k2.6\"\nDEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), \"../..\"))\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format='%(asctime)s - %(levelname)s - %(message)s',\n    handlers=[\n        logging.FileHandler('kv_cache_demo.log'),\n        logging.StreamHandler()\n    ]\n)\nlogger = logging.getLogger(__name__)\n\n\n# ---------------------------------------------------------------------------\n# Metrics helpers (shared by live comparison and offline report)\n# ---------------------------------------------------------------------------\n\ndef _coerce_metrics(metrics: Any) -> Dict[str, Any]:\n    \"\"\"Normalize a stored metrics value into a plain dict.\n\n    Handles both formats found in result files:\n      - dict: produced by --compare (asdict) and by the fixed --mode path\n      - str : legacy single-mode files that stored repr(AgentMetrics(...))\n              because json.dump used default=str\n    \"\"\"\n    if isinstance(metrics, dict):\n        return metrics\n    if isinstance(metrics, str) and metrics.startswith(\"AgentMetrics(\"):\n        # Safe eval: only AgentMetrics is exposed, no builtins.\n        try:\n            obj = eval(metrics, {\"__builtins__\": {}}, {\"AgentMetrics\": AgentMetrics})\n            return asdict(obj)\n        except Exception as e:  # pragma: no cover - defensive\n            logger.warning(f\"Could not parse legacy metrics string: {e}\")\n    return {}\n\n\ndef _avg_ttft(m: Dict[str, Any]) -> float:\n    \"\"\"Average TTFT across iterations, falling back to first-iteration TTFT.\"\"\"\n    lst = m.get(\"ttft_per_iteration\") or []\n    return sum(lst) / len(lst) if lst else float(m.get(\"ttft\", 0.0) or 0.0)\n\n\ndef _hit_rate(m: Dict[str, Any]) -> float:\n    total = (m.get(\"cache_hits\", 0) or 0) + (m.get(\"cache_misses\", 0) or 0)\n    return (m.get(\"cache_hits\", 0) or 0) / total * 100 if total else 0.0\n\n\n", "total_lines": 548, "lines_read": 80, "offset": 0, "end_line": 80, "truncated": false, "success": true}
```

**消息 6 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "grep_2",
    "function": {
      "arguments": "{\"pattern\": \"class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens\", \"file_path\": \"chapter2/kv-cache/agent.py\"}",
      "name": "grep"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 7 · 工具（`tool`）**

```text
{"pattern": "class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens", "matches": [{"file": "chapter2/kv-cache/agent.py", "line_num": 3, "line": "Demonstrates the importance of KV cache through correct and incorrect implementations."}, {"file": "chapter2/kv-cache/agent.py", "line_num": 33, "line": "chat models do NOT reason (and also do not report cached_tokens).\"\"\""}, {"file": "chapter2/kv-cache/agent.py", "line_num": 59, "line": "class KVCacheMode(Enum):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 61, "line": "CORRECT = \"correct\"  # Correct implementation with stable context"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 62, "line": "DYNAMIC_SYSTEM = \"dynamic_system\"  # Changing system prompt with timestamp"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 63, "line": "SHUFFLED_TOOLS = \"shuffled_tools\"  # Shuffling tool order each request"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 64, "line": "DYNAMIC_PROFILE = \"dynamic_profile\"  # Changing user profile with credits"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 65, "line": "SLIDING_WINDOW = \"sliding_window\"  # Only keeping recent 6 messages"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 66, "line": "TEXT_FORMAT = \"text_format\"  # Formatting messages as plain text"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 91, "line": "cached_tokens: int = 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 357, "line": "def __init__(self, api_key: str, mode: KVCacheMode = KVCacheMode.CORRECT,"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 486, "line": "if self.mode == KVCacheMode.DYNAMIC_SYSTEM:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 497, "line": "if self.mode == KVCacheMode.SHUFFLED_TOOLS:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 505, "line": "if self.mode == KVCacheMode.DYNAMIC_PROFILE:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 514, "line": "\"\"\"Format messages based on mode - recreated each iteration for incorrect modes\"\"\""}, {"file": "chapter2/kv-cache/agent.py", "line_num": 517, "line": "# Add system prompt (changes each time for DYNAMIC_SYSTEM mode)"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 528, "line": "if self.mode == KVCacheMode.SLIDING_WINDOW:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 540, "line": "elif self.mode == KVCacheMode.TEXT_FORMAT:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 575, "line": "# For CORRECT, DYNAMIC_SYSTEM, SHUFFLED_TOOLS, DYNAMIC_PROFILE modes"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 646, "line": "# CORRECT mode: Build messages once on first iteration, then keep appending"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 649, "line": "# INCORRECT modes: Recreate entire messages list from history each iteration"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 654, "line": "if self.mode == KVCacheMode.CORRECT:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 655, "line": "# Correct mode: Build messages once, then keep using same list"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 659, "line": "# Incorrect modes: Recreate messages from history each iteration"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 671, "line": "# Add tools for all modes (TEXT_FORMAT still needs tools to work)"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 672, "line": "# TEXT_FORMAT only affects how conversation history is formatted, not tool availability"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 706, "line": "# The cached_tokens field appears directly in the usage object"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 708, "line": "if hasattr(usage, 'cached_tokens'):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 710, "line": "cached = usage.cached_tokens if usage.cached_tokens is not None else 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 711, "line": "self.metrics.cached_tokens += cached"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 720, "line": "if details and hasattr(details, 'cached_tokens'):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 721, "line": "cached = details.cached_tokens if details.cached_tokens is not None else 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 722, "line": "self.metrics.cached_tokens += cached"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 883, "line": "logger.info(f\"Cached Tokens: {metrics.cached_tokens}\")"}], "files_searched": 1, "match_count": 34, "truncated": false, "success": true}
```

**消息 8 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

</details>

**模型本轮回复**

```text
根据前三步工具返回的结果，现对本次 **KV 缓存对照实验（编号：KV缓存对照-20260808-192341）** 总结如下：

---

### 一、实验目的
该实验通过运行同一个 **ReAct Agent**，分别采用 6 种不同的上下文构造策略，来**演示和量化 KV Cache（自动前缀缓存）的重要性**。  
项目默认选用 **Moonshot / Kimi 的 `kimi-k2.6` 模型**作为被测对象，原因是该模型族会返回 `cached_tokens` 指标，能够直观暴露“前缀缓存命中 vs. 未命中”的差异；而不返回该指标的非推理模型则无法完成此演示。

---

### 二、六种模式（定义于 `agent.py` 的 `KVCacheMode`）
| 模式 | 含义 | 对 KV Cache 的影响 |
|------|------|-------------------|
| **CORRECT** | 正确实现：首次构建消息列表后持续复用，稳定追加 | ✅ 利于前缀缓存命中 |
| **DYNAMIC_SYSTEM** | 每次请求动态修改系统提示（如附加时间戳） | ❌ 破坏缓存 |
| **SHUFFLED_TOOLS** | 每次请求打乱工具（Tools）的顺序 | ❌ 破坏缓存 |
| **DYNAMIC_PROFILE** | 动态变更用户资料（如积分信息） | ❌ 破坏缓存 |
| **SLIDING_WINDOW** | 仅保留最近 6 条消息，丢弃早期上下文 | ❌ 缓存窗口不稳定 |
| **TEXT_FORMAT** | 将对话历史重新格式化为纯文本发送 | ❌ 改变序列结构，不利于缓存 |

核心实现差异：`CORRECT` 模式在首次迭代后**持续复用**消息列表并追加新内容；其余 5 种“错误模式”每次迭代都**从历史重新构建**整个消息列表，导致前缀无法复用。

---

### 三、最值得比较的指标
根据 `main.py` 的指标辅助函数与 `agent.py` 的采集逻辑，最值得关注的指标是：

1. **`cached_tokens`（缓存令牌数）**  
   —— 直接由模型返回，是**最能反映前缀缓存是否命中**的核心指标。该值越高，说明越多前置 token 被复用。

2. **TTFT（Time To First Token，首 token 延迟）**  
   —— `main.py` 中专门计算了 `_avg_ttft`（各轮次平均 TTFT）。缓存命中会显著降低 TTFT，体现推理加速效果。

3. **缓存命中率（`cache_hits / (cache_hits + cache_misses)`）**  
   —— `main.py` 中通过 `_hit_rate` 计算。用于衡量命中次数在总请求中的占比。

---

**一句话结论**：实验通过对比 **CORRECT** 与另外 5 种破坏上下文稳定性的模式，以 **`cached_tokens`** 和 **TTFT** 为核心指标，量化展示“保持消息序列稳定”对 KV 前缀缓存命中率和推理延迟的决定性作用。
```

**该模式最终回答**

```text
根据前三步工具返回的结果，现对本次 **KV 缓存对照实验（编号：KV缓存对照-20260808-192341）** 总结如下：

---

### 一、实验目的
该实验通过运行同一个 **ReAct Agent**，分别采用 6 种不同的上下文构造策略，来**演示和量化 KV Cache（自动前缀缓存）的重要性**。  
项目默认选用 **Moonshot / Kimi 的 `kimi-k2.6` 模型**作为被测对象，原因是该模型族会返回 `cached_tokens` 指标，能够直观暴露“前缀缓存命中 vs. 未命中”的差异；而不返回该指标的非推理模型则无法完成此演示。

---

### 二、六种模式（定义于 `agent.py` 的 `KVCacheMode`）
| 模式 | 含义 | 对 KV Cache 的影响 |
|------|------|-------------------|
| **CORRECT** | 正确实现：首次构建消息列表后持续复用，稳定追加 | ✅ 利于前缀缓存命中 |
| **DYNAMIC_SYSTEM** | 每次请求动态修改系统提示（如附加时间戳） | ❌ 破坏缓存 |
| **SHUFFLED_TOOLS** | 每次请求打乱工具（Tools）的顺序 | ❌ 破坏缓存 |
| **DYNAMIC_PROFILE** | 动态变更用户资料（如积分信息） | ❌ 破坏缓存 |
| **SLIDING_WINDOW** | 仅保留最近 6 条消息，丢弃早期上下文 | ❌ 缓存窗口不稳定 |
| **TEXT_FORMAT** | 将对话历史重新格式化为纯文本发送 | ❌ 改变序列结构，不利于缓存 |

核心实现差异：`CORRECT` 模式在首次迭代后**持续复用**消息列表并追加新内容；其余 5 种“错误模式”每次迭代都**从历史重新构建**整个消息列表，导致前缀无法复用。

---

### 三、最值得比较的指标
根据 `main.py` 的指标辅助函数与 `agent.py` 的采集逻辑，最值得关注的指标是：

1. **`cached_tokens`（缓存令牌数）**  
   —— 直接由模型返回，是**最能反映前缀缓存是否命中**的核心指标。该值越高，说明越多前置 token 被复用。

2. **TTFT（Time To First Token，首 token 延迟）**  
   —— `main.py` 中专门计算了 `_avg_ttft`（各轮次平均 TTFT）。缓存命中会显著降低 TTFT，体现推理加速效果。

3. **缓存命中率（`cache_hits / (cache_hits + cache_misses)`）**  
   —— `main.py` 中通过 `_hit_rate` 计算。用于衡量命中次数在总请求中的占比。

---

**一句话结论**：实验通过对比 **CORRECT** 与另外 5 种破坏上下文稳定性的模式，以 **`cached_tokens`** 和 **TTFT** 为核心指标，量化展示“保持消息序列稳定”对 KV 前缀缓存命中率和推理延迟的决定性作用。
```

### text_format · 历史转纯文本

机制：每轮把结构化历史重新拼成一条纯文本消息。

结果：`success=True`，API 4 轮，工具调用 3 次，累计 Cache% 17.2%。

#### 第 1 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 603 | 603 | 0 | 100.0% | 94 | 5.123s | system → user | read_file → find → grep |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。
```

**消息 2 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

</details>

**模型本轮回复**

```text
我将按顺序执行这四步。先从第 1 步开始。
```

工具调用 1：`find`

参数：

```json
{"pattern": "*.py", "directory": "chapter2/kv-cache"}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "pattern": "*.py",
  "directory": "chapter2/kv-cache",
  "matches": [
    "chapter2/kv-cache/agent.py",
    "chapter2/kv-cache/main.py",
    "chapter2/kv-cache/tests/conftest.py",
    "chapter2/kv-cache/tests/manual/_bootstrap.py",
    "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py",
    "chapter2/kv-cache/tests/manual/check_cache_invalidation.py",
    "chapter2/kv-cache/tests/manual/check_cached_tokens.py",
    "chapter2/kv-cache/tests/manual/check_completion.py",
    "chapter2/kv-cache/tests/manual/check_tool_calling.py",
    "chapter2/kv-cache/tests/manual/check_ttft.py",
    "chapter2/kv-cache/tests/manual/demo_quick.py",
    "chapter2/kv-cache/tests/test_error_handling.py",
    "chapter2/kv-cache/tests/test_file_range.py",
    "chapter2/kv-cache/tests/test_interactive.py",
    "chapter2/kv-cache/tests/test_message_flow.py",
    "chapter2/kv-cache/tests/test_negative_size.py",
    "chapter2/kv-cache/tests/test_tools.py"
  ],
  "count": 17,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 2 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 901 | 256 | 645 | 28.4% | 138 | 4.805s | system → user → user | read_file → find → grep |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。
```

**消息 2 · 用户（`user`）**

```text
此前对话：
助手：我将按顺序执行这四步。先从第 1 步开始。
助手：[正在调用工具]
  - 调用 find，参数：{"pattern": "*.py", "directory": "chapter2/kv-cache"}
工具返回：{"pattern": "*.py", "directory": "chapter2/kv-cache", "matches": ["chapter2/kv-cache/agent.py", "chapter2/kv-cache/main.py", "chapter2/kv-cache/tests/conftest.py", "chapter2/kv-cache/tests/manual/_bootstrap.py", "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py", "chapter2/kv-cache/tests/manual/check_cache_invalidation.py", "chapter2/kv-cache/tests/manual/check_cached_tokens.py", "chapter2/kv-cache/tests/manual/check_completion.py", "chapter2/kv-cache/tests/manual/check_tool_calling.py", "chapter2/kv-cache/tests/manual/check_ttft.py", "chapter2/kv-cache/tests/manual/demo_quick.py", "chapter2/kv-cache/tests/test_error_handling.py", "chapter2/kv-cache/tests/test_file_range.py", "chapter2/kv-cache/tests/test_interactive.py", "chapter2/kv-cache/tests/test_message_flow.py", "chapter2/kv-cache/tests/test_negative_size.py", "chapter2/kv-cache/tests/test_tools.py"], "count": 17, "truncated": false, "success": true}

```

**消息 3 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

</details>

**模型本轮回复**

```text
第 1 步已完成，找到了 17 个 Python 文件。现在执行第 2 步：读取 `main.py` 的前 80 行。
```

工具调用 1：`read_file`

参数：

```json
{"file_path":"chapter2/kv-cache/main.py","offset":0,"size":80}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "path": "chapter2/kv-cache/main.py",
  "content": "\"\"\"\nMain script to demonstrate KV cache importance\nRuns the ReAct agent with different implementations and compares performance\n\"\"\"\n\nimport os\nimport sys\nimport glob\nimport json\nimport argparse\nimport logging\nfrom typing import Dict, List, Any\nfrom datetime import datetime\nfrom dataclasses import asdict\n\ntry:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n\nfrom agent import KVCacheAgent, KVCacheMode, AgentMetrics, compare_implementations\n\n# Default model (Moonshot / Kimi). The whole current Kimi family (k2.5/k2.6/\n# k2.7/k3) reports cached_tokens for automatic prefix caching AND reasons, so it\n# only accepts temperature=1 (agent.py handles that automatically). kimi-k2.6 has\n# the lightest reasoning footprint of the cache-reporting models, giving the\n# cleanest TTFT while still exposing the prefix-cache hit metric this demo needs.\n# (The non-reasoning moonshot-v1-* models do NOT report cached_tokens, so they\n# cannot demonstrate the cache effect.)\nDEFAULT_MODEL = \"kimi-k2.6\"\nDEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), \"../..\"))\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format='%(asctime)s - %(levelname)s - %(message)s',\n    handlers=[\n        logging.FileHandler('kv_cache_demo.log'),\n        logging.StreamHandler()\n    ]\n)\nlogger = logging.getLogger(__name__)\n\n\n# ---------------------------------------------------------------------------\n# Metrics helpers (shared by live comparison and offline report)\n# ---------------------------------------------------------------------------\n\ndef _coerce_metrics(metrics: Any) -> Dict[str, Any]:\n    \"\"\"Normalize a stored metrics value into a plain dict.\n\n    Handles both formats found in result files:\n      - dict: produced by --compare (asdict) and by the fixed --mode path\n      - str : legacy single-mode files that stored repr(AgentMetrics(...))\n              because json.dump used default=str\n    \"\"\"\n    if isinstance(metrics, dict):\n        return metrics\n    if isinstance(metrics, str) and metrics.startswith(\"AgentMetrics(\"):\n        # Safe eval: only AgentMetrics is exposed, no builtins.\n        try:\n            obj = eval(metrics, {\"__builtins__\": {}}, {\"AgentMetrics\": AgentMetrics})\n            return asdict(obj)\n        except Exception as e:  # pragma: no cover - defensive\n            logger.warning(f\"Could not parse legacy metrics string: {e}\")\n    return {}\n\n\ndef _avg_ttft(m: Dict[str, Any]) -> float:\n    \"\"\"Average TTFT across iterations, falling back to first-iteration TTFT.\"\"\"\n    lst = m.get(\"ttft_per_iteration\") or []\n    return sum(lst) / len(lst) if lst else float(m.get(\"ttft\", 0.0) or 0.0)\n\n\ndef _hit_rate(m: Dict[str, Any]) -> float:\n    total = (m.get(\"cache_hits\", 0) or 0) + (m.get(\"cache_misses\", 0) or 0)\n    return (m.get(\"cache_hits\", 0) or 0) / total * 100 if total else 0.0\n\n\n",
  "total_lines": 548,
  "lines_read": 80,
  "offset": 0,
  "end_line": 80,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 3 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1,786 | 256 | 1,530 | 14.3% | 207 | 10.742s | system → user → user | read_file → find → grep |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。
```

**消息 2 · 用户（`user`）**

```text
此前对话：
助手：我将按顺序执行这四步。先从第 1 步开始。
助手：[正在调用工具]
  - 调用 find，参数：{"pattern": "*.py", "directory": "chapter2/kv-cache"}
工具返回：{"pattern": "*.py", "directory": "chapter2/kv-cache", "matches": ["chapter2/kv-cache/agent.py", "chapter2/kv-cache/main.py", "chapter2/kv-cache/tests/conftest.py", "chapter2/kv-cache/tests/manual/_bootstrap.py", "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py", "chapter2/kv-cache/tests/manual/check_cache_invalidation.py", "chapter2/kv-cache/tests/manual/check_cached_tokens.py", "chapter2/kv-cache/tests/manual/check_completion.py", "chapter2/kv-cache/tests/manual/check_tool_calling.py", "chapter2/kv-cache/tests/manual/check_ttft.py", "chapter2/kv-cache/tests/manual/demo_quick.py", "chapter2/kv-cache/tests/test_error_handling.py", "chapter2/kv-cache/tests/test_file_range.py", "chapter2/kv-cache/tests/test_interactive.py", "chapter2/kv-cache/tests/test_message_flow.py", "chapter2/kv-cache/tests/test_negative_size.py", "chapter2/kv-cache/tests/test_tools.py"], "count": 17, "truncated": false, "success": true}
助手：第 1 步已完成，找到了 17 个 Python 文件。现在执行第 2 步：读取 `main.py` 的前 80 行。
助手：[正在调用工具]
  - 调用 read_file，参数：{"file_path":"chapter2/kv-cache/main.py","offset":0,"size":80}
工具返回：{"path": "chapter2/kv-cache/main.py", "content": "\"\"\"\nMain script to demonstrate KV cache importance\nRuns the ReAct agent with different implementations and compares performance\n\"\"\"\n\nimport os\nimport sys\nimport glob\nimport json\nimport argparse\nimport logging\nfrom typing import Dict, List, Any\nfrom datetime import datetime\nfrom dataclasses import asdict\n\ntry:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n\nfrom agent import KVCacheAgent, KVCacheMode, AgentMetrics, compare_implementations\n\n# Default model (Moonshot / Kimi). The whole current Kimi family (k2.5/k2.6/\n# k2.7/k3) reports cached_tokens for automatic prefix caching AND reasons, so it\n# only accepts temperature=1 (agent.py handles that automatically). kimi-k2.6 has\n# the lightest reasoning footprint of the cache-reporting models, giving the\n# cleanest TTFT while still exposing the prefix-cache hit metric this demo needs.\n# (The non-reasoning moonshot-v1-* models do NOT report cached_tokens, so they\n# cannot demonstrate the cache effect.)\nDEFAULT_MODEL = \"kimi-k2.6\"\nDEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), \"../..\"))\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format='%(asctime)s - %(levelname)s - %(message)s',\n    handlers=[\n        logging.FileHandler('kv_cache_demo.log'),\n        logging.StreamHandler()\n    ]\n)\nlogger = logging.getLogger(__name__)\n\n\n# ---------------------------------------------------------------------------\n# Metrics helpers (shared by live comparison and offline report)\n# ---------------------------------------------------------------------------\n\ndef _coerce_metrics(metrics: Any) -> Dict[str, Any]:\n    \"\"\"Normalize a stored metrics value into a plain dict.\n\n    Handles both formats found in result files:\n      - dict: produced by --compare (asdict) and by the fixed --mode path\n      - str : legacy single-mode files that stored repr(AgentMetrics(...))\n              because json.dump used default=str\n    \"\"\"\n    if isinstance(metrics, dict):\n        return metrics\n    if isinstance(metrics, str) and metrics.startswith(\"AgentMetrics(\"):\n        # Safe eval: only AgentMetrics is exposed, no builtins.\n        try:\n            obj = eval(metrics, {\"__builtins__\": {}}, {\"AgentMetrics\": AgentMetrics})\n            return asdict(obj)\n        except Exception as e:  # pragma: no cover - defensive\n            logger.warning(f\"Could not parse legacy metrics string: {e}\")\n    return {}\n\n\ndef _avg_ttft(m: Dict[str, Any]) -> float:\n    \"\"\"Average TTFT across iterations, falling back to first-iteration TTFT.\"\"\"\n    lst = m.get(\"ttft_per_iteration\") or []\n    return sum(lst) / len(lst) if lst else float(m.get(\"ttft\", 0.0) or 0.0)\n\n\ndef _hit_rate(m: Dict[str, Any]) -> float:\n    total = (m.get(\"cache_hits\", 0) or 0) + (m.get(\"cache_misses\", 0) or 0)\n    return (m.get(\"cache_hits\", 0) or 0) / total * 100 if total else 0.0\n\n\n", "total_lines": 548, "lines_read": 80, "offset": 0, "end_line": 80, "truncated": false, "success": true}

```

**消息 3 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

</details>

**模型本轮回复**

```text
前 2 步已有成功结果，现在执行第 3 步：在 `agent.py` 中搜索六种模式与缓存指标相关的代码证据。
```

工具调用 1：`grep`

参数：

```json
{"pattern":"class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens","file_path":"chapter2/kv-cache/agent.py"}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "pattern": "class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens",
  "matches": [
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 3,
      "line": "Demonstrates the importance of KV cache through correct and incorrect implementations."
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 33,
      "line": "chat models do NOT reason (and also do not report cached_tokens).\"\"\""
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 59,
      "line": "class KVCacheMode(Enum):"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 61,
      "line": "CORRECT = \"correct\"  # Correct implementation with stable context"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 62,
      "line": "DYNAMIC_SYSTEM = \"dynamic_system\"  # Changing system prompt with timestamp"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 63,
      "line": "SHUFFLED_TOOLS = \"shuffled_tools\"  # Shuffling tool order each request"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 64,
      "line": "DYNAMIC_PROFILE = \"dynamic_profile\"  # Changing user profile with credits"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 65,
      "line": "SLIDING_WINDOW = \"sliding_window\"  # Only keeping recent 6 messages"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 66,
      "line": "TEXT_FORMAT = \"text_format\"  # Formatting messages as plain text"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 91,
      "line": "cached_tokens: int = 0"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 357,
      "line": "def __init__(self, api_key: str, mode: KVCacheMode = KVCacheMode.CORRECT,"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 486,
      "line": "if self.mode == KVCacheMode.DYNAMIC_SYSTEM:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 497,
      "line": "if self.mode == KVCacheMode.SHUFFLED_TOOLS:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 505,
      "line": "if self.mode == KVCacheMode.DYNAMIC_PROFILE:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 514,
      "line": "\"\"\"Format messages based on mode - recreated each iteration for incorrect modes\"\"\""
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 517,
      "line": "# Add system prompt (changes each time for DYNAMIC_SYSTEM mode)"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 528,
      "line": "if self.mode == KVCacheMode.SLIDING_WINDOW:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 540,
      "line": "elif self.mode == KVCacheMode.TEXT_FORMAT:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 575,
      "line": "# For CORRECT, DYNAMIC_SYSTEM, SHUFFLED_TOOLS, DYNAMIC_PROFILE modes"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 646,
      "line": "# CORRECT mode: Build messages once on first iteration, then keep appending"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 649,
      "line": "# INCORRECT modes: Recreate entire messages list from history each iteration"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 654,
      "line": "if self.mode == KVCacheMode.CORRECT:"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 655,
      "line": "# Correct mode: Build messages once, then keep using same list"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 659,
      "line": "# Incorrect modes: Recreate messages from history each iteration"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 671,
      "line": "# Add tools for all modes (TEXT_FORMAT still needs tools to work)"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 672,
      "line": "# TEXT_FORMAT only affects how conversation history is formatted, not tool availability"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 706,
      "line": "# The cached_tokens field appears directly in the usage object"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 708,
      "line": "if hasattr(usage, 'cached_tokens'):"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 710,
      "line": "cached = usage.cached_tokens if usage.cached_tokens is not None else 0"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 711,
      "line": "self.metrics.cached_tokens += cached"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 720,
      "line": "if details and hasattr(details, 'cached_tokens'):"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 721,
      "line": "cached = details.cached_tokens if details.cached_tokens is not None else 0"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 722,
      "line": "self.metrics.cached_tokens += cached"
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 883,
      "line": "logger.info(f\"Cached Tokens: {metrics.cached_tokens}\")"
    }
  ],
  "files_searched": 1,
  "match_count": 34,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 4 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 3,207 | 0 | 3,207 | 0.0% | 1,023 | 31.563s | system → user → user | read_file → find → grep |

<details>
<summary>展开：本轮发送给模型的完整消息</summary>

**消息 1 · 系统（`system`）**

```text
你是一名可以使用本地文件系统工具的 AI 助手。
你可以读取文件、按模式查找文件，并在文件中搜索文本。
请使用 ReAct 工作方式：先判断下一步需要什么证据，再调用工具，观察工具结果后继续。

当用户要求分析或总结代码项目时，请遵循以下顺序：
1. 先使用 find 了解文件结构；
2. 再读取关键文件理解内容；
3. 需要定位特定模式时使用 grep；
4. 收集到足够证据后直接回答，不再调用工具。

请逐步完成任务。证据不足时先调用工具；证据足够时直接给出最终回答。所有面向用户的自然语言必须使用中文。
```

**消息 2 · 用户（`user`）**

```text
此前对话：
助手：我将按顺序执行这四步。先从第 1 步开始。
助手：[正在调用工具]
  - 调用 find，参数：{"pattern": "*.py", "directory": "chapter2/kv-cache"}
工具返回：{"pattern": "*.py", "directory": "chapter2/kv-cache", "matches": ["chapter2/kv-cache/agent.py", "chapter2/kv-cache/main.py", "chapter2/kv-cache/tests/conftest.py", "chapter2/kv-cache/tests/manual/_bootstrap.py", "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py", "chapter2/kv-cache/tests/manual/check_cache_invalidation.py", "chapter2/kv-cache/tests/manual/check_cached_tokens.py", "chapter2/kv-cache/tests/manual/check_completion.py", "chapter2/kv-cache/tests/manual/check_tool_calling.py", "chapter2/kv-cache/tests/manual/check_ttft.py", "chapter2/kv-cache/tests/manual/demo_quick.py", "chapter2/kv-cache/tests/test_error_handling.py", "chapter2/kv-cache/tests/test_file_range.py", "chapter2/kv-cache/tests/test_interactive.py", "chapter2/kv-cache/tests/test_message_flow.py", "chapter2/kv-cache/tests/test_negative_size.py", "chapter2/kv-cache/tests/test_tools.py"], "count": 17, "truncated": false, "success": true}
助手：第 1 步已完成，找到了 17 个 Python 文件。现在执行第 2 步：读取 `main.py` 的前 80 行。
助手：[正在调用工具]
  - 调用 read_file，参数：{"file_path":"chapter2/kv-cache/main.py","offset":0,"size":80}
工具返回：{"path": "chapter2/kv-cache/main.py", "content": "\"\"\"\nMain script to demonstrate KV cache importance\nRuns the ReAct agent with different implementations and compares performance\n\"\"\"\n\nimport os\nimport sys\nimport glob\nimport json\nimport argparse\nimport logging\nfrom typing import Dict, List, Any\nfrom datetime import datetime\nfrom dataclasses import asdict\n\ntry:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n\nfrom agent import KVCacheAgent, KVCacheMode, AgentMetrics, compare_implementations\n\n# Default model (Moonshot / Kimi). The whole current Kimi family (k2.5/k2.6/\n# k2.7/k3) reports cached_tokens for automatic prefix caching AND reasons, so it\n# only accepts temperature=1 (agent.py handles that automatically). kimi-k2.6 has\n# the lightest reasoning footprint of the cache-reporting models, giving the\n# cleanest TTFT while still exposing the prefix-cache hit metric this demo needs.\n# (The non-reasoning moonshot-v1-* models do NOT report cached_tokens, so they\n# cannot demonstrate the cache effect.)\nDEFAULT_MODEL = \"kimi-k2.6\"\nDEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), \"../..\"))\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format='%(asctime)s - %(levelname)s - %(message)s',\n    handlers=[\n        logging.FileHandler('kv_cache_demo.log'),\n        logging.StreamHandler()\n    ]\n)\nlogger = logging.getLogger(__name__)\n\n\n# ---------------------------------------------------------------------------\n# Metrics helpers (shared by live comparison and offline report)\n# ---------------------------------------------------------------------------\n\ndef _coerce_metrics(metrics: Any) -> Dict[str, Any]:\n    \"\"\"Normalize a stored metrics value into a plain dict.\n\n    Handles both formats found in result files:\n      - dict: produced by --compare (asdict) and by the fixed --mode path\n      - str : legacy single-mode files that stored repr(AgentMetrics(...))\n              because json.dump used default=str\n    \"\"\"\n    if isinstance(metrics, dict):\n        return metrics\n    if isinstance(metrics, str) and metrics.startswith(\"AgentMetrics(\"):\n        # Safe eval: only AgentMetrics is exposed, no builtins.\n        try:\n            obj = eval(metrics, {\"__builtins__\": {}}, {\"AgentMetrics\": AgentMetrics})\n            return asdict(obj)\n        except Exception as e:  # pragma: no cover - defensive\n            logger.warning(f\"Could not parse legacy metrics string: {e}\")\n    return {}\n\n\ndef _avg_ttft(m: Dict[str, Any]) -> float:\n    \"\"\"Average TTFT across iterations, falling back to first-iteration TTFT.\"\"\"\n    lst = m.get(\"ttft_per_iteration\") or []\n    return sum(lst) / len(lst) if lst else float(m.get(\"ttft\", 0.0) or 0.0)\n\n\ndef _hit_rate(m: Dict[str, Any]) -> float:\n    total = (m.get(\"cache_hits\", 0) or 0) + (m.get(\"cache_misses\", 0) or 0)\n    return (m.get(\"cache_hits\", 0) or 0) / total * 100 if total else 0.0\n\n\n", "total_lines": 548, "lines_read": 80, "offset": 0, "end_line": 80, "truncated": false, "success": true}
助手：前 2 步已有成功结果，现在执行第 3 步：在 `agent.py` 中搜索六种模式与缓存指标相关的代码证据。
助手：[正在调用工具]
  - 调用 grep，参数：{"pattern":"class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens","file_path":"chapter2/kv-cache/agent.py"}
工具返回：{"pattern": "class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens", "matches": [{"file": "chapter2/kv-cache/agent.py", "line_num": 3, "line": "Demonstrates the importance of KV cache through correct and incorrect implementations."}, {"file": "chapter2/kv-cache/agent.py", "line_num": 33, "line": "chat models do NOT reason (and also do not report cached_tokens).\"\"\""}, {"file": "chapter2/kv-cache/agent.py", "line_num": 59, "line": "class KVCacheMode(Enum):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 61, "line": "CORRECT = \"correct\"  # Correct implementation with stable context"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 62, "line": "DYNAMIC_SYSTEM = \"dynamic_system\"  # Changing system prompt with timestamp"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 63, "line": "SHUFFLED_TOOLS = \"shuffled_tools\"  # Shuffling tool order each request"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 64, "line": "DYNAMIC_PROFILE = \"dynamic_profile\"  # Changing user profile with credits"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 65, "line": "SLIDING_WINDOW = \"sliding_window\"  # Only keeping recent 6 messages"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 66, "line": "TEXT_FORMAT = \"text_format\"  # Formatting messages as plain text"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 91, "line": "cached_tokens: int = 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 357, "line": "def __init__(self, api_key: str, mode: KVCacheMode = KVCacheMode.CORRECT,"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 486, "line": "if self.mode == KVCacheMode.DYNAMIC_SYSTEM:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 497, "line": "if self.mode == KVCacheMode.SHUFFLED_TOOLS:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 505, "line": "if self.mode == KVCacheMode.DYNAMIC_PROFILE:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 514, "line": "\"\"\"Format messages based on mode - recreated each iteration for incorrect modes\"\"\""}, {"file": "chapter2/kv-cache/agent.py", "line_num": 517, "line": "# Add system prompt (changes each time for DYNAMIC_SYSTEM mode)"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 528, "line": "if self.mode == KVCacheMode.SLIDING_WINDOW:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 540, "line": "elif self.mode == KVCacheMode.TEXT_FORMAT:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 575, "line": "# For CORRECT, DYNAMIC_SYSTEM, SHUFFLED_TOOLS, DYNAMIC_PROFILE modes"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 646, "line": "# CORRECT mode: Build messages once on first iteration, then keep appending"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 649, "line": "# INCORRECT modes: Recreate entire messages list from history each iteration"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 654, "line": "if self.mode == KVCacheMode.CORRECT:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 655, "line": "# Correct mode: Build messages once, then keep using same list"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 659, "line": "# Incorrect modes: Recreate messages from history each iteration"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 671, "line": "# Add tools for all modes (TEXT_FORMAT still needs tools to work)"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 672, "line": "# TEXT_FORMAT only affects how conversation history is formatted, not tool availability"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 706, "line": "# The cached_tokens field appears directly in the usage object"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 708, "line": "if hasattr(usage, 'cached_tokens'):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 710, "line": "cached = usage.cached_tokens if usage.cached_tokens is not None else 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 711, "line": "self.metrics.cached_tokens += cached"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 720, "line": "if details and hasattr(details, 'cached_tokens'):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 721, "line": "cached = details.cached_tokens if details.cached_tokens is not None else 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 722, "line": "self.metrics.cached_tokens += cached"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 883, "line": "logger.info(f\"Cached Tokens: {metrics.cached_tokens}\")"}], "files_searched": 1, "match_count": 34, "truncated": false, "success": true}

```

**消息 3 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面四步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192341
```

</details>

**模型本轮回复**

```text
根据前三步已返回的工具结果，我直接给出第 4 步的总结：

---

### 实验目的
这个实验旨在**演示 KV Cache（键值缓存）的重要性**。它通过实现一个 ReAct Agent，并对比六种不同模式下的运行表现，来展示“正确的上下文构造方式”与“破坏 KV Cache 复用的错误方式”之间的性能差异。`main.py` 明确说明其任务是“用不同实现运行 ReAct agent 并比较性能”。

### 六种模式
在 `agent.py` 中定义了 `KVCacheMode` 枚举，共六种模式：

| 模式 | 含义 |
|------|------|
| **CORRECT** | 正确实现：保持上下文稳定，消息列表一旦构建后持续复用并追加。 |
| **DYNAMIC_SYSTEM** | 错误实现：每次请求都修改 system prompt（例如加入时间戳），导致前缀变化。 |
| **SHUFFLED_TOOLS** | 错误实现：每次请求打乱 tools 的顺序，破坏前缀一致性。 |
| **DYNAMIC_PROFILE** | 错误实现：动态改变用户资料（如 credits），使上下文内容不断变化。 |
| **SLIDING_WINDOW** | 错误实现：仅保留最近 6 条消息，历史窗口滑动导致前缀无法复用。 |
| **TEXT_FORMAT** | 错误实现：将消息格式化为纯文本，改变了消息结构，影响缓存匹配。 |

前一种是**正确做法**，后五种是**常见错误做法**，它们都会在每一轮迭代中“重新创建”整个消息列表，从而破坏 KV Cache 的命中。

### 最值得比较的指标
从代码证据来看，最值得比较的指标包括：

1. **`cached_tokens`（缓存 Token 数）**  
   `agent.py` 直接从 API 返回的 `usage.cached_tokens` 中提取并累加。这是**最直接反映 KV Cache 命中效果**的指标——命中越高，复用越多，演示效果越明显。

2. **TTFT（首 Token 延迟）**  
   `main.py` 专门定义了 `_avg_ttft()`，用于计算每次迭代的平均首 token 时间。KV Cache 命中高时，TTFT 应该显著降低。

3. **Cache 命中率（`cache_hits` / `cache_misses`）**  
   `main.py` 中有 `_hit_rate()` 函数，统计命中与未命中的比例，用于量化缓存效率。

4. **整体性能对比**  
   `main.py` 的核心逻辑就是调用 `compare_implementations()`，将各模式的上述指标并排比较，从而直观展示 KV Cache 对延迟和成本的影响。

---

**一句话结论**：该实验通过“稳定上下文 vs. 故意破坏前缀一致性”的六种模式对比，以 **`cached_tokens`** 和 **TTFT** 为核心指标，量化验证 KV Cache 对 ReAct Agent 推理速度与效率的决定性作用。
```

**该模式最终回答**

```text
根据前三步已返回的工具结果，我直接给出第 4 步的总结：

---

### 实验目的
这个实验旨在**演示 KV Cache（键值缓存）的重要性**。它通过实现一个 ReAct Agent，并对比六种不同模式下的运行表现，来展示“正确的上下文构造方式”与“破坏 KV Cache 复用的错误方式”之间的性能差异。`main.py` 明确说明其任务是“用不同实现运行 ReAct agent 并比较性能”。

### 六种模式
在 `agent.py` 中定义了 `KVCacheMode` 枚举，共六种模式：

| 模式 | 含义 |
|------|------|
| **CORRECT** | 正确实现：保持上下文稳定，消息列表一旦构建后持续复用并追加。 |
| **DYNAMIC_SYSTEM** | 错误实现：每次请求都修改 system prompt（例如加入时间戳），导致前缀变化。 |
| **SHUFFLED_TOOLS** | 错误实现：每次请求打乱 tools 的顺序，破坏前缀一致性。 |
| **DYNAMIC_PROFILE** | 错误实现：动态改变用户资料（如 credits），使上下文内容不断变化。 |
| **SLIDING_WINDOW** | 错误实现：仅保留最近 6 条消息，历史窗口滑动导致前缀无法复用。 |
| **TEXT_FORMAT** | 错误实现：将消息格式化为纯文本，改变了消息结构，影响缓存匹配。 |

前一种是**正确做法**，后五种是**常见错误做法**，它们都会在每一轮迭代中“重新创建”整个消息列表，从而破坏 KV Cache 的命中。

### 最值得比较的指标
从代码证据来看，最值得比较的指标包括：

1. **`cached_tokens`（缓存 Token 数）**  
   `agent.py` 直接从 API 返回的 `usage.cached_tokens` 中提取并累加。这是**最直接反映 KV Cache 命中效果**的指标——命中越高，复用越多，演示效果越明显。

2. **TTFT（首 Token 延迟）**  
   `main.py` 专门定义了 `_avg_ttft()`，用于计算每次迭代的平均首 token 时间。KV Cache 命中高时，TTFT 应该显著降低。

3. **Cache 命中率（`cache_hits` / `cache_misses`）**  
   `main.py` 中有 `_hit_rate()` 函数，统计命中与未命中的比例，用于量化缓存效率。

4. **整体性能对比**  
   `main.py` 的核心逻辑就是调用 `compare_implementations()`，将各模式的上述指标并排比较，从而直观展示 KV Cache 对延迟和成本的影响。

---

**一句话结论**：该实验通过“稳定上下文 vs. 故意破坏前缀一致性”的六种模式对比，以 **`cached_tokens`** 和 **TTFT** 为核心指标，量化验证 KV Cache 对 ReAct Agent 推理速度与效率的决定性作用。
```

## 验证边界

- 本报告证明请求真实到达 Kimi，并保存了服务端返回的 usage 与对话收据。
- 它不证明缓存命中了哪一个具体消息片段；Kimi 当前只返回总 `cached_tokens`。
- 六种模式按顺序连续执行，服务端缓存可能受到前面模式和更早请求的预热影响；报告保留首轮数据，不把首轮自动命中误称为本地代码预先计算的缓存。
- 响应耗时还会受到推理长度、网络和服务端负载影响，因此判断 KV Cache 时优先看 Token 指标，再把耗时作为辅助证据。
