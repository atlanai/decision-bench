# Finance module (authoring/bench/finance.py) — report

Both checks pass: `python3 scripts/fetch_sources.py --only finance` (all 217 declared files present, no hash
mismatches; the manifest is not pinned) and `python3 scripts/build_bench.py --dry-run --only finance` ends with
`"problems": []`. 121 rows in four tasks. Files created: `authoring/bench/finance.py`, `data/assets/finance/`
(30 JPEGs, 5.3 MB), `data/sources/{edgar-corpus,edgar-8k,cord-v2,finer-139}/` (downloads, 21 MB, plus a
`LICENSE-CARD.md` in each). Nothing else was touched and nothing was committed.

## Tasks built

| Task | Rows | Answer balance | Source | Label origin |
| --- | --- | --- | --- | --- |
| FIN-1 Which part of the 10-K? | 30 | 6 × business, risk_factors, legal_proceedings, mdna, controls | EDGAR-CORPUS (2015–2020 test splits, one filing per CIK) | objective record (the filing's item heading, as split by the corpus) |
| FIN-2 What does this 8-K report? | 30 | 6 × results, officer_change, agreement, other, shareholder_vote | SEC EDGAR 8-Ks filed 4–8 March 2024 | objective record (EDGAR's item list for the filing) |
| FIN-3 Which figure is the total? (image) | 30 | per-row options (4–5 printed figures), gold = total.total_price | CORD-v2 test split | trained annotators |
| FIN-5 What does this number report? | 31 | borrowings 6, goodwill 6, share_based_compensation 6, revenue 5, income_tax_expense 4, amortization 4 | FiNER-139 test split rows 0–11,999 | self-declared (the filer's XBRL tag) |

State sizes: FIN-1 median 1,643 chars (max 2,265); FIN-2 median 1,495 (max 5,013, no truncation needed);
FIN-3 median 462; FIN-5 median 472.

## Dropped

**FIN-4 "Which value answers the question?" (TAT-QA) — dropped on licence.** The dataset itself is CC BY 4.0
(README, github.com/NExTplusplus/TAT-QA) and the code is MIT (LICENSE file, Fengbin Zhu 2021). But the paper
(Zhu et al., ACL 2021, §2.1, read via ar5iv.labs.arxiv.org/html/2105.07624) says the hybrid contexts were taken from
"about 500 financial reports released in the past two years" downloaded from https://www.annualreports.com/, of
which 182 reports were kept. Those are the companies' own annual reports (glossy reports, many non-US), not SEC
filings, and neither the README nor the paper states any licence for redistributing their text. The two-part test
in the contract (dataset licence and content terms) fails on the second part.

## Licence evidence (URLs actually read)

- **EDGAR-CORPUS** — https://huggingface.co/datasets/eloukas/edgar-corpus (card metadata `license: apache-2.0`;
  "EDGAR data is publicly available"), pinned revision 7e90f0f342569b35213445f809cfaf3b91f9964f. Rows were read from
  the Parquet duplicate https://huggingface.co/datasets/c3po-ai/edgar-corpus (revision 5b6b1526…, page marked
  "Duplicated from eloukas/edgar-corpus", same apache-2.0 card) because the original is a loading-script dataset
  whose per-year files are 180 MB–1.4 GB and are not served by the rows API. Content: 10-K filings, US public
  records; SEC website policy "Website Dissemination" (https://www.sec.gov/privacy): "Information presented on sec.gov
  is considered public information and may be copied or further distributed by users of the web site without the
  SEC's permission." Declared `content_license="Public domain"`.
- **SEC EDGAR 8-K filings** — fetched from https://www.sec.gov/Archives/edgar/data/<cik>/<accession>/<doc> after
  EDGAR full-text search (efts.sec.gov); same SEC dissemination policy as above. `license="Public domain"`.
- **CORD-v2** — https://huggingface.co/datasets/naver-clova-ix/cord-v2 (card metadata `license: cc-by-4.0`, revision
  7f0115a4…); repository README https://github.com/clovaai/cord: "This work is licensed under a Creative Commons
  Attribution 4.0 International License"; the receipts are "thousands of Indonesian receipts" from shops and
  restaurants, released with the annotations by Clova AI. Store names, addresses and card details on the photos are
  already blurred by the dataset (checked on the selected images). `license = content_license = CC-BY-4.0`.
- **FiNER-139** — https://huggingface.co/datasets/nlpaueb/finer-139 (card metadata `license: cc-by-sa-4.0`, revision
  080f677a…); sentences from ~10k SEC 10-K/10-Q filings 2016–2020 (public records, SEC policy above). Rows carry
  CC-BY-SA-4.0; `content_license="Public domain"`.

## What was dropped by hand (SKIP tables in the module)

- FIN-1 `FIN1_SKIP`: Aldeyra Therapeutics 2019, MD&A passage — it recites licence-fee and royalty terms of an
  agreement and reads like the Business section; the filer was reassigned to Controls by the written rule.
