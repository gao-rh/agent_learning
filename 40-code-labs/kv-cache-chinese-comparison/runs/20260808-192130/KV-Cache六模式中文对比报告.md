---
type: code-lab-report
status: interrupted
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
- 开始：`2026-08-08T19:21:30+08:00`
- 结束：`2026-08-08T19:22:38+08:00`
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
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索 `cached_tokens`。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192130
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
| `correct` | 是 | 4 | 3 | 5,574 | 2,560 | 3,014 | 45.9% | 2,412 | 16.932s | 67.736s | 是 |

## `correct`：新增 Prompt 与旧前缀复用

只有 `correct` 每轮都在完全相同的消息列表末尾追加，因此可以用 `本轮 cached_tokens ÷ 上轮 prompt_tokens` 近似回答“上一轮不动的前缀有没有基本命中”。它仍不是服务商提供的精确前缀覆盖字段，会受到缓存块粒度和服务端已有缓存影响。

| 轮次 | Prompt | 比上轮新增 | Cached | 未缓存 | Cache% | Cached ÷ 上轮 Prompt | 响应耗时 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 564 | — | 0 | 564 | 0.0% | — | 3.689s |
| 2 | 894 | +330 | 512 | 382 | 57.3% | 90.8% | 3.129s |
| 3 | 1,822 | +928 | 512 | 1,310 | 28.1% | 57.3% | 2.920s |
| 4 | 2,294 | +472 | 1,536 | 758 | 67.0% | 84.3% | 57.991s |

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

结果：`success=True`，API 4 轮，工具调用 3 次，累计 Cache% 45.9%。

#### 第 1 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 564 | 0 | 564 | 0.0% | 73 | 3.689s | system → user | read_file → find → grep |

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
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索 `cached_tokens`。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192130
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
| 894 | 512 | 382 | 57.3% | 102 | 3.129s | system → user → assistant → tool | read_file → find → grep |

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
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索 `cached_tokens`。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192130
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
| 1,822 | 512 | 1,310 | 28.1% | 68 | 2.920s | system → user → assistant → tool → assistant → tool | read_file → find → grep |

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
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索 `cached_tokens`。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192130
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

</details>

**模型本轮回复**

工具调用 1：`grep`

参数：

