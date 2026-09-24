"""Compact viewer index with on-demand, content-addressed row details.

The public data.json and corpus.json downloads remain complete. The viewer needs
scores to filter/rank models, but only needs record bodies and raw model outputs
when somebody opens a row. Keep both representations losslessly reconstructable.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict


def write_viewer(output, site):
    by_case = defaultdict(list)
    for record in output['results']:
        by_case[record['case_id']].append(record)
    directory = site / 'details'
    directory.mkdir(exist_ok=True)
    cases = []
    for case in output['cases']:
        detail = {'corpus_sha256': output['corpus_sha256'], 'case': case,
                  'results': by_case[case['id']]}
        body = json.dumps(detail, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
        digest = hashlib.sha256(body.encode()).hexdigest()
        name = f'{digest}.json'
        (directory / name).write_text(body, encoding='utf-8')
        cases.append({**{k: v for k, v in case.items() if k not in ('state', 'provenance')},
                      'detail_url': f'details/{name}'})
    records = []
    for record in output['results']:
        summary = {k: v for k, v in record.items() if k not in ('output_text', 'raw_response')}
        summary['scores'] = [{k: v for k, v in score.items() if k != 'probabilities'}
                             for score in record['scores']]
        if record.get('tokens'):
            summary['tokens'] = {k: v for k, v in record['tokens'].items() if k in ('input', 'output')}
        records.append(summary)
    index = {**output, 'cases': cases, 'results': records}
    temporary = site / 'viewer.json.tmp'
    temporary.write_text(json.dumps(index, ensure_ascii=False, allow_nan=False, separators=(',', ':')),
                         encoding='utf-8')
    temporary.replace(site / 'viewer.json')
    return index
