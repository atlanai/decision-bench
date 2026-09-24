#!/usr/bin/env python3
"""Audit repeatability and option-order sensitivity on the frozen 50-row Tev1 pilot."""
import copy
import json
from pathlib import Path
import random
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from decision_bench import adapters, config, corpus, scoring
from decision_bench.runner import add_estimated_cost, read_jsonl, write_json
from run_tev1 import selected

folder = corpus.ROOT / 'runs/tev1-robustness-v1'
folder.mkdir(exist_ok=True)
path = folder / 'results.jsonl'
seen = {r['id'] for r in read_jsonl(path)}
model = config.get_model('tev1-4b-experimental')
rows = selected('pilot')
for mode, count in [('repeat', 2), ('permutation', 3)]:
    for seed in range(count):
        for original in rows:
            ident = f'{mode}-{seed}-{original["id"]}'
            if ident in seen:
                continue
            case = copy.deepcopy(original)
            q = case['questions'][0]
            if mode == 'permutation':
                order = list(corpus.ordered_options(q))
                random.Random(f'{seed}:{case["id"]}').shuffle(order)
                q['option_order'] = order
            t = time.perf_counter()
            out = add_estimated_cost(adapters.call(model, case, 60), model)
            answer = scoring.normalize_answers(out['response'], case, out['source'])
            record = {'id':ident, 'mode':mode, 'seed':seed, 'case_id':case['id'],
                      'scores':scoring.score(case,answer), 'duration_ms':(time.perf_counter()-t)*1000,
                      'cost_usd':out['cost_usd'], 'usage':out['usage'], 'payload':out['payload'], 'raw':out['raw']}
            # Provider adapter has already redacted both output and metadata.
            with path.open('a') as f:
                f.write(json.dumps(record,ensure_ascii=False)+'\n')
            seen.add(ident)
        print(f'{mode} {seed+1} completed',flush=True)
base = {r['case_id']:r['scores'][0]['label'] for r in read_jsonl(
    corpus.ROOT/'runs/tev1-4b-bench-v4-full-v1/results.jsonl')}
records = read_jsonl(path)
summary = {}
for mode in ['repeat', 'permutation']:
    group = [r for r in records if r['mode']==mode]
    summary[mode] = {'calls':len(group),'correct':sum(r['scores'][0]['correct'] for r in group),
                     'changed_from_full_run':sum(r['scores'][0]['label']!=base[r['case_id']] for r in group)}
summary['estimated_cost_usd'] = sum(r['cost_usd'] for r in records)
write_json(folder/'summary.json',summary)
print(json.dumps(summary,indent=2))
