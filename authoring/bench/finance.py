"""finance: SEC filings, receipts and financial sentences.

FIN-1  Which part of the 10-K is this from?  A 600–2,000 character passage from one of five sections of an annual
       report (Item 1 Business, 1A Risk Factors, 3 Legal Proceedings, 7 MD&A, 9A Controls and Procedures), read from
       EDGAR-CORPUS (Loukas et al. 2021; Apache-2.0; the filings themselves are US public records). The answer is the
       section the passage was split into by the corpus, i.e. the filing's own item heading.
FIN-2  What does this 8-K report?  The body of a current report filed with the SEC in the week of 4–8 March 2024, with
       the "Item X.XX" heading lines removed, classified as results of operations (2.02), an officer or director change
       (5.02), a material agreement (1.01), a Regulation FD or other event (7.01/8.01) or a shareholder vote (5.07).
       The answer is the item number the filer put on the filing (EDGAR's own item list).
FIN-3  Which figure is the total?  (image) A photo of an Indonesian shop or restaurant receipt from CORD-v2 (Clova
       AI; CC BY 4.0) with four or five monetary figures printed on it offered as options; the answer is the figure the
       CORD annotators labelled total.total_price. The state carries the annotated words in reading order.
FIN-5  What does this number report?  One sentence from a 10-K/10-Q in FiNER-139 (Loukas et al. 2022; CC BY-SA 4.0)
       with exactly one XBRL-tagged dollar amount, marked [[like this]]; six plain-words options stand for groups of
       XBRL elements (revenue, goodwill, borrowings, share-based compensation, income tax, amortization of
       intangibles). The answer is the element the company itself tagged the amount with.

Dropped: FIN-4 "Which value answers the question?" (TAT-QA). The dataset is CC BY 4.0 and the code MIT, but the
paper (Zhu et al. 2021, §2.1) says the tables and paragraphs were taken from about 500 annual reports downloaded from
annualreports.com; those reports are the companies' own copyrighted documents, many from outside the US, and no
licence for redistributing their text could be established. See the finance report.

Deviations from the brief, for the maintainer
- EDGAR-CORPUS on Hugging Face (eloukas/edgar-corpus) is a loading-script dataset whose per-year files are 180 MB
  to 1.4 GB, so the rows are read through the datasets-server rows API from c3po-ai/edgar-corpus, a Parquet copy that
  Hugging Face marks "Duplicated from eloukas/edgar-corpus" (same Apache-2.0 card). One 10-K per window, 42 windows.
- FiNER-139's 139 elements do not include net income, total assets or cash and equivalents (it tags amounts that
  appear in narrative sentences), and shares-outstanding sentences almost always carry two tagged numbers. The
  options are therefore the six FiNER groups above, chosen for being plain concepts a practitioner can tell apart
  and for having enough single-amount sentences in 12,000 test rows (interest expense had only two clean ones and
  was left out; the debt elements DebtInstrumentFaceAmount, LongTermDebt, LineOfCredit and
  DebtInstrumentCarryingAmount are merged into "borrowings" because filers use them interchangeably).
- The 8-K filings are fetched from SEC EDGAR itself (there is no open 8-K corpus with item labels); their item
  numbers come from EDGAR's full-text search index, which mirrors the filer's own cover-page item list, and are
  cross-checked against the "Item X.XX" headings parsed from the document.

Written sampling rules
- FIN-1: one 10-K per rows-API window (test split of year_2015 … year_2020, offsets 0, 90, …, 540; 42 filings),
  ordered by rank(filename); one row per CIK. A section yields a passage when, starting at the paragraph that
  contains the 30% point of the section (the first paragraph when the section is under 2,000 characters), a run of
  consecutive prose paragraphs (≥ 60 characters, ≤ 12% digits, ≥ 65% letters, ending in sentence punctuation other
  than a colon) reaches 600 characters without exceeding 2,000; the run stops at 1,200. The section heading lines
  ("Item 1A." / "Risk Factors") are removed first, and a passage is rejected if it mentions its own item number or
  its own section title. Each filer is given the section with the fewest rows so far among those that yield a
  passage and are not in FIN1_SKIP (ties in the order 1, 1A, 3, 7, 9A); six rows per section.
- FIN-2: EDGAR full-text search, forms 8-K, filed 2024-03-04 to 2024-03-08, one query per item number
  ("Item 2.02", …, "Item 8.01"). Hits kept when the form is a plain 8-K (no 8-K/A), a single filer, and the items
  other than 9.01 are exactly {2.02}, {5.02}, {1.01} or {1.01, 2.03}, {7.01}/{8.01}/{7.01, 8.01}, or {5.07}; one
  filing per CIK; the first nine per option by rank(accession number) were downloaded, and the first six per option
  that are not in FIN2_SKIP are rows. The state shows only the sections of the option's own items: the 9.01 exhibit
  list and the 2.03 cross-reference ("the information in Item 1.01 is incorporated by reference") are dropped, the
  heading line and official item title are removed, and in-body references to item numbers are redacted to
  "Item [number removed]". Nothing else is changed.
- FIN-3: CORD-v2 test split (100 receipts, all fetched), ordered by rank("cord-v2-test-<image_id>"). Kept when the
  photo's longest side is at least 800 px, the parse has a single total.total_price whose digits appear among the
  annotated words only in total-type fields (total_price, cashprice, creditcardprice, emoneyprice), at least three
  other distinct monetary figures of 100 or more are printed, and 8–120 words are annotated. Options are the total
  and the first four other distinct figures by rank("<image_id>:<digits>"), each keyed by the text as printed.
  First 30. The image is resized (never enlarged) so its longest side is at most 1,600 px and re-encoded as JPEG
  under 400 KB (macOS sips on the authoring machine).
- FIN-5: FiNER-139 test split, 120 consecutive 100-row windows (rows 0–11,999), ordered by rank(id). Kept when the
  sentence has exactly one B- tag and no I- tag, the tagged token is a number immediately preceded by "$", the tag is
  in one of the six groups, the sentence is 12–120 tokens and at most 700 characters, and the id is not in
  FIN5_SKIP. Up to six rows per group, in rank order.
"""
from __future__ import annotations

import html
import json
import re
import shutil
import struct
import subprocess
from html.parser import HTMLParser
from pathlib import Path

from . import dataset, task, row, rank, ROOT, SOURCES as SOURCE_DIR, ASSETS

CATEGORY = "finance"
UA_NOTE = "SEC EDGAR asks automated clients to send a User-Agent header; scripts/fetch_sources.py does."

# ---------------------------------------------------------------- upstream files

HF_ROWS = "https://datasets-server.huggingface.co/rows?dataset={ds}&config={config}&split={split}&offset={off}&length={n}"

EDGAR_MIRROR = "c3po-ai%2Fedgar-corpus"        # Parquet duplicate of eloukas/edgar-corpus (see module docstring)
EDGAR_MIRROR_SHA = "5b6b152615afae7042778a79d25aa810091a74c7"
EDGAR_CORPUS_SHA = "7e90f0f342569b35213445f809cfaf3b91f9964f"
CORD_SHA = "7f0115a4b758a71d6473b8d085751692da2fef98"
FINER_SHA = "080f677a026e304c38666d759ef625d621dc8cb9"

FIN1_YEARS = range(2015, 2021)
FIN1_OFFSETS = range(0, 541, 90)
FIN3_OFFSETS = range(0, 100, 10)
FIN5_OFFSETS = range(0, 12000, 100)

SOURCES = []
SOURCES += [{"dataset": "EDGAR-CORPUS",
             "url": HF_ROWS.format(ds=EDGAR_MIRROR, config=f"year_{y}", split="test", off=off, n=1),
             "path": f"edgar-corpus/year_{y}-test-{off:04d}.json"} for y in FIN1_YEARS for off in FIN1_OFFSETS]
