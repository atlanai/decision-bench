# Product category (authoring/bench/product.py) — authoring report

Module: authoring/bench/product.py
Checks: `python3 scripts/fetch_sources.py --only product` (exit 0, 14 files, no hash mismatches — nothing is pinned yet)
        `python3 scripts/build_bench.py --dry-run --only product` -> 60 rows, "problems": []
New source folders: data/sources/upworthy/ (one 14.3 MB CSV), data/sources/changelogs/ (13 files, 3–211 KB).

## Tasks built

### PRD-1 "Which headline won?" — 30 rows, A 17 / B 13
Upworthy Research Archive, exploratory packages file. Each row: the story lede both packages shared, and two
packages (headline + excerpt) from one home-page test, relabelled A/B by rank(test id). Answer = the package with
the higher click-through rate. Label origin: objective record (impressions and clicks).
Filters (all written in the module docstring): packages with >= 4,000 impressions; the highest- vs lowest-CTR such
package; CTR ratio >= 1.4; two-proportion z >= 2.5758 (p < 0.01 two-sided); headlines differ; same eyecatcher_id
and same lede (so headline/excerpt is the only visible difference); non-empty lede; profanity block list.
Of the first 34 qualifying tests, 2 were dropped by the block list (headlines containing "Fuck"/"Fuck Off" and
"D*ck Pics"); the first 30 remaining are used. No ledes needed truncation (max state 1,361 chars).
Titles are hand-written per test in TITLES (subject of the story only). Rationales quote clicks/impressions, both
CTRs, the ratio and z. A `note` gives the test week and how many packages the full test had.

### PRD-2 "Major, minor or patch?" — 30 rows, major 10 / minor 10 / patch 10
CHANGELOG.md of 13 repositories (Keep a Changelog + semver), pinned at a commit; 10 repositories ended up
contributing (max 4 each: ramsey/uuid, Textualize/textual, Textualize/rich, thephpleague/flysystem,
python-poetry/poetry, guzzle/guzzle 4 each; sebastianbergmann/diff 2, sebastianbergmann/environment 2,
sebastianbergmann/exporter 1, thephpleague/commonmark 1; httpie/cli, sebastianbergmann/comparator and
olivierlacan/keep-a-changelog declared but not drawn). Label derived by rule from the two consecutive version
headings; only canonical successors count (x+1.0.0 / x.y+1.0 / x.y.z+1, both >= 1.0.0), which avoids mislabelling
back-ported releases in repositories with parallel branches. Section rules per answer are in the docstring
(major: Removed/Breaking section or breaking/dropped-support wording; minor: Added, nothing removed, no
security mention; patch: only Fixed/Security, no feature wording). Bodies containing the words major, minor,
patch or unreleased are excluded (the Keep a Changelog 2.0.0 notes literally say "first major revision").
State = {"project": neutral description, "release_notes": body}; versions -> x.y.z, dates -> [date], GitHub
pull/issue links -> #123, other links into the repo -> [link]. Titles: "Release notes · <description> · <date>".
Median state 422 chars, max 3,200. Majors were filled first (they are scarce: 20 candidates vs 94 minor / 66
patch); this order is stated in the docstring.

