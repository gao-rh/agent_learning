# 阅读快照：2026-09-07；保留完整原文件，仅增加讲解注释。
# 原文件：/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/runtime.py
# 原文件 SHA-256：d6a291d13643359c2ef1e284ab459a9a51f9609c6c30ba00228faec1bc2e5503
# 本副本用于阅读，不作为可独立运行的脚本；运行请使用原包的 python -m 入口。
# 搜索“剩余阅读”可定位还没按执行顺序讲完的部分；下文行号均指原文件。
# 配套摘要：../代码阅读摘要.md。注释是 Codex 的源码解读，不代表已验收你的理解。

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


# ── 执行版本记录｜原文件 25–42 行 ──
# 给源码计算摘要并记录依赖版本，日后判断旧 Trace 对应什么代码。不是业务证据 ID。
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


# ── 按任务找到目录｜原文件 45–49 行 ──
# 当前实现是一任务一目录；合法 thread_id 只能包含有限字符，避免被当成任意路径。
def thread_directory(output_dir, thread_id):
    # thread_id 是文件夹名，拒绝路径穿越；它不是用户自然语言问题。
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", thread_id):
        raise ValueError("thread_id 只能包含 1–80 位英文字母、数字、下划线或连字符。")
    return Path(output_dir).resolve() / thread_id


# ── 同一任务的进程锁｜原文件 52–63 行 ──
# with 进入时加锁，离开时解锁。LOCK_NB 表示争抢失败立即报错。
# 这只是本机同一任务的互斥，不是多用户调度器，也不创建 Python 线程。
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


# ── 应用执行器｜原文件 66–121 行 ──
# 输入：新问题或澄清补充、任务 ID、输出目录。输出：State 和目录。
# 顺序：打开 checkpoint → 创建 Trace/模型/图 → 建立新输入或恢复命令 → stream 驱动图。
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
    # ── 打开恢复存储｜原文件 78–87 行 ──
    # SqliteSaver 使用任务目录里的 checkpoints.sqlite；它负责 LangGraph 的持久化协议。
    # 图通过闭包使用 model 和 trace，State 内不保存这些对象。
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
        # ── 新任务和恢复的分界｜原文件 88–102 行 ──
        # 新问题不能复用已有任务 ID；resume 只接受真正停在 interrupt 的存档。
        # 因此当前代码尚不支持“回答完以后继续追问”这种通用聊天会话。
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
            # ── 剩余阅读 4：向中断点交回补充 ──
            # Command(resume=answer) 会让 clarify 内的 interrupt() 在恢复执行时返回 answer。
            # 普通的 {"answer": ...} 状态更新不能替代这个恢复命令。
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
        # ── 开始实际调度｜原文件 113–133 行 ──
        # build_graph 只组装图；迭代 graph.stream 时才开始调用节点。
        # updates 记录每步返回的 patch；values 记录合并后图实际持有的 State。
        try:
            with tracing_context(enabled=False), trace.span("graph", "main_agent") as span:
                # values 是合并 reducer 后的真实 State；updates 是每个节点返回的增量。
                # 两种都记录，能看见“节点写了什么”和“图最终持有什么”。
                for mode, value in graph.stream(data, config, stream_mode=["updates", "values"]):
                    if mode == "values":
                        trace.event("state_snapshot", "merged_state", state=value)
                    else:
                        trace.event("graph_update", "node_update", update=value)
                # ── 剩余阅读 3：取回最终或暂停快照｜原文件 122–133 行 ──
                # stream 结束不一定代表业务完成：也可能正在等用户。查看 status、next 和 interrupts。
                # get_state 从 checkpoint 系统取快照，不是请求模型生成一份总结。
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
        # ── 导出便于人读的文件｜原文件 134–155 行 ──
        # finally 在正常结束、暂停和可处理异常时都会执行，尽量保留最后存档。
        # state.json 是状态导出；checkpoints.json 是历史导出；trace.html 是事件回放。
        # 真正恢复任务读取 SQLite。不能通过改 state.json 来控制下一次恢复。
        # 强制杀进程/断电等不保证执行 finally；这里不是对所有故障的保证。
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
        # ── 回到命令行入口｜原文件 156 行 ──
        # 返回后看 __main__.py 第 53–68 行：打印结果、返回退出码；with 同时负责关闭资源。
        return snapshot.values, directory
