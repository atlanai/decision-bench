/* SVG charts drawn at the container's measured width. Hover and focus details come from data-tip (see tip.jsx). */
import {useEffect, useLayoutEffect, useRef, useState} from 'react';
import {M, result, okOf, answered, caseTitle, taskName, goldText, ident, runName, runColor, keyOf, subsetMetrics, catKey, catInfo, answerOf} from '@/lib/bench';
import {pct, pct0, clip} from '@/lib/format';
import {rowHref} from '@/lib/route';
import {tip, showTip, moveTip, hideTip} from '@/components/tip';
import {cn} from '@/lib/utils';

const SVG_CLS = 'block overflow-visible font-sans text-[12px] [&_text]:fill-muted-foreground [&_.t-ink]:fill-foreground/80 [&_.t-value]:fill-foreground [&_.t-value]:tabular-nums [&_.grid]:stroke-border [&_.minor]:opacity-50 [&_.axis]:stroke-foreground/20 [&_.ref]:stroke-muted-foreground/60 [&_.ref]:[stroke-dasharray:3_3] [&_.hit]:fill-transparent [&_.whisker]:fill-none [&_.whisker]:stroke-foreground/70 [&_.ghost]:fill-none [&_.ghost]:stroke-foreground/15 [&_g[data-tip]:hover_.hit]:fill-foreground/5';

export function useWidth(min = 220) {
  const ref = useRef(null), [w, setW] = useState(0);
  useLayoutEffect(() => {
    const el = ref.current; if (!el) return;
    const measure = () => setW(Math.max(min, Math.floor(el.clientWidth)));
    measure();
    const ro = new ResizeObserver(measure); ro.observe(el);
    return () => ro.disconnect();
  }, [min]);
  return [ref, w];
}
export function Chart({label, className, children}) {
  const [ref, w] = useWidth();
  return <div ref={ref} role="img" aria-label={label} className={cn('w-full min-w-0', className)}>{w > 0 && children(w)}</div>;
}
const Hatch = () => <defs><pattern id="hatch" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="4" height="4" fill="var(--background)" /><line x1="0" y1="0" x2="0" y2="4" stroke="var(--bad)" strokeWidth="1.5" /></pattern></defs>;
const Svg = ({w, h, children}) => <svg viewBox={`0 0 ${w} ${h}`} width={w} height={h} aria-hidden="true" className={SVG_CLS}><Hatch />{children}</svg>;

const lin = (d0, d1, r0, r1) => v => r0 + (v - d0) / (d1 - d0 || 1) * (r1 - r0);
const logS = (d0, d1, r0, r1) => v => r0 + (Math.log10(v) - Math.log10(d0)) / (Math.log10(d1) - Math.log10(d0) || 1) * (r1 - r0);
function niceStep(range, count) { const raw = range / count || 1, mag = 10 ** Math.floor(Math.log10(raw)), n = raw / mag; return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * mag; }
export function niceTicks(lo, hi, count = 4) { const st = niceStep(hi - lo, count), a = Math.floor(lo / st + 1e-9) * st, out = []; for (let v = a; v <= hi + st * .999; v += st) out.push(+v.toFixed(10)); return out; }
function logDomain(vals) { const pos = vals.filter(v => v > 0); if (!pos.length) return [.1, 1]; const lo = 10 ** Math.floor(Math.log10(Math.min(...pos))), hi = 10 ** Math.ceil(Math.log10(Math.max(...pos))); return [lo, hi === lo ? hi * 10 : hi]; }
function logTicks([lo, hi]) { const out = []; for (let d = lo; d <= hi * 1.0001; d *= 10) for (const m of [1, 2, 5]) if (d * m <= hi * 1.0001) out.push({v: d * m, major: m === 1}); return out; }
export function zoomDomain(vals, step = .05) { const lo = Math.max(0, Math.floor((Math.min(...vals) - .02) / step) * step); return [+lo.toFixed(4), 1]; }
const Label = ({k, x, cy, maxW}) => <><circle cx={x + 4} cy={cy} r="3.5" fill={M(k).color} /><text className="t-ink" x={x + 13} y={cy + 4}>{clip(M(k).short, Math.floor((maxW - 13) / 6.4))}</text></>;

