"""Published results: results/<suite>/<model-id>/ holds the latest completed run for each model.

  metadata.json      model, request options, corpus version + sha256, harness commit, dates, coverage, totals
  predictions.jsonl  one line per row: answer, gold, correct, raw output text, confidence, tokens, cost, latency
  scores.json        overall, per-category and per-task accuracy with Wilson 95% intervals; cost, latency, tokens
  README.md          short generated summary

results/<suite>/leaderboard.json and leaderboard.md summarize every published model.
See docs/results-format.md for the full schema."""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from . import corpus
from .metrics import attempt_totals, consolidate_attempts, summarize
from .runner import read_jsonl, runs_dir, write_json
from .scoring import score_answer

SCHEMA_VERSION = 1
MAX_OUTPUT_CHARS = 20000
URL = re.compile(r"[a-z][a-z0-9+.-]*://[^\s\"'<>)]+", re.IGNORECASE)


def results_dir():
    return corpus.ROOT / "results"


def utc():
    return datetime.now(timezone.utc).isoformat()


def public_error(message):
    """Errors are published without URLs (an endpoint may echo internal addresses) and kept short."""
    if not message:
        return None
    return URL.sub("[url]", str(message))[:500]


def _tokens(usage):
    usage = usage or {}
    return {"input": usage.get("input_tokens"), "output": usage.get("output_tokens"),
            "cached_input": usage.get("cached_input_tokens"), "reasoning_output": usage.get("reasoning_output_tokens")}


def load_run(run_id):
    folder = runs_dir() / run_id
    if not (folder / "run.json").exists():
        raise ValueError(f"No run at runs/{run_id}")
    meta = json.loads((folder / "run.json").read_text())
    selected = meta["config"]["selected_case_ids"]
    wanted = set(selected)
    latest = {r["case_id"]: r for r in read_jsonl(folder / "results.jsonl", allow_partial=True)}
    records = [latest[i] for i in selected if i in latest]
    ledger = [a for a in read_jsonl(folder / "attempts.jsonl", allow_partial=True) if a["case_id"] in wanted]
    return meta, records, ledger


def predictions_from_run(records, ledger, case_map):
    """One public line per finished row. Tokens and cost cover every attempt, including failed paid retries."""
    attempts = consolidate_attempts(ledger)
    by_case = {}
    for a in attempts:
        by_case.setdefault(a["case_id"], []).append(a)
    out = []
    for r in records:
        case = case_map[r["case_id"]]
        q = case["questions"][0]
        answer = (r.get("answers") or {}).get(q["id"])
        own = sorted(by_case.get(r["case_id"], []), key=lambda a: (a.get("started_at") or "", a["attempt_id"]))
        totals = attempt_totals(own)
        text = r.get("output_text")
        row = {"row_id": r["case_id"], "task": case["task"], "category": case["category"], "status": r["status"],
               "answer": answer["label"] if answer else None, "gold": q["gold"],
               "correct": bool(answer and answer["label"] == q["gold"]),
               "confidence": answer["probabilities"][answer["label"]] if answer else None,
               "probabilities": answer["probabilities"] if answer else None,
               "output_text": text[:MAX_OUTPUT_CHARS] if isinstance(text, str) else None,
               "error": public_error(r.get("error")) if r["status"] != "ok" else None,
               "latency_ms": r.get("duration_ms"), "images_sent": r.get("images_sent", 0),
               "tokens": {k.removesuffix("_tokens"): totals["tokens"][k]
                          for k in ("input_tokens", "output_tokens", "cached_input_tokens", "reasoning_output_tokens")},
               "cost_usd": totals["cost_usd"], "cost_basis": totals["cost_bases"],
               "attempts": [{"status": "incomplete" if a.get("event") == "started" else a.get("status"),
                             "error": public_error(a.get("error")), "duration_ms": a.get("duration_ms"),
                             "cost_usd": a.get("cost_usd"), "cost_basis": a.get("cost_basis"),
                             "tokens": _tokens(a.get("usage"))} for a in own]}
        if isinstance(text, str) and len(text) > MAX_OUTPUT_CHARS:
            row["output_truncated"] = True
        out.append(row)
    return out


