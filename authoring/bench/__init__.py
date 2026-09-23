"""Decision Bench v3: seven categories, fourteen task types, mostly real rows.

A *task* is one fixed question with one fixed option set. A *row* is one input (a real record from a public
dataset, or a clearly badged written example) with its answer. Category modules call `task()` once per task
and `row()` once per row, then `build()` collects and checks them.

Rules enforced here (see docs/tasks.md):
- every task: short question (≤ 12 words), 2–6 options, each option the answer at least once,
  no answer on more than 60% of a task's rows;
- every real row names its dataset, license, URL, record id, original label and who labelled it;
- every dataset is declared once in its module's DATASETS (see `dataset()`), with a license that allows public
  redistribution including commercial use, for both the dataset and the text it contains;
- titles never contain the answer's option key or label text;
- rows are sampled deterministically (see `rank`), never by looking at model output.
"""
from __future__ import annotations

import collections
import hashlib
import json
import re
from pathlib import Path

from ..common import option_order

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCES = ROOT / "data/sources"
SUITE = "bench-v3"

CATEGORIES = {
    "prompt-injection": ("Prompt injection", "Spot inputs that try to take over an assistant."),
    "pii": ("Sensitive data", "Find personal data and secrets that must be masked or removed."),
    "trace-classification": ("Trace classification", "Say what went wrong in an agent run, and where."),
    "trace-routing": ("Trace routing", "Send a request to the right tool or team."),
    "eval-judging": ("Eval judging", "Judge a model's answer against its sources or an alternative."),
    "contract-policy": ("Contract and policy checks", "Check what a legal document actually says."),
    "skill-improvement": ("Skill improvement", "Diagnose a failing agent skill and decide on a fix."),
}
MODULES = ["prompt_injection", "pii", "trace_classification", "trace_routing", "eval_judging",
           "contract_policy", "skill_improvement"]

TASKS = {}
ROWS = []
DATASETS = {}

# Licenses that allow anyone to copy, modify and redistribute, including commercially. A dataset qualifies only
# if both its own license and the terms of the text inside it (e.g. the web pages or news it was built from)
# are on this list. Share-alike (CC BY-SA) is allowed; those rows carry the same license.
PERMISSIVE = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "CC0-1.0", "Public domain",
              "CC-BY-4.0", "CC-BY-SA-3.0", "CC-BY-SA-4.0", "ODC-BY-1.0", "CDLA-Permissive-2.0"}
DATASET_FIELDS = ("id", "name", "tasks", "homepage", "license", "license_url", "content", "content_license",
                  "content_terms", "labelled_by", "changes", "selection", "citation", "bibtex")


def rank(key):
    """Deterministic, model-independent sampling order."""
    return hashlib.sha256(str(key).encode()).hexdigest()


def dataset(**d):
    """Declare a source dataset (one call per dataset, from the module that samples it).

    id               short slug, referenced by each row's source["dataset_id"]
    name             display name
    tasks            task ids that use it
    homepage         project page or repository
    license          SPDX-style id from PERMISSIVE (the dataset's own license)
    license_url      the license file or card that was actually read to confirm it
    content          one sentence: what the text in a row is and where it originally came from
    content_license  SPDX-style id for that underlying text (same as license when the dataset authors wrote it)
    content_terms    plain-words note on the underlying text's terms, with a link where one exists
    labelled_by      who or what decided the answer, in plain words
    changes          what this benchmark changed (trimming, redaction, faked secrets, reformatting)
    selection        how rows were chosen, in one or two sentences
    citation         one-line citation
    bibtex           BibTeX entry for the paper or dataset
    """
    missing = [k for k in DATASET_FIELDS if not d.get(k)]
    assert not missing, f"dataset {d.get('id')}: missing {missing}"
    assert d["id"] not in DATASETS, f"dataset {d['id']} declared twice"
    DATASETS[d["id"]] = {k: d[k] for k in DATASET_FIELDS}


def task(ident, *, category, name, ask, instruction, options, per_row_options=False):
    """Register a task. `options` maps short keys to one-line descriptions.

    With per_row_options=True the option set differs per row (e.g. the functions offered in that row);
    rows then pass `options=` themselves and the task's `options` is only a description of the scheme.
    """
    assert category in CATEGORIES, category
    assert len(ask.split()) <= 12, f"{ident}: question longer than 12 words"
    TASKS[ident] = dict(id=ident, category=category, name=name, ask=ask, instruction=instruction,
                        options=options, per_row_options=per_row_options)


