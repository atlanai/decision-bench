/* Decision Bench viewer. Plain ES module, no dependencies.
   Reads data.json (schema 2, from `python3 -m decision_bench report`), datasets.json and protocol.txt. */

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

/* The repository URL lives in one place: <meta name="repo"> in index.html. */
const REPO=(document.querySelector('meta[name="repo"]')?.content||'').replace(/\/+$/,'');
const gh=path=>`${REPO}/blob/main/${path}`;
const ghIssue=template=>`${REPO}/issues/new?template=${template}`;
const ext=(href,html)=>href?`<a href="${esc(href)}" target="_blank" rel="noopener">${html}</a>`:html;

/* ---------- State ---------- */
let data,datasetsDoc=null,protocolText=null,caseMap=new Map(),recordMap=new Map(),runMap=new Map(),allCases=[];
let RUNS=[],PARTIAL=[];
let sort={key:'accuracy',dir:'desc'},moreCols=false;
let refKey=null,hl=[null,''],histModel='',failAll=false,taskAll=false,queueAll=false;
const filters={category:'',source:'',show:'',dataset:''};
let viz=[],vizSeq=0;
const statCache=new Map();
const man=()=>data?.manifest||{};

/* ---------- Model identity: label, colour and interface come from data.json models[] ---------- */
const IFACE={'openai-compatible':'API',typesafe:'API','claude-cli':'Claude Code CLI','codex-cli':'Codex CLI'};
const PALETTE=['#2563eb','#7c3aed','#0f766e','#d97706','#db2777','#0891b2','#65a30d','#c2410c','#6d28d9','#475569'];
let MODELS={},ORDER=[];
function registerModel(m,configured){
 if(!m?.id||MODELS[m.id])return;
 const hash=[...m.id].reduce((n,c)=>(n*31+c.charCodeAt(0))>>>0,0);
 MODELS[m.id]={name:m.label||m.id,short:m.short_label||m.label||m.id,vendor:m.vendor||'',iface:IFACE[m.provider]||m.provider||'',color:m.color||PALETTE[hash%PALETTE.length],configured};
 ORDER.push(m.id);
}
const keyOf=r=>r.model_id||r.model?.id||r.config?.model_id;
const M=k=>MODELS[k]||{name:k,short:k,iface:'',vendor:'',color:'var(--faint)'};
const ident=r=>M(keyOf(r));
const fullName=k=>M(k).iface&&M(k).iface!=='API'?`${M(k).name} · ${M(k).iface}`:M(k).name;
const runName=r=>fullName(keyOf(r));
const runColor=r=>ident(r).color;
const byOrder=(a,b)=>ORDER.indexOf(keyOf(a))-ORDER.indexOf(keyOf(b));
const dotHtml=k=>`<i class="dot" style="background:${esc(M(k).color)}"></i>`;
/* One line per model; the interface is shown only when it is not a plain API (CLI latency includes startup). */
function modelHtml(k,{sub=true}={}){const m=M(k);return `<span class="m">${dotHtml(k)}<span class="m-name">${esc(m.name)}</span>${sub&&m.iface&&m.iface!=='API'?`<span class="m-if">${esc(m.iface)}</span>`:''}</span>`;}

/* ---------- Runs: completed runs on the current corpus, one per model ---------- */
function collectRuns(){
 const by=new Map();
 for(const r of data.runs||[]){
  if(r.config?.corpus_sha256!==data.corpus_sha256||r.current_corpus===false)continue;
  if(!String(r.status||'').startsWith('completed'))continue;
  const k=keyOf(r),o=by.get(k);
  if(!o||r.metrics.cases>o.metrics.cases||(r.metrics.cases===o.metrics.cases&&String(r.completed_at||'')>String(o.completed_at||'')))by.set(k,r);
 }
 const all=[...by.values()];
 RUNS=all.filter(r=>r.coverage?.full!==false);
 PARTIAL=all.filter(r=>r.coverage?.full===false);
}
const hasResults=()=>RUNS.length>0;
const result=(runId,caseId)=>recordMap.get(`${runId}:${caseId}`);
const okOf=v=>!!v&&v.scores.length>0&&v.scores.every(s=>s.correct);

/* ---------- Corpus vocabulary: category › task › row ---------- */
const catKey=c=>c.category;
const catName=c=>c.category_name||man().categories?.[c.category]?.name||c.category;
const taskName=t=>man().tasks?.[t]?.name||allCases.find(c=>c.task===t)?.task_name||t;
const taskLabel=c=>c.task_name||taskName(c.task);
const caseTitle=c=>c.title||c.id;
const askOf=q=>q.ask||null;
const optionOrder=q=>(q.option_order&&q.option_order.length?q.option_order:Object.keys(q.options));
const isRealRow=c=>c.source_kind?c.source_kind==='real':!!c.source;
const origLabel=v=>v==null?'none':Array.isArray(v)?(v.length?v.map(x=>typeof x==='object'?JSON.stringify(x):String(x)).join(', '):'none'):typeof v==='object'?JSON.stringify(v):String(v);
function categoryOrder(){const m=man().categories,keys=m?Object.keys(m):[];for(const c of allCases)if(!keys.includes(catKey(c)))keys.push(catKey(c));return keys.filter(k=>allCases.some(c=>catKey(c)===k));}
function catInfo(k){const m=man().categories?.[k],c=allCases.find(x=>catKey(x)===k);return {name:m?.name||(c&&catName(c))||k,description:m?.description||''};}
function taskOrder(){const t=man().tasks,keys=t?Object.keys(t):[];for(const c of allCases)if(!keys.includes(c.task))keys.push(c.task);return keys;}
function rowsInOrder(){const co=categoryOrder(),to=taskOrder();return allCases.map((c,i)=>[c,i]).sort(([a,i],[b,j])=>co.indexOf(catKey(a))-co.indexOf(catKey(b))||to.indexOf(a.task)-to.indexOf(b.task)||i-j).map(([c])=>c);}
const goldText=c=>{const q=c.questions[0],g=q.gold;return String(g).length<=2&&q.options?.[g]?`${g}: ${clip(String(q.options[g]),42)}`:human(g);};
const sourceBadge=c=>isRealRow(c)?`<span class="badge real" title="${esc(c.source?.dataset||'')}">Real data</span>`:`<span class="badge written" title="Written for this benchmark where no real, redistributable data exists">Written example</span>`;

