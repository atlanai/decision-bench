# Kev 27B benchmark

The published result in `results/bench-v4/kev-27b/` covers all 1,071 rows (run `kev-27b-bench-v4-full-v1`,
21 November 2026). Kev 27B reads no images, so its 122 image rows use their text rendering.

The earlier run on the 949 text-only rows (run `kev-27b-bench-v4-text-v1`, 12 October 2026, 866/949) is preserved in
`text-v1/published-results/`. Every one of those 949 rows gets the same answer in the full run.

`server-receipt.json` records the deployment of the full run.
