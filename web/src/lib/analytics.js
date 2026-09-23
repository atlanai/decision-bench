import * as B from './bench.js';

const pages = ['home', 'tasks', 'task', 'row', 'models', 'model', 'compare', 'data', 'methodology', 'review'];
const sections = ['what', 'rows', 'sees', 'metrics', 'verdict', 'limits', 'submit'];
let current, previousFilters;

// Only public catalog identifiers enter payloads. Never copy URL queries, titles or DOM text.
export function context(route) {
  const page = pages.includes(route.page) ? route.page : 'home';
  const out = {page_type: page, benchmark_version: B.man().version || 'unknown'};
  let id = '';
  const row = ['row', 'review'].includes(page) && B.caseMap.get(route.id);
  if (row) { id = row.id; out.row_id = row.id; out.task_id = row.task; out.category = row.category; const ds = B.dsOf(row); if (ds) out.dataset_id = ds.id; }
  if (page === 'task' && B.taskOrder().includes(route.id)) { id = route.id; out.task_id = id; out.category = B.taskCat(id); }
  if (page === 'model' && Object.hasOwn(B.MODELS, route.id)) { id = route.id; out.model_id = id; }
  if (page === 'data' && B.DATASETS.some(d => d.id === route.id)) { id = route.id; out.dataset_id = id; }
  if (page === 'methodology' && sections.includes(route.id)) { id = route.id; out.section = id; }
  out.page_path = '/#/' + (page === 'home' ? '' : page) + (id ? '/' + encodeURIComponent(id) : '');
  out.page_location = location.origin + out.page_path;
  out.page_title = `${page} · Decision Bench`;
  return out;
}
function filters(route) {
  const q = route.q, out = {};
  if (B.categoryOrder().includes(q.get('category'))) out.filter_category = q.get('category');
  if (['text', 'image'].includes(q.get('modality'))) out.filter_modality = q.get('modality');
  for (const k of ['a', 'b']) if (Object.hasOwn(B.MODELS, q.get(k))) out[`model_${k}`] = q.get(k);
  if (q.has('models')) out.selected_model_count = (q.get('models') || '').split(',').filter(k => Object.hasOwn(B.MODELS, k)).length;
  out.search_active = !!q.get('q');
  return out;
}
export function track(name, params = {}) { window.dbAnalytics?.event(name, params); }
export function pageView(route) {
  const next = context(route), f = filters(route);
  const changed = current?.page_path !== next.page_path;
  window.dbAnalytics?.page({...next, ...f});
  if (!changed && previousFilters !== JSON.stringify(f)) track(route.page === 'compare' ? 'comparison_change' : 'filter_change', f);
  current = next; previousFilters = JSON.stringify(f);
}

export function installClicks() {
  const onClick = event => {
    const el = event.target.closest?.('[data-track], a[href], tr');
    if (!el || el.closest('[data-analytics-preferences], [data-analytics-choice]') || el.closest('[disabled], [aria-disabled="true"]')) return;
    const area = el.closest('header') ? 'header' : el.closest('footer') ? 'footer' : 'content';
    if (el.dataset.track) {
      track('ui_click', {control: el.dataset.track, area, ...(el.getAttribute('aria-expanded') != null ? {expanded: el.getAttribute('aria-expanded') !== 'true'} : {})});
      return;
    }
    const link = el.matches('a') ? el : el.querySelector('a[href]');
    if (!link) return;
    let url; try { url = new URL(link.href, location.href); } catch { return; }
    if (!['http:', 'https:'].includes(url.protocol)) return;
    if (url.origin === location.origin && url.hash.startsWith('#/')) {
      const [path, query] = url.hash.slice(2).split('?');
      const [page, ...parts] = path.split('/');
      let id; try { id = decodeURIComponent(parts.join('/')); } catch { return; }
      const route = {page: page || 'home', id, q: new URLSearchParams(query)};
      const dest = context(route);
      track('navigation_click', {destination_page: dest.page_type, destination_path: dest.page_path, area, ...filters(route)});
    } else if (link.hasAttribute('download')) {
      // Fixed public asset names only; never export filenames containing user data.
      const file = url.pathname.split('/').pop();
      track('file_download', {file_name: ['corpus.json', 'datasets.json', 'data.json', 'predictions.jsonl', 'protocol.txt', 'CITATION.cff'].includes(file) ? file : 'benchmark_file', area});
    } else if (url.origin !== location.origin) {
      track('outbound_click', {link_domain: url.hostname, area});
    } else if (url.pathname.endsWith('/privacy.html')) track('navigation_click', {destination_page: 'privacy', area});
  };
  document.addEventListener('click', onClick, true);
  return () => document.removeEventListener('click', onClick, true);
}
