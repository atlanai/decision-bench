# GitHub release setup

Verified 2026-09-23 for [atlanai/decision-bench](https://github.com/atlanai/decision-bench). Visibility remains **private**. The remote contains its organization starter commit; the benchmark's local history has not been uploaded by this review.

## Applied and read back

| Control | Verified setting |
| --- | --- |
| Main branch checks | `test (3.11)` and `test (3.12)`, bound to GitHub Actions app 15368; branch must be current |
| Pull requests | One approving review; stale approvals dismissed; conversations resolved |
| Administrator bypass | Main branch protection enforced for administrators |
| Force push and deletion | Both disabled on main |
| Commit signatures | Existing organization signed-commits rule retained |
| Actions token | Read-only by default; cannot approve pull requests |
| Merged branches | Automatic deletion enabled |
| Pages environment | Deployment restricted to protected branches |
| Workflow dependencies | Six Actions resolved from upstream tags to immutable commit SHAs in local workflows |

The required Python checks become satisfiable after the benchmark CI workflow is submitted. The starter repository does not contain it yet. A normal code review is still required; no protection was disabled to upload benchmark content.

## Platform and organization blockers

- **Dependabot alerts:** enabling returned HTTP 422 because an enforced organization security configuration prevents changing this setting. An organization owner must change or exempt that configuration. Readback confirms alerts remain disabled.
- **Private vulnerability reporting:** both read and enable calls returned HTTP 404 on this private repository. Enable and verify it when preparing the public release before advertising the Security-tab reporting flow.
- **Fork workflow approval:** GitHub returned HTTP 422 because this setting is not allowed for private repositories. Apply `all_external_contributors` after visibility changes.
- **Secret scanning/push protection:** readback showed disabled. No paid Advanced Security feature was activated. Request the appropriate organization configuration or enable eligible public-repository features at release.
- **Pages hosting:** the protected environment is prepared, but no Pages site was created and no content deployed. Activate workflow-based Pages only after the data/history release decisions are resolved.

Repository links in the contribution guide, viewer and citation now target the final repository. Badges do not claim successful remote CI while the benchmark has not run there.

## Release sequence

1. Resolve the [data review](data-release-review.md) decisions and the exposed-key rotation noted in [the initial review](public-release-review.md).
2. Prepare the intended public snapshot without accidentally uploading old local history or overwriting the remote starter/security files. Submit it through the protected pull-request path with signed commits.
3. Obtain the required review and passing checks. Apply organization-controlled security settings.
4. Change visibility only when ready, then enable/read back public-only reporting, push protection and fork approvals. Configure Pages from Actions if the site is intended to be public.

Changing visibility, rewriting history, and merging or publishing benchmark data were not part of the settings changes performed here.
