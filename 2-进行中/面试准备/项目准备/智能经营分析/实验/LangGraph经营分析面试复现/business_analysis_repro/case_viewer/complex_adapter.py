"""复杂语义实验的固定读取适配器；不导入实验运行器，也不调用模型。"""
import io
import json
import re
import zipfile

from ..playground.usage import add, summarize
from .repository import read_events, read_json
from .storage import read_bytes


def case_payload(repo, folder, config, case_id):
    if not re.fullmatch(r'[\w.-]+',case_id) or case_id not in config['case_ids']:
        raise FileNotFoundError('案例不存在')
    with zipfile.ZipFile(io.BytesIO(read_bytes(repo.safe(folder/'source-snapshot.zip')))) as z:
        def fixture(name):return json.loads(z.read('complex_lab/fixtures/'+name))
        spec=next(c for c in fixture('cases.json')['cases'] if c['id']==case_id)
        rubric=fixture('rubrics.private.json')['cases'][case_id]
        catalog=fixture('catalog.json')
    directory=repo.safe(folder/case_id)
    paths=sorted((p for p in directory.glob('turn-*.json')
                  if re.fullmatch(r'turn-\d+\.json', p.name)),
                 key=lambda p:int(re.search(r'turn-(\d+)',p.name)[1]))
    events=read_events(repo.safe(directory/'trace.jsonl'));turns=[]
    adaptive=bool(config.get('simulation'))
    for path in paths:
        record=read_json(repo.safe(path));number=record['turn_number']
        current=[e for e in events if e.get('run_id')==record.get('run_id')]
        review=read_json(repo.safe(directory/f'review-{number}.json'))
        proposal=record.get('resolver_result',{});validation=record.get('validation',{})
        status=review.get('grade','pending')
        if status=='pending_human_review':status='pending'
        if record.get('status')=='execution_error':status='failed'
        findings=[{'type':'check','text':c['label'],'data':c} for c in review.get('checks',[]) if not c['passed']]
        if (review.get('human_review') or {}).get('passed') is False:
            findings.append({'type':'human','text':review['human_review']['notes']})
        turns.append({'number':number,'question':record.get('question',''),'answer':record.get('answer') or '本轮未得到完整回复，请查看失败记录。',
            'status':status,'runtime_status':record.get('status'),'proposal':proposal,'validation':validation,
            'review':review,'expected':{} if adaptive else {'expected_outcome':rubric['outcomes'][number-1],'expected_tasks':[],
            'must_ask':rubric['question_topics'] if number==1 else []},'findings':findings,
            'input_origin':record.get('input_origin'),'simulated_user':record.get('simulated_user'),
            'submissions':[s.get('arguments',s) for s in record.get('model_submissions',[])],
            'actual_tasks':validation.get('normalized_tasks',[]),'queries':[],
            'requirements':proposal.get('requirements',[]),'checks':review.get('checks',[]),
            'usage':summarize(current),'steps':repo.steps(current),'run_id':record.get('run_id'),
            'event_count':len(current),'_events':current,'_path':str(directory/'trace.jsonl')})
    status=('not_run' if not turns else 'failed' if any(t['status']=='failed' for t in turns) else
            'incomplete' if len(turns)<spec['planned_turns'] else 'passed' if all(t['status'] in {'passed','clarify'} for t in turns) else 'pending')
    simulation=repo.simulation(folder,case_id,config)
    if adaptive:
        status=('failed' if any(t['status']=='failed' for t in turns) else
                'passed' if simulation.get('finished') and turns and all(t['status'] in {'passed','clarify'} for t in turns) else
                'pending' if simulation.get('finished') else 'incomplete')
    future=[] if adaptive else [spec['question'],*rubric.get('replies',[])]
    assistant_usage=summarize([e for t in turns for e in t['_events']])
    return {'batch':folder.name,'id':case_id,'title':spec['title'],'category':spec['category'],
        'kind':'complex','status':status,'planned_turns':spec['planned_turns'],'turns':turns,
        'skipped':[{'number':i+1,'question':q} for i,q in enumerate(future) if i>=len(turns)],
        'history':spec.get('history',[]),'usage':add([assistant_usage,simulation['user_usage']]) if adaptive else assistant_usage,
        'assistant_usage':assistant_usage if adaptive else None,
        'catalog':catalog,'frozen':True,'model':config['model'],'guidance':None,'simulation':simulation,
        'review_note':'复杂需求只确认计划，未运行SQL或归因；结构检查加记录审阅，不是独立裁判或生产准确率。'}
