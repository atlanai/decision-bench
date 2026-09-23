"""engineering: code changes, commits, vulnerabilities and secrets.

ENG-1  Which file must change? SWE-bench Verified: a GitHub issue from a permissively licensed Python project and
       four to six file paths from that project; one is the single non-test file the merged fix changed.
ENG-2  What kind of change is this? CommitPackFT: a one-file unified diff whose developer wrote a Conventional
       Commit prefix (fix / feat / docs / refactor / test); the diff is shown, never the message.
ENG-3  Which weakness class is this? NVD: a CVE description, with NVD analysts' primary CWE mapped to one of six
       weakness classes.
ENG-4  Live secret or placeholder? Samsung CredData: a secret scanner's hit in a permissively licensed repository,
       judged by CredData's reviewers; ported from bench-v3 PII-2 and grown from 24 to 30 rows.
ENG-5  Which message describes this diff? CommitPackFT: a one-file diff and four real commit messages from the
       same repository, one of which is the diff's own.

CommitBench (Maxscha/commitbench), the source named for ENG-2 and ENG-5, is CC BY-NC 4.0 and so fails the licence
policy; both tasks use CommitPackFT (bigcode/commitpackft, MIT, one repository licence recorded per sample)
instead. ENG-2 keeps its label (the developer's own prefix), ENG-5 its shape.

Written sampling rules
----------------------
ENG-1  All 500 SWE-bench Verified instances are read through the Hugging Face rows API. Eligible: the repository
       licence is MIT, Apache-2.0, BSD-2-Clause or BSD-3-Clause (pylint, GPL-2.0, and matplotlib, whose own PSF-style
       licence is not on the benchmark's list, are excluded); the gold patch touches exactly one file, a .py file
       outside test directories; the issue text is 150–8,000 characters (trimmed to 3,500 with a marker). Distractor
       paths are real non-test .py files changed by the gold patches of other Verified instances in the same
       repository, in a different directory from the answer and from each other, with a different base name from the
       answer, and whose path or base name is not mentioned in the issue; the first four in rank(instance/path)
       order are used, and instances with fewer than four are dropped. Rows are taken in rank(instance_id) order,
       at most eight per repository, until 30.
ENG-2  CommitPackFT's Rust, Go and TypeScript files (34 MB together). Eligible: the commit message starts with
       fix, feat, docs, refactor or test, optionally scoped, then a colon; the sample's repository licence is MIT,
       Apache-2.0, BSD-2/3-Clause, ISC, CC0-1.0 or Unlicense; the unified diff of the one file (three lines of
       context, computed from the sample's old and new contents) is 300–4,000 characters; the repository name
       contains no label word. Six rows per prefix in rank(commit/file) order, at most one row per repository.
       Rows passed over by hand are in ENG2_SKIP with the reason.
ENG-3  Five nine-day publication windows of 2023 from the NVD 2.0 API (each under the 2,000-result page limit;
       five requests fit the API's public rate limit of five per rolling 30 seconds). Eligible: a weakness entry
       from nvd@nist.gov of type Primary with exactly one CWE id, and that id in exactly one of the six groups
       below; an English description of 80–1,200 characters that is not a rejected or disputed record and is more
       than a bare product-and-title line. Per class, rows are taken in rank(CVE id) order: the first four whose
       description does not name the class (per-class regex), then one that does, at most two rows per reporting
       CNA per class. Rows passed over by hand are in ENG3_SKIP.
ENG-4  The 24 bench-v3 rows are kept unchanged (same order key sha256("pii-2/<Id>"), same rules, see the v3 module
       docstring reproduced in authoring/bench/engineering_creddata.json's "rules" entry). Six rows were added by
       continuing the same walk: the next two lines per label that pass the v3 rules, come from a repository not yet
       used whose GitHub licence is MIT, Apache-2.0, BSD-2/3-Clause, ISC, CC0-1.0 or Unlicense, and survive a read
       (lines passed over are in CRED_EXCLUDED with the reason). Every credential-shaped value in a shown excerpt is
       replaced by a random same-shape fake before it is written to the JSON; the originals are recorded nowhere.
ENG-5  Same files and licence rule as ENG-2. Eligible repositories have at least four distinct commits with
       distinct first message lines of 20–120 characters that carry no URL and no issue number; the target commit's
       diff is 300–5,000 characters and its message shares at least one content word (5+ letters, not a stop word)
       with the diff, while each distractor message has at least one content word absent from both the diff and the
       target message. Distractors are the three eligible messages closest in length to the target's. Rows in
       rank(commit/file) order, one per repository, until 30. Hand skips in ENG5_SKIP.
"""
from __future__ import annotations

import collections
import difflib
import json
import os
import re

from . import dataset, task, row, rank, SOURCES as SOURCE_DIR, ROOT

CATEGORY = "engineering"

# ------------------------------------------------------------------------------------------------ sources
SWE_REVISION = "c104f840cc67f8b6eec6f759ebc8b2693d585d4a"           # princeton-nlp/SWE-bench_Verified, read 2026-09-23
SWE_CODE_COMMIT = "main"
SWE_OFFSETS = [0, 100, 200, 300, 400]
CPFT_REVISION = "fc56fe33c030c6daa414c2b112c932b8eed085e6"          # bigcode/commitpackft
CPFT_LANGS = ["rust", "go", "typescript"]
NVD_WINDOWS = [("2023-01-10", "2023-01-18"), ("2023-03-07", "2023-03-15"), ("2023-05-09", "2023-05-17"),
               ("2023-07-11", "2023-07-19"), ("2023-09-12", "2023-09-20")]
CRED_COMMIT = "c09c0c52fc6dae4ae5438ae69ba486f9f8059f0d"
CRED_REPO = "https://github.com/Samsung/CredData"
CRED_RAW = f"https://raw.githubusercontent.com/Samsung/CredData/{CRED_COMMIT}"
EXCERPTS = ROOT / "authoring/bench/engineering_creddata.json"
_CRED = json.loads(EXCERPTS.read_text(encoding="utf-8"))

