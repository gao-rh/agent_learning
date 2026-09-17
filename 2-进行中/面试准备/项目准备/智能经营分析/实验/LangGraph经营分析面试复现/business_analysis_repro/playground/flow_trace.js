// 只读 Trace 可视化：回放改变浏览器的游标，不重跑 LangGraph、不调用模型。
const $=s=>document.querySelector(s);
// 回放说明会随当前并行节点换行；让详情面板避开实际高度，避免被顶部控制条遮住。
new ResizeObserver(([entry])=>{
  document.documentElement.style.setProperty('--controls-height',entry.target.getBoundingClientRect().height+'px');
}).observe($('.controls'));
const parts=location.pathname.split('/').filter(Boolean),cid=parts[1],tid=parts[2];
const base=`id=${cid}&task_id=${tid}`;
const el=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;};
const statusNames={superseded:'已按新要求调整',cancelled:'已停止',cancelling:'正在停止',review_failed:'复核未通过，准备重写', ok:'完成',completed:'已完成',running:'执行中',failed:'失败',error:'异常',partial:'部分完成',waiting_user:'等待补充',interrupted:'等待补充',incomplete:'记录中断',future:'尚未到达'};
const kindNames={control:'主 Agent 消息处理',context:'上下文管理',node:'LangGraph 节点',tool:'工具 / Python 函数',model:'Kimi 模型',graph:'父图'};
let data,run,byId=new Map(),children=new Map(),selected=null,cursor=0,following=true,playing=null,detailTicket=0,refreshing=false;
const duration=ms=>ms==null?'未结束':ms<1000?`${ms.toFixed(1)} ms`:`${(ms/1000).toFixed(2)} 秒`;
function cutoff(){return cursor===0?run.steps[0]?.seq-1:run.steps[cursor-1]?.seq||run.last_seq;}
function nodeState(n){const seq=cutoff();return n.start_seq>seq?'future':n.end_seq!=null&&n.end_seq<=seq?n.status:'running';}
function nowMillis(){return cursor?run.steps[cursor-1]?.ms||0:0;}
async function get(url){const response=await fetch(url);if(!response.ok)throw Error('暂时无法读取执行记录');return response.json();}
function stop(){if(playing)clearInterval(playing);playing=null;$('#play').textContent='逐步回放';}

