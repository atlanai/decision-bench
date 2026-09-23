"""data: SQL, tables, charts and columns.

DAT-1  Which SQL answers the question?   Spider dev set (Yale, CC BY-SA 4.0). The database schema, one question and
       four of Spider's own gold queries for that database; exactly one is the gold query for this question, the
       others are gold queries for different questions.
DAT-2  Which cell answers the question?  WikiTableQuestions test set (Stanford, CC BY-SA 4.0; tables from Wikipedia,
       CC BY-SA 3.0). A table of at most 25 rows and a crowd-written question whose answer is one cell; the options are
       the gold cell and three other values from the same column.
DAT-3  Does the chart support the claim?  Our World in Data grapher charts (CC BY 4.0), each a line chart of four
       countries. The claim is TEMPLATED FROM THE CHART'S OWN DATA by two fixed patterns (a comparison in one year, a
       rise or fall between two years); half are true and half state the opposite of the data. The data points used
       are in the state as the text rendering.
DAT-4  What does this column hold?        Fifteen values from one column of an open-data CSV with the header hidden,
       plus the file's other headers; the answer is the real header's meaning under a written mapping.

Dropped: DAT-5 "Is this generated SQL correct?" needs published model predictions on Spider dev with execution
results under a clear licence; none was found (taoyds/test-suite-sql-eval ships one unlabelled example prediction
file and no execution results), so the task is not built. BIRD was not used (licence inconsistent). Federal Socrata
portals (data.cdc.gov, data.transportation.gov, healthdata.gov) return 403 to plain HTTP clients, so their CSVs cannot
be re-fetched by scripts/fetch_sources.py and are not used; data.gov's CKAN API was retired in 2025.

Written sampling rules
DAT-1  Records of dev.json (taoyds/spider at SPIDER_COMMIT) ordered by rank("spider-dev-<index>"). Keep a record if
       its database has 3–8 tables, its query is at most 220 characters and its question at most 160, its gold query
       has a structure (tables, selected columns ignoring aggregation, where, group, having, order, limit, set
       operations, from Spider's parsed `sql`) not already used by a kept row, the database has fewer than 3 kept rows,
       and it is not in DAT1_SKIP. Distractors: the other dev records of the same database whose question text and
       query structure differ from the gold's and from each other, ordered by rank("spider-dev-<index>-<other>"),
       first three; a record with fewer than three is dropped. The four queries are labelled q1–q4 in rank order.
DAT-2  Examples of data/pristine-unseen-tables.tsv (ppasupat/WikiTableQuestions at WTQ_COMMIT) ordered by
       rank(example id). Question-level filters: single-value answer (no "|"), the answer is not purely numeric, the
       question contains none of COUNT_WORDS (counts and arithmetic are computed, not read off a cell), one example per
       table. Table-level filters: 5–25 body rows and at most 8 columns; the answer equals (case- and whitespace-
       insensitively) at least one cell and all matching cells are in one column; that column has at least three
       other distinct non-empty values; the answer does not appear in the question. Hand drops are in DAT2_SKIP. The
       walk covers the first question-level candidates in rank order; their tables are WTQ_TABLES, and the walk stops
       at the first table not in that list (which happens after the target is reached).
DAT-3  CHARTS is a hand list of grapher slugs whose every data origin is CC BY 4.0, CC BY 3.0 IGO, CC0 or public
       domain (checked in the indicator metadata on 2026-09-23), with four countries and a year range per chart. For
       each chart two claims: (A) "In <year>, <X>'s <metric> was higher than <Y>'s" over decade years and the last
       year, kept when the higher value is at least 1.15 times the lower and the gap is at least 10% of the chart's
       largest value; (B) "<X>'s <metric> rose/fell between <y1>
       and <y2>" over decade years and the last year at least 10 years apart, kept when the end value is at least 15%
       above (rose) or below (fell) the start, the change is at least 10% of the chart's largest value, and the series
       between stays within 5% of that range. Candidates are
       chosen by rank("<slug>:A:<year>:<X>:<Y>") and rank("<slug>:B:<X>:<y1>:<y2>"). The truth of claim A is even/odd
       of rank("<slug>:truth"); claim B gets the other truth value; a false claim swaps X and Y (A) or the direction
       (B). The PNG is copied unchanged.
DAT-4  FILES is a hand list of CSVs with an explicit CC0, public-domain or CC BY 4.0 licence; MAPPING gives, per file,
       the headers whose meaning is unambiguous under the seven options (headers that could fit two options, such as
       numeric ids, postal codes, URLs, personal names and years, are left out). Per file the mapped headers are
       ordered by rank("<file>:<header>") and the first three taken. Values: rows ordered by rank("<file>:<row>"), the
       first 15 whose cell is non-empty and not a suppression mark ("**", "NA").
"""
from __future__ import annotations

import csv
import io
import json
import re
import shutil
import struct

from . import dataset, task, row, rank, ROOT, SOURCES as SOURCE_DIR, ASSETS

# ---------------------------------------------------------------- sources

SPIDER_COMMIT = "b7b5b8c890cd30e35427348bb9eb8c6d1350ca7c"  # taoyds/spider master, 2024-05-29
SPIDER_RAW = f"https://raw.githubusercontent.com/taoyds/spider/{SPIDER_COMMIT}/evaluation_examples/examples/"
WTQ_COMMIT = "7d455a5a707b96341ef72aff9428749d443d8aa9"  # ppasupat/WikiTableQuestions master, 2021-03-19
WTQ_RAW = f"https://raw.githubusercontent.com/ppasupat/WikiTableQuestions/{WTQ_COMMIT}/"
FTE_COMMIT = "4c1ff5e3aef1816ae04af63218015066e186c147"  # fivethirtyeight/data master, 2025-02-25
FTE_RAW = f"https://raw.githubusercontent.com/fivethirtyeight/data/{FTE_COMMIT}/"
LEG_COMMIT = "73e2fcd181e1c48d1b0580d417e8d0314b22f7c9"  # unitedstates/congress-legislators gh-pages, 2026-09-03
LEG_RAW = f"https://raw.githubusercontent.com/unitedstates/congress-legislators/{LEG_COMMIT}/"
FISCAL_API = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"
FEDREG_API = "https://www.federalregister.gov/api/v1/documents.csv"
OWID = "https://ourworldindata.org/grapher/"

