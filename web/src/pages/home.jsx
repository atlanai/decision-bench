import {track} from '@/lib/analytics';
import {useEffect, useLayoutEffect, useRef, useState} from 'react';
import {ArrowDownIcon, ArrowUpIcon, ChevronDownIcon} from 'lucide-react';
import * as B from '@/lib/bench';
import {pct, pct0, ms, money, compact, num, metric, plural, secs, ciText} from '@/lib/format';
import {href, withQ, rowHref, taskHref, catHref, modelHref} from '@/lib/route';
import {haptic, reducedMotion, usePhone} from '@/lib/device';
import {tip} from '@/components/tip';
import {cn} from '@/lib/utils';
import {ModelName, Logo, Section, Notice, Dash, Notes} from '@/components/common';
import {List, Item} from '@/components/list';
import {UseCaseSelect, ModalityTabs, ModelPicker, selectedRuns} from '@/components/filters';
import {RowsChart, Scatter, RecordGrid, Legend, zoomDomain} from '@/components/charts';
import {HeatTasks} from '@/components/heat';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {SegmentedControl, SegmentedList, SegmentedOption} from '@/components/ui/segmented-control';

const scopeCases = route => { const cat = route.q.get('category') || '', mod = route.q.get('modality') || ''; return B.rowsInOrder().filter(c => (!cat || B.catKey(c) === cat) && (!mod || (mod === 'image') === B.isImageTask(c.task))); };
export const ChartCard = ({title, description, foot, children, className}) => (
  <div className={cn('min-w-0 rounded-xl border bg-card p-4 shadow-xs md:p-5', className)}>
    <h3 className="text-sm font-semibold">{title}</h3>
    {description && <p className="mt-0.5 mb-4 text-xs text-muted-foreground">{description}</p>}
    {children}
    {foot && <p className="mt-3 text-xs text-muted-foreground">{foot}</p>}
  </div>
);
const Link = ({href, children}) => <a href={href} className="text-brand underline underline-offset-4">{children}</a>;
const HowToAdd = () => <>Results are added by pull request: run a model on every row, publish the run into <code>results/</code>, and open a PR. {B.repoOk() && <Link href={B.gh('results/README.md')}>How to submit results</Link>}</>;
const SubmitLink = () => B.repoOk() ? <Link href={B.gh('results/README.md')}>How to submit results</Link> : null;

/* ---------- Banner ---------- */
/* Rows by use case as a small pixel bar chart, one square per eight rows (ten on phones). Each line filters the leaderboard.
   On hover a wave runs across the squares (see .px-* in index.html) and the caption under the list says what the
   use case covers, in place, so nothing floats over the chart. The caption keeps a fixed two-line height: the block
   is centred in the banner, so a caption that grew or shrank would shift the whole list. */
const PER = 8;
function UseCases({route}) {
  const cur = route.q.get('category') || '', counts = B.categoryOrder().map(k => [k, B.allCases.filter(c => B.catKey(c) === k).length]);
  /* Phones: a square per ten rows, so the longest bar still clears its count. */
  const [hot, setHot] = useState(''), shown = hot || cur, per = usePhone() ? 10 : PER;
  return (
    <div data-no-trail className="w-full rounded-xl border bg-background/90 p-3 shadow-xs backdrop-blur-sm sm:p-4 lg:max-w-[420px] lg:justify-self-end">
      <div className="mb-3 flex items-baseline justify-between gap-4 px-0.5 font-mono text-[11px] tracking-[.08em] text-muted-foreground uppercase sm:px-0">
        <span>Browse by use case</span>
        <span className="inline-flex items-center gap-1.5"><i className="inline-block size-[6px] bg-foreground/70" />= {per} rows</span>
      </div>
      <ul className="px-strip -mx-2" onPointerLeave={() => setHot('')}>
        {counts.map(([k, n]) => { const on = cur === k, sq = Math.max(1, Math.round(n / per)), w = sq * 8 - 2;
          return <li key={k}><a href={href('', {category: on ? '' : k, modality: route.q.get('modality') || ''})} aria-describedby="use-case-note" data-on={on || undefined} aria-current={on || undefined}
            onPointerEnter={() => setHot(k)} onFocus={() => setHot(k)} onBlur={() => setHot('')}
            className="px-chip grid grid-cols-[7.75rem_minmax(0,1fr)_1.75rem] items-center gap-2 rounded-md px-1.5 py-[7px] font-mono text-[11px] tracking-[.06em] uppercase outline-offset-0 hover:bg-muted focus-visible:bg-muted active:bg-muted sm:grid-cols-[10rem_minmax(0,1fr)_2.25rem] sm:gap-3 sm:px-2 sm:py-[5px]">
            <span className="px-label truncate">{B.catInfo(k).name}</span>
            <svg width={w} height="6" viewBox={`0 0 ${w} 6`} aria-hidden="true" className="overflow-visible">
              {Array.from({length: sq}, (_, i) => <rect key={i} x={i * 8} y="0" width="6" height="6" className="px px-on" style={{'--d': `${i * 22}ms`}} />)}
            </svg>
            <span className="px-n text-right tabular-nums">{n}</span>
          </a></li>; })}
      </ul>
      <p id="use-case-note" aria-live="polite" className="mt-3 box-content h-[2.75em] border-t pt-3 text-[13px] leading-snug text-muted-foreground"><span className="line-clamp-2">
        {shown ? <><span className="font-medium text-foreground">{B.catInfo(shown).name}.</span> {B.catInfo(shown).description}{cur === shown && !hot && <> <a href={href('', {modality: route.q.get('modality') || ''})} className="text-foreground underline-offset-4 hover:underline">Show all</a></>}</> : 'Pick a use case to filter the leaderboard to its rows.'}
      </span></p>
    </div>
  );
}
/* The banner under the cursor: a pink glow glides after the pointer (eased, so it trails a little), the grid lines
   around it turn pink, and the cells the pointer crosses light up as pixels that fade out, with a few sparks
   beside them. Drawn on one canvas; positions go to CSS variables, never through React state. */
