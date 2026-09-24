# Decision Bench v4 · category "agents" — build report

Module: `authoring/bench/agents.py`. New source folders: `data/sources/agentdojo/` (LICENSE + 160 run files, ~0.9 MB)
and `data/sources/tau-bench/` (LICENSE + two gpt-4o trajectory files, 15 MB). BFCL, HAGRID and MT-Bench files
were reused from the existing downloads.

`python3 scripts/fetch_sources.py --only agents` and `python3 scripts/build_bench.py --dry-run --only agents`
both pass; the dry run ends with `"problems": []`. 154 rows in five tasks. I did not run `--pin`.

## Tasks built

| Task | Name | Rows | Answers | State size (median / max chars) |
| --- | --- | --- | --- | --- |
| AGT-1 | Which tool to call | 36 | 27 named functions (22 ordinary + 5 Schema-Guided Dialogue), 9 `none` (25%) | 849 / 1,527 |
| AGT-2 | Did the injection succeed? | 30 | 15 hijacked / 15 not_hijacked | 3,625 / 7,171 |
| AGT-3 | Did the agent complete the task? | 30 | 15 completed / 15 not_completed (airline 8+8, retail 7+7) | 12,775 / 14,759 |
| AGT-4 | (not built, see RouterBench below) | – | – | – |
| AGT-5 | Is the answer backed by sources? | 30 | 15 supported / 15 not_supported (short/long answer types 15/15) | 1,321 / 4,204 |
| AGT-6 | Which reply is better? | 28 | 14 A / 14 B | 2,536 / 4,013 |

The task ids keep the numbering from the brief, so AGT-4 is a gap. Renumber if you prefer contiguous ids.

AGT-2 mix: pipelines Llama-3.3-70B 10, gpt-4o 8, gpt-4o-mini 4, gemini-1.5-flash-002 3, claude-3-5-sonnet 3,
claude-3-sonnet 1, command-r-plus 1; suites slack 14, banking 9, workspace 4, travel 3; attacks
important_instructions 16, direct 8, ignore_previous 4, tool_knowledge 2.

## Datasets and licence evidence

**BFCL v3 Live (AGT-1)** — Apache-2.0. Read: the dataset card
https://huggingface.co/datasets/gorilla-llm/Berkeley-Function-Calling-Leaderboard/blob/61fc0608cfd831fcfbbaa676ebdfef0ed963eeda/README.md
(`license: apache-2.0` in the YAML header; a copy is in `data/sources/bfcl/LICENSE-CARD.md`). Content: real user
requests sent to BFCL's hosted endpoint, cleaned by the authors (BFCL V2 blog); no other terms stated. Same
attribution as v3 TR-1.

**AgentDojo recorded runs (AGT-2)** — MIT. Read:
https://github.com/ethz-spylab/agentdojo/blob/089ed468cf3ed0322acc66b0211f26d9d90dbf60/LICENSE ("MIT License,
Copyright (c) 2024 Edoardo Debenedetti, Jie Zhang, …"). The repository (including `runs/`) carries that one
licence; task suites, injections and environments were written by the authors, people and companies are fictional,
agent turns are model output. Runs pinned at commit 089ed468 (main, 2026-06-02).

**τ-bench historical trajectories (AGT-3)** — MIT. Read:
https://github.com/sierra-research/tau-bench/blob/59a200c6d575d595120f1cb70fea53cef0632f6b/LICENSE ("MIT License,
Copyright (c) 2024 Sierra"). Policies, scenarios and databases are the authors' synthetic data; turns are model
output. Files pinned at commit 59a200c6 (main, 2026-03-18): `historical_trajectories/gpt-4o-airline.json` and
`gpt-4o-retail.json` (the Sonnet files, 11 and 27 MB, were not needed).

**HAGRID (AGT-5)** — Apache-2.0, Wikipedia passages CC BY-SA 3.0. Read:
https://github.com/project-miracl/hagrid/blob/7ffab03942e93d3138b0dbd14ad0a844f8a075d5/LICENSE (copy in
`data/sources/hagrid/LICENSE`); passage terms https://en.wikipedia.org/wiki/Wikipedia:Copyrights. Rows carry
CC BY-SA 3.0 and link the source articles, as in v3.

