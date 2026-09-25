#!/usr/bin/env python3
"""Run Sage on deterministic text-only smoke, pilot, or full benchmark selections."""
import argparse
from collections import defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from decision_bench import corpus
from decision_bench.__main__ import parser
from decision_bench.runner import run


def selected(stage):
    rows = [r for r in corpus.load_cases() if not r.get('assets')]
    if stage == 'full':
        return rows
    groups = defaultdict(list)
    for row in rows:
        groups[row['category']].append(row)
    for group in groups.values():
        group.sort(key=lambda r: corpus.digest(r['id']))
    ordered = []
    while any(groups.values()):
        for category in sorted(groups):
            if groups[category]:
                ordered.append(groups[category].pop())
    return ordered[:5 if stage == 'smoke' else 50]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=['smoke', 'pilot', 'full'])
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    rows = selected(a.stage)
    run_id = 'sage-bench-v4-' + a.stage + '-v1'
    if a.dry_run:
        print(f'{run_id}: {len(rows)} text-only rows; selection hash {corpus.digest([r["id"] for r in rows])}')
        return
    args = parser().parse_args(['run', '--model', 'sage', '--run-id', run_id,
                               '--jobs', '1', '--max-attempts', '1', '--timeout', '60',
                               '--ids', ','.join(r['id'] for r in rows)])
    run(args)


if __name__ == '__main__':
    main()
