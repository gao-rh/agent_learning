"""本地Trace的只读用量投影：一轮/run、一任务/thread、一会话分别累计。

只计model_request/model_response，不计重复State快照、SSE片段或页面浏览。
缺usage的调用明确列为未知，不假装免费。价格为有日期的估算参数，非账单。
"""
import json
import statistics
from collections import defaultdict, deque
from datetime import UTC, datetime
from pathlib import Path

PRICE = {'model': 'kimi-k2.6', 'currency': 'CNY', 'per_million':
         {'input': 6.5, 'cache_read': 1.1, 'output': 27},
         'checked_at': '2026-09-09',
         'source': 'https://www.kimi.com/resources/kimi-k2-6-pricing'}
FIELDS = ('calls', 'responses', 'input_tokens', 'output_tokens', 'total_tokens', 'cache_read',
          'usage_unknown_calls', 'model_errors')


def read(path):
    if not path.exists():
        return []
    result = []
    for line in path.read_text().splitlines():
        try:
            result.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # 活跃任务可能刚写到半行；下次刷新再读
    return result


def cost(row):
    rates = PRICE['per_million']
    return round(((row['input_tokens']-row['cache_read'])*rates['input'] +
                  row['cache_read']*rates['cache_read'] +
                  row['output_tokens']*rates['output']) / 1_000_000, 6)


def summarize(events):
    out = dict.fromkeys(FIELDS, 0)
    models = {e.get('model') for e in events if e.get('kind') == 'model_request'}
    for e in events:
        if e.get('kind') == 'model_request':
            out['calls'] += 1
        elif e.get('kind') == 'model_error':
            out['model_errors'] += 1
        elif e.get('kind') == 'model_response':
            usage = e.get('usage') or {}
            if not usage:
                continue
            out['responses'] += 1
            for key in ('input_tokens', 'output_tokens', 'total_tokens'):
                out[key] += usage.get(key, 0)
            out['cache_read'] += (usage.get('input_token_details') or {}).get('cache_read', 0)
    out['usage_unknown_calls'] = max(0, out['calls']-out['responses'])
    out['estimated_cny'] = cost(out) if models.issubset({'kimi-k2.6'}) else None
    return out


def add(rows):
    rows = list(rows)
    out = {key: sum(row[key] for row in rows) for key in FIELDS}
    costs = [r.get('estimated_cny') for r in rows]
    out['estimated_cny'] = round(sum(c for c in costs if c is not None), 6)
    out['unpriced_records'] = sum(c is None for c in costs)
    return out


def task_kind(events, question):
    if any(e.get('kind') == 'conversation_reply' for e in events):
        return 'conversation'
    plans = [e for e in events if e.get('kind') == 'plan']
    intents = {j['task']['intent'] for p in plans for j in p.get('jobs', [])}
    if not intents:  # 旧版本或尚在澄清：明确标出类型由问题推断
        for e in reversed(events):
            if e.get('kind') == 'state_snapshot':
                task = (e.get('state') or {}).get('task') or {}
                if task.get('intent'):
                    intents.add(task['intent'])
                    break
    if 'analysis' in intents:
        return 'analysis'
    if 'query' in intents:
        return 'query'
    if 'knowledge' in intents:
        return 'knowledge'
    return 'unresolved_analysis' if any(t in question for t in ('分析', '归因', '为什么')) else 'unresolved'


def timestamp(value):
    return datetime.fromisoformat(value).timestamp()


def peaks(events):
    """滚动60秒：RPM按请求发起；Token按收到usage时归属，仅作客户端观测。"""
    points = []
    for e in events:
        if not e.get('time'):
            continue
        if e.get('kind') == 'model_request':
            points.append((timestamp(e['time']), 1, 0))
        elif e.get('kind') == 'model_response':
            points.append((timestamp(e['time']), 0, (e.get('usage') or {}).get('total_tokens', 0)))
    window, calls, tokens, rpm, tpm = deque(), 0, 0, 0, 0
    for t, c, v in sorted(points):
        while window and window[0][0] <= t-60:
            _, old_c, old_v = window.popleft()
            calls -= old_c
            tokens -= old_v
        window.append((t, c, v))
        calls += c
        tokens += v
        rpm, tpm = max(rpm, calls), max(tpm, tokens)
    return {'observed_peak_rpm': rpm, 'observed_peak_tpm': tpm,
            'note': '滚动60秒观测；Token按usage返回时间，不等于供应商精确限流账本。'}


