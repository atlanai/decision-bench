<p align="center">
  <img src="docs/assets/decision-bench-frontier.png" alt="Decision Bench" width="960">
</p>

# Decision Bench

An open benchmark for how accurately, quickly, and cheaply language models make bounded decisions on real data.

![1,071 benchmark rows](https://img.shields.io/badge/rows-1%2C071-3028C8?style=flat-square&labelColor=161616)
![35 benchmark tasks](https://img.shields.io/badge/tasks-35-ED9FC8?style=flat-square&labelColor=161616)
![12 models evaluated](https://img.shields.io/badge/models-12-ED9FC8?style=flat-square&labelColor=161616)
[![Code license: MIT](https://img.shields.io/badge/code-MIT-3028C8?style=flat-square&labelColor=161616)](LICENSE)

[Explore the leaderboard](https://decisionbench.ai/) · [Read the docs](docs/protocol.md) · [Dataset on Hugging Face](https://huggingface.co/datasets/atlanai/decision-bench)

Read the launch article: [Putting Jev to the test with Decision Bench](https://x.com/rohanatlan/article/2103188107143307541) by Rohan Goel, covering the benchmark’s design and the initial 12-model results.

## What it measures

Decision Bench tests choices that software asks models to make: route a complaint, identify a clause, select a tool, classify a code change, or pick the total from a receipt.

The current corpus, **bench-v4**, contains **1,071 rows across 35 tasks and 11 use cases**, sampled from **36 public datasets**. Answers come from the dataset's own label or an objective record. Every row has exactly one choice question with two or more options; 122 rows carry an image as well as a text rendering of it.

The model receives the evidence, instructions, and options. Answers, rationales, and source metadata are withheld. It returns a choice and a probability for every option. Invalid responses count as incorrect.

We report accuracy with 95% confidence intervals, calibration, latency, token usage, and cost. The [evaluation protocol](docs/protocol.md) describes the inputs, scoring, and integrity checks.

## Published results

**Results for 12 models on bench-v4 were published on 23 September 2026.** Browse the [leaderboard and per-task results](https://decisionbench.ai/), or inspect the [published runs](results/README.md) for predictions, scores, and run metadata.

Start with the task you need the model to perform. Small accuracy differences may be noise, and public datasets may appear in model training data. Text-only models receive available text renderings; vision models also receive the images. The viewer excludes image-only icon cases when the image was not sent and marks them N/E; see the [viewer scoring policy](docs/viewer-scoring.md). Latency includes retries and network or CLI overhead. Cost is provider-reported or estimated, with unknown cost recorded as unknown.

## Quick start

Python 3.11 or newer. There are no runtime dependencies beyond the standard library. The corpus is committed, so you do not need to download the upstream datasets.

From the repository root:

```sh
python3 -m decision_bench validate
cp .env.example .env
# Set DECISION_BENCH_BASE_URL and DECISION_BENCH_API_KEY in .env.
python3 -m decision_bench run --model gemini-3.5-flash --limit 5
```

Remove `--limit 5` to run the full corpus. Repeat the same run command to resume. The smoke test and full evaluation are separate runs.

The [running guide](docs/running.md) covers endpoint configuration, supported providers, the local viewer, and publishing a completed run.

## Tasks and data

- [Task catalog](docs/tasks.md): questions, options, and sampling details.
- [Source catalog](data/SOURCES.md): datasets, licenses, and citations.
- [Authoring guide](docs/authoring-v4.md): how the corpus is built and reviewed.

The corpus is frozen, and every run records its SHA-256. Runs from different corpus versions cannot be combined. The code is MIT; corpus rows, images, and source excerpts remain under their own source terms. The [data and privacy review](docs/data-release-review.md) records source evidence, privacy screening, and open notes.

For data removal or private reports, see [SECURITY.md](SECURITY.md).

## Contributing and citing

Label corrections, new models, results, and new tasks are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

To cite the benchmark, use [CITATION.cff](CITATION.cff) and identify the corpus SHA-256 and harness commit from your run metadata. Please also cite the datasets behind the tasks you use; their citations are in the source catalog.
