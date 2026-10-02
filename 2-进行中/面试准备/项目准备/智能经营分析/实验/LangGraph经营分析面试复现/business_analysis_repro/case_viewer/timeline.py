"""从实际事件提取连续阅读记录，不用最终 State 回填早先的工具参数。

只投影外显消息、实际工具输入输出和程序检查；不推测模型的思考过程。
模型上下文和工程节点仍可通过原步骤接口展开。
"""
import json


def step_payload(events, span_id, cutoff=None):
    """仅投影该步骤的外显事件；不导入执行器，且不展示游标后的输出。"""
    log = [e for e in events if cutoff is None or e['seq'] <= cutoff]
    start = next((e for e in log if e['kind'] == 'span_start' and e['span_id'] == span_id), None)
    if start is None:
        raise FileNotFoundError('该时刻尚未进入此节点')
    end = next((e for e in log if e['kind'] == 'span_end' and e['span_id'] == span_id), None)
    attached = [e for e in log if e.get('parent_span_id') == span_id
                and e['kind'] not in {'span_start', 'span_end', 'state_snapshot', 'graph_update', 'answer_delta'}]
    chunks = [e for e in log if e.get('parent_span_id') == span_id and e['kind'] == 'answer_delta']
    return {'input': start.get('inputs'), 'output': end.get('output') if end else None,
            'finished': end is not None, 'events': attached,
            'stream_text': ''.join(e['delta'] for e in chunks)}


def message_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return '\n'.join(x.get('text', '') for x in content
                         if isinstance(x, dict) and x.get('type') == 'text')
    return ''


def project_timeline(events, steps, answer):
    ends = {e['span_id']: e for e in events if e['kind'] == 'span_end'}
    starts = [e for e in events if e['kind'] == 'span_start' and e.get('category') == 'tool']
    roles = {s['id']: s['role'] for s in steps}
    items = []
    matched = set()
    previous_messages = None
    for event in events:
        kind = event['kind']
        if kind == 'model_request':
            messages = event.get('messages', [])
            # 初始 human 消息包含用户问题与组装上下文。后续仅投影在同一
            # 消息链尾部新增的 human 消息：它们是运行程序送给模型的反馈。
            # 若上下文被重写或截断，就不根据角色猜测其来源。
            if (previous_messages is not None
                    and messages[:len(previous_messages)] == previous_messages):
                for index, message in enumerate(messages[len(previous_messages):]):
                    if message.get('type', message.get('role')) not in {'human', 'user'}:
                        continue
                    content = message_text(message.get('content'))
                    if content.strip():
                        items.append({'id': f"feedback-{event['seq']}-{index}",
                                      'seq': event['seq'], 'kind': 'feedback', 'text': content})
            previous_messages = messages
        elif kind == 'model_response':
            content = message_text(event.get('content'))
            if content.strip() and content.strip() != answer.strip():
                items.append({'id': 'message-' + str(event['seq']), 'seq': event['seq'],
                              'kind': 'message', 'text': content})
            # 没有后续执行记录的工具请求也保留，不能把“提出调用”写成“已完成”。
            for index, call in enumerate(event.get('tool_calls', [])):
                arguments = call.get('args', call.get('arguments', {}))
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except ValueError:
                        pass
                match = next((s for s in starts if s['span_id'] not in matched
                              and s['seq'] > event['seq'] and s['name'] == call.get('name')
                              and s.get('inputs') == arguments), None)
                if match:
                    matched.add(match['span_id'])
                else:
                    items.append({'id': f"requested-{event['seq']}-{index}", 'seq': event['seq'],
                                  'kind': 'tool', 'name': call.get('name', ''),
                                  'role': '模型提出调用', 'input': arguments, 'output': None,
                                  'status': 'not_recorded', 'step_id': None})
        elif kind == 'span_start' and event.get('category') == 'tool':
            end = ends.get(event['span_id'], {})
            items.append({'id': event['span_id'], 'step_id': event['span_id'], 'seq': event['seq'],
                          'kind': 'tool', 'name': event['name'],
                          'role': roles.get(event['span_id'], '工具调用'),
                          'input': event.get('inputs'), 'output': end.get('output'),
                          'status': end.get('status', 'incomplete')})
        elif kind in {'model_error', 'experiment_error'}:
            items.append({'id': 'event-' + str(event['seq']), 'seq': event['seq'],
                          'kind': 'error', 'text': event.get('error') or event.get('error_type') or '调用失败'})
        elif kind in {'experiment_inspection', 'experiment_boundary'}:
            # 自动评审标准不插入执行过程，只显示当时真正执行的程序校验。
            validation = event.get('validation')
            if validation:
                items.append({'id': 'event-' + str(event['seq']), 'seq': event['seq'],
                              'kind': 'validation', 'validation': validation})
    return sorted(items, key=lambda item: item['seq'])
