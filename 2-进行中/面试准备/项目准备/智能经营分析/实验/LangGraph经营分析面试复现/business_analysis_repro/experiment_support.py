"""小实验共用的来源协议和源码快照。只读公开检索记录，不读标准答案。"""

import hashlib
import zipfile
from copy import deepcopy


def source_bound_tool(tool, knowledge):
    """把可引用来源限定为模型已经实际收到的 ID，不替模型猜或改写引用。"""
    result = deepcopy(tool)
    properties = result["function"]["parameters"].get("properties", {})
    if "knowledge_refs" in properties and hasattr(knowledge, "received_knowledge_ids"):
        refs = properties["knowledge_refs"]
        ids = sorted(knowledge.received_knowledge_ids())
        refs["description"] = "只能选择已读取的来源 ID；指标 ID、任务 ID 不属于来源。"
        if ids:
            refs["items"] = {"type": "string", "enum": ids}
        else:
            refs["maxItems"] = 0
    return result


def validate_source_refs(proposal, knowledge):
    if not hasattr(knowledge, "received_knowledge_ids"):
        return {}
    before = list(getattr(proposal, "knowledge_refs", []))
    received = knowledge.received_knowledge_ids()
    # 只从实际工具返回建立映射，不能拼 SYN- 前缀或从整个目录补证据。
    sources = {}
    for observation in getattr(knowledge, "observations", []):
        if observation.get("tool") != "get_metric_definition":
            continue
        result = observation.get("result", {})
        metric_id = result.get("metric_id") or observation.get("arguments", {}).get("metric_id")
        source_id = result.get("source", {}).get("id")
        if metric_id and source_id in received:
            sources.setdefault(metric_id, set()).add(source_id)
    converted, mappings = [], []
    for ref in before:
        choices = sources.get(ref, set())
        target = next(iter(choices)) if ref not in received and len(choices) == 1 else ref
        if target != ref:
            mappings.append({"metric_id": ref, "source_id": target})
        if target not in converted:
            converted.append(target)
    unknown = set(converted) - received
    if unknown:
        raise ValueError("knowledge_refs 含未读取的来源 ID：" + ", ".join(sorted(unknown)))
    if before == converted:
        return {}
    proposal.knowledge_refs = converted
    return {"before": before, "after": converted, "mappings": mappings}


def write_snapshot(directory, root, hashes):
    """仅冻结 manifest 白名单；凭证和运行日志不进入源码包。拒绝半途漂移。"""
    target = directory / "source-snapshot.zip"
    temporary = directory / "source-snapshot.tmp"
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            for relative, expected in sorted(hashes.items()):
                path = (root / relative).resolve()
                if not path.is_relative_to(root.resolve()) or path.suffix not in {".py", ".json"}:
                    raise ValueError("快照只能包含包内明确列出的源码和固定资料")
                content = path.read_bytes()
                if hashlib.sha256(content).hexdigest() != expected:
                    raise ValueError("准备期间文件变化，请用新目录重新准备：" + relative)
                archive.writestr(relative, content)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