/* ---------- Datasets: datasets.json when present, else derived from the rows' source fields ---------- */
let DATASETS=[];const dsByRow=new Map();
const normName=s=>String(s||'').toLowerCase().replace(/\s+/g,' ').trim();
const normUrl=u=>String(u||'').toLowerCase().replace(/^https?:\/\/(www\.)?/,'').replace(/\/+$/,'');
function indexDatasets(){
 DATASETS=(datasetsDoc?.datasets||[]).map(d=>({...d,id:d.id||slug(d.name),tasks:d.tasks||[],rows:[],derived:false}));
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
const dsAnchor=d=>`ds-${slug(d.id)}`;
const dsLink=d=>d?`<a href="#data/${esc(encodeURIComponent(d.id))}">${esc(d.name)}</a>`:'';

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

/* ---------- Heatmaps: faded when ≥95%, colour only the misses ---------- */
const heatClass=a=>a>=.95?'h0':a>=.9?'h1':a>=.8?'h2':a>=.65?'h3':'h4';
const heatLegend=()=>`<div class="legend heat-legend"><span><i class="cell h0"></i>≥ 95%</span><span><i class="cell h1"></i>90–95</span><span><i class="cell h2"></i>80–90</span><span><i class="cell h3"></i>65–80</span><span><i class="cell h4"></i>&lt; 65</span></div>`;
const sliceOf=(r,key,name)=>r.metrics.slices?.[key]?.find(x=>x.name===name);
function heatCell(r,s,label){if(!s)return '<td class="hc na">—</td>';return `<td class="hc ${heatClass(s.accuracy)}"${tipAttr(tipBody(`${runName(r)} · ${label}`,[['Accuracy',pct(s.accuracy)],['95% interval',ciText(s.wilson95)],['Correct',`${s.correct}/${s.count}`]]),false)}>${s.accuracy>=.995?'100':(s.accuracy*100).toFixed(s.accuracy>=.1?0:1)}</td>`;}
/* Models as rows, slice values as columns: for slices with few values. */
function heatModels(rs,key,{names={},order}={}){
 let vals=[...new Set(rs.flatMap(r=>(r.metrics.slices?.[key]||[]).map(s=>s.name)))];
 if(order)vals.sort((a,b)=>order.indexOf(a)-order.indexOf(b));
 const count=n=>{for(const r of rs){const s=sliceOf(r,key,n);if(s)return s.count;}return 0;};
 return `<div class="table-wrap"><table class="heat"><thead><tr><th class="sticky">Model</th>${vals.map(n=>`<th class="hc">${esc(names[n]||n)}<span class="sub">${count(n)}</span></th>`).join('')}</tr></thead><tbody>${rs.map(r=>`<tr><th class="sticky" scope="row">${modelHtml(keyOf(r),{sub:false})}</th>${vals.map(n=>heatCell(r,sliceOf(r,key,n),names[n]||n)).join('')}</tr>`).join('')}</tbody></table></div>`;
}
/* Tasks as rows (grouped by category), models as columns. */
function heatTasks(rs,{limit}={}){
 const to=taskOrder(),co=categoryOrder();
 let vals=[...new Set(rs.flatMap(r=>(r.metrics.slices?.task||[]).map(s=>s.name)))];
 const catOf=t=>man().tasks?.[t]?.category||allCases.find(c=>c.task===t)?.category;
 const mean=n=>{const a=rs.map(r=>sliceOf(r,'task',n)?.accuracy).filter(v=>v!=null);return a.reduce((x,y)=>x+y,0)/Math.max(1,a.length);};
 let group=true;
 if(limit){vals=vals.sort((a,b)=>mean(a)-mean(b)).slice(0,limit);group=false;}
 else vals.sort((a,b)=>co.indexOf(catOf(a))-co.indexOf(catOf(b))||to.indexOf(a)-to.indexOf(b));
 const count=n=>{for(const r of rs){const s=sliceOf(r,'task',n);if(s)return s.count;}return 0;};
 let last=null;
 return `<div class="table-wrap"><table class="heat wide"><thead><tr><th class="sticky">Task</th>${rs.map(r=>`<th class="hc mh" title="${esc(runName(r))}">${dotHtml(keyOf(r))}<span>${esc(ident(r).short)}</span></th>`).join('')}</tr></thead><tbody>${vals.map(n=>{let g='';const cat=catOf(n);if(group&&cat!==last){last=cat;g=`<tr class="grp"><th class="sticky">${esc(catInfo(cat).name)}</th><td colspan="${rs.length}"></td></tr>`;}return g+`<tr><th class="sticky" scope="row"><span class="tn">${esc(taskName(n))}</span> <span class="tid">${count(n)}</span></th>${rs.map(r=>heatCell(r,sliceOf(r,'task',n),taskName(n))).join('')}</tr>`;}).join('')}</tbody></table></div>`;
}

/* ---------- Page scaffolding ---------- */
const pageHead=(title,sub,extra='')=>`<header class="page-head"><div><h1>${title}</h1>${sub?`<p class="lede">${sub}</p>`:''}</div>${extra}</header>`;
const section=(title,sub,body,{id='',aside=''}={})=>`<section class="sec"${id?` id="${id}"`:''}><div class="sec-head"><div><h2>${title}</h2>${sub?`<p>${sub}</p>`:''}</div>${aside?`<div class="aside">${aside}</div>`:''}</div>${body}</section>`;
const block=(title,sub,body,{aside='',foot=''}={})=>`<div class="block"><div class="block-head"><h3>${title}</h3>${aside?`<div class="aside">${aside}</div>`:''}</div>${sub?`<p class="help">${sub}</p>`:''}${body}${foot?`<p class="foot">${foot}</p>`:''}</div>`;
const seg=(label,items,attr,current)=>`<div class="seg" role="group" aria-label="${esc(label)}">${items.map(([v,l])=>`<button type="button" data-${attr}="${esc(v)}" aria-pressed="${v===current}">${esc(l)}</button>`).join('')}</div>`;
const selectHtml=(id,label,opts,cur)=>`<label class="sel"><span>${esc(label)}</span><select id="${id}">${opts.map(([v,l])=>`<option value="${esc(v)}"${v===cur?' selected':''}>${esc(l)}</option>`).join('')}</select></label>`;
const noResults=title=>pageHead(title,'')+`<p class="notice">No model has been evaluated on this version yet, so there is nothing to show here. See the <a href="#overview">leaderboard</a> for how results are added.</p>`;

/* ---------- Leaderboard ---------- */
function rankOf(r,rs){const [,hi]=r.metrics.accuracy_wilson95||[r.metrics.accuracy,r.metrics.accuracy];return 1+rs.filter(o=>o!==r&&(o.metrics.accuracy_wilson95?.[0]??o.metrics.accuracy)>hi).length;}
const tokensPerRow=m=>m.tokens?.input_tokens==null?null:(m.tokens.input_tokens+(m.tokens.output_tokens||0))/Math.max(1,m.cases);
function sortValue(r,key){
 const m=r.metrics;
 if(key.startsWith('cat:'))return sliceOf(r,'category',key.slice(4))?.accuracy;
 return {accuracy:m.accuracy,latency:m.latency_ms?.p50,cost:m.cost_per_1000_cases_usd,tokens:tokensPerRow(m),ece:m.reliability?.ece,brier:m.brier,macro:m.macro_task_f1,errors:m.operational_errors}[key];
}
function leaderboard(rs){
 const cats=categoryOrder(),los=rs.flatMap(r=>r.metrics.accuracy_wilson95||[]),[d0]=los.length?zoomDomain(los,.1):[0,1],cx=lin(d0,1,0,56);
 const sorted=rs.slice().sort((a,b)=>{const va=sortValue(a,sort.key),vb=sortValue(b,sort.key);if(va==null)return 1;if(vb==null)return -1;return sort.dir==='asc'?va-vb:vb-va;});
 const th=(key,label,cls='',title='')=>`<th class="${cls}"${title?` title="${esc(title)}"`:''}>${key?`<button type="button" data-sort="${esc(key)}"${sort.key===key?` data-dir="${sort.dir}"`:''}>${label}</button>`:label}</th>`;
 const head=`<tr>${th('','#','rank','1 + the number of models whose 95% interval lies entirely above this one')}${th('','Model')}${th('accuracy','Accuracy','acc','Share of rows answered as the key does, with its Wilson 95% interval')}${cats.map(k=>th(`cat:${k}`,esc(catInfo(k).name),'r cat',`${catInfo(k).name}: accuracy`)).join('')}${th('latency','Latency','r','Median wall-clock time per row')}${th('cost','$ / 1k rows','r','Cost per 1,000 rows (provider-reported, else estimated from list prices)')}${th('tokens','Tokens','r','Input + output tokens per row')}${moreCols?th('ece','ECE','r','Expected calibration error; lower is better')+th('brier','Brier','r')+th('macro','Macro F1','r','Mean F1 across tasks')+th('errors','Errors','r','Rows with no valid answer'):''}</tr>`;
 const row=r=>{const m=r.metrics,ci=m.accuracy_wilson95,rank=rankOf(r,rs),tp=tokensPerRow(m);
  const bar=ci?`<span class="ci" aria-hidden="true"><i style="left:${cx(ci[0])}px;width:${Math.max(2,cx(ci[1])-cx(ci[0]))}px"></i><b style="left:${cx(m.accuracy)}px;background:${esc(runColor(r))}"></b></span>`:'';
  const accTip=tipBody(runName(r),[['Accuracy',pct(m.accuracy)],['95% interval',ciText(ci)],['Correct',`${m.correct}/${m.questions}`]]);
  return `<tr><td class="rank">${rank}</td><td>${modelHtml(keyOf(r))}</td><td class="acc"><span class="accw"${tipAttr(accTip,false)}><span class="accv num">${pct(m.accuracy)}</span>${bar}<span class="n num">${ciText(ci)}</span></span></td>${cats.map(k=>{const s=sliceOf(r,'category',k);return `<td class="r num"${s?tipAttr(tipBody(`${runName(r)} · ${catInfo(k).name}`,[['Accuracy',pct(s.accuracy)],['95% interval',ciText(s.wilson95)],['Correct',`${s.correct}/${s.count}`]]),false):''}>${s?pct0(s.accuracy):'—'}</td>`;}).join('')}<td class="r num">${ms(m.latency_ms?.p50)}</td><td class="r num">${money(m.cost_per_1000_cases_usd)}${m.cost_coverage!=null&&m.cost_coverage<1?`<sup title="Cost known for ${pct(m.cost_coverage)} of attempts">*</sup>`:''}</td><td class="r num"${tp!=null?tipAttr(tipBody(runName(r),[['Input / row',compact(m.tokens.input_tokens/m.cases)],['Output / row',compact((m.tokens.output_tokens||0)/m.cases)]]),false):''}>${compact(tp)}</td>${moreCols?`<td class="r num">${metric(m.reliability?.ece)}</td><td class="r num">${metric(m.brier)}</td><td class="r num">${pct(m.macro_task_f1)}</td><td class="r num">${num(m.operational_errors)}</td>`:''}</tr>`;};
 const partial=rs.some(r=>r.metrics.cost_coverage!=null&&r.metrics.cost_coverage<1);
 return `<div class="table-wrap"><table class="lb"><thead>${head}</thead><tbody>${sorted.map(row).join('')}</tbody></table></div><div class="table-foot"><button type="button" class="linklike" data-more>${moreCols?'Fewer columns':'More columns'}</button><span>${partial?'* Cost known for only part of the attempts. ':''}Models whose 95% intervals overlap share a rank.</span></div>`;
}
function headline(rs){
 const ordered=rs.slice().sort((a,b)=>b.metrics.accuracy-a.metrics.accuracy);
 const acc=ordered.map(r=>{const m=r.metrics,ci=m.accuracy_wilson95||[m.accuracy,m.accuracy];return {key:keyOf(r),color:runColor(r),value:m.accuracy,lo:ci[0],hi:ci[1],tip:tipBody(runName(r),[['Accuracy',pct(m.accuracy)],['95% interval',ciText(ci)]])};});
 const lat=ordered.map(r=>{const l=r.metrics.latency_ms||{};return {key:keyOf(r),color:runColor(r),value:l.p50==null?null:l.p50/1000,tick:l.p95==null?null:l.p95/1000,tip:tipBody(runName(r),[['Median',ms(l.p50)],['p95',ms(l.p95)]])};});
 const cost=ordered.map(r=>{const m=r.metrics,ok=m.cost_coverage===1&&m.cost_per_1000_cases_usd!=null;return ok?{key:keyOf(r),color:runColor(r),value:m.cost_per_1000_cases_usd,tip:tipBody(runName(r),[['$ / 1k rows',money(m.cost_per_1000_cases_usd)],['Basis',(m.cost_bases||[]).join(', ')||'—']])}:{key:keyOf(r),value:null,ghost:'partly known',tip:tipBody(runName(r),[['Known subtotal',`${money(m.cost_per_1000_cases_usd)} / 1k`],['Cost coverage',pct(m.cost_coverage)]])};});
 const [lo]=zoomDomain(acc.map(a=>a.lo),.1);
 return `<div class="grid-3">${block('Accuracy','Whiskers: 95% interval.',vizBox(rowsChart(acc,{fmt:pct,tickFmt:pct0,max:1,min:lo}),'Accuracy by model'))}${block('Median latency','Tick: 95th percentile. CLI times include startup.',vizBox(rowsChart(lat,{fmt:secs,tickFmt:v=>v===0?'0':secs(v)}),'Median latency by model'))}${block('Cost per 1,000 rows','USD, provider-reported or estimated from list prices.',vizBox(rowsChart(cost,{fmt:money,tickFmt:v=>v===0?'$0':`$${v<1?v.toFixed(2):v.toFixed(v<10?1:0)}`}),'Cost per 1,000 rows by model'))}</div>`;
}
/* Every row as one cell. Column i is the same row for every model. */
function answerOf(v){if(!v)return 'Not run';if(!v.scores.some(s=>s.label!=null))return 'No valid answer';return v.scores.map(s=>human(s.label)).join(', ');}
function recordGrid(rs,cs){return w=>{
 const LW=w<640?132:228,groups=[];
 for(const c of cs){const g=groups.at(-1),name=catName(c);if(g&&g.name===name)g.cases.push(c);else groups.push({name,cases:[c]});}
 const avail=w-LW-4,gaps=Math.max(1,groups.length-1),pitch=Math.max(4,Math.min(12,Math.floor((avail-7*gaps)/cs.length))),GAP=groups.length>1?Math.max(7,Math.min(22,Math.floor((avail-pitch*cs.length)/gaps))):0,cell=pitch-1,RH=13;
 const xs=[];let x=0;for(const g of groups){g.x=x;for(const _ of g.cases){xs.push(x);x+=pitch;}g.w=x-g.x-1;x+=GAP;}
 const W=x-GAP;
 const res=rs.map(r=>cs.map(c=>result(r.id,c.id)));
 const wrong=cs.map((c,i)=>{let k=0,m=0;res.forEach(row=>{const v=row[i];if(!v)return;m++;if(!okOf(v))k++;});return [k,m];});
 const cat=`<svg width="${W}" height="18" aria-hidden="true">${groups.map(g=>{const fit=Math.floor(g.w/6.3),short=g.name.split(/\s+/)[0],label=g.name.length<=fit?g.name:short.length<=fit?short:fit>=4?clip(short,fit):'';return `<g${tipAttr(tipBody(g.name,[['Rows',g.cases.length]]),false)}><rect class="hit" x="${g.x}" y="0" width="${g.w+1}" height="18"/>${label?`<text class="t-ink" x="${g.x}" y="10">${esc(label)}</text>`:''}<line class="axis" x1="${g.x}" x2="${g.x+g.w}" y1="16.5" y2="16.5"/></g>`;}).join('')}</svg>`;
 const SH=20,sum=`<svg width="${W}" height="${SH}" aria-hidden="true">${cs.map((c,i)=>{const [k,m]=wrong[i],h=m?Math.round((SH-3)*k/m):0;return `<a href="#task/${esc(c.id)}" tabindex="-1"${tipAttr(tipBody(caseTitle(c),[['Models wrong',`${k} of ${m}`],['Answer key',goldText(c)]]),false)}><rect class="hit" x="${xs[i]}" y="0" width="${pitch}" height="${SH}"/><rect class="rg-base" x="${xs[i]}" y="${SH-1}" width="${cell}" height="1"/>${h?`<rect class="rg-bad" x="${xs[i]}" y="${SH-1-h}" width="${cell}" height="${h}"/>`:''}</a>`;}).join('')}</svg>`;
 const rows=rs.map((r,ri)=>{let n=0;const cells=cs.map((c,i)=>{const v=res[ri][i],ok=okOf(v),err=v&&!v.scores.some(q=>q.label!=null);if(v&&!ok)n++;const cls=!v?'rg-none':err?'rg-err':ok?'rg-ok':'rg-bad';
   const inset=!v||err?.5:0;return `<a href="#task/${esc(c.id)}" tabindex="-1"${tipAttr(tipBody(caseTitle(c),[['Category',catName(c)],['Answer key',goldText(c)],[ident(r).name,answerOf(v)]]),false)}><rect class="${cls}" x="${xs[i]+inset}" y="${inset}" width="${cell-2*inset}" height="${RH-2*inset}"/></a>`;}).join('');
  return `<div class="rg-row"><div class="rg-label" title="${esc(runName(r))}">${w<640?`<span class="m">${dotHtml(keyOf(r))}<span class="m-name">${esc(ident(r).short)}</span></span>`:modelHtml(keyOf(r),{sub:false})}<span class="num">${n} wrong</span></div><svg width="${W}" height="${RH}" aria-hidden="true">${DEFS}${cells}</svg></div>`;}).join('');
 return `<div class="rg" style="--lw:${LW}px"><div class="rg-row"><div class="rg-label"></div>${cat}</div><div class="rg-row rg-sum"><div class="rg-label"><span class="muted">Models wrong</span></div>${sum}</div>${rows}</div>`;
};}
function record(rs){
 const ordered=rs.slice().sort((a,b)=>b.metrics.accuracy-a.metrics.accuracy),cs=rowsInOrder().filter(c=>rs.some(r=>result(r.id,c.id)));
 return `${legend([['cell','var(--rec-ok)','Correct'],['cell','var(--bad)','Wrong'],['hatch','','No valid answer'],['bar','var(--bad)','Bar: how many models got the row wrong']])}<div class="rec">${vizBox(recordGrid(ordered,cs),'Result of every model on every row','rgv')}</div>`;
}
function overviewHead(){
 const real=allCases.filter(isRealRow).length;
 const kpi=(l,v)=>`<div><dt>${l}</dt><dd class="num">${v}</dd></div>`;
 return `<header class="page-head lead"><div><h1>Decision Bench</h1><p class="lede">How well language models make the everyday decisions inside AI software: spotting prompt injection, masking sensitive data, classifying and routing agent traces, judging answers, checking contracts and fixing skills. ${num(real)} of ${num(allCases.length)} rows are real records from <a href="#data">public datasets</a>.</p></div><dl class="kpis">${kpi('Rows',num(allCases.length))}${kpi('Categories',categoryOrder().length)}${kpi('Tasks',taskOrder().length)}${hasResults()?kpi('Models',RUNS.length):''}</dl></header>`;
}
const unevaluated=()=>ORDER.filter(k=>MODELS[k].configured&&!RUNS.some(r=>keyOf(r)===k)&&!PARTIAL.some(r=>keyOf(r)===k));
const howToAdd=()=>`Results are added by pull request: run a model on every row, publish the run into <code>results/</code>, and open a PR. <a href="${esc(gh('results/README.md'))}" target="_blank" rel="noopener">How to submit results</a>.`;
function configuredTable(keys){
 return `<div class="table-wrap"><table class="plain cfg"><thead><tr><th>Model</th><th>Vendor</th><th>Interface</th><th>Result</th></tr></thead><tbody>${keys.map(k=>`<tr><td>${modelHtml(k,{sub:false})}</td><td>${esc(M(k).vendor)}</td><td>${esc(M(k).iface)}</td><td class="muted">Not evaluated yet</td></tr>`).join('')}</tbody></table></div>`;
}
function coverageList(){
 const to=taskOrder();
 return `<div class="cover">${categoryOrder().map(k=>{const info=catInfo(k),cs=allCases.filter(c=>catKey(c)===k),tasks=[...new Set(cs.map(c=>c.task))].sort((a,b)=>to.indexOf(a)-to.indexOf(b));
  return `<div class="cover-cat"><h3><a href="#tasks?category=${esc(encodeURIComponent(k))}">${esc(info.name)}</a></h3>${info.description?`<p>${esc(info.description)}</p>`:''}<ul>${tasks.map(t=>{const n=cs.filter(c=>c.task===t).length;return `<li><span>${esc(taskName(t))}</span><span class="num muted">${n}</span></li>`;}).join('')}</ul></div>`;}).join('')}</div>`;
}
function overview(){
 const head=overviewHead();
 if(!hasResults()){
  const keys=ORDER.filter(k=>MODELS[k].configured);
  return head+section('Leaderboard','',`<p class="notice">No model has been evaluated on this version yet. ${howToAdd()}</p>${keys.length?configuredTable(keys):''}`,{id:'leaderboard'})+
   section('What the bench covers',`${plural(allCases.length,'row')}, one multiple-choice question each. Open a category to read its rows.`,coverageList());
 }
 const rs=RUNS,un=unevaluated();
 const extra=[PARTIAL.length?`Partial runs, not ranked: ${PARTIAL.map(r=>`${esc(ident(r).short)} (${num(r.metrics.cases)} of ${num(allCases.length)} rows)`).join(', ')}.`:'',un.length?`Configured but not evaluated yet: ${un.map(k=>esc(M(k).short)).join(', ')}. ${howToAdd()}`:''].filter(Boolean).map(t=>`<p class="foot">${t}</p>`).join('');
 return head+section('Leaderboard','Sorted by accuracy. Click a column to re-sort.',leaderboard(rs)+extra,{id:'leaderboard'})+
  section('Accuracy, speed and cost','',headline(rs))+
  section('Every row','Each column is one row, in the same position for every model, grouped by category. Hover for the row; click to open it.',record(rs));
}

/* ---------- Analysis ---------- */
function pairedPanel(rs){
 const ids=new Set(rs.map(r=>r.id)),ranked=rs.slice().sort((a,b)=>b.metrics.accuracy-a.metrics.accuracy),keys=new Set(rs.map(keyOf));
 if(!refKey||!keys.has(refKey))refKey=keyOf(ranked[0]);
 const out=new Map();
 for(const p of data.comparisons||[]){if(!ids.has(p.a)||!ids.has(p.b))continue;const ka=keyOf(runMap.get(p.a)),kb=keyOf(runMap.get(p.b));let other,sign;if(kb===refKey){other=ka;sign=1;}else if(ka===refKey){other=kb;sign=-1;}else continue;if(out.has(other))continue;const [lo,hi]=p.cluster_bootstrap_ci95||[p.accuracy_difference,p.accuracy_difference];
  out.set(other,{key:other,d:sign*p.accuracy_difference,lo:sign>0?lo:-hi,hi:sign>0?hi:-lo,p,otherOnly:sign>0?p.a_only_correct:p.b_only_correct,refOnly:sign>0?p.b_only_correct:p.a_only_correct});}
 const rows=[...out.values()].sort((x,y)=>y.d-x.d);
 const sel=selectHtml('ref-model','Reference',ranked.map(r=>[keyOf(r),runName(r)]),refKey);
 if(!rows.length)return section('Paired difference','',`<p class="muted">Paired comparisons need at least two full runs.</p>`);
 const dLo=Math.floor(Math.min(-.05,...rows.map(x=>x.lo))/.05)*.05,dHi=Math.ceil(Math.max(.05,...rows.map(x=>x.hi))/.05)*.05;
 const forest=w=>{const rowH=24,L=Math.min(128,w*.32),R=48,T=4,B=34,h=T+B+rowH*rows.length,pw=w-L-R,x=lin(dLo,dHi,L,L+pw);
  let s=niceTicks(dLo,dHi,pw<260?3:5).filter(t=>t>=dLo-1e-9&&t<=dHi+1e-9).map(t=>`<line class="${Math.abs(t)<1e-9?'zero':'grid'}" x1="${x(t)}" x2="${x(t)}" y1="${T}" y2="${h-B}"/><text x="${x(t)}" y="${h-B+15}" text-anchor="middle">${pp(t)}</text>`).join('');
  s+=`<text x="${x(0)-6}" y="${h-3}" text-anchor="end">← ${esc(M(refKey).short)} better</text><text x="${x(0)+6}" y="${h-3}">other better →</text>`;
  rows.forEach((p,i)=>{const cy=T+rowH*(i+.5),sig=p.lo>0||p.hi<0;
   s+=`<g${tipAttr(tipBody(`${fullName(p.key)} − ${fullName(refKey)}`,[['Difference',`${pp(p.d)} pp`],['95% interval',`${pp(p.lo)} to ${pp(p.hi)} pp`],['Only this model right',p.otherOnly],['Only reference right',p.refOnly],['Shared rows',p.p.cases]]),false)}><rect class="hit" x="0" y="${cy-rowH/2}" width="${w}" height="${rowH}"/>${labelSvg(p.key,0,cy,L-6)}<path d="M${x(p.lo)} ${cy}H${x(p.hi)}" style="stroke:${sig?'var(--ink)':'var(--faint)'};stroke-width:1.5"/><circle cx="${x(p.d)}" cy="${cy}" r="4" style="fill:${esc(M(p.key).color)}"/><text class="t-value" x="${x(p.hi)+6}" y="${cy+4}">${pp(p.d)}</text></g>`;});
  return svg(w,h,s);};
 return section('Paired difference','Each model minus the reference, in percentage points, on the rows both answered. The interval resamples whole tasks; grey lines cross zero: no demonstrated difference.',vizBox(forest,`Accuracy difference versus ${fullName(refKey)}`),{aside:sel});
}
function tradeoffs(rs){
 const pt=(r,xv,extra)=>{const m=r.metrics,ci=m.accuracy_wilson95||[m.accuracy,m.accuracy];return {key:keyOf(r),color:runColor(r),x:xv,y:m.accuracy,lo:ci[0],hi:ci[1],tip:tipBody(runName(r),[['Accuracy',pct(m.accuracy)],['95% interval',ciText(ci)],...extra])};};
 const lat=rs.filter(r=>r.metrics.latency_ms?.p50>0).map(r=>pt(r,r.metrics.latency_ms.p50/1000,[['Median latency',ms(r.metrics.latency_ms.p50)]]));
 const ok=rs.filter(r=>r.metrics.cost_coverage===1&&r.metrics.cost_per_1000_cases_usd>0),ex=rs.filter(r=>!ok.includes(r));
 const cost=ok.map(r=>pt(r,r.metrics.cost_per_1000_cases_usd,[['$ / 1k rows',money(r.metrics.cost_per_1000_cases_usd)]]));
 return `<div class="grid-2">${block('Accuracy vs latency','',vizBox(scatter(lat,{xFmt:secs,xLabel:'Median seconds per row'}),'Accuracy versus median latency'))}${block('Accuracy vs cost','',vizBox(scatter(cost,{xFmt:v=>`$${v<.1?v.toFixed(3):v<1?v.toFixed(2):v.toFixed(v<10?1:0)}`,xLabel:'USD per 1,000 rows'}),'Accuracy versus cost'),{foot:ex.length?`Not plotted, cost only partly known: ${ex.map(r=>esc(ident(r).short)).join(', ')}.`:''})}</div>`;
}
function hlKeys(rs){const ranked=rs.slice().sort((a,b)=>b.metrics.accuracy-a.metrics.accuracy),keys=new Set(rs.map(keyOf));if(!hl[0]||!keys.has(hl[0]))hl[0]=keyOf(ranked[0]);if(hl[1]&&!keys.has(hl[1]))hl[1]='';return hl.filter(Boolean);}
const bins=r=>(r.metrics.reliability?.bins||[]).filter(b=>b.count&&b.confidence!=null&&b.accuracy!=null);
function reliabilityChart(rs,focus){return w=>{
 const h=Math.min(w,400)*.8,L=40,R=10,T=10,B=36,pw=w-L-R,ph=h-T-B,x=lin(0,1,L,L+pw),y=lin(0,1,T+ph,T);
 let s=[0,.25,.5,.75,1].map(t=>`<line class="grid" x1="${L}" x2="${L+pw}" y1="${y(t)}" y2="${y(t)}"/><text x="${L-6}" y="${y(t)+4}" text-anchor="end">${pct0(t)}</text><text x="${x(t)}" y="${T+ph+16}" text-anchor="middle">${pct0(t)}</text>`).join('');
 s+=`<line class="ref" x1="${x(0)}" y1="${y(0)}" x2="${x(1)}" y2="${y(1)}"/><line class="axis" x1="${L}" x2="${L+pw}" y1="${T+ph}" y2="${T+ph}"/><text x="${L+pw}" y="${h-3}" text-anchor="end">Stated confidence → observed accuracy</text>`;
 for(const r of rs.filter(r=>!focus.includes(keyOf(r))))s+=`<polyline class="ghost-line" points="${bins(r).map(b=>`${x(b.confidence)},${y(b.accuracy)}`).join(' ')}"/>`;
 for(const r of rs.filter(r=>focus.includes(keyOf(r)))){const bs=bins(r);s+=`<polyline points="${bs.map(b=>`${x(b.confidence)},${y(b.accuracy)}`).join(' ')}" style="fill:none;stroke:${esc(runColor(r))};stroke-width:2"/>`+bs.map(b=>`<g${tipAttr(tipBody(runName(r),[['Bin',`${pct0(b.lo)}–${pct0(b.hi)}`],['Rows',b.count],['Mean confidence',pct(b.confidence)],['Accuracy',pct(b.accuracy)]]),false)}><circle class="hit" cx="${x(b.confidence)}" cy="${y(b.accuracy)}" r="10"/><circle cx="${x(b.confidence)}" cy="${y(b.accuracy)}" r="${Math.min(7,2.5+Math.sqrt(b.count)/2.5)}" style="fill:${esc(runColor(r))};stroke:var(--bg);stroke-width:1"/></g>`).join('');}
 return svg(w,h,s);};}
function riskChart(rs,focus){return w=>{
 const h=Math.min(w,400)*.8,L=40,R=10,T=10,B=36,pw=w-L-R,ph=h-T-B;
 const pts=r=>(r.metrics.risk_coverage||[]).filter(p=>p.risk!=null).sort((a,b)=>a.coverage-b.coverage);
 const maxRisk=Math.max(.05,...rs.flatMap(r=>pts(r).map(p=>p.risk))),top=niceTicks(0,maxRisk,4).at(-1),x=lin(0,1,L,L+pw),y=lin(0,top,T+ph,T);
 let s=niceTicks(0,top,4).map(t=>`<line class="grid" x1="${L}" x2="${L+pw}" y1="${y(t)}" y2="${y(t)}"/><text x="${L-6}" y="${y(t)+4}" text-anchor="end">${pct0(t)}</text>`).join('')+[0,.25,.5,.75,1].map(t=>`<text x="${x(t)}" y="${T+ph+16}" text-anchor="middle">${pct0(t)}</text>`).join('');
 s+=`<line class="axis" x1="${L}" x2="${L+pw}" y1="${T+ph}" y2="${T+ph}"/><text x="${L+pw}" y="${h-3}" text-anchor="end">Share of answers accepted</text><text x="${L+4}" y="${T+10}">Error rate among accepted</text>`;
 for(const r of rs.filter(r=>!focus.includes(keyOf(r))))s+=`<polyline class="ghost-line" points="${pts(r).map(p=>`${x(p.coverage)},${y(p.risk)}`).join(' ')}"/>`;
 for(const r of rs.filter(r=>focus.includes(keyOf(r)))){const ps=pts(r);s+=`<polyline points="${ps.map(p=>`${x(p.coverage)},${y(p.risk)}`).join(' ')}" style="fill:none;stroke:${esc(runColor(r))};stroke-width:2"/>`+ps.filter((_,i)=>i%Math.max(1,Math.floor(ps.length/8))===0||i===ps.length-1).map(p=>`<g${tipAttr(tipBody(runName(r),[['Threshold',p.threshold.toFixed(3)],['Accepted',`${p.accepted} (${pct(p.coverage)})`],['Wrong among accepted',`${p.errors} (${pct(p.risk)})`]]),false)}><circle class="hit" cx="${x(p.coverage)}" cy="${y(p.risk)}" r="10"/><circle cx="${x(p.coverage)}" cy="${y(p.risk)}" r="3" style="fill:${esc(runColor(r))}"/></g>`).join('');}
 return svg(w,h,s);};}
function latencyChart(rs){return w=>{
 const list=rs.filter(r=>r.metrics.latency_ms?.p50>0);
 const rowH=24,L=Math.min(128,w*.3),R=16,T=4,B=26,h=T+B+rowH*list.length,pw=w-L-R;
 const vals=list.flatMap(r=>[r.metrics.latency_ms.p50,r.metrics.latency_ms.p99].map(v=>v/1000)),dom=logDomain(vals),x=logS(...dom,L,L+pw);
 let s=logTicks(dom).map(t=>`<line class="grid${t.major?'':' minor'}" x1="${x(t.v)}" x2="${x(t.v)}" y1="${T}" y2="${h-B}"/>${t.major||pw>380?`<text x="${x(t.v)}" y="${h-B+15}" text-anchor="middle">${secs(t.v)}</text>`:''}`).join('');
 list.forEach((r,i)=>{const cy=T+rowH*(i+.5),l=r.metrics.latency_ms,[a,b,c]=[l.p50,l.p95,l.p99].map(v=>x(Math.max(v,1e-6)/1000));
  s+=`<g${tipAttr(tipBody(runName(r),[['p50',ms(l.p50)],['p95',ms(l.p95)],['p99',ms(l.p99)]]),false)}><rect class="hit" x="0" y="${cy-rowH/2}" width="${w}" height="${rowH}"/>${labelSvg(keyOf(r),0,cy,L-6)}<path d="M${a} ${cy}H${c}" style="stroke:${esc(runColor(r))};stroke-width:1.5;stroke-opacity:.6"/><path d="M${b} ${cy-5}v10" class="whisker"/><circle cx="${a}" cy="${cy}" r="4" style="fill:${esc(runColor(r))}"/><circle cx="${c}" cy="${cy}" r="3" style="fill:var(--bg);stroke:${esc(runColor(r))};stroke-width:1.5"/></g>`;});
 return svg(w,h,s);};}
function tokensBlock(rs){
 const with_=rs.filter(r=>r.metrics.tokens?.input_tokens!=null);
 if(!with_.length)return block('Tokens per row','',`<p class="muted">No token counts were reported.</p>`);
 const row=(r,v)=>({key:keyOf(r),value:v,color:runColor(r),tip:tipBody(runName(r),[['Per row',compact(v)],['Coverage',pct(r.metrics.tokens.input_tokens_coverage)]])});
 const byIn=with_.slice().sort((a,b)=>a.metrics.tokens.input_tokens/a.metrics.cases-b.metrics.tokens.input_tokens/b.metrics.cases);
 return block('Tokens per row','CLI counts include the tool’s own prompt.',`<div class="grid-2 tight"><div><h4 class="minor-head">Input</h4>${vizBox(rowsChart(byIn.map(r=>row(r,r.metrics.tokens.input_tokens/r.metrics.cases)),{fmt:compact}),'Input tokens per row')}</div><div><h4 class="minor-head">Output</h4>${vizBox(rowsChart(byIn.map(r=>row(r,(r.metrics.tokens.output_tokens||0)/r.metrics.cases)),{fmt:compact}),'Output tokens per row')}</div></div>`);
}
function compare(){
 if(!hasResults())return noResults('Analysis');
 const rs=RUNS.slice().sort((a,b)=>b.metrics.accuracy-a.metrics.accuracy),focus=hlKeys(rs);
 const hlSel=`<div class="sel-row">${selectHtml('hl-a','Highlight',rs.map(r=>[keyOf(r),runName(r)]),hl[0])}${selectHtml('hl-b','and',[['','—'],...rs.filter(r=>keyOf(r)!==hl[0]).map(r=>[keyOf(r),runName(r)])],hl[1])}</div>`;
 const hlLegend=legend(focus.map(k=>['line',M(k).color,fullName(k)]).concat([['line','var(--line-strong)','Other models']]));
 const calTable=`<div class="table-wrap"><table class="plain compact"><thead><tr><th>Model</th><th class="r">ECE</th><th class="r">Brier</th><th class="r">Log loss</th></tr></thead><tbody>${rs.slice().sort((a,b)=>(a.metrics.reliability?.ece??1)-(b.metrics.reliability?.ece??1)).map(r=>`<tr class="${focus.includes(keyOf(r))?'hl':''}"><td>${modelHtml(keyOf(r))}</td><td class="r num">${metric(r.metrics.reliability?.ece)}</td><td class="r num">${metric(r.metrics.brier)}</td><td class="r num">${metric(r.metrics.log_loss)}</td></tr>`).join('')}</tbody></table></div>`;
 const nTasks=new Set(rs.flatMap(r=>(r.metrics.slices?.task||[]).map(s=>s.name))).size,lim=taskAll||nTasks<=16?0:12;
 return pageHead('Analysis','Where each model loses accuracy, how sure it is, and what it costs.')+
  section('Accuracy by task',lim?`The ${lim} tasks with the lowest mean accuracy, of ${nTasks}.`:'Only misses are coloured; faded cells are at or above 95%. Small tasks are diagnostic only.',heatTasks(rs,{limit:lim})+heatLegend(),{aside:nTasks>16?`<button type="button" class="linklike" data-taskall>${taskAll?'Show the 12 hardest':`Show all ${nTasks}`}</button>`:''})+
  section('Real data and written examples','',`<div class="narrow">${heatModels(rs,'source_kind',{names:{real:'Real data',written:'Written examples'},order:['real','written']})}</div>`)+
  pairedPanel(rs)+
  section('Tradeoffs','Up and to the left is better. Vertical lines are 95% intervals.',tradeoffs(rs))+
  section('Confidence','Does a model’s stated confidence match how often it is right?',hlSel+hlLegend+`<div class="grid-2">${block('Reliability','On the diagonal = well calibrated. Dot size reflects the number of rows.',vizBox(reliabilityChart(rs,focus),'Reliability diagram'))}${block('Risk and coverage','Error rate if low-confidence answers are deferred.',vizBox(riskChart(rs,focus),'Risk versus coverage'))}</div><details class="adv"><summary>Calibration scores for every model</summary>${calTable}</details>`)+
  section('Latency and tokens','',`<div class="grid-2">${block('Latency','Dot: median · tick: p95 · ring: p99 · log scale.',vizBox(latencyChart(rs),'Latency percentiles'))}${tokensBlock(rs)}</div>`);
}

/* ---------- Failures ---------- */
function failureGroups(rs){
 const out=[];
 for(const c of rowsInOrder()){const q=c.questions[0];let n=0;const wrong=[];for(const r of rs){const v=result(r.id,c.id);if(!v)continue;n++;const s=v.scores[0];if(!s||!s.correct)wrong.push({r,v,s:s||{label:null,confidence:null,gold:q.gold}});}
  if(wrong.length){const counts={};for(const w of wrong){const l=w.s.label??null;counts[l]=(counts[l]||0)+1;}const top=Object.entries(counts).sort((a,b)=>b[1]-a[1]);out.push({c,q,n,wrong,counts:top,maxConf:Math.max(...wrong.map(w=>w.s.confidence??0)),agree:top[0][0]!=='null'?top[0][1]:0});}}
 return out.sort((a,b)=>b.wrong.length-a.wrong.length||b.maxConf-a.maxConf);
}
const answered=g=>g.counts.map(([l,n])=>`${n}× ${esc(human(l==='null'?null:l))}`).join(', ');
const failRow=g=>`<tr><td><a class="t-link" href="#task/${esc(g.c.id)}">${esc(caseTitle(g.c))}</a><span class="sub">${esc(catName(g.c))} · ${esc(taskLabel(g.c))}</span></td><td class="r num">${g.wrong.length}/${g.n}</td><td>${answered(g)}</td><td>${esc(human(g.q.gold))}</td><td class="r num">${pct0(g.maxConf)}</td></tr>`;
const failHead='<thead><tr><th>Row</th><th class="r">Models wrong</th><th>They answered</th><th>Answer key</th><th class="r">Max confidence</th></tr></thead>';
function failures(){
 if(!hasResults())return noResults('Failures');
 const rs=RUNS.slice().sort((a,b)=>b.metrics.accuracy-a.metrics.accuracy),groups=failureGroups(rs);
 const all=groups.flatMap(g=>g.wrong.map(w=>({...w,c:g.c})));
 const queue=groups.filter(g=>g.n>=2&&g.agree>=g.n/2);
 const stat=(l,v)=>`<div><dt>${l}</dt><dd class="num">${v}</dd></div>`;
 const head=pageHead('Failures','Rows the models get wrong.',`<dl class="kpis">${stat('Wrong answers',num(all.length))}${stat('Rows affected',num(groups.length))}${stat('Confident errors',num(all.filter(x=>(x.s.confidence??0)>=.9).length))}${stat('No valid answer',num(rs.reduce((n,r)=>n+(r.metrics.operational_errors||0),0)))}</dl>`);
 const queueSec=section('Possible label problems',`At least half of the models agree on the same answer, and it differs from the key. <a href="${esc(ghIssue('label-error.yml'))}" target="_blank" rel="noopener">Report a label error</a>.`,queue.length?`<div class="table-wrap"><table class="plain fails">${failHead}<tbody>${(queueAll?queue:queue.slice(0,15)).map(failRow).join('')}</tbody></table></div>${queue.length>15?`<div class="table-foot"><button type="button" class="linklike" data-queueall>${queueAll?'Show the first 15':`Show all ${queue.length}`}</button></div>`:''}`:'<p class="muted">No row has a majority agreeing on one wrong answer.</p>');
 const cats=categoryOrder(),cnt=(r,k)=>all.filter(x=>x.r===r&&catKey(x.c)===k).length,maxC=Math.max(1,...rs.flatMap(r=>cats.map(k=>cnt(r,k))));
 const tot=k=>allCases.filter(c=>catKey(c)===k).length;
 const where=`<div class="table-wrap"><table class="heat"><thead><tr><th class="sticky">Model</th>${cats.map(k=>`<th class="hc">${esc(catInfo(k).name)}<span class="sub">${tot(k)}</span></th>`).join('')}<th class="hc">Total</th></tr></thead><tbody>${rs.map(r=>`<tr><th class="sticky" scope="row">${modelHtml(keyOf(r),{sub:false})}</th>${cats.map(k=>{const v=cnt(r,k),h=v===0?'h0':v/maxC<.2?'h1':v/maxC<.45?'h2':v/maxC<.7?'h3':'h4';return `<td class="hc ${h}"${tipAttr(tipBody(`${runName(r)} · ${catInfo(k).name}`,[['Wrong answers',v],['Rows',tot(k)]]),false)}>${v||'·'}</td>`;}).join('')}<td class="hc h0 strong">${all.filter(x=>x.r===r).length}</td></tr>`).join('')}</tbody></table></div>`;
 const binsC=[[0,.5],[.5,.6],[.6,.7],[.7,.8],[.8,.9],[.9,1.01]],labels=['<50%','50–60','60–70','70–80','80–90','≥90%'];
 const pool=histModel?all.filter(x=>keyOf(x.r)===histModel):all,color=histModel?M(histModel).color:'var(--ink-2)';
 const counts=binsC.map(([a,b])=>pool.filter(x=>(x.s.confidence??0)>=a&&(x.s.confidence??0)<b).length);
 const hist=w=>{const h=200,L=36,R=8,T=18,B=34,pw=w-L-R,ph=h-T-B,top=niceTicks(0,Math.max(1,...counts),4).at(-1),y=lin(0,top,T+ph,T),slot=pw/binsC.length,bw=Math.min(56,slot*.62);
  let s=niceTicks(0,top,4).map(t=>`<line class="grid" x1="${L}" x2="${w-R}" y1="${y(t)}" y2="${y(t)}"/><text x="${L-6}" y="${y(t)+4}" text-anchor="end">${t}</text>`).join('');
  counts.forEach((v,i)=>{const cx=L+slot*(i+.5);s+=`<g${tipAttr(tipBody(`${labels[i]} confidence`,[['Wrong answers',v]]),false)}><rect class="hit" x="${cx-slot/2}" y="${T}" width="${slot}" height="${ph}"/><rect x="${cx-bw/2}" y="${y(v)}" width="${bw}" height="${T+ph-y(v)}" rx="1.5" style="fill:${i===5?'var(--bad)':esc(color)};fill-opacity:${i===5?1:.75}"/>${v?`<text class="t-value" x="${cx}" y="${y(v)-5}" text-anchor="middle">${v}</text>`:''}<text x="${cx}" y="${T+ph+15}" text-anchor="middle">${labels[i]}</text></g>`;});
  s+=`<line class="axis" x1="${L}" x2="${w-R}" y1="${T+ph}" y2="${T+ph}"/><text x="${w-R}" y="${h-3}" text-anchor="end">Confidence placed on the wrong answer</text>`;return svg(w,h,s);};
 const histSel=selectHtml('hist-model','Model',[['','All models'],...rs.map(r=>[keyOf(r),runName(r)])],histModel);
 const shown=failAll?groups:groups.slice(0,25);
 return head+queueSec+
  section('Where the errors are','Wrong answers per model and category. The number under each category is its row count.',where)+
  section('How confident when wrong','Errors at ≥90% confidence would pass a confidence gate.',`<div class="hist">${vizBox(hist,'Confidence of wrong answers')}</div>`,{aside:histSel})+
  section('All failures',`${plural(groups.length,'row')} with at least one wrong answer, most models wrong first.`,`<div class="table-wrap"><table class="plain fails">${failHead}<tbody>${shown.map(failRow).join('')}</tbody></table></div>${groups.length>25?`<div class="table-foot"><button type="button" class="linklike" data-failall>${failAll?'Show the first 25':`Show all ${groups.length}`}</button></div>`:''}`);
}

/* ---------- Rows: category → task → rows ---------- */
function rowMatch(c){
 if(filters.category&&catKey(c)!==filters.category)return false;
 if(filters.source&&(filters.source==='real')!==isRealRow(c))return false;
 if(filters.dataset&&dsByRow.get(c.id)?.id!==filters.dataset)return false;
 if(filters.show&&hasResults()){const st=caseStats(c);if(filters.show==='disagree'&&!(st.ok>0&&st.ok<st.n))return false;if(filters.show==='wrong'&&!(st.ok<st.n))return false;}
 return true;
}
function taskOptionsHtml(rows){
 const sets=new Set(rows.map(c=>Object.keys(c.questions[0].options).sort().join('\u0000')));
 if(sets.size>1)return `<p class="help">Options differ per row (for example: ${esc(Object.keys(rows[0].questions[0].options).slice(0,4).map(human).join(', '))}${Object.keys(rows[0].questions[0].options).length>4?', …':''}).</p>`;
 const q=rows[0].questions[0];return `<ul class="task-opts">${Object.keys(q.options).map(k=>`<li><b>${esc(human(k))}</b> <span>${esc(q.options[k])}</span></li>`).join('')}</ul>`;
}
function filterBar(){
 const ds=filters.dataset&&DATASETS.find(d=>d.id===filters.dataset);
 return `<div class="filters">${selectHtml('filter-category','Category',[['','All'],...categoryOrder().map(k=>[k,catInfo(k).name])],filters.category)}${selectHtml('filter-source','Source',[['','All'],['real','Real data'],['written','Written examples']],filters.source)}${hasResults()?selectHtml('filter-show','Show',[['','All rows'],['disagree','Models disagree'],['wrong','Any model wrong']],filters.show):''}${ds?`<span class="chip">Dataset: ${esc(ds.name)} <button type="button" class="linklike" data-clear-dataset aria-label="Show rows from every dataset">×</button></span>`:''}</div>`;
}
function rowsTable(){
 const results=hasResults(),all=rowsInOrder(),shown=all.filter(rowMatch),real=shown.filter(isRealRow).length,to=taskOrder();
 const body=categoryOrder().map(k=>{const cs=shown.filter(c=>catKey(c)===k);if(!cs.length)return '';const info=catInfo(k);
  const tasks=[...new Set(cs.map(c=>c.task))].sort((a,b)=>to.indexOf(a)-to.indexOf(b));
  return `<section class="cat" id="cat-${esc(k)}"><div class="cat-head"><h2>${esc(info.name)}</h2>${info.description?`<p>${esc(info.description)}</p>`:''}</div>${tasks.map(t=>{const rows=cs.filter(c=>c.task===t),q=rows[0].questions[0];
   return `<div class="task-block"><div class="task-head"><h3>${esc(taskLabel(rows[0]))} <span class="muted">· ${plural(rows.length,'row')}</span></h3><p class="task-ask">${esc(askOf(q)||firstSentence(q.instructions))}</p>${taskOptionsHtml(all.filter(c=>c.task===t))}</div><div class="table-wrap"><table class="plain rows${results?'':' no-res'}"><thead><tr><th>Row</th><th>Answer</th><th>Source</th>${results?'<th>Models correct</th>':''}</tr></thead><tbody>${rows.map(c=>`<tr><td><a class="t-link" href="#task/${esc(c.id)}">${esc(caseTitle(c))}</a>${c.summary?`<span class="sub">${esc(c.summary)}</span>`:''}</td><td>${esc(goldText(c))}</td><td>${sourceBadge(c)}</td>${results?`<td>${correctCell(caseStats(c))}</td>`:''}</tr>`).join('')}</tbody></table></div></div>`;}).join('')}</section>`;}).join('');
 return `<div class="table-meta"><span>${plural(shown.length,'row')} · ${num(real)} real, ${num(shown.length-real)} written</span></div>${body||'<p class="muted">No rows match these filters.</p>'}`;
}
const tasksPage=()=>pageHead('Rows',`Every row by category and task, with its answer. <a href="corpus.json" download>Download all rows (JSON)</a>`)+filterBar()+`<div id="task-table">${rowsTable()}</div>`;

/* ---------- Row detail ---------- */
const labelOf=k=>{const s=String(k).replace(/_/g,' ');return s[0].toUpperCase()+s.slice(1);};
const isObj=v=>v&&typeof v==='object'&&!Array.isArray(v);
/* Only real diffs get diff colouring: a "diff --git" or "---"/"+++" header, or "@@ " hunk lines. */
const isDiff=s=>/^diff --git /m.test(s)||(/^--- \S/m.test(s)&&/^\+\+\+ \S/m.test(s))||/^@@ .* @@/m.test(s);
/* Monospace only for code, logs and column-aligned text; other multi-line text (emails, markdown replies) stays prose. */
const CODE_LINE=/^\s{2,}\S|[{};]\s*$|^\s*(def |function |class |import |from \S+ import|SELECT |FROM |WHERE |\$ |>>> |#!|<\/?[a-z][\w-]*[ >])|^\[?\d{4}-\d\d-\d\d[T ]\d\d:|^\[?\d\d:\d\d(:\d\d)?\]?\s|\S {3,}\S/;
function isCodeish(s){if(/```/.test(s))return true;const lines=s.split('\n').filter(l=>l.trim());if(lines.length<2)return /^\s*(def|function|class|import|SELECT)\b/.test(s);return lines.filter(l=>CODE_LINE.test(l)).length>=Math.max(2,lines.length*.3);}
const pretty=v=>`<pre class="code">${esc(JSON.stringify(v,null,2))}</pre>`;
function renderString(s){
 if(isDiff(s))return `<pre class="code">${s.split('\n').map(l=>/^\+(?!\+\+ )/.test(l)?`<span class="add">${esc(l)}</span>`:/^-(?!-- )/.test(l)?`<span class="del">${esc(l)}</span>`:/^@@/.test(l)?`<span class="hunk">${esc(l)}</span>`:esc(l)).join('\n')}</pre>`;
 if(isCodeish(s))return `<pre class="code">${esc(s)}</pre>`;
 return s.length>200||/\n/.test(s)?`<p class="long${s.length>1600?' clamp':''}">${esc(s)}</p>`:`<span class="sv">${esc(s)}</span>`;
}
/* Arrays of tool calls, spans or events: one row per item, expandable to its full JSON. */
const NAME_KEYS=['tool','tool_name','name','span_name','event','action','function','type','op'];
const STEP_KEYS=['step','seq','index','turn','i'];
const DUR_KEYS=['duration_ms','latency_ms','elapsed_ms','duration'];
const nameOf=o=>{for(const k of NAME_KEYS)if(typeof o[k]==='string')return [k,o[k]];return null;};
function isEventList(v){
 if(!Array.isArray(v)||!v.length||!v.every(isObj))return false;
 const named=v.filter(o=>nameOf(o)).length;
 return named>=Math.ceil(v.length*.8)&&v.some(o=>DUR_KEYS.some(k=>k in o)||'status' in o||['args','arguments','result','input','output','attributes','payload'].some(k=>k in o));
}
function statusOf(o){const s=o.status;if(s==null)return o.error?'error':'';if(typeof s==='string'||typeof s==='number')return String(s);if(isObj(s))return String(s.code??s.status??JSON.stringify(s));return String(s);}
function renderEvents(v){
 return `<div class="events">${v.map((o,i)=>{const [nk,nm]=nameOf(o)||['',`#${i+1}`];const sk=STEP_KEYS.find(k=>o[k]!=null),dk=DUR_KEYS.find(k=>o[k]!=null),st=statusOf(o);
  const rest=Object.fromEntries(Object.entries(o).filter(([k])=>k!==nk&&k!==sk&&k!==dk&&k!=='status'));
  const bad=/err|fail|timeout|denied|4\d\d|5\d\d/i.test(st);
  const dur=dk?(typeof o[dk]==='number'?ms(dk==='duration'&&o[dk]<100?o[dk]*1000:o[dk]):esc(String(o[dk]))):'';
  const hint=Object.keys(rest).length?clip(JSON.stringify(rest.args??rest.arguments??rest.input??rest.attributes??rest),90):'';
  return `<details class="ev"><summary><span class="ev-i num">${esc(sk?o[sk]:i+1)}</span><span class="ev-n">${esc(nm)}</span><span class="ev-s${bad?' bad':''}">${esc(st)}</span><span class="ev-d num">${dur}</span><span class="ev-h">${esc(hint)}</span></summary>${Object.keys(rest).length?pretty(rest):'<p class="muted">No further fields.</p>'}</details>`;}).join('')}</div>`;
}
function renderValue(v,depth=0){
 if(v==null)return '<span class="muted">none</span>';
 if(typeof v==='string')return renderString(v);
 if(typeof v!=='object')return `<span class="num">${esc(String(v))}</span>`;
 if(isEventList(v))return renderEvents(v);
 if(Array.isArray(v)){
  if(!v.length)return '<span class="muted">empty</span>';
  if(v.every(isObj)){const keys=[...new Set(v.flatMap(Object.keys))];const flat=v.every(o=>Object.values(o).every(x=>x==null||typeof x!=='object'||(Array.isArray(x)&&x.every(y=>typeof y!=='object'))));
   if(keys.length<=7&&flat)return `<div class="table-wrap"><table class="st"><thead><tr>${keys.map(k=>`<th>${esc(labelOf(k))}</th>`).join('')}</tr></thead><tbody>${v.map(o=>`<tr>${keys.map(k=>`<td>${o[k]==null?'':Array.isArray(o[k])?esc(o[k].join(', ')):typeof o[k]==='string'?renderString(o[k]):esc(String(o[k]))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
   return depth>=2?pretty(v):`<ol class="sl">${v.map(x=>`<li>${renderValue(x,depth+1)}</li>`).join('')}</ol>`;}
  if(v.every(x=>typeof x!=='object'||x===null))return `<ol class="sl">${v.map(x=>`<li>${renderValue(x,depth+1)}</li>`).join('')}</ol>`;
  return depth>=2?pretty(v):`<ol class="sl">${v.map(x=>`<li>${renderValue(x,depth+1)}</li>`).join('')}</ol>`;
 }
 const ents=Object.entries(v);if(!ents.length)return '<span class="muted">empty</span>';
 /* At most two levels of labelled fields; anything deeper is shown as JSON. */
 if(depth>=3)return pretty(v);
 return `<dl class="kv${depth>1?' nested':''}">${ents.map(([k,x])=>`<div><dt>${esc(labelOf(k))}</dt><dd>${renderValue(x,depth+1)}</dd></div>`).join('')}</dl>`;
}
function renderState(c){
 const st=c.state;
 const body=isObj(st)?`<div class="state">${Object.entries(st).map(([k,v])=>`<section class="field"><h4>${esc(labelOf(k))}</h4>${renderValue(v,1)}</section>`).join('')}</div>`:renderValue(st);
 return body+`<details class="raw"><summary>Raw JSON</summary><button type="button" class="linklike copy" data-copy>Copy</button><pre class="code">${esc(JSON.stringify(st,null,2))}</pre></details>`;
}
/* Compact source line for a real row: dataset (links to the Data page), record id, original label, license. */
function attribution(c){
 const src=c.source;
 if(!src)return `<div class="attrib"><h4 class="minor-head">Source</h4><p>Written example, authored for this benchmark (MIT). <a href="#data">About the data</a></p></div>`;
 const d=dsByRow.get(c.id),orig=src.document_url||src.code_url;
 return `<div class="attrib"><h4 class="minor-head">Source</h4><p>${d?dsLink(d):esc(src.dataset||'')}${src.record_id!=null?` · record <code>${esc(src.record_id)}</code>`:''}${src.original_label!=null?` · original label <code>${esc(clip(origLabel(src.original_label),80))}</code>`:''}</p><p class="muted">${esc(src.license||'')}${src.labelled_by?` · answer from ${esc(src.labelled_by)}`:''}${orig?` · ${ext(orig,'original')}`:''}</p></div>`;
}
function answerKey(c){
 const q=c.questions[0];
 return `<div class="key"><div class="key-gold"><strong>${esc(human(q.gold))}</strong></div>${q.rationale?`<p class="rationale">${esc(q.rationale)}</p>`:''}${c.note?`<p class="row-note">${esc(c.note)}</p>`:''}<h4 class="minor-head">Options</h4><ol class="opts">${optionOrder(q).map(k=>`<li class="${k===q.gold?'gold':''}"><span class="o-k">${esc(human(k))}${k===q.gold?' <span class="tick" aria-label="answer key">✓</span>':''}</span><span class="o-d">${esc(q.options[k])}</span></li>`).join('')}</ol>${attribution(c)}</div>`+
 `<details class="instr"><summary>Instruction sent to the model</summary><p class="long">${esc(q.instructions)}</p>${data.prompt?.system?`<h4 class="minor-head">System prompt (${esc(data.prompt.version||'')})</h4><pre class="code wrap">${esc(data.prompt.system)}</pre>`:''}<p class="help">The model also received the input and the options as JSON. The answer key and rationale are never sent.</p></details>`;
}
function answersTable(c,rs){
 const rows=rs.map(r=>({r,v:result(r.id,c.id)})).filter(x=>x.v).map(x=>({...x,ok:okOf(x.v)})).sort((a,b)=>(a.ok-b.ok)||byOrder(a.r,b.r));
 if(!rows.length)return '';
 const tr=({r,v,ok})=>{const s=v.scores[0],conf=s?.confidence;
  const ans=s?.label!=null?esc(human(s.label)):`<span class="muted">${esc(v.status==='ok'?'no answer':human(v.status))}</span>`;
  const id=`ans-${esc(r.id)}`;
  const probs=Object.entries(s?.probabilities||{}).sort((a,b)=>b[1]-a[1]).map(([l,p])=>`<div class="prob"><span>${esc(human(l))}${l===s.gold?' ✓':''}</span><span class="pt"><i style="width:${p*100}%;background:${l===s.gold?'var(--good)':l===s.label?'var(--bad)':'var(--faint)'}"></i></span><span class="num">${pct(p)}</span></div>`).join('');
  const t=v.tokens||{},file=r.files?.predictions;
  const meta=[`status ${esc(v.status)}`,v.attempt_count!=null?plural(v.attempt_count,'attempt'):'',t.input!=null?`${compact(t.input)} in / ${compact(t.output)} out tokens`:'',file?`<a href="${esc(file)}" download>raw output (predictions.jsonl)</a>`:r.source==='local'?'local run':''].filter(Boolean).join(' · ');
  return `<tr class="ans ${ok?'':'wrong'}" data-expand="${id}" tabindex="0" aria-expanded="false"><td><span class="caret" aria-hidden="true"></span>${modelHtml(keyOf(r))}</td><td class="${ok?'ok':'bad'}">${ok?'✓':'✗'} ${ans}</td><td class="r num">${pct0(conf)}</td><td class="r num">${ms(v.duration_ms)}</td><td class="r num">${money(v.cost_usd)}</td></tr><tr class="ans-detail" id="${id}" hidden><td colspan="5"><div class="ans-grid"><div>${probs||'<p class="muted">No probabilities returned.</p>'}${v.error?`<p class="error">${esc(v.error)}</p>`:''}</div><div class="tiny-meta">${meta}</div></div></td></tr>`;};
 return `<div class="table-wrap"><table class="plain answers"><colgroup><col style="width:38%"><col style="width:26%"><col><col><col></colgroup><thead><tr><th>Model</th><th>Answer</th><th class="r">Confidence</th><th class="r">Latency</th><th class="r">Cost</th></tr></thead><tbody>${rows.map(tr).join('')}</tbody></table></div>`;
}
function verdict(c){
 const st=caseStats(c);if(!st.n)return '';
 const w=Object.entries(st.wrong).sort((a,b)=>b[1]-a[1]),wrongN=st.n-st.ok;
 const others=st.ok===0?(st.n===1?'It':`All ${st.n}`):`The other ${wrongN===1?'one':wrongN}`;
 const tail=!wrongN?'':w.length===1?` ${others} chose ${esc(human(w[0][0]==='null'?null:w[0][0]))}.`:` ${st.ok===0?'They':'The others'} chose ${w.map(([l,n])=>`${esc(human(l==='null'?null:l))} (${n})`).join(', ')}.`;
 return `<p class="verdict"><strong>${st.ok} of ${st.n} models</strong> match the answer key.${tail}</p>`;
}
function taskDetail(id){
 const c=caseMap.get(id);if(!c)return '<div class="empty"><h1>Unknown row</h1><p><a href="#tasks">Back to all rows</a></p></div>';
 const q=c.questions[0];
 const crumb=`<nav class="crumbs" aria-label="Breadcrumb"><a href="#tasks?">Rows</a><span>›</span><a href="#tasks?category=${esc(encodeURIComponent(catKey(c)))}">${esc(catName(c))}</a><span>›</span><span>${esc(taskLabel(c))}</span></nav>`;
 const rs=[...RUNS,...PARTIAL].filter(r=>result(r.id,id));
 const answers=rs.length?answersTable(c,rs):`<p class="muted">${hasResults()?'No result has been recorded for this row.':'No model has been evaluated yet.'}</p>`;
 return crumb+`<header class="case-head"><h1>${esc(caseTitle(c))}</h1><p class="badges">${sourceBadge(c)}</p><p class="ask">${esc(askOf(q)||firstSentence(q.instructions))}</p>${verdict(c)}</header>`+
 `<div class="case-cols"><section class="saw"><h2>What the model saw</h2>${renderState(c)}</section><aside class="keycol"><h2>Answer key</h2>${answerKey(c)}</aside></div>`+
 (hasResults()||rs.length?section('Model answers','',answers):'')+
 `<footer class="case-meta"><code>${esc(c.id)}</code> · ${isRealRow(c)?`${esc(c.source?.license||'')} · <a href="${esc(ghIssue('label-error.yml'))}" target="_blank" rel="noopener">Report a label error</a> · <a href="${esc(ghIssue('data-removal.yml'))}" target="_blank" rel="noopener">Request removal</a>`:`Written example · MIT · <a href="${esc(ghIssue('label-error.yml'))}" target="_blank" rel="noopener">Report a label error</a>`}</footer>`;
}

/* ---------- Review: step through every row; state stays in this browser ----------
   Storage key and per-row key are part of the reviewer's saved progress: `db-review:<corpus sha256>` → {<row id>: {status, note, at}}. */
const REVIEW_KEY=sha=>`db-review:${sha}`;
const caseHash=()=>data.corpus_sha256;
const reviewMem={};
let reviewFilter='all',reviewMsg='';
/* A new corpus version starts with the verdicts saved for earlier versions, matched by row id (newest wins).
   Rows whose id changed start unreviewed; rows that no longer exist are simply never shown. */
function reviewCarry(sha){const out={};try{for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(!k||!k.startsWith('db-review:')||k===REVIEW_KEY(sha))continue;const v=JSON.parse(localStorage.getItem(k)||'{}')||{};for(const[id,r]of Object.entries(v)){if(!out[id]||(r.at||'')>(out[id].at||''))out[id]={...r,carried_from:k.slice(10)};}}}catch(e){}return out;}
function reviewStore(sha){if(!reviewMem[sha]){let v=null;try{v=JSON.parse(localStorage.getItem(REVIEW_KEY(sha))||'null');}catch(e){v=null;}if(!v){v=reviewCarry(sha);reviewMem[sha]=v;if(Object.keys(v).length)reviewSave(sha);}reviewMem[sha]=v||{};}return reviewMem[sha];}
function reviewSave(sha){try{localStorage.setItem(REVIEW_KEY(sha),JSON.stringify(reviewMem[sha]||{}));return true;}catch(e){return false;}}
const reviewOf=c=>reviewStore(caseHash(c))[c.id]||null;
function setReview(c,patch){const st=reviewStore(caseHash(c)),cur=st[c.id]||{};st[c.id]={...cur,...patch,at:new Date().toISOString()};if(!st[c.id].status&&!st[c.id].note)delete st[c.id];reviewSave(caseHash(c));}
const reviewAll=()=>rowsInOrder();
const reviewList=()=>reviewAll().filter(c=>{const r=reviewOf(c);return reviewFilter==='todo'?!r?.status:reviewFilter==='flagged'?r?.status==='flag':true;});
function reviewCurrent(id){const list=reviewList();let c=id&&list.find(x=>x.id===id);if(!c&&id&&reviewFilter!=='all'){const all=reviewAll(),i=all.findIndex(x=>x.id===id);c=all.slice(i+1).find(x=>list.includes(x));}return c||list[0]||null;}
function reviewStep(id,dir){const list=reviewList(),i=list.findIndex(x=>x.id===id);let n;if(i<0){const all=reviewAll(),j=all.findIndex(x=>x.id===id);n=dir>0?all.slice(j+1).find(x=>list.includes(x)):all.slice(0,j).reverse().find(x=>list.includes(x));}else n=list[i+dir];if(n)location.hash=`#review/${encodeURIComponent(n.id)}`;return !!n;}
function reviewAnswer(c){
 const q=c.questions[0];
 return `<div class="key-gold"><span class="k-label">Answer key</span><strong>${esc(human(q.gold))}</strong></div>${q.rationale?`<p class="rationale">${esc(q.rationale)}</p>`:''}${c.note?`<p class="row-note">${esc(c.note)}</p>`:''}<h4 class="minor-head">Options</h4><ol class="opts">${optionOrder(q).map(k=>`<li class="${k===q.gold?'gold':''}"><span class="o-k">${esc(human(k))}${k===q.gold?' <span class="tick" aria-label="answer key">✓</span>':''}</span><span class="o-d">${esc(q.options[k])}</span></li>`).join('')}</ol>${attribution(c)}<details class="instr"><summary>Instruction sent to the model</summary><p class="long">${esc(q.instructions)}</p></details>`;
}
function review(id){
 const all=reviewAll(),c=reviewCurrent(id);
 const done=all.filter(x=>reviewOf(x)?.status).length,flagged=all.filter(x=>reviewOf(x)?.status==='flag').length;
 const bar=`<div class="rv-top"><div class="rv-progress"><div class="rv-bar" role="progressbar" aria-valuemin="0" aria-valuemax="${all.length}" aria-valuenow="${done}"><i style="width:${all.length?done/all.length*100:0}%"></i><b style="width:${all.length?flagged/all.length*100:0}%"></b></div><span class="num">${num(done)} / ${num(all.length)} reviewed, ${plural(flagged,'flagged','flagged')}</span></div><div class="rv-tools">${seg('Show',[['all','All rows'],['todo','Not yet reviewed'],['flagged','Flagged']],'rvfilter',reviewFilter)}<button type="button" class="btn-s" data-rv-export>Export reviews (JSON)</button><label class="btn-s file">Import<input type="file" accept="application/json,.json" data-rv-import hidden></label></div>${reviewMsg?`<p class="rv-msg" role="status">${esc(reviewMsg)}</p>`:''}</div>`;
 if(!c)return pageHead('Review','')+bar+`<p class="muted">${reviewFilter==='flagged'?'No flagged rows.':reviewFilter==='todo'?'Every row has been reviewed.':'No rows.'}</p>`;
 const list=reviewList(),pos=list.indexOf(c),r=reviewOf(c),q=c.questions[0];
 const status=r?.status==='ok'?'<span class="rv-status ok">✓ Looks right</span>':r?.status==='flag'?'<span class="rv-status flag">⚑ Flagged</span>':'<span class="rv-status">Not reviewed</span>';
 return pageHead('Review','Read each row and its answer key. Reviews are saved in this browser only; export them to share.')+bar+
 `<article class="rv" data-rv-id="${esc(c.id)}"><div class="rv-meta"><span>${esc(catName(c))} › ${esc(taskLabel(c))}</span><span class="num">Row ${pos+1} of ${list.length}${reviewFilter!=='all'?` (${reviewFilter==='todo'?'not yet reviewed':'flagged'})`:''}</span></div>
 <h2 class="rv-title"><a href="#task/${esc(c.id)}">${esc(caseTitle(c))}</a> ${isRealRow(c)?'':sourceBadge(c)}</h2><p class="ask">${esc(askOf(q)||firstSentence(q.instructions))}</p>
 <div class="case-cols"><section class="saw"><h3 class="col-h">Input</h3>${renderState(c)}</section><aside class="keycol">${reviewAnswer(c)}</aside></div>
 <div class="rv-actions"><div class="rv-buttons"><button type="button" class="btn-s" data-rv="prev" title="Previous (k)">← Previous <kbd>k</kbd></button><button type="button" class="btn-p ok" data-rv="ok" title="Looks right (y)">Looks right <kbd>y</kbd></button><button type="button" class="btn-p flag" data-rv="flag" title="Flag (f)">Flag <kbd>f</kbd></button><button type="button" class="btn-s" data-rv="next" title="Next (j)">Next → <kbd>j</kbd></button>${status}</div><label class="rv-note"><span class="sr">Note</span><textarea id="rv-note" rows="2" placeholder="Note (why is this row wrong or unclear?)">${esc(r?.note||'')}</textarea></label></div></article>`;
}
function exportReviews(){
 const out=[];for(const c of reviewAll()){const r=reviewOf(c);if(r)out.push({id:c.id,corpus_sha256:caseHash(c),task:c.task,title:caseTitle(c),status:r.status==='ok'?'looks_right':r.status==='flag'?'flagged':'note_only',note:r.note||'',reviewed_at:r.at});}
 const doc={kind:'decision-bench-review',exported_at:new Date().toISOString(),corpora:[{id:data.suite,version:man().version,sha256:data.corpus_sha256}],count:out.length,reviews:out};
 const blob=new Blob([JSON.stringify(doc,null,2)],{type:'application/json'}),a=document.createElement('a');
 a.href=URL.createObjectURL(blob);a.download=`decision-bench-review-${man().version||'v'}-${new Date().toISOString().slice(0,10)}.json`;document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove();},500);
}
function importReviews(text){
 let doc;try{doc=JSON.parse(text);}catch(e){return 'That file is not valid JSON.';}
 const items=Array.isArray(doc)?doc:Array.isArray(doc?.reviews)?doc.reviews:null;if(!items)return 'No reviews found in that file.';
 let n=0,skip=0;const touched=new Set();
 for(const it of items){const c=caseMap.get(it?.id);if(!c){skip++;continue;}const st=reviewStore(caseHash(c));st[c.id]={status:it.status==='looks_right'||it.status==='ok'?'ok':it.status==='flagged'||it.status==='flag'?'flag':undefined,note:it.note||'',at:it.reviewed_at||new Date().toISOString()};if(!st[c.id].status)delete st[c.id].status;touched.add(caseHash(c));n++;}
 for(const sha of touched)reviewSave(sha);
 return `Imported ${plural(n,'review')}${skip?`; skipped ${num(skip)} for rows not in this version`:''}.`;
}
let reviewKeys=null;
function bindReview(){
 const art=$('.rv'),c=art&&caseMap.get(art.dataset.rvId);
 $$('[data-rvfilter]').forEach(b=>b.onclick=()=>{reviewFilter=b.dataset.rvfilter;reviewMsg='';const n=reviewCurrent(c?.id);if(n&&n.id!==c?.id)location.hash=`#review/${encodeURIComponent(n.id)}`;else rerender();});
 const ex=$('[data-rv-export]');if(ex)ex.onclick=exportReviews;
 const im=$('[data-rv-import]');if(im)im.onchange=()=>{const f=im.files?.[0];if(!f)return;f.text().then(t=>{reviewMsg=importReviews(t);rerender();});};
 if(!c)return;
 const note=$('#rv-note');let t;if(note)note.oninput=()=>{clearTimeout(t);t=setTimeout(()=>setReview(c,{note:note.value}),250);};
 const act=a=>{if(note)setReview(c,{note:note.value});if(a==='prev')reviewStep(c.id,-1);else if(a==='next')reviewStep(c.id,1);else if(a==='ok'){setReview(c,{status:'ok'});reviewMsg='';if(!reviewStep(c.id,1))rerender();}else if(a==='flag'){setReview(c,{status:'flag'});rerender();setTimeout(()=>$('#rv-note')?.focus(),0);}};
 $$('[data-rv]').forEach(b=>b.onclick=()=>act(b.dataset.rv));
 reviewKeys=e=>{if(e.metaKey||e.ctrlKey||e.altKey)return;const tag=e.target.tagName;if(tag==='TEXTAREA'||tag==='INPUT'||tag==='SELECT'){if(e.key==='Escape')e.target.blur();return;}const k=e.key.toLowerCase(),a=k==='j'?'next':k==='k'?'prev':k==='y'?'ok':k==='f'?'flag':null;if(a){e.preventDefault();act(a);}};
}
document.addEventListener('keydown',e=>{if(reviewKeys&&location.hash.startsWith('#review'))reviewKeys(e);});

/* ---------- Data: every source dataset, its license and how rows were taken from it ---------- */
function dsTasks(d){
 const byTask=t=>d.rows.filter(c=>c.task===t).length;
 return d.tasks.map(t=>`<span class="ds-task">${esc(taskName(t))} <span class="num muted">${byTask(t)}</span></span>`).join('')||'<span class="muted">—</span>';
}
function dsLicense(d){
 const main=ext(d.license_url,esc(d.license||'—'));
 const text=d.content_license&&d.content_license!==d.license?`<span class="sub">Text: ${esc(d.content_license)}</span>`:'';
 return main+text;
}
function dsDetail(d){
 const field=(label,v)=>v?`<div><dt>${label}</dt><dd>${esc(v)}</dd></div>`:'';
 const rows=d.rows.length;
 return `<dl class="ds-dl">${field('What the text is',d.content)}${field('Terms of the text',d.content_terms)}${field('Labelled by',d.labelled_by)}${field('How rows were chosen',d.selection)}${field('Changes made',d.changes)}${field('Citation',d.citation)}</dl>`+
 (d.bibtex?`<div class="bib"><div class="bib-head"><span class="minor-head">BibTeX</span><button type="button" class="linklike" data-copy>Copy</button></div><pre class="code">${esc(d.bibtex)}</pre></div>`:'')+
 `<p class="ds-links">${rows?`<a href="#tasks?dataset=${esc(encodeURIComponent(d.id))}">Read the ${plural(rows,'row')} from this dataset</a>`:'<span class="muted">No rows from this dataset in this version.</span>'}${d.homepage?` · ${ext(d.homepage,'Dataset homepage')}`:''}${d.license_url?` · ${ext(d.license_url,'License')}`:''}</p>`;
}
function dataPage(){
 const real=allCases.filter(isRealRow),written=allCases.length-real.length,wTasks=[...new Set(allCases.filter(c=>!isRealRow(c)).map(c=>c.task))];
 const head=pageHead('Data',`Where every row comes from. ${num(real.length)} of ${num(allCases.length)} rows are records from ${plural(DATASETS.filter(d=>d.rows.length).length,'public dataset')}; ${num(written)} are written examples.`);
 const policy=`<p class="notice">A dataset is used only if both its own license and the terms of the text inside it allow anyone to redistribute it, including for commercial use. Every real row keeps its source license and links back to its dataset; written examples and the code are MIT.</p>`;
 const list=`<div class="ds-list"><div class="ds-row ds-hdr" aria-hidden="true"><span>Dataset</span><span>Tasks · rows</span><span>License</span><span>What the text is</span><span>Labelled by</span></div>${DATASETS.map(d=>`<details class="ds" id="${esc(dsAnchor(d))}"><summary class="ds-row"><span class="ds-name"><span class="caret" aria-hidden="true"></span>${d.homepage?ext(d.homepage,esc(d.name)):esc(d.name)}</span><span class="ds-tasks">${dsTasks(d)}</span><span>${dsLicense(d)}</span><span class="ds-content">${esc(d.content||'')}</span><span class="ds-by">${esc(d.labelled_by||'')}</span></summary><div class="ds-body">${dsDetail(d)}</div></details>`).join('')}${written?`<div class="ds-row ds-written"><span class="ds-name"><span class="caret blank" aria-hidden="true"></span>Written examples</span><span class="ds-tasks">${wTasks.map(t=>`<span class="ds-task">${esc(taskName(t))} <span class="num muted">${allCases.filter(c=>c.task===t&&!isRealRow(c)).length}</span></span>`).join('')}</span><span>MIT</span><span class="ds-content">Written for this benchmark, only where no real, redistributable labelled data exists.</span><span class="ds-by">The benchmark authors</span></div>`:''}</div>`;
 const note=DATASETS.some(d=>d.derived)?`<p class="foot">Some datasets are listed from their rows only; their full notes are in <a href="${esc(gh('data/SOURCES.md'))}" target="_blank" rel="noopener">data/SOURCES.md</a>.</p>`:'';
 const links=`<ul class="link-list"><li><a href="${esc(gh('data/SOURCES.md'))}" target="_blank" rel="noopener">data/SOURCES.md</a> — sources, licenses, upstream terms and changes, in one file.</li><li><a href="${esc(ghIssue('data-removal.yml'))}" target="_blank" rel="noopener">Request removal of a row</a> — if a row contains your personal data or content you own.</li><li><a href="${esc(ghIssue('label-error.yml'))}" target="_blank" rel="noopener">Report a label error</a> — if an answer key looks wrong.</li>${datasetsDoc?'<li><a href="datasets.json" download>datasets.json</a> — this table as JSON.</li>':''}<li><a href="corpus.json" download>corpus.json</a> — every row with its <code>source</code> record.</li></ul>`;
 return head+policy+section('Datasets','Open a dataset for its terms, how rows were chosen, what was changed, and its citation.',list+note)+section('More','',links);
}

/* ---------- About ---------- */
/* Minimal Markdown for protocol.txt: headings, paragraphs, lists, tables, code fences, inline code, bold, links. */
function inlineMd(s){
 let out=esc(s);
 out=out.replace(/`([^`]+)`/g,'<code>$1</code>');
 out=out.replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');
 out=out.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g,(m,t,href)=>{const raw=href.replace(/&amp;/g,'&');let url;try{url=/^(https?:|#)/.test(raw)?raw:new URL(raw,gh('docs/')).href;}catch(e){return t;}return `<a href="${esc(url)}" target="_blank" rel="noopener">${t}</a>`;});
 return out;
}
function markdown(md){
 const lines=String(md).replace(/\r/g,'').split('\n'),out=[];let i=0;
 while(i<lines.length){
  const l=lines[i];
  if(/^```/.test(l)){const buf=[];i++;while(i<lines.length&&!/^```/.test(lines[i]))buf.push(lines[i++]);i++;out.push(`<pre class="code">${esc(buf.join('\n'))}</pre>`);continue;}
  const h=l.match(/^(#{1,4})\s+(.*)/);if(h){const lv=Math.min(4,h[1].length+1);out.push(`<h${lv}>${inlineMd(h[2])}</h${lv}>`);i++;continue;}
  if(/^\s*\|/.test(l)){const rows=[];while(i<lines.length&&/^\s*\|/.test(lines[i]))rows.push(lines[i++]);const cells=r=>r.trim().replace(/^\||\|$/g,'').split('|').map(x=>x.trim());const body=rows.filter((r,j)=>!(j===1&&/^[\s|:-]+$/.test(r)));out.push(`<div class="table-wrap"><table class="plain compact"><thead><tr>${cells(body[0]).map(c=>`<th>${inlineMd(c)}</th>`).join('')}</tr></thead><tbody>${body.slice(1).map(r=>`<tr>${cells(r).map(c=>`<td>${inlineMd(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`);continue;}
  if(/^\s*[-*]\s+/.test(l)){const items=[];while(i<lines.length&&(/^\s*[-*]\s+/.test(lines[i])||(/^\s{2,}\S/.test(lines[i])&&items.length))){if(/^\s*[-*]\s+/.test(lines[i]))items.push(lines[i].replace(/^\s*[-*]\s+/,''));else items[items.length-1]+=' '+lines[i].trim();i++;}out.push(`<ul>${items.map(x=>`<li>${inlineMd(x)}</li>`).join('')}</ul>`);continue;}
  if(!l.trim()){i++;continue;}
  const buf=[];while(i<lines.length&&lines[i].trim()&&!/^(```|#{1,4}\s|\s*\||\s*[-*]\s+)/.test(lines[i]))buf.push(lines[i++]);
  out.push(`<p>${inlineMd(buf.join(' '))}</p>`);
 }
 return out.join('');
}
function about(){
 const rows=allCases,real=rows.filter(isRealRow),to=taskOrder(),v=man().version||'';
 const tasks=to.filter(t=>rows.some(c=>c.task===t));
 const taskTable=`<div class="table-wrap"><table class="plain meth"><thead><tr><th>Category</th><th>Task</th><th>Question</th><th class="r">Rows</th></tr></thead><tbody>${tasks.map((t,i)=>{const rs=rows.filter(c=>c.task===t),c=rs[0],w=rs.filter(x=>!isRealRow(x)).length,first=!i||catKey(rows.find(x=>x.task===tasks[i-1]))!==catKey(c);return `<tr${first&&i?' class="grp-start"':''}><td>${first?esc(catName(c)):''}</td><td><a href="#tasks?category=${esc(encodeURIComponent(catKey(c)))}">${esc(taskLabel(c))}</a></td><td>${esc(man().tasks?.[t]?.ask||askOf(c.questions[0])||'')}</td><td class="r num">${rs.length}${w?` <span class="badge written" title="${w} written examples">${w===rs.length?'written':`${w} written`}</span>`:''}</td></tr>`;}).join('')}</tbody></table></div>`;
 const link=(p,l)=>`<a href="${esc(gh(p))}" target="_blank" rel="noopener">${l}</a>`;
 const what=`<div class="prose"><p><strong>Decision Bench ${esc(v)}</strong> has ${num(rows.length)} rows in ${categoryOrder().length} categories and ${tasks.length} tasks. A task is one fixed question with a short list of options; a row is one input with its answer. ${num(real.length)} rows are real records from <a href="#data">public datasets</a>, with the answer the dataset's own annotators (or an objective record, such as a repository's tests) gave. The other ${num(rows.length-real.length)} are written examples, used only where no real, redistributable labelled data exists.</p><p>Answers were frozen before any model was run. Public datasets may be in model training data, so scores on real rows may be inflated, and real labels carry some annotator noise.</p></div>`;
 const how=`<div class="prose"><p><strong>What the model sees.</strong> The row's input, the question and its options in a fixed order, and one shared system prompt saying the input is untrusted data. Never the answer, the rationale, the source or the row id. No tools or web search.</p><p><strong>What it returns.</strong> One option and a probability for every option, as JSON. Anything else (invalid JSON, an unknown option, probabilities that do not sum to 1, a cut-off response) counts as no valid answer, which is scored as wrong and also counted separately. Invalid output is not retried.</p><p><strong>Scoring.</strong> Accuracy is the share of rows answered as the key does, with a Wilson 95% interval, overall, per category and per task. Models whose intervals overlap are not reliably different. Cost is provider-reported where available, otherwise estimated from list prices; latency is wall-clock per row, including retries.</p>${data.prompt?.system?`<details class="adv"><summary>System prompt (${esc(data.prompt.version||'')})</summary><pre class="code wrap">${esc(data.prompt.system)}</pre></details>`:''}${protocolText?`<details class="adv" id="protocol"><summary>Full protocol</summary><div class="md">${markdown(protocolText)}</div></details>`:''}</div>`;
 const contribute=`<ul class="link-list"><li>${link('results/README.md','Add results for a model')} — run it on every row, publish the run into <code>results/</code>, open a pull request.</li><li>${link('CONTRIBUTING.md','CONTRIBUTING.md')} — how to propose tasks, rows or fixes.</li><li><a href="${esc(ghIssue('add-model.yml'))}" target="_blank" rel="noopener">Suggest a model</a> · <a href="${esc(ghIssue('label-error.yml'))}" target="_blank" rel="noopener">Report a label error</a> · <a href="${esc(ghIssue('data-removal.yml'))}" target="_blank" rel="noopener">Request data removal</a> · <a href="${esc(ghIssue('bug.yml'))}" target="_blank" rel="noopener">Report a bug</a></li></ul>`;
 const cite=`<div class="prose"><p>Cite the bench with ${link('CITATION.cff','CITATION.cff')} (GitHub shows it as “Cite this repository”), and cite the source datasets of the tasks you use; each has a citation and BibTeX on the <a href="#data">Data</a> page.</p><p><strong>License.</strong> Code and written examples are ${link('LICENSE','MIT')}. Real rows keep their source dataset's license, listed per row and on the <a href="#data">Data</a> page.</p></div>`;
 const dl=(href,label,kind)=>`<a href="${href}" download><span>${label}</span><span class="k">${kind}</span></a>`;
 const downloads=`<div class="downloads">${dl('corpus.json',`All ${num(rows.length)} rows`,'JSON')}${datasetsDoc?dl('datasets.json','Datasets','JSON'):''}${dl('results/'+esc(data.suite||'')+'/leaderboard.json','Leaderboard','JSON')}${protocolText?dl('protocol.txt','Protocol','Markdown'):''}</div>`;
 return pageHead('About','What the bench measures, how a model is run, and how to take part.')+
  section('What it is','',what+taskTable)+section('How a model is run','',how)+section('Contribute','',contribute)+section('Cite and license','',cite)+section('Downloads','',downloads);
}

/* ---------- Routing and binding ---------- */
const TITLES={overview:'Leaderboard',tasks:'Rows',task:'Row',compare:'Analysis',failures:'Failures',review:'Review',data:'Data',about:'About'};
const ALIASES={reports:'about',methodology:'about'};
function rerender(){render({keepScroll:true});}
function bindControls(){
 $$('[data-sort]').forEach(b=>b.onclick=()=>{const k=b.dataset.sort;sort=sort.key===k?{key:k,dir:sort.dir==='desc'?'asc':'desc'}:{key:k,dir:['latency','cost','tokens','ece','brier','errors'].includes(k)?'asc':'desc'};rerender();});
 $$('[data-more]').forEach(b=>b.onclick=()=>{moreCols=!moreCols;rerender();});
 $$('[data-failall]').forEach(b=>b.onclick=()=>{failAll=!failAll;rerender();});
 $$('[data-queueall]').forEach(b=>b.onclick=()=>{queueAll=!queueAll;rerender();});
 $$('[data-taskall]').forEach(b=>b.onclick=()=>{taskAll=!taskAll;rerender();});
 $$('[data-copy]').forEach(b=>b.onclick=e=>{e.preventDefault();const t=b.closest('details,.bib')?.querySelector('pre')?.textContent||'';navigator.clipboard?.writeText(t).then(()=>{b.textContent='Copied';setTimeout(()=>{b.textContent='Copy';},1500);},()=>{b.textContent='Copy failed';});});
 const toggle=tr=>{const d=document.getElementById(tr.dataset.expand);d.hidden=!d.hidden;tr.setAttribute('aria-expanded',String(!d.hidden));};
 $$('[data-expand]').forEach(tr=>{tr.onclick=e=>{if(e.target.closest('a,button'))return;toggle(tr);};tr.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();toggle(tr);}};});
 const on=(id,fn)=>{const e=document.getElementById(id);if(e)e.onchange=()=>{fn(e.value);rerender();};};
 on('ref-model',v=>{refKey=v;});on('hl-a',v=>{hl[0]=v;if(hl[1]===v)hl[1]='';});on('hl-b',v=>{hl[1]=v;});on('hist-model',v=>{histModel=v;});
}
function bindFilters(){
 const re=()=>{$('#task-table').innerHTML=rowsTable();};
 for(const k of ['category','source','show']){const e=$(`#filter-${k}`);if(e)e.addEventListener('change',()=>{filters[k]=e.value;re();});}
 const cl=$('[data-clear-dataset]');if(cl)cl.onclick=()=>{filters.dataset='';location.hash='#tasks';};
}
/* #tasks?category=…&source=…&dataset=… presets the row filters, so filtered views can be linked. */
function applyQuery(qs){for(const k of Object.keys(filters))filters[k]='';for(const [k,v] of new URLSearchParams(qs))if(k in filters)filters[k]=v;}
function render({keepScroll=false,query=false}={}){
 if(!data)return;const y=scrollY;
 const [path,qs]=(location.hash.slice(1)||'overview').split('?');
 const route=path.split('/'),first=ALIASES[route[0]]||route[0],page=TITLES[first]?first:'overview',sub=decodeURIComponent(route.slice(1).join('/')||'');
 if(query&&page==='tasks'&&qs!=null)applyQuery(qs);
 $$('nav a[data-page]').forEach(a=>{const p=a.dataset.page,on=p===(page==='task'?'tasks':page);a.classList.toggle('active',on);if(on)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');if(p==='compare'||p==='failures')a.hidden=!hasResults();});
 viz=[];$('#tip').hidden=true;reviewKeys=null;
 $('#main').innerHTML=page==='review'?review(sub):page==='tasks'?tasksPage():page==='task'?taskDetail(sub):page==='compare'?compare():page==='failures'?failures():page==='data'?dataPage():page==='about'?about():overview();
 document.title=`${page==='task'?caseTitle(caseMap.get(sub)||{id:sub}):TITLES[page]} · Decision Bench`;
 drawViz(true);bindControls();if(page==='tasks')bindFilters();if(page==='review')bindReview();
 if(page==='data'&&sub){const d=DATASETS.find(x=>x.id===sub),el=d&&document.getElementById(dsAnchor(d));if(el){el.open=true;requestAnimationFrame(()=>el.scrollIntoView({block:'start'}));keepScroll=false;}}
 $('#footer').innerHTML=`<span>Decision Bench ${esc(man().version||'')} · generated ${esc(new Date(data.generated_at).toLocaleDateString('en-US',{year:'numeric',month:'short',day:'numeric'}))}</span><span>Code and written examples MIT · real rows keep their <a href="#data">source licenses</a> · <a href="${esc(REPO)}" target="_blank" rel="noopener">GitHub</a></span>`;
 if(keepScroll)scrollTo(0,y);
}
async function getJSON(url){const res=await fetch(url,{cache:'no-store'});if(!res.ok)throw Error(`${url}: HTTP ${res.status}`);return res.json();}
async function load(){
 try{
  const d=await getJSON('data.json');
  if(d.schema_version!==2)throw Error(`data.json schema ${d.schema_version} is not supported; rebuild it with the current harness`);
  /* The dataset registry may be embedded in the manifest; otherwise it is the optional datasets.json. */
  const inline=d.manifest?.datasets,inlineList=Array.isArray(inline)?inline:inline&&typeof inline==='object'?Object.entries(inline).map(([id,x])=>({id,...x})):null;
  const [ds,pt]=await Promise.all([inlineList?.length?{datasets:inlineList}:getJSON('datasets.json').catch(()=>null),fetch('protocol.txt',{cache:'no-store'}).then(r=>r.ok?r.text():null).catch(()=>null)]);
  data=d;datasetsDoc=ds&&Array.isArray(ds.datasets)?ds:null;protocolText=pt;
  allCases=data.cases||[];caseMap=new Map(allCases.map(c=>[c.id,c]));
  recordMap=new Map((data.results||[]).map(r=>[`${r.run_id}:${r.case_id}`,r]));runMap=new Map((data.runs||[]).map(r=>[r.id,r]));
  MODELS={};ORDER=[];for(const m of data.models||[])registerModel(m,true);for(const r of data.runs||[])registerModel(r.model||{id:keyOf(r)},false);
  collectRuns();statCache.clear();indexDatasets();
  /* Stable model order everywhere: accuracy of evaluated models, then configured order. */
  const acc=new Map(RUNS.map(r=>[keyOf(r),r.metrics.accuracy]));
  ORDER=ORDER.map((k,i)=>[k,i]).sort(([a,i],[b,j])=>(acc.get(b)??-1)-(acc.get(a)??-1)||i-j).map(([k])=>k);
  $('#task-count').textContent=allCases.length;
  render({keepScroll:true,query:true});
 }catch(e){console.error(e);$('#main').innerHTML=`<div class="empty"><h1>The site data is not built yet</h1><p>Run <code>python3 -m decision_bench report</code>, then reload.</p><p class="muted">${esc(e.message)}</p></div>`;}
}
function toggleTheme(){const dark=document.documentElement.dataset.theme?document.documentElement.dataset.theme==='dark':matchMedia('(prefers-color-scheme: dark)').matches;const next=dark?'light':'dark';document.documentElement.dataset.theme=next;try{localStorage.setItem('db-theme',next);}catch(e){}}
window.addEventListener('hashchange',()=>{render({query:true});if(!location.hash.startsWith('#data/'))window.scrollTo(0,0);});
/* Reload is only useful while `python3 -m decision_bench serve` is running locally. */
const refresh=$('#refresh');if(refresh){if(/^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname)){refresh.hidden=false;refresh.onclick=load;}}
$('#theme').onclick=toggleTheme;load();
