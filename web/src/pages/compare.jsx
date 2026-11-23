import {useEffect, useMemo, useState} from 'react';
import {CheckIcon, PlusIcon, XIcon} from 'lucide-react';
import * as B from '@/lib/bench';
import {pct, pct0, pp, num, plural, ms} from '@/lib/format';
import {href, go, withQ, taskHref, rowHref} from '@/lib/route';
import {cn} from '@/lib/utils';
import {Section, EmptyPage, ModelName} from '@/components/common';
import {CopyButton} from '@/components/record';
import {Radar, RecordGrid, Legend, SLOTS, Mark, zoomDomain} from '@/components/charts';
import {tip} from '@/components/tip';
import {Button} from '@/components/ui/button';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';
import {SegmentedControl, SegmentedList, SegmentedOption} from '@/components/ui/segmented-control';
import {GRID} from '@/pages/home';
import {TableCard} from '@/pages/task';

const TH = 'h-10 px-3 text-left text-[13px] font-medium whitespace-nowrap text-muted-foreground first:pl-5 last:pr-5';
const TD = 'px-3 py-2.5 first:pl-5 last:pr-5 tabular-nums';
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
  return <div className={cn('border-b [--grid-line:var(--border)]', GRID)}>
    <div className="bg-gradient-to-b from-background/40 via-background/70 to-background">
      <div className="mx-auto max-w-[1600px] px-4 pt-8 pb-10 md:px-8 md:pt-14 md:pb-12">
        <p className="mb-4 font-mono text-[11px] tracking-[.08em] text-muted-foreground uppercase md:mb-5">Compare · same rows, same prompt · {num(rows.length)} rows</p>
        <h1 className="max-w-[20ch] font-pixel text-4xl leading-[1.02] uppercase sm:text-5xl lg:text-[52px]">Where does each model <em className="text-brand not-italic">get it wrong</em>?</h1>
        <p className="mt-5 max-w-[60ch] text-base leading-relaxed text-foreground/75">Pick up to {B.MAX_PICKS} models. See where they agree, which rows split them, and what each one answered against the answer key.</p>
        <div className="mt-8 mb-2 flex items-center justify-between gap-3">
          <span className={LABEL}>{keys.length} of {B.MAX_PICKS} models</span>
          <CopyButton text={`${location.origin}${href('compare', {m: keys.join(',')})}`} label="Copy link to this comparison" />
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {runs.map((r, i) => <ModelCard key={r.id} route={route} keys={keys} i={i} run={r} rows={rows} />)}
          {keys.length < B.MAX_PICKS && <AddCard route={route} keys={keys} />}
        </div>
        <Agreement route={route} rows={rows} />
      </div>
    </div>
  </div>;
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

function Pairs({runs}) {
  const gaps = usePairs(runs), others = B.evaluated(B.RUNS, B.allCases).length - 1;
  const pairs = runs.flatMap((_, i) => runs.slice(i + 1).map((__, j) => [i, i + 1 + j]));
  return <Section title={pairs.length === 1 ? 'Verdict' : 'Verdict, pair by pair'} description={`Each pair on the rows both were scored on. A model is ahead only when the gap holds at 95% confidence, adjusted for comparing each model with the other ${num(others)}; otherwise the pair is too close to call.`}>
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{pairs.map(([i, j]) => {
      const a = runs[i], b = runs[j], g = gaps.get(`${i}-${j}`), lead = g?.call === 'ahead' ? i : g?.call === 'behind' ? j : null;
      const cmp = (B.data.comparisons || []).find(p => (p.a === a.id && p.b === b.id) || (p.a === b.id && p.b === a.id));
      const ci = cmp?.cluster_bootstrap_ci95 && !B.subsetMetrics(a, B.allCases).excluded && !B.subsetMetrics(b, B.allCases).excluded ? (cmp.a === a.id ? cmp.cluster_bootstrap_ci95 : [-cmp.cluster_bootstrap_ci95[1], -cmp.cluster_bootstrap_ci95[0]]) : null;
      return <div key={`${a.id}|${b.id}`} className="rounded-xl border bg-card p-4 shadow-xs">
        <div className="flex min-w-0 items-center gap-2 text-sm font-medium"><Mark slot={i} /><span className="truncate">{B.ident(a).short}</span><span className="text-muted-foreground">vs</span><Mark slot={j} /><span className="truncate">{B.ident(b).short}</span></div>
        {!g ? <p className="mt-3 text-sm text-muted-foreground">Working out the verdict…</p> : <>
          <div className="mt-3 font-pixel text-2xl leading-tight uppercase" style={lead == null ? undefined : {color: SLOTS[lead][0]}}>{lead == null ? 'Too close to call' : `${B.ident(runs[lead]).short} ahead`}</div>
          <p className="mt-2 text-xs leading-relaxed text-muted-foreground">Only {B.ident(a).short} right on {plural(g.wins, 'row')}, only {B.ident(b).short} on {num(g.losses)}, of {num(g.rows)}. Gap {pp(g.gap)} pp{g.lo == null ? '; too few rows for an interval' : `, 95% interval ${pp(g.lo)} to ${pp(g.hi)}`}.{ci && ` On new tasks: ${pp(ci[0])} to ${pp(ci[1])}.`}</p>
        </>}
      </div>; })}</div>
  </Section>;
}

