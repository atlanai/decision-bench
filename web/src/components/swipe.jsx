/* A page you can swipe like a card in a deck. Drag it sideways with a finger: it follows, tilts around a point
   below the screen, and a stamp says what letting go will do. Past about a third of the screen, or on a quick
   flick, it flies off and the next card rises from the deck; short of that it springs back. Vertical scrolling,
   sideways scrolling inside code and tables, and the browser's own edge swipe are left alone.
   left / right: what a swipe that way does, as {label, tone, run, stay, off, onOff}. run() returns false when there
   was nowhere to go; stay keeps the card (it springs back after run); off refuses with a rubber band and onOff(). */
import {useEffect, useRef, useState} from 'react';
import {HandIcon} from 'lucide-react';
import {cn} from '@/lib/utils';
import {haptic, matches, once, reducedMotion} from '@/lib/device';
import {navHint} from '@/lib/route';

/* How the next card should arrive, set by the card that just left. */
const deck = {enter: ''};

function scrollsX(el, root) {
  for (let n = el; n && n !== root; n = n.parentElement) {
    if (n.scrollWidth > n.clientWidth + 1) { const o = getComputedStyle(n).overflowX; if (o === 'auto' || o === 'scroll') return true; }
  }
  return false;
}
const TONE = {good: 'border-good text-good', warn: 'border-warn text-warn', ink: 'border-foreground/80 text-foreground'};
const Stamp = ({ref, act, side}) => act ? (
  <div ref={ref} aria-hidden="true" className={cn('pointer-events-none fixed top-[26%] z-50 rounded-lg border-[3px] bg-background/85 px-3 pt-2 pb-1.5 font-pixel text-[22px] leading-none tracking-wide uppercase opacity-0 shadow-sm backdrop-blur-sm', side === 'left' ? 'left-5' : 'right-5', TONE[act.tone || 'ink'])}
    style={{transform: `rotate(${side === 'left' ? -14 : 14}deg)`}}>{act.label}</div>
) : null;
/* What waits under the card: shown as the card moves off it. */
const Peek = ({ref, act}) => act?.peek ? <div ref={ref} aria-hidden="true" className="pointer-events-none fixed inset-x-4 top-[34%] z-0 mx-auto max-w-md opacity-0">{act.peek}</div> : null;

