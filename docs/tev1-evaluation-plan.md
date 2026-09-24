# Tev1 independent evaluation plan

Prepared 2026-09-25. Executed on branch `upgrade-bench-v1`. The full text-only run completed with 810/949 correct, zero errors, and 387 ms median latency. Local report: `runs/tev1-4b-bench-v4-full-v1/REPORT.md`. Two repeat passes and three option permutations on 50 rows are complete; see `runs/tev1-robustness-v1/summary.json`.

## Verified interface

Model: `together/Tev1-4B-experimental`, hosted serverless through
`https://api.together.ai/v1/chat/completions`. The console lists text input/output,
32.8K context and 4.7B parameters. The announcement quotes $0.042 per million input
tokens and zero output-token cost; the console rounds its display to $0.04.
Verify the exact API rate before estimating the final run.

Follow the vendor's decision example: a system instruction that treats state as
untrusted data, then a JSON object with `state`, `question`, and `options`.
Each option has a consecutive A–X `label`, semantic `key`, and `description`.
Set temperature 0, max_tokens 8, enable_thinking false, and regex-constrain output
to allowed letters. Request logprobs and preserve the exact raw response.
Map the returned letter back to the original option key; never infer an answer
from an invalid response or silently replace the selected label.

## Separate evaluation path

Use a dedicated Tev1 adapter and independent run IDs/artifacts. Keep credentials
in ignored `.env` as `TOGETHER_API_KEY`; do not overwrite the existing shared
OpenAI-compatible endpoint settings or Sage configuration. Include this key in
redaction and child-process exclusions before making requests. Refuse redirects.
Do not provision a dedicated endpoint or start a fine-tuning job.

The current benchmark requires a full categorical distribution. Tev1's official
example requests only five top token logprobs, while our text rows have up to
nine options. Therefore the first experiment must support accuracy-only results,
with calibration unavailable if all option probabilities cannot be recovered.
Never fill missing mass with zeros, use one-hot predictions as confidence, or
present token logprobs as calibrated confidence. Any full-coverage conditional
letter distribution should be reported separately with its derivation and raw
logprobs retained.

## Staged execution

1. Credentialed smoke: 5 hand-checkable synthetic tasks, including two and nine
   options, a non-first winning option, and instructions embedded in state.
   Verify auth, model identity, exact letter mapping, regex support, usage,
   logprob shape/coverage, and timing. Stop on auth/credit failures.
2. Pilot: freeze 50 rows, stratified across the ten text categories and option
   counts. Include long inputs and an insufficient-evidence label. Run serially;
   collect correctness, invalid answers, truncations, token usage and latency.
   Stop and repair contract failures before increasing scale; do not tune on gold.
3. Main comparison: freeze the eligible text-only manifest and corpus hash.
   There are 949 rows with no image assets in the current 1,071-row corpus,
   all with 2–9 options. Check token lengths against the context limit; report
   exclusions without truncating inputs silently. Compare existing model results
   only on the identical row intersection.
4. Robustness: choose a fixed 50-row subset and run three deterministic option
   permutations, mapping letters back to semantic keys. Repeat the original
   ordering three times to quantify label stability and latency variance.
5. Report overall and macro task accuracy, category results, paired differences
   with bootstrap intervals, invalid/error rate, p50/p95 end-to-end latency,
   token usage, actual/estimated cost, and option-order sensitivity. Separate
   serial latency measurements from any later concurrency/throughput experiment.

Use an initial experiment budget cap of $1 and no automatic credit purchases.
At the announced rate, 949 rows averaging 2,000 input tokens would cost about
$0.080 for one pass, excluding retries and additional experiments. Replace this
illustrative estimate with measured pilot usage before the full run.

## Data overlap and reproducibility

The vendor lists MultiNLI, BoolQ, Banking77, AG News, SST-5, and synthetic policy,
routing, and research data. Audit our source identifiers and, where obtainable,
record text against the released training recipe before claiming a clean holdout.
Separate known overlaps; absent overlap evidence does not establish no contamination.
The vendor's published 880/1,000 and 300/300 results are described as reused
 development benchmarks, so they are context rather than an independent baseline.

Freeze vendor example revision, model identifier, payload options, corpus hash,
row selection, option order, and adapter revision. Keep raw outputs private under
`runs/`; publish only reviewed, redacted artifacts after the evaluation.

## Sources

- https://github.com/togethercomputer/tev1
- https://github.com/togethercomputer/tev1/blob/main/examples/decide.py
- https://github.com/togethercomputer/tev1/blob/main/DATA_SOURCES.md
- https://huggingface.co/togethercomputer/Tev1-4B-experimental
- https://www.together.ai/blog/how-to-train-your-own-jev