def records_from_predictions(predictions, run_id):
    """Rebuild scoring records and an attempt ledger from public predictions, so every published number can be
    recomputed from predictions.jsonl alone."""
    records, events = [], []
    for p in predictions:
        s = {"question_id": "decision", "type": "choice", **score_answer(p["gold"], p["answer"], p.get("probabilities"))}
        records.append({"run_id": run_id, "case_id": p["row_id"], "status": p["status"], "error": p.get("error"),
                        "duration_ms": p.get("latency_ms"), "scores": [s], "cost_usd": p.get("cost_usd"),
                        "tokens": p.get("tokens"), "attempt_count": len(p.get("attempts", [])),
                        "images_sent": p.get("images_sent", 0), "output_text": p.get("output_text")})
        for i, a in enumerate(p.get("attempts", [])):
            t = a.get("tokens") or {}
            events.append({"attempt_id": f"{p['row_id']}#{i}", "case_id": p["row_id"],
                           "event": "started" if a.get("status") == "incomplete" else "finished",
                           "status": a.get("status"), "cost_usd": a.get("cost_usd"), "cost_basis": a.get("cost_basis"),
                           "usage": {"input_tokens": t.get("input"), "output_tokens": t.get("output"),
                                     "cached_input_tokens": t.get("cached_input"),
                                     "reasoning_output_tokens": t.get("reasoning_output")}})
    return records, events


def scores_summary(metrics, manifest):
    tasks, categories = manifest.get("tasks", {}), manifest.get("categories", {})

    def rows(key, names):
        return [{"id": s["name"], "name": names.get(s["name"], {}).get("name", s["name"]),
                 **({"category": names[s["name"]].get("category")} if key == "task" and s["name"] in names else {}),
                 "rows": s["count"], "correct": s["correct"], "accuracy": s["accuracy"], "wilson95": s["wilson95"]}
                for s in metrics["slices"][key]]
    t = metrics["tokens"]
    return {"overall": {"rows": metrics["cases"], "correct": metrics["correct"], "accuracy": metrics["accuracy"],
                        "wilson95": metrics["accuracy_wilson95"], "errors": metrics["operational_errors"],
                        "macro_category_accuracy": metrics["macro_category_accuracy"],
                        "macro_task_f1": metrics["macro_task_f1"]},
            "by_category": rows("category", categories), "by_task": rows("task", tasks),
            "by_source_kind": rows("source_kind", {}),
            "calibration": {"brier": metrics["brier"], "log_loss": metrics["log_loss"],
                            "ece": metrics["reliability"]["ece"], "high_confidence_errors": metrics["high_confidence_errors"]},
            "cost": {"usd": metrics["cost_usd"], "coverage": metrics["cost_coverage"], "basis": metrics["cost_bases"],
                     "per_1000_rows_usd": metrics["cost_per_1000_cases_usd"]},
            "latency_ms": {k: metrics["latency_ms"][k] for k in ("p50", "p95", "p99", "mean")},
            "tokens": {"input": t["input_tokens"], "output": t["output_tokens"], "cached_input": t["cached_input_tokens"],
                       "reasoning_output": t["reasoning_output_tokens"], "coverage": t["input_tokens_coverage"]},
            "attempts": {k: metrics[k] for k in ("attempts", "retries", "attempt_errors", "incomplete_attempts")}}


def coverage(meta, records, corpus_rows):
    selected = meta["config"]["selected_case_ids"]
    errors = sum(r["status"] != "ok" for r in records)
    return {"rows_in_corpus": corpus_rows, "rows_selected": len(selected), "rows_completed": len(records),
            "rows_ok": len(records) - errors, "rows_error": errors,
            "full": len(selected) == corpus_rows and len(records) == corpus_rows}


