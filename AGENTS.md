# Agent guide

Read [CONTRIBUTING.md](CONTRIBUTING.md) first. It has the rules for data, labels and code. This file adds what an
agent needs on top.

## Commands

```sh
make check                                    # tests, validate, secret scan, site build
python3 -m decision_bench run --model <id>    # see docs/running.md
python3 -m decision_bench publish <run-id>    # writes results/<suite>/<model-id>/
python3 -m decision_bench leaderboard         # rewrites results/<suite>/leaderboard.*
```

## Rules

- Runtime code uses the Python standard library only. Tests never call a real model.
- Never read, print or copy `.env`. Keys and endpoints come only from environment variables.
- Never write an endpoint URL, a hostname, an IP address or a local path into a committed file, a commit message, a
  PR or a comment. `scripts/check_secrets.py` checks committed files only.
- Never edit generated files by hand: `results/<suite>/<model-id>/` and the leaderboard files come from `publish`
  and `leaderboard`.
- A frozen corpus never changes. A fix is a new corpus version.
- The same `--run-id` resumes a run. Use a new one for a new run.

## Pull requests

Fill in `.github/PULL_REQUEST_TEMPLATE.md` and delete the sections that do not apply. A PR that changes a
`results/<suite>/<model-id>/` folder must fill in the **Results** fields. CI (`scripts/check_pr_body.py`) fails
until it does.

## Reviewing a provider or results PR

Use the `review-provider-pr` skill. Agents without skills read
[.claude/skills/review-provider-pr/SKILL.md](.claude/skills/review-provider-pr/SKILL.md) and follow it.