const GRID = 'bg-[linear-gradient(var(--grid-line)_1px,transparent_1px),linear-gradient(90deg,var(--grid-line)_1px,transparent_1px)] bg-[size:24px_24px] bg-[position:0_0]';
const CELL = 24;
function usePixelTrail(ref, canvasRef) {
  useEffect(() => {
    const el = ref.current, cv = canvasRef.current; if (!el || !cv) return;
    const ctx = cv.getContext('2d'), reduce = matchMedia('(prefers-reduced-motion: reduce)').matches, cells = new Map();
    let tx = 0, ty = 0, sx = 0, sy = 0, inside = false, raf = 0, last = null, pink = '#F34D77', dpr = 1;
    const size = () => { dpr = Math.min(2, devicePixelRatio || 1); cv.width = el.clientWidth * dpr; cv.height = el.clientHeight * dpr; cv.style.width = `${el.clientWidth}px`; cv.style.height = `${el.clientHeight}px`; pink = getComputedStyle(el).getPropertyValue('--pink').trim() || pink; };
    const ro = new ResizeObserver(size); ro.observe(el); size();
    const light = (c, r, v) => { const k = `${c},${r}`; cells.set(k, Math.max(cells.get(k) || 0, v)); };
    const frame = () => {
      raf = 0;
      sx += (tx - sx) * (reduce ? 1 : .16); sy += (ty - sy) * (reduce ? 1 : .16);
      el.style.setProperty('--mx', `${sx}px`); el.style.setProperty('--my', `${sy}px`);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, cv.width, cv.height); ctx.fillStyle = pink;
      for (const [k, v] of cells) {
        const [c, r] = k.split(',').map(Number), inset = 3 + (1 - v) * 5;
        ctx.globalAlpha = v * .5; ctx.fillRect(c * CELL + inset, r * CELL + inset, CELL - 2 * inset + 1, CELL - 2 * inset + 1);
        const nv = v * (reduce ? 0 : .94); if (nv < .03) cells.delete(k); else cells.set(k, nv);
      }
      ctx.globalAlpha = 1;
      if (inside || cells.size || Math.abs(tx - sx) + Math.abs(ty - sy) > .5) raf = requestAnimationFrame(frame);
    };
    const kick = () => { if (!raf) raf = requestAnimationFrame(frame); };
    const move = e => {
      if (e.pointerType !== 'mouse') return;
      const b = el.getBoundingClientRect(); tx = e.clientX - b.left; ty = e.clientY - b.top;
      if (!inside) { sx = tx; sy = ty; } inside = true;
      const c = Math.floor(tx / CELL), r = Math.floor(ty / CELL);
      /* No pixels behind the use-case list, and the pink grid and glow fade while the pointer is on it (data-calm):
         its own hover wave is the effect there, and the labels stay legible. */
      if (e.target.closest?.('[data-no-trail]')) { if (el.dataset.calm == null) el.dataset.calm = ''; last = null; kick(); return; }
      if (el.dataset.calm != null) delete el.dataset.calm;
      if (!reduce && (!last || last[0] !== c || last[1] !== r)) {
        /* Fill the cells between the last one and this one, so a fast swipe leaves an unbroken trail. */
        const [c0, r0] = last || [c, r], steps = Math.max(Math.abs(c - c0), Math.abs(r - r0), 1);
        for (let i = 1; i <= steps; i++) light(Math.round(c0 + (c - c0) * i / steps), Math.round(r0 + (r - r0) * i / steps), 1);
        for (let i = 0; i < 2; i++) if (Math.random() < .55) light(c + Math.round(Math.random() * 4 - 2), r + Math.round(Math.random() * 2 - 1), .35 + Math.random() * .35);
        last = [c, r];
      }
      kick();
    };
    const leave = () => { inside = false; last = null; delete el.dataset.calm; kick(); };
    /* No hover on a touch screen: a tap sets off a small burst of pixels where the finger lands instead. */
    const tap = e => {
      if (e.pointerType === 'mouse' || reduce || e.target.closest?.('[data-no-trail],a,button')) return;
      const b = el.getBoundingClientRect(), c = Math.floor((e.clientX - b.left) / CELL), r = Math.floor((e.clientY - b.top) / CELL);
      light(c, r, 1); for (let i = 0; i < 9; i++) light(c + Math.round(Math.random() * 4 - 2), r + Math.round(Math.random() * 4 - 2), .35 + Math.random() * .6);
      haptic(6); kick();
    };
    el.addEventListener('pointermove', move); el.addEventListener('pointerleave', leave); el.addEventListener('pointerdown', tap);
    return () => { el.removeEventListener('pointermove', move); el.removeEventListener('pointerleave', leave); el.removeEventListener('pointerdown', tap); ro.disconnect(); cancelAnimationFrame(raf); };
  }, [ref, canvasRef]);
}
function Banner({route}) {
  const rows = B.allCases.length, imgs = B.allCases.filter(c => B.isImageTask(c.task)).length, models = B.RUNS.length, configured = B.ORDER.filter(k => B.MODELS[k].configured).length;
  const stat = (l, v, t) => <div title={t || undefined} className="flex min-w-0 flex-col-reverse px-3 first:pl-0 last:pr-0 sm:px-6"><dt className="mt-1 font-mono text-[10px] tracking-[.08em] text-muted-foreground uppercase sm:text-[11px]">{l}</dt><dd className="font-mono text-xl font-medium tabular-nums sm:text-2xl">{v}</dd></div>;
  const box = useRef(null), canvas = useRef(null);
  usePixelTrail(box, canvas);
  return (
    <div ref={box} className={cn('group/banner relative overflow-hidden border-b [--grid-line:var(--border)]', GRID)}>
      <div className="relative bg-gradient-to-b from-background/40 via-background/70 to-background">
        <canvas ref={canvas} aria-hidden="true" className="pointer-events-none absolute top-0 left-0" />
        <div aria-hidden="true" className={cn('pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-700 group-hover/banner:opacity-100 group-data-[calm]/banner:opacity-0! [--grid-line:color-mix(in_oklab,var(--pink)_55%,transparent)] [mask-image:radial-gradient(200px_circle_at_var(--mx,50%)_var(--my,50%),#000,transparent_72%)]', GRID)} />
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-700 group-hover/banner:opacity-100 group-data-[calm]/banner:opacity-0! [background:radial-gradient(360px_circle_at_var(--mx,50%)_var(--my,50%),color-mix(in_oklab,var(--pink)_9%,transparent),transparent_70%)]" />
        <div className="relative mx-auto grid max-w-[1240px] items-center gap-x-16 gap-y-10 px-4 pt-8 pb-10 md:px-8 md:pt-14 md:gap-y-12 md:pb-12 lg:grid-cols-[minmax(0,1fr)_minmax(340px,400px)]">
          <div>
            <p className="mb-4 font-mono text-[11px] tracking-[.08em] text-muted-foreground uppercase md:mb-5"><span className="max-md:hidden">Decision Bench · </span>{B.man().version} · real records, open licences</p>
            <h1 className="max-w-[16ch] font-pixel text-4xl leading-[1.02] uppercase sm:text-5xl lg:text-[52px]">Can a small model make <em className="text-brand not-italic">this decision</em> for you?</h1>
            <p className="mt-5 max-w-[48ch] text-base leading-relaxed text-foreground/75">Route a ticket, spot an injection, check a contract: real records from <Link href="#/data">open datasets</Link>, each answered by its source, never by a model.</p>
            <dl className="mt-7 flex gap-y-4 divide-x sm:mt-8 sm:flex-wrap">
              {stat('rows', num(rows), imgs ? `${num(imgs)} with images` : '')}{stat('tasks', B.taskOrder().length)}{stat(models ? 'models' : 'configured', models || configured)}{stat('datasets', B.DATASETS.length)}
            </dl>
          </div>
          <UseCases route={route} />
        </div>
      </div>
    </div>
  );
}

