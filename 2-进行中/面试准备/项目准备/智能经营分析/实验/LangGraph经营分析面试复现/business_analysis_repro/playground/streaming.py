"""SSE 是只读订阅，不发起模型任务。执行统一经过 ChatStore.send。

按 request_id 绑定一次输入，按 trace.seq 重连补读；同一个 LangGraph thread
澄清恢复会追加日志，因此还需要 stream_after_seq 避免重放上一轮草稿。
"""

import json
import time


def public_event(event):
    """只发送页面需要的事件，完整 State/模型提示词/工具参数留在 Trace。"""
    kind = event["kind"]
    if kind == "inbox_applied":
        return {"type": "inbox_applied", "decision": event["decision"]}
    if kind == "plan_revised":
        return {"type": "plan_revised"}
    if kind == "analysis_progress":
        return {"type": "analysis", "message": event.get("message", ""),
                "job_id": event.get("job_id"), "name": event.get("metric_name", ""),
                "hypothesis": event.get("hypothesis", "")}
    if kind == "plan":
        return {
            "type": "plan",
            "decomposition": event.get("decomposition", ""),
            "jobs": [
                {
                    "job_id": j["job_id"],
                    "name": j["name"],
                    "intent": j["task"]["intent"],
                    "status": "queued",
                }
                for j in event["jobs"]
            ],
        }
    if kind == "job_status":
        return {
            "type": "job",
            "job_id": event["job_id"],
            "name": event.get("metric_name", ""),
            "status": event["status"],
        }
    if kind == "result_card":
        return {"type": "card", "card": event["card"]}
    if kind in {"answer_start", "answer_delta", "answer_end", "answer_reset"}:
        return {"type": kind, **{k: event[k] for k in ("delta", "attempt", "reason", "phase", "has_tools") if k in event}}
    if kind == "span_start" and event.get("category") in {"node", "tool", "model"}:
        return {"type": "progress", "step": event["name"], "job_id": event.get("job_id")}
    return None


def frame(kind, payload, event_id=None):
    header = f"id: {event_id}\n" if event_id is not None else ""
    return (
        header + f"event: {kind}\ndata: " + json.dumps(payload, ensure_ascii=False) + "\n\n"
    ).encode()


def tail_events(path, offset):
    """只读新追加的完整行；写到一半的行留到下次，不吞掉断开的Unicode字符。"""
    if not path.exists():
        return [], offset
    events = []
    with path.open("rb") as handle:
        handle.seek(offset)
        while line := handle.readline():
            if not line.endswith(b"\n"):
                break
            events.append(json.loads(line))
            offset = handle.tell()
    return events, offset


def iter_sse(store, cid, request_id, after=0, *, poll_interval=0.05, idle_timeout=180):
    """实时日志→SSE。浏览器断线后此迭代停止，但另一个POST线程继续完成任务。

    心跳避免安静的检索阶段被当作断连。最多等待未出现/失去活动的任务3分钟；
    正常收到新事件会刷新计时。重连只是读日志，不重发用户问题、不新增费用。
    """
    yield b"retry: 1000\n\n"
    offset, floor, attached, last_activity = 0, after, None, time.monotonic()
    heartbeat = last_activity
    while True:
        conversation = store.get(cid)
        active = conversation.get("active_request_id") == request_id and conversation.get("active")
        finished = next(
            (
                m
                for m in reversed(conversation["messages"])
                if m.get("role") == "assistant" and m.get("request_id") == request_id
            ),
            None,
        )
        info = (
            {
                "thread_id": conversation["active"],
                "stream_after_seq": conversation.get("active_after_seq", 0),
            }
            if active
            else finished
        )
        if info:
            if attached is None:
                attached = info["thread_id"]
                floor = max(after, info.get("stream_after_seq", 0))
                yield frame("started", {"thread_id": attached, "trace": f"/trace/{cid}/{attached}"})
            path = store.directory(cid) / "tasks" / attached / "trace.jsonl"
            events, offset = tail_events(path, offset)
            for event in events:
                if event["seq"] <= floor:
                    continue
                floor = event["seq"]
                last_activity = time.monotonic()
                payload = public_event(event)
                if hasattr(store, "control") and store.control.cancelled(cid, request_id):
                    # 公共输出从这里统一过滤；内部 Trace 仍保留返回结果与 usage。
                    payload = None
                if payload:
                    yield frame("update", payload, f"{request_id}:{floor}")
            if finished:
                # 完整权威结果替换草稿；不可把客户端看到的中间文本当成最终回答。
                yield frame("done", conversation, f"{request_id}:{floor}")
                return
        now = time.monotonic()
        if now - last_activity > idle_timeout:
            yield frame(
                "stream_idle", {"message": "订阅暂未收到新进度，可刷新恢复；不会重复发送问题。"}
            )
            return
        if now - heartbeat >= 10:
            yield b": heartbeat\n\n"
            heartbeat = now
        time.sleep(poll_interval)
