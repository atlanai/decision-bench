/* Path routing: every view has a shareable URL. Existing #/ links are upgraded on load. */
import {startTransition, useEffect, useState} from 'react';
import {flushSync} from 'react-dom';
import {COMPACT, matches, reducedMotion} from '@/lib/device';

export const PAGES = ['tasks', 'task', 'row', 'models', 'model', 'compare', 'data', 'methodology', 'review'];

/* Preserve old shared links without leaving the fragment in the address bar. */
function upgradeLegacyHash() {
  const h = location.hash.slice(1);
  if (!h || h === 'main' || h === 'hot-turn') return;
  const [rawPath, rawQuery = ''] = h.split('?');
  const old = {overview: '', tasks: 'tasks', compare: 'compare', failures: '', review: 'review', data: 'data', about: 'methodology', reports: 'methodology'};
  let path = rawPath;
  if (!path.startsWith('/')) {
    const [first, ...rest] = path.split('/');
    path = '/' + (first === 'task' ? 'row' : old[first] ?? first) + (rest.length ? '/' + rest.join('/') : '');
  }
  const [page, ...parts] = path.slice(1).split('/');
  if (page && !PAGES.includes(page)) return;
  let id = '';
  try { id = decodeURIComponent(parts.join('/')); } catch { return; }
  const q = new URLSearchParams(rawQuery).toString();
  const next = '/' + (page || '') + (id ? '/' + encodeURIComponent(id) : '') + (q ? '?' + q : '');
  history.replaceState(history.state, '', next);
}
upgradeLegacyHash();

export function parseRoute() {
  const parts = location.pathname.split('/').filter(Boolean);
  const q = new URLSearchParams(location.search);
  if (!['text', 'image'].includes(q.get('modality'))) q.delete('modality');
  let id = '';
  try { id = decodeURIComponent(parts.slice(1).join('/') || ''); } catch { id = parts.slice(1).join('/'); }
  return {page: PAGES.includes(parts[0]) ? parts[0] : 'home', id, q};
}

/* How a navigation should look on a phone or tablet. Each history entry carries its position (dbi), so going back
   is told apart from going somewhere new. Deeper pages push in from the right, shallower ones pop back, tabs fade,
   and stepping between rows deals the next card. '' means no page transition (a filter, a sheet, an anchor). */
const DEPTH = {home: 0, tasks: 0, models: 0, data: 0, methodology: 0, task: 1, model: 1, compare: 1, review: 1, row: 2};
let pos = history.state?.dbi ?? 0, hint = null;
if (history.state?.dbi == null) history.replaceState({...history.state, dbi: 0}, '');
/* The page itself animated this change (a swiped card): 'skip'. Or say which way: 'next', 'prev'. A soft hint
   gives way to one already set. */
export const navHint = (k, soft = false) => { if (!soft || hint == null) hint = k; };
export const historyPos = () => pos;
function kindOf(a, b, back) {
  if (a.page === b.page && (a.id === b.id || a.page === 'data' || a.page === 'methodology')) return '';
  if (a.page === b.page && (a.page === 'row' || a.page === 'review')) return back ? 'prev' : 'next';
  if (back) return 'pop';
  const da = DEPTH[a.page] ?? 0, db = DEPTH[b.page] ?? 0;
  return db > da ? 'push' : db < da ? 'pop' : 'tab';
}
/* iOS and Android draw their own animation for an edge swipe back; don't play a second one on top. */
let edge = null, edgeAt = 0;
if (typeof addEventListener === 'function') {
  addEventListener('touchstart', e => { const x = e.touches[0]?.clientX ?? 99; edge = x < 20 || x > innerWidth - 20 ? x : null; }, {passive: true, capture: true});
  addEventListener('touchmove', e => { if (edge != null && Math.abs((e.touches[0]?.clientX ?? edge) - edge) > 10) edgeAt = performance.now(); }, {passive: true, capture: true});
  addEventListener('touchcancel', () => { if (edge != null) edgeAt = performance.now(); }, {passive: true, capture: true});
}
const canAnimate = () => !!document.startViewTransition && matches(COMPACT) && !reducedMotion() && performance.now() - edgeAt > 1200 && !document.hidden;

export function useRoute() {
  const [route, setRoute] = useState(parseRoute);
  useEffect(() => {
    let last = parseRoute();
    const on = () => {
      const r = parseRoute(), i = history.state?.dbi;
      let back = false;
      if (i == null) { pos += 1; history.replaceState({...history.state, dbi: pos}, ''); } else { back = i < pos; pos = i; }
      const k = hint ?? kindOf(last, r, back); hint = null; last = r;
      /* A transition, so the click that changed the URL (a menu closing, a tick) paints before the page re-renders. */
      if (!k || k === 'skip' || !canAnimate()) { startTransition(() => setRoute(r)); return; }
      const root = document.documentElement; root.dataset.nav = k;
      const t = document.startViewTransition(() => flushSync(() => setRoute(r)));
      t.finished.finally(() => { if (root.dataset.nav === k) delete root.dataset.nav; });
    };
    addEventListener('popstate', on);
    addEventListener('db:navigate', on);
    const click = e => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = e.target.closest?.('a[href]');
      if (!a || a.hasAttribute('download') || (a.target && a.target !== '_self')) return;
      if (a.getAttribute('href')?.startsWith('#')) return;
      let url; try { url = new URL(a.href, location.href); } catch { return; }
      if (url.origin !== location.origin || url.hash) return;
      const first = url.pathname.split('/').filter(Boolean)[0];
      if (first && !PAGES.includes(first)) return;
      e.preventDefault(); go(url.pathname + url.search);
    };
    document.addEventListener('click', click);
    return () => { removeEventListener('popstate', on); removeEventListener('db:navigate', on); document.removeEventListener('click', click); };
  }, []);
  return route;
}

export const href = (path, params = {}) => {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== '' && v != null) q.set(k, v);
  const s = q.toString();
  return `/${path}${s ? `?${s}` : ''}`;
};
/* The current URL with some query parameters changed. */
export const withQ = (route, patch) => {
  const q = new URLSearchParams(route.q);
  for (const [k, v] of Object.entries(patch)) { if (v === '' || v == null) q.delete(k); else q.set(k, v); }
  const s = q.toString();
  return `/${[route.page === 'home' ? '' : route.page, route.id].filter(Boolean).map(encodeURIComponent).join('/')}${s ? `?${s}` : ''}`;
};
export const go = path => {
  if (location.pathname + location.search === path) return;
  history.pushState({...history.state, dbi: pos + 1}, '', path);
  dispatchEvent(new Event('db:navigate'));
};
/* Change the URL without a new history entry (typing in a search box). */
export const replace = path => { history.replaceState({...history.state, dbi: pos}, '', path); dispatchEvent(new Event('db:navigate')); };

export const taskHref = t => href(`task/${encodeURIComponent(t)}`);
export const rowHref = c => href(`row/${encodeURIComponent(c.id)}`);
export const modelHref = k => href(`model/${encodeURIComponent(k)}`);
export const catHref = k => href('', {category: k});
export const dataHref = id => href(`data/${encodeURIComponent(id)}`);
