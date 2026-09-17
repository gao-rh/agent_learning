# Python 核心复现：第一课

本课建议 20–30 分钟。你主要使用 Python，因此不先上 JavaScript 课。

只解决一个问题：模型返回“我要读文件”以后，谁真正读取文件，结果怎样进入下一次请求？

## 你现在做什么

1. 打开 [01_tool_call.py](01_tool_call.py)，只看 `main` 中的 `assistant_message`。先预测：仅把这条消息追加到列表，会不会读取文件？`arguments` 是字典还是字符串？
2. 运行观察模式，核对预测。它只打印消息，不读练习文件，不调用模型。

```bash
cd /Users/gaoronghui/Documents/agent_learning/2-进行中/Pi-Agent源码学习/实验/python-core
python3 01_tool_call.py
```

3. 补完 `execute_tool_call`，其他代码先不改。需要做：解析参数 → 按名称找函数 → 调用函数 → 返回工具结果消息。提示已经写在函数里；不要用 `eval`，也不要把文件内容写死。
4. 运行执行模式，观察 `messages` 从两条变成三条。

```bash
python3 01_tool_call.py --execute
```

练习未填时，出现“请先补完 execute_tool_call”是预留的练习提示，不是环境错误。

5. 改一下 [lesson.txt](lesson.txt) 的内容，再运行。指出哪条消息随之变化，并解释为什么。完成后把你的函数和解释发回对话。

Python 标准库即可运行，无需 pip、API Key、Node 或新插件。可在任意已有终端运行；是否已经安装 VS Code 不影响本课。无需给 Cursor 付费。

## 先记住的三个边界

- **工具请求不是执行。** `assistant_message` 只是数据；只有程序调用本地 `read` 函数时，才发生文件读取。
- **读到不等于模型看到了。** 把结果追加到本地列表后，还需要在下一次模型请求中发送它。本课没有进行这次网络请求。
- **请求与结果要对应。** 工具结果里的 `tool_call_id` 指向产生它的调用 ID。不能只把文件内容当成一条无来源的用户消息。

本课模拟了常见的 chat/tool-call 消息形状，并非 Pi 原生消息对象，也不是已验证的 Kimi 完整请求。没有模拟模型推理能力，没有工具定义的首次发送，也没有完整 Agent 循环。接入真实模型时再核实模型、工具 schema 和消息协议。

## 你完成了吗

- 能解释默认运行为什么没有读取文件。
- `--execute` 后依次保留 user、带 tool_calls 的 assistant、tool 三条消息。
- tool 消息的 ID 对应请求 ID，内容来自真实读取而非硬编码。
- 改练习文件后，实际工具结果跟着变化。
- 能指出仍缺少“再次请求模型”和“循环/停止条件”，不把本课说成已经跑通 Kimi Agent。

未知工具、无效 JSON、缺失参数和工具异常转成错误消息，是下一课的增量；本课仅演示成功路径。`read` 的固定文件名限制只是本课操作范围，不是生产级沙箱。

## 对照 Pi：做完再看，不用提前通读

固定版本：`v0.85.0` / `107d79f11072bbc8a3a757ed7fd69596bee7d68c`。

在 [agent-loop.ts](../../资料/本地资料/pi/packages/agent/src/agent-loop.ts) 中，只查这四处：

| 本课的动作 | Pi 对照位置 |
| --- | --- |
| 按名称找工具、检查参数 | `prepareToolCall`，第 607 行起 |
| 真正调用本地工具 | `executePreparedToolCall`，第 677 行起 |
| 把结果组成消息并携带调用 ID | `createToolResultMessage`，第 784 行起 |
| 把工具结果追加到上下文 | `runLoop`，第 237 行起 |

Pi 内部使用 `role: "toolResult"` 和 `toolCallId` 等字段；本课使用 `role: "tool"` 和 `tool_call_id`，不要原样混用。后续接入层负责映射。上游流式、并发和扩展钩子不在本课范围。
