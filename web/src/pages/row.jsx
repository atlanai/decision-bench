import {track} from '@/lib/analytics';
/* One row: the record as the model saw it, and beside it one card that answers "what was asked, what is right,
   and what did the models say" — the options with the answer key marked and each model's pick counted. */
import {Fragment, useEffect, useState} from 'react';
import {CheckIcon, ChevronLeftIcon, ChevronRightIcon, ChevronDownIcon, ExternalLinkIcon, FlagIcon} from 'lucide-react';
import * as B from '@/lib/bench';
import {pct, pct0, ms, money, compact, human, hostOf, plural} from '@/lib/format';
import {href, rowHref, taskHref, dataHref} from '@/lib/route';
import {cn} from '@/lib/utils';
import {Crumbs, Section, Notice, ModelName, EmptyPage, Ext, Notes} from '@/components/common';
import {Code, CopyButton, exactInput} from '@/components/record';
import {RecordView} from '@/components/records/views';
import {TableCard} from '@/pages/task';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {Tip} from '@/components/ui/tooltip';

/* Which models chose each option, from the published results. */
function votesOf(c) {
  const by = {};
  for (const r of B.RUNS) { const v = B.result(r.id, c.id); if (!v) continue; const l = v.scores[0]?.label ?? null; (by[l] ||= []).push(B.keyOf(r)); }
  return by;
}

/* An option's description, unless it only repeats the option ("x.py (a file in the repository)"). */
const describes = (k, d) => { if (!d) return false; const s = String(d), key = String(k); return !(s.startsWith(key) && /^\s*(\(.*\))?\s*$/.test(s.slice(key.length))); };

function QuestionCard({c, review}) {
  const q = c.questions[0], t = c.task, votes = review ? {} : votesOf(c), n = Object.values(votes).flat().length;
  const [instr, setInstr] = useState(false);
  const opts = B.optionOrder(q), none = votes.null || [];
  const long = opts.some(k => String(q.options[k] || '').length > 90);
  const ok = (votes[q.gold] || []).length;
  return (
    <div className="rounded-xl border bg-card shadow-xs">
      <div className="px-5 pt-5">
        <div className="text-xs font-medium text-muted-foreground">Question</div>
        <p className="mt-1.5 text-[15px] leading-snug font-semibold text-balance">{B.taskAsk(t) || q.instructions}</p>
        <button type="button" aria-expanded={instr} data-track="task_instructions" onClick={() => setInstr(v => !v)} className="mt-2 inline-flex cursor-pointer items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
          Instructions the model received<ChevronDownIcon className={cn('size-3.5 transition-transform', instr && 'rotate-180')} />
        </button>
        {instr && <p className="mt-2 text-[13px] leading-relaxed text-muted-foreground">{q.instructions}</p>}
      </div>
      <div className="mt-4 flex items-baseline justify-between gap-3 border-t px-5 pt-4 pb-2">
        <span className="text-xs font-medium text-muted-foreground">Options, in the order the model saw them</span>
        {n > 0 && <span className="text-xs whitespace-nowrap text-muted-foreground tabular-nums">models</span>}
      </div>
      <ul className="px-2 pb-2">
        {opts.map(k => { const gold = k === q.gold, who = votes[k] || [];
          return <li key={k} className={cn('relative grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3 rounded-lg px-3 py-2.5', gold && 'bg-good-soft')}>
            <div className="min-w-0">
              <span className={cn('block text-sm font-medium [overflow-wrap:anywhere]', gold && 'text-good')}>{B.optLabel(t, k)}</span>
              {gold && <span className="mt-0.5 flex items-center gap-1 text-xs font-medium text-good"><CheckIcon className="size-3.5" />Answer key</span>}
              {describes(k, q.options[k]) && <p className={cn('mt-0.5 text-[13px] leading-relaxed text-muted-foreground', long && 'line-clamp-3')}>{q.options[k]}</p>}
            </div>
            {n > 0 && <Tip content={who.length ? who.map(x => B.M(x).name).join(', ') : 'No model chose this'}>
              <span className="flex cursor-default items-center gap-2 pt-0.5" tabIndex={0}>
                <span className="h-1.5 w-12 overflow-hidden rounded-full bg-foreground/10"><i className={cn('block h-full rounded-full', gold ? 'bg-good' : 'bg-bad')} style={{width: `${who.length / n * 100}%`}} /></span>
                <span className={cn('w-5 text-right text-sm tabular-nums', who.length ? 'font-medium' : 'text-muted-foreground/60')}>{who.length}</span>
              </span>
            </Tip>}
          </li>; })}
        {none.length > 0 && <li className="flex items-center justify-between px-3 py-2 text-sm text-muted-foreground"><span>No valid answer</span><Tip content={none.map(x => B.M(x).name).join(', ')}><span className="w-5 text-right font-medium text-bad tabular-nums" tabIndex={0}>{none.length}</span></Tip></li>}
      </ul>
      {n > 0 && <div className="border-t px-5 py-3 text-[13px] text-muted-foreground"><span className="font-medium text-foreground">{ok} of {n}</span> models match the answer key.</div>}
    </div>
  );
}

