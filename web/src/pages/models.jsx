import {useState} from 'react';
import {ChevronRightIcon} from 'lucide-react';
import * as B from '@/lib/bench';
import {pct, pct0, ms, money, metric, plural, ciText} from '@/lib/format';
import {href, modelHref, catHref, taskHref, rowHref, go as navigate} from '@/lib/route';
import {cn} from '@/lib/utils';
import {PageHeader, Crumbs, Section, ModelName, Logo, Fit, Meter, Stat, EmptyPage, Dash, Notes, Notice} from '@/components/common';
import {List, Item} from '@/components/list';
import {Reliability, Risk} from '@/components/charts';
import {Code} from '@/components/record';
import {ChartCard} from '@/pages/home';
import {TableCard} from '@/pages/task';
import {Badge} from '@/components/ui/badge';
import {Button} from '@/components/ui/button';

const TH = 'h-10 px-3 text-left text-[13px] font-medium whitespace-nowrap text-muted-foreground first:pl-5 last:pr-5';
const TD = 'px-3 py-2.5 first:pl-5 last:pr-5';
const go = h => e => { if (!e.target.closest('a,button')) navigate(h); };

export function Models() {
  const available = [...B.RUNS, ...B.PARTIAL];
  const published = new Set(available.map(B.keyOf));
  const keys = B.ORDER.filter(k => published.has(k));
  return <>
    <PageHeader title="Models" description="Models with published benchmark results. Open one for its fit by use case, failures and calibration."
      actions={B.RUNS.length > 1 && <Button variant="outline" asChild className="max-md:h-11 max-md:w-full max-md:rounded-xl"><a href={href('compare')}>Compare two models</a></Button>} />
    <List className="md:hidden">{keys.map(k => { const m = B.M(k), run = available.find(r => B.keyOf(r) === k), mm = B.subsetMetrics(run, B.allCases);
      return <Item key={k} href={modelHref(k)} lead={<Logo k={k} size={30} className="rounded-lg" />} title={B.fullName(k)}
        sub={[m.vendor, m.vision ? 'Text and images' : 'Text only', ms(mm.latency.p50), run.coverage?.full === false && `${run.coverage.rows_completed} rows · partial`].filter(Boolean).join(' · ')}
        trail={<span className="text-[15px] font-semibold tabular-nums">{pct(mm.accuracy)}</span>} />; })}</List>
    <TableCard className="max-md:hidden">
      <table className="w-full text-sm">
        <thead><tr className="border-b"><th className={TH}>Model</th><th className={TH}>Vendor</th><th className={TH}>Interface</th><th className={TH}>Model name sent</th><th className={TH}>Input</th><th className={cn(TH, 'text-right')}>Accuracy</th><th className={cn(TH, 'text-right')}>Latency</th><th className={cn(TH, 'text-right')}>$ / 1k rows</th></tr></thead>
        <tbody>{keys.map(k => { const m = B.M(k), run = available.find(r => B.keyOf(r) === k), mm = B.subsetMetrics(run, B.allCases);
          return <tr key={k} onClick={go(modelHref(k))} className="cursor-pointer border-b last:border-0 hover:bg-muted/40">
            <td className={TD}><ModelName k={k} />{run.coverage?.full === false && <Badge variant="secondary" className="mt-1">{run.coverage.rows_completed} rows · partial</Badge>}</td>
            <td className={cn(TD, 'text-muted-foreground')}>{m.vendor}</td>
            <td className={cn(TD, 'text-muted-foreground')}>{m.iface}</td>
            <td className={TD}><code className="text-muted-foreground">{m.api_model}</code></td>
            <td className={TD}><Badge variant={m.vision ? 'brand' : 'secondary'}>{m.vision ? 'Text and images' : 'Text only'}</Badge></td>
            <td className={cn(TD, 'text-right font-medium tabular-nums')}>{pct(mm.accuracy)}</td>
            <td className={cn(TD, 'text-right tabular-nums')}>{ms(mm.latency.p50)}</td>
            <td className={cn(TD, 'text-right tabular-nums')}>{money(mm.costPer1k)}</td>
          </tr>; })}</tbody>
      </table>
    </TableCard>
    <Notes items={['Cost is provider-reported where the endpoint returns it, else list price at the time of the run.', "Vendor marks identify the model's maker and remain their property."]} />
  </>;
}