## Licence evidence
- Upworthy Research Archive: OSF node jd64p licence "CC-By Attribution 4.0 International"
  (https://api.osf.io/v2/nodes/jd64p/?embed=license; project page https://osf.io/jd64p/); the archive site
  states "Creative Commons Attribution 4.0 International License" (https://upworthy.natematias.com/). Content
  (headlines, excerpts, ledes) was written by Upworthy staff and released by Upworthy in the archive; no separate
  upstream author. Paper: Matias, Munger, Le Quere, Ebersole, Scientific Data 8:195 (2021),
  doi 10.1038/s41597-021-00934-7 (Crossref record; article licence CC BY 4.0). File used:
  upworthy-archive-exploratory-packages-03.12.2020.csv, https://osf.io/download/3vqmp/, 14,260,949 bytes,
  sha256 8368313b060f4015a0c6fb34e6d788163cee29554144aba9390b14922eb9d8ce (matches OSF's listed hash).
- Changelogs: each repository's LICENSE was read at the pinned commit (raw.githubusercontent.com/<repo>/<sha>/
  LICENSE) and matches the GitHub API spdx_id. MIT: Textualize/rich, Textualize/textual, python-poetry/poetry,
  thephpleague/flysystem, guzzle/guzzle, ramsey/uuid, olivierlacan/keep-a-changelog. BSD-3-Clause: httpie/cli,
  thephpleague/commonmark, sebastianbergmann/{diff,comparator,environment,exporter}. The changelog is a file in
  the repository, so the repository licence covers it. Declared as two datasets (changelogs-mit, changelogs-bsd)
  because dataset() takes one SPDX id; content_terms lists every repo with its LICENSE URL and each row's
  source.license carries its own repo's licence.

## Not built
- PRD-3 "Bug, feature or question?" (NLBSE'23 issue-report classification): the repository
  github.com/nlbse2023/issue-report-classification is AGPL-3.0 (not in PERMISSIVE), the data is hosted on Azure
  blob storage with no separate data licence statement, and GitHub's Terms of Service (D.5) grant other users a
  licence to reproduce public content only "through the Service"; nothing establishes a licence to redistribute
  issue text off GitHub. Dropped.
- PRD-4 (other product-feedback / prioritisation data): the one candidate with a verifiable open licence is the
  PROMISE NFR requirements dataset (625 requirements from 15 student projects; header of
  http://ctp.di.fct.unl.pt/RE2017//downloads/datasets/nfr.arff says "(c) 2007 Jane Cleland-Huang ... distributed
  under the Creative Commons Attribution-Share Alike 3.0 License"). Not built: one-sentence requirements such as
  "The system shall refresh the display every 60 seconds" (labelled performance) or "The product shall ensure
  that it can only be accessed by authorized users" (security) are arguable between functional and a quality
  class, so most rows would fail the one-defensible-answer rule. Also looked at and rejected: Promise+ (Zenodo,
  CC BY 4.0, but provenance of the added requirements unclear), public Jira/Bugzilla issue dumps (issue text
  terms unestablished), app-store review sets (no explicit licence). The Upworthy confirmatory file (66 MB)
  would give many more PRD-1 rows if ever needed, but exceeds the ~50 MB guideline.

## Judgement calls for a maintainer
1. PRD-1 rows are empirically labelled: a reader can only "see why" after the fact from the CTRs in the rationale.
   The 1.4x / p<0.01 / >=4,000-impression filters keep the outcome unambiguous, as requested.
2. PRD-1 keeps some sensitive-subject stories (a mass killing and #YesAllWomen, rape-prevention framing, a
   father's funeral, HIV); none are gratuitous and all are real Upworthy tests. Block list covers explicit
   profanity and slurs only; "Piss Off" and "BS" in two headlines were kept.
3. PRD-1 state says both packages used the same picture (the archive has no images). Excerpts are shown even
   when identical or empty, because that is what the record holds.
4. PRD-2 hides the repository name in title and description, but links and prose in the notes are not scrubbed
   (a PR number or the word "Textual"/"Guzzle" may remain); versions and dates are masked.
5. PRD-2 minor rows with a Changed section that alters behaviour (e.g. textual 5.1.0 "apply to displayed children
   only", 8.1.0) are kept: semver-wise they add functionality without removal; a strict reader might call a
   behaviour change breaking. flysystem 3.13.0 ends with a stray empty bullet from the source file.
6. Two dataset() entries for many repositories is a compromise with the one-SPDX-id schema; see above.
7. Title date for PRD-2 rows is the release date from the heading; with the repo name hidden this is not a
   direct giveaway, but a determined reader could look it up (contamination marked medium).
