"""查看器只投影证据：隔离轮次、冻结标准、回放边界和只读 HTTP。"""
import hashlib
import json
import threading
import zipfile
from collections import Counter
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from business_analysis_repro.case_viewer.__main__ import make_handler
from business_analysis_repro.case_viewer.repository import Repository, public_case

ROOT = Path(__file__).resolve().parents[1] / '.runs'
BATCH = 'query-suite-20260930'


@pytest.fixture
def repo():
    if not (ROOT / BATCH / 'batch.json').exists():
        pytest.skip('实跑记录只保存在本地，不进入 Git')
    return Repository(ROOT)


def test_latest_scenarios_follow_reviews_not_runtime_success(repo):
    cases = repo.overview(BATCH)['cases']
    assert Counter(c['status'] for c in cases) == {'passed': 8, 'failed': 4}
    case = repo.case(BATCH, 'Q11')
    assert case['turns'][1]['runtime_status'] == 'completed'
    assert case['status'] == 'failed'  # SQL 执行完成仍然可能查错。
    assert case['turns'][1]['expected']['expected_tasks'][0]['group_by'] == ['merchant_age']
    assert case['turns'][1]['actual_tasks'][0]['group_by'] == []


def test_resume_isolated_by_run_and_usage_not_counted_twice(repo):
    case = repo.case(BATCH, 'Q09')
    first, second = case['turns']
    assert first['run_id'] != second['run_id']
    assert first['queries'] == [] and len(second['queries']) == 2
    assert first['proposal']['outcome'] == 'clarify'
    assert second['proposal']['outcome'] == 'ready'
    assert max(e['seq'] for e in first['_events']) < min(e['seq'] for e in second['_events'])
    assert case['usage']['total_tokens'] == 40821
    assert first['usage']['total_tokens'] + second['usage']['total_tokens'] == 40821
    assert all('_events' not in t and '_path' not in t for t in public_case(case)['turns'])


def test_replay_hides_output_and_future_model_response(repo):
    case = repo.case(BATCH, 'Q11')
    step = next(s for s in case['turns'][1]['steps'] if s['kind'] == 'model')
    args = (BATCH, 'Q11', 2, step['id'])
    with pytest.raises(FileNotFoundError):
        repo.detail(*args, cutoff=step['seq'] - 1)
    initial = repo.detail(*args, cutoff=step['seq'])
    assert initial['output'] is None and initial['finished'] is False
    assert not any(e['kind'] == 'model_response' for e in initial['events'])
    assert repo.detail(*args)['finished'] is True


def test_corrected_audit_and_knowledge_results_keep_their_boundaries(repo):
    old = repo.case('simple-query-smoke-20260929-a', 'Q09')['turns'][1]
    assert old['audit']['review_artifact_correction']
    assert not any(f['type'] == 'difference' for f in old['findings'])
    assert old['status'] == 'failed'
    guided = repo.case('knowledge-guided-20260930', 'alias_unknown')
    assert [t['proposal']['outcome'] for t in guided['turns']] == ['clarify', 'ready']
    assert guided['status'] == 'failed'
    assert guided['usage']['total_tokens'] == 23574
    defined = repo.case('knowledge-contrast-20260930', 'alias_defined')
    assert defined['knowledge_profile'] == 'with_definition'
    assert defined['status'] == 'failed'
    assert not any(s['name'] == 'search_business_knowledge' and s['role'] == '模型调用工具' for s in defined['turns'][0]['steps'])


def test_reads_do_not_rewrite_original_evidence(repo):
    paths = [ROOT / BATCH / 'Q11-turn-2.json', ROOT / BATCH / 'source-snapshot.zip']
    before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
    repo.overview(BATCH)
    repo.case(BATCH, 'Q11')
    assert [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths] == before


def test_no_snapshot_never_uses_current_gold(tmp_path):
    runs = tmp_path / '.runs'
    batch = runs / 'example'
    batch.mkdir(parents=True)
    (batch / 'batch.json').write_text(json.dumps({'case_ids': {'Q01': 'fake'}}))
    current = tmp_path / 'business_analysis_repro/clarification_lab/fixtures'
    current.mkdir(parents=True)
    (current / 'simple_query_rubrics.private.json').write_text('{"cases":{"Q01":{"new_gold":true}}}')
    repository = Repository(runs)
    assert repository.fixture(batch, 'simple_query_rubrics.private.json') == {}
    with zipfile.ZipFile(batch / 'source-snapshot.zip', 'w') as z:
        z.writestr('clarification_lab/fixtures/simple_query_rubrics.private.json', '{"frozen":true}')
    assert repository.fixture(batch, 'simple_query_rubrics.private.json') == {'frozen': True}


