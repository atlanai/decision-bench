---
pretty_name: Decision Bench
language:
  - en
license: other
license_name: mixed-source-licenses
license_link: https://huggingface.co/datasets/atlanai/decision-bench/blob/main/DATA_LICENSE.md
size_categories:
  - 1K<n<10K
task_categories:
  - question-answering
  - text-classification
tags:
  - benchmark
  - evaluation
  - decision-making
  - multimodal
configs:
  - config_name: bench-v4
    default: true
    data_files:
      - split: test
        path: test.jsonl
---

# Decision Bench

An open benchmark for how accurately, quickly, and cheaply language models make bounded decisions on real data.

**1,071 rows · 35 tasks · 11 use cases · 36 public source datasets**

[Leaderboard](https://decisionbench.ai/) · [Code and evaluation harness](https://github.com/atlanai/decision-bench) · [Protocol](docs/protocol.md) · [Task catalog](docs/tasks.md)

## Background and analysis

[Putting Jev to the test with Decision Bench](https://x.com/rohanatlan/article/2103188107143307541) — Rohan Goel, 24 September 2026.

The launch article explains why Decision Bench was built, how its 35 tasks use real public records, and what the initial 12-model evaluation found about Jev’s accuracy, latency, cost, and task-specific limitations. For current model coverage and results, use the [live leaderboard](https://decisionbench.ai/); the article describes the launch snapshot.

## What it measures

Decision Bench tests choices that software asks models to make: route a complaint, identify a clause, select a tool, classify a code change, or pick the total from a receipt. Each row has one question with at least two options. Answers come from the source dataset's label or an objective record. There are 122 image-bearing rows referencing 106 unique images.

The model receives evidence, instructions, and options. It returns one choice and a probability for every option. Invalid responses count as incorrect. The harness measures accuracy, calibration, latency, token usage, and cost.

## Load the dataset

```python
import json
from datasets import load_dataset

dataset = load_dataset("atlanai/decision-bench", "bench-v4", split="test")
row = dataset[0]
state = json.loads(row["state"])
questions = json.loads(row["questions"])
```

The viewer export stores `state`, `questions`, `source`, and `assets` as JSON strings so heterogeneous evidence and variable option keys load consistently. Other fields retain their original types. Decode these four fields with `json.loads` to recover the original row objects. Asset paths are relative to this repository root.

The original corpus is preserved byte-for-byte at `data/corpus/bench-v4/cases.jsonl`. Use the [official harness](https://github.com/atlanai/decision-bench) for comparable evaluations; passing the entire dataset row to a model leaks the answers. Gold choices, rationales, provenance, and source metadata must be withheld from model inputs.

## Version and reproducibility

- Release version: **1.0**; frozen corpus identifier: **bench-v4**.
- Canonical corpus SHA-256: `{{CORPUS_SHA256}}`.
- `release.json` records the source commit and hashes of packaged files.
- This is an evaluation-only test split; no training or validation split is provided.

## Sources, licenses, and privacy

The benchmark software is MIT licensed. **The corpus is not covered by a blanket MIT license.** Rows, images, and source excerpts retain their individual licenses and attribution, including applicable share-alike terms. See [data license guidance](DATA_LICENSE.md), the [source catalog](data/SOURCES.md), packaged source notices, and the [data and privacy review](docs/data-release-review.md).

The release review records two open packaging/interpretation notes: deepset's pinned card contains both Apache-2.0 and CC-BY-4.0 declarations; source-specific code notices and Wikipedia-derived share-alike requirements must remain intact. SEC filing reuse is grounded in the SEC dissemination policy, rather than a blanket claim that privately authored filings are public domain.

The corpus includes public complaints, contracts, filings, toxicity examples, and adversarial prompts. Some content may be offensive or contain benchmark identities and public business contact details. These are evaluation records, not actual customer records to act upon. See [SECURITY.md](SECURITY.md) for private reports and removal requests.

## Limitations

Public datasets may appear in model training data. Small accuracy differences may be sampling noise. Text-only and vision runs receive different available modalities; consult the [viewer scoring policy](https://github.com/atlanai/decision-bench/blob/main/docs/viewer-scoring.md). Latency includes retries and network or CLI overhead; cost can be provider-reported or estimated, and unknown cost remains unknown. These tasks do not establish reliability in production or suitability for high-stakes decisions.

## Citation

See [CITATION.cff](CITATION.cff). Identify the corpus hash and harness commit in results, and cite the source datasets behind the tasks used, as listed in [data/SOURCES.md](data/SOURCES.md).
