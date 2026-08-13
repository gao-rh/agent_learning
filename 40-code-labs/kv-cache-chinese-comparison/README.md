---
type: code-lab
status: active
tags: [agent, kv-cache, kimi, context-engineering]
created: 2026-08-08
updated: 2026-08-08
---

# KV Cache 六模式中文对照实验

这个代码实验复用《深入理解 AI Agent》实验 2-3 的官方 `KVCacheAgent`，按教材顺序运行六种模式：

1. `correct`
2. `dynamic_system`
3. `shuffled_tools`
4. `dynamic_profile`
5. `sliding_window`
6. `text_format`

它不修改教材源码，只增加三件事：

- 把共享系统提示、工具说明、动态资料和用户任务改成中文；
- 旁路保存每一轮真正发送给模型的消息、工具顺序、模型回复、工具调用和 usage；
- 同时生成完整 JSON 和人可以直接阅读的中文 Markdown 报告。

## 运行

依赖和 API Key 继续使用教材工作区已有的共享环境与 `chapter2/kv-cache/.env`：

```bash
cd /Users/gaoronghui/Documents/agent_learning/学习资料/Agent/参考资料/深入理解AI-Agent/ai-agent-book-chapter2-current/chapter2/kv-cache
PYTHONPATH=../.. ../../.venv/bin/python /Users/gaoronghui/Documents/agent_learning/40-code-labs/kv-cache-chinese-comparison/run_campaign.py
```

脚本不会把 API Key 写入控制台、JSON 或 Markdown。

如需根据已有 JSON 重新生成报告：

```bash
cd /Users/gaoronghui/Documents/agent_learning/学习资料/Agent/参考资料/深入理解AI-Agent/ai-agent-book-chapter2-current/chapter2/kv-cache
PYTHONPATH=../.. ../../.venv/bin/python /Users/gaoronghui/Documents/agent_learning/40-code-labs/kv-cache-chinese-comparison/run_campaign.py \
  --render-only /绝对路径/campaign.json
```

## 输出

每次运行在 `runs/<时间戳>/` 下生成：

| 文件 | 用途 |
| --- | --- |
| `campaign.json` | 机器可读的完整实验收据；保存每轮请求和响应，但移除隐藏推理与凭据。 |
| `KV-Cache六模式中文对比报告.md` | 人可读报告；包含总表、逐轮指标和可展开的完整对话。 |

## 指标边界

- `cached_tokens` 是 Kimi 返回的真实缓存 Token 数。
- `Cache% = cached_tokens / prompt_tokens`，表示本轮 Prompt 有多少由缓存提供。
- `未缓存 Tokens = prompt_tokens - cached_tokens`。
- 只有 `correct` 是严格追加式上下文，因此它的“缓存量 ÷ 上轮 Prompt”才可近似观察上一轮前缀是否完整复用；其他模式的上一轮请求不一定是当前请求的完整前缀。
- 教材当前调用是非流式的，代码中名为 `TTFT` 的计时实际覆盖整个 `chat.completions.create`。本实验将它改称“响应耗时”，不冒充真正的首 Token 延迟。

## 完成标准

- 六种模式都留下成功或失败收据，失败不能被静默跳过。
- 六种模式使用同一个中文任务、同一个模型和同一个工具根目录。
- 报告可以逐轮追溯：模型看到了什么、回复了什么、调用了什么、工具返回了什么。
- 报告把匹配的六模式数据与此前英文诊断样本分开。

## 2026-08-08 正式实测

正式运行使用 4 次工具调用 + 1 次最终回答，共 5 轮。这样 `sliding_window` 在最终轮会从 8 条历史中删掉最早一对 assistant/tool 消息，确实触发教材要观察的截断行为。

| 模式 | Prompt | Cached | 未缓存 | Cache% | 总墙钟时间 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `correct` | 11,407 | 4,864 | 6,543 | 42.6% | 46.667s |
| `dynamic_system` | 11,437 | 1,280 | 10,157 | 11.2% | 56.669s |
| `shuffled_tools` | 11,729 | 2,304 | 9,425 | 19.6% | 49.324s |
| `dynamic_profile` | 11,435 | 1,024 | 10,411 | 9.0% | 32.620s |
| `sliding_window` | 11,053 | 3,207 | 7,846 | 29.0% | 28.833s |
| `text_format` | 10,819 | 1,671 | 9,148 | 15.4% | 50.999s |

正式产物：

- [中文对比报告](runs/20260808-193109/KV-Cache六模式中文对比报告.md)
- [完整 JSON 收据](runs/20260808-193109/campaign.json)

此前两个 run 只保留为诊断，不作为正式结论：

- [20260808-192130](runs/20260808-192130/)：发现 grep 证据不足后中断，只完成 `correct`。
- [20260808-192341](runs/20260808-192341/)：六模式都跑完，但 4 轮短任务没有真正触发滑动窗口截断。

## 结论

- 本轮 `correct` 的累计 Cache% 最高，支持“稳定、只追加的前缀更容易持续复用”。
- 动态 system 和动态 profile 把变化字段放在靠前位置，后续历史无法形成不断增长的稳定前缀。
- 滑动窗口第 4 轮为 Prompt 3,368 / Cached 1,536；第 5 轮截断后为 Prompt 4,179 / Cached 256。它让上下文变短了一些，但同时把本轮 Cache% 从 45.6% 降到 6.1%。
- 工具乱序最后一轮出现 1,536 Cached Tokens，说明连续运行时会叠加服务端预热与偶然相同排列；不能把六种模式当成必然固定排名，必须看逐轮工具顺序与 Cached Token 轨迹。
- 教材当前的非流式计时不是严格 TTFT；本实验只把它称为完整响应耗时，并以 Token 指标作为主要证据。

## 验证结果

- 正式 JSON：6 个模式、30 次 API 请求、24 次工具执行，全部成功；六个最终回答都包含中文。
- 凭据扫描：产物中没有 `sk-...` 形态字符串；没有保存 `reasoning_content` 字段。
- 教材离线测试：`6 passed, 1 failed`。唯一失败是旧测试硬编码读取当前工作区不存在的 `chapter1/context/README.md`，与本代码实验无关；未修改教材或伪造缺失文件。
