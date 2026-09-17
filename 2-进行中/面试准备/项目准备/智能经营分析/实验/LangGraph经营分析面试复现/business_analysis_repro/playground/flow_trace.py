"""Trace 的只读路线投影，不执行图、工具或模型，也不改写旧日志。

parent_span_id 表示真实调用归属；seq 表示事件先后。一次澄清恢复有新的
run_id，分开展示，不能把等待用户的几小时算作某个节点的运行耗时。
"""

from datetime import datetime

from .parallel_trace import LABELS

PURPOSE = {
    "prepare_context": "按预算保留近期原文、滚动摘要与精确业务条件；不会删除原始记录。点击可看压缩前后估算量。",
    "compress_context": "模型只压缩旧问答；不回答业务问题，不修改精确指标、日期或筛选条件。调用计入本轮 Token。",
    "handle_inbox": "主 Agent 在调用边界接收用户插入消息，决定回复、吸收补充、调整查询范围或停止；不会默认取消任务。",
    "parallel-v4": "主 Agent 的一次图执行。下面包含实际节点及模型、工具调用，澄清恢复会另列一轮。",
    "analysis-v5": "主 Agent 的一次图执行；分析分支可读取 Skill、基于证据做模型决策与实际补查。",
    "load_analysis_skill": "读取本地专题方法和业务知识，把适用步骤与边界提供给分析模型。",
    "analysis_followup": "模型根据已有比较证据选择补查范围；代码校验后，分别查询本期与前期。",
    "understand_request": "主 Agent 理解问题，检索指标与口径，提交计划；代码检查日期、维度和枚举。",
    "metric_worker": "父图分发的一个指标任务。它只处理自己的指标和查询范围。",
    "analysis_agent": "分析 Agent 的 Python 函数：内部查询本期和前期，对齐分组并计算变化。这里没有独立的模型推理。",
    "query_agent": "取数 Agent 的 Python 函数：按精确指标和范围，从模拟平台或参数化 SQL 读取数据。",
    "analysis.query_agent": "分析 Agent 内部的一次取数调用；只查这个期间，再把结果返回给分析函数。",
    "gather_results": "等待所有并行分支结束，按任务 ID 收集成功结果和失败项。",
    "compose_reply": "把汇总后的证据交给 Kimi，生成面向用户的文字摘要；明细表由程序保留。",
    "validate_reply": "复核摘要与证据。通过后交付，未通过可有限重写；无法生成可靠摘要时保留计算表格。",
    "clarify": "暂停图并等待用户补充；补充后恢复同一个任务。",
}


def millis(value, origin):
    return round((datetime.fromisoformat(value) - origin).total_seconds() * 1000, 2)


def task_input(event):
    inputs = event.get("inputs") or {}
    if not isinstance(inputs, dict):
        return {}
    return inputs.get("task") or inputs


def result_brief(end):
    """只提取已记录的业务事实；正文、完整状态和模型消息按需读详情接口。"""
    output = end.get("output") or {}
    if not isinstance(output, dict):
        return ""
    outcome = output.get("outcome") or {}
    update = output.get("state_update") or {}
    result = output.get("result") or outcome.get("result") or update.get("result") or {}
    if not isinstance(result, dict):
        return ""
    if "tokens_before" in result and "tokens_after" in result:
        return (f"历史约 {result['tokens_before']:,} → {result['tokens_after']:,} Tokens；"
                f"保留 {result['recent_turns']} 轮原文，历史处理方式：{result['mode']}。")
    if outcome.get("error") or output.get("error"):
        return "本次调用有异常，点击查看原因。"
    facts = result.get("facts") or {}
    if facts:
        pieces = [f"{k}：{facts[k]}" for k in ["结果", "前期结果", "变动"] if k in facts]
        if isinstance(result.get("groups"), list):
            pieces.append(f"保留 {len(result['groups'])} 行分组")
        return "；".join(pieces)
    if "cards" in result:
        return f"收集 {len(result['cards'])} 个指标结果，包含失败项（如有）。"
    if update.get("pending_question"):
        return update["pending_question"]
    if update.get("jobs"):
        return f"计划包含 {len(update['jobs'])} 个独立指标任务。"
    if update.get("answer"):
        return "已形成可交付回复；完整正文见对话或日志。"
    if update.get("draft_reply"):
        return "摘要草稿生成完毕，接下来进入复核。"
    if (update.get("validation") or {}).get("passed") is False:
        return "摘要未通过复核，沿父图返回摘要节点进行有限重写。"
    return ""


