/* Screen size and touch helpers for the app shell. Phone: below md, where lists replace tables. Compact: below
   lg, where the tab bar, the compact top bar and page transitions take over from the desktop header. */
import {useSyncExternalStore} from 'react';

export const PHONE = '(max-width: 767px)', COMPACT = '(max-width: 1023px)';
export const matches = q => typeof matchMedia === 'function' && matchMedia(q).matches;
export const reducedMotion = () => matches('(prefers-reduced-motion: reduce)');

export function useMedia(q) {
  return useSyncExternalStore(
    on => { const mq = matchMedia(q); mq.addEventListener('change', on); return () => mq.removeEventListener('change', on); },
    () => matchMedia(q).matches,
    () => false,
  );
}
export const usePhone = () => useMedia(PHONE);
export const useCompact = () => useMedia(COMPACT);

/* A light tap on phones that support it (Android); a no-op elsewhere. */
export const haptic = (ms = 8) => { try { navigator.vibrate?.(ms); } catch {} };

/* One-time hints: remembered in this browser if storage works, else for this page load only. */
const seen = new Set();
export const once = {
  has: k => { if (seen.has(k)) return true; try { return localStorage.getItem(`db-once:${k}`) === '1'; } catch { return false; } },
  mark: k => { seen.add(k); try { localStorage.setItem(`db-once:${k}`, '1'); } catch {} },
};