SOURCES += [{"dataset": "CORD-v2",
             "url": HF_ROWS.format(ds="naver-clova-ix%2Fcord-v2", config="default", split="test", off=off, n=10),
             "path": f"cord-v2/test-{off:03d}.json"} for off in FIN3_OFFSETS]
SOURCES += [{"dataset": "FiNER-139",
             "url": HF_ROWS.format(ds="nlpaueb%2Ffiner-139", config="finer-139", split="test", off=off, n=100),
             "path": f"finer-139/test-{off:05d}.json"} for off in FIN5_OFFSETS]

# cik -> (EDGAR conformed name, SIC description), read from data.sec.gov/submissions/CIK##########.json on 2026-09-23
FIN1_FILERS = {
    "3570": ("Cheniere Energy, Inc.", "Natural Gas Distribution"),
    "21076": ("CLOROX CO /DE/", "Specialty Cleaning, Polishing and Sanitation Preparations"),
    "26172": ("CUMMINS INC", "Engines & Turbines"),
    "69633": ("NAPCO SECURITY TECHNOLOGIES, INC", "Communications Equipment, NEC"),
    "93676": ("STARRETT L S CO", "Cutlery, Handtools & General Hardware"),
    "351569": ("Ameris Bancorp", "State Commercial Banks"),
    "720858": ("INVESTORS TITLE CO", "Title Insurance"),
    "771266": ("KOPIN CORP", "Semiconductors & Related Devices"),
    "880984": ("ACORN ENERGY, INC.", "Services-Engineering Services"),
    "930810": ("RECKSON OPERATING PARTNERSHIP LP", "Real Estate Investment Trusts"),
    "944745": ("CIVISTA BANCSHARES, INC.", "State Commercial Banks"),
    "1019787": ("PURADYN FILTER TECHNOLOGIES INC", "Motor Vehicle Parts & Accessories"),
    "1042642": ("DISH DBS CORP", "Communications Services, NEC"),
    "1051470": ("CROWN CASTLE INC.", "Real Estate Investment Trusts"),
    "1172318": ("Asia Interactive Media Inc.", "Blank Checks"),
    "1235468": ("LIQUIDITY SERVICES INC", "Services-Business Services, NEC"),
    "1266806": ("Vivani Medical, Inc.", "Electromedical & Electrotherapeutic Apparatus"),
    "1280784": ("Hercules Capital, Inc.", ""),
    "1282723": ("MEWBOURNE ENERGY PARTNERS 05-A LP", "Crude Petroleum & Natural Gas"),
    "1288403": ("W&T OFFSHORE INC", "Crude Petroleum & Natural Gas"),
    "1311828": ("Independence Bancshares, Inc.", "National Commercial Banks"),
    "1331463": ("Federal Home Loan Bank of Boston", "Federal & Federally-Sponsored Credit Agencies"),
    "1341235": ("Aldeyra Therapeutics, Inc.", "Pharmaceutical Preparations"),
    "1389128": ("Frontier Long/Short Commodity Fund", "Commodity Contracts Brokers & Dealers"),
    "1420720": ("iBio, Inc.", "Pharmaceutical Preparations"),
    "1424929": ("FOX FACTORY HOLDING CORP", "Motorcycles, Bicycles & Parts"),
    "1462103": ("MEWBOURNE ENERGY PARTNERS 09-A, L.P.", "Crude Petroleum & Natural Gas"),
    "1483195": ("Oritani Financial Corp", "State Commercial Banks"),
    "1495536": ("Ener-Core, Inc.", "Miscellaneous Chemical Products"),
    "1501862": ("Empire Global Gaming, Inc.", "Games, Toys & Children's Vehicles (No Dolls & Bicycles)"),
    "1514994": ("North Texas Energy, Inc.", "Crude Petroleum & Natural Gas"),
    "1563880": ("Trevi Therapeutics, Inc.", "Pharmaceutical Preparations"),
    "1571283": ("Rexford Industrial Realty, Inc.", "Real Estate Investment Trusts"),
    "1597892": ("JRSIS HEALTH CARE Corp", "Services-Hospitals"),
    "1627469": ("Photozou Holdings, Inc.", "Services-Advertising"),
    "1635298": ("SMART ABS Series 2015-1US Trust", "Asset-Backed Securities"),
    "1650132": ("Four Corners Property Trust, Inc.", "Real Estate Investment Trusts"),
    "1656839": ("GS Mortgage Securities Trust 2015-GS1", "Asset-Backed Securities"),
    "1667313": ("Zedge, Inc.", "Services-Prepackaged Software"),
    "1687229": ("Invitation Homes Inc.", "Real Estate Operators (No Developers) & Lessors"),
    "1699147": ("CNH Equipment Trust 2017-A", "Asset-Backed Securities"),
    "1744659": ("Akero Therapeutics, Inc.", "Pharmaceutical Preparations"),
}

