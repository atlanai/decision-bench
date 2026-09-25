#!/usr/bin/env python3
"""Package an export_huggingface.py output for the Hub's flat file uploader."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
src, out = args.source.resolve(), args.output.resolve()
if out.exists() and any(out.iterdir()):
    parser.error('Output must be empty')
if out == src or out.is_relative_to(src):
    parser.error('Output must be outside the source export')
receipt = json.loads((src / 'release.json').read_text())
for name, digest in receipt['files'].items():
    path = (src / name).resolve()
    if not path.is_relative_to(src) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError(f'Export integrity check failed: {name}')
out.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(out / 'decision-bench-v1.0.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in sorted([*receipt['files'], 'release.json']):
        archive.write(src / name, name)
for name in ['test.jsonl', 'DATA_LICENSE.md', 'LICENSE', 'SECURITY.md', 'CITATION.cff']:
    shutil.copyfile(src / name, out / name)
links = {'docs/protocol.md': 'protocol.md', 'docs/tasks.md': 'tasks.md',
         'docs/data-release-review.md': 'data-release-review.md', 'data/SOURCES.md': 'SOURCES.md'}
for source, target in links.items():
    shutil.copyfile(src / source, out / target)
card = (src / 'README.md').read_text()
for source, target in links.items():
    card = card.replace(source, target)
card = card.replace('Asset paths are relative to this repository root.',
                    'Asset paths are relative to the root of the downloadable release archive.')
card = card.replace('The original corpus is preserved byte-for-byte at `data/corpus/bench-v4/cases.jsonl`.',
                    '[Download the complete release](decision-bench-v1.0.zip) for all 106 images, source notices, and the original corpus, preserved byte-for-byte at `data/corpus/bench-v4/cases.jsonl` inside the archive.')
card = card.replace('`release.json` records the source commit and hashes of packaged files.',
                    '`release.json` inside the archive records the source commit and hashes of packaged files. `upload-manifest.json` checksums this Hub distribution.')
card = card.replace('packaged source notices', 'source notices packaged in the release archive')
(out / 'README.md').write_text(card)
license_path = out / 'DATA_LICENSE.md'
license_path.write_text(license_path.read_text().replace('data/SOURCES.md', 'SOURCES.md')
    .replace('docs/data-release-review.md', 'data-release-review.md')
    .replace('under data/sources/', 'under data/sources/ inside decision-bench-v1.0.zip'))
manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file()}
(out / 'upload-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(f'Packaged {len(manifest) + 1} files in {out}')
