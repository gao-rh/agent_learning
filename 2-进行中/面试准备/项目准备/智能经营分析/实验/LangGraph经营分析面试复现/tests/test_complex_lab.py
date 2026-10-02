"""校准装置，不将替身模型的结果算作实模效果。"""
from copy import deepcopy
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from business_analysis_repro.complex_lab import runtime
from business_analysis_repro.complex_lab.contract import Plan, validate
from business_analysis_repro.complex_lab.knowledge import FIXTURES, ComplexKnowledge
from business_analysis_repro.complex_lab.review import evaluate


@pytest.fixture
def knowledge():
    k=ComplexKnowledge(); tools=k.tools()
    for mid in k.metrics:tools['get_metric_definition'](metric_id=mid)
    for r in k.records:tools['search_business_knowledge'](query=r['title'])
    return k


@pytest.fixture
def goldens():return runtime.read(FIXTURES/'goldens.private.json')


@pytest.mark.parametrize('case,n',[('C01',1),('C01',2),('C02',1),('C02',2),('C02',3),('C03',1),('C04',1),('C04',2)])
def test_complete_human_plans_are_expressible(case,n,goldens,knowledge):
    p=Plan.model_validate(goldens[case][n-1]); result=validate(p,knowledge,n)
    assert result['accepted'],result['errors']
    record={'case_id':case,'turn_number':n,'status':'waiting_review','resolver_result':p.model_dump(),'validation':result}
    review=evaluate(case,record)
    assert review['grade']=='pending_human_review',review['mismatches']


def test_newest_source_does_not_override_history(goldens,knowledge):
    bad=deepcopy(goldens['C04'][1]);bad['tasks'][0]['definition_version']='v2'
    p=Plan.model_validate(bad)
    r=evaluate('C04',{'turn_number':2,'status':'waiting_review','resolver_result':p.model_dump(),'validation':validate(p,knowledge,2)})
    assert any(not c['passed'] and '历史6月' in c['label'] for c in r['checks'])


def test_public_validation_cannot_fill_missing_user_conditions(goldens,knowledge):
    bad=deepcopy(goldens['C03'][0]);bad['tasks'][0]['filters'].pop('province')
    p=Plan.model_validate(bad);v=validate(p,knowledge,1)
    assert v['accepted']  # 没有业务gold的准入不能知道用户指定过两省。
    assert 'province' not in v['normalized_tasks'][0]['filters']
    review=evaluate('C03',{'turn_number':1,'status':'waiting_review','resolver_result':p.model_dump(),'validation':v})
    assert review['grade']=='failed'


def test_source_and_capability_are_not_guessed(goldens,knowledge):
    p=Plan.model_validate(goldens['C01'][1]);p.knowledge_refs.append('fake-source')
    p.tasks[0].metric_id='cx_timely_merchant'
    errors=validate(p,knowledge,2)['errors']
    assert any('未实际读取' in e for e in errors) and any('明确不可用' in e for e in errors)


def test_required_rule_and_period_fail_without_correction(goldens,knowledge):
    p=Plan.model_validate(goldens['C03'][0]);p.tasks[0].predicates=[];p.tasks[0].period.end='2026-07-01'
    errors=validate(p,knowledge,1)['errors']
    assert any('必选规则' in e for e in errors) and any('倒置' in e for e in errors)


def test_original_requirements_cannot_disappear_after_accepting_alternative(goldens,knowledge):
    p=Plan.model_validate(goldens['C01'][1]);p.requirements=[r for r in p.requirements if r.status!='gap']
    review=evaluate('C01',{'turn_number':2,'status':'waiting_review','resolver_result':p.model_dump(),'validation':validate(p,knowledge,2)})
    assert any(not c['passed'] and '七类' in c['label'] for c in review['checks'])


def test_cancelled_requirement_has_no_active_task(goldens,knowledge):
    p=Plan.model_validate(goldens['C03'][0]);p.requirements[0].status='cancelled'
    assert any('不可执行' in e for e in validate(p,knowledge,1)['errors'])


def test_fixed_runtime_records_real_messages_and_does_not_read_gold(tmp_path,monkeypatch):
    monkeypatch.setattr(runtime,'configuration',lambda:{'model':'fake'})
    directory=tmp_path/'batch';runtime.prepare(directory)
    captured=[]
    class Client:
        @property
        def bound(self):return self
        def bind_tools(self,*args,**kwargs):return self
        def invoke(self,messages):
            captured.append([m.model_dump() for m in messages])
            return AIMessage(content='没有结构化提交的回复',usage_metadata={'input_tokens':100,'output_tokens':5,'total_tokens':105})
    factory=lambda trace,max_calls:SimpleNamespace(model_name='fake',client=Client())
    result=runtime.run_turn(directory,'C03',model_factory=factory)
    assert result['usage']['total_tokens']==105*8
    assert result['usage']['calls']==len(captured)==8
    assert result['status']=='execution_error' and result['outcome'] is None
    assert '没有提交复杂计划' in captured[1][-1]['content']
    sent=str(captured)
    assert 'goldens' not in sent and 'final_metrics' not in sent and 'expected_tasks' not in sent
    with pytest.raises(ValueError):runtime.run_turn(directory,'C03',model_factory=factory)
