"""Compare a submitted results folder with our repeat runs of the same model.

Step 4 of SKILL.md gives the command. Exit code 0 when the submitted correct count is inside our range
(max + 2 sd), 1 when it is not or when a run cannot be compared.
"""
import argparse
import collections
import json
import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
from decision_bench.corpus import load_cases, load_manifest  # noqa: E402
from decision_bench.metrics import paired_comparison  # noqa: E402
from decision_bench.results import _fmt, export_run, records_from_predictions  # noqa: E402
from decision_bench.runner import read_jsonl  # noqa: E402

MIN_SD = 1.0


def load_folder(folder):
    folder = Path(folder)
    metadata = json.loads((folder / "metadata.json").read_text())
    return metadata, read_jsonl(folder / "predictions.jsonl")


def pass_rule(ours, submitted):
    """(mean, sd, limit, passed): the submitted count passes when it is not above our max + 2 sd, sd at least 1 row."""
    sd = max(statistics.stdev(ours) if len(ours) > 1 else 0.0, MIN_SD)
    limit = max(ours) + 2 * sd
    return statistics.mean(ours), sd, limit, submitted <= limit


def by_row(predictions):
    return {p["row_id"]: p for p in predictions}


def gold_probability(p):
    return (p.get("probabilities") or {}).get(p["gold"], 0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submitted", help="results/<suite>/<model-id> folder from the PR")
    parser.add_argument("--runs", required=True, help="Comma-separated run ids (or published folders) of our runs")
    parser.add_argument("--against", help="A published model id for a paired comparison, for example the neighbour")
    args = parser.parse_args()

    cases, manifest = load_cases(), load_manifest()
    case_map = {c["id"]: c for c in cases}
    runs = {"submitted": load_folder(args.submitted)}
    for run in args.runs.split(","):
        if Path(run).is_dir():
            runs[run] = load_folder(run)
        else:
            metadata, predictions, _ = export_run(run, cases, manifest)
            runs[run] = (metadata, predictions)
    rows = {name: by_row(predictions) for name, (_, predictions) in runs.items()}
    ours = [name for name in runs if name != "submitted"]
    for name in ours:
        if rows[name].keys() != rows["submitted"].keys():
            sys.exit(f"{name} has {len(rows[name])} rows and the submitted run has {len(rows['submitted'])}. "
                     "Finish the run (the same command resumes it) before you compare.")
        if any(p["status"] != "ok" for p in rows[name].values()):
            sys.exit(f"{name} has error rows. Run the same command with --retry-errors before you compare.")

    print("| Run | Correct | Accuracy | Median latency | Server time | Errors | git_dirty |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    counts = {}
    for name, (metadata, predictions) in runs.items():
        totals = metadata["totals"]
        counts[name] = sum(p["correct"] for p in predictions)
        errors = sum(p["status"] != "ok" for p in predictions)
        print(f"| {name} | {counts[name]} | {counts[name] / len(predictions):.2%} | "
              f"{_fmt(totals['latency_p50_ms'], 'ms')} | {_fmt(totals.get('server_time_p50_ms_estimate'), 'ms')} | "
              f"{errors} | {metadata['harness']['git_dirty']} |")

    ours_counts = [counts[name] for name in ours]
    mean, sd, limit, inside = pass_rule(ours_counts, counts["submitted"])
    print(f"\nOurs: mean {mean:.1f}, sd {sd:.2f} (floor {MIN_SD}), range {min(ours_counts)}-{max(ours_counts)}.")
    print(f"Submitted {counts['submitted']} is {(counts['submitted'] - mean) / sd:+.2f} sd from our mean; "
          f"limit max + 2 sd = {limit:.1f} -> {'PASS' if inside else 'FAIL'}")

    print("\nCategories where the correct count is not the same in every run:")
    categories = sorted({p["category"] for p in rows["submitted"].values()})
    for category in categories:
        per_run = [sum(p["correct"] for p in rows[name].values() if p["category"] == category) for name in runs]
        if len(set(per_run)) > 1:
            print(f"  {category}: " + ", ".join(f"{name} {n}" for name, n in zip(runs, per_run)))

    submitted = rows["submitted"]
    split = [i for i in submitted if all(rows[name][i]["correct"] != submitted[i]["correct"] for name in ours)]
    print(f"\nRows where the submitted run differs from all {len(ours)} of ours: {len(split)} "
          f"({sum(submitted[i]['correct'] for i in split)} go the submitted run's way)")
    for i in split:
        answers = collections.Counter(rows[name][i]["answer"] for name in ours)
        gold_ours = [gold_probability(rows[name][i]) for name in ours]
        print(f"  {i}: gold {submitted[i]['gold']}, submitted {submitted[i]['answer']} "
              f"(p(gold) {gold_probability(submitted[i]):.2f}), ours {dict(answers)} "
              f"(p(gold) {min(gold_ours):.2f}-{max(gold_ours):.2f})")

    def same_probabilities(a, b):
        return sum(rows[a][i].get("probabilities") is not None
                   and rows[a][i].get("probabilities") == rows[b][i].get("probabilities") for i in submitted)

    pairs = [same_probabilities(a, b) for n, a in enumerate(ours) for b in ours[n + 1:]]
    print("\nRows with identical probabilities: "
          + (f"between our runs {min(pairs)}-{max(pairs)}; " if pairs else "")
          + "submitted vs each of ours " + ", ".join(str(same_probabilities("submitted", name)) for name in ours))

    if args.against:
        _, reference = load_folder(Path(args.submitted).parent / args.against)
        b = records_from_predictions(reference, args.against)[0]
        print(f"\nPaired accuracy difference against {args.against} (task-cluster bootstrap 95% interval):")
        for name, (_, predictions) in runs.items():
            c = paired_comparison(records_from_predictions(predictions, name)[0], b, case_map)
            low, high = c["cluster_bootstrap_ci95"]
            print(f"  {name}: {c['accuracy_difference']:+.4f} [{low:+.4f}, {high:+.4f}]")
    return 0 if inside else 1


if __name__ == "__main__":
    sys.exit(main())
