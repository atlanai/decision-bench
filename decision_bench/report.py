"""Build the static site's data from results/ (the public source of truth) and, optionally, local runs/.

Writes into site/:
  data.json      everything the viewer renders (schema in docs/results-format.md)
  corpus.json    the active corpus rows, including reader-only fields (rationale, note, source)
  assets/rows/   copies of the row images under data/assets/
  datasets.json  copy of data/datasets.json, when it exists
  protocol.txt   copy of docs/protocol.md
  results/       copy of results/, so published files can be downloaded from the site
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone

from . import config, corpus
from .corpus import PROMPT_VERSION, SYSTEM
from .metrics import paired_comparison, summarize
from .results import export_run, leaderboard, load_published, records_from_predictions
from .runner import runs_dir

DATA_SCHEMA_VERSION = 2


def _run_entry(metadata, metrics, source, cases):
    m, run = metadata["model"], metadata["run"]
    return {"id": run["run_id"], "source": source, "status": run["status"],
            "created_at": run.get("created_at"), "completed_at": run.get("completed_at"),
            "published_at": run.get("published_at"), "model_id": m["id"], "model": m,
            "config": {"model_id": m["id"], "provider": m["provider"], "api_model": m.get("api_model"),
                       "request": metadata.get("request", {}), "suite": metadata["suite"],
                       "corpus_version": metadata["corpus"]["version"], "corpus_sha256": metadata["corpus"]["sha256"],
                       "prompt_version": metadata.get("prompt_version"), "endpoint_id": metadata["run"].get("endpoint_id"),
                       "selected_case_ids": [c["id"] for c in cases]},
            "coverage": metadata["coverage"], "current_corpus": metadata["corpus"]["current"],
            "harness": metadata.get("harness"), "pricing": metadata.get("pricing"),
            "files": ({k: f"results/{metadata['suite']}/{m['id']}/{f}" for k, f in
                       [("metadata", "metadata.json"), ("predictions", "predictions.jsonl"),
                        ("scores", "scores.json"), ("readme", "README.md")]} if source == "published" else None),
            "metrics": metrics}


def collect(include_runs=False):
    cases, manifest = corpus.load_cases(), corpus.load_manifest()
    case_map = {c["id"]: c for c in cases}
    suite = manifest.get("suite")
    entries, records = {}, {}
    for metadata, predictions, _ in load_published(suite):
        if metadata["corpus"]["sha256"] != manifest["sha256"]:
            print(f"skip results/{suite}/{metadata['model']['id']}: older corpus", file=sys.stderr)
            continue
        run_id = metadata["run"]["run_id"]
        rows, events = records_from_predictions(predictions, run_id)
        selected = [case_map[p["row_id"]] for p in predictions]
        entries[run_id] = _run_entry(metadata, summarize(rows, case_map, events), "published", selected)
        records[run_id] = rows
    if include_runs and runs_dir().is_dir():
        for path in sorted(runs_dir().glob("*/run.json")):
            run_id = path.parent.name
            try:
                metadata, predictions, metrics = export_run(run_id, cases, manifest)
            except (ValueError, KeyError, json.JSONDecodeError) as exc:
                print(f"skip runs/{run_id}: {exc}", file=sys.stderr)
                continue
            selected = [case_map[i] for i in json.loads(path.read_text())["config"]["selected_case_ids"] if i in case_map]
            # A local run replaces a published copy of the same run id: it may have been resumed since.
            entries[run_id] = _run_entry(metadata, metrics, "local", selected)
            records[run_id] = records_from_predictions(predictions, run_id)[0]
    return cases, manifest, list(entries.values()), records


def build(include_runs=False):
    cases, manifest, runs, records = collect(include_runs)
    case_map = {c["id"]: c for c in cases}
    suite = manifest.get("suite")
    comparable = [r for r in runs if r["current_corpus"] and r["coverage"]["full"]]
    comparisons = []
    for i, a in enumerate(comparable):
        for b in comparable[i + 1:]:
            paired = paired_comparison(records[a["id"]], records[b["id"]], case_map)
            if paired:
                comparisons.append({"a": a["id"], "b": b["id"], "corpus_sha256": manifest["sha256"], **paired})
    published = sum(r["source"] == "published" for r in runs)
    models = [{**config.display(m), "api_model": m["model"], "request": m.get("request", {}),
               "pricing": m.get("pricing"), "vision": bool(m.get("vision"))} for m in config.load_models()]
    output = {"schema_version": DATA_SCHEMA_VERSION, "generated_at": datetime.now(timezone.utc).isoformat(),
              "suite": suite, "corpus_sha256": manifest["sha256"], "manifest": manifest,
              "inventory": {"cases": len(cases), "questions": sum(len(c["questions"]) for c in cases),
                            "tasks": len({c["task"] for c in cases}), "categories": len({c["category"] for c in cases}),
                            "models_configured": len(models), "runs": len(runs), "published_runs": published},
              "prompt": {"version": PROMPT_VERSION, "system": SYSTEM},
              "models": models,
              "leaderboard": leaderboard(suite, manifest=manifest)["models"],
              "runs": runs,
              "results": [r for rid in records for r in records[rid]],
              "comparisons": comparisons,
              "include_runs": include_runs,
              "cases": cases}
    site = corpus.ROOT / "site"
    site.mkdir(exist_ok=True)
    temporary = site / "data.json.tmp"
    temporary.write_text(json.dumps(output, ensure_ascii=False, allow_nan=False))
    temporary.replace(site / "data.json")
    (site / "corpus.json").write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n")
    datasets = corpus.ROOT / "data/datasets.json"
    if datasets.exists():
        shutil.copyfile(datasets, site / "datasets.json")
    protocol = corpus.ROOT / "docs/protocol.md"
    if protocol.exists():
        shutil.copyfile(protocol, site / "protocol.txt")
    # Row images (data/assets/<category>/…) are served from site/assets/rows/ so the viewer can show them.
    shutil.rmtree(site / "assets" / "rows", ignore_errors=True)
    if (corpus.ROOT / "data/assets").is_dir():
        shutil.copytree(corpus.ROOT / "data/assets", site / "assets" / "rows",
                        ignore=shutil.ignore_patterns(".*"))
    shutil.rmtree(site / "results", ignore_errors=True)
    if (corpus.ROOT / "results").is_dir():
        shutil.copytree(corpus.ROOT / "results", site / "results",
                        ignore=shutil.ignore_patterns(".*"))
    summary = {"suite": suite, "rows": len(cases), "runs": len(runs), "published": published,
               "local": len(runs) - published, "site": "site/data.json"}
    print(json.dumps(summary))
    return output
