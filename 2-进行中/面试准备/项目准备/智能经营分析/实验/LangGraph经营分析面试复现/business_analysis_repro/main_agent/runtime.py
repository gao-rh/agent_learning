"""应用执行入口：SQLite 持久化、恢复、文件锁与追溯产物。

Graph 负责业务节点与边；这个文件负责把它放进真实进程里运行。
一次 thread 对应一个任务，多轮澄清沿用它；新问题使用新的 thread。
"""

import fcntl
import hashlib
import importlib.metadata
import json
import re
from contextlib import contextmanager
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from langsmith import tracing_context

from .graph import build_graph
from .model import KimiModel
from .state import initial_state
from .trace import Trace


def manifest():
    """把执行代码指纹、依赖版本留下，便于判断 Trace 对应哪一版实现。"""
    root = Path(__file__).parent
    sources = (
        list(root.glob("*.py")) + list(root.glob("*.html")) + [root.parent / "calendar_tools.py"]
    )
    return {
        "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        "versions": {
            p: importlib.metadata.version(p)
            for p in [
                "langgraph",
                "langgraph-checkpoint-sqlite",
                "langchain-openai",
                "pydantic",
            ]
        },
    }


def thread_directory(output_dir, thread_id):
    # thread_id 是文件夹名，拒绝路径穿越；它不是用户自然语言问题。
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", thread_id):
        raise ValueError("thread_id 只能包含 1–80 位英文字母、数字、下划线或连字符。")
    return Path(output_dir).resolve() / thread_id


@contextmanager
def locked(directory):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("同一任务正在另一个进程执行，请等待它结束。") from exc
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def execute(
    *,
    output_dir,
    thread_id,
    question=None,
    reference_date=None,
    answer=None,
    model_factory=KimiModel,
    graph_options=None,
    max_calls=16,
):
    directory = thread_directory(output_dir, thread_id)
    with (
        locked(directory),
        SqliteSaver.from_conn_string(str(directory / "checkpoints.sqlite")) as saver,
    ):
        trace = Trace(directory, thread_id)
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 40}
        # 创建模型对象不发网络请求；没有密钥时在图运行前明确报错。
        model = model_factory(trace, max_calls=max_calls)
        graph = build_graph(model, trace, saver, **(graph_options or {}))
        previous = graph.get_state(config)
        if question is not None:
            if previous.values:
                raise ValueError(
                    "thread_id 已存在；补充信息请用 resume，新问题请用新的 thread_id。"
                )
            if not question.strip() or len(question) > 4000:
                raise ValueError("问题需要是非空文本，且不超过 4000 字符。")
            data = initial_state(question, reference_date)
        else:
            if not previous.values or not any(t.interrupts for t in previous.tasks):
                raise ValueError("该 thread 没有等待用户输入的中断，不能 resume。")
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError("resume 需要非空的用户补充文本。")
            # Command(resume=...) 才会给 interrupt 返回值，普通字典输入不能替代它。
            data = Command(resume=answer)
        current_manifest = manifest()
        trace.event(
            "execution_start",
            "main_agent",
            mode="start" if question is not None else "resume",
            manifest=current_manifest,
            model=getattr(model, "model_name", "test-double"),
            input={"question": question, "answer": answer, "reference_date": reference_date},
        )
        (directory / "graph.mmd").write_text(graph.get_graph().draw_mermaid(), encoding="utf-8")
        try:
            with tracing_context(enabled=False), trace.span("graph", "main_agent") as span:
                # values 是合并 reducer 后的真实 State；updates 是每个节点返回的增量。
                # 两种都记录，能看见“节点写了什么”和“图最终持有什么”。
                for mode, value in graph.stream(data, config, stream_mode=["updates", "values"]):
                    if mode == "values":
                        trace.event("state_snapshot", "merged_state", state=value)
                    else:
                        trace.event("graph_update", "node_update", update=value)
                snapshot = graph.get_state(config)
                span["status"] = snapshot.values.get("status")
                span["next"] = snapshot.next
                span["checkpoint_id"] = snapshot.config["configurable"]["checkpoint_id"]
                trace.event(
                    "checkpoint",
                    "persisted",
                    config=snapshot.config,
                    next=snapshot.next,
                    metadata=snapshot.metadata,
                    interrupts=[i.value for t in snapshot.tasks for i in t.interrupts],
                )
        finally:
            # 即使进程中遇到异常，也尽量留下最后可恢复的状态和报告。
            snapshot = graph.get_state(config)
            if snapshot.values:
                trace.event("state_snapshot", "final_persisted_state", state=snapshot.values)
                (directory / "state.json").write_text(
                    json.dumps(trace.clean(snapshot.values), ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            history = [
                {
                    "checkpoint_id": s.config["configurable"]["checkpoint_id"],
                    "next": s.next,
                    "metadata": s.metadata,
                    "state": s.values,
                }
                for s in graph.get_state_history(config)
            ]
            (directory / "checkpoints.json").write_text(
                json.dumps(trace.clean(history), ensure_ascii=False, indent=2), encoding="utf-8"
            )
            trace.render()
        return snapshot.values, directory
