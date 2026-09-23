"""Decision Bench v4: eleven use-case categories, fixed tasks, real rows.

A *task* is one fixed question with one fixed option set (or a per-row option set drawn from the record, such as
the functions offered in a request). A *row* is one real record from a public dataset with its answer. Category
modules call `dataset()` once per source, `task()` once per task and `row()` once per row; `build()` collects and
checks them. See docs/authoring-v4.md for the quality bar and the licence policy.

Rules enforced here:
- every task: a question of 12 words or fewer, 2–10 options with one-line descriptions, every option the answer
  at least once, no answer on more than 60% of a task's rows, 20–40 rows;
- every task declares its labels: decision shape, input type, modality, expertise needed, contamination risk;
- every row names its dataset, licence, URL, record id, original label and who decided the answer;
- every dataset is declared once with a licence that allows public redistribution including commercial use, for
  both the dataset and the text or images inside it;
- titles never contain the answer;
- image rows carry the image as an asset and a text rendering in the state, so text-only models get a fair track;
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
ASSETS = ROOT / "data/assets"
SUITE = "bench-v4"
VERSION = "4.0.0"

# Order here is display order on the site.
CATEGORIES = {
    "engineering": ("Engineering", "Code changes, commits, vulnerabilities and secrets."),
    "agents": ("AI agents & evals", "Tool calls, agent runs, model routing and judging model output."),
    "safety": ("Trust & safety", "Attacks on assistants, moderation and toxicity."),
    "support": ("Customer support", "Complaints, tickets and how they were resolved."),
    "commerce": ("Sales & commerce", "Search relevance, product catalogues and company profiles."),
    "finance": ("Finance", "SEC filings, receipts and financial tables."),
    "legal": ("Legal", "Contracts, clauses and terms of service."),
    "product": ("Product management", "Experiments, releases and user feedback."),
    "data": ("Data & analytics", "SQL, tables, charts and columns."),
    "documents": ("Documents & meetings", "Document pages, meeting transcripts and summaries."),
    "design": ("Design", "Screens and icons."),
}
MODULES = ["engineering", "agents", "safety", "support", "commerce", "finance", "legal", "product", "data",
           "documents", "design"]

SHAPES = {"classify": "Put the record in one of several classes.",
          "route": "Send the record to one of several destinations.",
          "verify": "Check a statement or an answer against evidence.",
          "compare": "Choose the better of two candidates.",
          "detect": "Say whether something is present.",
          "locate": "Pick the one item in the record that the question points at."}
MODALITIES = {"text", "image", "text+image"}
EXPERTISE = {"none": "A careful generalist can decide it.",
             "practitioner": "Someone who does this job can decide it.",
             "specialist": "Needs domain training (law, accounting, security)."}
CONTAMINATION = {"low", "medium", "high"}
LABEL_ORIGINS = {"human experts", "trained annotators", "crowd", "objective record", "self-declared", "derived by rule"}

TASKS = {}
ROWS = []
DATASETS = {}

# Licences that allow anyone to copy, modify and redistribute, including commercially. A dataset qualifies only
# if both its own licence and the terms of the text or images inside it are on this list. Share-alike is allowed;
# those rows carry the same licence.
PERMISSIVE = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "CC0-1.0", "Public domain",
              "CC-BY-3.0", "CC-BY-4.0", "CC-BY-SA-3.0", "CC-BY-SA-4.0", "ODC-BY-1.0", "CDLA-Permissive-1.0",
              "CDLA-Permissive-2.0",
              # The CVE Program's Terms of Use (SPDX cve-tou): a perpetual, royalty-free licence to reproduce and
              # distribute CVE records, provided MITRE's copyright notice is kept.
              "cve-tou"}
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
    license          SPDX-style id from PERMISSIVE (the dataset's own licence)
    license_url      the licence file or card that was actually read to confirm it
    content          one sentence: what the text or image in a row is and where it originally came from
    content_license  SPDX-style id for that underlying material (same as license when the authors wrote it)
    content_terms    plain-words note on the underlying material's terms, with a link where one exists
    labelled_by      who or what decided the answer, in plain words
    changes          what this benchmark changed (trimming, redaction, faked secrets, reformatting, resizing)
    selection        how rows were chosen, in one or two sentences
    citation         one-line citation
    bibtex           BibTeX entry for the paper or dataset
    """
    missing = [k for k in DATASET_FIELDS if not d.get(k)]
    assert not missing, f"dataset {d.get('id')}: missing {missing}"
    assert d["id"] not in DATASETS, f"dataset {d['id']} declared twice"
    DATASETS[d["id"]] = {k: d[k] for k in DATASET_FIELDS}


