"""Run-level metrics. Every number is recomputed from per-row records and the full attempt ledger."""
from __future__ import annotations

import math
import random
from collections import defaultdict

SLICES = ("category", "task", "source_kind")
TOKEN_KEYS = ("input_tokens", "output_tokens", "cached_input_tokens", "reasoning_output_tokens",
              "cache_creation_input_tokens")


def quantile(values, p):
    xs = sorted(x for x in values if x is not None and math.isfinite(x))
    if not xs:
        return None
    at = (len(xs) - 1) * p
    lo, hi = math.floor(at), math.ceil(at)
    return xs[lo] + (xs[hi] - xs[lo]) * (at - lo)


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def wilson(successes, n, z=1.96):
    """Wilson score interval for a binomial proportion (95% by default). Not adjusted for clustering."""
    if not n:
        return [None, None]
    p = successes / n
    center = (p + z * z / (2 * n)) / (1 + z * z / n)
    radius = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [max(0, center - radius), min(1, center + radius)]


def reliability(scores, bins=10):
    points = []
    valid = [s for s in scores if s.get("confidence") is not None]
    for i in range(bins):
        rows = [s for s in valid if min(int(s["confidence"] * bins), bins - 1) == i]
        points.append({"lo": i / bins, "hi": (i + 1) / bins, "count": len(rows),
                       "confidence": mean([s["confidence"] for s in rows]),
                       "accuracy": mean([int(s["correct"]) for s in rows])})
    ece = (sum(p["count"] * abs(p["confidence"] - p["accuracy"]) for p in points if p["count"]) / len(valid)
           if valid else None)
    return {"bins": points, "ece": ece, "valid_count": len(valid)}


def risk_coverage(scores):
    valid = [s for s in scores if s.get("confidence") is not None]
    points = []
    for t in sorted({0.0, 1.0, *[s["confidence"] for s in valid]}):
        kept = [s for s in valid if s["confidence"] >= t]
        points.append({"threshold": t, "coverage": len(kept) / len(scores) if scores else 0,
                       "risk": 1 - mean([int(s["correct"]) for s in kept]) if kept else None,
                       "accepted": len(kept), "errors": sum(not s["correct"] for s in kept)})
    return points


def consolidate_attempts(events):
    """A start and a finish describe one attempt; an orphan start is still work."""
    latest = {}
    for event in events:
        ident = event["attempt_id"]
        # Never let a duplicate start overwrite a finished receipt.
        if ident not in latest or event.get("event") == "finished":
            latest[ident] = event
    return list(latest.values())


def attempt_totals(attempts):
    known_cost = [a["cost_usd"] for a in attempts if a.get("cost_usd") is not None]
    tokens = {}
    for key in TOKEN_KEYS:
        values = [(a.get("usage") or {}).get(key) for a in attempts if (a.get("usage") or {}).get(key) is not None]
        tokens[key] = sum(values) if values else None
        tokens[key + "_coverage"] = len(values) / len(attempts) if attempts else 0
    by_case = defaultdict(int)
    for a in attempts:
        by_case[a["case_id"]] += 1
    return {"attempts": len(attempts), "retries": sum(max(n - 1, 0) for n in by_case.values()),
            "incomplete_attempts": sum(a.get("event") == "started" for a in attempts),
            "attempt_errors": sum(a.get("event") == "finished" and a.get("status") != "ok" for a in attempts),
            "cost_usd": sum(known_cost) if known_cost else None,
            "cost_coverage": len(known_cost) / len(attempts) if attempts else 0,
            "cost_bases": sorted({a.get("cost_basis") or "unavailable" for a in attempts}),
            "tokens": tokens}


def _slice(name, rows):
    correct = sum(s["correct"] for s in rows)
    return {"name": name, "count": len(rows), "correct": correct, "accuracy": correct / len(rows) if rows else None,
            "wilson95": wilson(correct, len(rows)), "brier": mean([s.get("brier") for s in rows])}