# The tables the DAT-2 walk touches, in walk order (see the module docstring).
WTQ_TABLES = [
    'csv/203-csv/566.csv', 'csv/203-csv/493.csv', 'csv/204-csv/150.csv', 'csv/203-csv/571.csv',
    'csv/203-csv/738.csv', 'csv/203-csv/0.csv', 'csv/201-csv/30.csv', 'csv/203-csv/260.csv', 'csv/204-csv/315.csv',
    'csv/204-csv/545.csv', 'csv/203-csv/520.csv', 'csv/204-csv/892.csv', 'csv/204-csv/773.csv',
    'csv/204-csv/303.csv', 'csv/204-csv/875.csv', 'csv/204-csv/819.csv', 'csv/203-csv/87.csv',
    'csv/203-csv/740.csv', 'csv/203-csv/604.csv', 'csv/203-csv/318.csv', 'csv/203-csv/32.csv',
    'csv/203-csv/284.csv', 'csv/204-csv/827.csv', 'csv/201-csv/8.csv', 'csv/204-csv/934.csv',
    'csv/204-csv/368.csv', 'csv/203-csv/624.csv', 'csv/203-csv/768.csv', 'csv/203-csv/579.csv',
    'csv/203-csv/278.csv', 'csv/204-csv/306.csv', 'csv/203-csv/389.csv', 'csv/204-csv/424.csv',
    'csv/201-csv/26.csv', 'csv/204-csv/434.csv', 'csv/204-csv/720.csv', 'csv/204-csv/380.csv',
    'csv/204-csv/931.csv', 'csv/204-csv/417.csv', 'csv/204-csv/454.csv', 'csv/203-csv/748.csv',
    'csv/204-csv/92.csv', 'csv/203-csv/669.csv', 'csv/204-csv/818.csv', 'csv/203-csv/178.csv',
    'csv/204-csv/619.csv', 'csv/203-csv/628.csv', 'csv/204-csv/264.csv', 'csv/204-csv/657.csv',
    'csv/204-csv/714.csv', 'csv/203-csv/12.csv', 'csv/203-csv/585.csv', 'csv/204-csv/695.csv',
    'csv/203-csv/500.csv', 'csv/204-csv/900.csv', 'csv/203-csv/259.csv', 'csv/203-csv/488.csv',
    'csv/204-csv/844.csv', 'csv/204-csv/830.csv', 'csv/203-csv/48.csv', 'csv/204-csv/366.csv',
    'csv/204-csv/803.csv', 'csv/203-csv/264.csv', 'csv/203-csv/662.csv', 'csv/203-csv/617.csv',
    'csv/204-csv/167.csv', 'csv/203-csv/169.csv', 'csv/200-csv/45.csv', 'csv/202-csv/264.csv',
    'csv/204-csv/578.csv', 'csv/203-csv/659.csv', 'csv/203-csv/822.csv', 'csv/203-csv/72.csv',
    'csv/204-csv/134.csv', 'csv/204-csv/326.csv', 'csv/203-csv/103.csv', 'csv/204-csv/8.csv',
    'csv/204-csv/289.csv', 'csv/204-csv/645.csv', 'csv/204-csv/758.csv', 'csv/204-csv/21.csv',
    'csv/204-csv/904.csv', 'csv/204-csv/372.csv', 'csv/203-csv/351.csv', 'csv/204-csv/407.csv',
    'csv/203-csv/128.csv', 'csv/203-csv/369.csv', 'csv/204-csv/280.csv', 'csv/204-csv/259.csv',
    'csv/204-csv/491.csv', 'csv/203-csv/21.csv', 'csv/204-csv/943.csv', 'csv/204-csv/857.csv',
    'csv/203-csv/64.csv', 'csv/203-csv/596.csv',
]

# DAT-3 charts: slug, OWID's chart title, the metric phrase used in claims, unit, the data source printed on the
# chart, four countries (ISO3) and the year range requested. Every data origin was checked to be CC BY 4.0,
# CC BY 3.0 IGO, CC0 or public domain in api.ourworldindata.org/v1/indicators/<id>.metadata.json.
CHARTS = [
    dict(slug="population", title="Population", metric="population", unit="people",
         source="HYDE (2023); Gapminder (2022); UN WPP (2024)", countries="USA~IDN~BRA~PAK", time="1950..2023"),
    dict(slug="co2-emissions-per-capita", title="CO₂ emissions per capita", metric="CO₂ emissions per capita",
         unit="tonnes per person", source="Global Carbon Budget (2025)", countries="USA~GBR~CHN~IND", time="1950..2023"),
    dict(slug="annual-co2-emissions-per-country", title="Annual CO₂ emissions", metric="annual CO₂ emissions",
         unit="tonnes", source="Global Carbon Budget (2025)", countries="CHN~USA~IND~DEU", time="1950..2023"),
    dict(slug="share-of-population-urban", title="Share of population living in urban areas",
         metric="share of population living in urban areas", unit="%", source="UN World Urbanization Prospects",
         countries="CHN~IND~BRA~NGA", time="1950..2023"),
    dict(slug="gdp-per-capita-worldbank", title="GDP per capita", metric="GDP per capita",
         unit="international-$ in 2021 prices", source="World Bank (Eurostat, OECD, IMF)",
         countries="KOR~MEX~TUR~ZAF", time="1990..2023"),
    dict(slug="share-of-individuals-using-the-internet", title="Share of the population using the Internet",
         metric="share of the population using the Internet", unit="% of population",
         source="ITU via World Bank", countries="BRA~IND~IDN~RUS", time="1990..2023"),
    dict(slug="children-per-woman-un", title="Fertility rate: births per woman", metric="fertility rate",
         unit="live births per woman", source="UN World Population Prospects (2024)",
         countries="BGD~KEN~JPN~MEX", time="1950..2023"),
    dict(slug="median-age", title="Median age", metric="median age", unit="years",
         source="UN World Population Prospects (2024)", countries="JPN~NGA~BRA~DEU", time="1950..2023"),
    dict(slug="gdp-per-capita-maddison-project-database", title="GDP per capita", metric="GDP per capita",
         unit="international-$ in 2011 prices", source="Maddison Project Database 2023 (Bolt and van Zanden)",
         countries="ARG~ITA~JPN~KOR", time="1900..2022"),
    dict(slug="carbon-intensity-electricity", title="Lifecycle carbon intensity of electricity",
         metric="carbon intensity of electricity", unit="grams of CO₂ equivalents per kilowatt-hour",
         source="Ember", countries="FRA~POL~IND~BRA", time="1990..2023"),
    dict(slug="life-expectancy-unwpp", title="Life expectancy at birth", metric="life expectancy at birth",
         unit="years", source="UN World Population Prospects (2024)", countries="ETH~VNM~RUS~CHL", time="1950..2023"),
    dict(slug="crude-birth-rate", title="Birth rate", metric="birth rate", unit="births per 1,000 people",
         source="UN World Population Prospects (2024)", countries="NER~CHN~DEU~EGY", time="1950..2023"),
    dict(slug="co2-emissions-transport", title="CO₂ emissions from transport", metric="CO₂ emissions from transport",
         unit="tonnes", source="Climate Watch", countries="USA~CHN~JPN~DEU", time="1990..2022"),
    dict(slug="total-ghg-emissions", title="Greenhouse gas emissions", metric="greenhouse gas emissions",
         unit="tonnes of CO₂ equivalents", source="Jones et al. (2025)", countries="CHN~USA~IND~RUS", time="1950..2023"),
    dict(slug="mobile-cellular-subscriptions-per-100-people", title="Mobile phone subscriptions per 100 people",
         metric="mobile phone subscriptions per 100 people", unit="per 100 people", source="ITU via World Bank",
         countries="CHN~IND~NGA~USA", time="1990..2023"),
    dict(slug="gdp-per-capita-penn-world-table", title="GDP per capita", metric="GDP per capita",
         unit="international-$ in 2021 prices", source="Penn World Table 11.0 (Feenstra et al.)",
         countries="IRL~ESP~POL~CHL", time="1950..2019"),
    dict(slug="electricity-demand", title="Electricity demand", metric="electricity demand", unit="terawatt-hours",
         source="Ember", countries="CHN~USA~IND~JPN", time="1990..2023"),
    dict(slug="human-development-index", title="Human Development Index", metric="Human Development Index",
         unit="index (0–1)", source="UNDP, Human Development Report", countries="CHN~IND~BRA~ZAF", time="1990..2023"),
]
DAT3_CHARTS = 16  # first CHARTS entries that yield both claims

