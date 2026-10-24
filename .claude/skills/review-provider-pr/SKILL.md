---
name: review-provider-pr
description: Review a Decision Bench pull request that adds a model provider or publishes results. Reviews the adapter code, checks the published files, re-runs the model 3 to 5 times, compares the runs row by row, checks latency against the network baseline, and drafts the GitHub review for the maintainer. Use when a PR changes an adapter in decision_bench/, config/models.json or a results/<suite>/<model-id>/ folder, or when asked to verify or benchmark a submitted model.
---

# Review a provider or results PR

The goal is to decide whether the submitted number is what the model gives today, through the named provider, and
whether the code that produced it is safe to merge. Every claim in the review must come from a file, a run or a
command output that you can show.

## Rules for every step

- Never read, print or copy `.env`. Never link or copy the maintainer's main `.env` into a PR worktree: the PR's
  code runs there and can send any key it finds to its own endpoint. The maintainer writes a worktree `.env` with
  only the reviewed provider's key.
- Never write an endpoint URL, a hostname or an IP address into a file, a commit, a PR or a comment. Say "the
  endpoint". `scripts/check_secrets.py` scans committed files only, not comments.
- Never post a review, approve, request changes or merge until the maintainer says so. Show the draft first.
- Write the pass rule (step 4) down before the first run finishes, so the result cannot move it.

## 1. Set up

```sh
gh pr view <n> --json title,author,headRefOid,files,body,commits
git fetch origin pull/<n>/head
git worktree add --detach /tmp/db-pr<n> FETCH_HEAD
```

Classify the PR with the kinds in `.github/PULL_REQUEST_TEMPLATE.md`. Note every Results and Provider field that
is empty or vague. The Results fields are the questions you would otherwise ask in the review.

## 2. Review the code

Diff with `git -C /tmp/db-pr<n> diff origin/main...HEAD`. Run this step in a subagent when one is available, and
give it this list and CONTRIBUTING.md as the rubric:

- **Shared code.** List every change outside the new adapter module and every provider it reaches. Ask for a test
  that pins the old behaviour of those providers. A payload helper that four adapters share is the usual case.
- **Recording.** Every attempt, error, token count and timing is recorded, and the exact model and request options.
  An unknown value is `null`, never `0` or a guess.
- **No silent substitution.** No fallback model under another model's name. If `--api-model` changes the payload,
  it changes the URL too, or the adapter rejects it.
- **Secrets.** Keys and endpoints come only from environment variables. Nothing in `config/models.json`, the run
  record or `metadata.json` carries a host, except a public pricing `source_url`.
- **Images.** How the adapter sends them. No image bytes or local paths in the records.
- **Network baseline.** The provider's URL is in `runner.FIXED_ENDPOINTS` or `runner.endpoint_url()`. The provider
  coverage test in `tests/test_runner.py` fails otherwise. When two provider PRs are open, the one that merges
  second adds its entry.
- **Pricing.** A public price page in `config/models.json`.
- **Tests.** They cover the new payload and parsing and never call a real model.

## 3. Check the published files

In `/tmp/db-pr<n>`:

```sh
make check
python3 -m decision_bench leaderboard && git diff --exit-code results/
```

`validate` already rescores `predictions.jsonl` and `scores.json` against the corpus. The second command shows that
the committed leaderboard matches. In `metadata.json`, check:

- `harness.git_commit` is in the PR and `harness.git_dirty` is `false`. If it is `true`, ask what was not committed.
- coverage is every row, and `corpus.sha256` is the current corpus;
- the run dates and the request options (`run.jobs`, `run.max_attempts`, `run.timeout_seconds`);
- `run.network_baseline` and `totals.server_time_p50_ms_estimate`, when the harness recorded them.

## 4. Re-run the model

Ask the maintainer to write `/tmp/db-pr<n>/.env` with only the environment variable that the provider reads (the
Provider section of the PR names it), set to a key of the same kind that a customer gets. Then:

```sh
cd /tmp/db-pr<n>
python3 -m decision_bench run --model <model-id> --limit 20 --run-id <model-id>-pr<n>-smoke
python3 -m decision_bench run --model <model-id> --run-id <model-id>-pr<n>-r1 \
    --jobs <run.jobs> --max-attempts <run.max_attempts> --timeout <run.timeout_seconds>
```

- Use the submitted request options. Run from a clean tree at the PR head.
- Every run needs a new `--run-id`. The same id resumes the old run. If a run ends with errors, run the same command
  with `--retry-errors`.
- Make 3 full runs, one after another. Runs in parallel share rate limits and change the latency.
- If the PR changes `decision_bench/results.py`, `metrics.py`, `scoring.py` or `corpus.py`, stop and tell the
  maintainer. `compare_runs.py` scores our runs with the PR's own copy of that code.
- Compare, with the model next to it on the leaderboard as `--against`:

  ```sh
  python3 -I <maintainer checkout>/.claude/skills/review-provider-pr/compare_runs.py results/<suite>/<model-id> \
      --runs <model-id>-pr<n>-r1,<model-id>-pr<n>-r2,<model-id>-pr<n>-r3 --against <neighbour-model-id>
  ```

**Pass rule.** The submitted correct count passes when it is not above our maximum plus 2 standard deviations (the
standard deviation has a floor of 1 row). If it fails after 3 runs, make 2 more and decide on all 5. A submitted
count far below ours is not inflation, but report it.

**Read the output.**

- Run-to-run noise on this corpus is small (about 1 to 2 rows). The 95% interval on one run is about plus or minus
  15 rows, so the paired comparison against the neighbour is what tells you if a rank changes.
- Rows where the submitted run differs from all of ours, with a confident probability on the other answer, are not
  sampling noise. If the input tokens are the same, the requests were the same and the model or the deployment
  behind the key changed.
- If our runs share identical probabilities on many more rows with each other than with the submitted run, the
  submitted run came from a different backend.
- The client location does not change accuracy. Do not ask for a re-run from another region to explain an accuracy
  gap.

## 5. Check latency

The median latency is what the client sees: model time, provider serving time and the client's network. Each run
records the network baseline and an estimated server time (see `docs/protocol.md`). Compare the server time with the
submitter's, not the median. A lower submitted median usually means that their client was nearer the endpoint. Get
the client location from the Results fields.

## 6. Draft the review

Write it in the maintainer's voice, short and direct, and show it before posting:

- one opening paragraph: what checks out and what does not;
- a table of every run, submitted and ours: date, correct, accuracy, median latency, server time;
- one line with our mean, spread and the result of the pass rule;
- the deviations: the categories whose counts differ, and the rows that differ from all of our runs;
- latency in one sentence;
- questions only where the answer changes the decision;
- requested changes as a GitHub task list (`- [ ] ...`).

No diagrams, no commands for the author, no notes on how to read a table. Post only when told, with
`gh pr review <n> --request-changes --body-file <file>` (or `--approve`, or `--comment`).

## 7. After the decision

- If another provider PR is open, check which one adds the `FIXED_ENDPOINTS` entry, and re-run CI on the one that
  merges second.
- After the merge, `python3 -m decision_bench report` and the site build pass on `main`.
- Clean up: delete the worktree `.env`, copy any run folder you want to keep (`runs/` is ignored), then
  `git worktree remove /tmp/db-pr<n>`.