SOURCES = [
    {"dataset": "SWE-bench Verified", "path": f"swe-bench-verified/rows-{off:03d}.json",
     "url": ("https://datasets-server.huggingface.co/rows?dataset=princeton-nlp%2FSWE-bench_Verified"
             f"&config=default&split=test&offset={off}&length=100")} for off in SWE_OFFSETS
] + [
    {"dataset": "SWE-bench (licence)", "path": "swe-bench-verified/LICENSE",
     "url": "https://raw.githubusercontent.com/SWE-bench/SWE-bench/main/LICENSE"},
] + [
    {"dataset": "CommitPackFT", "path": f"commitpackft/{lang}.jsonl",
     "url": f"https://huggingface.co/datasets/bigcode/commitpackft/resolve/{CPFT_REVISION}/data/{lang}/data.jsonl"}
    for lang in CPFT_LANGS
] + [
    {"dataset": "CommitPackFT (dataset card)", "path": "commitpackft/README.md",
     "url": f"https://huggingface.co/datasets/bigcode/commitpackft/resolve/{CPFT_REVISION}/README.md"},
] + [
    {"dataset": "NVD (CVE API 2.0)", "path": f"nvd/{a}_{b}.json",
     "url": (f"https://services.nvd.nist.gov/rest/json/cves/2.0?pubStartDate={a}T00:00:00.000"
             f"&pubEndDate={b}T23:59:59.999&resultsPerPage=2000")} for a, b in NVD_WINDOWS
] + [
    {"dataset": "Samsung CredData", "url": f"{CRED_RAW}/LICENSE", "path": "creddata/LICENSE"},
] + [
    {"dataset": "Samsung CredData (metadata)", "url": f"{CRED_RAW}/meta/{m}.csv", "path": f"creddata/meta/{m}.csv"}
    for m in sorted({e["meta"] for e in _CRED["excerpts"]})
]

PERMISSIVE_REPO = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "CC0-1.0", "Unlicense"}
CPFT_PERMISSIVE = {"mit": "MIT", "apache-2.0": "Apache-2.0", "bsd-3-clause": "BSD-3-Clause",
                   "bsd-2-clause": "BSD-2-Clause", "isc": "ISC", "cc0-1.0": "CC0-1.0", "unlicense": "Unlicense"}
TRIM = "…[{n:,} chars truncated]"


def _trim(text, limit):
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + " " + TRIM.format(n=len(text) - limit)


def _no_words(title, banned, where):
    low = title.lower()
    hits = [w for w in banned if re.search(rf"\b{re.escape(w)}\b", low)]
    assert not hits, f"{where}: title {title!r} contains answer words {hits}"


# ------------------------------------------------------------------------------------------------ datasets
SWE_CITATION = ("Jimenez et al., SWE-bench: Can Language Models Resolve Real-World GitHub Issues?, ICLR 2024; "
                "SWE-bench Verified (OpenAI and the SWE-bench authors, 2024), princeton-nlp/SWE-bench_Verified.")
CPFT_CITATION = "Muennighoff et al., OctoPack: Instruction Tuning Code Large Language Models, ICLR 2024 (CommitPackFT)."
NVD_CITATION = ("National Institute of Standards and Technology, National Vulnerability Database (NVD), CVE API 2.0; "
                "descriptions are CVE Records of the CVE Program (MITRE).")
CRED_CITATION = "Yun et al., Project CredData: A Dataset of Credentials for Research, Samsung, 2021."


