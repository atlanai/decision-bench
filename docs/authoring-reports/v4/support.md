# support (SUP) — Decision Bench v4 module report

Module: `authoring/bench/support.py`. Data: `data/sources/cfpb/rows-*.json` (32 fixed 100-row pages of the CC0
Hugging Face mirror `BEE-spoke-data/consumer-finance-complaints`, config `has-text`). Both
`python3 scripts/fetch_sources.py --only support` (exit 0, no hash mismatch on the 16 already-pinned pages; 16 new
pages downloaded, not yet pinned) and `python3 scripts/build_bench.py --dry-run --only support` (`"problems": []`)
pass.

## Tasks built

### SUP-1 "Which team owns this complaint?" — 35 rows, 5 per team
Port of bench-v3 TR-3. The 28 v3 rows, titles and rationales are unchanged; SUP-1 deliberately reads only the 16
pages v3 read so its rank order (and therefore its rows) survive. One new row per team, read and annotated:

| team | new row | why it is that team |
| --- | --- | --- |
| credit_reporting | 7817733 | letters mailed to the credit bureaus about misleading information, no response |
| debt_collection | 1517103 | Focus Receivables keeps calling about a debt discharged in bankruptcy, voicemail only |
| mortgage | 2645305 | Ocwen took over the home loan, returned cashier's checks, demands $5,900, threatens foreclosure |
| credit_card | 7737249 | American Express added finance charge, late fee and trailing interest to a paid-in-full card |
| bank_account | 6729896 | closed Wells Fargo account with unexplained monthly and overdraft fees (a checking account) |
| student_loan | 4820759 | AES/PHEAA has not processed an employment certification form for loan forgiveness |
| money_transfer | 4512245 | PayPal closed the account for no reason and will not help |

Label balance: 5/5/5/5/5/5/5. Median state 819 chars, max 1,759. Label origin: self-declared (the consumer's
product choice). Three first-in-rank candidates were added to SUP1_SKIP (the v3 table is kept in full):
4840308 (four-sentence boilerplate demand, no story), 2951045 (asks for a discharged debt to be deleted from the
credit report, so credit reporting fits too — same reason as v3's 4762809 skip), 3009822 (names no product; it is
about retaliation for earlier complaints).