@pytest.mark.parametrize('decision,grade,status', [('clarify','failed','failed'), ('ready','passed','passed')])
def test_knowledge_semantic_review_is_distinct_from_structural_decision(tmp_path, decision, grade, status):
    batch = tmp_path / 'reviewed'
    case = batch / 'example'
    case.mkdir(parents=True)
    (batch / 'batch.json').write_text(json.dumps({'kind':'knowledge', 'case_ids':['example']}))
    (case / 'session.json').write_text(json.dumps({'case':{'id':'example', 'question':'原问题'}}))
    (case / 'turn-1.json').write_text(json.dumps({'turn_number':1,
        'resolver_result':{'outcome':decision}, 'validation':{'accepted':True}}))
    (case / 'review-1.json').write_text(json.dumps({'final_grade':grade,
        'exact_task_match':True, 'required_knowledge_cited':True,
        'human_review':{'notes':'问句误解原词' if grade == 'failed' else '任务审阅通过'}}))
    with zipfile.ZipFile(batch / 'source-snapshot.zip', 'w') as archive:
        archive.writestr('clarification_lab/fixtures/rubrics.private.json', json.dumps({'cases':{
            'example':{'first_decision':decision, 'expected_tasks':[], 'fixed_reply':''}}}))
    record = Repository(tmp_path).case('reviewed','example')
    assert record['turns'][0]['status'] == record['status'] == status
    if grade == 'failed':
        assert any(f['text'] == '问句误解原词' for f in record['turns'][0]['findings'])


def test_traversal_and_symlinks_cannot_read_outside_runs(tmp_path):
    runs = tmp_path / '.runs'
    batch = runs / 'example'
    batch.mkdir(parents=True)
    outside = tmp_path / 'private.json'
    outside.write_text('{"case_ids":{"Q01":"fake"}}')
    (batch / 'batch.json').symlink_to(outside)
    repository = Repository(runs)
    assert repository.batches() == []
    for name in ('../private.json', 'example', '/tmp'):
        with pytest.raises(FileNotFoundError):
            repository.batch_path(name)


def test_http_deep_links_and_read_only_api(repo):
    server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(repo))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f'http://127.0.0.1:{server.server_port}'
    try:
        with urlopen(origin + f'/case/{BATCH}/Q11?turn=2') as response:
            html = response.read().decode()
            assert '完整案例' in html and 'case-sidebar' in html
            assert response.headers['X-Content-Type-Options'] == 'nosniff'
        with urlopen(origin + f'/api/case?batch={BATCH}&case=Q11') as response:
            data = json.load(response)
            assert len(data['turns']) == 2
            assert any(item['name'] == 'query_local_simulation'
                       for item in data['turns'][1]['timeline'] if item['kind'] == 'tool')
        with urlopen(origin + f'/api/raw?batch={BATCH}&case=Q09&turn=1') as response:
            events = [json.loads(line) for line in response.read().decode().splitlines()]
            assert len({e['run_id'] for e in events}) == 1
        with pytest.raises(HTTPError) as error:
            urlopen(Request(origin + '/api/run', data=b'{}', method='POST'))
        assert error.value.code == 405
        with pytest.raises(HTTPError) as error:
            urlopen(origin + '/api/case?batch=..&case=Q11')
        assert error.value.code == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_complex_case_preserves_requirements_revisions_and_review_audit(repo):
    root = ROOT / 'complex-clarification-20260930'
    if not root.exists():
        pytest.skip('复杂实跑记录仅在本地')
    c1=repo.case(root.name,'C01')
    assert c1['status']=='failed' and len(c1['skipped'])==1
    assert any(r['status']=='gap' and r['views']==[] for r in c1['turns'][0]['requirements'])
    c2=repo.case(root.name,'C02')
    assert c2['turns'][0]['run_id']!=c2['turns'][1]['run_id']
    assert c2['turns'][1]['actual_tasks'][0]['period']['start']=='2026-08-17'
    c4=repo.case(root.name,'C04')
    assert c4['status']=='passed'
    assert c4['turns'][1]['review']['automatic_grade']=='failed'
    assert c4['turns'][1]['review']['audit_corrections']
    assert len(c4['turns'][1]['actual_tasks'])==4


def test_complex_audit_sidecars_are_not_conversation_turns(tmp_path):
    batch = tmp_path / 'runs' / 'complex-example'
    case = batch / 'C01'
    case.mkdir(parents=True)
    config = {'kind': 'complex', 'case_ids': ['C01'], 'model': {'model': 'offline'}}
    (batch / 'batch.json').write_text(json.dumps(config))
    with zipfile.ZipFile(batch / 'source-snapshot.zip', 'w') as archive:
        archive.writestr('complex_lab/fixtures/cases.json', json.dumps({'cases': [{
            'id': 'C01', 'title': '待确认任务', 'category': '复杂需求',
            'question': '先确认范围', 'planned_turns': 2,
        }]}))
        archive.writestr('complex_lab/fixtures/rubrics.private.json', json.dumps({'cases': {
            'C01': {'outcomes': ['clarify', 'ready'], 'question_topics': ['范围'],
                    'replies': ['按已问范围处理']},
        }}))
        archive.writestr('complex_lab/fixtures/catalog.json', '{}')
    record = {'turn_number': 1, 'run_id': 'actual-first-run', 'status': 'waiting_review',
              'question': '先确认范围', 'answer': '请补充范围',
              'resolver_result': {'outcome': 'clarify'},
              'validation': {'accepted': True}, 'model_submissions': []}
    (case / 'turn-1.json').write_text(json.dumps(record))
    (case / 'review-1.json').write_text(json.dumps({'grade': 'clarify', 'checks': []}))
    audit = case / 'turn-1-audit.json'
    audit.write_text('{"original_unchanged": true}')
    (case / 'turn-pending.json').write_text('{"not_a_turn": true}')
    original = audit.read_bytes()
    result = Repository(batch.parent).case(batch.name, 'C01')
    assert len(result['turns']) == 1 and result['turns'][0]['number'] == 1
    assert result['status'] == 'incomplete' and len(result['skipped']) == 1
    assert audit.read_bytes() == original
