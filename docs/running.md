# Running Decision Bench

## Install

Python 3.11 or newer. There are no runtime dependencies beyond the standard library.

```sh
git clone <this repository> && cd decision-bench
python3 -m decision_bench validate
```

`pip install -e .` also works and adds a `decision-bench` command; the examples below use `python3 -m decision_bench`.

The corpus is committed (`data/corpus/`). You do not need `scripts/fetch_sources.py` to run the benchmark; it is
only for rebuilding the corpus from the upstream datasets.

## Configure an endpoint

Copy `.env.example` to `.env` (ignored by git) and fill in what you need. Values in the real environment take
precedence over `.env`.

| Variable | Used by | Meaning |
| --- | --- | --- |
| `DECISION_BENCH_BASE_URL` | `openai-compatible` | Base URL that `/chat/completions` is appended to, usually ending in `/v1`. HTTPS is required except for `localhost`. |
| `DECISION_BENCH_API_KEY` | `openai-compatible` | Bearer key. Optional for a `localhost` endpoint. |
| `TYPESAFE_API_KEY` | `typesafe` | Key for `https://api.typesafe.ai`. |
| `DJEV_API_KEY` | `djev` | Key for the hosted DiffusionGemma-Jev API at `https://api.djev.dev`. |
| `LAYA_BASE_URL` | `laya` | Laya System One base URL ending in `/v1`. Use `https://api.impossibl.com/v1` or a self-hosted `http://localhost:8000/v1`. |
| `LAYA_API_KEY` | `laya` | Bearer key; required for hosted Laya, optional for an unauthenticated localhost server. |

Examples of `DECISION_BENCH_BASE_URL`: `https://api.openai.com/v1`, `https://openrouter.ai/api/v1`,
`http://localhost:4000/v1` (a local LiteLLM proxy), `http://localhost:8000/v1` (vLLM).

The harness never reads `OPENAI_API_KEY` or other provider variables. The key is sent only to the configured
origin, redirects are refused, and neither the key nor the URL is written to any run record.

The `claude-cli` and `codex-cli` providers use the `claude` and `codex` commands on your `PATH` with their own
sign-in. The harness removes its own keys from their environment.

Laya uses the same typed question protocol as Jev. To run its hosted API, set `LAYA_BASE_URL` and
`LAYA_API_KEY` in `.env`, then run `python3 -m decision_bench run --model laya-routed --limit 5`.
To self-host, install `laya[serve]` in a separate environment, start `laya-serve`, and set
`LAYA_BASE_URL=http://localhost:8000/v1`. Laya's router chooses the checkpoint per request;
`--api-model` can override the configured model id. Laya has no price in this config, so
API cost is recorded as unknown; self-hosting compute is outside the cost estimate.

