/* Decision Bench viewer. Plain ES module, no dependencies.
   Reads data.json (schema 2, from `python3 -m decision_bench report`), datasets.json and protocol.txt.
   Every view has a shareable URL: #/, #/tasks, #/task/<id>, #/row/<id>, #/models, #/model/<id>, #/compare,
   #/data, #/data/<dataset>, #/methodology, #/review/<row>. Filters live in the query string after the path. */

/* ---------- Utilities ---------- */
const $=s=>document.querySelector(s);
const $$=s=>[...document.querySelectorAll(s)];
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=v=>v==null?'—':`${(v*100).toFixed(1)}%`;
const pct0=v=>v==null?'—':`${Math.round(v*100)}%`;
const pp=v=>`${v>=0?'+':'−'}${Math.abs(v*100).toFixed(1)}`;
const num=v=>v==null?'—':Number(v).toLocaleString('en-US',{maximumFractionDigits:2});
const metric=v=>v==null?'—':Number(v).toFixed(3);
const ms=v=>v==null?'—':v>=1000?`${(v/1000).toFixed(v>=10000?1:2)} s`:`${v.toFixed(0)} ms`;
const secs=v=>v>=10?`${v.toFixed(0)}s`:v>=1?`${v.toFixed(1)}s`:v>=.01?`${v.toFixed(2)}s`:`${(v*1000).toFixed(0)}ms`;
const money=v=>v==null?'—':`$${v<.01?v.toFixed(5):v<1?v.toFixed(3):v.toFixed(2)}`;
const compact=v=>v==null||!isFinite(v)?'—':v>=1e6?`${(v/1e6).toFixed(2)}M`:v>=1e4?`${(v/1e3).toFixed(1)}K`:Math.round(v).toLocaleString('en-US');
const human=l=>l==null?'no answer':String(l).replaceAll('_',' ');
const plural=(n,w,p=w+'s')=>`${num(n)} ${n===1?w:p}`;
const clip=(t,n)=>t.length>n?t.slice(0,Math.max(1,n-1))+'…':t;
const slug=s=>String(s||'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
const firstSentence=t=>{const s=String(t||'').trim(),m=s.match(/^.*?[.?!](\s|$)/);return (m?m[0]:s).trim();};
const ciText=ci=>ci?`${(ci[0]*100).toFixed(0)}–${(ci[1]*100).toFixed(0)}%`:'';
const cap=s=>s?s[0].toUpperCase()+s.slice(1):s;
const REPO=(document.querySelector('meta[name="repo"]')?.content||'').replace(/\/+$/,'');
const gh=path=>`${REPO}/blob/main/${path}`;
const ghIssue=(template,params={})=>`${REPO}/issues/new?template=${template}${Object.entries(params).map(([k,v])=>`&${k}=${encodeURIComponent(v)}`).join('')}`;
const ext=(href,html)=>href?`<a href="${esc(href)}" target="_blank" rel="noopener">${html}</a>`:html;

/* ---------- Routing helpers: every state is a URL ---------- */
const route={page:'home',id:'',q:new URLSearchParams()};
const href=(path,params={})=>{const q=new URLSearchParams();for(const [k,v] of Object.entries(params))if(v!==''&&v!=null)q.set(k,v);const s=q.toString();return `#/${path}${s?`?${s}`:''}`;};
const withQ=(patch)=>{const q=new URLSearchParams(route.q);for(const [k,v] of Object.entries(patch)){if(v===''||v==null)q.delete(k);else q.set(k,v);}const s=q.toString();return `#/${[route.page==='home'?'':route.page,route.id].filter(Boolean).join('/')}${s?`?${s}`:''}`;};
const go=hash=>{if(location.hash!==hash)location.hash=hash;else render();};

/* ---------- State ---------- */
let data,datasetsDoc=null,protocolText=null,caseMap=new Map(),recordMap=new Map(),allCases=[];
let RUNS=[],PARTIAL=[];
let sort={key:'accuracy',dir:'desc'},moreCols=false,popOpen=false,rowsShown=40;
let viz=[],vizSeq=0;
const statCache=new Map(),metricCache=new Map();
const man=()=>data?.manifest||{};

/* ---------- Model identity: label, colour, vendor logo and interface come from data.json models[] ---------- */
const IFACE={'openai-compatible':'API',typesafe:'API','claude-cli':'Claude Code CLI','codex-cli':'Codex CLI'};
const PALETTE=['#2563eb','#7c3aed','#0f766e','#d97706','#db2777','#0891b2','#65a30d','#c2410c','#6d28d9','#475569'];
const LOGOS={google:'google.com',anthropic:'anthropic.com',openai:'openai.com',deepseek:'deepseek.com','z.ai':'z.ai',zhipu:'z.ai',qwen:'qwen.ai',alibaba:'alibabacloud.com',amazon:'amazon.com',aws:'amazon.com',typesafe:'typesafe.ai'};
let MODELS={},ORDER=[];
function registerModel(m,configured){
 if(!m?.id||MODELS[m.id])return;
 const hash=[...m.id].reduce((n,c)=>(n*31+c.charCodeAt(0))>>>0,0),vendor=m.vendor||'';
 const logo=LOGOS[vendor.toLowerCase()];
 MODELS[m.id]={id:m.id,name:m.label||m.id,short:m.short_label||m.label||m.id,vendor,iface:IFACE[m.provider]||m.provider||'',provider:m.provider,color:m.color||PALETTE[hash%PALETTE.length],logo:logo?`assets/logos/${logo}.png`:null,vision:!!m.vision,configured,api_model:m.api_model,request:m.request,pricing:m.pricing};
 ORDER.push(m.id);
}
const keyOf=r=>r.model_id||r.model?.id||r.config?.model_id;
const M=k=>MODELS[k]||{id:k,name:k,short:k,iface:'',vendor:'',color:'var(--faint)',logo:null};
const ident=r=>M(keyOf(r));
const fullName=k=>M(k).iface&&M(k).iface!=='API'?`${M(k).name} · ${M(k).iface}`:M(k).name;
const runName=r=>fullName(keyOf(r));
const runColor=r=>ident(r).color;
const byOrder=(a,b)=>ORDER.indexOf(keyOf(a))-ORDER.indexOf(keyOf(b));
const dotHtml=k=>`<i class="dot" style="background:${esc(M(k).color)}"></i>`;
const logoHtml=k=>{const m=M(k);return m.logo?`<img class="logo" src="${esc(m.logo)}" alt="" width="18" height="18" loading="lazy">`:dotHtml(k);};
/* One line per model: vendor logo, name, and the interface only when it is not a plain API. */
function modelHtml(k,{sub=true,link=true}={}){const m=M(k);const inner=`${logoHtml(k)}<span class="m-name">${esc(m.name)}</span>${sub&&m.iface&&m.iface!=='API'?`<span class="m-if">${esc(m.iface)}</span>`:''}`;return link?`<a class="m" href="${href(`model/${encodeURIComponent(k)}`)}">${inner}</a>`:`<span class="m">${inner}</span>`;}

/* ---------- Runs: completed runs on the current corpus, one per model ---------- */
function collectRuns(){
 const by=new Map();
 for(const r of data.runs||[]){
  if(r.config?.corpus_sha256!==data.corpus_sha256||r.current_corpus===false)continue;
  if(!String(r.status||'').startsWith('completed'))continue;
  const k=keyOf(r),o=by.get(k);
  if(!o||r.metrics.cases>o.metrics.cases||(r.metrics.cases===o.metrics.cases&&String(r.completed_at||'')>String(o.completed_at||'')))by.set(k,r);
 }
 const all=[...by.values()].sort(byOrder);
 RUNS=all.filter(r=>r.coverage?.full!==false);
 PARTIAL=all.filter(r=>r.coverage?.full===false);
}
const hasResults=()=>RUNS.length>0;
const result=(runId,caseId)=>recordMap.get(`${runId}:${caseId}`);
const okOf=v=>!!v&&v.scores.length>0&&v.scores.every(s=>s.correct);
const answered=v=>!!v&&v.scores.some(s=>s.label!=null);

/* ---------- Corpus vocabulary: category › task › row ---------- */
const catKey=c=>c.category;
const catName=c=>c.category_name||man().categories?.[c.category]?.name||c.category;
const taskInfo=t=>man().tasks?.[t]||{};
const taskName=t=>taskInfo(t).name||allCases.find(c=>c.task===t)?.task_name||t;
const taskAsk=t=>taskInfo(t).ask||allCases.find(c=>c.task===t)?.questions[0].ask||'';
const taskCat=t=>taskInfo(t).category||allCases.find(c=>c.task===t)?.category;
const taskRows=t=>allCases.filter(c=>c.task===t);
const taskModality=t=>taskInfo(t).modality||(taskRows(t).some(c=>c.assets?.length)?'image':'text');
const isImageTask=t=>taskModality(t)!=='text';
const caseTitle=c=>c.title||c.id;
const askOf=q=>q.ask||null;
const optionOrder=q=>(q.option_order&&q.option_order.length?q.option_order:Object.keys(q.options));
const origLabel=v=>v==null?'none':Array.isArray(v)?(v.length?v.map(x=>typeof x==='object'?JSON.stringify(x):String(x)).join(', '):'none'):typeof v==='object'?JSON.stringify(v):String(v);
function categoryOrder(){const m=man().categories,keys=m?Object.keys(m):[];for(const c of allCases)if(!keys.includes(catKey(c)))keys.push(catKey(c));return keys.filter(k=>allCases.some(c=>catKey(c)===k));}
function catInfo(k){const m=man().categories?.[k],c=allCases.find(x=>catKey(x)===k);return {name:m?.name||(c&&catName(c))||k,description:m?.description||''};}
function taskOrder(){const t=man().tasks,keys=t?Object.keys(t):[];for(const c of allCases)if(!keys.includes(c.task))keys.push(c.task);const co=categoryOrder();return keys.filter(t=>allCases.some(c=>c.task===t)).sort((a,b)=>co.indexOf(taskCat(a))-co.indexOf(taskCat(b))||keys.indexOf(a)-keys.indexOf(b));}
function rowsInOrder(){const co=categoryOrder(),to=taskOrder();return allCases.map((c,i)=>[c,i]).sort(([a,i],[b,j])=>co.indexOf(catKey(a))-co.indexOf(catKey(b))||to.indexOf(a.task)-to.indexOf(b.task)||i-j).map(([c])=>c);}
const goldText=c=>{const q=c.questions[0],g=q.gold;return String(g).length<=2&&q.options?.[g]?`${g}: ${clip(String(q.options[g]),42)}`:human(g);};
const rowHref=c=>href(`row/${encodeURIComponent(c.id)}`);
const taskHref=t=>href(`task/${encodeURIComponent(t)}`);
const catHref=k=>href('',{category:k});
const assetUrl=a=>String(a.path||'').replace(/^data\/assets\//,'assets/rows/');

/* ---------- Datasets: datasets.json when present, else derived from the rows' source fields ---------- */
let DATASETS=[];const dsByRow=new Map();
const normName=s=>String(s||'').toLowerCase().replace(/\s+/g,' ').trim();
const normUrl=u=>String(u||'').toLowerCase().replace(/^https?:\/\/(www\.)?/,'').replace(/\/+$/,'');
function indexDatasets(){
 DATASETS=(datasetsDoc?.datasets||[]).map(d=>({...d,id:d.id||slug(d.name),tasks:[...(d.tasks||[])],rows:[],derived:false}));
 const byId=new Map(DATASETS.map(d=>[d.id,d])),byName=new Map(DATASETS.map(d=>[normName(d.name),d])),byHome=new Map(DATASETS.filter(d=>d.homepage).map(d=>[normUrl(d.homepage),d]));
 dsByRow.clear();
 for(const c of allCases){
  const s=c.source;if(!s)continue;
  let d=byId.get(s.dataset_id)||byName.get(normName(s.dataset))||byHome.get(normUrl(s.url));
  if(!d){const id=s.dataset_id||slug(s.dataset)||'unknown';d={id,name:s.dataset||id,homepage:s.url,license:s.license,labelled_by:s.labelled_by,citation:s.citation,tasks:[],rows:[],derived:true};DATASETS.push(d);byId.set(id,d);byName.set(normName(d.name),d);}
  d.rows.push(c);dsByRow.set(c.id,d);
 }
 for(const d of DATASETS)for(const c of d.rows)if(!d.tasks.includes(c.task))d.tasks.push(c.task);
 const to=taskOrder();
 for(const d of DATASETS)d.tasks.sort((a,b)=>to.indexOf(a)-to.indexOf(b));
 DATASETS.sort((a,b)=>to.indexOf(a.tasks[0])-to.indexOf(b.tasks[0]));
}
const dsLink=d=>d?`<a href="${href(`data/${encodeURIComponent(d.id)}`)}">${esc(d.name)}</a>`:'';
const dsOf=c=>dsByRow.get(c.id)||null;

/* ---------- Metrics recomputed in the browser for any subset of rows (a category, a task, a modality) ---------- */
function wilson(k,n,z=1.96){if(!n)return null;const p=k/n,d=1+z*z/n,c=(p+z*z/(2*n))/d,h=z*Math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d;return [Math.max(0,c-h),Math.min(1,c+h)];}
function quantile(vals,q){const a=vals.filter(v=>v!=null).sort((x,y)=>x-y);if(!a.length)return null;const i=(a.length-1)*q,lo=Math.floor(i),hi=Math.ceil(i);return a[lo]+(a[hi]-a[lo])*(i-lo);}
const meanOf=a=>{const b=a.filter(v=>v!=null);return b.length?b.reduce((x,y)=>x+y,0)/b.length:null;};
function subsetMetrics(run,cases){
 const key=`${run.id}|${cases.length}|${cases[0]?.id}|${cases.at(-1)?.id}`;
 if(metricCache.has(key))return metricCache.get(key);
 const recs=cases.map(c=>result(run.id,c.id)).filter(Boolean);
 const scores=recs.flatMap(r=>r.scores),n=scores.length,correct=scores.filter(s=>s.correct).length;
 const cost=recs.map(r=>r.cost_usd),known=cost.filter(v=>v!=null),tokIn=recs.map(r=>r.tokens?.input),tokOut=recs.map(r=>r.tokens?.output);
 const bins=[];for(let i=0;i<10;i++)bins.push({lo:i/10,hi:(i+1)/10,count:0,conf:0,acc:0});
 for(const s of scores){if(s.confidence==null)continue;const b=bins[Math.min(9,Math.floor(s.confidence*10))];b.count++;b.conf+=s.confidence;b.acc+=s.correct?1:0;}
 const withConf=scores.filter(s=>s.confidence!=null).length;
 const ece=withConf?bins.reduce((e,b)=>b.count?e+b.count/withConf*Math.abs(b.acc/b.count-b.conf/b.count):e,0):null;
 const m={cases:recs.length,questions:n,correct,accuracy:n?correct/n:null,wilson:wilson(correct,n),
  errors:recs.filter(r=>r.status!=='ok').length,highConfErrors:scores.filter(s=>!s.correct&&(s.confidence||0)>=.9).length,
  latency:{p50:quantile(recs.map(r=>r.duration_ms),.5),p95:quantile(recs.map(r=>r.duration_ms),.95),p99:quantile(recs.map(r=>r.duration_ms),.99)},
  costUsd:known.length?known.reduce((x,y)=>x+y,0):null,costCoverage:recs.length?known.length/recs.length:null,
  costPer1k:known.length?known.reduce((x,y)=>x+y,0)/known.length*1000:null,
  tokensIn:meanOf(tokIn),tokensOut:meanOf(tokOut),
  brier:meanOf(scores.map(s=>s.brier)),ece,
  bins:bins.map(b=>({...b,confidence:b.count?b.conf/b.count:null,accuracy:b.count?b.acc/b.count:null}))};
 metricCache.set(key,m);return m;
}
const macroF1=(run,tasks)=>meanOf(tasks.map(t=>{const rows=taskRows(t).map(c=>result(run.id,c.id)).filter(Boolean).flatMap(r=>r.scores);if(!rows.length)return null;const labels=new Set(rows.flatMap(s=>[s.gold,s.label].filter(x=>x!=null)));const fs=[...labels].map(l=>{const tp=rows.filter(s=>s.gold===l&&s.label===l).length,fp=rows.filter(s=>s.gold!==l&&s.label===l).length,fn=rows.filter(s=>s.gold===l&&s.label!==l).length;return 2*tp+fp+fn?2*tp/(2*tp+fp+fn):0;});return meanOf(fs);}));
/* Fit verdict: the plain answer to "can I use this model for this task?" */
function verdict(m){if(!m||m.accuracy==null||!m.questions)return {k:'na',t:'Not run'};const [lo]=m.wilson;if(m.accuracy>=.9&&lo>=.85)return {k:'ok',t:'Fits'};if(m.accuracy>=.8)return {k:'risk',t:'Risky'};return {k:'no',t:'Not fit'};}
const fitHtml=v=>`<span class="fit ${v.k}">${v.t}</span>`;

/* ---------- Per-row statistics across evaluated models ---------- */
function caseStats(c){
 if(statCache.has(c.id))return statCache.get(c.id);
 let n=0,ok=0;const wrong={},dots=[];
 for(const r of RUNS){const v=result(r.id,c.id);if(!v)continue;n++;const good=okOf(v);if(good)ok++;else{const l=v.scores[0]?.label??null;wrong[l]=(wrong[l]||0)+1;}dots.push({k:keyOf(r),ok:good});}
 const st={n,ok,wrong,dots};statCache.set(c.id,st);return st;
}
const dotStrip=st=>`<span class="strip" aria-hidden="true">${st.dots.map(d=>`<i class="${d.ok?'':'x'}" title="${esc(fullName(d.k))}: ${d.ok?'correct':'wrong'}"></i>`).join('')}</span>`;
const correctCell=st=>st.n?`<span class="mc"><span class="num">${st.ok}/${st.n}</span>${dotStrip(st)}</span>`:'<span class="muted">—</span>';

/* ---------- Tooltip ---------- */
const tipAttr=(html,focus=true)=>` data-tip="${esc(html)}"${focus?' tabindex="0"':''}`;
const tipBody=(title,rows)=>`<strong>${esc(title)}</strong>${rows.map(([k,v])=>`<div class="row"><span>${esc(k)}</span><span>${esc(v)}</span></div>`).join('')}`;
function placeTip(x,y){const t=$('#tip'),b=t.getBoundingClientRect();let l=x+14,tp=y+14;if(l+b.width>innerWidth-8)l=x-b.width-14;if(tp+b.height>innerHeight-8)tp=y-b.height-14;t.style.left=`${Math.max(8,l)}px`;t.style.top=`${Math.max(8,tp)}px`;}
function showTip(el,x,y){const t=$('#tip');t.innerHTML=el.getAttribute('data-tip');t.hidden=false;placeTip(x,y);}
document.addEventListener('pointerover',e=>{const el=e.target.closest?.('[data-tip]');if(el)showTip(el,e.clientX,e.clientY);});
document.addEventListener('pointermove',e=>{if(!$('#tip').hidden&&e.target.closest?.('[data-tip]'))placeTip(e.clientX,e.clientY);});
document.addEventListener('pointerout',e=>{const el=e.target.closest?.('[data-tip]');if(el&&!el.contains(e.relatedTarget))$('#tip').hidden=true;});
document.addEventListener('focusin',e=>{const el=e.target.closest?.('[data-tip]');if(el){const b=el.getBoundingClientRect();showTip(el,b.right,b.bottom);}});
document.addEventListener('focusout',()=>{$('#tip').hidden=true;});
addEventListener('scroll',()=>{$('#tip').hidden=true;},{passive:true});
document.addEventListener('click',e=>{const p=$('.models-pop');if(p&&p.open&&!p.contains(e.target)){p.open=false;popOpen=false;}});

/* ---------- Chart primitives (drawn at the container's measured width) ---------- */
function vizBox(draw,label,cls=''){const id=`viz-${++vizSeq}`;viz.push({id,draw,w:0});return `<div class="viz ${cls}" id="${id}" role="img" aria-label="${esc(label)}"></div>`;}
function drawViz(force){for(const v of viz){const el=document.getElementById(v.id);if(!el)continue;const w=Math.max(220,Math.floor(el.clientWidth));if(!force&&w===v.w)continue;v.w=w;el.innerHTML=v.draw(w);}}
let resizeTimer;addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>drawViz(false),120);});
const DEFS='<defs><pattern id="hatch" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="4" height="4" style="fill:var(--bg)"/><line x1="0" y1="0" x2="0" y2="4" style="stroke:var(--bad);stroke-width:1.5"/></pattern></defs>';
const svg=(w,h,body)=>`<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" aria-hidden="true">${DEFS}${body}</svg>`;
const lin=(d0,d1,r0,r1)=>v=>r0+(v-d0)/(d1-d0||1)*(r1-r0);
const logS=(d0,d1,r0,r1)=>v=>r0+(Math.log10(v)-Math.log10(d0))/(Math.log10(d1)-Math.log10(d0)||1)*(r1-r0);
function niceStep(range,count){const raw=range/count||1,mag=10**Math.floor(Math.log10(raw)),n=raw/mag;return (n<=1?1:n<=2?2:n<=2.5?2.5:n<=5?5:10)*mag;}
function niceTicks(lo,hi,count=4){const st=niceStep(hi-lo,count),a=Math.floor(lo/st+1e-9)*st,out=[];for(let v=a;v<=hi+st*.999;v+=st)out.push(+v.toFixed(10));return out;}
function logDomain(vals){const pos=vals.filter(v=>v>0);if(!pos.length)return [.1,1];const lo=10**Math.floor(Math.log10(Math.min(...pos))),hi=10**Math.ceil(Math.log10(Math.max(...pos)));return [lo,hi===lo?hi*10:hi];}
function logTicks([lo,hi]){const out=[];for(let d=lo;d<=hi*1.0001;d*=10)for(const m of [1,2,5])if(d*m<=hi*1.0001)out.push({v:d*m,major:m===1});return out;}
function zoomDomain(vals,step=.05){const lo=Math.max(0,Math.floor((Math.min(...vals)-.02)/step)*step);return [+lo.toFixed(4),1];}
const labelSvg=(k,x,cy,maxW)=>`<circle cx="${x+4}" cy="${cy}" r="3.5" style="fill:${esc(M(k).color)}"/><text class="t-ink" x="${x+13}" y="${cy+4}">${esc(clip(M(k).short,Math.floor((maxW-13)/6.4)))}</text>`;
const legend=items=>`<div class="legend">${items.map(([kind,color,label])=>`<span><i class="key-${kind}" style="${kind==='box'?`border-color:${color}`:`background:${color}`}"></i>${esc(label)}</span>`).join('')}</div>`;

