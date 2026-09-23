# Decision Bench v4 · category "data" · authoring report

Module: `authoring/bench/data.py`. Assets: `data/assets/data/` (16 PNGs, 932 KB total, each 850×600 and 41–76 KB).
`python3 scripts/fetch_sources.py --only data` fetches 148 files (all present); `python3 scripts/build_bench.py
--dry-run --only data` ends with `"problems": []`. 126 rows.

## Tasks built

| Task | Name | Rows | Answer balance | State size (median / max chars) |
| --- | --- | --- | --- | --- |
| DAT-1 | Which SQL answers the question? | 30 | q1 5, q2 6, q3 9, q4 10 (per-row labels) | 1,062 / 1,817 |
| DAT-2 | Which cell answers the question? | 30 | cell_1 11, cell_2 5, cell_3 6, cell_4 8 (per-row labels) | 1,213 / 11,484 |
| DAT-3 | Does the chart support the claim? | 32 | supported 16, not_supported 16 | 820 / 1,446 (+ image) |
| DAT-4 | What does this column hold? | 34 | category 6, count_or_measurement 7, geography 5, money 5, date 4, identifier 4, free_text 3 | 573 / 7,310 |

DAT-5 was not built (see "Dropped").

### DAT-1 · Spider dev set
- Source: `taoyds/spider` at commit `b7b5b8c` (2024-05-29), files `evaluation_examples/examples/dev.json` (1,034
  records, includes Spider's parsed `sql`) and `tables.json`.
- Row: compact schema (`table(col*, …)` with primary keys starred and foreign keys listed), the question, and four of
  Spider's own gold queries for that database labelled q1–q4 in hash order. Rationale names the gold and quotes the
  three other questions whose gold queries the distractors are.
- Rules: rank order over dev index; databases with 3–8 tables; query ≤ 220 chars, question ≤ 160; one row per distinct
  query structure (so Spider's paraphrase pairs do not produce two rows); ≤ 3 rows per database (14 databases used);
  distractors must differ structurally (tables, selected columns ignoring aggregation, where/group/having/order/limit,
  set ops) from the gold and from each other.
- Hand skip: dev index 819 ("countries where Spanish is predominantly spoken") — Spider's gold is a known dev-set error.
  It still appears as a distractor on row dev-807, where it is plainly not an answer to "Count the countries in Asia".
- All 30 rows were read; every gold is the only query whose result answers the question.

### DAT-2 · WikiTableQuestions test set
- Source: `ppasupat/WikiTableQuestions` at commit `7d455a5` (2021-03-19): `data/pristine-unseen-tables.tsv` plus the
  95 table CSVs the rank-ordered walk touches (listed in `WTQ_TABLES`; the walk stops at the first table not listed,
  which is after the 30th kept row).
- Filters: single-value, non-numeric answer; question without count/arithmetic words (`how many`, `how much`, `number
  of`, `total`, `how long`, `difference`, `average`, `sum`) — such answers are computed, not read from a cell; one
  example per table; 5–25 body rows, ≤ 8 columns; the answer matches cells of exactly one column; that column has ≥ 3
  other distinct values; the answer is not in the question.
- Hand skips (3): nu-4017 (cells merge two lines, garbled option text), nu-4271 ("the only administrator with just a
  B.S." — two rows have a B.S.), nu-4320 ("New Orleans Saints" and "at New Orleans Saints" both offered, same team).
- All 30 tables were read against their questions; all decidable from the table alone.

### DAT-3 · Our World in Data charts (image, text+image)
- 16 grapher charts × 2 claims. Each chart: four countries and a year range chosen by hand; PNG fetched from
  `ourworldindata.org/grapher/<slug>.png?tab=chart&country=…&time=…` and copied unchanged; CSV from the `.csv`
  endpoint (filtered in code by ISO code, because map-default charts return the full table).
- Claims are TEMPLATED FROM THE DATA (stated in the module docstring, the task instruction, the dataset `changes`, the
  state's `claim_origin` and the tags). Two patterns: (A) "In Y, X's metric was higher than Z's" (ratio ≥ 1.15 and gap
  ≥ 10% of the chart's largest value); (B) "X's metric rose/fell between y1 and y2" (≥ 15% change, ≥ 10% of the
  chart's largest value, ≥ 10 years apart, series stays within 5% of the start–end range so the trend is clean).
  Candidates chosen by sha256; one claim per chart is true, the other false (false = swapped countries or swapped
  direction), parity decided by sha256 of the slug. The state carries the data points used and each series sampled
  every ten years as the text rendering.
- Charts used: population, co2-emissions-per-capita, annual-co2-emissions-per-country, share-of-population-urban,
  gdp-per-capita-worldbank, share-of-individuals-using-the-internet, children-per-woman-un, median-age,
  gdp-per-capita-maddison-project-database, carbon-intensity-electricity, life-expectancy-unwpp, crude-birth-rate,
  co2-emissions-transport, total-ghg-emissions, mobile-cellular-subscriptions-per-100-people,
  gdp-per-capita-penn-world-table (electricity-demand and human-development-index are listed as spares; the module
  takes the first 16 charts that yield both claims, so they were not used).
- I looked at five of the PNGs (median age, urban share, population, annual CO₂, mobile subscriptions, transport CO₂);
  the claimed differences are visible at a glance and the CC BY stamp is on every chart.

### DAT-4 · open-data columns
- 14 CSV files, ≤ 3 columns each, 15 values per row, header hidden, other headers shown. Label = the real header's
  meaning under the written `MAPPING` (headers whose meaning could fit two options — numeric ids, postal codes, URLs,
  personal names, bare years, currency names — are not mapped).
- Files: FiveThirtyEight (9 files: KNYC weather, librarians by MSA, DC comic characters, Daily Show guests, Bechdel
  movies, college majors, police locals, airline safety, bad drivers); congress-legislators `legislators-current.csv`;
  Treasury Fiscal Data (Debt to the Penny Jan–Mar 2024; Rates of Exchange 2024-03-31); Federal Register documents
  published 2024-03-01 and 2024-09-03 (first 60, oldest first).
- Note: these are not data.gov-hosted CSVs. Federal Socrata portals (data.cdc.gov, data.transportation.gov,
  healthdata.gov) answer 403 to plain HTTP clients, so `fetch_sources.py` could not reproduce them, and data.gov's CKAN
  API was retired in 2025 (the v4 API needs an api key and only lists metadata). The federal APIs used (Fiscal Data,
  Federal Register) are public-domain U.S. government works; the GitHub-hosted files have explicit CC0 / CC BY 4.0.

## Licence evidence (URLs actually read)

| Dataset | Dataset licence | Evidence | Content inside | Evidence |
| --- | --- | --- | --- | --- |
| Spider | CC BY-SA 4.0 | https://huggingface.co/datasets/xlangai/spider (card metadata `license: cc-by-sa-4.0` and "Licensing Information: The spider dataset is licensed under the CC BY-SA 4.0") | questions, SQL and schemas written by the Spider authors | same |
| WikiTableQuestions | CC BY-SA 4.0 | https://github.com/ppasupat/WikiTableQuestions/blob/7d455a5a707b96341ef72aff9428749d443d8aa9/LICENSE (Attribution-ShareAlike 4.0 International legal code) | tables are Wikipedia content, CC BY-SA 3.0 | https://en.wikipedia.org/wiki/Wikipedia:Copyrights; README: tables come from Wikipedia pages (`page/` folder holds the raw HTML) |
| Our World in Data charts | CC BY 4.0 | https://ourworldindata.org/faqs#can-i-reuse-or-republish-your-charts ("you can use, reproduce, and distribute any chart we made (those with our logo and CC BY copyright stamp), provided that you cite us"); https://ourworldindata.org/about ("All of these charts are free to reuse under our permissive Creative Commons license") | third-party data | per-indicator `origins[].license` at `https://api.ourworldindata.org/v1/indicators/<id>.metadata.json`, read 2026-09-23 for every chart: all origins CC BY 4.0, CC BY 3.0 IGO or CC0 (Gapminder, PBL, UN WPP/WUP, Global Carbon Project, Eurostat/OECD/IMF/World Bank, ITU via World Bank, Bolt & van Zanden, Ember, Climate Watch, Jones et al., Feenstra et al.) |
| FiveThirtyEight data | CC BY 4.0 | https://github.com/fivethirtyeight/data/blob/4c1ff5e3aef1816ae04af63218015066e186c147/LICENSE and README ("Unless otherwise noted, our data sets are available under the Creative Commons Attribution 4.0 International License") | factual records compiled by FiveThirtyEight | same |
| congress-legislators | CC0 1.0 | https://github.com/unitedstates/congress-legislators/blob/73e2fcd181e1c48d1b0580d417e8d0314b22f7c9/LICENSE (CC0 1.0 Universal legal code) | public official records | same |
| Treasury Fiscal Data | Public domain | https://fiscaldata.treasury.gov/api-documentation/#license-and-authorization ("offered free, without restriction, and available to copy, adapt, redistribute, or otherwise use for non-commercial or commercial purposes") | U.S. government work | same; 17 U.S.C. § 105 |
| Federal Register API | Public domain | https://www.govinfo.gov/about/policies#copyright (GPO Public Domain & Copyright Notice quoting 17 U.S.C. § 105: "public documents can generally be reprinted without legal restriction") | U.S. government work | same |

Charts checked and rejected on origin licence (not used): child-mortality (UN IGME "Copyright © UNICEF"),
cereal-yield / meat-production / agricultural-land / population-density (FAO CC BY-NC-SA 3.0 IGO), forest-area
(mixed publisher copyrights), daily-per-capita-caloric-supply (publisher copyrights), life-expectancy long-run
(Riley, JSTOR terms), electricity mix and per-capita generation charts (Energy Institute "© Energy Institute", UK
DESNZ OGL), mean-years-of-schooling (Barro-Lee copyright), homicide-rate-unodc ("© United Nations"),
international-tourist-arrivals ("© UNWTO"), co2-emissions-aviation (OECD terms).

## Dropped and why

- **DAT-5 "Is this generated SQL correct?"** — not built. No published set of model predictions on Spider dev with
  execution results under a clear licence was found. `taoyds/test-suite-sql-eval` (Apache-2.0) ships one unlabelled
  example `evaluation_examples/predict.txt` and no execution results; producing results would need the Spider
  SQLite databases (large download) and my own execution, which is not a published record.
- **BIRD** — not used, as instructed (licence inconsistent).
- **Federal Socrata portals and data.gov CKAN API** — unreachable for plain HTTP clients / retired (above).
- **Hand-skipped rows**: Spider dev 819; WTQ nu-4017, nu-4271, nu-4320 (reasons above and in the module's SKIP tables).
- **WTQ question-level rule** dropped all count/arithmetic questions, so every DAT-2 answer is a cell read off the
  table; ~40% of the walk's tables also failed the 5–25-row / ≤ 8-column size rule or had no matching cell.

## Judgement calls for a maintainer to review

1. **WTQ licence id.** The Hugging Face card metadata tags `stanfordnlp/wikitablequestions` as `cc-by-4.0`, but the
   card's Licensing section and the repository's LICENSE file are CC BY-SA 4.0. I recorded what the LICENSE file says
   (CC-BY-SA-4.0). Rows carry CC BY-SA 3.0 because the tables are Wikipedia content.
2. **Spider licence source.** The GitHub README does not state a data licence (the repo is Apache-2.0 for code); the
   CC BY-SA 4.0 statement is on the Hugging Face card maintained by the Spider authors' group (xlangai). `license_url`
   points there.
3. **OWID data drift.** OWID updates chart data and PNGs; `fetch_sources.py` will report hash mismatches when they do.
   Rows are built from the pinned local files, so the frozen corpus is unaffected, but re-fetching may change claims.
   The PNG requests carry `tab=chart`, `country=` and `time=` so the image shows exactly the four series the CSV has.
4. **DAT-3 wording.** The templated claims use OWID's chart title lower-cased as the metric phrase and a possessive
   (`Japan's`, `United States'`). "X's annual CO₂ emissions was higher" is grammatically clumsy but unambiguous; I left
   the template rigid rather than hand-editing rows. Two rows share one image per chart (claim A and claim B).
5. **DAT-3 country choices** (four per chart) and the **DAT-4 file list** are hand choices, like choosing a dataset;
   every downstream choice (claim, year, countries compared, columns, values) is by sha256.
6. **DAT-4 money rows.** `bechdel/movies.csv` `budget` values are plain integers (e.g. 150000000); the visible sibling
   headers `budget_2013$`, `domgross_2013$`, `intgross_2013$` make "money" the only sensible reading, but a stickler
   could call the bare number a measurement. Debt to the Penny amounts (14-digit, two decimals, sibling headers
   `debt_held_public_amt` etc.) and bad-drivers premiums/losses (sibling header ends in "($)") are clearer. If the
   bechdel row is judged too soft, remove `budget` from `MAPPING["bechdel"]` (money would drop to 4 rows, still fine).
7. **DAT-4 exchange_rate** (Treasury Reporting Rates of Exchange) is labelled count_or_measurement: a rate, not an
   amount of money. The option text defines money as "an amount", so I consider it one-answer, but it sits near the
   boundary.
8. **DAT-4 sources are not data.gov CSVs** (see above). If the maintainer wants strictly portal-hosted files, the
   Fiscal Data and Federal Register APIs are the two federal sources here; the GitHub-hosted ones are CC0/CC BY 4.0.
9. **DAT-1 record ids** are dev.json indices (`dev.json[338]`), since Spider records have no ids; the pinned commit
   makes them stable.
10. **DAT-2 SOURCES** lists 95 table files (one entry each) so `fetch_sources.py` can reproduce the walk without a
    Python parquet dependency (the HF dataset viewer is disabled for WTQ and pyarrow is not available).

## Files touched

- `authoring/bench/data.py` (new)
- `data/assets/data/dat-3-<slug>.png` (16 files, copied unchanged from the OWID downloads)
- `data/sources/{spider,wikitablequestions,owid,opendata}/` (downloads, not committed)
