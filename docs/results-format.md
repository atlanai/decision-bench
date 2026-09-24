# Results format

Decision Bench keeps two kinds of output:

- `runs/<run-id>/` is the local working area. It is ignored by git and may contain raw provider output.
- `results/<suite>/<model-id>/` is committed. It holds only the latest published run for each model and contains
  nothing that identifies your infrastructure.

The layout follows the common pattern of public benchmarks (SWE-bench `evaluation/<split>/<run>/`,
lm-evaluation-harness `results_*.json` + `samples_*.jsonl`, HELM `runs/<suite>/`): run metadata, one prediction
per example, and aggregate scores, side by side.

All files are UTF-8 JSON. Unknown values are `null`, never `0`. Schema version: `1`.

## Local runs: `runs/<run-id>/`

| File | Contents |
| --- | --- |
| `run.json` | Frozen `config`, `status` (`running`, `completed`, `completed_with_errors`), `executions` (one per invocation: start time, git commit, jobs, timeout, attempts), display fields and prices. |
| `results.jsonl` | One record per finished row, append-only. A later record for the same row (after `--retry-errors`) supersedes the earlier one. |
| `attempts.jsonl` | A `started` and a `finished` receipt for every provider call, including retries and failures. Cost and token totals come from this ledger. |
| `raw/<attempt-id>.json` | Full provider output (HTTP body or CLI stdout/stderr). Never published. |

The frozen `config` is what defines the measurement. Resuming a run with a different one is refused:

```json
{"suite": "bench-v4", "corpus_version": "1.0", "corpus_sha256": "…", "prompt_version": "choice-v1",
 "model_id": "gemini-3.5-flash", "provider": "openai-compatible", "api_model": "gemini-3.5-flash",
 "request": {"response_format": "json_schema", "max_output_tokens": 8192, "…": "…"},
 "endpoint_id": "endpoint-8f59086678b3", "selected_case_ids": ["…"]}
```

`endpoint_id` is the first 12 hex characters of the sha256 of the base URL. It tells two endpoints apart
without recording either. Concurrency, timeouts and attempt limits are not frozen; they are recorded per execution.

## Published results: `results/<suite>/<model-id>/`

### `metadata.json`

```json
{
  "schema_version": 1,
  "suite": "bench-v4",
  "model": {"id": "gemini-3.5-flash", "label": "Gemini 3.5 Flash", "short_label": "Gemini Flash",
            "vendor": "Google", "provider": "openai-compatible", "color": "#2563eb",
            "api_model": "gemini-3.5-flash", "resolved_models": ["gemini-3.5-flash"]},
  "request": {"response_format": "json_schema", "token_limit_field": "max_tokens", "max_output_tokens": 8192,
              "reasoning_effort": "low", "temperature": null, "json_wrapper_policy": "allow_single_code_fence"},
  "pricing": {"input_per_mtok": 1.5, "cached_input_per_mtok": 0.15, "output_per_mtok": 9,
              "source_url": "https://…", "as_of": "2026-09", "note": "…"},
  "prompt_version": "choice-v1",
  "corpus": {"version": "1.0", "sha256": "…", "current": true},
  "harness": {"version": "0.3.0", "git_commit": "…", "git_dirty": false, "git_commits": ["…"]},
  "run": {"run_id": "…", "status": "completed", "created_at": "…", "completed_at": "…", "published_at": "…",
          "executions": 1, "jobs": 3, "timeout_seconds": 180, "max_attempts": 2,
          "endpoint_id": "endpoint-…", "platform": {"os": "Linux", "python": "3.12.4"}},
  "coverage": {"rows_in_corpus": 359, "rows_selected": 359, "rows_completed": 359, "rows_ok": 357,
               "rows_error": 2, "full": true},
  "totals": {"correct": 301, "accuracy": 0.778, "wilson95": [0.734, 0.816], "errors": 2, "cost_usd": 0.19,
             "cost_coverage": 1.0, "input_tokens": 390000, "output_tokens": 41000, "latency_p50_ms": 1840}
}
```

`resolved_models` is the model string the provider returned. A proxy may return its own alias, so it does not prove
which upstream snapshot answered. `published_with_warnings` appears only when `--force` was used.

