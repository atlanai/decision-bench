#!/usr/bin/env python3
"""Reproduce Kev 27B on the full corpus; it reads no images, so image rows use their text rendering."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from decision_bench import corpus
from decision_bench.__main__ import parser
from decision_bench.runner import run


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['smoke','full'])
    p.add_argument('--dry-run',action='store_true')
    a=p.parse_args()
    rows=corpus.load_cases()
    assert len(rows)==1071
    if a.stage=='smoke':
        rows=[rows[0],rows[len(rows)//4],rows[len(rows)//2],rows[3*len(rows)//4],rows[-1]]
    run_id='kev-27b-bench-v4-'+('smoke' if a.stage=='smoke' else 'full')+'-v1'
    if a.dry_run:
        print(f'{run_id}: {len(rows)} rows; no API calls')
        return
    args=parser().parse_args(['run','--model','kev-27b','--ids',','.join(r['id'] for r in rows),
        '--run-id',run_id,'--jobs','1' if a.stage=='smoke' else '3',
        '--max-attempts','1' if a.stage=='smoke' else '3','--timeout','60'])
    run(args)


if __name__=='__main__':
    main()
