# Tasks

Decision Bench v3 has **359 rows in 14 tasks and 7 categories**. 323 rows are real records from 14 public datasets. In each, the answer comes from the dataset's own human annotators or from an objective record. The other 36 rows are written examples, used only where no real, redistributable, labelled data exists.

Each task asks one fixed question with a fixed set of 2–10 options, each described in one line. TR-1 and TC-2 are the exceptions: their options come from the row itself (the functions offered in that request, or the agents in that log). Sources, licences and citations are in [data/SOURCES.md](../data/SOURCES.md).

| Category | Task | Question | Options | Rows | Source |
| --- | --- | --- | --- | --- | --- |
| Prompt injection | PI-1 | Is this message an attack on the assistant? | injection · jailbreak · benign | 30 | deepset/prompt-injections; In-The-Wild Jailbreak Prompts |
| | PI-2 | Does this email try to make the assistant do something unrequested? | yes · no | 24 | LLMail-Inject |
| Sensitive data | PII-2 | Is this a real secret committed in code? | real credential · placeholder or test value · not a secret | 24 | Samsung CredData |
| Trace classification | TC-1 | What kind of failure happens at this step? | ignored instruction · user info · blocked · wrong plan · misread output · bad call | 25 | AgentRx (τ-bench and Magentic-One runs) |
| | TC-2 | Which agent caused the failure? | the agents in that log | 22 | Who&When |
| | TC-3 | Did this coding-agent run fix the issue? | fixed · not fixed | 24 | SWE-agent trajectories (answer from the repository's tests) |
| Trace routing | TR-1 | Which tool should the agent call for this request? | the functions offered in that request, or none | 30 | BFCL v3 Live |
| | TR-2 | Which team should handle this customer message? | 10 queues of one bank | 30 | BANKING77 |
| | TR-3 | Which product team owns this complaint? | 7 product areas | 28 | CFPB Consumer Complaint Database (answer is the consumer's own choice) |
| Eval judging | EJ-1 | Is this answer supported by its sources? | supported · not supported | 28 | HAGRID; BEGIN (Wizard of Wikipedia) |
| | EJ-2 | Which response is better? | A · B | 28 | MT-Bench expert human judgments |
| Contract checks | CP-1 | Does this NDA say this? | yes · says the opposite · not addressed | 30 | ContractNLI |
| Skill improvement | SK-1 | Why did the skill fail on this run? | step skipped · step missing · steps conflict · environment · can't tell | 15 | Written examples |
| | SK-2 | Should this skill change ship? | ship · don't ship · not enough evidence | 21 | Written examples |

## How rows are chosen

- **Deterministic.** Candidates are ordered by the sha256 of their source id, then taken in order while they pass the module's written rules. No model output is used anywhere in selection or labelling.
- **Defensible labels.** Real labels carry noise. A row a careful reader could argue has a different answer is dropped. Most drops follow a written rule. Where a module drops specific records by hand, it lists each one with its reason (`EXCLUDE`, `TC1_SKIP`, `CRED_EXCLUDED` and similar in `authoring/bench/`).
- **Balanced.** Every option is the answer at least once, and no option is the answer on more than 60% of a task's rows.
- **Readable.** The question is 12 words or fewer. The title is neutral and never hints at the answer. The input is shown as the real artifact, trimmed only where marked `…[trimmed]`.
- **Safe to publish.**
  - Real secrets are replaced with same-shape fakes, and nothing records where they came from.
  - Contact details in contracts are replaced with placeholders.
  - Offensive prompts and text centred on private individuals are filtered out by written rules.

## What the model sees

Only the row's input (`state`), the task instruction and the options, in a fixed per-row shuffled order. The answer, rationale, title, summary, note, source and short question are never sent. See [protocol.md](protocol.md).

## Removed before release

These were built, then removed because their sources failed the licence policy. Each module's docstring gives the details.

- **PII-1 (mask a mention in a court judgment).** TAB is MIT, but the European Court of Human Rights requires written permission for commercial reuse of its judgments. No replacement with human masking labels has a permissive licence. The closest, a set of Wikipedia biographies annotated with TAB's scheme, has no licence. If its authors add one, PII-1 can return.
- **The first versions of TC-1, EJ-1 and EJ-2.**
  - TC-1 used TRAIL, whose authors ask that it not be reshared outside a gated repository.
  - EJ-1 used RAGTruth, which is built on MS MARCO (non-commercial) and news articles (publisher copyright).
  - EJ-2 used LLMBar, whose pairs come from AlpacaFarm (CC BY-NC).

## Caveats

- **Contamination.** These public datasets may be in model training data, which can inflate scores.
- **Small tasks.** With 15–30 rows per task, per-task scores have wide intervals, so read the Wilson 95% interval shown with each score. SK-1 (15 rows) and TC-2 (22) are the smallest.
- **Written examples.** Skill improvement is written by the maintainers, not real data. It is badged "Written example" everywhere and can be filtered out.