def task(ident, *, category, name, ask, instruction, options, shape, input_type, modality, expertise,
         contamination, label_origin, per_row_options=False, abstain=None):
    """Register a task.

    ident            e.g. "ENG-1": category prefix, dash, number
    name             2–5 plain words shown as the task's title, e.g. "Live secret or placeholder?"
    ask              the question shown to readers, 12 words or fewer
    instruction      the instruction sent to models: what the record is and how to decide, written once per task
    options          {key: one-line description}; keys are short snake_case or the record's own identifiers
    shape            one of SHAPES
    input_type       plain words, e.g. "chat message", "code diff", "contract", "receipt image", "SQL query"
    modality         "text", "image" or "text+image" (image tasks still carry a text rendering)
    expertise        one of EXPERTISE
    contamination    "low" (fresh derivation), "medium", "high" (a famous benchmark, likely in training data)
    label_origin     one of LABEL_ORIGINS, e.g. "objective record" for a repository's tests or a filing's own field
    per_row_options  True when the option set comes from the record itself; rows then pass options=
    abstain          the option key that means "none / not addressed / can't tell", or None
    """
    assert category in CATEGORIES, f"{ident}: unknown category {category}"
    assert re.fullmatch(r"[A-Z]{2,4}-\d+", ident), f"{ident}: task ids look like ENG-1"
    assert len(ask.split()) <= 12, f"{ident}: question longer than 12 words"
    assert 2 <= len(name.split()) <= 6, f"{ident}: task name should be 2–6 words"
    assert shape in SHAPES, f"{ident}: shape {shape!r}"
    assert modality in MODALITIES, f"{ident}: modality {modality!r}"
    assert expertise in EXPERTISE, f"{ident}: expertise {expertise!r}"
    assert contamination in CONTAMINATION, f"{ident}: contamination {contamination!r}"
    assert label_origin in LABEL_ORIGINS, f"{ident}: label_origin {label_origin!r}"
    assert per_row_options or 2 <= len(options) <= 10, f"{ident}: 2–10 options"
    assert abstain is None or per_row_options or abstain in options, f"{ident}: abstain key not an option"
    for k, desc in options.items():
        assert isinstance(desc, str) and 0 < len(desc) <= 160, f"{ident}: option {k!r} needs a one-line description"
    TASKS[ident] = dict(id=ident, category=category, name=name, ask=ask, instruction=instruction, options=options,
                        shape=shape, input_type=input_type, modality=modality, expertise=expertise,
                        contamination=contamination, label_origin=label_origin, per_row_options=per_row_options,
                        abstain=abstain)


def row(task_id, record_id, *, title, state, gold, rationale, source, options=None, note=None, assets=(), tags=()):
    """Register a row.

    title      neutral description of the record, never hinting at the answer, e.g. "Consumer complaint · calls to
               the workplace continue"
    state      the record as the model sees it (dict or string); for image rows include a text rendering (OCR text,
               table cells, or a plain description) under a clearly named key, e.g. "ocr_text"
    gold       the answer key (an option key)
    rationale  one or two sentences pointing at the evidence; for objective labels, say what the record says
    source     dict(dataset_id, dataset, license, url, citation, record_id, original_label, labelled_by)
    assets     for image rows: [{"path": "data/assets/<category>/<file>.png", "mime_type": "image/png",
               "alt_text": "...", "width": W, "height": H}]; the file must exist
    note       optional one line of context shown to readers after the answer (never sent to models)
    """
    t = TASKS[task_id]
    opts = options if t["per_row_options"] else t["options"]
    assert opts and gold in opts, f"{task_id}/{record_id}: gold {gold!r} not in options"
    assert source and source.get("dataset_id") in DATASETS, f"{task_id}/{record_id}: source must name a declared dataset"
    ident = f"{task_id.lower()}-{record_id}"
    ident = re.sub(r"[^a-z0-9.-]+", "-", ident.lower()).strip("-")
    assets = [dict(a) for a in assets]
    for a in assets:
        assert (ROOT / a["path"]).is_file(), f"{ident}: missing asset {a['path']}"
        assert a.get("mime_type", "").startswith("image/") and a.get("alt_text"), f"{ident}: asset needs mime_type and alt_text"
    assert (t["modality"] == "text") == (not assets), f"{ident}: modality {t['modality']} but {len(assets)} assets"
    provenance = (f"Real record from {source['dataset']} ({source['license']}). {source.get('citation', '')} "
                  f"Answer from {source['labelled_by']}.")
    ROWS.append({
        "id": ident, "suite": SUITE, "category": t["category"], "category_name": CATEGORIES[t["category"]][0],
        "task": task_id, "task_name": t["name"], "source_kind": "real",
        "title": title, **({"note": note} if note else {}),
        "provenance": provenance.strip(), "source": source,
        "modality": t["modality"], "tags": list(tags), "state": state, "assets": assets,
        "questions": [{"id": "decision", "type": "choice", "ask": t["ask"], "instructions": t["instruction"],
                       "options": opts, "option_order": option_order(ident, opts, "choice"),
                       "gold": gold, "rationale": rationale}],
    })