def flow_payload(events, cid, tid, active=False):
    if not events:
        raise FileNotFoundError("暂无执行事件")
    execution_events = [e for e in events if e["kind"] == "execution_start"]
    # 兼容旧日志未记录execution_start的情况，仍按真实run_id分段。
    run_ids = list(dict.fromkeys(e["run_id"] for e in events))
    runs = []
    for rid in run_ids:
        log = [e for e in events if e["run_id"] == rid]
        origin = datetime.fromisoformat(log[0]["time"])
        adaptive = any(e["kind"] == "execution_start" and e["name"] == "analysis-v5" for e in log)
        starts = {e["span_id"]: e for e in log if e["kind"] == "span_start"}
        ends = {e["span_id"]: e for e in log if e["kind"] == "span_end"}
        nodes = []
        for sid, start in starts.items():
            end = ends.get(sid, {})
            status = end.get("status", "running")
            output = end.get("output") or {}
            if isinstance(output, dict):
                outcome = (output.get("outcome") or {}).get("status")
                if outcome == "failed":
                    status = "failed"
                elif outcome == "needs_clarification":
                    status = "interrupted"
                validation = (output.get("state_update") or {}).get("validation") or {}
                if validation.get("passed") is False:
                    status = "review_failed"
            inputs = task_input(start)
            label = LABELS.get(start["name"], start["name"])
            if start["name"] == "analysis_agent":
                label = "分析 Agent"
            elif start["name"] == "query_agent":
                label = "取数 Agent"
            elif start["name"] == "analysis.query_agent":
                parent = task_input(starts.get(start.get("parent_span_id"), {}))
                same = all(inputs.get(k) == parent.get(k) for k in ["start_date", "end_date"])
                label = "取数 Agent · 本期" if same else "取数 Agent · 对比期"
            elif start["name"] == "metric_worker":
                label = "指标分支"
            nodes.append(
                {
                    "id": sid,
                    "name": start["name"],
                    "label": label,
                    "kind": start["category"],
                    "parent": start.get("parent_span_id"),
                    "job_id": start.get("job_id"),
                    "metric_name": start.get("metric_name"),
                    "intent": inputs.get("intent"),
                    "start_seq": start["seq"],
                    "end_seq": end.get("seq"),
                    "start_ms": millis(start["time"], origin),
                    "end_ms": millis(end["time"], origin) if end else None,
                    "elapsed_ms": end.get("elapsed_ms"),
                    "status": status,
                    "period": " ～ ".join(
                        str(inputs[k]) for k in ["start_date", "end_date"] if inputs.get(k)
                    ),
                    "purpose": ("简易分析 Agent：先读取 Skill 和两期证据，再由模型选择补查或结束；代码执行合法查询。"
                                if adaptive and start["name"] == "analysis_agent" else PURPOSE.get(
                        start["name"],
                        "模型调用：实际上下文与返回见详情。"
                        if start["category"] == "model"
                        else "工具调用：实际参数与结果见详情。",
                    )),
                    "result_brief": result_brief(end),
                }
            )
        roots = [n for n in nodes if n["kind"] == "graph"]
        root_ids = {n["id"] for n in roots}
        top = [n for n in nodes if (n["kind"] == "node" and n["parent"] in root_ids)
               or n["kind"] == "control"]
        # 连续的metric_worker合并成并行区；前后节点仍是日志中每次真实调用。
        # 一次摘要重写因此会呈现 compose→validate→compose→validate，不折叠丢失。
        phases = []
        for n in top:
            if n["name"] == "metric_worker" and phases and phases[-1]["kind"] == "parallel":
                phases[-1]["ids"].append(n["id"])
            else:
                phases.append(
                    {
                        "kind": "parallel" if n["name"] == "metric_worker" else "node",
                        "ids": [n["id"]],
                    }
                )
        if not phases:
            phases = [
                {"kind": "node", "ids": [n["id"]]} for n in nodes if n["parent"] not in starts
            ]
        start_event = next((e for e in execution_events if e["run_id"] == rid), {})
        latest_state = next(
            (e["state"] for e in reversed(log) if e["kind"] == "state_snapshot"), {}
        )
        graph_end = next((ends[n["id"]] for n in reversed(roots) if n["id"] in ends), {})
        status = latest_state.get("status") or (
            "completed" if graph_end.get("status") == "ok" else graph_end.get("status", "running")
        )
        if graph_end.get("status") == "error":
            status = "failed"
        # 日志没有结束且服务端已不再执行，应显示“记录中断”，不能一直冒充正在运行。
        if not graph_end and not (active and rid == run_ids[-1]):
            status = "incomplete"
        steps = [
            {
                "seq": e["seq"],
                "id": e["span_id"],
                "kind": e["kind"],
                "ms": millis(e["time"], origin),
            }
            for e in log
            if e["kind"] in {"span_start", "span_end"}
        ]
        runs.append(
            {
                "id": rid,
                "question": (start_event.get("input") or {}).get("text", ""),
                "resume": (start_event.get("input") or {}).get("resume", False),
                "start_time": log[0]["time"],
                "status": status,
                "active": active and rid == run_ids[-1],
                "duration_ms": millis(log[-1]["time"], origin),
                "last_seq": log[-1]["seq"],
                "nodes": nodes,
                "phases": phases,
                "steps": steps,
                "stop_events": [
                    {"kind": e["kind"], "ms": millis(e["time"], origin),
                     "status": e.get("status"), "query_id": e.get("query_id")}
                    for e in log if e["kind"] in {
                        "cancel_requested", "query_cancel_result", "execution_cancelled"}
                ],
                "inbox_events": [{"ms": millis(e["time"], origin),
                                  "texts": [r["text"] for r in e["messages"]],
                                  "decision": e["decision"]}
                                 for e in log if e["kind"] == "inbox_applied"],
                "stats": {
                    "analysis": sum(n["name"] == "analysis_agent" for n in nodes),
                    "queries": sum(
                        n["name"] in {"query_agent", "analysis.query_agent"} for n in nodes
                    ),
                    "models": sum(e["kind"] == "model_request" for e in log),
                    "tokens": sum(
                        e.get("usage", {}).get("total_tokens", 0)
                        for e in log
                        if e["kind"] == "model_response"
                    ),
                    "branches": sum(n["name"] == "metric_worker" for n in nodes),
                },
            }
        )
    return {"conversation_id": cid, "thread_id": tid, "revision": events[-1]["seq"], "runs": runs}


def node_payload(events, span_id, cutoff=None):
    """详情按回放游标过滤，不能在“刚进入节点”时展示未来才得到的输出。"""
    log = [e for e in events if cutoff is None or e["seq"] <= cutoff]
    start = next((e for e in log if e["kind"] == "span_start" and e["span_id"] == span_id), None)
    if start is None:
        raise FileNotFoundError("该时刻尚未进入此节点")
    end = next((e for e in log if e["kind"] == "span_end" and e["span_id"] == span_id), None)
    attached = [
        e
        for e in log
        if e.get("parent_span_id") == span_id
        and e["kind"]
        not in {"span_start", "span_end", "state_snapshot", "graph_update", "answer_delta"}
    ]
    chunks = [e for e in log if e.get("parent_span_id") == span_id and e["kind"] == "answer_delta"]
    return {
        "input": start.get("inputs"),
        "output": end.get("output") if end else None,
        "finished": end is not None,
        "events": attached,
        "stream_text": "".join(e["delta"] for e in chunks),
        "result_brief": result_brief(end or {}),
    }
