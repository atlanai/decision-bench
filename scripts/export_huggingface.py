#!/usr/bin/env python3
"""Stage an explicit, credential-free Hugging Face dataset release."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from decision_bench.corpus import digest as corpus_digest, load_cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New, empty staging directory")
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error("Output must be empty; refusing to overwrite a release")
    corpus = ROOT / "data/corpus/bench-v4/cases.jsonl"
    manifest = json.loads(corpus.with_name("manifest.json").read_text())
    rows = load_cases(corpus)
    digest = corpus_digest(rows)
    if digest != manifest["sha256"]:
        raise ValueError("Corpus does not match frozen manifest")
    tracked = set(subprocess.check_output(
        ["git", "ls-files"], cwd=ROOT, text=True).splitlines())
    selected = {
        "data/corpus/current.json", "data/corpus/bench-v4/cases.jsonl",
        "data/corpus/bench-v4/manifest.json", "data/SOURCES.md",
        "data/datasets.json", "data/sources/manifest.json", "data/sources/README.md",
        "docs/protocol.md", "docs/tasks.md", "docs/authoring-v4.md",
        "docs/data-release-review.md", "docs/data-release-review.json",
        "SECURITY.md", "CITATION.cff", "LICENSE",
    }
    selected.update(p for p in tracked if p.startswith("data/sources/")
                    and Path(p).name.startswith("LICENSE"))
    assets = {a["path"] for row in rows for a in row["assets"]}
    selected.update(assets)
    for name in sorted(selected):
        if name not in tracked:
            raise ValueError(f"Release file is not tracked: {name}")
        src = ROOT / name
        if src.is_symlink() or not src.is_file():
            raise ValueError(f"Release file is not a regular file: {name}")
        dest = out / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    # Heterogeneous evidence/source objects and option keys do not form one
    # stable Arrow struct. Keep these losslessly as JSON strings for the viewer;
    # the canonical corpus above stays byte-identical for the official harness.
    with (out / "test.jsonl").open("w") as handle:
        for row in rows:
            exported = {
                key: json.dumps(value, ensure_ascii=False, sort_keys=True)
                if key in {"state", "source", "questions", "assets"} else value
                for key, value in row.items()
            }
            handle.write(json.dumps(exported, ensure_ascii=False) + "\n")
    card = (ROOT / "docs/huggingface-dataset-card.md").read_text()
    (out / "README.md").write_text(card.replace("{{CORPUS_SHA256}}", digest))
    (out / "DATA_LICENSE.md").write_text(
        "# Data licenses\n\nThis is a collection of independently licensed public "
        "source material, not an MIT-licensed dataset. Each row retains its source "
        "terms. See [source attribution](data/SOURCES.md), the original notices "
        "under data/sources/, and [release review](docs/data-release-review.md). "
        "Preserve attribution and applicable share-alike requirements. The root "
        "LICENSE and CITATION.cff license field apply to the benchmark software.\n")
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    receipt = {
        "source_commit": commit, "corpus_sha256": digest, "rows": len(rows),
        "tasks": len({r["task"] for r in rows}), "unique_assets": len(assets),
        "files": {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(out.rglob("*")) if p.is_file()},
    }
    (out / "release.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "files"}, indent=2))
    print(f"Staged {len(receipt['files']) + 1} files in {out}")


if __name__ == "__main__":
    main()
