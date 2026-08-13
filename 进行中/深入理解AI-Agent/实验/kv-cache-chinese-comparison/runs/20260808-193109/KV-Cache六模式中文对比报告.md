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
- 开始：`2026-08-08T19:31:09+08:00`
- 结束：`2026-08-08T19:35:34+08:00`
- 模式顺序：`correct -> dynamic_system -> shuffled_tools -> dynamic_profile -> sliding_window -> text_format`
- 随机种子：`20260808`
- 最大轮数：`8`
- 教材 `agent.py` SHA-256：`9f33f25affbc51d06e419e3bc9f56431ddeb3a3576692588559cc914635cf84c`
- 中文适配：共享 system、工具说明、动态资料、纯文本历史标签和用户任务翻译为中文；六种上下文管理机制不变。
- 凭据：只从本地环境读取，未写入任何实验产物。隐藏推理 `reasoning_content` 也未保存。

### 统一中文任务

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
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
| `correct` | 是 | 5 | 4 | 11,407 | 4,864 | 6,543 | 42.6% | 1,331 | 9.331s | 46.667s | 是 |
| `dynamic_system` | 是 | 5 | 4 | 11,437 | 1,280 | 10,157 | 11.2% | 1,335 | 11.331s | 56.669s | 是 |
| `shuffled_tools` | 是 | 5 | 4 | 11,729 | 2,304 | 9,425 | 19.6% | 1,471 | 9.862s | 49.324s | 是 |
| `dynamic_profile` | 是 | 5 | 4 | 11,435 | 1,024 | 10,411 | 9.0% | 1,365 | 6.522s | 32.620s | 是 |
| `sliding_window` | 是 | 5 | 4 | 11,053 | 3,207 | 7,846 | 29.0% | 856 | 5.764s | 28.833s | 是 |
| `text_format` | 是 | 5 | 4 | 10,819 | 1,671 | 9,148 | 15.4% | 2,650 | 10.197s | 50.999s | 是 |

## 本轮实测观察

1. `correct` 的累计 Cache% 为 **42.6%**，高于动态 system（11.2%）、工具乱序（19.6%）、动态 profile（9.0%）和纯文本历史（15.4%）。这支持“稳定、只追加的前缀更容易持续复用”。
2. `dynamic_system` 五轮都只有 256 个 Cached Token；`dynamic_profile` 前四轮也只有 256、最后一轮为 0。动态字段放在靠前位置后，后面的历史即使内容相同，也不能继续成为同一稳定前缀。
3. `sliding_window` 的累计 Cache% 看起来仍有 29.0%，但关键要看截断瞬间：第 4 轮是 Prompt 3,368 / Cached 1,536，第 5 轮删掉最早一对 assistant/tool 后变为 Prompt 4,179 / Cached 256；同轮完整 `correct` 的 Prompt 是 4,527。它同时减少了一部分输入，也把缓存复用从 45.6% 打到 6.1%。
4. `shuffled_tools` 最后一轮意外命中 1,536 Tokens，导致累计值高于部分动态模式。逐轮工具顺序证明它确实发生了重排；这个跳升更可能来自某次排列与本次连续 campaign 中已有服务端前缀碰巧重合，不能据此反推“乱序没有影响”。
5. 响应耗时的方向没有 Cache% 那么干净，因为各模式 Completion Tokens 不同，Kimi 推理长度、网络和服务端负载也不同。本轮只把耗时当辅助信号，不把模型回答里对 TTFT 的表述当成真实首 Token 测量。

> 本轮结论不是“所有反模式一定按固定名次变差”，而是：改变越靠近前缀开头、改变得越频繁，可连续复用的范围通常越小；真实自动缓存还会叠加块粒度、历史预热和跨请求匹配。

## `correct`：新增 Prompt 与旧前缀复用

只有 `correct` 每轮都在完全相同的消息列表末尾追加，因此可以用 `本轮 cached_tokens ÷ 上轮 prompt_tokens` 近似回答“上一轮不动的前缀有没有基本命中”。它仍不是服务商提供的精确前缀覆盖字段，会受到缓存块粒度和服务端已有缓存影响。

| 轮次 | Prompt | 比上轮新增 | Cached | 未缓存 | Cache% | Cached ÷ 上轮 Prompt | 响应耗时 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 647 | — | 256 | 391 | 39.6% | — | 5.019s |
| 2 | 970 | +323 | 512 | 458 | 52.8% | 79.1% | 2.809s |
| 3 | 1,876 | +906 | 512 | 1,364 | 27.3% | 52.8% | 6.966s |
| 4 | 3,387 | +1,511 | 1,536 | 1,851 | 45.3% | 81.9% | 3.370s |
| 5 | 4,527 | +1,140 | 2,048 | 2,479 | 45.2% | 60.5% | 28.490s |

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

结果：`success=True`，API 5 轮，工具调用 4 次，累计 Cache% 42.6%。

#### 第 1 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 647 | 256 | 391 | 39.6% | 66 | 5.019s | system → user | read_file → find → grep |

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
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
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
| 970 | 512 | 458 | 52.8% | 80 | 2.809s | system → user → assistant → tool | read_file → find → grep |

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
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
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
| 1,876 | 512 | 1,364 | 27.3% | 172 | 6.966s | system → user → assistant → tool → assistant → tool | read_file → find → grep |

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
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
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
| 3,387 | 1,536 | 1,851 | 45.3% | 86 | 3.370s | system → user → assistant → tool → assistant → tool → assistant → tool | read_file → find → grep |

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
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
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

工具调用 1：`read_file`

参数：

```json
{"file_path": "chapter2/kv-cache/agent.py", "offset": 640, "size": 100}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "path": "chapter2/kv-cache/agent.py",
  "content": "        while iteration < max_iterations:\n            iteration += 1\n            \n            # CRITICAL: Message handling for KV cache demonstration\n            # \n            # CORRECT mode: Build messages once on first iteration, then keep appending\n            #   - Maintains stable context → KV cache works efficiently\n            # \n            # INCORRECT modes: Recreate entire messages list from history each iteration\n            #   - Forces complete context reconstruction → KV cache invalidated\n            #   - Within an iteration, we still append to messages for proper API flow\n            #   - But at the start of each new iteration, we rebuild from scratch\n            \n            if self.mode == KVCacheMode.CORRECT:\n                # Correct mode: Build messages once, then keep using same list\n                if iteration == 1:\n                    messages = self._format_messages(original_task)\n            else:\n                # Incorrect modes: Recreate messages from history each iteration\n                # This forces cache invalidation due to context changes\n                messages = self._format_messages(original_task)\n            \n            # Prepare request\n            request_data = {\n                \"model\": self.model,\n                \"messages\": messages,\n                \"temperature\": _reasoning_safe_temperature(self.model, 0.7),\n                \"max_tokens\": _reasoning_safe_max_tokens(self.model, 2000)\n            }\n            \n            # Add tools for all modes (TEXT_FORMAT still needs tools to work)\n            # TEXT_FORMAT only affects how conversation history is formatted, not tool availability\n            request_data[\"tools\"] = self._get_tools()\n            request_data[\"tool_choice\"] = \"auto\"\n            \n            # Make API call\n            api_start = time.time()\n            try:\n                response = self.client.chat.completions.create(**request_data)\n                \n                # Record TTFT for this iteration\n                iteration_ttft = time.time() - api_start\n                self.metrics.ttft_per_iteration.append(iteration_ttft)\n                \n                # Record first iteration TTFT separately for backwards compatibility\n                if iteration == 1:\n                    self.metrics.ttft = iteration_ttft\n                \n                # Extract response\n                message = response.choices[0].message\n                \n                # Print assistant content to console (always show, not just verbose)\n                if message.content:\n                    print(f\"\\n🤖 Assistant (Iteration {iteration}):\")\n                    print(\"-\" * 40)\n                    print(message.content)\n                    print(\"-\" * 40)\n                \n                # Log token usage and cache information\n                if hasattr(response, 'usage'):\n                    usage = response.usage\n                    self.metrics.prompt_tokens += usage.prompt_tokens\n                    self.metrics.completion_tokens += usage.completion_tokens\n                    \n                    # Check for cached tokens (Kimi specific)\n                    # The cached_tokens field appears directly in the usage object\n                    cached = 0\n                    if hasattr(usage, 'cached_tokens'):\n                        # Direct attribute on usage object\n                        cached = usage.cached_tokens if usage.cached_tokens is not None else 0\n                        self.metrics.cached_tokens += cached\n                        if cached > 0:\n                            self.metrics.cache_hits += 1\n                        else:\n                            self.metrics.cache_misses += 1\n                    else:\n                        # Try alternative locations\n                        if hasattr(usage, 'prompt_tokens_details'):\n                            details = usage.prompt_tokens_details\n                            if details and hasattr(details, 'cached_tokens'):\n                                cached = details.cached_tokens if details.cached_tokens is not None else 0\n                                self.metrics.cached_tokens += cached\n                                if cached > 0:\n                                    self.metrics.cache_hits += 1\n                                else:\n                                    self.metrics.cache_misses += 1\n                        \n                        # Debug logging when verbose and no cached tokens field found\n                        if self.verbose and iteration > 1 and cached == 0:\n                            logger.debug(f\"Usage object attributes: {dir(usage)}\")\n                            logger.debug(f\"Usage data: {usage}\")\n                    \n                    if self.verbose:\n                        # Log with TTFT for this iteration\n                        cache_info = f\", cached={cached}\" if cached > 0 else \"\"\n                        logger.info(f\"Iteration {iteration} - TTFT: {iteration_ttft:.3f}s, \"\n                                  f\"Tokens: prompt={usage.prompt_tokens}, \"\n                                  f\"completion={usage.completion_tokens}\"\n                                  f\"{cache_info}\")\n                \n",
  "total_lines": 888,
  "lines_read": 100,
  "offset": 640,
  "end_line": 740,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 5 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4,527 | 2,048 | 2,479 | 45.2% | 927 | 28.490s | system → user → assistant → tool → assistant → tool → assistant → tool → assistant → tool | read_file → find → grep |

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
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
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

**消息 9 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "read_file_3",
    "function": {
      "arguments": "{\"file_path\": \"chapter2/kv-cache/agent.py\", \"offset\": 640, \"size\": 100}",
      "name": "read_file"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 10 · 工具（`tool`）**

```text
{"path": "chapter2/kv-cache/agent.py", "content": "        while iteration < max_iterations:\n            iteration += 1\n            \n            # CRITICAL: Message handling for KV cache demonstration\n            # \n            # CORRECT mode: Build messages once on first iteration, then keep appending\n            #   - Maintains stable context \u2192 KV cache works efficiently\n            # \n            # INCORRECT modes: Recreate entire messages list from history each iteration\n            #   - Forces complete context reconstruction \u2192 KV cache invalidated\n            #   - Within an iteration, we still append to messages for proper API flow\n            #   - But at the start of each new iteration, we rebuild from scratch\n            \n            if self.mode == KVCacheMode.CORRECT:\n                # Correct mode: Build messages once, then keep using same list\n                if iteration == 1:\n                    messages = self._format_messages(original_task)\n            else:\n                # Incorrect modes: Recreate messages from history each iteration\n                # This forces cache invalidation due to context changes\n                messages = self._format_messages(original_task)\n            \n            # Prepare request\n            request_data = {\n                \"model\": self.model,\n                \"messages\": messages,\n                \"temperature\": _reasoning_safe_temperature(self.model, 0.7),\n                \"max_tokens\": _reasoning_safe_max_tokens(self.model, 2000)\n            }\n            \n            # Add tools for all modes (TEXT_FORMAT still needs tools to work)\n            # TEXT_FORMAT only affects how conversation history is formatted, not tool availability\n            request_data[\"tools\"] = self._get_tools()\n            request_data[\"tool_choice\"] = \"auto\"\n            \n            # Make API call\n            api_start = time.time()\n            try:\n                response = self.client.chat.completions.create(**request_data)\n                \n                # Record TTFT for this iteration\n                iteration_ttft = time.time() - api_start\n                self.metrics.ttft_per_iteration.append(iteration_ttft)\n                \n                # Record first iteration TTFT separately for backwards compatibility\n                if iteration == 1:\n                    self.metrics.ttft = iteration_ttft\n                \n                # Extract response\n                message = response.choices[0].message\n                \n                # Print assistant content to console (always show, not just verbose)\n                if message.content:\n                    print(f\"\\n\ud83e\udd16 Assistant (Iteration {iteration}):\")\n                    print(\"-\" * 40)\n                    print(message.content)\n                    print(\"-\" * 40)\n                \n                # Log token usage and cache information\n                if hasattr(response, 'usage'):\n                    usage = response.usage\n                    self.metrics.prompt_tokens += usage.prompt_tokens\n                    self.metrics.completion_tokens += usage.completion_tokens\n                    \n                    # Check for cached tokens (Kimi specific)\n                    # The cached_tokens field appears directly in the usage object\n                    cached = 0\n                    if hasattr(usage, 'cached_tokens'):\n                        # Direct attribute on usage object\n                        cached = usage.cached_tokens if usage.cached_tokens is not None else 0\n                        self.metrics.cached_tokens += cached\n                        if cached > 0:\n                            self.metrics.cache_hits += 1\n                        else:\n                            self.metrics.cache_misses += 1\n                    else:\n                        # Try alternative locations\n                        if hasattr(usage, 'prompt_tokens_details'):\n                            details = usage.prompt_tokens_details\n                            if details and hasattr(details, 'cached_tokens'):\n                                cached = details.cached_tokens if details.cached_tokens is not None else 0\n                                self.metrics.cached_tokens += cached\n                                if cached > 0:\n                                    self.metrics.cache_hits += 1\n                                else:\n                                    self.metrics.cache_misses += 1\n                        \n                        # Debug logging when verbose and no cached tokens field found\n                        if self.verbose and iteration > 1 and cached == 0:\n                            logger.debug(f\"Usage object attributes: {dir(usage)}\")\n                            logger.debug(f\"Usage data: {usage}\")\n                    \n                    if self.verbose:\n                        # Log with TTFT for this iteration\n                        cache_info = f\", cached={cached}\" if cached > 0 else \"\"\n                        logger.info(f\"Iteration {iteration} - TTFT: {iteration_ttft:.3f}s, \"\n                                  f\"Tokens: prompt={usage.prompt_tokens}, \"\n                                  f\"completion={usage.completion_tokens}\"\n                                  f\"{cache_info}\")\n                \n", "total_lines": 888, "lines_read": 100, "offset": 640, "end_line": 740, "truncated": false, "success": true}
```

</details>

**模型本轮回复**

```text
根据四步工具返回的证据，总结如下：

