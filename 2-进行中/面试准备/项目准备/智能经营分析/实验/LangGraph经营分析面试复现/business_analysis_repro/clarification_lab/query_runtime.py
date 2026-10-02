"""简单查数实验执行器。

复用正式 ChatStore/ContextMemory/ParallelModel，实验父图只保留理解、澄清、
本地查询三步。SQL只来自白名单模板；不读取标准答案，不调用线上指标平台。
本模块不依赖测试案例，数据由固定的模拟事实行生成，不根据问题返回预设答案。
"""

import hashlib
import json
import operator
import sqlite3
from pathlib import Path
from typing import Annotated, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from langsmith import tracing_context

from ..main_agent.runtime import locked
from ..playground.context_memory import ContextMemory, tokens
from ..playground.parallel_model import ParallelModel
from ..playground.server import save_json
from ..playground.trace import Trace
from .contract import LabResolution, validate_submission
from .experiment import experiment_instruction
from .knowledge import LabKnowledge
from .synthetic_queries import SPECS, TABLE_COLUMNS, seed_database

ENGINE = "simple-query-suite-v2"
EXPRESSIONS = {key: spec[1] for key, spec in SPECS.items()}


def query_local(path, task, trace):
    """参数化查询。指标/列/操作符均白名单，任务规则由上游契约完整校验。"""
    mid = task["metric_id"]
    if mid not in EXPRESSIONS or task["intent"] != "query":
        raise ValueError("本次适配器仅执行声明过的九个简单查数指标")
    table, expression = SPECS[mid]
    group = task["group_by"]
    if not (set(group) | set(task["filters"])) <= TABLE_COLUMNS[table]:
        raise ValueError("不支持该物理查询维度")
    clauses, params = ["day BETWEEN ? AND ?"], [task["period"]["start"], task["period"]["end"]]
    for dim, values in task["filters"].items():
        clauses.append(dim + " IN (" + ",".join("?" for _ in values) + ")")
        params.extend(values)
    for predicate in task["required_predicates"]:
        if table != "facts" or predicate["field_id"] not in {"valid", "fx_open"} or predicate["operator"] not in {"eq", "ne"}:
            raise ValueError("不支持的谓词")
        clauses.append(predicate["field_id"] + (" = ?" if predicate["operator"] == "eq" else " <> ?"))
        params.append(predicate["value"])
    sql = "SELECT " + (", ".join(group) + ", " if group else "") + expression
    sql += " AS value FROM " + table + " WHERE " + " AND ".join(clauses)
    if group:
        sql += " GROUP BY " + ", ".join(group) + " ORDER BY " + ", ".join(group)
    qid = hashlib.sha256(json.dumps(task, sort_keys=True).encode()).hexdigest()[:16]
    with trace.span("tool", "query_local_simulation", {"task": task, "sql": sql, "params": params}) as span:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
            db.row_factory = sqlite3.Row
            rows = [dict(r) for r in db.execute(sql, params)]
        result = {"query_id": qid, "metric_id": mid, "scope": task,
                  "rows": rows, "synthetic": True, "source": "local_sqlite_simulation"}
        span["result"] = result
        return result


class LabState(TypedDict):
    messages: Annotated[list[dict], operator.add]
    status: str
    pending_question: str | None
    answer: str
    task: dict | None
    result: dict | None
    inspection: dict


class BudgetExceeded(RuntimeError):
    pass


class LimitedTrace(Trace):
    """付费前检查整个隔离批次的请求数，包括重试与上下文摘要。"""
    def __init__(self, directory, thread_id, batch_root):
        super().__init__(directory, thread_id)
        self.batch_root = Path(batch_root)
        self.turn_calls = 0

    def event(self, kind, name, **data):
        if kind == "model_request":
            from ..conversation_lab.budget import check
            check(self.batch_root, data)
            config_file = self.batch_root / "batch.json"
            limits = json.loads(config_file.read_text())["limits"] if config_file.exists() else {
                "batch_requests": 30, "requests_per_turn": 6, "estimated_input_per_request": 18000}
            count = 0
            for file in self.batch_root.glob("conversations/*/tasks/*/trace.jsonl"):
                count += sum(json.loads(line)["kind"] == "model_request" for line in file.read_text().splitlines())
            if count >= limits["batch_requests"] or self.turn_calls >= limits["requests_per_turn"]:
                raise BudgetExceeded("达到本批次或本轮模型请求上限")
            if tokens({k: data[k] for k in ("messages", "tools") if k in data}) > limits["estimated_input_per_request"]:
                raise BudgetExceeded("请求本地估算超过18000输入Token，停止而不扩大实验")
            self.turn_calls += 1
        return super().event(kind, name, **data)


