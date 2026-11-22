# Microsoft Decision 1 benchmark

The published result in `results/bench-v4/microsoft-decision-1/` covers all 1,071 rows (run
`microsoft-decision-1-bench-v4-r1`, 21 November 2026). The model reads no images, so its 122 image rows use their
text rendering.

The earlier run on the 949 text-only rows (run `microsoft-decision-1-bench-v4-text-v1`, 10 October 2026, 861/949) is
preserved in `text-v1/published-results/`. Both runs resolved to checkpoint `microsoft/microsoft-decision-1-20261009`.
The new run gives the same answer on 894 of those 949 rows and gets 866 of them right. Its three November runs got
968, 974 and 976 of 1,071, so the model is not fully deterministic.
