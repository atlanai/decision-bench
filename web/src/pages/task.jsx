import {track} from '@/lib/analytics';
import {useState} from 'react';
import {BadgeCheckIcon, FileTextIcon, ImageIcon, InfoIcon, ListChecksIcon} from 'lucide-react';
import * as B from '@/lib/bench';
import {pct, ms, money, plural, human, cap, ciText, hostOf} from '@/lib/format';
import {href, rowHref, dataHref, modelHref, go} from '@/lib/route';
import {cn} from '@/lib/utils';
import {Crumbs, Section, Notice, ModelName, Logo, Fit, Meter, EmptyPage, Ext, Notes} from '@/components/common';
import {List, Item} from '@/components/list';
import {Expandable} from '@/components/records/kit';
import {Tip} from '@/components/ui/tooltip';
import {Strip, HowToAdd} from '@/pages/home';
import {Badge} from '@/components/ui/badge';
import {Button} from '@/components/ui/button';
import {SegmentedControl, SegmentedList, SegmentedOption} from '@/components/ui/segmented-control';

const CONTAMINATION = {low: 'A fresh derivation, unlikely to be in training data.', medium: 'A public dataset that may be in training data.', high: 'A well-known benchmark, probably in training data.'};
const TH = 'h-10 px-3 text-left text-[13px] font-medium whitespace-nowrap text-muted-foreground first:pl-5 last:pr-5';
const TD = 'px-3 py-2.5 first:pl-5 last:pr-5';

export const TableCard = ({children, className}) => <div className={cn('overflow-hidden rounded-xl border bg-card shadow-xs', className)}><div className="overflow-x-auto">{children}</div></div>;

/* Training-data risk as three grey bars, not a colour. */
const Risk = ({level}) => { const n = {low: 1, medium: 2, high: 3}[level] || 0;
  return <span className="inline-flex items-end gap-[2px]" aria-hidden="true">{[5, 8, 11].map((h, j) => <i key={h} className={cn('w-[3px] rounded-[1px]', j < n ? 'bg-foreground/70' : 'bg-foreground/15')} style={{height: h}} />)}</span>; };
/* One line of the details panel: label on the left, value on the right, the long explanation in a tooltip. */
const Prop = ({label, hint, children}) => (
  <div className="flex items-baseline justify-between gap-4 py-2.5">
    <dt className="flex shrink-0 items-center gap-1 text-muted-foreground">{label}{hint && <Tip content={hint}><button type="button" aria-label={`About ${label}`} className="cursor-help text-muted-foreground/60 hover:text-foreground"><InfoIcon className="size-3" /></button></Tip>}</dt>
    <dd className="flex min-w-0 items-center gap-2 text-right font-medium">{children}</dd>
  </div>
);