/* ---------- Leaderboard ---------- */
/* One-word column labels so the header stays on a single line; the full name is in the tooltip */
const SHORT_CAT = {'AI agents': 'Agents', 'Customer support': 'Support', 'Product management': 'Product'};
const shortCat = name => { const n = name.split(' & ')[0]; return SHORT_CAT[n] || n; };
const ASC = ['latency', 'cost', 'tokens', 'ece', 'brier', 'errors'];
/* Holds the extra-columns toggle so flipping it re-renders only the table, not the charts below. */
function LeaderboardSection({route, runs, cases}) {
  const [more, setMore] = useState(false), cat = route.q.get('category') || '';
  const toggle = <Button variant="ghost" size="sm" className="text-muted-foreground max-md:hidden" title="Tokens, macro F1, calibration and errors" aria-expanded={more} data-track="leaderboard_columns" onClick={() => setMore(v => !v)}>{more ? 'Fewer columns' : 'More columns'}<ChevronDownIcon className={cn('size-3.5 transition-transform', more && 'rotate-180')} /></Button>;
  const scope = `${cat ? `${B.catInfo(cat).name} rows` : 'All rows'}${route.q.get('modality') ? ` · ${route.q.get('modality')} inputs` : ''}`;
  return <Section id="leaderboard" title="Leaderboard" actions={toggle} description={<><span className="max-md:hidden">{scope}. Click a column to re-sort.</span><span className="md:hidden">{scope} · {plural(cases.length, 'row')} in {new Set(cases.map(c => c.task)).size} tasks.</span></>} className="mt-6 md:mt-8">
    <div className="md:hidden"><LeaderList runs={runs} cases={cases} /></div>
    <div className="max-md:hidden"><Leaderboard route={route} runs={runs} cases={cases} more={more} /></div>
  </Section>;
}
function Leaderboard({route, runs, cases, more}) {
  const [sort, setSort] = useState({key: 'accuracy', dir: 'desc'});
  const cat = route.q.get('category') || '', cols = cat ? B.taskOrder().filter(t => cases.some(c => c.task === t)) : B.categoryOrder().filter(k => cases.some(c => B.catKey(c) === k));
  const colCases = k => cases.filter(c => (cat ? c.task : B.catKey(c)) === k), colName = k => cat ? B.taskName(k) : B.catInfo(k).name, colHref = k => cat ? taskHref(k) : catHref(k);
  const tasks = [...new Set(cases.map(c => c.task))];
  const metrics = runs.map(r => [r, B.subsetMetrics(r, cases)]), all = metrics.map(([, m]) => m);
  const los = metrics.flatMap(([, m]) => m.wilson || []), [d0] = los.length ? zoomDomain(los, .1) : [0], cx = v => (v - d0) / (1 - d0 || 1) * 56;
  const value = (m, key, r) => key.startsWith('col:') ? B.subsetMetrics(r, colCases(key.slice(4))).accuracy : {accuracy: m.accuracy, latency: m.latency.p50, cost: m.costPer1k, tokens: m.tokensIn == null ? null : m.tokensIn + (m.tokensOut || 0), ece: m.ece, brier: m.brier, macro: B.macroF1(r, tasks), errors: m.errors}[key];
  const sorted = metrics.slice().sort(([ra, a], [rb, b]) => { const va = value(a, sort.key, ra), vb = value(b, sort.key, rb); if (va == null) return 1; if (vb == null) return -1; return sort.dir === 'asc' ? va - vb : vb - va; });
  const Th = ({k, children, className, title}) => (
    <th title={title} className={cn('h-10 px-3 text-[13px] font-medium whitespace-nowrap text-muted-foreground first:pl-5 last:pr-5', className)}>
      {k ? <button type="button" data-track={`sort_${k}`} onClick={() => setSort(s => s.key === k ? {key: k, dir: s.dir === 'desc' ? 'asc' : 'desc'} : {key: k, dir: ASC.includes(k) ? 'asc' : 'desc'})} className={cn('inline-flex cursor-pointer items-center gap-1 hover:text-foreground', sort.key === k && 'text-foreground')}>
        {children}{sort.key === k && (sort.dir === 'desc' ? <ArrowDownIcon className="size-3.5" /> : <ArrowUpIcon className="size-3.5" />)}</button> : children}
    </th>
  );
  const partial = all.some(m => m.costCoverage != null && m.costCoverage < 1);
  return <>
    <div className="overflow-hidden rounded-xl border bg-card shadow-xs">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr className="border-b text-left align-bottom [&>th]:py-2">
            <Th title="1 + the number of models whose 95% interval lies entirely above this one" className="w-10">#</Th><Th className="sticky left-0 z-[1] bg-card">Model</Th>
            <Th k="accuracy" title="Share of rows answered as the key does, with its Wilson 95% interval">Accuracy</Th>
            {cols.map(k => <Th key={k} k={`col:${k}`} className={cn('px-1.5 text-right', cat && 'text-xs leading-tight whitespace-normal [&_button]:max-w-[84px] [&_button]:text-right')} title={`${colName(k)}: accuracy on ${colCases(k).length} rows`}>{cat ? colName(k) : shortCat(colName(k))}</Th>)}
            <Th k="latency" className="text-right" title="Median wall-clock time per row">Latency</Th>
            <Th k="cost" className="text-right" title="Cost per 1,000 rows: provider-reported, else estimated from list prices">$ / 1k</Th>
            {more && <><Th k="tokens" className="text-right" title="Input + output tokens per row">Tokens</Th><Th k="macro" className="text-right" title="Mean F1 across tasks">Macro F1</Th><Th k="ece" className="text-right" title="Expected calibration error; lower is better">ECE</Th><Th k="brier" className="text-right" title="Squared error of the stated probabilities; lower is better">Brier</Th><Th k="errors" className="text-right" title="Rows with no valid answer; counted as wrong">No answer</Th></>}
          </tr></thead>
          <tbody>
            {sorted.map(([r, m]) => { const ci = m.wilson, tp = m.tokensIn == null ? null : m.tokensIn + (m.tokensOut || 0);
              return <tr key={r.id} className="border-b transition-colors last:border-0 hover:bg-muted/40">
                <td className="py-2.5 pl-5 text-muted-foreground tabular-nums">{m.questions ? B.rankOf(m, all) : '—'}</td>
                {/* Stays put while the use-case columns scroll sideways on narrower screens. */}
                <td className="sticky left-0 z-[1] bg-card px-3 py-2.5 max-xl:shadow-[1px_0_0_var(--border)]"><ModelName k={B.keyOf(r)} /></td>
                <td className="px-3 py-2.5" data-tip={tip(B.runName(r), [['Accuracy', pct(m.accuracy)], ['95% interval', ciText(ci)], ['Correct', `${m.correct}/${m.questions}`]])}>
                  <span className="flex items-center gap-3 whitespace-nowrap">
                    <span className="w-12 font-semibold tabular-nums">{pct(m.accuracy)}</span>
                    {ci && <span className="relative inline-block h-2.5 w-14 shrink-0" aria-hidden="true"><i className="absolute inset-x-0 top-[4.5px] h-px bg-border" /><i className="absolute top-[3px] h-1 rounded-full bg-foreground/20" style={{left: cx(ci[0]), width: Math.max(2, cx(ci[1]) - cx(ci[0]))}} /><b className="absolute top-px h-2 w-[3px] -translate-x-1/2 rounded-[1px]" style={{left: cx(m.accuracy), background: B.runColor(r)}} /></span>}
                  </span>
                </td>
                {cols.map(k => { const s = B.subsetMetrics(r, colCases(k)); return <td key={k} className="px-1.5 py-2.5 text-right text-foreground/80 tabular-nums" data-tip={s.questions ? tip(`${B.runName(r)} · ${colName(k)}`, [['Accuracy', pct(s.accuracy)], ['95% interval', ciText(s.wilson)], ['Correct', `${s.correct}/${s.questions}`]]) : undefined}>{s.questions ? pct0(s.accuracy) : <Dash />}</td>; })}
                <td className="px-3 py-2.5 text-right whitespace-nowrap tabular-nums">{ms(m.latency.p50)}</td>
                <td className={cn('px-3 py-2.5 text-right whitespace-nowrap tabular-nums', !more && 'pr-5')}>{money(m.costPer1k)}{m.costCoverage != null && m.costCoverage < 1 && <sup className="text-warn" title={`Cost known for ${pct(m.costCoverage)} of rows`}>*</sup>}</td>
                {more && <><td className="px-3 py-2.5 text-right tabular-nums" data-tip={tp != null ? tip(B.runName(r), [['Input / row', compact(m.tokensIn)], ['Output / row', compact(m.tokensOut)]]) : undefined}>{compact(tp)}</td><td className="px-3 py-2.5 text-right tabular-nums">{pct(B.macroF1(r, tasks))}</td><td className="px-3 py-2.5 text-right tabular-nums">{metric(m.ece)}</td><td className="px-3 py-2.5 text-right tabular-nums">{metric(m.brier)}</td><td className="py-2.5 pr-5 pl-3 text-right tabular-nums">{num(m.errors)}</td></>}
              </tr>; })}
          </tbody>
        </table>
      </div>
    </div>
    <Notes items={[
      'Overlapping 95% intervals share a rank.',
      B.allCases.some(c => B.isImageTask(c.task)) && 'Image tasks count only for models sent the image.',
      partial && '* Cost known for part of the rows.',
      B.PARTIAL.length > 0 && `Partial, not ranked: ${B.PARTIAL.map(r => `${B.ident(r).short} (${num(r.metrics.cases)} of ${num(B.allCases.length)} rows)`).join(', ')}.`,
      B.unevaluated().length > 0 && <>Not yet evaluated: {B.unevaluated().map(k => B.M(k).short).join(', ')}. <SubmitLink /></>,
    ]} />
  </>;
}