Djev uses the same typed answer format through its hosted `POST /v1/request` endpoint. Set
`DJEV_API_KEY` in `.env`, then run `python3 -m decision_bench run --model djev --limit 5`.
The configured $0.035 per million input tokens is the announced rate, so reported cost is an
estimate until the API supplies a charged amount. This entry evaluates text rows; image input
is not enabled in the Djev adapter. See [Djev's API contract](https://djev.dev/llms.txt).

## Choose a model

Models live in `config/models.json`:

```sh
python3 -m decision_bench models            # configured models
python3 -m decision_bench models --remote   # model ids your endpoint lists (printed only, nothing saved)
```

Each entry:

```jsonc
{
  "id": "gemini-3.5-flash",              // our stable slug: run ids and results/ paths use it
  "label": "Gemini 3.5 Flash", "short_label": "Gemini Flash", "vendor": "Google", "color": "#2563eb",
  "provider": "openai-compatible",       // openai-compatible | typesafe | djev | laya | claude-cli | codex-cli
  "model": "gemini-3.5-flash",           // the model name sent to the provider
  "request": {"response_format": "json_schema", "token_limit_field": "max_tokens", "max_output_tokens": 8192,
              "reasoning_effort": "low", "temperature": null, "json_wrapper_policy": "allow_single_code_fence"},
  "pricing": {"input_per_mtok": 1.5, "cached_input_per_mtok": 0.15, "output_per_mtok": 9.0,
              "source_url": "https://...", "as_of": "2026-09"}  // optional, for cost estimates
}
```

The `model` names in the committed config are the names one particular proxy used. Your endpoint may call the same
model something else (for example `google/gemini-3.5-flash` on OpenRouter). Pass `--api-model <name>` to send a
different name without editing the config; it is recorded in the run. To add a model, add an entry and open a pull
request.

`request` options for `openai-compatible`:

- `response_format`: `json_schema` (strict schema, default), `json_object`, or `prompt` (schema in the prompt only).
- `token_limit_field`: `max_tokens` (default) or `max_completion_tokens` (newer OpenAI models).
- `max_output_tokens`: default 4096. `reasoning_effort`, `temperature`: omitted when `null`.
- `json_wrapper_policy`: `allow_single_code_fence` (default) or `strict`.

## Run

```sh
python3 -m decision_bench run --model gemini-3.5-flash --limit 5     # smoke test on 5 rows
python3 -m decision_bench run --model gemini-3.5-flash               # every row
python3 -m decision_bench run --model gemini-3.5-flash,qwen3-32b     # several models, one after another
```

Options: `--jobs` (concurrent requests, default 3), `--timeout` (seconds per request, default 180),
`--max-attempts` (default 2), `--ids a,b,c` (specific rows), `--run-id` (a name of your choice).
Optional `--rpm` and `--global-rpm` pace request starts, including retries. The global cap is shared
by benchmark processes in this checkout.

To run every configured API model, use `python3 scripts/run_all.py`. It starts three models at a time,
with four concurrent requests per model by default. Request starts are paced to 60 per minute per
model and 120 per minute across the checkout; tune these with `--parallel`, `--jobs`, `--rpm`, and
`--global-rpm` for your provider. In a terminal, the live dashboard shows a loader and row progress
for each model, plus publish/build progress. Detailed row output stays in `runs/<model-id>.log`, and
timestamped session events and progress milestones go to `runs/run-all-*.log`. Use `--plan` to preview,
`--no-tui` for line-by-line output, or `--limit 5` for a smoke test that does not publish. Rate-limit
waiting is recorded separately and excluded from model latency.

The default run id is `<model-id>-<suite>-<hash of the frozen configuration>`, with `-subset` added when not every
row is selected. So a smoke test and a full run are separate runs, and repeating a command continues the same run.

### Resume

Run the same command again. Finished rows are skipped. A run can only resume with the same frozen configuration
(model, model name sent, request options, endpoint, prompt version, corpus, selected rows); change any of these and
you get a new run id. `--jobs`, `--timeout` and `--max-attempts` can change between invocations.

Rows that ended in an error are not retried on resume. To retry them:

```sh
python3 -m decision_bench run --model gemini-3.5-flash --retry-errors
```

Earlier failed attempts stay in `runs/<run-id>/attempts.jsonl` and still count toward cost and tokens.

## Publish

```sh
python3 -m decision_bench publish gemini-3.5-flash-bench-v4-1a2b3c4d
python3 -m decision_bench validate
```

This writes `results/<suite>/<model-id>/` (replacing any previous result for that model) and rebuilds
`results/<suite>/leaderboard.json` and `.md`. It refuses a run that is still running or does not cover every row;
`--force` publishes it anyway and records a warning. A run on another corpus version can never be published.
See [results-format.md](results-format.md) and [results/README.md](../results/README.md) for submitting results.

## Preview the site

```sh
python3 -m decision_bench report                  # from results/ only
python3 -m decision_bench report --include-runs   # also local runs/, e.g. one still in progress
python3 -m decision_bench serve                   # http://127.0.0.1:8765
```

`serve` exposes only `site/`, not the repository or `.env`. The viewer is a React app in `web/`; build it into
`site/` once with `make site` (`npm ci --prefix web && npm run build --prefix web`), and after `report` `site/` is a
complete static site. For live editing, `npm run dev --prefix web` serves the viewer with hot reload at
http://localhost:5173, reading the data in `site/`.

## Tests and checks

```sh
python3 -m unittest discover -s tests -v
python3 -m decision_bench validate
python3 scripts/check_secrets.py
npm run build --prefix web
```

or `make check`. Tests use a local fake endpoint and never call a model.

## Costs and limits

- A full run is 359 requests, plus retries. With reasoning models, output tokens dominate the cost.
- Costs are the provider's own figure when it reports one, otherwise an estimate from `config/models.json` prices.
  Prices change; check them before relying on a number. Codex CLI costs are API-equivalent estimates, not what a
  subscription charges.
- Keep `--jobs`, `--rpm`, and `--global-rpm` within your provider's limits. 429 responses are retried,
  but a run that keeps hitting limits will record errors. Retry them later with `--retry-errors`.
- Proxies and providers may cache responses. Nothing in the harness disables caching, so repeated runs can be
  faster and cheaper than a cold run.
- Latency includes the network or CLI start-up and depends on `--jobs`; compare latency only between runs made the
  same way.
- File locking uses `fcntl`, so runs need Linux or macOS (or WSL on Windows).
