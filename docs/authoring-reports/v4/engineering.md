# Engineering module report (Decision Bench v4)

Module: `authoring/bench/engineering.py` (+ `authoring/bench/engineering_creddata.json`). Both
`python3 scripts/fetch_sources.py --only engineering` and `python3 scripts/build_bench.py --dry-run --only engineering`
pass; the build ends with `"problems": []`. 150 rows, five tasks, 30 rows each. No images. Nothing under
`data/sources/manifest.json`, `scripts/`, `__init__.py` or other modules was touched; `--pin` was not run.

## Tasks built

| Task | Name | Rows | Balance | Label origin | Source |
| --- | --- | --- | --- | --- | --- |
| ENG-1 | Which file must change? | 30 | per-row options (5 paths each), every gold distinct; repos: django 8, sympy 8, sphinx 8, astropy 3, scikit-learn 3 | objective record | SWE-bench Verified |
| ENG-2 | What kind of change is this? | 30 | fix 6, feat 6, docs 6, refactor 6, test 6 | self-declared | CommitPackFT (Rust, Go, TypeScript) |
| ENG-3 | Which weakness class is this? | 30 | 5 per class (injection, memory_safety, broken_auth, path_traversal, csrf, info_exposure); 19 descriptions do not name the class, 11 do | trained annotators (NVD analysts) | NVD CVE API 2.0 |
| ENG-4 | Live secret or placeholder? | 30 | real_credential 10, placeholder_or_test 10, not_a_secret 10 | human experts (CredData reviewers) | Samsung CredData |
| ENG-5 | Which message describes this diff? | 30 | per-row options (4 messages), every gold distinct; TypeScript 18, Rust 8, Go 4 | objective record | CommitPackFT |

State sizes (JSON chars): ENG-1 median 1,604 / max 4,102; ENG-2 640 / 2,342; ENG-3 270 / 630; ENG-4 316 / 606;
ENG-5 1,373 / 2,691. Every sampling rule is written in the module docstring; hand skips are in `ENG1_SKIP` (1),
`ENG2_SKIP` (19), `ENG3_SKIP` (12), `ENG5_SKIP` (2) and `CRED_EXCLUDED` (6 from v3 + 12 new), each with a reason.

## Source change the maintainer must know about

**CommitBench is CC BY-NC 4.0, so ENG-2 and ENG-5 do not use it.** The card
(https://huggingface.co/datasets/Maxscha/commitbench, README at revision 1500792c) says "Dataset under the CC BY-NC 4.0
license, code under the MIT license". NC fails the policy. I replaced it with **CommitPackFT** (bigcode/commitpackft,
MIT), keeping ENG-2's label (the developer's own Conventional Commit prefix) and ENG-5's shape. CommitPackFT stores
whole before/after files rather than diffs, so each row's diff is computed with `difflib.unified_diff` (3 lines of
context) from the sample's `old_contents`/`new_contents`; that is a faithful rendering of the real change, not new
text. I also looked at CommitChronicle (JetBrains-Research/commit-chronicle): its content is from permissive repos with
a per-row licence, but the dataset's own card says `license: other` with no grant, so it fails the "dataset's own
licence" half of the policy and was not used. Three third-party "conventional commits" datasets on Hugging Face carry
no licence at all.

## Licence evidence, per dataset (what I actually read)

**SWE-bench Verified (ENG-1).**
- Hugging Face card, `princeton-nlp/SWE-bench_Verified` README at revision `c104f840cc67f8b6eec6f759ebc8b2693d585d4a`
  (also the redirected `SWE-bench/SWE-bench_Verified`, revision 78f471bf): **no licence field** in the YAML and no
  licence prose. The parent `princeton-nlp/SWE-bench` card likewise has none.
- SWE-bench project LICENSE (https://raw.githubusercontent.com/SWE-bench/SWE-bench/main/LICENSE): MIT, "Copyright (c)
  2023 Carlos E Jimenez, John Yang, ...". This is what I recorded as the dataset licence (fetched as
  `swe-bench-verified/LICENSE`).