def metadata_for(meta, records, cases, manifest, metrics, published_at=None):
    cfg = meta["config"]
    commits = [e.get("git", {}).get("commit") for e in meta.get("executions", [])]
    last_git = next((e.get("git") for e in reversed(meta.get("executions", [])) if e.get("git")), {}) or {}
    resolved = sorted({str(r["resolved_model"]) for r in records if r.get("resolved_model")})
    last = (meta.get("executions") or [{}])[-1]
    return {"schema_version": SCHEMA_VERSION, "suite": cfg["suite"],
            "model": {**meta.get("model", {"id": cfg["model_id"]}), "id": cfg["model_id"],
                      "provider": cfg["provider"], "api_model": cfg["api_model"], "resolved_models": resolved},
            "request": cfg.get("request", {}), "pricing": meta.get("pricing"), "prompt_version": cfg["prompt_version"],
            "corpus": {"version": cfg.get("corpus_version"), "sha256": cfg["corpus_sha256"],
                       "current": cfg["corpus_sha256"] == manifest["sha256"]},
            "harness": {"version": meta.get("harness_version"), "git_commit": last_git.get("commit"),
                        "git_dirty": last_git.get("dirty"), "git_commits": sorted({c for c in commits if c})},
            "run": {"run_id": meta["id"], "status": meta["status"], "created_at": meta.get("created_at"),
                    "completed_at": meta.get("completed_at"), "published_at": published_at,
                    "executions": len(meta.get("executions", [])), "jobs": last.get("jobs"),
                    "timeout_seconds": last.get("timeout_seconds"), "max_attempts": last.get("max_attempts"),
                    "endpoint_id": cfg.get("endpoint_id"), "platform": meta.get("platform")},
            "coverage": coverage(meta, records, len(cases)),
            "totals": {"correct": metrics["correct"], "accuracy": metrics["accuracy"],
                       "wilson95": metrics["accuracy_wilson95"], "errors": metrics["operational_errors"],
                       "cost_usd": metrics["cost_usd"], "cost_coverage": metrics["cost_coverage"],
                       "input_tokens": metrics["tokens"]["input_tokens"],
                       "output_tokens": metrics["tokens"]["output_tokens"],
                       "latency_p50_ms": metrics["latency_ms"]["p50"]}}


def export_run(run_id, cases=None, manifest=None):
    """(metadata, predictions, metrics) for a local run, in the published format. Nothing is written."""
    cases = cases or corpus.load_cases()
    manifest = manifest or corpus.load_manifest()
    case_map = {c["id"]: c for c in cases}
    meta, records, ledger = load_run(run_id)
    if meta["config"]["corpus_sha256"] != manifest["sha256"]:
        raise ValueError(f"Run {run_id} used corpus {meta['config']['corpus_sha256'][:12]}, not the current "
                         f"{manifest['sha256'][:12]}; its rows cannot be scored against the current answers")
    predictions = predictions_from_run(records, ledger, case_map)
    rebuilt, events = records_from_predictions(predictions, run_id)
    metrics = summarize(rebuilt, case_map, events)
    return metadata_for(meta, records, cases, manifest, metrics), predictions, metrics


def _fmt(v, kind):
    if v is None:
        return "n/a"
    return {"pct": f"{v:.1%}", "usd": f"${v:.4f}", "ms": f"{v:.0f} ms"}[kind]


def model_readme(metadata, scores):
    m, o = metadata["model"], scores["overall"]
    lo, hi = o["wilson95"]
    lines = [f"# {m.get('label', m['id'])} on {metadata['suite']}", "",
             "Generated by `python3 -m decision_bench publish`. Do not edit by hand.", "",
             f"- Model id: `{m['id']}` (provider `{m['provider']}`, model name sent: `{m['api_model']}`)",
             f"- Corpus: {metadata['corpus']['version']} (sha256 `{metadata['corpus']['sha256'][:16]}...`)",
             f"- Harness commit: `{metadata['harness']['git_commit'] or 'unknown'}`",
             f"- Run completed: {metadata['run']['completed_at']}", "",
             f"**Accuracy {_fmt(o['accuracy'], 'pct')}** ({o['correct']}/{o['rows']}; Wilson 95% "
             f"{_fmt(lo, 'pct')}-{_fmt(hi, 'pct')}). Rows with no valid answer: {o['errors']}.", "",
             f"Cost {_fmt(scores['cost']['usd'], 'usd')} (coverage {scores['cost']['coverage']:.0%}; "
             f"basis {', '.join(scores['cost']['basis'])}). Median latency {_fmt(scores['latency_ms']['p50'], 'ms')}.",
             "", "| Category | Correct | Accuracy | Wilson 95% |", "| --- | --- | --- | --- |"]
    for s in scores["by_category"]:
        lines.append(f"| {s['name']} | {s['correct']}/{s['rows']} | {_fmt(s['accuracy'], 'pct')} | "
                     f"{_fmt(s['wilson95'][0], 'pct')}-{_fmt(s['wilson95'][1], 'pct')} |")
    lines += ["", "| Task | Correct | Accuracy |", "| --- | --- | --- |"]
    for s in scores["by_task"]:
        lines.append(f"| {s['id']} {s['name']} | {s['correct']}/{s['rows']} | {_fmt(s['accuracy'], 'pct')} |")
    return "\n".join(lines) + "\n"