def _datasets():
    dataset(id="swe-bench-verified", name="SWE-bench Verified", tasks=["ENG-1"],
            homepage="https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified",
            license="MIT",
            license_url="https://github.com/SWE-bench/SWE-bench/blob/main/LICENSE",
            content="The title and body of a GitHub issue from one of the Python projects SWE-bench draws on (django, "
                    "sympy, sphinx, scikit-learn, astropy, xarray, pytest, requests, seaborn, flask), plus file paths "
                    "from that project; the answer is the file the merged pull request changed.",
            content_license="BSD-3-Clause",
            content_terms="The SWE-bench project (dataset build code and the released instances) is MIT; the Hugging "
                          "Face card of SWE-bench Verified carries no separate licence field (read at revision "
                          f"{SWE_REVISION}). Issue text is written by the projects' users on GitHub; this benchmark "
                          "keeps only projects whose own licence is MIT, Apache-2.0, BSD-2-Clause or BSD-3-Clause and "
                          "records that licence per row (source.repo_license): django, sympy, scikit-learn, astropy, "
                          "seaborn and flask are BSD-3-Clause, sphinx BSD-2-Clause, xarray and requests Apache-2.0, "
                          "pytest MIT. pylint (GPL-2.0) and matplotlib (its own PSF-style licence) are excluded. File "
                          "paths are facts about the repository.",
            labelled_by="the merged pull request that closed the issue (the SWE-bench gold patch)",
            changes="Issue text longer than 3,500 characters is cut with a visible marker; the hints, tests and patch "
                    "are not shown. Distractor paths come from other instances' gold patches in the same repository.",
            selection="Instances whose gold patch changes exactly one non-test .py file, in sha256 order of the "
                      "instance id, at most eight per repository, with four real distractor paths from other "
                      "directories of the same repository; see the module docstring.",
            citation=SWE_CITATION,
            bibtex="""@inproceedings{jimenez2024swebench,
  title     = {{SWE}-bench: Can Language Models Resolve Real-world Github Issues?},
  author    = {Carlos E Jimenez and John Yang and Alexander Wettig and Shunyu Yao and Kexin Pei and Ofir Press and Karthik R Narasimhan},
  booktitle = {The Twelfth International Conference on Learning Representations},
  year      = {2024},
  url       = {https://openreview.net/forum?id=VTF8yNQM66}
}""")
    dataset(id="commitpackft", name="CommitPackFT", tasks=["ENG-2", "ENG-5"],
            homepage="https://huggingface.co/datasets/bigcode/commitpackft",
            license="MIT",
            license_url=f"https://huggingface.co/datasets/bigcode/commitpackft/blob/{CPFT_REVISION}/README.md",
            content="One file's before-and-after contents from a real GitHub commit (Rust, Go and TypeScript files), "
                    "rendered as a unified diff, and the commit's message; every sample names its repository and the "
                    "repository's licence.",
            content_license="MIT",
            content_terms="The card's licence field is mit and its Licensing Information section says \"Each sample "
                          "comes from a code repository with a permissive license. The license is provided by the "
                          "`license` field for each sample.\" This benchmark keeps only samples whose repository "
                          "licence is mit, apache-2.0, bsd-3-clause, bsd-2-clause, isc, cc0-1.0 or unlicense and "
                          "records it per row (source.repo_license); mpl, epl, lgpl, agpl, artistic and unknown are "
                          "skipped.",
            labelled_by="the developer who wrote the commit (ENG-2: the Conventional Commit prefix of their message; "
                        "ENG-5: the message itself)",
            changes="The diff is computed from the sample's old and new file contents with three lines of context "
                    "(CommitPackFT stores whole files, not diffs). ENG-2 shows the diff only, never the message. "
                    "ENG-5 shows the first line of each message. Nothing else is changed.",
            selection="Written rules in the module docstring: prefix, licence and diff-length filters for ENG-2, six "
                      "rows per prefix in sha256 order; same-repository message sets for ENG-5, one row per "
                      "repository in sha256 order.",
            citation=CPFT_CITATION,
            bibtex="""@inproceedings{muennighoff2024octopack,
  title     = {OctoPack: Instruction Tuning Code Large Language Models},
  author    = {Niklas Muennighoff and Qian Liu and Armel Zebaze and Qinkai Zheng and Binyuan Hui and Terry Yue Zhuo and Swayam Singh and Xiangru Tang and Leandro von Werra and Shayne Longpre},
  booktitle = {The Twelfth International Conference on Learning Representations},
  year      = {2024},
  url       = {https://openreview.net/forum?id=mw1PWNSWZP}
}""")
    dataset(id="nvd", name="NVD (National Vulnerability Database)", tasks=["ENG-3"],
            homepage="https://nvd.nist.gov/",
            license="Public domain",
            license_url="https://www.nist.gov/open/copyright-fair-use-and-licensing-statements-srd-data-software-and-technical-series-publications",
            content="The English description of a CVE record published in 2023, as served by the NVD CVE API 2.0, "
                    "with the CVE id and publication date; the answer is the CWE that NVD's analysts assigned.",
            content_license="cve-tou",
            content_terms="NVD is a NIST product: NIST says \"Data/works created by NIST employees ... are subject to "
                          "17 U.S.C. §105 and generally are not subject to copyright protection within the United "
                          "States\" (license_url) and its NVD FAQ says \"There are no fees, licensing restrictions, or "
                          "even a requirement to register\" (https://nvd.nist.gov/general/faq). The CWE assignment is "
                          "NVD's own analysis. The description text is CVE Record information from the CVE Program, "
                          "whose Terms of Use (SPDX id cve-tou, https://www.cve.org/Legal/TermsOfUse, text at "
                          "https://spdx.org/licenses/cve-tou.html) grant \"a perpetual, worldwide, non-exclusive, "
                          "no-charge, royalty-free, irrevocable copyright license to reproduce, prepare derivative "
                          "works of, publicly display, publicly perform, sublicense, and distribute\" CVE, provided "
                          "MITRE's copyright designation and the licence are reproduced: CVE is Copyright (c) "
                          "1999-2026 The MITRE Corporation; CVE and the CVE logo are registered trademarks of The "
                          "MITRE Corporation. Rows carry that notice in source.notice. NVD asks that services using "
                          "the API display: \"This product uses the NVD API but is not endorsed or certified by the "
                          "NVD.\"",
            labelled_by="NVD analysts (the weakness entry with source nvd@nist.gov and type Primary)",
            changes="None to the text. CWE ids are mapped to six classes by the written table in the module; only "
                    "records whose primary CWE falls in exactly one class are used.",
            selection="Five nine-day publication windows of 2023 (about 5,000 CVEs), filtered by the written rules, "
                      "then five per class in sha256 order of the CVE id: four whose description does not name the "
                      "class and one that does, at most two per reporting CNA per class.",
            citation=NVD_CITATION,
            bibtex="""@misc{nvd,
  author       = {{National Institute of Standards and Technology}},
  title        = {National Vulnerability Database (NVD), CVE API 2.0},
  howpublished = {\\url{https://nvd.nist.gov/developers/vulnerabilities}},
  year         = {2023}
}""")
    dataset(id="creddata", name="Samsung CredData", tasks=["ENG-4"], homepage=CRED_REPO,
            license="Apache-2.0", license_url=f"{CRED_REPO}/blob/{CRED_COMMIT}/LICENSE",
            content="One to five lines of source, config or documentation files from public GitHub repositories, "
                    "around a line that secret scanners flagged; CredData supplies the labels and line positions.",
            content_license="Apache-2.0",
            content_terms="CredData's labels and metadata are Apache-2.0; its README says \"Each file is under the "
                          "existing project's license\". Each excerpt here keeps its repository's licence, read from "
                          "GitHub's licence detection and the repository's licence file, and recorded per row "
                          "(source.code_license and source.code_license_file): MIT, Apache-2.0, BSD-3-Clause or ISC "
                          "for all 30 rows. The repository and the file's base name are shown (CredData hides both "
                          "behind ids; the repository is kept for attribution and the base name because it is part "
                          "of the evidence); nothing that locates the file is.",
            labelled_by="CredData's reviewers, who manually checked every scanner hit against written ground rules",
            changes="Every value CredData judged a real credential, and any other credential-shaped string in the "
                    "shown lines, is replaced with a random fake of the same length and character classes (AWS keys "
                    "with AWS's documented example pair). Only the flagged line and up to two lines either side are "
                    "shown. So that no row leads a reader to a live secret, every row (whatever its label) keeps only "
                    "the repository URL and licence, the CredData metadata file and Id, and the file's base name. The "
                    "scrubbed excerpts are committed in authoring/bench/engineering_creddata.json; the commit, "
                    "directory path and line number of the originals are recorded nowhere in this repository.",
            selection="Labelled lines from CredData repositories with a permissive GitHub licence, in sha256 order of "
                      "\"pii-2/<Id>\", 10 per label, at most one per repository, filtered by the written rules in the "
                      "module docstring; the 24 bench-v3 rows are kept and six added by continuing the same walk. "
                      "Lines dropped after reading are in CRED_EXCLUDED.",
            citation=CRED_CITATION,
            bibtex="""@misc{sr-cred21,
  author       = {JaeKu Yun and ShinHyung Choi and YuJeong Lee and Oleksandra Sokol and WooChul Shim and Arkadiy Melkonyan and Dmytro Kuzmenko},
  title        = {Project {CredData}: A Dataset of Credentials for Research},
  howpublished = {\\url{https://github.com/Samsung/CredData}},
  year         = {2021}
}""")


