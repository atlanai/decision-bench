/* One floating tooltip for charts, heatmaps and dense tables, where a Radix tooltip per cell would be too heavy.
   Elements carry data-tip='{"t":"title","r":[["label","value"]]}' (see tip()); this reads it on hover or focus. */
import {useEffect, useRef, useState} from 'react';

export const tip = (t, r = []) => JSON.stringify({t, r});

export function ChartTip() {
  const box = useRef(null), [body, setBody] = useState(null);
  useEffect(() => {
    let cur = null;
    const place = (x, y) => {
      const el = box.current; if (!el) return;
      const b = el.getBoundingClientRect(); let l = x + 14, t = y + 14;
      if (l + b.width > innerWidth - 8) l = x - b.width - 14;
      if (t + b.height > innerHeight - 8) t = y - b.height - 14;
      el.style.left = `${Math.max(8, l)}px`; el.style.top = `${Math.max(8, t)}px`;
    };
    const show = (el, x, y) => { if (el !== cur) { cur = el; try { setBody(JSON.parse(el.getAttribute('data-tip'))); } catch { setBody(null); } } requestAnimationFrame(() => place(x, y)); };
    const hide = () => { cur = null; setBody(null); };
    const over = e => { const el = e.target.closest?.('[data-tip]'); if (el) show(el, e.clientX, e.clientY); };
    const move = e => { if (cur && e.target.closest?.('[data-tip]') === cur) place(e.clientX, e.clientY); };
    const out = e => { const el = e.target.closest?.('[data-tip]'); if (el && !el.contains(e.relatedTarget)) hide(); };
    const focus = e => { const el = e.target.closest?.('[data-tip]'); if (el) { const b = el.getBoundingClientRect(); show(el, b.right, b.bottom); } };
    document.addEventListener('pointerover', over); document.addEventListener('pointermove', move); document.addEventListener('pointerout', out);
    document.addEventListener('focusin', focus); document.addEventListener('focusout', hide); addEventListener('scroll', hide, {passive: true}); addEventListener('hashchange', hide);
    return () => { document.removeEventListener('pointerover', over); document.removeEventListener('pointermove', move); document.removeEventListener('pointerout', out); document.removeEventListener('focusin', focus); document.removeEventListener('focusout', hide); removeEventListener('scroll', hide); removeEventListener('hashchange', hide); };
  }, []);
  return (
    <div ref={box} role="tooltip" hidden={!body} className="pointer-events-none fixed z-[60] max-w-xs rounded-md bg-foreground px-3 py-2 text-xs leading-relaxed text-background shadow-lg">
      {body && <>
        <div className="mb-1 font-semibold">{body.t}</div>
        {body.r.map(([k, v], i) => <div key={i} className="flex justify-between gap-4"><span className="opacity-70">{k}</span><span className="tabular-nums">{v}</span></div>)}
      </>}
    </div>
  );
}