# DAT-4 files: key -> (dataset id, display label, url, path).
FILES = {
    "weather": ("fivethirtyeight", "FiveThirtyEight us-weather-history/KNYC.csv",
                FTE_RAW + "us-weather-history/KNYC.csv", "opendata/fte-KNYC.csv"),
    "librarians": ("fivethirtyeight", "FiveThirtyEight librarians/librarians-by-msa.csv",
                   FTE_RAW + "librarians/librarians-by-msa.csv", "opendata/fte-librarians-by-msa.csv"),
    "dc": ("fivethirtyeight", "FiveThirtyEight comic-characters/dc-wikia-data.csv",
           FTE_RAW + "comic-characters/dc-wikia-data.csv", "opendata/fte-dc-wikia-data.csv"),
    "dailyshow": ("fivethirtyeight", "FiveThirtyEight daily-show-guests/daily_show_guests.csv",
                  FTE_RAW + "daily-show-guests/daily_show_guests.csv", "opendata/fte-daily_show_guests.csv"),
    "bechdel": ("fivethirtyeight", "FiveThirtyEight bechdel/movies.csv", FTE_RAW + "bechdel/movies.csv",
                "opendata/fte-bechdel-movies.csv"),
    "college": ("fivethirtyeight", "FiveThirtyEight college-majors/recent-grads.csv",
                FTE_RAW + "college-majors/recent-grads.csv", "opendata/fte-recent-grads.csv"),
    "police": ("fivethirtyeight", "FiveThirtyEight police-locals/police-locals.csv",
               FTE_RAW + "police-locals/police-locals.csv", "opendata/fte-police-locals.csv"),
    "airline": ("fivethirtyeight", "FiveThirtyEight airline-safety/airline-safety.csv",
                FTE_RAW + "airline-safety/airline-safety.csv", "opendata/fte-airline-safety.csv"),
    "baddrivers": ("fivethirtyeight", "FiveThirtyEight bad-drivers/bad-drivers.csv",
                   FTE_RAW + "bad-drivers/bad-drivers.csv", "opendata/fte-bad-drivers.csv"),
    "legislators": ("congress-legislators", "unitedstates/congress-legislators legislators-current.csv",
                    LEG_RAW + "legislators-current.csv", "opendata/legislators-current.csv"),
    "debt": ("fiscal-data", "U.S. Treasury Fiscal Data · Debt to the Penny, January–March 2024",
             FISCAL_API + "v2/accounting/od/debt_to_penny?format=csv&filter=record_date:gte:2024-01-01,"
             "record_date:lte:2024-03-31&page[size]=100", "opendata/fiscal-debt-to-penny-2024q1.csv"),
    "fx": ("fiscal-data", "U.S. Treasury Fiscal Data · Treasury Reporting Rates of Exchange, 31 March 2024",
           FISCAL_API + "v1/accounting/od/rates_of_exchange?format=csv&filter=record_date:eq:2024-03-31&page[size]=200",
           "opendata/fiscal-rates-of-exchange-2024-03-31.csv"),
    "fedreg1": ("federal-register", "Federal Register · documents published 2024-03-01",
                FEDREG_API + "?conditions[publication_date][is]=2024-03-01&per_page=60&order=oldest",
                "opendata/federal-register-2024-03-01.csv"),
    "fedreg2": ("federal-register", "Federal Register · documents published 2024-09-03",
                FEDREG_API + "?conditions[publication_date][is]=2024-09-03&per_page=60&order=oldest",
                "opendata/federal-register-2024-09-03.csv"),
}
# The written mapping from a real header to its meaning. Only headers whose meaning is unambiguous are listed.
MAPPING = {
    "weather": {"date": "date", "actual_max_temp": "count_or_measurement"},
    "librarians": {"area_name": "geography", "tot_emp": "count_or_measurement"},
    "dc": {"ALIGN": "category", "APPEARANCES": "count_or_measurement", "FIRST APPEARANCE": "date"},
    "dailyshow": {"Show": "date", "Group": "category"},
    "bechdel": {"imdb": "identifier", "binary": "category", "budget": "money"},
    "college": {"Major_category": "category", "Total": "count_or_measurement"},
    "police": {"city": "geography", "police_force_size": "count_or_measurement"},
    "airline": {"fatalities_85_99": "count_or_measurement"},
    "baddrivers": {"State": "geography", "Car Insurance Premiums ($)": "money",
                   "Losses incurred by insurance companies for collisions per insured driver ($)": "money"},
    "legislators": {"birthday": "date", "party": "category", "bioguide_id": "identifier", "fec_ids": "identifier",
                    "state": "geography"},
    "debt": {"record_date": "date", "tot_pub_debt_out_amt": "money", "debt_held_public_amt": "money"},
    "fx": {"country": "geography", "exchange_rate": "count_or_measurement"},
    "fedreg1": {"title": "free_text", "abstract": "free_text", "document_number": "identifier", "type": "category"},
    "fedreg2": {"title": "free_text", "abstract": "free_text", "document_number": "identifier", "type": "category"},
}
DAT4_PER_FILE, DAT4_VALUES = 3, 15
DAT4_OPTIONS = {
    "date": "A calendar date or timestamp, in any format, possibly with a time of day.",
    "money": "An amount of money: a price, payment, budget, revenue, loss or debt in some currency.",
    "identifier": "A code or number that identifies one record or entity: an ID, case number, registry code.",
    "category": "One of a small fixed set of labels that classify the row: a type, status, class, party.",
    "count_or_measurement": "A number that counts or measures something and is not money: a total, rate, share, "
                            "temperature, size.",
    "free_text": "Prose written by a person: a title, description, abstract, comment or narrative.",
    "geography": "A place: a country, state, county, city or metro area, given as a name or a code.",
}

SOURCES = [
    {"dataset": "Spider", "url": SPIDER_RAW + "dev.json", "path": "spider/dev.json"},
    {"dataset": "Spider", "url": SPIDER_RAW + "tables.json", "path": "spider/tables.json"},
    {"dataset": "WikiTableQuestions", "url": WTQ_RAW + "data/pristine-unseen-tables.tsv",
     "path": "wikitablequestions/pristine-unseen-tables.tsv"},
]
SOURCES += [{"dataset": "WikiTableQuestions", "url": WTQ_RAW + t, "path": "wikitablequestions/" + t}
            for t in WTQ_TABLES]
for _c in CHARTS:
    _q = f"country=~{_c['countries']}&time={_c['time']}"
    SOURCES += [
        {"dataset": "Our World in Data", "url": f"{OWID}{_c['slug']}.png?tab=chart&{_q}",
         "path": f"owid/{_c['slug']}.png"},
        {"dataset": "Our World in Data", "url": f"{OWID}{_c['slug']}.csv?csvType=filtered&useColumnShortNames=true&{_q}",
         "path": f"owid/{_c['slug']}.csv"},
    ]
SOURCES += [{"dataset": ds, "url": url, "path": path} for ds, _, url, path in FILES.values()]


def _png_size(path):
    head = path.read_bytes()[:24]
    assert head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR", f"{path}: not a PNG"
    return struct.unpack(">II", head[16:24])


# ---------------------------------------------------------------- datasets

