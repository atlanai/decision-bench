# Sage 1.3 (Levanto) benchmark

**983/1071 correct (91.78%)**. 18 abstentions; 0 operational errors.

Median end-to-end latency: 441 ms; p95: 2658 ms.
Accuracy Wilson 95% interval: 89.99%–93.28%.

## Method

All 1,071 rows, including 122 image-containing rows, were evaluated with three workers, reasoning `auto`, no grounding/web search, and the native Choice endpoint. The hosted model version is verified on every response. Inputs contain only evidence, instructions and options.
A null choice is an abstention and counts as incorrect, not an API failure. Native categorical probabilities are retained; no answer is replaced by an argmax.
Cost is a token-price usage estimate at verified Starter rates: $0.046 per million input tokens and $10 per million output tokens. Measured input includes separately reported image tokens; measured output includes billed reasoning. No web searches were used. Account credits covered usage; this is not a card charge. Current source: https://levanto.ai/pricing.
The earlier 949-text-row Sage v1.1 run and its dated decision-unit estimate are preserved in v1.1/. Those historical subscription assumptions are not the current pricing model.
Training-data overlap has not been ruled out. Historical latency comparisons include different provider/network setups; they are not controlled inference-speed comparisons.

Corpus SHA256: `3599baea0d9c7e4e3d86c8b06af96e6850edca037b334bbc6b4e1a0033021725`.
Resolved model(s): levanto-sage-v1.3.

## Category results

| Category | Correct / rows | Accuracy |
|---|---:|---:|
| agents | 133/154 | 86.36% |
| commerce | 83/90 | 92.22% |
| data | 124/126 | 98.41% |
| design | 27/30 | 90.00% |
| documents | 78/87 | 89.66% |
| engineering | 141/150 | 94.00% |
| finance | 119/121 | 98.35% |
| legal | 118/126 | 93.65% |
| product | 39/60 | 65.00% |
| safety | 58/60 | 96.67% |
| support | 63/67 | 94.03% |

## Identical-row comparisons

Sage minus each comparison model. Intervals use 2,000 paired row bootstrap samples (seed 42), without adjustment for task clustering or multiple comparisons.

| Model | Shared rows | Accuracy | Sage difference | 95% interval |
|---|---:|---:|---:|---:|
| pplx-decider-v1.1-27b | 1071 | 94.49% | -2.71 pp | -4.11 to -1.31 pp |
| gemini-3.5-flash | 1071 | 94.21% | -2.43 pp | -3.92 to -0.84 pp |
| gemini-flash-lite-latest | 1071 | 94.12% | -2.33 pp | -3.73 to -0.84 pp |
| gpt-6-luna | 1071 | 93.65% | -1.87 pp | -3.55 to -0.19 pp |
| deepseek-v4.1-flash | 1071 | 92.72% | -0.93 pp | -2.52 to +0.75 pp |
| claude-sonnet-5 | 1071 | 92.62% | -0.84 pp | -2.52 to +0.84 pp |
| gpt-5.6-luna | 1071 | 92.62% | -0.84 pp | -2.61 to +0.84 pp |
| jev-1.13 | 1071 | 92.44% | -0.65 pp | -2.24 to +0.93 pp |
| glm-5.3-flash | 1071 | 92.25% | -0.47 pp | -2.05 to +1.21 pp |
| claude-haiku-4.5 | 1071 | 90.57% | +1.21 pp | -0.47 to +2.89 pp |
| gpt-6-luna-decisions | 1071 | 90.48% | +1.31 pp | -0.47 to +3.08 pp |
| tev1-4b-experimental | 949 | 85.35% | +5.69 pp | +3.48 to +7.90 pp |
| qwen3-32b | 1071 | 79.65% | +12.14 pp | +9.90 to +14.38 pp |
| nova-micro-v1 | 1071 | 66.39% | +25.40 pp | +22.50 to +28.48 pp |
| laya-routed | 1071 | 52.75% | +39.03 pp | +35.85 to +42.20 pp |

## Reproduce

`python3 scripts/run_sage.py full` resumes the frozen Sage 1.3 full-corpus run. `python3 scripts/summarize_sage.py` rebuilds this report. Published predictions and scores are in `results/bench-v4/sage/`; private raw responses remain under `runs/`.

Levanto logo: official site icon, downloaded from https://levanto.ai/favicon/android-chrome-192x192.png.

## Pricing reconciliation

The full run used 989,879 input tokens (including images) and 39,087 billed output tokens. At the verified Starter rates, its metered usage estimate is $0.436404434 ($0.407473795 per 1,000 cases). The full run, five smoke calls and two successful probes total $0.43745551; the provider dashboard reports $0.4375 for Sage 1.3, matching at its displayed precision. See [pricing-audit.json](pricing-audit.json).
