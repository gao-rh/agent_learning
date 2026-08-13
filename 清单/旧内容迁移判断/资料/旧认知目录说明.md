# 认知迭代

这里保存 DeepMe 同步内容、每日反思、判断更新和认知迭代记录。

一条认知迭代不等于普通日记。它至少要说清楚：

- 原来的判断是什么。
- 今天的新证据是什么。
- 判断发生了什么变化。
- 下一步要验证什么。

建议命名：

```text
YYYY-MM-DD-认知迭代.md
deepme/
```

如果 DeepMe 有独立 GitHub 仓库，可以同步到 `60-cognition/deepme/`，再由 Codex 做每日汇总和周复盘。

## 每晚反思提醒

当前本机配置了 Hermes cron：

```text
daily-cognitive-reflection-codex
```

- 时间：每天 22:00（Asia/Shanghai）
- 投递：QQBot 私聊
- 机制：Hermes 只负责定时触发和 QQ 投递；实际反思总结由 Codex CLI 使用 `gpt-5.5` 以只读方式生成。
- 脚本：`~/.hermes/scripts/daily-cognitive-reflection-codex.sh`

这个任务默认不自动修改笔记。如果有值得沉淀的新内容，它只会建议目标文件和写法。

手机提醒不追求完整报告。默认文案控制在 120-180 个中文字符，只输出三行：

```text
今晚一句话：今天最重要的认知变化。
问自己：一个真正值得停下来想的问题。
明天一小步：一个 10 分钟内能完成的验证动作。
```
