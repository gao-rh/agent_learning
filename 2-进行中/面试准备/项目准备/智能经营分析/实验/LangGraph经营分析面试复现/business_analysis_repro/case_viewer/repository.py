"""把现有两种实验记录投影为人读数据，不改写日志、判分或旧批次。

运行事实来自当轮 run_id 的 Trace；标准来自批次源码快照；审计纠正另列。
只从 .runs 边界内读取，记录中的绝对路径不能扩大文件访问范围。
"""
import io
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path

from ..playground.usage import add, summarize
from .storage import read_bytes, read_text
from .timeline import step_payload

LABELS = {
    'resolve_batch': '模型判断下一步', 'understand_request': '理解问题',
    'prepare_context': '准备本轮上下文', 'clarify': '等待／接收补充', 'query': '执行取数',
    'search_metrics': '搜索指标', 'get_metric_definition': '读取指标定义',
    'search_dimensions': '搜索维度', 'search_dimension_values': '查询枚举',
    'search_business_knowledge': '检索业务知识', 'finish_resolution': '提交任务或澄清',
    'query_local_simulation': '查询本地模拟数据', 'before_query': '程序校验任务',
    'finish_plan': '提交完整任务清单', 'resolve_complex': '模型理解与检索', 'complex_plan_check': '复杂任务契约检查',
    'stop_before_execution': '语义检查后停止', 'resolver_result': '程序接收模型结果',
}
CATEGORIES = {'model': '模型', 'tool': '工具', 'context': '上下文', 'node': '节点', 'graph': '执行图'}


def read_json(path, default=None):
    try:
        return json.loads(read_text(path))
    except (FileNotFoundError, json.JSONDecodeError):
        return {} if default is None else default


def read_events(path):
    events = []
    if path.exists():
        for line in read_text(path).splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # 正在写入的末行下次刷新再读取。
    return events


