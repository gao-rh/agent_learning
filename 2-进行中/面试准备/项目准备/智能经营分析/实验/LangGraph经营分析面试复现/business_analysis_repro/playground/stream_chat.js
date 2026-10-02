function chooseMetric(){const m=knowledge.metrics.find(x=>x.id===$('#metric').value);if(!m){for(const id of ['metricId','preset','aggregation','source','method'])$('#'+id).textContent='';$('#definition').textContent='没有匹配的指标，请换个名称或别名。';$('#dimensions').replaceChildren();return;}$('#metricId').textContent=m.id;$('#definition').textContent=m.definition;$('#preset').textContent=m.preset_text;$('#aggregation').textContent=m.aggregation==='ratio_of_sums'?'先汇总分子、分母，再计算比率或单均值':'期间日计数或金额累计';$('#dimensions').replaceChildren();for(const [id,ids]of Object.entries(m.dimensions)){const d=knowledge.dimensions[id];const block=document.createElement('div');block.className='dimension';const name=document.createElement('div');name.className='dimname';name.textContent=d.name;const tags=document.createElement('div');tags.className='enums';for(const v of d.values.filter(x=>ids.includes(x.id))){const tag=document.createElement('span');tag.className='tag';tag.textContent=v.name;tag.title=v.id;tags.append(tag)}const meaning=document.createElement('small');meaning.textContent=d.definition;block.append(name,tags,meaning);$('#dimensions').append(block)}$('#source').textContent='名称/口径参考：'+m.sources.map(id=>knowledge.sources.find(s=>s.id===id)?.title||id).join('、');$('#method').textContent='查询方式：'+(m.query.method==='sql'?'本地SQLite执行参数化SQL':'本地指标平台模拟函数')}
function filterMetrics(){const q=$('#search').value.toLowerCase();const old=$('#metric').value;$('#metric').replaceChildren();for(const m of knowledge.metrics.filter(m=>[m.name,...m.aliases].some(t=>t.toLowerCase().includes(q)))){const o=document.createElement('option');o.value=m.id;o.textContent=m.name;$('#metric').append(o)}if([...$('#metric').options].some(o=>o.value===old))$('#metric').value=old;chooseMetric()}

// POST只执行一次任务；EventSource独立订阅，断线重连不会再次调用模型。
const $ = s => document.querySelector(s);
let knowledge, busy = false, subscription = null, currentRequest = null, live = null;
let renderedRequest = null;
let renderedMessages = new Set();
const completedSeen = new Map();
const selectedId = new URLSearchParams(location.search).get('id');
const newId = () => crypto.randomUUID().replaceAll('-', '').slice(0, 16);
let cid = (/^[a-f0-9]{16}$/.test(selectedId || '') ? selectedId : null)
  || (/^[a-f0-9]{16}$/.test(localStorage.getItem('lg-playground-conversation') || '') ? localStorage.getItem('lg-playground-conversation') : newId());
localStorage.setItem('lg-playground-conversation', cid);
function persistChatView(){try{localStorage.setItem('lg-playground-draft:'+cid, $('#text').value);sessionStorage.setItem('lg-playground-scroll:'+cid,String($('#messages').scrollTop));}catch{}}
function restoreDraft(){try{$('#text').value=localStorage.getItem('lg-playground-draft:'+cid)||'';}catch{}}
window.addEventListener('pagehide',persistChatView);
restoreDraft();
const labels = {handle_inbox:'主 Agent 正在处理插入消息',reuse_evidence:'复用已取得的数据',analysis_decision:'分析 Agent 正在选择下一步',load_analysis_skill:'读取专题 Skill',analysis_followup:'分析 Agent 按假设补查',search_business_knowledge:'检索业务知识',query_agent:'取数 Agent 正在查询', analysis_agent:'分析 Agent 正在比较', 'analysis.query_agent':'分析 Agent 内部取数', validate_batch_reply:'核对回答与证据', metric_worker:'并行执行指标', gather_results:'汇总各指标', understand_request:'理解需求与搜索知识', search_metrics:'搜索指标候选', get_metric_definition:'读取精确指标定义', search_dimensions:'检查支持维度', search_dimension_values:'搜索枚举', finish_resolution:'检查查询条件', run_query:'执行模拟取数', run_analysis:'取数并计算对比', compose_batch:'Kimi 正在生成回答', compose_reply:'生成回答', validate_reply:'检查回答', validate_dates:'核对日期', resolve_batch:'理解需求与搜索知识', clarify:'等待补充'};
const intentName = intent => ({analysis:'分析 Agent', query:'取数 Agent', knowledge:'口径查询'})[intent] || '指标任务';
const node = (tag, className, text) => {const e=document.createElement(tag);if(className)e.className=className;if(text!==undefined)e.textContent=text;return e;};
const nearBottom = () => {const e=$('#messages');return e.scrollHeight-e.scrollTop-e.clientHeight<100;};
const toBottom = () => {const e=$('#messages');e.scrollTop=e.scrollHeight;};
function setBusy(value){busy=value;updateControlButtons();}
async function api(url, options){const r=await fetch(url,options);const v=await r.json();if(!r.ok)throw Error(v.error||'请求失败');return v;}
function traceLink(trace, text){const a=node('a','',text);a.href=trace;a.target='_blank';a.rel='noopener';return a;}

