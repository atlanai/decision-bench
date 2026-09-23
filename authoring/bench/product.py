"""product: two tasks a product manager decides from real records.

PRD-1  "Which headline won?"  A · B
  Two headline packages from one Upworthy home-page test (2013–2015), with the story lede both shared. The
  answer is the package with the higher click-through rate, from the archive's recorded impressions and clicks.
PRD-2  "Major, minor or patch?"  major · minor · patch
  One release's notes from the CHANGELOG.md of an open-source project that follows Keep a Changelog and semantic
  versioning, with version numbers and dates masked. The answer is derived from the two consecutive version
  numbers in the changelog.
PRD-3 (GitHub issue classification) was not built: the NLBSE'23 repository is AGPL-3.0 and GitHub's terms only
  license issue text for reproduction "through the Service". PRD-4 was not built; see the authoring report.

Sampling rules
  PRD-1 (Upworthy Research Archive, exploratory packages file, CC BY 4.0)
    - tests are ordered by rank(clickability_test_id); within a test only packages with >= 4,000 impressions
      count; the pair compared is the highest- and lowest-CTR such package (ties broken by slug);
    - the winner's CTR is at least 1.4x the loser's and a two-proportion z-test gives |z| >= 2.5758 (p < 0.01,
      two-sided); the two headlines differ; both packages share the same eyecatcher_id (image) and the same
      lede, so the headline and excerpt are the only differences a viewer saw; the lede is non-empty;
    - BLOCK: any package whose headline, excerpt or lede matches the profanity list below is dropped;
    - A/B assignment: the winner is A when the first 8 hex digits of rank(test id) are even, else B;
    - ledes over 1,200 characters are cut with an explicit "…[N chars truncated]" marker; HTML tags stripped;
    - the first 30 tests passing these rules are used; TITLES holds a hand-written neutral title per test.
  PRD-2 (CHANGELOG.md files of the repositories in REPOS, pinned at a commit)
    - the file is split at every "## " heading; a heading is a release when it starts with x.y.z (optionally
      bracketed or linked) ; the previous release is the next such heading down the file;
    - both versions are >= 1.0.0 and the release is the canonical successor of the previous one: major when
      x+1.0.0, minor when x.y+1.0, patch when x.y.z+1; anything else (parallel branches, skipped numbers) is
      skipped;
    - the body has at least one "### " section, is 150–6,000 characters, and does not contain the words
      major, minor, patch or unreleased (which would give the answer away or refer to a different release);
    - section names are normalised (Fixes -> Fixed, Changes -> Changed, New Features/Features -> Added,
      Breaking changes -> Breaking, Bug Fixes -> Fixed);
    - major rows: a Removed or Breaking section, or the body says "breaking", "drop(ped|s) support" or
      "no longer support";
    - minor rows: an Added section, no Removed, Breaking or Security section, no mention of security (a
      security release reads as a patch, which would make the answer arguable), and none of: breaking,
      drop(ped|s) support, no longer, removed, renamed, deprecated, "remove ", dropped;
    - patch rows: only Fixed and/or Security sections, none of the words above, and none of add/added/adds,
      new, "support for";
    - cleaning: "[#123](url)" -> "#123"; GitHub pull/issue URLs -> "#123"; other links into the repository ->
      "[link]"; every x.y.z token -> "x.y.z"; dates -> "[date]";
    - candidates are filled by answer, major first, then minor, then patch (major releases are scarce), each in
      rank("owner/repo@version") order; at most 4 rows per repository and 10 per answer.
"""
from __future__ import annotations

import collections
import csv
import html
import math
import re

from . import dataset, task, row, rank, SOURCES as SOURCE_DIR

# --------------------------------------------------------------------------------------------- sources

UPWORTHY_FILE = "upworthy/upworthy-archive-exploratory-packages-03.12.2020.csv"
UPWORTHY_URL = "https://osf.io/download/3vqmp/"  # osfstorage GUID 3vqmp in project https://osf.io/jd64p/
UPWORTHY_CITE = ("Matias, Munger, Le Quere and Ebersole, The Upworthy Research Archive, a time series of 32,487 "
                 "experiments in U.S. media, Scientific Data 8:195, 2021.")

