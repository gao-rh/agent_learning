"""第一课：模型请求是数据；由 Python 执行工具。离线，不调用任何模型。"""

import argparse
import json
from pathlib import Path


def read(path):
    """提供好的示例工具：只读取本课的 lesson.txt。"""
    if path != "lesson.txt":
        raise ValueError("本课只允许读取 lesson.txt")
    return Path(__file__).with_name("lesson.txt").read_text(encoding="utf-8")


TOOLS = {"read": read}  # 名称 -> Python 函数；模型不能任意指定代码执行。


def execute_tool_call(tool_call):
    """你的练习区：把一条工具请求变成一条工具结果消息。"""
    # 1. 从 tool_call["function"] 取出 name 和 arguments。
    # 2. arguments 是 JSON 字符串，用 json.loads 得到参数字典。
    # 3. 从 TOOLS 找到函数，用参数字典调用它，取得实际结果。
    # 4. 返回字典，含 role="tool"、tool_call_id、content 三个字段。
    #    tool_call_id 对应本次请求的 id；content 必须是实际工具结果。
    raise NotImplementedError("请先补完 execute_tool_call，再使用 --execute")


def main(execute=False):
    messages = [{"role": "user", "content": "请读取 lesson.txt，告诉我复现语言。"}]

    # 这是人工写好的模拟响应，不是 Kimi 生成的，也没有发生网络请求。
    assistant_message = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_read_001",
                "type": "function",
                "function": {
                    "name": "read",
                    "arguments": '{"path": "lesson.txt"}',
                },
            }
        ],
    }
    messages.append(assistant_message)
    print("当前消息（模拟模型已经提出请求）：")
    print(json.dumps(messages, ensure_ascii=False, indent=2))

    if not execute:
        print("\n观察模式：尚未执行 read，也没有把消息发给模型。")
        return messages

    tool_call = assistant_message["tool_calls"][0]
    tool_message = execute_tool_call(tool_call)
    messages.append(tool_message)
    print("\n工具执行后，准备给下一次模型请求的消息：")
    print(json.dumps(messages, ensure_ascii=False, indent=2))
    print("\n本课到这里停止：尚未发起第二次模型请求，也没有生成最终回答。")
    return messages


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="执行你补完的练习函数")
    args = parser.parse_args()
    try:
        main(execute=args.execute)
    except NotImplementedError as error:
        parser.exit(1, f"练习提示：{error}\n")