function renderCard(card, open=false){
  const d=node('details');d.open=open;d.dataset.jobId=card.job_id;
  const intent=card.intent || (card.has_baseline?'analysis':'query');
  d.append(node('summary','',`${card.name} · ${intentName(intent)} · ${card.status==='ok'?`完整结果 / ${(card.rows||[]).length} 行明细`:'未完成'}`));
  const facts=card.facts||{};
  // 打开指标先看到数值和表格，较长的口径/ID放到二级折叠中。
  d.append(node('div','card-facts',card.error ? card.error.message :
    '合计：'+(facts['结果']||'口径查询')+(card.has_baseline?' · 前期：'+facts['前期结果']+' · '+facts['变动']:'')+
    '\n维度顺序：'+((card.group_by||[]).join(' / ')||'总计')));
  if(card.rows?.length){
    const wrap=node('div','table-scroll'),table=node('table','result-table');
    const tr=table.createTHead().insertRow();
    for(const label of ['分组','本期',...(card.has_baseline?['前期','变化']:[])])tr.append(node('th','',label));
    const body=table.createTBody();
    for(const row of card.rows){const r=body.insertRow();for(const key of ['group','current',...(card.has_baseline?['baseline','change']:[])])r.insertCell().textContent=row[key];}
    wrap.append(table);d.append(wrap);
  }
  if(!card.error){const metadata=node('details');metadata.append(node('summary','','合计、口径与证据'),
    node('div','card-facts',Object.entries(facts).map(([k,v])=>k+'：'+v).join('\n')+'\n证据 ID：'+card.evidence_id));d.append(metadata);}
  if(card.investigation){
    const inv=card.investigation, box=node('details');box.open=true;
    box.append(node('summary','','分析过程 · '+inv.skill_id+' · '+(inv.status==='completed'?'已完成':'部分完成')));
    const list=node('ol');for(const s of inv.steps){list.append(node('li','',`${s.action==='compare'?'补查':s.action==='finish'?'汇总':'停止'} · ${{done:'完成',rejected:'未执行',failed:'失败',proposed:'待执行'}[s.status]||s.status}：${s.reason||s.finding||''}`+(s.hypothesis?'\n待验证假设：'+s.hypothesis:'')+(s.error?'\n'+s.error:'')));}
    box.append(list,node('p','',inv.finding),node('p','','待验证假设：'+(inv.hypothesis||'见各步骤；尚无已证实业务原因')),
      node('p','','待核验：'+inv.open_questions.join('；')),
      node('small','','证据：'+inv.evidence_ids.join('、')));
    for(const follow of card.followups||[])box.append(renderCard(follow,false));d.append(box);
  }
  return d;
}
function makeCards(cards, open=false){
  const box=node('div','cards');box.append(node('div','detail-heading',`完整明细 · ${cards.length} 个结果 · 点击下列指标展开`));
  for(const card of cards)box.append(renderCard(card,open));return box;
}
function showConversation(state){
  renderedMessages=new Set(state.messages.map(m=>m.request_id).filter(Boolean));
  renderedRequest=state.messages.filter(m=>m.role==='assistant').at(-1)?.request_id||null;
  const box=$('#messages');box.replaceChildren();live=null;
  if(!state.messages.length){const e=node('div','empty');e.append(node('b','','从一个熟悉的经营问题开始'),document.createTextNode('可以查数、问口径、按维度看结果，再接着追问。执行进度、明细表和回答会陆续显示。'));box.append(e);}
  for(const m of state.messages){
    const e=node('div','message '+m.role);e.append(node('div','role',m.role==='user'?'你':'经营分析助手'));
    if(m.trace)e.append(traceLink(m.trace.replace('/trace/','/flow/'),'查看执行路线 →'));
    // 明细位于长正文之前。单指标或“展开明细”请求默认展开。
    if(m.result_cards?.length)e.append(makeCards(m.result_cards,!!m.view_only));
    e.append(node('div','body',m.content));
    if(m.trace){const f=node('div','foot');f.append(traceLink(m.trace,m.view_only?'查看原任务回放':'查看这次执行回放'),document.createTextNode(m.view_only?'查看已有结果，未调用模型':m.response_kind==='conversation'?'已回复':({waiting_user:'等待你补充',completed:'检查通过',partial:'部分完成，请看失败项',failed:'未完成',cancelled:'已停止',interrupted:'执行中断'})[m.status]||m.status));e.append(f);}
    if(m.usage){const u=m.usage;e.append(node('div','muted',`本轮 ${u.calls} 次模型请求 · ${u.total_tokens.toLocaleString()} Token（输入 ${u.input_tokens.toLocaleString()} / 输出 ${u.output_tokens.toLocaleString()}，缓存 ${u.cache_read.toLocaleString()}） · 估算 ¥${u.estimated_cny==null?'未知':u.estimated_cny.toFixed(4)}`+(u.usage_unknown_calls?` · ${u.usage_unknown_calls} 次用量未知`:'')));}
    box.append(e);
  }
  if($('#usageLink'))$('#usageLink').href='/usage?id='+cid;
  // 定位最新回复开头，让用户首先看到明细入口；不直接跳到长回答末尾。
  const last=box.lastElementChild;if(last?.classList.contains('assistant'))box.scrollTop=last.offsetTop-box.offsetTop;else toBottom();
}
function renderBranches(){
  const box=$('#branches');box.replaceChildren();if(!live)return;
  const names={queued:'排队',running:'执行中',retrying:'重试中',ok:'完成',failed:'失败',needs_clarification:'需调整',cancelled:'已停止'};
  for(const j of live.jobs.values())box.append(node('span','branch',`${j.name} · ${intentName(j.intent)} · ${names[j.status]||j.status}`));
  if(live.trace)box.append(traceLink(live.trace.replace('/trace/','/flow/'),'查看实时执行路线'),traceLink(live.trace,'完整日志'));
}
function ensureLive(){
  if(live)return;
  const e=node('div','message assistant live'), status=node('div','stream-label','正在执行，明细和回答会陆续显示'),cards=node('div'),body=node('div','body');
  e.append(node('div','role','经营分析助手'),status,body,cards);$('#messages').append(e);
  live={element:e,status,cards,body,jobs:new Map(),cardMap:new Map(),trace:null};toBottom();
}
function updateLive(payload){
  if(stoppedRequests.has(currentRequest))return;
  ensureLive();const follow=nearBottom();
  switch(payload.type){
    case 'analysis': live.status.textContent=(payload.name?payload.name+'：':'')+payload.message+(payload.hypothesis?' · 待验证假设：'+payload.hypothesis:'');break;
    case 'inbox_applied': syncControl().catch(()=>{});break;
    case 'plan_revised': live.jobs.clear();live.cardMap.clear();live.cards.replaceChildren();live.body.textContent='';live.status.textContent='主 Agent 已调整需求，正在重新校验查询范围。';renderBranches();break;
    case 'plan': live.jobs=new Map(payload.jobs.map(j=>[j.job_id,j]));live.cardMap.clear();live.cards.replaceChildren();renderBranches();break;
    case 'job': if(!live.jobs.has(payload.job_id))break;live.jobs.set(payload.job_id,{...live.jobs.get(payload.job_id),...payload});renderBranches();break;
    case 'card': {
      if(!live.jobs.has(payload.card.job_id))break;
      live.cardMap.set(payload.card.job_id,payload.card);
      const opened=new Set([...live.cards.querySelectorAll('details[data-job-id][open]')].map(e=>e.dataset.jobId));
      const ordered=[...live.jobs.keys()].filter(id=>live.cardMap.has(id));
      for(const id of live.cardMap.keys())if(!ordered.includes(id))ordered.push(id);
      const box=makeCards(ordered.map(id=>live.cardMap.get(id)));
      for(const d of box.querySelectorAll('details[data-job-id]'))d.open=opened.has(d.dataset.jobId);
      live.cards.replaceChildren(box);break;
    }
    case 'answer_start': live.body.textContent='';live.status.textContent=payload.phase==='conversation'?'主 Agent 正在回复…':'正在生成回答 · 草稿待校验';break;
    case 'answer_delta': live.body.append(document.createTextNode(payload.delta));break;
    case 'answer_reset': live.body.textContent='';live.status.textContent=payload.reason;break;
    case 'answer_end': live.status.textContent=payload.phase==='conversation'?(payload.has_tools?'正在继续处理你的问题…':'回复已生成'):'正文已生成，正在检查 · 尚非最终结论';break;
    case 'progress': $('#progress').textContent=labels[payload.step]||payload.step;
      if(payload.step==='validate_reply')live.status.textContent='正在检查回答，稍后显示正式结果';break;
  }
  if(follow)toBottom();
}
function finish(state, rid){
  if(currentRequest!==rid)return;
  completedSeen.delete(rid);
  subscription?.close();subscription=null;currentRequest=null;
  showConversation(state);$('#branches').replaceChildren();setBusy(false);
  $('#progress').textContent=state.pending?'请根据问题补充信息。':'本轮已结束，可以继续追问。';
  watchControl();syncControl().catch(()=>{});
}
function attach(rid){
  subscription?.close();currentRequest=rid;setBusy(true);ensureLive();
  const source=new EventSource(`/api/events?id=${cid}&request_id=${rid}`);subscription=source;watchControl();
  source.addEventListener('started',e=>{if(currentRequest!==rid)return;ensureLive();live.trace=JSON.parse(e.data).trace;renderBranches();});
  source.addEventListener('update',e=>{if(currentRequest===rid)updateLive(JSON.parse(e.data));});
  source.addEventListener('done',e=>finish(JSON.parse(e.data),rid));
  source.addEventListener('stream_idle',async e=>{
    if(currentRequest!==rid)return;source.close();$('#progress').textContent=JSON.parse(e.data).message;
    try{const s=await api('/api/conversation?id='+cid);if(s.messages.some(m=>m.role==='assistant'&&m.request_id===rid))finish(s,rid);else{setBusy(false);currentRequest=null;}}catch{setBusy(false);currentRequest=null;}
  });
  source.onerror=()=>{if(currentRequest===rid)$('#progress').textContent='连接暂时中断，正在自动重连；不会重新发送问题。';};
}
async function load(){
  knowledge=await api('/api/catalog');filterMetrics();const s=await api('/api/conversation?id='+cid);showConversation(s);
  if(!s.active_request_id){const saved=Number(sessionStorage.getItem('lg-playground-scroll:'+cid)||0);requestAnimationFrame(()=>{$('#messages').scrollTop=saved;});}
  if(s.active_request_id){$('#progress').textContent='正在恢复本轮流式进度…';attach(s.active_request_id);}
  await syncControl();if(controlState?.active||waitingRequest())watchControl();
}
async function send(){
  const text=$('#text').value.trim();if(controlBusy||!text)return;
  if(busy||controlState?.active||queuedMessages().length){await queueMessage(text);return;}
  setBusy(true);const rid=newId();
  $('#text').value='';persistChatView();$('#progress').textContent='正在开始本轮执行…';
  try{
    const old=await api('/api/conversation?id='+cid);
    if(old.active_request_id){showConversation(old);attach(old.active_request_id);$('#text').value=text;return;}
    showConversation({...old,messages:[...old.messages,{role:'user',content:text}]});attach(rid);
    const s=await api('/api/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:cid,text,request_id:rid})});
    // POST完成不能抢先关闭SSE，否则短回复的末批chunk可能还没进DOM。
    // 正常由SSE的done交付；仅在订阅未结束时用已保存终态兜底。
    setTimeout(()=>{if(currentRequest===rid)finish(s,rid);},2000);
  }catch(e){
    // POST断线不等于执行失败；先读持久化结果，绝不自动重发付费请求。
    try{const s=await api('/api/conversation?id='+cid);
      if(s.messages.some(m=>m.role==='assistant'&&m.request_id===rid)){finish(s,rid);return;}
      if(s.active_request_id===rid){$('#progress').textContent='请求连接中断，服务端仍在执行，正在等待结果。';return;}
    }catch{}
    subscription?.close();subscription=null;currentRequest=null;setBusy(false);
    $('#progress').textContent=e.message+'；可刷新查看已保存进度。';if(!$('#text').value)$('#text').value=text;
  }
}
$('#send').onclick=send;
$('#text').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();send();}};
$('#new').onclick=()=>{persistChatView();subscription?.close();subscription=null;currentRequest=null;history.replaceState({},'','/');cid=newId();localStorage.setItem('lg-playground-conversation',cid);showConversation({messages:[]});$('#progress').textContent='新对话已就绪';$('#branches').replaceChildren();$('#text').value='';persistChatView();controlState=null;renderInbox();$('#controlHint').textContent='';clearInterval(controlTimer);controlTimer=null;};
$('#search').oninput=filterMetrics;$('#metric').onchange=chooseMetric;
document.querySelectorAll('[data-q]').forEach(b=>b.onclick=()=>{$('#text').value=b.dataset.q;$('#text').focus();updateControlButtons();});

