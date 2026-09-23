#!/usr/bin/env python3
"""Download the public source files that bench-v3 rows are sampled from, and verify their hashes.

Each module in authoring/bench declares SOURCES = [{"dataset", "url", "path", optional "zip_member"}], where path is relative to
data/sources. Files are not committed; data/sources/manifest.json pins their sha256.

  python3 scripts/fetch_sources.py            # download missing files, verify all against the manifest
  python3 scripts/fetch_sources.py --pin      # record hashes of the files now present (maintainers only)
  python3 scripts/fetch_sources.py --only pii # limit to one module
"""
import argparse
import concurrent.futures
import hashlib
import json
import sys
import urllib.request
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from authoring import bench

MANIFEST = bench.SOURCES / "manifest.json"


def declared(only=None):
    files = []
    for name in bench.MODULES:
        if only and name != only:
            continue
        for s in getattr(import_module(f"authoring.bench.{name}"), "SOURCES", []):
            files.append({**s, "module": name})
    return files


def download(entry):
    target = bench.SOURCES / entry["path"]
    if target.exists() and target.stat().st_size:
        return entry["path"], "present"
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(entry["url"], headers={"User-Agent": "DecisionBench/3 (source fetch)"})
    with urllib.request.urlopen(request, timeout=300) as response:
        data = response.read()
    if entry.get("zip_member"):  # e.g. one split inside a dataset archive; the archive itself is not kept
        import io
        import zipfile
        data = zipfile.ZipFile(io.BytesIO(data)).read(entry["zip_member"])
    tmp = target.with_suffix(target.suffix + ".part")
    tmp.write_bytes(data)
    tmp.replace(target)
    return entry["path"], f"downloaded {len(data):,} bytes"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pin", action="store_true")
    parser.add_argument("--only")
    parser.add_argument("--jobs", type=int, default=8)
    args = parser.parse_args()
    files = declared(args.only)
    with concurrent.futures.ThreadPoolExecutor(args.jobs) as pool:
        for path, status in pool.map(download, files):
            print(f"{status:>24}  {path}")
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    pinned = manifest.setdefault("files", {})
    failures = 0
    for entry in files:
        data = (bench.SOURCES / entry["path"]).read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        record = {"dataset": entry["dataset"], "url": entry["url"], "bytes": len(data), "sha256": sha}
        if args.pin:
            pinned[entry["path"]] = record
        elif entry["path"] in pinned and pinned[entry["path"]]["sha256"] != sha:
            failures += 1
            print(f"HASH MISMATCH {entry['path']}: upstream changed; rows may differ from the frozen corpus")
    if args.pin:
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"pinned {len(files)} files in {MANIFEST.relative_to(ROOT)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
