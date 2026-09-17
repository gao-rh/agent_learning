"""试玩版可读回放：沿用原始日志协议，为真实工具循环增加阅读视图。

只投影日志中实际记录的内容，不调用模型，不修改 trace.jsonl；旧 v2 的
Trace 与页面保持原样。检索、精确口径读取、枚举映射各有单独的工具卡片。
"""

import json
from pathlib import Path

from ..main_agent.trace import Trace as BaseTrace
from ..main_agent.trace_report import report_data

TOOL_LABELS = {
    "search_metrics": "搜索指标候选",
    "get_metric_definition": "按精确 ID 读取口径",
    "search_dimensions": "查找维度与支持范围",
    "search_dimension_values": "搜索枚举并确认所属维度",
    "finish_resolution": "提交结构化条件，交给程序检查",
    "query_agent": "执行取数函数",
    "analysis_agent": "执行分析函数",
    "analysis.query_agent": "分析内的取数步骤",
}


def readable_data(events, thread_id):
    data = report_data(events, thread_id)
    # 分析父结果引用本期，只有其 current / baseline 子结果是实际两次取数。
    data["queries"] = [q for q in data["queries"] if not q["evidence_id"].endswith("-comparison")]
    for step in data["steps"]:
        # 旧回放的解释对应 v2 渠道贡献算法；本版本仅承诺等长期间及同组对比。
        step["notes"] = [
            n.replace("分析变化及渠道贡献", "比较前后期间")
            .replace("差额、变动率和渠道贡献", "总量和各分组的前后变化")
            .replace("渠道贡献能定位变化分布", "分组对比能展示变化分布")
            .replace(
                "完成日期范围内的取数，并检查是否缺行、截断或出现异常值。",
                "按已通过白名单检查的条件读取模拟日数据，返回行数和是否有结果。",
            )
            for n in step["notes"]
        ]
        ends = {e["span_id"]: e for e in step["raw_events"] if e["kind"] == "span_end"}
        step["tools"] = []
        for change in step["changes"]:
            for key in ["before", "after"]:
                if change.get(key) == "分析变化及渠道贡献":
                    change[key] = "比较前后期间"
        for e in step["raw_events"]:
            if e["kind"] != "span_start" or e.get("category") != "tool":
                continue
            end = ends.get(e["span_id"], {})
            output = end.get("output", {})
            result = output.get("result", output)
            summary = "详细输入和返回见下方；本步骤未记录完成结果。"
            if "candidates" in result:
                candidates = result["candidates"]
                summary = (
                    "；".join(
                        x["name"]
                        + ("（不支持）" if x.get("supported") is False else "")
                        + (" → " + x["dimension_name"] if x.get("dimension_name") else "")
                        for x in candidates
                    )
                    or "没有匹配候选，需要调整或澄清。"
                )
                if result.get("exact_ambiguity"):
                    summary += "。有多个同名候选，不能按相似度直接选一个。"
            elif e["name"] == "get_metric_definition" and result.get("name"):
                summary = (
                    result["name"]
                    + "；支持："
                    + "、".join(d["name"] for d in result.get("supported_dimensions", []))
                )
            elif e["name"] == "finish_resolution":
                summary = "模型提出的任务条件如下，随后由代码准入或进入澄清。"
            elif result.get("facts"):
                summary = "；".join(f"{k}：{v}" for k, v in result["facts"].items())
            elif result.get("error"):
                summary = str(result["error"])
            step["tools"].append(
                {
                    "label": TOOL_LABELS.get(e["name"], e["name"]),
                    "name": e["name"],
                    "inputs": e.get("inputs"),
                    "summary": summary,
                    "output": result,
                }
            )
        responses = [e for e in step["raw_events"] if e["kind"] == "model_response"]
        for call, response in zip(step["model_calls"], responses):
            if response.get("tool_calls"):
                call["response"] = json.dumps(
                    {"content": response.get("content"), "tool_calls": response["tool_calls"]},
                    ensure_ascii=False,
                )
            for message in call["messages"]:
                message["role"] = message.get("role") or message.get("type", "unknown")
                if message.get("tool_calls"):
                    message["content"] = json.dumps(
                        {"content": message.get("content"), "tool_calls": message["tool_calls"]},
                        ensure_ascii=False,
                    )
    return data


class Trace(BaseTrace):
    def render(self):
        data = readable_data(self.read(), self.thread_id)
        payload = (
            json.dumps(data, ensure_ascii=False)
            .replace("<", "\\u003c")
            .replace(">", "\\u003e")
            .replace("&", "\\u0026")
        )
        page = (
            Path(__file__)
            .with_name("trace_view.html")
            .read_text()
            .replace("__TRACE_DATA_JSON__", payload)
        )
        target = self.directory / "trace.html"
        target.write_text(page, encoding="utf-8")
        return target