def define(modules=None):
    from importlib import import_module
    TASKS.clear()
    ROWS.clear()
    DATASETS.clear()
    for name in (modules or MODULES):
        import_module(f"{__name__}.{name}").define()


def length_band(rows):
    sizes = sorted(len(json.dumps(r["state"], ensure_ascii=False)) for r in rows)
    median = sizes[len(sizes) // 2] if sizes else 0
    return "short" if median < 1000 else "medium" if median <= 5000 else "long"


def task_summary(task_id, rows):
    """The task's labels as published in the manifest."""
    t = TASKS[task_id]
    items = [r for r in rows if r["task"] == task_id]
    datasets = sorted({r["source"]["dataset_id"] for r in items})
    return {k: t[k] for k in ("category", "name", "ask", "instruction", "shape", "input_type", "modality",
                              "expertise", "contamination", "label_origin", "per_row_options", "abstain")} | {
        "options": t["options"], "rows": len(items), "length": length_band(items), "datasets": datasets}


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
        text = r.get("title", "").lower().replace("_", " ")
        if text and re.search(rf"\b{answer}\b", text) and len(answer) > 2:
            problems.append(f"{r['id']}: title contains the answer '{q['gold']}'")
        if len(r["title"]) > 120:
            problems.append(f"{r['id']}: title longer than 120 characters")
        if len(q["rationale"].split()) < 4:
            problems.append(f"{r['id']}: rationale too short")
        missing = {"dataset_id", "dataset", "license", "url", "record_id", "original_label", "labelled_by"} - set(r["source"])
        if missing:
            problems.append(f"{r['id']}: source missing {sorted(missing)}")
        d = DATASETS.get(r["source"].get("dataset_id"))
        if d is None:
            problems.append(f"{r['id']}: dataset_id {r['source'].get('dataset_id')!r} is not declared")
        elif r["task"] not in d["tasks"]:
            problems.append(f"{r['id']}: dataset {d['id']} does not list task {r['task']}")
        for a in r["assets"]:
            if (ROOT / a["path"]).stat().st_size > 400_000:
                problems.append(f"{r['id']}: asset {a['path']} is over 400 KB")
    ids = collections.Counter(r["id"] for r in rows)
    problems += [f"duplicate row id {i}" for i, n in ids.items() if n > 1]
    titles = collections.Counter((r["task"], r["title"]) for r in rows)
    problems += [f"{t}: title used {n} times: {title!r}" for (t, title), n in titles.items() if n > 1]
    states = collections.Counter((r["task"], json.dumps(r["state"], sort_keys=True)) for r in rows)
    problems += [f"{t}: identical state used {n} times" for (t, _), n in states.items() if n > 1]
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
        if not 20 <= len(items) <= 40:
            problems.append(f"{task_id}: {len(items)} rows (target 30, allowed 20–40)")
    for task_id in TASKS:
        if task_id not in by_task:
            problems.append(f"{task_id}: no rows")
    for d in DATASETS.values():
        for field in ("license", "content_license"):
            if d[field] not in PERMISSIVE:
                problems.append(f"dataset {d['id']}: {field} {d[field]!r} does not allow public redistribution")
        if not any(r["source"].get("dataset_id") == d["id"] for r in rows):
            problems.append(f"dataset {d['id']}: declared but no rows use it")
    return problems


def build(modules=None):
    define(modules)
    return list(ROWS)