/* Phones: the leaderboard as a list, re-sorted by a segmented control. A row that moved settles in with a short
   nudge from the side it came from and a quick fade; no travel across the list. */
function useSettle(ref, key) {
  const at = useRef(new Map());
  useLayoutEffect(() => {
    const items = [...(ref.current?.querySelectorAll('[data-flip]') || [])], next = new Map(items.map(n => [n.dataset.flip, n.offsetTop]));
    if (at.current.size && !reducedMotion()) for (const n of items) { const d = (at.current.get(n.dataset.flip) ?? next.get(n.dataset.flip)) - next.get(n.dataset.flip); if (Math.abs(d) > 1) n.animate([{opacity: .45, transform: `translateY(${Math.sign(d) * Math.min(16, Math.abs(d))}px)`}, {opacity: 1, transform: 'none'}], {duration: 260, easing: 'cubic-bezier(.2,.8,.2,1)'}); }
    at.current = next;
  }, [ref, key]);
}
const BY = {accuracy: ['Most accurate', m => m.accuracy, -1, m => pct(m.accuracy)], latency: ['Fastest', m => m.latency.p50, 1, m => ms(m.latency.p50)], cost: ['Cheapest', m => m.costPer1k, 1, m => money(m.costPer1k)]};
function LeaderList({runs, cases}) {
  const [key, setKey] = useState('accuracy'), box = useRef(null), [, val, dir, show] = BY[key];
  const metrics = runs.map(r => [r, B.subsetMetrics(r, cases)]), all = metrics.map(([, m]) => m);
  const sorted = metrics.slice().sort(([, a], [, b]) => { const va = val(a), vb = val(b); if (va == null) return 1; if (vb == null) return -1; return dir * (va - vb) || b.accuracy - a.accuracy; });
  const los = metrics.flatMap(([, m]) => m.wilson || []), [d0] = los.length ? zoomDomain(los, .1) : [0], cx = v => `${(v - d0) / (1 - d0 || 1) * 100}%`;
  useSettle(box, key);
  const others = m => Object.entries(BY).filter(([k]) => k !== key).map(([k, [, , , f]]) => `${f(m)}${k === 'cost' ? ' / 1k' : ''}`).join(' · ');
  return <>
    <SegmentedControl aria-label="Sort the leaderboard" value={key} onValueChange={v => { track('ui_click', {control: 'leaderboard_sort', sort: v}); haptic(); setKey(v); }} className="mb-3">
      <SegmentedList aria-label="Sort the leaderboard" className="h-10 w-full rounded-xl">{Object.entries(BY).map(([k, [t]]) => <SegmentedOption key={k} value={k} className="rounded-[9px]">{t}</SegmentedOption>)}</SegmentedList>
    </SegmentedControl>
    <div ref={box}><List>
      {sorted.map(([r, m], i) => { const k = B.keyOf(r), id = B.ident(r), ci = m.wilson;
        return <Item key={r.id} data-flip={r.id} href={modelHref(k)} chevron={false}
          lead={<><span className="w-5 text-center text-[13px] text-muted-foreground tabular-nums">{key === 'accuracy' ? B.rankOf(m, all) : i + 1}</span><Logo k={k} size={30} className="ml-2 rounded-lg" /></>}
          title={id.name} sub={<>{id.iface && id.iface !== 'API' && <>{id.iface} · </>}{others(m)}</>}
          trail={<span className="flex flex-col items-end gap-1.5">
            <span className="text-[15px] font-semibold tabular-nums">{show(m)}</span>
            {key === 'accuracy' && ci && <span className="relative block h-1.5 w-14" aria-hidden="true"><i className="absolute inset-x-0 top-[2.5px] h-px bg-border" /><i className="absolute top-0.5 h-0.5 rounded-full bg-foreground/25" style={{left: cx(ci[0]), width: `calc(${cx(ci[1])} - ${cx(ci[0])})`}} /><b className="absolute top-0 h-1.5 w-[3px] -translate-x-1/2 rounded-[1px]" style={{left: cx(m.accuracy), background: B.runColor(r)}} /></span>}
          </span>} />; })}
    </List></div>
    <Notes items={[key === 'accuracy' && 'Overlapping 95% intervals share a rank.', B.PARTIAL.length > 0 && `Partial, not ranked: ${B.PARTIAL.map(r => B.ident(r).short).join(', ')}.`, 'Tap a model for its fit by use case.']} />
  </>;
}

