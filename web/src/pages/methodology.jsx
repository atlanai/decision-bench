import {useEffect} from 'react';
import {ChartColumnIcon, DatabaseIcon, DownloadIcon, ScaleIcon, ScrollTextIcon} from 'lucide-react';
import * as B from '@/lib/bench';
import {num} from '@/lib/format';
import {PageHeader, Stat, Fit, Logo} from '@/components/common';
import {Code} from '@/components/record';
import {Accordion, AccordionContent, AccordionItem, AccordionTrigger} from '@/components/ui/accordion';

const A = ({href, children}) => <a href={href} target={href.startsWith('#') ? undefined : '_blank'} rel="noopener" className="text-brand underline-offset-4 hover:underline">{children}</a>;
const Terms = ({items}) => <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-[max-content_minmax(0,1fr)]">{items.map(([k, v]) => <div key={typeof k === 'string' ? k : v} className="contents"><dt className="font-medium text-foreground">{k}</dt><dd className="text-foreground/80 max-sm:mb-2">{v}</dd></div>)}</dl>;
const METRICS = [
  ['Accuracy', 'Share of rows answered as the key does; no answer counts as wrong. Shown with a Wilson 95% interval; models whose intervals overlap share a rank.'],
  ['Per use case, per task', 'The same, recomputed on that subset of rows.'],
  ['Macro F1', 'F1 per option averaged within a task, then across tasks. Rewards the rare options.'],
  ['ECE and Brier', 'Calibration: the gap between stated confidence and observed accuracy, and the squared error of the stated probabilities. Lower is better.'],
  ['Latency', 'Wall-clock time per row at the client: median and 95th percentile. CLI times include start-up and are marked.'],
  ['Cost per 1,000 rows', 'Provider-reported cost where the endpoint returns it, else tokens priced at the list prices recorded with the run.'],
  ['Tokens', 'Input and output tokens per row.'],
  ['Paired difference', 'Rows where only one of two models is right, with a bootstrap interval over task clusters.'],
];