/* Horizontal bars, one row per model. items: {key,value,lo?,hi?,tick?,color,tip,ghost?} */
export function RowsChart({items, fmt, tickFmt = fmt, max, min = 0, label}) {
  return <Chart label={label}>{w => {
    const L = Math.min(132, Math.max(112, w * .3)), R = 56, T = 2, B = 22, rowH = 24, h = T + B + items.length * rowH, pw = w - L - R;
    const vals = items.flatMap(i => i.value == null ? [] : [i.value, i.hi ?? 0, i.tick ?? 0]);
    const ticks = niceTicks(min, max ?? Math.max(...vals, 1e-9), pw < 200 ? 2 : 4).filter(t => t >= min - 1e-9), top = max ?? ticks.at(-1), x = lin(min, top, L, L + pw);
    return <Svg w={w} h={h}>
      {ticks.map(t => <g key={t}><line className="grid" x1={x(t)} x2={x(t)} y1={T} y2={h - B} /><text x={x(t)} y={h - B + 15} textAnchor="middle">{tickFmt(t)}</text></g>)}
      {items.map((it, i) => { const cy = T + rowH * (i + .5), xe = it.value == null ? 0 : Math.max(x(it.value), L + 1);
        return <g key={it.key} data-tip={it.tip}>
          <rect className="hit" x="0" y={cy - rowH / 2} width={w} height={rowH} /><Label k={it.key} x={0} cy={cy} maxW={L - 6} />
          {it.value == null ? <text x={L} y={cy + 4}>{it.ghost || '—'}</text> : <>
            <rect x={L} y={cy - 4} width={xe - L} height="8" rx="2" fill={it.color} />
            {it.lo != null && <path d={`M${x(it.lo)} ${cy}H${x(it.hi)}M${x(it.lo)} ${cy - 4}v8M${x(it.hi)} ${cy - 4}v8`} className="whisker" />}
            {it.tick != null && <path d={`M${x(it.tick)} ${cy - 6}v12`} className="whisker" />}
            <text className="t-value" x={Math.max(xe, it.hi != null ? x(it.hi) : 0, it.tick != null ? x(it.tick) : 0) + 6} y={cy + 4}>{fmt(it.value)}</text>
          </>}
        </g>; })}
    </Svg>;
  }}</Chart>;
}