- FIN-2 `FIN2_SKIP` (4 of the 45 downloaded filings): Blackbaud (Item 8.01 body is the company entering an
  accelerated share repurchase agreement — arguably "material agreement"); Core Scientific (Item 7.01 press release
  announces a hosting agreement — arguably "material agreement"); CenterPoint Energy (Item 7.01 furnishes a
  subsidiary's audited financial statements — arguably "results"); Panacea Life Sciences (body mixes a 2022
  agreement, a 2023 payoff and a 2024 conversion; unclear what is being reported).
- FIN-3 `FIN3_SKIP`: none needed.
- FIN-5 `FIN5_SKIP` (9 ids): a standby letter of credit tagged LineOfCredit (not plainly a borrowing); two
  sentences carrying table-caption/statement-header fragments; three of four near-identical Heartland "net of
  taxes of $X" sentences (kept one, plus other filers); two "payment from Total in the amount of $X" sentences and
  one "deferred revenue balance" sentence tagged as revenue, which the sentence itself does not support.

## Judgement calls for the maintainer

1. **FIN-1 mirror.** Rows come from c3po-ai/edgar-corpus, a Parquet duplicate, not eloukas/edgar-corpus itself.
   The dataset is declared as EDGAR-CORPUS with the mirror named in `content`, `license_url` pointing at the
   original card, and the mirror revision recorded. Same pattern as v3's CFPB mirror.
2. **FIN-1 passage position.** Passages start at the paragraph containing the 30% point of the section (not the
   opening), so they are specific content (a particular risk factor, a results comparison, a lawsuit) rather than
   boilerplate openers. Item 3 and 9A are short, so their passages often are the whole body. Cross-references to
   *other* items ("see Item 7") are left in; a passage that names its own item or title is rejected.
3. **FIN-1 filer names / SIC** come from data.sec.gov/submissions (looked up once on 2026-09-23 and hard-coded in
   `FIN1_FILERS`), because the corpus carries only the CIK. Titles are "10-K passage · <filer>".
4. **FIN-2 redaction.** Beyond removing the heading line and official item title (as asked), in-body references
   such as "furnished pursuant to Item 2.02" are shown as "Item [number removed]" (12 rows affected), the Item 9.01
   exhibit list and Item 2.03 "incorporated by reference" cross-references are dropped, and only the sections of
   the reported item are shown. Declared in `changes`. Without this the results rows would be answerable from the
   item number alone. Option descriptions still name the item numbers.
5. **FIN-2 candidate discovery** was done once with EDGAR full-text search (one week, one query per item number);
   the 45 hits kept are hard-coded in `EIGHT_K` with their EDGAR item lists, and the module asserts that the
   parsed "Item X.XX" headings agree with EDGAR's list. Results (2.02) rows are near-boilerplate and easy; agreement
   rows admit {1.01, 2.03} because loan agreements always carry 2.03.
6. **FIN-3 options are the printed strings** ("174,600", "51.300", "365000.00") including the receipt's own
   thousands separator; a figure printed in two formats is keyed by its first printed form. Photos under 800 px on
   the longest side were excluded as illegible (five candidates), images are never upscaled, and figures under 100
   (rounding lines, zeros) are never distractors. The OCR text in the state is CORD's annotated words only (menu,
   subtotal and total blocks); store headers are not annotated, and the state says so.
7. **FIN-5 option set differs from the brief.** FiNER-139 has no tags for net income, total assets or cash, and
   shares-outstanding sentences carry two numbers, so the five requested concepts could not be built. The six
   groups used are plain, separable concepts with enough single-amount "$" sentences in 12,000 test rows: borrowings
   (DebtInstrumentFaceAmount + LongTermDebt + LineOfCredit + DebtInstrumentCarryingAmount, merged because filers
   use them interchangeably), goodwill, share-based compensation (two elements), revenue (three elements), income
   tax expense, amortization of intangibles. Interest expense had only two clean sentences and was left out. Two
   groups have 4 rows and one has 5; total 31. If the maintainer prefers exactly 30, drop one goodwill row.
8. **FIN-5 tag quality is self-declared.** A few kept sentences carry a caption fragment before the amount
   (FiNER's own sentence splitting) and the "income tax" rows include "net of taxes of $X" adjustments, which are
   tagged IncomeTaxExpenseBenefit by the filer; they are defensible against the other five options but a
   practitioner might quibble with the filer's tagging.
9. **Hugging Face rate limits.** The rows API returned 429/5xx frequently; the 172 windows were downloaded
   sequentially with back-off (scratch script, not in the repo). `fetch_sources.py` downloads in 8 parallel threads
   and may hit the same limits on a fresh clone; re-running it is enough, as it skips files already present.
10. **CORD images** came from the rows API's signed, expiring image URLs, so they cannot be declared in `SOURCES`;
    they were fetched once and resized with macOS `sips` by `prepare_fin3_assets()` (a hand-run helper in the
    module). The committed JPEGs are the record; the JSON windows with the ground truth are in `SOURCES`.
11. **8-K officer-change rows name real directors and officers** (public filings about public-company officers);
    receipts show no personal data.
