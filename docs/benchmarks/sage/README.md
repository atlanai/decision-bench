# Sage (Levanto) benchmark

**874/949 correct (92.10%)**. 6 abstentions; 0 operational errors.

Median end-to-end latency: 733 ms; p95: 4460 ms.
Accuracy Wilson 95% interval: 90.21%–93.65%.

## Method

One serial request per row, reasoning `auto`, no grounding/web search. Native Choice endpoint; the server selects the version, recorded in each result. All 949 rows without image assets from bench-v4 were evaluated; all 122 image-containing rows were excluded. This is a partial evaluation, not a full-corpus leaderboard entry. Model inputs contain only state, question instructions and options.
A null choice counts as unanswered and incorrect, not an API failure. No argmax is substituted. Independent option probabilities are renormalized for categorical diagnostics; these metrics do not measure the provider’s original calibrated confidence. Raw probabilities are retained in local responses.
The run uses granted decision credits. Dollar cost remains unavailable because subscription decision units cannot be converted into a measured per-call dollar charge. Input token counts are the provider’s billed_input_tokens field, not a local tokenizer estimate.
Training-data overlap has not been ruled out. Historical latency comparisons include different provider/network setups; they are not controlled inference-speed comparisons.

Corpus SHA256: `3599baea0d9c7e4e3d86c8b06af96e6850edca037b334bbc6b4e1a0033021725`.
Resolved model(s): levanto-sage-v1.1.

## Category results

| Category | Correct / rows | Accuracy |
|---|---:|---:|
| agents | 135/154 | 87.66% |
| commerce | 83/90 | 92.22% |
| data | 92/94 | 97.87% |
| documents | 45/57 | 78.95% |
| engineering | 140/150 | 93.33% |
| finance | 89/91 | 97.80% |
| legal | 117/126 | 92.86% |
| product | 50/60 | 83.33% |
| safety | 58/60 | 96.67% |
| support | 65/67 | 97.01% |

## Identical-row comparisons

Sage minus each comparison model. Intervals use 2,000 paired row bootstrap samples (seed 42), without adjustment for task clustering or multiple comparisons.

| Model | Shared rows | Accuracy | Sage difference | 95% interval |
|---|---:|---:|---:|---:|
| deepseek-v4.1-flash | 949 | 93.68% | -1.58 pp | -3.27 to +0.21 pp |
| gemini-3.5-flash | 949 | 93.47% | -1.37 pp | -3.06 to +0.32 pp |
| gemini-flash-lite-latest | 949 | 93.36% | -1.26 pp | -3.16 to +0.53 pp |
| jev-1.13 | 949 | 93.15% | -1.05 pp | -2.63 to +0.63 pp |
| glm-5.3-flash | 949 | 93.05% | -0.95 pp | -2.53 to +0.74 pp |
| gpt-6-luna | 949 | 92.94% | -0.84 pp | -2.74 to +0.95 pp |
| claude-sonnet-5 | 949 | 91.68% | +0.42 pp | -1.37 to +2.32 pp |
| gpt-5.6-luna | 949 | 91.68% | +0.42 pp | -1.58 to +2.42 pp |
| claude-haiku-4.5 | 949 | 89.57% | +2.53 pp | +0.63 to +4.53 pp |
| tev1-4b-experimental | 949 | 85.35% | +6.74 pp | +4.53 to +8.96 pp |
| qwen3-32b | 949 | 80.93% | +11.17 pp | +8.75 to +13.70 pp |
| nova-micro-v1 | 949 | 66.91% | +25.18 pp | +21.92 to +28.56 pp |
| laya-routed | 949 | 51.21% | +40.89 pp | +37.51 to +44.26 pp |

## Reproduce

`python3 scripts/run_sage.py full` resumes the frozen text run. `python3 scripts/summarize_sage.py` rebuilds this report. Published predictions and scores are in `results/bench-v4/sage/`; private raw responses remain under `runs/`.

Levanto logo: official site icon, downloaded from https://levanto.ai/favicon/android-chrome-192x192.png.