/* Scatter with short-name labels placed to avoid collisions. items: {key,x,y,lo,hi,color,tip} */
export function Scatter({items, xFmt, xLabel, label}) {
  return <Chart label={label}>{w => {
    const h = 340, L = 44, R = 16, T = 14, B = 40, pw = w - L - R, ph = h - T - B;
    if (!items.length) return <Svg w={w} h={h}><text x={w / 2} y={h / 2} textAnchor="middle">No model has complete data for this view</text></Svg>;
    const [x0, x1] = logDomain(items.map(i => i.x)), x = logS(x0, x1, L, L + pw);
    const [y0] = zoomDomain(items.map(i => i.lo), .05), y = lin(y0, 1, T + ph, T);
    const pts = items.map(it => ({...it, px: x(it.x), py: y(it.y)})), boxes = pts.map(p => ({x0: p.px - 4, x1: p.px + 4, y0: p.py - 4, y1: p.py + 4}));
    const hit = b => boxes.some(o => b.x0 < o.x1 && b.x1 > o.x0 && b.y0 < o.y1 && b.y1 > o.y0);
    /* Every decade gets a label; the 2s and 5s only where they clear their neighbours by 8px. */
    const xTicks = logTicks([x0, x1]).map(t => ({...t, half: xFmt(t.v).length * 3.4})), taken = [];
    const fits = t => { const a = x(t.v) - t.half, b = x(t.v) + t.half; return a >= 0 && b <= w && taken.every(([c, d]) => b + 8 <= c || a >= d + 8); };
    for (const t of [...xTicks.filter(t => t.major), ...xTicks.filter(t => !t.major)]) if (t.show = fits(t)) taken.push([x(t.v) - t.half, x(t.v) + t.half]);
    const labels = [];
    for (const p of pts.slice().sort((a, b) => a.py - b.py)) {
      const t = M(p.key).short, tw = t.length * 6.4 + 2;
      const cands = [[p.px + 7, p.py + 4, 'start'], [p.px - 7, p.py + 4, 'end'], [p.px, p.py - 8, 'middle'], [p.px, p.py + 16, 'middle'], [p.px + 7, p.py + 15, 'start'], [p.px + 7, p.py - 6, 'start'], [p.px - 7, p.py - 6, 'end'], [p.px - 7, p.py + 15, 'end']];
      for (const [lx, ly, a] of cands) { const bx0 = a === 'start' ? lx : a === 'end' ? lx - tw : lx - tw / 2, b = {x0: bx0, x1: bx0 + tw, y0: ly - 10, y1: ly + 2}; if (b.x0 < L || b.x1 > w || b.y0 < 0 || b.y1 > T + ph) continue; if (!hit(b)) { boxes.push(b); labels.push(<text key={p.key} className="t-ink" x={lx} y={ly} textAnchor={a}>{t}</text>); break; } }
    }
    return <Svg w={w} h={h}>
      {niceTicks(y0, 1, 4).filter(t => t >= y0 - 1e-9).map(t => <g key={t}><line className="grid" x1={L} x2={L + pw} y1={y(t)} y2={y(t)} /><text x={L - 6} y={y(t) + 4} textAnchor="end">{pct0(t)}</text></g>)}
      {xTicks.map(t => <g key={t.v}><line className={cn('grid', !t.major && 'minor')} x1={x(t.v)} x2={x(t.v)} y1={T} y2={T + ph} />{t.show && <text x={x(t.v)} y={T + ph + 16} textAnchor="middle">{xFmt(t.v)}</text>}</g>)}
      <line className="axis" x1={L} x2={L + pw} y1={T + ph} y2={T + ph} /><text x={L + pw / 2} y={h - 4} textAnchor="middle">{xLabel} (log scale)</text>
      {pts.map(p => <g key={p.key} data-tip={p.tip} tabIndex={0}><circle className="hit" cx={p.px} cy={p.py} r="12" /><path d={`M${p.px} ${y(p.lo)}V${y(p.hi)}`} stroke={p.color} strokeWidth="1.5" strokeOpacity=".45" /><circle cx={p.px} cy={p.py} r="4.5" fill={p.color} /></g>)}
      {labels}
    </Svg>;
  }}</Chart>;
}