def publish(run_id, force=False):
    cases, manifest = corpus.load_cases(), corpus.load_manifest()
    meta, records, _ = load_run(run_id)
    if meta["config"]["corpus_sha256"] != manifest["sha256"]:
        # Rows and answers may differ between corpus versions, so such a run cannot be scored; not even --force.
        raise ValueError(f"Refusing to publish {run_id}: it used corpus {meta['config']['corpus_sha256'][:12]}, "
                         f"not the current {manifest['sha256'][:12]}. Re-run the model on the current corpus.")
    problems = []
    if meta.get("status") not in ("completed", "completed_with_errors"):
        problems.append(f"its status is {meta.get('status')!r}, not completed")
    cov = coverage(meta, records, len(cases))
    if not cov["full"]:
        problems.append(f"it covers {cov['rows_completed']} of {cov['rows_in_corpus']} rows")
    if problems and not force:
        raise ValueError(f"Refusing to publish {run_id}: " + "; ".join(problems) + ". Use --force to publish anyway.")
    metadata, predictions, metrics = export_run(run_id, cases, manifest)
    metadata["run"]["published_at"] = utc()
    if problems:
        metadata["published_with_warnings"] = problems
    scores = {"schema_version": SCHEMA_VERSION, "suite": metadata["suite"], "model_id": metadata["model"]["id"],
              "corpus_sha256": metadata["corpus"]["sha256"], **scores_summary(metrics, manifest)}
    suite_dir = results_dir() / metadata["suite"]
    target = suite_dir / metadata["model"]["id"]
    staging = suite_dir / f".{metadata['model']['id']}.tmp"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    write_json(staging / "metadata.json", metadata)
    write_json(staging / "scores.json", scores)
    (staging / "predictions.jsonl").write_text("".join(json.dumps(p, ensure_ascii=False, sort_keys=True) + "\n"
                                                       for p in predictions))
    (staging / "README.md").write_text(model_readme(metadata, scores))
    shutil.rmtree(target, ignore_errors=True)
    staging.replace(target)
    board = write_leaderboard(metadata["suite"])
    return {"published": str(target.relative_to(corpus.ROOT)), "rows": len(predictions),
            "accuracy": metrics["accuracy"], "leaderboard_models": len(board["models"]),
            "warnings": problems}


def load_published(suite):
    """[(metadata, predictions, scores)] for every model in results/<suite>/."""
    out = []
    folder = results_dir() / suite
    if not folder.is_dir():
        return out
    for model_dir in sorted(p for p in folder.iterdir() if p.is_dir() and not p.name.startswith(".")):
        meta_path = model_dir / "metadata.json"
        if not meta_path.exists():
            continue
        metadata = json.loads(meta_path.read_text())
        predictions = read_jsonl(model_dir / "predictions.jsonl")
        scores_path = model_dir / "scores.json"
        scores = json.loads(scores_path.read_text()) if scores_path.exists() else None
        out.append((metadata, predictions, scores))
    return out