**实验目的**：通过对比正确与错误的上下文构造方式，演示 KV Cache 对推理首字延迟（TTFT）与 token 成本的影响。

**六种模式**：  
1. **CORRECT**——稳定上下文，首轮构建消息后持续追加；  
2. **DYNAMIC_SYSTEM**——系统提示携带时间戳，每轮变化；  
3. **SHUFFLED_TOOLS**——每轮打乱工具定义顺序；  
4. **DYNAMIC_PROFILE**——动态变更用户资料；  
5. **SLIDING_WINDOW**——仅保留最近 6 条消息；  
6. **TEXT_FORMAT**——将消息历史格式化为纯文本。  
后五种均为故意破坏前缀缓存的"错误"实现。

**请求构造差异**：CORRECT 模式只构建一次 `messages` 并在后续迭代中复用、追加；其余五种模式每轮都从零重建完整上下文，强制使 KV Cache 失效。

**最值得比较的指标**：`cached_tokens`（缓存命中令牌数）与 `TTFT`（首字延迟）。CORRECT 模式应呈现高 `cached_tokens` 与显著降低的迭代 TTFT，其余模式则相反，二者直接量化 KV Cache 带来的延迟与成本收益。
```

**该模式最终回答**

```text
根据四步工具返回的证据，总结如下：

**实验目的**：通过对比正确与错误的上下文构造方式，演示 KV Cache 对推理首字延迟（TTFT）与 token 成本的影响。

**六种模式**：  
1. **CORRECT**——稳定上下文，首轮构建消息后持续追加；  
2. **DYNAMIC_SYSTEM**——系统提示携带时间戳，每轮变化；  
3. **SHUFFLED_TOOLS**——每轮打乱工具定义顺序；  
4. **DYNAMIC_PROFILE**——动态变更用户资料；  
5. **SLIDING_WINDOW**——仅保留最近 6 条消息；  
6. **TEXT_FORMAT**——将消息历史格式化为纯文本。  
后五种均为故意破坏前缀缓存的"错误"实现。

**请求构造差异**：CORRECT 模式只构建一次 `messages` 并在后续迭代中复用、追加；其余五种模式每轮都从零重建完整上下文，强制使 KV Cache 失效。

**最值得比较的指标**：`cached_tokens`（缓存命中令牌数）与 `TTFT`（首字延迟）。CORRECT 模式应呈现高 `cached_tokens` 与显著降低的迭代 TTFT，其余模式则相反，二者直接量化 KV Cache 带来的延迟与成本收益。
```

### dynamic_system · 动态系统提示

机制：每轮在系统提示末尾追加不同时间戳。

结果：`success=True`，API 5 轮，工具调用 4 次，累计 Cache% 11.2%。

#### 第 1 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 665 | 256 | 409 | 38.5% | 75 | 3.759s | system → user | read_file → find → grep |

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

当前时间：2026-08-08 19:31:56.201825
```

**消息 2 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
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
| 997 | 256 | 741 | 25.7% | 68 | 4.308s | system → assistant → tool → user | read_file → find → grep |

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

当前时间：2026-08-08 19:31:59.961106
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
      "arguments": "{\"pattern\":\"*.py\",\"directory\":\"chapter2/kv-cache\"}",
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
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
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
| 1,891 | 256 | 1,635 | 13.5% | 131 | 3.922s | system → assistant → tool → assistant → tool → user | read_file → find → grep |

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

当前时间：2026-08-08 19:32:04.272023
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
      "arguments": "{\"pattern\":\"*.py\",\"directory\":\"chapter2/kv-cache\"}",
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
      "arguments": "{\"file_path\":\"chapter2/kv-cache/main.py\",\"offset\":0,\"size\":80}",
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
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
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
| 3,361 | 256 | 3,105 | 7.6% | 108 | 4.265s | system → assistant → tool → assistant → tool → assistant → tool → user | read_file → find → grep |

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

当前时间：2026-08-08 19:32:08.199809
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
      "arguments": "{\"pattern\":\"*.py\",\"directory\":\"chapter2/kv-cache\"}",
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
      "arguments": "{\"file_path\":\"chapter2/kv-cache/main.py\",\"offset\":0,\"size\":80}",
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
      "arguments": "{\"pattern\":\"class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens\",\"file_path\":\"chapter2/kv-cache/agent.py\"}",
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
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
```

</details>

**模型本轮回复**

工具调用 1：`read_file`

参数：

```json
{"file_path":"chapter2/kv-cache/agent.py","offset":640,"size":100}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "path": "chapter2/kv-cache/agent.py",
  "content": "        while iteration < max_iterations:\n            iteration += 1\n            \n            # CRITICAL: Message handling for KV cache demonstration\n            # \n            # CORRECT mode: Build messages once on first iteration, then keep appending\n            #   - Maintains stable context → KV cache works efficiently\n            # \n            # INCORRECT modes: Recreate entire messages list from history each iteration\n            #   - Forces complete context reconstruction → KV cache invalidated\n            #   - Within an iteration, we still append to messages for proper API flow\n            #   - But at the start of each new iteration, we rebuild from scratch\n            \n            if self.mode == KVCacheMode.CORRECT:\n                # Correct mode: Build messages once, then keep using same list\n                if iteration == 1:\n                    messages = self._format_messages(original_task)\n            else:\n                # Incorrect modes: Recreate messages from history each iteration\n                # This forces cache invalidation due to context changes\n                messages = self._format_messages(original_task)\n            \n            # Prepare request\n            request_data = {\n                \"model\": self.model,\n                \"messages\": messages,\n                \"temperature\": _reasoning_safe_temperature(self.model, 0.7),\n                \"max_tokens\": _reasoning_safe_max_tokens(self.model, 2000)\n            }\n            \n            # Add tools for all modes (TEXT_FORMAT still needs tools to work)\n            # TEXT_FORMAT only affects how conversation history is formatted, not tool availability\n            request_data[\"tools\"] = self._get_tools()\n            request_data[\"tool_choice\"] = \"auto\"\n            \n            # Make API call\n            api_start = time.time()\n            try:\n                response = self.client.chat.completions.create(**request_data)\n                \n                # Record TTFT for this iteration\n                iteration_ttft = time.time() - api_start\n                self.metrics.ttft_per_iteration.append(iteration_ttft)\n                \n                # Record first iteration TTFT separately for backwards compatibility\n                if iteration == 1:\n                    self.metrics.ttft = iteration_ttft\n                \n                # Extract response\n                message = response.choices[0].message\n                \n                # Print assistant content to console (always show, not just verbose)\n                if message.content:\n                    print(f\"\\n🤖 Assistant (Iteration {iteration}):\")\n                    print(\"-\" * 40)\n                    print(message.content)\n                    print(\"-\" * 40)\n                \n                # Log token usage and cache information\n                if hasattr(response, 'usage'):\n                    usage = response.usage\n                    self.metrics.prompt_tokens += usage.prompt_tokens\n                    self.metrics.completion_tokens += usage.completion_tokens\n                    \n                    # Check for cached tokens (Kimi specific)\n                    # The cached_tokens field appears directly in the usage object\n                    cached = 0\n                    if hasattr(usage, 'cached_tokens'):\n                        # Direct attribute on usage object\n                        cached = usage.cached_tokens if usage.cached_tokens is not None else 0\n                        self.metrics.cached_tokens += cached\n                        if cached > 0:\n                            self.metrics.cache_hits += 1\n                        else:\n                            self.metrics.cache_misses += 1\n                    else:\n                        # Try alternative locations\n                        if hasattr(usage, 'prompt_tokens_details'):\n                            details = usage.prompt_tokens_details\n                            if details and hasattr(details, 'cached_tokens'):\n                                cached = details.cached_tokens if details.cached_tokens is not None else 0\n                                self.metrics.cached_tokens += cached\n                                if cached > 0:\n                                    self.metrics.cache_hits += 1\n                                else:\n                                    self.metrics.cache_misses += 1\n                        \n                        # Debug logging when verbose and no cached tokens field found\n                        if self.verbose and iteration > 1 and cached == 0:\n                            logger.debug(f\"Usage object attributes: {dir(usage)}\")\n                            logger.debug(f\"Usage data: {usage}\")\n                    \n                    if self.verbose:\n                        # Log with TTFT for this iteration\n                        cache_info = f\", cached={cached}\" if cached > 0 else \"\"\n                        logger.info(f\"Iteration {iteration} - TTFT: {iteration_ttft:.3f}s, \"\n                                  f\"Tokens: prompt={usage.prompt_tokens}, \"\n                                  f\"completion={usage.completion_tokens}\"\n                                  f\"{cache_info}\")\n                \n",
  "total_lines": 888,
  "lines_read": 100,
  "offset": 640,
  "end_line": 740,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 5 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4,523 | 256 | 4,267 | 5.7% | 953 | 40.403s | system → assistant → tool → assistant → tool → assistant → tool → assistant → tool → user | read_file → find → grep |

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

当前时间：2026-08-08 19:32:12.467232
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
      "arguments": "{\"pattern\":\"*.py\",\"directory\":\"chapter2/kv-cache\"}",
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
      "arguments": "{\"file_path\":\"chapter2/kv-cache/main.py\",\"offset\":0,\"size\":80}",
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
      "arguments": "{\"pattern\":\"class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens\",\"file_path\":\"chapter2/kv-cache/agent.py\"}",
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

