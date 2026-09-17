"""将真实事件投影成按节点阅读的回放，不用模型改写或补造历史。

几十条 span/request/state 事件被归到实际执行的节点里。说明文字按代码语义生成，
数字、提议、草稿、错误、路由和配置全部来自日志。旧日志缺失的元数据保持缺失。
"""

import json
from pathlib import Path

LABELS = {
    "understand_request": "理解你的问题",
    "clarify": "补充必要信息",
    "run_query": "按指标配置取数",
    "run_analysis": "取数并完成分析",
    "consult_knowledge": "查找指标口径",
    "compose_reply": "组织回答",
    "validate_reply": "检查回答",
}
STATUS = {
    "running": "执行中",
    "waiting_user": "等待你补充",
    "completed": "已完成",
    "failed": "未完成",
}
INTENTS = {"query": "查询一个数值", "analysis": "分析变化及渠道贡献", "knowledge": "解释指标口径"}


def state_fields(state):
    """只显示人理解流程需要的工作数据，完整 State 仍在原始记录中。"""
    task = state.get("task") or {}
    result = state.get("result") or {}
    verdict = state.get("validation") or {}
    return {
        "执行状态": STATUS.get(state.get("status"), "尚未开始"),
        "任务类型": INTENTS.get(task.get("intent"), "尚未确定"),
        "业务": task.get("business") or "尚未确定 / 本任务不需要",
        "指标 ID": task.get("metric_id") or task.get("metric") or "尚未确定",
        "日期": f"{task['start_date']} 至 {task['end_date']}"
        if task.get("start_date")
        else "尚未确定 / 本任务不需要",
        "任务版本": state.get("task_revision", 0),
        "取数或分析结果": "已取得"
        if result.get("status") == "ok"
        else "失败"
        if result.get("status") == "failed"
        else "尚未取得",
        "回答检查": "通过" if verdict.get("passed") else "未通过" if verdict else "尚未检查",
        "回复重写次数": state.get("repair_count", 0),
        "回答草稿": ((state.get("draft_reply") or {}).get("text") or "尚未生成")[:120],
        "最终交付": (state.get("answer") or "尚未交付")[:120],
        "需要你补充": state.get("pending_question") or "无",
    }


def walk_results(value):
    if isinstance(value, dict):
        if value.get("source") in {"query", "analysis", "knowledge"} and value.get("facts"):
            yield value
        for key in ["current", "baseline", "result"]:
            yield from walk_results(value.get(key))


