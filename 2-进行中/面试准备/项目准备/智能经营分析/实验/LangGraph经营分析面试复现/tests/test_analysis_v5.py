"""用真实数据函数测试有限分析决策、范围守卫、预算和费用统计。无外部模型调用。"""
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from business_analysis_repro.main_agent.model import ModelFailure
from business_analysis_repro.playground.business_knowledge import (
    read_skill,
    search_business_knowledge,
)
from business_analysis_repro.playground.investigation import AnalysisAction, investigate, refinement
from business_analysis_repro.playground.parallel_trace import Trace
from business_analysis_repro.playground.streaming import public_event
from business_analysis_repro.playground.usage import capacity, collect, peaks, summarize


def task():
    return {'intent': 'analysis', 'metric_id': 'demo_metric_funnel_join',
            'metric': 'demo_metric_funnel_join', 'start_date': '2026-08-24',
            'end_date': '2026-08-30', 'reference_date': '2026-09-01', 'revision': 1,
            'group_by': ['channel_l1'], 'filters': {}}


def test_model_chooses_followup_from_observed_group_and_keeps_original_scope(tmp_path):
    seen = []

    class Model:
        def complete(self, stage, instruction, payload, schema):
            seen.append(payload)
            e = payload['evidence'][-1]
            if len(seen) == 1:
                top = e['largest_changes_not_contributions'][0]['dimensions']['channel_l1']
                return schema(action='compare', reason='核验变化最大的渠道来源构成',
                              hypothesis='可能与获客来源有关，待验证', group_by=['source'],
                              filters={'channel_l1': [top]}, evidence_ids=[e['evidence_id']])
            assert len(payload['evidence']) == 2
            assert payload['evidence'][-1]['scope']['filters']['channel_l1']
            return schema(action='finish', reason='已补查来源', finding='完成一层细分比较',
                          evidence_ids=[e['evidence_id']], open_questions=['需要活动记录'])

    original = task()
    result = investigate(original, Model(), Trace(tmp_path, 'adaptive'))
    assert original == task() and result['scope'] == original
    inv = result['investigation']
    assert inv['status'] == 'completed' and len(inv['followup_results']) == 1
    assert inv['steps'][0]['result_evidence_id'] == inv['evidence_ids'][1]
    events = [json.loads(x) for x in (tmp_path/'trace.jsonl').read_text().splitlines()]
    assert sum(e['kind'] == 'span_start' and e['name'] == 'analysis.query_agent' for e in events) == 4
    assert any(public_event(e) and public_event(e)['type'] == 'analysis' for e in events)


def test_reject_scope_widening_and_unsupported_dimension():
    original = task()
    original['filters'] = {'source': ['app']}
    # 按当前定义读取编码，而不是把测试里的猜测编码当业务事实。
    from business_analysis_repro.playground import catalog
    ids = catalog.METRICS[original['metric_id']]['dimensions']['source']
    original['filters'] = {'source': [ids[0]]}
    with pytest.raises(ValueError, match='扩大'):
        refinement(original, AnalysisAction(action='compare', reason='坏条件',
                   filters={'source': list(ids)}))
    with pytest.raises(Exception, match='不支持'):
        refinement(original, AnalysisAction(action='compare', reason='坏维度', group_by=['region']))


def test_repeated_action_is_rejected_without_requery_and_stops(tmp_path):
    class Model:
        def complete(self, stage, instruction, payload, schema):
            return schema(action='compare', reason='重复', group_by=['channel_l1'],
                          evidence_ids=[payload['evidence'][0]['evidence_id']])
    result = investigate(task(), Model(), Trace(tmp_path, 'repeat'))
    inv = result['investigation']
    assert inv['status'] == 'partial' and len(inv['steps']) == 3
    assert not inv['followup_results']
    assert all(s['status'] == 'rejected' for s in inv['steps'])


def test_atomic_model_budget_across_parallel_branches(tmp_path):
    trace = Trace(tmp_path, 'budget')
    trace.model_call_limit = 3

    def reserve(i):
        try:
            trace.event('model_request', 'decision', model='test-double')
            return 1
        except ModelFailure:
            return 0
    with ThreadPoolExecutor(max_workers=10) as pool:
        assert sum(pool.map(reserve, range(20))) == 3
    assert sum(e['kind'] == 'model_request' for e in trace.read()) == 3


def test_knowledge_topic_and_skill_are_local_and_grounded():
    found = search_business_knowledge('做一个渠道归因专题')['candidates'][0]
    assert found['id'] == 'kb_channel' and found['metrics']
    assert read_skill('demo_metric_fx_premium')['id'] == 'premium'
    assert '不是向量' in search_business_knowledge('保费')['method']


def event(seq, kind, run='a', **kwargs):
    return {'seq': seq, 'kind': kind, 'name': 'analysis-v5' if kind == 'execution_start' else 'model',
            'thread_id': 't', 'run_id': run, 'time': f'2026-09-09T00:00:{seq:02d}+00:00', **kwargs}