# EDGAR full-text search hits (forms=8-K, filed 2024-03-04..2024-03-08, one query per item number), in rank(adsh) order per
# option: option, accession number, CIK, primary document, EDGAR display name, filing date, date of report, item list.
EIGHT_K = [
    ("results", "0000737758-24-000020", 737758, "ttc-20240307.htm", "TORO CO", "2024-03-07", "2024-03-07", ["2.02", "9.01"]),
    ("results", "0001462418-24-000011", 1462418, "asps-20240307.htm", "ALTISOURCE PORTFOLIO SOLUTIONS S.A.", "2024-03-07", "2024-03-07", ["2.02", "9.01"]),
    ("results", "0001493152-24-009023", 1317945, "form8-k.htm", "Omega Flex, Inc.", "2024-03-06", "2024-03-06", ["2.02", "9.01"]),
    ("results", "0001628280-24-009387", 1044777, "ospn-20240306.htm", "OneSpan Inc.", "2024-03-06", "2024-03-06", ["2.02", "9.01"]),
    ("results", "0001493152-24-009216", 1196298, "form8-k.htm", "NEPHROS INC", "2024-03-07", "2024-03-07", ["2.02", "9.01"]),
    ("results", "0001493152-24-009258", 1600422, "form8-k.htm", "Superior Drilling Products, Inc.", "2024-03-07", "2024-03-07", ["2.02", "9.01"]),
    ("results", "0000950170-24-027592", 1673772, "rapt-20240307.htm", "RAPT Therapeutics, Inc.", "2024-03-07", "2024-03-07", ["2.02", "9.01"]),
    ("results", "0001140361-24-012128", 1228627, "ef20023762_8k.htm", "Ocuphire Pharma, Inc.", "2024-03-08", "2024-03-08", ["2.02", "9.01"]),
    ("results", "0001171843-24-001222", 1123494, "f8k_030724.htm", "HARVARD BIOSCIENCE INC", "2024-03-07", "2024-03-07", ["2.02", "9.01"]),
    ("officer_change", "0000750686-24-000027", 750686, "cac-20240306.htm", "CAMDEN NATIONAL CORP", "2024-03-07", "2024-03-06", ["5.02", "9.01"]),
    ("officer_change", "0001140361-24-011018", 357301, "ef20023348_8k.htm", "TRUSTCO BANK CORP N Y", "2024-03-04", "2024-02-28", ["5.02"]),
    ("officer_change", "0001193125-24-062170", 19871, "d802458d8k.htm", "CHICAGO RIVET & MACHINE CO", "2024-03-07", "2024-03-01", ["5.02"]),
    ("officer_change", "0001874944-24-000014", 1874944, "vcsa-20240305.htm", "Vacasa, Inc.", "2024-03-07", "2024-03-05", ["5.02"]),
    ("officer_change", "0000216085-24-000006", 216085, "hvt-20240304.htm", "HAVERTY FURNITURE COMPANIES INC", "2024-03-05", "2024-03-04", ["5.02"]),
    ("officer_change", "0001193125-24-060717", 1949543, "d804322d8k.htm", "Sitio Royalties Corp.", "2024-03-05", "2024-02-29", ["5.02"]),
    ("officer_change", "0001104659-24-031529", 1053352, "tm248406d1_8k.htm", "HERITAGE COMMERCE CORP", "2024-03-06", "2024-03-06", ["5.02"]),
    ("officer_change", "0001692427-24-000010", 1692427, "ncsm-20240308.htm", "NCS Multistage Holdings, Inc.", "2024-03-08", "2024-03-08", ["5.02"]),
    ("officer_change", "0001193125-24-060861", 1021860, "d724521d8k.htm", "NOV Inc.", "2024-03-06", "2024-03-06", ["5.02", "9.01"]),
    ("agreement", "0001213900-24-020790", 1421636, "ea0201323-8k_cbond.htm", "C-Bond Systems, Inc", "2024-03-07", "2024-03-01", ["1.01", "2.03", "9.01"]),
    ("agreement", "0001193125-24-059517", 1812554, "d794453d8k.htm", "Blue Owl Credit Income Corp.", "2024-03-04", "2024-03-01", ["1.01", "2.03", "9.01"]),
    ("agreement", "0001493152-24-009173", 1552189, "form8-k.htm", "PANACEA LIFE SCIENCES HOLDINGS, INC.", "2024-03-07", "2024-03-05", ["1.01", "2.03"]),
    ("agreement", "0001829126-24-001349", 1823882, "airspan_8k.htm", "Airspan Networks Holdings Inc.", "2024-03-05", "2024-02-28", ["1.01", "2.03", "9.01"]),
    ("agreement", "0001493152-24-008733", 1847986, "form8-k.htm", "Dragonfly Energy Holdings Corp.", "2024-03-05", "2024-01-24", ["1.01", "2.03", "9.01"]),
    ("agreement", "0001144879-24-000053", 1144879, "apld-20240228.htm", "Applied Digital Corp.", "2024-03-05", "2024-02-28", ["1.01", "2.03", "9.01"]),
    ("agreement", "0001104659-24-031881", 69633, "tm248533d1_8k.htm", "NAPCO SECURITY TECHNOLOGIES, INC", "2024-03-07", "2024-03-05", ["1.01", "9.01"]),
    ("agreement", "0001437749-24-006939", 1069533, "rgco20240306_8k.htm", "RGC RESOURCES INC", "2024-03-07", "2024-03-06", ["1.01", "2.03", "9.01"]),
    ("agreement", "0001562088-24-000058", 1562088, "duol-20240304.htm", "Duolingo, Inc.", "2024-03-06", "2024-03-04", ["1.01", "2.03"]),
    ("other", "0000950103-24-003367", 1509991, "dp207805_8k.htm", "Kosmos Energy Ltd.", "2024-03-04", "2024-03-04", ["8.01", "9.01"]),
    ("other", "0000929008-24-000007", 929008, "wcc-20240305.htm", "WESCO INTERNATIONAL INC", "2024-03-05", "2024-03-05", ["7.01", "9.01"]),
    ("other", "0001161697-24-000112", 1438901, "form8k.htm", "Auto Parts 4Less Group, Inc.", "2024-03-06", "2024-03-04", ["7.01", "9.01"]),
    ("other", "0000950170-24-025436", 1666291, "cmtg-20240305.htm", "Claros Mortgage Trust, Inc.", "2024-03-05", "2024-03-05", ["7.01", "9.01"]),
    ("other", "0001280058-24-000017", 1280058, "blkb-20240304.htm", "BLACKBAUD INC", "2024-03-04", "2024-03-04", ["7.01", "8.01", "9.01"]),
    ("other", "0001628280-24-009396", 1839341, "corz-20240306.htm", "Core Scientific, Inc./tx", "2024-03-06", "2024-03-06", ["7.01", "9.01"]),
    ("other", "0001130310-24-000047", 1130310, "cnp-20240306.htm", "CENTERPOINT ENERGY INC", "2024-03-06", "2024-03-06", ["7.01", "9.01"]),
    ("other", "0001193125-24-062567", 1552797, "d799457d8k.htm", "Delek Logistics Partners, LP", "2024-03-07", "2024-03-07", ["8.01", "9.01"]),
    ("other", "0000728391-24-000016", 728391, "ipalco-20240229.htm", "IPALCO ENTERPRISES, INC.", "2024-03-04", "2024-02-29", ["8.01"]),
    ("shareholder_vote", "0000943374-24-000098", 1382230, "form8k.htm", "ESSA Bancorp, Inc.", "2024-03-07", "2024-03-07", ["5.07"]),
    ("shareholder_vote", "0000804328-24-000020", 804328, "qcom-20240305.htm", "QUALCOMM INC/DE", "2024-03-07", "2024-03-05", ["5.07", "9.01"]),
    ("shareholder_vote", "0001140361-24-011464", 1845368, "ef20023634_8k.htm", "HCM Acquisition Corp", "2024-03-05", "2024-03-05", ["5.07", "9.01"]),
    ("shareholder_vote", "0001227654-24-000070", 1227654, "cmp-20240305.htm", "COMPASS MINERALS INTERNATIONAL INC", "2024-03-07", "2024-03-05", ["5.07"]),
    ("shareholder_vote", "0001104659-24-031950", 1633932, "tm248559d1_8k.htm", "ESSA Pharma Inc.", "2024-03-07", "2024-03-06", ["5.07"]),
    ("shareholder_vote", "0001558370-24-002560", 1828588, "hnvr-20240305x8k.htm", "Hanover Bancorp, Inc. /NY", "2024-03-06", "2024-03-05", ["5.07"]),
    ("shareholder_vote", "0001193125-24-062311", 842717, "d813052d8k.htm", "BLUE RIDGE BANKSHARES, INC.", "2024-03-07", "2024-03-06", ["5.07"]),
    ("shareholder_vote", "0001371451-24-000015", 1371451, "form8k.htm", "HIGHWATER ETHANOL LLC", "2024-03-08", "2024-03-07", ["5.07"]),
    ("shareholder_vote", "0000807882-24-000009", 807882, "jack-20240301.htm", "JACK IN THE BOX INC", "2024-03-06", "2024-03-01", ["5.07"]),
]
for _opt, _adsh, _cik, _doc, *_rest in EIGHT_K:
    SOURCES.append({"dataset": "SEC EDGAR 8-K filings",
                    "url": f"https://www.sec.gov/Archives/edgar/data/{_cik}/{_adsh.replace('-', '')}/{_doc}",
                    "path": f"edgar-8k/{_adsh}.htm"})


# ---------------------------------------------------------------- shared helpers

def _company(name):
    """EDGAR conformed names are upper case with state suffixes ('CLOROX CO /DE/'); show them in title case."""
    name = re.sub(r"\s*/\s*[A-Za-z]{2}\s*/?\s*$", "", name).strip()
    small = {"of", "and", "the", "de", "in"}
    keep = {"LLC", "LP", "L.P.", "NY", "USA", "S.A.", "II", "III", "IV", "N.A.", "ABS", "GS", "CNH", "DBS", "NCS", "W&T",
            "RGC", "NOV", "RAPT", "ESSA", "HCM", "IPALCO", "NAPCO", "OneSpan", "iBio", "JRSIS"}
    words = []
    for w in name.split():
        if w.upper() in keep or w in keep:
            words.append(w.upper() if w.upper() in keep and w not in keep else w)
        elif w.lower() in small and words:
            words.append(w.lower())
        elif re.search(r"\d", w):
            words.append(w)
        elif re.fullmatch(r"[A-Z0-9&.,'/-]+", w) or w.islower():
            words.append(w[:1].upper() + w[1:].lower())
        else:
            words.append(w)
    return " ".join(words)


