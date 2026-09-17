# 阅读快照：2026-09-07；保留完整原文件，仅增加讲解注释。
# 原文件：/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/__main__.py
# 原文件 SHA-256：35749ad39024c945eff7aaabace2bc778b3f2d7ceed54029f91e1897f379106d
# 本副本用于阅读，不作为可独立运行的脚本；运行请使用原包的 python -m 入口。
# 搜索“剩余阅读”可定位还没按执行顺序讲完的部分；下文行号均指原文件。
# 配套摘要：../代码阅读摘要.md。注释是 Codex 的源码解读，不代表已验收你的理解。

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


# ── 应用入口｜原文件 17–52 行 ──
# 先沿 run 分支阅读：解析命令 → 准备参数 → 调用 execute。
# argparse 把终端文本变成 args 的属性，它不理解业务问题。
# execute 返回前，main 就停在这一层等待；图结束后从第 53 行继续。
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
    # ── 任务标识｜原文件 35 行 ──
    # 用户给了 thread_id 就沿用，否则生成新 ID。它是存档索引，不是操作系统线程。
    thread_id = args.thread_id or ("task-" + uuid.uuid4().hex[:10])
    try:
        # ── 查看与执行分开｜原文件 37–52 行 ──
        # inspect 读取已导出的状态并重建 HTML；不会创建 Kimi 客户端。
        # run / resume 进入同一个 execute，以 question 或 answer 区分模式。
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
        # ── 剩余阅读 3：把结果交给终端｜原文件 53–68 行 ──
        # execute 返回的是最终/暂停 State 和任务目录。这里选取五个字段打印。
        # 等待补充时 answer 可能为空，应看 pending_question；业务失败有明确失败回答。
        # 退出码 0=完成，2=正常等待用户，1=失败；inspect 成功固定返回 0。
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
    # ── 最外层异常边界｜原文件 69–83 行 ──
    # 节点之外的配置错误、文件错误等在这里转换成终端错误结果。
    # 这与 State.status=failed 分开：前者是入口执行异常，后者是图给出的失败状态。
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


# ── 实际启动点｜原文件 86–87 行 ──
# python -m business_analysis_repro.main_agent 会执行 main()，再把返回数字作为进程退出码。
if __name__ == "__main__":
    raise SystemExit(main())