/* Horizontal bars, one row per model. items: {key,value,lo?,hi?,tick?,color,tip,ghost?} */
function rowsChart(items,{fmt,tickFmt=fmt,max,min=0}){return w=>{
 const L=Math.min(132,Math.max(112,w*.3)),R=56,T=2,B=22,rowH=22,h=T+B+items.length*rowH,pw=w-L-R;
 const vals=items.flatMap(i=>i.value==null?[]:[i.value,i.hi??0,i.tick??0]);
 const ticks=niceTicks(min,max??Math.max(...vals,1e-9),pw<200?2:4).filter(t=>t>=min-1e-9),top=max??ticks.at(-1),x=lin(min,top,L,L+pw);
 let s=ticks.map(t=>`<line class="grid" x1="${x(t)}" x2="${x(t)}" y1="${T}" y2="${h-B}"/><text x="${x(t)}" y="${h-B+15}" text-anchor="middle">${esc(tickFmt(t))}</text>`).join('');
 items.forEach((it,i)=>{const cy=T+rowH*(i+.5);
  s+=`<g${tipAttr(it.tip,false)}><rect class="hit" x="0" y="${cy-rowH/2}" width="${w}" height="${rowH}"/>${labelSvg(it.key,0,cy,L-6)}`;
  if(it.value==null)s+=`<text x="${L}" y="${cy+4}">${esc(it.ghost||'—')}</text>`;
  else{const xe=Math.max(x(it.value),L+1);s+=`<rect x="${L}" y="${cy-4}" width="${xe-L}" height="8" rx="1.5" style="fill:${esc(it.color)}"/>`;
   if(it.lo!=null)s+=`<path d="M${x(it.lo)} ${cy}H${x(it.hi)}M${x(it.lo)} ${cy-4}v8M${x(it.hi)} ${cy-4}v8" class="whisker"/>`;
   if(it.tick!=null)s+=`<path d="M${x(it.tick)} ${cy-6}v12" class="whisker"/>`;
   s+=`<text class="t-value" x="${Math.max(xe,it.hi!=null?x(it.hi):0,it.tick!=null?x(it.tick):0)+6}" y="${cy+4}">${esc(fmt(it.value))}</text>`;}
  s+='</g>';});
 return svg(w,h,s);};}

/* Scatter with short-name labels placed to avoid collisions. items: {key,x,y,lo,hi,color,tip} */
function scatter(items,{xFmt,xLabel}){return w=>{
 const h=340,L=44,R=16,T=14,B=40,pw=w-L-R,ph=h-T-B;
 if(!items.length)return svg(w,h,`<text x="${w/2}" y="${h/2}" text-anchor="middle">No model has complete data for this view</text>`);
 const [x0,x1]=logDomain(items.map(i=>i.x)),x=logS(x0,x1,L,L+pw);
 const [y0]=zoomDomain(items.map(i=>i.lo),.05),y=lin(y0,1,T+ph,T);
 let s=niceTicks(y0,1,4).filter(t=>t>=y0-1e-9).map(t=>`<line class="grid" x1="${L}" x2="${L+pw}" y1="${y(t)}" y2="${y(t)}"/><text x="${L-6}" y="${y(t)+4}" text-anchor="end">${pct0(t)}</text>`).join('');
 s+=logTicks([x0,x1]).map(t=>`<line class="grid${t.major?'':' minor'}" x1="${x(t.v)}" x2="${x(t.v)}" y1="${T}" y2="${T+ph}"/>${t.major||pw>420?`<text x="${x(t.v)}" y="${T+ph+16}" text-anchor="middle">${esc(xFmt(t.v))}</text>`:''}`).join('');
 s+=`<line class="axis" x1="${L}" x2="${L+pw}" y1="${T+ph}" y2="${T+ph}"/><text x="${L+pw}" y="${h-4}" text-anchor="end">${esc(xLabel)} (log scale)</text>`;
 const pts=items.map(it=>({...it,px:x(it.x),py:y(it.y)})),boxes=pts.map(p=>({x0:p.px-4,x1:p.px+4,y0:p.py-4,y1:p.py+4}));
 const hit=b=>boxes.some(o=>b.x0<o.x1&&b.x1>o.x0&&b.y0<o.y1&&b.y1>o.y0);
 let marks='',labels='';
 for(const p of pts.slice().sort((a,b)=>a.py-b.py)){
  const t=M(p.key).short,tw=t.length*6.4+2;
  const cands=[[p.px+7,p.py+4,'start'],[p.px-7,p.py+4,'end'],[p.px,p.py-8,'middle'],[p.px,p.py+16,'middle'],[p.px+7,p.py+15,'start'],[p.px+7,p.py-6,'start'],[p.px-7,p.py-6,'end'],[p.px-7,p.py+15,'end']];
  let pick=null;for(const [lx,ly,a] of cands){const bx0=a==='start'?lx:a==='end'?lx-tw:lx-tw/2,b={x0:bx0,x1:bx0+tw,y0:ly-10,y1:ly+2};if(b.x0<L||b.x1>w||b.y0<0||b.y1>T+ph)continue;if(!hit(b)){pick=[lx,ly,a,b];break;}}
  if(pick){boxes.push(pick[3]);labels+=`<text class="t-ink" x="${pick[0]}" y="${pick[1]}" text-anchor="${pick[2]}">${esc(t)}</text>`;}
  marks+=`<g${tipAttr(p.tip)}><circle class="hit" cx="${p.px}" cy="${p.py}" r="12"/><path d="M${p.px} ${y(p.lo)}V${y(p.hi)}" style="stroke:${esc(p.color)};stroke-width:1.5;stroke-opacity:.45"/><circle cx="${p.px}" cy="${p.py}" r="4" style="fill:${esc(p.color)}"/></g>`;}
 return svg(w,h,s+marks+labels);};}

/* Reliability and risk–coverage from recomputed bins and scores. */
function reliabilityChart(rs,cases,focus){return w=>{
 const h=Math.min(w,400)*.8,L=40,R=10,T=10,B=36,pw=w-L-R,ph=h-T-B,x=lin(0,1,L,L+pw),y=lin(0,1,T+ph,T);
 let s=[0,.25,.5,.75,1].map(t=>`<line class="grid" x1="${L}" x2="${L+pw}" y1="${y(t)}" y2="${y(t)}"/><text x="${L-6}" y="${y(t)+4}" text-anchor="end">${pct0(t)}</text><text x="${x(t)}" y="${T+ph+16}" text-anchor="middle">${pct0(t)}</text>`).join('');
 s+=`<line class="ref" x1="${x(0)}" y1="${y(0)}" x2="${x(1)}" y2="${y(1)}"/><line class="axis" x1="${L}" x2="${L+pw}" y1="${T+ph}" y2="${T+ph}"/><text x="${L+pw}" y="${h-3}" text-anchor="end">Stated confidence → observed accuracy</text>`;
 for(const r of rs){const bins=subsetMetrics(r,cases).bins.filter(b=>b.count),foc=focus.includes(keyOf(r));const pts=bins.map(b=>`${x(b.confidence)},${y(b.accuracy)}`).join(' ');
  if(!foc){s+=`<polyline class="ghost-line" points="${pts}"/>`;continue;}
  s+=`<polyline points="${pts}" style="fill:none;stroke:${esc(runColor(r))};stroke-width:2"/>`+bins.map(b=>`<g${tipAttr(tipBody(runName(r),[['Confidence bin',`${pct0(b.lo)}–${pct0(b.hi)}`],['Decisions',b.count],['Mean confidence',pct(b.confidence)],['Accuracy',pct(b.accuracy)]]),false)}><circle class="hit" cx="${x(b.confidence)}" cy="${y(b.accuracy)}" r="10"/><circle cx="${x(b.confidence)}" cy="${y(b.accuracy)}" r="${Math.min(7,2.5+Math.sqrt(b.count)/2.5)}" style="fill:${esc(runColor(r))};stroke:var(--bg);stroke-width:1"/></g>`).join('');}
 return svg(w,h,s);};}