def _jpeg_size(path: Path):
    b = path.read_bytes()
    assert b[:2] == b"\xff\xd8", f"{path}: not a JPEG"
    i = 2
    while i < len(b) - 1:
        assert b[i] == 0xFF, f"{path}: bad JPEG marker"
        marker = b[i + 1]
        i += 2
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            continue
        (seglen,) = struct.unpack(">H", b[i:i + 2])
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            height, width = struct.unpack(">HH", b[i + 3:i + 7])
            return width, height
        i += seglen
    raise ValueError(f"{path}: no JPEG frame header")


def _trim(text, limit):
    if len(text) <= limit:
        return text
    cut = text.rfind("\n", 0, limit)
    cut = cut if cut > limit // 2 else limit
    return text[:cut].rstrip() + f"\n…[{len(text) - cut:,} chars truncated]"


# ---------------------------------------------------------------- FIN-1  10-K sections (EDGAR-CORPUS)

# option key -> (corpus column, item number, official title, regex for the title)
FIN1_SECTIONS = {
    "business": ("section_1", "1", "Business", r"business"),
    "risk_factors": ("section_1A", "1A", "Risk Factors", r"risk\s+factors"),
    "legal_proceedings": ("section_3", "3", "Legal Proceedings", r"legal\s+proceedings"),
    "mdna": ("section_7", "7", "Management's Discussion and Analysis of Financial Condition and Results of Operations",
             r"management.s\s+discussion\s+and\s+analysis"),
    "controls": ("section_9A", "9A", "Controls and Procedures", r"controls\s+and\s+procedures"),
}
FIN1_ORDER = list(FIN1_SECTIONS)
FIN1_PER_SECTION = 6
FIN1_MIN, FIN1_MAX, FIN1_STOP = 600, 2000, 1200
ITEM_HEAD = re.compile(r"^\s*item\s+\d{1,2}[ab]?\b", re.I)
FIN1_SKIP = {  # (filename, option key) -> reason; the filer stays eligible for its other sections
    ("1341235_2019.htm", "mdna"): "Aldeyra: the MD&A passage recites licence-fee and royalty terms of the MEEI agreement, "
                                  "which reads like the Business section's description of agreements.",
}


def _fin1_paragraphs(text, title_re):
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    while lines and (ITEM_HEAD.match(lines[0]) or re.fullmatch(title_re + r"[.:]?", lines[0], re.I) or len(lines[0]) < 4):
        lines.pop(0)
    while lines and ITEM_HEAD.match(lines[-1]):
        lines.pop()
    return lines


def _prose(p):
    if len(p) < 60 or p[-1] not in ".;)”\"'":  # a colon introduces a table or list that is not in the excerpt
        return False
    digits = sum(c.isdigit() for c in p)
    alpha = sum(c.isalpha() for c in p)
    return digits / len(p) <= 0.12 and alpha / len(p) >= 0.65


def _fin1_passage(text, item, title_re):
    paras = _fin1_paragraphs(text, title_re)
    if not paras:
        return None
    total = sum(len(p) for p in paras)
    start, acc = 0, 0
    if total > FIN1_MAX:
        for i, p in enumerate(paras):
            acc += len(p)
            if acc >= 0.3 * total:
                start = i
                break
    i = start
    while i < len(paras):
        run, size, j = [], 0, i
        while j < len(paras) and _prose(paras[j]) and size + len(paras[j]) + 1 <= FIN1_MAX:
            run.append(paras[j])
            size += len(paras[j]) + 1
            j += 1
            if size >= FIN1_STOP:
                break
        if size >= FIN1_MIN:
            passage = "\n".join(run)
            own_item = re.search(rf"\bitem\s+{item}\b", passage, re.I)
            own_title = item != "1" and re.search(title_re, passage, re.I)
            if not own_item and not own_title:
                return passage
        i = j + 1 if j == i else j
    return None


def _fin1_records():
    for y in FIN1_YEARS:
        for off in FIN1_OFFSETS:
            data = json.loads((SOURCE_DIR / f"edgar-corpus/year_{y}-test-{off:04d}.json").read_text())
            for r in data["rows"]:
                yield r["row"]


def _fin1():
    records = {r["filename"]: r for r in _fin1_records()}
    counts = {k: 0 for k in FIN1_ORDER}
    seen = set()
    for filename in sorted(records, key=rank):
        r = records[filename]
        if r["cik"] in seen:
            continue
        available = {}
        for key, (column, item, _title, title_re) in FIN1_SECTIONS.items():
            passage = _fin1_passage(r[column], item, title_re)
            if passage and (filename, key) not in FIN1_SKIP:
                available[key] = passage
        open_keys = [k for k in available if counts[k] < FIN1_PER_SECTION]
        if not open_keys:
            continue
        key = min(open_keys, key=lambda k: (counts[k], FIN1_ORDER.index(k)))
        counts[key] += 1
        seen.add(r["cik"])
        column, item, title, _ = FIN1_SECTIONS[key]
        name, sic = FIN1_FILERS[r["cik"]]
        filer = _company(name)
        row("FIN-1", f"edgar-{filename.replace('.htm', '')}",
            title=f"10-K passage · {filer}",
            state={"form": "10-K (annual report)", "filer": filer, "industry": sic or "not stated in EDGAR",
                   "fiscal_year": r["year"],
                   "passage": available[key],
                   "note": "An excerpt of consecutive paragraphs from one section of the filing; the section heading "
                           "has been removed."},
            gold=key,
            rationale=(f"EDGAR-CORPUS places this text in the filing's Item {item} ({title}) section, i.e. under the "
                       f"filer's own “Item {item}” heading in the {r['year']} 10-K."),
            source={"dataset_id": "edgar-corpus", "dataset": "EDGAR-CORPUS", "license": "Apache-2.0",
                    "url": f"https://huggingface.co/datasets/eloukas/edgar-corpus (mirror c3po-ai/edgar-corpus, "
                           f"config year_{r['year']}, test split; {filename})",
                    "citation": "Loukas et al., EDGAR-CORPUS: Billions of Tokens Make The World Go Round, ECONLP 2021.",
                    "record_id": filename, "original_label": column,
                    "labelled_by": "the filing's own item headings, as split by EDGAR-CORPUS",
                    "cik": r["cik"], "edgar_filings": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
                                                      f"&CIK={int(r['cik']):010d}&type=10-K"},
            note=f"CIK {r['cik']}; EDGAR lists the filer as “{name}” ({sic or 'no SIC'}).",
            tags=["10-k", key])
    assert all(n == FIN1_PER_SECTION for n in counts.values()), f"FIN-1 unbalanced: {counts}"


# ---------------------------------------------------------------- FIN-2  8-K items (SEC EDGAR)

FIN2_OPTIONS = {
    "results": "Results of operations: the company announces quarterly or annual financial results (Item 2.02).",
    "officer_change": "A director or officer departs, is appointed or elected, or has a compensation change (Item 5.02).",
    "agreement": "The company enters into (or amends) a material definitive agreement such as a loan, lease or "
                 "underwriting agreement (Item 1.01).",
    "other": "A Regulation FD disclosure or other event: a presentation, an offering announcement, a completed "
             "transaction, another press release (Item 7.01 or 8.01).",
    "shareholder_vote": "Results of a shareholder or member vote at an annual, special or extraordinary meeting (Item 5.07).",
}
FIN2_PRIMARY = {"results": {"2.02"}, "officer_change": {"5.02"}, "agreement": {"1.01"}, "other": {"7.01", "8.01"},
                "shareholder_vote": {"5.07"}}