function Headline({runs, cases}) {
  const metrics = runs.map(r => [r, B.subsetMetrics(r, cases)]).filter(([, m]) => m.questions).sort(([, a], [, b]) => b.accuracy - a.accuracy);
  const acc = metrics.map(([r, m]) => ({key: B.keyOf(r), color: B.runColor(r), value: m.accuracy, lo: m.wilson[0], hi: m.wilson[1], tip: tip(B.runName(r), [['Accuracy', pct(m.accuracy)], ['95% interval', ciText(m.wilson)]])}));
  const lat = metrics.map(([r, m]) => ({key: B.keyOf(r), color: B.runColor(r), value: m.latency.p50 == null ? null : m.latency.p50 / 1000, tick: m.latency.p95 == null ? null : m.latency.p95 / 1000, tip: tip(B.runName(r), [['Median', ms(m.latency.p50)], ['p95', ms(m.latency.p95)]])}));
  const cost = metrics.map(([r, m]) => m.costCoverage === 1 && m.costPer1k != null ? {key: B.keyOf(r), color: B.runColor(r), value: m.costPer1k, tip: tip(B.runName(r), [['$ / 1k rows', money(m.costPer1k)]])} : {key: B.keyOf(r), value: null, ghost: m.costPer1k == null ? 'unknown' : 'partly known', tip: tip(B.runName(r), [['Known subtotal', `${money(m.costPer1k)} / 1k`], ['Cost coverage', pct(m.costCoverage)]])});
  const [lo] = zoomDomain(acc.map(a => a.lo), .1);
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <ChartCard title="Accuracy" description="Whiskers: Wilson 95% interval."><RowsChart items={acc} fmt={pct} tickFmt={pct0} max={1} min={lo} label="Accuracy by model" /></ChartCard>
      <ChartCard title="Latency per row" description="Bar: median. Tick: 95th percentile. CLI runs include process start-up."><RowsChart items={lat} fmt={secs} tickFmt={v => v === 0 ? '0' : secs(v)} label="Median latency by model" /></ChartCard>
      <ChartCard title="Cost per 1,000 rows" description="USD, provider-reported or estimated from list prices."><RowsChart items={cost} fmt={money} tickFmt={v => v === 0 ? '$0' : `$${v < 1 ? v.toFixed(2) : v.toFixed(v < 10 ? 1 : 0)}`} label="Cost per 1,000 rows by model" /></ChartCard>
    </div>
  );
}

