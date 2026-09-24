# Authoring Decision Bench v4

This is the contract for every category module in `authoring/bench/`. `authoring/bench/__init__.py` enforces the
mechanical parts; this page holds the judgement calls.

## What the bench is for

A visitor should be able to answer "can I use this model for my use case?" Every row is therefore a real record
that a real job would put in front of a model, with one bounded question and one defensible answer. A smart
generalist must be able to read the row and see why the answer is right within a couple of minutes.

## Non-negotiables

1. **Real records only.** No text written for the benchmark, no model-generated text, no templated scenarios.
   A label may be *derived by a written rule* from the record itself (a filing's item number, a version tag, a
   test result); say so in `label_origin="derived by rule"` or `"objective record"`.
2. **Open licences only.** `PERMISSIVE` in `__init__.py` lists them. Check the dataset's own licence *and* the
   terms of the text or images inside it; record the URL you actually read in `license_url` and quote or link the
   inner terms in `content_terms`. If you cannot establish both, do not build the task, and say so in your report.
   Stack Exchange dumps (2024 terms), BIRD (inconsistent), Rico (unstated), SpamAssassin (no licence) are known
   failures.
3. **Exactly one defensible answer.** If a careful reader could argue for a second option from the record alone,
   drop the row. Drop by written rule where you can; hand-drops go in a `SKIP` table with the reason, as v3 did.
4. **Deterministic sampling.** Order candidates by `rank(record_id)` and take the first that pass your written
   filters. Never look at model output. Never pick rows because they look interesting.
5. **Balanced, complete options.** Every option is the answer at least once; no option on more than 60% of rows;
   20–40 rows per task, target 30. Add an abstain option only when the data supports it and pass `abstain=`.
6. **Neutral titles.** `Artifact · subject`, 120 characters max, never containing the answer or hinting at it.
   Good: "Consumer complaint · calls to the workplace continue". Bad: "Debt collector harassment complaint".
7. **Plain rationales.** One or two sentences that point at the evidence in the record. For objective labels,
   state the fact ("the filing is an 8-K Item 5.02, a departure of a director or officer").
8. **Safe to publish.** No live secrets (replace with same-shape fakes as v3 did), no private individuals'
   personal data beyond what the source already publishes with consent, no gratuitous offensive content. When a
   dataset is about harmful content (moderation, toxicity), keep the rows a reader can stomach and say in the
   module docstring what you screened out.
9. **Right-sized inputs.** Median state under 5,000 characters where the artifact allows; never over 16,000.
   Trim with an explicit marker such as `…[2,184 chars truncated]`, never silently.
10. **Attribution.** One `dataset(...)` call per source with every field filled honestly, including BibTeX.

## Image rows

Tasks with `modality="image"` or `"text+image"` store each image under `data/assets/<category>/`, PNG or JPEG,
longest side at most 1600 px, at most 400 KB, and pass `assets=[{"path", "mime_type", "alt_text", "width",
"height"}]`. The `state` must also carry a faithful text rendering (OCR lines, table cells, or a plain
description that a person would write) so text-only models get a fair track. The alt text describes the image
without giving the answer.

## Module layout

```python
"""<category>: what the tasks are, in three lines each, then the written sampling rules."""
from . import dataset, task, row, rank, SOURCES as SOURCE_DIR, ASSETS

SOURCES = [{"dataset": "...", "url": "...", "path": "<folder>/<file>"}, ...]   # fetched by scripts/fetch_sources.py

def _datasets(): dataset(...)            # one per source
def _<task>(): ...                       # sampling, filters, SKIP table, row(...) calls
def define():
    _datasets()
    task("ENG-1", category="engineering", name="...", ask="...", instruction="...", options={...},
         shape="classify", input_type="code diff", modality="text", expertise="practitioner",
         contamination="medium", label_origin="objective record")
    _<task>()
```

Fetching: declare every upstream file in `SOURCES` (Hugging Face `datasets-server` rows API windows, GitHub raw
files at a pinned commit, or direct downloads; keep each dataset under ~50 MB, never whole multi-GB dumps), then
run `python3 scripts/fetch_sources.py --only <module>`. Do not run `--pin`; the maintainer pins hashes once.

Checking: `python3 scripts/build_bench.py --dry-run --only <module>` must end with `"problems": []`. Use
`--summary` to eyeball every row's id, answer and title, and `--dump <task-id-prefix>` to read whole rows.

## Task ids and names

Ids are `<PREFIX>-<n>`: ENG, AGT, SAF, SUP, COM, FIN, LEG, PRD, DAT, DOC, DSN. Names are 2–6 plain words that a
visitor would say ("Live secret or placeholder?", "Which tool to call", "Does the NDA say this?"). Questions are
12 words or fewer. Option keys are short snake_case, or the record's own identifiers for per-row options.

## Report

When the module passes, write a short report to the path given in your instructions: tasks built with row counts
and label balance, each dataset with the licence evidence you read, anything you dropped and why, and any
judgement call a maintainer should review. The report is read by a person, so keep it plain.