export function Swipe({left, right, hint, hintKey = 'swipe', className, children}) {
  const card = useRef(null), stampL = useRef(null), stampR = useRef(null), peekL = useRef(null), peekR = useRef(null);
  const acts = useRef({left, right}); acts.current = {left, right};
  const [enter] = useState(() => deck.enter), [coach, setCoach] = useState(false);
  useEffect(() => { deck.enter = ''; }, []);

  useEffect(() => {
    if (!hint || once.has(hintKey) || !matches('(pointer: coarse)')) return;
    const a = setTimeout(() => setCoach(true), 900), b = setTimeout(() => setCoach(false), 8000);
    return () => { clearTimeout(a); clearTimeout(b); };
  }, [hint, hintKey]);

  useEffect(() => {
    const el = card.current; if (!el) return;
    const calm = reducedMotion();
    let s = null;
    const paint = dx => {
      el.style.transform = dx ? `translateX(${dx}px) rotate(${calm ? 0 : dx / 32}deg)` : '';
      const p = Math.min(1, Math.abs(dx) / 110);
      for (const [r, on, deg] of [[stampR, dx > 0, -14], [stampL, dx < 0, 14]]) if (r.current) { r.current.style.opacity = on ? p : 0; r.current.style.transform = `rotate(${deg}deg) scale(${.7 + .3 * (on ? p : 0)})`; }
      for (const [r, on] of [[peekR, dx > 0], [peekL, dx < 0]]) if (r.current) { const q = on ? Math.min(1, Math.abs(dx) / 220) : 0; r.current.style.opacity = q; r.current.style.transform = `scale(${.9 + .1 * q})`; }
    };
    const settle = () => {
      el.style.transition = calm ? 'transform .2s ease' : 'transform .5s cubic-bezier(.3,1.45,.45,1)';
      for (const r of [stampL, stampR, peekL, peekR]) if (r.current) r.current.style.transition = 'opacity .25s ease, transform .25s ease';
      paint(0);
      setTimeout(() => { for (const r of [stampL, stampR, peekL, peekR]) if (r.current) r.current.style.transition = ''; }, 300);
    };
    const commit = (a, dir) => {
      haptic(12); once.mark(hintKey); setCoach(false);
      if (a.stay) { settle(); a.run(); return; }
      el.style.transition = 'transform .28s cubic-bezier(.4,0,.9,.55)';
      el.style.transform = `translateX(${dir * innerWidth * 1.15}px) rotate(${calm ? 0 : dir * 16}deg)`;
      setTimeout(() => {
        deck.enter = dir < 0 ? 'rise' : 'return'; navHint('skip');
        if (a.run() === false) { deck.enter = ''; navHint(null); settle(); }
      }, 220);
    };
    const down = e => {
      if (e.pointerType === 'mouse' || !e.isPrimary || s) return;
      if (e.clientX < 24 || e.clientX > innerWidth - 24) return;
      if (e.target.closest('input,textarea,select,[contenteditable],[data-no-swipe]') || scrollsX(e.target, el)) return;
      s = {id: e.pointerId, x: e.clientX, y: e.clientY, lock: false, dx: 0, v: 0, lx: e.clientX, lt: performance.now()};
    };
    const move = e => {
      if (!s || e.pointerId !== s.id) return;
      const dx = e.clientX - s.x, dy = e.clientY - s.y;
      if (!s.lock) {
        if (Math.hypot(dx, dy) < 10) return;
        if (Math.abs(dx) < Math.abs(dy) * 1.3) { s = null; return; }
        s.lock = true; try { el.setPointerCapture(e.pointerId); } catch {}
        el.style.transition = 'none'; el.style.transformOrigin = `50% ${Math.round(innerHeight * 1.15 - el.getBoundingClientRect().top)}px`; el.dataset.dragging = '';
        for (const r of [stampL, stampR, peekL, peekR]) if (r.current) r.current.style.transition = '';
      }
      const now = performance.now(); s.v = (e.clientX - s.lx) / Math.max(1, now - s.lt); s.lx = e.clientX; s.lt = now;
      const a = dx < 0 ? acts.current.left : acts.current.right;
      s.dx = a && !a.off ? dx : Math.sign(dx) * Math.min(64, Math.abs(dx) * .28);
      paint(s.dx);
    };
    const up = e => {
      if (!s || e.pointerId !== s.id) return;
      const {lock, dx, v} = s; s = null; if (!lock) return;
      delete el.dataset.dragging;
      /* A drag that started on a link or button is not a tap. */
      const stop = ev => { ev.preventDefault(); ev.stopPropagation(); };
      el.addEventListener('click', stop, {capture: true, once: true}); setTimeout(() => el.removeEventListener('click', stop, {capture: true}), 0);
      const a = dx < 0 ? acts.current.left : acts.current.right;
      const far = Math.abs(dx) > Math.min(140, innerWidth * .3) || (Math.abs(dx) > 40 && Math.abs(v) > .5 && Math.sign(v) === Math.sign(dx));
      if (a && !a.off && far) commit(a, Math.sign(dx));
      else { if (a?.off && Math.abs(dx) > 40) { haptic(4); a.onOff?.(); } settle(); }
    };
    el.addEventListener('pointerdown', down); el.addEventListener('pointermove', move); el.addEventListener('pointerup', up); el.addEventListener('pointercancel', up);
    return () => { el.removeEventListener('pointerdown', down); el.removeEventListener('pointermove', move); el.removeEventListener('pointerup', up); el.removeEventListener('pointercancel', up); };
  }, [hintKey]);

  return <>
    <Peek ref={peekL} act={left} /><Peek ref={peekR} act={right} />
    <div ref={card} className={cn('relative z-10 -mx-4 bg-background [touch-action:pan-y_pinch-zoom] px-4 [transform-origin:50%_110vh] md:-mx-8 md:px-8 data-[dragging]:rounded-3xl data-[dragging]:shadow-[0_20px_60px_-20px_rgb(0_0_0/.35)] data-[dragging]:ring-1 data-[dragging]:ring-border', enter === 'rise' && 'motion-safe:animate-deck-rise', enter === 'return' && 'motion-safe:animate-deck-return', className)}>
      {children}
    </div>
    <Stamp ref={stampR} act={right} side="left" /><Stamp ref={stampL} act={left} side="right" />
    {coach && <div className="pointer-events-none fixed inset-x-0 bottom-[calc(env(safe-area-inset-bottom)+92px)] z-40 flex justify-center px-4 lg:bottom-8">
      <button type="button" onClick={() => { once.mark(hintKey); setCoach(false); }} className="pointer-events-auto flex cursor-pointer items-center gap-3 rounded-full border bg-background/90 py-1.5 pr-4 pl-1.5 text-[13px] shadow-lg backdrop-blur-md motion-safe:animate-toast-in">
        <span className="grid size-8 place-items-center rounded-full bg-muted"><HandIcon className="size-4 motion-safe:animate-hint-hand" /></span>{hint}
      </button>
    </div>}
  </>;
}