def _datasets():
    dataset(
        id="spider", name="Spider (dev set)", tasks=["DAT-1"], homepage="https://yale-lily.github.io/spider",
        license="CC-BY-SA-4.0", license_url="https://huggingface.co/datasets/xlangai/spider#licensing-information",
        content=("A natural-language question written by Yale students for one of Spider's 20 dev databases, the "
                 "database schema from tables.json, and four of Spider's gold SQL queries for that database."),
        content_license="CC-BY-SA-4.0",
        content_terms=("Questions, gold SQL and schemas were written by the Spider authors and are released with the "
                       "dataset under CC BY-SA 4.0 (creativecommons.org/licenses/by-sa/4.0/legalcode); the dataset "
                       "card at huggingface.co/datasets/xlangai/spider states the licence. Rows carry CC BY-SA 4.0."),
        labelled_by="the Spider annotators' gold SQL for each question, verified by the Spider authors",
        changes=("The schema is rendered compactly (table(columns), primary keys starred, foreign keys listed) from "
                 "tables.json; queries are shown verbatim. Distractor queries are other gold queries of the same "
                 "database, labelled q1–q4 in a fixed hash order."),
        selection=("Dev records in sha256 order of their index, databases with 3–8 tables, queries of at most 220 "
                   "characters, one row per distinct query structure, at most three rows per database; distractors "
                   "are the first three structurally different gold queries of the database in hash order (see the "
                   "module docstring)."),
        citation="Yu et al., Spider: A Large-Scale Human-Labeled Dataset for Complex and Cross-Domain Semantic "
                 "Parsing and Text-to-SQL Task, EMNLP 2018.",
        bibtex="""@inproceedings{yu-etal-2018-spider,
  title     = {Spider: A Large-Scale Human-Labeled Dataset for Complex and Cross-Domain Semantic Parsing and Text-to-{SQL} Task},
  author    = {Yu, Tao and Zhang, Rui and Yang, Kai and Yasunaga, Michihiro and Wang, Dongxu and Li, Zifan and Ma, James and Li, Irene and Yao, Qingning and Roman, Shanelle and Zhang, Zilin and Radev, Dragomir},
  booktitle = {Proceedings of the 2018 Conference on Empirical Methods in Natural Language Processing},
  year      = {2018},
  pages     = {3911--3921},
  doi       = {10.18653/v1/D18-1425}
}""",
    )
    dataset(
        id="wikitablequestions", name="WikiTableQuestions (test set)", tasks=["DAT-2"],
        homepage="https://github.com/ppasupat/WikiTableQuestions", license="CC-BY-SA-4.0",
        license_url=f"https://github.com/ppasupat/WikiTableQuestions/blob/{WTQ_COMMIT}/LICENSE",
        content=("A table extracted from a Wikipedia article (csv/ folder of the repository) and a question about it "
                 "written by an Amazon Mechanical Turk worker, with the worker's answer."),
        content_license="CC-BY-SA-3.0",
        content_terms=("The tables are Wikipedia content, licensed by Wikipedia's contributors under CC BY-SA 3.0 "
                       "(https://en.wikipedia.org/wiki/Wikipedia:Copyrights); the questions and answers are released "
                       "with the dataset under CC BY-SA 4.0 (the repository's LICENSE file). Rows carry CC BY-SA 3.0."),
        labelled_by="the crowd worker who wrote the question (the dataset's targetValue), checked by the authors' "
                    "verification pass",
        changes=("None to the table cells or question; the table is shown as its header and rows. The three "
                 "distractor values are other cells of the same column, chosen in a fixed hash order."),
        selection=("Test-set (pristine-unseen-tables) examples in sha256 order of their id, single-value non-numeric "
                   "answers to questions that do not ask for a count or a computation, tables of 5–25 rows and at "
                   "most 8 columns in which the answer is a cell of exactly one column, one example per table, "
                   "minus hand drops listed with reasons (see the module docstring)."),
        citation="Pasupat and Liang, Compositional Semantic Parsing on Semi-Structured Tables, ACL 2015.",
        bibtex="""@inproceedings{pasupat-liang-2015-compositional,
  title     = {Compositional Semantic Parsing on Semi-Structured Tables},
  author    = {Pasupat, Panupong and Liang, Percy},
  booktitle = {Proceedings of the 53rd Annual Meeting of the Association for Computational Linguistics and the 7th International Joint Conference on Natural Language Processing (Volume 1: Long Papers)},
  year      = {2015},
  pages     = {1470--1480},
  doi       = {10.3115/v1/P15-1142}
}""",
    )
    dataset(
        id="owid-grapher", name="Our World in Data grapher charts", tasks=["DAT-3"],
        homepage="https://ourworldindata.org/", license="CC-BY-4.0",
        license_url="https://ourworldindata.org/faqs#can-i-reuse-or-republish-your-charts",
        content=("A grapher line chart (PNG as served by ourworldindata.org/grapher/<slug>.png for four countries and "
                 "a year range) and the chart's CSV data, from which a claim is templated."),
        content_license="CC-BY-4.0",
        content_terms=("Charts with the OWID logo and CC BY stamp may be reproduced and distributed with citation "
                       "(FAQ: Can I reuse or republish your charts?). The underlying data are third-party; only charts "
                       "whose every data origin is CC BY 4.0, CC BY 3.0 IGO, CC0 or public domain were used, checked "
                       "per indicator at api.ourworldindata.org/v1/indicators/<id>.metadata.json on 2026-09-23. The "
                       "claims are not OWID's: they are templated from the data by this benchmark."),
        labelled_by="a written rule: the claim is compared with the chart's own CSV values (see the module docstring)",
        changes=("The PNG is copied unchanged (850×600 px). THE CLAIM IS TEMPLATED BY THIS BENCHMARK from the chart's "
                 "CSV using two fixed patterns; half the claims state the opposite of the data. The data points used "
                 "are listed in the state, with the series sampled every ten years, as the text rendering."),
        selection=("A hand list of charts with permissive data origins, four countries each; two claims per chart "
                   "(one comparison, one trend) chosen by sha256 over the qualifying candidates, one true and one "
                   "false per chart, differences of at least 15% (see the module docstring)."),
        citation="Our World in Data, grapher charts (ourworldindata.org/grapher), retrieved 2026-09-23, CC BY 4.0.",
        bibtex="""@misc{owid_grapher,
  title        = {Our World in Data grapher charts},
  author       = {{Our World in Data}},
  howpublished = {\\url{https://ourworldindata.org/grapher}},
  year         = {2026},
  note         = {Retrieved 2026-09-23. CC BY 4.0; underlying data from the producers named on each chart}
}""",
    )
    dataset(
        id="fivethirtyeight", name="FiveThirtyEight data repository", tasks=["DAT-4"],
        homepage="https://github.com/fivethirtyeight/data", license="CC-BY-4.0",
        license_url=f"https://github.com/fivethirtyeight/data/blob/{FTE_COMMIT}/LICENSE",
        content=("Fifteen values from one column of a CSV in FiveThirtyEight's data repository (weather, librarians, "
                 "comic characters, talk-show guests, film budgets, college majors, police, airline safety, drivers), "
                 "with the file's other headers."),
        content_license="CC-BY-4.0",
        content_terms=("The repository README states that, unless otherwise noted, the data sets are available under "
                       "CC BY 4.0 (github.com/fivethirtyeight/data/blob/master/README.md); none of the folders used "
                       "notes otherwise. The values are factual records compiled by FiveThirtyEight from public sources."),
        labelled_by="a written mapping from the column's real header to one of seven meanings (MAPPING in the module)",
        changes="The header of the shown column is hidden; values are shown verbatim, 15 per row in a fixed hash order.",
        selection=("Nine CSVs chosen by hand; per file the unambiguously mapped headers in sha256 order, at most three; "
                   "values are the first 15 non-empty cells in sha256 order of the row index."),
        citation=f"FiveThirtyEight. Data and code behind the articles and graphics at FiveThirtyEight. "
                 f"github.com/fivethirtyeight/data, commit {FTE_COMMIT[:7]}.",
        bibtex=f"""@misc{{fivethirtyeight_data,
  title        = {{Data and code behind the articles and graphics at FiveThirtyEight}},
  author       = {{{{FiveThirtyEight}}}},
  howpublished = {{\\url{{https://github.com/fivethirtyeight/data}}}},
  year         = {{2025}},
  note         = {{Commit {FTE_COMMIT}, CC BY 4.0}}
}}""",
    )
    dataset(
        id="congress-legislators", name="congress-legislators (legislators-current.csv)", tasks=["DAT-4"],
        homepage="https://github.com/unitedstates/congress-legislators", license="CC0-1.0",
        license_url=f"https://github.com/unitedstates/congress-legislators/blob/{LEG_COMMIT}/LICENSE",
        content=("Fifteen values from one column of legislators-current.csv, the public roster of current members of "
                 "the United States Congress maintained by the @unitedstates project, with the file's other headers."),
        content_license="CC0-1.0",
        content_terms=("The project dedicates the data to the public domain under CC0 1.0 (LICENSE file); the values "
                       "are public official records (birth dates, parties, states, government identifiers)."),
        labelled_by="a written mapping from the column's real header to one of seven meanings (MAPPING in the module)",
        changes="The header of the shown column is hidden; values are shown verbatim, 15 per row in a fixed hash order.",
        selection="Mapped headers in sha256 order, at most three; values are the first 15 non-empty cells in sha256 "
                  "order of the row index.",
        citation=f"The @unitedstates project. congress-legislators. github.com/unitedstates/congress-legislators, "
                 f"gh-pages commit {LEG_COMMIT[:7]}.",
        bibtex=f"""@misc{{congress_legislators,
  title        = {{congress-legislators: Members of the United States Congress, 1789-Present}},
  author       = {{{{The @unitedstates project}}}},
  howpublished = {{\\url{{https://github.com/unitedstates/congress-legislators}}}},
  year         = {{2026}},
  note         = {{Commit {LEG_COMMIT}, CC0 1.0}}
}}""",
    )
    dataset(
        id="fiscal-data", name="U.S. Treasury Fiscal Data", tasks=["DAT-4"],
        homepage="https://fiscaldata.treasury.gov/", license="Public domain",
        license_url="https://fiscaldata.treasury.gov/api-documentation/#license-and-authorization",
        content=("Fifteen values from one column of a Fiscal Data API CSV (Debt to the Penny, January–March 2024; "
                 "Treasury Reporting Rates of Exchange, 31 March 2024), with the file's other headers."),
        content_license="Public domain",
        content_terms=("Fiscal Data's API documentation, section License and Authorization: the data is offered free, "
                       "without restriction, and available to copy, adapt, redistribute or otherwise use for "
                       "non-commercial or commercial purposes. The values are U.S. government works (17 U.S.C. § 105)."),
        labelled_by="a written mapping from the column's real header to one of seven meanings (MAPPING in the module)",
        changes="The header of the shown column is hidden; values are shown verbatim, 15 per row in a fixed hash order.",
        selection="Two API extracts with fixed date filters; mapped headers in sha256 order, at most three per file.",
        citation="U.S. Department of the Treasury, Bureau of the Fiscal Service. Fiscal Data: Debt to the Penny; "
                 "Treasury Reporting Rates of Exchange. fiscaldata.treasury.gov, retrieved 2026-09-23.",
        bibtex="""@misc{fiscal_data,
  title        = {Fiscal Data: Debt to the Penny; Treasury Reporting Rates of Exchange},
  author       = {{U.S. Department of the Treasury, Bureau of the Fiscal Service}},
  howpublished = {\\url{https://fiscaldata.treasury.gov/}},
  year         = {2024},
  note         = {Retrieved 2026-09-23. Public domain (U.S. government work)}
}""",
    )
    dataset(
        id="federal-register", name="Federal Register documents API", tasks=["DAT-4"],
        homepage="https://www.federalregister.gov/developers/documentation/api/v1", license="Public domain",
        license_url="https://www.govinfo.gov/about/policies#copyright",
        content=("Fifteen values from one column of the Federal Register API's CSV listing of the documents published "
                 "on one day (title, type, abstract, document number), with the file's other headers."),
        content_license="Public domain",
        content_terms=("The Federal Register is published by the Office of the Federal Register and the Government "
                       "Publishing Office; GPO's Public Domain & Copyright Notice cites 17 U.S.C. § 105: copyright "
                       "protection is not available for any work of the United States Government, so public documents "
                       "can generally be reprinted without legal restriction."),
        labelled_by="a written mapping from the column's real header to one of seven meanings (MAPPING in the module)",
        changes="The header of the shown column is hidden; values are shown verbatim, 15 per row in a fixed hash order.",
        selection="Two publication days (2024-03-01 and 2024-09-03), first 60 documents each in the API's oldest-first "
                  "order; mapped headers in sha256 order, at most three per file.",
        citation="Office of the Federal Register. Federal Register API v1, documents.csv. federalregister.gov, "
                 "retrieved 2026-09-23.",
        bibtex="""@misc{federal_register_api,
  title        = {Federal Register API, version 1},
  author       = {{Office of the Federal Register, National Archives and Records Administration}},
  howpublished = {\\url{https://www.federalregister.gov/developers/documentation/api/v1}},
  year         = {2024},
  note         = {Retrieved 2026-09-23. Public domain (U.S. government work)}
}""",
    )


