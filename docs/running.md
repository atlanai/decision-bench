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
| `SAGE_API_KEY` | `sage` | Levanto key from Intelligence → API Keys. |
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
  "provider": "openai-compatible",       // openai-compatible | typesafe | djev | sage | laya | claude-cli | codex-cli
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

## Levanto Sage 1.3

Set `SAGE_API_KEY` in the ignored `.env`. The hosted server selects its version;
the adapter verifies `levanto-sage-v1.3` on every response. Use a fresh run ID for
this rerun: `python3 -m decision_bench run --model sage --run-id sage-v1.3-bench-v4-full-v1`.
The entry evaluates all 1,071 rows, including 122 images, with reasoning `auto`
and no web grounding. Native categorical Choice probabilities are retained;
a null choice counts as unanswered/incorrect, not an API failure, and no argmax
is substituted.

Pricing changed from decision-unit subscriptions to metered token usage. The
verified Starter rates are $0.046 per million input tokens and $10 per million
output tokens. Sage reports text/reasoning input separately from image tokens;
both are billed as input. Use measured `meta.usage.output_tokens`, which includes
billed reasoning, rather than assuming output is free. Benchmark costs are
price-table usage estimates covered by account credits, not card charges.
[Current pricing](https://levanto.ai/pricing). The earlier Sage v1.1 text run and
its dated decision-unit audit are archived in `docs/benchmarks/sage/v1.1/`.

## Together Tev1

Set `TOGETHER_API_KEY` in ignored `.env`. Run `python3 scripts/run_tev1.py smoke`,
then `pilot`, then `full` after checking each completed stage. These select only
rows with no image assets (949 in bench-v4), use one serial worker, and retain
separate resumable run IDs. `--dry-run` prints selection counts without an API call.
The model is `together/Tev1-4B-experimental`, with native A–X labels, regex
constraints and thinking disabled. Accuracy is scored; calibration is unavailable
because the native top-5 token logprobs do not cover every option. Raw logprobs
remain available locally for inspection. No model-generated distribution is requested.

## Perplexity Decider via OpenRouter

Set `OPENROUTER_API_KEY` in the ignored `.env`. Use
`python3 -m decision_bench run --model pplx-decider-v1.1-27b --limit 5 --jobs 1 --max-attempts 1`
for a smoke test, then remove `--limit 5` for the full corpus. The native adapter
sends one Choice question per row to OpenRouter's `/api/alpha/decisions`, including
image assets as base64 image parts when present. It preserves the returned choice
and categorical probabilities, records images sent, and uses the reported token
usage and USD cost. No chat completion or generated probability distribution is used.

[OpenRouter Decisions reference](https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-request)

## OpenAI GPT-6 Luna Decisions via OpenRouter

Use the same ignored `OPENROUTER_API_KEY` with
`python3 -m decision_bench run --model gpt-6-luna-decisions --limit 5 --jobs 1 --max-attempts 1`
for a smoke test, then remove `--limit 5` for the full corpus. This entry sends
native Choice questions to OpenRouter's Decisions endpoint, with text and image
evidence and unchanged native probabilities. It is separate from `gpt-6-luna`,
which uses chat completions with generated structured output. Input tokens are
billed at the Decisions rate; output tokens are free, and provider-reported
cost takes precedence over the fallback price table.

[OpenRouter model](https://openrouter.ai/openai/gpt-6-luna-decisions) ·
[OpenAI Decisions guide](https://developers.openai.com/api/docs/guides/decisions)

## Microsoft-Decision-1 via OpenRouter

Use the ignored `OPENROUTER_API_KEY` and model id `microsoft-decision-1`. This
text-only entry uses the native Decisions API and is evaluated on the 949 corpus
rows without image assets. All 122 image-containing rows are excluded for the
same shared-text comparison used for Tev1. Its partial run is not ranked on the
full-corpus leaderboard. Hosted weights may update; the resolved model identity
is retained for every response. Input costs $0.042 per million tokens and output
is free as verified on 10 October 2026; measured provider-reported costs take
precedence over this fallback rate.

[OpenRouter model](https://openrouter.ai/microsoft/microsoft-decision-1)