FIN2_PER_OPTION = 6
FIN2_SKIP = {
    "0001280058-24-000017": "Blackbaud: the Item 8.01 body is the company entering an accelerated share repurchase "
                            "agreement with a bank; a reader could defend 'material agreement'.",
    "0001628280-24-009396": "Core Scientific: the Item 7.01 press release announces a hosting agreement with CoreWeave; a "
                            "reader could defend 'material agreement'.",
    "0001130310-24-000047": "CenterPoint Energy: the Item 7.01 filing furnishes a subsidiary's audited financial "
                            "statements; a reader could defend 'results of operations'.",
    "0001493152-24-009173": "Panacea Life Sciences: the body describes a 2022 exchange agreement, a 2023 payoff agreement "
                            "and a 2024 share conversion; which event is being reported is unclear.",
}
FIN2_TITLES = {  # official Form 8-K item titles, matched loosely at the start of a section body
    "1.01": r"entry\s+into\s+(a\s+)?material\s+(definitive\s+)?agreement",
    "2.02": r"results\s+of\s+operations\s+and\s+financial\s+condition",
    "5.02": (r"departure\s+of\s+(directors\s+or\s+)?certain\s+officers(\s*[;:,]\s*election\s+of\s+directors)?"
             r"(\s*[;:,]\s*appointment\s+of\s+certain\s+officers)?(\s*[;:,]\s*compensatory\s+arrangements\s+of\s+certain\s+officers)?"),
    "5.07": r"submissions?\s+of\s+matters?\s+to\s+(a\s+)?vote\s+of\s+security\s+holders",
    "7.01": r"regulation\s+fd\s+disclosure",
    "8.01": r"other\s+events",
}
ITEM_LINE = re.compile(r"^\s*Item\s+(\d\.\d\d)\b\.?\s*(.*)$", re.I)
SIGNATURE_LINE = re.compile(r"^\s*SIGNATURES?\s*$", re.I)
BLOCK_TAGS = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table", "hr", "td", "th"}