class Repository:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.project = self.root.parent

    def safe(self, path):
        path = Path(path).resolve()
        if not path.is_relative_to(self.root):
            raise FileNotFoundError('文件不在实验目录中')
        return path

    def batch_path(self, batch):
        if not re.fullmatch(r'[\w.-]+', batch) or batch in {'.', '..'}:
            raise FileNotFoundError('批次不存在')
        path = self.safe(self.root / batch)
        if not self.safe(path / 'batch.json').is_file():
            raise FileNotFoundError('批次不存在')
        return path

    def fixture(self, folder, name, *, allow_current=False):
        archive = folder / 'source-snapshot.zip'
        if archive.exists():
            with zipfile.ZipFile(io.BytesIO(read_bytes(self.safe(archive)))) as z:
                try:
                    return json.loads(z.read('clarification_lab/fixtures/' + name))
                except KeyError:
                    pass
        # 历史评审标准不能退回当前版本。仅名称目录允许使用当前资料。
        if not allow_current:
            return {}
        path = self.project / 'business_analysis_repro/clarification_lab/fixtures' / name
        return read_json(path)

    def batches(self):
        result = []
        for marker in self.root.glob('*/batch.json'):
            try:
                folder = self.batch_path(marker.parent.name)
                config = read_json(self.safe(marker))
                ids = config.get('case_ids', {})
                if not ids:
                    continue
                query = isinstance(ids, dict)
                title = ('复杂澄清 · 字段约定对照' if config.get('guidance') else '复杂业务需求澄清') if config.get('kind')=='complex' else '查数与多轮追问' if query else ('知识对照 · 明确要求先检索' if config.get('guidance') else '知识对照 · 原版提示')
                if config.get('simulation'):
                    title = 'AI 模拟用户 · ' + title
                result.append({'id': folder.name, 'title': title, 'kind': config.get('kind') or ('query' if query else 'knowledge'),
                               'cases': len(ids), 'model': config.get('model', {}).get('model', '未记录'),
                               'frozen': (folder/'source-snapshot.zip').exists()})
            except (ValueError, OSError):
                continue
        def chronology(item):
            stamp=re.search(r'(20\d{6})(?:[-_](\d{6}))?',item['id'])
            return (stamp[1],stamp[2] or '',item['id']) if stamp else ('','',item['id'])
        return sorted(result, key=chronology, reverse=True)

    def catalog(self, folder):
        return self.fixture(folder, 'catalog.json', allow_current=True)

    def locate(self, batch, case):
        folder = self.batch_path(batch)
        if not re.fullmatch(r'[\w.-]+', case) or case in {'.', '..'}:
            raise FileNotFoundError('案例不存在')
        config = read_json(self.safe(folder/'batch.json'))
        if case not in config.get('case_ids', {}):
            raise FileNotFoundError('案例不存在')
        query = isinstance(config['case_ids'], dict)
        if query:
            source = self.fixture(folder, 'simple_query_cases.json')
            rubric = self.fixture(folder, 'simple_query_rubrics.private.json').get('cases', {}).get(case, {})
            spec = next((c for c in source.get('cases', []) if c['id'] == case), {'id': case, 'title': case, 'turns': []})
            paths = folder.glob(case+'-turn-*.json')
            records = [read_json(self.safe(p)) for p in paths if re.fullmatch(re.escape(case)+r'-turn-\d+\.json', p.name)]
        else:
            directory = self.safe(folder/case)
            session = read_json(self.safe(directory/'session.json'))
            spec = session.get('case', {'id': case, 'title': case})
            rubric = self.fixture(folder, 'rubrics.private.json').get('cases', {}).get(case, {})
            records = [read_json(self.safe(p)) for p in sorted(directory.glob('turn-*.json')) if re.fullmatch(r'turn-\d+\.json', p.name)]
        records.sort(key=lambda r: r.get('turn', r.get('turn_number', 0)))
        return folder, config, query, spec, rubric, records

    def case(self, batch, case):
        folder = self.batch_path(batch)
        config = read_json(self.safe(folder/'batch.json'))
        if config.get('kind') == 'complex':
            from .complex_adapter import case_payload
            return case_payload(self, folder, config, case)
        folder, config, query, spec, rubric, records = self.locate(batch, case)
        turns, counts = [], defaultdict(int)
        adaptive=bool(config.get('simulation'))
        for index, record in enumerate(records):
            number = record.get('turn', record.get('turn_number', index+1))
            if query:
                # trace字段仅作为实验目录内定位参考，不允许读取任意本地路径。
                path = Path(record.get('trace', '')).with_suffix('.jsonl')
                path = self.safe(path if path.is_absolute() else self.project/path)
            else:
                path = self.safe(folder/case/'trace.jsonl')
            events = read_events(path)
            run_ids = list(dict.fromkeys(e.get('run_id') for e in events if e.get('run_id')))
            offset = counts[str(path)]; counts[str(path)] += 1
            selected_run = record.get('run_id') or (run_ids[offset] if offset < len(run_ids) else None)
            current = [e for e in events if selected_run and e.get('run_id') == selected_run]
            inspection = next((e for e in reversed(current) if e['kind'] == 'experiment_inspection'), {})
            # 无当轮inspection时不读取上次checkpoint来伪造本轮状态。
            actual = inspection if query else record
            proposal = actual.get('resolver_result', {})
            validation = actual.get('validation', {})
            submissions = actual.get('model_submissions', []) or [e['inputs'] for e in current if e['kind']=='span_start' and e['name']=='finish_resolution']
            submissions = [s.get('arguments', s) for s in submissions]
            if query:
                review = record.get('review', {})
                expected = (rubric.get('turns', [])[index] if index < len(rubric.get('turns', [])) else {})
                question, answer = record.get('question', ''), record.get('answer', '')
                audit = read_json(self.safe(folder/f'{case}-turn-{number}-audit.json'))
            else:
                review = read_json(self.safe(folder/case/f'review-{number}.json'))
                expected = {'expected_outcome': rubric.get('first_decision') if index == 0 else 'ready',
                            'expected_tasks': rubric.get('expected_tasks', []) if index > 0 or rubric.get('first_decision') == 'ready' else [],
                            'must_ask': rubric.get('question_topics', []) if index == 0 else []}
                messages = actual.get('actual_input', {}).get('messages', [])
                question = next((m.get('content', '') for m in reversed(messages) if m.get('role') in {'human','user'}), spec.get('question', ''))
                answer = proposal.get('question') or '本实验在任务形成后停止，没有生成业务回答。'
                audit = {}
            if adaptive:
                expected={}
                question=record.get('question',question)
                answer=record.get('answer',answer)
            findings = self.findings(query, review, expected, proposal, validation, audit)
            outcome = proposal.get('outcome')
            if query:
                status = 'failed' if review.get('grade') == 'failed' else ('clarify' if outcome == 'clarify' else 'passed' if review.get('grade') == 'task_matched' else 'pending')
            else:
                matches = outcome == expected.get('expected_outcome')
                if outcome == 'ready':
                    matches = matches and validation.get('accepted', False) and review.get('exact_task_match') is True and review.get('required_knowledge_cited', False)
                status = 'pending' if not rubric else ('failed' if not matches else ('clarify' if outcome == 'clarify' else 'pending'))
                # 结构化clarify仍可能问错；ready结构匹配后须已有明确审阅，才标通过。
                if review.get('final_grade') == 'failed':
                    status = 'failed'
                elif review.get('final_grade') == 'passed' and matches:
                    status = 'clarify' if outcome == 'clarify' else 'passed'
            if adaptive:
                status=('failed' if record.get('status')=='execution_error' or review.get('grade')=='failed' else
                        review['grade'] if review.get('grade') in {'passed','clarify'} else 'pending')
            turns.append({'number': number, 'question': question, 'answer': answer, 'status': status,
                          'runtime_status': record.get('status'), 'proposal': proposal,
                          'submissions': submissions, 'validation': validation, 'review': review,
                          'expected': expected, 'findings': findings, 'audit': audit,
                          'actual_tasks': validation.get('normalized_tasks', []),
                          'queries': record.get('queries', []), 'usage': summarize(current),
                          'steps': self.steps(current), 'run_id': selected_run,
                          'event_count': len(current), '_events': current, '_path': str(path),
                          'input_origin':record.get('input_origin'),'simulated_user':record.get('simulated_user')})
        planned = len(spec.get('turns', [])) if query else 1 + bool(rubric.get('fixed_reply'))
        if not turns:
            status = 'not_run'
        elif any(t['status']=='failed' for t in turns):
            status = 'failed'
        elif len(turns)<planned:
            status = 'incomplete'
        elif all(t['status'] in {'passed','clarify'} for t in turns):
            status = 'passed'
        else:
            status = 'pending'
        skipped = [{'number': i+1, 'question': t['user_message']} for i,t in enumerate(spec.get('turns', [])) if i>=len(turns)] if query else ([{'number': 2, 'question': rubric['fixed_reply']}] if len(turns)==1 and rubric.get('fixed_reply') else [])
        all_events = [e for t in turns for e in t['_events']]
        simulation=self.simulation(folder,case,config)
        if adaptive:
            skipped=[]
            status=('failed' if any(t['status']=='failed' for t in turns) else
                    'passed' if simulation.get('finished') and turns and all(t['status'] in {'passed','clarify'} for t in turns) else
                    'pending' if simulation.get('finished') else 'incomplete')
        data = {'batch': batch, 'id': case, 'title': spec.get('title', case), 'category': spec.get('category','业务知识对照'),
                'kind': config.get('kind') or ('query' if query else 'knowledge'), 'status': status, 'planned_turns': planned,
                'turns': turns, 'skipped': skipped, 'history': spec.get('history', []), 'usage': summarize(all_events),
                'catalog': self.catalog(folder), 'frozen': bool(rubric),
                'guidance': config.get('guidance'), 'knowledge_profile': spec.get('knowledge_profile'),
                'model': config.get('model'), 'simulation':simulation,
                'review_note': '结构化评审与实际执行分别呈现；澄清问句仍应人工核对。'}
        if adaptive:
            data['assistant_usage']=data['usage']
            data['usage']=add([data['assistant_usage'],simulation['user_usage']])
        return data

    def simulation(self,folder,case,config):
        if not config.get('simulation'):
            return {}
        session=read_json(self.safe(folder/'simulated-users'/case/'session.json'))
        events=[e for path in (folder/'simulated-users'/case).glob('after-*/trace.jsonl')
                for e in read_events(self.safe(path))]
        return {'protocol':config['simulation']['protocol'],'finished':session.get('finished',False),
                'stop_reason':session.get('stop_reason'),'last_user_decision':session.get('last_user_decision'),
                'user_usage':summarize(events),
                'grading':config['simulation']['grading'],'capability_policy':config['simulation']['capability_policy']}

    @staticmethod
    def findings(query, review, expected, proposal, validation, audit):
        notes = []
        if audit:
            notes.append({'type': 'audit', 'text': audit.get('review_artifact_correction') or audit.get('first_cause') or audit.get('original_result', '本轮有补充审计'), 'data': audit})
        # 有明确更正时保留旧差异在原记录详情，不继续显示已经被推翻的漏指标诊断。
        if not audit.get('review_artifact_correction'):
            for d in review.get('mismatches', []):
                notes.append({'type':'difference','text':'预期与实际条件不同','data':d})
        for error in validation.get('errors', []):
            notes.append({'type':'validation','text':error})
        if expected.get('expected_outcome') and proposal.get('outcome') and proposal['outcome'] != expected.get('expected_outcome'):
            notes.append({'type':'decision','text':f"应提交 {expected.get('expected_outcome')}，实际为 {proposal['outcome']}"})
        if not query and review.get('exact_task_match') is False and proposal.get('outcome')=='ready':
            notes.append({'type':'difference','text':'实际任务与标准任务不同，请对照下方条件表。'})
        if not query and review.get('required_knowledge_cited') is False:
            notes.append({'type':'knowledge','text':'没有引用本场景要求的业务知识记录。'})
        if not query and review.get('final_grade') == 'failed' and (review.get('human_review') or {}).get('notes'):
            notes.append({'type':'review','text':review['human_review']['notes']})
        return notes

    @staticmethod
    def steps(events):
        ends = {e['span_id']:e for e in events if e['kind']=='span_end'}
        result=[]; calls=[]
        for e in events:
            if e['kind']=='model_response':
                calls.extend(e.get('tool_calls', []))
            if e['kind']=='span_start':
                if e.get('category')=='graph':
                    continue
                end=ends.get(e['span_id'], {})
                role=CATEGORIES.get(e.get('category'), '步骤')
                if e.get('category')=='tool':
                    role='模型调用工具' if any(c.get('name')==e['name'] and c.get('args')==e.get('inputs') for c in calls) else '程序调用工具'
                result.append({'id':e['span_id'],'seq':e['seq'],'end_seq':end.get('seq'),
                               'name':e['name'],'label':LABELS.get(e['name'],e['name']), 'kind':e.get('category'),
                               'role':role,'parent':e.get('parent_span_id'),'status':end.get('status','incomplete'),
                               'elapsed_ms':end.get('elapsed_ms')})
            elif e['kind'] in {'experiment_inspection','experiment_boundary','experiment_error','model_error'}:
                result.append({'id':'event-'+str(e['seq']),'seq':e['seq'],'end_seq':e['seq'],
                               'name':e['name'],'label':LABELS.get(e['name'],e['name']), 'kind':'validation',
                               'role':'程序检查','parent':e.get('parent_span_id'),
                               'status':'error' if 'error' in e['kind'] or e.get('validation',{}).get('errors') else 'ok'})
        return result

    def detail(self, batch, case, turn, node, cutoff=None):
        data=self.case(batch,case)
        current=next((t for t in data['turns'] if t['number']==turn),None)
        if current is None:
            raise FileNotFoundError('轮次不存在')
        events=current['_events']
        if node.startswith('event-'):
            event=next((e for e in events if str(e['seq'])==node[6:] and (cutoff is None or e['seq']<=cutoff)),None)
            if event is None:
                raise FileNotFoundError('事件尚未发生')
            return {'input':None,'output':event,'events':[],'finished':True}
        return step_payload(events,node,cutoff)

    def overview(self, batch):
        folder=self.batch_path(batch); config=read_json(self.safe(folder/'batch.json'))
        items=[]
        for case in config['case_ids']:
            data=self.case(batch,case)
            items.append({k:data[k] for k in ['id','title','category','status','planned_turns','usage']}
                         | {'actual_turns':len(data['turns']), 'first_question': data['turns'][0]['question'] if data['turns'] else ''})
        return {'batch':batch, 'cases':items}


def public_case(data):
    from .timeline import project_timeline
    return {**data, 'turns': [
        {**{k: v for k, v in t.items() if not k.startswith('_')},
         'timeline': project_timeline(t['_events'], t['steps'], t['answer'])}
        for t in data['turns']
    ]}
