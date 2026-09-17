"""可检索的本地知识：名称有出处，执行 ID / 支持矩阵 / 数值是演示配置。

工具只返回候选和配置，不执行查询。是否采用某个候选仍需消歧；进入取数
前 validate_task 会再次检查指标、维度、枚举和父子关系，不能凭模型口头承诺。
"""

import json
import re
from copy import deepcopy
from difflib import SequenceMatcher
from pathlib import Path

KNOWLEDGE = json.loads(Path(__file__).with_name("knowledge.json").read_text())
METRICS = {m["id"]: m for m in KNOWLEDGE["metrics"]}
DIMENSIONS = KNOWLEDGE["dimensions"]


class ClarificationNeeded(ValueError):
    """可向用户解释的需求问题，不是需要重试的网络故障。"""


def normalize(text):
    return re.sub(r"[\W_]", "", text.lower())


def score(query, item):
    q = normalize(query)
    # 目录工具既支持人类名称/别名，也支持已读到的精确 ID。
    # 例如 merchant_app 是合法枚举编码，不应因为与中文名称不相似而搜不到。
    names = [
        normalize(x)
        for x in [item["name"], *item.get("aliases", []), *([item["id"]] if item.get("id") else [])]
    ]
    if not q:
        return 1.0
    if q in names:
        return 1.0
    return max(
        0.8 if q in name or name in q else SequenceMatcher(None, q, name).ratio() for name in names
    )


def search_metrics(query: str) -> dict:
    """按用户指标表达搜索候选；同名/别名冲突会返回多个，不自动取第一名。"""
    matches = sorted([(score(query, m), m) for m in METRICS.values()], key=lambda x: -x[0])
    hits = [
        {
            "id": m["id"],
            "name": m["name"],
            "aliases": m["aliases"],
            "definition": m["definition"],
            "score": round(s, 3),
        }
        for s, m in matches
        if s >= 0.42
    ][:6]
    return {"candidates": hits, "exact_ambiguity": sum(h["score"] == 1 for h in hits) > 1}


def get_metric_definition(metric_id: str) -> dict:
    """用搜索获得的精确 ID 读取口径、查询方式和可用维度，不查询业务数值。"""
    if metric_id not in METRICS:
        raise ClarificationNeeded("未找到这个指标 ID，请先搜索指标。")
    m = deepcopy(METRICS[metric_id])
    m["metric_id"] = m["id"]  # 兼容原来的可读 Trace 元数据契约。
    # 数值夹具不提前给模型；回答中的值必须来自实际执行函数。
    m.pop("preset")
    m["supported_dimensions"] = [
        {"id": d, "name": DIMENSIONS[d]["name"], "aliases": DIMENSIONS[d]["aliases"]}
        for d in m["dimensions"]
    ]
    return m


def search_dimensions(metric_id: str, query: str) -> dict:
    """找维度并标出当前指标是否支持；不支持的维度不能悄悄丢弃或替换。"""
    m = get_metric_definition(metric_id)
    hits = [
        {
            "id": key,
            "name": d["name"],
            "definition": d["definition"],
            "supported": key in m["dimensions"],
            "score": round(score(query, d), 3),
        }
        for key, d in DIMENSIONS.items()
        if score(query, d) >= 0.45
    ]
    hits.sort(key=lambda x: -x["score"])
    return {"candidates": hits[:5], "supported_dimensions": m["supported_dimensions"]}


def search_dimension_values(metric_id: str, query: str, dimension_id: str = "") -> dict:
    """搜索枚举及所属维度；例如“新商”返回商户新老维度及标准枚举编码。

    dimension_id 可留空做跨维度搜索；结果同时指出此指标是否支持该维度/枚举。
    """
    m = get_metric_definition(metric_id)
    if dimension_id and dimension_id not in DIMENSIONS:
        raise ClarificationNeeded("未知维度 ID，请先搜索维度。")
    hits = []
    for key, d in DIMENSIONS.items():
        if dimension_id and key != dimension_id:
            continue
        for value in d["values"]:
            s = score(query, value)
            if s >= 0.5:
                hits.append(
                    {
                        **value,
                        "dimension_id": key,
                        "dimension_name": d["name"],
                        "supported": value["id"] in m["dimensions"].get(key, []),
                        "score": round(s, 3),
                    }
                )
    hits.sort(key=lambda x: -x["score"])
    allowed = {
        key: [v for v in DIMENSIONS[key]["values"] if v["id"] in ids]
        for key, ids in m["dimensions"].items()
        if not dimension_id or key == dimension_id
    }
    return {"candidates": hits[:10], "allowed_values": allowed}


def validate_task(task):
    """取数前的确定性准入：不接受凭空指标、全局合法但本指标不支持的维度或值。"""
    metric = get_metric_definition(task["metric_id"])
    supported = metric["dimensions"]
    for dim in set(task.get("group_by", [])) | set(task.get("filters", {})):
        if dim not in supported:
            label = DIMENSIONS.get(dim, {}).get("name", dim)
            choices = "、".join(DIMENSIONS[d]["name"] for d in supported)
            raise ClarificationNeeded(
                f"{metric['name']}不支持“{label}”；支持{choices}。要改用哪项，还是取消这项条件？"
            )
    for dim, ids in task.get("filters", {}).items():
        if not isinstance(ids, list) or not ids or any(v not in supported[dim] for v in ids):
            choices = "、".join(
                v["name"] for v in DIMENSIONS[dim]["values"] if v["id"] in supported[dim]
            )
            raise ClarificationNeeded(
                f"{metric['name']}的{DIMENSIONS[dim]['name']}只支持：{choices}。请选择或取消该条件。"
            )
    filters = task.get("filters", {})
    if "channel_l1" in filters and "channel_l2" in filters:
        parents = DIMENSIONS["channel_l2"]["parent_values"]
        if any(parents[v] not in filters["channel_l1"] for v in filters["channel_l2"]):
            raise ClarificationNeeded("二级渠道与一级渠道不匹配：钱包下的入口不能与开门营业组合。")
    return metric


def enum_name(dim, value):
    return next(v["name"] for v in DIMENSIONS[dim]["values"] if v["id"] == value)