export function ModelPage({id: k}) {
  const [adv, setAdv] = useState(false);
  const m = B.MODELS[k];
  const run = [...B.RUNS, ...B.PARTIAL].find(r => B.keyOf(r) === k);
  if (!m || !run) return <EmptyPage title="No published result">See the <a href="/models" className="text-brand hover:underline">models with results</a>.</EmptyPage>;
  const head = <>
    <Crumbs items={[['Models', href('models')], [m.name, '']]} />
    <div className="flex items-center gap-4">
      {m.logo && <img src={m.logo} alt="" width="48" height="48" className="size-12 shrink-0 rounded-xl border bg-white object-contain p-1" />}
      <div className="min-w-0"><h1 className="text-[26px] leading-tight font-semibold tracking-tight md:text-3xl">{m.name}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{[m.vendor, m.iface, m.vision ? 'text and images' : 'text only'].filter(Boolean).join(' · ')}{m.api_model && <> · sent as <code>{m.api_model}</code></>}</p></div>
    </div>
  </>;
  const details = json => <div className="mt-10"><Button variant="ghost" size="sm" className="-ml-2 whitespace-normal text-left text-muted-foreground max-md:h-auto max-md:py-2" aria-expanded={adv} data-track="model_run_details" onClick={() => setAdv(v => !v)}><ChevronRightIcon className={cn('transition-transform', adv && 'rotate-90')} />Request options, prices and run record</Button>{adv && <Code className="mt-2">{JSON.stringify(json, null, 2)}</Code>}</div>;
  const all = B.subsetMetrics(run, B.allCases), textCases = B.allCases.filter(c => !B.isImageTask(c.task));
  const fits = B.taskOrder().map(t => [t, B.verdict(B.subsetMetrics(run, B.taskRows(t)))]), count = x => fits.filter(([, v]) => v.k === x).length;
  const fails = B.allCases.filter(c => { const v = B.result(run.id, c.id); if (!v || B.okOf(v)) return false; const st = B.caseStats(c); return st.n >= 3 && st.ok >= Math.ceil(st.n * .6); }).map(c => ({c, st: B.caseStats(c), v: B.result(run.id, c.id)})).sort((a, b) => b.st.ok / b.st.n - a.st.ok / a.st.n).slice(0, 20);
  const others = B.RUNS.filter(r => r !== run);
  return <>
    {head}
    <div className="mt-6 grid grid-cols-2 gap-3 md:mt-8 md:grid-cols-5 [&>:last-child:nth-child(odd)]:max-md:col-span-2">
      <Stat label={`Accuracy · ${all.questions} scored rows`} value={pct(all.accuracy)} /><Stat label="95% interval" value={ciText(all.wilson)} /><Stat label="Median latency" value={ms(all.latency.p50)} />
      <Stat label="$ / 1k rows" value={money(all.costPer1k)} /><Stat label="Tasks that fit" value={`${count('ok')} / ${fits.filter(([, v]) => v.k !== 'na').length}`} />
    </div>
    {run.coverage?.full === false && <Notice>This is a partial evaluation: {run.coverage.rows_completed} of {run.coverage.rows_in_corpus} corpus rows were run. Unrun rows are not scored, and this run is not ranked on the full leaderboard. {m.provider === 'tev1' && 'Tev1 was evaluated on 949 text-only cases; all 122 image-containing cases were excluded. Calibration metrics are unavailable for this label-only evaluation.'}</Notice>}
    {m.provider === 'sage' && <Notice>Sage abstained on {B.allCases.filter(c => { const r = B.rawResult(run.id, c.id); return r?.status === 'ok' && r.scores.some(s => s.label == null); }).length} rows. These count as incorrect in accuracy, not as API failures. Probability metrics use renormalized independent option probabilities and do not measure Sage’s original calibrated confidence. Dollar cost is unavailable for this subscription-funded run.</Notice>}
    {all.excluded > 0 && <Notice>{all.excluded} image-only rows excluded: the required image was not sent. Overall metrics use {all.questions} eligible rows. Downloaded run files retain the original, unadjusted results for audit.</Notice>}
    <Section title="Fit by use case" description="Fits: accuracy at or above 90% with the whole 95% interval above 85%. Risky: above 80%. Not fit: below 80%.">
      <List className="md:hidden">{B.categoryOrder().map(c => { const cs = B.allCases.filter(x => B.catKey(x) === c && (run.coverage?.full !== false || B.rawResult(run.id, x.id))), mm = B.subsetMetrics(run, cs), best = B.RUNS.map(r => [r, B.subsetMetrics(r, cs)]).filter(([, x]) => x.questions).sort(([, a], [, b]) => b.accuracy - a.accuracy)[0];
        return <Item key={c} href={catHref(c)} chevron={false} title={B.catInfo(c).name} sub={best ? `Best: ${B.ident(best[0]).short}, ${pct0(best[1].accuracy)}` : ''}
          trail={<span className="flex flex-col items-end gap-1"><span className="text-[15px] font-semibold tabular-nums">{mm.questions ? pct(mm.accuracy) : '—'}</span><Fit v={B.verdict(mm)} /></span>} />; })}</List>
      <TableCard className="max-md:hidden"><table className="w-full text-sm">
        <thead><tr className="border-b"><th className={TH}>Use case</th><th className={TH}>This model</th><th className={cn(TH, 'text-right')}>Best model</th><th className={TH}>Verdict</th></tr></thead>
        <tbody>{B.categoryOrder().map(c => { const cs = B.allCases.filter(x => B.catKey(x) === c && (run.coverage?.full !== false || B.rawResult(run.id, x.id))), mm = B.subsetMetrics(run, cs), best = B.RUNS.map(r => [r, B.subsetMetrics(r, cs)]).filter(([, x]) => x.questions).sort(([, a], [, b]) => b.accuracy - a.accuracy)[0];
          return <tr key={c} onClick={go(catHref(c))} className="cursor-pointer border-b last:border-0 hover:bg-muted/40">
            <td className={TD}><a href={catHref(c)} className="font-medium hover:underline">{B.catInfo(c).name}</a></td>
            <td className={TD}>{mm.questions ? <span className="flex items-center gap-3"><span className="w-12 font-semibold tabular-nums">{pct(mm.accuracy)}</span><Meter value={mm.accuracy} color={m.color} /></span> : <span className="text-muted-foreground">{mm.excluded ? 'Not evaluated: image required' : 'not run'}</span>}</td>
            <td className={cn(TD, 'text-right text-muted-foreground tabular-nums')}>{best ? `${pct0(best[1].accuracy)} · ${B.ident(best[0]).short}` : '—'}</td>
            <td className={TD}><Fit v={B.verdict(mm)} /></td>
          </tr>; })}</tbody>
      </table></TableCard>
    </Section>
    <Section title="Fit by task">
      <div className="grid gap-x-8 rounded-xl border bg-card px-5 py-2 shadow-xs sm:grid-cols-2 lg:grid-cols-3">
        {fits.map(([t, v]) => { const mm = B.subsetMetrics(run, B.taskRows(t));
          return <a key={t} href={taskHref(t)} className="group flex items-center justify-between gap-3 border-b py-2.5 last:border-0 sm:[&:nth-last-child(-n+2)]:border-0 lg:[&:nth-last-child(-n+3)]:border-0">
            <span className="min-w-0"><span className="block truncate text-sm font-medium group-hover:underline">{B.taskName(t)}</span><span className="block truncate text-xs text-muted-foreground">{B.catInfo(B.taskCat(t)).name} · {mm.questions ? `${pct0(mm.accuracy)} on ${mm.questions} rows` : mm.excluded ? 'Not evaluated: image required' : B.isImageTask(t) ? 'image task, not run' : 'not run'}</span></span>
            <Fit v={v} />
          </a>; })}
      </div>
    </Section>
    <Section title="Where it fails while most models succeed" description="The likeliest places to look before using this model. Each opens the row.">
      {fails.length ? <>
      <List className="md:hidden">{fails.map(({c, st, v}) => <Item key={c.id} href={rowHref(c)} wrap title={B.caseTitle(c)}
        sub={<>{B.taskName(c.task)} · key {B.goldText(c)} · <span className="text-bad">said {B.answerOf(v)}</span></>}
        trail={<span className="text-[13px] whitespace-nowrap text-muted-foreground tabular-nums">{st.ok}/{st.n} right</span>} />)}</List>
      <TableCard className="max-md:hidden"><table className="w-full text-sm">
        <thead><tr className="border-b"><th className={TH}>Row</th><th className={TH}>Task</th><th className={TH}>Answer key</th><th className={TH}>This model said</th><th className={cn(TH, 'text-right')}>Others right</th></tr></thead>
        <tbody>{fails.map(({c, st, v}) => <tr key={c.id} onClick={go(rowHref(c))} className="cursor-pointer border-b last:border-0 hover:bg-muted/40">
          <td className={cn(TD, 'max-w-[340px]')}><a href={rowHref(c)} className="line-clamp-2 font-medium hover:underline">{B.caseTitle(c)}</a></td>
          <td className={cn(TD, 'text-muted-foreground')}>{B.taskName(c.task)}</td>
          <td className={cn(TD, 'max-w-[220px]')}><span className="line-clamp-1">{B.goldText(c)}</span></td>
          <td className={cn(TD, 'max-w-[220px] text-bad')}><span className="line-clamp-1">{B.answerOf(v)}</span></td>
          <td className={cn(TD, 'text-right tabular-nums')}>{st.ok}/{st.n}</td>
        </tr>)}</tbody>
      </table></TableCard></> : <p className="text-sm text-muted-foreground">No row where this model is wrong while most others are right.</p>}
    </Section>
    <Section title={m.provider === 'sage' ? 'Renormalized probability diagnostics' : 'Confidence'} description={`Expected calibration error ${metric(all.ece)} · Brier ${metric(all.brier)} · ${plural(all.highConfErrors, 'wrong answer')} given with 90% confidence or more.`}>
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Reliability" description={m.provider === 'sage' ? 'Renormalized option scores versus observed accuracy; these are transformed scores, not Sage’s original confidence.' : 'On the diagonal, stated confidence matches observed accuracy. Dot size is the number of decisions in the bin.'}><Reliability runs={[run, ...others]} cases={textCases} focus={[k]} label="Reliability diagram" /></ChartCard>
        <ChartCard title="Risk and coverage" description="Error rate if answers below a confidence threshold are handed to a person. Other models in grey."><Risk runs={[run, ...others]} cases={textCases} focus={[k]} label="Risk against coverage" /></ChartCard>
      </div>
    </Section>
    {details({request: m.request, pricing: m.pricing, run: {id: run.id, status: run.status, completed_at: run.completed_at, coverage: run.coverage, files: run.files}, resolved: run.model?.resolved_models})}
  </>;
}