/* 停止控制是独立的短请求；旧 SSE 的结束不能覆盖新一轮。 */
let controlBusy=false, controlTimer=null, pollingControl=false;
let controlState=null, restoredPending=null;
const stoppedRequests=new Set();
function waitingRequest(){
  const p=controlState?.pending_request;
  return p && ['queued','starting'].includes(p.status) ? p : null;
}
function updateControlButtons(){
  const waiting=waitingRequest();
  $('#stop').hidden=!busy;
  $('#replace').hidden=true;
  $('#stop').disabled=controlBusy||!currentRequest||stoppedRequests.has(currentRequest);
  $('#replace').disabled=controlBusy||!currentRequest||!!waiting||!$('#text').value.trim();
  $('#replace').textContent=stoppedRequests.has(currentRequest)?'发送新问题':'停止并发送';
  $('#send').disabled=controlBusy||!$('#text').value.trim();
  $('#new').disabled=busy||controlBusy||!!waiting||queuedMessages().length>0;
}
function markStopping(rid){
  stoppedRequests.add(rid);
  if(currentRequest===rid && live){
    live.status.textContent='正在停止：当前调用返回后退出，后续结果不再交付';
    $('#progress').textContent='停止请求已受理，等待当前调用返回。';
    live.cards.replaceChildren();
  }
  updateControlButtons();
}
function watchControl(){
  if(!controlTimer)controlTimer=setInterval(()=>syncControl().catch(()=>{}),750);
}
async function syncControl(){
  if(pollingControl)return;
  pollingControl=true;const requestedCid=cid;
  try{
    const info=await api('/api/control?id='+requestedCid);
    if(requestedCid!==cid)return;
    controlState=info;
    renderInbox();
    const active=info.active,pending=waitingRequest();
    if(active && active.rid!==currentRequest){
      const s=await api('/api/conversation?id='+cid);
      if(requestedCid!==cid)return;
      // 控制库可能先落盘，聊天记录随后才就绪；过期快照不重新订阅旧任务。
      if(s.active_request_id===active.rid){showConversation(s);attach(active.rid);}
    }
    if(!active&&!pending&&info.latest&&info.latest.rid!==renderedRequest){
      // 控制轮询可能比SSE先收到“完成”。给正在订阅的正文先排空事件，不能
      // 直接重画终态并关闭SSE；否则很短的回复可能一个片段也进不了页面。
      if(subscription&&currentRequest===info.latest.rid){
        if(!completedSeen.has(currentRequest))completedSeen.set(currentRequest,Date.now());
        if(Date.now()-completedSeen.get(currentRequest)<2000)return;
      }
      const s=await api('/api/conversation?id='+cid);
      if(requestedCid!==cid)return;
      // 下一条可能在一次轮询之间就完成（例如只展开明细）；直接展示持久化终态。
      if(!s.active_request_id&&s.messages.some(m=>m.role==='assistant'&&m.request_id===info.latest.rid)){
        subscription?.close();subscription=null;currentRequest=null;
        showConversation(s);$('#branches').replaceChildren();setBusy(false);
        $('#progress').textContent='本轮已结束，可以继续追问。';
      }
    }
    if(active?.cancel_requested)markStopping(active.rid);
    if(pending){
      $('#controlHint').textContent='已保存下一条问题，待当前调用结束并退出后自动开始：'+pending.text;
    }else if(info.pending_request?.status==='interrupted'&&!active&&!busy){
      const saved=info.pending_request;
      $('#controlHint').textContent='服务中断，待启动问题已保留，请重新发送：'+saved.text;
      if(restoredPending!==saved.rid&&!$('#text').value){
        $('#text').value=saved.text;restoredPending=saved.rid;
      }
    }else{
      $('#controlHint').textContent=active?.cancel_requested?'停止请求已受理；不需要等完整分析跑完。':'';
    }
    updateControlButtons();
    renderInbox();
    if(!active&&!pending&&!busy&&!queuedMessages().length){
      clearInterval(controlTimer);controlTimer=null;
    }
  }finally{pollingControl=false;}
}
async function stopRun(replace=false){
  const expected=currentRequest,text=$('#text').value.trim();
  if(controlBusy||!expected||(replace&&!text))return;
  controlBusy=true;updateControlButtons();
  const nextId=replace?newId():null;
  try{
    controlState=await api(replace?'/api/replace':'/api/stop',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({id:cid,expected_request_id:expected,...(replace?{request_id:nextId,text}:{})})
    });
    if(controlState.active?.rid===expected&&controlState.active.cancel_requested)markStopping(expected);
    if(replace)$('#text').value='';
    watchControl();await syncControl();
  }catch(e){
    $('#controlHint').textContent=e.message+'；输入文字已保留。';
    // 响应丢失时只读查询受理记录，绝不换一个ID自动重发。
    try{await syncControl();}catch{}
  }finally{controlBusy=false;updateControlButtons();}
}
$('#stop').onclick=()=>stopRun(false);
$('#replace').onclick=()=>stopRun(true);
$('#text').addEventListener('input',()=>{persistChatView();updateControlButtons();renderInbox();});

