# Legal category (authoring/bench/legal.py) — report

Module: `authoring/bench/legal.py` (category `legal`, tasks LEG-1…LEG-4). New source folders:
`data/sources/cuad/` (test.json + LICENSE-CARD.md + LICENSE-README.txt) and `data/sources/lexglue-unfair-tos/`
(17 datasets-server windows + LICENSE-CARD.md). `data/sources/contractnli/` reused as is.

`python3 scripts/fetch_sources.py --only legal` → all 19 files present.
`python3 scripts/build_bench.py --dry-run --only legal` → 126 rows, `"problems": []`.

## Tasks built

| Task | Name | Rows | Balance | State size (median / max chars) |
| --- | --- | --- | --- | --- |
| LEG-1 | Does the NDA say this? | 33 | yes 11 · says_opposite 11 · not_addressed 11 (abstain = not_addressed) | 6,582 / 9,989 |
| LEG-2 | What kind of clause is this? | 30 | 5 each: governing_law, cap_on_liability, anti_assignment, license_grant, non_compete, termination_for_convenience | 932 / 1,586 |
| LEG-3 | Is this term unfair, and how? | 33 | not_unfair 9 · 3 each of the eight UNFAIR-ToS types | 598 / 1,159 |
| LEG-4 | Does the contract cover this? | 30 | yes 15 · no 15; per type (yes/no): governing law 3/2, cap on liability 2/3, anti-assignment 2/3, license grant 3/2, non-compete 2/3, termination for convenience 3/2 | 3,795 / 4,859 |

LEG-1 is over the 5,000-character median (it shows whole NDAs of ≤10,000 characters, as v3 did, because a
"not addressed" answer has to be checkable against the entire document). Everything else is under.