export function TaskPage({id: t}) {
  const [sort, setSort] = useState('order'), [all, setAll] = useState(false);
  const rows = B.taskRows(t);
  if (!rows.length) return <EmptyPage title="No such task">It may have been renamed in this version. <a href="/tasks" className="text-brand hover:underline">Browse every task</a></EmptyPage>;
  const i = B.taskInfo(t), q0 = rows[0].questions[0], cat = B.taskCat(t), ds = B.datasetsOfTask(t), man = B.man(), img = B.isImageTask(t);
  const nOpts = Object.keys(q0.options).length, by = rows[0].source?.labelled_by || '';
  /* How the task works, in three steps: what the model reads, what it chooses between, what the answer is checked against. */
  const steps = [
    [img ? ImageIcon : FileTextIcon, 'Reads', cap(i.input_type || (img ? 'an image' : 'a text record')), [i.length && `${cap(i.length)} input`, img && 'Image'].filter(Boolean).join(' · ')],
    [ListChecksIcon, 'Chooses', B.taskPicks(t) || `One of ${nOpts} options`, i.per_row_options ? 'The options come with each row' : `${nOpts} options, the same for every row`],
    [BadgeCheckIcon, 'Checked against', cap(i.label_origin || 'the source'), cap(by)],
  ];
  const metrics = B.evaluated(B.RUNS, rows).map(r => [r, B.subsetMetrics(r, rows)]).sort(([, a], [, b]) => b.accuracy - a.accuracy);
  const list = rows.slice().sort((a, b) => { if (sort === 'hardest') { const sa = B.caseStats(a), sb = B.caseStats(b); return (sa.n ? sa.ok / sa.n : 1) - (sb.n ? sb.ok / sb.n : 1); } if (sort === 'title') return B.caseTitle(a).localeCompare(B.caseTitle(b)); return 0; });
  const shown = all ? list : list.slice(0, 40);
  return <>
    <Crumbs items={[['Tasks', href('tasks')], [B.catInfo(cat).name, href('tasks', {category: cat})], [B.taskName(t), '']]} />
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="min-w-0">
        <div className="mb-3 flex flex-wrap items-center gap-2 text-[13px] text-muted-foreground">
          <span className="font-mono text-xs">{t}</span><span aria-hidden="true">·</span><a href={href('tasks', {category: cat})} className="hover:text-foreground">{B.catInfo(cat).name}</a>
          {img && <Badge variant="outline" className="ml-1 font-normal text-muted-foreground"><ImageIcon />Image input</Badge>}
        </div>
        <h1 className="text-[28px] leading-tight font-semibold tracking-tight text-balance md:text-3xl">{B.taskName(t)}</h1>
        <p className="mt-2 max-w-[62ch] text-[15px] leading-relaxed text-muted-foreground">{B.taskBlurb(t)}</p>

        <ol className="mt-6 grid overflow-hidden rounded-xl border bg-card shadow-xs max-sm:divide-y sm:grid-cols-3 sm:divide-x">
          {steps.map(([Icon, k, v, sub]) => <li key={k} className="min-w-0 px-4 py-3.5">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground"><Icon className="size-3.5" />{k}</div>
            <p className="mt-1 text-sm leading-snug font-medium">{v}</p>
            {sub && <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground" title={sub}>{sub}</p>}
          </li>)}
        </ol>

        <div className="mt-4 rounded-xl border bg-card shadow-xs">
          <div className="px-5 py-4">
            <div className="text-xs text-muted-foreground">The question</div>
            <p className="mt-1 text-[15px] leading-snug font-medium text-balance">{B.taskAsk(t)}</p>
            {q0.instructions && <Expandable lines={2} label="Full instructions" className="mt-2"><p className="text-[13px] leading-relaxed text-muted-foreground">{q0.instructions}</p></Expandable>}
          </div>
          {!i.per_row_options && <ul className="grid grid-cols-1 border-t sm:grid-cols-[max-content_minmax(0,1fr)]">
            {Object.entries(q0.options).map(([k, d]) => <li key={k} className="col-span-full grid grid-cols-subgrid gap-x-8 gap-y-0.5 border-b px-5 py-2.5 text-sm last:border-0">
              <span className="font-medium">{human(k)}{i.abstain === k && <span className="ml-2 text-xs font-normal text-muted-foreground">abstain</span>}</span><span className="text-muted-foreground">{d}</span>
            </li>)}
          </ul>}
        </div>
      </div>
      <aside className="h-fit rounded-xl border bg-card px-5 pt-4 pb-2 shadow-xs lg:sticky lg:top-20">
        <h2 className="text-sm font-semibold">About this task</h2>
        <dl className="mt-1 divide-y text-[13px]">
          <Prop label="Rows">{rows.length}</Prop>
          {i.shape && <Prop label="Decision" hint={man.shapes?.[i.shape]}>{cap(i.shape)}</Prop>}
          {i.expertise && <Prop label="Expertise" hint={man.expertise?.[i.expertise]}>{i.expertise === 'none' ? 'Generalist' : cap(i.expertise)}</Prop>}
          {i.contamination && <Prop label="Training-data risk" hint={CONTAMINATION[i.contamination]}><Risk level={i.contamination} />{cap(i.contamination)}</Prop>}
        </dl>
        {ds.length > 0 && <div className="border-t py-3 text-[13px]">
          <div className="text-muted-foreground">Source</div>
          {ds.map(d => <div key={d.id} className="mt-1.5">
            <a href={dataHref(d.id)} className="font-medium hover:underline">{d.name}</a>
            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">{d.license && <span className="font-mono">{d.license}</span>}{d.homepage && <Ext href={d.homepage} icon className="hover:text-foreground">{hostOf(d.homepage)}</Ext>}</div>
          </div>)}
        </div>}
      </aside>
    </div>

    <Section title="Results on this task" description={`${plural(rows.length, 'row')} each. Fits: accuracy at or above 90% with the whole 95% interval above 85%. Risky: above 80%. Not fit: below 80%.`}>
      {metrics.length ? <>
      <List className="md:hidden">{metrics.map(([r, m]) => { const k = B.keyOf(r);
        return <Item key={r.id} href={modelHref(k)} chevron={false} lead={<Logo k={k} size={28} className="rounded-lg" />} title={B.runName(r)}
          sub={`95% CI ${ciText(m.wilson)} · ${ms(m.latency.p50)} · ${money(m.costPer1k)}/1k${m.errors ? ` · ${m.errors} unanswered` : ''}`}
          trail={<span className="flex flex-col items-end gap-1"><span className="text-[15px] font-semibold tabular-nums">{pct(m.accuracy)}</span><Fit v={B.verdict(m)} /></span>} />; })}</List>
      <TableCard className="max-md:hidden">
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
      </TableCard></> : <Notice>{B.hasResults() ? 'No model has results on this task yet.' : <>No model has been evaluated on this version yet. <HowToAdd /></>}</Notice>}
      {B.isImageTask(t) && metrics.length > 0 && <Notes items={['Text-only models saw a text rendering, not the image.', 'Models never sent this task are not listed.']} />}
    </Section>

    <Section title="Rows" description="Every record in this task with its answer key. Open a row to read the record as the model saw it."
      actions={<SegmentedControl aria-label="Sort rows" value={sort} onValueChange={v => { track('ui_click', {control: 'row_sort', sort: v}); setSort(v); }} className="max-md:w-full"><SegmentedList aria-label="Sort rows" className="max-md:w-full"><SegmentedOption value="order">Corpus order</SegmentedOption><SegmentedOption value="hardest">Hardest first</SegmentedOption><SegmentedOption value="title">Title</SegmentedOption></SegmentedList></SegmentedControl>}>
      <List className="md:hidden">{shown.map(c => { const st = B.caseStats(c);
        return <Item key={c.id} href={rowHref(c)} wrap lead={<span className="w-6 text-[13px] text-muted-foreground tabular-nums">{rows.indexOf(c) + 1}</span>} title={B.caseTitle(c)} sub={`Key: ${B.goldText(c)}`}
          trail={st.n ? <span className="text-[13px] whitespace-nowrap text-muted-foreground tabular-nums"><span className={cn('font-medium', st.ok < st.n ? 'text-foreground' : 'text-muted-foreground')}>{st.ok}</span>/{st.n}</span> : null} />; })}</List>
      <TableCard className="max-md:hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b"><th className={cn(TH, 'w-12')}>#</th><th className={TH}>Row</th><th className={TH}>Answer key</th><th className={cn(TH, 'text-right')}>Models right</th></tr></thead>
          <tbody>{shown.map(c => <tr key={c.id} onClick={e => { if (!e.target.closest('a')) go(rowHref(c)); }} className="cursor-pointer border-b last:border-0 hover:bg-muted/40">
            <td className={cn(TD, 'text-muted-foreground tabular-nums')}>{rows.indexOf(c) + 1}</td>
            <td className={cn(TD, 'max-w-[520px]')}><a href={rowHref(c)} className="line-clamp-2 font-medium hover:underline">{B.caseTitle(c)}</a></td>
            <td className={cn(TD, 'max-w-[280px]')}><span className="line-clamp-1 text-foreground/80">{B.goldText(c)}</span></td>
            <td className={cn(TD, 'text-right')}><Strip st={B.caseStats(c)} /></td>
          </tr>)}</tbody>
        </table>
      </TableCard>
      {rows.length > shown.length && <div className="mt-4 flex justify-center"><Button variant="outline" className="max-md:h-11 max-md:w-full max-md:rounded-xl" data-track="show_all_rows" onClick={() => setAll(true)}>Show all {rows.length} rows</Button></div>}
    </Section>
  </>;
}
