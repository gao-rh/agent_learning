# 阅读快照：2026-09-07；保留完整原文件，仅增加讲解注释。
# 原文件：/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/trace.py
# 原文件 SHA-256：e6e1201ff6cca06ee93d0a6c74dc77cd9578fd556965d737e58fff1650ced28e
# 本副本用于阅读，不作为可独立运行的脚本；运行请使用原包的 python -m 入口。
# 搜索“剩余阅读”可定位还没按执行顺序讲完的部分；下文行号均指原文件。
# 配套摘要：../代码阅读摘要.md。注释是 Codex 的源码解读，不代表已验收你的理解。

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

# ── 关联父子调用｜原文件 20 行 ──
# ContextVar 保存当前 span ID，嵌套调用自然形成 graph → node → model/tool。
_parent = contextvars.ContextVar("main_agent_trace_parent", default=None)


# ── 可序列化表示｜原文件 23–32 行 ──
# 将消息、Pydantic 对象等转成 JSON 能表达的值；这是日志转换，不是 checkpoint 序列化器。
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


# ── 一次进程与一个任务｜原文件 35–43 行 ──
# thread_id 关联同任务恢复前后；run_id 每次执行器运行新建。seq 沿已有日志继续。
class Trace:
    def __init__(self, directory: Path, thread_id: str, secrets: tuple[str, ...] = ()):
        directory.mkdir(parents=True, exist_ok=True)
        self.directory = directory
        self.path = directory / "trace.jsonl"
        self.thread_id = thread_id
        self.run_id = str(uuid.uuid4())  # 每次进程调用不同，恢复仍属于同一个 thread
        self.secrets = tuple(s for s in secrets if s)
        self.seq = len(self.read())

    # ── 日志清理｜原文件 45–61 行 ──
    # 写事件前递归清理认证字段及已知密钥。这不是把整段日志发给模型的预处理。
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

    # ── 读取已有事件｜原文件 63–66 行 ──
    # JSONL 的每一行是一份完整 JSON 对象；文件整体不是一个 JSON 数组。
    def read(self):
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line]

    # ── 追加一条事实事件｜原文件 68–85 行 ──
    # 记录时间、任务、进程运行、事件类型和父 span；追加到 trace.jsonl 并 flush/fsync。
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

    # ── 一段调用的开始与结束｜原文件 87–117 行 ──
    # with trace.span(...) as span 在进入时写开始事件，退出时写结果、状态和耗时。
    # 调用方把 result/state_update 等写入 span 字典；finally 将它们落盘。
    # 中断是 interrupted，普通调用异常是 error；这与业务 State.status 的四种取值不同。
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
            status = "error"
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

    # ── 生成给人看的回放｜原文件 119–123 行 ──
    # trace_report.py 将已有事件归并成步骤，trace_view.html 展示；不会再调用模型写解说。
    # 本轮不展开 HTML/CSS，可以直接打开已保存的 trace.html 对照各节点。
    def render(self):
        """从现有原始事件生成面向阅读的节点回放，不调用模型。"""
        from .trace_report import render_report

        return render_report(self.read(), self.thread_id, self.directory)