function queuedMessages(){
  return (controlState?.inbox||[]).filter(r=>['queued','processing','dispatched'].includes(r.status));
}
function renderInbox(){
  const box=$('#inbox');box.replaceChildren();
  for(const r of controlState?.inbox||[]){
    if(renderedMessages.has(r.mid)&&!['queued','processing','interrupted','failed'].includes(r.status))continue;
    if(r.status==='applied'&&r.target!==currentRequest)continue;
    const item=node('div','inbox-item');
    const label={queued:r.delivery==='steer'?'待插入：等待下一个安全位置':'已排队：当前任务结束后处理',
      processing:'主 Agent 正在处理补充',dispatched:'已开始后续任务',applied:'主 Agent 已处理',
      interrupted:'服务中断，文字已保留',failed:'未成功处理，文字已保留'}[r.status]||r.status;
    item.append(node('small','muted',label),node('div','',r.text));
    if(['interrupted','failed'].includes(r.status)&&r.has_run){
      const b=node('button','','恢复到输入框');b.onclick=()=>{
        if($('#text').value.trim())return; // 不覆盖正在编辑的新消息
        $('#text').value=r.text;$('#text').focus();updateControlButtons();
      };b.disabled=controlBusy||!!$('#text').value.trim();item.prepend(b);
    }else if(['queued','interrupted','failed'].includes(r.status)&&r.delivery!=='steer'){
      const b=node('button','','立即插入');b.disabled=controlBusy;
      b.onclick=()=>insertMessage(r.mid);item.prepend(b);
    }else if(['interrupted','failed'].includes(r.status)){
      const b=node('button','','重新插入');b.onclick=()=>insertMessage(r.mid);item.prepend(b);
    }
    if(r.reply)item.append(node('div','inbox-reply','主 Agent：'+r.reply));
    box.append(item);
  }
}
async function queueMessage(text){
  const mid=newId(),targetCid=cid;
  controlBusy=true;updateControlButtons();
  try{
    await api('/api/inbox',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({id:cid,text,message_id:mid,expected_request_id:currentRequest})});
    if(cid!==targetCid)return;
    if($('#text').value.trim()===text){$('#text').value='';persistChatView();}
    watchControl();await syncControl();
  }catch(e){$('#controlHint').textContent=e.message+'；未自动重发，输入文字保留。';}
  finally{controlBusy=false;updateControlButtons();renderInbox();}
}
async function insertMessage(mid){
  controlBusy=true;updateControlButtons();renderInbox();
  try{
    await api('/api/insert',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({id:cid,message_id:mid,expected_request_id:currentRequest})});
    watchControl();await syncControl();
  }catch(e){$('#controlHint').textContent=e.message;}
  finally{controlBusy=false;updateControlButtons();renderInbox();}
}

load().catch(e=>$('#progress').textContent='加载失败：'+e.message);