### LEG-1 — ContractNLI, port of v3 CP-1
Same EXCLUDE table, consent-gating rule (nda-7/nda-17 contradictions whose evidence mentions consent), copyright-
notice rule, e-mail/phone scrubbing and one-row-per-agreement / ≤2-per-hypothesis rules. PER_LABEL 10 → 11, so 33
rows; 17 hypotheses all present (16 twice, nda-5 once). Four newly sampled agreements got neutral names (51, 57 → later
excluded, 77, 190, 455). Task metadata: shape verify, expertise none, contamination high, label_origin
"trained annotators" (ContractNLI's annotators were trained non-lawyers; v3 said the same).

### LEG-2 — CUAD clause type
Six CUAD categories with the dataset's own "Details" definitions shown in the rationale. Rules: span of 120–1,600
characters; the span plus its context window must not touch a span of another of the six types in the same contract;
spans ending in ":" (lead-ins) or containing redaction markers (`[**]`, `{***}`, `***`) are skipped; one row per
contract; scarcest type filled first; sha256 order. Context = one sentence before/after (≤350 characters each).
Label origin "human experts" (Atticus reviewers: law students under attorney supervision).

### LEG-3 — UNFAIR-ToS (LexGLUE)
The 1,607 test sentences are ten ToS documents in order; I verified the boundaries sentence by sentence against
the original CLAUDETTE `ToS.zip` (Sentences/*.txt), so neighbours come from the same document only (TOS_DOCUMENTS
table). Rules: 60–600 characters; exactly one tag (14 multi-tag sentences skipped); untagged sentences qualify as
"not unfair" only if they contain none of the cue words of the eight types (FAIR_SCREEN), so a "not unfair" row is
never a near miss; ≤5 rows per document (actual: 1–5). Text is shown lower-cased as LexGLUE has it, with the PTB
tokenisation undone (quotes, spaces before punctuation). Arbitration and content removal have only 7 single-tag
test sentences each, hence 3 per type. Label origin "human experts" (CLAUDETTE's legal annotators).

### LEG-4 — CUAD yes/no coverage (built; negatives are defensible in my judgement)
"Yes" = a 2,000–5,000 character window snapped to line/sentence boundaries containing one whole reviewer span of
the type (same colon/redaction span rules as LEG-2). "No" = a window from a contract whose reviewers marked the type
`is_impossible`, which must (a) match nothing in a per-type ABSENCE_SCREEN regex (e.g. for anti-assignment:
assign / transfer-or-pledge-with-consent / "successors and assigns"; for license grant: licen[sc]e, right to use,
use of the marks/software/…), (b) be running prose: ≥62% letters, ≥5 sentences of 80+ characters, at most one
signature-line marker, no notice-address block (Attn/Fax/Esq/zip code). The task instruction tells the model that on
"no" rows the experts found no such clause anywhere in the whole contract. Contracts used by LEG-2 are not reused;
one row per contract. Each "no" rationale names the screen that passed. I read all 15 negative excerpts in full.

## Licence evidence

**ContractNLI** — CC BY 4.0. LICENSE and TERMS inside the dataset zip
(https://stanfordnlp.github.io/contract-nli/resources/contract-nli.zip; saved at data/sources/contractnli/LICENSE,
LICENSE-TERMS). TERMS: use "in accordance with the terms and conditions of the Creative Commons Attribution 4.0
International Public License". Content: SEC EDGAR exhibits ("Information presented on sec.gov is considered public
information and may be copied or further distributed by users of the web site without the SEC's permission",
https://www.sec.gov/privacy) and web-posted NDA templates; agreements with a copyright notice are excluded (rule).

**CUAD** — CC BY 4.0. Hugging Face card https://huggingface.co/datasets/theatticusproject/cuad (`license: cc-by-4.0`,
saved as data/sources/cuad/LICENSE-CARD.md); Atticus project page https://www.atticusprojectai.org/cuad states
"CC BY 4.0" in its header and that contracts were "manually labeled under the supervision of experienced lawyers";
CUAD_v1_README.txt (datasheet) saved as LICENSE-README.txt. Content: contracts are EDGAR exhibits (file names carry
the form type and filing date; SEC terms as above). Source file: `data.zip` → `test.json` from the CUAD GitHub repo,
pinned to commit 7aad649183846688381a147eeb3601aff590fe4a (the repo moved to The-Atticus-Project/cuad; the
TheAtticusProject URL redirects and fetches fine, 18.3 MB).

**UNFAIR-ToS via LexGLUE** — CC BY 4.0 per the dataset card metadata of https://huggingface.co/datasets/coastalcph/lex_glue
(`license: cc-by-4.0`, saved as data/sources/lexglue-unfair-tos/LICENSE-CARD.md). Caveats a maintainer should know:
the card's "Licensing Information" section itself says "More Information Needed", and the original CLAUDETTE corpus
page (https://claudette.eui.eu/corpora/) lists the 50-document ToS corpus without any licence statement. The
underlying text is sentences from ten companies' public terms of service (2017–18); each row shows at most three
consecutive sentences. I recorded `content_license="CC-BY-4.0"` on the strength of the LexGLUE release, as v3 did for
ContractNLI's unlicensed web templates, and flagged it here. If the maintainer wants a stricter reading, LEG-3 is
the task to drop.

## Dropped / not built
- **CaseHOLD**: not built, as instructed.
- **LEG-2 hand skips (CLAUSE_SKIP)**: contract 20 (span is the tail of a page-broken sentence); contract 45 (both
  spans are termination mechanics, the without-cause words are elsewhere); contract 40 (a no-transfer-of-technology
  covenant tagged Non-Compete; anti_assignment is arguable).
- **LEG-4 hand skip (COVERAGE_SKIP)**: contract 45 / termination for convenience (CUAD's span is an automatic
  termination when shares are not sold).
- **CUAD contract 35** excluded from both tasks by a written OCR rule (glued function words such as "ofthis",
  "ofDefault": 12.9 per 1,000 words vs 0.24 for the next-worst contract).
- **LEG-1 new exclusion**: (57, nda-5) PwC Annex III NDA, labelled NotMentioned, but clause 2.1(c) bars disclosure
  "to anyone else" with no employee carve-out — same reasoning as the existing exclusions for docs 83 and 452.
- UNFAIR-ToS multi-tag sentences (14) skipped by rule; Governing Law negatives limited to 2 because only 19 test
  contracts lack one and several are signature-page joint filing agreements.

## Judgement calls for review
1. LEG-4 "no" excerpts rely on CUAD's `is_impossible` for the whole contract plus my cue screens; CUAD's own recall
   is not perfect. Two rows I would watch: `leg-4-cuad-17-license-grant` (a water-rights cooperation agreement
   that grants rights to develop wells — no licence wording, but a lawyer might call some of it a licence) and
   `leg-4-cuad-86-cap-on-liability` (an equity sponsors' agreement titled "Sponsorship Agreement").
2. LEG-2 keeps a few spans that are decidable only by elimination among the six options: `leg-2-cuad-3` (a right
   to terminate a lease term on 60 days' notice, tagged Termination For Convenience), `leg-2-cuad-16` (a
   restriction on the licensed mark, tagged License Grant), `leg-2-cuad-91` (customer non-solicit tagged Non-Compete).
3. LEG-3 `leg-3-unfair-tos-test-759` ("we have the right to limit how you connect and interact") is tagged
   Unilateral change by the annotators; defensible but the weakest label in the set.
4. Titles for CUAD rows are derived from the file name's agreement type and filing date (counterparties and any
   individuals' names after " - " or "between" are dropped); LEG-4 titles end with the clause type as a question,
   which does not reveal yes/no.
5. Personal data: e-mails and phone/fax numbers are scrubbed everywhere (3 LEG-1 and 1 LEG-4 rows contain
   placeholders). Signature blocks and notice-address blocks are excluded from LEG-4 negatives by rule; names of
   signing organisations, and of public-figure endorsers who are parties (e.g. an athlete in an endorsement
   agreement), remain as filed with the SEC.
6. `LEG-1` label_origin is "trained annotators" (ContractNLI), the others "human experts".