const shortCat = name => name.split(' & ')[0];
function UseCases({runs, rows}) {
  const cats = B.categoryOrder().filter(k => rows.some(x => B.catKey(x.c) === k));
  if (cats.length < 3) return null;
  const by = new Map(cats.map(k => [k, rows.filter(x => B.catKey(x.c) === k)]));
  const series = runs.map((r, i) => ({key: r.id, color: SLOTS[i][0], shape: SLOTS[i][1],
    values: cats.map(k => accuracyOn(by.get(k), i)),
    tips: cats.map(k => tip(`${B.runName(r)} · ${B.catInfo(k).name}`, [['Accuracy', pct(accuracyOn(by.get(k), i))], ['Rows', num(by.get(k).length)]]))}));
  const [min] = zoomDomain(series.flatMap(x => x.values), .1);
  return <Section title="By use case" description="Accuracy on the rows every picked model was scored on. The best model in each use case is in bold.">
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="rounded-xl border bg-card p-4 shadow-xs">
        <Radar axes={cats.map(k => ({key: k, name: shortCat(B.catInfo(k).name)}))} series={series} min={min} label="Accuracy by use case" />
        <p className="mt-3 text-xs text-muted-foreground">The scale starts at {pct0(min)}, not 0, so small gaps look large. Hover a point for its numbers.</p>
      </div>
      <TableCard label="Accuracy by use case"><table className="w-full text-sm">
        <thead><tr className="border-b"><th className={TH}>Use case</th>{runs.map((r, i) => <th key={r.id} className={cn(TH, 'text-right')}><span className="inline-flex items-center gap-1.5"><Mark slot={i} />{B.ident(r).short}</span></th>)}<th className={cn(TH, 'text-right')}>Differ</th></tr></thead>
        <tbody>{cats.map(k => { const rs = by.get(k), acc = runs.map((_, i) => accuracyOn(rs, i)), best = Math.max(...acc);
          return <tr key={k} className="border-b last:border-0">
            <td className="py-2.5 pr-3 pl-5 font-medium">{B.catInfo(k).name}</td>
            {acc.map((v, i) => <td key={i} className={cn(TD, 'text-right', v === best ? 'font-semibold' : 'text-muted-foreground')}>{pct(v)}</td>)}
            <td className={cn(TD, 'text-right')}>{num(rs.filter(x => x.kind === 'split').length)}</td>
          </tr>; })}</tbody>
      </table></TableCard>
    </div>
  </Section>;
}