function SourceCard({c}) {
  const q = c.questions[0], src = c.source, d = B.dsOf(c);
  if (!src && !q.rationale) return null;
  const facts = src ? [
    ['Dataset', d ? <a href={dataHref(d.id)} className="font-medium hover:underline">{d.name}</a> : src.dataset],
    ['Record', src.record_id != null && <code className="break-all">{String(src.record_id)}</code>],
    ['Answer decided by', src.labelled_by],
    ['Original label', src.original_label != null && <code className="block max-h-28 overflow-auto break-all">{B.origLabel(src.original_label)}</code>],
    ['Licence', src.license && <Badge variant="secondary" className="font-mono text-[11px]">{src.license}</Badge>],
  ].filter(([, v]) => v) : [];
  return (
    <div className="rounded-xl border bg-card shadow-xs">
      {q.rationale && <div className="px-5 py-4 [overflow-wrap:anywhere]"><div className="text-xs font-medium text-muted-foreground">Why this is the answer</div><p className="mt-1.5 text-[13px] leading-relaxed text-foreground/85">{q.rationale}</p>{c.note && <p className="mt-2 border-l-2 pl-3 text-[13px] leading-relaxed text-muted-foreground">{c.note}</p>}</div>}
      {facts.length > 0 && <dl className={cn('space-y-2.5 px-5 py-4 text-[13px]', q.rationale && 'border-t')}>
        {facts.map(([k, v]) => <div key={k} className="grid grid-cols-[112px_minmax(0,1fr)] gap-3"><dt className="text-muted-foreground">{k}</dt><dd className="min-w-0">{v}</dd></div>)}
      </dl>}
      {(src?.url || B.repoOk()) && <div className="flex flex-wrap gap-x-4 gap-y-1 border-t px-5 py-3 text-[13px]">
        {src?.url && <Ext href={src.url} className="inline-flex items-center gap-1.5 text-brand hover:underline"><ExternalLinkIcon className="size-3.5" />Source record{hostOf(src.url) && <span className="text-muted-foreground">· {hostOf(src.url)}</span>}</Ext>}
        {B.repoOk() && <a href={B.ghIssue('label-error.yml', {title: `Label question: ${c.id}`})} target="_blank" rel="noopener" className="inline-flex items-center gap-1.5 text-muted-foreground hover:text-foreground"><FlagIcon className="size-3.5" />Report a label problem</a>}
      </div>}
    </div>
  );
}

