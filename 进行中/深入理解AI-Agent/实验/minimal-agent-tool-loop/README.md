# Minimal Agent Tool Loop

这个实验把《深入理解 AI Agent》第 2 章的工具调用片段变成一个可以直接运行的本地环境。

## 要验证什么

观察最小 Agent 循环：

```text
用户问题
→ 模型决定调用工具
→ Python 执行真实工具
→ 工具结果追加进 messages
→ 模型根据更新后的轨迹继续决策或回答
```

它同时展示了最小 Harness：工具定义、参数校验、错误结果、轨迹保存和最大迭代次数。

## 已安装环境

- macOS Apple Silicon，16 GB 内存
- Ollama `0.32.5`，通过 Homebrew 官方 core formula 安装
- `qwen3:0.6b`，来自 Ollama 官方模型库，约 523 MB
- Python 3.11 独立虚拟环境
- 天气数据使用 Open-Meteo，无需 API Key

Ollama 已设置为登录时自动启动：

```bash
brew services info ollama
ollama list
```

## 运行

```bash
cd "/Users/gaoronghui/Documents/agent_learning/进行中/深入理解AI-Agent/实验/minimal-agent-tool-loop"
uv run python agent.py
```

也可以修改用户问题：

```bash
uv run python agent.py "What's the current time and weather in Shanghai?"
```

程序会打印每一轮的工具调用和工具结果，方便观察 `messages` 轨迹如何增长。

这个 0.6B 小模型在 OpenAI 兼容接口的 `tool_choice=auto` 下偶尔会只生成“应该调用工具”的推理，却不真正发出调用。为了让教学实验稳定，第一轮使用 `tool_choice=required`，只约束“必须至少用一个工具”，具体选时间、天气还是两者仍由模型决定；工具结果回填后恢复 `auto`，由模型决定是否结束。这也是 Harness 对模型脆弱点进行最小纠正的实例。

## 测试

```bash
uv run pytest -q
```

## 与书中原代码相比补了什么

| 书中教学片段 | 本实验 |
| --- | --- |
| `OpenAI()` 默认连接云端 | 指向本地 Ollama 的 OpenAI 兼容接口 |
| 模型名 `Qwen3-0.6B`（vLLM） | Ollama 模型名 `qwen3:0.6b` |
| 时间、天气为固定假数据 | 真实时区时间 + Open-Meteo 实时天气 |
| `arguments` 没有解析 | 使用 `json.loads` 解析并返回结构化错误 |
| `while True` | 设置 `max_iterations` 停止条件 |
| 不显示执行轨迹 | 打印每轮 tool call 与 tool result |
| 小模型 `auto` 模式可能产生空答案 | 第一轮要求至少一次工具调用，后续恢复 `auto` |
| Python 可能通过系统代理访问 localhost | OpenAI 客户端对本地 Ollama 设置 `trust_env=False` |

## 环境配置

默认配置已经可以直接运行。如需修改，复制示例：

```bash
cp .env.example .env
```

不要提交 `.env`。

## 当前结论

2026-07-28 已完成机器验证：5 个单元测试通过；本地 Qwen3 在第一轮并行选择了时间和天气工具，Python 返回真实结果，第二轮模型根据工具结果生成最终回答，完整循环在 2 轮内结束。

下一步由用户亲自运行并观察轨迹。重点不是天气答案，而是指出每一步分别属于模型、工具、上下文还是 Harness。