# ------------------------------------------------------------------------------------------------ ENG-1
SWE_LICENCE = {"django/django": "BSD-3-Clause", "sympy/sympy": "BSD-3-Clause", "sphinx-doc/sphinx": "BSD-2-Clause",
               "scikit-learn/scikit-learn": "BSD-3-Clause", "astropy/astropy": "BSD-3-Clause",
               "pydata/xarray": "Apache-2.0", "pytest-dev/pytest": "MIT", "psf/requests": "Apache-2.0",
               "mwaskom/seaborn": "BSD-3-Clause", "pallets/flask": "BSD-3-Clause"}
SWE_EXCLUDED_REPOS = {"pylint-dev/pylint": "GPL-2.0", "matplotlib/matplotlib": "Matplotlib (PSF-style) licence"}
ENG1_ISSUE_MAX = 3500
ENG1_PER_REPO = 8
ENG1_ROWS = 30
# Instances passed over after reading the issue against its option list.
ENG1_SKIP = {
    "sympy__sympy-18211": "the issue is about as_set()/solveset returning a ConditionSet; sympy/sets/sets.py is a "
                          "defensible second answer beside the file the fix changed",
}


def _swe_records():
    records = []
    for off in SWE_OFFSETS:
        page = json.loads((SOURCE_DIR / f"swe-bench-verified/rows-{off:03d}.json").read_text(encoding="utf-8"))
        assert not any(r["truncated_cells"] for r in page["rows"]), off
        records += [r["row"] for r in page["rows"]]
    assert len({r["instance_id"] for r in records}) == len(records) == 500
    return records


def _patch_files(patch):
    return re.findall(r"^diff --git a/(\S+) b/", patch, flags=re.M)


def _is_test_path(path):
    return bool(re.search(r"(^|/)(tests?|testing)(/|$)|(^|/)test_|_tests?\.py$|conftest", path))


def _eng1():
    records = _swe_records()
    pool = collections.defaultdict(set)
    for r in records:
        for p in _patch_files(r["patch"]):
            if p.endswith(".py") and not _is_test_path(p):
                pool[r["repo"]].add(p)
    candidates = []
    for r in records:
        if r["repo"] not in SWE_LICENCE:
            continue
        files = _patch_files(r["patch"])
        if len(files) != 1 or not files[0].endswith(".py") or _is_test_path(files[0]):
            continue
        issue = r["problem_statement"].strip()
        if not 150 <= len(issue) <= 8000:
            continue
        gold = files[0]
        low = issue.lower()
        others = [p for p in pool[r["repo"]]
                  if p != gold and os.path.dirname(p) != os.path.dirname(gold)
                  and os.path.basename(p) != os.path.basename(gold)
                  and os.path.basename(p).lower() not in low and p.lower() not in low]
        others.sort(key=lambda p: rank(f"{r['instance_id']}/{p}"))
        chosen, dirs, names = [], set(), set()
        for p in others:
            d, b = os.path.dirname(p), os.path.basename(p)
            if d in dirs or b in names:
                continue
            dirs.add(d)
            names.add(b)
            chosen.append(p)
            if len(chosen) == 4:
                break
        if len(chosen) < 4:
            continue
        candidates.append((r, gold, chosen))
    candidates.sort(key=lambda c: rank(c[0]["instance_id"]))
    per_repo = collections.Counter()
    taken = 0
    for r, gold, chosen in candidates:
        if r["instance_id"] in ENG1_SKIP or per_repo[r["repo"]] >= ENG1_PER_REPO:
            continue
        per_repo[r["repo"]] += 1
        taken += 1
        paths = sorted([gold] + chosen)
        number = r["instance_id"].rsplit("-", 1)[-1]
        title = f"GitHub issue · {r['repo']} · instance {number}"
        row("ENG-1", r["instance_id"].replace("__", "-"), title=title, gold=gold,
            options={p: f"{p} (a file in the repository)" for p in paths},
            state={"repository": f"github.com/{r['repo']}", "base_commit": r["base_commit"],
                   "issue": _trim(r["problem_statement"], ENG1_ISSUE_MAX), "candidate_files": paths},
            rationale=f"The merged fix for this issue changed {gold} and no other non-test file (the SWE-bench "
                      f"Verified gold patch); the other paths are files that other fixes in this repository touched.",
            source={"dataset_id": "swe-bench-verified", "dataset": "SWE-bench Verified", "license": "MIT",
                    "url": f"https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified/viewer/default/test?q="
                           f"{r['instance_id']}",
                    "citation": SWE_CITATION, "record_id": f"instance_id {r['instance_id']}",
                    "original_label": f"gold patch touches {gold}",
                    "labelled_by": "the merged pull request that closed the issue (SWE-bench gold patch)",
                    "repo": f"https://github.com/{r['repo']}", "repo_license": SWE_LICENCE[r["repo"]],
                    "difficulty": r["difficulty"]},
            tags=[r["repo"].split("/")[1]])
        if taken == ENG1_ROWS:
            break
    assert taken == ENG1_ROWS, taken


# ------------------------------------------------------------------------------------------------ ENG-2 / ENG-5
PREFIX_RE = re.compile(r"^(fix|feat|docs|refactor|test)(\([^)\n]{1,40}\))?!?:\s")
ENG2_OPTIONS = {"fix": "A bug fix: corrects behaviour that was wrong.",
                "feat": "A feature: adds or extends functionality.",
                "docs": "Documentation only: comments, doc files or doc strings.",
                "refactor": "A restructuring that neither fixes a bug nor adds a feature.",
                "test": "Adds or changes tests only."}
