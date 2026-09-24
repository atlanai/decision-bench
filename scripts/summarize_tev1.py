#!/usr/bin/env python3
"""Summarize the completed Tev1 text run and compare identical rows with published models."""
import json
from pathlib import Path
import random
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from decision_bench import corpus, metrics
from decision_bench.runner import read_jsonl

root = corpus.ROOT
folder = root / 'runs/tev1-4b-bench-v4-full-v1'
meta = json.loads((folder / 'run.json').read_text())
if meta['status'] != 'completed':
    raise SystemExit('Full run has not completed successfully')
records = list({r['case_id']: r for r in read_jsonl(folder / 'results.jsonl')}.values())
cases = {r['id']: r for r in corpus.load_cases()}
events = read_jsonl(folder / 'attempts.jsonl')
summary = metrics.summarize(records, cases, events)
(folder / 'metrics.json').write_text(json.dumps(summary, indent=2)+'\n')
ours = {r['case_id']: r for r in records}
comparisons = []
for p in sorted((root / 'results/bench-v4').glob('*/predictions.jsonl')):
    other = {r['row_id']: r for r in read_jsonl(p)}
    ids = sorted(ours.keys() & other.keys())
    if not ids:
        continue
    a = [int(ours[i]['scores'][0]['correct']) for i in ids]
    b = [int(other[i]['correct']) for i in ids]
    deltas = [x-y for x,y in zip(a,b)]
    rng = random.Random(42)
    boot = sorted(sum(rng.choices(deltas, k=len(ids)))/len(ids) for _ in range(2000))
    comparisons.append({'model':p.parent.name,'n':len(ids),'tev1_accuracy':sum(a)/len(a),
                        'accuracy':sum(b)/len(b),'delta':sum(deltas)/len(deltas),
                        'paired_bootstrap95':[boot[49],boot[1949]]})
comparisons.sort(key=lambda x:x['accuracy'],reverse=True)
(folder/'paired-comparisons.json').write_text(json.dumps(comparisons,indent=2)+'\n')
lines = ['# Tev1 4B Experimental benchmark', '',
         f"Model: `together/Tev1-4B-experimental`. Branch: `upgrade-bench-v1`.", '',
         f"**{summary['correct']}/{summary['cases']} correct ({summary['accuracy']:.2%})**, "
         f"with {summary['operational_errors']} operational errors.", '',
         f"95% Wilson accuracy interval: {summary['accuracy_wilson95'][0]:.2%}–{summary['accuracy_wilson95'][1]:.2%}.",
         f"Median latency: {summary['latency_ms']['p50']:.0f} ms; p95: {summary['latency_ms']['p95']:.0f} ms. "
         'Serial end-to-end HTTP latency, including client overhead.',
         f"Estimated cost: ${summary['cost_usd']:.6f}; input tokens: {summary['tokens']['input_tokens']:,}; "
         f"output tokens: {summary['tokens']['output_tokens']:,}.", '',
         '## Scope and method', '',
         '949 rows without image assets from the frozen 1,071-row bench-v4 corpus. The remaining '
         '122 rows were excluded, not counted as failures. No inputs were silently truncated. '
         'One request per row, one serial worker, one attempt per row. Native A–X letter output, '
         'regex constrained, temperature 0, thinking disabled, max_tokens 8. Semantic keys are mapped '
         'back before scoring. Confidence, Brier, ECE and log loss are unavailable: top-5 token '
         'logprobs do not cover every question’s options and are not calibrated confidence.', '',
         'Estimated cost uses the announced $0.042/M input and $0/M output rate, not a billing receipt. '
         'Cached input tokens are conservatively counted at the full input rate. '
         'Smoke and pilot calls are separate from these full-run metrics. '
         'Training overlap has not been ruled out; results measure this corpus, not a proven uncontaminated holdout.', '',
         f"Corpus SHA256: `{meta['config']['corpus_sha256']}`.",
         'The credential-free implementation snapshot is in `runs/tev1-implementation-v1/`.', '',
         '## Categories', '', '| Category | Correct / rows | Accuracy |', '|---|---:|---:|']
for s in summary['slices']['category']:
    lines.append(f"| {s['name']} | {s['correct']}/{s['count']} | {s['accuracy']:.2%} |")
lines += ['', '## Comparison on identical rows', '',
          'Historical model runs are rescored on the intersection with this run. Differences are Tev1 minus '
          'the comparison model. Intervals are paired row bootstrap intervals (2,000 samples, seed 42), '
          'not adjusted for task clustering or multiple comparisons. Latency across different run dates '
          'and provider settings should not be treated as a controlled speed comparison.', '',
          '| Model | Shared rows | Accuracy | Tev1 difference | 95% interval |',
          '|---|---:|---:|---:|---:|']
for c in comparisons:
    lines.append(f"| {c['model']} | {c['n']} | {c['accuracy']:.2%} | {c['delta']*100:+.2f} pp | "
                 f"{c['paired_bootstrap95'][0]*100:+.2f} to {c['paired_bootstrap95'][1]*100:+.2f} pp |")
lines += ['', '## Artifacts', '', '`run.json`, `results.jsonl`, `attempts.jsonl`, `raw/`, `metrics.json`, '
          'and `paired-comparisons.json` live alongside this report. Raw records remain local and ignored by git.', '']
(folder/'REPORT.md').write_text('\n'.join(lines))
print(json.dumps({k:summary[k] for k in ['cases','correct','accuracy','operational_errors','cost_usd','latency_ms']},indent=2))
print('Report:',folder/'REPORT.md')
