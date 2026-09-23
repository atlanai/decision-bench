# Decision Bench

An open benchmark for the bounded decisions software asks language models to make:
- Which team owns this complaint?
- Is this message a prompt injection?
- Does this NDA say this?
- Which tool should the agent call?
- Is this commit a fix, a feature or a refactor?
- Which figure on this receipt is the total?

**1,071 rows · 35 tasks · 11 use cases · 36 public datasets.** Every row is a real record; the answer comes from the dataset's own annotators or an objective record such as a test result or a filing's item number, never from a model. 122 rows carry an image as well as a text rendering, so vision and text-only models can both be scored. Every row names its dataset, licence, record id and original label.

Browse every row, every source and the leaderboard on the site (run `python3 -m decision_bench serve` for a local copy).

| Use case | Questions | Rows | Sources |
| --- | --- | --- | --- |
| Engineering | Which file did the fix for this issue change? · What kind of change does this diff make? · Which weakness class does this CVE describe? · Is this a real secret committed in code? · Which commit message belongs to this diff? | 150 | CommitPackFT, NVD (National Vulnerability Database), SWE-bench Verified, Samsung CredData |
| AI agents & evals | Which tool should the agent call for this request? · Did the agent carry out the injected instruction? · Did the agent complete what the user's scenario required? · Is this answer supported by its sources? · Which response is better? | 154 | AgentDojo recorded runs, BFCL v3 Live (Berkeley Function-Calling Leaderboard), HAGRID, MT-Bench human judgments, τ-bench historical trajectories |
| Trust & safety | Is this message an attack? · Is this comment toxic? | 60 | Civil Comments, In-The-Wild Jailbreak Prompts (JailbreakHub), deepset/prompt-injections |
| Customer support | Which product team owns this complaint? · What is this complaint about? | 67 | CFPB Consumer Complaint Database |
| Sales & commerce | How relevant is this product to the shopping query? · What type of product is this listing? · Which SIC division is this company in? | 90 | Amazon Berkeley Objects (ABO), Amazon Shopping Queries Dataset (ESCI), EDGAR-CORPUS (10-K Item 1) with SEC EDGAR SIC codes |
| Finance | Which section of the annual report is this passage from? · What event does this current report disclose? · Which of these figures is the receipt's total? · What does the marked amount in this sentence report? | 121 | CORD-v2 (Consolidated Receipt Dataset), EDGAR-CORPUS, FiNER-139, SEC EDGAR 8-K filings |
| Legal | Does the agreement say this, the opposite, or neither? · Which of these clause types is this? · Is this term unfair, and how? · Does this excerpt contain that clause type? | 126 | CUAD (Contract Understanding Atticus Dataset) v1, ContractNLI, UNFAIR-ToS (LexGLUE) |
| Product management | Which package got more clicks per view? · Which part of the version was bumped? | 60 | CHANGELOG.md files of BSD-3-Clause-licensed projects (Keep a Changelog), CHANGELOG.md files of MIT-licensed projects (Keep a Changelog), Upworthy Research Archive (exploratory packages) |
| Data & analytics | Which query answers the question on this schema? · Which value is the answer to the question? · Do the chart's data support the claim? · What kind of value does the hidden column hold? | 126 | Federal Register documents API, FiveThirtyEight data repository, Our World in Data grapher charts, Spider (dev set), U.S. Treasury Fiscal Data, WikiTableQuestions (test set), congress-legislators (legislators-current.csv) |
| Documents & meetings | What kind of document is this page from? · Is the highlighted utterance a decision, an action item, or neither? · Which of the four summaries describes this meeting? | 87 | AMI Meeting Corpus (manual annotations 1.6.2), DocLayNet v1.2 |
| Design | Which of these names is this icon's official name? | 30 | Material Symbols (google/material-design-icons) |

The full task list, with options and how rows were chosen, is in [docs/tasks.md](docs/tasks.md). Sources, licences and citations are in [data/SOURCES.md](data/SOURCES.md). The authoring rules are in [docs/authoring-v4.md](docs/authoring-v4.md).