# (owner/repo, SPDX licence of the repository, changelog file, pinned commit, neutral description for titles)
REPOS = [
    ("Textualize/rich", "MIT", "CHANGELOG.md", "9d8f9a372cc5916fd4781fec207ced7ddac2f08f",
     "a Python terminal text-formatting library"),
    ("Textualize/textual", "MIT", "CHANGELOG.md", "06dbeef4bb70fb718236aa418ed658ef4667a126",
     "a Python terminal application framework"),
    ("python-poetry/poetry", "MIT", "CHANGELOG.md", "94b6e35b9091991887aa54feeb3771a86d3bd692",
     "a Python packaging and dependency tool"),
    ("httpie/cli", "BSD-3-Clause", "CHANGELOG.md", "5b604c37c6c67e18e7c3e9aee6c88a8c22b98345",
     "a command-line HTTP client"),
    ("thephpleague/flysystem", "MIT", "CHANGELOG.md", "f7fb152932f30072d573510cbd4dd657d6475b25",
     "a PHP filesystem abstraction library"),
    ("thephpleague/commonmark", "BSD-3-Clause", "CHANGELOG.md", "6efbd9c472b91db0a3350fcd601c8332c2382e1f",
     "a PHP Markdown parser"),
    ("guzzle/guzzle", "MIT", "CHANGELOG.md", "93939470950a9b11e2e84204166ef5e048c55fe4",
     "a PHP HTTP client"),
    ("ramsey/uuid", "MIT", "CHANGELOG.md", "dc681915388ca5fd55a7fcb7c85bd9202f20fd4a",
     "a PHP UUID library"),
    ("sebastianbergmann/diff", "BSD-3-Clause", "ChangeLog.md", "3540781ec37cef2da235448e5461e13b7c54206b",
     "a PHP diff library"),
    ("sebastianbergmann/comparator", "BSD-3-Clause", "ChangeLog.md", "34dcca995ee957b433ebfb9f1f46777cce2909a2",
     "a PHP value-comparison library"),
    ("sebastianbergmann/environment", "BSD-3-Clause", "ChangeLog.md", "627b083b89c8ecdb43d2bd3ce8179b81fa4eb766",
     "a PHP runtime-environment helper library"),
    ("sebastianbergmann/exporter", "BSD-3-Clause", "ChangeLog.md", "7e269da761c5714d069904597c01023918898a02",
     "a PHP variable-export library"),
    ("olivierlacan/keep-a-changelog", "MIT", "CHANGELOG.md", "08d0df5a7e93b71d902def8be0f0d40025b56289",
     "the Keep a Changelog website"),
]


def _cl_path(repo):
    return f"changelogs/{repo.replace('/', '__')}.md"


SOURCES = [{"dataset": "Upworthy Research Archive", "url": UPWORTHY_URL, "path": UPWORTHY_FILE}] + [
    {"dataset": f"{repo} changelog", "url": f"https://raw.githubusercontent.com/{repo}/{sha}/{fname}",
     "path": _cl_path(repo)} for repo, _, fname, sha, _ in REPOS]

CHANGELOG_DATASET = {"MIT": "changelogs-mit", "BSD-3-Clause": "changelogs-bsd"}


def _repo_list(lic):
    return "; ".join(f"{repo} (https://github.com/{repo}/blob/{sha}/LICENSE)" for repo, l, _, sha, _ in REPOS
                     if l == lic)