/* Reliability and risk–coverage from recomputed bins and scores. */
export function Reliability({runs, cases, focus, label}) {
  return <Chart label={label}>{w => {
    const h = Math.min(w, 400) * .8, L = 40, R = 10, T = 10, B = 36, pw = w - L - R, ph = h - T - B, x = lin(0, 1, L, L + pw), y = lin(0, 1, T + ph, T);
    return <Svg w={w} h={h}>
      {[0, .25, .5, .75, 1].map(t => <g key={t}><line className="grid" x1={L} x2={L + pw} y1={y(t)} y2={y(t)} /><text x={L - 6} y={y(t) + 4} textAnchor="end">{pct0(t)}</text><text x={x(t)} y={T + ph + 16} textAnchor="middle">{pct0(t)}</text></g>)}
      <line className="ref" x1={x(0)} y1={y(0)} x2={x(1)} y2={y(1)} /><line className="axis" x1={L} x2={L + pw} y1={T + ph} y2={T + ph} /><text x={L + pw} y={h - 3} textAnchor="end">Stated confidence → observed accuracy</text>
      {runs.map(r => { const bins = subsetMetrics(r, cases).bins.filter(b => b.count), foc = focus.includes(keyOf(r)), pts = bins.map(b => `${x(b.confidence)},${y(b.accuracy)}`).join(' ');
        if (!foc) return <polyline key={r.id} className="ghost" points={pts} />;
        return <g key={r.id}><polyline points={pts} fill="none" stroke={runColor(r)} strokeWidth="2" />
          {bins.map(b => <g key={b.lo} data-tip={tip(runName(r), [['Confidence bin', `${pct0(b.lo)}–${pct0(b.hi)}`], ['Decisions', b.count], ['Mean confidence', pct(b.confidence)], ['Accuracy', pct(b.accuracy)]])}><circle className="hit" cx={x(b.confidence)} cy={y(b.accuracy)} r="10" /><circle cx={x(b.confidence)} cy={y(b.accuracy)} r={Math.min(7, 2.5 + Math.sqrt(b.count) / 2.5)} fill={runColor(r)} stroke="var(--background)" /></g>)}</g>; })}
    </Svg>;
  }}</Chart>;
}
function riskPoints(r, cases) { const sc = cases.map(c => result(r.id, c.id)).filter(Boolean).flatMap(v => v.scores).filter(s => s.confidence != null).sort((a, b) => b.confidence - a.confidence); const out = []; let wrong = 0; sc.forEach((s, i) => { if (!s.correct) wrong++; if (i % Math.max(1, Math.floor(sc.length / 40)) === 0 || i === sc.length - 1) out.push({coverage: (i + 1) / sc.length, risk: wrong / (i + 1), threshold: s.confidence, accepted: i + 1, errors: wrong}); }); return out; }
export function Risk({runs, cases, focus, label}) {
  return <Chart label={label}>{w => {
    const h = Math.min(w, 400) * .8, L = 40, R = 10, T = 10, B = 36, pw = w - L - R, ph = h - T - B;
    const all = runs.map(r => riskPoints(r, cases)), maxRisk = Math.max(.05, ...all.flat().map(p => p.risk)), top = niceTicks(0, maxRisk, 4).at(-1), x = lin(0, 1, L, L + pw), y = lin(0, top, T + ph, T);
    return <Svg w={w} h={h}>
      {niceTicks(0, top, 4).map(t => <g key={t}><line className="grid" x1={L} x2={L + pw} y1={y(t)} y2={y(t)} /><text x={L - 6} y={y(t) + 4} textAnchor="end">{pct0(t)}</text></g>)}
      {[0, .25, .5, .75, 1].map(t => <text key={t} x={x(t)} y={T + ph + 16} textAnchor="middle">{pct0(t)}</text>)}
      <line className="axis" x1={L} x2={L + pw} y1={T + ph} y2={T + ph} /><text x={L + pw} y={h - 3} textAnchor="end">Share of decisions accepted (most confident first)</text><text x={L + 4} y={T + 10}>Error rate among accepted</text>
      {runs.map((r, i) => { const ps = all[i], foc = focus.includes(keyOf(r)), pts = ps.map(p => `${x(p.coverage)},${y(p.risk)}`).join(' ');
        if (!foc) return <polyline key={r.id} className="ghost" points={pts} />;
        return <g key={r.id}><polyline points={pts} fill="none" stroke={runColor(r)} strokeWidth="2" />
          {ps.filter((_, j) => j % 5 === 0 || j === ps.length - 1).map(p => <g key={p.accepted} data-tip={tip(runName(r), [['Threshold', p.threshold.toFixed(2)], ['Accepted', `${p.accepted} (${pct(p.coverage)})`], ['Wrong among accepted', `${p.errors} (${pct(p.risk)})`]])}><circle className="hit" cx={x(p.coverage)} cy={y(p.risk)} r="10" /><circle cx={x(p.coverage)} cy={y(p.risk)} r="3" fill={runColor(r)} /></g>)}</g>; })}
    </Svg>;
  }}</Chart>;
}

/* Every row as one cell: column i is the same row for every model. Drawn on one canvas, because 12k cells as SVG
   made the whole page slow to restyle (theme switches, menus). Hover marks the column and shows the row at once;
   click opens it. */
