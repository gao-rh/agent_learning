"""CLI：运行一个问题、跨进程补充信息，或离线查看既有 Trace。

示例在本实验 README。返回码：0 完成/查看，2 等待澄清，1 失败。
"""

import argparse
import json
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from ..settings import PROJECT_DIR
from .runtime import execute, thread_directory
from .trace import Trace


def main():
    parser = argparse.ArgumentParser(description="七节点 LangGraph 主 Agent；业务数据均为模拟。")
    subs = parser.add_subparsers(dest="command", required=True)
    for command in ["run", "resume", "inspect"]:
        sub = subs.add_parser(command)
        sub.add_argument("--thread-id", required=command != "run")
        sub.add_argument("--output-dir", default=str(PROJECT_DIR / ".runs" / "main-agent"))
        if command == "run":
            sub.add_argument("question")
            sub.add_argument(
                "--reference-date",
                default=datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat(),
            )
        if command == "resume":
            sub.add_argument("answer")
        if command != "inspect":
            sub.add_argument("--max-model-calls", type=int, default=16)
    args = parser.parse_args()
    thread_id = args.thread_id or ("task-" + uuid.uuid4().hex[:10])
    try:
        if args.command == "inspect":
            directory = thread_directory(args.output_dir, thread_id)
            state = json.loads((directory / "state.json").read_text())
            Trace(directory, thread_id).render()  # 离线重建报告，不需要密钥
        else:
            kwargs = (
                {"question": args.question, "reference_date": args.reference_date}
                if args.command == "run"
                else {"answer": args.answer}
            )
            state, directory = execute(
                output_dir=args.output_dir,
                thread_id=thread_id,
                max_calls=args.max_model_calls,
                **kwargs,
            )
        print(
            json.dumps(
                {
                    "thread_id": thread_id,
                    "status": state["status"],
                    "answer": state["answer"],
                    "pending_question": state["pending_question"],
                    "trace": str(directory / "trace.html"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        if args.command == "inspect":
            return 0
        return {"completed": 0, "waiting_user": 2, "failed": 1}[state["status"]]
    except Exception as exc:  # noqa: BLE001 -- CLI 最外层避免 SDK 错误暴露请求认证信息
        # 不向终端打印含有 SDK 请求信息的原始堆栈。
        print(
            json.dumps(
                {
                    "status": "error",
                    "error_type": type(exc).__name__,
                    "message": str(exc)
                    if isinstance(exc, (ValueError, FileNotFoundError))
                    else "执行未完成，请检查本地配置和 Trace。",
                },
                ensure_ascii=False,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
