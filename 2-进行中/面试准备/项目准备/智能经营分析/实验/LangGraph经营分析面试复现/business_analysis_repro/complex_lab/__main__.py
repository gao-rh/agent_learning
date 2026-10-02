import argparse
import json
from pathlib import Path

from .runtime import FIXTURES, prepare, read, run_turn


def main():
    p = argparse.ArgumentParser(description="复杂语义实验；运行须显式--live，每次只进行一轮。")
    commands = p.add_subparsers(dest="command", required=True)
    q = commands.add_parser("prepare")
    q.add_argument("directory", type=Path)
    q.add_argument("--cases", nargs="+")
    q.add_argument("--guidance-file", type=Path)
    q = commands.add_parser("step")
    q.add_argument("directory", type=Path)
    q.add_argument("case")
    q.add_argument("--reply")
    q.add_argument("--question-reviewed", action="store_true")
    q.add_argument("--live", action="store_true")
    a = p.parse_args()
    if a.command == "prepare":
        value = prepare(
            a.directory, a.cases, a.guidance_file.read_text() if a.guidance_file else ""
        )
    else:
        if not a.live:
            p.error("真实调用必须显式--live")
        case = next(c for c in read(FIXTURES / "cases.json")["cases"] if c["id"] == a.case)
        if case["planned_turns"] > 1 or read(a.directory / "batch.json").get("simulation"):
            p.error("新的多轮测试使用 python -m business_analysis_repro.conversation_lab run <目录> --case <案例> --live")
        value = run_turn(a.directory, a.case, a.reply, a.question_reviewed)
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