```json
{"pattern":"cached_tokens","file_path":"chapter2/kv-cache/agent.py"}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "pattern": "cached_tokens",
  "matches": [
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 33,
      "line": "chat models do NOT reason (and also do not report cached_tokens).\"\"\""
    },
    {
      "file": "chapter2/kv-cache/agent.py",
      "line_num": 91,
      "line": "cached_tokens: int = 0"
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
  "match_count": 10,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 4 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 2,294 | 1,536 | 758 | 67.0% | 2,169 | 57.991s | system → user → assistant → tool → assistant → tool → assistant → tool | read_file → find → grep |

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
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索 `cached_tokens`。
4. 只根据以上工具返回，用中文总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-192130
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
      "arguments": "{\"pattern\":\"cached_tokens\",\"file_path\":\"chapter2/kv-cache/agent.py\"}",
      "name": "grep"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 8 · 工具（`tool`）**

```text
{"pattern": "cached_tokens", "matches": [{"file": "chapter2/kv-cache/agent.py", "line_num": 33, "line": "chat models do NOT reason (and also do not report cached_tokens).\"\"\""}, {"file": "chapter2/kv-cache/agent.py", "line_num": 91, "line": "cached_tokens: int = 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 706, "line": "# The cached_tokens field appears directly in the usage object"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 708, "line": "if hasattr(usage, 'cached_tokens'):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 710, "line": "cached = usage.cached_tokens if usage.cached_tokens is not None else 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 711, "line": "self.metrics.cached_tokens += cached"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 720, "line": "if details and hasattr(details, 'cached_tokens'):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 721, "line": "cached = details.cached_tokens if details.cached_tokens is not None else 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 722, "line": "self.metrics.cached_tokens += cached"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 883, "line": "logger.info(f\"Cached Tokens: {metrics.cached_tokens}\")"}], "files_searched": 1, "match_count": 10, "truncated": false, "success": true}
```

</details>

**模型本轮回复**

```text
根据已执行的三步工具返回，现对该 KV Cache 对照实验总结如下：

### 1. 实验目的
该实验旨在**演示 KV Cache（键值缓存）的重要性**。通过运行 ReAct Agent 的**不同实现**并对比它们的性能表现，来验证前缀缓存（prefix caching）对实际调用效果的影响。

### 2. 六种模式
在已返回的工具结果中（`main.py` 前 80 行以及 `agent.py` 中 `cached_tokens` 的检索结果），**未直接列出六种模式的具体定义**。`main.py` 中仅提到从 `agent.py` 导入了 `KVCacheMode` 枚举，但本次读取范围未覆盖其枚举值，因此现有工具返回不足以说明这六种模式的名称与差异。

### 3. 最值得比较的指标
从现有代码逻辑可确定，实验重点对比以下指标：

- **TTFT（Time To First Token，首 Token 响应时间）**：`main.py` 中专门定义了 `_avg_ttft` 函数，计算多次迭代的平均 TTFT，这是衡量缓存加速效果最直接的性能指标。
- **cached_tokens（缓存 Token 数）**：`agent.py` 中显式追踪该字段，从 API 返回的 `usage` 对象直接提取，用于量化前缀缓存实际命中的 Token 数量。
- **cache_hits / cache_misses（缓存命中与未命中）**：`main.py` 中通过 `_hit_rate` 函数计算缓存命中率，是评估 KV Cache 有效性的核心比例指标。

综上，本次实验围绕 **“有无/不同程度 KV Cache”** 的对照展开，**TTFT 与 cached_tokens** 是最值得优先比较的两大指标。
```

**该模式最终回答**

```text
根据已执行的三步工具返回，现对该 KV Cache 对照实验总结如下：

### 1. 实验目的
该实验旨在**演示 KV Cache（键值缓存）的重要性**。通过运行 ReAct Agent 的**不同实现**并对比它们的性能表现，来验证前缀缓存（prefix caching）对实际调用效果的影响。

### 2. 六种模式
在已返回的工具结果中（`main.py` 前 80 行以及 `agent.py` 中 `cached_tokens` 的检索结果），**未直接列出六种模式的具体定义**。`main.py` 中仅提到从 `agent.py` 导入了 `KVCacheMode` 枚举，但本次读取范围未覆盖其枚举值，因此现有工具返回不足以说明这六种模式的名称与差异。

### 3. 最值得比较的指标
从现有代码逻辑可确定，实验重点对比以下指标：

- **TTFT（Time To First Token，首 Token 响应时间）**：`main.py` 中专门定义了 `_avg_ttft` 函数，计算多次迭代的平均 TTFT，这是衡量缓存加速效果最直接的性能指标。
- **cached_tokens（缓存 Token 数）**：`agent.py` 中显式追踪该字段，从 API 返回的 `usage` 对象直接提取，用于量化前缀缓存实际命中的 Token 数量。
- **cache_hits / cache_misses（缓存命中与未命中）**：`main.py` 中通过 `_hit_rate` 函数计算缓存命中率，是评估 KV Cache 有效性的核心比例指标。

综上，本次实验围绕 **“有无/不同程度 KV Cache”** 的对照展开，**TTFT 与 cached_tokens** 是最值得优先比较的两大指标。
```

## 验证边界

- 本报告证明请求真实到达 Kimi，并保存了服务端返回的 usage 与对话收据。
- 它不证明缓存命中了哪一个具体消息片段；Kimi 当前只返回总 `cached_tokens`。
- 六种模式按顺序连续执行，服务端缓存可能受到前面模式和更早请求的预热影响；报告保留首轮数据，不把首轮自动命中误称为本地代码预先计算的缓存。
- 响应耗时还会受到推理长度、网络和服务端负载影响，因此判断 KV Cache 时优先看 Token 指标，再把耗时作为辅助证据。