def _datasets():
    dataset(id="upworthy-archive", name="Upworthy Research Archive (exploratory packages)", tasks=["PRD-1"],
            homepage="https://upworthy.natematias.com/",
            license="CC-BY-4.0",
            license_url="https://osf.io/jd64p/",
            content="Headline packages (headline, excerpt, lede) that Upworthy's editors wrote and tested on the "
                    "upworthy.com home page between 2013 and 2015, with each package's impressions and clicks.",
            content_license="CC-BY-4.0",
            content_terms="The OSF project (jd64p) is licensed CC-By Attribution 4.0 International and the archive "
                          "site says the archive is released under a Creative Commons Attribution 4.0 International "
                          "License (https://upworthy.natematias.com/). The headlines and ledes were written by "
                          "Upworthy's own staff and released by Upworthy as part of the archive; there is no "
                          "separate upstream author.",
            labelled_by="the recorded impressions and clicks of each package (the click-through rates)",
            changes="HTML tags stripped from ledes and ledes over 1,200 characters cut with an explicit marker; "
                    "otherwise headlines, excerpts and ledes are verbatim. Packages are relabelled A/B.",
            selection="Tests in sha256 order of their id; the highest- and lowest-CTR packages with at least 4,000 "
                      "impressions each, sharing the same image and lede, with a CTR ratio of at least 1.4 and a "
                      "two-proportion z-test p < 0.01; a profanity block list; the first 30.",
            citation=UPWORTHY_CITE,
            bibtex="""@article{matias2021upworthy,
  author  = {Matias, J. Nathan and Munger, Kevin and Le Quere, Marianne Aubin and Ebersole, Charles},
  title   = {The Upworthy Research Archive, a time series of 32,487 experiments in U.S. media},
  journal = {Scientific Data},
  volume  = {8},
  number  = {195},
  year    = {2021},
  doi     = {10.1038/s41597-021-00934-7}
}""")
    for lic, ident in CHANGELOG_DATASET.items():
        first = next(r for r in REPOS if r[1] == lic)
        dataset(id=ident, name=f"CHANGELOG.md files of {lic}-licensed projects (Keep a Changelog)", tasks=["PRD-2"],
                homepage="https://keepachangelog.com/",
                license=lic,
                license_url=f"https://github.com/{first[0]}/blob/{first[3]}/LICENSE",
                content="Release notes written by the maintainers of open-source projects in their CHANGELOG.md, "
                        "fetched from GitHub at a pinned commit.",
                content_license=lic,
                content_terms=f"Each changelog is a file in its repository and is covered by the repository's {lic} "
                              f"LICENSE, read at the pinned commit: {_repo_list(lic)}.",
                labelled_by="the two consecutive version numbers in the changelog (a written rule maps them to "
                            "major, minor or patch)",
                changes="Version numbers replaced with x.y.z, dates with [date], GitHub pull/issue links reduced to "
                        "#number and other links into the repository to [link]; the version heading is removed.",
                selection="Releases in sha256 order of owner/repo@version, both versions at or above 1.0.0, the "
                          "release a canonical successor of the previous entry, section rules per answer (see the "
                          "module docstring), at most 4 per repository and 10 per answer.",
                citation=f"CHANGELOG.md files of {', '.join(r[0] for r in REPOS if r[1] == lic)} (GitHub, pinned "
                         "commits in data/sources/manifest.json).",
                bibtex=f"""@misc{{{ident.replace('-', '')}2026,
  title        = {{CHANGELOG.md files of {lic}-licensed open-source projects following Keep a Changelog}},
  howpublished = {{GitHub; pinned commits listed in data/sources/manifest.json}},
  note         = {{{', '.join(r[0] for r in REPOS if r[1] == lic)}}},
  year         = {{2026}}
}}""")


# --------------------------------------------------------------------------------------------- PRD-1

PRD1_INSTRUCTION = (
    "Upworthy tested headlines on its home page between 2013 and 2015: visitors were randomly shown one of "
    "several packages (a headline and a short excerpt) for the same story, with the same picture, and clicks "
    "were counted. Below are two packages from one such test and the story's opening paragraph (lede), which "
    "both packages led to. Decide which package earned the higher click-through rate. Each package was shown "
    "to at least 4,000 visitors and the difference was large (at least 1.4 times, p < 0.01), so one of them "
    "clearly won.")

PRD1_OPTIONS = {"A": "Package A had the higher click-through rate.",
                "B": "Package B had the higher click-through rate."}

BLOCK = re.compile(r"\b(fuck\w*|shit\w*|d\*ck|dick\w*|cunt\w*|bitch\w*|asshole\w*|whore\w*|slut\w*|nigg\w*|"
                   r"fag\w*|retard\w*)\b", re.I)
LEDE_LIMIT = 1200