# ---------------------------------------------------------------- DAT-1  Spider

DB_NAMES = {
    "concert_singer": "concert singers", "pets_1": "students and pets", "car_1": "car makers and models",
    "flight_2": "airlines and flights", "employee_hire_evaluation": "shops and employees",
    "cre_Doc_Template_Mgt": "documents and templates", "course_teach": "courses and teachers",
    "museum_visit": "museum visits", "wta_1": "tennis players and matches", "battle_death": "battles and ships",
    "tvshow": "TV channels and series", "voter_1": "contestants and votes", "world_1": "world countries and cities",
    "orchestra": "orchestras and conductors", "network_1": "high-school friendships", "dog_kennels": "dog kennels",
    "real_estate_properties": "real-estate properties",
}
DAT1_TARGET, DAT1_PER_DB, DAT1_QUERY_MAX, DAT1_QUESTION_MAX = 30, 3, 220, 160
# dev.json index -> reason for passing over the record.
DAT1_SKIP = {
    819: "Spider's gold for 'Count the number of countries for which Spanish is the predominantly spoken language' "
         "(SELECT count(*), max(Percentage) ... GROUP BY CountryCode) does not answer the question; a known dev-set error.",
}


def _sig(record):
    """The query's structure from Spider's parsed sql: tables, selected columns (ignoring aggregation), and clauses."""
    sql = record["sql"]
    select = tuple(sorted(json.dumps(c[1][1][1]) for c in sql["select"][1]))
    return json.dumps([sorted(json.dumps(u) for u in sql["from"]["table_units"]), select, sql["where"],
                       sql["groupBy"], sql["having"], sql["orderBy"], sql["limit"], sql["intersect"], sql["union"],
                       sql["except"]], sort_keys=True)