def collect(root):
    root = Path(root)
    seen, events, turns, tasks = set(), [], [], []
    for path in sorted(root.rglob('trace.jsonl'),
                       key=lambda p: (p.parent.parent.name != 'tasks', str(p))):
        local = []
        for e in read(path):
            key = (e.get('run_id') or str(path), e.get('seq'), e.get('kind'))
            if key in seen:
                continue
            seen.add(key)
            local.append(e)
        if not local:
            continue
        starts = [e for e in local if e.get('kind') == 'execution_start']
        if not starts:
            continue
        # 不把确定性测试替身当真实Kimi样本；旧实验无usage仍显示未知。
        models = {e.get('model') for e in local if e.get('kind') == 'model_request'}
        if models and models != {'kimi-k2.6'}:
            continue
        events.extend(local)
        cid = path.parent.parent.parent.name if path.parent.parent.name == 'tasks' else None
        tid = local[0].get('thread_id', path.parent.name)
        folder = str(path.parent.relative_to(root))
        by_run = defaultdict(list)
        for e in local:
            by_run[e.get('run_id')].append(e)
        task_turns = []
        for start in starts:
            rs = by_run[start.get('run_id')]
            last = next((e.get('state', {}) for e in reversed(rs)
                         if e.get('kind') == 'state_snapshot'), {})
            source_input = start.get('input') or {}
            question = source_input.get('text') or source_input.get('answer') or source_input.get('question') or ''
            row = {**summarize(rs), 'run_id': start.get('run_id'), 'thread_id': tid,
                   'conversation_id': cid, 'engine': start['name'], 'time': start.get('time'),
                   'question': question, 'kind': task_kind(rs, question),
                   'analysis_complete': all(c.get('investigation', {}).get('status', 'completed') == 'completed'
                       for c in (last.get('result') or {}).get('cards', [])),
                   'status': last.get('status', 'unknown'), 'folder': folder,
                   'duration_seconds': round(timestamp(rs[-1]['time'])-timestamp(start['time']), 2)}
            turns.append(row)
            task_turns.append(row)
        if not task_turns:
            continue
        last = task_turns[-1]
        tasks.append({**add(task_turns), 'conversation_id': cid, 'thread_id': tid, 'folder': folder,
                      'engine': last['engine'], 'status': last['status'],
                      'kind': task_kind(local, task_turns[0]['question']),
                      'question': task_turns[0]['question'], 'time': last['time'],
                      'rounds': len(task_turns), 'analysis_complete': last['analysis_complete'],
                      'duration_seconds': sum(r['duration_seconds'] for r in task_turns)})
    groups = defaultdict(list)
    for task in tasks:
        groups[(task['engine'], task['kind'])].append(task)
    profiles = []
    for (engine, kind), group in sorted(groups.items()):
        success = [g for g in group if g['status'] == 'completed' and not g['usage_unknown_calls']
                   and g['calls'] and g['analysis_complete']]
        profiles.append({'engine': engine, 'kind': kind, 'samples': len(group),
                         'completed_samples': len(success),
                         'other_samples': len(group)-len(success),
                         **{f'avg_{field}': round(statistics.mean(g[field] for g in success), 2)
                            if success else None
                            for field in ('rounds', 'calls', 'total_tokens', 'duration_seconds')},
                         'total': add(group)})
    return {'generated_at': datetime.now(UTC).isoformat(), 'price': PRICE,
            'total': add(turns), 'turn_count': len(turns), 'task_count': len(tasks),
            'profiles': profiles, 'turns': sorted(turns, key=lambda t: t['time'], reverse=True),
            'tasks': sorted(tasks, key=lambda t: t['time'], reverse=True),
            'observed': peaks(events)}


def capacity(query_tokens=12000, analysis_tokens=30000, query_calls=6, analysis_calls=10,
             analysis_share=.3, concurrent=15, batch_seconds=60, users=30, tasks_per_user=10):
    """场景估算，不假装已经完成真实并发压测；输入均有上下界。"""
    values = [query_tokens, analysis_tokens, query_calls, analysis_calls, analysis_share,
              concurrent, batch_seconds, users, tasks_per_user]
    if any(not isinstance(v, (int, float)) or not 0 <= v <= 1e8 for v in values):
        raise ValueError('容量参数超出范围')
    if not 0 <= analysis_share <= 1 or batch_seconds < 1:
        raise ValueError('比例需为0至1，完成周期至少1秒')
    tokens = query_tokens*(1-analysis_share)+analysis_tokens*analysis_share
    calls = query_calls*(1-analysis_share)+analysis_calls*analysis_share
    per_minute = concurrent*60/batch_seconds
    per_day = users*tasks_per_user
    return {'mixed_tokens_per_task': round(tokens), 'mixed_calls_per_task': round(calls, 2),
            'estimated_tpm': round(per_minute*tokens), 'estimated_rpm': round(per_minute*calls, 1),
            'daily_tasks': per_day, 'daily_tokens': round(per_day*tokens),
            'daily_model_calls': round(per_day*calls),
            'note': '假设每个完成周期处理一批任务并持续该速率；并发上限5可能让任务排队，不保证达到此吞吐。'}