function Tradeoffs({runs, cases}) {
  const metrics = runs.map(r => [r, B.subsetMetrics(r, cases)]).filter(([, m]) => m.questions);
  const pt = (r, m, xv, extra) => ({key: B.keyOf(r), color: B.runColor(r), x: xv, y: m.accuracy, lo: m.wilson[0], hi: m.wilson[1], tip: tip(B.runName(r), [['Accuracy', pct(m.accuracy)], ['95% interval', ciText(m.wilson)], ...extra])});
  const lat = metrics.filter(([, m]) => m.latency.p50).map(([r, m]) => pt(r, m, m.latency.p50 / 1000, [['Median latency', ms(m.latency.p50)]]));
  const ok = metrics.filter(([, m]) => m.costCoverage === 1 && m.costPer1k > 0), ex = metrics.filter(x => !ok.includes(x));
  const cost = ok.map(([r, m]) => pt(r, m, m.costPer1k, [['$ / 1k rows', money(m.costPer1k)]]));
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ChartCard title="Accuracy against latency" description="Up and to the left is better. Log scale; vertical lines are 95% intervals."><Scatter items={lat} xFmt={secs} xLabel="Median seconds per row" label="Accuracy against median latency" /></ChartCard>
      <ChartCard title="Accuracy against cost" description="Up and to the left is better. Log scale; vertical lines are 95% intervals." foot={ex.length ? `Not plotted (cost unknown or partial): ${ex.map(([r]) => B.ident(r).short).join(', ')}.` : ''}><Scatter items={cost} xFmt={v => `$${v < .1 ? v.toFixed(3) : v < 1 ? v.toFixed(2) : v.toFixed(v < 10 ? 1 : 0)}`} xLabel="USD per 1,000 rows" label="Accuracy against cost" /></ChartCard>
    </div>
  );
}

