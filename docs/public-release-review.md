# Public release review — 2026-09-23

**Follow-up:** Repository links are now set and live GitHub controls were verified. See [repository setup](github-release-setup.md) and the completed [data/privacy review](data-release-review.md). Some publication decisions remain open; the original observations below are the first-review snapshot.

The working tree was reviewed before its public-release preparation commit. No confirmed live credential was found. This is a bounded code and disclosure review, not an exhaustive audit or a guarantee that every upstream record is safe to redistribute.

## Changes made

- Escaped the viewer's URL-controlled modality subtitle and restricted the filter to `text` or `image`. External source links now accept only HTTP(S). Fixed latency-formatter shadowing that crashed populated leaderboard and task pages.
- Redacted configured OpenAI-compatible, TypeSafe and Laya credentials, endpoint URLs and remote hostnames across response structures, dictionary keys, run persistence and prediction export. Added successful-response and old-output regression tests.
- Confined image reads to `data/assets/`, rejecting absolute paths, traversal and symlinks escaping that directory.
- Applied recognized provider-key patterns to third-party data too, added fine-grained GitHub token detection, and removed credential excerpts from scanner output.
- Isolated native-provider tests from local `.env` settings so mocked tests cannot accidentally read real credentials.
- Added validation, secret checks and viewer regressions to the Pages build before artifact upload. Corrected the security policy's claims about raw response IDs and heuristic scan coverage.
- Removed the company-specific visual-reference URL from the banner prompt notes. The new banner images were visually inspected.

## Evidence and limits

- Reviewed API destination checks, redirect handling, CLI invocation, configuration, raw output persistence, publication, corpus image reads, key viewer rendering paths, source fetching and CI/Pages workflows.
- Scanned the nine existing reachable commits: 299 distinct blob/path versions. The detected history entries were three local home-directory references in old authoring reports and two matches in the same known synthetic CredData fixture. The historical fixture is identical to its current scrubbed version.
- Compared three nonempty local configuration values against current commit candidates and all reachable history blobs without printing the values. No matches.
- The active corpus validates at 1,071 rows, 35 tasks and 11 categories, with 14 configured models. There are no published model results yet. A model in configuration is not evidence of a successful live run.
- Runtime tests use mocks and local fake endpoints. The review did not send benchmark data or credentials to real providers.
- Large third-party datasets, historical corpus content and existing binary assets were not exhaustively reviewed manually. The text scanner skips probable binary files and files larger than 20 MB; third-party hostname/path exemptions remain intentional. Encoded or unknown secrets may evade heuristics.
- CLI isolation depends on installed CLI behavior. Repository settings, branch protections, private vulnerability reporting and hosting configuration were not verified: this checkout has no Git remote.

## Before changing visibility

- **Decide what history to publish.** Existing commits retain the author's personal email and old local home paths. A new cleanup commit does not erase those. If these should stay private, prepare a separately approved history rewrite or a fresh public history before pushing. Do not assume deleting a current file removes it from Git.
- **Set the final repository URL.** Replace `OWNER` in `CONTRIBUTING.md` and the `repo` meta tag in `site/index.html`; update citation/release links and badges when a destination exists.
- **Configure repository controls.** Enable private vulnerability reporting as promised by `SECURITY.md`; select required checks and review rules; configure the Pages environment and intended audience. Consider pinning third-party Actions to reviewed immutable commits.
- **Review redistribution and privacy.** Keep dataset-specific attribution and licenses with rows; the code's MIT license does not replace them. Confirm upstream/embedded-content rights and inspect personal-data-bearing records, historical datasets, binary assets and vendor marks before release. The source catalog is evidence to review, not independent legal clearance.
- **Inspect every export.** Keep `.env`, `runs/`, downloaded source data and local caches ignored. Review `results/` and the exact Pages artifact, particularly when exporting older runs whose keys are no longer configured. Avoid publishing a local preview generated with `--include-runs` unintentionally.
- **Rotate any key exposed in diagnostic output.** A pre-existing native-provider test read a local key through configuration fallback and included it in a failed assertion during this review. The HTTP request was mocked; the temporary log was scrubbed and test isolation fixed. Rotation remains an operator action.
- **Preserve reproducibility.** Source fetching currently checks hashes only for existing manifest entries and writes downloads before checking them. Review source changes and pins before rebuilding; do not use `--pin` to accept an unexplained upstream change.

## Repeatable local checks

```sh
make check
python3 -m decision_bench report
git diff --check
git status --short
```

These checks do not rewrite history, enable GitHub protections, verify third-party legal rights, or publish anything.