def test_usage_resumes_dedup_cache_and_unknown_not_free(tmp_path):
    folder = tmp_path/'playground'/'c'/'tasks'/'t'
    folder.mkdir(parents=True)
    usage = {'input_tokens': 1000, 'output_tokens': 100, 'total_tokens': 1100,
             'input_token_details': {'cache_read': 800}}
    events = [event(1, 'execution_start', input={'text': '分析渠道'}),
              event(2, 'model_request', model='kimi-k2.6'),
              event(3, 'model_response', usage=usage),
              event(4, 'state_snapshot', state={'status': 'waiting_user'}),
              event(5, 'execution_start', run='b', input={'text': '上周'}),
              event(6, 'model_request', run='b', model='kimi-k2.6'),
              event(7, 'state_snapshot', run='b', state={'status': 'failed'})]
    (folder/'trace.jsonl').write_text('\n'.join(json.dumps(e) for e in events))
    # 模拟复制的日志，不能重复计费。
    mirror = tmp_path/'copy'; mirror.mkdir()
    (mirror/'trace.jsonl').write_text((folder/'trace.jsonl').read_text())
    r = collect(tmp_path)
    assert r['total']['calls'] == 2 and r['total']['total_tokens'] == 1100
    assert r['total']['usage_unknown_calls'] == 1
    assert r['task_count'] == 1 and r['turn_count'] == 2
    assert r['tasks'][0]['rounds'] == 2
    assert summarize(events)['estimated_cny'] == .00488
    assert r['profiles'][0]['completed_samples'] == 0


def test_capacity_and_rolling_minute_boundaries():
    r = capacity()
    assert r['estimated_tpm'] == 261000 and r['estimated_rpm'] == 108
    assert r['daily_tokens'] == 5220000 and r['daily_model_calls'] == 2160
    events = [event(1, 'model_request'), event(2, 'model_request')]
    assert peaks(events)['observed_peak_rpm'] == 2
    events[1]['time'] = '2026-09-09T00:01:01+00:00'
    assert peaks(events)['observed_peak_rpm'] == 1
    with pytest.raises(ValueError):
        capacity(batch_seconds=0)


def test_dependent_followup_is_not_dispatched_as_independent_job():
    from business_analysis_repro.playground.parallel_agent import defer_dependent_jobs
    a = {'job_id': 'a', 'task': task()}
    b = {'job_id': 'b', 'task': {**task(), 'group_by': ['source']}}
    jobs, deferred = defer_dependent_jobs([a, b], '先按渠道比较，再根据结果补查一层获客来源')
    assert jobs == [a] and deferred == [b]
    jobs, deferred = defer_dependent_jobs([a, b], '按渠道和来源分别查询，给两张表')
    assert jobs == [a, b] and not deferred


def test_resolver_stops_after_three_empty_searches(tmp_path):
    from types import SimpleNamespace

    from langchain_core.messages import AIMessage, AIMessageChunk

    from business_analysis_repro.playground.parallel_model import ParallelModel

    class Client:
        calls = 0

        def bind_tools(self, tools):
            return self

        def stream(self, messages, **kwargs):
            response = self.invoke(messages)
            yield AIMessageChunk(content=response.content, tool_calls=response.tool_calls)

        def invoke(self, messages):
            self.calls += 1
            return AIMessage(content='', tool_calls=[{'name': 'search_metrics',
                'args': {'query': '不存在的指标星际XYZ'+str(self.calls)},
                'id': str(self.calls)}])

    client = Client()
    model = object.__new__(ParallelModel)
    model.client = SimpleNamespace(bound=client)
    model.trace = Trace(tmp_path, 'early-stop')
    model.max_calls, model.model_name = 40, 'test-double'
    result = model.resolve({'messages': [{'role': 'human', 'content': '渠道归因专题'}]})
    assert result.outcome == 'clarify' and client.calls == 3
    assert '外卖险加入商户数' in result.question
    assert any(e['kind'] == 'retrieval_stop' for e in model.trace.read())


def test_ignore_echoed_runtime_fields_but_reject_unknown_business_fields():
    from pydantic import ValidationError
    action = AnalysisAction.model_validate({'action': 'finish', 'reason': '结束',
        'status': 'in_progress', 'budget': {'remaining_followups': 999}})
    assert 'budget' not in action.model_dump() and 'status' not in action.model_dump()
    with pytest.raises(ValidationError):
        AnalysisAction.model_validate({'action': 'compare', 'reason': '错误拼写', 'filter': {}})


def test_one_followup_request_sets_one_followup_budget(tmp_path):
    seen = []
    class Model:
        def complete(self, stage, instruction, payload, schema):
            seen.append(payload['budget'])
            return schema(action='finish', reason='足够', evidence_ids=[payload['evidence'][0]['evidence_id']])
    spec = {**task(), 'analysis_goal': '根据结果选择一次获客来源补查'}
    investigate(spec, Model(), Trace(tmp_path, 'one-step'))
    assert seen[0]['remaining_followups'] == 1