function Answers({c}) {
  const [open, setOpen] = useState(() => new Set());
  const rs = B.RUNS.filter(r => B.result(r.id, c.id));
  if (!rs.length) return <Notice>{B.hasResults() ? 'No model has a result on this row.' : 'No model has been evaluated on this version yet.'}</Notice>;
  const rows = rs.map(r => { const v = B.result(r.id, c.id); return {r, v, ok: B.okOf(v)}; }).sort((a, b) => (a.ok - b.ok) || B.byOrder(a.r, b.r));
  const img = B.isImageTask(c.task), cols = img ? 7 : 6;
  const toggle = id => { track('result_toggle', {expanded: !open.has(id)}); setOpen(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; }); };
  const TH = 'h-10 px-3 text-left text-[13px] font-medium whitespace-nowrap text-muted-foreground first:pl-5 last:pr-5';
  return <>
    <TableCard>
      <table className="w-full text-sm">
        <thead><tr className="border-b"><th className={TH}>Model</th><th className={TH}>Answer</th><th className={cn(TH, 'text-right')}>Confidence</th><th className={cn(TH, 'text-right')}>Latency</th><th className={cn(TH, 'text-right')}>Cost</th><th className={cn(TH, 'text-right')}>Tokens in / out</th>{img && <th className={TH}>Saw</th>}</tr></thead>
        <tbody>{rows.map(({r, v, ok}) => { const s = v.scores[0], on = open.has(r.id);
          const probs = Object.entries(s?.probabilities || {}).sort((a, b) => b[1] - a[1]);
          return <Fragment key={r.id}>
            <tr onClick={() => toggle(r.id)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(r.id); } }} tabIndex={0} aria-expanded={on}
              className={cn('cursor-pointer border-b transition-colors outline-none hover:bg-muted/40 focus-visible:bg-muted/50', on && 'bg-muted/40')}>
              <td className="py-2.5 pl-5"><span className="flex items-center gap-2"><ChevronRightIcon className={cn('size-4 shrink-0 text-muted-foreground transition-transform', on && 'rotate-90')} /><ModelName k={B.keyOf(r)} link={false} /></span></td>
              <td className="max-w-[280px] px-3 py-2.5">
                <span className={cn('inline-flex max-w-full items-center gap-1.5', ok ? 'text-foreground' : 'text-bad')}>
                  <span className={cn('grid size-4 shrink-0 place-items-center rounded-full text-[10px] font-bold', ok ? 'bg-good-soft text-good' : 'bg-bad-soft text-bad')}>{ok ? '✓' : '✗'}</span>
                  <span className="truncate font-medium">{s?.label != null ? B.optLabel(c.task, s.label) : v.status === 'ok' ? 'no answer' : human(v.status)}</span>
                </span>
              </td>
              <td className="px-3 py-2.5 text-right tabular-nums">{pct0(s?.confidence)}</td>
              <td className="px-3 py-2.5 text-right whitespace-nowrap tabular-nums">{ms(v.duration_ms)}</td>
              <td className="px-3 py-2.5 text-right tabular-nums">{money(v.cost_usd)}</td>
              <td className={cn('px-3 py-2.5 text-right whitespace-nowrap text-muted-foreground tabular-nums', !img && 'pr-5')}>{v.tokens?.input != null ? `${compact(v.tokens.input)} / ${compact(v.tokens.output)}` : '—'}</td>
              {img && <td className="py-2.5 pr-5 pl-3">{v.images_sent ? <Badge variant="brand">image</Badge> : <Badge variant="secondary">text rendering</Badge>}</td>}
            </tr>
            {on && <tr className="border-b bg-muted/30"><td colSpan={cols} className="px-5 py-4">
              <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
                <div>
                  <h4 className="mb-2 text-xs font-medium text-muted-foreground">Probabilities the model gave</h4>
                  {probs.length ? <div className="space-y-1.5">{probs.map(([l, p]) => <div key={l} className="grid grid-cols-[minmax(0,1fr)_96px_48px] items-center gap-3 text-[13px]">
                    <span className="truncate">{B.optLabel(c.task, l)}{l === s.gold && <CheckIcon className="ml-1 inline size-3.5 text-good" />}</span>
                    <span className="h-1.5 overflow-hidden rounded-full bg-foreground/10"><i className="block h-full rounded-full" style={{width: `${p * 100}%`, background: l === s.gold ? 'var(--good)' : l === s.label ? 'var(--bad)' : 'var(--muted-foreground)'}} /></span>
                    <span className="text-right text-xs text-muted-foreground tabular-nums">{pct(p)}</span></div>)}</div> : <p className="text-[13px] text-muted-foreground">No probabilities returned.</p>}
                  {v.error && <p className="mt-3 text-[13px] text-bad">{v.error}</p>}
                </div>
                <div>
                  <h4 className="mb-2 text-xs font-medium text-muted-foreground">Raw response</h4>
                  <Code wrap className="max-h-64 bg-background">{v.output_text || v.raw_response || '(not published)'}</Code>
                  <p className="mt-2 text-xs text-muted-foreground">{[B.ident(r).iface, v.status && `status ${v.status}`, v.attempt_count && plural(v.attempt_count, 'attempt')].filter(Boolean).join(' · ')}</p>
                </div>
              </div>
            </td></tr>}
          </Fragment>; })}</tbody>
      </table>
    </TableCard>
    <Notes items={['Wrong answers first; select a model for its probabilities and raw response.', 'Confidence is the probability the model gave its own answer.']} />
  </>;
}

