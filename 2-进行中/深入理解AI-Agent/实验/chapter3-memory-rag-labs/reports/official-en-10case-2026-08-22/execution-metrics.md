# Chapter 3 记忆实验：10 用例 × 4 模式执行记录

## 实验边界

- 用例：原仓库英文 YAML，共 10 个目的抽样用例（Layer 1: 2，Layer 2: 4，Layer 3: 4）。
- 记忆模式：`notes` / `enhanced_notes` / `json_cards` / `advanced_json_cards`。
- Writer + Answerer：Kimi K2.6。
- Judge：独立 GPT-5.6 SOL 子 Agent，不参与记忆写入和回答生成。
- 英文模式直接调用原 runner 中的 `memory_prompt()` 和 `answer_prompt()`，没有翻译或修改 prompt。
- 每轮写入只接收“旧记忆状态 + 当前新会话”，最终回答只接收最终记忆，不接收原始历史会话。

这不是原作者完整 campaign 的逐参数复刻。用户指定将 writer/answerer 换成 Kimi K2.6；本地教学 wrapper 关闭 Kimi thinking，记忆/回答输出上限为 16,384 / 4,096 token，而原 runner 默认为温度 0、6,000 / 1,200 token。因此本次结果应视为“原用例 + 原 prompt 的 Kimi 模型对照”。

## 执行完整性

- 预期 arm：40
- 生成成功：39
- 生成失败：1
- 失败 arm：`layer1_04_airline_booking / advanced_json_cards`
- 失败阶段：第 1 个会话的记忆写入
- 失败原因：Kimi 输出触发 16,384 token 上限
- 失败处理：保留原始失败，不提高上限，不重试

39 个成功 JSON 均通过解析和元数据检查：英文、Kimi K2.6、无 Kimi 自评分。

## Token、成本与延迟

费用使用 [Kimi K2.6 官方价格](https://platform.kimi.com/docs/pricing/chat-k26)估算：输入缓存未命中 ¥6.50 / 1M token，输出 ¥27.00 / 1M token。receipt 没有返回缓存命中 token，下表对成功 arm 统一按“全部输入未命中”计算。失败调用没有 usage receipt，未计入费用。所以这是可复算的试验估算，不是账单总额。

| 模式 | 成功用例 | 输入 token | 输出 token | 总 token | 估算费用 | 平均每成功用例 | API 累计延迟 | 平均每成功用例 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Notes | 10 | 68,067 | 33,739 | 101,806 | ¥1.3534 | ¥0.1353 | 757.4 s | 75.7 s |
| Enhanced Notes | 10 | 68,458 | 34,481 | 102,939 | ¥1.3760 | ¥0.1376 | 825.1 s | 82.5 s |
| JSON Cards | 10 | 81,653 | 48,463 | 130,116 | ¥1.8392 | ¥0.1839 | 1,113.1 s | 111.3 s |
| Advanced JSON Cards | 9 | 112,421 | 76,646 | 189,067 | ¥2.8002 | ¥0.3111 | 1,675.3 s | 186.1 s |
| **成功 arm 合计** | **39** | **330,599** | **193,329** | **523,928** | **¥7.3688** | — | **4,370.9 s** | — |

相对 Notes：

- Enhanced Notes：平均费用约 1.02 倍，平均延迟约 1.09 倍。
- JSON Cards：平均费用约 1.36 倍，平均延迟约 1.47 倍。
- Advanced JSON Cards：平均费用约 2.30 倍，平均延迟约 2.46 倍，并有 1 个未完成 arm。

费用主要花在“会话结束后的记忆重写”，不是最后回答：Notes / Enhanced / JSON / Advanced 的成功记忆维护估算费用分别为 ¥1.1108 / ¥1.1230 / ¥1.5396 / ¥2.4150。

## 记忆结构观察

| 模式 | 最终记忆平均大小 | 中位数 | 最大值 | 格式结果 |
|---|---:|---:|---:|---|
| Notes | 5,337 bytes | 5,415 | 12,505 | 8/10 为字符串数组；2/10 漂移成对象数组 |
| Enhanced Notes | 6,051 bytes | 6,645 | 9,293 | 10/10 为字符串段落数组 |
| JSON Cards | 6,655 bytes | 8,016 | 10,544 | 10/10 为层级 JSON 对象 |
| Advanced JSON Cards | 13,151 bytes | 12,340 | 23,098 | 9 个成功 arm 的最终卡片均含 8 个必填字段 |

Notes 的 2 次结构漂移发生在 `layer1_04_airline_booking` 和 `layer3_01_travel_coordination`。这说明即使 prompt 不变，自然语言格式指令也不保证模型始终产生同一 schema。

## 与原 runner 输出上限的关系

本地 wrapper 比原 runner 宽松。成功结果中：

- 1 次记忆写入超过原 runner 的 6,000 token 上限：`layer3_04_warranty_coordination / advanced_json_cards / session 4`，实际输出 6,670 token。
- 4 个税务用例的最终回答均超过原 runner 的 1,200 token 上限，分别为 1,577 / 1,411 / 1,466 / 1,249 token。

因此若严格使用原 runner 上限，本次的“可完成性”会更差，不会更好。
