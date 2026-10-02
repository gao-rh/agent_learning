"""复用v5模型/工具循环，止于澄清提交；不构建业务父图，也没有取数调用。

保持公开输入和人工标准分离。真实模型由显式run命令创建；预览不会加载密钥。
"""

import hashlib
import importlib.metadata
import json
from pathlib import Path

from ..playground.parallel_model import INSTRUCTION
from .contract import LabResolution, validate_submission
from .knowledge import FIXTURES, LabKnowledge

PROFILE_VERSION = "clarification-preparation-v1"


def experiment_instruction():
    # 不把本版本包装成原封不动的v5基线：仅替换不适用于语义实验的执行声明。
    base = INSTRUCTION.replace(
        "不支持自选双期间、同比、真实因果、Shapley或任意跨指标依赖DAG。",
        "本实验只研究任务语义；可记录用户明确的比较基期，不承诺执行分析。")
    return base + """
\n【澄清实验契约，覆盖涉及下游执行能力的旧说明】
只理解问题、检索本次模拟目录并提交语义任务，不执行取数、认证、分析或报告。
所有指标/维度/枚举均以本次工具返回为准，不使用旧试玩的ID或口径。
分析比较需要用comparison_period显式记录基期。未定义的比较术语应询问，不自行猜测。
定义中的mandatory_predicates必须逐项写入对应任务的required_predicates；不要要求用户确认系统已明确的规则。
不能为了填字段修改用户需求。过滤按每个request绑定；明确无需分组时group_by为空。
业务别名没有可用定义时先检索，有实质歧义再问；用户的本次选择不自动变成全局知识。
business_topic_hint是程序按本轮用户原话检索的实际业务知识；先检查适用范围、版本，再决定使用。
用户提出的业务范围词不能仅按常识映射为某维度。预检索没有对应定义时，先按该短语检索；仍无定义就问用户具体筛选范围，不擅自增加分组。
澄清未定义的范围词时保留用户原词，问它对应哪些对象或筛选边界；不能先把它改述为另一个展示操作，也不能撤销已确认的整体汇总。
已找到的定义要求筛选还是分组必须逐项落实；采用时knowledge_refs包含实际来源。不因为检索完成就认定业务含义已经正确。
用missing_items记录待解决条件、原因和由谁提供信息；knowledge_refs记录本轮实际收到并采用的业务知识。
没有业务数值，不得宣称已查询或分析出结果。可以提交intent=analysis，但它只表示比较需求，执行始终关闭。
"""


def payload_for(case, turns=()):
    # 只挑模型可见的字段：不包含案例标题、知识配置名称、固定回复或判分标准。
    return {"messages": [{"role": "human", "content": case["question"]}, *turns],
            "reference_date": "2026-09-01", "timezone": "Asia/Shanghai",
            "conversation_context": case["history"],
            "conversation_memory": {"summary": "", "status": "not_needed"}}


def manifest():
    root = Path(__file__).resolve().parents[1]
    paths = list(Path(__file__).parent.glob("*.py")) + list(FIXTURES.glob("*.json"))
    paths += [root / "playground" / n for n in
              ("parallel_model.py", "parallel_state.py", "catalog.py", "agent.py")]
    paths += [root / "main_agent" / "model.py", root / "calendar_tools.py", root / "experiment_support.py"]
    return {"profile_version": PROFILE_VERSION,
            "instruction_sha256": hashlib.sha256(experiment_instruction().encode()).hexdigest(),
            "versions": {name: importlib.metadata.version(name) for name in
                         ("langgraph", "langchain-core", "langchain-openai", "pydantic")},
            "sha256": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in sorted(paths)}}


def execute_turn(model, case, turns=()):
    """保留模型原始提交、resolve处理结果、契约校验三层，不能把程序澄清算作模型判断。"""
    knowledge = LabKnowledge(case["knowledge_profile"])
    payload = payload_for(case, turns)
    event_start = len(model.trace.read())
    model.trace.event("experiment_input", "clarification_only", payload=payload,
                      profile=PROFILE_VERSION, input_manifest=manifest())
    proposal = model.resolve(payload, tools=knowledge.tools(), knowledge_catalog=knowledge,
        instruction=experiment_instruction(), resolution_schema=LabResolution,
        topic_resolver=knowledge.business_context, require_submission=True,
        submission_validator=lambda proposal: validate_submission(proposal, knowledge))
    # 这里只调用公开契约检查；绝不根据gold修正模型的指标/条件。
    resolved = proposal.model_dump()
    model.trace.event("experiment_proposal", "resolver_result", proposal=resolved)
    turn_events = model.trace.read()[event_start:]
    submissions = [{"span_id": e["span_id"], "arguments": e.get("inputs")}
                   for e in turn_events if e["kind"] == "span_start"
                   and e.get("category") == "tool" and e["name"] == "finish_resolution"]
    validation = validate_submission(proposal, knowledge)
    allowed = set(knowledge.tools()) | {"finish_resolution"}
    attempted = [e["name"] for e in turn_events
                 if e["kind"] == "span_start" and e.get("category") == "tool"
                 and e["name"] not in allowed]
    if attempted:
        validation["accepted"] = False
        validation["errors"].append("越界工具调用尝试：" + ",".join(attempted))
    model.trace.event("experiment_boundary", "stop_before_execution", validation=validation)
    return {"model_submissions": submissions, "resolver_result": resolved, "validation": validation,
            "knowledge_observations": knowledge.observations,
            "boundary_violations": attempted, "actual_input": payload}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