export function RowView({c, review = false, nav}) {
  const t = c.task, rows = B.taskRows(t), i = rows.indexOf(c), d = B.dsOf(c);
  const [raw, setRaw] = useState(false);
  return <>
    <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-2">
      <Crumbs items={[['Tasks', href('tasks')], [B.catInfo(B.catKey(c)).name, href('tasks', {category: B.catKey(c)})], [B.taskName(t), taskHref(t)], [`Row ${i + 1}`, '']]} />
      {nav}
    </div>
    <h1 className="text-2xl font-semibold tracking-tight text-balance break-words">{B.caseTitle(c)}</h1>
    <p className="mt-1.5 text-sm text-muted-foreground">
      <a href={taskHref(t)} className="font-mono text-xs hover:text-foreground">{t}</a><span className="mx-2 opacity-50">·</span>Row {i + 1} of {rows.length}
      {d && <><span className="mx-2 opacity-50">·</span>from <a href={dataHref(d.id)} className="hover:text-foreground hover:underline">{d.name}</a></>}
    </p>
    <div className="mt-6 grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
      <div className="min-w-0">
        <div className="rounded-xl border bg-card shadow-xs">
          <div className="flex items-center justify-between gap-3 border-b px-5 py-3">
            <h2 className="text-sm font-semibold">The record</h2>
            {B.isImageTask(t) && <Badge variant="brand">Image task</Badge>}
          </div>
          <RecordView c={c} />
          <div className="border-t px-5 py-3">
            <div className="flex items-center justify-between gap-3">
              <button type="button" aria-expanded={raw} data-track="raw_record" onClick={() => setRaw(v => !v)} className="inline-flex cursor-pointer items-center gap-1 text-[13px] text-muted-foreground hover:text-foreground">
                <ChevronRightIcon className={cn('size-4 transition-transform', raw && 'rotate-90')} />Exact input sent to the model (JSON)
              </button>
              {raw && <CopyButton text={exactInput(c)} />}
            </div>
            {raw && <Code className="mt-3">{exactInput(c)}</Code>}
          </div>
        </div>
      </div>
      <aside className="flex flex-col gap-4">
        <QuestionCard c={c} review={review} />
        <SourceCard c={c} />
      </aside>
    </div>
    {!review && <Section title="Model answers"><Answers c={c} /></Section>}
    <div className="mt-12 flex flex-wrap justify-between gap-3 border-t pt-4 text-xs text-muted-foreground">
      <span><code>{c.id}</code> · {B.man().version}</span>
      <CopyButton text={`${location.origin}${location.pathname}${rowHref(c)}`} label="Copy link to this row" />
    </div>
  </>;
}

export function RowPage({id}) {
  const c = B.caseMap.get(id);
  const rows = c ? B.taskRows(c.task) : [], i = rows.indexOf(c), prev = rows[i - 1], next = rows[i + 1];
  useEffect(() => {
    const on = e => { if (e.metaKey || e.ctrlKey || e.altKey || ['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return; if (e.key === 'j' && next) location.hash = rowHref(next); if (e.key === 'k' && prev) location.hash = rowHref(prev); };
    addEventListener('keydown', on); return () => removeEventListener('keydown', on);
  }, [prev, next]);
  if (!c) return <EmptyPage title="Unknown row"><a href="#/tasks" className="text-brand hover:underline">All tasks</a></EmptyPage>;
  const nav = <div className="flex items-center gap-2 text-[13px] text-muted-foreground">
    <span className="tabular-nums">{i + 1} / {rows.length}</span>
    <Tip content="Previous row (k)"><Button variant="outline" size="icon-sm" asChild aria-disabled={!prev}><a href={prev ? rowHref(prev) : undefined} aria-label="Previous row"><ChevronLeftIcon /></a></Button></Tip>
    <Tip content="Next row (j)"><Button variant="outline" size="icon-sm" asChild aria-disabled={!next}><a href={next ? rowHref(next) : undefined} aria-label="Next row"><ChevronRightIcon /></a></Button></Tip>
  </div>;
  return <RowView c={c} nav={nav} />;
}