# Hand-written neutral titles per test id (the subject of the story, never a hint at which headline won).
TITLES = {
    "5314692e5187adda77000006": "Upworthy test · street-art posters about harassment of women",
    "53860d3c92398a9dda00001b": "Upworthy test · a Twitter hashtag after a mass killing",
    "53990fb7d5d900b82500002d": "Upworthy test · post-traumatic stress",
    "539b60dab1ca28937e000016": "Upworthy test · Caribbean nations and slavery reparations",
    "5332fe040967e669a5000008": "Upworthy test · a note about orangutans",
    "53da9dc4c8d9d17311000012": "Upworthy test · the history of mental-illness stigma",
    "54287977735e82571100000d": "Upworthy test · where rape-prevention efforts are aimed",
    "5395fa8f0e0fa8f43a000001": "Upworthy test · teenagers teach seniors to use the internet",
    "541c816b7bc1ef895600002b": "Upworthy test · a map of energy use by country",
    "527bea8be3b9cb208701d060": "Upworthy test · a film director's speech to feminists",
    "528ba310e10b5a2dc5001f4f": "Upworthy test · an actress talks about being transgender",
    "53f253aaf1592f712e000017": "Upworthy test · why people procrastinate",
    "523897723b612b7ab900148f": "Upworthy test · a talk-show host's monologue about a pop star",
    "539c24359123cd1f5f000008": "Upworthy test · an animal shelter's new adoption campaign",
    "53a8f12d7bb5bcf6eb000076": "Upworthy test · a student who stayed in high school",
    "538e4254ca7472ee38000003": "Upworthy test · Florida teenagers with adult criminal records",
    "53169523a16f78f2a000003e": "Upworthy test · teachers Americanize a Mexican child's name",
    "5400c0a1bd37b6e55100006b": "Upworthy test · a father's wishes about his funeral",
    "539dda25050be602a8000020": "Upworthy test · advice on negotiating",
    "545395482693bbcdc6000046": "Upworthy test · an animated short about American workers",
    "5148c60378ec5400020020d9": "Upworthy test · deported US military veterans",
    "54089fe6844567ec2d000002": "Upworthy test · a scientist on Common Core school standards",
    "52ceb70737594313bc0014ec": "Upworthy test · photographs of people across social divides",
    "53db8e9f2248657aa1000027": "Upworthy test · how clothing affects thinking",
    "53f548f1ba722b505e000029": "Upworthy test · growing older with HIV",
    "53b3158fe07a81619500001a": "Upworthy test · whether unions are still needed",
    "52a170689f521e4642000255": "Upworthy test · Nelson Mandela's advice on living",
    "53a9bd237bb5bcb2470000c2": "Upworthy test · an infographic about recycling",
    "54207b8c02c5bf386500002d": "Upworthy test · a mother's essay on breastfeeding",
    "52d0ad1b1229172bb2000a47": "Upworthy test · brainstorming at work",
    "5399e6b88bc010a36b00003a": "Upworthy test · a campaign showing people of all body sizes",
    "52d569abcf7c51b2d2001cb4": "Upworthy test · a passenger's lessons from the Hudson River landing",
}

SKIP_PRD1 = {}  # test id -> reason, for rows dropped on reading (none so far)


def _strip_html(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).replace("\r", "").strip()


def _ctr(p):
    return int(p["clicks"]) / int(p["impressions"])


def _ztest(a, b):
    ca, na, cb, nb = int(a["clicks"]), int(a["impressions"]), int(b["clicks"]), int(b["impressions"])
    p = (ca + cb) / (na + nb)
    se = math.sqrt(p * (1 - p) * (1 / na + 1 / nb))
    return abs(ca / na - cb / nb) / se if se else 0.0


def _prd1(target=30):
    with open(SOURCE_DIR / UPWORTHY_FILE, encoding="utf-8", newline="") as f:
        tests = collections.defaultdict(list)
        for r in csv.DictReader(f):
            tests[r["clickability_test_id"]].append(r)
    n = 0
    for tid in sorted(tests, key=rank):
        if n >= target:
            break
        if tid in SKIP_PRD1:
            continue
        arms = [p for p in tests[tid] if int(p["impressions"]) >= 4000]
        if len(arms) < 2:
            continue
        arms.sort(key=lambda p: (-_ctr(p), p["slug"]))
        win, lose = arms[0], arms[-1]
        if _ctr(lose) == 0 or _ctr(win) / _ctr(lose) < 1.4 or _ztest(win, lose) < 2.5758:
            continue
        if win["headline"].strip() == lose["headline"].strip():
            continue
        lede = _strip_html(win["lede"])
        if not lede or win["eyecatcher_id"] != lose["eyecatcher_id"] or lede != _strip_html(lose["lede"]):
            continue
        if any(BLOCK.search(p[k]) for p in (win, lose) for k in ("headline", "excerpt", "lede")):
            continue
        if len(lede) > LEDE_LIMIT:
            lede = lede[:LEDE_LIMIT] + f"…[{len(lede) - LEDE_LIMIT:,} chars truncated]"
        gold = "A" if int(rank(tid)[:8], 16) % 2 == 0 else "B"
        packages = {gold: win, ("B" if gold == "A" else "A"): lose}
        state = {"story_lede": lede,
                 "picture": "both packages used the same picture (not included in the archive)",
                 "package_A": {"headline": packages["A"]["headline"].strip(),
                               "excerpt": packages["A"]["excerpt"].strip()},
                 "package_B": {"headline": packages["B"]["headline"].strip(),
                               "excerpt": packages["B"]["excerpt"].strip()}}
        ratio = _ctr(win) / _ctr(lose)
        loser_key = "B" if gold == "A" else "A"
        rationale = (f"Package {gold} drew {int(win['clicks']):,} clicks from {int(win['impressions']):,} impressions "
                     f"({_ctr(win):.2%}) against {int(lose['clicks']):,} from {int(lose['impressions']):,} "
                     f"({_ctr(lose):.2%}) for package {loser_key}: {ratio:.1f} times the click-through rate "
                     f"(two-proportion z = {_ztest(win, lose):.1f}, p < 0.01).")
        title = TITLES.get(tid)
        assert title, f"PRD-1: no title for test {tid}: {lede[:120]!r}"
        row("PRD-1", tid, title=title, state=state, gold=gold, rationale=rationale,
            source=dict(dataset_id="upworthy-archive", dataset="Upworthy Research Archive (exploratory packages)",
                        license="CC-BY-4.0", url="https://osf.io/jd64p/", citation=UPWORTHY_CITE, record_id=tid,
                        original_label=f"{win['slug']} {win['clicks']}/{win['impressions']} vs "
                                       f"{lose['slug']} {lose['clicks']}/{lose['impressions']}",
                        labelled_by="the recorded impressions and clicks of each package"),
            note=f"Test week {win['test_week']}; {len(tests[tid])} packages were in the test.")
        n += 1


