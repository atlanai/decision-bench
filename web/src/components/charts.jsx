/* SVG charts drawn at the container's measured width. Hover and focus details come from data-tip (see tip.jsx). */
import {useLayoutEffect, useRef, useState} from 'react';
import {M, result, okOf, answered, caseTitle, taskName, goldText, ident, runName, runColor, keyOf, subsetMetrics, catKey, catInfo, answerOf} from '@/lib/bench';
import {pct, pct0, clip} from '@/lib/format';
import {rowHref} from '@/lib/route';
import {tip} from '@/components/tip';
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
    const labels = [];
    for (const p of pts.slice().sort((a, b) => a.py - b.py)) {
      const t = M(p.key).short, tw = t.length * 6.4 + 2;
      const cands = [[p.px + 7, p.py + 4, 'start'], [p.px - 7, p.py + 4, 'end'], [p.px, p.py - 8, 'middle'], [p.px, p.py + 16, 'middle'], [p.px + 7, p.py + 15, 'start'], [p.px + 7, p.py - 6, 'start'], [p.px - 7, p.py - 6, 'end'], [p.px - 7, p.py + 15, 'end']];
      for (const [lx, ly, a] of cands) { const bx0 = a === 'start' ? lx : a === 'end' ? lx - tw : lx - tw / 2, b = {x0: bx0, x1: bx0 + tw, y0: ly - 10, y1: ly + 2}; if (b.x0 < L || b.x1 > w || b.y0 < 0 || b.y1 > T + ph) continue; if (!hit(b)) { boxes.push(b); labels.push(<text key={p.key} className="t-ink" x={lx} y={ly} textAnchor={a}>{t}</text>); break; } }
    }
    return <Svg w={w} h={h}>
      {niceTicks(y0, 1, 4).filter(t => t >= y0 - 1e-9).map(t => <g key={t}><line className="grid" x1={L} x2={L + pw} y1={y(t)} y2={y(t)} /><text x={L - 6} y={y(t) + 4} textAnchor="end">{pct0(t)}</text></g>)}
      {logTicks([x0, x1]).map(t => <g key={t.v}><line className={cn('grid', !t.major && 'minor')} x1={x(t.v)} x2={x(t.v)} y1={T} y2={T + ph} />{(t.major || pw > 420) && <text x={x(t.v)} y={T + ph + 16} textAnchor="middle">{xFmt(t.v)}</text>}</g>)}
      <line className="axis" x1={L} x2={L + pw} y1={T + ph} y2={T + ph} /><text x={L + pw} y={h - 4} textAnchor="end">{xLabel} (log scale)</text>
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

