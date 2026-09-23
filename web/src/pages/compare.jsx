import * as B from '@/lib/bench';
import {pp} from '@/lib/format';
import {href, go, taskHref} from '@/lib/route';
import {cn} from '@/lib/utils';
import {PageHeader, Section, Notice, ModelName} from '@/components/common';
import {List, ListHead, Item} from '@/components/list';
import {CopyButton} from '@/components/record';
import {TableCard} from '@/pages/task';
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select';

const TH = 'h-10 px-3 text-left text-[13px] font-medium whitespace-nowrap text-muted-foreground first:pl-5 last:pr-5';
const TD = 'px-3 py-2.5 first:pl-5 last:pr-5 tabular-nums';

function Pick({label, value, other, onChange}) {
  return <label className="flex flex-col gap-1.5 text-xs font-medium text-muted-foreground max-md:w-full">{label}
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="min-w-64 text-foreground max-md:h-11! max-md:w-full max-md:rounded-xl"><SelectValue /></SelectTrigger>
      <SelectContent>{B.RUNS.map(B.keyOf).filter(k => k !== other).map(k => <SelectItem key={k} value={k}><ModelName k={k} link={false} /></SelectItem>)}</SelectContent>
    </Select></label>;
}

export function Compare({route}) {
  if (B.RUNS.length < 2) return <><PageHeader title="Compare two models" /><Notice>Paired comparison needs at least two evaluated models.</Notice></>;
  const ids = B.RUNS.map(B.keyOf), qa = route.q.get('a'), qb = route.q.get('b');
  const a = ids.includes(qa) ? qa : ids[0], b = ids.includes(qb) && qb !== a ? qb : ids.find(x => x !== a);
  const ra = B.RUNS.find(r => B.keyOf(r) === a), rb = B.RUNS.find(r => B.keyOf(r) === b);
  const rows = B.taskOrder().map(t => { let both = 0, ao = 0, bo = 0, none = 0, n = 0; for (const c of B.taskRows(t)) { const va = B.result(ra.id, c.id), vb = B.result(rb.id, c.id); if (!va || !vb) continue; n++; const x = B.okOf(va), y = B.okOf(vb); if (x && y) both++; else if (x) ao++; else if (y) bo++; else none++; } return {t, n, both, ao, bo, none, d: n ? (ao - bo) / n : null}; }).filter(r => r.n);
  const tot = rows.reduce((s, r) => ({n: s.n + r.n, ao: s.ao + r.ao, bo: s.bo + r.bo, both: s.both + r.both, none: s.none + r.none}), {n: 0, ao: 0, bo: 0, both: 0, none: 0});
  const cmp = (B.data.comparisons || []).find(p => (p.a === ra.id && p.b === rb.id) || (p.a === rb.id && p.b === ra.id));
  const ci = cmp?.cluster_bootstrap_ci95 ? (cmp.a === ra.id ? cmp.cluster_bootstrap_ci95 : [-cmp.cluster_bootstrap_ci95[1], -cmp.cluster_bootstrap_ci95[0]]) : null;
  const diff = d => <span className={cn(d > 0 ? 'text-good' : d < 0 ? 'text-bad' : '')}>{d == null ? '—' : `${pp(d)} pp`}</span>;
  const url = `${location.origin}${location.pathname}${href('compare', {a, b})}`;
  return <>
    <PageHeader title="Compare two models" description="Same rows, so the difference is real: rows where only one of the two is right, by task. Positive means model A is better." />
    <div className="flex flex-wrap items-end gap-3">
      <Pick label="Model A" value={a} other={b} onChange={v => go(href('compare', {a: v, b}))} />
      <Pick label="Model B" value={b} other={a} onChange={v => go(href('compare', {a, b: v}))} />
      <span className="ml-auto max-md:-mt-1"><CopyButton text={url} label="Copy link" /></span>
    </div>
    <Section title={`${B.M(a).name} against ${B.M(b).name}`} description={ci ? `Overall difference ${pp(cmp.a === ra.id ? cmp.accuracy_difference : -cmp.accuracy_difference)} percentage points; 95% bootstrap interval over task clusters ${pp(ci[0])} to ${pp(ci[1])}.` : ''}>
      <List className="md:hidden">
        <ListHead aside={diff(tot.n ? (tot.ao - tot.bo) / tot.n : null)}>All tasks · {tot.n} shared rows · A minus B</ListHead>
        {rows.map(r => <Item key={r.t} href={taskHref(r.t)} chevron={false} title={B.taskName(r.t)}
          sub={`Only A right ${r.ao} · only B ${r.bo} · both wrong ${r.none}`} trail={<span className="text-[15px] font-medium tabular-nums">{diff(r.d)}</span>} />)}
      </List>
      <TableCard className="max-md:hidden"><table className="w-full text-sm">
        <thead><tr className="border-b"><th className={TH}>Task</th><th className={cn(TH, 'text-right')}>Shared rows</th><th className={cn(TH, 'text-right')}>Both right</th><th className={cn(TH, 'text-right')}>Only {B.M(a).short}</th><th className={cn(TH, 'text-right')}>Only {B.M(b).short}</th><th className={cn(TH, 'text-right')}>Both wrong</th><th className={cn(TH, 'text-right')}>Difference</th></tr></thead>
        <tbody>
          {rows.map(r => <tr key={r.t} onClick={e => { if (!e.target.closest('a')) location.hash = taskHref(r.t); }} className="cursor-pointer border-b hover:bg-muted/40">
            <td className="py-2.5 pr-3 pl-5"><a href={taskHref(r.t)} className="font-medium hover:underline">{B.taskName(r.t)}</a><span className="block text-xs text-muted-foreground">{B.catInfo(B.taskCat(r.t)).name}</span></td>
            <td className={cn(TD, 'text-right')}>{r.n}</td><td className={cn(TD, 'text-right text-muted-foreground')}>{r.both}</td><td className={cn(TD, 'text-right')}>{r.ao}</td><td className={cn(TD, 'text-right')}>{r.bo}</td><td className={cn(TD, 'text-right text-muted-foreground')}>{r.none}</td><td className={cn(TD, 'text-right font-medium')}>{diff(r.d)}</td>
          </tr>)}
          <tr className="bg-muted/40 font-semibold"><td className="py-2.5 pl-5">All tasks</td><td className={cn(TD, 'text-right')}>{tot.n}</td><td className={cn(TD, 'text-right')}>{tot.both}</td><td className={cn(TD, 'text-right')}>{tot.ao}</td><td className={cn(TD, 'text-right')}>{tot.bo}</td><td className={cn(TD, 'text-right')}>{tot.none}</td><td className={cn(TD, 'text-right')}>{diff(tot.n ? (tot.ao - tot.bo) / tot.n : null)}</td></tr>
        </tbody>
      </table></TableCard>
    </Section>
  </>;
}
