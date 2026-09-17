"""Interactive CLI for the E2 LangGraph clarification workflow."""

import argparse
import sqlite3
from pathlib import Path
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from business_analysis_repro.clarification_graph import (
    build_clarification_graph,
    initial_state,
)

DEFAULT_QUESTION = "我想看看B准今天的保费情况。"
DEFAULT_REFERENCE_DATE = "2026-08-28"
DEFAULT_DB = Path(__file__).resolve().parents[1] / "clarification_checkpoints.sqlite3"


def _interrupt_payload(result: dict) -> dict | None:
    interrupts = result.get("__interrupt__", ())
    return interrupts[0].value if interrupts else None


def run_interactive(
    question: str,
    *,
    reference_date: str,
    thread_id: str,
    checkpoint_db: Path,
) -> dict:
    connection = sqlite3.connect(checkpoint_db, check_same_thread=False)
    try:
        checkpointer = SqliteSaver(connection)
        checkpointer.setup()
        graph = build_clarification_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        graph_input: dict | Command = initial_state(question, reference_date=reference_date)

        print("=== E2 LangGraph 指标澄清实验 ===")
        print(f"thread_id: {thread_id}")
        print(f"checkpoint: {checkpoint_db}")
        print(f"用户: {question}")

        while True:
            result = graph.invoke(graph_input, config=config)
            payload = _interrupt_payload(result)
            if payload is None:
                print(f"\n最终状态: {result['status']}")
                print(f"澄清轮数: {result['clarification_rounds']}")
                print(f"工具执行次数: {result['tool_executions']}")
                print(f"AI: {result['final_answer']}")
                print(f"Token usage: {result['token_usage']}")
                return result

            print(f"\nAI（第 {payload['round']} 轮澄清）: {payload['question']}")
            answer = input("你: ").strip()
            graph_input = Command(resume=answer)
    finally:
        connection.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行E2 LangGraph多轮指标澄清实验")
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument("--reference-date", default=DEFAULT_REFERENCE_DATE)
    parser.add_argument("--thread-id", default=f"e2-{uuid4()}")
    parser.add_argument("--checkpoint-db", type=Path, default=DEFAULT_DB)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_interactive(
        args.question,
        reference_date=args.reference_date,
        thread_id=args.thread_id,
        checkpoint_db=args.checkpoint_db,
    )


if __name__ == "__main__":
    main()