class _HtmlText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        t = tag.split(":")[-1]
        if t in ("style", "script", "head"):
            self.skip += 1
        if t in BLOCK_TAGS:
            self.out.append(" " if t in ("td", "th") else "\n")

    def handle_endtag(self, tag):
        t = tag.split(":")[-1]
        if t in ("style", "script", "head"):
            self.skip = max(0, self.skip - 1)
        if t in BLOCK_TAGS:
            self.out.append(" " if t in ("td", "th") else "\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data.replace("\n", " ").replace("\r", " "))


def _html_to_lines(raw):
    p = _HtmlText()
    p.feed(raw)
    text = "".join(p.out).replace("\xa0", " ")
    text = re.sub(r"[​﻿‎]", "", text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return [line for line in lines if line]


def _fin2_sections(lines):
    """[(item, rest_of_heading_line, body_lines)] from the first 'Item X.XX' line to SIGNATURE(S)."""
    out, cur = [], None
    for line in lines:
        m = ITEM_LINE.match(line)
        if m:
            cur = [m.group(1), m.group(2), []]
            out.append(cur)
            continue
        if SIGNATURE_LINE.match(line) and cur:
            break
        if cur is not None:
            cur[2].append(line)
    return out


def _fin2_body(item, rest, body_lines):
    text = (rest + "\n" + "\n".join(body_lines)).strip()
    m = re.match(r"^[\s\W]*" + FIN2_TITLES[item] + r"[\s.:;–-]*", text, re.I | re.S)
    if m:
        text = text[m.end():]
    lines = [line for line in (x.strip() for x in text.split("\n"))
             if line and not re.fullmatch(r"[-–\s]*\d{1,2}[-–\s]*", line)]  # page numbers
    text = "\n".join(lines)
    return re.sub(r"\bItem\s+\d\.\d\d\b", "Item [number removed]", text)


def _fin2():
    counts = {k: 0 for k in FIN2_OPTIONS}
    for option in FIN2_OPTIONS:
        filings = sorted((f for f in EIGHT_K if f[0] == option), key=lambda f: rank(f[1]))
        for _, adsh, cik, doc, name, filed, period, items in filings:
            if adsh in FIN2_SKIP or counts[option] >= FIN2_PER_OPTION:
                continue
            lines = _html_to_lines((SOURCE_DIR / f"edgar-8k/{adsh}.htm").read_text(errors="replace"))
            sections = _fin2_sections(lines)
            parsed = {s[0] for s in sections}
            assert set(items) - {"9.01"} <= parsed | {"2.03"}, f"{adsh}: items {items} but parsed {sorted(parsed)}"
            parts = [_fin2_body(it, rest, body) for it, rest, body in sections if it in FIN2_PRIMARY[option]]
            body = "\n\n".join(p for p in parts if p)
            assert len(body) >= 150, f"{adsh}: body too short ({len(body)} chars)"
            counts[option] += 1
            filer = _company(name)
            row("FIN-2", f"sec-{adsh}",
                title=f"8-K · {filer}",
                state={"form": "8-K (current report)", "filer": filer, "filed": filed, "date_of_report": period,
                       "body": _trim(body, 6000),
                       "note": "The 'Item X.XX' heading lines, the exhibit list and cross-references between items were "
                               "removed; in-body item numbers are shown as 'Item [number removed]'."},
                gold=option,
                rationale=(f"The filer reported this under Item {' and '.join(sorted(set(items) & FIN2_PRIMARY[option]))} "
                           f"of Form 8-K (EDGAR item list: {', '.join(items)})."),
                source={"dataset_id": "sec-edgar-8k", "dataset": "SEC EDGAR 8-K filings", "license": "Public domain",
                        "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{adsh.replace('-', '')}/{doc}",
                        "citation": "U.S. Securities and Exchange Commission, EDGAR full-text search (efts.sec.gov).",
                        "record_id": adsh, "original_label": ",".join(items),
                        "labelled_by": "the filer's own item numbers on the Form 8-K cover, as indexed by EDGAR",
                        "cik": f"{cik:010d}"},
                note=f"Accession {adsh}; the filing lists items {', '.join(items)}.",
                tags=["8-k", option])
    assert all(n == FIN2_PER_OPTION for n in counts.values()), f"FIN-2 unbalanced: {counts}"


# ---------------------------------------------------------------- FIN-3  receipts (CORD-v2)

FIN3_TARGET = 30
FIN3_MIN_SIDE = 800   # source photos smaller than this on their longest side are too small to read
FIN3_MAX_SIDE = 1600
FIN3_TOTAL_FIELDS = {"total_price", "cashprice", "creditcardprice", "emoneyprice"}
FIN3_MONEY_FIELDS = FIN3_TOTAL_FIELDS | {"price", "itemsubtotal", "unitprice", "subtotal_price", "discount_price",
                                        "service_price", "tax_price", "etc", "total_etc", "othersvc_price", "changeprice"}
FIN3_FIELD_WORDS = {"price": "a line-item price", "itemsubtotal": "a line-item subtotal", "unitprice": "a unit price",
                    "subtotal_price": "the subtotal", "discount_price": "a discount", "service_price": "a service charge",
                    "tax_price": "the tax", "etc": "another charge", "total_etc": "another total-block figure",
                    "othersvc_price": "another service charge", "changeprice": "the change given",
                    "cashprice": "the cash tendered", "creditcardprice": "the card payment", "emoneyprice": "the e-money payment",
                    "total_price": "the total"}
MONEY_RE = re.compile(r"^-?[\d.,]+$")
FIN3_SKIP = {}  # image_id -> reason


def _digits(s):
    return re.sub(r"\D", "", str(s))


def _fin3_records():
    for off in FIN3_OFFSETS:
        data = json.loads((SOURCE_DIR / f"cord-v2/test-{off:03d}.json").read_text())
        for r in data["rows"]:
            gt = json.loads(r["row"]["ground_truth"])
            yield gt["meta"]["image_id"], gt, r["row"]["image"]


def _fin3_words(gt):
    """Annotated words grouped into physical lines (row_id), lines top to bottom, words left to right."""
    lines = {}
    for line in gt["valid_line"]:
        cat = line["category"].split(".")[-1]
        for w in line["words"]:
            q = w["quad"]
            lines.setdefault(w["row_id"], []).append(((q["y1"] + q["y4"]) / 2, q["x1"], w["text"], cat))
    ordered = sorted(lines.values(), key=lambda ws: sum(w[0] for w in ws) / len(ws))
    return [sorted(ws, key=lambda w: w[1]) for ws in ordered]


def _fin3_candidate(image_id, gt):
    parse = gt["gt_parse"]
    total = parse.get("total", {})
    total = total[0] if isinstance(total, list) else total
    tp = total.get("total_price") if isinstance(total, dict) else None
    if isinstance(tp, list) or not tp:
        return None
    lines = _fin3_words(gt)
    words = [w for line in lines for w in line]
    if not 8 <= len(words) <= 120:
        return None
    figures = {}  # digits -> (first printed text, set of fields)
    for _, _, text, cat in words:
        if cat in FIN3_MONEY_FIELDS and MONEY_RE.match(text.replace(" ", "")) and _digits(text):
            d = _digits(text)
            entry = figures.setdefault(d, [text, set()])
            entry[1].add(cat)
    gold = _digits(tp)
    if gold not in figures or not figures[gold][1] <= FIN3_TOTAL_FIELDS:
        return None
    others = [d for d in figures if d != gold and int(d) >= 100]  # no zero, rounding or single-digit figures
    if len(others) < 3:
        return None
    others = sorted(others, key=lambda d: rank(f"{image_id}:{d}"))[:4]
    return {"image_id": image_id, "gold": gold, "figures": figures, "others": others, "lines": lines,
            "n_items": len(parse["menu"]) if isinstance(parse.get("menu"), list) else 1}


def _fin3_select():
    cands = []
    for image_id, gt, image in _fin3_records():
        if image_id in FIN3_SKIP or max(image["width"], image["height"]) < FIN3_MIN_SIDE:
            continue
        c = _fin3_candidate(image_id, gt)
        if c:
            c["image"] = image
            cands.append(c)
    return sorted(cands, key=lambda c: rank(f"cord-v2-test-{c['image_id']}"))[:FIN3_TARGET]


def _fin3_asset_path(image_id):
    return ASSETS / "finance" / f"fin-3-cord-test-{image_id:03d}.jpg"


def prepare_fin3_assets(raw_dir):
    """One-off: resize the downloaded CORD test images (raw_dir/test-<id>.jpg, from the rows API's signed image URLs)
    to a longest side of 1,600 px and at most 400 KB with macOS sips. Run by hand; define() only reads the results."""
    assert shutil.which("sips"), "prepare_fin3_assets uses macOS sips"
    for c in _fin3_select():
        src = Path(raw_dir) / f"test-{c['image_id']:03d}.jpg"
        dst = _fin3_asset_path(c["image_id"])
        dst.parent.mkdir(parents=True, exist_ok=True)
        longest = min(FIN3_MAX_SIDE, max(_jpeg_size(src)))  # never upscale
        for side, quality in ((longest, 82), (longest, 70), (min(longest, 1400), 70), (min(longest, 1200), 65),
                              (min(longest, 1000), 60)):
            subprocess.run(["sips", "-Z", str(side), "-s", "format", "jpeg", "-s", "formatOptions", str(quality),
                            str(src), "--out", str(dst)], check=True, capture_output=True)
            if dst.stat().st_size <= 400_000:
                break
        assert dst.stat().st_size <= 400_000, f"{dst} is still over 400 KB"
        print(f"{dst.name}: {dst.stat().st_size:,} bytes, {_jpeg_size(dst)}")


def _fin3():
    for c in _fin3_select():
        path = _fin3_asset_path(c["image_id"])
        width, height = _jpeg_size(path)
        keys = [c["gold"], *c["others"]]
        options = {c["figures"][d][0]: f"A figure printed on the receipt: {c['figures'][d][0]}"
                   for d in sorted(keys, key=lambda d: rank(f"{c['image_id']}:opt:{d}"))}
        gold_text = c["figures"][c["gold"]][0]
        explain = "; ".join(f"{c['figures'][d][0]} is {' / '.join(sorted(FIN3_FIELD_WORDS[f] for f in c['figures'][d][1]))}"
                            for d in c["others"])
        ocr = "\n".join(" ".join(w[2] for w in line) for line in c["lines"])
        n_lines = len(c["lines"])
        row("FIN-3", f"cord-test-{c['image_id']:03d}",
            title=f"Receipt · CORD-v2 test image {c['image_id']:03d} · {c['n_items']} line item{'s' if c['n_items'] != 1 else ''}",
            state={"image": f"a photo of a printed shop or restaurant receipt, {width}×{height} px",
                   "ocr_text": ocr,
                   "ocr_note": "The dataset's annotated words in reading order (menu lines, subtotal block and total "
                               "block); the store header and footer text are not annotated.",
                   "candidate_figures": list(options)},
            gold=gold_text,
            options=options,
            rationale=(f"CORD's annotators labelled {gold_text} as total.total_price, the amount charged for the whole "
                       f"receipt; of the other figures, {explain}."),
            source={"dataset_id": "cord-v2", "dataset": "CORD-v2 (Consolidated Receipt Dataset)", "license": "CC-BY-4.0",
                    "url": f"https://huggingface.co/datasets/naver-clova-ix/cord-v2 (test split, image_id {c['image_id']})",
                    "citation": "Park et al., CORD: A Consolidated Receipt Dataset for Post-OCR Parsing, NeurIPS 2019 "
                                "Document Intelligence Workshop.",
                    "record_id": f"test-{c['image_id']}", "original_label": f"total.total_price = {gold_text}",
                    "labelled_by": "the CORD annotators' key-value labels (gt_parse)"},
            assets=[{"path": str(path.relative_to(ROOT)), "mime_type": "image/jpeg",
                     "alt_text": f"A photo of a printed receipt from an Indonesian shop or restaurant with {c['n_items']} "
                                 f"line item{'s' if c['n_items'] != 1 else ''}, a subtotal block and a total block; several "
                                 "monetary figures are legible.",
                     "width": width, "height": height}],
            note=f"CORD-v2 test image {c['image_id']}; the other figures are item prices, subtotals, tax, cash tendered or change.",
            tags=["receipt", "vision"])


# ---------------------------------------------------------------- FIN-5  XBRL-tagged amounts (FiNER-139)

FIN5_GROUPS = {
    "revenue": ("Revenue: sales or revenue recognised (or adjusted) for a period.",
                {"Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                 "RevenueFromContractWithCustomerIncludingAssessedTax"}),
    "goodwill": ("Goodwill: the carrying amount of goodwill, or goodwill recorded in an acquisition.", {"Goodwill"}),
    "borrowings": ("Borrowings: the principal, face or outstanding amount of a loan, notes, term loan or credit "
                   "facility.", {"DebtInstrumentFaceAmount", "LongTermDebt", "LineOfCredit", "DebtInstrumentCarryingAmount"}),
    "share_based_compensation": ("Share-based compensation: stock- or unit-based compensation expense recognised.",
                                 {"ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"}),
    "income_tax_expense": ("Income tax: income tax expense, provision or benefit, including the tax on an adjustment.",
                           {"IncomeTaxExpenseBenefit"}),
    "amortization": ("Amortization of intangible assets: amortization expense recognised on acquired intangibles.",
                     {"AmortizationOfIntangibleAssets"}),
}
FIN5_PER_GROUP = 6
FIN5_SKIP = {  # FiNER-139 test id -> reason (hand review of the candidates in rank order)
    1016978: "a standby letter of credit tagged LineOfCredit; a reader need not call a letter of credit a borrowing.",
    1013813: "the sentence carries a table caption and footnote fragment before the amount.",
    1019094: "the sentence carries a financial-statement header fragment ('_ _ _ _') before the amount.",
    1022311: "third of four near-identical Heartland 'net of taxes of $X' sentences; two are enough.",
    1022307: "fourth of four near-identical Heartland 'net of taxes of $X' sentences.",
    1022310: "second of four near-identical Heartland 'net of taxes of $X' sentences.",
    1023173: "'payment from Total in the amount of $38.4 million' under an agreement; the sentence does not show it is revenue.",
    1023170: "'payment from Total in the amount of $3.2 million' under an agreement; the sentence does not show it is revenue.",
    1020040: "a deferred revenue balance (a liability) tagged as revenue; not defensible from the sentence.",
}
NUMBER_RE = re.compile(r"^\d[\d,]*(\.\d+)?$")


def _fin5_tag_names():
    data = json.loads((SOURCE_DIR / f"finer-139/test-{FIN5_OFFSETS[0]:05d}.json").read_text())
    feature = next(f for f in data["features"] if f["name"] == "ner_tags")
    return feature["type"]["feature"]["names"]


def _fin5_records():
    for off in FIN5_OFFSETS:
        data = json.loads((SOURCE_DIR / f"finer-139/test-{off:05d}.json").read_text())
        for r in data["rows"]:
            yield r["row"]


def _detokenize(tokens):
    text = " ".join(tokens)
    text = re.sub(r"\s+([,.;:%)\]’”])", r"\1", text)
    text = re.sub(r"([($\[‘“])\s+", r"\1", text)
    text = re.sub(r"\s+'\s*s\b", "'s", text)
    text = re.sub(r"(\w)\s+-\s+(\w)", r"\1-\2", text)
    return text


def _fin5_candidate(r, names):
    toks, tags = r["tokens"], r["ner_tags"]
    if not 12 <= len(toks) <= 120:
        return None
    ents = [(i, names[t]) for i, t in enumerate(tags) if names[t] != "O"]
    if len(ents) != 1 or not ents[0][1].startswith("B-"):
        return None
    i, tag = ents[0]
    tag = tag[2:]
    group = next((g for g, (_, tags_) in FIN5_GROUPS.items() if tag in tags_), None)
    if group is None or i == 0 or toks[i - 1] != "$" or not NUMBER_RE.match(toks[i]):
        return None
    marked = _detokenize(toks[:i] + [f"[[{toks[i]}]]"] + toks[i + 1:])
    if len(marked) > 700:
        return None
    return {"id": r["id"], "group": group, "tag": tag, "number": toks[i], "sentence": marked}


def _fin5():
    names = _fin5_tag_names()
    cands = [c for c in (_fin5_candidate(r, names) for r in _fin5_records()) if c and c["id"] not in FIN5_SKIP]
    counts = {g: 0 for g in FIN5_GROUPS}
    for c in sorted(cands, key=lambda c: rank(c["id"])):
        if counts[c["group"]] >= FIN5_PER_GROUP:
            continue
        counts[c["group"]] += 1
        row("FIN-4", f"finer-test-{c['id']}",
            title=f"Filing sentence · FiNER-139 test id {c['id']}",
            state={"source": "one sentence from a US company's 10-K or 10-Q filing (2016–2020)",
                   "sentence": c["sentence"],
                   "marked_number": c["number"],
                   "note": "The amount in question is marked [[like this]]; it is the only XBRL-tagged number in the sentence."},
            gold=c["group"],
            rationale=(f"The company tagged the marked amount with the XBRL element us-gaap:{c['tag']} in its filing, which "
                       f"FiNER-139 records as the token label B-{c['tag']}."),
            source={"dataset_id": "finer-139", "dataset": "FiNER-139", "license": "CC-BY-SA-4.0",
                    "url": f"https://huggingface.co/datasets/nlpaueb/finer-139 (test split, id {c['id']})",
                    "citation": "Loukas et al., FiNER: Financial Numeric Entity Recognition for XBRL Tagging, ACL 2022.",
                    "record_id": f"test-{c['id']}", "original_label": f"B-{c['tag']}",
                    "labelled_by": "the filing company's own XBRL tag on the amount (eXtensible Business Reporting Language)"},
            note=f"XBRL element: {c['tag']}.",
            tags=["xbrl", c["group"]])
    assert all(counts.values()), f"FIN-5: a group has no rows: {counts}"


# ---------------------------------------------------------------- datasets

SEC_TERMS = ("SEC filings are public records. The SEC's website policy (https://www.sec.gov/privacy, “Website "
             "Dissemination”) says: “Information presented on sec.gov is considered public information and may be "
             "copied or further distributed by users of the web site without the SEC's permission”, asking only for "
             "attribution to the SEC and no use of the SEC seal or logos.")


def _datasets():
    dataset(id="edgar-corpus", name="EDGAR-CORPUS", tasks=["FIN-1"],
            homepage="https://huggingface.co/datasets/eloukas/edgar-corpus",
            license="Apache-2.0",
            license_url=f"https://huggingface.co/datasets/eloukas/edgar-corpus/blob/{EDGAR_CORPUS_SHA}/README.md",
            content=("A passage of consecutive paragraphs from one section (Item 1, 1A, 3, 7 or 9A) of a US public "
                     "company's annual report on Form 10-K for fiscal years 2015–2020, as split into sections by "
                     "EDGAR-CORPUS; read through the Hugging Face rows API from the Parquet duplicate "
                     f"c3po-ai/edgar-corpus (revision {EDGAR_MIRROR_SHA[:7]}, marked “Duplicated from eloukas/edgar-corpus”)."),
            content_license="Public domain",
            content_terms=SEC_TERMS + " The corpus card adds “EDGAR data is publicly available.”",
            labelled_by="the filing's own item headings, as located by EDGAR-CORPUS's section splitter",
            changes=("The section's heading lines are removed and one run of paragraphs is excerpted (whitespace "
                     "normalised); the filer name and SIC description come from EDGAR's submissions API, not the corpus."),
            selection=("One 10-K per rows-API window (42 windows over the 2015–2020 test splits), one per CIK, in sha256 "
                       "order of the corpus filename; each filer takes the section with the fewest rows so far among "
                       "those that yield a 600–2,000 character prose passage; six rows per section."),
            citation="Loukas, Fergadiotis, Androutsopoulos and Malakasiotis, EDGAR-CORPUS: Billions of Tokens Make The "
                     "World Go Round, ECONLP 2021.",
            bibtex="""@inproceedings{loukas-etal-2021-edgar,
  title     = {{EDGAR}-{CORPUS}: Billions of Tokens Make The World Go Round},
  author    = {Loukas, Lefteris and Fergadiotis, Manos and Androutsopoulos, Ion and Malakasiotis, Prodromos},
  booktitle = {Proceedings of the Third Workshop on Economics and Natural Language Processing},
  year      = {2021},
  publisher = {Association for Computational Linguistics},
  url       = {https://aclanthology.org/2021.econlp-1.2}
}""")
    dataset(id="sec-edgar-8k", name="SEC EDGAR 8-K filings", tasks=["FIN-2"],
            homepage="https://www.sec.gov/edgar/search/",
            license="Public domain",
            license_url="https://www.sec.gov/privacy",
            content=("The body of a current report on Form 8-K filed with the SEC between 4 and 8 March 2024, the primary "
                     "document converted from HTML to text."),
            content_license="Public domain",
            content_terms=SEC_TERMS + " " + UA_NOTE,
            labelled_by="the item numbers the filer put on the Form 8-K cover, as indexed by EDGAR full-text search",
            changes=("HTML converted to text; only the sections of the reported item are kept (the Item 9.01 exhibit list "
                     "and Item 2.03 cross-references are dropped); the 'Item X.XX' heading line and official title are "
                     "removed and in-body item numbers redacted to 'Item [number removed]'; bodies over 6,000 characters "
                     "are truncated with a marker."),
            selection=("EDGAR full-text search for one week of 8-K filings, one query per item number; plain 8-Ks whose "
                       "items other than 9.01 map to exactly one option; one per filer; the first nine per option by "
                       "sha256 of the accession number were downloaded and the first six not in FIN2_SKIP are rows."),
            citation="U.S. Securities and Exchange Commission, EDGAR full-text search, filings of 4–8 March 2024.",
            bibtex="""@misc{sec_edgar_8k,
  author       = {{U.S. Securities and Exchange Commission}},
  title        = {{EDGAR} Form 8-K filings, 4--8 March 2024},
  howpublished = {\\url{https://www.sec.gov/edgar/search/}},
  year         = {2024}
}""")
    dataset(id="cord-v2", name="CORD-v2 (Consolidated Receipt Dataset)", tasks=["FIN-3"],
            homepage="https://github.com/clovaai/cord",
            license="CC-BY-4.0",
            license_url=f"https://huggingface.co/datasets/naver-clova-ix/cord-v2/blob/{CORD_SHA}/README.md",
            content=("A photograph of a printed receipt from an Indonesian shop or restaurant, with the dataset's "
                     "word-level OCR annotations and key-value parse (menu lines, subtotal and total)."),
            content_license="CC-BY-4.0",
            content_terms=("The CORD repository (github.com/clovaai/cord) says “This work is licensed under a Creative Commons "
                           "Attribution 4.0 International License” and that the dataset “consists of thousands of Indonesian "
                           "receipts” collected from shops and restaurants; the images and annotations were released "
                           "together by Clova AI (NAVER) under that licence, and the Hugging Face card carries cc-by-4.0."),
            labelled_by="Clova AI's trained annotators (CORD's key-value labels: total.total_price)",
            changes=("The image is resized to a longest side of at most 1,600 px and re-encoded as JPEG under 400 KB; "
                     "the annotated words are shown as lines in reading order; option figures are as printed."),
            selection=("All 100 test-split receipts, in sha256 order of the image id; kept when the photo is at least 800 px "
                       "on its longest side, a single total_price is annotated, its digits appear only in total-type "
                       "fields, at least three other distinct figures of 100 or more are printed and 8–120 words are "
                       "annotated; first 30."),
            citation="Park et al., CORD: A Consolidated Receipt Dataset for Post-OCR Parsing, Document Intelligence "
                     "Workshop at NeurIPS 2019.",
            bibtex="""@inproceedings{park2019cord,
  title     = {{CORD}: A Consolidated Receipt Dataset for Post-{OCR} Parsing},
  author    = {Park, Seunghyun and Shin, Seung and Lee, Bado and Lee, Junyeop and Surh, Jaeheung and Seo, Minjoon and Lee, Hwalsuk},
  booktitle = {Document Intelligence Workshop at Neural Information Processing Systems},
  year      = {2019}
}""")
    dataset(id="finer-139", name="FiNER-139", tasks=["FIN-4"],
            homepage="https://huggingface.co/datasets/nlpaueb/finer-139",
            license="CC-BY-SA-4.0",
            license_url=f"https://huggingface.co/datasets/nlpaueb/finer-139/blob/{FINER_SHA}/README.md",
            content=("One tokenised sentence from a US public company's 10-K or 10-Q filing (2016–2020) with the XBRL "
                     "element the company attached to one dollar amount in it."),
            content_license="Public domain",
            content_terms=SEC_TERMS + " The dataset's own annotations (token labels) are CC BY-SA 4.0, so these rows "
                                      "carry that licence.",
            labelled_by="the filing company itself: the XBRL element it tagged the amount with in its SEC filing",
            changes=("Tokens are joined back into a sentence (spacing around punctuation restored) and the tagged number is "
                     "wrapped in [[ ]]; eleven of the 139 XBRL elements are mapped to six plain-words groups, and only "
                     "sentences tagged with one of those elements are used."),
            selection=("Test split rows 0–11,999 in sha256 order of the row id; sentences with exactly one tagged token, a "
                       "dollar sign before it and a tag in one of the six groups, minus the ids in FIN5_SKIP; up to six "
                       "per group."),
            citation="Loukas et al., FiNER: Financial Numeric Entity Recognition for XBRL Tagging, ACL 2022.",
            bibtex="""@inproceedings{loukas-etal-2022-finer,
  title     = {{FiNER}: Financial Numeric Entity Recognition for {XBRL} Tagging},
  author    = {Loukas, Lefteris and Fergadiotis, Manos and Chalkidis, Ilias and Spyropoulou, Eirini and Malakasiotis, Prodromos and Androutsopoulos, Ion and Paliouras, George},
  booktitle = {Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)},
  year      = {2022},
  publisher = {Association for Computational Linguistics},
  url       = {https://aclanthology.org/2022.acl-long.303}
}""")


def define():
    _datasets()
    task("FIN-1", category=CATEGORY, name="Which part of the 10-K?",
         ask="Which section of the annual report is this passage from?",
         instruction=("The record is a passage of consecutive paragraphs from a US company's annual report on Form 10-K, "
                      "with the section heading removed. Decide which of the five sections it was taken from, using the "
                      "kind of content each section holds."),
         options={"business": "Item 1, Business: what the company does, its products, markets, competition, employees, regulation.",
                  "risk_factors": "Item 1A, Risk Factors: things that could go wrong and hurt the business or the stock.",
                  "legal_proceedings": "Item 3, Legal Proceedings: pending lawsuits, claims and regulatory actions.",
                  "mdna": "Item 7, MD&A: management's discussion of results, liquidity, capital resources and trends.",
                  "controls": "Item 9A, Controls and Procedures: disclosure controls and internal control over financial reporting."},
         shape="classify", input_type="10-K passage", modality="text", expertise="none", contamination="medium",
         label_origin="objective record")
    task("FIN-2", category=CATEGORY, name="What does this 8-K report?",
         ask="What event does this current report disclose?",
         instruction=("The record is the body of a Form 8-K current report with its item heading removed. Decide which "
                      "kind of event the filer is reporting. Choose 'other' for Regulation FD disclosures and other events "
                      "(Items 7.01 and 8.01) that are not results, an officer or director change, a material agreement or "
                      "a shareholder vote."),
         options=FIN2_OPTIONS,
         shape="classify", input_type="8-K filing body", modality="text", expertise="none", contamination="low",
         label_origin="objective record")
    task("FIN-3", category=CATEGORY, name="Which figure is the total?",
         ask="Which of these figures is the receipt's total?",
         instruction=("The image is a photo of a printed receipt; the state also lists the annotated words in reading "
                      "order. Four or five monetary figures printed on the receipt are offered. Pick the one that is the "
                      "total amount charged for the whole receipt (not a line item, subtotal, tax, discount, cash tendered or "
                      "change)."),
         options={}, per_row_options=True,
         shape="locate", input_type="receipt image", modality="image", expertise="none", contamination="high",
         label_origin="trained annotators")
    task("FIN-4", category=CATEGORY, name="What does this number report?",
         ask="What does the marked amount in this sentence report?",
         instruction=("The record is one sentence from a company's SEC filing with one dollar amount marked [[like this]]. "
                      "Decide which financial concept the company reported with that amount, as it would be tagged in XBRL."),
         options={k: v[0] for k, v in FIN5_GROUPS.items()},
         shape="classify", input_type="filing sentence", modality="text", expertise="practitioner", contamination="medium",
         label_origin="self-declared")
    _fin1()
    _fin2()
    _fin3()
    _fin5()
