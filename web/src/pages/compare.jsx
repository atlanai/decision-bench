import {useEffect, useMemo, useState} from 'react';
import {CheckIcon, PlusIcon, XIcon} from 'lucide-react';
import * as B from '@/lib/bench';
import {pct, pct0, pp, num, plural, ms} from '@/lib/format';
import {href, go, withQ, taskHref, rowHref} from '@/lib/route';
import {cn} from '@/lib/utils';
import {EmptyPage, ModelName} from '@/components/common';
import {CopyButton} from '@/components/record';
import {RecordGrid, Legend, SLOTS, Mark} from '@/components/charts';
import {Button} from '@/components/ui/button';
import {Tip} from '@/components/ui/tooltip';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {SegmentedControl, SegmentedList, SegmentedOption} from '@/components/ui/segmented-control';
import {PixelBanner, UseCaseRadar} from '@/pages/home';

const LABEL = 'font-mono text-[10px] tracking-[.08em] text-muted-foreground uppercase sm:text-[11px]';
const VIEWS = [['split', 'They differ'], ['wrong', 'All wrong'], ['all', 'All rows']];
const PAGE = 24;

const pickHref = (route, keys) => withQ(route, {m: keys.join(','), a: '', b: ''});
const toRows = () => document.getElementById('rows')?.scrollIntoView({behavior: 'smooth', block: 'start'});
const accuracyOn = (rows, i) => rows.length ? rows.filter(x => x.oks[i]).length / rows.length : null;

function ModelSelect({value, taken, onChange, placeholder, className}) {
  return <Select value={value} onValueChange={onChange}>
    <SelectTrigger aria-label={placeholder || 'Model'} className={cn('h-9 min-w-0 flex-1 border-none bg-transparent px-1 shadow-none hover:bg-muted/60 dark:bg-transparent', className)}>{value ? <ModelName k={value} link={false} /> : <SelectValue placeholder={placeholder} />}</SelectTrigger>
    <SelectContent className="max-h-96">{B.RUNS.map(B.keyOf).filter(k => k === value || !taken.includes(k)).map(k => <SelectItem key={k} value={k}><ModelName k={k} link={false} /></SelectItem>)}</SelectContent>
  </Select>;
}

/* One card per picked model: its slot colour and marker, overall accuracy, and how it did on the shared rows. */
function ModelCard({route, keys, i, run, rows}) {
  const m = B.subsetMetrics(run, B.allCases), wrong = rows.filter(x => !x.oks[i]).length, alone = rows.filter(x => x.oks[i] && x.oks.filter(Boolean).length === 1).length;
  const stat = (label, value, title) => <div title={title} className="min-w-0"><dd className="font-mono text-lg font-medium tabular-nums">{value}</dd><dt className={LABEL}>{label}</dt></div>;
  return <div className="relative overflow-hidden rounded-xl border bg-card/90 p-4 pt-5 shadow-xs backdrop-blur-sm">
    <i aria-hidden="true" className="absolute inset-x-0 top-0 h-1" style={{background: SLOTS[i][0]}} />
    <div className="flex items-center gap-1.5">
      <Mark slot={i} />
      <ModelSelect value={keys[i]} taken={keys} onChange={k => go(pickHref(route, keys.map((x, j) => j === i ? k : x)))} />
      {keys.length > 2 && <Button variant="ghost" size="icon-sm" data-track="compare_remove" aria-label={`Remove ${B.ident(run).name}`} onClick={() => go(pickHref(route, keys.filter((_, j) => j !== i)))}><XIcon /></Button>}
    </div>
    <div className="mt-5 font-pixel text-5xl leading-none tabular-nums">{pct(m.accuracy)}</div>
    <div className={cn(LABEL, 'mt-2')}>Accuracy · #{B.positionOf(m, B.RUNS.map(r => B.subsetMetrics(r, B.allCases)))} of {B.RUNS.length}</div>
    <dl className="mt-5 grid grid-cols-3 gap-3 border-t pt-3">
      {stat('Wrong', num(wrong), `Rows it got wrong, of the ${num(rows.length)} every picked model was scored on`)}
      {stat(keys.length === 2 ? 'Only it right' : 'Alone right', num(alone), 'Rows it got right while every other picked model got wrong')}
      {stat('Median', ms(m.latency.p50), 'Median time per row')}
    </dl>
  </div>;
}