export function Methodology({id}) {
  const rows = B.allCases.length, imgs = B.allCases.filter(c => B.isImageTask(c.task)).length, prompt = B.data.prompt?.system || '';
  useEffect(() => { if (id) document.getElementById(`m-${id}`)?.scrollIntoView({block: 'start'}); }, [id]);
  const parts = [
    ['what', 'What is measured', 'The same call a person or a record made, on real work', <>
      <p>Whether a model makes the same call a human or an objective record made on a real piece of work. Each row is one record with one question and a short fixed list of options; the model picks one and states a probability for each. Nothing is generated or graded by another model.</p>
      <p>The corpus is frozen by sha256 and results from different versions are never mixed.</p></>],
    ['rows', 'Where rows come from', 'Open-licence datasets, chosen by written rules', <ul>
      <li>Every dataset is on the <A href="#/data">Data page</A> with its licence, the terms of the material inside it, who decided the answers, and how rows were chosen.</li>
      <li>Both the dataset and the material inside it must allow copying, changing and redistributing, commercially too. Non-commercial or publisher-copyrighted sources are not used.</li>
      <li>Every option is the answer at least once; no option on more than 60% of a task's rows. Titles are neutral and never sent to models.</li>
      <li>Some labels are derived by rule from the record itself (a version bump from tags, a chart claim checked against the chart's data); those task pages say so.</li></ul>],
    ['sees', 'What the model sees', 'The record, the instruction and shuffled options', <>
      <p>The record, the task instruction and the options in a fixed per-row shuffled order. Never the answer, the rationale, the title or the source. Vision models also receive the row's images; text-only models receive the text rendering instead, and the site marks which was used.</p>
      <p>API models use a chat completions endpoint with a JSON schema response format where supported. CLI models run in an empty directory with tools disabled. A response cut off by the token limit, a refusal, a tool call or invalid JSON is <em>no answer</em>: counted as wrong, reported separately.</p>
      {prompt && <div className="mt-4"><div className="mb-2 text-xs font-medium text-muted-foreground">System prompt sent with every request · {B.data.prompt?.version}</div><Code wrap>{prompt}</Code></div>}</>],
    ['metrics', 'Metrics', 'Accuracy with intervals, calibration, latency and cost', <Terms items={METRICS} />],
    ['verdict', 'The fit verdict', 'Fits, Risky or Not fit, computed from the numbers', <>
      <Terms items={[[<Fit v={{k: 'ok', t: 'Fits'}} />, 'Accuracy at or above 90% with the whole 95% interval above 85%.'], [<Fit v={{k: 'risk', t: 'Risky'}} />, 'Accuracy above 80%.'], [<Fit v={{k: 'no', t: 'Not fit'}} />, 'Accuracy below 80%.'], [<Fit v={{k: 'na', t: 'Not run'}} />, 'The model was not sent those rows.']]} />
      <p className="mt-4">Computed from the numbers, never written by hand; a starting point, not a guarantee.</p></>],
    ['limits', 'Limits', 'Contamination, label noise, small tasks', <Terms items={[['Contamination', 'Public datasets may be in training data; each task states its risk.'], ['Label noise', 'Real labels carry error. Arguable rows are dropped by rule where possible and every row links to its source record.'], ['Small tasks', '20–40 rows each: read the interval, not the point.'], ['One prompt for all', 'No per-model tuning.'], ['Not your data', 'Research datasets and public records, not a production sample.']]} />],
    ['submit', 'Results and citing', 'Add a model by pull request; cite the datasets', <p>Results are added by pull request: run a model on every row, publish the run into <code>results/</code>, open a PR with that folder. The harness, viewer and selection code are MIT; each row keeps its dataset's licence. Please cite the datasets behind the tasks you use as well as the bench.{B.repoOk() && <> <A href={B.gh('results/README.md')}>How to submit</A> · <A href={B.gh('CITATION.cff')}>Citation</A>.</>}</p>],
  ];
  const files = [[DatabaseIcon, 'corpus.json', 'All rows', 'Every row with its answer key', 'JSON'], [ChartColumnIcon, 'data.json', 'Site data', 'Everything the site shows', 'JSON'], [ScaleIcon, 'datasets.json', 'Dataset records', 'Licences, terms and citations', 'JSON'], [ScrollTextIcon, 'protocol.txt', 'Protocol', 'The frozen protocol', 'TXT']];
  const preds = B.RUNS.filter(r => r.files?.predictions);
  const steps = [['A real record', 'From an open-licence dataset, chosen by a written rule in a fixed order.'], ['One question', '12 words or fewer, 2–10 options, each described in one line.'], ['An answer from the source', 'The dataset’s annotators or an objective record, never a model.'], ['A strict JSON answer', 'One option plus a probability for each. Anything else is no answer.']];
  return <div className="max-w-4xl">
    <PageHeader title="Methodology" description="How the bench is built, what a model sees, how answers are scored, and where the limits are." />
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5 max-sm:[&>:last-child:nth-child(odd)]:col-span-2">
      <Stat label="Rows" value={num(rows)} /><Stat label="Tasks" value={B.taskOrder().length} /><Stat label="Use cases" value={B.categoryOrder().length} /><Stat label="Datasets" value={B.DATASETS.length} />{imgs > 0 && <Stat label="With an image" value={num(imgs)} />}
    </div>
    <h2 className="mt-10 mb-4 text-lg font-semibold tracking-tight md:mt-12">How a row is built</h2>
    <ol className="grid grid-cols-2 gap-3 lg:grid-cols-4">{steps.map(([h, p], i) => <li key={h} className="rounded-xl border bg-card p-3.5 shadow-xs md:p-4">
      <span className="grid size-6 place-items-center rounded-full bg-muted font-mono text-xs font-medium">{i + 1}</span>
      <h3 className="mt-3 text-sm font-semibold">{h}</h3><p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">{p}</p></li>)}</ol>
    <h2 className="mt-12 mb-4 text-lg font-semibold tracking-tight">The details</h2>
    <Accordion type="multiple" defaultValue={[id || 'what']} className="rounded-xl border bg-card px-4 shadow-xs md:px-5">
      {parts.map(([k, t, sub, body]) => <AccordionItem key={k} value={k} id={`m-${k}`} className="scroll-mt-20">
        <AccordionTrigger data-track={`methodology_${k}`} className="py-4 hover:no-underline [&[data-state=open]_.sub]:text-foreground/60"><span><span className="block text-[15px] font-semibold">{t}</span><span className="sub mt-0.5 block text-[13px] font-normal text-muted-foreground">{sub}</span></span></AccordionTrigger>
        <AccordionContent className="prose-db max-w-3xl pb-6">{body}</AccordionContent>
      </AccordionItem>)}
    </Accordion>
    <h2 className="mt-12 text-lg font-semibold tracking-tight">Downloads</h2>
    <p className="mt-1 text-sm text-muted-foreground">Everything behind the site, as plain files.</p>
    <h3 className="mt-6 mb-3 text-xs font-medium text-muted-foreground">The bench</h3>
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{files.map(([Icon, h, l, s, k]) => <a key={h} href={h} download className="group flex flex-col rounded-xl border bg-card p-4 shadow-xs transition-colors hover:bg-muted/40">
      <span className="flex items-center justify-between"><span className="grid size-8 place-items-center rounded-lg border bg-background text-muted-foreground group-hover:text-foreground"><Icon className="size-4" /></span><DownloadIcon className="size-4 text-muted-foreground/0 transition-colors group-hover:text-muted-foreground" /></span>
      <span className="mt-3 text-sm font-medium">{l}</span><span className="mt-0.5 text-xs text-muted-foreground">{s}</span>
      <span className="mt-3 font-mono text-[11px] text-muted-foreground">{h}</span></a>)}</div>
    {preds.length > 0 && <>
      <h3 className="mt-8 mb-3 flex items-baseline justify-between gap-4 text-xs font-medium text-muted-foreground"><span>Predictions by model</span><span className="font-normal">JSONL · the answer and confidence for every row</span></h3>
      <ul className="grid rounded-xl border bg-card p-1.5 shadow-xs sm:grid-cols-2 lg:grid-cols-3">{preds.map(r => { const k = B.keyOf(r), m = B.M(k);
        return <li key={r.id}><a href={r.files.predictions} download className="group flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors hover:bg-muted/60">
          <Logo k={k} size={20} /><span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium">{m.name}</span><span className="block truncate text-xs text-muted-foreground">{[m.vendor, m.iface && m.iface !== 'API' && m.iface].filter(Boolean).join(' · ') || 'Predictions'}</span></span>
          <DownloadIcon className="size-4 shrink-0 text-muted-foreground/60 group-hover:text-foreground" /></a></li>; })}</ul>
    </>}
  </div>;
}
