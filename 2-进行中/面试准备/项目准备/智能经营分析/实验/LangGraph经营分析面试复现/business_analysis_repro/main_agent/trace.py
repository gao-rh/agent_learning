"""本地全链路事件日志 + 无需服务的 HTML 报告。

trace.jsonl 是事实源：每行立即追加并落盘，异常前的事件也能保留。
span_id / parent_span_id 串起 graph → node → model/tool；thread_id 串起恢复前后。
报告只是这些事件的另一种呈现。它不等于 checkpoint，也不承诺记录模型内部思考。
"""

import contextvars
import json
import os
import re
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from langgraph.errors import GraphInterrupt

_parent = contextvars.ContextVar("main_agent_trace_parent", default=None)


def jsonable(value):
    if hasattr(value, "model_dump"):
        return jsonable(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


class Trace:
    def __init__(self, directory: Path, thread_id: str, secrets: tuple[str, ...] = ()):
        directory.mkdir(parents=True, exist_ok=True)
        self.directory = directory
        self.path = directory / "trace.jsonl"
        self.thread_id = thread_id
        self.run_id = str(uuid.uuid4())  # 每次进程调用不同，恢复仍属于同一个 thread
        self.secrets = tuple(s for s in secrets if s)
        self.seq = len(self.read())

    def clean(self, value):
        """不记录认证头；对错误文本以及误传的 key 再做防御性清理。"""
        value = jsonable(value)
        if isinstance(value, dict):
            return {
                k: "[REDACTED]"
                if re.search(r"api.?key|authorization|secret|password", k, re.IGNORECASE)
                else self.clean(v)
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [self.clean(v) for v in value]
        if isinstance(value, str):
            for secret in self.secrets:
                value = value.replace(secret, "[REDACTED]")
            return re.sub(r"\bsk-[A-Za-z0-9_-]{12,}", "[REDACTED]", value)
        return value

    def read(self):
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line]

    def check_cancel(self):
        token = getattr(self, "cancellation", None)
        if token:
            token.check()

    def event(self, kind: str, name: str, **data):
        self.seq += 1
        event = self.clean(
            {
                "seq": self.seq,
                "time": datetime.now(UTC).isoformat(),
                "thread_id": self.thread_id,
                "run_id": self.run_id,
                "kind": kind,
                "name": name,
                "parent_span_id": _parent.get(),
                **data,
            }
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    @contextmanager
    def span(self, kind: str, name: str, inputs=None):
        span_id = uuid.uuid4().hex
        parent_id = _parent.get()
        self.event("span_start", name, span_id=span_id, category=kind, inputs=inputs)
        token = _parent.set(span_id)
        started = time.perf_counter()
        output = {}
        status = "ok"
        try:
            yield output
        except GraphInterrupt:
            # interrupt 是 LangGraph 的正常控制流，不能吞掉或当成工具失败。
            status = "interrupted"
            raise
        except BaseException as exc:
            status = ({"RunCancelled": "cancelled", "ReplanRequested": "superseded",
                       "RefreshReply": "superseded"}.get(type(exc).__name__, "error"))
            output["error"] = {"type": type(exc).__name__, "message": str(exc)}
            raise
        finally:
            _parent.reset(token)
            self.event(
                "span_end",
                name,
                span_id=span_id,
                category=kind,
                parent_span_id=parent_id,
                status=status,
                elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
                output=output,
            )

    def render(self):
        """从现有原始事件生成面向阅读的节点回放，不调用模型。"""
        from .trace_report import render_report

        return render_report(self.read(), self.thread_id, self.directory)