def make_executor(batch_root, model_factory=ParallelModel):
    """只接收运行配置，不接收用例ID、标准任务或将来的用户输入。"""
    batch_root = Path(batch_root)

    def execute(output_dir, thread_id, text, *, resume=False, context=(),
                context_cache_path=None, cancel=None, **_):
        directory = Path(output_dir) / thread_id
        directory.mkdir(parents=True, exist_ok=True)
        trace = LimitedTrace(directory, thread_id, batch_root)
        trace.cancellation = cancel
        if cancel:
            cancel.attach(trace)
        model = model_factory(trace, max_calls=40)  # 更严格的批次/轮次限额由Trace在请求前执行。
        memory = ContextMemory(model, trace, context_cache_path)
        database = batch_root / "synthetic.sqlite"
        seed_database(database)

        def understand(state):
            with trace.span("node", "understand_request", {"messages": state["messages"]}):
                packet = memory.prepare(context, state["messages"])
                payload = {"messages": state["messages"], "reference_date": "2026-09-01",
                           "timezone": "Asia/Shanghai", **packet}
                knowledge = LabKnowledge()
                start = len(trace.read())
                proposal = model.resolve(payload, tools=knowledge.tools(), knowledge_catalog=knowledge,
                    instruction=experiment_instruction(), resolution_schema=LabResolution,
                    topic_resolver=knowledge.business_context, require_submission=True,
                    submission_validator=lambda proposal: validate_submission(proposal, knowledge))
                events = trace.read()[start:]
                submissions = [e["inputs"] for e in events if e["kind"] == "span_start"
                               and e.get("category") == "tool" and e["name"] == "finish_resolution"]
                validation = validate_submission(proposal, knowledge)
                inspection = {"model_submissions": submissions, "resolver_result": proposal.model_dump(),
                    "validation": validation, "actual_input": payload,
                    "knowledge_observations": knowledge.observations}
                trace.event("experiment_inspection", "before_query", **inspection)
                base = {"inspection": inspection, "task": None, "result": None, "answer": "",
                        "pending_question": None}
                if proposal.outcome == "clarify":
                    return {**base, "status": "waiting_user", "pending_question": proposal.question}
                if not validation["accepted"]:
                    return {**base, "status": "failed", "answer": "未通过实验查询准入；详见Trace。"}
                jobs = []
                for i, task in enumerate(validation["normalized_tasks"]):
                    # 保留原任务全字段；只增加正式历史投影使用的绝对起止日期。
                    scope = {**task, "start_date": task["period"]["start"], "end_date": task["period"]["end"]}
                    jobs.append({"job_id": f"job-{i+1}", "name": knowledge.metrics[task["metric_id"]]["name"], "task": scope})
                return {**base, "status": "ready", "task": {"jobs": jobs}}

        def clarify(state):
            with trace.span("node", "clarify", {"question": state["pending_question"]}):
                reply = interrupt({"question": state["pending_question"]})
                return {"messages": [{"role": "ai", "content": state["pending_question"]},
                                     {"role": "human", "content": reply}], "pending_question": None}

        def query(state):
            with trace.span("node", "query", {"tasks": state["inspection"]["validation"]["normalized_tasks"]}):
                tasks = state["inspection"]["validation"]["normalized_tasks"]
                # 全部指标均能执行才开始，防止半个批次被误记为完成。
                if any(t["metric_id"] not in EXPRESSIONS or t["intent"] != "query" for t in tasks):
                    raise ValueError("超出本轮适配器能力")
                results = [query_local(database, task, trace) for task in tasks]
                # 模板如实输出实际查询结果；不额外花一次模型调用润色。
                answer = "本地模拟查询已完成：\n" + "\n".join(
                    job["name"] + "（" + result["scope"]["period"]["start"] + " 至 " + result["scope"]["period"]["end"] + "）：" + json.dumps(result["rows"], ensure_ascii=False)
                    for job, result in zip(state["task"]["jobs"], results))
                return {"status": "completed", "result": {"cards": [], "queries": results}, "answer": answer}

        with locked(directory), SqliteSaver.from_conn_string(str(directory / "checkpoints.sqlite")) as saver:
            graph = StateGraph(LabState)
            graph.add_node("understand", understand)
            graph.add_node("clarify", clarify)
            graph.add_node("query", query)
            graph.add_edge(START, "understand")
            graph.add_conditional_edges("understand", lambda s: s["status"],
                                        {"waiting_user": "clarify", "ready": "query", "failed": END})
            graph.add_edge("clarify", "understand")
            graph.add_edge("query", END)
            app = graph.compile(checkpointer=saver)
            config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 12}
            previous = app.get_state(config)
            if resume and not any(t.interrupts for t in previous.tasks):
                raise ValueError("没有可恢复的澄清")
            if not resume and previous.values:
                raise ValueError("不能覆盖已有任务")
            incoming = Command(resume=text) if resume else {"messages": [{"role": "human", "content": text}]}
            try:
                with tracing_context(enabled=False), trace.span("graph", ENGINE):
                    app.invoke(incoming, config)
                result = dict(app.get_state(config).values)
                result["engine_version"] = ENGINE
                save_json(directory / "state.json", result)
                trace.event("state_snapshot", "completed_or_waiting", state=result)
                return result, directory
            finally:
                trace.render()

    return execute
