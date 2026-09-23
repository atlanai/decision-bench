import {useState} from 'react';
import {ChevronRightIcon} from 'lucide-react';
import * as B from '@/lib/bench';
import {pct, pct0, ms, money, metric, plural, ciText} from '@/lib/format';
import {href, modelHref, catHref, taskHref, rowHref} from '@/lib/route';
import {cn} from '@/lib/utils';
import {PageHeader, Crumbs, Section, Notice, ModelName, Fit, Meter, Stat, EmptyPage, Dash, Notes} from '@/components/common';
import {Reliability, Risk} from '@/components/charts';
import {Code} from '@/components/record';
import {ChartCard, HowToAdd} from '@/pages/home';
import {TableCard} from '@/pages/task';
import {Badge} from '@/components/ui/badge';
import {Button} from '@/components/ui/button';

const TH = 'h-10 px-3 text-left text-[13px] font-medium whitespace-nowrap text-muted-foreground first:pl-5 last:pr-5';
const TD = 'px-3 py-2.5 first:pl-5 last:pr-5';
const go = h => e => { if (!e.target.closest('a,button')) location.hash = h; };

export function Models() {
  const keys = B.ORDER.filter(k => B.MODELS[k].configured);
  return <>
    <PageHeader title="Models" description={<>Every model the harness can run, with the request options and prices used. {B.hasResults() ? 'Open a model for its fit by use case, its failures and its calibration.' : <HowToAdd />}</>}
      actions={B.RUNS.length > 1 && <Button variant="outline" asChild><a href={href('compare')}>Compare two models</a></Button>} />
    <TableCard>
      <table className="w-full text-sm">
        <thead><tr className="border-b"><th className={TH}>Model</th><th className={TH}>Vendor</th><th className={TH}>Interface</th><th className={TH}>Model name sent</th><th className={TH}>Input</th><th className={cn(TH, 'text-right')}>Accuracy</th><th className={cn(TH, 'text-right')}>Latency</th><th className={cn(TH, 'text-right')}>$ / 1k rows</th></tr></thead>
        <tbody>{keys.map(k => { const m = B.M(k), run = B.RUNS.find(r => B.keyOf(r) === k), mm = run ? B.subsetMetrics(run, B.allCases) : null;
          return <tr key={k} onClick={go(modelHref(k))} className="cursor-pointer border-b last:border-0 hover:bg-muted/40">
            <td className={TD}><ModelName k={k} /></td>
            <td className={cn(TD, 'text-muted-foreground')}>{m.vendor}</td>
            <td className={cn(TD, 'text-muted-foreground')}>{m.iface}</td>
            <td className={TD}><code className="text-muted-foreground">{m.api_model}</code></td>
            <td className={TD}><Badge variant={m.vision ? 'brand' : 'secondary'}>{m.vision ? 'Text and images' : 'Text only'}</Badge></td>
            <td className={cn(TD, 'text-right font-medium tabular-nums')}>{mm ? pct(mm.accuracy) : <span className="text-xs font-normal text-muted-foreground">not evaluated</span>}</td>
            <td className={cn(TD, 'text-right tabular-nums')}>{mm ? ms(mm.latency.p50) : ''}</td>
            <td className={cn(TD, 'text-right tabular-nums')}>{mm ? money(mm.costPer1k) : ''}</td>
          </tr>; })}</tbody>
      </table>
    </TableCard>
    <Notes items={['Cost is provider-reported where the endpoint returns it, else list price at the time of the run.', "Vendor marks identify the model's maker and remain their property."]} />
  </>;
}