- Repository licences via the GitHub API `license` field, plus the licence files for the two GitHub reports as
  "Other": django BSD-3-Clause, scikit-learn BSD-3-Clause, astropy BSD-3-Clause, seaborn BSD-3-Clause, flask
  BSD-3-Clause, xarray Apache-2.0, requests Apache-2.0, pytest MIT, sympy BSD-3-Clause (LICENSE text read:
  three-clause BSD, "Copyright (c) 2006-2023 SymPy Development Team"), sphinx BSD-2-Clause (LICENSE.rst: "two clause
  BSD licence"). **Excluded:** pylint (GPL-2.0) and matplotlib (its own PSF-style "License agreement for matplotlib
  versions 1.3.0 and later", not on the PERMISSIVE list). The per-row repo licence is in `source.repo_license`.
- Judgement call for review: the issue text is user-generated GitHub content. GitHub's terms let others view and fork
  it on GitHub; off-platform redistribution rests on the SWE-bench authors' MIT release of the instances, which the
  whole field relies on but which the Verified card itself does not restate. I built the task as instructed and
  restricted to permissive projects; if the maintainer wants a stricter reading, ENG-1 is the task to drop.
  `content_license` is recorded as BSD-3-Clause (the majority licence) with the per-repo detail in `content_terms`.

**CommitPackFT (ENG-2, ENG-5).**
- Card at revision `fc56fe33c030c6daa414c2b112c932b8eed085e6` (https://huggingface.co/datasets/bigcode/commitpackft):
  YAML `license: mit`; Licensing Information section: "Each sample comes from a code repository with a permissive
  license. The license is provided by the `license` field for each sample." Fetched as `commitpackft/README.md`.
- Per-sample `license` values kept: mit, apache-2.0, bsd-3-clause, bsd-2-clause, isc, cc0-1.0, unlicense (recorded in
  `source.repo_license`); skipped: mpl-2.0, epl-1.0, lgpl-2.1, agpl-3.0, artistic-2.0, unknown. Rows used: MIT 38,
  Apache-2.0 18, BSD-2-Clause 2, BSD-3-Clause 1, CC0-1.0 1.
- Files fetched: `data/rust/data.jsonl` (7.4 MB), `data/go/data.jsonl` (12.4 MB), `data/typescript/data.jsonl`
  (14.6 MB) at the pinned revision. The Hugging Face rows/filter API does not serve this dataset (no viewer), so whole
  language files are the smallest unit; Python/JavaScript/Ruby files are 130–200 MB and were not used.

**NVD (ENG-3).**
- NIST copyright and licensing statements
  (https://www.nist.gov/open/copyright-fair-use-and-licensing-statements-srd-data-software-and-technical-series-publications),
  read: "Data/works created by NIST employees that are not covered by the Standard Reference Data Act are subject to
  17 U.S.C. §105 and generally are not subject to copyright protection within the United States", with a request to
  acknowledge NIST as the source. Recorded as `license_url`.
- NVD FAQ (https://nvd.nist.gov/general/faq) and developer terms (https://nvd.nist.gov/developers/terms-of-use) are
  JavaScript-rendered and could not be fetched directly; web search returned their text: "There are no fees,
  licensing restrictions, or even a requirement to register", "All NIST publications are available in the public
  domain according to Title 17 of the United States Code", and the requested notice "This product uses the NVD API
  but is not endorsed or certified by the NVD" (rate limit: 5 requests per rolling 30 s without a key). The notice is
  carried in every row's `source.notice`.
- The **description text is CVE Record information**, not a NIST work. CVE Program Terms of Use (SPDX id `cve-tou`,
  text read at https://spdx.org/licenses/cve-tou.html; live page https://www.cve.org/Legal/TermsOfUse is a
  JavaScript app): "MITRE hereby grants you a perpetual, worldwide, non-exclusive, no-charge, royalty-free,
  irrevocable copyright license to reproduce, prepare derivative works of, publicly display, publicly perform,
  sublicense, and distribute Common Vulnerabilities and Exposures (CVE)", provided "you reproduce MITRE's copyright
  designation and this license in any such copy". Rows carry that designation in `source.notice`.
- **Judgement call for review:** `cve-tou` is a permissive, attribution-style licence but is not in `PERMISSIVE`
  (which I may not edit). `content_license` is therefore recorded as "Public domain" (accurate for the NVD label and
  record; the nearest listed value for the description text), and `content_terms` spells out the real position.
  Adding `cve-tou` to `PERMISSIVE` and switching `content_license` to it would be the clean fix.
- Fetch: five 9-day publication windows of 2023 (949, 729, 1,148, 1,051 and 1,292 CVEs; 3–5.5 MB each, 22 MB
  total), each under the 2,000-per-page limit; five requests fit the public rate limit, and `fetch_sources.py`
  succeeded with its default 8 parallel jobs. Note for pinning: NVD records are re-analysed and descriptions edited
  over time, so these API responses will not stay byte-identical; a hash pin may fail later through no fault of the
  rows. Only CWE entries with `source == nvd@nist.gov` and `type == Primary` are used, so every label is NVD's own.

**Samsung CredData (ENG-4).**
- LICENSE at commit `c09c0c52fc6dae4ae5438ae69ba486f9f8059f0d`: Apache-2.0 (fetched, `creddata/LICENSE`). README at the
  same commit, "License" section: "Each file is under the existing project's license." Meta CSVs for every row's
  repository are fetched (`creddata/meta/<id>.csv`, 30 files).
- Each excerpt's repository licence was read from the GitHub API `license` field at the pinned repository commit
  and recorded per row (`source.code_license`, `source.code_license_file`): MIT 17, Apache-2.0 9, BSD-3-Clause 4 (v3
  rows kept their v3 values; the new rows are angular/protractor MIT, grpc-ecosystem/grpc-gateway BSD-3-Clause,
  backup/backup MIT, timdorr/tesla-api MIT, appleboy/gorush MIT, brocaar/chirpstack-network-server MIT).

## What was dropped, and why

- **CommitBench** (ENG-2/ENG-5 source as specified): CC BY-NC 4.0. Replaced, see above.
- **CommitChronicle** (candidate replacement): dataset licence "other". Not used.
- **pylint** and **matplotlib** instances of SWE-bench Verified: GPL-2.0 and a non-listed licence.
- **ENG-1 by rule:** instances whose gold patch touches more than one file or a test file, issues outside 150–8,000
  characters, and instances with fewer than four real distractor paths from other directories; xarray, pytest,
  requests, seaborn and flask never reach the sample for that last reason. Hand skip: sympy-18211 (as_set/solveset
  issue; `sympy/sets/sets.py` is a defensible second answer).
- **ENG-2 hand skips (19):** diffs where the developer's prefix is not the only natural reading, e.g. a "fix" that
  wires a new setting in (feat), a "refactor" that removes a key handler (fix), "fix"/"refactor" commits whose file
  is a spec (test), a "feat" that changes an example (docs), and one commit reached twice through a fork
  (cloudfoundry/cli duplicate of 18F/cli). Self-declared prefixes are noisy; the walk needed 49 candidates to seat 30.
  The maintainer may prefer to treat ENG-2 as the noisiest task in the category.
- **ENG-3 by rule:** records without an NVD Primary CWE, with more than one CWE, CWEs outside the six groups,
  rejected/disputed records, descriptions under 12 words (bare "Product Title Vulnerability" lines from Microsoft), and
  the Unisoc template "there is a possible missing params check. This could lead to local denial of service" (a regex
  rule, `ENG3_TEMPLATE_RE`). **Hand skips (12):** descriptions where NVD's CWE cannot be read from the text (an
  "incomplete fix for another CVE", "DoS via a crafted input", "dissector crash", "long inputs not properly
  processed", "RCE via crafted CIP messages") or where a second class is equally defensible ("missing permission check"
  records that NVD filed as CWE-22 or CWE-352, an arbitrary file upload filed as XSS, a temp-file-permissions bug filed
  as CWE-863, a crafted-archive arbitrary file write filed as CWE-787). Non-literal memory-safety candidates ran out, so
  that class is 2 non-literal + 3 literal instead of 4 + 1; the others are 4 + 1 (CSRF had only 3 non-literal in the
  windows: 3 + 2).
- **ENG-4:** six real-credential candidates dropped in v3 stay dropped; the v4 walk dropped 12 more (all listed in
  `CRED_EXCLUDED`): Firebase URL and Imgur client id (public identifiers), a docstring example labelled real, WordPress
  keys under a "change all these lines" comment, credentials for local test/dev containers or tutorial repos (test
  reading arguable), canal's documented default password hash, a personal e-mail account's SMTP password (privacy), and
  one not_a_secret line that needs Kubernetes internals to judge (a storage-version hash table).
- **ENG-5 hand skips (2):** a new hook file whose repository had two messages with the same "[field]" scope, and a
  distractor ("Add some tests forr good measure") that describes a new test file as well as the real message does.

## Other judgement calls for the maintainer

1. **Secrets.** The six new ENG-4 excerpts had their credential-shaped values replaced by deterministic same-shape
   fakes (same length, same upper/lower/digit classes) before being written to `engineering_creddata.json`; the
   neighbouring `BROWSER_STACK_ACCESS_KEY` and `password0` values were faked too. Original values, paths, commits and
   line numbers are recorded nowhere in the repository (same pointer rule as v3). The candidate walk left plaintext
   values in my scratchpad only (`scratchpad/probe/cred_candidates*.json`, `cred_cache/`); those files are outside the
   repo and can be deleted.
2. **ENG-1 distractors** come from other Verified instances' gold patches in the same repository, so they are real
   paths but not guaranteed to exist at the instance's exact base commit (the brief allowed "from other commits").
   Distractors are from different directories than the answer and each other, with distinct base names, and are not
   mentioned in the issue. This makes the task decidable but easier than a same-directory design would be.
3. **ENG-1 titles** are neutral by construction ("GitHub issue · sympy/sympy · instance 13798") because issue titles
   usually name the module. The issue text itself may name or link the file; that is the record and is kept.
4. **ENG-2 rationale** quotes the developer's prefix (e.g. `fix:` or `fix(rustup):`), never the message body; the
   message is not in the state.
5. **ENG-5 decidability rule:** the target message must share a content word (5+ letters, non-stop-word) with the
   diff, and each distractor must carry a content word absent from both the diff and the target message; distractors
   are the three closest in length. Option keys are 8-character commit hashes (the record's identifiers) with the
   message as the description; the diff carries no hash.
6. **Contamination:** ENG-1 and ENG-3 are marked high (SWE-bench Verified and CVE text are certainly in training
   data), ENG-2/ENG-4/ENG-5 medium.
7. **Language mix in ENG-2/ENG-5** skews to TypeScript (23 and 18 of 30) because TypeScript projects use Conventional
   Commits far more than Rust or Go in CommitPackFT and because the walk is by hash order. Adding a per-language cap
   would be a one-line change if a flatter mix is wanted.
8. **`SWE_CODE_COMMIT`/LICENSE URL** for SWE-bench points at `main` (the LICENSE file has not changed since 2023); pin
   to a commit if preferred.

## Summary

Five engineering tasks, 150 real rows, all balanced and passing the mechanical checks. Two tasks changed source
because CommitBench is non-commercial; both now run on CommitPackFT (MIT, per-sample repo licence). Two licence
questions are flagged rather than hidden: SWE-bench Verified's card has no licence field (the project LICENSE is MIT;
issue text is user-generated), and CVE description text is under the CVE Terms of Use (`cve-tou`), which is
permissive but not on the `PERMISSIVE` list. Everything dropped by hand is listed in the module with a reason.
