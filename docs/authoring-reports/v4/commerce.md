# Commerce module report (authoring/bench/commerce.py)

Status: `python3 scripts/fetch_sources.py --only commerce` reports 158 files present; `python3 scripts/build_bench.py
--dry-run --only commerce` ends with `"problems": []`. 90 rows, all real records. Nothing under data/sources was pinned.

## Tasks built

| Task | Name | Rows | Answers | Source | Label origin |
| --- | --- | --- | --- | --- | --- |
| COM-1 | Does this product match the query? | 30 | exact 8, substitute 8, complement 7, irrelevant 7 | Amazon Shopping Queries Dataset (ESCI), via the Hugging Face mirror tasksource/esci | trained annotators |
| COM-2 | What type of product is this? | 30 | chair 4, sofa 4, table 4, rug 4, lamp 4, wall_art 4, shoes 3, grocery 3 | Amazon Berkeley Objects listings shard listings_0.json.gz | self-declared (seller's product_type) |
| COM-3 | Which industry is this company in? | 30 | manufacturing 6, finance 6, services 6, transport/comms/utilities 4, mining 4, retail 3, wholesale 1 | EDGAR-CORPUS year_2020 (mirror c3po-ai/edgar-corpus) joined to data.sec.gov submissions | objective record (SIC code) |

Median state sizes: COM-1 1,349 chars, COM-2 853, COM-3 2,178 (max 2,287).

### COM-1 details
- 27 fixed 100-row pages of tasksource/esci train (offsets 20,000 + 66,000·k, k < 27; pages beyond are es/jp). 2,175 US-locale
  rows, 3,000 rows total, 7.9 MB.
- Rules: US locale, non-empty title without CJK characters, ASCII query of at most 100 characters, no adult words in the query,
  example_id unique in the pages (the mirror joins products by id without locale, so 46 example_ids appear 2–3 times with
  Japanese/Spanish product text), one row per query_id, fixed per-label quotas, rank() order of example_id.
- Titles are `Search result · “<query>”`: the shopper's own words, which never carry the label. Rationales are hand-written.
- 19 hand-skips in COM1_SKIP, each with the reason. Patterns worth knowing: ESCI labels are noisy at the exact/substitute
  boundary and complement is often misapplied (a fuel-line kit that includes a fuel filter labelled complement; Echo Auto
  labelled complement for "car electronics"; a set of two candle holders labelled complement for "3 candle holder").
  Two rows were dropped for language (a German-edition book; a Spanish query in the US locale).

### COM-2 details
- One ABO listings shard (5.4 MB; 9,232 listings, 1,544 for the US marketplace with an en_US name). Eight product types
  chosen so that each is separable from the others; PILLOW, OTTOMAN, STOOL_SEATING, LIGHT_FIXTURE, HOME and BED were not
  offered because ABO sellers use them inconsistently (a "Pillow Sofa" filed as PILLOW; patio cushions as PILLOW).
- Shown fields: name, brand, bullet points, description, colour, material, style, pattern, shape, fabric/finish type, model
  fields, dimensions, weight. Removed: product_type and browse node (the answer), hidden search keywords (not customer-facing
  and often listing other product types), image/spin/3D identifiers, marketplace and country.
- Fabric swatches and listings with no bullet point or description are excluded by rule. Two hand-skips: a bath bomb filed
  as GROCERY and a "Garden Stool or Side Table" filed as TABLE.
- Text only. A text+image variant is feasible: `images/metadata/images.csv.gz` (6.4 MB) maps main_image_id to a path under
  `images/small/` and individual small JPEGs are fetchable from S3 (the sample checked was 1.5 KB). I did not build it because
  the instructions limited me to data/sources, and assets would have to be committed under data/assets/commerce.
- The title is `Amazon listing · item <ASIN>` by rule; brand names were avoided in titles because Amazon private-label brands
  hint at the vertical (Rivet = furniture, Happy Belly = grocery).

### COM-3 details
- 14 fixed 10-row pages of c3po-ai/edgar-corpus config year_2020 (offsets 0, 400, …, 5200; 140 filings, 42 MB, each row is a
  whole 10-K so pages must be small). 116 filings have an Item 1 of at least 6,000 characters; the SEC submissions record of
  every one of them is declared in SOURCES (COM3_CIKS, 116 files, 13.9 MB) so the SIC lookup is complete and pinnable.
- SIC divisions by code range; agriculture (0100–0999), construction (1500–1799), public administration and 9995 are dropped by
  rule (two construction filers fell out this way). At most one blank-check company (SIC 6770).
- Only one wholesaler (Houston Wire & Cable, SIC 5063) exists among the 116 candidates, so the wholesale quota is 1 and retail 3.
- Shown text: first 2,000 characters of Item 1 with the filer's current and former names (from the submissions record)
  replaced by "[the Company]" case-insensitively, plus per-row aliases (short names, tickers, websites) matched case-sensitively.
  I read all 30 excerpts; subsidiary names and executives named in the filing remain (they are public record).
- Judgement call for a maintainer: the SIC is the one EDGAR records today, not as of 2020. Where the 2020 business no longer
  matches (Red Cat, AYRO/Fabric.AI, NextTrip/Sigma Labs, Transact Energy, DSS) the filing was skipped by hand. Clinical-stage
  biotechs with no marketed product were also skipped because the SEC files them under 2834/2836 (manufacturing) or 8731
  (research services) inconsistently; the two pharma rows kept (Yarrow/VYNE and GW Pharmaceuticals) had approved products
  on the market. 16 hand-skips in COM3_SKIP with reasons; 19 filers have redaction aliases in COM3_ALIASES.
- Expertise is marked "practitioner": the option texts and instruction spell out the SIC conventions a generalist would not
  know (restaurants are retail; REITs and blank checks are finance; streaming is communications).

## Licence evidence read

- ESCI: https://github.com/amazon-science/esci-data/blob/main/LICENSE (Apache License 2.0; README: "This project is licensed
  under the Apache-2.0 License"). Mirror card https://huggingface.co/datasets/tasksource/esci declares apache-2.0. Labels:
  the paper (arXiv:2206.06588, section 2) says each pair "was manually annotated with E/S/C/I labels by humans trained on the
  task", "a minimum of three annotations were collected for each pair", majority vote, 91% agreement on an audit sample.
  The product texts are Amazon catalogue listings released by Amazon in the dataset under the same licence.
- ABO: https://amazon-berkeley-objects.s3.amazonaws.com/index.html ("A CC BY 4.0-licensed dataset of Amazon products with
  metadata, catalog images, and 3D models") and https://amazon-berkeley-objects.s3.amazonaws.com/LICENSE-CC-BY-4.0.txt.
- EDGAR-CORPUS: https://huggingface.co/datasets/eloukas/edgar-corpus (apache-2.0; "EDGAR data is publicly available") and the
  parquet mirror https://huggingface.co/datasets/c3po-ai/edgar-corpus (apache-2.0). The filings themselves are SEC public
  records; SEC states its web content is public domain (https://www.sec.gov/privacy#dissemination). SIC codes from
  https://data.sec.gov/submissions/CIK##########.json (SEC open data API; the fetch script's fixed User-Agent was accepted).

## Dropped

- COM-4 (WDC Product Data Corpus / WDC Products): dropped. https://webdatacommons.org/structureddata/ says "We publish the
  corpora for research purposes only" and only the extraction framework is Apache-licensed; the LSPC v2 and WDC Products pages
  state no licence at all. The product texts are copied from retailers' pages in Common Crawl, whose terms do not grant
  redistribution rights to page content. Neither the dataset nor its contents meets the open-licence policy.
- Original eloukas/edgar-corpus files: not used directly because the smallest per-year file is 45 MB (1993) and 2020 is
  1.5 GB; the rows API refuses the dataset (script-based). The c3po-ai parquet mirror serves fixed windows instead.
- The datasets-server `/filter` endpoint rejects `length()` clauses (HTTP 422), so COM-3 pages are plain fixed windows.

## B2B sales-conversation data

There is no open-licence corpus of real B2B sales conversations. What exists: CallCenterEN (91k real call-centre
transcripts) and EndgameLabs/SalesTranscriptQA are CC BY-NC 4.0; gwenshap/sales-transcripts, DeepMostInnovations/
saas-sales-conversations and goendalf666/sales-conversations are synthetic or simulated; MarketCalls v1.0 (CC BY 4.0) is
earnings-call transcripts, not sales. A "sales & commerce" category therefore has to lean on search relevance, catalogue
data and public company profiles, as this module does.

## Notes for the maintainer

- Hugging Face datasets-server rate-limits bursts (429). I pre-downloaded the windows with pauses under the script's exact URLs
  and paths; `fetch_sources.py` then reports them present. If a fresh clone hits 429s with `--jobs 8`, rerunning picks up
  where it stopped.
- Another module has a `data/sources/edgar-corpus/` folder (year_2015 windows). Mine is `edgar-corpus-2020/` with dataset id
  `edgar-corpus-10k-business`, so ids do not collide.
- COM-1 contamination is marked "medium" (ESCI is a well-known KDD Cup dataset, but per-pair labels are unlikely to be
  memorised); COM-2 "low"; COM-3 "medium" (the filings are surely in training data; the label join is fresh, but a model may
  recognise the company from subsidiaries or products even with the name removed).