function HardestRows({cases}) {
  const items = cases.map(c => ({c, st: B.caseStats(c)})).filter(x => x.st.n >= 2 && x.st.ok < x.st.n).sort((a, b) => (b.st.n - b.st.ok) / b.st.n - (a.st.n - a.st.ok) / a.st.n || b.st.n - a.st.n).slice(0, 12);
  if (!items.length) return <p className="text-sm text-muted-foreground">Every evaluated model agrees with every answer key in this selection.</p>;
  return <>
    <List className="md:hidden">{items.map(({c, st}) => <Item key={c.id} href={rowHref(c)} wrap title={B.caseTitle(c)} sub={`${B.taskName(c.task)} · key: ${B.goldText(c)}`}
      trail={<span className="text-[13px] whitespace-nowrap text-muted-foreground tabular-nums"><span className="font-medium text-foreground">{st.ok}</span>/{st.n}</span>} />)}</List>
    <div className="overflow-hidden rounded-xl border bg-card shadow-xs max-md:hidden"><div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead><tr className="border-b text-left text-[13px] text-muted-foreground"><th className="h-10 pl-5 font-medium">Row</th><th className="px-3 font-medium">Task</th><th className="px-3 font-medium">Answer key</th><th className="px-3 font-medium">Models answered</th><th className="pr-5 text-right font-medium">Models right</th></tr></thead>
        <tbody>{items.map(({c, st}) => (
          <tr key={c.id} onClick={e => { if (!e.target.closest('a')) location.hash = rowHref(c); }} className="cursor-pointer border-b transition-colors last:border-0 hover:bg-muted/40">
            <td className="max-w-[360px] py-2.5 pl-5"><a href={rowHref(c)} className="line-clamp-2 font-medium hover:underline">{B.caseTitle(c)}</a></td>
            <td className="px-3 py-2.5 text-muted-foreground">{B.taskName(c.task)}</td>
            <td className="px-3 py-2.5"><Badge variant="good">{B.goldText(c)}</Badge></td>
            <td className="px-3 py-2.5 text-muted-foreground">{Object.entries(st.wrong).sort((a, b) => b[1] - a[1]).map(([l, n]) => `${n}× ${l === 'null' ? 'no answer' : l.replaceAll('_', ' ')}`).join(', ')}</td>
            <td className="py-2.5 pr-5 text-right"><Strip st={st} /></td>
          </tr>))}</tbody>
      </table>
    </div></div>
  </>;
}
export const Strip = ({st}) => st.n ? <span className="inline-flex items-center gap-2 whitespace-nowrap"><span className="tabular-nums">{st.ok}/{st.n}</span><span className="inline-flex gap-0.5" aria-hidden="true">{st.dots.map(d => <i key={d.k} title={`${B.fullName(d.k)}: ${d.ok ? 'correct' : 'wrong'}`} className={cn('h-2.5 w-[5px] rounded-[1px]', d.ok ? 'bg-good/40' : 'bg-bad')} />)}</span></span> : <Dash />;

