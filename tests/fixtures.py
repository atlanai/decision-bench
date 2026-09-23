"""A tiny self-contained repository tree for tests: corpus, manifest, config/models.json, docs."""
import contextlib
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from decision_bench import corpus

FAKE_KEY = "fixture-key-0000"


def row(ident, task, category, gold, options=("a", "b")):
    return {"id": ident, "title": f"TITLE_{ident}", "task": task, "category": category,
            "category_name": category.title(), "source_kind": "real", "provenance": f"PROVENANCE_{ident}",
            "note": f"NOTE_{ident}", "source": {"dataset": "SOURCE_DATASET", "record_id": ident},
            "state": {"message": f"Message {ident[::-1]}"}, "assets": [], "tags": [],
            "questions": [{"id": "decision", "type": "choice", "ask": f"ASK_{ident}?",
                           "instructions": "Pick one.", "options": {o: o.upper() for o in options},
                           "option_order": list(reversed(options)), "gold": gold,
                           "rationale": f"RATIONALE_{ident}"}]}


ROWS = [row("r1", "T-1", "alpha", "a"), row("r2", "T-1", "alpha", "b"), row("r3", "T-2", "beta", "a")]
MODELS = {"models": [
    {"id": "fake-model", "label": "Fake Model", "vendor": "Test", "provider": "openai-compatible",
     "model": "fake/model-1", "request": {"response_format": "json_schema", "max_output_tokens": 256},
     "pricing": {"input_per_mtok": 1.0, "output_per_mtok": 2.0, "source_url": "https://example.com/pricing"}},
    {"id": "fake-typesafe", "label": "Fake TypeSafe", "vendor": "Test", "provider": "typesafe", "model": "jev-test"},
    {"id": "fake-claude", "label": "Fake Claude", "vendor": "Test", "provider": "claude-cli", "model": "claude-test",
     "request": {"reasoning_effort": "low"}},
]}


def build(root, rows=ROWS):
    root = Path(root)
    folder = root / "data/corpus/mini"
    folder.mkdir(parents=True)
    (folder / "cases.jsonl").write_text("".join(corpus.canonical(r) + "\n" for r in rows))
    manifest = {"version": "0.0.1", "suite": "mini", "label": "Mini", "sha256": corpus.digest(rows),
                "categories": {"alpha": {"name": "Alpha"}, "beta": {"name": "Beta"}},
                "tasks": {"T-1": {"category": "alpha", "name": "Task one", "ask": "?"},
                          "T-2": {"category": "beta", "name": "Task two", "ask": "?"}},
                "counts": {"cases": len(rows), "questions": len(rows)}}
    (folder / "manifest.json").write_text(json.dumps(manifest))
    (root / "data/corpus/current.json").write_text(json.dumps({"path": "data/corpus/mini/cases.jsonl"}))
    (root / "config").mkdir()
    (root / "config/models.json").write_text(json.dumps(MODELS))
    (root / "docs").mkdir()
    (root / "docs/protocol.md").write_text("Protocol")
    return manifest


@contextlib.contextmanager
def repo(env=None, rows=ROWS):
    """Point the package at a temporary tree, with only the given DECISION_BENCH_* / TYPESAFE_* variables set."""
    with tempfile.TemporaryDirectory() as tmp:
        build(tmp, rows)
        clean = {k: v for k, v in os.environ.items()
                 if not k.startswith(("DECISION_BENCH_", "TYPESAFE_", "LITELLM_"))}
        clean.update(env or {})
        with patch.object(corpus, "ROOT", Path(tmp)), patch.dict(os.environ, clean, clear=True):
            yield Path(tmp)
