#!/usr/bin/env python3
"""Summarize the Sage 1.3 full run and identical-row comparisons."""
import json
from pathlib import Path
import random
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from decision_bench import corpus, metrics
from decision_bench.runner import read_jsonl

root=corpus.ROOT
folder=root/'runs/sage-v1.3-bench-v4-full-v1'
meta=json.loads((folder/'run.json').read_text())
if not meta['status'].startswith('completed'):
    raise SystemExit('Sage run is not complete')
records=list({r['case_id']:r for r in read_jsonl(folder/'results.jsonl')}.values())
cases={r['id']:r for r in corpus.load_cases()}
ledger=read_jsonl(folder/'attempts.jsonl')
if meta.get('decision_pricing'):
    from decision_bench.decision_pricing import apply
    ledger=apply(ledger,meta['decision_pricing'])
summary=metrics.summarize(records,cases,ledger)
abstentions=sum(r['status']=='ok' and s['label'] is None for r in records for s in r['scores'])
summary['abstentions']=abstentions
answered=sum(r['status']=='ok' and s['label'] is not None for r in records for s in r['scores'])
summary['answered_accuracy']=summary['correct']/answered if answered else None
ours={r['case_id']:r for r in records}
comparisons=[]
for p in sorted((root/'results/bench-v4').glob('*/predictions.jsonl')):
    if p.parent.name=='sage':continue
    other={r['row_id']:r for r in read_jsonl(p)}
    ids=sorted(ours.keys()&other.keys())
    a=[int(ours[i]['scores'][0]['correct']) for i in ids]
    b=[int(other[i]['correct']) for i in ids]
    deltas=[x-y for x,y in zip(a,b)]
    rng=random.Random(42)
    boot=sorted(sum(rng.choices(deltas,k=len(ids)))/len(ids) for _ in range(2000))
    comparisons.append({'model':p.parent.name,'n':len(ids),'sage_accuracy':sum(a)/len(a),'accuracy':sum(b)/len(b),
                        'delta':sum(deltas)/len(deltas),'paired_bootstrap95':[boot[49],boot[1949]]})
comparisons.sort(key=lambda x:x['accuracy'],reverse=True)
out=root/'docs/benchmarks/sage';out.mkdir(parents=True,exist_ok=True)
for name,value in [('metrics.json',summary),('paired-comparisons.json',comparisons)]:
    (out/name).write_text(json.dumps(value,indent=2)+'\n')
lines=['# Sage (Levanto) benchmark','',
       f"**{summary['correct']}/{summary['cases']} correct ({summary['accuracy']:.2%})**. "
       f"{abstentions} abstentions; {summary['operational_errors']} operational errors.",'',
       f"Median end-to-end latency: {summary['latency_ms']['p50']:.0f} ms; p95: {summary['latency_ms']['p95']:.0f} ms.",
       f"Accuracy Wilson 95% interval: {summary['accuracy_wilson95'][0]:.2%}–{summary['accuracy_wilson95'][1]:.2%}.",'',
       '## Method','',
       'All 1,071 rows, including 122 image-containing rows, were evaluated with three workers, '
       'reasoning `auto`, no grounding/web search, and the native Choice endpoint. The hosted model '
       'version is verified on every response. Inputs contain only evidence, instructions and options.',
       'A null choice is an abstention and counts as incorrect, not an API failure. Native categorical '
       'probabilities are retained; no answer is replaced by an argmax.',
       'Cost is a token-price usage estimate at verified Starter rates: $0.046 per million input tokens '
       'and $10 per million output tokens. Measured input includes separately reported image tokens; '
       'measured output includes billed reasoning. No web searches were used. Account credits covered '
       'usage; this is not a card charge. Current source: https://levanto.ai/pricing.',
       'The earlier 949-text-row Sage v1.1 run and its dated decision-unit estimate are preserved in v1.1/. '
       'Those historical subscription assumptions are not the current pricing model.',
       'Training-data overlap has not been ruled out. Historical latency comparisons include different '
       'provider/network setups; they are not controlled inference-speed comparisons.','',
       f"Corpus SHA256: `{meta['config']['corpus_sha256']}`.",
       f"Resolved model(s): {', '.join(sorted({r['resolved_model'] for r in records if r.get('resolved_model')}))}.",'',
       '## Category results','', '| Category | Correct / rows | Accuracy |','|---|---:|---:|']
for s in summary['slices']['category']:
    lines.append(f"| {s['name']} | {s['correct']}/{s['count']} | {s['accuracy']:.2%} |")
lines+=['','## Identical-row comparisons','',
        'Sage minus each comparison model. Intervals use 2,000 paired row bootstrap samples (seed 42), '
        'without adjustment for task clustering or multiple comparisons.','',
        '| Model | Shared rows | Accuracy | Sage difference | 95% interval |','|---|---:|---:|---:|---:|']
for c in comparisons:
    lines.append(f"| {c['model']} | {c['n']} | {c['accuracy']:.2%} | {c['delta']*100:+.2f} pp | "
                 f"{c['paired_bootstrap95'][0]*100:+.2f} to {c['paired_bootstrap95'][1]*100:+.2f} pp |")
lines+=['','## Reproduce','',
        '`python3 scripts/run_sage.py full` resumes the frozen Sage 1.3 full-corpus run. '
        '`python3 scripts/summarize_sage.py` rebuilds this report. '
        'Published predictions and scores are in `results/bench-v4/sage/`; private raw responses remain under `runs/`.','',
        'Levanto logo: official site icon, downloaded from https://levanto.ai/favicon/android-chrome-192x192.png.','']
(out/'README.md').write_text('\n'.join(lines))
print(json.dumps({k:summary[k] for k in ['cases','correct','accuracy','abstentions','operational_errors','latency_ms']},indent=2))