function nodeButton(n){
  const b=el('button','node');b.dataset.id=n.id;b.type='button';b.setAttribute('aria-pressed',String(n.id===selected));
  b.append(el('span','title',n.label),el('span','subtitle',n.period||kindNames[n.kind]||n.kind),el('span','state',''));
  b.onclick=()=>selectNode(n.id);return b;
}
function connector(text=''){const d=el('div','connector','↓');if(text)d.append(el('small','',text));return d;}
function subtree(parent,container){
  for(const child of children.get(parent)||[]){
    container.append(connector(),nodeButton(child));
    if(children.has(child.id)){const inner=el('div','inner');subtree(child.id,inner);container.append(inner);}
  }
}
function drawDiagram(){
  const flow=$('#flow');flow.replaceChildren();
  for(const [index,phase] of run.phases.entries()){
    if(index)flow.append(connector(phase.kind==='parallel'?'父图分发':'返回父图，继续执行'));
    if(phase.kind==='parallel'){
      flow.append(el('p','parallel-label',`${phase.ids.length} 个独立指标分支 · 并发名额上限 5`));
      const grid=el('div','branches');grid.style.setProperty('--cols',Math.min(4,phase.ids.length));
      for(const id of phase.ids){
        const n=byId.get(id),branch=el('div','branch');
        branch.append(el('p','metric',n.metric_name||'指标任务'),nodeButton(n));
        subtree(id,branch);grid.append(branch);
      }
      flow.append(grid);
    }else{
      const n=byId.get(phase.ids[0]),stage=el('div','stage');stage.append(nodeButton(n));
      const calls=children.get(n.id)||[];
      if(calls.length){const d=el('details','children');d.append(el('summary','',`展开内部模型 / 工具调用（${calls.length} 次）`));const list=el('div','children-list');for(const child of calls)list.append(nodeButton(child));d.append(list);stage.append(d);}
      flow.append(stage);
    }
  }
  if(!run.phases.length)flow.append(el('p','muted','尚未记录到执行节点。'));
  drawTimeline();
}
function drawTimeline(){
  const box=$('#timeline');box.replaceChildren();
  const workers=run.nodes.filter(n=>n.name==='metric_worker');
  if(!workers.length){box.append(el('p','muted','这一轮尚无并行指标分支。'));return;}
  // 聚焦指标执行窗口；仍用统一比例，不给短分支人为画成同样长。
  const left=Math.min(...workers.map(n=>n.start_ms));
  const right=Math.max(...workers.map(n=>n.end_ms??run.duration_ms));
  const width=Math.max(right-left,1);
  const axis=el('div','axis');axis.append(el('span','',`相对本轮 +${(left/1000).toFixed(3)}s`),el('span','',`+${(right/1000).toFixed(3)}s`));box.append(axis);
  for(const n of workers){
    const row=el('div','time-row'),label=el('button','',n.metric_name||n.label);label.onclick=()=>selectNode(n.id);
    label.append(el('span','time-label',`${(n.start_ms/1000).toFixed(3)}s → ${n.end_ms==null?'未结束':(n.end_ms/1000).toFixed(3)+'s'}`));
    const track=el('div','bar-track'),bar=el('div','bar');bar.dataset.id=n.id;bar.dataset.left=left;bar.dataset.width=width;
    bar.style.left=((n.start_ms-left)/width*100)+'%';track.append(bar);row.append(label,track);box.append(row);
  }
}
function updateCursor(){
  cursor=Math.max(0,Math.min(cursor,run.steps.length));$('#cursor').max=run.steps.length;$('#cursor').value=cursor;
  $('#position').textContent=`${cursor} / ${run.steps.length}`;$('#back').disabled=cursor===0;$('#next').disabled=cursor===run.steps.length;
  const step=run.steps[cursor-1],active=run.nodes.filter(n=>n.kind==='node'&&nodeState(n)==='running');
  $('#now').textContent=step?`+${(step.ms/1000).toFixed(3)}s · ${step.kind==='span_start'?'进入':'离开'}「${byId.get(step.id)?.label||'父图'}」${active.length?' · 仍在执行的图节点：'+active.slice(0,5).map(n=>n.label+(n.metric_name?'（'+n.metric_name+'）':'')).join('、')+(active.length>5?' 等':''):''}`:'回到本轮开始之前';
  for(const b of document.querySelectorAll('.node[data-id]')){
    const n=byId.get(b.dataset.id),state=nodeState(n);b.dataset.state=state;b.setAttribute('aria-pressed',String(n.id===selected));
    b.querySelector('.state').textContent=(statusNames[state]||state)+(state==='future'?'':state==='running'?` · 已经过 ${duration(Math.max(0,nowMillis()-n.start_ms))}`:` · ${duration(n.elapsed_ms)}`);
  }
  for(const bar of document.querySelectorAll('.bar')){
    const n=byId.get(bar.dataset.id),state=nodeState(n);bar.hidden=state==='future';bar.classList.toggle('running',state==='running');
    const end=Math.min(n.end_ms??nowMillis(),nowMillis());bar.style.width=(Math.max(0,end-n.start_ms)/Number(bar.dataset.width)*100)+'%';
  }
  if(selected)showDetail();
}
function selectNode(id){selected=id;updateCursor();}
function followStep(){
  const step=run.steps[cursor-1];if(step)selected=step.id;updateCursor();
  // 内部模型被折叠时，定位到它可见的父节点；不展开整棵树打断主链。
  let n=byId.get(selected),target;
  while(n){target=document.querySelector('.node[data-id="'+n.id+'"]');if(target?.getClientRects().length)break;n=byId.get(n.parent);}
  if(target?.getClientRects().length){const rect=target.getBoundingClientRect();const top=$('.controls').getBoundingClientRect().height+16;if(rect.top<top||rect.bottom>innerHeight-24)target.scrollIntoView({block:'center',behavior:'instant'});}
}
function rawBlock(label,value){const d=el('details','raw');d.append(el('summary','',label),el('pre','',typeof value==='string'?value:JSON.stringify(value,null,2)));return d;}
async function showDetail(){
  const n=byId.get(selected);if(!n)return;const ticket=++detailTicket;const seq=cutoff(),state=nodeState(n);
  $('#node-title').textContent=n.label;$('#node-purpose').textContent=n.purpose;
  $('#node-meta').textContent=[n.metric_name,kindNames[n.kind],`状态：${statusNames[state]||state}`,n.period,`进入：+${(n.start_ms/1000).toFixed(3)} 秒`,state==='future'?'':state==='running'?'本时刻尚未返回输出':`耗时：${duration(n.elapsed_ms)}`].filter(Boolean).join('\n');
  const box=$('#node-detail');box.replaceChildren();
  if(state==='future'){box.append(el('p','muted','回放还没有走到这里，暂不展示输入输出。'));return;}
  if(n.result_brief&&n.end_seq<=seq)box.append(el('p','result-brief',n.result_brief));
  const calls=(children.get(n.id)||[]).filter(child=>child.start_seq<=seq);
  if(calls.length){box.append(el('p','event-title','它在内部调用了谁'));const list=el('div','children-list');for(const child of calls){const b=el('button','',child.label+(child.metric_name?' · '+child.metric_name:''));b.onclick=()=>selectNode(child.id);list.append(b);}box.append(list);}
  if(n.parent&&byId.has(n.parent)){const parent=el('button','',`↑ 返回调用方：${byId.get(n.parent).label}`);parent.onclick=()=>selectNode(n.parent);box.append(parent);}
  const content=el('div');box.append(content);
  try{
    const detail=await get(`/api/flow-node?${base}&span_id=${n.id}&seq=${seq}`);if(ticket!==detailTicket)return;
    content.append(rawBlock('实际输入',detail.input),rawBlock(detail.finished?'实际输出':'输出（本时刻尚未返回）',detail.output));
    if(detail.stream_text)content.append(rawBlock('已收到的流式正文（生成过程）',detail.stream_text));
    for(const event of detail.events){
      const names={inbox_received:'主 Agent 收到插入消息',inbox_applied:'主 Agent 的处理决定',query_reused:'复用已取得的数据',plan_revised:'调整当前任务范围',model_request:'模型实际上下文 / 请求',model_response:'模型返回与用量',model_error:'模型异常',plan:'拆解计划',job_status:'分支状态',answer_reset:'撤回未完成草稿',batch_summary:'各指标完整结果'};
      content.append(rawBlock(names[event.kind]||event.kind,event));
    }
    if(!detail.events.length&&n.kind==='model')content.append(el('p','muted','本时刻还没有收到模型请求或响应事件。'));
  }catch(e){if(ticket===detailTicket)content.append(el('p','muted',e.message));}
}
function chooseRun(id){
  stop();run=data.runs.find(r=>r.id===id)||data.runs.at(-1);byId=new Map(run.nodes.map(n=>[n.id,n]));children=new Map();
  for(const n of run.nodes){if(!children.has(n.parent))children.set(n.parent,[]);children.get(n.parent).push(n);}
  cursor=run.steps.length;following=true;selected=run.nodes.find(n=>n.name==='analysis_agent')?.id||run.nodes.find(n=>n.kind==='node')?.id;
  $('#question').textContent=run.question||'这轮日志没有记录原始问题';$('#status').textContent=statusNames[run.status]||run.status;
  const s=run.stats;$('#stats').textContent=`全程已记录：${s.branches} 个指标分支 · ${s.analysis} 次分析 Agent · ${s.queries} 次取数 · ${s.models} 次模型请求 · ${s.tokens.toLocaleString()} Tokens · ${duration(run.duration_ms)}`;
  const stopped=$('#stop-events');stopped.replaceChildren();
  for(const e of run.stop_events||[]){
    const name=e.kind==='cancel_requested'?'收到停止请求；当前调用返回后退出':e.kind==='execution_cancelled'?'图执行已停止；结果不再交付':e.status==='failed'?'查询取消接口失败；仍停止本地后续步骤':'已请求取消模拟查询';
    stopped.append(el('p','muted',`+${(e.ms/1000).toFixed(2)}秒 · ${name}${e.query_id?' · '+e.query_id:''}`));
  }
  for(const e of run.inbox_events||[]){
    const action={reply:'回复，原任务继续',continue:'吸收补充',revise:'调整范围',stop:'停止任务'}[e.decision.action]||e.decision.action;
    stopped.append(el('p','result-brief',`+${(e.ms/1000).toFixed(2)}秒 · 用户插入：${e.texts.join('；')}\n主 Agent（${action}）：${e.decision.reply}`));
  }
  drawDiagram();updateCursor();
}
async function refresh(first=false){
  if(refreshing||playing)return;refreshing=true;
  try{
    const next=await get('/api/flow?'+base);$('#connection').textContent='';
    const changed=!data||next.revision!==data.revision||next.runs.at(-1)?.active!==data.runs.at(-1)?.active;
    data=next;
    if(first||changed){
      const prior=run?.id,position=cursor,follow=following,selectedId=selected;
      $('#run').replaceChildren();data.runs.forEach((r,i)=>{const option=el('option','',`第 ${i+1} 轮 · ${r.resume?'用户补充后恢复':'开始执行'} · ${statusNames[r.status]||r.status}`);option.value=r.id;$('#run').append(option);});
      chooseRun(prior);$('#run').value=run.id;
      if(!first){following=follow;if(!follow)cursor=Math.min(position,run.steps.length);if(byId.has(selectedId))selected=selectedId;updateCursor();}
    }
    if(run.active)$('#connection').textContent='正在实时追踪，每 2 秒更新';
  }catch(e){$('#connection').textContent=e.message+'，稍后重试';}finally{refreshing=false;}
}
$('#run').onchange=e=>chooseRun(e.target.value);
$('#back').onclick=()=>{stop();following=false;cursor--;followStep();};
$('#next').onclick=()=>{stop();following=false;cursor++;followStep();};
$('#cursor').oninput=e=>{stop();following=false;cursor=Number(e.target.value);followStep();};
$('#end').onclick=()=>{stop();following=true;cursor=run.steps.length;updateCursor();refresh();};
$('#play').onclick=()=>{
  if(!run)return;if(playing){stop();return;}following=false;if(cursor===run.steps.length)cursor=0;updateCursor();$('#play').textContent='暂停回放';
  playing=setInterval(()=>{if(cursor>=run.steps.length){stop();return;}cursor++;followStep();},600);
};
$('#conversation').href='/?id='+cid;$('#raw').href=`/trace/${cid}/${tid}`;
refresh(true);setInterval(()=>{if(!data||data.runs.at(-1)?.active)refresh();},2000);