def _schema(db):
    tables = db["table_names_original"]
    cols = [[] for _ in tables]
    pks = set(db["primary_keys"])
    for i, (t, name) in enumerate(db["column_names_original"]):
        if t >= 0:
            cols[t].append(name + ("*" if i in pks else ""))
    fks = []
    for a, b in db["foreign_keys"]:
        ta, ca = db["column_names_original"][a]
        tb, cb = db["column_names_original"][b]
        fks.append(f"{tables[ta]}.{ca} -> {tables[tb]}.{cb}")
    return {"tables": [f"{t}({', '.join(c)})" for t, c in zip(tables, cols)], "primary_keys_marked": "*",
            "foreign_keys": fks}


def _short(text, limit=160):
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def _dat1():
    dev = json.loads((SOURCE_DIR / "spider/dev.json").read_text(encoding="utf-8"))
    schemas = {t["db_id"]: t for t in json.loads((SOURCE_DIR / "spider/tables.json").read_text(encoding="utf-8"))}
    records = [dict(index=i, **r) for i, r in enumerate(dev)]
    by_db = {}
    for r in records:
        by_db.setdefault(r["db_id"], []).append(r)
    ok = {db for db, t in schemas.items() if 3 <= len(t["table_names_original"]) <= 8}
    assert ok & set(by_db) <= set(DB_NAMES), sorted((ok & set(by_db)) - set(DB_NAMES))
    per_db, used, picked = {}, set(), []
    for r in sorted(records, key=lambda r: rank(f"spider-dev-{r['index']}")):
        if r["db_id"] not in ok or per_db.get(r["db_id"], 0) >= DAT1_PER_DB:
            continue
        if len(r["query"]) > DAT1_QUERY_MAX or len(r["question"]) > DAT1_QUESTION_MAX:
            continue
        gold_sig = _sig(r)
        if gold_sig in used:
            continue
        pool = [o for o in by_db[r["db_id"]] if o["index"] != r["index"] and o["question"] != r["question"]
                and _sig(o) != gold_sig and len(o["query"]) <= DAT1_QUERY_MAX]
        distractors, seen = [], {gold_sig}
        for o in sorted(pool, key=lambda o: rank(f"spider-dev-{r['index']}-{o['index']}")):
            if _sig(o) in seen:
                continue
            seen.add(_sig(o))
            distractors.append(o)
            if len(distractors) == 3:
                break
        if len(distractors) < 3:
            continue
        if r["index"] in DAT1_SKIP:
            continue
        used.add(gold_sig)
        per_db[r["db_id"]] = per_db.get(r["db_id"], 0) + 1
        picked.append((r, distractors))
        if len(picked) == DAT1_TARGET:
            break
    assert len(picked) == DAT1_TARGET, len(picked)

    for r, distractors in picked:
        candidates = sorted([r, *distractors], key=lambda o: rank(f"spider-dev-{r['index']}:{o['index']}"))
        keys = {o["index"]: f"q{k}" for k, o in enumerate(candidates, 1)}
        gold = keys[r["index"]]
        others = "; ".join(f"{keys[o['index']]} is the gold SQL for “{o['question'].strip()}”" for o in distractors)
        row("DAT-1", f"dev-{r['index']}",
            title=f"Spider · {DB_NAMES[r['db_id']]} database · dev question {r['index']}",
            state={"database": r["db_id"], "schema": _schema(schemas[r["db_id"]]), "question": r["question"].strip(),
                   "candidate_queries": {keys[o["index"]]: o["query"].strip() for o in candidates}},
            options={keys[o["index"]]: _short(o["query"]) for o in candidates},
            gold=gold,
            rationale=(f"Spider's gold SQL for this question is {gold}. The other three are Spider's gold SQL for "
                       f"different questions about the same database: {others}."),
            source={"dataset_id": "spider", "dataset": "Spider (dev set)", "license": "CC-BY-SA-4.0",
                    "url": f"https://github.com/taoyds/spider/blob/{SPIDER_COMMIT}/evaluation_examples/examples/dev.json",
                    "citation": "Yu et al., Spider, EMNLP 2018.", "record_id": f"dev.json[{r['index']}]",
                    "original_label": r["query"].strip(),
                    "labelled_by": "the Spider annotators' gold SQL for the question"},
            note=f"Database {r['db_id']} has {len(schemas[r['db_id']]['table_names_original'])} tables.",
            tags=["sql", r["db_id"]])


# ---------------------------------------------------------------- DAT-2  WikiTableQuestions

DAT2_TARGET = 30
COUNT_WORDS = re.compile(r"\b(how many|how much|how may|number of|total|how long|difference|average|sum)\b")
# example id -> reason for passing over the example (records that survive the written filters).
DAT2_SKIP = {
    "nu-4017": "the Contestant cells merge two lines (name, then age and occupation), so the option text is garbled "
               "('Aleksandr Byalko 50.the physicist').",
    "nu-4271": "the question says 'the only administrator to have just a B.S.' but two rows do (Sikandar Zaman, "
               "'Bachelor of Science (B.S.)', and Raza Hussain, 'B.S.'); the premise is wrong.",
    "nu-4320": "the Opponent column lists 'New Orleans Saints' and 'at New Orleans Saints'; both would be offered and "
               "both name the team asked for.",
}


def _norm(s):
    return " ".join(s.split()).lower()


def _wtq_table(path):
    text = (SOURCE_DIR / "wikitablequestions" / path).read_text(encoding="utf-8")
    rows = list(csv.reader(io.StringIO(text), escapechar="\\", doublequote=False))
    return rows[0], rows[1:]


def _dat2():
    tsv = (SOURCE_DIR / "wikitablequestions/pristine-unseen-tables.tsv").read_text(encoding="utf-8")
    examples = list(csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE))
    examples.sort(key=lambda e: rank(e["id"]))
    listed = set(WTQ_TABLES)
    seen, picked = set(), []
    for e in examples:
        answer, question = e["targetValue"].strip(), e["utterance"].strip()
        if e["context"] in seen or "|" in answer or COUNT_WORDS.search(question.lower()) \
                or re.fullmatch(r"[\d.,\-]+", answer):
            continue
        if e["context"] not in listed:
            break
        seen.add(e["context"])
        header, body = _wtq_table(e["context"])
        if not 5 <= len(body) <= 25 or len(header) > 8:
            continue
        hits = [(i, j) for i, r in enumerate(body) for j, c in enumerate(r) if _norm(c) == _norm(answer)]
        cols = {j for _, j in hits}
        if len(cols) != 1:
            continue
        j = cols.pop()
        others = sorted({_norm(r[j]) for r in body if j < len(r) and _norm(r[j]) and _norm(r[j]) != _norm(answer)})
        if len(others) < 3 or _norm(answer) in _norm(question):
            continue
        if e["id"] in DAT2_SKIP:
            continue
        picked.append((e, header, body, j, [i for i, _ in hits]))
        if len(picked) == DAT2_TARGET:
            break
    assert len(picked) == DAT2_TARGET, len(picked)

    for e, header, body, j, hit_rows in picked:
        answer = e["targetValue"].strip()
        # Distractors: other distinct values of the answer's column, by hash order; shown with their original text.
        originals = {}
        for r in body:
            if j < len(r) and _norm(r[j]) and _norm(r[j]) != _norm(answer):
                originals.setdefault(_norm(r[j]), " ".join(r[j].split()))
        distractors = sorted(originals, key=lambda v: rank(f"{e['id']}:{v}"))[:3]
        values = sorted([answer, *(originals[v] for v in distractors)], key=lambda v: rank(f"{e['id']}:opt:{v}"))
        keys = {v: f"cell_{k}" for k, v in enumerate(values, 1)}
        col = " ".join(header[j].split())
        where = ", ".join(str(i + 1) for i in hit_rows)
        row("DAT-2", e["id"],
            title=f"Wikipedia table · {len(body)} rows × {len(header)} columns · question {e['id']}",
            state={"table": {"columns": header, "rows": body}, "question": e["utterance"].strip()},
            options={keys[v]: _short(v) for v in values},
            gold=keys[answer],
            rationale=(f"The dataset's answer is the cell “{answer}” in column “{col}” (row {where} of the table); "
                       f"the other options are other values of that column."),
            source={"dataset_id": "wikitablequestions", "dataset": "WikiTableQuestions (test set)",
                    "license": "CC-BY-SA-4.0",
                    "url": f"https://github.com/ppasupat/WikiTableQuestions/blob/{WTQ_COMMIT}/{e['context']}",
                    "citation": "Pasupat and Liang, ACL 2015.", "record_id": e["id"], "original_label": answer,
                    "labelled_by": "the crowd worker who wrote the question, as recorded in targetValue"},
            note=f"Table {e['context']}; the answer column is “{col}”.",
            tags=["table-qa"])