**消息 8 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "read_file_3",
    "function": {
      "arguments": "{\"file_path\":\"chapter2/kv-cache/agent.py\",\"offset\":640,\"size\":100}",
      "name": "read_file"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 9 · 工具（`tool`）**

```text
{"path": "chapter2/kv-cache/agent.py", "content": "        while iteration < max_iterations:\n            iteration += 1\n            \n            # CRITICAL: Message handling for KV cache demonstration\n            # \n            # CORRECT mode: Build messages once on first iteration, then keep appending\n            #   - Maintains stable context \u2192 KV cache works efficiently\n            # \n            # INCORRECT modes: Recreate entire messages list from history each iteration\n            #   - Forces complete context reconstruction \u2192 KV cache invalidated\n            #   - Within an iteration, we still append to messages for proper API flow\n            #   - But at the start of each new iteration, we rebuild from scratch\n            \n            if self.mode == KVCacheMode.CORRECT:\n                # Correct mode: Build messages once, then keep using same list\n                if iteration == 1:\n                    messages = self._format_messages(original_task)\n            else:\n                # Incorrect modes: Recreate messages from history each iteration\n                # This forces cache invalidation due to context changes\n                messages = self._format_messages(original_task)\n            \n            # Prepare request\n            request_data = {\n                \"model\": self.model,\n                \"messages\": messages,\n                \"temperature\": _reasoning_safe_temperature(self.model, 0.7),\n                \"max_tokens\": _reasoning_safe_max_tokens(self.model, 2000)\n            }\n            \n            # Add tools for all modes (TEXT_FORMAT still needs tools to work)\n            # TEXT_FORMAT only affects how conversation history is formatted, not tool availability\n            request_data[\"tools\"] = self._get_tools()\n            request_data[\"tool_choice\"] = \"auto\"\n            \n            # Make API call\n            api_start = time.time()\n            try:\n                response = self.client.chat.completions.create(**request_data)\n                \n                # Record TTFT for this iteration\n                iteration_ttft = time.time() - api_start\n                self.metrics.ttft_per_iteration.append(iteration_ttft)\n                \n                # Record first iteration TTFT separately for backwards compatibility\n                if iteration == 1:\n                    self.metrics.ttft = iteration_ttft\n                \n                # Extract response\n                message = response.choices[0].message\n                \n                # Print assistant content to console (always show, not just verbose)\n                if message.content:\n                    print(f\"\\n\ud83e\udd16 Assistant (Iteration {iteration}):\")\n                    print(\"-\" * 40)\n                    print(message.content)\n                    print(\"-\" * 40)\n                \n                # Log token usage and cache information\n                if hasattr(response, 'usage'):\n                    usage = response.usage\n                    self.metrics.prompt_tokens += usage.prompt_tokens\n                    self.metrics.completion_tokens += usage.completion_tokens\n                    \n                    # Check for cached tokens (Kimi specific)\n                    # The cached_tokens field appears directly in the usage object\n                    cached = 0\n                    if hasattr(usage, 'cached_tokens'):\n                        # Direct attribute on usage object\n                        cached = usage.cached_tokens if usage.cached_tokens is not None else 0\n                        self.metrics.cached_tokens += cached\n                        if cached > 0:\n                            self.metrics.cache_hits += 1\n                        else:\n                            self.metrics.cache_misses += 1\n                    else:\n                        # Try alternative locations\n                        if hasattr(usage, 'prompt_tokens_details'):\n                            details = usage.prompt_tokens_details\n                            if details and hasattr(details, 'cached_tokens'):\n                                cached = details.cached_tokens if details.cached_tokens is not None else 0\n                                self.metrics.cached_tokens += cached\n                                if cached > 0:\n                                    self.metrics.cache_hits += 1\n                                else:\n                                    self.metrics.cache_misses += 1\n                        \n                        # Debug logging when verbose and no cached tokens field found\n                        if self.verbose and iteration > 1 and cached == 0:\n                            logger.debug(f\"Usage object attributes: {dir(usage)}\")\n                            logger.debug(f\"Usage data: {usage}\")\n                    \n                    if self.verbose:\n                        # Log with TTFT for this iteration\n                        cache_info = f\", cached={cached}\" if cached > 0 else \"\"\n                        logger.info(f\"Iteration {iteration} - TTFT: {iteration_ttft:.3f}s, \"\n                                  f\"Tokens: prompt={usage.prompt_tokens}, \"\n                                  f\"completion={usage.completion_tokens}\"\n                                  f\"{cache_info}\")\n                \n", "total_lines": 888, "lines_read": 100, "offset": 640, "end_line": 740, "truncated": false, "success": true}
```

**消息 10 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
```

</details>

**模型本轮回复**

```text
实验旨在演示 KV 缓存的重要性，通过对比一种正确实现与五种常见错误实现，展示哪些做法会破坏前缀缓存、增加延迟与成本。

六种模式包括：**CORRECT**（正确实现，首次构建消息后持续复用追加，保持上下文稳定）；**DYNAMIC_SYSTEM**（系统提示带时间戳，每次变化）；**SHUFFLED_TOOLS**（每轮打乱工具顺序）；**DYNAMIC_PROFILE**（动态修改用户资料）；**SLIDING_WINDOW**（仅保留最近 6 条消息）；**TEXT_FORMAT**（将消息转为纯文本）。后五种均在每轮迭代重新构造完整消息列表，导致前缀缓存失效。

最值得比较的指标是 **`cached_tokens`**（直接反映缓存命中的 token 数量）与 **`TTFT`**（首 token 返回时间）。这两项最能量化 KV 缓存对推理速度和实际成本的提升效果。
```

**该模式最终回答**

```text
实验旨在演示 KV 缓存的重要性，通过对比一种正确实现与五种常见错误实现，展示哪些做法会破坏前缀缓存、增加延迟与成本。

六种模式包括：**CORRECT**（正确实现，首次构建消息后持续复用追加，保持上下文稳定）；**DYNAMIC_SYSTEM**（系统提示带时间戳，每次变化）；**SHUFFLED_TOOLS**（每轮打乱工具顺序）；**DYNAMIC_PROFILE**（动态修改用户资料）；**SLIDING_WINDOW**（仅保留最近 6 条消息）；**TEXT_FORMAT**（将消息转为纯文本）。后五种均在每轮迭代重新构造完整消息列表，导致前缀缓存失效。

最值得比较的指标是 **`cached_tokens`**（直接反映缓存命中的 token 数量）与 **`TTFT`**（首 token 返回时间）。这两项最能量化 KV 缓存对推理速度和实际成本的提升效果。
```

### shuffled_tools · 工具顺序变化

机制：每轮随机改变三个工具定义的顺序。

结果：`success=True`，API 5 轮，工具调用 4 次，累计 Cache% 19.6%。

#### 第 1 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 647 | 0 | 647 | 0.0% | 64 | 4.649s | system → user | find → read_file → grep |

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
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
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
| 968 | 256 | 712 | 26.4% | 89 | 3.580s | system → assistant → tool → user | grep → read_file → find |

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
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
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
| 1,883 | 256 | 1,627 | 13.6% | 249 | 8.086s | system → assistant → tool → assistant → tool → user | find → grep → read_file |

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
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
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
| 3,471 | 256 | 3,215 | 7.4% | 235 | 7.754s | system → assistant → tool → assistant → tool → assistant → tool → user | read_file → find → grep |

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
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
```

</details>

**模型本轮回复**

工具调用 1：`read_file`

参数：

```json
{"file_path": "chapter2/kv-cache/agent.py", "offset": 640, "size": 100}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "path": "chapter2/kv-cache/agent.py",
  "content": "        while iteration < max_iterations:\n            iteration += 1\n            \n            # CRITICAL: Message handling for KV cache demonstration\n            # \n            # CORRECT mode: Build messages once on first iteration, then keep appending\n            #   - Maintains stable context → KV cache works efficiently\n            # \n            # INCORRECT modes: Recreate entire messages list from history each iteration\n            #   - Forces complete context reconstruction → KV cache invalidated\n            #   - Within an iteration, we still append to messages for proper API flow\n            #   - But at the start of each new iteration, we rebuild from scratch\n            \n            if self.mode == KVCacheMode.CORRECT:\n                # Correct mode: Build messages once, then keep using same list\n                if iteration == 1:\n                    messages = self._format_messages(original_task)\n            else:\n                # Incorrect modes: Recreate messages from history each iteration\n                # This forces cache invalidation due to context changes\n                messages = self._format_messages(original_task)\n            \n            # Prepare request\n            request_data = {\n                \"model\": self.model,\n                \"messages\": messages,\n                \"temperature\": _reasoning_safe_temperature(self.model, 0.7),\n                \"max_tokens\": _reasoning_safe_max_tokens(self.model, 2000)\n            }\n            \n            # Add tools for all modes (TEXT_FORMAT still needs tools to work)\n            # TEXT_FORMAT only affects how conversation history is formatted, not tool availability\n            request_data[\"tools\"] = self._get_tools()\n            request_data[\"tool_choice\"] = \"auto\"\n            \n            # Make API call\n            api_start = time.time()\n            try:\n                response = self.client.chat.completions.create(**request_data)\n                \n                # Record TTFT for this iteration\n                iteration_ttft = time.time() - api_start\n                self.metrics.ttft_per_iteration.append(iteration_ttft)\n                \n                # Record first iteration TTFT separately for backwards compatibility\n                if iteration == 1:\n                    self.metrics.ttft = iteration_ttft\n                \n                # Extract response\n                message = response.choices[0].message\n                \n                # Print assistant content to console (always show, not just verbose)\n                if message.content:\n                    print(f\"\\n🤖 Assistant (Iteration {iteration}):\")\n                    print(\"-\" * 40)\n                    print(message.content)\n                    print(\"-\" * 40)\n                \n                # Log token usage and cache information\n                if hasattr(response, 'usage'):\n                    usage = response.usage\n                    self.metrics.prompt_tokens += usage.prompt_tokens\n                    self.metrics.completion_tokens += usage.completion_tokens\n                    \n                    # Check for cached tokens (Kimi specific)\n                    # The cached_tokens field appears directly in the usage object\n                    cached = 0\n                    if hasattr(usage, 'cached_tokens'):\n                        # Direct attribute on usage object\n                        cached = usage.cached_tokens if usage.cached_tokens is not None else 0\n                        self.metrics.cached_tokens += cached\n                        if cached > 0:\n                            self.metrics.cache_hits += 1\n                        else:\n                            self.metrics.cache_misses += 1\n                    else:\n                        # Try alternative locations\n                        if hasattr(usage, 'prompt_tokens_details'):\n                            details = usage.prompt_tokens_details\n                            if details and hasattr(details, 'cached_tokens'):\n                                cached = details.cached_tokens if details.cached_tokens is not None else 0\n                                self.metrics.cached_tokens += cached\n                                if cached > 0:\n                                    self.metrics.cache_hits += 1\n                                else:\n                                    self.metrics.cache_misses += 1\n                        \n                        # Debug logging when verbose and no cached tokens field found\n                        if self.verbose and iteration > 1 and cached == 0:\n                            logger.debug(f\"Usage object attributes: {dir(usage)}\")\n                            logger.debug(f\"Usage data: {usage}\")\n                    \n                    if self.verbose:\n                        # Log with TTFT for this iteration\n                        cache_info = f\", cached={cached}\" if cached > 0 else \"\"\n                        logger.info(f\"Iteration {iteration} - TTFT: {iteration_ttft:.3f}s, \"\n                                  f\"Tokens: prompt={usage.prompt_tokens}, \"\n                                  f\"completion={usage.completion_tokens}\"\n                                  f\"{cache_info}\")\n                \n",
  "total_lines": 888,
  "lines_read": 100,
  "offset": 640,
  "end_line": 740,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 5 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4,760 | 1,536 | 3,224 | 32.3% | 834 | 25.243s | system → assistant → tool → assistant → tool → assistant → tool → assistant → tool → user | find → grep → read_file |

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

**消息 8 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "read_file_3",
    "function": {
      "arguments": "{\"file_path\": \"chapter2/kv-cache/agent.py\", \"offset\": 640, \"size\": 100}",
      "name": "read_file"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 9 · 工具（`tool`）**

```text
{"path": "chapter2/kv-cache/agent.py", "content": "        while iteration < max_iterations:\n            iteration += 1\n            \n            # CRITICAL: Message handling for KV cache demonstration\n            # \n            # CORRECT mode: Build messages once on first iteration, then keep appending\n            #   - Maintains stable context \u2192 KV cache works efficiently\n            # \n            # INCORRECT modes: Recreate entire messages list from history each iteration\n            #   - Forces complete context reconstruction \u2192 KV cache invalidated\n            #   - Within an iteration, we still append to messages for proper API flow\n            #   - But at the start of each new iteration, we rebuild from scratch\n            \n            if self.mode == KVCacheMode.CORRECT:\n                # Correct mode: Build messages once, then keep using same list\n                if iteration == 1:\n                    messages = self._format_messages(original_task)\n            else:\n                # Incorrect modes: Recreate messages from history each iteration\n                # This forces cache invalidation due to context changes\n                messages = self._format_messages(original_task)\n            \n            # Prepare request\n            request_data = {\n                \"model\": self.model,\n                \"messages\": messages,\n                \"temperature\": _reasoning_safe_temperature(self.model, 0.7),\n                \"max_tokens\": _reasoning_safe_max_tokens(self.model, 2000)\n            }\n            \n            # Add tools for all modes (TEXT_FORMAT still needs tools to work)\n            # TEXT_FORMAT only affects how conversation history is formatted, not tool availability\n            request_data[\"tools\"] = self._get_tools()\n            request_data[\"tool_choice\"] = \"auto\"\n            \n            # Make API call\n            api_start = time.time()\n            try:\n                response = self.client.chat.completions.create(**request_data)\n                \n                # Record TTFT for this iteration\n                iteration_ttft = time.time() - api_start\n                self.metrics.ttft_per_iteration.append(iteration_ttft)\n                \n                # Record first iteration TTFT separately for backwards compatibility\n                if iteration == 1:\n                    self.metrics.ttft = iteration_ttft\n                \n                # Extract response\n                message = response.choices[0].message\n                \n                # Print assistant content to console (always show, not just verbose)\n                if message.content:\n                    print(f\"\\n\ud83e\udd16 Assistant (Iteration {iteration}):\")\n                    print(\"-\" * 40)\n                    print(message.content)\n                    print(\"-\" * 40)\n                \n                # Log token usage and cache information\n                if hasattr(response, 'usage'):\n                    usage = response.usage\n                    self.metrics.prompt_tokens += usage.prompt_tokens\n                    self.metrics.completion_tokens += usage.completion_tokens\n                    \n                    # Check for cached tokens (Kimi specific)\n                    # The cached_tokens field appears directly in the usage object\n                    cached = 0\n                    if hasattr(usage, 'cached_tokens'):\n                        # Direct attribute on usage object\n                        cached = usage.cached_tokens if usage.cached_tokens is not None else 0\n                        self.metrics.cached_tokens += cached\n                        if cached > 0:\n                            self.metrics.cache_hits += 1\n                        else:\n                            self.metrics.cache_misses += 1\n                    else:\n                        # Try alternative locations\n                        if hasattr(usage, 'prompt_tokens_details'):\n                            details = usage.prompt_tokens_details\n                            if details and hasattr(details, 'cached_tokens'):\n                                cached = details.cached_tokens if details.cached_tokens is not None else 0\n                                self.metrics.cached_tokens += cached\n                                if cached > 0:\n                                    self.metrics.cache_hits += 1\n                                else:\n                                    self.metrics.cache_misses += 1\n                        \n                        # Debug logging when verbose and no cached tokens field found\n                        if self.verbose and iteration > 1 and cached == 0:\n                            logger.debug(f\"Usage object attributes: {dir(usage)}\")\n                            logger.debug(f\"Usage data: {usage}\")\n                    \n                    if self.verbose:\n                        # Log with TTFT for this iteration\n                        cache_info = f\", cached={cached}\" if cached > 0 else \"\"\n                        logger.info(f\"Iteration {iteration} - TTFT: {iteration_ttft:.3f}s, \"\n                                  f\"Tokens: prompt={usage.prompt_tokens}, \"\n                                  f\"completion={usage.completion_tokens}\"\n                                  f\"{cache_info}\")\n                \n", "total_lines": 888, "lines_read": 100, "offset": 640, "end_line": 740, "truncated": false, "success": true}
```

**消息 10 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
```

</details>

**模型本轮回复**

```text
实验通过对比六种 KV 缓存构造方式，验证前缀缓存对推理延迟的影响。正确模式仅在首轮构建消息列表并持续追加，其余五种错误模式每轮都重建上下文：动态系统提示、打乱工具顺序、动态用户画像、滑动窗口截断、纯文本格式。后五种均会破坏前缀一致性，导致 KV 缓存失效。最值得比较的指标是每轮首 Token 延迟（TTFT）与缓存 Token 数（cached_tokens），前者直接反映缓存加速效果，后者量化命中规模。
```

**该模式最终回答**

```text
实验通过对比六种 KV 缓存构造方式，验证前缀缓存对推理延迟的影响。正确模式仅在首轮构建消息列表并持续追加，其余五种错误模式每轮都重建上下文：动态系统提示、打乱工具顺序、动态用户画像、滑动窗口截断、纯文本格式。后五种均会破坏前缀一致性，导致 KV 缓存失效。最值得比较的指标是每轮首 Token 延迟（TTFT）与缓存 Token 数（cached_tokens），前者直接反映缓存加速效果，后者量化命中规模。
```

### dynamic_profile · 动态用户资料

机制：每轮在靠前位置加入不断变化的剩余额度。

结果：`success=True`，API 5 轮，工具调用 4 次，累计 Cache% 9.0%。

#### 第 1 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 665 | 256 | 409 | 38.5% | 78 | 3.726s | system → user → user | read_file → find → grep |

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
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
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
| 1,000 | 256 | 744 | 25.6% | 81 | 2.668s | system → user → assistant → tool → user | read_file → find → grep |

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

**消息 5 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
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
| 1,907 | 256 | 1,651 | 13.4% | 123 | 4.272s | system → user → assistant → tool → assistant → tool → user | read_file → find → grep |

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

**消息 7 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
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
| 3,369 | 256 | 3,113 | 7.6% | 71 | 3.211s | system → user → assistant → tool → assistant → tool → assistant → tool → user | read_file → find → grep |

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

**消息 9 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
```

</details>

**模型本轮回复**

工具调用 1：`read_file`

参数：

```json
{"file_path": "chapter2/kv-cache/agent.py", "offset": 640, "size": 100}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "path": "chapter2/kv-cache/agent.py",
  "content": "        while iteration < max_iterations:\n            iteration += 1\n            \n            # CRITICAL: Message handling for KV cache demonstration\n            # \n            # CORRECT mode: Build messages once on first iteration, then keep appending\n            #   - Maintains stable context → KV cache works efficiently\n            # \n            # INCORRECT modes: Recreate entire messages list from history each iteration\n            #   - Forces complete context reconstruction → KV cache invalidated\n            #   - Within an iteration, we still append to messages for proper API flow\n            #   - But at the start of each new iteration, we rebuild from scratch\n            \n            if self.mode == KVCacheMode.CORRECT:\n                # Correct mode: Build messages once, then keep using same list\n                if iteration == 1:\n                    messages = self._format_messages(original_task)\n            else:\n                # Incorrect modes: Recreate messages from history each iteration\n                # This forces cache invalidation due to context changes\n                messages = self._format_messages(original_task)\n            \n            # Prepare request\n            request_data = {\n                \"model\": self.model,\n                \"messages\": messages,\n                \"temperature\": _reasoning_safe_temperature(self.model, 0.7),\n                \"max_tokens\": _reasoning_safe_max_tokens(self.model, 2000)\n            }\n            \n            # Add tools for all modes (TEXT_FORMAT still needs tools to work)\n            # TEXT_FORMAT only affects how conversation history is formatted, not tool availability\n            request_data[\"tools\"] = self._get_tools()\n            request_data[\"tool_choice\"] = \"auto\"\n            \n            # Make API call\n            api_start = time.time()\n            try:\n                response = self.client.chat.completions.create(**request_data)\n                \n                # Record TTFT for this iteration\n                iteration_ttft = time.time() - api_start\n                self.metrics.ttft_per_iteration.append(iteration_ttft)\n                \n                # Record first iteration TTFT separately for backwards compatibility\n                if iteration == 1:\n                    self.metrics.ttft = iteration_ttft\n                \n                # Extract response\n                message = response.choices[0].message\n                \n                # Print assistant content to console (always show, not just verbose)\n                if message.content:\n                    print(f\"\\n🤖 Assistant (Iteration {iteration}):\")\n                    print(\"-\" * 40)\n                    print(message.content)\n                    print(\"-\" * 40)\n                \n                # Log token usage and cache information\n                if hasattr(response, 'usage'):\n                    usage = response.usage\n                    self.metrics.prompt_tokens += usage.prompt_tokens\n                    self.metrics.completion_tokens += usage.completion_tokens\n                    \n                    # Check for cached tokens (Kimi specific)\n                    # The cached_tokens field appears directly in the usage object\n                    cached = 0\n                    if hasattr(usage, 'cached_tokens'):\n                        # Direct attribute on usage object\n                        cached = usage.cached_tokens if usage.cached_tokens is not None else 0\n                        self.metrics.cached_tokens += cached\n                        if cached > 0:\n                            self.metrics.cache_hits += 1\n                        else:\n                            self.metrics.cache_misses += 1\n                    else:\n                        # Try alternative locations\n                        if hasattr(usage, 'prompt_tokens_details'):\n                            details = usage.prompt_tokens_details\n                            if details and hasattr(details, 'cached_tokens'):\n                                cached = details.cached_tokens if details.cached_tokens is not None else 0\n                                self.metrics.cached_tokens += cached\n                                if cached > 0:\n                                    self.metrics.cache_hits += 1\n                                else:\n                                    self.metrics.cache_misses += 1\n                        \n                        # Debug logging when verbose and no cached tokens field found\n                        if self.verbose and iteration > 1 and cached == 0:\n                            logger.debug(f\"Usage object attributes: {dir(usage)}\")\n                            logger.debug(f\"Usage data: {usage}\")\n                    \n                    if self.verbose:\n                        # Log with TTFT for this iteration\n                        cache_info = f\", cached={cached}\" if cached > 0 else \"\"\n                        logger.info(f\"Iteration {iteration} - TTFT: {iteration_ttft:.3f}s, \"\n                                  f\"Tokens: prompt={usage.prompt_tokens}, \"\n                                  f\"completion={usage.completion_tokens}\"\n                                  f\"{cache_info}\")\n                \n",
  "total_lines": 888,
  "lines_read": 100,
  "offset": 640,
  "end_line": 740,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 5 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4,494 | 0 | 4,494 | 0.0% | 1,012 | 18.733s | system → user → assistant → tool → assistant → tool → assistant → tool → assistant → tool → user | read_file → find → grep |

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
[用户资料：高级用户，剩余 95 点额度]
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

**消息 9 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "read_file_3",
    "function": {
      "arguments": "{\"file_path\": \"chapter2/kv-cache/agent.py\", \"offset\": 640, \"size\": 100}",
      "name": "read_file"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 10 · 工具（`tool`）**

```text
{"path": "chapter2/kv-cache/agent.py", "content": "        while iteration < max_iterations:\n            iteration += 1\n            \n            # CRITICAL: Message handling for KV cache demonstration\n            # \n            # CORRECT mode: Build messages once on first iteration, then keep appending\n            #   - Maintains stable context \u2192 KV cache works efficiently\n            # \n            # INCORRECT modes: Recreate entire messages list from history each iteration\n            #   - Forces complete context reconstruction \u2192 KV cache invalidated\n            #   - Within an iteration, we still append to messages for proper API flow\n            #   - But at the start of each new iteration, we rebuild from scratch\n            \n            if self.mode == KVCacheMode.CORRECT:\n                # Correct mode: Build messages once, then keep using same list\n                if iteration == 1:\n                    messages = self._format_messages(original_task)\n            else:\n                # Incorrect modes: Recreate messages from history each iteration\n                # This forces cache invalidation due to context changes\n                messages = self._format_messages(original_task)\n            \n            # Prepare request\n            request_data = {\n                \"model\": self.model,\n                \"messages\": messages,\n                \"temperature\": _reasoning_safe_temperature(self.model, 0.7),\n                \"max_tokens\": _reasoning_safe_max_tokens(self.model, 2000)\n            }\n            \n            # Add tools for all modes (TEXT_FORMAT still needs tools to work)\n            # TEXT_FORMAT only affects how conversation history is formatted, not tool availability\n            request_data[\"tools\"] = self._get_tools()\n            request_data[\"tool_choice\"] = \"auto\"\n            \n            # Make API call\n            api_start = time.time()\n            try:\n                response = self.client.chat.completions.create(**request_data)\n                \n                # Record TTFT for this iteration\n                iteration_ttft = time.time() - api_start\n                self.metrics.ttft_per_iteration.append(iteration_ttft)\n                \n                # Record first iteration TTFT separately for backwards compatibility\n                if iteration == 1:\n                    self.metrics.ttft = iteration_ttft\n                \n                # Extract response\n                message = response.choices[0].message\n                \n                # Print assistant content to console (always show, not just verbose)\n                if message.content:\n                    print(f\"\\n\ud83e\udd16 Assistant (Iteration {iteration}):\")\n                    print(\"-\" * 40)\n                    print(message.content)\n                    print(\"-\" * 40)\n                \n                # Log token usage and cache information\n                if hasattr(response, 'usage'):\n                    usage = response.usage\n                    self.metrics.prompt_tokens += usage.prompt_tokens\n                    self.metrics.completion_tokens += usage.completion_tokens\n                    \n                    # Check for cached tokens (Kimi specific)\n                    # The cached_tokens field appears directly in the usage object\n                    cached = 0\n                    if hasattr(usage, 'cached_tokens'):\n                        # Direct attribute on usage object\n                        cached = usage.cached_tokens if usage.cached_tokens is not None else 0\n                        self.metrics.cached_tokens += cached\n                        if cached > 0:\n                            self.metrics.cache_hits += 1\n                        else:\n                            self.metrics.cache_misses += 1\n                    else:\n                        # Try alternative locations\n                        if hasattr(usage, 'prompt_tokens_details'):\n                            details = usage.prompt_tokens_details\n                            if details and hasattr(details, 'cached_tokens'):\n                                cached = details.cached_tokens if details.cached_tokens is not None else 0\n                                self.metrics.cached_tokens += cached\n                                if cached > 0:\n                                    self.metrics.cache_hits += 1\n                                else:\n                                    self.metrics.cache_misses += 1\n                        \n                        # Debug logging when verbose and no cached tokens field found\n                        if self.verbose and iteration > 1 and cached == 0:\n                            logger.debug(f\"Usage object attributes: {dir(usage)}\")\n                            logger.debug(f\"Usage data: {usage}\")\n                    \n                    if self.verbose:\n                        # Log with TTFT for this iteration\n                        cache_info = f\", cached={cached}\" if cached > 0 else \"\"\n                        logger.info(f\"Iteration {iteration} - TTFT: {iteration_ttft:.3f}s, \"\n                                  f\"Tokens: prompt={usage.prompt_tokens}, \"\n                                  f\"completion={usage.completion_tokens}\"\n                                  f\"{cache_info}\")\n                \n", "total_lines": 888, "lines_read": 100, "offset": 640, "end_line": 740, "truncated": false, "success": true}
```

**消息 11 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
```

</details>

**模型本轮回复**

```text
实验目的是验证 KV Cache 对多轮对话性能的影响，通过正确与错误实现对照，展示稳定上下文对缓存命中的决定性作用。六种模式包括：CORRECT（正确实现，保持上下文稳定）、DYNAMIC_SYSTEM（每轮变更系统提示）、SHUFFLED_TOOLS（打乱工具顺序）、DYNAMIC_PROFILE（动态用户资料）、SLIDING_WINDOW（仅保留最近6条消息）、TEXT_FORMAT（改用纯文本格式）。后五种均因改变请求结构而破坏前缀缓存。最值得比较的指标是 TTFT（首Token延迟）与 cached_tokens（缓存Token数）：前者直接反映缓存生效带来的响应速度差异，后者由模型直接返回，可量化缓存命中规模。
```

**该模式最终回答**

```text
实验目的是验证 KV Cache 对多轮对话性能的影响，通过正确与错误实现对照，展示稳定上下文对缓存命中的决定性作用。六种模式包括：CORRECT（正确实现，保持上下文稳定）、DYNAMIC_SYSTEM（每轮变更系统提示）、SHUFFLED_TOOLS（打乱工具顺序）、DYNAMIC_PROFILE（动态用户资料）、SLIDING_WINDOW（仅保留最近6条消息）、TEXT_FORMAT（改用纯文本格式）。后五种均因改变请求结构而破坏前缀缓存。最值得比较的指标是 TTFT（首Token延迟）与 cached_tokens（缓存Token数）：前者直接反映缓存生效带来的响应速度差异，后者由模型直接返回，可量化缓存命中规模。
```

### sliding_window · 滑动窗口

机制：每轮只保留最近约六条历史消息。

结果：`success=True`，API 5 轮，工具调用 4 次，累计 Cache% 29.0%。

#### 第 1 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 647 | 647 | 0 | 100.0% | 64 | 5.196s | system → user | read_file → find → grep |

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
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
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
| 968 | 256 | 712 | 26.4% | 97 | 3.222s | system → assistant → tool → user | read_file → find → grep |

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
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
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
| 1,891 | 512 | 1,379 | 27.1% | 138 | 4.411s | system → assistant → tool → assistant → tool → user | read_file → find → grep |

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
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
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
| 3,368 | 1,536 | 1,832 | 45.6% | 78 | 2.787s | system → assistant → tool → assistant → tool → assistant → tool → user | read_file → find → grep |

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
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
```

</details>

**模型本轮回复**

工具调用 1：`read_file`

参数：

```json
{"file_path": "chapter2/kv-cache/agent.py", "offset": 640, "size": 100}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "path": "chapter2/kv-cache/agent.py",
  "content": "        while iteration < max_iterations:\n            iteration += 1\n            \n            # CRITICAL: Message handling for KV cache demonstration\n            # \n            # CORRECT mode: Build messages once on first iteration, then keep appending\n            #   - Maintains stable context → KV cache works efficiently\n            # \n            # INCORRECT modes: Recreate entire messages list from history each iteration\n            #   - Forces complete context reconstruction → KV cache invalidated\n            #   - Within an iteration, we still append to messages for proper API flow\n            #   - But at the start of each new iteration, we rebuild from scratch\n            \n            if self.mode == KVCacheMode.CORRECT:\n                # Correct mode: Build messages once, then keep using same list\n                if iteration == 1:\n                    messages = self._format_messages(original_task)\n            else:\n                # Incorrect modes: Recreate messages from history each iteration\n                # This forces cache invalidation due to context changes\n                messages = self._format_messages(original_task)\n            \n            # Prepare request\n            request_data = {\n                \"model\": self.model,\n                \"messages\": messages,\n                \"temperature\": _reasoning_safe_temperature(self.model, 0.7),\n                \"max_tokens\": _reasoning_safe_max_tokens(self.model, 2000)\n            }\n            \n            # Add tools for all modes (TEXT_FORMAT still needs tools to work)\n            # TEXT_FORMAT only affects how conversation history is formatted, not tool availability\n            request_data[\"tools\"] = self._get_tools()\n            request_data[\"tool_choice\"] = \"auto\"\n            \n            # Make API call\n            api_start = time.time()\n            try:\n                response = self.client.chat.completions.create(**request_data)\n                \n                # Record TTFT for this iteration\n                iteration_ttft = time.time() - api_start\n                self.metrics.ttft_per_iteration.append(iteration_ttft)\n                \n                # Record first iteration TTFT separately for backwards compatibility\n                if iteration == 1:\n                    self.metrics.ttft = iteration_ttft\n                \n                # Extract response\n                message = response.choices[0].message\n                \n                # Print assistant content to console (always show, not just verbose)\n                if message.content:\n                    print(f\"\\n🤖 Assistant (Iteration {iteration}):\")\n                    print(\"-\" * 40)\n                    print(message.content)\n                    print(\"-\" * 40)\n                \n                # Log token usage and cache information\n                if hasattr(response, 'usage'):\n                    usage = response.usage\n                    self.metrics.prompt_tokens += usage.prompt_tokens\n                    self.metrics.completion_tokens += usage.completion_tokens\n                    \n                    # Check for cached tokens (Kimi specific)\n                    # The cached_tokens field appears directly in the usage object\n                    cached = 0\n                    if hasattr(usage, 'cached_tokens'):\n                        # Direct attribute on usage object\n                        cached = usage.cached_tokens if usage.cached_tokens is not None else 0\n                        self.metrics.cached_tokens += cached\n                        if cached > 0:\n                            self.metrics.cache_hits += 1\n                        else:\n                            self.metrics.cache_misses += 1\n                    else:\n                        # Try alternative locations\n                        if hasattr(usage, 'prompt_tokens_details'):\n                            details = usage.prompt_tokens_details\n                            if details and hasattr(details, 'cached_tokens'):\n                                cached = details.cached_tokens if details.cached_tokens is not None else 0\n                                self.metrics.cached_tokens += cached\n                                if cached > 0:\n                                    self.metrics.cache_hits += 1\n                                else:\n                                    self.metrics.cache_misses += 1\n                        \n                        # Debug logging when verbose and no cached tokens field found\n                        if self.verbose and iteration > 1 and cached == 0:\n                            logger.debug(f\"Usage object attributes: {dir(usage)}\")\n                            logger.debug(f\"Usage data: {usage}\")\n                    \n                    if self.verbose:\n                        # Log with TTFT for this iteration\n                        cache_info = f\", cached={cached}\" if cached > 0 else \"\"\n                        logger.info(f\"Iteration {iteration} - TTFT: {iteration_ttft:.3f}s, \"\n                                  f\"Tokens: prompt={usage.prompt_tokens}, \"\n                                  f\"completion={usage.completion_tokens}\"\n                                  f\"{cache_info}\")\n                \n",
  "total_lines": 888,
  "lines_read": 100,
  "offset": 640,
  "end_line": 740,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 5 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4,179 | 256 | 3,923 | 6.1% | 479 | 13.207s | system → assistant → tool → assistant → tool → assistant → tool → user | read_file → find → grep |

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

**消息 3 · 工具（`tool`）**

```text
{"path": "chapter2/kv-cache/main.py", "content": "\"\"\"\nMain script to demonstrate KV cache importance\nRuns the ReAct agent with different implementations and compares performance\n\"\"\"\n\nimport os\nimport sys\nimport glob\nimport json\nimport argparse\nimport logging\nfrom typing import Dict, List, Any\nfrom datetime import datetime\nfrom dataclasses import asdict\n\ntry:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n\nfrom agent import KVCacheAgent, KVCacheMode, AgentMetrics, compare_implementations\n\n# Default model (Moonshot / Kimi). The whole current Kimi family (k2.5/k2.6/\n# k2.7/k3) reports cached_tokens for automatic prefix caching AND reasons, so it\n# only accepts temperature=1 (agent.py handles that automatically). kimi-k2.6 has\n# the lightest reasoning footprint of the cache-reporting models, giving the\n# cleanest TTFT while still exposing the prefix-cache hit metric this demo needs.\n# (The non-reasoning moonshot-v1-* models do NOT report cached_tokens, so they\n# cannot demonstrate the cache effect.)\nDEFAULT_MODEL = \"kimi-k2.6\"\nDEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), \"../..\"))\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format='%(asctime)s - %(levelname)s - %(message)s',\n    handlers=[\n        logging.FileHandler('kv_cache_demo.log'),\n        logging.StreamHandler()\n    ]\n)\nlogger = logging.getLogger(__name__)\n\n\n# ---------------------------------------------------------------------------\n# Metrics helpers (shared by live comparison and offline report)\n# ---------------------------------------------------------------------------\n\ndef _coerce_metrics(metrics: Any) -> Dict[str, Any]:\n    \"\"\"Normalize a stored metrics value into a plain dict.\n\n    Handles both formats found in result files:\n      - dict: produced by --compare (asdict) and by the fixed --mode path\n      - str : legacy single-mode files that stored repr(AgentMetrics(...))\n              because json.dump used default=str\n    \"\"\"\n    if isinstance(metrics, dict):\n        return metrics\n    if isinstance(metrics, str) and metrics.startswith(\"AgentMetrics(\"):\n        # Safe eval: only AgentMetrics is exposed, no builtins.\n        try:\n            obj = eval(metrics, {\"__builtins__\": {}}, {\"AgentMetrics\": AgentMetrics})\n            return asdict(obj)\n        except Exception as e:  # pragma: no cover - defensive\n            logger.warning(f\"Could not parse legacy metrics string: {e}\")\n    return {}\n\n\ndef _avg_ttft(m: Dict[str, Any]) -> float:\n    \"\"\"Average TTFT across iterations, falling back to first-iteration TTFT.\"\"\"\n    lst = m.get(\"ttft_per_iteration\") or []\n    return sum(lst) / len(lst) if lst else float(m.get(\"ttft\", 0.0) or 0.0)\n\n\ndef _hit_rate(m: Dict[str, Any]) -> float:\n    total = (m.get(\"cache_hits\", 0) or 0) + (m.get(\"cache_misses\", 0) or 0)\n    return (m.get(\"cache_hits\", 0) or 0) / total * 100 if total else 0.0\n\n\n", "total_lines": 548, "lines_read": 80, "offset": 0, "end_line": 80, "truncated": false, "success": true}
```

**消息 4 · 助手（`assistant`）**

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

**消息 5 · 工具（`tool`）**

```text
{"pattern": "class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens", "matches": [{"file": "chapter2/kv-cache/agent.py", "line_num": 3, "line": "Demonstrates the importance of KV cache through correct and incorrect implementations."}, {"file": "chapter2/kv-cache/agent.py", "line_num": 33, "line": "chat models do NOT reason (and also do not report cached_tokens).\"\"\""}, {"file": "chapter2/kv-cache/agent.py", "line_num": 59, "line": "class KVCacheMode(Enum):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 61, "line": "CORRECT = \"correct\"  # Correct implementation with stable context"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 62, "line": "DYNAMIC_SYSTEM = \"dynamic_system\"  # Changing system prompt with timestamp"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 63, "line": "SHUFFLED_TOOLS = \"shuffled_tools\"  # Shuffling tool order each request"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 64, "line": "DYNAMIC_PROFILE = \"dynamic_profile\"  # Changing user profile with credits"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 65, "line": "SLIDING_WINDOW = \"sliding_window\"  # Only keeping recent 6 messages"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 66, "line": "TEXT_FORMAT = \"text_format\"  # Formatting messages as plain text"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 91, "line": "cached_tokens: int = 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 357, "line": "def __init__(self, api_key: str, mode: KVCacheMode = KVCacheMode.CORRECT,"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 486, "line": "if self.mode == KVCacheMode.DYNAMIC_SYSTEM:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 497, "line": "if self.mode == KVCacheMode.SHUFFLED_TOOLS:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 505, "line": "if self.mode == KVCacheMode.DYNAMIC_PROFILE:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 514, "line": "\"\"\"Format messages based on mode - recreated each iteration for incorrect modes\"\"\""}, {"file": "chapter2/kv-cache/agent.py", "line_num": 517, "line": "# Add system prompt (changes each time for DYNAMIC_SYSTEM mode)"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 528, "line": "if self.mode == KVCacheMode.SLIDING_WINDOW:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 540, "line": "elif self.mode == KVCacheMode.TEXT_FORMAT:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 575, "line": "# For CORRECT, DYNAMIC_SYSTEM, SHUFFLED_TOOLS, DYNAMIC_PROFILE modes"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 646, "line": "# CORRECT mode: Build messages once on first iteration, then keep appending"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 649, "line": "# INCORRECT modes: Recreate entire messages list from history each iteration"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 654, "line": "if self.mode == KVCacheMode.CORRECT:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 655, "line": "# Correct mode: Build messages once, then keep using same list"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 659, "line": "# Incorrect modes: Recreate messages from history each iteration"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 671, "line": "# Add tools for all modes (TEXT_FORMAT still needs tools to work)"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 672, "line": "# TEXT_FORMAT only affects how conversation history is formatted, not tool availability"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 706, "line": "# The cached_tokens field appears directly in the usage object"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 708, "line": "if hasattr(usage, 'cached_tokens'):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 710, "line": "cached = usage.cached_tokens if usage.cached_tokens is not None else 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 711, "line": "self.metrics.cached_tokens += cached"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 720, "line": "if details and hasattr(details, 'cached_tokens'):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 721, "line": "cached = details.cached_tokens if details.cached_tokens is not None else 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 722, "line": "self.metrics.cached_tokens += cached"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 883, "line": "logger.info(f\"Cached Tokens: {metrics.cached_tokens}\")"}], "files_searched": 1, "match_count": 34, "truncated": false, "success": true}
```

**消息 6 · 助手（`assistant`）**

```text

```

工具调用声明：

```json
[
  {
    "id": "read_file_3",
    "function": {
      "arguments": "{\"file_path\": \"chapter2/kv-cache/agent.py\", \"offset\": 640, \"size\": 100}",
      "name": "read_file"
    },
    "type": "function",
    "index": 0
  }
]
```

**消息 7 · 工具（`tool`）**

```text
{"path": "chapter2/kv-cache/agent.py", "content": "        while iteration < max_iterations:\n            iteration += 1\n            \n            # CRITICAL: Message handling for KV cache demonstration\n            # \n            # CORRECT mode: Build messages once on first iteration, then keep appending\n            #   - Maintains stable context \u2192 KV cache works efficiently\n            # \n            # INCORRECT modes: Recreate entire messages list from history each iteration\n            #   - Forces complete context reconstruction \u2192 KV cache invalidated\n            #   - Within an iteration, we still append to messages for proper API flow\n            #   - But at the start of each new iteration, we rebuild from scratch\n            \n            if self.mode == KVCacheMode.CORRECT:\n                # Correct mode: Build messages once, then keep using same list\n                if iteration == 1:\n                    messages = self._format_messages(original_task)\n            else:\n                # Incorrect modes: Recreate messages from history each iteration\n                # This forces cache invalidation due to context changes\n                messages = self._format_messages(original_task)\n            \n            # Prepare request\n            request_data = {\n                \"model\": self.model,\n                \"messages\": messages,\n                \"temperature\": _reasoning_safe_temperature(self.model, 0.7),\n                \"max_tokens\": _reasoning_safe_max_tokens(self.model, 2000)\n            }\n            \n            # Add tools for all modes (TEXT_FORMAT still needs tools to work)\n            # TEXT_FORMAT only affects how conversation history is formatted, not tool availability\n            request_data[\"tools\"] = self._get_tools()\n            request_data[\"tool_choice\"] = \"auto\"\n            \n            # Make API call\n            api_start = time.time()\n            try:\n                response = self.client.chat.completions.create(**request_data)\n                \n                # Record TTFT for this iteration\n                iteration_ttft = time.time() - api_start\n                self.metrics.ttft_per_iteration.append(iteration_ttft)\n                \n                # Record first iteration TTFT separately for backwards compatibility\n                if iteration == 1:\n                    self.metrics.ttft = iteration_ttft\n                \n                # Extract response\n                message = response.choices[0].message\n                \n                # Print assistant content to console (always show, not just verbose)\n                if message.content:\n                    print(f\"\\n\ud83e\udd16 Assistant (Iteration {iteration}):\")\n                    print(\"-\" * 40)\n                    print(message.content)\n                    print(\"-\" * 40)\n                \n                # Log token usage and cache information\n                if hasattr(response, 'usage'):\n                    usage = response.usage\n                    self.metrics.prompt_tokens += usage.prompt_tokens\n                    self.metrics.completion_tokens += usage.completion_tokens\n                    \n                    # Check for cached tokens (Kimi specific)\n                    # The cached_tokens field appears directly in the usage object\n                    cached = 0\n                    if hasattr(usage, 'cached_tokens'):\n                        # Direct attribute on usage object\n                        cached = usage.cached_tokens if usage.cached_tokens is not None else 0\n                        self.metrics.cached_tokens += cached\n                        if cached > 0:\n                            self.metrics.cache_hits += 1\n                        else:\n                            self.metrics.cache_misses += 1\n                    else:\n                        # Try alternative locations\n                        if hasattr(usage, 'prompt_tokens_details'):\n                            details = usage.prompt_tokens_details\n                            if details and hasattr(details, 'cached_tokens'):\n                                cached = details.cached_tokens if details.cached_tokens is not None else 0\n                                self.metrics.cached_tokens += cached\n                                if cached > 0:\n                                    self.metrics.cache_hits += 1\n                                else:\n                                    self.metrics.cache_misses += 1\n                        \n                        # Debug logging when verbose and no cached tokens field found\n                        if self.verbose and iteration > 1 and cached == 0:\n                            logger.debug(f\"Usage object attributes: {dir(usage)}\")\n                            logger.debug(f\"Usage data: {usage}\")\n                    \n                    if self.verbose:\n                        # Log with TTFT for this iteration\n                        cache_info = f\", cached={cached}\" if cached > 0 else \"\"\n                        logger.info(f\"Iteration {iteration} - TTFT: {iteration_ttft:.3f}s, \"\n                                  f\"Tokens: prompt={usage.prompt_tokens}, \"\n                                  f\"completion={usage.completion_tokens}\"\n                                  f\"{cache_info}\")\n                \n", "total_lines": 888, "lines_read": 100, "offset": 640, "end_line": 740, "truncated": false, "success": true}
```

**消息 8 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
```

</details>

**模型本轮回复**

```text
本实验旨在演示 **KV Cache（键值缓存）对 LLM 推理性能的影响**，通过对比“正确保留上下文”与“破坏上下文稳定性”的六种实现，观察缓存命中与首次 token 延迟（TTFT）的差异。

六种模式包括：
1. **CORRECT**：系统提示、工具顺序、消息格式均稳定，KV Cache 可高效复用。
2. **DYNAMIC_SYSTEM**：每次请求变更系统提示（如加时间戳），导致缓存失效。
3. **SHUFFLED_TOOLS**：每轮打乱工具定义顺序，破坏前缀一致性。
4. **DYNAMIC_PROFILE**：动态修改用户资料字段，使上下文变化。
5. **SLIDING_WINDOW**：仅保留最近 6 条消息，丢弃历史前缀。
6. **TEXT_FORMAT**：将消息转为纯文本，改变结构化格式。

最值得关注的指标是 **`cached_tokens`**（缓存 token 数）与 **`ttft_per_iteration`**（每轮首次 token 延迟）：CORRECT 模式应出现大量缓存命中、TTFT 显著降低；其余模式因上下文被重建，缓存命中少、TTFT 高。
```

**该模式最终回答**

```text
本实验旨在演示 **KV Cache（键值缓存）对 LLM 推理性能的影响**，通过对比“正确保留上下文”与“破坏上下文稳定性”的六种实现，观察缓存命中与首次 token 延迟（TTFT）的差异。

六种模式包括：
1. **CORRECT**：系统提示、工具顺序、消息格式均稳定，KV Cache 可高效复用。
2. **DYNAMIC_SYSTEM**：每次请求变更系统提示（如加时间戳），导致缓存失效。
3. **SHUFFLED_TOOLS**：每轮打乱工具定义顺序，破坏前缀一致性。
4. **DYNAMIC_PROFILE**：动态修改用户资料字段，使上下文变化。
5. **SLIDING_WINDOW**：仅保留最近 6 条消息，丢弃历史前缀。
6. **TEXT_FORMAT**：将消息转为纯文本，改变结构化格式。

最值得关注的指标是 **`cached_tokens`**（缓存 token 数）与 **`ttft_per_iteration`**（每轮首次 token 延迟）：CORRECT 模式应出现大量缓存命中、TTFT 显著降低；其余模式因上下文被重建，缓存命中少、TTFT 高。
```

### text_format · 历史转纯文本

机制：每轮把结构化历史重新拼成一条纯文本消息。

结果：`success=True`，API 5 轮，工具调用 4 次，累计 Cache% 15.4%。

#### 第 1 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 647 | 647 | 0 | 100.0% | 92 | 2.924s | system → user | read_file → find → grep |

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
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
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
| 928 | 256 | 672 | 27.6% | 91 | 2.794s | system → user → user | read_file → find → grep |

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
助手：[正在调用工具]
  - 调用 find，参数：{"pattern": "*.py", "directory": "chapter2/kv-cache"}
工具返回：{"pattern": "*.py", "directory": "chapter2/kv-cache", "matches": ["chapter2/kv-cache/agent.py", "chapter2/kv-cache/main.py", "chapter2/kv-cache/tests/conftest.py", "chapter2/kv-cache/tests/manual/_bootstrap.py", "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py", "chapter2/kv-cache/tests/manual/check_cache_invalidation.py", "chapter2/kv-cache/tests/manual/check_cached_tokens.py", "chapter2/kv-cache/tests/manual/check_completion.py", "chapter2/kv-cache/tests/manual/check_tool_calling.py", "chapter2/kv-cache/tests/manual/check_ttft.py", "chapter2/kv-cache/tests/manual/demo_quick.py", "chapter2/kv-cache/tests/test_error_handling.py", "chapter2/kv-cache/tests/test_file_range.py", "chapter2/kv-cache/tests/test_interactive.py", "chapter2/kv-cache/tests/test_message_flow.py", "chapter2/kv-cache/tests/test_negative_size.py", "chapter2/kv-cache/tests/test_tools.py"], "count": 17, "truncated": false, "success": true}

```

**消息 3 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
```

</details>

**模型本轮回复**

```text
我已完成第 1 步。现在进入第 2 步。
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
| 1,793 | 256 | 1,537 | 14.3% | 223 | 6.243s | system → user → user | read_file → find → grep |

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
助手：[正在调用工具]
  - 调用 find，参数：{"pattern": "*.py", "directory": "chapter2/kv-cache"}
工具返回：{"pattern": "*.py", "directory": "chapter2/kv-cache", "matches": ["chapter2/kv-cache/agent.py", "chapter2/kv-cache/main.py", "chapter2/kv-cache/tests/conftest.py", "chapter2/kv-cache/tests/manual/_bootstrap.py", "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py", "chapter2/kv-cache/tests/manual/check_cache_invalidation.py", "chapter2/kv-cache/tests/manual/check_cached_tokens.py", "chapter2/kv-cache/tests/manual/check_completion.py", "chapter2/kv-cache/tests/manual/check_tool_calling.py", "chapter2/kv-cache/tests/manual/check_ttft.py", "chapter2/kv-cache/tests/manual/demo_quick.py", "chapter2/kv-cache/tests/test_error_handling.py", "chapter2/kv-cache/tests/test_file_range.py", "chapter2/kv-cache/tests/test_interactive.py", "chapter2/kv-cache/tests/test_message_flow.py", "chapter2/kv-cache/tests/test_negative_size.py", "chapter2/kv-cache/tests/test_tools.py"], "count": 17, "truncated": false, "success": true}
助手：我已完成第 1 步。现在进入第 2 步。
助手：[正在调用工具]
  - 调用 read_file，参数：{"file_path":"chapter2/kv-cache/main.py","offset":0,"size":80}
工具返回：{"path": "chapter2/kv-cache/main.py", "content": "\"\"\"\nMain script to demonstrate KV cache importance\nRuns the ReAct agent with different implementations and compares performance\n\"\"\"\n\nimport os\nimport sys\nimport glob\nimport json\nimport argparse\nimport logging\nfrom typing import Dict, List, Any\nfrom datetime import datetime\nfrom dataclasses import asdict\n\ntry:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n\nfrom agent import KVCacheAgent, KVCacheMode, AgentMetrics, compare_implementations\n\n# Default model (Moonshot / Kimi). The whole current Kimi family (k2.5/k2.6/\n# k2.7/k3) reports cached_tokens for automatic prefix caching AND reasons, so it\n# only accepts temperature=1 (agent.py handles that automatically). kimi-k2.6 has\n# the lightest reasoning footprint of the cache-reporting models, giving the\n# cleanest TTFT while still exposing the prefix-cache hit metric this demo needs.\n# (The non-reasoning moonshot-v1-* models do NOT report cached_tokens, so they\n# cannot demonstrate the cache effect.)\nDEFAULT_MODEL = \"kimi-k2.6\"\nDEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), \"../..\"))\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format='%(asctime)s - %(levelname)s - %(message)s',\n    handlers=[\n        logging.FileHandler('kv_cache_demo.log'),\n        logging.StreamHandler()\n    ]\n)\nlogger = logging.getLogger(__name__)\n\n\n# ---------------------------------------------------------------------------\n# Metrics helpers (shared by live comparison and offline report)\n# ---------------------------------------------------------------------------\n\ndef _coerce_metrics(metrics: Any) -> Dict[str, Any]:\n    \"\"\"Normalize a stored metrics value into a plain dict.\n\n    Handles both formats found in result files:\n      - dict: produced by --compare (asdict) and by the fixed --mode path\n      - str : legacy single-mode files that stored repr(AgentMetrics(...))\n              because json.dump used default=str\n    \"\"\"\n    if isinstance(metrics, dict):\n        return metrics\n    if isinstance(metrics, str) and metrics.startswith(\"AgentMetrics(\"):\n        # Safe eval: only AgentMetrics is exposed, no builtins.\n        try:\n            obj = eval(metrics, {\"__builtins__\": {}}, {\"AgentMetrics\": AgentMetrics})\n            return asdict(obj)\n        except Exception as e:  # pragma: no cover - defensive\n            logger.warning(f\"Could not parse legacy metrics string: {e}\")\n    return {}\n\n\ndef _avg_ttft(m: Dict[str, Any]) -> float:\n    \"\"\"Average TTFT across iterations, falling back to first-iteration TTFT.\"\"\"\n    lst = m.get(\"ttft_per_iteration\") or []\n    return sum(lst) / len(lst) if lst else float(m.get(\"ttft\", 0.0) or 0.0)\n\n\ndef _hit_rate(m: Dict[str, Any]) -> float:\n    total = (m.get(\"cache_hits\", 0) or 0) + (m.get(\"cache_misses\", 0) or 0)\n    return (m.get(\"cache_hits\", 0) or 0) / total * 100 if total else 0.0\n\n\n", "total_lines": 548, "lines_read": 80, "offset": 0, "end_line": 80, "truncated": false, "success": true}

```

**消息 3 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
```

</details>

**模型本轮回复**

```text
正在执行第 3 步。
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
| 3,188 | 256 | 2,932 | 8.0% | 190 | 5.627s | system → user → user | read_file → find → grep |

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
助手：[正在调用工具]
  - 调用 find，参数：{"pattern": "*.py", "directory": "chapter2/kv-cache"}
工具返回：{"pattern": "*.py", "directory": "chapter2/kv-cache", "matches": ["chapter2/kv-cache/agent.py", "chapter2/kv-cache/main.py", "chapter2/kv-cache/tests/conftest.py", "chapter2/kv-cache/tests/manual/_bootstrap.py", "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py", "chapter2/kv-cache/tests/manual/check_cache_invalidation.py", "chapter2/kv-cache/tests/manual/check_cached_tokens.py", "chapter2/kv-cache/tests/manual/check_completion.py", "chapter2/kv-cache/tests/manual/check_tool_calling.py", "chapter2/kv-cache/tests/manual/check_ttft.py", "chapter2/kv-cache/tests/manual/demo_quick.py", "chapter2/kv-cache/tests/test_error_handling.py", "chapter2/kv-cache/tests/test_file_range.py", "chapter2/kv-cache/tests/test_interactive.py", "chapter2/kv-cache/tests/test_message_flow.py", "chapter2/kv-cache/tests/test_negative_size.py", "chapter2/kv-cache/tests/test_tools.py"], "count": 17, "truncated": false, "success": true}
助手：我已完成第 1 步。现在进入第 2 步。
助手：[正在调用工具]
  - 调用 read_file，参数：{"file_path":"chapter2/kv-cache/main.py","offset":0,"size":80}
工具返回：{"path": "chapter2/kv-cache/main.py", "content": "\"\"\"\nMain script to demonstrate KV cache importance\nRuns the ReAct agent with different implementations and compares performance\n\"\"\"\n\nimport os\nimport sys\nimport glob\nimport json\nimport argparse\nimport logging\nfrom typing import Dict, List, Any\nfrom datetime import datetime\nfrom dataclasses import asdict\n\ntry:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n\nfrom agent import KVCacheAgent, KVCacheMode, AgentMetrics, compare_implementations\n\n# Default model (Moonshot / Kimi). The whole current Kimi family (k2.5/k2.6/\n# k2.7/k3) reports cached_tokens for automatic prefix caching AND reasons, so it\n# only accepts temperature=1 (agent.py handles that automatically). kimi-k2.6 has\n# the lightest reasoning footprint of the cache-reporting models, giving the\n# cleanest TTFT while still exposing the prefix-cache hit metric this demo needs.\n# (The non-reasoning moonshot-v1-* models do NOT report cached_tokens, so they\n# cannot demonstrate the cache effect.)\nDEFAULT_MODEL = \"kimi-k2.6\"\nDEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), \"../..\"))\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format='%(asctime)s - %(levelname)s - %(message)s',\n    handlers=[\n        logging.FileHandler('kv_cache_demo.log'),\n        logging.StreamHandler()\n    ]\n)\nlogger = logging.getLogger(__name__)\n\n\n# ---------------------------------------------------------------------------\n# Metrics helpers (shared by live comparison and offline report)\n# ---------------------------------------------------------------------------\n\ndef _coerce_metrics(metrics: Any) -> Dict[str, Any]:\n    \"\"\"Normalize a stored metrics value into a plain dict.\n\n    Handles both formats found in result files:\n      - dict: produced by --compare (asdict) and by the fixed --mode path\n      - str : legacy single-mode files that stored repr(AgentMetrics(...))\n              because json.dump used default=str\n    \"\"\"\n    if isinstance(metrics, dict):\n        return metrics\n    if isinstance(metrics, str) and metrics.startswith(\"AgentMetrics(\"):\n        # Safe eval: only AgentMetrics is exposed, no builtins.\n        try:\n            obj = eval(metrics, {\"__builtins__\": {}}, {\"AgentMetrics\": AgentMetrics})\n            return asdict(obj)\n        except Exception as e:  # pragma: no cover - defensive\n            logger.warning(f\"Could not parse legacy metrics string: {e}\")\n    return {}\n\n\ndef _avg_ttft(m: Dict[str, Any]) -> float:\n    \"\"\"Average TTFT across iterations, falling back to first-iteration TTFT.\"\"\"\n    lst = m.get(\"ttft_per_iteration\") or []\n    return sum(lst) / len(lst) if lst else float(m.get(\"ttft\", 0.0) or 0.0)\n\n\ndef _hit_rate(m: Dict[str, Any]) -> float:\n    total = (m.get(\"cache_hits\", 0) or 0) + (m.get(\"cache_misses\", 0) or 0)\n    return (m.get(\"cache_hits\", 0) or 0) / total * 100 if total else 0.0\n\n\n", "total_lines": 548, "lines_read": 80, "offset": 0, "end_line": 80, "truncated": false, "success": true}
助手：正在执行第 3 步。
助手：[正在调用工具]
  - 调用 grep，参数：{"pattern":"class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens","file_path":"chapter2/kv-cache/agent.py"}
工具返回：{"pattern": "class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens", "matches": [{"file": "chapter2/kv-cache/agent.py", "line_num": 3, "line": "Demonstrates the importance of KV cache through correct and incorrect implementations."}, {"file": "chapter2/kv-cache/agent.py", "line_num": 33, "line": "chat models do NOT reason (and also do not report cached_tokens).\"\"\""}, {"file": "chapter2/kv-cache/agent.py", "line_num": 59, "line": "class KVCacheMode(Enum):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 61, "line": "CORRECT = \"correct\"  # Correct implementation with stable context"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 62, "line": "DYNAMIC_SYSTEM = \"dynamic_system\"  # Changing system prompt with timestamp"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 63, "line": "SHUFFLED_TOOLS = \"shuffled_tools\"  # Shuffling tool order each request"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 64, "line": "DYNAMIC_PROFILE = \"dynamic_profile\"  # Changing user profile with credits"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 65, "line": "SLIDING_WINDOW = \"sliding_window\"  # Only keeping recent 6 messages"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 66, "line": "TEXT_FORMAT = \"text_format\"  # Formatting messages as plain text"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 91, "line": "cached_tokens: int = 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 357, "line": "def __init__(self, api_key: str, mode: KVCacheMode = KVCacheMode.CORRECT,"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 486, "line": "if self.mode == KVCacheMode.DYNAMIC_SYSTEM:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 497, "line": "if self.mode == KVCacheMode.SHUFFLED_TOOLS:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 505, "line": "if self.mode == KVCacheMode.DYNAMIC_PROFILE:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 514, "line": "\"\"\"Format messages based on mode - recreated each iteration for incorrect modes\"\"\""}, {"file": "chapter2/kv-cache/agent.py", "line_num": 517, "line": "# Add system prompt (changes each time for DYNAMIC_SYSTEM mode)"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 528, "line": "if self.mode == KVCacheMode.SLIDING_WINDOW:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 540, "line": "elif self.mode == KVCacheMode.TEXT_FORMAT:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 575, "line": "# For CORRECT, DYNAMIC_SYSTEM, SHUFFLED_TOOLS, DYNAMIC_PROFILE modes"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 646, "line": "# CORRECT mode: Build messages once on first iteration, then keep appending"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 649, "line": "# INCORRECT modes: Recreate entire messages list from history each iteration"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 654, "line": "if self.mode == KVCacheMode.CORRECT:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 655, "line": "# Correct mode: Build messages once, then keep using same list"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 659, "line": "# Incorrect modes: Recreate messages from history each iteration"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 671, "line": "# Add tools for all modes (TEXT_FORMAT still needs tools to work)"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 672, "line": "# TEXT_FORMAT only affects how conversation history is formatted, not tool availability"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 706, "line": "# The cached_tokens field appears directly in the usage object"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 708, "line": "if hasattr(usage, 'cached_tokens'):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 710, "line": "cached = usage.cached_tokens if usage.cached_tokens is not None else 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 711, "line": "self.metrics.cached_tokens += cached"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 720, "line": "if details and hasattr(details, 'cached_tokens'):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 721, "line": "cached = details.cached_tokens if details.cached_tokens is not None else 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 722, "line": "self.metrics.cached_tokens += cached"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 883, "line": "logger.info(f\"Cached Tokens: {metrics.cached_tokens}\")"}], "files_searched": 1, "match_count": 34, "truncated": false, "success": true}

```

**消息 3 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
```

</details>

**模型本轮回复**

工具调用 1：`read_file`

参数：

```json
{"file_path":"chapter2/kv-cache/agent.py","offset":640,"size":100}
```

工具真实返回：

<details>
<summary>展开工具返回</summary>

```json
{
  "path": "chapter2/kv-cache/agent.py",
  "content": "        while iteration < max_iterations:\n            iteration += 1\n            \n            # CRITICAL: Message handling for KV cache demonstration\n            # \n            # CORRECT mode: Build messages once on first iteration, then keep appending\n            #   - Maintains stable context → KV cache works efficiently\n            # \n            # INCORRECT modes: Recreate entire messages list from history each iteration\n            #   - Forces complete context reconstruction → KV cache invalidated\n            #   - Within an iteration, we still append to messages for proper API flow\n            #   - But at the start of each new iteration, we rebuild from scratch\n            \n            if self.mode == KVCacheMode.CORRECT:\n                # Correct mode: Build messages once, then keep using same list\n                if iteration == 1:\n                    messages = self._format_messages(original_task)\n            else:\n                # Incorrect modes: Recreate messages from history each iteration\n                # This forces cache invalidation due to context changes\n                messages = self._format_messages(original_task)\n            \n            # Prepare request\n            request_data = {\n                \"model\": self.model,\n                \"messages\": messages,\n                \"temperature\": _reasoning_safe_temperature(self.model, 0.7),\n                \"max_tokens\": _reasoning_safe_max_tokens(self.model, 2000)\n            }\n            \n            # Add tools for all modes (TEXT_FORMAT still needs tools to work)\n            # TEXT_FORMAT only affects how conversation history is formatted, not tool availability\n            request_data[\"tools\"] = self._get_tools()\n            request_data[\"tool_choice\"] = \"auto\"\n            \n            # Make API call\n            api_start = time.time()\n            try:\n                response = self.client.chat.completions.create(**request_data)\n                \n                # Record TTFT for this iteration\n                iteration_ttft = time.time() - api_start\n                self.metrics.ttft_per_iteration.append(iteration_ttft)\n                \n                # Record first iteration TTFT separately for backwards compatibility\n                if iteration == 1:\n                    self.metrics.ttft = iteration_ttft\n                \n                # Extract response\n                message = response.choices[0].message\n                \n                # Print assistant content to console (always show, not just verbose)\n                if message.content:\n                    print(f\"\\n🤖 Assistant (Iteration {iteration}):\")\n                    print(\"-\" * 40)\n                    print(message.content)\n                    print(\"-\" * 40)\n                \n                # Log token usage and cache information\n                if hasattr(response, 'usage'):\n                    usage = response.usage\n                    self.metrics.prompt_tokens += usage.prompt_tokens\n                    self.metrics.completion_tokens += usage.completion_tokens\n                    \n                    # Check for cached tokens (Kimi specific)\n                    # The cached_tokens field appears directly in the usage object\n                    cached = 0\n                    if hasattr(usage, 'cached_tokens'):\n                        # Direct attribute on usage object\n                        cached = usage.cached_tokens if usage.cached_tokens is not None else 0\n                        self.metrics.cached_tokens += cached\n                        if cached > 0:\n                            self.metrics.cache_hits += 1\n                        else:\n                            self.metrics.cache_misses += 1\n                    else:\n                        # Try alternative locations\n                        if hasattr(usage, 'prompt_tokens_details'):\n                            details = usage.prompt_tokens_details\n                            if details and hasattr(details, 'cached_tokens'):\n                                cached = details.cached_tokens if details.cached_tokens is not None else 0\n                                self.metrics.cached_tokens += cached\n                                if cached > 0:\n                                    self.metrics.cache_hits += 1\n                                else:\n                                    self.metrics.cache_misses += 1\n                        \n                        # Debug logging when verbose and no cached tokens field found\n                        if self.verbose and iteration > 1 and cached == 0:\n                            logger.debug(f\"Usage object attributes: {dir(usage)}\")\n                            logger.debug(f\"Usage data: {usage}\")\n                    \n                    if self.verbose:\n                        # Log with TTFT for this iteration\n                        cache_info = f\", cached={cached}\" if cached > 0 else \"\"\n                        logger.info(f\"Iteration {iteration} - TTFT: {iteration_ttft:.3f}s, \"\n                                  f\"Tokens: prompt={usage.prompt_tokens}, \"\n                                  f\"completion={usage.completion_tokens}\"\n                                  f\"{cache_info}\")\n                \n",
  "total_lines": 888,
  "lines_read": 100,
  "offset": 640,
  "end_line": 740,
  "truncated": false,
  "success": true
}
```

</details>

#### 第 5 轮

| Prompt | Cached | 未缓存 | Cache% | Completion | 响应耗时 | 消息角色 | 工具顺序 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4,263 | 256 | 4,007 | 6.0% | 2,054 | 33.400s | system → user → user | read_file → find → grep |

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
助手：[正在调用工具]
  - 调用 find，参数：{"pattern": "*.py", "directory": "chapter2/kv-cache"}
工具返回：{"pattern": "*.py", "directory": "chapter2/kv-cache", "matches": ["chapter2/kv-cache/agent.py", "chapter2/kv-cache/main.py", "chapter2/kv-cache/tests/conftest.py", "chapter2/kv-cache/tests/manual/_bootstrap.py", "chapter2/kv-cache/tests/manual/check_agent_error_recovery.py", "chapter2/kv-cache/tests/manual/check_cache_invalidation.py", "chapter2/kv-cache/tests/manual/check_cached_tokens.py", "chapter2/kv-cache/tests/manual/check_completion.py", "chapter2/kv-cache/tests/manual/check_tool_calling.py", "chapter2/kv-cache/tests/manual/check_ttft.py", "chapter2/kv-cache/tests/manual/demo_quick.py", "chapter2/kv-cache/tests/test_error_handling.py", "chapter2/kv-cache/tests/test_file_range.py", "chapter2/kv-cache/tests/test_interactive.py", "chapter2/kv-cache/tests/test_message_flow.py", "chapter2/kv-cache/tests/test_negative_size.py", "chapter2/kv-cache/tests/test_tools.py"], "count": 17, "truncated": false, "success": true}
助手：我已完成第 1 步。现在进入第 2 步。
助手：[正在调用工具]
  - 调用 read_file，参数：{"file_path":"chapter2/kv-cache/main.py","offset":0,"size":80}
工具返回：{"path": "chapter2/kv-cache/main.py", "content": "\"\"\"\nMain script to demonstrate KV cache importance\nRuns the ReAct agent with different implementations and compares performance\n\"\"\"\n\nimport os\nimport sys\nimport glob\nimport json\nimport argparse\nimport logging\nfrom typing import Dict, List, Any\nfrom datetime import datetime\nfrom dataclasses import asdict\n\ntry:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n\nfrom agent import KVCacheAgent, KVCacheMode, AgentMetrics, compare_implementations\n\n# Default model (Moonshot / Kimi). The whole current Kimi family (k2.5/k2.6/\n# k2.7/k3) reports cached_tokens for automatic prefix caching AND reasons, so it\n# only accepts temperature=1 (agent.py handles that automatically). kimi-k2.6 has\n# the lightest reasoning footprint of the cache-reporting models, giving the\n# cleanest TTFT while still exposing the prefix-cache hit metric this demo needs.\n# (The non-reasoning moonshot-v1-* models do NOT report cached_tokens, so they\n# cannot demonstrate the cache effect.)\nDEFAULT_MODEL = \"kimi-k2.6\"\nDEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), \"../..\"))\n\n# Configure logging\nlogging.basicConfig(\n    level=logging.INFO,\n    format='%(asctime)s - %(levelname)s - %(message)s',\n    handlers=[\n        logging.FileHandler('kv_cache_demo.log'),\n        logging.StreamHandler()\n    ]\n)\nlogger = logging.getLogger(__name__)\n\n\n# ---------------------------------------------------------------------------\n# Metrics helpers (shared by live comparison and offline report)\n# ---------------------------------------------------------------------------\n\ndef _coerce_metrics(metrics: Any) -> Dict[str, Any]:\n    \"\"\"Normalize a stored metrics value into a plain dict.\n\n    Handles both formats found in result files:\n      - dict: produced by --compare (asdict) and by the fixed --mode path\n      - str : legacy single-mode files that stored repr(AgentMetrics(...))\n              because json.dump used default=str\n    \"\"\"\n    if isinstance(metrics, dict):\n        return metrics\n    if isinstance(metrics, str) and metrics.startswith(\"AgentMetrics(\"):\n        # Safe eval: only AgentMetrics is exposed, no builtins.\n        try:\n            obj = eval(metrics, {\"__builtins__\": {}}, {\"AgentMetrics\": AgentMetrics})\n            return asdict(obj)\n        except Exception as e:  # pragma: no cover - defensive\n            logger.warning(f\"Could not parse legacy metrics string: {e}\")\n    return {}\n\n\ndef _avg_ttft(m: Dict[str, Any]) -> float:\n    \"\"\"Average TTFT across iterations, falling back to first-iteration TTFT.\"\"\"\n    lst = m.get(\"ttft_per_iteration\") or []\n    return sum(lst) / len(lst) if lst else float(m.get(\"ttft\", 0.0) or 0.0)\n\n\ndef _hit_rate(m: Dict[str, Any]) -> float:\n    total = (m.get(\"cache_hits\", 0) or 0) + (m.get(\"cache_misses\", 0) or 0)\n    return (m.get(\"cache_hits\", 0) or 0) / total * 100 if total else 0.0\n\n\n", "total_lines": 548, "lines_read": 80, "offset": 0, "end_line": 80, "truncated": false, "success": true}
助手：正在执行第 3 步。
助手：[正在调用工具]
  - 调用 grep，参数：{"pattern":"class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens","file_path":"chapter2/kv-cache/agent.py"}
工具返回：{"pattern": "class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens", "matches": [{"file": "chapter2/kv-cache/agent.py", "line_num": 3, "line": "Demonstrates the importance of KV cache through correct and incorrect implementations."}, {"file": "chapter2/kv-cache/agent.py", "line_num": 33, "line": "chat models do NOT reason (and also do not report cached_tokens).\"\"\""}, {"file": "chapter2/kv-cache/agent.py", "line_num": 59, "line": "class KVCacheMode(Enum):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 61, "line": "CORRECT = \"correct\"  # Correct implementation with stable context"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 62, "line": "DYNAMIC_SYSTEM = \"dynamic_system\"  # Changing system prompt with timestamp"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 63, "line": "SHUFFLED_TOOLS = \"shuffled_tools\"  # Shuffling tool order each request"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 64, "line": "DYNAMIC_PROFILE = \"dynamic_profile\"  # Changing user profile with credits"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 65, "line": "SLIDING_WINDOW = \"sliding_window\"  # Only keeping recent 6 messages"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 66, "line": "TEXT_FORMAT = \"text_format\"  # Formatting messages as plain text"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 91, "line": "cached_tokens: int = 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 357, "line": "def __init__(self, api_key: str, mode: KVCacheMode = KVCacheMode.CORRECT,"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 486, "line": "if self.mode == KVCacheMode.DYNAMIC_SYSTEM:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 497, "line": "if self.mode == KVCacheMode.SHUFFLED_TOOLS:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 505, "line": "if self.mode == KVCacheMode.DYNAMIC_PROFILE:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 514, "line": "\"\"\"Format messages based on mode - recreated each iteration for incorrect modes\"\"\""}, {"file": "chapter2/kv-cache/agent.py", "line_num": 517, "line": "# Add system prompt (changes each time for DYNAMIC_SYSTEM mode)"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 528, "line": "if self.mode == KVCacheMode.SLIDING_WINDOW:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 540, "line": "elif self.mode == KVCacheMode.TEXT_FORMAT:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 575, "line": "# For CORRECT, DYNAMIC_SYSTEM, SHUFFLED_TOOLS, DYNAMIC_PROFILE modes"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 646, "line": "# CORRECT mode: Build messages once on first iteration, then keep appending"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 649, "line": "# INCORRECT modes: Recreate entire messages list from history each iteration"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 654, "line": "if self.mode == KVCacheMode.CORRECT:"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 655, "line": "# Correct mode: Build messages once, then keep using same list"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 659, "line": "# Incorrect modes: Recreate messages from history each iteration"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 671, "line": "# Add tools for all modes (TEXT_FORMAT still needs tools to work)"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 672, "line": "# TEXT_FORMAT only affects how conversation history is formatted, not tool availability"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 706, "line": "# The cached_tokens field appears directly in the usage object"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 708, "line": "if hasattr(usage, 'cached_tokens'):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 710, "line": "cached = usage.cached_tokens if usage.cached_tokens is not None else 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 711, "line": "self.metrics.cached_tokens += cached"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 720, "line": "if details and hasattr(details, 'cached_tokens'):"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 721, "line": "cached = details.cached_tokens if details.cached_tokens is not None else 0"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 722, "line": "self.metrics.cached_tokens += cached"}, {"file": "chapter2/kv-cache/agent.py", "line_num": 883, "line": "logger.info(f\"Cached Tokens: {metrics.cached_tokens}\")"}], "files_searched": 1, "match_count": 34, "truncated": false, "success": true}
助手：[正在调用工具]
  - 调用 read_file，参数：{"file_path":"chapter2/kv-cache/agent.py","offset":640,"size":100}
工具返回：{"path": "chapter2/kv-cache/agent.py", "content": "        while iteration < max_iterations:\n            iteration += 1\n            \n            # CRITICAL: Message handling for KV cache demonstration\n            # \n            # CORRECT mode: Build messages once on first iteration, then keep appending\n            #   - Maintains stable context \u2192 KV cache works efficiently\n            # \n            # INCORRECT modes: Recreate entire messages list from history each iteration\n            #   - Forces complete context reconstruction \u2192 KV cache invalidated\n            #   - Within an iteration, we still append to messages for proper API flow\n            #   - But at the start of each new iteration, we rebuild from scratch\n            \n            if self.mode == KVCacheMode.CORRECT:\n                # Correct mode: Build messages once, then keep using same list\n                if iteration == 1:\n                    messages = self._format_messages(original_task)\n            else:\n                # Incorrect modes: Recreate messages from history each iteration\n                # This forces cache invalidation due to context changes\n                messages = self._format_messages(original_task)\n            \n            # Prepare request\n            request_data = {\n                \"model\": self.model,\n                \"messages\": messages,\n                \"temperature\": _reasoning_safe_temperature(self.model, 0.7),\n                \"max_tokens\": _reasoning_safe_max_tokens(self.model, 2000)\n            }\n            \n            # Add tools for all modes (TEXT_FORMAT still needs tools to work)\n            # TEXT_FORMAT only affects how conversation history is formatted, not tool availability\n            request_data[\"tools\"] = self._get_tools()\n            request_data[\"tool_choice\"] = \"auto\"\n            \n            # Make API call\n            api_start = time.time()\n            try:\n                response = self.client.chat.completions.create(**request_data)\n                \n                # Record TTFT for this iteration\n                iteration_ttft = time.time() - api_start\n                self.metrics.ttft_per_iteration.append(iteration_ttft)\n                \n                # Record first iteration TTFT separately for backwards compatibility\n                if iteration == 1:\n                    self.metrics.ttft = iteration_ttft\n                \n                # Extract response\n                message = response.choices[0].message\n                \n                # Print assistant content to console (always show, not just verbose)\n                if message.content:\n                    print(f\"\\n\ud83e\udd16 Assistant (Iteration {iteration}):\")\n                    print(\"-\" * 40)\n                    print(message.content)\n                    print(\"-\" * 40)\n                \n                # Log token usage and cache information\n                if hasattr(response, 'usage'):\n                    usage = response.usage\n                    self.metrics.prompt_tokens += usage.prompt_tokens\n                    self.metrics.completion_tokens += usage.completion_tokens\n                    \n                    # Check for cached tokens (Kimi specific)\n                    # The cached_tokens field appears directly in the usage object\n                    cached = 0\n                    if hasattr(usage, 'cached_tokens'):\n                        # Direct attribute on usage object\n                        cached = usage.cached_tokens if usage.cached_tokens is not None else 0\n                        self.metrics.cached_tokens += cached\n                        if cached > 0:\n                            self.metrics.cache_hits += 1\n                        else:\n                            self.metrics.cache_misses += 1\n                    else:\n                        # Try alternative locations\n                        if hasattr(usage, 'prompt_tokens_details'):\n                            details = usage.prompt_tokens_details\n                            if details and hasattr(details, 'cached_tokens'):\n                                cached = details.cached_tokens if details.cached_tokens is not None else 0\n                                self.metrics.cached_tokens += cached\n                                if cached > 0:\n                                    self.metrics.cache_hits += 1\n                                else:\n                                    self.metrics.cache_misses += 1\n                        \n                        # Debug logging when verbose and no cached tokens field found\n                        if self.verbose and iteration > 1 and cached == 0:\n                            logger.debug(f\"Usage object attributes: {dir(usage)}\")\n                            logger.debug(f\"Usage data: {usage}\")\n                    \n                    if self.verbose:\n                        # Log with TTFT for this iteration\n                        cache_info = f\", cached={cached}\" if cached > 0 else \"\"\n                        logger.info(f\"Iteration {iteration} - TTFT: {iteration_ttft:.3f}s, \"\n                                  f\"Tokens: prompt={usage.prompt_tokens}, \"\n                                  f\"completion={usage.completion_tokens}\"\n                                  f\"{cache_info}\")\n                \n", "total_lines": 888, "lines_read": 100, "offset": 640, "end_line": 740, "truncated": false, "success": true}

```

**消息 3 · 用户（`user`）**

```text
你正在参加一次 KV Cache 对照实验。请严格按顺序完成下面五步，每轮最多调用一个工具，并等待该工具返回后再进入下一步：

1. 使用 find 查找 `chapter2/kv-cache` 目录中的所有 Python 文件。
2. 使用 read_file 读取 `chapter2/kv-cache/main.py` 的前 80 行（offset=0，size=80）。
3. 使用 grep 在 `chapter2/kv-cache/agent.py` 中搜索正则表达式 `class KVCacheMode|CORRECT|DYNAMIC_SYSTEM|SHUFFLED_TOOLS|DYNAMIC_PROFILE|SLIDING_WINDOW|TEXT_FORMAT|cached_tokens`，一次取得六种模式和缓存指标的代码证据。
4. 使用 read_file 读取 `chapter2/kv-cache/agent.py` 从 offset=640 开始的 100 行，核对六种模式如何构造请求并记录缓存指标。
5. 只根据以上工具返回，用不超过 400 个汉字总结：这个实验的目的、六种模式，以及最值得比较的指标。

如果某一步已经有成功的工具结果，不要重复执行。不要读取其他目录。所有说明、进度文字和最终回答都必须使用中文。

本轮对照实验编号：KV缓存对照-20260808-193109
```

</details>

**模型本轮回复**

```text
本实验旨在通过正确与错误实现对比，演示KV缓存对ReAct智能体性能的影响。实验设置六种模式：`CORRECT`为正确实现，首轮构建消息后持续追加，保持上下文稳定；其余五种为错误实现，包括`DYNAMIC_SYSTEM`（动态系统提示，带时间戳）、`SHUFFLED_TOOLS`（每轮打乱工具顺序）、`DYNAMIC_PROFILE`（动态用户资料积分）、`SLIDING_WINDOW`（滑动窗口仅保留最近6条消息）和`TEXT_FORMAT`（纯文本格式）。错误模式每轮重建完整消息列表，破坏上下文稳定性，导致KV缓存失效。最值得比较的指标是**TTFT（首令牌延迟）**与**cached_tokens（缓存复用token数）**：`CORRECT`模式应呈现高`cached_tokens`和低TTFT，而错误模式因缓存失效，TTFT较高且`cached_tokens`极低。
```

**该模式最终回答**

```text
本实验旨在通过正确与错误实现对比，演示KV缓存对ReAct智能体性能的影响。实验设置六种模式：`CORRECT`为正确实现，首轮构建消息后持续追加，保持上下文稳定；其余五种为错误实现，包括`DYNAMIC_SYSTEM`（动态系统提示，带时间戳）、`SHUFFLED_TOOLS`（每轮打乱工具顺序）、`DYNAMIC_PROFILE`（动态用户资料积分）、`SLIDING_WINDOW`（滑动窗口仅保留最近6条消息）和`TEXT_FORMAT`（纯文本格式）。错误模式每轮重建完整消息列表，破坏上下文稳定性，导致KV缓存失效。最值得比较的指标是**TTFT（首令牌延迟）**与**cached_tokens（缓存复用token数）**：`CORRECT`模式应呈现高`cached_tokens`和低TTFT，而错误模式因缓存失效，TTFT较高且`cached_tokens`极低。
```

## 验证边界

- 本报告证明请求真实到达 Kimi，并保存了服务端返回的 usage 与对话收据。
- 它不证明缓存命中了哪一个具体消息片段；Kimi 当前只返回总 `cached_tokens`。
- 六种模式按顺序连续执行，服务端缓存可能受到前面模式和更早请求的预热影响；报告保留首轮数据，不把首轮自动命中误称为本地代码预先计算的缓存。
- 响应耗时还会受到推理长度、网络和服务端负载影响，因此判断 KV Cache 时优先看 Token 指标，再把耗时作为辅助证据。
