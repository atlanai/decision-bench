# Results

This folder holds the latest published run of each model on each suite. It is the source of truth for the
leaderboard and the site. Local, in-progress work lives in `runs/` (ignored by git); a finished run is copied
here with `python3 -m decision_bench publish <run-id>`.

```
results/
  <suite>/                      e.g. bench-v4
    leaderboard.json            every published model, sorted by accuracy
    leaderboard.md              the same as a table
    <model-id>/                 id from config/models.json
      metadata.json             model, request options, corpus version and sha256, harness commit, dates, coverage, totals
      predictions.jsonl         one line per row: answer, gold, correct, raw output, confidence, tokens, cost, latency
      scores.json               overall, per-category and per-task accuracy with Wilson 95% intervals; cost, latency, tokens
      README.md                 short generated summary
```

Publishing replaces the previous folder for that model and suite, and rebuilds the leaderboard. Only one run per
model is kept; older runs remain in git history. The full schema is in [docs/results-format.md](../docs/results-format.md).

Nothing here contains an API key, an endpoint URL, a hostname or a provider request id. Endpoints appear only as an
opaque `endpoint_id` (a hash). Errors are published as a status class only (for example `HTTP 429`).

## About the bench-v4 runs

The twelve bench-v4 runs were made on 23 September 2026 with harness 0.3.0, before the repository was published as
a single public snapshot. The `harness.git_commit` values in their `metadata.json` point to that earlier private
history and cannot be checked out here, and five runs (Claude Haiku 4.5, Claude Sonnet 5, GLM 5.3 Flash, Jev 1.13
and Amazon Nova Micro) record `git_dirty: true`. Every run used prompt `choice-v1` on the same corpus hash, and
`validate` recomputes each published score from its predictions.

Ten API models were called through one OpenAI-compatible gateway (`endpoint-2a0f85ecc26e`); Jev and Laya were called
through their own APIs. Gateway routing, reasoning settings (see each model's `request`) and concurrency (`jobs`)
all affect latency, so compare latency with those in view. Rate-limited attempts (HTTP 429) never reached a model
and are left out of cost coverage.

## Submitting results

1. Run the model on the current corpus (see [docs/running.md](../docs/running.md)). The run must cover every row.
2. `python3 -m decision_bench publish <run-id>`. It refuses runs that are incomplete or on another corpus version.
3. `python3 -m decision_bench validate` must report no problems. It recomputes `scores.json` from
   `predictions.jsonl` and checks every answer and gold label against the corpus.
4. Open a pull request with only the `results/<suite>/<model-id>/` folder and the updated leaderboard files. If the
   model is new, add its entry to `config/models.json` in the same pull request. Say in the description which
   endpoint type you used (for example "OpenRouter" or "vLLM 0.9 on one H100") and anything unusual about the run.

Do not edit generated files by hand. Maintainers may re-run a submitted model to check it.