def report_data(events, thread_id):
    starts = [e for e in events if e["kind"] == "span_start" and e.get("category") == "node"]
    ends = {e["span_id"]: e for e in events if e["kind"] == "span_end"}
    parents = {e["span_id"]: e.get("parent_span_id") for e in events if e["kind"] == "span_start"}
    final = next((e["state"] for e in reversed(events) if e["kind"] == "state_snapshot"), {})
    question = next(
        (
            e.get("input", {}).get("question")
            for e in events
            if e["kind"] == "execution_start" and e.get("input", {}).get("question")
        ),
        "未记录原始问题",
    )

    def belongs(event, span_id):
        cursor = event.get("parent_span_id")
        while cursor:
            if cursor == span_id:
                return True
            cursor = parents.get(cursor)
        return event.get("span_id") == span_id

    steps = []
    metrics, queries = {}, {}
    seen_names = {}
    for index, start in enumerate(starts):
        name = start["name"]
        seen_names[name] = seen_names.get(name, 0) + 1
        end = ends.get(start["span_id"])
        output = end.get("output", {}) if end else {}
        patch = output.get("state_update", {})
        before = start.get("inputs") or {}
        until = starts[index + 1]["seq"] if index + 1 < len(starts) else float("inf")
        after = next(
            (
                e["state"]
                for e in events
                if end and end["seq"] < e["seq"] < until and e["kind"] == "state_snapshot"
            ),
            before,
        )
        route = next(
            (e for e in events if end and end["seq"] < e["seq"] < until and e["kind"] == "route"),
            None,
        )
        owned = [e for e in events if belongs(e, start["span_id"])]
        errors = [e["error"] for e in owned if e["kind"] in {"node_error", "model_error"}]
        parsed = [
            e["output"]["parsed"]
            for e in owned
            if e["kind"] == "span_end" and e.get("output", {}).get("parsed")
        ]
        metric = next((e["metric"] for e in owned if e["kind"] == "metric_resolution"), None)
        results = list(walk_results(patch.get("result")))
        for result in results:
            definition = result.get("metric_definition")
            if definition:
                metrics[(definition["metric_id"], definition.get("business"))] = definition
            if result.get("query_execution"):
                queries[result["evidence_id"]] = {
                    "evidence_id": result["evidence_id"],
                    "facts": result["facts"],
                    "execution": result["query_execution"],
                    "checks": result.get("checks", {}),
                    "total": result.get("total"),
                }
        if metric:
            metrics[(metric["metric_id"], metric.get("business"))] = metric
        task = patch.get("task") or before.get("task") or {}
        title = LABELS.get(name, name)
        notes, facts = [], {}
        text = ""
        tone, outcome = "good", "完成"
        if name == "understand_request":
            candidate = parsed[0] if parsed else {}
            if patch.get("pending_question"):
                notes = [
                    "模型理解了部分需求，但执行所需的信息还不完整。",
                    "程序选择先询问你，尚未开始取数。",
                ]
                text = patch["pending_question"]
                tone, outcome = "wait", "需要补充"
            elif task:
                notes = [
                    f"识别为“{INTENTS.get(task.get('intent'), '未确定')}”。",
                    "模型提出业务和指标；程序查指标配置并计算实际日期，再选择下一步。",
                ]
                facts = {
                    "业务": task.get("business") or "此问题不需要业务",
                    "指标": (metric or {}).get("name") or task.get("metric"),
                    "时间": f"{task['start_date']} 至 {task['end_date']}"
                    if task.get("start_date")
                    else "口径解释不需要日期",
                }
            else:
                notes = [(patch.get("result") or {}).get("reason", "未得到可以执行的任务。")]
                tone, outcome = "bad", "停止执行"
            if candidate.get("reason"):
                notes.append("模型返回的判断说明：" + candidate["reason"])
        elif name == "clarify":
            if end and end.get("status") == "interrupted":
                title = "等你补充信息"
                text = before.get("pending_question") or "等待用户输入。"
                notes = ["任务状态已保存到 SQLite。此时进程可以退出，补充后继续原任务。"]
                tone, outcome = "wait", "已暂停"
            else:
                title = "收到你的补充"
                messages = patch.get("messages", [])
                text = messages[-1].get("content", "") if messages else "未记录补充内容。"
                notes = ["从之前保存的位置恢复，把这次补充交回理解环节。没有重复取数。"]
        elif name in {"run_query", "run_analysis", "consult_knowledge"}:
            result = patch.get("result") or {}
            if result.get("status") == "ok":
                facts = result.get("facts", {})
                if name == "run_analysis":
                    notes = [
                        "查询本期与前一段等长期间，代码计算差额、变动率和渠道贡献。",
                        "下方数值来自取数结果；渠道贡献能定位变化分布，不能证明业务因果。",
                    ]
                elif name == "run_query":
                    execution = result.get("query_execution", {})
                    method = {
                        "metric_platform": "指标平台的本地模拟接口",
                        "sql": "本地 SQLite 的参数化 SQL",
                    }.get(execution.get("method"), "旧版取数函数（当时未记录详细查询配置）")
                    notes = [
                        f"本次实际执行：{method}。",
                        "完成日期范围内的取数，并检查是否缺行、截断或出现异常值。",
                    ]
                else:
                    notes = ["读取指标目录中的标准定义，无需查询数值或执行 SQL。"]
            else:
                tone, outcome = "bad", "未取得结果"
                notes = [
                    errors[0]["message"]
                    if errors
                    else result.get("reason", "执行失败，未获得可用证据。")
                ]
        elif name == "compose_reply":
            if seen_names[name] > 1:
                title = "根据检查意见重写"
                notes = ["保留已取得的数据，只修复表达和事实呈现；这一步没有重新取数。"]
            else:
                notes = ["把已取得的事实组织成回答草稿，接下来还要检查才能交付。"]
            text = (patch.get("draft_reply") or {}).get("text", "未生成草稿。")
            outcome = "草稿生成"
        elif name == "validate_reply":
            validation = patch.get("validation") or {}
            if validation.get("passed"):
                notes = ["事实值、模拟数据标识、证据引用以及辅助语义检查通过，程序交付这份回答。"]
                title, outcome = "检查通过，交付回答", "通过"
            else:
                tone = "warn" if patch.get("status") != "failed" else "bad"
                title, outcome = "发现问题，要求修复", "未通过"
                notes = validation.get("issues") or ["检查未完成，程序没有交付未经校验的草稿。"]
                if patch.get("status") == "failed":
                    title = "停止并说明原因"
        if errors and patch.get("status") == "failed":
            tone, outcome = "bad", "执行失败"
            notes = [e["message"] for e in errors]
            if name == "compose_reply":
                title = "回答生成失败"
                text = "未生成可以交付的回答。"
        elif errors and not notes:
            notes = [e["message"] for e in errors]
        tool_retries = sum(e["kind"] == "tool_retry" and e.get("retry") is True for e in owned)
        model_retries = sum(e["kind"] == "model_error" and e.get("retry") is True for e in owned)
        if tool_retries:
            notes.append(f"本步骤遇到工具超时，程序实际重试了 {tool_retries} 次。")
        if model_retries:
            notes.append(f"本步骤发生 {model_retries} 次模型调用重试，失败记录也已保留。")
        before_fields, after_fields = state_fields(before), state_fields(after)
        changes = [
            {"field": key, "before": value, "after": after_fields[key]}
            for key, value in before_fields.items()
            if value != after_fields[key]
        ]
        calls = []
        for request in [e for e in owned if e["kind"] == "model_request"]:
            response = next(
                (
                    e
                    for e in owned
                    if e["kind"] == "model_response"
                    and e.get("parent_span_id") == request.get("parent_span_id")
                    and e["seq"] > request["seq"]
                ),
                None,
            )
            calls.append(
                {
                    "messages": request.get("messages", []),
                    "model": request.get("model"),
                    "response": response.get("content") if response else None,
                    "usage": response.get("usage", {}) if response else {},
                }
            )
        next_name = (
            route["destination"]
            if route
            else (starts[index + 1]["name"] if index + 1 < len(starts) else "__end__")
        )
        steps.append(
            {
                "title": title,
                "node": name,
                "number": index + 1,
                "notes": notes,
                "facts": facts,
                "text": text,
                "tone": tone,
                "outcome": outcome,
                "next": "本轮结束" if next_name == "__end__" else LABELS.get(next_name, next_name),
                "changes": changes,
                "model_calls": calls,
                "errors": errors,
                "elapsed_ms": end.get("elapsed_ms") if end else None,
                "event_range": [start["seq"], end["seq"] if end else start["seq"]],
                "raw_events": owned,
            }
        )
    responses = [e for e in events if e["kind"] == "model_response"]
    return {
        "thread_id": thread_id,
        "question": question,
        "status": final.get("status", "unknown"),
        "status_label": STATUS.get(final.get("status"), "未完成"),
        "answer": final.get("answer"),
        "pending_question": final.get("pending_question"),
        "steps": steps,
        "metrics": list(metrics.values()),
        "queries": list(queries.values()),
        "model_calls": sum(e["kind"] == "model_request" for e in events),
        "usage": {
            k: sum(e.get("usage", {}).get(k, 0) for e in responses)
            for k in ["input_tokens", "output_tokens"]
        },
        "events": events,
    }


def render_report(events, thread_id, directory):
    data = report_data(events, thread_id)
    # JSON 进入 script 标签时要额外转义 < 等字符，防止用户输入提前结束标签。
    payload = (
        json.dumps(data, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    template = Path(__file__).with_name("trace_view.html").read_text(encoding="utf-8")
    page = template.replace("__TRACE_DATA_JSON__", payload)
    target = directory / "trace.html"
    target.write_text(page, encoding="utf-8")
    return target