def row(task_id, record_id, *, title, state, gold, rationale, source=None, summary=None, options=None,
        note=None, tags=()):
    """Register a row.

    source: None for a written example, else dict(dataset, license, url, citation, record_id, original_label,
            labelled_by) — `labelled_by` in plain words, e.g. "expert annotators", "the repository's tests".
    note:   optional one-line context shown to readers after the answer (never sent to models).
    """
    t = TASKS[task_id]
    opts = options if t["per_row_options"] else t["options"]
    assert opts and gold in opts, f"{task_id}/{record_id}: gold {gold!r} not in options"
    ident = f"{task_id.lower()}-{record_id}"
    ident = re.sub(r"[^a-z0-9.-]+", "-", ident.lower()).strip("-")
    real = source is not None
    provenance = (f"Real record from {source['dataset']} ({source['license']}). {source.get('citation', '')} "
                  f"Answer from {source['labelled_by']}." if real else
                  "Written example (authored for this benchmark; no real, redistributable data exists for this "
                  "task). MIT licensed.")
    ROWS.append({
        "id": ident, "suite": SUITE, "category": t["category"], "category_name": CATEGORIES[t["category"]][0],
        "task": task_id, "task_name": t["name"], "workload": CATEGORIES[t["category"]][0],
        "family": t["category"], "source_kind": "real" if real else "written",
        "title": title, **({"summary": summary} if summary else {}), **({"note": note} if note else {}),
        "provenance": provenance.strip(), **({"source": source} if real else {}),
        "modality": "text", "tags": list(tags), "state": state, "assets": [],
        "questions": [{"id": "decision", "type": "choice", "ask": t["ask"], "instructions": t["instruction"],
                       "options": opts, "option_order": option_order(ident, opts, "choice"),
                       "gold": gold, "rationale": rationale}],
    })


def define():
    from importlib import import_module
    TASKS.clear()
    ROWS.clear()
    DATASETS.clear()
    for name in MODULES:
        import_module(f"{__name__}.{name}").define()


def check(rows):
    problems = []
    by_task = collections.defaultdict(list)
    for r in rows:
        by_task[r["task"]].append(r)
        q = r["questions"][0]
        size = len(json.dumps(r["state"], ensure_ascii=False))
        if size > 16000:
            problems.append(f"{r['id']}: state is {size} characters (limit 16,000)")
        answer = re.escape(q["gold"].lower().replace("_", " "))
        for field in ("title", "summary"):
            text = r.get(field, "").lower().replace("_", " ")
            if text and re.search(rf"\b{answer}\b", text):
                problems.append(f"{r['id']}: {field} contains the answer '{q['gold']}'")
        if r["source_kind"] == "real":
            missing = {"dataset_id", "dataset", "license", "url", "record_id", "original_label",
                       "labelled_by"} - set(r["source"])
            if missing:
                problems.append(f"{r['id']}: source missing {sorted(missing)}")
            d = DATASETS.get(r["source"].get("dataset_id"))
            if d is None:
                problems.append(f"{r['id']}: dataset_id {r['source'].get('dataset_id')!r} is not declared")
            elif r["task"] not in d["tasks"]:
                problems.append(f"{r['id']}: dataset {d['id']} does not list task {r['task']}")
    ids = collections.Counter(r["id"] for r in rows)
    problems += [f"duplicate row id {i}" for i, n in ids.items() if n > 1]
    titles = collections.Counter((r["task"], r["title"]) for r in rows)
    problems += [f"{t}: title used {n} times: {title!r}" for (t, title), n in titles.items() if n > 1]
    for task_id, items in by_task.items():
        t = TASKS[task_id]
        golds = collections.Counter(r["questions"][0]["gold"] for r in items)
        if not t["per_row_options"]:
            unused = set(t["options"]) - set(golds)
            if unused:
                problems.append(f"{task_id}: options never the answer: {sorted(unused)}")
        top, n = golds.most_common(1)[0]
        if n > 0.6 * len(items):
            problems.append(f"{task_id}: '{top}' is the answer on {n}/{len(items)} rows")
        if not 12 <= len(items) <= 40:
            problems.append(f"{task_id}: {len(items)} rows (target 24–36)")
    for task_id in TASKS:
        if task_id not in by_task:
            problems.append(f"{task_id}: no rows")
    for d in DATASETS.values():
        for field in ("license", "content_license"):
            if d[field] not in PERMISSIVE:
                problems.append(f"dataset {d['id']}: {field} {d[field]!r} does not allow public redistribution")
        used = sum(r.get("source", {}).get("dataset_id") == d["id"] for r in rows)
        if not used:
            problems.append(f"dataset {d['id']}: declared but no rows use it")
    return problems


def build():
    define()
    return list(ROWS)