## Quick start

Python 3.11+, standard library only.

```sh
git clone https://github.com/OWNER/decision-bench && cd decision-bench
python3 -m decision_bench validate           # check the frozen corpus and any published results
python3 -m decision_bench report && python3 -m decision_bench serve   # http://127.0.0.1:8765
```

To evaluate a model, point the harness at any OpenAI-compatible endpoint (OpenAI, OpenRouter, a LiteLLM proxy, vLLM, Ollama and others):

```sh
cp .env.example .env      # set DECISION_BENCH_BASE_URL and DECISION_BENCH_API_KEY; .env is never committed
python3 -m decision_bench models                                   # models in config/models.json
python3 -m decision_bench run --model gemini-3.5-flash --limit 5   # smoke test
python3 -m decision_bench run --model gemini-3.5-flash             # all rows; re-run the same command to resume
python3 -m decision_bench publish <run-id>                         # copy the finished run into results/
python3 scripts/run_all.py                                         # every API model, then publish and rebuild
```

Models flagged `"vision": true` in `config/models.json` receive the row's images; the others receive the text rendering. There are also adapters for the Claude Code CLI, the Codex CLI and the TypeSafe API. Setup, options, costs and resuming are covered in [docs/running.md](docs/running.md).

## How it works

- **The model sees only the evidence.** Each row's record, the task instruction and the options (in a fixed per-row shuffled order) are sent. The answer, rationale, title, source and notes never are. The system prompt treats the record as untrusted data. CLI adapters run in an empty directory with tools disabled. See [docs/protocol.md](docs/protocol.md).
- **Answers are strict JSON:** a label from the options plus a probability for each option. Anything else counts as no answer, not a guess.
- **Scores are accuracy with Wilson 95% intervals,** overall, per use case and per task, alongside macro F1, calibration, latency, cost and tokens. Each task page also shows a plain fit verdict per model, computed from the numbers.
- **The corpus is frozen** with a sha256 in its manifest. Every run records the hash it used, and results from different versions are never mixed.

## Results

`results/<suite>/<model-id>/` holds the latest published run of each model: `metadata.json`, one line per row in `predictions.jsonl`, and `scores.json`. `results/<suite>/leaderboard.json` ranks them. No file there contains a key, an endpoint URL or a provider request id. The format and how to submit results are in [results/README.md](results/README.md).

## Data and licences

The code is MIT. Each row keeps its dataset's licence. A dataset is used only if both its own licence and the terms of the text or images inside it allow anyone to copy, modify and redistribute it, commercially too; the build enforces this. Datasets that failed that test were not used, even when the dataset itself was MIT (the reasons are recorded in each module's docstring under `authoring/bench/`).

- Real secrets in code rows are replaced with fake values of the same shape.
- Contact details in contracts are replaced with placeholders.
- Row images are resized copies of the source images, under 400 KB each.
- Rows can be traced to their upstream record, but not to a live secret.

`scripts/fetch_sources.py` re-downloads every upstream file and checks it against the pinned sha256 in `data/sources/manifest.json`. `scripts/build_bench.py --dry-run` then rebuilds the rows.

If you hold rights in a row or are named in one, open a **Data removal request** issue, or report privately (see [SECURITY.md](SECURITY.md)).

## Limits

- Public datasets may be in model training data, so scores may be inflated. Each task states a contamination risk.
- Tasks have 27–36 rows each, so per-task differences of a few points are usually within noise. Compare the intervals, not the point estimates.
- Some labels are derived by a written rule from the record itself (a version bump, a templated chart claim); those task pages say so.

## Contributing and citing

Label corrections, new models, results and new tasks are all welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and the [code of conduct](CODE_OF_CONDUCT.md). To cite the benchmark, use [CITATION.cff](CITATION.cff), and please also cite the datasets behind the tasks you use. Their BibTeX is in [data/SOURCES.md](data/SOURCES.md).
