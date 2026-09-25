# Publishing Decision Bench on Hugging Face

The dataset is hosted at https://huggingface.co/datasets/goelrohan6/decision-bench.
The website's footer and Data page use the `huggingface-dataset` metadata value in `web/index.html`.

Create a new staging directory for each export:

```sh
python3 -m decision_bench validate
python3 scripts/export_huggingface.py tmp/hf-release
python3 scripts/package_huggingface_web.py tmp/hf-release tmp/hf-web-upload
```

Upload the files inside `tmp/hf-web-upload` to the dataset repository root. The Hub viewer reads only `test.jsonl`, configured as the `bench-v4` test split. Its four heterogeneous JSON fields decode losslessly to the canonical row objects. The downloadable archive preserves the canonical corpus, all referenced images, source notices, and license/privacy documentation at their original paths.

Verify the uploaded files against `upload-manifest.json`, the archive against its internal `release.json`, and the viewer's row count before linking a new destination. Do not upload the repository root, raw source downloads, environment files, local run ledgers, or editorial drafts. The corpus retains its source licenses; the code's MIT license does not relicense source material.

If the dataset moves to the Atlan organization, update the card's load example and license link, this document, and the website metadata to the verified new URL.
