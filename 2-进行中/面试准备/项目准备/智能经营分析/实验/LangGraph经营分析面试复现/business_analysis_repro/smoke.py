"""Verify that the project environment can compile and run a minimal LangGraph graph."""

from importlib.metadata import version
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class SmokeState(TypedDict):
    value: int
    events: list[str]


def verify_environment(state: SmokeState) -> SmokeState:
    """Produce one deterministic state update without calling a model or external service."""
    return {
        "value": state["value"] + 1,
        "events": [*state["events"], "environment_ready"],
    }


def build_smoke_graph():
    builder = StateGraph(SmokeState)
    builder.add_node("verify_environment", verify_environment)
    builder.add_edge(START, "verify_environment")
    builder.add_edge("verify_environment", END)
    return builder.compile()


def run_smoke() -> SmokeState:
    graph = build_smoke_graph()
    return graph.invoke({"value": 0, "events": []})


def main() -> None:
    result = run_smoke()
    if result != {"value": 1, "events": ["environment_ready"]}:
        raise RuntimeError(f"Unexpected smoke result: {result}")

    packages = ("langchain", "langgraph", "langsmith", "langgraph-checkpoint-sqlite")
    print("environment: ready")
    for package in packages:
        print(f"{package}: {version(package)}")
    print(f"graph result: {result}")


if __name__ == "__main__":
    main()
