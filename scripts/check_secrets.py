#!/usr/bin/env python3
"""Fail if a committed text file contains a credential, a private hostname or a local home path.

Scans every file git would commit (tracked plus untracked-but-not-ignored). Third-party corpus data
(data/corpus/, data/sources/, and the scrubbed CredData excerpts, whose credential-shaped values are random
fakes) is checked only for live credential formats, since real records legitimately contain paths, hostnames and
secret-looking strings. Exit status 1 when anything is found.

  python3 scripts/check_secrets.py [ROOT]
"""
from __future__ import annotations

import math
import re
import subprocess
import sys
from urllib.parse import urlsplit
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THIRD_PARTY = ("data/corpus/", "data/sources/", "data/assets/", "authoring/bench/engineering_creddata.json")
SKIP_DIRS = {".git", "runs", "__pycache__", ".venv", "node_modules"}
MAX_BYTES = 20_000_000

# Live credential formats. Checked everywhere, including corpus data.
CREDENTIALS = [
    ("Together API key", r"\btgp_v[0-9]+_[A-Za-z0-9_-]{20,}"),
    ("Levanto API key", r"\blv_live_[A-Za-z0-9_-]{20,}"),
    ("AWS access key", r"\bAKIA[0-9A-Z]{16}\b"),
    ("GitHub token", r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    ("Slack token", r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    ("Stripe live key", r"\b[sr]k_live_[A-Za-z0-9]{20,}"),
    ("Google API key", r"\bAIza[0-9A-Za-z_-]{35}\b"),
    ("private key", r"-----BEGIN [A-Z ]*PRIVATE KEY"),
    ("OpenAI/Anthropic-style key", r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{24,}"),
    ("GitHub fine-grained token", r"\bgithub_pat_[A-Za-z0-9_]{22,}"),
    ("Laya API key", r"\bimp-rt-[A-Za-z0-9_-]{24,}"),
    ("bearer token", r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{24,}"),
]
# Checked in code, config and docs. Strings are split so this file does not match itself.
PROJECT = [
    ("internal proxy host", "llm" + "proxy"),
    ("company URL", r"(?i)[a-z][a-z0-9+.-]*://[^\s\"'<>)]*" + "at" + "lan" + r"[^\s\"'<>)]*"),
    ("private hostname", r"(?i)\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:internal|corp|intranet|lan)\b(?![\w-])"),
    ("private IP address", r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b"),
    ("home directory", r"(?<![\w.])/" + r"Users/[A-Za-z0-9._-]+|(?<![\w.])/" + r"home/[a-z][a-z0-9_-]*/|[A-Z]:\\" + r"Users\\"),
    ("infrastructure field", r"\b(?:deploy" + r"ment_ids?|gateway_" + r"base_url)\b"),
]
# Documented placeholder values (e.g. AWS's AKIA...EXAMPLE) are not credentials.
PLACEHOLDER = re.compile(r"EXAMPLE|X{8,}|0{16,}")
ASSIGNMENT = re.compile(r"(?i)(?:api[_-]?key|secret|token|password|passwd)[\"']?\s*[:=]\s*[\"']([A-Za-z0-9/+_.=-]{20,})[\"']")
CREDENTIAL_RE = [(name, re.compile(p)) for name, p in CREDENTIALS]
PROJECT_RE = [(name, re.compile(p)) for name, p in PROJECT]


def public_repository_url(value):
    """The public project destination is allowed; other company URLs remain findings."""
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    repository = "/at" + "lanai/decision-bench"
    if parsed.netloc == "huggingface.co":
        repository = "/datasets" + repository
    return (parsed.scheme == "https" and parsed.netloc in {"github.com", "huggingface.co"}
            and ".." not in parsed.path.split("/")
            and (parsed.path == repository or parsed.path.startswith(repository + "/")))


def entropy(s):
    counts = {c: s.count(c) for c in set(s)}
    return -sum(n / len(s) * math.log2(n / len(s)) for n in counts.values())


def files(root):
    try:
        out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root,
                             capture_output=True, text=True, check=True).stdout
        paths = [p for p in out.split("\0") if p]
    except (OSError, subprocess.CalledProcessError):
        paths = [str(p.relative_to(root)) for p in root.rglob("*")
                 if p.is_file() and not SKIP_DIRS & set(p.relative_to(root).parts)]
    return sorted(p for p in paths if (root / p).is_file())


def scan_text(rel, text):
    findings = []
    third_party = rel.startswith(THIRD_PARTY)
    rules = CREDENTIAL_RE + ([] if third_party else PROJECT_RE)
    for lineno, line in enumerate(text.splitlines(), 1):
        for name, rx in rules:
            for m in rx.finditer(line):
                if name == "company URL" and public_repository_url(m.group(0)):
                    continue
                if not PLACEHOLDER.search(m.group(0)):
                    findings.append((rel, lineno, name, "[REDACTED]"))
                    break
        if not third_party:
            for m in ASSIGNMENT.finditer(line):
                if entropy(m.group(1)) >= 3.5 and not PLACEHOLDER.search(m.group(1)):
                    findings.append((rel, lineno, "high-entropy secret assignment", "[REDACTED]"))
    return findings


def scan(root=ROOT):
    root = Path(root)
    findings = []
    for rel in files(root):
        path = root / rel
        if path.stat().st_size > MAX_BYTES:
            continue
        data = path.read_bytes()
        if b"\0" in data[:4096]:
            continue
        findings += scan_text(rel, data.decode("utf-8", errors="replace"))
    return findings


def main(argv):
    root = Path(argv[1]) if len(argv) > 1 else ROOT
    findings = scan(root)
    for rel, lineno, name, excerpt in findings:
        print(f"{rel}:{lineno}: {name}: {excerpt}")
    print(f"{len(findings)} finding(s) in {len(files(root))} files", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