const HEAD = 18, SH = 20, ROWH = 20, RGAP = 2, RH = 13, TOP = SH + 6;
const cssVar = (el, v) => getComputedStyle(el).getPropertyValue(v).trim();
function hatchPattern(ctx, color) {
  const c = document.createElement('canvas'); c.width = c.height = 4;
  const g = c.getContext('2d'); g.strokeStyle = color; g.lineWidth = 1.2; g.beginPath(); g.moveTo(0, 4); g.lineTo(4, 0); g.moveTo(-1, 1); g.lineTo(1, -1); g.moveTo(3, 5); g.lineTo(5, 3); g.stroke();
  return ctx.createPattern(c, 'repeat');
}
export function RecordGrid({runs, cases}) {
  const [ref, w] = useWidth(), cv = useRef(null), band = useRef(null), L = useRef(null);
  let body = null;
  if (w > 0) {
    const LW = w < 640 ? 132 : 228, groups = [];
    for (const c of cases) { const g = groups.at(-1), name = catInfo(catKey(c)).name; if (g && g.name === name) g.cases.push(c); else groups.push({name, cases: [c]}); }
    const avail = w - LW - 4, gaps = Math.max(1, groups.length - 1), pitch = Math.max(3, Math.min(12, Math.floor((avail - 7 * gaps) / cases.length))), GAP = groups.length > 1 ? Math.max(7, Math.min(22, Math.floor((avail - pitch * cases.length) / gaps))) : 0, cell = Math.max(2, pitch - 1);
    const xs = []; let x = 0; for (const g of groups) { g.x = x; for (const _ of g.cases) { xs.push(x); x += pitch; } g.w = x - g.x - 1; x += GAP; }
    const W = x - GAP, H = TOP + runs.length * (ROWH + RGAP) - RGAP, res = runs.map(r => cases.map(c => result(r.id, c.id)));
    /* 0 not run, 1 right, 2 wrong, 3 no valid answer */
    const codes = res.map(row => Uint8Array.from(row, v => !v ? 0 : !answered(v) ? 3 : okOf(v) ? 1 : 2));
    const wrong = cases.map((_, i) => { let k = 0, m = 0; for (const row of codes) { if (!row[i]) continue; m++; if (row[i] !== 1) k++; } return [k, m]; });
    L.current = {xs, pitch, cell, W, H, codes, wrong, runs, cases, res};
    body = <div className="relative flex w-max min-w-full">
      <div className="sticky left-0 z-[2] shrink-0 bg-card pr-3" style={{width: LW}}>
        <div style={{height: HEAD + 2}} />
        <div className="flex items-center text-xs text-muted-foreground" style={{height: SH, marginBottom: TOP - SH}}>Models wrong</div>
        {runs.map((r, ri) => <div key={r.id} className="flex items-center justify-between gap-2 overflow-hidden text-[13px]" style={{height: ROWH, marginBottom: RGAP}} title={runName(r)}>
          <span className="inline-flex min-w-0 items-center gap-2"><i className="size-2 shrink-0 rounded-full" style={{background: ident(r).color}} /><span className="truncate font-medium">{w < 640 ? ident(r).short : ident(r).name}</span></span>
          <span className="shrink-0 text-xs whitespace-nowrap text-muted-foreground tabular-nums">{codes[ri].reduce((n, v) => n + (v > 1), 0)} wrong</span>
        </div>)}
      </div>
      <div className="relative" style={{width: W}}>
        <svg width={W} height={HEAD} aria-hidden="true" className={cn(SVG_CLS, 'mb-0.5')}>{groups.map(g => { const fit = Math.floor(g.w / 6.3), short = g.name.split(/\s+/)[0], t = g.name.length <= fit ? g.name : short.length <= fit ? short : fit >= 4 ? clip(short, fit) : ''; return <g key={g.name} data-tip={tip(g.name, [['Rows', g.cases.length]])}><rect className="hit" x={g.x} y="0" width={g.w + 1} height="18" />{t && <text className="t-ink" x={g.x} y="10">{t}</text>}<line className="axis" x1={g.x} x2={g.x + g.w} y1="16.5" y2="16.5" /></g>; })}</svg>
        <div ref={band} aria-hidden="true" className="pointer-events-none absolute bottom-0 left-0 z-[1] rounded-[3px] bg-foreground/[.08] opacity-0 ring-1 ring-foreground/15" style={{top: HEAD + 2, width: 0}} />
        <canvas ref={cv} className="relative block cursor-pointer" style={{width: W, height: H}} />
      </div>
    </div>;
  }
  useEffect(() => {
    const c = cv.current, g = L.current; if (!c || !g) return;
    const {xs, pitch, cell, W, H, codes, wrong} = g, n = xs.length, ctx = c.getContext('2d');
    const dpr = Math.min(2, devicePixelRatio || 1); c.width = Math.ceil(W * dpr); c.height = Math.ceil(H * dpr);
    const draw = () => {
      const ok = cssVar(c, '--grid-ok'), bad = cssVar(c, '--bad'), line = cssVar(c, '--border'), hatch = hatchPattern(ctx, bad);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = line; for (let i = 0; i < n; i++) ctx.fillRect(xs[i], SH - 1, cell, 1);
      ctx.fillStyle = bad; for (let i = 0; i < n; i++) { const [k, m] = wrong[i]; if (k && m) { const hh = Math.round((SH - 3) * k / m); ctx.fillRect(xs[i], SH - 1 - hh, cell, hh); } }
      codes.forEach((row, ri) => {
        const y = TOP + ri * (ROWH + RGAP) + (ROWH - RH) / 2;
        for (const [code, style] of [[1, ok], [2, bad], [3, hatch]]) { ctx.fillStyle = style; for (let i = 0; i < n; i++) if (row[i] === code) ctx.fillRect(xs[i], y, cell, RH); }
        ctx.lineWidth = 1;
        for (const [code, style] of [[0, line], [3, bad]]) { ctx.strokeStyle = style; for (let i = 0; i < n; i++) if (row[i] === code) ctx.strokeRect(xs[i] + .5, y + .5, Math.max(0, cell - 1), RH - 1); }
      });
    };
    /* Which row and model sit under the pointer. */
    const at = e => {
      const r = c.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
      let lo = 0, hi = n - 1; while (lo < hi) { const m = (lo + hi + 1) >> 1; if (xs[m] <= x) lo = m; else hi = m - 1; }
      if (!(x >= xs[lo] && x < xs[lo] + pitch)) return null;
      if (y < SH) return {i: lo, ri: -1};
      const ri = Math.floor((y - TOP) / (ROWH + RGAP)); return y >= TOP && ri < codes.length ? {i: lo, ri} : null;
    };
    let key = '';
    const mark = i => { const b = band.current; if (!b) return; if (i < 0) { b.style.opacity = '0'; return; } b.style.transform = `translateX(${xs[i] - 2}px)`; b.style.width = `${cell + 4}px`; b.style.opacity = '1'; };
    const move = e => {
      const h = at(e), k = h ? `${h.i}:${h.ri}` : '';
      if (!h) { if (key) { hideTip(); mark(-1); } key = ''; return; }
      if (k === key) { moveTip(e.clientX, e.clientY); return; }
      key = k; mark(h.i);
      const cs = g.cases[h.i], [nk, nm] = wrong[h.i];
      showTip({t: caseTitle(cs), r: h.ri < 0 ? [['Models wrong', `${nk} of ${nm}`], ['Answer key', goldText(cs)]] : [['Task', taskName(cs.task)], ['Answer key', goldText(cs)], [ident(g.runs[h.ri]).name, answerOf(g.res[h.ri][h.i])]]}, e.clientX, e.clientY);
    };
    const leave = () => { key = ''; hideTip(); mark(-1); };
    const click = e => { const h = at(e); if (h) location.hash = rowHref(g.cases[h.i]); };
    draw();
    const mo = new MutationObserver(draw); mo.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
    c.addEventListener('pointermove', move); c.addEventListener('pointerleave', leave); c.addEventListener('click', click);
    return () => { mo.disconnect(); c.removeEventListener('pointermove', move); c.removeEventListener('pointerleave', leave); c.removeEventListener('click', click); hideTip(); };
  }, [w, runs, cases]);
  return <div ref={ref} role="img" aria-label="Result of every model on every row" className="w-full min-w-0 overflow-x-auto pb-1">{body}</div>;
}

export const Legend = ({items}) => (
  <div className="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
    {items.map(([kind, color, text]) => <span key={text} className="inline-flex items-center gap-1.5">
      <i className={cn('inline-block', kind === 'bar' ? 'h-3 w-1' : 'size-2.5 rounded-[2px]', kind === 'box' && 'border')} style={kind === 'hatch' ? {background: 'repeating-linear-gradient(45deg,var(--bad) 0 1.5px,transparent 1.5px 4px)'} : kind === 'box' ? {borderColor: color} : {background: color}} />{text}
    </span>)}
  </div>
);
