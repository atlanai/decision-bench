# Contributing

Thanks for helping. There are four common ways to contribute, and each has a template.

| You want to | Do this |
| --- | --- |
| Report a wrong answer key | Open a **Label error** issue with the row id (shown on every row page) and why the answer is wrong. |
| Add results for a model | Run it, `publish`, and open a pull request with the `results/` folder. See [results/README.md](results/README.md). |
| Add a model to the config | Add an entry to `config/models.json` in a pull request. See [docs/running.md](docs/running.md#choose-a-model). |
| Add or change rows or tasks | Read the rules below, then open a pull request that changes `authoring/bench/`. |

Rights holders and people named in a row can ask for it to be removed with the **Data removal request** template, or privately (see [SECURITY.md](SECURITY.md)).

## Set up

```sh
git clone https://github.com/atlanai/decision-bench && cd decision-bench
python3 -m decision_bench validate
make check        # tests, validate, secret scan, JS syntax
```

Python 3.11 or newer. Nothing needs installing to run, test or view the benchmark. Copy `.env.example` to `.env` only if you will call a model. Never commit `.env`, keys, endpoint URLs or files from `runs/`.

## How the data is built

Each category has a module in `authoring/bench/`. A module declares:
- the upstream files it needs (`SOURCES`);
- the datasets it samples, with their licences (`dataset(...)`);
- its fixed tasks (`task(...)`);
- one `row(...)` per row.

Rows are chosen by written, deterministic rules (sha256 order plus documented exclusions), never by looking at model output.

```sh
python3 scripts/fetch_sources.py            # download upstream files and verify their pinned sha256
python3 scripts/build_bench.py --dry-run    # build and check everything, write nothing
python3 scripts/build_bench.py --dry-run --dump pii-2     # print the rows whose id starts with pii-2
python3 scripts/build_bench.py --dry-run --summary        # one line per row: id, answer, title
```

`scripts/build_bench.py` without `--dry-run` freezes a new corpus. Only maintainers do this, as part of a release.

## Rules for rows and tasks

**Data and licences.** A dataset may be used only if its own licence *and* the terms of the text inside it allow anyone to copy, modify and redistribute it, commercially too. That means MIT, Apache-2.0, BSD, CC0, CC BY, CC BY-SA or public domain. A dataset that is MIT but built on non-commercial or publisher-copyrighted text does not qualify. Nor does one whose authors ask that it not be reshared. The build refuses any licence outside that list (`PERMISSIVE` in `authoring/bench/__init__.py`).

**Labels.** Answers come from the dataset's own human annotators or from an objective record, such as a repository's tests or the consumer's own product choice. Never use a model to produce or "fix" a label. Drop a row you can't defend from its text alone, and do it with a written rule.

**Privacy and safety.** Don't add:
- text centred on private individuals;
- working credentials;
- personal contact details;
- offensive content beyond what a task needs.

Real secrets are replaced with fake values of the same shape, and contact details with placeholders.

**Readability.** A reader should understand a row in about 30 seconds:
- The question is 12 words or fewer, with 2–6 options, each described in one line.
- The title is neutral (`artifact · subject`) and never hints at the answer.
- The input is shown as the real artifact.
- Every option is the answer at least once, and no option is the answer on more than 60% of a task's rows.

`build_bench.py --dry-run` checks all of these mechanically.

**Written examples.** Use them only where no real, redistributable, labelled data exists (today: skill improvement). They are badged "Written example" everywhere.

## Versions

A frozen corpus never changes once results exist for it. A fix to a row or label is a new corpus version with a [CHANGELOG](CHANGELOG.md) entry, and every model is re-run on it. Never change a label because a particular model disagrees with it.

## Code

- Runtime code uses the Python standard library only. The viewer is plain browser JavaScript with no build step.
- New providers must record every attempt, error, token count and timing. They must also record the exact model and request options. Unknown values are `null`, not guesses.
- Never route a request to a fallback model under another model's name.
- Keys and endpoints come only from environment variables. Never write them to a file.
- Add a test for behaviour you change. Tests must not call real models.

## Pull requests

Keep a pull request to one purpose and fill in the template. CI runs the tests on Python 3.11 and 3.12, `validate`, the secret scan and a JavaScript syntax check. By contributing, you agree that your code and written examples are released under the MIT licence.
