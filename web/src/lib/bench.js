/* The benchmark as the site sees it: data.json (schema 2, from `python3 -m decision_bench report`) and datasets.json,
   indexed once at load. Everything here is read-only after init(), so pages call these helpers directly. */
import {slug, human, clip} from './format.js';
import {TASK_COPY} from './names.js';
import {imageInputExclusion} from './eligibility.js';

export let data = null;
export let allCases = [];
export let caseMap = new Map();
export let RUNS = [], PARTIAL = [], DATASETS = [];
export let MODELS = {}, ORDER = [];
let recordMap = new Map(), rowsByTask = new Map(), dsByRow = new Map(), CAT_ORDER = [], TASK_ORDER = [];
const statCache = new Map(), metricCache = new Map();

export const man = () => data?.manifest || {};
export const REPO = (document.querySelector('meta[name="repo"]')?.content || '').replace(/\/+$/, '');
export const repoOk = () => REPO && !REPO.includes('OWNER');
export const gh = path => `${REPO}/blob/main/${path}`;
export const ghIssue = (template, params = {}) => `${REPO}/issues/new?template=${template}${Object.entries(params).map(([k, v]) => `&${k}=${encodeURIComponent(v)}`).join('')}`;

/* ---------- Models: label, colour, vendor logo and interface come from data.json models[] ---------- */
const IFACE = {'openai-compatible': 'API', typesafe: 'API', djev: 'API', sage: 'API', tev1: 'API', laya: 'API', 'claude-cli': 'Claude Code CLI', 'codex-cli': 'Codex CLI'};
const PALETTE = ['#2563eb', '#7c3aed', '#0f766e', '#d97706', '#db2777', '#0891b2', '#65a30d', '#c2410c', '#6d28d9', '#475569'];
const LOGOS = {'together ai': 'together.ai', together: 'together.ai', google: 'google.com', anthropic: 'anthropic.com', openai: 'openai.com', deepseek: 'deepseek.com', 'z.ai': 'z.ai', zhipu: 'z.ai', qwen: 'qwen.ai', alibaba: 'alibabacloud.com', amazon: 'amazon.com', aws: 'amazon.com', typesafe: 'typesafe.ai', laya: 'convaiinnovations.com', convai: 'convaiinnovations.com'};
function registerModel(m, configured) {
  if (!m?.id || MODELS[m.id]) return;
  const hash = [...m.id].reduce((n, c) => (n * 31 + c.charCodeAt(0)) >>> 0, 0), vendor = m.vendor || '', logo = LOGOS[vendor.toLowerCase()];
  MODELS[m.id] = {id: m.id, name: m.label || m.id, short: m.short_label || m.label || m.id, vendor, iface: IFACE[m.provider] || m.provider || '', provider: m.provider, color: m.color || PALETTE[hash % PALETTE.length], logo: logo ? `assets/logos/${logo}.png` : null, vision: !!m.vision, configured, api_model: m.api_model, request: m.request, pricing: m.pricing};
  ORDER.push(m.id);
}
export const keyOf = r => r.model_id || r.model?.id || r.config?.model_id;
export const M = k => MODELS[k] || {id: k, name: k, short: k, iface: '', vendor: '', color: 'var(--muted-foreground)', logo: null};
export const ident = r => M(keyOf(r));
export const fullName = k => M(k).iface && M(k).iface !== 'API' ? `${M(k).name} · ${M(k).iface}` : M(k).name;
export const runName = r => fullName(keyOf(r));
export const runColor = r => ident(r).color;
export const byOrder = (a, b) => ORDER.indexOf(keyOf(a)) - ORDER.indexOf(keyOf(b));
export const unevaluated = () => ORDER.filter(k => MODELS[k].configured && !RUNS.some(r => keyOf(r) === k) && !PARTIAL.some(r => keyOf(r) === k));

/* ---------- Runs: completed runs on the current corpus, one per model ---------- */
function collectRuns() {
  const by = new Map();
  for (const r of data.runs || []) {
    if (r.config?.corpus_sha256 !== data.corpus_sha256 || r.current_corpus === false) continue;
    if (!String(r.status || '').startsWith('completed')) continue;
    const k = keyOf(r), o = by.get(k);
    if (!o || r.metrics.cases > o.metrics.cases || (r.metrics.cases === o.metrics.cases && String(r.completed_at || '') > String(o.completed_at || ''))) by.set(k, r);
  }
  const all = [...by.values()].sort(byOrder);
  RUNS = all.filter(r => r.coverage?.full !== false);
  PARTIAL = all.filter(r => r.coverage?.full === false);
}
export const hasResults = () => RUNS.length > 0;
export const rawResult = (runId, caseId) => recordMap.get(`${runId}:${caseId}`);
export const exclusionReason = (runId, caseId) => imageInputExclusion(caseMap.get(caseId), rawResult(runId, caseId));
export const result = (runId, caseId) => exclusionReason(runId, caseId) ? undefined : rawResult(runId, caseId);
export const okOf = v => !!v && v.scores.length > 0 && v.scores.every(s => s.correct);
export const answered = v => !!v && v.scores.some(s => s.label != null);
export const answerOf = v => !v ? 'Not run' : !answered(v) ? 'No valid answer' : v.scores.map(s => human(s.label)).join(', ');

