# Tev1 4B Experimental benchmark

Model: `together/Tev1-4B-experimental`. Branch: `upgrade-bench-v1`.

**810/949 correct (85.35%)**, with 0 operational errors.

95% Wilson accuracy interval: 82.96%–87.46%.
Median latency: 387 ms; p95: 495 ms. Serial end-to-end HTTP latency, including client overhead.
Estimated cost: $0.031389; input tokens: 747,369; output tokens: 1,898.

## Scope and method

949 rows without image assets from the frozen 1,071-row bench-v4 corpus. The remaining 122 rows were excluded, not counted as failures. No inputs were silently truncated. One request per row, one serial worker, one attempt per row. Native A–X letter output, regex constrained, temperature 0, thinking disabled, max_tokens 8. Semantic keys are mapped back before scoring. Confidence, Brier, ECE and log loss are unavailable: top-5 token logprobs do not cover every question’s options and are not calibrated confidence.

Estimated cost uses the announced $0.042/M input and $0/M output rate, not a billing receipt. Cached input tokens are conservatively counted at the full input rate. Smoke and pilot calls are separate from these full-run metrics. Training overlap has not been ruled out; results measure this corpus, not a proven uncontaminated holdout.

Corpus SHA256: `3599baea0d9c7e4e3d86c8b06af96e6850edca037b334bbc6b4e1a0033021725`.
A credential-free implementation snapshot is retained locally in `runs/tev1-implementation-v1/`; provider and scoring source are included in this PR.

## Categories

| Category | Correct / rows | Accuracy |
|---|---:|---:|
| agents | 115/154 | 74.68% |
| commerce | 76/90 | 84.44% |
| data | 86/94 | 91.49% |
| documents | 38/57 | 66.67% |
| engineering | 125/150 | 83.33% |
| finance | 88/91 | 96.70% |
| legal | 116/126 | 92.06% |
| product | 47/60 | 78.33% |
| safety | 53/60 | 88.33% |
| support | 66/67 | 98.51% |

## Comparison on identical rows

Historical model runs are rescored on the intersection with this run. Differences are Tev1 minus the comparison model. Intervals are paired row bootstrap intervals (2,000 samples, seed 42), not adjusted for task clustering or multiple comparisons. Latency across different run dates and provider settings should not be treated as a controlled speed comparison.

| Model | Shared rows | Accuracy | Tev1 difference | 95% interval |
|---|---:|---:|---:|---:|
| deepseek-v4.1-flash | 949 | 93.68% | -8.32 pp | -10.64 to -6.11 pp |
| gemini-3.5-flash | 949 | 93.47% | -8.11 pp | -10.54 to -5.80 pp |
| gemini-flash-lite-latest | 949 | 93.36% | -8.01 pp | -10.43 to -5.80 pp |
| jev-1.13 | 949 | 93.15% | -7.80 pp | -9.91 to -5.69 pp |
| glm-5.3-flash | 949 | 93.05% | -7.69 pp | -10.12 to -5.37 pp |
| gpt-6-luna | 949 | 92.94% | -7.59 pp | -10.12 to -5.27 pp |
| claude-sonnet-5 | 949 | 91.68% | -6.32 pp | -8.64 to -4.00 pp |
| gpt-5.6-luna | 949 | 91.68% | -6.32 pp | -8.75 to -3.90 pp |
| claude-haiku-4.5 | 949 | 89.57% | -4.21 pp | -6.64 to -1.90 pp |
| qwen3-32b | 949 | 80.93% | +4.43 pp | +1.90 to +6.85 pp |
| nova-micro-v1 | 949 | 66.91% | +18.44 pp | +15.17 to +21.71 pp |
| laya-routed | 949 | 51.21% | +34.14 pp | +30.45 to +37.83 pp |

## Artifacts

Aggregate metrics, paired comparisons, and robustness summaries are committed alongside this report. Per-row records and raw provider responses remain in the local ignored run directories. This report does not add a published leaderboard entry.

## Repeatability and option order

- Repeat: 84/100 correct; 0/100 semantic answers changed from the full-run baseline.
- Permutation: 121/150 correct; 7/150 semantic answers changed from the full-run baseline.

Two repeat passes and three deterministic option permutations used the fixed 50-row pilot subset. Repeatability is measured only on this subset, not established for all possible requests. Additional estimated cost: $0.007987. Raw robustness records are in `runs/tev1-robustness-v1/`.