function riskPoints(r,cases){const sc=cases.map(c=>result(r.id,c.id)).filter(Boolean).flatMap(v=>v.scores).filter(s=>s.confidence!=null).sort((a,b)=>b.confidence-a.confidence);const out=[];let wrong=0;sc.forEach((s,i)=>{if(!s.correct)wrong++;if(i%Math.max(1,Math.floor(sc.length/40))===0||i===sc.length-1)out.push({coverage:(i+1)/sc.length,risk:wrong/(i+1),threshold:s.confidence,accepted:i+1,errors:wrong});});return out;}
function riskChart(rs,cases,focus){return w=>{
 const h=Math.min(w,400)*.8,L=40,R=10,T=10,B=36,pw=w-L-R,ph=h-T-B;
 const all=rs.map(r=>riskPoints(r,cases)),maxRisk=Math.max(.05,...all.flat().map(p=>p.risk)),top=niceTicks(0,maxRisk,4).at(-1),x=lin(0,1,L,L+pw),y=lin(0,top,T+ph,T);
 let s=niceTicks(0,top,4).map(t=>`<line class="grid" x1="${L}" x2="${L+pw}" y1="${y(t)}" y2="${y(t)}"/><text x="${L-6}" y="${y(t)+4}" text-anchor="end">${pct0(t)}</text>`).join('')+[0,.25,.5,.75,1].map(t=>`<text x="${x(t)}" y="${T+ph+16}" text-anchor="middle">${pct0(t)}</text>`).join('');
 s+=`<line class="axis" x1="${L}" x2="${L+pw}" y1="${T+ph}" y2="${T+ph}"/><text x="${L+pw}" y="${h-3}" text-anchor="end">Share of decisions accepted (most confident first)</text><text x="${L+4}" y="${T+10}">Error rate among accepted</text>`;
 rs.forEach((r,i)=>{const ps=all[i],foc=focus.includes(keyOf(r)),pts=ps.map(p=>`${x(p.coverage)},${y(p.risk)}`).join(' ');
  if(!foc){s+=`<polyline class="ghost-line" points="${pts}"/>`;return;}
  s+=`<polyline points="${pts}" style="fill:none;stroke:${esc(runColor(r))};stroke-width:2"/>`+ps.filter((_,j)=>j%5===0||j===ps.length-1).map(p=>`<g${tipAttr(tipBody(runName(r),[['Threshold',p.threshold.toFixed(2)],['Accepted',`${p.accepted} (${pct(p.coverage)})`],['Wrong among accepted',`${p.errors} (${pct(p.risk)})`]]),false)}><circle class="hit" cx="${x(p.coverage)}" cy="${y(p.risk)}" r="10"/><circle cx="${x(p.coverage)}" cy="${y(p.risk)}" r="3" style="fill:${esc(runColor(r))}"/></g>`).join('');});
 return svg(w,h,s);};}

/* ---------- Heatmaps: faded when ≥95%, colour only the misses ---------- */
const heatClass=a=>a>=.95?'h0':a>=.9?'h1':a>=.8?'h2':a>=.65?'h3':'h4';
const heatLegend=()=>`<div class="legend heat-legend"><span><i class="cell h0"></i>≥ 95%</span><span><i class="cell h1"></i>90–95</span><span><i class="cell h2"></i>80–90</span><span><i class="cell h3"></i>65–80</span><span><i class="cell h4"></i>&lt; 65</span><span><i class="cell h0"></i>— not run</span></div>`;
function heatCell(r,m,label,link){if(!m||!m.questions)return '<td class="hc na">—</td>';const inner=m.accuracy>=.995?'100':(m.accuracy*100).toFixed(m.accuracy>=.1?0:1);return `<td class="hc ${heatClass(m.accuracy)}"${tipAttr(tipBody(`${runName(r)} · ${label}`,[['Accuracy',pct(m.accuracy)],['95% interval',ciText(m.wilson)],['Correct',`${m.correct}/${m.questions}`]]),false)}>${link?`<a href="${link}" style="color:inherit">${inner}</a>`:inner}</td>`;}
/* Models as rows, categories as columns. */
function heatCategories(rs,cases){
 const cats=categoryOrder().filter(k=>cases.some(c=>catKey(c)===k));
 return `<div class="table-wrap"><table class="heat"><thead><tr><th class="sticky">Model</th>${cats.map(k=>`<th class="hc"><a href="${catHref(k)}">${esc(catInfo(k).name)}</a><span class="sub">${cases.filter(c=>catKey(c)===k).length}</span></th>`).join('')}</tr></thead><tbody>${rs.map(r=>`<tr><th class="sticky" scope="row">${modelHtml(keyOf(r),{sub:false})}</th>${cats.map(k=>heatCell(r,subsetMetrics(r,cases.filter(c=>catKey(c)===k)),catInfo(k).name)).join('')}</tr>`).join('')}</tbody></table></div>`;
}
/* Tasks as rows (grouped by category), models as columns. */
function heatTasks(rs,cases){
 const tasks=taskOrder().filter(t=>cases.some(c=>c.task===t));
 let last=null;
 return `<div class="table-wrap"><table class="heat wide"><thead><tr><th class="sticky">Task</th>${rs.map(r=>`<th class="hc mh" title="${esc(runName(r))}">${logoHtml(keyOf(r))}<span>${esc(ident(r).short)}</span></th>`).join('')}</tr></thead><tbody>${tasks.map(t=>{let g='';const cat=taskCat(t);if(cat!==last){last=cat;g=`<tr class="grp"><th class="sticky">${esc(catInfo(cat).name)}</th><td colspan="${rs.length}"></td></tr>`;}const tc=cases.filter(c=>c.task===t);return g+`<tr><th class="sticky" scope="row"><a class="t-link" href="${taskHref(t)}">${esc(taskName(t))}</a> <span class="tid">${tc.length}${isImageTask(t)?' · image':''}</span></th>${rs.map(r=>heatCell(r,subsetMetrics(r,tc),taskName(t))).join('')}</tr>`;}).join('')}</tbody></table></div>`;
}

/* ---------- Page scaffolding ---------- */
const pageHead=(title,sub,extra='')=>`<header class="page-head"><div><h1>${title}</h1>${sub?`<p class="lede">${sub}</p>`:''}</div>${extra}</header>`;
const section=(title,sub,body,{id='',aside=''}={})=>`<section class="sec"${id?` id="${id}"`:''}><div class="sec-head"><div><h2>${title}</h2>${sub?`<p>${sub}</p>`:''}</div>${aside?`<div class="aside">${aside}</div>`:''}</div>${body}</section>`;
const block=(title,sub,body,{aside='',foot=''}={})=>`<div class="block"><div class="block-head"><h3>${title}</h3>${aside?`<div class="aside">${aside}</div>`:''}</div>${sub?`<p class="help">${sub}</p>`:''}${body}${foot?`<p class="foot">${foot}</p>`:''}</div>`;
const seg=(label,items,attr,current)=>`<div class="seg" role="group" aria-label="${esc(label)}">${items.map(([v,l])=>`<button type="button" data-${attr}="${esc(v)}" aria-pressed="${v===current}">${esc(l)}</button>`).join('')}</div>`;
const selectHtml=(id,label,opts,cur)=>`<label class="sel"><span>${esc(label)}</span><select id="${id}">${opts.map(([v,l])=>`<option value="${esc(v)}"${v===cur?' selected':''}>${esc(l)}</option>`).join('')}</select></label>`;
const crumbs=items=>`<nav class="crumbs" aria-label="Breadcrumb">${items.map(([t,h],i)=>i<items.length-1?`<a href="${h}">${esc(t)}</a><span>›</span>`:`<span>${esc(t)}</span>`).join('')}</nav>`;
const howToAdd=()=>`Results are added by pull request: run a model on every row, publish the run into <code>results/</code>, and open a PR. <a href="${esc(gh('results/README.md'))}" target="_blank" rel="noopener">How to submit results</a>.`;

/* ---------- Scope: which rows and which models the current URL selects ---------- */
function scopeCases(){const cat=route.q.get('category')||'',mod=route.q.get('modality')||'',task=route.q.get('task')||'';return rowsInOrder().filter(c=>(!cat||catKey(c)===cat)&&(!mod||(mod==='image')===isImageTask(c.task))&&(!task||c.task===task));}
function scopeRuns(){const sel=route.q.get('models');if(!sel)return RUNS;const set=new Set(sel.split(','));return RUNS.filter(r=>set.has(keyOf(r)));}
const evaluated=(rs,cases)=>rs.filter(r=>subsetMetrics(r,cases).questions>0);

/* ---------- Banner and filter bar ---------- */
function banner(){
 const rows=allCases.length,tasks=taskOrder().length,cats=categoryOrder().length,models=RUNS.length,imgs=allCases.filter(c=>isImageTask(c.task)).length;
 const kpi=(l,v,s='')=>`<div><dt>${l}</dt><dd>${v}${s?`<small>${s}</small>`:''}</dd></div>`;
 const cat=route.q.get('category')||'';
 return `<div class="banner"><div class="banner-inner"><div><h1>Can a small model make <em>this decision</em> for you?</h1><p class="lede">Decision Bench measures how well language models make the bounded decisions inside software: route a ticket, spot an injection, check a contract, pick a tool, judge an answer. Every row is a real record from an <a href="#/data">open dataset</a>; every answer comes from the dataset's own annotators or an objective record, never from a model.</p></div>
 <dl class="kpis">${kpi('Rows',num(rows),imgs?`${num(imgs)} with images`:'')}${kpi('Tasks',tasks,`${cats} use cases`)}${kpi('Models',models||MODELS&&ORDER.filter(k=>MODELS[k].configured).length,models?'evaluated':'configured')}${kpi('Version',esc(man().version||''),'frozen')}</dl></div>
 <div class="usecases"><a href="${href('',{modality:route.q.get('modality')||''})}" class="${cat?'':'on'}">All use cases</a>${categoryOrder().map(k=>`<a href="${href('',{category:k,modality:route.q.get('modality')||''})}" class="${cat===k?'on':''}">${esc(catInfo(k).name)}<span class="n">${allCases.filter(c=>catKey(c)===k).length}</span></a>`).join('')}</div></div>`;
}
function filterBar(cases){
 const cat=route.q.get('category')||'',mod=route.q.get('modality')||'',rs=RUNS,sel=scopeRuns(),n=sel.length;
 const pop=rs.length?`<details class="models-pop"${popOpen?' open':''}><summary>Models <span class="num">(${n}${n<rs.length?` of ${rs.length}`:''})</span> ▾</summary><div class="pop" role="group" aria-label="Models shown"><div class="pop-actions"><button type="button" data-pick="all">All</button><button type="button" data-pick="none">None</button></div>${rs.map(r=>`<label><input type="checkbox" data-run="${esc(keyOf(r))}"${sel.includes(r)?' checked':''}>${modelHtml(keyOf(r),{link:false})}</label>`).join('')}</div></details>`:'';
 const hasImg=allCases.some(c=>isImageTask(c.task));
 return `<div class="filters">${selectHtml('f-category','Use case',[['','All'],...categoryOrder().map(k=>[k,catInfo(k).name])],cat)}${hasImg?seg('Input',[['','All inputs'],['text','Text'],['image','Image']],'modality',mod):''}${pop}<span class="spacer"></span><span class="count">${plural(cases.length,'row')} · ${new Set(cases.map(c=>c.task)).size} tasks</span></div>`;
}

