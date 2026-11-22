# Kev 4B benchmark

The published result in `results/bench-v4/kev-4b/` covers all 1,071 rows (run `kev-4b-bench-v4-r1`, 21 November
2026). The model reads no images, so its 122 image rows use their text rendering.

The earlier run on the 949 text-only rows (run `kev-4b-bench-v4-text-v1`, 12 October 2026, 795/949) is preserved in
`text-v1/published-results/`. Both runs resolved to checkpoint `jaredpalmer/kev-4b-20260924`. The new run gives the
same answer on 945 of those 949 rows and gets 793 of them right.