ENG2_PER_LABEL = 6
ENG2_DIFF_RANGE = (300, 4000)
# Rows passed over after reading the diff: the developer's prefix is not the only natural reading of the change.
# Keys are the first 12 characters of the commit hash.
ENG2_SKIP = {
    "381f9411de12": "labelled fix; the change wires a new user setting (tabWidth) into the layout, which reads as feat",
    "f9ead9582e75": "labelled fix; the only change is a return-type annotation, which reads as refactor as much as fix",
    "52f54b274756": "labelled fix; the file is a spec template, so test is an equally natural reading",
    "283415beab7e": "labelled fix; the change adds the http module to the bundle, which reads as feat",
    "918c679d941d": "labelled feat; the file is an example program, so docs is an equally natural reading",
    "2b16f9817548": "labelled feat; the change reworded lint messages and raised a severity, fix or refactor read as well",
    "cff8835e2eaa": "labelled feat; the change restructures benchmarks, which reads as refactor or test",
    "c0effc11163e": "labelled docs; the change alters props in a documentation site's page wrapper, fix or feat read as well",
    "1d43f2140d89": "labelled refactor; changing a type from unknown to any is as naturally a fix",
    "092a51640436": "labelled refactor; the file is a test, so test is an equally natural reading",
    "547a1fe10ffd": "labelled refactor; the change introduces lazy loading of routes, which reads as feat",
    "fe830a3d4823": "labelled fix; the file is a spec, so test is an equally natural reading",
    "cdf0bce0d23d": "labelled fix; the change swaps one type import for another in a .d.ts file, refactor reads as well",
    "5660399d1daa": "labelled feat; making display depend on isColumn reads as a fix",
    "a247a4bc9eb3": "labelled docs; the change wires a module into a demo app, fix or feat read as well",
    "c9547da2ec51": "the same commit as the 18F/cli row, reached through a fork (cloudfoundry/cli)",
    "55f3cf131146": "labelled feat; returning null instead of throwing reads as a fix or a refactor as well",
    "50000c5c0a8f": "labelled refactor; adding providers to an Angular module reads as a fix or feat as well",
    "18aae5d407a8": "labelled refactor; removing the Escape-key handler changes behaviour, fix reads as well",
}
ENG5_ROWS = 30
ENG5_DIFF_RANGE = (300, 5000)
ENG5_MSG_RANGE = (20, 120)
# Rows passed over after reading the diff against its four messages (keys: first 12 characters of the commit hash).
ENG5_SKIP = {
    "0bd78503b9d9": "the diff adds a useHover hook; two candidate messages carry the same [field] scope and neither "
                    "names the hook, so the change-list message is not uniquely defensible",
    "4e705c79fcd3": "a distractor, 'Add some tests forr good measure', describes a new test file as well as the real "
                    "message does",
}
STOP = set("""about above after again added adding against all also among around because been before being below between
both changed changes check could does doing down during each error errors every fields first fixed fixes fixing from
function functions further handle having here inside instead into just like make makes making method methods more most
name names never only other over remove removed removes return returns same should since some still such support
than that their them then there these they this those through under until update updated updates upon using value
values very were what when where which while will with within without would""".split())


def _udiff(r):
    a = r["old_contents"].splitlines(keepends=True)
    b = r["new_contents"].splitlines(keepends=True)
    return "".join(difflib.unified_diff(a, b, fromfile="a/" + r["old_file"], tofile="b/" + r["new_file"], n=3))