/* ---------- Leaderboard (the entry page) ---------- */
function sortValue(m,key,r,cases){
 if(key.startsWith('col:'))return subsetMetrics(r,cases.filter(c=>(route.q.get('category')?c.task:catKey(c))===key.slice(4))).accuracy;
 return {accuracy:m.accuracy,latency:m.latency.p50,cost:m.costPer1k,tokens:m.tokensIn==null?null:m.tokensIn+(m.tokensOut||0),ece:m.ece,brier:m.brier,macro:macroF1(r,[...new Set(cases.map(c=>c.task))]),errors:m.errors}[key];
}
function rankOf(m,ms){const hi=m.wilson?.[1]??m.accuracy;return 1+ms.filter(o=>o!==m&&(o.wilson?.[0]??o.accuracy)>hi).length;}
function leaderboard(rs,cases){
 const cat=route.q.get('category')||'',cols=cat?taskOrder().filter(t=>cases.some(c=>c.task===t)):categoryOrder().filter(k=>cases.some(c=>catKey(c)===k));
 const colCases=k=>cases.filter(c=>(cat?c.task:catKey(c))===k),colName=k=>cat?taskName(k):catInfo(k).name,colHref=k=>cat?taskHref(k):catHref(k);
 const ms=rs.map(r=>[r,subsetMetrics(r,cases)]),los=ms.flatMap(([,m])=>m.wilson||[]),[d0]=los.length?zoomDomain(los,.1):[0,1],cx=lin(d0,1,0,56);
 const sorted=ms.slice().sort(([ra,a],[rb,b])=>{const va=sortValue(a,sort.key,ra,cases),vb=sortValue(b,sort.key,rb,cases);if(va==null)return 1;if(vb==null)return -1;return sort.dir==='asc'?va-vb:vb-va;});
 const th=(key,label,cls='',title='')=>`<th class="${cls}"${title?` title="${esc(title)}"`:''}>${key?`<button type="button" data-sort="${esc(key)}"${sort.key===key?` data-dir="${sort.dir}"`:''}>${label}</button>`:label}</th>`;
 const head=`<tr>${th('','#','rank','1 + the number of models whose 95% interval lies entirely above this one')}${th('','Model')}${th('accuracy','Accuracy','acc','Share of rows answered as the key does, with its Wilson 95% interval')}${cols.map(k=>th(`col:${k}`,esc(clip(colName(k),18)),'r cat',`${colName(k)}: accuracy on ${colCases(k).length} rows`)).join('')}${th('latency','Latency','r','Median wall-clock time per row')}${th('cost','$ / 1k rows','r','Cost per 1,000 rows: provider-reported, else estimated from list prices')}${th('tokens','Tokens','r','Input + output tokens per row')}${moreCols?th('macro','Macro F1','r','Mean F1 across tasks; rewards getting every option right, not only the common ones')+th('ece','ECE','r','Expected calibration error; lower is better')+th('brier','Brier','r','Mean squared error of the stated probabilities; lower is better')+th('errors','No answer','r','Rows with no valid answer (invalid JSON, refusal, timeout); counted as wrong'):''}</tr>`;
 const all=ms.map(([,m])=>m);
 const row=([r,m])=>{const ci=m.wilson,rank=rankOf(m,all),tp=m.tokensIn==null?null:m.tokensIn+(m.tokensOut||0);
  const bar=ci?`<span class="ci" aria-hidden="true"><i style="left:${cx(ci[0])}px;width:${Math.max(2,cx(ci[1])-cx(ci[0]))}px"></i><b style="left:${cx(m.accuracy)}px;background:${esc(runColor(r))}"></b></span>`:'';
  return `<tr><td class="rank">${m.questions?rank:'—'}</td><td>${modelHtml(keyOf(r))}</td><td class="acc"><span class="accw"${tipAttr(tipBody(runName(r),[['Accuracy',pct(m.accuracy)],['95% interval',ciText(ci)],['Correct',`${m.correct}/${m.questions}`]]),false)}><span class="accv num">${pct(m.accuracy)}</span>${bar}<span class="n num">${ciText(ci)}</span></span></td>${cols.map(k=>{const s=subsetMetrics(r,colCases(k));return `<td class="r num cat"${s.questions?tipAttr(tipBody(`${runName(r)} · ${colName(k)}`,[['Accuracy',pct(s.accuracy)],['95% interval',ciText(s.wilson)],['Correct',`${s.correct}/${s.questions}`]]),false):''}>${s.questions?pct0(s.accuracy):'<span class="faint">—</span>'}</td>`;}).join('')}<td class="r num">${ms(m.latency.p50)}</td><td class="r num">${money(m.costPer1k)}${m.costCoverage!=null&&m.costCoverage<1?`<sup title="Cost known for ${pct(m.costCoverage)} of rows">*</sup>`:''}</td><td class="r num"${tp!=null?tipAttr(tipBody(runName(r),[['Input / row',compact(m.tokensIn)],['Output / row',compact(m.tokensOut)]]),false):''}>${compact(tp)}</td>${moreCols?`<td class="r num">${pct(macroF1(r,[...new Set(cases.map(c=>c.task))]))}</td><td class="r num">${metric(m.ece)}</td><td class="r num">${metric(m.brier)}</td><td class="r num">${num(m.errors)}</td>`:''}</tr>`;};
 const partial=all.some(m=>m.costCoverage!=null&&m.costCoverage<1);
 return `<div class="table-wrap"><table class="lb"><thead>${head}</thead><tbody>${sorted.map(row).join('')}</tbody></table></div><div class="table-foot"><button type="button" class="linklike" data-more>${moreCols?'Fewer columns':'More columns: macro F1, calibration, errors'}</button><span>${partial?'* Cost known for only part of the rows. ':''}Models whose 95% intervals overlap share a rank. Image tasks are scored only for models that were sent the image.</span></div>`;
}
function headline(rs,cases){
 const ms=rs.map(r=>[r,subsetMetrics(r,cases)]).filter(([,m])=>m.questions).sort(([,a],[,b])=>b.accuracy-a.accuracy);
 const acc=ms.map(([r,m])=>({key:keyOf(r),color:runColor(r),value:m.accuracy,lo:m.wilson[0],hi:m.wilson[1],tip:tipBody(runName(r),[['Accuracy',pct(m.accuracy)],['95% interval',ciText(m.wilson)]])}));
 const lat=ms.map(([r,m])=>({key:keyOf(r),color:runColor(r),value:m.latency.p50==null?null:m.latency.p50/1000,tick:m.latency.p95==null?null:m.latency.p95/1000,tip:tipBody(runName(r),[['Median',ms(m.latency.p50)],['p95',ms(m.latency.p95)]])}));
 const cost=ms.map(([r,m])=>m.costCoverage===1&&m.costPer1k!=null?{key:keyOf(r),color:runColor(r),value:m.costPer1k,tip:tipBody(runName(r),[['$ / 1k rows',money(m.costPer1k)]])}:{key:keyOf(r),value:null,ghost:m.costPer1k==null?'unknown':'partly known',tip:tipBody(runName(r),[['Known subtotal',`${money(m.costPer1k)} / 1k`],['Cost coverage',pct(m.costCoverage)]])});
 const [lo]=zoomDomain(acc.map(a=>a.lo),.1);
 return `<div class="grid-3">${block('Accuracy','Whiskers: Wilson 95% interval.',vizBox(rowsChart(acc,{fmt:pct,tickFmt:pct0,max:1,min:lo}),'Accuracy by model'))}${block('Latency per row','Dot: median. Tick: 95th percentile. CLI runs include process start-up.',vizBox(rowsChart(lat,{fmt:secs,tickFmt:v=>v===0?'0':secs(v)}),'Median latency by model'))}${block('Cost per 1,000 rows','USD, provider-reported or estimated from list prices.',vizBox(rowsChart(cost,{fmt:money,tickFmt:v=>v===0?'$0':`$${v<1?v.toFixed(2):v.toFixed(v<10?1:0)}`}),'Cost per 1,000 rows by model'))}</div>`;
}
function tradeoffs(rs,cases){
 const pt=(r,m,xv,extra)=>({key:keyOf(r),color:runColor(r),x:xv,y:m.accuracy,lo:m.wilson[0],hi:m.wilson[1],tip:tipBody(runName(r),[['Accuracy',pct(m.accuracy)],['95% interval',ciText(m.wilson)],...extra])});
 const ms=rs.map(r=>[r,subsetMetrics(r,cases)]).filter(([,m])=>m.questions);
 const lat=ms.filter(([,m])=>m.latency.p50).map(([r,m])=>pt(r,m,m.latency.p50/1000,[['Median latency',ms(m.latency.p50)]]));
 const ok=ms.filter(([,m])=>m.costCoverage===1&&m.costPer1k>0),ex=ms.filter(x=>!ok.includes(x));
 const cost=ok.map(([r,m])=>pt(r,m,m.costPer1k,[['$ / 1k rows',money(m.costPer1k)]]));
 return `<div class="grid-2">${block('Accuracy against latency','Up and to the left is better. Vertical lines are 95% intervals.',vizBox(scatter(lat,{xFmt:secs,xLabel:'Median seconds per row'}),'Accuracy against median latency'))}${block('Accuracy against cost','',vizBox(scatter(cost,{xFmt:v=>`$${v<.1?v.toFixed(3):v<1?v.toFixed(2):v.toFixed(v<10?1:0)}`,xLabel:'USD per 1,000 rows'}),'Accuracy against cost'),{foot:ex.length?`Not plotted, cost unknown or partly known: ${ex.map(([r])=>esc(ident(r).short)).join(', ')}.`:''})}</div>`;
}
/* Every row as one cell. Column i is the same row for every model. */
function answerOf(v){if(!v)return 'Not run';if(!answered(v))return 'No valid answer';return v.scores.map(s=>human(s.label)).join(', ');}
function recordGrid(rs,cs){return w=>{
 const LW=w<640?132:228,groups=[];
 for(const c of cs){const g=groups.at(-1),name=catName(c);if(g&&g.name===name)g.cases.push(c);else groups.push({name,cases:[c]});}
 const avail=w-LW-4,gaps=Math.max(1,groups.length-1),pitch=Math.max(3,Math.min(12,Math.floor((avail-7*gaps)/cs.length))),GAP=groups.length>1?Math.max(7,Math.min(22,Math.floor((avail-pitch*cs.length)/gaps))):0,cell=Math.max(2,pitch-1),RH=13;
 const xs=[];let x=0;for(const g of groups){g.x=x;for(const _ of g.cases){xs.push(x);x+=pitch;}g.w=x-g.x-1;x+=GAP;}
 const W=x-GAP;
 const res=rs.map(r=>cs.map(c=>result(r.id,c.id)));
 const wrong=cs.map((c,i)=>{let k=0,m=0;res.forEach(row=>{const v=row[i];if(!v)return;m++;if(!okOf(v))k++;});return [k,m];});
 const cat=`<svg width="${W}" height="18" aria-hidden="true">${groups.map(g=>{const fit=Math.floor(g.w/6.3),short=g.name.split(/\s+/)[0],label=g.name.length<=fit?g.name:short.length<=fit?short:fit>=4?clip(short,fit):'';return `<g${tipAttr(tipBody(g.name,[['Rows',g.cases.length]]),false)}><rect class="hit" x="${g.x}" y="0" width="${g.w+1}" height="18"/>${label?`<text class="t-ink" x="${g.x}" y="10">${esc(label)}</text>`:''}<line class="axis" x1="${g.x}" x2="${g.x+g.w}" y1="16.5" y2="16.5"/></g>`;}).join('')}</svg>`;
 const SH=20,sum=`<svg width="${W}" height="${SH}" aria-hidden="true">${cs.map((c,i)=>{const [k,m]=wrong[i],h=m?Math.round((SH-3)*k/m):0;return `<a href="${rowHref(c)}" tabindex="-1"${tipAttr(tipBody(caseTitle(c),[['Models wrong',`${k} of ${m}`],['Answer key',goldText(c)]]),false)}><rect class="hit" x="${xs[i]}" y="0" width="${pitch}" height="${SH}"/><rect class="rg-base" x="${xs[i]}" y="${SH-1}" width="${cell}" height="1"/>${h?`<rect class="rg-bad" x="${xs[i]}" y="${SH-1-h}" width="${cell}" height="${h}"/>`:''}</a>`;}).join('')}</svg>`;
 const rows=rs.map((r,ri)=>{let n=0;const cells=cs.map((c,i)=>{const v=res[ri][i],ok=okOf(v),err=v&&!answered(v);if(v&&!ok)n++;const cls=!v?'rg-none':err?'rg-err':ok?'rg-ok':'rg-bad';
   const inset=!v||err?.5:0;return `<a href="${rowHref(c)}" tabindex="-1"${tipAttr(tipBody(caseTitle(c),[['Task',taskName(c.task)],['Answer key',goldText(c)],[ident(r).name,answerOf(v)]]),false)}><rect class="${cls}" x="${xs[i]+inset}" y="${inset}" width="${cell-2*inset}" height="${RH-2*inset}"/></a>`;}).join('');
  return `<div class="rg-row"><div class="rg-label" title="${esc(runName(r))}">${w<640?`<span class="m">${dotHtml(keyOf(r))}<span class="m-name">${esc(ident(r).short)}</span></span>`:modelHtml(keyOf(r),{sub:false})}<span class="num">${n} wrong</span></div><svg width="${W}" height="${RH}" aria-hidden="true">${DEFS}${cells}</svg></div>`;}).join('');
 return `<div class="rg" style="--lw:${LW}px"><div class="rg-row"><div class="rg-label"></div>${cat}</div><div class="rg-row rg-sum"><div class="rg-label"><span class="muted">Models wrong</span></div>${sum}</div>${rows}</div>`;
};}
function record(rs,cases){
 const ordered=rs.slice().sort((a,b)=>subsetMetrics(b,cases).accuracy-subsetMetrics(a,cases).accuracy);
 return `${legend([['cell','var(--rec-ok)','Correct'],['cell','var(--bad)','Wrong'],['hatch','','No valid answer'],['box','var(--line-strong)','Not run'],['bar','var(--bad)','Bar: how many models got the row wrong']])}<div class="rec">${vizBox(recordGrid(ordered,cases),'Result of every model on every row','rgv')}</div>`;
}
function hardestRows(rs,cases,limit=12){
 const items=cases.map(c=>{const st=caseStats(c);return {c,st};}).filter(x=>x.st.n>=2&&x.st.ok<x.st.n).sort((a,b)=>(b.st.n-b.st.ok)/b.st.n-(a.st.n-a.st.ok)/a.st.n||b.st.n-a.st.n).slice(0,limit);
 if(!items.length)return '<p class="muted">Every evaluated model agrees with every answer key in this selection.</p>';
 return `<div class="table-wrap"><table class="plain"><thead><tr><th>Row</th><th>Task</th><th>Answer key</th><th>Models answered</th><th class="r">Models right</th></tr></thead><tbody>${items.map(({c,st})=>`<tr class="link" data-href="${rowHref(c)}"><td><a class="t-link" href="${rowHref(c)}">${esc(caseTitle(c))}</a></td><td class="muted">${esc(taskName(c.task))}</td><td>${esc(goldText(c))}</td><td class="muted">${Object.entries(st.wrong).sort((a,b)=>b[1]-a[1]).map(([l,n])=>`${n}× ${esc(human(l==='null'?null:l))}`).join(', ')}</td><td class="r">${correctCell(st)}</td></tr>`).join('')}</tbody></table></div>`;
}
function coverageList(){
 const to=taskOrder();
 return `<div class="verdicts">${categoryOrder().map(k=>{const info=catInfo(k),tasks=to.filter(t=>taskCat(t)===k);return `<div><h3 style="font-size:var(--fs-3);margin:14px 0 4px"><a href="${catHref(k)}">${esc(info.name)}</a></h3>${info.description?`<p class="muted" style="font-size:var(--fs-1)">${esc(info.description)}</p>`:''}${tasks.map(t=>`<a href="${taskHref(t)}"><span>${esc(taskName(t))}<span class="sub">${esc(taskAsk(t))}</span></span><span class="muted num">${taskRows(t).length} rows${isImageTask(t)?' · image':''}</span></a>`).join('')}</div>`;}).join('')}</div>`;
}
function home(){
 const cases=scopeCases(),rs=evaluated(scopeRuns(),cases),cat=route.q.get('category')||'';
 const catLine=cat?`<p class="lede" style="margin:8px 0 14px">${esc(catInfo(cat).description)} <a href="${href('tasks',{category:cat})}">See the ${taskOrder().filter(t=>taskCat(t)===cat).length} tasks</a>.</p>`:'';
 const body=`<div class="wrap">${cat?`<h2 style="font-size:var(--fs-5);margin-top:24px;font-family:var(--display)">${esc(catInfo(cat).name)}</h2>`:''}${catLine}${filterBar(cases)}`+
  (!hasResults()?`${section('Leaderboard','',`<p class="notice">No model has been evaluated on this version yet. ${howToAdd()}</p>`)}${section('What the bench covers',`${plural(allCases.length,'row')} in ${taskOrder().length} tasks. Open a task to read its rows.`,coverageList())}`:
  !rs.length?`<p class="notice">No selected model has results on these rows.</p>`:
  section('Leaderboard',`${cat?`${esc(catInfo(cat).name)} rows`:'All rows'}${route.q.get('modality')?` · ${route.q.get('modality')} inputs`:''}. Sorted by ${sort.key.replace('col:','')}; click a column to re-sort.`,leaderboard(rs,cases)+(PARTIAL.length?`<p class="foot">Partial runs, not ranked: ${PARTIAL.map(r=>`${esc(ident(r).short)} (${num(r.metrics.cases)} of ${num(allCases.length)} rows)`).join(', ')}.</p>`:'')+(unevaluated().length?`<p class="foot">Configured but not evaluated yet: ${unevaluated().map(k=>esc(M(k).short)).join(', ')}. ${howToAdd()}</p>`:''),{id:'leaderboard'})+
  section('Accuracy, speed and cost','',headline(rs,cases))+
  section(cat?'Accuracy by task':'Accuracy by use case','Only misses are coloured; faded cells are at or above 95%. Click a heading to open it.',(cat?heatTasks(rs,cases):heatCategories(rs,cases))+heatLegend())+
  (cat?'':section('Accuracy by task','Every task, grouped by use case.',heatTasks(rs,cases)+heatLegend()))+
  section('Trade-offs','',tradeoffs(rs,cases))+
  section('Every row','Each column is one row, in the same position for every model. Hover for the row; click to open it.',record(rs,cases))+
  section('Where models disagree with the answer key','Rows most models get wrong. Either the models are weak here, or the key deserves a second look; each row page links to the source record.',hardestRows(rs,cases)))+
  `</div>`;
 return banner()+body;
}
const unevaluated=()=>ORDER.filter(k=>MODELS[k].configured&&!RUNS.some(r=>keyOf(r)===k)&&!PARTIAL.some(r=>keyOf(r)===k));

