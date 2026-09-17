"""并行 Trace：追加写加锁，ContextVar 绑定 job，按分支回放。

seq 是写入顺序，不是业务依赖顺序。parent_span_id / job_id 才用于归属。
HTML 是 JSONL 的只读投影，可在执行中刷新，也可离线打开最终报告。
"""

import json
from contextlib import contextmanager
from contextvars import ContextVar
from html import escape
from threading import RLock

from ..main_agent.trace import Trace as BaseTrace
from . import catalog

_job = ContextVar("playground_trace_job", default=None)

LABELS = {
    "prepare_context": "准备上下文 · 历史与业务条件",
    "compress_context": "压缩旧对话 · 生成历史摘要",
    "handle_inbox": "主 Agent 处理插入消息",
    "reuse_evidence": "复用同任务中已取得的数据",
    "parallel-v4": "父图执行",
    "analysis-v5": "父图执行（简易分析）",
    "adaptive_analysis": "分析Agent",
    "analysis_decision": "读取证据并选择下一步",
    "analysis_followup": "按假设补查",
    "load_analysis_skill": "读取专题Skill",
    "search_business_knowledge": "检索业务知识",
    "understand_request": "理解需求与拆解",
    "resolve_batch": "模型搜索与规划",
    "search_metrics": "搜索指标",
    "get_metric_definition": "读取指标口径",
    "search_dimensions": "查找支持维度",
    "search_dimension_values": "搜索枚举",
    "finish_resolution": "提交候选计划",
    "validate_dates": "核对日期",
    "clarify": "等待补充 / 恢复",
    "metric_worker": "指标子任务",
    "query_agent": "查询数据",
    "analysis_agent": "对比分析",
    "analysis.query_agent": "查询一个期间",
    "knowledge_agent": "读取口径",
    "gather_results": "汇总所有分支",
    "compose_reply": "生成执行摘要",
    "compose_batch": "模型写摘要",
    "validate_reply": "校验与交付",
    "validate_batch_reply": "模型复核摘要",
}
STATUS = {
    "superseded": "已按新要求调整",
    "completed": "已完成",
    "cancelled": "已停止",
    "cancelling": "正在停止",
    "queued": "排队",
    "running": "执行中",
    "retrying": "重试中",
    "ok": "成功",
    "failed": "失败",
    "needs_clarification": "需要调整",
    "interrupted": "等待补充",
    "error": "异常",
}


def read_events(path):
    """实时读可能遇到尚未写完的末行；历史完整行损坏则明确报错。"""
    if not path.exists():
        return []
    lines = path.read_text().splitlines()
    result = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            result.append(json.loads(line))
        except json.JSONDecodeError:
            if i != len(lines) - 1:
                raise
    return result


def progress_jobs(events):
    # 每次重新规划只展示该计划的分支；历史计划仍在完整 Trace 中。
    plan = next((e for e in reversed(events) if e["kind"] == "plan"), None)
    jobs = {}
    if plan:
        jobs = {
            j["job_id"]: {"job_id": j["job_id"], "name": j["name"], "status": "queued"}
            for j in plan["jobs"]
        }
        for e in events:
            if e["seq"] > plan["seq"] and e["kind"] == "job_status" and e.get("job_id") in jobs:
                jobs[e["job_id"]].update(status=e["status"], attempts=e.get("attempts"))
    return list(jobs.values())


class Trace(BaseTrace):
    def __init__(self, *args, **kwargs):
        self._write_lock = RLock()
        super().__init__(*args, **kwargs)

    def read(self):
        with self._write_lock:
            return read_events(self.path)

    def check_cancel(self):
        from .run_control import check_cancel
        check_cancel(self)

    def event(self, kind, name, **data):
        if kind == "model_request":
            self.check_cancel()
        job = _job.get()
        if job:
            data = {"job_id": job["job_id"], "metric_name": job["name"], **data}
        # 一把锁包住 seq、序列化和 append/fsync；并行写不会重复编号或交错半行。
        with self._write_lock:
            # 决策模型现在可在多个分析分支里并行调用。检查与记账必须在同一把锁内，
            # 否则多个分支会同时看到“还剩一次”，一起越过任务预算。
            if (kind == "model_request" and hasattr(self, "model_call_limit")
                    and sum(e["kind"] == "model_request" for e in self.read()) >= self.model_call_limit):
                from ..main_agent.model import ModelFailure
                raise ModelFailure("本任务达到模型调用次数上限。")
            return super().event(kind, name, **data)

    @contextmanager
    def job(self, job):
        token = _job.set(job)
        try:
            yield
        finally:
            _job.reset(token)

    def render(self):
        output = self.directory / "trace.html"
        output.write_text(render_html(self.read(), self.thread_id))
        return output


