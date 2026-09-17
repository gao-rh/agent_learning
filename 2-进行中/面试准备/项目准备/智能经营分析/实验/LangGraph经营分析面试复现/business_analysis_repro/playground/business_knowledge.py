"""小型业务知识库：可解释的词项检索，无 embedding/API 调用。

精确指标配置仍在 catalog；这里保存方法、适用范围及推荐指标。
返回来源与证据状态，检索分数不是正确概率。Skill 文件是应用的运行时
资料，不是安装给 Codex 的全局技能；只按固定白名单读取。
"""
import json
import re
from pathlib import Path

from . import catalog

BASE = Path(__file__).parent
DOCUMENTS = json.loads((BASE / 'business_knowledge.json').read_text())
SKILLS = {'channel', 'premium', 'penetration', 'merchant'}


def search_business_knowledge(query: str) -> dict:
    """搜索业务专题/分析方法；如渠道归因、保费、渗透率、商户分析。"""
    q = catalog.normalize(query)
    hits = []
    for doc in DOCUMENTS:
        terms = [catalog.normalize(t) for t in doc['tags']]
        score = sum(len(t) for t in terms if t and t in q)
        if q and q in catalog.normalize(doc['title']):
            score += 2
        if score or not q:
            hits.append({**doc, 'score': score, 'metrics': [
                {'id': mid, 'name': catalog.METRICS[mid]['name']}
                for mid in doc['metric_ids']
            ]})
    return {'method': '关键词和别名匹配，不是向量语义搜索',
            'candidates': sorted(hits, key=lambda d: -d['score'])[:4]}


def read_skill(metric_id: str) -> dict:
    """用已确认指标选择所属专题，问法只决定深度，不改变指标口径。"""
    name = catalog.METRICS[metric_id]['name']
    if '保费' in name:
        key = 'premium'
    elif '渗透率' in name:
        key = 'penetration'
    elif any(t in name for t in ('外部入口', '详情页', '外卖险加入')):
        key = 'channel'
    else:
        key = 'merchant'
    path = BASE / 'analysis_skills' / key / 'SKILL.md'
    return {'id': key, 'version': 'demo-v1', 'path': str(path.relative_to(BASE)),
            'text': path.read_text(), 'knowledge': search_business_knowledge(
                next(d['tags'][0] for d in DOCUMENTS if d.get('skill') == key))['candidates']}


def topic_hint(messages: list[dict]) -> dict | None:
    """开放专题的问题才给建议；不把用户指定的精确指标替换为默认指标。"""
    text = ' '.join(m.get('content', '') for m in messages if m.get('role') in {'human', 'user'})
    if not re.search(r'专题|归因|为什么|原因|分析', text):
        return None
    hits = search_business_knowledge(text)['candidates']
    return hits[0] if hits else None