function ByTask({route, runs, rows, task}) {
  const [every, setEvery] = useState(false);
  const all = B.taskOrder().map(t => ({t, rs: rows.filter(x => x.c.task === t)})).filter(x => x.rs.length);
  const differ = all.filter(x => x.t === task || x.rs.some(r => r.kind === 'split')), tasks = every ? all : differ;
  const pick = t => { go(withQ(route, {task: t === task ? '' : t})); toRows(); };
  return <Section title="By task" description={`The models differ on ${plural(differ.length, 'task')} of ${num(all.length)}. Click a task to see its rows below.`}
    actions={all.length > differ.length && <Button variant="outline" size="sm" data-track="compare_all_tasks" onClick={() => setEvery(!every)}>{every ? 'Only tasks where they differ' : `Show all ${num(all.length)} tasks`}</Button>}>
    <TableCard label="Accuracy by task"><table className="w-full text-sm">
      <thead><tr className="border-b"><th className={TH}>Task</th><th className={cn(TH, 'text-right')}>Rows</th>{runs.map((r, i) => <th key={r.id} className={cn(TH, 'text-right')}><span className="inline-flex items-center gap-1.5"><Mark slot={i} />{B.ident(r).short}</span></th>)}<th className={cn(TH, 'text-right')}>Differ</th></tr></thead>
      <tbody>{tasks.map(({t, rs}) => { const acc = runs.map((_, i) => accuracyOn(rs, i)), best = Math.max(...acc), split = rs.filter(x => x.kind === 'split').length;
        return <tr key={t} data-track="compare_task" onClick={e => { if (!e.target.closest('a')) pick(t); }} className={cn('cursor-pointer border-b last:border-0 hover:bg-muted/40', t === task && 'bg-brand-soft hover:bg-brand-soft', !split && 'text-muted-foreground')}>
          <td className="py-2.5 pr-3 pl-5"><a href={taskHref(t)} className={cn('font-medium hover:underline', split && 'text-foreground')}>{B.taskName(t)}</a><span className="block text-xs text-muted-foreground">{B.catInfo(B.taskCat(t)).name}</span></td>
          <td className={cn(TD, 'text-right text-muted-foreground')}>{rs.length}</td>
          {acc.map((v, i) => <td key={i} className={cn(TD, 'text-right', split && v === best ? 'font-semibold' : 'text-muted-foreground')}>{pct0(v)}</td>)}
          <td className={cn(TD, 'text-right font-medium')}>{split ? <span className="inline-flex min-w-7 justify-center rounded-full bg-brand-soft px-2 text-brand">{split}</span> : <span className="text-muted-foreground/50">0</span>}</td>
        </tr>; })}</tbody>
    </table></TableCard>
  </Section>;
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

function Rows({route, runs, rows, task}) {
  const view = VIEWS.some(([k]) => k === route.q.get('view')) ? route.q.get('view') : 'split';
  const inTask = useMemo(() => task ? rows.filter(x => x.c.task === task) : rows, [rows, task]);
  const count = k => k === 'all' ? inTask.length : inTask.filter(x => x.kind === k).length;
  const shown = useMemo(() => view === 'all' ? inTask : inTask.filter(x => x.kind === view), [inTask, view]);
  const cases = useMemo(() => shown.map(x => x.c), [shown]);
  const [limit, setLimit] = useState({key: '', n: PAGE}), key = `${runs.map(r => r.id)}|${task}|${view}`, n = limit.key === key ? limit.n : PAGE;
  return <Section id="rows" title="Row by row" description="Each column is one row, in the same place for every model. Hover a cell for the answers; click it to open the row."
    actions={<div className="flex flex-wrap items-center gap-2">
      {task && <Button variant="outline" size="sm" data-track="compare_task_clear" onClick={() => go(withQ(route, {task: ''}))}>{B.taskName(task)}<XIcon /></Button>}
      <SegmentedControl aria-label="Rows to show" value={view} onValueChange={v => go(withQ(route, {view: v === 'split' ? '' : v}))}>
        <SegmentedList>{VIEWS.map(([k, label]) => <SegmentedOption key={k} value={k} data-track="compare_view">{label} <span className="text-xs text-muted-foreground tabular-nums">{num(count(k))}</span></SegmentedOption>)}</SegmentedList>
      </SegmentedControl>
    </div>}>
    {!shown.length ? <p className="rounded-xl border bg-card p-6 text-sm text-muted-foreground">No rows here{view === 'split' ? ': these models agree on every row' : ''}.</p> : <>
      <div className="rounded-xl border bg-card p-4 shadow-xs">
        <Legend items={[['cell', 'var(--grid-ok)', 'Correct'], ['cell', 'var(--bad)', 'Wrong'], ['hatch', '', 'No valid answer'], ['bar', 'var(--bad)', 'Bar: how many picked models got the row wrong']]} />
        <RecordGrid runs={runs} cases={cases} marks />
      </div>
      <ul className="mt-4 grid gap-3 md:grid-cols-2 2xl:grid-cols-3">{shown.slice(0, n).map(x => <AnswerCard key={x.c.id} x={x} runs={runs} />)}</ul>
      {shown.length > n && <div className="mt-4 flex justify-center"><Button variant="outline" data-track="compare_more" onClick={() => setLimit({key, n: n + PAGE * 2})}>Show {num(Math.min(PAGE * 2, shown.length - n))} more of {num(shown.length - n)}</Button></div>}
    </>}
  </Section>;
}

export function Compare({route}) {
  const ids = B.RUNS.map(B.keyOf), keys = B.pickKeys(route.q, ids), id = keys.join();
  const runs = useMemo(() => keys.map(k => B.RUNS.find(r => B.keyOf(r) === k)), [id]); // eslint-disable-line react-hooks/exhaustive-deps
  const rows = useMemo(() => B.splits(runs, B.allCases), [runs]);
  if (B.RUNS.length < 2) return <EmptyPage title="Compare models">Comparison needs at least two evaluated models.</EmptyPage>;
  const task = B.taskOrder().includes(route.q.get('task')) ? route.q.get('task') : '';
  return <>
    <Hero route={route} keys={keys} runs={runs} rows={rows} />
    <div className="mx-auto max-w-[1600px] px-4 pb-16 md:px-8 lg:pb-20">
      {runs.some(r => B.subsetMetrics(r, B.allCases).excluded) && <p className="mt-8 max-w-3xl rounded-lg border bg-muted/50 px-4 py-3 text-sm text-muted-foreground">Only rows with usable input for every picked model are compared. Image rows are left out when a model was not sent the image.</p>}
      <Pairs runs={runs} />
      <UseCases runs={runs} rows={rows} />
      <ByTask route={route} runs={runs} rows={rows} task={task} />
      <Rows route={route} runs={runs} rows={rows} task={task} />
    </div>
  </>;
}
