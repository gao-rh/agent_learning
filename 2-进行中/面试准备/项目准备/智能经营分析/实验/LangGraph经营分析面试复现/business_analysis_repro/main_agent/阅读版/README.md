# 主 Agent 注释阅读版

2026-09-07 源码阅读快照。先看 [代码阅读摘要](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/代码阅读摘要.md)。优先从 [主图的 compose_reply](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/阅读版/04_主图_注释版.py:286) 继续，其余文件按需查阅。

这些是完整原文件加教学注释的副本，不作为独立脚本运行；相对导入与原文件一致。运行仍从原包入口开始。当前八份副本的 AST 与各自原文件一致，语法编译通过；没有本轮 Kimi 调用或新增业务实现。

| 阅读版 | 原文件 | 主要用途 |
| --- | --- | --- |
| [01_入口_注释版.py](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/阅读版/01_入口_注释版.py:8) | [__main__.py 1–87 行](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/__main__.py:1) | 命令行传参、接收执行结果、退出码 |
| [02_运行管理_注释版.py](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/阅读版/02_运行管理_注释版.py:8) | [runtime.py 1–156 行](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/runtime.py:1) | 创建运行依赖、打开 checkpoint、驱动图、恢复及导出 |
| [03_状态定义_注释版.py](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/阅读版/03_状态定义_注释版.py:8) | [state.py 1–90 行](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/state.py:1) | 模型输出结构与主图共享数据 |
| [04_主图_注释版.py](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/阅读版/04_主图_注释版.py:8) | [graph.py 1–419 行](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/graph.py:1) | 七个节点、条件边、有限修复与结束 |
| [05_业务函数_注释版.py](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/阅读版/05_业务函数_注释版.py:8) | [capabilities.py 1–217 行](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/capabilities.py:1) | 准入、模拟取数、Python 分析、口径查询 |
| [06_指标目录_注释版.py](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/阅读版/06_指标目录_注释版.py:8) | [catalog.py 1–119 行](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/catalog.py:1) | 指标定义和本次查询配置 |
| [07_模型调用_注释版.py](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/阅读版/07_模型调用_注释版.py:8) | [model.py 1–117 行](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/model.py:1) | 构造上下文、请求 Kimi、结构校验和重试 |
| [08_轨迹记录_注释版.py](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/阅读版/08_轨迹记录_注释版.py:8) | [trace.py 1–123 行](/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/trace.py:1) | 追加事件、关联父子调用、生成可读回放 |

每份文件顶部保留原路径和 SHA-256；下文注释标记的行号始终指原文件。原文件若以后变化，这些副本不会自动更新。
