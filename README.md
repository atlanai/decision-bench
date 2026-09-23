# Decision Bench

An open benchmark for the small, bounded decisions that software asks models to make:
- Is this message a prompt injection?
- Is this a real secret?
- Which agent broke this run?
- Which team owns this ticket?
- Is this answer supported by its sources?
- Does this contract say this?

**359 rows · 14 tasks · 7 categories · 323 real records from 14 public datasets.** Every real row keeps its source licence and names its dataset, record id and original label. Answers come from each dataset's human annotators or from an objective record, never from a model.

Browse every row, the sources and the leaderboard on the site (GitHub Pages; run `python3 -m decision_bench serve` for a local copy).

| Category | Tasks | Rows | From |
| --- | --- | --- | --- |
| Prompt injection | Is this message an attack? · Does this email try to hijack the assistant? | 54 | deepset/prompt-injections, In-The-Wild Jailbreak Prompts, LLMail-Inject |
| Sensitive data | Is this a real secret committed in code? | 24 | Samsung CredData |
| Trace classification | What kind of failure is this step? · Which agent caused the failure? · Did the coding agent fix the issue? | 71 | AgentRx, Who&When, SWE-agent trajectories |
| Trace routing | Which tool should the agent call? · Which bank team handles this? · Which product team owns this complaint? | 88 | BFCL v3 Live, BANKING77, CFPB complaints |
| Eval judging | Is the answer supported by its sources? · Which response is better? | 56 | HAGRID, BEGIN, MT-Bench human judgments |
| Contract checks | Does this NDA say this? | 30 | ContractNLI |
| Skill improvement | Why did the skill fail? · Should this change ship? | 36 | Written examples |

The full task list, with questions, options and how rows were chosen, is in [docs/tasks.md](docs/tasks.md). Sources, licences and citations are in [data/SOURCES.md](data/SOURCES.md).

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
```

There are also adapters for the Claude Code CLI, the Codex CLI and the TypeSafe API. Setup, options, costs and resuming are covered in [docs/running.md](docs/running.md).

## How it works

- **The model sees only the evidence.** Each row's input, the task instruction and the options (in a fixed per-row shuffled order) are sent. The answer, rationale, title, source and notes never are. The system prompt treats the input as untrusted data. CLI adapters run in an empty directory with tools disabled. See [docs/protocol.md](docs/protocol.md).
- **Answers are strict JSON:** a label from the options plus a probability for each option. Anything else counts as an invalid answer, not a guess.
- **Scores are accuracy with Wilson 95% intervals,** overall, per category and per task, alongside cost, latency, tokens and calibration.
- **The corpus is frozen** with a sha256 in its manifest. Every run records the hash it used, and results from different versions are never mixed.

## Results

`results/<suite>/<model-id>/` holds the latest published run of each model: `metadata.json`, one line per row in `predictions.jsonl`, and `scores.json`. `results/<suite>/leaderboard.json` ranks them. No file there contains a key, an endpoint URL or a provider request id. The format and how to submit results are in [results/README.md](results/README.md).

## Data and licences

The code and the written examples are MIT. Each real row keeps its dataset's licence (MIT, Apache-2.0, CC BY 4.0, CC BY-SA or CC0). A dataset is used only if both its own licence and the terms of the text inside it allow anyone to copy, modify and redistribute it, commercially too. The build enforces this. Datasets built on non-commercial or publisher-copyrighted text were removed before release, even when the dataset itself was MIT (see [docs/tasks.md](docs/tasks.md#removed-before-release)).

- Real secrets in the code rows are replaced with fake values of the same shape.
- Contact details in contracts are replaced with placeholders.
- Rows can be traced to their upstream record, but not to a live secret.

`scripts/fetch_sources.py` re-downloads every upstream file and checks it against the pinned sha256 in `data/sources/manifest.json`. `scripts/build_bench.py --dry-run` then rebuilds the rows.

If you hold rights in a row or are named in one, open a **Data removal request** issue, or report privately (see [SECURITY.md](SECURITY.md)).

## Limits

- Public datasets may be in model training data, so scores may be inflated.
- Tasks have 15–30 rows each, so per-task differences of a few points are usually within noise. Compare the intervals, not the point estimates.
- Skill-improvement rows are written examples, not real data. They are badged everywhere and can be filtered out.

## Contributing and citing

Label corrections, new models, results and new tasks are all welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and the [code of conduct](CODE_OF_CONDUCT.md). To cite the benchmark, use [CITATION.cff](CITATION.cff), and please also cite the datasets behind the tasks you use. Their BibTeX is in [data/SOURCES.md](data/SOURCES.md).