### SUP-2 "What is the complaint about?" — 32 rows, 4 per issue group
Eight groups mapped from the CFPB "Issue" field across its taxonomy changes (the mapping is `SUP2_GROUPS`):
incorrect_info_on_report, debt_not_owed, collector_conduct, trouble_during_payment, managing_an_account,
purchase_dispute, closing_an_account, struggling_to_pay. Balance 4×8. Median state 1,042 chars, max 1,642. Label
origin: self-declared (the consumer's issue choice). No narrative is shared with SUP-1 (checked: overlap 0).

Written rules: 250–1,800 chars, prepaid sub-products excluded, SUP-1 narratives excluded, and a regex
(`SUP2_TEMPLATE`) drops template letters with no story ("penalty of perjury", "15 U.S.C", "This is my Nth request",
"in accordance with the Fair Credit Reporting Act", "NOTICE OF PENDING LITIGATION"). 24 hand skips in `SUP2_SKIP`,
each with the reason; the dominant reason is that a second offered option is arguable from the record (e.g. a
"debt not owed" narrative that also asks for the item to be deleted from the credit report, a "closing" narrative
that is mostly about fees on an idle account, a "struggling to pay" narrative that is really about a collector
calling a co-worker). Three were skipped because no offered option fits (a safe-deposit box, a servicer damaging a
late father's home, a reconveyance request), two because the narrative is garbled.

Groups considered and not used: "Improper use of your report" and the "investigation" issues (too confusable with
incorrect information: the consumer picks between them arbitrarily); "Fraud or scam" (money-transfer product only,
pool of 19, and confusable with an unauthorised card charge under purchase_dispute); "Getting a credit card /
Applying for a mortgage" (would have made nine groups; the brief asked for 6–8).

## Dropped: SUP-3 "How was it resolved?"
The CFPB "Company response to consumer" field. I built the candidate pool (narratives that ask for something,
by a request-word regex: 1,423 rows; only 41 monetary relief) and did a blind read of 24 narratives (8 per class,
shuffled, key hidden). I called 16/24 (chance 8/24). There is signal — a missing ATM deposit, a misdirected refund
check and a prepaid-card balance were monetary; identity-theft letters to bureaus were mostly non-monetary — but the
misses are indefensible from the record alone, which fails the contract's "exactly one defensible answer":

- 7867966: a denied auto-loan pre-approval with no money at stake — "Closed with monetary relief".
- 3939005: a four-line question about how to remove PMI — "Closed with monetary relief".
- 3102297: robo-calls about a paid Sears card — "Closed with monetary relief".
- 2755469: creditor confirmed fraud in writing and told the bureaus to remove the item; the consumer asks for the
  correction — "Closed with explanation".
- 5344860 / 7430574 (TransUnion, Equifax: "non-monetary relief") vs 7575929 / 5606763 (Experian: "explanation"):
  near-identical identity-theft or FCRA template letters get different outcomes depending on the bureau. The
  outcome is a fact about the company's practice, not about the complaint.

Also structural: monetary relief is 3% of the pool, so a balanced 30-row task would misrepresent the base rate, and
the majority class ("explanation", 75%) is the company declining, which cannot be read off a one-sided narrative.
Not built.

## Not built: SUP-4 (additional real support-conversation dataset)
Searched Hugging Face ("customer support", "nhtsa") and probed two live sources. Nothing met the licence bar:

- Hugging Face customer-support datasets are synthetic (Bitext, CDLA-Sharing-1.0, not in PERMISSIVE), NC
  (Tobi-Bueck cc-by-nc-4.0; Twitter TWCS mirrors cc-by-nc-sa-4.0), or unlicensed.
- Mozilla SUMO support questions (CC BY-SA 3.0 site content) — the API `support.mozilla.org/api/2/question/` is
  behind a JavaScript client challenge; not fetchable by the fetch script, and I did not try to bypass it.
- NHTSA ODI vehicle complaints — real consumer complaints with a component label, a natural "which team owns it"
  task. The public API (`api.nhtsa.gov/complaints/complaintsByVehicle`) works and NHTSA data is US-government;
  `emperor-mew/nhtsa-complaints` on HF is marked CC0 but is filtered to crash/injury/fire/death complaints (grim
  for a public bench), and `claritystorm/nhtsa-vehicle-complaints` is "license: other / public-domain" with only a
  1,000-row sample. I could not fetch a NHTSA statement about the consumer-written narrative text equivalent to the
  CFPB's consent-and-public-domain statement, so under rule 2 ("if you cannot establish both, do not build") I
  left it. A maintainer with the NHTSA complaint-form notice in hand could revisit; the API also drifts (new
  complaints arrive even for 2012 model years), so pinned windows would need old model years.

## Licence evidence (URLs read)
- Mirror card, CC0-1.0 in YAML header: https://huggingface.co/datasets/BEE-spoke-data/consumer-finance-complaints/blob/088cc7308d4afc2a880f2329d08e2f7a09188ec6/README.md
  (committed copy: `data/sources/cfpb/LICENSE-CARD.md`).
- CFPB: "Information created by the CFPB is in the public domain" — https://www.consumerfinance.gov/privacy/website-privacy-policy/
- CFPB 14 Aug 2026 notice that it "considers previously published narratives to be in the public domain for FOIA
  purposes" — https://www.consumerfinance.gov/about-us/newsroom/the-cfpb-to-cease-discretionary-publication-of-complaint-narratives-and-visualizations/
- Every row in the 32 pages has "Consumer consent provided?" = "Consent provided" (checked programmatically).
These are the same three sources v3 relied on; nothing new was asserted.

## Judgement calls for a maintainer
1. SUP-1 reads the original 16 pages only, so the v3 rows survive; SUP-2 reads all 32. Both windows are fixed and
   written down. If you would rather SUP-1 use all 32 pages, its rows (and notes) would change.
2. SUP-2 states carry only the narrative and date, not the CFPB product; the instruction says to pick the issue,
   not the product. Some rows lean on knowing that overdraft fees mean a bank account or that escrow means a
   mortgage payment; a smart generalist knows this.
3. Two SUP-1 rows are thin but decidable: 6729896 (three sentences, the account type is only implied by overdraft
   and monthly fees) and 4820759 (an "employment certification form" for loan forgiveness — PSLF — is the only
   clue that it is a student loan). Kept because rank order reached them and a second team is not arguable.
4. Two SUP-2 rows mention a collector being rude or calling in passing but complain about the debt itself
   (2740207, 4402032); a similar row where "continue to call and harass" was a stand-alone complaint (3033538) was
   skipped. The line is drawn at whether the conduct is itself a complaint.
5. 2645305 (SUP-1 mortgage) describes a disabled great-grandchild in the home (scrubbed to XXXX). It is the
   consumer's consented, published text; flagging in case you prefer to skip it as personal.
6. The 16 new CFPB pages are not pinned in `data/sources/manifest.json` (I did not run `--pin`).
