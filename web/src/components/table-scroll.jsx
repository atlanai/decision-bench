import {useEffect, useRef, useState} from 'react';
import {ChevronLeftIcon, ChevronRightIcon} from 'lucide-react';

/* Keep a scroll control near the headers: native macOS scrollbars disappear,
   and a wide table's bottom scrollbar can be below the fold. */
export function TableScroll({children, label = 'Results table'}) {
  const viewport = useRef(null), [position, setPosition] = useState({left: 0, max: 0});
  useEffect(() => {
    const el = viewport.current;
    const measure = () => {
      const max = Math.max(0, el.scrollWidth - el.clientWidth), left = Math.min(max, Math.max(0, el.scrollLeft));
      setPosition(p => p.left === left && p.max === max ? p : {left, max});
    };
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    if (el.firstElementChild) observer.observe(el.firstElementChild);
    el.addEventListener('scroll', measure, {passive: true});
    measure();
    return () => { observer.disconnect(); el.removeEventListener('scroll', measure); };
  }, []);
  const move = dir => {
    const el = viewport.current;
    el.scrollBy({left: dir * Math.max(160, el.clientWidth * .6), behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
  };
  const {left, max} = position, overflow = max > 1;
  return <div className="min-w-0">
    {overflow && <div className="flex items-center gap-2 border-b bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
      <span className="shrink-0">Scroll columns</span>
      <button type="button" aria-label={`Scroll ${label} left`} disabled={left <= 1} onClick={() => move(-1)} className="grid size-7 shrink-0 place-items-center rounded hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring disabled:opacity-30"><ChevronLeftIcon className="size-4" /></button>
      <input type="range" min="0" max="100" step="any" value={left / max * 100} aria-label={`${label} horizontal position`} aria-valuetext={`${Math.round(left / max * 100)}% across the table`} onChange={e => { viewport.current.scrollLeft = Number(e.target.value) / 100 * max; }} className="h-4 min-w-12 flex-1 cursor-pointer accent-brand" />
      <button type="button" aria-label={`Scroll ${label} right`} disabled={left >= max - 1} onClick={() => move(1)} className="grid size-7 shrink-0 place-items-center rounded hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring disabled:opacity-30"><ChevronRightIcon className="size-4" /></button>
    </div>}
    <div ref={viewport} role="region" aria-label={label} tabIndex={overflow ? 0 : -1} className="w-full min-w-0 overflow-x-auto focus-visible:outline-2 focus-visible:outline-ring">{children}</div>
  </div>;
}