/* Every row as one cell. Column i is the same row for every model. */
export function RecordGrid({runs, cases}) {
  const [ref, w] = useWidth();
  let body = null;
  if (w > 0) {
    const LW = w < 640 ? 132 : 228, groups = [];
    for (const c of cases) { const g = groups.at(-1), name = catInfo(catKey(c)).name; if (g && g.name === name) g.cases.push(c); else groups.push({name, cases: [c]}); }
    const avail = w - LW - 4, gaps = Math.max(1, groups.length - 1), pitch = Math.max(3, Math.min(12, Math.floor((avail - 7 * gaps) / cases.length))), GAP = groups.length > 1 ? Math.max(7, Math.min(22, Math.floor((avail - pitch * cases.length) / gaps))) : 0, cell = Math.max(2, pitch - 1), RH = 13;
    const xs = []; let x = 0; for (const g of groups) { g.x = x; for (const _ of g.cases) { xs.push(x); x += pitch; } g.w = x - g.x - 1; x += GAP; }
    const W = x - GAP, res = runs.map(r => cases.map(c => result(r.id, c.id)));
    const wrong = cases.map((c, i) => { let k = 0, m = 0; res.forEach(row => { const v = row[i]; if (!v) return; m++; if (!okOf(v)) k++; }); return [k, m]; });
    const SH = 20, label = 'sticky left-0 z-[1] flex shrink-0 items-center justify-between gap-2 overflow-hidden bg-card pr-3 text-[13px]';
    body = <div className="flex w-max min-w-full flex-col gap-0.5">
      <div className="flex items-center"><div className={label} style={{width: LW}} />
        <svg width={W} height={18} aria-hidden="true" className={SVG_CLS}>{groups.map(g => { const fit = Math.floor(g.w / 6.3), short = g.name.split(/\s+/)[0], t = g.name.length <= fit ? g.name : short.length <= fit ? short : fit >= 4 ? clip(short, fit) : ''; return <g key={g.name} data-tip={tip(g.name, [['Rows', g.cases.length]])}><rect className="hit" x={g.x} y="0" width={g.w + 1} height="18" />{t && <text className="t-ink" x={g.x} y="10">{t}</text>}<line className="axis" x1={g.x} x2={g.x + g.w} y1="16.5" y2="16.5" /></g>; })}</svg>
      </div>
      <div className="mb-1 flex items-center"><div className={cn(label, 'text-xs text-muted-foreground')} style={{width: LW}}>Models wrong</div>
        <svg width={W} height={SH} aria-hidden="true" className={SVG_CLS}>{cases.map((c, i) => { const [k, m] = wrong[i], hh = m ? Math.round((SH - 3) * k / m) : 0; return <a key={c.id} href={rowHref(c)} tabIndex={-1} data-tip={tip(caseTitle(c), [['Models wrong', `${k} of ${m}`], ['Answer key', goldText(c)]])}><rect className="hit" x={xs[i]} y="0" width={pitch} height={SH} /><rect x={xs[i]} y={SH - 1} width={cell} height="1" fill="var(--border)" />{hh > 0 && <rect x={xs[i]} y={SH - 1 - hh} width={cell} height={hh} fill="var(--bad)" />}</a>; })}</svg>
      </div>
      {runs.map((r, ri) => { let n = 0; const cells = cases.map((c, i) => { const v = res[ri][i], ok = okOf(v), err = v && !answered(v); if (v && !ok) n++; const inset = !v || err ? .5 : 0;
          return <a key={c.id} href={rowHref(c)} tabIndex={-1} data-tip={tip(caseTitle(c), [['Task', taskName(c.task)], ['Answer key', goldText(c)], [ident(r).name, answerOf(v)]])}><rect x={xs[i] + inset} y={inset} width={cell - 2 * inset} height={RH - 2 * inset} fill={!v ? 'none' : err ? 'url(#hatch)' : ok ? 'var(--grid-ok)' : 'var(--bad)'} stroke={!v ? 'var(--border)' : err ? 'var(--bad)' : undefined} className="hover:stroke-foreground" /></a>; });
        return <div key={r.id} className="flex items-center"><div className={label} style={{width: LW}} title={runName(r)}>
          <span className="inline-flex min-w-0 items-center gap-2"><i className="size-2 shrink-0 rounded-full" style={{background: ident(r).color}} /><span className="truncate font-medium">{w < 640 ? ident(r).short : ident(r).name}</span></span>
          <span className="shrink-0 text-xs whitespace-nowrap text-muted-foreground tabular-nums">{n} wrong</span></div>
          <svg width={W} height={RH} aria-hidden="true" className={SVG_CLS}><Hatch />{cells}</svg></div>; })}
    </div>;
  }
  return <div ref={ref} role="img" aria-label="Result of every model on every row" className="w-full min-w-0 overflow-x-auto pb-1">{body}</div>;
}

export const Legend = ({items}) => (
  <div className="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
    {items.map(([kind, color, text]) => <span key={text} className="inline-flex items-center gap-1.5">
      <i className={cn('inline-block', kind === 'bar' ? 'h-3 w-1' : 'size-2.5 rounded-[2px]', kind === 'box' && 'border')} style={kind === 'hatch' ? {background: 'repeating-linear-gradient(45deg,var(--bad) 0 1.5px,transparent 1.5px 4px)'} : kind === 'box' ? {borderColor: color} : {background: color}} />{text}
    </span>)}
  </div>
);