def summarize(records, case_map, attempt_events=None):
    """Metrics for one model on one corpus. A failed request counts as a wrong answer and an operational error."""
    scores = [s for r in records for s in r["scores"]]
    n, correct = len(scores), sum(s["correct"] for s in scores)
    attempts = (consolidate_attempts(attempt_events) if attempt_events is not None
                else [a for r in records for a in r.get("attempts", [])])
    totals = attempt_totals(attempts)
    slices = {}
    for key in SLICES:
        groups = defaultdict(list)
        for r in records:
            groups[case_map[r["case_id"]].get(key, "unknown")].extend(r["scores"])
        slices[key] = [_slice(name, rows) for name, rows in sorted(groups.items())]
    # Confusion matrices are per task; labels are never pooled across tasks.
    confusion = defaultdict(lambda: defaultdict(int))
    by_task = defaultdict(list)
    for r in records:
        task = case_map[r["case_id"]]["task"]
        for s in r["scores"]:
            confusion[task][f"{s['gold']} → {s['label']}"] += 1
            by_task[task].append(s)
    macro_f1s = []
    for rows in by_task.values():
        labels = {s["gold"] for s in rows} | {s["label"] for s in rows if s["label"] is not None}
        fs = []
        for label in labels:
            tp = sum(s["gold"] == label and s["label"] == label for s in rows)
            fp = sum(s["gold"] != label and s["label"] == label for s in rows)
            fn = sum(s["gold"] == label and s["label"] != label for s in rows)
            fs.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0)
        macro_f1s.append(mean(fs))
    durations = [r.get("duration_ms") for r in records]
    return {"cases": len(records), "questions": n, "correct": correct, "accuracy": correct / n if n else None,
            "accuracy_wilson95": wilson(correct, n),
            "macro_category_accuracy": mean([x["accuracy"] for x in slices["category"]]),
            "macro_task_f1": mean(macro_f1s),
            "operational_errors": sum(r["status"] != "ok" for r in records),
            "wrong_decisions": sum(not s["correct"] for r in records if r["status"] == "ok" for s in r["scores"]),
            **totals,
            "latency_ms": {"p50": quantile(durations, .5), "p95": quantile(durations, .95),
                           "p99": quantile(durations, .99), "mean": mean(durations),
                           "sum": sum(d for d in durations if d is not None)},
            "cost_per_1000_cases_usd": (totals["cost_usd"] / len(records) * 1000
                                        if totals["cost_usd"] is not None and records else None),
            "brier": mean([s.get("brier") for s in scores]),
            "log_loss": mean([s.get("log_loss") for s in scores]),
            "reliability": reliability(scores), "risk_coverage": risk_coverage(scores),
            "high_confidence_errors": sum(not s["correct"] and (s.get("confidence") or 0) >= .9 for s in scores),
            "slices": slices, "confusion": {k: dict(v) for k, v in confusion.items()}}


def paired_comparison(a, b, case_map, repetitions=2000, seed=20260923):
    """Paired accuracy difference on shared rows, with a bootstrap over task clusters."""
    aa = {r["case_id"]: r for r in a}
    bb = {r["case_id"]: r for r in b}
    common = sorted(aa.keys() & bb.keys())
    clusters = defaultdict(lambda: [0, 0, 0])
    counts = {"both_correct": 0, "a_only_correct": 0, "b_only_correct": 0, "both_wrong": 0}
    for cid in common:
        left = {s["question_id"]: s for s in aa[cid]["scores"]}
        right = {s["question_id"]: s for s in bb[cid]["scores"]}
        for qid in left.keys() & right.keys():
            ca, cb = int(left[qid]["correct"]), int(right[qid]["correct"])
            key = "both_correct" if ca and cb else "a_only_correct" if ca else "b_only_correct" if cb else "both_wrong"
            counts[key] += 1
            group = clusters[case_map[cid]["task"]]
            group[0] += ca
            group[1] += cb
            group[2] += 1
    values = list(clusters.values())
    n = sum(x[2] for x in values)
    if not n:
        return None
    rng = random.Random(seed)
    deltas = []
    for _ in range(repetitions):
        sample = [rng.choice(values) for _ in values]
        deltas.append(sum(x[0] - x[1] for x in sample) / sum(x[2] for x in sample))
    return {"cases": len(common), "questions": n, "task_clusters": len(values), "cluster_unit": "task", **counts,
            "accuracy_difference": sum(x[0] - x[1] for x in values) / n,
            "cluster_bootstrap_ci95": [quantile(deltas, .025), quantile(deltas, .975)],
            "repetitions": repetitions, "seed": seed}
