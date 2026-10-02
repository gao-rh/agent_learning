import argparse
import json
from pathlib import Path

from .runtime import prepare, run, step, summary


def main():
    parser = argparse.ArgumentParser(description="AI用户多轮测试；prepare/summary不联网，run/step须--live")
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("prepare")
    p.add_argument("directory", type=Path)
    p.add_argument("--kind", choices=["query", "complex", "knowledge"], required=True)
    p.add_argument("--cases", nargs="+", required=True)
    p.add_argument("--max-turns", type=int, default=6)
    p.add_argument("--max-requests", type=int, default=30)
    for name in ("run", "step", "summary"):
        p = commands.add_parser(name)
        p.add_argument("directory", type=Path)
        if name != "summary":
            p.add_argument("--case", required=True)
            p.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.directory, args.kind, args.cases, args.max_turns, args.max_requests)
    elif args.command == "summary":
        result = summary(args.directory)
    else:
        if not args.live:
            parser.error("付费入口需要显式--live；先说明本轮案例/调用/Token/费用预算")
        result = (run if args.command == "run" else step)(args.directory, args.case)
        if args.command == "step":
            result = {"turns": result["turns"], "finished": result["finished"],
                      "stop_reason": result.get("stop_reason")}
        else:
            result = {"usage": result["usage"], "assistant_usage": result["assistant_usage"],
                      "simulated_user_usage": result["simulated_user_usage"],
                      "cases": {k: {"turns": v.get("turns", 0), "stop_reason": v.get("stop_reason")}
                                for k, v in result["cases"].items()}, "grade": result["grade"]}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
