---
type: map
status: active
tags: [obsidian, workflow]
created: 2026-06-13
updated: 2026-06-13
---

# Obsidian 使用设置

## 日常入口

优先从这些页面开始，而不是从图谱开始：

- [AI Agent 与机器学习学习地图](AI%20Agent%E4%B8%8E%E6%9C%BA%E5%99%A8%E5%AD%A6%E4%B9%A0%E5%AD%A6%E4%B9%A0%E5%9C%B0%E5%9B%BE.md)
- [长期学习工作流](../50-systems/%E9%95%BF%E6%9C%9F%E5%AD%A6%E4%B9%A0%E5%B7%A5%E4%BD%9C%E6%B5%81.md)
- [Inbox](../00-inbox/README.md)

## 图谱筛选

默认图谱筛选：

```text
-file:README -path:templates
```

作用：

- 隐藏目录说明页，避免一堆 `README` 干扰判断。
- 隐藏模板文件，避免 `concept`、`source-note`、`weekly-review` 这类工具页出现在知识图谱里。
- 保留真正的学习笔记、概念卡片、实验记录和系统方法论。

如果以后 `assets/` 里出现很多 Markdown 说明页，可以临时改成：

```text
-file:README -path:templates -path:assets
```

## 使用原则

图谱用来观察关系，不作为主要导航。

主要导航依赖：

1. `01-maps/` 里的学习地图。
2. Obsidian 搜索。
3. 反向链接。
4. 每周复盘里的下一步列表。

