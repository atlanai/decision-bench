# Changelog

## 1.0 — first public release, rebuilt around use cases

- 1,071 rows in 35 tasks and 11 use-case categories, every row a real record from one of 36 public datasets. 122 rows carry an image.
- Categories are the visitor's job (engineering, AI agents and evals, trust and safety, customer support, sales and commerce, finance, legal, product management, data and analytics, documents and meetings, design). Each task publishes its labels: decision shape, input type, modality, expertise needed, contamination risk and who decided the answer.
- Removed from v3: the written skill-improvement examples, LLMail-Inject, BEGIN, BANKING77, AgentRx, Who&When and the SWE-agent outcome task, for authenticity or defensibility. Kept and grown: CFPB routing, ContractNLI, CredData secrets, BFCL tool selection, HAGRID grounding, MT-Bench pairwise, prompt injection.
- Not used after licence checks: Rico screenshots, RVL-CDIP, WDC product matching, CommitBench (CC BY-NC), RouterBench (no licence), TAT-QA (annual-report text), Stack Exchange dumps, GitHub issue datasets. The OpenAI moderation set is built but disabled because it mixes in model-generated text.
- Harness: rows may carry images; models flagged `vision` receive them and every prediction records whether the image was sent.
- Viewer: leaderboard entry page with filters in the URL, task table, task and row pages with a fit verdict per model, model profiles, paired compare, methodology, data and a maintainer review mode. On phones and tablets it behaves like an app: a tab bar, bottom sheets, lists in place of wide tables, page transitions, rows you swipe through like cards, and a splash screen; it can be added to a home screen.
- Results: 12 models on bench-v4, in [results/bench-v4/leaderboard.md](results/bench-v4/leaderboard.md). The runs used harness 0.3.0 before the public snapshot; see [results/README.md](results/README.md).

## Earlier internal draft

- 359 rows in 14 tasks and 7 categories. 323 rows are real records from 14 public datasets, and 36 are written examples (skill improvement).
- Every dataset passes the licence policy: its own licence and the terms of the text inside it allow redistribution, commercially too.
- Removed before release because their sources failed that policy: PII-1 (TAB / ECHR judgments), and the first versions of TC-1 (TRAIL), EJ-1 (RAGTruth) and EJ-2 (LLMBar). See [docs/tasks.md](docs/tasks.md#removed-before-release).
- No model results yet.

The earlier draft was internal; its corpus and authoring code are not part of this repository.
