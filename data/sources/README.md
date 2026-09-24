# Upstream source files

`scripts/fetch_sources.py` downloads the upstream files that the rows are sampled from into this folder. Each module in `authoring/bench/` lists what it needs in `SOURCES`. The downloads are not committed. `manifest.json` pins each file's URL, size and sha256, and the script fails if an upstream file has changed.

Each dataset's licence, dataset card or terms file is committed next to its folder as `LICENSE*`. You don't need any of this to run the benchmark: the built corpus is committed in `data/corpus/`.