# --------------------------------------------------------------------------------------------- PRD-2

PRD2_INSTRUCTION = (
    "Below are the release notes of one version of an open-source project, taken from its CHANGELOG.md. The "
    "project follows Keep a Changelog and semantic versioning and was already at version 1.0.0 or later. "
    "Version numbers are shown as x.y.z, dates as [date], and links as issue numbers. Decide which part of "
    "the version number was incremented for this release: major for incompatible changes (something removed, "
    "support dropped, or behaviour users must adapt to), minor for backward-compatible new functionality, "
    "patch for backward-compatible bug or security fixes only.")

PRD2_OPTIONS = {"major": "Incompatible changes: something was removed or users must adapt (x+1.0.0).",
                "minor": "Backward-compatible new functionality (x.y+1.0).",
                "patch": "Backward-compatible bug or security fixes only (x.y.z+1)."}

HEADING = re.compile(r"^##\s*\[?v?(\d+)\.(\d+)\.(\d+)\]?(?:\([^)]*\))?\s*[-–—:]?\s*\(?(\d{4}-\d{2}-\d{2})?\)?\s*$")
SECTION_NAMES = {"fixes": "fixed", "changes": "changed", "new features": "added", "features": "added",
                 "breaking changes": "breaking", "bug fixes": "fixed"}
MAJOR_CUES = re.compile(r"breaking|drop(ped|s)? support|no longer support", re.I)
INCOMPATIBLE = re.compile(r"breaking|drop(ped|s)? support|no longer|removed|renamed|deprecated|remove |dropped", re.I)
FEATURE = re.compile(r"\badd(ed|s)?\b|\bnew\b|\bsupport for\b", re.I)
GIVEAWAY = re.compile(r"\b(major|minor|patch|unreleased)\b", re.I)


def _sections(body):
    out = []
    for s in re.findall(r"^###\s*\[?(.+?)\]?\s*$", body, re.M):
        s = s.strip().lower()
        out.append(SECTION_NAMES.get(s, s.split()[0]))
    return out


def _clean(body, repo):
    body = re.sub(r"\[([\w./-]*#?\d+)\]\(https?://[^)\s]+\)", r"\1", body)
    body = re.sub(r"\(?https?://github\.com/[\w.-]+/[\w.-]+/(?:pull|issues)/(\d+)/?\)?", r"#\1", body, flags=re.I)
    body = re.sub(r"https?://github\.com/" + re.escape(repo) + r"[^\s)]*", "[link]", body, flags=re.I)
    body = re.sub(r"\bv?\d+\.\d+\.\d+\b", "x.y.z", body)
    body = re.sub(r"\d{4}-\d{2}-\d{2}", "[date]", body)
    return body.strip()