def _cpft_records():
    records = []
    for lang in CPFT_LANGS:
        with (SOURCE_DIR / f"commitpackft/{lang}.jsonl").open(encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                r["repo"] = r["repos"].split(",")[0]
                r["key"] = f"{r['commit']}/{r['new_file']}"
                r["first_line"] = r["message"].strip().splitlines()[0].strip() if r["message"].strip() else ""
                records.append(r)
    return records


def _cpft_source(r, record_kind):
    return {"dataset_id": "commitpackft", "dataset": "CommitPackFT", "license": "MIT",
            "url": f"https://github.com/{r['repo']}/commit/{r['commit']}", "citation": CPFT_CITATION,
            "record_id": f"commit {r['commit']} · {r['new_file']} ({r['lang']})",
            "original_label": record_kind,
            "labelled_by": "the developer who wrote the commit",
            "repo": f"https://github.com/{r['repo']}", "repo_license": CPFT_PERMISSIVE[r["license"]]}


def _words(text):
    return {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9_]{4,}", text) if w.lower() not in STOP}


def _eng2(records):
    labelled = []
    for r in records:
        m = PREFIX_RE.match(r["message"].lstrip())
        if not m or r["license"] not in CPFT_PERMISSIVE:
            continue
        if any(re.search(rf"\b{w}\b", r["repo"].lower()) for w in ENG2_OPTIONS):
            continue
        diff = _udiff(r)
        if not ENG2_DIFF_RANGE[0] <= len(diff) <= ENG2_DIFF_RANGE[1]:
            continue
        labelled.append((r, m.group(1), diff))
    labelled.sort(key=lambda x: rank(f"eng-2/{x[0]['key']}"))
    per_label = collections.Counter()
    used_repos = set()
    for r, label, diff in labelled:
        if per_label[label] >= ENG2_PER_LABEL or r["repo"].lower() in used_repos or r["commit"][:12] in ENG2_SKIP:
            continue
        per_label[label] += 1
        used_repos.add(r["repo"].lower())
        title = f"Commit {r['commit'][:10]} to {r['repo']} · {r['lang']} file"
        _no_words(title, ENG2_OPTIONS, f"ENG-2 {r['key']}")
        row("ENG-2", f"{r['commit'][:12]}", title=title, gold=label,
            state={"repository": f"github.com/{r['repo']}", "file": r["new_file"], "diff": diff},
            rationale=f"The developer's own message starts with the prefix \"{r['first_line'].split(':', 1)[0]}:\"; "
                      f"the diff to {os.path.basename(r['new_file'])} is the whole change.",
            source=_cpft_source(r, f"message prefix {label!r}"),
            tags=[r["lang"], label])
    assert all(per_label[k] == ENG2_PER_LABEL for k in ENG2_OPTIONS), per_label
    return used_repos


def _eng5(records):
    by_repo = collections.defaultdict(list)
    for r in records:
        if r["license"] not in CPFT_PERMISSIVE:
            continue
        fl = r["first_line"]
        if not ENG5_MSG_RANGE[0] <= len(fl) <= ENG5_MSG_RANGE[1] or re.search(r"https?://|#\d", fl):
            continue
        by_repo[r["repo"].lower()].append(r)
    candidates = []
    for repo, rs in by_repo.items():
        messages = {}
        for r in rs:
            messages.setdefault(r["first_line"], r["commit"])
        distinct = {fl: c for fl, c in messages.items() if len({r["commit"] for r in rs if r["first_line"] == fl}) == 1}
        if len(distinct) < 4:
            continue
        for r in rs:
            if r["first_line"] not in distinct:
                continue
            diff = _udiff(r)
            if not ENG5_DIFF_RANGE[0] <= len(diff) <= ENG5_DIFF_RANGE[1]:
                continue
            diff_words = _words(diff)
            gold_words = _words(r["first_line"])
            if not gold_words & diff_words:
                continue
            others = []
            for fl, c in distinct.items():
                if c == r["commit"] or fl == r["first_line"]:
                    continue
                ws = _words(fl)
                if ws and ws - diff_words - gold_words:
                    others.append((abs(len(fl) - len(r["first_line"])), fl, c))
            if len(others) < 3:
                continue
            others.sort()
            candidates.append((r, diff, [(fl, c) for _, fl, c in others[:3]]))
    candidates.sort(key=lambda x: rank(f"eng-5/{x[0]['key']}"))
    used_repos = set()
    taken = 0
    for r, diff, others in candidates:
        if r["repo"].lower() in used_repos or r["commit"][:12] in ENG5_SKIP:
            continue
        used_repos.add(r["repo"].lower())
        taken += 1
        options = {r["commit"][:8]: r["first_line"], **{c[:8]: fl for fl, c in others}}
        options = {k: options[k] for k in sorted(options)}
        assert len(options) == 4, r["key"]
        title = f"Commit to {r['repo']} · {os.path.basename(r['new_file'])}"
        row("ENG-5", f"{r['commit'][:12]}", title=title, gold=r["commit"][:8], options=options,
            state={"repository": f"github.com/{r['repo']}", "file": r["new_file"], "diff": diff,
                   "candidate_messages": options},
            rationale=f"The commit's own message is \"{r['first_line']}\"; the other three messages belong to other "
                      f"commits in {r['repo']} and describe changes this diff does not make.",
            source=_cpft_source(r, f"message: {r['first_line']}"),
            tags=[r["lang"]])
        if taken == ENG5_ROWS:
            break
    assert taken == ENG5_ROWS, taken


# ------------------------------------------------------------------------------------------------ ENG-3
CWE_GROUPS = {
    "injection": {"CWE-79": "Cross-site Scripting", "CWE-89": "SQL Injection", "CWE-77": "Command Injection",
                  "CWE-78": "OS Command Injection"},
    "memory_safety": {"CWE-787": "Out-of-bounds Write", "CWE-125": "Out-of-bounds Read", "CWE-416": "Use After Free",
                      "CWE-120": "Classic Buffer Overflow"},
    "broken_auth": {"CWE-287": "Improper Authentication", "CWE-862": "Missing Authorization",
                    "CWE-863": "Incorrect Authorization", "CWE-306": "Missing Authentication for Critical Function"},
    "path_traversal": {"CWE-22": "Path Traversal"},
    "csrf": {"CWE-352": "Cross-Site Request Forgery"},
    "info_exposure": {"CWE-200": "Exposure of Sensitive Information", "CWE-532": "Insertion of Sensitive Information "
                                                                                "into Log File"},
}
ENG3_OPTIONS = {
    "injection": "Untrusted input is interpreted as code or markup: XSS, SQL, shell or command injection.",
    "memory_safety": "Memory is read or written outside its bounds or after it is freed: overflows, out-of-bounds "
                     "access, use-after-free.",
    "broken_auth": "Authentication or authorization is missing or wrong: a check that is absent, bypassable or "
                   "applied to the wrong subject.",
    "path_traversal": "A supplied path escapes the intended directory to reach other files.",
    "csrf": "A victim's browser is made to send a state-changing request the victim did not intend.",
    "info_exposure": "Sensitive information is revealed to someone not meant to see it, including through logs.",
}
ENG3_LITERAL = {
    "injection": r"inject|xss|cross[- ]site script",
    "memory_safety": r"buffer|overflow|out[- ]of[- ]bounds|use[- ]after[- ]free|\buaf\b|memory|heap|stack",
    "broken_auth": r"authenticat|authoriz|access control|permission check|privilege",
    "path_traversal": r"travers|\.\./|directory",
    "csrf": r"csrf|cross[- ]site request|forgery",
    "info_exposure": r"disclos|exposure|leak|sensitive|information",
}
ENG3_PER_CLASS = 5
ENG3_NONLITERAL = 4
ENG3_PER_CNA = 2
ENG3_DESC_RANGE = (80, 1200)
# Vendor template descriptions that name no weakness ("In X, there is a possible missing params check. This could
# lead to local denial of service"); they are dropped by rule rather than one by one.
ENG3_TEMPLATE_RE = re.compile(r"there is a possible missing \w+ check", re.I)
# Records passed over after reading the description: NVD's CWE is not decidable from the text, or a second class
# is equally defensible from it.
ENG3_SKIP = {
    "CVE-2023-42362": "an arbitrary file upload that 'executes commands and obtains sensitive information'; NVD says "
                      "CWE-79, but injection and information exposure both read from the text",
    "CVE-2023-2196": "'a missing permission check' lets users test file paths; NVD says CWE-22, but broken "
                     "authorization is equally defensible",
    "CVE-2023-2680": "an incomplete fix for another CVE; the weakness is not described",
    "CVE-2023-27903": "a temporary file created with default permissions; NVD says CWE-863, but the text describes an "
                      "insecure temporary file, not an authorization check",
    "CVE-2023-2631": "'a missing permission check' lets users connect to a URL; NVD says CWE-352, but broken "
                     "authorization is equally defensible",
    "CVE-2023-37960": "sending 'emails with arbitrary files from the controller file system'; NVD says CWE-22, but "
                      "information exposure is equally defensible",
    "CVE-2023-36659": "'long inputs were not properly processed' causing loss of communication; the text does not "
                      "establish memory corruption",
    "CVE-2023-32981": "crafted archives create or replace arbitrary files; NVD says CWE-787, but the text describes "
                      "path traversal",
    "CVE-2023-3649": "'iSCSI dissector crash' via a crafted capture; the text does not say what kind of crash",
    "CVE-2022-46449": "'a Denial of Service via a crafted input'; nothing in the text points at memory",
    "CVE-2021-31239": "'a denial of service via the appendvfs.c function'; nothing in the text points at memory",
    "CVE-2023-3596": "'a denial of service ... through maliciously crafted CIP messages'; nothing in the text points "
                     "at memory",
    "CVE-2023-3595": "'remote code execution ... through maliciously crafted CIP messages'; injection is as "
                     "defensible as memory corruption from the text",
}


def _nvd_records():
    records = []
    for a, b in NVD_WINDOWS:
        page = json.loads((SOURCE_DIR / f"nvd/{a}_{b}.json").read_text(encoding="utf-8"))
        assert page["totalResults"] == len(page["vulnerabilities"]) <= 2000, (a, b)
        records += [v["cve"] for v in page["vulnerabilities"]]
    assert len({c["id"] for c in records}) == len(records)
    return records


def _eng3():
    by_class = collections.defaultdict(list)
    for c in _nvd_records():
        primary = [w for w in c.get("weaknesses", []) if w["source"] == "nvd@nist.gov" and w["type"] == "Primary"]
        ids = {d["value"] for w in primary for d in w["description"]}
        if len(ids) != 1:
            continue
        cwe = ids.pop()
        classes = [k for k, g in CWE_GROUPS.items() if cwe in g]
        if len(classes) != 1:
            continue
        desc = next((d["value"] for d in c["descriptions"] if d["lang"] == "en"), "").strip()
        desc = re.sub(r"[ \t\xa0]+", " ", desc)
        if not ENG3_DESC_RANGE[0] <= len(desc) <= ENG3_DESC_RANGE[1]:
            continue
        if re.search(r"\*\* (DISPUTED|REJECT|UNSUPPORTED)", desc) or c.get("vulnStatus") == "Rejected":
            continue
        if len(desc.split()) < 12:            # bare "<Product> <Title> Vulnerability" lines carry no evidence
            continue
        if ENG3_TEMPLATE_RE.search(desc):
            continue
        by_class[classes[0]].append((c, cwe, desc, bool(re.search(ENG3_LITERAL[classes[0]], desc, re.I))))
    for klass, items in by_class.items():
        items.sort(key=lambda x: rank(f"eng-3/{x[0]['id']}"))
        taken = {False: 0, True: 0}
        per_cna = collections.Counter()
        chosen = []
        for c, cwe, desc, literal in items:          # first the descriptions that do not name the class
            if literal or taken[False] >= ENG3_NONLITERAL or c["id"] in ENG3_SKIP \
                    or per_cna[c["sourceIdentifier"]] >= ENG3_PER_CNA:
                continue
            taken[False] += 1
            per_cna[c["sourceIdentifier"]] += 1
            chosen.append((c, cwe, desc, literal))
        for c, cwe, desc, literal in items:          # then the ones that do, to fill the class quota
            if not literal or sum(taken.values()) >= ENG3_PER_CLASS or c["id"] in ENG3_SKIP \
                    or per_cna[c["sourceIdentifier"]] >= ENG3_PER_CNA:
                continue
            taken[True] += 1
            per_cna[c["sourceIdentifier"]] += 1
            chosen.append((c, cwe, desc, literal))
        chosen.sort(key=lambda x: rank(f"eng-3/{x[0]['id']}"))
        for c, cwe, desc, literal in chosen:
            row("ENG-3", c["id"].lower(), title=f"CVE record · {c['id']}", gold=klass,
                state={"cve_id": c["id"], "published": c["published"][:10], "description": desc},
                rationale=f"NVD's analysts assigned {cwe} ({CWE_GROUPS[klass][cwe]}), which belongs to the "
                          f"{klass.replace('_', ' ')} class.",
                source={"dataset_id": "nvd", "dataset": "NVD (National Vulnerability Database)",
                        "license": "Public domain (NIST); description text under the CVE Terms of Use",
                        "url": f"https://nvd.nist.gov/vuln/detail/{c['id']}", "citation": NVD_CITATION,
                        "record_id": c["id"], "original_label": f"{cwe} (nvd@nist.gov, Primary)",
                        "labelled_by": "NVD analysts", "reporting_cna": c["sourceIdentifier"],
                        "notice": "CVE is Copyright (c) 1999-2026 The MITRE Corporation, used under the CVE Terms "
                                  "of Use (SPDX cve-tou). This product uses the NVD API but is not endorsed or "
                                  "certified by the NVD."},
                tags=[cwe.lower(), "names-the-class" if literal else "does-not-name-the-class"])
        assert sum(taken.values()) == ENG3_PER_CLASS, (klass, taken)
    assert set(by_class) == set(ENG3_OPTIONS), set(by_class)


# ------------------------------------------------------------------------------------------------ ENG-4
CRED_LABELS = {"T": "real_credential", "X": "placeholder_or_test", "F": "not_a_secret"}
CRED_OPTIONS = {"real_credential": "Looks like a real, usable credential hard-coded in code or config.",
                "placeholder_or_test": "A placeholder, an example or a value only used in tests.",
                "not_a_secret": "Not a credential at all, e.g. a variable, function call, type, message or setting."}

# Lines that passed the written rules but that a careful reader could not defend as labelled (v3 list, then v4).
CRED_EXCLUDED = {
    1494346: "a NATS user nkey (starts with U), which is a public key, in a server test config",
    32721: "an Algolia DocSearch key, which is a search-only key published for website search",
    41430: "a seeded user password in OWASP Juice Shop, a deliberately insecure training app",
    37415: "an AWS key pair; publishing it safely needs AWS's documented example values, which read as placeholders",
    136872: "a Firebase database URL, which is not a secret",
    35042: "a session token in a fake transport used to simulate server faults in tests",
    # v4 walk (in walk order)
    1479566: "MySQL passwords in a backup script whose users and databases are named test1 and test2; a test "
             "reading is arguable",
    136873: "a Firebase database URL, which is not a secret (same reason as 136872)",
    37733: "an OAuth token secret inside a docstring example; labelled T, but it is plainly illustrative",
    36400: "WordPress keys under a comment that says 'random sha1 strings - change all these lines'",
    34293: "an Imgur client id, which is a public identifier",
    11536787: "an encryption key in a .env used to start local acceptance-test containers; test reading arguable",
    31727: "a MySQL root password for a throwaway docker container started by a Makefile; test reading arguable",
    34359: "a Redshift password whose host name says 'sql-connector-test'; test reading arguable",
    1494641: "an AES key in a padding-oracle teaching example; test reading arguable",
    41544: "canal's documented default admin password hash shipped in the sample properties file",
    32571: "a database password for a localhost root account in a tutorial repository; test reading arguable",
    1495370: "an 8-byte Kubernetes storage-version hash; calling it a non-secret needs Kubernetes internals",
}

CRED_REASONS = {
    1494695: "A RabbitMQ password is hard-coded in the application's console config.",
    34244: "A Coveralls repository token is committed in the project's CI config.",
    42432: "A GitHub API token is committed in the CI workflow, split into two halves.",
    32268: "Devise's secret key, used to sign tokens, is hard-coded in the initializer.",
    34770: "A long random session-signing secret is hard-coded in a config file.",
    29500: "A fixed AES encryption key is hard-coded in the class that decrypts stored database passwords.",
    1493488: "A fixed Shiro remember-me cipher key is hard-coded in the Java configuration.",
    11536976: "A JWT signing secret is hard-coded as the default in the Helm chart's values file.",
    31185: "The value is a “<your key>” placeholder in documentation.",
    33539: "“admin” is the password of a throwaway database in a CI test workflow.",
    29475: "MY_OAUTH_TOKEN is a placeholder in the README's example code.",
    110520: "“foo2” is a dummy value in documentation that shows the config file format.",
    23505: "“my_secret” is a dummy option value inside a test spec.",
    35067: "The password is a fixed value in a test configuration file.",
    32498: "“pass” is a dummy credential in a test spec.",
    61652: "“test” is the default password in the sample docker-compose file generated for new projects.",
    11526114: "The flagged text is the name of a test key pair, not key material.",
    11528189: "RSA_2048 names a key type; it is a setting, not a secret.",
    11532785: "The flagged word is part of an error message in generated code.",
    11527047: "typing.Any is the type annotation of a method parameter.",
    11529947: "The value is a translation placeholder that refers to another label.",
    11531540: "o.AuthURL reads a URL from configuration; no secret is written here.",
    27607: "“secret” is the name of a database column.",
    37179: "“Invalid Password” is an error message in a test.",
    # v4 additions
    35449: "A Sauce Labs access key for the project's CI account is committed in the Travis config.",
    36090: "A CI registry password is committed in the CircleCI config, split in two with a comment saying it "
           "is split so GitHub will not revoke it.",
    31283: "“my_password” sits beside “my_username” and “my_database_name” in a CLI template that users fill in.",
    29440: "“eyJaccess” is a stub token in a recorded HTTP cassette used by the test suite.",
    11527808: "The value is a reference to a CI secret by name (from_secret), not the secret itself.",
    11528562: "c.Redis.Password reads the password from a configuration struct; nothing is hard-coded.",
}


def _eng4():
    for e in _CRED["excerpts"]:
        assert e["code_license"] in PERMISSIVE_REPO, f"ENG-4 {e['id']}: {e['repo']} is {e['code_license']}"
        assert e["id"] not in CRED_EXCLUDED
        assert CRED_LABELS[e["original_label"].split()[1].rstrip(",")] == e["label"], f"ENG-4 {e['id']}: label"
        row("ENG-4", f"creddata-{e['id']}", title=e["title"], state=e["state"], gold=e["label"],
            rationale=CRED_REASONS[e["id"]], note=e["note"], tags=e["tags"],
            source={"dataset_id": "creddata", "dataset": "Samsung CredData",
                    "license": "Apache-2.0 (labels and metadata); the code excerpt keeps its repository's licence, "
                               f"{e['code_license']}",
                    "url": f"{CRED_REPO}/blob/{CRED_COMMIT}/meta/{e['meta']}.csv", "citation": CRED_CITATION,
                    "record_id": f"CredData Id {e['id']} (meta/{e['meta']}.csv)",
                    "original_label": e["original_label"],
                    "labelled_by": "CredData's reviewers, who manually checked every scanner hit against written "
                                   "ground rules",
                    "code_repo": f"https://github.com/{e['repo']}", "code_license": e["code_license"],
                    "code_license_file": e["license_file"]})


# ------------------------------------------------------------------------------------------------ define
def define():
    _datasets()
    task("ENG-1", category=CATEGORY, name="Which file must change?",
         ask="Which file did the fix for this issue change?",
         instruction="A GitHub issue from an open-source Python project and several file paths from that project at "
                     "the issue's base commit. Exactly one of the paths is the file that the merged fix changed. "
                     "Choose it from the issue text alone.",
         options={}, per_row_options=True, shape="locate", input_type="GitHub issue", modality="text",
         expertise="practitioner", contamination="high", label_origin="objective record")
    task("ENG-2", category=CATEGORY, name="What kind of change is this?",
         ask="What kind of change does this diff make?",
         instruction="A unified diff of one file from a real commit. The developer labelled the commit with a "
                     "Conventional Commit prefix. Decide which prefix they used, from the diff alone: fix for a bug "
                     "fix, feat for new functionality, docs for documentation-only changes, refactor for a "
                     "restructuring that changes neither behaviour nor features, test for test-only changes.",
         options=ENG2_OPTIONS, shape="classify", input_type="code diff", modality="text",
         expertise="practitioner", contamination="medium", label_origin="self-declared")
    task("ENG-3", category=CATEGORY, name="Which weakness class is this?",
         ask="Which weakness class does this CVE describe?",
         instruction="The description of a CVE record. Decide which class of weakness (CWE family) the "
                     "vulnerability is, from the description alone.",
         options=ENG3_OPTIONS, shape="classify", input_type="CVE description", modality="text",
         expertise="practitioner", contamination="high", label_origin="trained annotators")
    task("ENG-4", category=CATEGORY, name="Live secret or placeholder?",
         ask="Is this a real secret committed in code?",
         instruction=("A secret scanner flagged a value (flagged_value) on one line of a file from a public GitHub "
                      "repository; the flagged line is marked with > among its neighbouring lines. Decide what the "
                      "flagged value is. Credential-shaped values in the excerpt may have been replaced by random "
                      "stand-ins of the same shape, so judge by the code and its context, not by testing the value."),
         options=CRED_OPTIONS, shape="classify", input_type="code excerpt", modality="text",
         expertise="practitioner", contamination="medium", label_origin="human experts")
    task("ENG-5", category=CATEGORY, name="Which message describes this diff?",
         ask="Which commit message belongs to this diff?",
         instruction="A unified diff of one file from a real commit, and the first lines of four commit messages "
                     "from the same repository. One is the message the developer wrote for this commit; the other "
                     "three belong to other commits. Choose the message that describes this diff.",
         options={}, per_row_options=True, shape="locate", input_type="code diff", modality="text",
         expertise="practitioner", contamination="medium", label_origin="objective record")
    _eng1()
    records = _cpft_records()
    _eng2(records)
    _eng3()
    _eng4()
    _eng5(records)