function Coverage() {
  return <div className="grid gap-x-8 gap-y-6 md:grid-cols-2 lg:grid-cols-3">{B.categoryOrder().map(k => <div key={k}>
    <h3 className="text-sm font-semibold"><a href={catHref(k)} className="hover:underline">{B.catInfo(k).name}</a></h3>
    <p className="mt-0.5 mb-2 text-xs text-muted-foreground">{B.catInfo(k).description}</p>
    {B.taskOrder().filter(t => B.taskCat(t) === k).map(t => <a key={t} href={taskHref(t)} className="flex justify-between gap-3 border-b py-2 text-sm hover:bg-muted/40"><span className="font-medium">{B.taskName(t)}</span><span className="text-muted-foreground tabular-nums">{B.taskRows(t).length} rows</span></a>)}
  </div>)}</div>;
}

export function Home({route}) {
  const cases = scopeCases(route), runs = B.evaluated(selectedRuns(route), cases), cat = route.q.get('category') || '';
  return <>
    <Banner route={route} />
    <div className="mx-auto max-w-[1240px] px-4 pb-20 md:px-8">
      {cat && <div className="pt-8 md:pt-10"><div className="text-sm font-medium text-muted-foreground">Use case</div><h2 className="mt-1 text-2xl font-semibold tracking-tight md:text-3xl">{B.catInfo(cat).name}</h2><p className="mt-2 text-[15px] text-muted-foreground">{B.catInfo(cat).description} <Link href={href('tasks', {category: cat})}>See the tasks</Link></p></div>}
      {/* Sticky under the top bar; on phones one line of chips that scrolls sideways. */}
      <div className="sticky top-[calc(env(safe-area-inset-top)+48px)] z-30 -mx-4 flex items-center gap-2 overflow-x-auto bg-background/85 px-4 py-2.5 backdrop-blur-md [scrollbar-width:none] md:-mx-8 md:mt-6 md:flex-wrap md:overflow-visible md:px-8 md:py-3 lg:top-14">
        <UseCaseSelect route={route} className="shrink-0 md:min-w-44" />
        {B.allCases.some(c => B.isImageTask(c.task)) && <div className="shrink-0 max-md:order-last"><ModalityTabs route={route} /></div>}
        {B.RUNS.length > 0 && <ModelPicker route={route} />}
        <span className="ml-auto text-[13px] text-muted-foreground tabular-nums max-md:hidden">{plural(cases.length, 'row')} · {new Set(cases.map(c => c.task)).size} tasks</span>
      </div>
      {!B.hasResults() ? <>
        <Section title="Leaderboard"><Notice>No model has been evaluated on this version yet. <HowToAdd /></Notice></Section>
        <Section title="What the bench covers" description={`${plural(B.allCases.length, 'row')} in ${B.taskOrder().length} tasks. Open a task to read its rows.`}><Coverage /></Section>
      </> : !runs.length ? <Section title="Leaderboard"><Notice>No selected model has results on these rows.</Notice></Section> : <>
        <LeaderboardSection route={route} runs={runs} cases={cases} />
        <Section title="Accuracy, speed and cost"><Headline runs={runs} cases={cases} /></Section>
        <Section title="Accuracy by task" description={<>Only misses are coloured; faded cells are at or above 95%. Open a task for its rows.<span className="md:hidden"> Scroll sideways for every model.</span></>}><HeatTasks runs={runs} cases={cases} /></Section>
        <Section title="Trade-offs"><Tradeoffs runs={runs} cases={cases} /></Section>
        {/* Hover-driven and 1,000 columns wide: desktop and tablet only. */}
        <Section title="Every row" className="max-md:hidden" description="Each column is one row, in the same position for every model. Hover for the row; click to open it.">
          <div className="rounded-xl border bg-card p-5 shadow-xs">
            <Legend items={[['cell', 'var(--grid-ok)', 'Correct'], ['cell', 'var(--bad)', 'Wrong'], ['hatch', '', 'No valid answer'], ['box', 'var(--border)', 'Not run'], ['bar', 'var(--bad)', 'Bar: how many models got the row wrong']]} />
            <RecordGrid runs={runs.slice().sort((a, b) => B.subsetMetrics(b, cases).accuracy - B.subsetMetrics(a, cases).accuracy)} cases={cases} />
          </div>
        </Section>
        <Section title="Where models disagree with the answer key" description="Rows most models get wrong. Either the models are weak here, or the key deserves a second look; each row page links to the source record."><HardestRows cases={cases} /></Section>
      </>}
    </div>
  </>;
}
export {HowToAdd, Link};
