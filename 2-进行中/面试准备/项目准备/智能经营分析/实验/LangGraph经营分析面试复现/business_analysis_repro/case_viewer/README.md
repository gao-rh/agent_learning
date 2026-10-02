# 固定案例查看器

这是实验结果的只读网站。复用一套页面，直接读取 `.runs` 中已有记录，不生成新答案，不执行实验，也不加载模型密钥。原对话试玩服务继续使用 8787；查看器使用 8788。

## 打开与使用

固定入口：<http://127.0.0.1:8788/>。

服务未启动时，在实验根目录双击 `启动案例查看器.command`。它同时独立后台启动案例页（8788）和汇总阅读页（8770），关闭启动终端不影响继续浏览；重复启动复用已有服务。未设置开机自启，重启电脑后需再双击一次。日志及 PID 位于 `.runs/viewer-services/`。

等价的后台启动命令：

```bash
.venv/bin/python -m business_analysis_repro.case_viewer.start_services
```

选择一组实验 → 选择案例 → 从上往下读。每轮固定按 **用户消息 → 中间操作 → Agent 回复** 排列，下一轮紧接在后面，不需要切换阅读模式。

- **默认直接显示**：完整用户消息与回复、实际工具操作、搜索内容、返回候选与口径、提交的指标 ID / 日期 / 筛选 / 分组 / 规则，以及程序是否放行。重复提交之间，运行程序新增给模型的反馈也按顺序显示。多个任务相同的条件集中列一次，差异留在各指标下面。
- **数据表格**：模拟取数的返回行，以及旧回复中直接拼接的 JSON 数据，排成可读表格；回复原文仍可展开。没有重新生成或修正历史答案。
- **按需展开**：各任务全部字段、完整工具输入输出、模型上下文、工具定义、SQL、Token 和原始日志。折叠内容在展开时才渲染；大段模型上下文只在展开相应技术步骤时加载。读取超时会提示刷新，不会一直停留在加载状态。
- **评审单独折叠**：放在每轮回复之后，保留冻结预期、检查项及后续审计更正，明确区分事后评审和实际执行。
- **保留执行边界**：程序调用与 Agent 调用分开标记。仅提出但没有执行记录的工具请求会明确提示；未发送的后续测试消息单列。复杂澄清实验没有真正取数，不显示成已完成分析。
- **用量**：位于每轮技术详情及页尾实验信息。费用沿用已有价格参数，是估算而非账单；浏览和刷新不会调用模型。

可直接收藏或分享给同一台电脑的浏览器：

- [最新测试报告与十项结果](http://127.0.0.1:8770/)
- [Q09：澄清日期后继续取数](http://127.0.0.1:8788/case/report-v2-20261002-024754-simple-a/Q09?turn=2)
- [Q11：第四轮撤销筛选并保留分组](http://127.0.0.1:8788/case/report-v2-20261002-024754-simple-d/Q11?turn=4)
- [有定义组：程序预检索后正确使用](http://127.0.0.1:8788/case/report-v2-20261002-024754-knowledge/alias_defined?turn=1)

每步右上的“链接”可定位并分享该步骤；顶部“第 N 轮”可跳转轮次。“复制链接”复制当前地址。旧的 `turn` / `step` 深链接继续可用，指向模型上下文时自动展开对应技术详情。`127.0.0.1` 只供本机访问。

## 网址与打不开时的处理

8770 展示 Markdown 报告；8788 将 `.runs` 中的 JSON / JSONL、当时的源码快照转成只读页面。`/case/<批次>/<题号>?turn=4` 表示打开指定批次的题目并定位第四轮，`step` 可继续定位具体步骤。浏览期间不会重新调用模型。

2026-10-02 实际复现过 iCloud 占位文件导致快照读取失败、接口断开连接。单题现在先读取目标题，案例列表稍后加载；完整原件校验长度、版本及缓存内容哈希后，保留在 `~/Library/Caches/business-analysis-case-viewer/`，原始记录不改写。原件变化会使缓存失效。文件下载等待受限，页面会指出具体未就绪文件；快照格式异常会返回明确错误，主脚本未启动也有独立提示。

出现错误可点击“重新读取”；主脚本未加载时使用“重新加载页面”。服务未启动则双击实验根目录的 `启动案例查看器.command`。尚未完整下载且没有有效缓存的文件仍需等待 iCloud，不能用当前资料或空内容替代历史记录。

## 新实验怎么接入：沿用固定记录格式

不需要重写网站。新批次保存到 `.runs/<批次名>/` 后，点击“刷新记录”。目前支持三种记录格式：

| 格式 | 必要文件 | 关键字段 |
| --- | --- | --- |
| 查数与多轮追问 | `batch.json`、`Qxx-turn-N.json`、对应 `trace.jsonl` | batch 的 `case_ids` 是案例 ID → 会话 ID 字典；每轮保存 case_id、turn、question、answer、review、queries、trace |
| 纯语义 / 知识对照 | `batch.json`、`<case>/session.json`、`turn-N.json`、`review-N.json`、`trace.jsonl` | batch 的 `case_ids` 是列表；session.case 保存标题/前文/知识分组；每轮保存 actual_input、resolver_result、validation、model_submissions |

简单查询和知识对照优先读取批次 `source-snapshot.zip` 内的 `clarification_lab/fixtures/`，获得当时的名称目录、场景与评审标准。没有冻结标准时明确标记，不能用现有标准冒充历史标准。

Trace 使用现有追加事件格式：`run_id` 区分每轮，`seq` 保留事件顺序，`span_start/span_end` 配对步骤，`model_request/model_response` 保存真实模型交互。新记录可显式保存 `run_id`；旧记录按同一 Trace 对应的轮次顺序配对。不使用最新 `state.json` 反推上一轮结果。

当前是这三种实验格式的查看器；其他格式需加一次适配器，不会自动把任意 JSON 变成可靠的 case。后续新增同格式案例、指标或批次无需新增网页，也无需调用模型。

复杂语义格式：`batch.json` 显式声明 `kind=complex`，每案例保存 `turn-N.json`、`review-N.json`、`session.json` 和带独立 `run_id` 的 Trace。冻结资料位于ZIP的 `complex_lab/fixtures/`。查看器展示需求缺口、替代关系、任务版本、比较口径和审计更正；基线与提示对照是独立批次。

最新测试报告：[Markdown](../../测试报告-v2-2026-10-02-02-48-37.md) · [阅读页](http://127.0.0.1:8770/)。启动器按报告文件名中的日期时间选择最新一份；旧结果仅用于历史回放。

## 文件与验证

- `repository.py`：只读记录适配，轮次隔离、冻结标准、用量与回放边界。
- `timeline.py`：从原始事件提取连续阅读记录，保留每次提交的真实参数，不拿最终 State 覆盖中途内容。
- `storage.py`：有界读取、完整性检查及本机缓存，避免 HTTP 请求无限等待云端文件。
- `__main__.py`：仅监听本机的标准库 HTTP 服务；只提供读取接口。
- `app.html / app.css / app.js`：固定页面，不依赖 CDN、打包服务或外部图表库。
- `../../tests/test_case_viewer.py`：轮次与 Token 隔离、错误查询判分、回放边界、旧审计、冻结标准、只读与路径访问测试。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_case_viewer.py tests/test_case_viewer_storage.py tests/test_case_timeline.py -q
.venv/bin/ruff check business_analysis_repro/case_viewer tests/test_case_viewer.py tests/test_case_timeline.py
```

HTTP 测试需要允许绑定本地临时端口。该模块独立放在 `clarification_lab` 之外，避免展示代码变化导致实验模型源码指纹变化。
