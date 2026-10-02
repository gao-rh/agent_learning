"""按实验实例装配只读知识，不修改试玩 catalog 的进程全局变量。

目录、定义和枚举属于模型可以查询的公开实验信息；题目标准答案不在这里。
每个对外工具的真实返回单独记录，避免把“库里有”误认为“模型看到了”。
"""

import json
from copy import deepcopy
from functools import wraps
from pathlib import Path

from ..playground.catalog import normalize, score

FIXTURES = Path(__file__).with_name("fixtures")


def load_public(name):
    if name not in {"catalog.json", "knowledge.json", "knowledge_with_definition.json", "cases.json"}:
        raise ValueError("该文件不是公开实验输入")
    return json.loads((FIXTURES / name).read_text())


def get_case(case_id):
    return next(c for c in load_public("cases.json")["cases"] if c["id"] == case_id)


class LabKnowledge:
    normalize = staticmethod(normalize)

    def __init__(self, profile="base"):
        if profile not in {"base", "with_definition"}:
            raise ValueError("未知实验知识配置")
        self.profile = profile
        self.catalog = load_public("catalog.json")
        self.DIMENSIONS = self.catalog["dimensions"]
        self.metrics = {m["id"]: m for m in self.catalog["metrics"]}
        self.records = load_public("knowledge.json")["records"]
        if profile == "with_definition":
            self.records += load_public("knowledge_with_definition.json")["records"]
        self.observations = []

    def search_metrics(self, query: str) -> dict:
        """搜索指标名、别名和ID，返回候选及定义摘要；分数不是正确概率。"""
        ranked = sorted(((score(query, m), m) for m in self.metrics.values()),
                        key=lambda pair: -pair[0])
        candidates = [{k: m[k] for k in ("id", "name", "aliases", "definition")}
                      | {"score": round(s, 3)} for s, m in ranked if s >= .42][:8]
        return {"candidates": candidates,
                "exact_ambiguity": sum(c["score"] == 1 for c in candidates) > 1}

    def get_metric_definition(self, metric_id: str) -> dict:
        """按精确ID读取模拟口径、必选规则、可用维度和日期能力，不返回业务数值。"""
        if metric_id not in self.metrics:
            raise ValueError("指标ID不存在，请先搜索")
        metric = deepcopy(self.metrics[metric_id])
        metric["metric_id"] = metric_id
        metric["supported_dimensions"] = [
            {"id": d, "name": self.DIMENSIONS[d]["name"],
             "aliases": self.DIMENSIONS[d]["aliases"]} for d in metric["dimensions"]]
        return metric

    def search_dimensions(self, metric_id: str, query: str) -> dict:
        """搜索维度并标记该指标是否支持，不执行分组或筛选。"""
        metric = self.get_metric_definition(metric_id)
        hits = [{"id": key, "name": d["name"], "definition": d["definition"],
                 "score": round(score(query, d), 3), "supported": key in metric["dimensions"]}
                for key, d in self.DIMENSIONS.items() if score(query, d) >= .45]
        return {"candidates": sorted(hits, key=lambda x: -x["score"]),
                "supported_dimensions": metric["supported_dimensions"]}

    def search_dimension_values(self, metric_id: str, query: str, dimension_id: str = "") -> dict:
        """查枚举及所属维度；query为空可列举枚举；明确标记该指标允许的值。"""
        metric = self.get_metric_definition(metric_id)
        if dimension_id and dimension_id not in self.DIMENSIONS:
            raise ValueError("维度ID不存在")
        hits, allowed = [], {}
        for dim_id, dim in self.DIMENSIONS.items():
            if dimension_id and dimension_id != dim_id:
                continue
            if dim_id in metric["dimensions"]:
                allowed[dim_id] = [deepcopy(v) for v in dim["values"]
                                   if v["id"] in metric["dimensions"][dim_id]]
            for value in dim["values"]:
                similarity = score(query, value)
                if similarity >= .5:
                    hits.append(deepcopy(value) | {"dimension_id": dim_id,
                        "dimension_name": dim["name"], "score": round(similarity, 3),
                        "supported": value["id"] in metric["dimensions"].get(dim_id, [])})
        return {"candidates": sorted(hits, key=lambda x: -x["score"])[:20],
                "allowed_values": allowed, "enum_set_complete": True}

    def search_business_knowledge(self, query: str) -> dict:
        """检索模拟业务定义，返回来源、适用范围和版本；无匹配不补造定义。"""
        hits = []
        for record in self.records:
            similarity = score(query, {"name": record["title"], "aliases": record["terms"]})
            if similarity >= .5:
                hits.append(deepcopy(record) | {"score": round(similarity, 3)})
        return {"records": sorted(hits, key=lambda x: -x["score"])[:5], "synthetic": True}

    def business_context(self, messages) -> dict:
        """小知识库先按当前用户原话检索；不用案例标签、词表补答案或调用模型。"""
        query = next((m.get("content", "") for m in reversed(messages)
                      if m.get("role") in {"human", "user"}), "")
        if not isinstance(query, str) or not query.strip():
            return {"records": [], "synthetic": True, "query": "", "initiated_by": "program"}
        result = self.tools()["search_business_knowledge"](query=query)
        return {**result, "query": query, "initiated_by": "program"}

    def tools(self):
        """保留原函数签名供 Tool Calling 生成 schema，记录外层实际返回。"""
        result = {}
        for name in ("search_metrics", "get_metric_definition", "search_dimensions",
                     "search_dimension_values", "search_business_knowledge"):
            method = getattr(self, name)

            def wrap(fn):
                @wraps(fn)
                def recorded(**kwargs):
                    value = fn(**kwargs)
                    self.observations.append({"tool": fn.__name__, "arguments": deepcopy(kwargs),
                                              "result": deepcopy(value)})
                    return value
                return recorded

            result[name] = wrap(method)
        return result

    def received_knowledge_ids(self):
        received = {r["id"] for item in self.observations
                    for r in item["result"].get("records", [])}
        # 指标定义也是可引用的知识来源，但只能引用本轮实际返回的source.id。
        # 不能因为整个catalog里存在某个ID就放行，否则会掩盖未检索/编造引用。
        received.update(item["result"]["source"]["id"] for item in self.observations
                        if item["tool"] == "get_metric_definition"
                        and item["result"].get("source", {}).get("id"))
        return received

    def snapshot(self):
        return {"catalog": deepcopy(self.catalog), "knowledge": deepcopy(self.records)}
