#!/usr/bin/env python3
"""Run every configured API model on the active corpus, then publish the runs and rebuild the site.

  python3 scripts/run_all.py --plan                  # show what would run
  python3 scripts/run_all.py                         # run all openai-compatible and typesafe models, 3 at a time
  python3 scripts/run_all.py --models a,b --jobs 4   # a subset, more concurrency per model
  python3 scripts/run_all.py --limit 5               # smoke test: 5 rows per model (separate run ids)

Each model is a separate `python3 -m decision_bench run` process, so a crash in one never touches another, and
re-running the same command resumes every run. CLI providers are skipped unless --include-cli is given.
"""
import argparse
import concurrent.futures
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from decision_bench import config  # noqa: E402

API = {"openai-compatible", "typesafe"}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--models", help="comma-separated model ids (default: every API model)")
    p.add_argument("--parallel", type=int, default=3, help="models run at the same time (default 3)")
    p.add_argument("--jobs", type=int, default=4, help="concurrent requests per model (default 4)")
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--limit", type=int, help="rows per model, for a smoke test")
    p.add_argument("--include-cli", action="store_true")
    p.add_argument("--no-publish", action="store_true", help="run only; do not publish or rebuild the site")
    p.add_argument("--plan", action="store_true")
    args = p.parse_args()
    models = config.load_models()
    wanted = set(args.models.split(",")) if args.models else None
    chosen = [m for m in models if (wanted is None or m["id"] in wanted)
              and (m["provider"] in API or args.include_cli)]
    if wanted:
        missing = wanted - {m["id"] for m in chosen}
        if missing:
            raise SystemExit(f"unknown or skipped models: {sorted(missing)}")
    if args.plan:
        for m in chosen:
            print(f"{m['id']:<28} {m['provider']:<18} vision={bool(m.get('vision'))}")
        return 0

    def run(m):
        cmd = [sys.executable, "-m", "decision_bench", "run", "--model", m["id"], "--jobs", str(args.jobs),
               "--timeout", str(args.timeout)]
        if args.limit:
            cmd += ["--limit", str(args.limit)]
        log = ROOT / "runs" / f"{m['id']}.log"
        log.parent.mkdir(exist_ok=True)
        with log.open("a") as f:
            code = subprocess.call(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
        return m["id"], code, log

    results = []
    with concurrent.futures.ThreadPoolExecutor(args.parallel) as pool:
        for model_id, code, log in pool.map(run, chosen):
            print(f"{'ok' if code == 0 else f'exit {code}':>8}  {model_id}  (log: {log.relative_to(ROOT)})", flush=True)
            results.append((model_id, code))
    if args.no_publish or args.limit:
        return 0 if all(c == 0 for _, c in results) else 1
    # Publish every completed full run, then rebuild the leaderboard and the site.
    for path in sorted((ROOT / "runs").glob("*/run.json")):
        meta = json.loads(path.read_text())
        if meta["config"]["model_id"] in {m["id"] for m in chosen} and str(meta.get("status", "")).startswith("completed") \
                and not path.parent.name.endswith("-subset"):
            code = subprocess.call([sys.executable, "-m", "decision_bench", "publish", path.parent.name], cwd=ROOT)
            print(f"{'published' if code == 0 else 'publish failed':>14}  {path.parent.name}", flush=True)
    subprocess.call([sys.executable, "-m", "decision_bench", "leaderboard"], cwd=ROOT)
    subprocess.call([sys.executable, "-m", "decision_bench", "report"], cwd=ROOT)
    return 0 if all(c == 0 for _, c in results) else 1


if __name__ == "__main__":
    sys.exit(main())
