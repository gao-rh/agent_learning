'use strict';
window.__viewerStarted=true;
const $=s=>document.querySelector(s), main=$('#main');
const state={batches:[],batch:'',overview:null,data:null,filter:'all',ticket:0};
const names={partial:'部分可继续',blocked:'阻断',active:'当前有效',gap:'能力缺口',superseded:'已替代',cancelled:'已撤销',passed:'通过',failed:'未通过',clarify:'需要补充',pending:'待人工审阅',incomplete:'未完成',not_run:'未运行',completed:'执行完成',waiting_user:'等待补充',waiting_review:'执行结束',ok:'完成',error:'异常',ready:'可执行',reply:'直接文字回复',unsupported:'能力不支持'};
const keys={requirements:'原需求清单',tasks:'当前任务',views:'展示视图',requirement_ids:'对应需求',replacement_ids:'接受的替代需求',predicates:'指标规则',population:'统计总体',cohort_rule:'新老商分群',definition_version:'当期口径版本',baseline_version:'基期口径版本',comparison_mode:'比较方式',recompute:'是否重算',purpose:'用途',revision:'当前版本',supersedes_revision:'替代的旧版本',delivery:'交付计划',changes:'本轮变更',goal:'整体目标',questions:'待解决问题',months:'每年选取月份',note:'说明',affects:'影响的需求',op:'条件关系',label:'需求名称',metric_id:'指标',intent:'任务类型',period:'查询期间',comparison_period:'比较期间',start:'开始日期',end:'结束日期',start_date:'开始日期',end_date:'结束日期',group_by:'分组维度',filters:'筛选条件',required_predicates:'必选口径',knowledge_refs:'引用来源',outcome:'决定',question:'澄清问题',decomposition:'拆分说明',requests:'指标任务',missing_items:'待确认条件',reason:'原因',owner:'信息提供方',source:'来源',source_id:'来源ID',records:'检索到的知识',candidates:'搜索候选',allowed_values:'可用枚举',supported_dimensions:'支持的维度',definition:'指标定义',formula:'计算公式',aliases:'别名',unit:'单位',dimensions:'维度',name:'名称',id:'ID',score:'匹配分数（非正确概率）',supported:'是否支持',version:'版本',text:'内容',scope:'适用范围',query:'搜索词',dimension_id:'维度',result:'工具返回',sql:'实际 SQL',params:'SQL 参数',rows:'实际数据行',value:'数值',validation:'程序校验',accepted:'是否允许查询',errors:'阻断原因',normalized_tasks:'程序解析后的任务',model_submissions:'模型原始提交',resolver_result:'检索循环最终返回',actual_input:'实际送入模型的上下文',knowledge_observations:'工具实际返回记录',messages:'当前消息与轨迹',conversation_context:'历史对话',conversation_memory:'会话记忆',business_anchor:'上一轮业务任务',summary:'历史摘要',task:'任务条件',jobs:'指标任务',reference_date:'日期基准',timezone:'时区',mode:'时间表达类型',offset:'相对偏移',exact_date:'明确单日',field:'字段',expected:'预期',actual:'实际',type:'类型',field_id:'口径字段',operator:'条件关系',model:'模型',content:'正文',role:'角色',tools:'可调用工具定义',usage:'本次调用用量',input_tokens:'输入 Token',output_tokens:'输出 Token',total_tokens:'合计 Token',cache_read:'缓存命中输入',input_token_details:'输入细项',tool_calls:'模型提出的工具调用',arguments:'参数',args:'工具参数',semantic_only:'只做语义检查',execution_enabled:'该阶段是否执行查询',transformations:'程序转换记录',decision:'决定',status:'状态',history:'预设前文',method:'查询方式',business_line_id:'业务线',dataset_id:'数据集',query_binding:'查询绑定',synthetic:'模拟数据',mandatory_predicates:'指标必选规则',availability:'数据覆盖时间',effective_from:'生效日期',effective_to:'有效截止日',required_knowledge_cited:'是否引用必要知识',task_match:'条件是否匹配'};
const number=n=>Number(n||0).toLocaleString('zh-CN');
function el(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;}
function btn(text,fn,cls=''){const b=el('button',cls,text);b.onclick=fn;return b;}
function isComplex(){return state.data?.kind==='complex'||state.batches.find(b=>b.id===state.batch)?.kind==='complex';}
function statusText(value){return isComplex()&&value==='passed'?'语义审阅通过':names[value]||value;}
function pill(value){return el('span','pill '+value,statusText(value));}
function notice(text){const n=$('#notice');n.textContent=text;n.style.display='block';setTimeout(()=>n.style.display='none',2600);}
function endpoint(path,params){return path+'?'+new URLSearchParams(params);}
async function api(path,params={}){
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
 try{const r=await fetch(endpoint(path,params),{signal:controller.signal});const data=await r.json();if(!r.ok)throw new Error(data.error||'读取失败');return data;}
 catch(error){if(controller.signal.aborted)throw new Error('读取记录超时，请点击「刷新记录」重试。不会重新运行实验。');if(error instanceof TypeError)throw new Error('无法连接本地案例服务。请双击实验目录里的「启动案例查看器.command」，再点击右上角「刷新记录」。实验记录仍保存在本地，重新打开不会调用模型。');throw error;}
 finally{clearTimeout(timer);}
}
function route(batch,caseId,turn,step){const u=new URL(location.href);u.pathname='/case/'+encodeURIComponent(batch)+'/'+encodeURIComponent(caseId);u.search='';if(turn)u.searchParams.set('turn',turn);if(step)u.searchParams.set('step',step);return u.pathname+u.search;}
function metric(id){return state.data?.catalog?.metrics?.find(m=>m.id===id)?.name||id;}
function dim(id){return state.data?.catalog?.dimensions?.[id]?.name||keys[id]||id;}
function valueName(dimId,v){return state.data?.catalog?.dimensions?.[dimId]?.values?.find(x=>x.id===v)?.name??(typeof v==='boolean'?(v?'是':'否'):String(v));}
function textValue(v){if(v==null)return '未提供';if(typeof v==='boolean')return v?'是':'否';if(typeof v==='object')return JSON.stringify(v);return String(v);}
function display(key,v){if(key==='metric_id')return metric(v);if(key==='group_by')return v.length?v.map(dim).join(' × '):'整体汇总（无分组）';if(key==='filters')return Object.keys(v).length?Object.entries(v).map(([d,vs])=>dim(d)+'＝'+vs.map(x=>valueName(d,x)).join(' / ')).join('；'):'无额外筛选';if(key==='period'||key==='comparison_period'){if(!v)return '无';if(v.start||v.start_date)return (v.start||v.start_date)+' 至 '+(v.end||v.end_date);if(v.mode==='exact')return v.exact_date;return (v.mode==='calendar'?'自然周期':'滚动周期')+' '+({month:'月',week:'周',day:'天',year:'年'}[v.unit]||v.unit)+'，偏移 '+v.offset;}if(key==='required_predicates')return v.length?v.map(p=>p.field_id+' '+({ne:'≠',eq:'＝'}[p.operator]||p.operator)+' '+p.value).join('；'):'无';return textValue(v);}
function details(label,body,open=false){
 const d=el('details');d.open=open;d.append(el('summary','',label));
 if(typeof body==='function'){
  let rendered=false;const render=()=>{if(rendered||!d.open)return;rendered=true;d.append(body());};
  d.addEventListener('toggle',render);render();
 }else d.append(body);
 return d;
}
function raw(label,data){return details(label,()=>el('pre','code',JSON.stringify(data,null,2)));}
function table(rows,columns){const wrap=el('div','table-wrap'),t=el('table'),h=el('thead'),hr=el('tr');for(const c of columns)hr.append(el('th','',typeof c==='string'?dim(c):c.label));h.append(hr);t.append(h);const b=el('tbody');for(const r of rows){const tr=el('tr');for(const c of columns){const key=typeof c==='string'?c:c.key;tr.append(el('td','',valueName(key,r[key])));}b.append(tr);}t.append(b);wrap.append(t);return wrap;}
function objectView(value,depth=0,key=''){
 if(value==null||typeof value!=='object'){
  if(typeof value==='string'&&/^[\[{]/.test(value.trim())){try{return objectView(JSON.parse(value),depth+1,key);}catch{}}
  return el('div','text-value',key==='metric_id'?metric(value):textValue(value));
 }
 const semanticArray=['group_by','required_predicates'].includes(key)&&Array.isArray(value);const semanticFilters=key==='filters'&&!Array.isArray(value)&&Object.values(value).every(Array.isArray);const semanticPeriod=['period','comparison_period'].includes(key)&&(typeof value.start==='string'||typeof value.start_date==='string'||typeof value.mode==='string');
 if(semanticArray||semanticFilters||semanticPeriod)return el('div','text-value',display(key,value));
 const box=el('div','object');
 if(Array.isArray(value)){
  if(!value.length)return el('div','muted','无');
  if(key==='rows')return table(value,Object.keys(value[0]||{}));
  if(value.every(v=>v==null||typeof v!=='object'))return el('div','text-value',value.map(v=>state.data?.catalog?.dimensions?.[key]?valueName(key,v):textValue(v)).join('、'));
  value.forEach((v,i)=>{let label=v?.name||v?.title||v?.metric_id&&metric(v.metric_id)||v?.role&&({'human':'用户输入','user':'用户输入','ai':'模型消息','assistant':'模型消息','tool':'工具返回','system':'系统提示'}[v.role]||v.role)||'第 '+(i+1)+' 项';
    if(key==='messages')label=(i+1)+'. '+({'system':'系统提示','human':'用户消息 / 组装上下文','ai':'模型消息','tool':'工具返回'}[v.type]||label);
    box.append(details(label,()=>objectView(v,depth+1),depth<2&&value.length<=3));});return box;
 }
 for(const [k,v] of Object.entries(value)){
  if(k==='type'&&['ai','human','tool','system'].includes(v))continue;
  if(['additional_kwargs','response_metadata'].includes(k)&&v&&typeof v==='object'&&!Object.keys(v).length)continue;
  if(['name','id'].includes(k)&&v==null)continue;
  const f=el('div','field');f.append(el('span','key',keys[k]||dim(k)));
  if((typeof v==='string'&&v.length>1400)||['tools','metadata','additional_kwargs','response_metadata'].includes(k))f.append(details('展开完整内容',()=>objectView(v,depth+1,k)));
  else if(depth>3&&typeof v==='object'&&v!==null)f.append(details('展开',()=>objectView(v,depth+1,k)));
  else f.append(objectView(v,depth+1,k));box.append(f);
 }return box;
}

// 默认页面是一份按真实顺序展开的对话记录。原始上下文仅在用户展开时加载。
function para(text,cls=''){return el('p',cls,text);}
function cut(text,n=150){text=String(text||'');return text.length>n?text.slice(0,n)+'…':text;}
function plain(v){return typeof v==='string'?v:JSON.stringify(v,null,2);}
function canonical(v){if(Array.isArray(v))return v.map(canonical);if(v&&typeof v==='object')return Object.fromEntries(Object.entries(v).sort(([a],[b])=>a.localeCompare(b)).map(([k,x])=>[k,canonical(x)]));return v;}
function safeInput(v){return v&&typeof v==='object'&&!Array.isArray(v)?v:{};}
function outcomeName(v){return {ready:'准备提交任务',clarify:'需要用户补充',partial:'提交可完成的部分',blocked:'暂时无法继续',reply:'直接回复'}[v]||v||'未记录';}
function batchLabel(b){const stamp=b.id.match(/(20\d{2})(\d{2})(\d{2})/);return b.title+(stamp?' · '+Number(stamp[2])+'月'+Number(stamp[3])+'日':'');}
function renderSide(){
 const box=$('#cases');box.replaceChildren();const q=$('#search').value.trim().toLowerCase();
 if(!state.overview){box.append(para('正在读取案例列表…','muted'));return;}
 for(const c of state.overview?.cases||[]){
  if(state.filter!=='all'&&c.status!==state.filter)continue;
  if(q&&!(c.id+c.title+c.first_question).toLowerCase().includes(q))continue;
  const a=el('a','case-link'+(state.data?.id===c.id?' selected':''));a.href=route(state.batch,c.id);
  a.append(el('span','case-number',c.id),el('span','case-title',c.title));
  a.onclick=e=>{e.preventDefault();loadCase(c.id,true);};box.append(a);
 }if(!box.children.length)box.append(para('没有匹配的案例。','muted'));
}
function showError(error){main.replaceChildren(el('h1','','暂时没有读取到记录'),para(error.message,'banner'),btn('重新读取',()=>init()));}
function overview(){
 state.data=null;renderSide();main.replaceChildren(el('div','eyebrow','实验记录'),el('h1','','选一个案例，从头看完整过程'),para('每个案例都按「用户消息 → 中间操作 → Agent 回复」排列。','intro'));
 const grid=el('div','overview-grid');for(const c of state.overview.cases){const a=el('a','overview-card');a.href=route(state.batch,c.id);a.append(el('small','muted',c.id+' · '+c.actual_turns+' 轮对话'),el('h2','',c.title),para(cut(c.first_question,160)));a.onclick=e=>{e.preventDefault();loadCase(c.id,true);};grid.append(a);}main.append(grid);
}
async function loadBatch(id,cid=null){
 const ticket=++state.ticket;state.batch=id;state.data=null;$('#batch').value=id;main.replaceChildren(para('正在读取案例…','loading'));
 try{const data=await api('/api/batch',{batch:id});if(ticket!==state.ticket)return;state.overview=data;renderSide();if(cid)await loadCase(cid,false);else{history.replaceState({},'','/?batch='+encodeURIComponent(id));overview();}}catch(e){if(ticket===state.ticket)showError(e);}
}
async function loadCase(id,push){
 document.body.classList.remove('cases-open');$('#toggle-cases').setAttribute('aria-expanded','false');
 const ticket=++state.ticket;const batch=state.batch;main.replaceChildren(para('正在读取完整对话…','loading'));
 try{const data=await api('/api/case',{batch,case:id});if(ticket!==state.ticket)return;state.data=data;if(push)history.pushState({},'',route(batch,id));renderSide();renderCase();}catch(e){if(ticket===state.ticket)showError(e);}
}
function metricLabel(id){return metric(id)||'未选择指标';}
function rulesText(rules){if(!Array.isArray(rules)||!rules.length)return '未提交额外规则';return rules.map(p=>{const field=p.field_id||p.field||'条件';const op=p.operator||p.op;const v=p.value;return dim(field)+' '+({eq:'＝',ne:'≠',in:'属于',not_in:'不属于',gt:'>',gte:'≥',lt:'<',lte:'≤'}[op]||op||'')+' '+(Array.isArray(v)?v.map(x=>valueName(field,x)).join(' / '):valueName(field,v));}).join('；');}
const taskLabels={period:'当期',comparison_period:'基期',filters:'筛选条件',group_by:'分组方式',predicates:'指标规则',required_predicates:'指标规则',population:'统计人群',cohort_rule:'分群规则',definition_version:'当期口径',baseline_version:'基期口径',comparison_mode:'比较方式',recompute:'是否重算',intent:'任务类型'};
function taskValue(k,v){
 if(v===undefined)return '未提交';if(v===null)return '无';
 if(k==='predicates'||k==='required_predicates')return rulesText(v);
 if(k==='intent')return {query:'取数',analysis:'分析',consult:'口径咨询'}[v]||v;
 if(k==='comparison_mode')return {none:'未指定跨期比较',historical_display:'按历史口径展示',same_definition:'按同一口径比较'}[v]||v;
 if(k==='recompute')return v?'是':'否';
 if(['period','comparison_period','group_by','filters'].includes(k))return display(k,v);
 return v===''?'未填写':textValue(v);
}
function fields(entries){const dl=el('dl','key-values');for(const [label,value]of entries){dl.append(el('dt','',label),el('dd','',value));}return dl;}
function compactTasks(tasks){
 const wrap=el('div','task-list');if(!tasks?.length)return para('本次尚未提交具体取数任务。','muted');
 const primary=['intent','period','comparison_period','filters','group_by','predicates','required_predicates','population','cohort_rule','definition_version','baseline_version','comparison_mode','recompute'];
 const present=primary.filter(k=>['period','filters','group_by'].includes(k)||tasks.some(t=>t[k]!==undefined&&t[k]!==null));
 const common=tasks.length>1?present.filter(k=>tasks.every(t=>JSON.stringify(canonical(t[k]))===JSON.stringify(canonical(tasks[0][k])))):[];
 if(common.length){const shared=el('div','shared-params');shared.append(el('h4','','以下 '+tasks.length+' 项任务共用的参数'),fields(common.map(k=>[taskLabels[k],taskValue(k,tasks[0][k])])));wrap.append(shared);}
 for(const [i,t]of tasks.entries()){
  const card=el('div','task-card');card.append(el('h4','',(i+1)+'. '+metricLabel(t.metric_id)),el('div','metric-id',t.metric_id||'指标 ID 未提交'));
  const unique=present.filter(k=>!common.includes(k));if(unique.length)card.append(fields(unique.map(k=>[taskLabels[k],taskValue(k,t[k])])));
  if(t.views?.length)card.append(para('展示：'+t.views.map(v=>({month:'按月',year:'按年',total:'期间合计',annual_months:'每年指定月份累计',quarter:'按季度'}[v.kind]||v.kind)+(v.months?.length?'（'+v.months.join('、')+'月）':'')).join('；'),'subtle'));
  if(t.purpose)card.append(para(t.purpose,'subtle'));
  card.append(details('这项任务的全部字段',()=>objectView(t)));wrap.append(card);
 }return wrap;
}
function planView(input){
 const body=el('div');const p=safeInput(input);body.append(para(outcomeName(p.outcome),'decision'));
 if(p.goal||p.decomposition)body.append(para(p.goal||p.decomposition));
 body.append(el('h4','','实际提交的参数'),compactTasks(p.tasks||p.requests||[]));
 if(p.requirements?.length){const reqs=el('div');for(const r of p.requirements)reqs.append(para(r.label+' · '+(names[r.status]||r.status)+(r.reason?'：'+r.reason:'')));body.append(details('原始需求及尚未解决的部分',reqs));}
 // 面向用户的回复统一放在本轮末尾。这里保留每次提交，防止最终结果覆盖中途错误。
 if(p.question)body.append(details('这次提交携带的回复文字',para(p.question,'verbatim')));
 return body;
}
function validationView(v){
 const box=el('div','validation-note');const errors=v?.errors||[];
 box.append(para(errors.length?'程序检查：存在 '+errors.length+' 项问题，未放行。':v?.accepted===true?'程序检查通过。':v?.decision==='reply'?'本轮直接回复，没有提交查询任务。':v?.decision==='clarify'?'本轮转为澄清，没有执行查询。':v?.execution_enabled===false?'本阶段只检查需求，不执行查询。':v?.accepted===false?'程序未放行；没有记录具体错误。':'程序已记录本次提交。'));
 if(errors.length)box.append(details('查看具体检查问题',()=>objectView(errors)));
 return box;
}
function candidateView(candidates,name){
 const box=el('div','tool-result');box.append(el('span','result-caption','工具返回'));
 if(!candidates.length){box.append(para('没有匹配到候选。'));return box;}
 const rows=el('ul','candidate-list');for(const c of candidates.slice(0,6)){
  const row=el('li');row.append(el('strong','',c.name||c.title||c.id||'候选'));
  if(c.id)row.append(el('span','inline-id',c.id));
  if(c.definition)row.append(para(cut(c.definition,170),'subtle'));
  if(c.supported===false)row.append(el('span','warning-inline','当前指标不支持'));
  rows.append(row);
 }box.append(rows);if(candidates.length>6)box.append(details('其余 '+(candidates.length-6)+' 个候选',()=>objectView(candidates.slice(6))));return box;
}
function toolView(item){
 const input=safeInput(item.input),output=item.output?.result??item.output;
 const box=el('div');
 if(['finish_plan','finish_resolution'].includes(item.name)){
  box.append(planView(input));
  if(output?.validation)box.append(validationView(output.validation));
  else if(output?.accepted_for_validation)box.append(para('已接收提交，后续还会做参数检查。','subtle'));
  else if(output?.errors?.length)box.append(details('程序反馈',()=>objectView(output),true));
 }else if(item.name==='query_local_simulation'){
  if(input.task)box.append(compactTasks([input.task]));
  if(output?.rows)box.append(el('h4','','实际查询结果'),table(output.rows,Object.keys(output.rows[0]||{})));
 }else{
  const ps=[];if(input.query!==undefined)ps.push(['搜索内容',input.query||'全部可用值']);if(input.metric_id)ps.push(['对应指标',metricLabel(input.metric_id)]);if(input.dimension_id)ps.push(['维度',dim(input.dimension_id)]);if(input.source==='topic_hint')ps.push(['检索方式','程序按当前话题预检索']);if(ps.length)box.append(fields(ps));
  if(Array.isArray(output?.candidates))box.append(candidateView(output.candidates,item.name));
  else if(item.name==='get_metric_definition'&&output){
   box.append(para(output.name||metricLabel(input.metric_id),'tool-result-title'),para(output.definition||'未返回定义正文。'));
   const rule=output.mandatory_predicates||output.required_predicates;if(rule?.length)box.append(para('必选规则：'+rulesText(rule),'rule-note'));
   if(output.supported===false)box.append(para('工具明确标记：当前能力不支持。','warning-inline'));
   const dims=output.supported_dimensions||output.dimensions;
   if(dims)box.append(details('支持哪些维度及枚举',()=>objectView(dims)));
  }else if(Array.isArray(output?.records)){
   if(!output.records.length)box.append(para('没有找到相关业务知识。','subtle'));
   for(const r of output.records)box.append(el('h4','',r.title||r.name||r.id||'知识记录'),para(cut(r.text||r.content||r.definition,360)),details('完整知识内容',()=>objectView(r)));
  }else if(output&&typeof output==='object'&&!Object.keys(output).length)box.append(para('没有返回匹配内容。','subtle'));
  else if(output!=null)box.append(details('查看工具返回内容',()=>objectView(output)));
 }
 if(item.status==='not_recorded')box.append(para('模型提出了调用，但没有找到对应的工具执行记录。','warning-inline'));
 else if(item.status==='incomplete')box.append(para('未记录到这次调用结束。','warning-inline'));
 else if(item.status==='error')box.append(para('这次调用发生异常，展开原始输入输出查看。','warning-inline'));
 box.append(details('原始输入与输出',()=>objectView({input:item.input,output:item.output})));
 return box;
}
const toolTitles={search_metrics:'查找指标',get_metric_definition:'读取指标口径',search_dimensions:'查找维度',search_dimension_values:'查找可用枚举',search_business_knowledge:'检索业务知识',finish_plan:'提交任务参数',finish_resolution:'提交任务参数',query_local_simulation:'执行模拟取数'};
function actionCard(item,turn,index){
 const node=el('article','action '+(item.name?.startsWith('finish_')?'submission':''));node.id='step-'+turn.number+'-'+item.id;node.dataset.step=item.id;
 const head=el('div','action-title');head.append(el('span','action-number',String(index+1).padStart(2,'0')));
 let title=item.kind==='message'?'Agent 中途输出':item.kind==='validation'?'程序检查参数':item.kind==='feedback'?'程序反馈给 Agent':item.kind==='error'?'执行遇到问题':toolTitles[item.name]||item.name;
 head.append(el('h3','',title));if(item.kind==='tool')head.append(el('span','actor',item.role==='程序调用工具'?'程序调用':'Agent 调用'));
 const anchor=el('a','step-anchor','链接');anchor.href=route(state.batch,state.data.id,turn.number,item.id);head.append(anchor);node.append(head);
 if(item.kind==='tool')node.append(toolView(item));else if(item.kind==='validation')node.append(validationView(item.validation));else node.append(para(item.text,'verbatim'));
 return node;
}
function chat(role,text){const node=el('article','chat '+role);node.append(el('div','chat-label',role==='user'?'你':'Agent 回复'),para(text||'没有记录到文字回复。','verbatim'));return node;}
function simulatedUserView(actor){
 const body=el('div');body.append(para('独立的一次模型参与：AI 扮演用户，只接收用户设定与实际可见对话。','subtle'));
 if(actor.usage)body.append(fields([['模型',actor.model||'未开始'],['请求',number(actor.usage.calls)+' 次'],['Token',number(actor.usage.total_tokens)],['估算费用',actor.usage.estimated_cny==null?'未知':'¥ '+Number(actor.usage.estimated_cny).toFixed(3)]]));
 body.append(details('AI 用户实际输入、模型返回与原始事件',()=>objectView(actor)));
 return details('模型参与 · AI 模拟用户',body);
}
function replyView(turn){
 // 旧实验把查询行直接拼成 JSON 回复；只排版原文里的数据，不用最终 State 改写答案。
 const node=el('article','chat assistant');node.append(el('div','chat-label',state.data?.simulation?.protocol&&state.data?.kind!=='query'?'Agent 回复 · 程序展示模型实际计划':'Agent 回复'));let formatted=false;
 for(const line of (turn.answer||'没有记录到文字回复。').split('\n')){
  const match=line.match(/^(.*?)[：:]\s*(\[\{.*\}\])\s*$/);let rows;
  if(match){try{rows=JSON.parse(match[2]);}catch{}}
  if(Array.isArray(rows)&&rows.length&&rows.every(r=>r&&typeof r==='object'&&!Array.isArray(r))){
   node.append(para(match[1],'verbatim'),table(rows,[...new Set(rows.flatMap(Object.keys))]));formatted=true;
  }else node.append(para(line,'verbatim'));
 }
 if(formatted)node.append(details('查看回复原文（数据已排成上面的表格）',para(turn.answer,'verbatim')));
 return node;
}
function reviewView(turn){
 const content=el('div');content.append(para('下面是实验结束后的评审，不属于 Agent 的对话或执行步骤。','subtle'),pill(turn.status));
 const note=turn.review?.human_review?.notes;if(note)content.append(para(note));
 if(turn.findings?.length){const seen=new Set();for(const f of turn.findings){if(seen.has(f.text))continue;seen.add(f.text);content.append(para(f.text),f.data?details('核对依据',()=>objectView(f.data)):el('span'));}}
 if(turn.checks?.length)content.append(table(turn.checks.map(x=>({check:x.label,result:x.passed?'通过':'未通过'})),[{key:'check',label:'检查项'},{key:'result',label:'结果'}]));
 if(turn.review?.audit_corrections?.length)content.append(details('评审更正记录',()=>objectView(turn.review.audit_corrections)));
 content.append(details('完整评审与预期',()=>objectView({review:turn.review,expected:turn.expected,audit:turn.audit})));
 return details('实验评审 · '+statusText(turn.status),content);
}
function technicalView(turn){
 const body=el('div');body.append(fields([['模型请求',number(turn.usage.calls)+' 次'],['Token',number(turn.usage.total_tokens)],['估算费用',turn.usage.estimated_cny==null?'未知':'¥ '+Number(turn.usage.estimated_cny).toFixed(3)]]));
 for(const step of turn.steps){
  const detail=details(step.label+' · '+step.role,el('div','lazy-body'));detail.id='technical-'+turn.number+'-'+step.id;
  detail.ontoggle=async()=>{
   if(!detail.open||detail.dataset.loaded)return;detail.dataset.loaded='loading';const target=detail.querySelector('.lazy-body');target.textContent='正在读取…';
   try{const data=await api('/api/step',{batch:state.data.batch,case:state.data.id,turn:turn.number,step:step.id});target.replaceChildren();
    const requests=data.events?.filter(e=>e.kind==='model_request')||[];const responses=data.events?.filter(e=>e.kind==='model_response')||[];
    if(requests.length){for(const r of requests)target.append(el('h4','','实际模型上下文'),objectView(r.messages,0,'messages'),details('工具定义与请求配置',()=>objectView({tools:r.tools,parameters:r.parameters})));for(const r of responses)target.append(el('h4','','模型原始返回'),objectView({content:r.content,tool_calls:r.tool_calls}),details('用量',()=>objectView(r.usage)));}
    else target.append(objectView({input:data.input,output:data.output,finished:data.finished}));
    target.append(raw('原始事件 JSON',data));detail.dataset.loaded='yes';
   }catch(e){target.textContent=e.message;delete detail.dataset.loaded;}
  };body.append(detail);
 }const rawLink=el('a','','下载／查看本轮原始日志');rawLink.href=endpoint('/api/raw',{batch:state.batch,case:state.data.id,turn:turn.number});rawLink.target='_blank';rawLink.rel='noopener';body.append(rawLink);
 const panel=details('技术详情 · 模型上下文、节点、Token 和原始日志',body);panel.classList.add('technical');return panel;
}
function scrollToTurn(number,changeUrl=true){const target=$('#turn-'+number);if(!target)return;if(changeUrl)history.replaceState({},'',route(state.batch,state.data.id,number));target.scrollIntoView({block:'start'});for(const a of document.querySelectorAll('.turn-nav a'))a.classList.toggle('current',a.dataset.turn===String(number));}
function renderCase(){
 const d=state.data;main.replaceChildren();const head=el('header','case-head');head.append(el('div','eyebrow',d.id+' · '+d.turns.length+' 轮实际对话'),el('h1','',d.title),para('按发生顺序往下读。关键参数直接显示，细节按需展开。','intro'));main.append(head);
 const nav=el('nav','turn-nav');nav.setAttribute('aria-label','跳到某一轮');for(const t of d.turns){const a=el('a','','第 '+t.number+' 轮');a.href=route(state.batch,d.id,t.number);a.dataset.turn=t.number;a.onclick=e=>{e.preventDefault();scrollToTurn(t.number);};nav.append(a);}const copy=btn('复制链接',async()=>{try{await navigator.clipboard.writeText(location.href);notice('已复制当前链接');}catch{notice(location.href);}});nav.append(copy);main.append(nav);
 if(d.kind==='complex')main.append(para('本案例只确认需求并提交任务参数，未执行取数或分析。','scope-note'));
 if(d.kind==='knowledge')main.append(para(d.knowledge_profile==='with_definition'?'本组工具中有相关业务定义，下面可看 Agent 是否实际检索。':'本组没有该业务别名的定义，下面保留实际检索和回复。','scope-note'));
 if(d.history?.length){const history=el('div');for(const m of d.history){if(typeof m.content==='string')history.append(chat(['user','human'].includes(m.role)?'user':'assistant',m.content));else history.append(objectView(m));}main.append(details('案例开始前的对话（预设背景）',history,true));}
 for(const turn of d.turns){
  const section=el('section','turn');section.id='turn-'+turn.number;section.append(el('h2','turn-heading','第 '+turn.number+' 轮'));
  if(turn.input_origin==='simulated_user')section.append(simulatedUserView(turn.simulated_user));
  const user=chat('user',turn.question);if(turn.input_origin)user.querySelector('.chat-label').textContent=turn.input_origin==='simulated_user'?'AI 模拟用户 · 实际发送':'测试初始需求';section.append(user);
  const activity=el('div','activity');activity.append(el('div','activity-label','中间发生了什么'));
  const items=turn.timeline||[];if(!items.length)activity.append(para('没有记录到中间工具操作。','muted'));
  items.forEach((item,i)=>activity.append(actionCard(item,turn,i)));section.append(activity,replyView(turn));
  const extras=el('div','turn-extras');extras.append(reviewView(turn),technicalView(turn));section.append(extras);main.append(section);
 }
 if(d.simulation?.protocol){
  main.append(para(d.simulation.finished?'对话已停止：'+d.simulation.stop_reason:'AI用户多轮实验仍在进行。','scope-note'));
  const actor=d.simulation.last_user_decision;if(d.simulation.finished&&actor){main.append(para('最后一次 AI 用户决定（未再发送给被测 Agent）；停止不代表测试通过。','subtle'),simulatedUserView(actor));}
 }
 if(d.skipped?.length){const body=el('div');for(const s of d.skipped)body.append(para('第 '+s.number+' 轮（未发送）：'+s.question));main.append(details('尚未执行的后续测试消息（'+d.skipped.length+' 条）',body));}
 const meta=el('div');if(d.simulation?.protocol)meta.append(fields([['合计请求',number(d.usage.calls)+' 次'],['被测助手',number(d.assistant_usage.calls)+' 次'],['AI 模拟用户',number(d.simulation.user_usage.calls)+' 次']]));meta.append(objectView({batch:d.batch,model:d.model,usage:d.usage,frozen:d.frozen,guidance:d.guidance,review_note:d.review_note}));main.append(details('关于这次实验与费用',meta),para('页面读取已有记录，浏览和刷新不会调用模型。','footnote'));
 const params=new URL(location.href).searchParams;const n=Number(params.get('turn'))||d.turns[0]?.number;const step=params.get('step');
 requestAnimationFrame(()=>{
  if(step){const node=document.getElementById('step-'+n+'-'+step)||document.getElementById('technical-'+n+'-'+step);if(node){let parent=node;while(parent){if(parent.tagName==='DETAILS')parent.open=true;parent=parent.parentElement;}node.classList.add('linked-step');node.scrollIntoView({block:'start'});return;}}
  if(params.has('turn'))scrollToTurn(n,false);else window.scrollTo(0,0);
 });
}
async function init(){
 const parts=location.pathname.split('/').filter(Boolean).map(decodeURIComponent);const params=new URL(location.href).searchParams;
 const selected=parts[0]==='case'?parts[1]:params.get('batch');
 // 单题链接先读目标题，批次列表与侧栏稍后加载，不被其他记录拖住。
 if(parts[0]==='case'&&parts[2]){
  state.batch=selected;state.overview=null;state.batches=[];
  await loadCase(parts[2],false);
  if(!state.data)return;
  refreshSidebar(selected);return;
 }
 try{state.batches=(await api('/api/batches')).batches;$('#batch').replaceChildren(...state.batches.map(b=>{const o=el('option','',batchLabel(b));o.value=b.id;return o;}));
  const batch=selected||state.batches[0]?.id;
  if(!batch){main.replaceChildren(para('还没有可读取的实验记录。'));return;}await loadBatch(batch,parts[0]==='case'?parts[2]:null);
 }catch(e){showError(e);}
}
async function refreshSidebar(batch){
 try{
  const [listing,overview]=await Promise.all([api('/api/batches'),api('/api/batch',{batch})]);
  if(state.batch!==batch)return;state.batches=listing.batches;state.overview=overview;
  $('#batch').replaceChildren(...state.batches.map(b=>{const o=el('option','',batchLabel(b));o.value=b.id;return o;}));$('#batch').value=batch;renderSide();
 }catch(error){if(state.batch===batch){const note=para('案例已打开；案例列表暂时未读取：'+error.message,'banner');$('#cases').replaceChildren(note);}}
}
$('#batch').onchange=()=>loadBatch($('#batch').value);$('#search').oninput=renderSide;
for(const b of document.querySelectorAll('[data-filter]'))b.onclick=()=>{state.filter=b.dataset.filter;for(const x of document.querySelectorAll('[data-filter]'))x.classList.toggle('active',x===b);renderSide();};
$('#refresh').onclick=init;window.addEventListener('popstate',init);
$('#toggle-cases').onclick=()=>{const open=document.body.classList.toggle('cases-open');$('#toggle-cases').setAttribute('aria-expanded',String(open));};
window.addEventListener('keydown',e=>{if(e.key==='Escape'){document.body.classList.remove('cases-open');$('#toggle-cases').setAttribute('aria-expanded','false');}});
init();