export function ModelPage({id: k}) {
  const [adv, setAdv] = useState(false);
  const m = B.MODELS[k];
  if (!m) return <EmptyPage title="Unknown model"><a href="#/models" className="text-brand hover:underline">All models</a></EmptyPage>;
  const run = B.RUNS.find(r => B.keyOf(r) === k) || B.PARTIAL.find(r => B.keyOf(r) === k);
  const head = <>
    <Crumbs items={[['Models', href('models')], [m.name, '']]} />
    <div className="flex items-center gap-4">
      {m.logo && <img src={m.logo} alt="" width="48" height="48" className="size-12 rounded-xl border bg-white object-contain p-1" />}
      <div className="min-w-0"><h1 className="text-3xl font-semibold tracking-tight">{m.name}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{[m.vendor, m.iface, m.vision ? 'text and images' : 'text only'].filter(Boolean).join(' · ')}{m.api_model && <> · sent as <code>{m.api_model}</code></>}</p></div>
    </div>
  </>;
  const details = json => <div className="mt-10"><Button variant="ghost" size="sm" className="-ml-2 text-muted-foreground" onClick={() => setAdv(v => !v)}><ChevronRightIcon className={cn('transition-transform', adv && 'rotate-90')} />Request options, prices and run record</Button>{adv && <Code className="mt-2">{JSON.stringify(json, null, 2)}</Code>}</div>;
  if (!run) return <>{head}<Notice className="mt-8">This model is configured but has not been evaluated on this version. <HowToAdd /></Notice>{m.request && details({request: m.request, pricing: m.pricing})}</>;
  const all = B.subsetMetrics(run, B.allCases), textCases = B.allCases.filter(c => !B.isImageTask(c.task));
  const fits = B.taskOrder().map(t => [t, B.verdict(B.subsetMetrics(run, B.taskRows(t)))]), count = x => fits.filter(([, v]) => v.k === x).length;
  const fails = B.allCases.filter(c => { const v = B.result(run.id, c.id); if (!v || B.okOf(v)) return false; const st = B.caseStats(c); return st.n >= 3 && st.ok >= Math.ceil(st.n * .6); }).map(c => ({c, st: B.caseStats(c), v: B.result(run.id, c.id)})).sort((a, b) => b.st.ok / b.st.n - a.st.ok / a.st.n).slice(0, 20);
  const others = B.RUNS.filter(r => r !== run);
  return <>
    {head}
    <div className="mt-8 grid grid-cols-2 gap-3 md:grid-cols-5">
      <Stat label="Accuracy" value={pct(all.accuracy)} /><Stat label="95% interval" value={ciText(all.wilson)} /><Stat label="Median latency" value={ms(all.latency.p50)} />
      <Stat label="$ / 1k rows" value={money(all.costPer1k)} /><Stat label="Tasks that fit" value={`${count('ok')} / ${fits.filter(([, v]) => v.k !== 'na').length}`} />
    </div>
    <Section title="Fit by use case" description="Fits: accuracy at or above 90% with the whole 95% interval above 85%. Risky: above 80%. Not fit: below 80%.">
      <TableCard><table className="w-full text-sm">
        <thead><tr className="border-b"><th className={TH}>Use case</th><th className={TH}>This model</th><th className={cn(TH, 'text-right')}>Best model</th><th className={TH}>Verdict</th></tr></thead>
        <tbody>{B.categoryOrder().map(c => { const cs = B.allCases.filter(x => B.catKey(x) === c), mm = B.subsetMetrics(run, cs), best = B.RUNS.map(r => [r, B.subsetMetrics(r, cs)]).filter(([, x]) => x.questions).sort(([, a], [, b]) => b.accuracy - a.accuracy)[0];
          return <tr key={c} onClick={go(catHref(c))} className="cursor-pointer border-b last:border-0 hover:bg-muted/40">
            <td className={TD}><a href={catHref(c)} className="font-medium hover:underline">{B.catInfo(c).name}</a></td>
            <td className={TD}>{mm.questions ? <span className="flex items-center gap-3"><span className="w-12 font-semibold tabular-nums">{pct(mm.accuracy)}</span><Meter value={mm.accuracy} color={m.color} /></span> : <span className="text-muted-foreground">not run</span>}</td>
            <td className={cn(TD, 'text-right text-muted-foreground tabular-nums')}>{best ? `${pct0(best[1].accuracy)} · ${B.ident(best[0]).short}` : '—'}</td>
            <td className={TD}><Fit v={B.verdict(mm)} /></td>
          </tr>; })}</tbody>
      </table></TableCard>
    </Section>
    <Section title="Fit by task">
      <div className="grid gap-x-8 rounded-xl border bg-card px-5 py-2 shadow-xs sm:grid-cols-2 lg:grid-cols-3">
        {fits.map(([t, v]) => { const mm = B.subsetMetrics(run, B.taskRows(t));
          return <a key={t} href={taskHref(t)} className="group flex items-center justify-between gap-3 border-b py-2.5 last:border-0 sm:[&:nth-last-child(-n+2)]:border-0 lg:[&:nth-last-child(-n+3)]:border-0">
            <span className="min-w-0"><span className="block truncate text-sm font-medium group-hover:underline">{B.taskName(t)}</span><span className="block truncate text-xs text-muted-foreground">{B.catInfo(B.taskCat(t)).name} · {mm.questions ? `${pct0(mm.accuracy)} on ${mm.questions} rows` : B.isImageTask(t) ? 'image task, not run' : 'not run'}</span></span>
            <Fit v={v} />
          </a>; })}
      </div>
    </Section>
    <Section title="Where it fails while most models succeed" description="The likeliest places to look before using this model. Each opens the row.">
      {fails.length ? <TableCard><table className="w-full text-sm">
        <thead><tr className="border-b"><th className={TH}>Row</th><th className={TH}>Task</th><th className={TH}>Answer key</th><th className={TH}>This model said</th><th className={cn(TH, 'text-right')}>Others right</th></tr></thead>
        <tbody>{fails.map(({c, st, v}) => <tr key={c.id} onClick={go(rowHref(c))} className="cursor-pointer border-b last:border-0 hover:bg-muted/40">
          <td className={cn(TD, 'max-w-[340px]')}><a href={rowHref(c)} className="line-clamp-2 font-medium hover:underline">{B.caseTitle(c)}</a></td>
          <td className={cn(TD, 'text-muted-foreground')}>{B.taskName(c.task)}</td>
          <td className={cn(TD, 'max-w-[220px]')}><span className="line-clamp-1">{B.goldText(c)}</span></td>
          <td className={cn(TD, 'max-w-[220px] text-bad')}><span className="line-clamp-1">{B.answerOf(v)}</span></td>
          <td className={cn(TD, 'text-right tabular-nums')}>{st.ok}/{st.n}</td>
        </tr>)}</tbody>
      </table></TableCard> : <p className="text-sm text-muted-foreground">No row where this model is wrong while most others are right.</p>}
    </Section>
    <Section title="Confidence" description={`Expected calibration error ${metric(all.ece)} · Brier ${metric(all.brier)} · ${plural(all.highConfErrors, 'wrong answer')} given with 90% confidence or more.`}>
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Reliability" description="On the diagonal, stated confidence matches observed accuracy. Dot size is the number of decisions in the bin."><Reliability runs={[run, ...others]} cases={textCases} focus={[k]} label="Reliability diagram" /></ChartCard>
        <ChartCard title="Risk and coverage" description="Error rate if answers below a confidence threshold are handed to a person. Other models in grey."><Risk runs={[run, ...others]} cases={textCases} focus={[k]} label="Risk against coverage" /></ChartCard>
      </div>
    </Section>
    {details({request: m.request, pricing: m.pricing, run: {id: run.id, status: run.status, completed_at: run.completed_at, coverage: run.coverage, files: run.files}, resolved: run.model?.resolved_models})}
  </>;
}
