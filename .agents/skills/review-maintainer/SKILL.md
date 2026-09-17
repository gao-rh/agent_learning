---
name: review-maintainer
description: 维护本仓库的索引、链接、AI 摘要及周月回顾草案，或盘点已授权迁移。用于仓库维护任务，不用于普通讨论或规划决策。
---

# 回顾维护

适用于 `/Users/gaoronghui/Documents/agent_learning`；遵循根目录 [AGENTS.md](../../../AGENTS.md) 的写入、状态和 Git 约定。

按任务范围读取相关索引和主题 README；周月回顾覆盖对应期间的进行中主题，局部链接修复无需扫描全库。仅在异常需要时深入实验、依赖或参考资料。

- 扫描逾期事项、需跟进但缺少检查日期的事项、长期无活动主题和失效链接，报告事实与异常，不据此自动改变优先级或完成状态。
- 自动重建摘要时使用 `<!-- AI-SUMMARY:START -->` / `<!-- AI-SUMMARY:END -->`，保留标记外正文。按授权更新机械索引和迁移链接，不删除原始资料。
- 周月回顾输出到 `2-进行中/周期回顾/记录/`，分别使用 `YYYY-Www-周回顾草案.md`、`YYYY-MM-月度回顾草案.md`。使用[回顾草案模板](assets/review-draft-template.md)，分清事实、机械异常、待用户决定与 AI 建议。
- 按改动验证链接、JSON、Git 差异和意外大文件；只有任务已授权且验证通过时才提交、推送。

## 专用脚本

- [check_markdown_links.py](scripts/check_markdown_links.py)：`--root .` 检查当前资料的本地链接，默认不遍历归档、本人面试记录、本地原件、依赖和生成物；`--list` 只列出范围；局部修改用 `--files 路径1.md 路径2.md`，路径相对仓库根目录。显式文件列表可用于用户授权的历史资料核对。仅检查目标路径存在性，不验证网页、锚点和正文正确性。
- [inventory.py](scripts/inventory.py)：迁移盘点时生成文件清单与摘要，参数见 `--help`。
- [stage_safe.py](scripts/stage_safe.py)：已授权提交前使用，处理 iCloud File Provider 兼容问题并遵守 `.gitignore`。优先用 `--root . --files 路径1 路径2 --dry-run` 预览范围，再去掉 `--dry-run` 暂存；预览不读取正文或修改暂存区。默认批量模式跳过归档、本人面试记录和迁移待判断原文，涉及这些资料时需按授权显式列出文件。已有混合改动时先核对差异，不能把整库暂存当作局部维护提交。
  - 白名单包含网页源码、YAML 配置、文本快照及启动脚本。`output/docx/` 下不超过 5 MiB 的正式 Word 导出仅接受显式文件列表；PDF、临时预览、真实凭据与数据库运行缓存不纳入本脚本暂存。