function AddCard({route, keys}) {
  return <div className="flex min-h-48 flex-col items-center justify-center gap-3 rounded-xl border border-dashed bg-card/60 p-4 text-center backdrop-blur-sm">
    <PlusIcon className="size-5 text-muted-foreground" />
    <ModelSelect taken={keys} placeholder="Add a model" onChange={k => go(pickHref(route, [...keys, k]))} className="w-full max-w-60 flex-none justify-center border-solid border-input bg-background dark:bg-input/30" />
    <span className="text-xs text-muted-foreground">Up to {B.MAX_PICKS} models</span>
  </div>;
}

/* The shared rows split three ways; each part opens its rows below. */
function Agreement({route, rows}) {
  const n = {right: 0, split: 0, wrong: 0};
  for (const x of rows) n[x.kind]++;
  const parts = [['right', 'all', 'All right', 'var(--grid-ok)'], ['split', 'split', 'They differ', 'var(--brand)'], ['wrong', 'wrong', 'All wrong', 'var(--bad)']];
  return <div className="mt-3 rounded-xl border bg-card/90 p-4 shadow-xs backdrop-blur-sm">
    <div className="flex h-2.5 gap-0.5 overflow-hidden rounded-full">{parts.map(([k, , , c]) => n[k] > 0 && <i key={k} style={{width: `${n[k] / rows.length * 100}%`, background: c}} />)}</div>
    <div className="mt-4 grid grid-cols-3 gap-3">{parts.map(([k, view, label, c]) => <button key={k} type="button" data-track="compare_agreement" onClick={() => { go(withQ(route, {view: view === 'split' ? '' : view})); toRows(); }} className="group cursor-pointer rounded-md text-left">
      <div className="font-pixel text-3xl leading-none tabular-nums sm:text-4xl">{num(n[k])}</div>
      <div className={cn(LABEL, 'mt-2 flex items-center gap-1.5 group-hover:text-foreground')}><i className="size-2 shrink-0 rounded-[2px]" style={{background: c}} />{label}<span className="max-sm:hidden">· {pct0(rows.length ? n[k] / rows.length : null)}</span></div>
    </button>)}</div>
  </div>;
}

function Hero({route, keys, runs, rows}) {
  return <PixelBanner>
      <div className="relative mx-auto max-w-[1600px] px-4 pt-8 pb-10 md:px-8 md:pt-14 md:pb-12">
        <p className="mb-4 font-mono text-[11px] tracking-[.08em] text-muted-foreground uppercase md:mb-5">Compare · same rows, same prompt · {num(rows.length)} rows</p>
        <h1 className="max-w-[20ch] font-pixel text-4xl leading-[1.02] uppercase sm:text-5xl lg:text-[52px]">Where does each model <em className="text-brand not-italic">get it wrong</em>?</h1>
        <p className="mt-5 max-w-[60ch] text-base leading-relaxed text-foreground/75">Pick up to {B.MAX_PICKS} models. See where they agree, which rows split them, and what each one answered against the answer key.</p>
        <div className="mt-8 mb-2 flex items-center justify-between gap-3">
          <span className={LABEL}>{keys.length} of {B.MAX_PICKS} models</span>
          <CopyButton text={`${location.origin}${href('compare', {m: keys.join(',')})}`} label="Copy link to this comparison" />
        </div>
        <div data-no-trail className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {runs.map((r, i) => <ModelCard key={r.id} route={route} keys={keys} i={i} run={r} rows={rows} />)}
          {keys.length < B.MAX_PICKS && <AddCard route={route} keys={keys} />}
        </div>
        <div data-no-trail><Agreement route={route} rows={rows} /><Verdicts runs={runs} /></div>
      </div>
  </PixelBanner>;
}

/* Each pair's verdict, from the paired bootstrap behind the leaderboard's rank range. One pair takes over 100 ms, so
   they are worked out one at a time after the page has painted. */
