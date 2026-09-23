/* Hash routing: every view has a shareable URL. #/, #/tasks, #/task/<id>, #/row/<id>, #/models, #/model/<id>,
   #/compare, #/data, #/data/<dataset>, #/methodology, #/methodology/<section>, #/review/<row>.
   Filters live in the query string after the path. */
import {startTransition, useEffect, useState} from 'react';

export const PAGES = ['tasks', 'task', 'row', 'models', 'model', 'compare', 'data', 'methodology', 'review'];

/* Old links: #overview, #tasks?…, #task/<id>, #review/<id>, #data/<id>, #about */
function upgradeLegacy(h) {
  if (h.startsWith('/')) return h;
  const [p, qs] = h.split('?');
  const map = {'': '/', overview: '/', tasks: '/tasks', compare: '/compare', failures: '/', review: '/review', data: '/data', about: '/methodology', reports: '/methodology'};
  let np = map[p.split('/')[0]];
  if (p.startsWith('task/')) np = `/row/${p.slice(5)}`;
  else if (p.startsWith('review/')) np = `/review/${p.slice(7)}`;
  else if (p.startsWith('data/')) np = `/data/${p.slice(5)}`;
  const out = (np || '/') + (qs ? `?${qs}` : '');
  history.replaceState(null, '', `#${out}`);
  return out;
}

export function parseRoute() {
  const h = upgradeLegacy(location.hash.replace(/^#/, ''));
  const [path, qs] = h.slice(1).split('?');
  const parts = path.split('/').filter(Boolean);
  const q = new URLSearchParams(qs || '');
  if (!['text', 'image'].includes(q.get('modality'))) q.delete('modality');
  let id = '';
  try { id = decodeURIComponent(parts.slice(1).join('/') || ''); } catch { id = parts.slice(1).join('/'); }
  return {page: PAGES.includes(parts[0]) ? parts[0] : 'home', id, q};
}

export function useRoute() {
  const [route, setRoute] = useState(parseRoute);
  useEffect(() => {
    /* A transition, so the click that changed the URL (a menu closing, a tick) paints before the page re-renders. */
    const on = () => { const r = parseRoute(); startTransition(() => setRoute(r)); };
    addEventListener('hashchange', on);
    return () => removeEventListener('hashchange', on);
  }, []);
  return route;
}

export const href = (path, params = {}) => {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== '' && v != null) q.set(k, v);
  const s = q.toString();
  return `#/${path}${s ? `?${s}` : ''}`;
};
/* The current URL with some query parameters changed. */
export const withQ = (route, patch) => {
  const q = new URLSearchParams(route.q);
  for (const [k, v] of Object.entries(patch)) { if (v === '' || v == null) q.delete(k); else q.set(k, v); }
  const s = q.toString();
  return `#/${[route.page === 'home' ? '' : route.page, route.id].filter(Boolean).map(encodeURIComponent).join('/')}${s ? `?${s}` : ''}`;
};
export const go = hash => { if (location.hash !== hash) location.hash = hash; };
/* Change the URL without a new history entry (typing in a search box). */
export const replace = hash => { history.replaceState(null, '', hash); dispatchEvent(new HashChangeEvent('hashchange')); };

export const taskHref = t => href(`task/${encodeURIComponent(t)}`);
export const rowHref = c => href(`row/${encodeURIComponent(c.id)}`);
export const modelHref = k => href(`model/${encodeURIComponent(k)}`);
export const catHref = k => href('', {category: k});
export const dataHref = id => href(`data/${encodeURIComponent(id)}`);