### `predictions.jsonl`

One line per row, in corpus order:

| Field | Meaning |
| --- | --- |
| `row_id`, `task`, `category` | From the corpus. |
| `status` | `ok`, or why no valid answer was recorded: an HTTP status (`"429"`), `invalid_output`, `timeout`, `transport_error`, `model_error`, `protocol_violation`, … |
| `answer` | The label the model chose, or `null`. Never replaced by the argmax of its probabilities. |
| `gold` | The corpus answer. |
| `correct` | `answer == gold`. A row with no valid answer is `false`. |
| `confidence` | The probability the model gave its own answer, after normalizing to sum 1. |
| `probabilities` | The full normalized distribution, or `null`. |
| `images_sent` | How many of the row's images were sent: 0 for text-only models and for text tasks. |
| `output_text` | The model's raw answer text for successful rows only (at most 20,000 characters; `output_truncated: true` if cut). Failed rows publish `null`. |
| `error` | Status-only error class such as `HTTP 429`, without provider response bodies or routing details. |
| `latency_ms` | Wall clock for the row, including retries. |
| `tokens` | `input`, `output`, `cached_input`, `reasoning_output`, summed over all attempts. |
| `cost_usd`, `cost_basis` | Summed over all attempts; the bases used (`provider_reported`, `price_table_estimate`, `unavailable`). |
| `attempts` | Each attempt: `status`, status-only `error`, `duration_ms`, `cost_usd`, `cost_basis`, `tokens`. `incomplete` means the process stopped before the call finished. |

### `scores.json`

```json
{
  "schema_version": 1, "suite": "bench-v4", "model_id": "…", "corpus_sha256": "…",
  "overall": {"rows": 359, "correct": 280, "accuracy": 0.780, "wilson95": [0.734, 0.820], "errors": 2,
              "macro_category_accuracy": 0.77, "macro_task_f1": 0.71},
  "by_category": [{"id": "pii", "name": "Sensitive data", "rows": 54, "correct": 40, "accuracy": 0.74, "wilson95": [0.61, 0.84]}],
  "by_task": [{"id": "PII-2", "name": "Triage a secret-scanner hit", "category": "pii", "rows": 24, "correct": 20,
               "accuracy": 0.74, "wilson95": [0.55, 0.87]}],
  "by_source_kind": [{"id": "real", "name": "real", "rows": 323, "…": "…"}],
  "calibration": {"brier": 0.31, "log_loss": 0.62, "ece": 0.08, "high_confidence_errors": 21},
  "cost": {"usd": 0.19, "coverage": 1.0, "basis": ["provider_reported"], "per_1000_rows_usd": 0.49},
  "latency_ms": {"p50": 1840, "p95": 4100, "p99": 7000, "mean": 2100},
  "tokens": {"input": 390000, "output": 41000, "cached_input": 0, "reasoning_output": 12000, "coverage": 1.0},
  "attempts": {"attempts": 391, "retries": 4, "attempt_errors": 6, "incomplete_attempts": 0}
}
```

Every value in `scores.json` can be recomputed from `predictions.jsonl` and the corpus; `validate` does this.

### `leaderboard.json` and `leaderboard.md`

`results/<suite>/leaderboard.json` lists every published model, sorted by accuracy:

```json
{"schema_version": 1, "suite": "bench-v4", "corpus_version": "1.0", "corpus_sha256": "…", "note": "…",
 "models": [{"model_id": "…", "label": "…", "vendor": "…", "provider": "…", "api_model": "…",
             "accuracy": 0.780, "wilson95": [0.734, 0.820], "correct": 280, "rows": 359, "errors": 2,
             "cost_usd": 0.19, "cost_coverage": 1.0, "cost_per_1000_rows_usd": 0.49, "latency_p50_ms": 1840,
             "corpus_current": true, "full_coverage": true, "completed_at": "…"}]}
```

## Site data: `site/` (generated, not committed)

`python3 -m decision_bench report` reads `results/` and writes:

| File | Contents |
| --- | --- |
| `site/data.json` | Everything the viewer renders (below). |
| `site/corpus.json` | The corpus rows exactly as committed, including reader-only fields (`rationale`, `note`, `source`, `ask`). |
| `site/datasets.json` | Copy of `data/datasets.json`, when it exists. |
| `site/protocol.txt` | Copy of `docs/protocol.md`. |
| `site/results/` | Copy of `results/`, so published files can be downloaded from the site. |

With `--include-runs`, local runs on the current corpus are added (marked `"source": "local"`). A local run replaces
a published entry with the same run id, because it may have been resumed since publishing.

`data.json` (schema version 2):

| Key | Contents |
| --- | --- |
| `schema_version`, `generated_at` | |
| `suite`, `corpus_sha256`, `manifest` | The active corpus and its manifest (categories, tasks, counts, datasets when present). |
| `cases` | The corpus rows (same as `corpus.json`). |
| `inventory` | `cases`, `questions`, `tasks`, `categories`, `models_configured`, `runs`, `published_runs`. |
| `prompt` | `version` and the `system` prompt sent to chat models. |
| `models` | Every entry of `config/models.json`: `id`, `label`, `short_label`, `vendor`, `provider`, `color`, `api_model`, `request`, `pricing`. |
| `leaderboard` | The `models` list of `leaderboard.json`. |
| `runs` | One entry per shown run (below). |
| `results` | One record per row per run: `run_id`, `case_id`, `status`, status-only `error`, `duration_ms`, `scores` (a one-item list: `question_id`, `gold`, `label`, `correct`, `confidence`, `probabilities`, `brier`, `log_loss`), `cost_usd`, `tokens`, `attempt_count`. Successful raw answer text is in the published `predictions.jsonl`. |
| `comparisons` | Paired differences between full runs: `a`, `b` (run ids), `both_correct`, `a_only_correct`, `b_only_correct`, `both_wrong`, `accuracy_difference`, `cluster_bootstrap_ci95` (resampling tasks). |
| `include_runs` | Whether local runs were included. |

A `runs` entry:

```json
{"id": "<run id>", "source": "published", "status": "completed", "created_at": "…", "completed_at": "…",
 "published_at": "…", "model_id": "…", "model": {"id": "…", "label": "…", "vendor": "…", "…": "…"},
 "config": {"model_id": "…", "provider": "…", "api_model": "…", "request": {}, "suite": "bench-v4",
            "corpus_version": "1.0", "corpus_sha256": "…", "prompt_version": "choice-v1",
            "endpoint_id": "…", "selected_case_ids": ["…"]},
 "coverage": {"…": "as in metadata.json"}, "current_corpus": true, "harness": {}, "pricing": {},
 "files": {"metadata": "results/bench-v4/<id>/metadata.json", "predictions": "…", "scores": "…", "readme": "…"},
 "metrics": {"cases": 359, "questions": 359, "correct": 280, "accuracy": 0.780, "accuracy_wilson95": [0.73, 0.82],
             "macro_category_accuracy": 0.77, "macro_task_f1": 0.71, "operational_errors": 2, "wrong_decisions": 84,
             "attempts": 391, "retries": 4, "incomplete_attempts": 0, "attempt_errors": 6,
             "cost_usd": 0.19, "cost_coverage": 1.0, "cost_bases": ["provider_reported"],
             "tokens": {"input_tokens": 0, "input_tokens_coverage": 1.0, "…": "…"},
             "latency_ms": {"p50": 0, "p95": 0, "p99": 0, "mean": 0, "sum": 0}, "cost_per_1000_cases_usd": 0.49,
             "brier": 0.31, "log_loss": 0.62, "reliability": {"bins": [], "ece": 0.08, "valid_count": 385},
             "risk_coverage": [], "high_confidence_errors": 21,
             "slices": {"category": [{"name": "pii", "count": 54, "correct": 40, "accuracy": 0.74, "wilson95": [0.61, 0.84], "brier": 0.3}],
                        "task": [], "source_kind": []},
             "confusion": {"PII-2": {"real_credential → real_credential": 7, "real_credential → placeholder_or_test": 1}}}}
```

`files` is `null` for local runs.
