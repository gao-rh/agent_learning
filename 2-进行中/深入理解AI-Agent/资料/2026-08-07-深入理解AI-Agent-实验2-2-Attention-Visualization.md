---
type: source
status: active
tags: [agent, context-engineering, attention, transformer, ai-agent-book]
created: 2026-08-07
updated: 2026-08-07
origin_type: 书籍实验
origin: 李博杰《深入理解 AI Agent》第 2 章实验 2-2
source_url: https://bojieli.github.io/ai-agent-book/chapter2/
related: [KV Cache, Context Engineering, Transformer]
---

# 实验 2-2：Attention Visualization 阶段整理

## 实验目的

这个实验不是要靠热力图完整解释模型为什么回答正确，而是建立一条进入 KV Cache 的直觉：

```text
当前位置的 Query 与历史 Key 匹配
→ mask + softmax 得到 Attention Weight
→ 对历史 Value 加权求和
→ 更新当前位置的 hidden state
→ 最后位置经 LM Head 预测下一个 token
```

## 用户实际完成的观察

- 运行默认 Prompt `北京 的 天气 怎么样`，观察最后一层、多 Head 平均图。
- 对比多 Head 平均与单 Head；理解平均会平滑不同 Head 的模式。
- 对比 Layer 0、Layer 1 和 Layer -1 的单 Head 图：浅层更接近对角/局部模式，末层在本输入上更分散并出现强首列。
- 识别第一列是 Chat Template 注入的 `<|im_start|>`，其高权重属于 attention sink 现象，不能直接等同于语义重要性或输出贡献。
- 通过改进后的学习网页辨认 Query 行、Key 列、Prompt/Generated 边界提示与原始/细节色标的差异。

## 已稳定的理解

| 问题 | 当前结论 |
| --- | --- |
| 热力图展示什么？ | 展示 `QK^T` 打分经 causal mask 与 softmax 后的 Attention Weight，不是 Q、K 或 V 本身。 |
| 一个格子表示什么？ | Query 行中的当前位置，把多少注意力权重分给 Key 列中的历史/当前位置。 |
| 为什么右上角为空？ | Causal mask 禁止当前位置读取未来位置；它是计算规则，不是一个 `[MASK]` token。 |
| Token 会关注自己吗？ | 可以。对角线是动态计算的自身注意力权重，不是每个 token 预存的固定参数；残差连接也会保留自身信息。 |
| Layer 与 Head 是什么关系？ | Layer 串行加工 hidden states；每层内部有多个 Head 并行读取信息。不同 Layer 的同编号 Head 是不同参数。 |
| `weights × V` 得到什么？ | 得到 attention output/context vector；它还要经过输出投影、残差和 MLP 才形成下一层 hidden state。 |
| 新 token 何时出现？ | 同一轮各 Layer 的序列长度不变；最后一个已有位置的最终 hidden state 经 LM Head 产生词表 logits，采样出的 token 在下一轮才作为新位置进入 Transformer。 |
| 为什么缓存 K/V？ | 未来的新 Query 需要反复匹配历史 K 并读取历史 V；历史 Query 用完后通常不再被未来位置读取。 |

## 用户理解发生的关键变化

1. 从“热力图可能展示 Value”修正为“热力图展示归一化后的 Attention Weight”。
2. 从“每层生成下一个 token”修正为“Layer 更新同一批位置，LM Head 在本轮结束后预测新 token”。
3. 从“尾部可能有一个 Mask 占位”修正为“causal mask 是分数矩阵上的未来访问禁令”。
4. 保留了一个正确判断：Transformer 同一轮各层的 token 数量与 hidden 维度必须对齐；这正好反证新 token 不会突然出现在最后一层内部。

## 证据边界

- 当前图能证明 causal triangle、特定输入/Layer/Head 的权重模式以及 attention sink 的存在，不能单独证明语义因果或某个 token 对最终输出最重要。
- “深层一定比浅层复杂”不能泛化；这里只观察到 Qwen3-0.6B 的一个 Prompt 和 Head 的变化。
- 教材 README 的生成续写步骤没有由用户单独描述并完成验收。用户在掌握核心机制后明确选择进入 2-3，因此本记录标记为“核心学习目标完成”，不声称官方所有观察步骤均已完成。

## 主动回忆

1. 热力图中一行、一列和一个格子分别表示什么？
2. 为什么 causal mask 不是一个 `[MASK]` token？
3. 输入 A/B 时，C 在哪里被预测出来？C 什么时候进入 Layer 0？
4. 为什么 KV Cache 缓存 K/V，而通常不缓存历史 Q？

## 下一步

进入实验 2-3，比较稳定前缀与五种上下文反模式如何改变缓存比例；优先把 `Cache%` 当主证据，把 TTFT 当噪声更大的辅助证据。
