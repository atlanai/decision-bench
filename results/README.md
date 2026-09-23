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
opaque `endpoint_id` (a hash). Error messages have URLs removed.

## Submitting results

1. Run the model on the current corpus (see [docs/running.md](../docs/running.md)). The run must cover every row.
2. `python3 -m decision_bench publish <run-id>`. It refuses runs that are incomplete or on another corpus version.
3. `python3 -m decision_bench validate` must report no problems. It recomputes `scores.json` from
   `predictions.jsonl` and checks every answer and gold label against the corpus.
4. Open a pull request with only the `results/<suite>/<model-id>/` folder and the updated leaderboard files. If the
   model is new, add its entry to `config/models.json` in the same pull request. Say in the description which
   endpoint type you used (for example "OpenRouter" or "vLLM 0.9 on one H100") and anything unusual about the run.

Do not edit generated files by hand. Maintainers may re-run a submitted model to check it.