/* ---------- Task table ---------- */
function taskTable(){
 const cat=route.q.get('category')||'',mod=route.q.get('modality')||'',q=(route.q.get('q')||'').toLowerCase();
 const tasks=taskOrder().filter(t=>(!cat||taskCat(t)===cat)&&(!mod||(mod==='image')===isImageTask(t))&&(!q||`${taskName(t)} ${taskAsk(t)} ${catInfo(taskCat(t)).name} ${taskInfo(t).input_type||''} ${(taskInfo(t).datasets||[]).join(' ')}`.toLowerCase().includes(q)));
 const best=t=>{const rows=taskRows(t),ms=RUNS.map(r=>[r,subsetMetrics(r,rows)]).filter(([,m])=>m.questions).sort(([,a],[,b])=>b.accuracy-a.accuracy);return ms[0]||null;};
 const hasImg=allCases.some(c=>isImageTask(c.task));
 const bar=`<div class="filters">${selectHtml('f-category','Use case',[['','All'],...categoryOrder().map(k=>[k,catInfo(k).name])],cat)}${hasImg?seg('Input',[['','All inputs'],['text','Text'],['image','Image']],'modality',mod):''}<input id="f-q" type="search" placeholder="Search tasks…" value="${esc(route.q.get('q')||'')}" aria-label="Search tasks"><span class="spacer"></span><span class="count">${plural(tasks.length,'task')} · ${num(tasks.reduce((n,t)=>n+taskRows(t).length,0))} rows</span></div>`;
 let last=null;
 const body=tasks.map(t=>{const i=taskInfo(t),rows=taskRows(t),ds=[...new Set(rows.map(c=>dsOf(c)).filter(Boolean))],b=best(t);let g='';if(taskCat(t)!==last){last=taskCat(t);g=`<tr class="grp"><td colspan="7" style="padding-top:18px;color:var(--muted);font-size:var(--fs-1);font-weight:500;border-bottom-color:var(--line-strong)"><a href="${catHref(last)}" style="color:inherit">${esc(catInfo(last).name)}</a></td></tr>`;}
  return g+`<tr class="link" data-href="${taskHref(t)}"><td><a class="t-link" href="${taskHref(t)}">${esc(taskName(t))}</a><span class="sub">${esc(t)}</span></td><td class="q">${esc(taskAsk(t))}<div class="opts-inline">${Object.keys(rows[0].questions[0].options).length<=8&&!i.per_row_options?Object.entries(rows[0].questions[0].options).slice(0,8).map(([k])=>`<b>${esc(human(k))}</b>`).join(''):`<b>${esc(i.per_row_options?'options come from the record':`${Object.keys(rows[0].questions[0].options).length} options`)}</b>`}</div></td><td><div class="tags">${i.input_type?`<span class="tag">${esc(i.input_type)}</span>`:''}${isImageTask(t)?'<span class="tag img">image</span>':''}${i.shape?`<span class="tag">${esc(i.shape)}</span>`:''}</div></td><td class="muted">${ds.map(d=>dsLink(d)).join(', ')||'—'}</td><td class="r num">${rows.length}</td><td>${b?`<span class="m">${logoHtml(keyOf(b[0]))}<span class="num">${pct0(b[1].accuracy)}</span></span>`:'<span class="faint">—</span>'}</td><td>${hasResults()?fitHtml(verdict(RUNS.length?subsetMetrics(RUNS.reduce((w,r)=>subsetMetrics(r,rows).accuracy>(w?subsetMetrics(w,rows).accuracy:-1)?r:w,null)||RUNS[0],rows):null)):'<span class="faint">—</span>'}</td></tr>`;}).join('');
 return pageHead('Tasks',`Every task is one fixed question with a short list of options, asked of ${plural(allCases.length,'real record')}. Open a task to read its rows and see how each model did. <a href="corpus.json" download>Download all rows (JSON)</a>`)+bar+`<div class="table-wrap"><table class="tasks"><thead><tr><th>Task</th><th>Question and options</th><th>Input</th><th>Source</th><th class="r">Rows</th><th>Best model</th><th>Best verdict</th></tr></thead><tbody>${body||'<tr><td colspan="7" class="muted">No task matches these filters.</td></tr>'}</tbody></table></div>`;
}

/* ---------- Task page ---------- */
function taskPage(t){
 const rows=taskRows(t);if(!rows.length)return `<div class="empty"><h1>Unknown task</h1><p><a href="#/tasks">All tasks</a></p></div>`;
 const i=taskInfo(t),q0=rows[0].questions[0],cat=taskCat(t),ds=[...new Set(rows.map(c=>dsOf(c)).filter(Boolean))];
 const labels=[['Decision',i.shape&&man().shapes?.[i.shape]?`${cap(i.shape)}: ${man().shapes[i.shape]}`:cap(i.shape||'')],['Input',[i.input_type,isImageTask(t)?'image':'text',i.length].filter(Boolean).join(' · ')],['Options',i.per_row_options?'From the record':`${Object.keys(q0.options).length}${i.abstain?`, including an abstain option (${human(i.abstain)})`:''}`],['Answer from',i.label_origin||rows[0].source?.labelled_by||''],['Expertise',i.expertise&&man().expertise?.[i.expertise]?`${cap(i.expertise)}: ${man().expertise[i.expertise]}`:cap(i.expertise||'')],['Contamination risk',i.contamination?`${cap(i.contamination)}: ${{low:'a fresh derivation, unlikely in training data',medium:'a public dataset that may be in training data',high:'a well-known benchmark, probably in training data'}[i.contamination]}`:''],['Source',ds.map(d=>`${dsLink(d)}${d.license?` <span class="lic">${esc(d.license)}</span>`:''}`).join(', ')]].filter(([,v])=>v);
 const optsHtml=i.per_row_options?`<p class="muted" style="margin-top:12px">The options differ per row: ${esc(Object.values(q0.options)[0]||'they come from the record')}</p>`:`<ol class="opts">${Object.entries(q0.options).map(([k,d])=>`<li><span class="o-k">${esc(human(k))}</span><span class="o-d">${esc(d)}</span></li>`).join('')}</ol>`;
 const rs=evaluated(RUNS,rows),ms=rs.map(r=>[r,subsetMetrics(r,rows)]).sort(([,a],[,b])=>b.accuracy-a.accuracy);
 const results=ms.length?`<div class="table-wrap"><table class="plain"><thead><tr><th>Model</th><th>Accuracy</th><th class="r">95% interval</th><th class="r">Latency</th><th class="r">$ / 1k rows</th><th class="r">No answer</th><th>Verdict</th></tr></thead><tbody>${ms.map(([r,m])=>`<tr><td>${modelHtml(keyOf(r))}</td><td><span class="accw"><span class="accv num">${pct(m.accuracy)}</span><span class="mini"><i style="width:${m.accuracy*100}%;background:${esc(runColor(r))}"></i></span></span></td><td class="r num muted">${ciText(m.wilson)}</td><td class="r num">${ms(m.latency.p50)}</td><td class="r num">${money(m.costPer1k)}</td><td class="r num">${m.errors||'0'}</td><td>${fitHtml(verdict(m))}</td></tr>`).join('')}</tbody></table></div><p class="foot">Fits: accuracy at or above 90% with the whole 95% interval above 85%. Risky: above 80%. Not fit: below 80%.${isImageTask(t)?' Text-only models saw the text rendering, not the image; models that were never sent this task are not listed.':''}</p>`:`<p class="notice">${hasResults()?'No model has results on this task yet.':'No model has been evaluated on this version yet.'}</p>`;
 const sortKey=route.q.get('sort')||'order';
 const list=rows.slice().sort((a,b)=>{if(sortKey==='hardest'){const sa=caseStats(a),sb=caseStats(b);return (sa.n?sa.ok/sa.n:1)-(sb.n?sb.ok/sb.n:1);}if(sortKey==='title')return caseTitle(a).localeCompare(caseTitle(b));return 0;});
 const shown=list.slice(0,rowsShown);
 const rowsTable=`<div class="table-meta"><span>${plural(rows.length,'row')}</span><span>Sort: ${[['order','corpus order'],['hardest','hardest first'],['title','title']].map(([k,l])=>k===sortKey?`<b>${l}</b>`:`<a href="${withQ({sort:k})}">${l}</a>`).join(' · ')}</span></div><div class="table-wrap"><table class="plain"><thead><tr><th>Row</th><th>Answer key</th><th>Source record</th><th class="r">Models right</th></tr></thead><tbody>${shown.map(c=>`<tr class="link" data-href="${rowHref(c)}"><td><a class="t-link" href="${rowHref(c)}">${esc(caseTitle(c))}</a></td><td>${esc(goldText(c))}</td><td class="muted">${esc(String(c.source?.record_id||''))}</td><td class="r">${correctCell(caseStats(c))}</td></tr>`).join('')}</tbody></table></div>${rows.length>rowsShown?`<div class="pagination"><button type="button" data-morerows>Show all ${rows.length} rows</button></div>`:''}`;
 return crumbs([['Tasks',href('tasks')],[catInfo(cat).name,href('tasks',{category:cat})],[taskName(t),'']])+
  `<div class="task-head"><div><p class="name">${esc(taskName(t))} · ${esc(t)}</p><h1>${esc(taskAsk(t))}</h1><p class="instr">${esc(q0.instructions)}</p>${optsHtml}</div><div class="card"><h3>About this task</h3><dl>${labels.map(([k,v])=>`<dt>${esc(k)}</dt><dd>${v}</dd>`).join('')}</dl></div></div>`+
  section('Results on this task',`${plural(rows.length,'row')} each.`,results)+
  section('Rows','Every record in this task, with its answer key. Open a row to read the record as the model saw it.',rowsTable);
}