function usePairs(runs) {
  const key = runs.map(r => r.id).join(), [got, setGot] = useState({key: null, gaps: new Map()});
  useEffect(() => {
    const pairs = runs.flatMap((a, i) => runs.slice(i + 1).map((b, j) => [i, i + 1 + j]));
    let gaps = new Map(), t;
    const step = k => {
      if (k >= pairs.length) return;
      const [i, j] = pairs[k];
      gaps = new Map(gaps).set(`${i}-${j}`, B.pairGap(B.RUNS, B.allCases, runs[i].id, runs[j].id));
      setGot({key, gaps});
      t = setTimeout(() => step(k + 1), 0);
    };
    t = setTimeout(() => step(0), 0);
    return () => clearTimeout(t);
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps
  return got.key === key ? got.gaps : new Map();
}

function Verdicts({runs}) {
  const gaps = usePairs(runs), others = B.evaluated(B.RUNS, B.allCases).length - 1;
  const pairs = runs.flatMap((_, i) => runs.slice(i + 1).map((__, j) => [i, i + 1 + j]));
  return <div className="mt-6">
    <div className="mb-2 flex items-center justify-between gap-3">
      <span className={LABEL}>{pairs.length === 1 ? 'Verdict' : 'Verdict, pair by pair'}</span>
      <Tip content={`Each pair on the rows both were scored on. A model is ahead only when the gap holds at 95% confidence, adjusted for comparing each model with the other ${num(others)}; otherwise the pair is too close to call.`}><span tabIndex={0} className="cursor-help text-xs text-muted-foreground underline decoration-dotted underline-offset-4">How is this decided?</span></Tip>
    </div>
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{pairs.map(([i, j]) => {
      const a = runs[i], b = runs[j], g = gaps.get(`${i}-${j}`), lead = g?.call === 'ahead' ? i : g?.call === 'behind' ? j : null;
      const cmp = (B.data.comparisons || []).find(p => (p.a === a.id && p.b === b.id) || (p.a === b.id && p.b === a.id));
      const ci = cmp?.cluster_bootstrap_ci95 && !B.subsetMetrics(a, B.allCases).excluded && !B.subsetMetrics(b, B.allCases).excluded ? (cmp.a === a.id ? cmp.cluster_bootstrap_ci95 : [-cmp.cluster_bootstrap_ci95[1], -cmp.cluster_bootstrap_ci95[0]]) : null;
      return <div key={`${a.id}|${b.id}`} className="rounded-xl border bg-card/90 p-4 shadow-xs backdrop-blur-sm">
        <div className="flex min-w-0 items-center gap-2 text-sm font-medium"><Mark slot={i} /><span className="truncate">{B.ident(a).short}</span><span className="text-muted-foreground">vs</span><Mark slot={j} /><span className="truncate">{B.ident(b).short}</span></div>
        {!g ? <p className="mt-3 text-sm text-muted-foreground">Working out the verdict…</p> : <>
          <div className="mt-3 font-pixel text-2xl leading-tight uppercase" style={lead == null ? undefined : {color: SLOTS[lead][0]}}>{lead == null ? 'Too close to call' : `${B.ident(runs[lead]).short} ahead`}</div>
          <p className="mt-2 text-xs leading-relaxed text-muted-foreground">Only {B.ident(a).short} right on {plural(g.wins, 'row')}, only {B.ident(b).short} on {num(g.losses)}, of {num(g.rows)}. Gap {pp(g.gap)} pp{g.lo == null ? '; too few rows for an interval' : `, 95% interval ${pp(g.lo)} to ${pp(g.hi)}`}.{ci && ` On new tasks: ${pp(ci[0])} to ${pp(ci[1])}.`}</p>
        </>}
      </div>; })}</div>
  </div>;
}

/* One row: the answer key, then each model's answer, whether it was right, and how sure it said it was. */
function AnswerCard({x, runs}) {
  const {c, vs, oks} = x;
  return <li className="flex flex-col rounded-xl border bg-card p-4 shadow-xs">
    <div className="flex justify-between gap-3 text-xs text-muted-foreground"><a href={taskHref(c.task)} className="truncate hover:text-foreground">{B.taskName(c.task)}</a><span className="shrink-0">{B.catInfo(B.catKey(c)).name}</span></div>
    <a href={rowHref(c)} className="mt-1 line-clamp-2 font-medium hover:underline">{B.caseTitle(c)}</a>
    <div className="mt-3 flex items-baseline gap-2 rounded-md bg-muted/60 px-3 py-2 text-sm"><span className={cn(LABEL, 'shrink-0')}>Answer key</span><span className="min-w-0 truncate font-medium">{B.goldText(c)}</span></div>
    <ul className="mt-1 divide-y">{runs.map((r, i) => { const v = vs[i], s = v.scores[0];
      return <li key={r.id} className="flex items-center gap-2 py-2 text-sm">
        <Mark slot={i} /><span className="w-24 shrink-0 truncate text-muted-foreground sm:w-32">{B.ident(r).short}</span>
        {oks[i] ? <CheckIcon aria-label="Right" className="size-4 shrink-0 text-good" /> : <XIcon aria-label="Wrong" className="size-4 shrink-0 text-bad" />}
        <span className={cn('min-w-0 flex-1 truncate', !oks[i] && 'text-bad')}>{B.answered(v) ? B.optText(c, s.label) : B.answerOf(v)}</span>
        {s?.confidence != null && <span className="shrink-0 text-xs text-muted-foreground tabular-nums" title="How sure the model said it was">{pct0(s.confidence)} sure</span>}
      </li>; })}</ul>
  </li>;
}

/* The rows in view: one task, one use case, or all, then all rows, the rows the models differ on, or the rows all got wrong. */
function useScope(route, rows) {
  const task = B.taskOrder().includes(route.q.get('task')) ? route.q.get('task') : '';
  const cat = !task && B.categoryOrder().includes(route.q.get('category')) ? route.q.get('category') : '';
  const view = VIEWS.some(([k]) => k === route.q.get('view')) ? route.q.get('view') : 'split';
  const inScope = useMemo(() => rows.filter(x => task ? x.c.task === task : !cat || B.catKey(x.c) === cat), [rows, task, cat]);
  const ofView = rs => view === 'all' ? rs : rs.filter(x => x.kind === view);
  return {task, cat, view, inScope, ofView};
}

/* Use cases and their tasks, each with how many of its rows are in the current view. Empty ones are left out, except
   the picked task, so a pick never vanishes from the list. */
function navTree(rows, ofView, task) {
  return B.categoryOrder().map(k => {
    const tasks = B.taskOrder().filter(t => B.taskCat(t) === k).map(t => ({t, n: ofView(rows.filter(x => x.c.task === t)).length})).filter(x => x.n || x.t === task);
    return {k, n: tasks.reduce((s, x) => s + x.n, 0), tasks};
  }).filter(g => g.tasks.length);
}

function NavItem({on, n, onClick, sub, children}) {
  return <button type="button" aria-current={on || undefined} data-track="compare_scope" onClick={onClick} className={cn('flex w-full cursor-pointer items-center justify-between gap-3 rounded-md px-3 py-1.5 text-left text-sm transition-colors hover:bg-muted/60', sub ? 'pl-6 text-muted-foreground hover:text-foreground' : 'font-medium', on && 'bg-brand-soft text-brand hover:bg-brand-soft hover:text-brand')}>
    <span className="min-w-0 truncate">{children}</span><span className={cn('shrink-0 text-xs tabular-nums', !on && 'text-muted-foreground')}>{num(n)}</span>
  </button>;
}

function Explorer({route, runs, rows}) {
  const {task, cat, view, inScope, ofView} = useScope(route, rows);
  const shown = useMemo(() => ofView(inScope), [inScope, view]); // eslint-disable-line react-hooks/exhaustive-deps
  const cases = useMemo(() => shown.map(x => x.c), [shown]);
  const tree = navTree(rows, ofView, task), total = tree.reduce((s, g) => s + g.n, 0);
  const scope = patch => go(withQ(route, {task: '', category: '', ...patch}));
  const pickValue = task ? `t:${task}` : cat ? `c:${cat}` : 'all';
  const [limit, setLimit] = useState({key: '', n: PAGE}), key = `${runs.map(r => r.id)}|${pickValue}|${view}`, n = limit.key === key ? limit.n : PAGE;
  return <section id="rows" className="mt-10 scroll-mt-28 md:mt-14 lg:scroll-mt-20">
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        <h2 className="text-lg font-semibold tracking-tight">Row by row</h2>
        <p className="mt-1 max-w-3xl text-sm text-pretty text-muted-foreground">Pick a use case or a task to see its rows. Each column of the grid is one row; hover a cell for the answers and click it to open the row.</p>
      </div>
      <SegmentedControl aria-label="Rows to show" value={view} onValueChange={v => go(withQ(route, {view: v === 'split' ? '' : v}))}>
        <SegmentedList>{VIEWS.map(([k, label]) => <SegmentedOption key={k} value={k} data-track="compare_view">{label} <span className="text-xs text-muted-foreground tabular-nums">{num(k === 'all' ? inScope.length : inScope.filter(x => x.kind === k).length)}</span></SegmentedOption>)}</SegmentedList>
      </SegmentedControl>
    </div>
    <div className="grid items-start gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
      <nav aria-label="Use cases and tasks" className="overflow-y-auto overscroll-contain rounded-xl border bg-card p-1.5 shadow-xs max-lg:hidden lg:sticky lg:top-20 lg:max-h-[calc(100dvh-6rem)]">
        <NavItem on={!task && !cat} n={total} onClick={() => scope({})}>All tasks</NavItem>
        {tree.map(g => <div key={g.k} className="mt-1.5 border-t pt-1.5">
          <NavItem on={cat === g.k} n={g.n} onClick={() => scope({category: g.k})}>{B.catInfo(g.k).name}</NavItem>
          {g.tasks.map(x => <NavItem key={x.t} sub on={task === x.t} n={x.n} onClick={() => scope({task: x.t})}>{B.taskName(x.t)}</NavItem>)}
        </div>)}
      </nav>
      <div className="min-w-0">
        <div className="mb-3 rounded-xl border bg-card p-4 shadow-xs">
          <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
            <div className="min-w-0">
              <div className={LABEL}>{task ? B.catInfo(B.taskCat(task)).name : cat ? 'Use case' : 'Showing'}</div>
              <div className="mt-0.5 flex items-center gap-2 text-base font-semibold">{task ? <a href={taskHref(task)} className="hover:underline">{B.taskName(task)}</a> : cat ? B.catInfo(cat).name : 'All tasks'}</div>
            </div>
            <Select value={pickValue} onValueChange={v => scope(v === 'all' ? {} : v.startsWith('t:') ? {task: v.slice(2)} : {category: v.slice(2)})}>
              <SelectTrigger aria-label="Use case or task" className="w-full lg:hidden"><SelectValue /></SelectTrigger>
              <SelectContent className="max-h-96">
                <SelectItem value="all">All tasks · {num(total)}</SelectItem>
                {tree.flatMap(g => [<SelectItem key={g.k} value={`c:${g.k}`} className="font-medium">{B.catInfo(g.k).name} · {num(g.n)}</SelectItem>,
                  ...g.tasks.map(x => <SelectItem key={x.t} value={`t:${x.t}`} className="pl-5 text-muted-foreground">{B.taskName(x.t)} · {num(x.n)}</SelectItem>)])}
              </SelectContent>
            </Select>
          </div>
          <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-2 border-t pt-3">{runs.map((r, i) => <div key={r.id} className="flex items-center gap-2 text-sm">
            <Mark slot={i} /><dt className="text-muted-foreground">{B.ident(r).short}</dt><dd className="font-mono font-medium tabular-nums">{pct(accuracyOn(inScope, i))}</dd>
          </div>)}<span className="self-center text-xs text-muted-foreground">on {plural(inScope.length, 'row')}</span></dl>
        </div>
        {!shown.length ? <p className="rounded-xl border bg-card p-6 text-sm text-muted-foreground">No rows here{view === 'split' ? ': these models agree on every row' : ''}.</p> : <>
          <div className="rounded-xl border bg-card p-4 shadow-xs">
            <Legend items={[['cell', 'var(--grid-ok)', 'Correct'], ['cell', 'var(--bad)', 'Wrong'], ['hatch', '', 'No valid answer'], ['bar', 'var(--bad)', 'Bar: how many picked models got the row wrong']]} />
            <RecordGrid runs={runs} cases={cases} marks />
          </div>
          <ul className="mt-3 grid gap-3 xl:grid-cols-2">{shown.slice(0, n).map(x => <AnswerCard key={x.c.id} x={x} runs={runs} />)}</ul>
          {shown.length > n && <div className="mt-4 flex justify-center"><Button variant="outline" data-track="compare_more" onClick={() => setLimit({key, n: n + PAGE * 2})}>Show {num(Math.min(PAGE * 2, shown.length - n))} more of {num(shown.length - n)}</Button></div>}
        </>}
      </div>
    </div>
  </section>;
}

export function Compare({route}) {
  const ids = B.RUNS.map(B.keyOf), keys = B.pickKeys(route.q, ids), id = keys.join();
  const runs = useMemo(() => keys.map(k => B.RUNS.find(r => B.keyOf(r) === k)), [id]); // eslint-disable-line react-hooks/exhaustive-deps
  const rows = useMemo(() => B.splits(runs, B.allCases), [runs]);
  if (B.RUNS.length < 2) return <EmptyPage title="Compare models">Comparison needs at least two evaluated models.</EmptyPage>;
  return <>
    <Hero route={route} keys={keys} runs={runs} rows={rows} />
    <div className="mx-auto max-w-[1600px] px-4 pb-16 md:px-8 lg:pb-20">
      {runs.some(r => B.subsetMetrics(r, B.allCases).excluded) && <p className="mt-8 max-w-3xl rounded-lg border bg-muted/50 px-4 py-3 text-sm text-muted-foreground">Only rows with usable input for every picked model are compared. Image rows are left out when a model was not sent the image.</p>}
      <Explorer route={route} runs={runs} rows={rows} />
      <UseCaseRadar route={route} runs={B.RUNS} cases={B.allCases} start={keys} />
    </div>
  </>;
}
