"""被测助手与模拟用户共用请求预算，重试也计费。"""

import json
from pathlib import Path

from ..main_agent.trace import Trace
from ..playground.usage import summarize


class BudgetExceeded(RuntimeError):
    pass


def events(root):
    paths = list(Path(root).glob("*/trace.jsonl"))
    paths += list(Path(root).glob("conversations/*/tasks/*/trace.jsonl"))
    paths += list(Path(root).glob("simulated-users/*/after-*/trace.jsonl"))
    return [json.loads(line) for path in paths for line in path.read_text().splitlines() if line]


def check(root, data, turn_calls=0, per_turn=None):
    path = Path(root) / "batch.json"
    if not path.exists():
        return
    config = json.loads(path.read_text()).get("simulation")
    if not config:
        return
    usage = summarize(events(root))
    limits = config["limits"]
    if usage["calls"] >= limits["requests"] or (per_turn and turn_calls >= per_turn):
        raise BudgetExceeded("被测助手与 AI 用户合计达到请求上限")
    # UTF-8 字节数作保守上界，不冒充供应商精确 Token。
    upper = len(json.dumps({k: data[k] for k in ("messages", "tools") if k in data},
                           ensure_ascii=False).encode())
    if upper > limits["input_bytes_per_request"]:
        raise BudgetExceeded("本次上下文超过输入字节上限")
    output = data.get("parameters", {}).get("max_tokens", 6000)
    if usage["total_tokens"] + upper + output > limits["tokens"]:
        raise BudgetExceeded("合计用量与下一次请求上界超过 Token 预算")
    rates = config["price_reference"]["per_million"]
    next_cost = (upper * rates["input"] + output * rates["output"]) / 1_000_000
    if (usage["estimated_cny"] or 0) + next_cost > limits["estimated_cny"]:
        raise BudgetExceeded("合计估算费用与下一次请求上界超过预算")


class BudgetTrace(Trace):
    def __init__(self, directory, thread_id, batch_root, per_turn):
        super().__init__(directory, thread_id)
        self.batch_root, self.per_turn, self.turn_calls = batch_root, per_turn, 0

    def event(self, kind, name, **data):
        if kind == "model_request":
            check(self.batch_root, data, self.turn_calls, self.per_turn)
            self.turn_calls += 1
        return super().event(kind, name, **data)