def _releases(text):
    """(version, date, body) for every '## ' heading that names a version, in file order."""
    parts = re.split(r"^(?=## )", text, flags=re.M)
    out = []
    for part in parts:
        head, _, body = part.partition("\n")
        m = HEADING.match(head)
        if m:
            out.append((tuple(int(x) for x in m.groups()[:3]), m.group(4), body.strip()))
    return out


def _bump(v, pv):
    if v == (pv[0] + 1, 0, 0):
        return "major"
    if v == (pv[0], pv[1] + 1, 0):
        return "minor"
    if v == (pv[0], pv[1], pv[2] + 1):
        return "patch"
    return None


def _prd2(per_answer=10, per_repo=4):
    candidates = []
    for repo, lic, fname, sha, desc in REPOS:
        text = (SOURCE_DIR / _cl_path(repo)).read_text(encoding="utf-8")
        rels = _releases(text)
        for i in range(len(rels) - 1):
            (v, date, body), (pv, _, _) = rels[i], rels[i + 1]
            bump = _bump(v, pv)
            if pv < (1, 0, 0) or bump is None or not date:
                continue
            secs = _sections(body)
            if not secs or not 150 <= len(body) <= 6000 or GIVEAWAY.search(body):
                continue
            if bump == "major":
                ok = "removed" in secs or "breaking" in secs or bool(MAJOR_CUES.search(body))
            elif bump == "minor":
                ok = ("added" in secs and not {"removed", "breaking", "security"} & set(secs)
                      and not INCOMPATIBLE.search(body) and not re.search(r"security", body, re.I))
            else:
                ok = set(secs) <= {"fixed", "security"} and not INCOMPATIBLE.search(body) and not FEATURE.search(body)
            if ok:
                ver = ".".join(map(str, v))
                candidates.append((rank(f"{repo}@{ver}"), repo, lic, fname, sha, desc, ver, ".".join(map(str, pv)),
                                   date, bump, body, secs))
    # Major releases are the scarce class, so answers are filled major, then minor, then patch, each in rank order;
    # otherwise minor and patch rows would use up the per-repository quota of the repositories that hold them.
    candidates.sort(key=lambda c: (["major", "minor", "patch"].index(c[9]), c[0]))
    n_answer, n_repo = collections.Counter(), collections.Counter()
    for _, repo, lic, fname, sha, desc, ver, prev, date, bump, body, secs in candidates:
        if n_answer[bump] >= per_answer or n_repo[repo] >= per_repo:
            continue
        n_answer[bump] += 1
        n_repo[repo] += 1
        part = {"major": "first", "minor": "second", "patch": "third"}[bump]
        if bump == "major":
            evidence = ("the notes have a Removed section" if "removed" in secs else
                        "the notes have a Breaking changes section" if "breaking" in secs else
                        "the notes describe dropped support or breaking changes")
        elif bump == "minor":
            evidence = "the notes add functionality and remove nothing"
        else:
            evidence = "the notes list only fixes" + (" and security fixes" if "security" in secs else "")
        rationale = (f"The changelog lists this release as {ver}, following {prev}: the {part} number was "
                     f"incremented, a {bump} release; {evidence}.")
        row("PRD-2", f"{repo}@{ver}", title=f"Release notes · {desc} · {date}",
            state={"project": desc, "release_notes": _clean(body, repo)},
            gold=bump, rationale=rationale,
            source=dict(dataset_id=CHANGELOG_DATASET[lic], dataset=f"{repo} {fname}", license=lic,
                        url=f"https://github.com/{repo}/blob/{sha}/{fname}",
                        citation=f"{repo} {fname} at commit {sha[:12]} (GitHub).",
                        record_id=f"{repo}@{ver}", original_label=f"{ver} after {prev}",
                        labelled_by="the two consecutive version numbers in the changelog"))


# --------------------------------------------------------------------------------------------- define

def define():
    _datasets()
    task("PRD-1", category="product", name="Which headline won?", ask="Which package got more clicks per view?",
         instruction=PRD1_INSTRUCTION, options=PRD1_OPTIONS, shape="compare", input_type="headline A/B test",
         modality="text", expertise="none", contamination="medium", label_origin="objective record")
    task("PRD-2", category="product", name="Major, minor or patch?", ask="Which part of the version was bumped?",
         instruction=PRD2_INSTRUCTION, options=PRD2_OPTIONS, shape="classify", input_type="release notes",
         modality="text", expertise="practitioner", contamination="medium", label_origin="derived by rule")
    _prd1()
    _prd2()
