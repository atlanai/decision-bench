import {useState} from 'react';
import * as B from '@/lib/bench';
import {pct, ms, money, plural, human, cap, ciText, hostOf} from '@/lib/format';
import {href, rowHref, dataHref} from '@/lib/route';
import {cn} from '@/lib/utils';
import {Crumbs, Section, Notice, ModelName, Fit, Meter, EmptyPage, Ext} from '@/components/common';
import {Strip, HowToAdd} from '@/pages/home';
import {Badge} from '@/components/ui/badge';
import {Button} from '@/components/ui/button';
import {Tabs, TabsList, TabsTrigger} from '@/components/ui/tabs';

const CONTAMINATION = {low: 'A fresh derivation, unlikely in training data', medium: 'A public dataset that may be in training data', high: 'A well-known benchmark, probably in training data'};
const TH = 'h-10 px-3 text-left text-[13px] font-medium whitespace-nowrap text-muted-foreground first:pl-5 last:pr-5';
const TD = 'px-3 py-2.5 first:pl-5 last:pr-5';

export const TableCard = ({children, className}) => <div className={cn('overflow-hidden rounded-xl border bg-card shadow-xs', className)}><div className="overflow-x-auto">{children}</div></div>;

export function TaskPage({id: t}) {
  const [sort, setSort] = useState('order'), [all, setAll] = useState(false);
  const rows = B.taskRows(t);
  if (!rows.length) return <EmptyPage title="Unknown task"><a href="#/tasks" className="text-brand hover:underline">All tasks</a></EmptyPage>;
  const i = B.taskInfo(t), q0 = rows[0].questions[0], cat = B.taskCat(t), ds = B.datasetsOfTask(t), man = B.man();
  const facts = [
    ['Decision', i.shape ? `${cap(i.shape)}${man.shapes?.[i.shape] ? ` — ${man.shapes[i.shape]}` : ''}` : ''],
    ['Input', [i.input_type, B.isImageTask(t) ? 'image' : 'text', i.length].filter(Boolean).join(' · ')],
    ['Options', i.per_row_options ? 'From the record' : `${Object.keys(q0.options).length}${i.abstain ? `, including abstain (${human(i.abstain)})` : ''}`],
    ['Answer from', i.label_origin || rows[0].source?.labelled_by || ''],
    ['Expertise', i.expertise ? `${cap(i.expertise)}${man.expertise?.[i.expertise] ? ` — ${man.expertise[i.expertise]}` : ''}` : ''],
    ['Contamination', i.contamination ? `${cap(i.contamination)} — ${CONTAMINATION[i.contamination] || ''}` : ''],
  ].filter(([, v]) => v);
  const metrics = B.evaluated(B.RUNS, rows).map(r => [r, B.subsetMetrics(r, rows)]).sort(([, a], [, b]) => b.accuracy - a.accuracy);
  const list = rows.slice().sort((a, b) => { if (sort === 'hardest') { const sa = B.caseStats(a), sb = B.caseStats(b); return (sa.n ? sa.ok / sa.n : 1) - (sb.n ? sb.ok / sb.n : 1); } if (sort === 'title') return B.caseTitle(a).localeCompare(B.caseTitle(b)); return 0; });
  const shown = all ? list : list.slice(0, 40);
  return <>
    <Crumbs items={[['Tasks', href('tasks')], [B.catInfo(cat).name, href('tasks', {category: cat})], [B.taskName(t), '']]} />
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_340px]">
      <div className="min-w-0">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <Badge variant="outline" className="font-mono">{t}</Badge>
          <Badge variant="secondary">{B.catInfo(cat).name}</Badge>
          {B.isImageTask(t) && <Badge variant="brand">Image input</Badge>}
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-balance">{B.taskAsk(t)}</h1>
        <p className="mt-3 max-w-[70ch] text-[15px] leading-relaxed text-muted-foreground">{q0.instructions}</p>
        <div className="mt-6 rounded-xl border bg-card shadow-xs">
          <div className="border-b px-5 py-3 text-sm font-semibold">Options</div>
          {i.per_row_options ? <p className="px-5 py-4 text-sm text-muted-foreground">The options differ per row: {Object.values(q0.options)[0] || 'they come from the record'}</p> :
            <ul className="divide-y">{Object.entries(q0.options).map(([k, d]) => <li key={k} className="grid gap-x-4 gap-y-1 px-5 py-3 text-sm sm:grid-cols-[minmax(120px,max-content)_1fr]"><span className="font-medium">{human(k)}</span><span className="text-muted-foreground">{d}</span></li>)}</ul>}
        </div>
      </div>
      <aside className="h-fit rounded-xl border bg-card p-5 shadow-xs lg:sticky lg:top-20">
        <h2 className="mb-4 text-sm font-semibold">About this task</h2>
        <dl className="space-y-3.5 text-sm">
          {facts.map(([k, v]) => <div key={k}><dt className="text-xs text-muted-foreground">{k}</dt><dd className="mt-0.5 text-foreground/90">{v}</dd></div>)}
          <div><dt className="text-xs text-muted-foreground">Source</dt><dd className="mt-1 space-y-1.5">{ds.map(d => <div key={d.id} className="flex flex-wrap items-center gap-2"><a href={dataHref(d.id)} className="font-medium hover:underline">{d.name}</a>{d.license && <Badge variant="secondary" className="font-mono text-[11px]">{d.license}</Badge>}{d.homepage && <Ext href={d.homepage} icon className="text-xs text-muted-foreground hover:text-foreground">{hostOf(d.homepage)}</Ext>}</div>)}</dd></div>
        </dl>
      </aside>
    </div>

    <Section title="Results on this task" description={`${plural(rows.length, 'row')} each. Fits: accuracy at or above 90% with the whole 95% interval above 85%. Risky: above 80%. Not fit: below 80%.`}>
      {metrics.length ? <TableCard>
        <table className="w-full text-sm">
          <thead><tr className="border-b"><th className={TH}>Model</th><th className={TH}>Accuracy</th><th className={cn(TH, 'text-right')}>95% interval</th><th className={cn(TH, 'text-right')}>Latency</th><th className={cn(TH, 'text-right')}>$ / 1k rows</th><th className={cn(TH, 'text-right')}>No answer</th><th className={TH}>Verdict</th></tr></thead>
          <tbody>{metrics.map(([r, m]) => <tr key={r.id} className="border-b last:border-0 hover:bg-muted/40">
            <td className={TD}><ModelName k={B.keyOf(r)} /></td>
            <td className={TD}><span className="flex items-center gap-3"><span className="w-12 font-semibold tabular-nums">{pct(m.accuracy)}</span><Meter value={m.accuracy} color={B.runColor(r)} /></span></td>
            <td className={cn(TD, 'text-right text-muted-foreground tabular-nums')}>{ciText(m.wilson)}</td>
            <td className={cn(TD, 'text-right tabular-nums')}>{ms(m.latency.p50)}</td>
            <td className={cn(TD, 'text-right tabular-nums')}>{money(m.costPer1k)}</td>
            <td className={cn(TD, 'text-right tabular-nums')}>{m.errors || 0}</td>
            <td className={TD}><Fit v={B.verdict(m)} /></td>
          </tr>)}</tbody>
        </table>
      </TableCard> : <Notice>{B.hasResults() ? 'No model has results on this task yet.' : <>No model has been evaluated on this version yet. <HowToAdd /></>}</Notice>}
      {B.isImageTask(t) && metrics.length > 0 && <p className="mt-2 text-xs text-muted-foreground">Text-only models saw the text rendering, not the image; models that were never sent this task are not listed.</p>}
    </Section>

    <Section title="Rows" description="Every record in this task with its answer key. Open a row to read the record as the model saw it."
      actions={<Tabs value={sort} onValueChange={setSort}><TabsList aria-label="Sort rows"><TabsTrigger value="order">Corpus order</TabsTrigger><TabsTrigger value="hardest">Hardest first</TabsTrigger><TabsTrigger value="title">Title</TabsTrigger></TabsList></Tabs>}>
      <TableCard>
        <table className="w-full text-sm">
          <thead><tr className="border-b"><th className={cn(TH, 'w-12')}>#</th><th className={TH}>Row</th><th className={TH}>Answer key</th><th className={cn(TH, 'text-right')}>Models right</th></tr></thead>
          <tbody>{shown.map(c => <tr key={c.id} onClick={e => { if (!e.target.closest('a')) location.hash = rowHref(c); }} className="cursor-pointer border-b last:border-0 hover:bg-muted/40">
            <td className={cn(TD, 'text-muted-foreground tabular-nums')}>{rows.indexOf(c) + 1}</td>
            <td className={cn(TD, 'max-w-[520px]')}><a href={rowHref(c)} className="line-clamp-2 font-medium hover:underline">{B.caseTitle(c)}</a></td>
            <td className={cn(TD, 'max-w-[280px]')}><span className="line-clamp-1 text-foreground/80">{B.goldText(c)}</span></td>
            <td className={cn(TD, 'text-right')}><Strip st={B.caseStats(c)} /></td>
          </tr>)}</tbody>
        </table>
      </TableCard>
      {rows.length > shown.length && <div className="mt-4 flex justify-center"><Button variant="outline" onClick={() => setAll(true)}>Show all {rows.length} rows</Button></div>}
    </Section>
  </>;
}