/* ---------- Corpus vocabulary: use case › task › row ---------- */
export const catKey = c => c.category;
export const taskInfo = t => man().tasks?.[t] || {};
export const taskRows = t => rowsByTask.get(t) || [];
export const taskName = t => TASK_COPY[t]?.[0] || taskInfo(t).name || taskRows(t)[0]?.task_name || t;
/* The exact question the model is asked; taskBlurb says in plain words what the task is, taskPicks what it chooses between. */
export const taskAsk = t => taskInfo(t).ask || taskRows(t)[0]?.questions[0].ask || '';
export const taskBlurb = t => TASK_COPY[t]?.[1] || taskAsk(t);
export const taskPicks = t => TASK_COPY[t]?.[2] || '';
export const taskCat = t => taskInfo(t).category || taskRows(t)[0]?.category;
export const isImageTask = t => (taskInfo(t).modality || (taskRows(t).some(c => c.assets?.length) ? 'image' : 'text')) !== 'text';
export const caseTitle = c => c.title || c.id;
export const optionOrder = q => q.option_order?.length ? q.option_order : Object.keys(q.options);
/* Option keys that come from the record (tool names, file paths, hashes) are shown verbatim; fixed labels are humanised. */
export const optLabel = (t, k) => k == null ? 'no answer' : taskInfo(t).per_row_options ? String(k) : human(k);
export const taskOptions = t => { const q = taskRows(t)[0]?.questions[0]; return q ? optionOrder(q) : []; };
export const origLabel = v => v == null ? 'none' : Array.isArray(v) ? (v.length ? v.map(x => typeof x === 'object' ? JSON.stringify(x) : String(x)).join(', ') : 'none') : typeof v === 'object' ? JSON.stringify(v) : String(v);
export const categoryOrder = () => CAT_ORDER;
export const taskOrder = () => TASK_ORDER;
export function catInfo(k) { const m = man().categories?.[k], c = allCases.find(x => catKey(x) === k); return {name: m?.name || c?.category_name || k, description: m?.description || ''}; }
export function rowsInOrder() { const co = CAT_ORDER, to = TASK_ORDER; return allCases.map((c, i) => [c, i]).sort(([a, i], [b, j]) => co.indexOf(catKey(a)) - co.indexOf(catKey(b)) || to.indexOf(a.task) - to.indexOf(b.task) || i - j).map(([c]) => c); }
export const goldText = c => { const q = c.questions[0], g = q.gold; return String(g).length <= 2 && q.options?.[g] ? `${g}: ${clip(String(q.options[g]), 42)}` : human(g); };
export const assetUrl = a => String(a.path || '').replace(/^data\/assets\//, 'assets/rows/');

/* ---------- Datasets: datasets.json when present, else derived from the rows' source fields ---------- */
const normName = s => String(s || '').toLowerCase().replace(/\s+/g, ' ').trim();
const normUrl = u => String(u || '').toLowerCase().replace(/^https?:\/\/(www\.)?/, '').replace(/\/+$/, '');
function indexDatasets(doc) {
  DATASETS = (doc?.datasets || []).map(d => ({...d, id: d.id || slug(d.name), tasks: [...(d.tasks || [])], rows: [], derived: false}));
  const byId = new Map(DATASETS.map(d => [d.id, d])), byName = new Map(DATASETS.map(d => [normName(d.name), d])), byHome = new Map(DATASETS.filter(d => d.homepage).map(d => [normUrl(d.homepage), d]));
  dsByRow = new Map();
  for (const c of allCases) {
    const s = c.source; if (!s) continue;
    let d = byId.get(s.dataset_id) || byName.get(normName(s.dataset)) || byHome.get(normUrl(s.url));
    if (!d) { const id = s.dataset_id || slug(s.dataset) || 'unknown'; d = {id, name: s.dataset || id, homepage: s.url, license: s.license, labelled_by: s.labelled_by, citation: s.citation, tasks: [], rows: [], derived: true}; DATASETS.push(d); byId.set(id, d); byName.set(normName(d.name), d); }
    d.rows.push(c); dsByRow.set(c.id, d);
  }
  for (const d of DATASETS) for (const c of d.rows) if (!d.tasks.includes(c.task)) d.tasks.push(c.task);
  for (const d of DATASETS) d.tasks.sort((a, b) => TASK_ORDER.indexOf(a) - TASK_ORDER.indexOf(b));
  DATASETS.sort((a, b) => TASK_ORDER.indexOf(a.tasks[0]) - TASK_ORDER.indexOf(b.tasks[0]));
}
export const dsOf = c => dsByRow.get(c.id) || null;
export const datasetsOfTask = t => [...new Set(taskRows(t).map(dsOf).filter(Boolean))];

/* ---------- Metrics recomputed in the browser for any subset of rows (a use case, a task, a modality) ---------- */
export function wilson(k, n, z = 1.96) { if (!n) return null; const p = k / n, d = 1 + z * z / n, c = (p + z * z / (2 * n)) / d, h = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d; return [Math.max(0, c - h), Math.min(1, c + h)]; }
function quantile(vals, q) { const a = vals.filter(v => v != null).sort((x, y) => x - y); if (!a.length) return null; const i = (a.length - 1) * q, lo = Math.floor(i), hi = Math.ceil(i); return a[lo] + (a[hi] - a[lo]) * (i - lo); }
export const meanOf = a => { const b = a.filter(v => v != null); return b.length ? b.reduce((x, y) => x + y, 0) / b.length : null; };
export function subsetMetrics(run, cases) {
  const key = `${run.id}|${cases.length}|${cases[0]?.id}|${cases.at(-1)?.id}`;
  if (metricCache.has(key)) return metricCache.get(key);
  const recs = cases.map(c => result(run.id, c.id)).filter(Boolean);
  const scores = recs.flatMap(r => r.scores), n = scores.length, correct = scores.filter(s => s.correct).length;
  const known = recs.map(r => r.cost_usd).filter(v => v != null);
  const bins = []; for (let i = 0; i < 10; i++) bins.push({lo: i / 10, hi: (i + 1) / 10, count: 0, conf: 0, acc: 0});
  for (const s of scores) { if (s.confidence == null) continue; const b = bins[Math.min(9, Math.floor(s.confidence * 10))]; b.count++; b.conf += s.confidence; b.acc += s.correct ? 1 : 0; }
  const withConf = scores.filter(s => s.confidence != null).length;
  const ece = withConf ? bins.reduce((e, b) => b.count ? e + b.count / withConf * Math.abs(b.acc / b.count - b.conf / b.count) : e, 0) : null;
  const m = {excluded: cases.filter(c => exclusionReason(run.id, c.id)).length, cases: recs.length, questions: n, correct, accuracy: n ? correct / n : null, wilson: wilson(correct, n),
    errors: recs.filter(r => r.status !== 'ok').length, highConfErrors: scores.filter(s => !s.correct && (s.confidence || 0) >= .9).length,
    latency: {p50: quantile(recs.map(r => r.duration_ms), .5), p95: quantile(recs.map(r => r.duration_ms), .95)},
    costPer1k: known.length ? known.reduce((x, y) => x + y, 0) / known.length * 1000 : null, costCoverage: recs.length ? known.length / recs.length : null,
    tokensIn: meanOf(recs.map(r => r.tokens?.input)), tokensOut: meanOf(recs.map(r => r.tokens?.output)),
    brier: meanOf(scores.map(s => s.brier)), ece,
    bins: bins.map(b => ({...b, confidence: b.count ? b.conf / b.count : null, accuracy: b.count ? b.acc / b.count : null}))};
  metricCache.set(key, m); return m;
}
export const macroF1 = (run, tasks) => meanOf(tasks.map(t => {
  const rows = taskRows(t).map(c => result(run.id, c.id)).filter(Boolean).flatMap(r => r.scores); if (!rows.length) return null;
  const labels = new Set(rows.flatMap(s => [s.gold, s.label].filter(x => x != null)));
  return meanOf([...labels].map(l => { const tp = rows.filter(s => s.gold === l && s.label === l).length, fp = rows.filter(s => s.gold !== l && s.label === l).length, fn = rows.filter(s => s.gold === l && s.label !== l).length; return 2 * tp + fp + fn ? 2 * tp / (2 * tp + fp + fn) : 0; }));
}));
/* Fit verdict: the plain answer to "can I use this model for this task?" */
export function verdict(m) { if (!m || m.accuracy == null || !m.questions) return {k: 'na', t: m?.excluded ? 'Not evaluated' : 'Not run'}; const [lo] = m.wilson; if (m.accuracy >= .9 && lo >= .85) return {k: 'ok', t: 'Fits'}; if (m.accuracy >= .8) return {k: 'risk', t: 'Risky'}; return {k: 'no', t: 'Not fit'}; }
export const rankOf = (m, ms) => { const hi = m.wilson?.[1] ?? m.accuracy; return 1 + ms.filter(o => o !== m && (o.wilson?.[0] ?? o.accuracy) > hi).length; };
export function bestOn(t) { const rows = taskRows(t); return RUNS.map(r => [r, subsetMetrics(r, rows)]).filter(([, m]) => m.questions).sort(([, a], [, b]) => b.accuracy - a.accuracy)[0] || null; }
export const evaluated = (rs, cases) => rs.filter(r => subsetMetrics(r, cases).questions > 0);

/* ---------- Per-row statistics across evaluated models ---------- */
export function caseStats(c) {
  if (statCache.has(c.id)) return statCache.get(c.id);
  let n = 0, ok = 0; const wrong = {}, picks = {}, dots = [];
  for (const r of RUNS) {
    const v = result(r.id, c.id); if (!v) continue; n++;
    const good = okOf(v), l = v.scores[0]?.label ?? null; picks[l] = (picks[l] || 0) + 1;
    if (good) ok++; else wrong[l] = (wrong[l] || 0) + 1;
    dots.push({k: keyOf(r), ok: good});
  }
  const st = {n, ok, wrong, picks, dots}; statCache.set(c.id, st); return st;
}

export function init(json, datasetsDoc) {
  data = json; MODELS = {}; ORDER = [];
  for (const m of data.models || []) registerModel(m, true);
  for (const r of data.runs || []) registerModel({...(r.model || {}), id: keyOf(r)}, false);
  /* Two evaluated models sharing a short label (e.g. two OpenAI releases both 'Luna API') fall back to their full names. */
  const seen = {}; for (const k of new Set((data.runs || []).map(keyOf))) { const m = MODELS[k]; if (m) (seen[m.short] ||= []).push(m); }
  for (const g of Object.values(seen)) if (g.length > 1) for (const m of g) m.short = m.name;
  allCases = data.cases || []; caseMap = new Map(allCases.map(c => [c.id, c]));
  rowsByTask = new Map(); for (const c of allCases) { if (!rowsByTask.has(c.task)) rowsByTask.set(c.task, []); rowsByTask.get(c.task).push(c); }
  recordMap = new Map((data.results || []).map(r => [`${r.run_id}:${r.case_id}`, r]));
  statCache.clear(); metricCache.clear();
  const cats = man().categories ? Object.keys(man().categories) : [];
  for (const c of allCases) if (!cats.includes(catKey(c))) cats.push(catKey(c));
  CAT_ORDER = cats.filter(k => allCases.some(c => catKey(c) === k));
  const tk = man().tasks ? Object.keys(man().tasks) : [];
  for (const c of allCases) if (!tk.includes(c.task)) tk.push(c.task);
  TASK_ORDER = tk.filter(t => rowsByTask.has(t)).sort((a, b) => CAT_ORDER.indexOf(taskCat(a)) - CAT_ORDER.indexOf(taskCat(b)) || tk.indexOf(a) - tk.indexOf(b));
  collectRuns(); indexDatasets(datasetsDoc);
  /* Stable model order everywhere: overall accuracy, then configured-only models. */
  const acc = new Map(RUNS.map(r => [keyOf(r), subsetMetrics(r, allCases).accuracy]));
  ORDER.sort((a, b) => (acc.get(b) ?? -1) - (acc.get(a) ?? -1));
  RUNS.sort(byOrder);
}

/* Load a row once, sharing concurrent requests. Mutate indexed objects so existing
   references (task lists, datasets, and review navigation) retain their identity. */
const detailRequests = new Map();
export function loadCaseDetail(c) {
  if (!c?.detail_url || Object.hasOwn(c, 'state')) return Promise.resolve();
  if (detailRequests.has(c.id)) return detailRequests.get(c.id);
  const request = (async () => {
    if (!/^details\/[a-f0-9]{64}\.json$/.test(c.detail_url)) throw Error('Invalid detail reference');
    const res = await fetch(c.detail_url, {signal: AbortSignal.timeout(30000)});
    if (!res.ok) throw Error('Row unavailable');
    const detail = await res.json();
    if (detail.corpus_sha256 !== data.corpus_sha256 || detail.case?.id !== c.id || !Array.isArray(detail.results)) throw Error('Row version mismatch');
    if (detail.results.some(r => r.case_id !== c.id || !rawResult(r.run_id, c.id))) throw Error('Row results mismatch');
    for (const r of detail.results) Object.assign(rawResult(r.run_id, c.id), r);
    Object.assign(c, detail.case);
  })().finally(() => detailRequests.delete(c.id));
  detailRequests.set(c.id, request);
  return request;
}