def leaderboard(suite, published=None, manifest=None):
    manifest = manifest or corpus.load_manifest()
    published = load_published(suite) if published is None else published
    rows = []
    for metadata, _, scores in published:
        if scores is None:
            continue
        m, o = metadata["model"], scores["overall"]
        rows.append({"model_id": m["id"], "label": m.get("label"), "vendor": m.get("vendor"),
                     "provider": m.get("provider"), "api_model": m.get("api_model"),
                     "accuracy": o["accuracy"], "wilson95": o["wilson95"], "correct": o["correct"], "rows": o["rows"],
                     "errors": o["errors"], "cost_usd": scores["cost"]["usd"], "cost_coverage": scores["cost"]["coverage"],
                     "cost_per_1000_rows_usd": scores["cost"]["per_1000_rows_usd"],
                     "latency_p50_ms": scores["latency_ms"]["p50"],
                     "corpus_current": metadata["corpus"]["sha256"] == manifest["sha256"],
                     "full_coverage": metadata["coverage"]["full"], "completed_at": metadata["run"]["completed_at"]})
    rows.sort(key=lambda r: (-(r["accuracy"] or 0), r["model_id"]))
    return {"schema_version": SCHEMA_VERSION, "suite": suite, "corpus_version": manifest.get("version"),
            "corpus_sha256": manifest["sha256"],
            "note": "Sorted by accuracy. Overlapping Wilson intervals mean the order is not a reliable ranking.",
            "models": rows}


def write_leaderboard(suite):
    board = leaderboard(suite)
    folder = results_dir() / suite
    folder.mkdir(parents=True, exist_ok=True)
    write_json(folder / "leaderboard.json", board)
    lines = [f"# Decision Bench leaderboard ({suite})", "",
             "Generated by `python3 -m decision_bench publish`. Do not edit by hand. " + board["note"], "",
             "| Model | Provider | Accuracy | Wilson 95% | No answer | Cost per 1k rows | Median latency |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in board["models"]:
        flag = "" if r["corpus_current"] and r["full_coverage"] else " (partial or older corpus)"
        lines.append(f"| {r['label']}{flag} | {r['provider']} | {_fmt(r['accuracy'], 'pct')} | "
                     f"{_fmt(r['wilson95'][0], 'pct')}-{_fmt(r['wilson95'][1], 'pct')} | {r['errors']} | "
                     f"{_fmt(r['cost_per_1000_rows_usd'], 'usd')} | {_fmt(r['latency_p50_ms'], 'ms')} |")
    if not board["models"]:
        lines.append("| (no published results yet) | | | | | | |")
    (folder / "leaderboard.md").write_text("\n".join(lines) + "\n")
    return board


def check_published(cases, manifest):
    """Consistency checks for committed results (run by `validate` and CI). Returns a list of problems."""
    problems = []
    case_map = {c["id"]: c for c in cases}
    suite = manifest.get("suite")
    for metadata, predictions, scores in load_published(suite):
        where = f"results/{suite}/{metadata.get('model', {}).get('id')}"
        if metadata.get("corpus", {}).get("sha256") != manifest["sha256"]:
            problems.append(f"{where}: published on corpus {metadata.get('corpus', {}).get('sha256', '')[:12]}, "
                            "not the current one")
            continue
        seen = set()
        for p in predictions:
            c = case_map.get(p.get("row_id"))
            if c is None:
                problems.append(f"{where}: unknown row {p.get('row_id')}")
                continue
            if p["row_id"] in seen:
                problems.append(f"{where}: duplicate row {p['row_id']}")
            seen.add(p["row_id"])
            q = c["questions"][0]
            if p.get("gold") != q["gold"]:
                problems.append(f"{where}: {p['row_id']} gold differs from the corpus")
            if p.get("answer") is not None and p["answer"] not in q["options"]:
                problems.append(f"{where}: {p['row_id']} answer is not an option")
            if bool(p.get("correct")) != (p.get("answer") is not None and p.get("answer") == q["gold"]):
                problems.append(f"{where}: {p['row_id']} correct flag is inconsistent")
        if scores is None:
            problems.append(f"{where}: scores.json is missing")
            continue
        records, events = records_from_predictions(predictions, metadata["run"]["run_id"])
        expected = scores_summary(summarize(records, case_map, events), manifest)
        if expected["overall"] != scores.get("overall") or expected["by_task"] != scores.get("by_task"):
            problems.append(f"{where}: scores.json does not match predictions.jsonl")
    return problems