def render_html(events, thread_id, conversation_id=None):
    def pretty(value):
        return "<pre>" + escape(json.dumps(value, ensure_ascii=False, indent=2)) + "</pre>"

    starts = {e["span_id"]: e for e in events if e["kind"] == "span_start"}
    ends = {e["span_id"]: e for e in events if e["kind"] == "span_end"}
    children = {}
    for e in starts.values():
        children.setdefault(e.get("parent_span_id"), []).append(e["span_id"])
    direct_events = {}
    for e in events:
        if e["kind"] not in {"span_start", "span_end", "state_snapshot", "graph_update"}:
            direct_events.setdefault(e.get("parent_span_id"), []).append(e)

    def span_html(span_id):
        start, end = starts[span_id], ends.get(span_id, {})
        title = LABELS.get(start["name"], start["name"])
        if start.get("metric_name"):
            title += " · " + start["metric_name"]
        status = STATUS.get(end.get("status"), "执行中")
        body = (
            "<details><summary>"
            + escape(title)
            + " <small>"
            + escape(f"{status} · {end.get('elapsed_ms', '…')} ms · {start['time'][11:23]} UTC")
            + "</small></summary>"
        )
        body += "<p>输入</p>" + pretty(start.get("inputs"))
        attached = direct_events.get(span_id, [])
        deltas = [e for e in attached if e["kind"] == "answer_delta"]
        if deltas:
            body += (
                f"<details><summary>流式正文 · {len(deltas)} 个片段（生成草稿）</summary>"
                + "<p>片段按实际接收顺序拼接；此处保留生成过程，最终结果以校验与交付为准。</p>"
                + pretty("".join(e["delta"] for e in deltas))
                + "</details>"
            )
        for event in attached:
            if event["kind"] == "answer_delta":
                continue  # 每个片段仍在原始JSONL；回放折叠为一段，避免几百行按钮。
            body += (
                "<details><summary>"
                + escape(event["kind"] + " · " + event["name"])
                + "</summary>"
                + pretty(event)
                + "</details>"
            )
        body += "".join(span_html(child) for child in children.get(span_id, []))
        if end:
            body += "<p>输出 / 异常</p>" + pretty(end.get("output"))
        return body + "</details>"

    plans = [e for e in events if e["kind"] == "plan"]
    jobs = progress_jobs(events)
    usage = [e.get("usage", {}) for e in events if e["kind"] == "model_response"]
    total_tokens = sum(u.get("total_tokens", 0) for u in usage)
    calls = sum(e["kind"] == "model_request" for e in events)
    queries = [e for e in starts.values() if e["name"] in {"query_agent", "analysis.query_agent"}]
    summary = next((e["summary"] for e in reversed(events) if e["kind"] == "batch_summary"), {})
    latest_state = next((e["state"] for e in reversed(events) if e["kind"] == "state_snapshot"), {})
    blocks = [
        "<!doctype html><html lang='zh-CN'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
        (
            "<title>并行执行回放</title><style>"
            "body{max-width:1200px;margin:28px auto;padding:0 24px;font:15px/1.6 -apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif;color:#263b32;background:#f6f8f6}"
            "h1{font-size:26px}h2{font-size:19px;margin-top:28px}small,.muted{color:#60756a}"
            ".stats{padding:16px;background:#e7f1e9;border-radius:10px}table{border-collapse:collapse;width:100%;font-size:13px;background:white}"
            "td,th{border:1px solid #dce5df;text-align:left;padding:9px}th{background:#eff4f0}"
            "details{background:white;border:1px solid #dbe5de;border-radius:8px;padding:10px 14px;margin:10px 0}"
            "details details{margin-left:12px}summary{cursor:pointer;font-weight:600}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.6 ui-monospace,monospace;background:#f5f7f5;padding:12px;max-height:600px;overflow:auto}"
            "button,a{color:#235c42}button{padding:6px 12px;border:1px solid #bdcfc2;background:white;border-radius:6px;cursor:pointer}"
            ".scroll{overflow:auto}.pill{white-space:nowrap}.fact{white-space:pre-wrap}</style>"
        ),
        "<h1>并行执行回放</h1><p class='muted'>先看拆解计划，再按指标展开。编号是落盘顺序；分支的时间可能重叠。</p>",
        (
            f"<div class='stats'>任务 {escape(thread_id)} · 状态 {escape(STATUS.get(latest_state.get('status'), latest_state.get('status', '执行中')))}<br>"
            f"并发上限 5（当前服务进程共享） · 模型请求 {calls} 次 · 已返回 token {total_tokens:,} · 期间查询尝试 {len(queries)} 次</div>"
        ),
        "<p><button onclick='location.reload()'>刷新执行进度</button> <small>执行中的页面可刷新；最终 HTML 也可离线打开。Trace 不包含模型内部思考。</small></p>",
    ]
    contexts = [e for e in events if e["kind"] == "context_prepared"]
    if contexts:
        blocks.append("<h2>本轮模型记住了什么</h2><p>历史预算采用本地 Token 估算；"
                      "当前需求和澄清原文另外保留。摘要不是指标口径或取数证据。</p>")
        modes = {"full": "完整历史", "cached": "复用摘要 + 近期原文",
                 "compressed": "本轮压缩旧对话"}
        for event in contexts:
            blocks.append("<div class='stats'>" + escape(modes.get(event["mode"], event["mode"]))
                + f" · 历史 {event['history_turns']} 轮 · 约 {event['tokens_before']:,}"
                + f" → {event['tokens_after']:,} Tokens<br>"
                + f"保留原文 {event['recent_turns']} 轮 · 已处理旧历史 {event['summarized_turns']} 轮"
                + f" · 本轮摘要步骤 {event['summary_calls']} 次</div>")
            if event.get("degraded") or event.get("excerpted_turns"):
                blocks.append("<p>部分历史使用摘录或有遗漏；完整内容仍在原会话，"
                              "涉及未保留的细节应重新确认。</p>")
            if event.get("over_budget"):
                blocks.append("<p>受保护的业务条件较长，本轮历史仍超过预算，未截断业务字段。</p>")
            memory = event.get("memory", {})
            blocks.append("<details><summary>查看旧对话摘要</summary>"
                          + pretty(memory.get("summary") or "本轮无需摘要") + "</details>")
            blocks.append("<details><summary>查看单独保留的业务条件</summary>"
                          + pretty({"最近业务焦点": memory.get("business_anchor"),
                                    "之前查数分析的条件": memory.get("last_data_task")}) + "</details>")
            blocks.append("<details><summary>查看实际发送的近期原文</summary>"
                          + pretty(event.get("recent_context")) + "</details>")
    controls = [e for e in events if e["kind"] in {
        "cancel_requested", "query_cancel_result", "execution_cancelled"}]
    inserts = [e for e in events if e["kind"] == "inbox_applied"]
    if inserts:
        blocks.append("<h2>运行中插入的消息</h2><p>发送先排队；点击立即插入后，在下一次调用边界由主 Agent 处理。</p>"
                      "<table><tr><th>处理时间 UTC</th><th>用户消息</th><th>处理方式</th><th>主 Agent 回复</th></tr>")
        actions = {"reply": "回复，原任务继续", "continue": "吸收补充，继续当前任务",
                   "revise": "调整范围，复用兼容数据", "stop": "停止当前任务"}
        for event in inserts:
            decision = event["decision"]
            values = [event["time"][11:23], "\n".join(r["text"] for r in event["messages"]),
                      "处理失败，文字保留" if decision.get("error") else actions.get(decision["action"], decision["action"]),
                      decision["reply"]]
            blocks.append("<tr>" + "".join("<td class='fact'>" + escape(v) + "</td>" for v in values) + "</tr>")
        blocks.append("</table>")
    if controls:
        blocks.append("<h2>停止记录</h2><p>停止后保留已返回调用的用量和轨迹；本轮不再交付完整结果。</p><ol>")
        for event in controls:
            message = {
                "cancel_requested": "收到停止请求，等待当前调用返回，禁止后续调用。",
                "execution_cancelled": "图内分支已退出，正在保存记录；随后可启动下一条问题。",
                "query_cancel_result": "已向模拟查询发出取消请求。",
            }[event["kind"]]
            if event["kind"] == "query_cancel_result" and event.get("status") == "failed":
                message = "查询取消接口失败，仍在本地停止后续执行。"
            blocks.append("<li>" + escape(event["time"][11:23] + " UTC · " + message)
                          + (" 查询ID：" + escape(event["query_id"]) if event.get("query_id") else "") + "</li>")
        blocks.append("</ol>")
    if conversation_id:
        blocks.append(
            f"<p><a href='/flow/{escape(conversation_id)}/{escape(thread_id)}'>打开可点击的执行路线与逐步回放 →</a></p>"
        )
    if plans:
        blocks.append("<h2>拆解与并行计划</h2>")
        for plan in plans:
            blocks.append(
                "<p>"
                + escape(plan.get("decomposition", ""))
                + f"（去重 {plan.get('deduplicated', 0)} 项）</p>"
            )
            blocks.append(
                "<div class='scroll'><table><tr><th>子任务</th><th>指标</th><th>期间 / 分组 / 筛选</th></tr>"
            )
            for job in plan["jobs"]:
                task = job["task"]
                scope = [
                    {"query": "查数", "analysis": "本期与前期对比", "knowledge": "解释口径"}[
                        task["intent"]
                    ],
                    task.get("start_date", "") + " ～ " + task.get("end_date", ""),
                    "分组："
                    + (
                        " / ".join(catalog.DIMENSIONS[d]["name"] for d in task["group_by"])
                        or "合计"
                    ),
                    "筛选："
                    + (
                        "；".join(
                            catalog.DIMENSIONS[d]["name"]
                            + "="
                            + "/".join(catalog.enum_name(d, v) for v in values)
                            for d, values in task["filters"].items()
                        )
                        or "全部合法枚举"
                    ),
                ]
                blocks.append(
                    "<tr><td>"
                    + escape(job["job_id"])
                    + "</td><td>"
                    + escape(job["name"])
                    + "</td><td>"
                    + "<div class='fact'>"
                    + escape("\n".join(scope))
                    + "</div>"
                    + "<details><summary>精确查询参数</summary>"
                    + pretty(task)
                    + "</details>"
                    + "</td></tr>"
                )
            blocks.append("</table></div>")
    if jobs:
        blocks.append(
            "<h2>各分支的执行时间</h2><table><tr><th>指标</th><th>状态</th><th>开始 → 结束（UTC）</th><th>尝试次数</th></tr>"
        )
        for job in jobs:
            transitions = [
                e for e in events if e["kind"] == "job_status" and e.get("job_id") == job["job_id"]
            ]
            start = next(
                (e["time"][11:23] for e in transitions if e["status"] == "running"), "排队"
            )
            end = next(
                (
                    e["time"][11:23]
                    for e in reversed(transitions)
                    if e["status"] in {"ok", "failed", "needs_clarification", "cancelled"}
                ),
                "执行中",
            )
            blocks.append(
                f"<tr><td>{escape(job['name'])}</td><td>{STATUS.get(job['status'], job['status'])}</td><td>{start} → {end}</td><td>{job.get('attempts') or '—'}</td></tr>"
            )
        blocks.append("</table>")
    if summary:
        blocks.append(f"<h2>交付结果 · 成功 {summary['succeeded']} / 失败 {summary['failed']}</h2>")
        for card in summary["cards"]:
            blocks.append(
                "<details><summary>"
                + escape(card["name"])
                + f" · {STATUS.get(card['status'], card['status'])} · {len(card['rows'])} 行明细</summary>"
            )
            if card.get("error"):
                blocks.append(pretty(card["error"]))
            else:
                blocks.append(
                    "<div class='fact'>"
                    + escape("\n".join(f"{k}：{v}" for k, v in card["facts"].items()))
                    + "</div>"
                )
                if card["rows"]:
                    blocks.append(
                        "<p>维度顺序："
                        + escape(" / ".join(card["group_by"]))
                        + "</p><div class='scroll'><table><tr><th>分组</th><th>本期</th>"
                        + ("<th>前期</th><th>变化</th>" if card["has_baseline"] else "")
                        + "</tr>"
                    )
                    for row in card["rows"]:
                        keys = ["group", "current"] + (
                            ["baseline", "change"] if card["has_baseline"] else []
                        )
                        blocks.append(
                            "<tr>"
                            + "".join("<td>" + escape(row[k]) + "</td>" for k in keys)
                            + "</tr>"
                        )
                    blocks.append("</table></div>")
            blocks.append("</details>")
    blocks.append(
        "<h2>全链路：父图 → 节点 → 模型 / 工具</h2><p class='muted'>模型节点可展开真实请求消息、tool_calls、工具返回及 token；数据工具可查看实际参数、SQL、结果与异常。状态快照在末尾原始事件中。</p>"
    )
    roots = [e["span_id"] for e in starts.values() if e.get("parent_span_id") not in starts]
    blocks.extend(span_html(root) for root in roots)
    blocks.append(
        "<details><summary>全部原始事件（包含 State 快照与迁移来源）</summary>"
        + pretty(events)
        + "</details></html>"
    )
    return "".join(blocks)