# ---------------------------------------------------------------- DAT-3  Our World in Data

DAT3_RATIO, DAT3_TREND, DAT3_SLACK, DAT3_GAP, DAT3_SPAN = 1.15, 0.15, 0.05, 10, 0.10


def _owid_series(chart):
    """entity -> {year: value} for the chart's requested countries, from the chart's data column (the first
    non-projection, non-region column). Filtering by ISO code here: charts whose default view is a map return the
    full table from the CSV endpoint."""
    slug, codes = chart["slug"], set(chart["countries"].split("~"))
    t0, t1 = (int(x) for x in chart["time"].split(".."))
    text = (SOURCE_DIR / f"owid/{slug}.csv").read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    fields = reader.fieldnames
    data_cols = [f for f in fields[3:] if not f.endswith("__projected") and f != "owid_region"]
    assert fields[:3] == ["entity", "code", "year"] and data_cols, (slug, fields)
    col = data_cols[0]
    series = {}
    for r in reader:
        if r["code"] in codes and r[col] not in ("", None) and t0 <= int(r["year"]) <= t1:
            series.setdefault(r["entity"], {})[int(r["year"])] = float(r[col])
    return series


def _pos(name):
    """Possessive: Japan's, United States'."""
    return name + ("'" if name.endswith("s") else "'s")


def _fmt(v):
    if abs(v) >= 1e9:
        return f"{v / 1e9:.2f} billion"
    if abs(v) >= 1e6:
        return f"{v / 1e6:.2f} million"
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    return f"{v:.3g}" if abs(v) < 10 else f"{v:,.1f}"


def _claims(chart, series):
    """(claim A, claim B) as dicts with the wording, truth and the data points used, or None if a pattern fails."""
    t0, t1 = (int(x) for x in chart["time"].split(".."))
    years = sorted({y for y in range(t0, t1 + 1) if y % 10 == 0} | {t1})
    entities = sorted(series)
    metric = chart["metric"]
    top = max(v for e in entities for v in series[e].values())  # the chart's y-axis reaches at least this
    clear = lambda a, b: abs(a - b) >= DAT3_SPAN * top  # visible at a glance
    a_truth = int(rank(f"{chart['slug']}:truth"), 16) % 2 == 0
    # A: comparison in one year
    cands = []
    for y in years:
        for x in entities:
            for z in entities:
                if x != z and y in series[x] and y in series[z] and series[z][y] > 0 \
                        and series[x][y] / series[z][y] >= DAT3_RATIO and clear(series[x][y], series[z][y]):
                    cands.append((y, x, z))
    if not cands:
        return None
    y, hi, lo = min(cands, key=lambda c: rank(f"{chart['slug']}:A:{c[0]}:{c[1]}:{c[2]}"))
    first, second = (hi, lo) if a_truth else (lo, hi)
    claim_a = dict(claim=f"In {y}, {_pos(first)} {metric} was higher than {_pos(second)}.", truth=a_truth,
                   points={hi: {str(y): series[hi][y]}, lo: {str(y): series[lo][y]}},
                   evidence=(f"In {y} the chart's data give {hi} {_fmt(series[hi][y])} and {lo} "
                             f"{_fmt(series[lo][y])} {chart['unit']}"))
    # B: rise or fall between two years
    cands = []
    for x in entities:
        for y1 in years:
            for y2 in years:
                if y2 - y1 < DAT3_GAP or y1 not in series[x] or y2 not in series[x]:
                    continue
                v1, v2 = series[x][y1], series[x][y2]
                between = [v for yy, v in series[x].items() if y1 <= yy <= y2]
                if not clear(v1, v2):
                    continue
                if v1 > 0 and v2 >= v1 * (1 + DAT3_TREND) and max(between) <= v2 * (1 + DAT3_SLACK) \
                        and min(between) >= v1 * (1 - DAT3_SLACK):
                    cands.append((x, y1, y2, "rose"))
                elif v1 > 0 and v2 <= v1 * (1 - DAT3_TREND) and min(between) >= v2 * (1 - DAT3_SLACK) \
                        and max(between) <= v1 * (1 + DAT3_SLACK):
                    cands.append((x, y1, y2, "fell"))
    if not cands:
        return None
    x, y1, y2, direction = min(cands, key=lambda c: rank(f"{chart['slug']}:B:{c[0]}:{c[1]}:{c[2]}"))
    b_truth = not a_truth
    said = direction if b_truth else {"rose": "fell", "fell": "rose"}[direction]
    v1, v2 = series[x][y1], series[x][y2]
    change = (v2 - v1) / v1 * 100
    claim_b = dict(claim=f"{_pos(x)} {metric} {said} between {y1} and {y2}.", truth=b_truth,
                   points={x: {str(y1): v1, str(y2): v2}},
                   evidence=(f"The chart's data give {x} {_fmt(v1)} {chart['unit']} in {y1} and {_fmt(v2)} in {y2}, "
                             f"a {'rise' if change > 0 else 'fall'} of {abs(change):.0f}%"))
    return claim_a, claim_b


