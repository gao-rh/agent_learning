# Attention Visualization 学习操作台

这是《深入理解 AI Agent》实验 2-2 `attention_cli.py` 的薄网页包装。

它不改变教材实验：页面收集预测和参数，显示等价 CLI 命令，调用教材脚本并展示生成的 PNG。这样可以减少反复输入命令和寻找图片的操作，但不能代替观察、描述与解释。

页面额外提供高对比配色、横纵轴语义提示、缩放和原始大图入口，并同时生成两种视图：

- 教材原始权重图：线性色标，忠实显示绝对权重，适合观察 attention sink 和 causal triangle。
- 低权重细节图：用 `PowerNorm(gamma=0.22)` 拉伸颜色，让很小的权重差异可见；attention 数值本身不变。

## 启动

```bash
cd "/Users/gaoronghui/Documents/agent_learning/2-进行中/深入理解AI-Agent/资料/本地资料/深入理解AI-Agent/ai-agent-book-chapter2-current"
source .venv/bin/activate
cd "/Users/gaoronghui/Documents/agent_learning/2-进行中/深入理解AI-Agent/实验/attention-visualization-learning-ui"
python app.py
```

浏览器打开：<http://127.0.0.1:8000>

按 `Control-C` 停止网站。

## 学习规则

1. 运行前填写预测。
2. 按老师给出的当前步骤设置参数，不提前跳到后续变量。
3. 运行后先描述坐标、亮区和预测是否一致。
4. 把观察发给 Codex，完成机制解释后再进入下一步。

生成图片保存在本目录的 `outputs/` 下，不提交 Git。
