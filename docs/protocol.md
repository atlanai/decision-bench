# Evaluation protocol

This describes how Decision Bench measures a model on the active corpus: what the model sees, how answers are
parsed and scored, and what is recorded. Commands are in [running.md](running.md); file formats are in
[results-format.md](results-format.md).

## Corpus

`data/corpus/current.json` names the one active corpus. Today that is **bench-v3** (`data/corpus/bench-v3/`):
359 rows in 14 fixed tasks and 7 categories. 323 rows are real records sampled from public datasets, with the
dataset's own label as the answer; the rest are written examples. Every row is text and has exactly one choice
question with two or more options. See [data/SOURCES.md](../data/SOURCES.md) for sources and licenses.

The corpus is frozen: its sha256 is in `manifest.json`, and loading fails if the rows do not match. Every run
records the sha256 it used. A run on a different corpus version cannot be resumed, published or compared.

Public datasets may appear in model training data, so scores may be inflated by contamination.

## What the model sees

The model input is built by allowlist (`decision_bench/corpus.py: public_input`):

- the row's `state` (the evidence), and
- for its question: `id`, `type`, `instructions`, and the options in the row's stored presentation order
  (`option_order`, a fixed per-row shuffle).

Everything else is excluded: the answer (`gold`), `rationale`, row id, `title`, `summary`, `note`, `source`,
`provenance`, tags, and the short reader-facing question (`ask`). Tests check this for every row.

A shared policy is sent with every request: the state is untrusted data, instructions inside it do not override
the question, actions in it must not be carried out, and no tools, files or web search may be used. The exact
system prompt is in `corpus.py` (`SYSTEM`) and in `site/data.json` (`prompt.system`). Its version is recorded as
`prompt_version` (currently `choice-v1`).

How it is sent depends on the provider:

| Provider | Request |
| --- | --- |
| `openai-compatible` | `POST <base>/chat/completions` with a system message (the policy) and a user message (the public input as JSON, then the answer JSON schema). By default `response_format` is `json_schema` (strict); models that do not support it use `json_object` or `prompt`, as set in `config/models.json`. Token limit field, maximum tokens, reasoning effort and temperature also come from the config; unset values use the provider's default. |
| `typesafe` | `POST https://api.typesafe.ai/v1/systemone` with the state and the question in TypeSafe's native format (the policy is prefixed to the instructions). |
| `claude-cli` | `claude --print` with the policy as system prompt, the public input on stdin, `--json-schema`, no tools, no MCP servers, no session persistence, and `--effort` from the config. |
| `codex-cli` | `codex exec` with the prompt on stdin, `--output-schema`, a read-only sandbox, shell and patch tools disabled, and `model_reasoning_effort` from the config. |

CLI runs are closed book: each call runs in a new empty temporary directory, so the corpus and answers are not
reachable, and the harness's own API keys are removed from the child environment. Any tool call reported by
Codex invalidates that answer (`protocol_violation`).

## Answer parsing

The model must return `{"answers": {"<question id>": {"label": "<option>", "probabilities": {"<option>": p, ...}}}}`
(TypeSafe returns `choice` instead of `label`). An answer is valid only if:

- the response is a JSON object. For chat models, one complete Markdown code fence around the JSON is removed
  when `json_wrapper_policy` is `allow_single_code_fence` (the default). No other extraction or repair is done;
- the label is one of the options;
- there is a probability for exactly the listed options, each a finite number in [0, 1];
- the probabilities sum to 1 within 0.02. The raw sum is recorded, then they are normalized.

A response cut off by the token limit (`finish_reason: length`) or containing a tool call is invalid. The model's
own label is scored even when it disagrees with its own highest probability; that disagreement is recorded
(`label_is_argmax`).

## Scoring

- **Accuracy**: exact match of the label with the answer. A row with no valid answer (any error) counts as wrong
  and is also counted separately as an operational error. Accuracy is reported overall, per category, per task
  and per source kind, each with a Wilson 95% interval. Intervals are not adjusted for related rows within a task.
- **Macro averages**: mean accuracy over categories, and mean macro-F1 over tasks, so large tasks do not dominate.
- **Calibration** (descriptive only): Brier score, log loss (true-label probability clipped at 1e-12), expected
  calibration error over 10 bins, a reliability curve, and a risk/coverage curve. Only valid answers contribute.
- **Paired comparisons**: for two full runs, the accuracy difference on shared rows with a bootstrap interval that
  resamples whole tasks (2,000 repetitions, fixed seed).

Order on the leaderboard is by accuracy. Models whose intervals overlap are not reliably different.

## Retries and resuming

A call that fails with a retryable error (HTTP 408, 409, 425, 429, 5xx, a transport error, or a non-JSON body)
is retried up to `--max-attempts` times (default 2) with backoff of 2, 4, 8 seconds. Invalid model output is not
retried: the model's formatting reliability is part of the measurement. `--retry-errors` explicitly re-runs rows
whose latest result is an error; earlier attempts stay in the ledger.

Results and attempts are appended to JSONL ledgers as they finish, so a stopped run resumes where it left off by
repeating the same command. A run resumes only with an identical frozen configuration (model, model name sent,
request options, endpoint id, prompt version, corpus sha256, selected rows).

## What is recorded

Per attempt (local `attempts.jsonl`): start and finish times, status and error, duration, token usage (input,
output, cached input, reasoning output), cost and its basis, the model name the provider returned, and the
provider-reported duration when available.

Per row (local `results.jsonl`): the parsed answer, its score, the raw output text, the input hash, and every
attempt. The published `predictions.jsonl` keeps the answer, gold, correctness, raw output, confidence,
probabilities, tokens, cost, latency and a summary of each attempt.

**Cost.** The provider's own figure is used when it reports one (LiteLLM's `x-litellm-response-cost` header,
OpenRouter's `usage.cost`, Claude Code's `total_cost_usd`); basis `provider_reported`. Otherwise the cost is
estimated from token counts and the per-million-token prices in `config/models.json`; basis
`price_table_estimate`, with the price source URL recorded. Cached input tokens use the cached rate when one is
given; cache writes are not priced separately. Unknown cost is `null`, never zero, and totals report the share
of attempts with a known cost. None of these are verified invoices. Failed attempts that were billed still count.

**Latency.** Wall clock per row, including retries, measured by the harness. For HTTP providers this includes the
network round trip; for CLIs it includes starting a fresh process. It is not pure inference time. Concurrency
(`--jobs`) is recorded; throughput is not single-request latency.

**Never recorded:** API keys, endpoint URLs or hostnames (only an opaque `endpoint_id`, a hash of the base URL),
provider request ids, routing or deployment headers, and local install paths. Error messages are published with
URLs removed. Raw provider output stays in the ignored `runs/<id>/raw/`.

## Integrity

Answers are frozen before any model is run. A correction to a row requires a new corpus version, never an edit
that removes a failure. Runs record the harness git commit and whether the tree was dirty. Failed attempts and
partial runs are kept. Only complete runs on the current corpus are published without `--force`, and
`validate` recomputes every published score from its predictions.