def _dat3():
    assets_dir = ASSETS / "data"
    built = 0
    for chart in CHARTS:
        if built == DAT3_CHARTS:
            break
        series = _owid_series(chart)
        assert len(series) == 4, (chart["slug"], sorted(series))
        claims = _claims(chart, series)
        if claims is None:
            continue
        built += 1
        src_png = SOURCE_DIR / f"owid/{chart['slug']}.png"
        png = assets_dir / f"dat-3-{chart['slug']}.png"
        if not png.is_file():
            png.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src_png, png)
        width, height = _png_size(png)
        assert max(width, height) <= 1600 and png.stat().st_size <= 400_000, chart["slug"]
        t0, t1 = (int(x) for x in chart["time"].split(".."))
        entities = sorted(series)
        sampled = {e: {str(y): v for y, v in sorted(series[e].items()) if y % 10 == 0 or y == max(series[e])}
                   for e in entities}
        url = f"{OWID}{chart['slug']}?tab=chart&country=~{chart['countries']}&time={chart['time']}"
        for label, c in zip("AB", claims):
            gold = "supported" if c["truth"] else "not_supported"
            row("DAT-3", f"{chart['slug']}-{label.lower()}",
                title=f"OWID chart · {chart['title']} · {', '.join(entities)} · claim {label}",
                state={
                    "chart": {"title": chart["title"], "unit": chart["unit"], "type": "line chart, one line per country",
                              "countries": entities, "years": f"{t0}–{t1}", "data_source": chart["source"],
                              "publisher": "Our World in Data (CC BY)"},
                    "claim": c["claim"],
                    "claim_origin": "templated from the chart's data by the benchmark, not written by OWID",
                    "text_rendering": {"data_points_used_by_the_claim": c["points"],
                                       "series_sampled_every_10_years": sampled},
                },
                gold=gold,
                rationale=f"{c['evidence']}, so the claim is {'supported' if c['truth'] else 'not supported'}.",
                source={"dataset_id": "owid-grapher", "dataset": "Our World in Data grapher charts",
                        "license": "CC-BY-4.0", "url": url,
                        "citation": f"Our World in Data; data: {chart['source']}.",
                        "record_id": f"{chart['slug']}?country={chart['countries']}&time={chart['time']}#{label}",
                        "original_label": f"claim {'true' if c['truth'] else 'false'} by rule",
                        "labelled_by": "a written rule comparing the claim with the chart's CSV values"},
                assets=[{"path": str(png.relative_to(ROOT)), "mime_type": "image/png",
                         "alt_text": (f"Line chart from Our World in Data titled “{chart['title']}”, one line each for "
                                      f"{', '.join(entities)}, years {t0} to {t1}, values in {chart['unit']}."),
                         "width": width, "height": height}],
                note=f"Chart: {url}",
                tags=["chart", "templated-claim"])
    assert built == DAT3_CHARTS, built


# ---------------------------------------------------------------- DAT-4  open-data columns

def _read_csv(path):
    text = (SOURCE_DIR / path).read_text(encoding="utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    return rows[0], [r for r in rows[1:] if any(c.strip() for c in r)]


def _dat4():
    for key, (dataset_id, label, url, path) in FILES.items():
        header, body = _read_csv(path)
        mapping = MAPPING[key]
        missing = set(mapping) - set(header)
        assert not missing, f"DAT-4 {key}: headers {sorted(missing)} not in file"
        chosen = sorted(mapping, key=lambda h: rank(f"{key}:{h}"))[:DAT4_PER_FILE]
        order = sorted(range(len(body)), key=lambda i: rank(f"{key}:{i}"))
        for h in chosen:
            j = header.index(h)
            values = []
            for i in order:
                v = body[i][j].strip() if j < len(body[i]) else ""
                if v and v not in ("**", "NA", "N/A"):
                    values.append(v)
                if len(values) == DAT4_VALUES:
                    break
            assert len(values) == DAT4_VALUES, (key, h, len(values))
            others = [c for c in header if c != h]
            d = _DATASET_NAMES[dataset_id]
            row("DAT-4", f"{key}-{j}",
                title=f"CSV column · {label} · column {j + 1} of {len(header)}",
                state={"file": label, "columns_in_file": len(header), "other_headers": others,
                       "hidden_column_position": j + 1, "values_from_the_hidden_column": values},
                gold=mapping[h],
                rationale=(f"The hidden header is “{h}”, which the written mapping classes as "
                           f"{mapping[h].replace('_', ' ')}; the values are shown verbatim from the file."),
                source={"dataset_id": dataset_id, "dataset": d["name"], "license": d["license"], "url": url,
                        "citation": d["citation"], "record_id": f"{path}#{h}", "original_label": h,
                        "labelled_by": "a written mapping from the file's real header to one of seven meanings"},
                note=f"File: {url}",
                tags=["column-typing", dataset_id])


_DATASET_NAMES = {
    "fivethirtyeight": dict(name="FiveThirtyEight data repository", license="CC-BY-4.0",
                            citation="FiveThirtyEight data repository, github.com/fivethirtyeight/data."),
    "congress-legislators": dict(name="congress-legislators (legislators-current.csv)", license="CC0-1.0",
                                 citation="The @unitedstates project, congress-legislators."),
    "fiscal-data": dict(name="U.S. Treasury Fiscal Data", license="Public domain",
                        citation="U.S. Treasury, Bureau of the Fiscal Service, Fiscal Data."),
    "federal-register": dict(name="Federal Register documents API", license="Public domain",
                             citation="Office of the Federal Register, Federal Register API v1."),
}


# ---------------------------------------------------------------- tasks

def define():
    _datasets()
    task("DAT-1", category="data", name="Which SQL answers the question?",
         ask="Which query answers the question on this schema?",
         instruction=("The record is a relational database schema (tables with their columns, primary keys starred, "
                      "foreign keys listed), a question in plain English, and four SQL queries written for this "
                      "database. Exactly one of the queries answers the question; the others answer different "
                      "questions. Read each query against the schema and pick the one whose result is what the "
                      "question asks for."),
         options={}, per_row_options=True,
         shape="locate", input_type="database schema, question and SQL queries", modality="text",
         expertise="practitioner", contamination="high", label_origin="objective record")
    _dat1()
    task("DAT-2", category="data", name="Which cell answers the question?",
         ask="Which value is the answer to the question?",
         instruction=("The record is a table (its column headers and rows, in their original order) and a question "
                      "about it. The answer is a single value that appears in the table. Four values from the table "
                      "are offered; pick the one that answers the question."),
         options={}, per_row_options=True,
         shape="locate", input_type="table and question", modality="text", expertise="none",
         contamination="high", label_origin="crowd")
    _dat2()
    task("DAT-3", category="data", name="Does the chart support the claim?",
         ask="Do the chart's data support the claim?",
         instruction=("The image is a line chart from Our World in Data with one line per country. The claim was "
                      "produced by the benchmark from the chart's own data using a fixed template (a comparison "
                      "between two countries in one year, or a rise or fall for one country between two years); it "
                      "is not a statement by the chart's authors. Decide whether the chart supports the claim. The "
                      "text rendering lists the data points the claim refers to and the series sampled every ten "
                      "years, so the row can also be decided from the text."),
         options={"supported": "The chart's data show what the claim says.",
                  "not_supported": "The chart's data show the opposite of what the claim says."},
         shape="verify", input_type="chart image and templated claim", modality="text+image", expertise="none",
         contamination="low", label_origin="derived by rule")
    _dat3()
    task("DAT-4", category="data", name="What does this column hold?",
         ask="What kind of value does the hidden column hold?",
         instruction=("The record is one column of an open-data CSV file with its header hidden: fifteen of its "
                      "values, plus the headers of the file's other columns for context. Decide what kind of value "
                      "the hidden column holds. Numbers that are amounts of money are 'money'; other numbers are "
                      "'count or measurement'; codes that identify a record are 'identifier'; a small set of "
                      "repeating labels is 'category'; place names or codes are 'geography'; sentences are 'free text'."),
         options=DAT4_OPTIONS,
         shape="classify", input_type="CSV column values", modality="text", expertise="none",
         contamination="low", label_origin="derived by rule")
    _dat4()
