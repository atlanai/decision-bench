#!/usr/bin/env python3
"""Stop only the benchmark Modal app after a bounded wall-clock interval.

Start immediately before deployment in a separate supervised process; stop the
app immediately on normal completion too. This timer is a backup, not billing data.
"""
import argparse
import subprocess
import time

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--modal', required=True, help='Absolute path to the authenticated Modal CLI')
p.add_argument('--seconds', type=int, default=1800)
a = p.parse_args()
if not 1 <= a.seconds <= 1800:
    p.error('The benchmark shutdown timer must be at most 30 minutes')
time.sleep(a.seconds)
subprocess.run([a.modal, 'app', 'stop', 'decision-bench-kev-27b', '--yes'], check=True, timeout=60)