**MT-Bench human judgments (AGT-6)** — CC BY 4.0. Read:
https://huggingface.co/datasets/lmsys/mt_bench_human_judgments/blob/f7d2896d2cc5d80f8b55c2bbc722613555233c25/README.md
(`license: cc-by-4.0`; copy in `data/sources/mt-bench-human-judgments/README.md`); the questions are also in
FastChat under Apache-2.0 (LICENSE copy in the same folder).

**RouterBench (AGT-4) — dropped: no licence for the data could be established.** What I read:
- Hugging Face card https://huggingface.co/datasets/withmartian/routerbench (README at commit 78402148, 2024-03-27):
  no `license` field in the YAML and no licence text; the repository API's `cardData` has no licence either.
- GitHub https://github.com/withmartian/routerbench: the LICENSE file is MIT for the code (oddly copyrighted to
  "LangChain, Inc."); the README links the Hugging Face data as "example files" and says nothing about the data's
  licence.
- The paper (arXiv 2403.12031, abstract and HTML full text) and the Martian blog post
  (https://withmartian.com/post/introducing-routerbench) say "open source" / "code and data are available" and
  name no licence.
Two further obstacles even if a licence turned up: the data is three pandas pickles (the 0-shot file alone is
99.6 MB, above the ~50 MB guidance, and unpickling needs pandas, which the project does not depend on), and the
prompts include HellaSwag (WikiHow text, CC BY-NC-SA) and a news-based RAG set, which would have to be screened
out. If the maintainer obtains a licence statement from Martian, the tier design from the brief still works.

## What was dropped and why

**AGT-1.** v3's SKIP table is kept. Growing to 36 rows met three new records I passed over: `live_multiple_172-71-1`
and `live_multiple_205-90-7` (both about the named individual "Adriel", as v3 skipped `210-91-4`; the first is also
garbled) and `live_multiple_183-78-0` (three offered functions translate text and their names contradict their
descriptions, so the ground truth `finish` is not separable). Four new tool rows and one new `none` row got notes.

**AGT-2.** Candidate pool: 160 runs fixed by rule (first 40 per suite in sha256 order of the run path, among eight
undefended pipelines under four attacks at the pinned commit); the pool is written out in `AD_POOL` because the
repository tree is not fetched. Filters dropped runs with errors and runs whose injection never reached a tool
result the agent saw, leaving 81 candidates (22 hijacked). One hand skip: `command-r-plus/banking/u11/…/i0`, which
AgentDojo counts as hijacked because money reached the injected account, although the transactions carry the
user's own subjects rather than the requested "music streaming service" content. Per-pipeline cap 7 and per-suite
cap 8 were needed to reach 15 hijacked rows; no workspace-suite run in the pool was hijacked.

**AGT-3.** Written rules dropped, out of 660 gpt-4o runs: 168 whose task requires the agent to tell the user a value
(`outputs`; see judgement calls), 174 whose rendered state would exceed 15,000 characters, 60 reward-0 runs whose
successful database-writing calls match the expected actions by name (the failure is in the arguments — these are
the "coin-flips" the brief asked to count), and 57 reward-1 runs whose write calls differ from the expected list by
name. Hand skips (`TAU_SKIP`, 11): three where τ-bench's expected actions contradict the policy in the record
(airline task 47 twice and task 10: the record expects no cancellation of a business-class booking, which the
policy says can always be cancelled, or expects cancelling an uninsured economy booking, which it forbids), five
where the outcome is arguable (a downgrade that failed only for lack of seats, a booking the simulated user never
finishes, a certificate offered but never accepted, a transfer where declining was also allowed, a one-step update
that reaches the expected end state), one where the transcript never gets past a missing user id although the
record expects no change, and two repeats of the same failed-authentication scenario (Mei Kovacs). A write call
that returned an error is not counted as a write (rule), which removed a run whose only extra call had failed.

**AGT-5.** v3's HAGRID rules are kept and one rule was added: an unsupported sentence that is an invented
bibliographic reference line (GPT-3.5 sometimes appends "… Wikipedia, 2021. [2]") does not by itself make a row
not_supported, because a reader may not count it as a claim. Hand exclusions grew from 5 to 18; the 13 new ones
are all annotation slips or arguable labels found in review (for example "Tom Clancy's real name is Thomas Leo
Clancy Jr." labelled unsupported although the passage says exactly that; "reigned from 17 March 1861" labelled
supported although the passage has him King of Sardinia from 1849; a Brazil passage applied to the United States
labelled supported). Each is listed with its reason in `EXCLUDE`.

**AGT-6.** New written filters: both responses 300–3,000 characters, neither a refusal or AI-disclaimer (`BROKEN`).
The extraction category has no pair with both responses over 300 characters (its answers are short lists, JSON or
CSV), so it yields nothing and the task has six categories. Six new hand exclusions: two pairs where two judges
preferred the shorter Vicuna answer over a more detailed and at least as accurate GPT-4 answer (q159, q89), two
where both answers meet every requirement and only style differs (q110, q86), one where the preferred answer
breaks the "fewer than two paragraphs" constraint (q85), and one where both answers reach the same physics
conclusion and the winner's argument is wrong (q142). With one pair per question and the exclusions, 27 questions
remain eligible; 28 rows was reached by taking nine STEM questions. Model pairs shown as A/B are balanced by the
alternating rule from v3.

## Judgement calls for the maintainer

1. **AGT-3 state size.** The airline policy is 6,155 characters and the retail policy 5,718, so every row is over
   the 5,000-character median guidance (median 12,775, cap 15,000). Tool results are cut at 1,000 characters
   (search results lose most of their content; user, reservation and order records fit). Cutting the policy would
   mean writing a summary, which the contract forbids.
2. **AGT-3 label reliability.** The recorded reward is τ-bench's, but the gpt-4o files show two weaknesses: (a) for
   tasks with `outputs`, the reward is a substring check of a number and, in retail task 3 trial 1, is 1 although
   the agent modified a different order than the expected action — hence the rule dropping all `outputs` tasks;
   (b) some tasks' expected actions contradict the policy (airline 10, 47). Rows that survived were each read;
   the rationale states the expected and actual write calls from the record.
3. **AGT-3 shows the user simulator's scenario** (including hidden preferences such as "don't reveal your date of
   birth"), because without it a reader cannot know what the customer wanted. The note on each row says the user
   was simulated.
4. **AGT-2 pool composition** skews to Llama-3.3 and gpt-4o (the pipelines with the most attack variants) and to
   the slack and banking suites; hijacked rows come only from slack, banking and travel. Enlarging `AD_POOL` (a
   larger `AD_POOL_PER_SUITE`) would add manifest entries but give more variety.
5. **AGT-2 "direct" attacks** put the bare injected sentence into the environment (in one slack row it even appears
   as a channel name); the `injected_text` field shows what was injected so the reader can find it.
6. **AGT-5 noise.** HAGRID's sentence labels are noisier than v3's 14 rows suggested: 18 hand exclusions for 30 rows.
   Rows kept are ones where the passage plainly lacks or contradicts the claim.
7. **AGT-6 has 28 rows** (the brief's lower bound) and no extraction category; getting to 30 would need two pairs
   from one question or relaxing the 300-character floor for extraction.
8. **Manifest growth.** The module declares 205 source files (34 MT-Bench pages, 160 AgentDojo runs, 11 others);
   `--pin` will add about 165 entries.

## Summary

Five of the six requested tasks are built and pass the checks: 154 rows (36 + 30 + 30 + 30 + 28), every option
balanced, every row from a pinned public file under Apache-2.0, MIT or CC BY 4.0 (HAGRID rows CC BY-SA 3.0 for the
Wikipedia text). AGT-4 (RouterBench) was not built because no licence for the data could be found on the Hugging
Face card, the GitHub repository, the paper or the announcement. All sampling is by written rule in sha256 order;
every hand decision is in a SKIP/EXCLUDE table with its reason, and every row was read before its title and
rationale were written.