/* ---------- Rendering a record as the artifact it is ---------- */
const labelOf=k=>{const s=String(k).replace(/_/g,' ');return s[0].toUpperCase()+s.slice(1);};
const isObj=v=>v&&typeof v==='object'&&!Array.isArray(v);
const isDiff=s=>/^diff --git /m.test(s)||(/^--- \S/m.test(s)&&/^\+\+\+ \S/m.test(s))||/^@@ .* @@/m.test(s);
const CODE_LINE=/^\s{2,}\S|[{};]\s*$|^\s*(def |function |class |import |from \S+ import|SELECT |FROM |WHERE |\$ |>>> |#!|<\/?[a-z][\w-]*[ >])|^\[?\d{4}-\d\d-\d\d[T ]\d\d:|\S {3,}\S/;
function isCodeish(s){if(/```/.test(s))return true;const lines=s.split('\n').filter(l=>l.trim());if(lines.length<2)return /^\s*(def|function|class|import|SELECT|CREATE TABLE)\b/.test(s);return lines.filter(l=>CODE_LINE.test(l)).length>=Math.max(2,lines.length*.3);}
const pretty=v=>`<pre class="code">${esc(JSON.stringify(v,null,2))}</pre>`;
function renderString(s){
 if(isDiff(s))return `<pre class="code">${s.split('\n').map(l=>/^\+(?!\+\+ )/.test(l)?`<span class="add">${esc(l)}</span>`:/^-(?!-- )/.test(l)?`<span class="del">${esc(l)}</span>`:/^@@/.test(l)?`<span class="hunk">${esc(l)}</span>`:esc(l)).join('\n')}</pre>`;
 if(isCodeish(s))return `<pre class="code">${esc(s)}</pre>`;
 return s.length>160||/\n/.test(s)?`<p class="long${s.length>2400?' clamp':''}">${esc(s)}</p>`:`<span class="sv">${esc(s)}</span>`;
}
/* Turn lists: transcripts, logs and tool calls. Accepts objects with a speaker-like key and a text-like key. */
const WHO=['speaker','role','from','agent','author','sender','name','turn_by'],WHAT=['text','content','message','utterance','body','said'];
const looksTurn=o=>isObj(o)&&WHO.some(k=>typeof o[k]==='string')&&WHAT.some(k=>typeof o[k]==='string');
const looksTurnLine=s=>typeof s==='string'&&/^\s*(\d+[.)]\s*)?[A-Za-z_][\w .-]{0,40}:\s/.test(s);
function renderTurns(v){
 return `<div class="turns">${v.map((o,i)=>{let who,what,no=i+1,tool=false;
  if(isObj(o)){who=WHO.map(k=>o[k]).find(x=>typeof x==='string')||'';what=WHAT.map(k=>o[k]).find(x=>typeof x==='string')||'';no=o.turn??o.step??o.index??o.no??no;tool=/tool|function|terminal|system/i.test(who);
   const rest=Object.fromEntries(Object.entries(o).filter(([k,x])=>!WHO.includes(k)&&!WHAT.includes(k)&&!['turn','step','index','no'].includes(k)&&x!=null&&x!==''));if(Object.keys(rest).length)what+=`\n${Object.entries(rest).map(([k,x])=>`${k}: ${typeof x==='string'?x:JSON.stringify(x)}`).join('\n')}`;}
  else{const m=String(o).match(/^\s*(?:(\d+)[.)]\s*)?([A-Za-z_][\w .()-]{0,60}?):\s([\s\S]*)$/);if(m){no=m[1]||no;who=m[2];what=m[3];}else{who='';what=String(o);}tool=/tool|function|terminal|system|result/i.test(who);}
  return `<div class="turn${tool?' tool':''}"><span class="no num">${esc(no)}</span><span class="who" title="${esc(who)}">${esc(who)}</span><span class="what">${esc(what)}</span></div>`;}).join('')}</div>`;
}
const looksEmail=o=>isObj(o)&&('subject' in o||'from' in o)&&('body' in o||'text' in o);
function renderEmail(o){const hdr=['from','to','cc','date','subject'].filter(k=>o[k]!=null);const body=o.body??o.text??'';const rest=Object.entries(o).filter(([k])=>![...hdr,'body','text'].includes(k));
 return `<div class="email"><dl class="hdr">${hdr.map(k=>`<dt>${esc(labelOf(k))}</dt><dd>${esc(String(o[k]))}</dd>`).join('')}</dl><div class="body">${esc(String(body))}</div></div>${rest.length?`<dl class="kv" style="margin-top:8px">${rest.map(([k,x])=>`<div><dt>${esc(labelOf(k))}</dt><dd>${renderValue(x,2)}</dd></div>`).join('')}</dl>`:''}`;}
function renderValue(v,depth=0){
 if(v==null)return '<span class="muted">none</span>';
 if(typeof v==='string')return renderString(v);
 if(typeof v!=='object')return `<span class="num">${esc(String(v))}</span>`;
 if(Array.isArray(v)){
  if(!v.length)return '<span class="muted">empty</span>';
  if(v.length>=2&&v.every(x=>looksTurn(x)||looksTurnLine(x)))return renderTurns(v);
  if(v.every(isObj)){const keys=[...new Set(v.flatMap(Object.keys))];const flat=v.every(o=>Object.values(o).every(x=>x==null||typeof x!=='object'));
   if(keys.length<=8&&flat&&v.length>1)return `<div class="table-wrap"><table class="st"><thead><tr>${keys.map(k=>`<th>${esc(labelOf(k))}</th>`).join('')}</tr></thead><tbody>${v.map(o=>`<tr>${keys.map(k=>`<td>${o[k]==null?'':typeof o[k]==='string'?renderString(o[k]):esc(String(o[k]))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
   return depth>=2?pretty(v):`<ol class="sl">${v.map(x=>`<li>${renderValue(x,depth+1)}</li>`).join('')}</ol>`;}
  if(v.every(x=>Array.isArray(x))&&v.length>1&&v.every(x=>x.length===v[0].length&&x.every(y=>typeof y!=='object')))return `<div class="table-wrap"><table class="st"><thead><tr>${v[0].map(k=>`<th>${esc(String(k))}</th>`).join('')}</tr></thead><tbody>${v.slice(1).map(r=>`<tr>${r.map(x=>`<td>${esc(String(x??''))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  return `<ol class="sl">${v.map(x=>`<li>${renderValue(x,depth+1)}</li>`).join('')}</ol>`;
 }
 if(looksEmail(v))return renderEmail(v);
 const ents=Object.entries(v);if(!ents.length)return '<span class="muted">empty</span>';
 if(depth>=3)return pretty(v);
 return `<dl class="kv${depth>1?' nested':''}">${ents.map(([k,x])=>`<div><dt>${esc(labelOf(k))}</dt><dd>${renderValue(x,depth+1)}</dd></div>`).join('')}</dl>`;
}
function renderRecord(c){
 const st=c.state,imgs=(c.assets||[]).filter(a=>String(a.mime_type||'').startsWith('image/'));
 const media=imgs.map(a=>`<figure class="media"><a href="${esc(assetUrl(a))}" target="_blank" rel="noopener"><img src="${esc(assetUrl(a))}" alt="${esc(a.alt_text||'')}"${a.width?` width="${a.width}"`:''}${a.height?` height="${a.height}"`:''}></a><figcaption>${esc(a.alt_text||'')} · Sent as an image to vision models; text-only models receive the text below.</figcaption></figure>`).join('');
 let body;
 if(typeof st==='string')body=renderString(st);
 else if(looksEmail(st))body=renderEmail(st);
 else if(isObj(st))body=Object.entries(st).map(([k,v])=>`<section class="field"><h4>${esc(labelOf(k))}</h4>${renderValue(v,1)}</section>`).join('');
 else body=renderValue(st);
 return `<div class="artifact">${media}${body}</div><details class="raw"><summary>Exact input sent to the model (JSON)</summary><button type="button" class="linklike copy" data-copy>Copy</button><pre class="code">${esc(JSON.stringify({state:st,question:{instructions:c.questions[0].instructions,options:Object.fromEntries(optionOrder(c.questions[0]).map(k=>[k,c.questions[0].options[k]]))}},null,2))}</pre></details>`;
}

/* ---------- Row page ---------- */
function answerKey(c){
 const q=c.questions[0],src=c.source,d=dsOf(c);
 const opts=`<ol class="opts">${optionOrder(q).map(k=>`<li class="${k===q.gold?'gold':''}"><span class="o-k">${esc(human(k))}${k===q.gold?' <span class="tick" aria-label="answer key">✓</span>':''}</span><span class="o-d">${esc(q.options[k])}</span></li>`).join('')}</ol>`;
 const attrib=src?`<p class="attrib">From ${d?dsLink(d):esc(src.dataset)}${src.record_id!=null?`, record <code>${esc(String(src.record_id))}</code>`:''}${src.url?` (${ext(src.url,'source')})`:''}. Answer decided by ${esc(src.labelled_by||'the dataset')}${src.original_label!=null?`; original label <code>${esc(origLabel(src.original_label))}</code>`:''}. Licence ${esc(src.license||'')}.${REPO&&!REPO.includes('OWNER')?` <a href="${esc(ghIssue('label-error.yml',{title:`Label question: ${c.id}`}))}" target="_blank" rel="noopener">Report a label problem</a>.`:''}</p>`:'';
 return `<div class="key-gold"><span class="k-label">Answer key</span><strong>${esc(human(q.gold))}</strong></div><p class="rationale">${esc(q.rationale)}</p>${c.note?`<p class="row-note">${esc(c.note)}</p>`:''}<h3 class="minor-head" style="margin-top:16px">Options, in the order the model saw them</h3>${opts}${attrib}`;
}
function answersTable(c){
 const rs=RUNS.filter(r=>result(r.id,c.id));if(!rs.length)return `<p class="notice">${hasResults()?'No model has a result on this row.':'No model has been evaluated on this version yet.'}</p>`;
 const rows=rs.map(r=>{const v=result(r.id,c.id);return {r,v,ok:okOf(v)};}).sort((a,b)=>(a.ok-b.ok)||byOrder(a.r,b.r));
 const tr=({r,v,ok})=>{const s=v.scores[0],id=`ans-${slug(r.id)}`;
  const ans=s?.label!=null?esc(human(s.label)):`<span class="muted">${esc(v.status==='ok'?'no answer':human(v.status))}</span>`;
  const probs=Object.entries(s?.probabilities||{}).sort((a,b)=>b[1]-a[1]).map(([l,p])=>`<div class="prob"><span>${esc(human(l))}${l===s.gold?' ✓':''}</span><span class="pt"><i style="width:${p*100}%;background:${l===s.gold?'var(--good)':l===s.label?'var(--bad)':'var(--faint)'}"></i></span><span class="num">${pct(p)}</span></div>`).join('');
  return `<tr class="ans" data-expand="${id}" tabindex="0" aria-expanded="false"><td><span class="caret" aria-hidden="true">▸</span>${modelHtml(keyOf(r),{link:false})}</td><td class="ans ${ok?'ok':'bad'}">${ok?'✓':'✗'} ${ans}</td><td class="r num">${pct0(s?.confidence)}</td><td class="r num">${ms(v.duration_ms)}</td><td class="r num">${money(v.cost_usd)}</td><td class="r num muted">${v.tokens?.input!=null?`${compact(v.tokens.input)} / ${compact(v.tokens.output)}`:'—'}</td><td>${isImageTask(c.task)?(v.images_sent?'<span class="tag img">image</span>':'<span class="tag">text rendering</span>'):''}</td></tr><tr class="ans-detail" id="${id}" hidden><td colspan="7"><div class="ans-grid"><div><h4 class="minor-head" style="margin-top:0">Probabilities the model gave</h4>${probs||'<p class="muted">No probabilities returned.</p>'}${v.error?`<p class="error">${esc(v.error)}</p>`:''}</div><div><h4 class="minor-head" style="margin-top:0">Raw response</h4><pre class="code wrap" style="max-height:260px">${esc(v.output_text||v.raw_response||'(not published)')}</pre><p class="tiny-meta">${esc(ident(r).iface)}${v.status?` · status ${esc(v.status)}`:''}${v.attempt_count?` · ${plural(v.attempt_count,'attempt')}`:''}</p></div></div></td></tr>`;};
 return `<div class="table-wrap"><table class="answers"><thead><tr><th>Model</th><th>Answer</th><th class="r">Confidence</th><th class="r">Latency</th><th class="r">Cost</th><th class="r">Tokens in / out</th><th>${isImageTask(c.task)?'Saw':''}</th></tr></thead><tbody>${rows.map(tr).join('')}</tbody></table></div><p class="foot">Wrong answers first. Select a row for the probabilities and the raw response. Confidence is the probability the model gave its own answer.</p>`;
}
function verdictLine(c){const st=caseStats(c);if(!st.n)return '';const wrong=st.n-st.ok,w=Object.entries(st.wrong).sort((a,b)=>b[1]-a[1]);return `<p class="answer-with"><strong style="color:var(--ink)">${st.ok} of ${st.n} models</strong> match the answer key.${wrong?` The other ${wrong===1?'one':wrong} chose ${w.map(([l,n])=>`${esc(human(l==='null'?null:l))}${w.length>1?` (${n})`:''}`).join(', ')}.`:''}</p>`;}
function rowPage(id,review=false){
 const c=caseMap.get(id);if(!c)return `<div class="empty"><h1>Unknown row</h1><p><a href="#/tasks">All tasks</a></p></div>`;
 const q=c.questions[0],t=c.task,rows=taskRows(t),i=rows.indexOf(c),prev=rows[i-1],next=rows[i+1];
 const nav=`<div class="row-nav"><span>Row ${i+1} of ${rows.length}</span><a href="${prev?rowHref(prev):'#'}"${prev?'':' aria-disabled="true"'} title="Previous row (k)">‹ Previous</a><a href="${next?rowHref(next):'#'}"${next?'':' aria-disabled="true"'} title="Next row (j)">Next ›</a></div>`;
 const head=crumbs([['Tasks',href('tasks')],[catInfo(catKey(c)).name,href('tasks',{category:catKey(c)})],[taskName(t),taskHref(t)],[`Row ${i+1}`,'']])+
  `<div class="row-head"><div><h1>${esc(taskAsk(t)||firstSentence(q.instructions))}</h1><p class="title">${esc(caseTitle(c))}</p><div class="answer-with"><span>Answer with</span>${optionOrder(q).map(k=>`<span class="tag">${esc(human(k))}</span>`).join('')}${isImageTask(t)?'<span class="tag img">image task</span>':''}</div>${review?'':verdictLine(c)}</div>${nav}</div>`;
 const body=`<section class="record"><h2>The record</h2>${renderRecord(c)}</section><section class="key"><h2>Answer key</h2>${answerKey(c)}</section>`+(review?'':`<section class="answers"><h2>Model answers</h2>${answersTable(c)}</section>`)+
  `<footer class="case-meta"><span><code>${esc(c.id)}</code> · ${esc(taskName(t))} · ${esc(man().version||'')}</span><span><a href="${location.hash.split('?')[0]}">Link to this row</a></span></footer>`;
 return head+body;
}

/* ---------- Models ---------- */
function modelsPage(){
 const keys=ORDER.filter(k=>MODELS[k].configured);
 const rows=keys.map(k=>{const m=M(k),run=RUNS.find(r=>keyOf(r)===k),mm=run?subsetMetrics(run,allCases):null;
  return `<tr class="link" data-href="${href(`model/${encodeURIComponent(k)}`)}"><td>${modelHtml(k)}</td><td class="muted">${esc(m.vendor)}</td><td class="muted">${esc(m.iface)}</td><td class="muted"><code>${esc(m.api_model||'')}</code></td><td>${m.vision?'Yes':'Text only'}</td><td class="r num">${mm?pct(mm.accuracy):'<span class="faint">not evaluated</span>'}</td><td class="r num">${mm?ms(mm.latency.p50):''}</td><td class="r num">${mm?money(mm.costPer1k):''}</td></tr>`;}).join('');
 return pageHead('Models',`Every model the harness can run, with the request options and prices used. ${hasResults()?'Open a model for its fit by use case, its failures and its calibration.':howToAdd()}`)+
  `<div class="table-wrap"><table class="plain"><thead><tr><th>Model</th><th>Vendor</th><th>Interface</th><th>Model name sent</th><th>Images</th><th class="r">Accuracy</th><th class="r">Latency</th><th class="r">$ / 1k rows</th></tr></thead><tbody>${rows}</tbody></table></div>`+
  `<p class="foot">Vendor marks are used to identify the model's maker and remain their property. Prices are list prices at the time of the run; provider-reported cost is used where the endpoint returns it.</p>`;
}
function modelPage(k){
 const m=MODELS[k];if(!m)return `<div class="empty"><h1>Unknown model</h1><p><a href="#/models">All models</a></p></div>`;
 const run=RUNS.find(r=>keyOf(r)===k)||PARTIAL.find(r=>keyOf(r)===k);
 const head=crumbs([['Models',href('models')],[m.name,'']])+`<div class="profile-head">${m.logo?`<img class="logo" src="${esc(m.logo)}" alt="" width="44" height="44">`:''}<div><h1>${esc(m.name)}</h1><p class="muted">${esc([m.vendor,m.iface,m.vision?'text and images':'text only',m.api_model?`sent as ${m.api_model}`:''].filter(Boolean).join(' · '))}</p></div></div>`;
 if(!run)return head+`<p class="notice" style="margin-top:20px">This model is configured but has not been evaluated on this version. ${howToAdd()}</p>${m.request?`<details class="adv"><summary>Request options and prices</summary><pre class="code">${esc(JSON.stringify({request:m.request,pricing:m.pricing},null,2))}</pre></details>`:''}`;
 const all=subsetMetrics(run,allCases),textCases=allCases.filter(c=>!isImageTask(c.task));
 const kpi=(l,v)=>`<div><dt>${l}</dt><dd class="num">${v}</dd></div>`;
 const fits=taskOrder().map(t=>[t,verdict(subsetMetrics(run,taskRows(t)))]);
 const count=k=>fits.filter(([,v])=>v.k===k).length;
 const kpis=`<dl class="kpis" style="margin-top:22px">${kpi('Accuracy',pct(all.accuracy))}${kpi('95% interval',ciText(all.wilson))}${kpi('Median latency',ms(all.latency.p50))}${kpi('$ / 1k rows',money(all.costPer1k))}${kpi('Tasks that fit',`${count('ok')} / ${fits.filter(([,v])=>v.k!=='na').length}`)}</dl>`;
 const byCat=`<div class="table-wrap"><table class="plain"><thead><tr><th>Use case</th><th>This model</th><th class="r">Best model</th><th>Verdict</th></tr></thead><tbody>${categoryOrder().map(c=>{const cs=allCases.filter(x=>catKey(x)===c),mm=subsetMetrics(run,cs),best=RUNS.map(r=>[r,subsetMetrics(r,cs)]).filter(([,x])=>x.questions).sort(([,a],[,b])=>b.accuracy-a.accuracy)[0];return `<tr class="link" data-href="${catHref(c)}"><td><a class="t-link" href="${catHref(c)}">${esc(catInfo(c).name)}</a></td><td>${mm.questions?`<span class="accw"><span class="accv num">${pct(mm.accuracy)}</span><span class="mini"><i style="width:${mm.accuracy*100}%;background:${esc(m.color)}"></i></span></span>`:'<span class="faint">not run</span>'}</td><td class="r num muted">${best?`${pct0(best[1].accuracy)} · ${esc(ident(best[0]).short)}`:'—'}</td><td>${fitHtml(verdict(mm))}</td></tr>`;}).join('')}</tbody></table></div>`;
 const byTask=`<div class="verdicts">${fits.map(([t,v])=>{const mm=subsetMetrics(run,taskRows(t));return `<a href="${taskHref(t)}"><span>${esc(taskName(t))}<span class="sub">${esc(catInfo(taskCat(t)).name)} · ${mm.questions?`${pct0(mm.accuracy)} on ${mm.questions} rows`:isImageTask(t)?'image task, not run':'not run'}</span></span>${fitHtml(v)}</a>`;}).join('')}</div>`;
 const fails=allCases.filter(c=>{const v=result(run.id,c.id);if(!v||okOf(v))return false;const st=caseStats(c);return st.n>=3&&st.ok>=Math.ceil(st.n*.6);}).map(c=>{const st=caseStats(c),v=result(run.id,c.id);return {c,st,v};}).sort((a,b)=>b.st.ok/b.st.n-a.st.ok/a.st.n).slice(0,20);
 const failTable=fails.length?`<div class="table-wrap"><table class="plain"><thead><tr><th>Row</th><th>Task</th><th>Answer key</th><th>This model said</th><th class="r">Others right</th></tr></thead><tbody>${fails.map(({c,st,v})=>`<tr class="link" data-href="${rowHref(c)}"><td><a class="t-link" href="${rowHref(c)}">${esc(caseTitle(c))}</a></td><td class="muted">${esc(taskName(c.task))}</td><td>${esc(goldText(c))}</td><td style="color:var(--bad)">${esc(answerOf(v))}</td><td class="r num">${st.ok}/${st.n}</td></tr>`).join('')}</tbody></table></div>`:'<p class="muted">No row where this model is wrong while most others are right.</p>';
 const others=RUNS.filter(r=>r!==run);
 const conf=`<div class="grid-2">${block('Reliability','On the diagonal, stated confidence matches observed accuracy. Dot size is the number of decisions in the bin.',vizBox(reliabilityChart([run,...others],textCases,[k]),'Reliability diagram'))}${block('Risk and coverage','Error rate if answers below a confidence threshold are handed to a person. Other models in grey.',vizBox(riskChart([run,...others],textCases,[k]),'Risk against coverage'))}</div><p class="foot">Expected calibration error ${metric(all.ece)} · Brier ${metric(all.brier)} · ${plural(all.highConfErrors,'wrong answer')} given with 90% confidence or more.</p>`;
 return head+kpis+section('Fit by use case','Fits: accuracy at or above 90% with the whole 95% interval above 85%. Risky: above 80%. Not fit: below 80%.',byCat)+section('Fit by task','',byTask)+section('Where it fails while most models succeed','The likeliest places to look before using this model. Each opens the row.',failTable)+section('Confidence','',conf)+
  `<details class="adv"><summary>Request options, prices and run record</summary><pre class="code">${esc(JSON.stringify({request:m.request,pricing:m.pricing,run:{id:run.id,status:run.status,completed_at:run.completed_at,coverage:run.coverage,files:run.files},resolved:run.model?.resolved_models},null,2))}</pre></details>`;
}

/* ---------- Compare two models ---------- */
function comparePage(){
 if(RUNS.length<2)return pageHead('Compare','')+`<p class="notice">Paired comparison needs at least two evaluated models.</p>`;
 const ids=RUNS.map(keyOf),a=route.q.get('a')&&ids.includes(route.q.get('a'))?route.q.get('a'):ids[0],b=route.q.get('b')&&ids.includes(route.q.get('b'))&&route.q.get('b')!==a?route.q.get('b'):ids.find(x=>x!==a);
 const ra=RUNS.find(r=>keyOf(r)===a),rb=RUNS.find(r=>keyOf(r)===b);
 const sel=`<div class="filters">${selectHtml('cmp-a','Model A',ids.map(k=>[k,M(k).name]),a)}${selectHtml('cmp-b','Model B',ids.map(k=>[k,M(k).name]),b)}</div>`;
 const rows=taskOrder().map(t=>{const cs=taskRows(t);let both=0,ao=0,bo=0,none=0,n=0;for(const c of cs){const va=result(ra.id,c.id),vb=result(rb.id,c.id);if(!va||!vb)continue;n++;const x=okOf(va),y=okOf(vb);if(x&&y)both++;else if(x)ao++;else if(y)bo++;else none++;}return {t,n,both,ao,bo,none,d:n?(ao-bo)/n:null};}).filter(r=>r.n);
 const tot=rows.reduce((acc,r)=>({n:acc.n+r.n,ao:acc.ao+r.ao,bo:acc.bo+r.bo,both:acc.both+r.both,none:acc.none+r.none}),{n:0,ao:0,bo:0,both:0,none:0});
 const table=`<div class="table-wrap"><table class="plain"><thead><tr><th>Task</th><th class="r">Shared rows</th><th class="r">Both right</th><th class="r">Only ${esc(M(a).short)}</th><th class="r">Only ${esc(M(b).short)}</th><th class="r">Both wrong</th><th class="r">Difference</th></tr></thead><tbody>${rows.map(r=>`<tr class="link" data-href="${taskHref(r.t)}"><td><a class="t-link" href="${taskHref(r.t)}">${esc(taskName(r.t))}</a><span class="sub">${esc(catInfo(taskCat(r.t)).name)}</span></td><td class="r num">${r.n}</td><td class="r num muted">${r.both}</td><td class="r num">${r.ao}</td><td class="r num">${r.bo}</td><td class="r num muted">${r.none}</td><td class="r num" style="color:${r.d>0?'var(--good)':r.d<0?'var(--bad)':'inherit'}">${r.d==null?'—':`${pp(r.d)} pp`}</td></tr>`).join('')}<tr><th>All tasks</th><th class="r num">${tot.n}</th><th class="r num">${tot.both}</th><th class="r num">${tot.ao}</th><th class="r num">${tot.bo}</th><th class="r num">${tot.none}</th><th class="r num">${tot.n?`${pp((tot.ao-tot.bo)/tot.n)} pp`:'—'}</th></tr></tbody></table></div>`;
 const cmp=(data.comparisons||[]).find(p=>(p.a===ra.id&&p.b===rb.id)||(p.a===rb.id&&p.b===ra.id));
 const ci=cmp?.cluster_bootstrap_ci95?(cmp.a===ra.id?cmp.cluster_bootstrap_ci95:[-cmp.cluster_bootstrap_ci95[1],-cmp.cluster_bootstrap_ci95[0]]):null;
 return pageHead('Compare two models','Same rows, so the difference is real: rows where only one of the two is right, by task. Positive means model A is better.')+sel+section(`${esc(M(a).name)} against ${esc(M(b).name)}`,ci?`Overall difference ${pp(cmp.a===ra.id?cmp.accuracy_difference:-cmp.accuracy_difference)} percentage points; 95% bootstrap interval over task clusters ${pp(ci[0])} to ${pp(ci[1])}.`:'',table)+
  `<p class="foot">Share this comparison: <a href="${href('compare',{a,b})}">${location.origin}${location.pathname}${href('compare',{a,b})}</a></p>`;
}

/* ---------- Data page: every dataset, its licence and its terms ---------- */
function dataPage(focus){
 const items=DATASETS.length?DATASETS:[];
 const card=d=>`<article class="ds" id="ds-${esc(slug(d.id))}"><h3>${d.homepage?ext(d.homepage,esc(d.name)):esc(d.name)}${d.license?`<span class="lic">${esc(d.license)}</span>`:''}${d.content_license&&d.content_license!==d.license?`<span class="lic" title="Licence of the text or images inside the dataset">content ${esc(d.content_license)}</span>`:''}</h3><dl>
  <dt>Used for</dt><dd>${d.tasks.map(t=>`<a href="${taskHref(t)}">${esc(taskName(t))}</a>`).join(', ')} · ${plural(d.rows.length,'row')}</dd>
  ${d.content?`<dt>What a row is</dt><dd>${esc(d.content)}</dd>`:''}
  ${d.labelled_by?`<dt>Answers from</dt><dd>${esc(d.labelled_by)}</dd>`:''}
  ${d.selection?`<dt>How rows were chosen</dt><dd>${esc(d.selection)}</dd>`:''}
  ${d.changes?`<dt>What we changed</dt><dd>${esc(d.changes)}</dd>`:''}
  ${d.content_terms?`<dt>Terms of the material</dt><dd>${esc(d.content_terms)}</dd>`:''}
  ${d.license_url?`<dt>Licence read at</dt><dd>${ext(d.license_url,esc(d.license_url.replace(/^https?:\/\//,'')))}</dd>`:''}
  </dl>${d.citation?`<p class="cite">Cite: ${esc(d.citation)}</p>`:''}${d.bibtex?`<details class="adv"><summary>BibTeX</summary><pre class="code">${esc(d.bibtex)}</pre></details>`:''}</article>`;
 setTimeout(()=>{if(focus){const el=document.getElementById(`ds-${slug(focus)}`);if(el)el.scrollIntoView();}},0);
 return pageHead('Data',`${items.length} public datasets supply every row. Each keeps its own licence; the code is MIT. A dataset is used only when both its licence and the terms of the material inside it allow anyone to copy, change and redistribute it, commercially too.`)+
  `<div class="downloads" style="margin-bottom:8px"><a href="corpus.json" download><span>All rows with answer keys</span><span class="k">JSON</span></a><a href="datasets.json" download><span>Dataset records</span><span class="k">JSON</span></a>${REPO&&!REPO.includes('OWNER')?`<a href="${esc(gh('data/SOURCES.md'))}" target="_blank" rel="noopener"><span>Sources and attribution</span><span class="k">GitHub</span></a><a href="${esc(ghIssue('data-removal.yml'))}" target="_blank" rel="noopener"><span>Ask for a row to be removed</span><span class="k">Issue</span></a>`:''}</div>`+items.map(card).join('');
}

/* ---------- Methodology ---------- */
function methodology(){
 const rows=allCases.length,tasks=taskOrder().length,cats=categoryOrder().length,ds=DATASETS.length,imgs=allCases.filter(c=>isImageTask(c.task)).length;
 const prompt=data.prompt?.system||'';
 const toc=[['what','What is measured'],['rows','Where the rows come from'],['sees','What the model sees'],['answers','How answers are parsed'],['metrics','Metrics'],['verdict','The fit verdict'],['limits','Limits'],['submit','Submitting results'],['cite','Citing and licences']];
 const step=(n,h,p)=>`<div class="step"><b>${n}</b><h4>${h}</h4><p>${p}</p></div>`;
 const body=`<div class="method">
<h2 id="m-what">What is measured</h2>
<p>Decision Bench measures one narrow thing: whether a language model makes the same call a human or an objective record made on a real piece of work. Each row is a real record (a complaint, a contract, a code change, a transcript, a receipt) with one question and a short fixed list of options. The model picks one option and states a probability for each. Nothing is generated, ranked by taste, or graded by another model.</p>
<p>The bench has <strong>${num(rows)} rows</strong> in <strong>${tasks} tasks</strong> across <strong>${cats} use cases</strong>, from <strong>${ds} public datasets</strong>.${imgs?` ${num(imgs)} rows carry an image as well as a text rendering.`:''} The corpus is frozen: its sha256 is in the manifest, every run records the hash it used, and results from different versions are never mixed.</p>
<div class="steps">${step('1','A real record','Sampled from an open-licence dataset by a written rule, in a fixed order, never by looking at model output.')}${step('2','One bounded question','Fixed per task, 12 words or fewer, with 2–10 options each described in one line. Abstain options exist where the data supports them.')}${step('3','An answer from the source','The dataset’s own annotators, or an objective record such as a test result or a filing’s item number.')}${step('4','A strict JSON answer','The model returns one option and a probability for every option. Anything else counts as no answer, not as a guess.')}</div>
<h2 id="m-rows">Where the rows come from</h2>
<p>Every dataset is listed on the <a href="#/data">Data page</a> with its licence, the terms of the material inside it, who decided the answers and how rows were chosen. A dataset is used only when both its own licence and the terms of the text or images inside it allow anyone to copy, change and redistribute it, including commercially. Datasets built on non-commercial or publisher-copyrighted text are not used, even when the dataset itself is MIT.</p>
<p>Rows are chosen deterministically: candidates are ordered by the sha256 of their source id and taken in order while they pass the module's written filters. Where a maintainer dropped a specific record by hand, the module lists it with the reason. Every option is the answer at least once and no option is the answer on more than 60% of a task's rows. Titles are neutral and never shown to models.</p>
<p>Some labels are <em>derived by rule</em> from the record itself, for example a release's version bump from its tags or a claim checked against a chart's own data. Those tasks say so on their task page, and the rule is in the module.</p>
<h2 id="m-sees">What the model sees</h2>
<p>The model input is built by allowlist: the row's record (<code>state</code>), the task instruction, and the options in a fixed per-row shuffled order. The answer, the rationale, the row title, the source and the reader-facing question are never sent. For image rows, vision models receive the image and text-only models receive the text rendering; the two are reported separately.</p>
<p>Every request carries the same system policy, version <code>${esc(data.prompt?.version||'')}</code>:</p>
<pre class="code wrap">${esc(prompt)}</pre>
<p>API models are called through a chat completions endpoint with a JSON schema response format where the provider supports it. CLI models run in an empty temporary directory with tools disabled; a tool call invalidates the answer. The exact request options for each model are on its <a href="#/models">model page</a>.</p>
<h2 id="m-answers">How answers are parsed</h2>
<ul><li>The response must be one JSON object with a label from the options and a probability for exactly the listed options, each a finite number in [0, 1], summing to 1 within 0.02. One surrounding Markdown code fence is tolerated; nothing else is repaired.</li><li>The model's own label is scored, even when it disagrees with its highest probability; that disagreement is recorded.</li><li>A response cut off by the token limit, a refusal, a transport error or invalid JSON is <em>no answer</em>. It counts as wrong for accuracy and is reported separately.</li></ul>
<h2 id="m-metrics">Metrics</h2>
<p>The leaderboard follows the conventions of established evaluation suites: accuracy with an interval, per-slice accuracy, a class-balanced score, calibration, latency and cost, all recomputable from the published predictions.</p>
<table class="metric-table"><thead><tr><th>Metric</th><th>Definition</th><th>Why it is here</th></tr></thead><tbody>
<tr><td>Accuracy</td><td>Share of rows whose answer equals the key. No answer counts as wrong.</td><td>The headline number. Rank ties models whose intervals overlap.</td></tr>
<tr><td>Wilson 95% interval</td><td>Score interval for a binomial proportion; shown as whiskers and beside every accuracy.</td><td>Tasks have 20–40 rows, so differences of a few points are usually within noise.</td></tr>
<tr><td>Per use case, per task</td><td>Accuracy and its interval recomputed on that subset of rows.</td><td>The answer to "can I use it for my case?" lives here, not in the overall number.</td></tr>
<tr><td>Macro F1</td><td>F1 per option, averaged within a task, then averaged across tasks.</td><td>Rewards getting the rare options right, not only the common ones.</td></tr>
<tr><td>Expected calibration error</td><td>Mean gap between stated confidence and observed accuracy over ten confidence bins.</td><td>Says whether the probabilities can be trusted for routing low-confidence rows to a person.</td></tr>
<tr><td>Brier score</td><td>Mean squared error of the stated probability distribution against the one-hot key.</td><td>A single calibration-and-accuracy number; lower is better.</td></tr>
<tr><td>Latency</td><td>Wall-clock time per row at the client: median, 95th and 99th percentile.</td><td>API times measure the endpoint; CLI times include process start-up and are marked.</td></tr>
<tr><td>Cost per 1,000 rows</td><td>Provider-reported cost when the endpoint returns it, otherwise input and output tokens priced at the list prices recorded with the run.</td><td>Comparable across providers; the basis is recorded per row.</td></tr>
<tr><td>Tokens</td><td>Input and output tokens per row as reported by the provider.</td><td>Shows how much of the cost is the record and how much is the model's answer.</td></tr>
<tr><td>Paired difference</td><td>Rows where only one of two models is right, with a bootstrap interval over task clusters.</td><td>Two models on the same rows: the difference is real, not two noisy means.</td></tr>
</tbody></table>
<h2 id="m-verdict">The fit verdict</h2>
<p>Each task and use-case page shows a plain verdict per model, computed from accuracy and its interval, never written by hand: <span class="fit ok">Fits</span> accuracy at or above 90% with the whole 95% interval above 85%; <span class="fit risk">Risky</span> accuracy above 80%; <span class="fit no">Not fit</span> below 80%; <span class="fit na">Not run</span> when the model was not sent those rows, for example an image task and a text-only model. The thresholds are a starting point for a decision, not a guarantee: your data will differ from these rows.</p>
<h2 id="m-limits">Limits</h2>
<ul><li><strong>Contamination.</strong> These are public datasets and may be in a model's training data. Each task page states a contamination risk; fresh derivations are lower risk than famous benchmarks.</li><li><strong>Label noise.</strong> Real labels carry some error. Rows a careful reader could argue either way are dropped by rule where possible, and every row page links to its source record so a label can be challenged.</li><li><strong>Small tasks.</strong> With 20–40 rows per task, read the interval, not the point.</li><li><strong>One prompt.</strong> Every model gets the same instruction and schema. A prompt tuned for one model would likely lift its score; that is out of scope.</li><li><strong>Not a production sample.</strong> The rows come from research datasets and public records, not from your systems.</li></ul>
<h2 id="m-submit">Submitting results</h2>
<p>Results are added by pull request. Run a model on every row with the harness, publish the run into <code>results/&lt;suite&gt;/&lt;model&gt;/</code>, and open a PR with only that folder and the updated leaderboard files. The published folder holds run metadata, one prediction per row and aggregate scores; nothing in it identifies your infrastructure. Maintainers may re-run a submitted model to check it.${REPO&&!REPO.includes('OWNER')?` <a href="${esc(gh('results/README.md'))}" target="_blank" rel="noopener">Full instructions</a>.`:''}</p>
<h2 id="m-cite">Citing and licences</h2>
<p>The harness, the viewer and the row selection code are MIT. Each row keeps its dataset's licence, and the <a href="#/data">Data page</a> carries the citation and BibTeX for every dataset; please cite the datasets behind the tasks you use as well as the bench.${REPO&&!REPO.includes('OWNER')?` The repository's <a href="${esc(gh('CITATION.cff'))}" target="_blank" rel="noopener">CITATION.cff</a> has the bench's own entry.`:''}</p>
<h3>Downloads</h3>
<div class="downloads"><a href="corpus.json" download><span>All rows with answer keys</span><span class="k">JSON</span></a><a href="data.json" download><span>Everything the site shows</span><span class="k">JSON</span></a><a href="datasets.json" download><span>Dataset records</span><span class="k">JSON</span></a><a href="protocol.txt" download><span>Protocol</span><span class="k">Text</span></a>${hasResults()?RUNS.filter(r=>r.files).map(r=>`<a href="${esc(r.files.predictions)}" download><span>${esc(M(keyOf(r)).name)} predictions</span><span class="k">JSONL</span></a>`).join(''):''}</div>
</div>`;
 return pageHead('Methodology','How the bench is built, what a model sees, how answers are scored, and where the limits are.')+`<div class="method-grid">${body}<nav class="toc" aria-label="On this page">${toc.map(([id,l])=>`<a href="#/methodology/${id}">${esc(l)}</a>`).join('')}</nav></div>`;
}

/* ---------- Review mode (maintainers): step through rows, mark each, export ---------- */
const REVIEW_KEY=sha=>`db-review:${sha}`;
const reviewMem={};let reviewFilter='all',reviewMsg='';
function reviewStore(){const sha=data.corpus_sha256;if(!reviewMem[sha]){let v={};try{v=JSON.parse(localStorage.getItem(REVIEW_KEY(sha))||'{}')||{};}catch(e){v={};}reviewMem[sha]=v;}return reviewMem[sha];}
function reviewSave(){try{localStorage.setItem(REVIEW_KEY(data.corpus_sha256),JSON.stringify(reviewStore()));}catch(e){}}
const reviewOf=c=>reviewStore()[c.id]||null;
function setReview(c,patch){const st=reviewStore(),cur=st[c.id]||{};st[c.id]={...cur,...patch,at:new Date().toISOString()};if(!st[c.id].status&&!st[c.id].note)delete st[c.id];reviewSave();}
const reviewList=()=>rowsInOrder().filter(c=>{const r=reviewOf(c);return reviewFilter==='todo'?!r?.status:reviewFilter==='flagged'?r?.status==='flag':true;});
function reviewStep(c,dir){const list=reviewList();let i=list.indexOf(c),n;if(i<0){const all=rowsInOrder(),j=all.indexOf(c);n=dir>0?all.slice(j+1).find(x=>list.includes(x)):all.slice(0,j).reverse().find(x=>list.includes(x));}else n=list[i+dir];if(n)location.hash=href(`review/${encodeURIComponent(n.id)}`);return !!n;}
function reviewPage(id){
 const all=rowsInOrder(),list=reviewList(),c=caseMap.get(id)||list[0];
 const done=all.filter(x=>reviewOf(x)?.status).length,flagged=all.filter(x=>reviewOf(x)?.status==='flag').length;
 const bar=`<div class="rv-top"><div class="rv-progress"><div class="rv-bar" role="progressbar" aria-valuemin="0" aria-valuemax="${all.length}" aria-valuenow="${done}"><i style="width:${all.length?done/all.length*100:0}%"></i><b style="width:${all.length?flagged/all.length*100:0}%"></b></div><span class="num">${num(done)} / ${num(all.length)} reviewed · ${num(flagged)} flagged</span></div><div class="rv-tools">${seg('Show',[['all','All rows'],['todo','Not yet reviewed'],['flagged','Flagged']],'rvfilter',reviewFilter)}<button type="button" class="btn-s" data-rv-export>Export reviews (JSON)</button><label class="btn-s file">Import<input type="file" accept="application/json,.json" data-rv-import hidden></label></div>${reviewMsg?`<p class="rv-msg" role="status">${esc(reviewMsg)}</p>`:''}</div>`;
 if(!c)return pageHead('Review','')+bar+`<p class="muted">${reviewFilter==='flagged'?'No flagged rows.':'Every row has been reviewed.'}</p>`;
 const r=reviewOf(c),status=r?.status==='ok'?'<span class="rv-status ok">✓ Looks right</span>':r?.status==='flag'?'<span class="rv-status flag">⚑ Flagged</span>':'<span class="rv-status">Not reviewed</span>';
 return bar+`<article class="rv" data-rv-id="${esc(c.id)}">${rowPage(c.id,true)}<div class="rv-actions"><div class="rv-buttons"><button type="button" class="btn-s" data-rv="prev" title="Previous (k)">← Previous <kbd>k</kbd></button><button type="button" class="btn-p ok" data-rv="ok" title="Looks right (y)">Looks right <kbd>y</kbd></button><button type="button" class="btn-p flag" data-rv="flag" title="Flag (f)">Flag <kbd>f</kbd></button><button type="button" class="btn-s" data-rv="next" title="Next (j)">Next → <kbd>j</kbd></button>${status}</div><label class="rv-note"><span class="sr">Note</span><textarea id="rv-note" rows="2" placeholder="Note (why is this row wrong or unclear?)">${esc(r?.note||'')}</textarea></label></div></article>`;
}
function exportReviews(){const out=[];for(const c of rowsInOrder()){const r=reviewOf(c);if(r)out.push({id:c.id,task:c.task,title:caseTitle(c),status:r.status==='ok'?'looks_right':r.status==='flag'?'flagged':'note_only',note:r.note||'',reviewed_at:r.at});}
 const doc={kind:'decision-bench-review',exported_at:new Date().toISOString(),corpus:{version:man().version,sha256:data.corpus_sha256},count:out.length,reviews:out};
 const blob=new Blob([JSON.stringify(doc,null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`decision-bench-review-${man().version||'v'}-${new Date().toISOString().slice(0,10)}.json`;document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove();},500);}
function importReviews(text){let doc;try{doc=JSON.parse(text);}catch(e){return 'That file is not valid JSON.';}const items=Array.isArray(doc)?doc:Array.isArray(doc?.reviews)?doc.reviews:null;if(!items)return 'No reviews found in that file.';let n=0,skip=0;const st=reviewStore();for(const it of items){const c=caseMap.get(it?.id);if(!c){skip++;continue;}st[c.id]={status:it.status==='looks_right'||it.status==='ok'?'ok':it.status==='flagged'||it.status==='flag'?'flag':undefined,note:it.note||'',at:it.reviewed_at||new Date().toISOString()};if(!st[c.id].status)delete st[c.id].status;n++;}reviewSave();return `Imported ${plural(n,'review')}${skip?`; skipped ${num(skip)} for rows not in this version`:''}.`;}
let reviewKeys=null;
function bindReview(){
 const art=$('.rv'),c=art&&caseMap.get(art.dataset.rvId);
 $$('[data-rvfilter]').forEach(b=>b.onclick=()=>{reviewFilter=b.dataset.rvfilter;reviewMsg='';render();});
 const ex=$('[data-rv-export]');if(ex)ex.onclick=exportReviews;
 const im=$('[data-rv-import]');if(im)im.onchange=()=>{const f=im.files?.[0];if(!f)return;f.text().then(t=>{reviewMsg=importReviews(t);render();});};
 if(!c)return;
 const note=$('#rv-note');let t;if(note)note.oninput=()=>{clearTimeout(t);t=setTimeout(()=>setReview(c,{note:note.value}),250);};
 const act=a=>{if(note)setReview(c,{note:note.value});if(a==='prev')reviewStep(c,-1);else if(a==='next')reviewStep(c,1);else if(a==='ok'){setReview(c,{status:'ok'});reviewMsg='';if(!reviewStep(c,1))render();}else if(a==='flag'){setReview(c,{status:'flag'});render();setTimeout(()=>$('#rv-note')?.focus(),0);}};
 $$('[data-rv]').forEach(b=>b.onclick=()=>act(b.dataset.rv));
 reviewKeys=e=>{if(e.metaKey||e.ctrlKey||e.altKey)return;const tag=e.target.tagName;if(tag==='TEXTAREA'||tag==='INPUT'||tag==='SELECT'){if(e.key==='Escape')e.target.blur();return;}const k=e.key.toLowerCase(),a=k==='j'?'next':k==='k'?'prev':k==='y'?'ok':k==='f'?'flag':null;if(a){e.preventDefault();act(a);}};
}
document.addEventListener('keydown',e=>{if(reviewKeys&&route.page==='review')reviewKeys(e);
 if(route.page==='row'&&!e.metaKey&&!e.ctrlKey&&!e.altKey&&!['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName)){const c=caseMap.get(route.id);if(!c)return;const rows=taskRows(c.task),i=rows.indexOf(c);if(e.key==='j'&&rows[i+1])location.hash=rowHref(rows[i+1]);if(e.key==='k'&&rows[i-1])location.hash=rowHref(rows[i-1]);}});

/* ---------- Routing and binding ---------- */
const TITLES={home:'Leaderboard',tasks:'Tasks',task:'Task',row:'Row',models:'Models',model:'Model',compare:'Compare',data:'Data',methodology:'Methodology',review:'Review'};
function parseRoute(){
 let h=location.hash.replace(/^#/,'');
 /* Old links: #overview, #tasks?…, #task/<id>, #review/<id>, #data/<id>, #about */
 if(!h.startsWith('/')){const [p,qs]=h.split('?');const map={'':'/','overview':'/','tasks':'/tasks','compare':'/compare','failures':'/','review':'/review','data':'/data','about':'/methodology','reports':'/methodology'};let np=map[p.split('/')[0]];if(p.startsWith('task/'))np=`/row/${p.slice(5)}`;else if(p.startsWith('review/'))np=`/review/${p.slice(7)}`;else if(p.startsWith('data/'))np=`/data/${p.slice(5)}`;h=(np||'/')+(qs?`?${qs}`:'');history.replaceState(null,'',`#${h}`);}
 const [path,qs]=h.slice(1).split('?');const parts=path.split('/').filter(Boolean);
 route.page=TITLES[parts[0]]?parts[0]:'home';route.id=decodeURIComponent(parts.slice(1).join('/')||'');route.q=new URLSearchParams(qs||'');
}
function bindControls(){
 $$('[data-run]').forEach(e=>e.onchange=()=>{popOpen=true;const sel=new Set((route.q.get('models')||RUNS.map(keyOf).join(',')).split(',').filter(Boolean));e.checked?sel.add(e.dataset.run):sel.delete(e.dataset.run);const all=sel.size===RUNS.length;go(withQ({models:all?'':[...sel].join(',')}));});
 $$('[data-pick]').forEach(b=>b.onclick=()=>{popOpen=true;go(withQ({models:b.dataset.pick==='all'?'':'none'}));});
 const pop=$('.models-pop');if(pop)pop.ontoggle=()=>{popOpen=pop.open;};
 $$('[data-sort]').forEach(b=>b.onclick=()=>{const k=b.dataset.sort;sort=sort.key===k?{key:k,dir:sort.dir==='desc'?'asc':'desc'}:{key:k,dir:['latency','cost','tokens','ece','brier','errors'].includes(k)?'asc':'desc'};render(true);});
 $$('[data-more]').forEach(b=>b.onclick=()=>{moreCols=!moreCols;render(true);});
 $$('[data-morerows]').forEach(b=>b.onclick=()=>{rowsShown=10000;render(true);});
 $$('[data-modality]').forEach(b=>b.onclick=()=>go(withQ({modality:b.dataset.modality})));
 const cat=$('#f-category');if(cat)cat.onchange=()=>go(withQ({category:cat.value}));
 const q=$('#f-q');if(q){let t;q.oninput=()=>{clearTimeout(t);t=setTimeout(()=>{const pos=q.selectionStart;history.replaceState(null,'',withQ({q:q.value}));parseRoute();render(true);const nq=$('#f-q');if(nq){nq.focus();nq.setSelectionRange(pos,pos);}},200);};}
 const ca=$('#cmp-a'),cb=$('#cmp-b');if(ca)ca.onchange=()=>go(href('compare',{a:ca.value,b:cb.value}));if(cb)cb.onchange=()=>go(href('compare',{a:ca.value,b:cb.value}));
 $$('[data-copy]').forEach(b=>b.onclick=()=>{const t=b.parentElement.querySelector('pre')?.textContent||'';navigator.clipboard?.writeText(t).then(()=>{b.textContent='Copied';setTimeout(()=>{b.textContent='Copy';},1500);},()=>{b.textContent='Copy failed';});});
 const toggle=tr=>{const d=document.getElementById(tr.dataset.expand);d.hidden=!d.hidden;tr.setAttribute('aria-expanded',String(!d.hidden));};
 $$('[data-expand]').forEach(tr=>{tr.onclick=e=>{if(e.target.closest('a,button'))return;toggle(tr);};tr.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();toggle(tr);}};});
 $$('tr.link[data-href]').forEach(tr=>{tr.onclick=e=>{if(e.target.closest('a,button,input,select'))return;location.hash=tr.dataset.href;};});
}
function render(keepScroll=false){
 if(!data)return;const y=scrollY;parseRoute();
 const page=route.page,id=route.id;
 if(!keepScroll){rowsShown=40;}
 $$('nav a[data-page]').forEach(a=>{const on=a.dataset.page===({task:'tasks',row:'tasks',model:'models',compare:'models',review:'tasks'}[page]||page);a.classList.toggle('active',on);if(on)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
 viz=[];$('#tip').hidden=true;reviewKeys=null;
 const main=$('#main');main.classList.toggle('wide',page==='home');
 main.innerHTML=page==='home'?home():page==='tasks'?taskTable():page==='task'?taskPage(id):page==='row'?rowPage(id):page==='models'?modelsPage():page==='model'?modelPage(id):page==='compare'?comparePage():page==='data'?dataPage(id):page==='methodology'?methodology():page==='review'?reviewPage(id):home();
 const t=page==='row'?caseTitle(caseMap.get(id)||{id}):page==='task'?taskName(id):page==='model'?M(id).name:TITLES[page];
 document.title=`${t} · Decision Bench`;
 drawViz(true);bindControls();if(page==='review')bindReview();
 if(page==='methodology'&&id){const el=document.getElementById(`m-${id}`);if(el)setTimeout(()=>el.scrollIntoView(),0);}
 $('#footer').innerHTML=`<span>Decision Bench ${esc(man().version||'')} · corpus <code>${esc((data.corpus_sha256||'').slice(0,12))}</code> · built ${esc(new Date(data.generated_at).toLocaleDateString())}</span><span>Code MIT · rows keep their <a href="#/data">source licences</a> · <a href="#/review">Review mode</a></span>`;
 if(keepScroll)scrollTo(0,y);else if(page!=='methodology')scrollTo(0,0);
}
async function load(){
 try{const res=await fetch('data.json',{cache:'no-store'});if(!res.ok)throw Error(`HTTP ${res.status}`);data=await res.json();
  try{const d=await fetch('datasets.json',{cache:'no-store'});datasetsDoc=d.ok?await d.json():null;}catch(e){datasetsDoc=null;}
  MODELS={};ORDER=[];for(const m of data.models||[])registerModel(m,true);for(const r of data.runs||[])registerModel({...(r.model||{}),id:keyOf(r)},false);
  allCases=data.cases||[];caseMap=new Map(allCases.map(c=>[c.id,c]));
  recordMap=new Map((data.results||[]).map(r=>[`${r.run_id}:${r.case_id}`,r]));
  statCache.clear();metricCache.clear();
  collectRuns();indexDatasets();
  /* Stable model order everywhere: overall accuracy, then configured-only models. */
  const acc=new Map(RUNS.map(r=>[keyOf(r),subsetMetrics(r,allCases).accuracy]));
  ORDER.sort((a,b)=>(acc.get(b)??-1)-(acc.get(a)??-1));
  $('#task-count').textContent=taskOrder().length;
  const ghl=$('#gh-link');if(REPO&&!REPO.includes('OWNER')){ghl.href=REPO;ghl.hidden=false;}
  render();
 }catch(e){console.error(e);$('#main').innerHTML=`<div class="empty"><h1>Results are not built yet</h1><p>Run <code>python3 -m decision_bench report</code>, then refresh.</p><p class="muted">${esc(e.message)}</p></div>`;}
}
function toggleTheme(){const dark=document.documentElement.dataset.theme?document.documentElement.dataset.theme==='dark':matchMedia('(prefers-color-scheme: dark)').matches;const next=dark?'light':'dark';document.documentElement.dataset.theme=next;try{localStorage.setItem('db-theme',next);}catch(e){}}
window.addEventListener('hashchange',()=>render());
$('#theme').onclick=toggleTheme;load();
