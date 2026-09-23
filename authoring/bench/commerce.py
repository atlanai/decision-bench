"""commerce: search relevance, product catalogues and company profiles.

COM-1  does a product match a shopping query: Exact / Substitute / Complement / Irrelevant, from the Amazon
       Shopping Queries Dataset (ESCI), US locale, one row per query, labels by trained human annotators;
COM-2  what type of product an Amazon listing is, from Amazon Berkeley Objects (ABO) listings metadata, with the
       seller's own product_type field as the answer and eight distinct types offered;
COM-3  which SIC division a public company belongs to, from the opening of Item 1 (Business) of its 2020 Form 10-K
       in EDGAR-CORPUS, joined to the SIC code that SEC EDGAR records for the filer (data.sec.gov submissions API).

Not built: COM-4 "Do these two records describe the same product?" from the WDC Product Data Corpus / WDC
Products. Web Data Commons publishes its corpora "for research purposes only" and states no licence for the
extracted schema.org data, which is copied from retailers' pages found in Common Crawl; neither the dataset nor
the text inside it meets the open-licence policy, so it was dropped (see the module report).

Written sampling rules
----------------------
COM-1: 27 fixed 100-row pages of the pre-joined Hugging Face mirror tasksource/esci (train split, offsets
20,000 + 66,000·k for k < 27; pages beyond that are Spanish and Japanese). Candidates: product_locale "us",
non-empty product title without CJK characters, query of at most 100 characters and plain ASCII, no adult-content
words in the query (ADULT regex), and an example_id that occurs once in the pages (the mirror joins products by id
without the locale, so some US examples are repeated with Japanese or Spanish product text; those are dropped).
Candidates are walked in rank() order of example_id; a query is used at most once; labels are
filled to fixed quotas (Exact 8, Substitute 8, Complement 7, Irrelevant 7). Pairs passed over by hand are in
COM1_SKIP with the reason. Product descriptions are stripped of HTML tags and cut at 800 characters with a marker.

COM-2: listings_0.json.gz, one of the sixteen ABO listings shards (5.4 MB). Candidates: marketplace country
"US", an en_US item name, product_type among the eight offered, at least one en_US bullet point or description,
and not a fabric swatch (item name containing "swatch"). Candidates are walked in rank() order of item_id and
filled to quotas of 4 rows per type (3 for shoes and grocery). The product_type and browse-node fields are
removed from the shown listing, as are the hidden search keywords and image/model identifiers. Listings passed
over by hand are in COM2_SKIP.

COM-3: 14 fixed 10-row pages of the Hugging Face parquet mirror c3po-ai/edgar-corpus (config year_2020, train
split, offsets 0, 400, …, 5200; the rows are whole 10-K filings, so pages are small). Candidates: Item 1 of at
least 6,000 characters. For every candidate the filer's SEC submissions record is fetched
(data.sec.gov/submissions/CIK##########.json) and its SIC code mapped to a division by code range. Candidates are
walked in rank() order of filename; filers outside the seven offered divisions (agriculture, construction, public
administration, non-operating) are dropped by rule; at most one blank-check company (SIC 6770); quotas per
division are in COM3_QUOTA. The shown text is the first 2,000 characters of Item 1 with the filer's current and
former names (and per-row aliases listed in COM3_ALIASES) replaced by "[the Company]". Filings passed over by
hand are in COM3_SKIP. Note that the SIC code is the one EDGAR records for the filer today, not as of 2020; rows
where the 2020 business no longer matches were skipped by hand.
"""
import collections
import gzip
import json
import re

from . import dataset, task, row, rank, SOURCES as SOURCE_DIR

CATEGORY = "commerce"

# ---------------------------------------------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------------------------------------------
ESCI_MIRROR = "tasksource/esci"
ESCI_OFFSETS = [20_000 + 66_000 * k for k in range(27)]
SOURCES = [{"dataset": "Amazon Shopping Queries Dataset (ESCI)",
            "url": ("https://datasets-server.huggingface.co/rows?dataset=tasksource%2Fesci&config=default&split=train"
                    f"&offset={off}&length=100"),
            "path": f"esci/train-{off:07d}.json"} for off in ESCI_OFFSETS]

ABO_BASE = "https://amazon-berkeley-objects.s3.amazonaws.com/"
SOURCES += [{"dataset": "Amazon Berkeley Objects (ABO)", "url": ABO_BASE + "listings/metadata/listings_0.json.gz",
             "path": "abo/listings_0.json.gz"}]

EDGAR_MIRROR = "c3po-ai/edgar-corpus"
EDGAR_OFFSETS = list(range(0, 5480, 400))
SOURCES += [{"dataset": "EDGAR-CORPUS",
             "url": ("https://datasets-server.huggingface.co/rows?dataset=c3po-ai%2Fedgar-corpus&config=year_2020"
                     f"&split=train&offset={off}&length=10"),
             "path": f"edgar-corpus-2020/train-{off:05d}.json"} for off in EDGAR_OFFSETS]

# The CIK of every filing in the EDGAR pages above whose Item 1 is at least 6,000 characters (116 filers). The list
# is derived by that rule and frozen here so that scripts/fetch_sources.py can declare and pin the lookups.
COM3_CIKS = [
    27419, 58492, 61339, 62996, 70866, 75208, 95029, 310522, 352915, 718413, 723531, 726854, 748268, 752714,
    771999, 778946, 788611, 811156, 827054, 860731, 861838, 876167, 879682, 887919, 889971, 912463, 913144,
    913760, 931059, 944314, 949039, 1004036, 1008848, 1020569, 1029744, 1036188, 1046311, 1065332, 1086745,
    1096343, 1117480, 1133421, 1144215, 1162194, 1169055, 1178711, 1198415, 1206264, 1260968, 1260990, 1267813,
    1282224, 1285543, 1297937, 1328143, 1334978, 1341726, 1350653, 1351288, 1356949, 1358762, 1371782, 1372020,
    1383394, 1397911, 1404281, 1411207, 1413119, 1428439, 1430306, 1431959, 1451505, 1455863, 1467154, 1490873,
    1492298, 1493566, 1497649, 1519117, 1522727, 1535379, 1538263, 1542447, 1543637, 1553404, 1559720, 1566044,
    1573516, 1576940, 1586495, 1592386, 1601548, 1603923, 1604464, 1614178, 1616262, 1627606, 1641489, 1653477,
    1654151, 1661920, 1664703, 1676047, 1678463, 1680581, 1685237, 1696558, 1697587, 1711754, 1740797, 1804591,
    1815526, 1817071, 1818346, 1828478, 1830029,
]
SOURCES += [{"dataset": "SEC EDGAR company submissions", "url": f"https://data.sec.gov/submissions/CIK{cik:010d}.json",
             "path": f"sec-submissions/CIK{cik:010d}.json"} for cik in COM3_CIKS]


def _no_words(title, banned, where):
    low = title.lower()
    hits = [w for w in banned if w in low]
    assert not hits, f"{where}: title {title!r} contains answer words {hits}"


def _hf_rows(path):
    page = json.loads((SOURCE_DIR / path).read_text(encoding="utf-8"))
    assert not any(r["truncated_cells"] for r in page["rows"]), path
    return [r["row"] for r in page["rows"]]


def _cut(text, limit):
    text = text.strip()
    if len(text) <= limit:
        return text
    head = text[:limit].rsplit(" ", 1)[0]
    return f"{head} …[{len(text) - len(head):,} chars truncated]"


# ---------------------------------------------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------------------------------------------
ESCI = dict(dataset_id="amazon-esci", dataset="Amazon Shopping Queries Dataset (ESCI)", license="Apache-2.0",
            url="https://github.com/amazon-science/esci-data",
            citation="Reddy et al., Shopping Queries Dataset: A Large-Scale ESCI Benchmark for Improving Product "
                     "Search, arXiv:2206.06588, 2022. Read through the Apache-2.0 Hugging Face mirror tasksource/esci.",
            labelled_by="Amazon's trained human annotators (at least three judgements per pair, majority vote)")
ABO = dict(dataset_id="amazon-berkeley-objects", dataset="Amazon Berkeley Objects (ABO)", license="CC-BY-4.0",
           url="https://amazon-berkeley-objects.s3.amazonaws.com/index.html",
           citation="Collins et al., ABO: Dataset and Benchmarks for Real-World 3D Object Understanding, CVPR 2022.",
           labelled_by="the seller's own product_type field in the listing")
EDGAR = dict(dataset_id="edgar-corpus-10k-business", dataset="EDGAR-CORPUS (10-K Item 1) with SEC EDGAR SIC codes",
             license="Apache-2.0", url="https://huggingface.co/datasets/eloukas/edgar-corpus",
             citation="Loukas et al., EDGAR-CORPUS: Billions of Tokens Make The World Go Round, ECONLP 2021. Read "
                      "through the Apache-2.0 parquet mirror c3po-ai/edgar-corpus; SIC codes from "
                      "data.sec.gov/submissions.",
             labelled_by="the SIC code SEC EDGAR records for the filer, mapped to its division by code range")


def _datasets():
    dataset(id="amazon-esci", name="Amazon Shopping Queries Dataset (ESCI)", tasks=["COM-1"],
            homepage="https://github.com/amazon-science/esci-data", license="Apache-2.0",
            license_url="https://github.com/amazon-science/esci-data/blob/main/LICENSE",
            content="A real Amazon.com search query and one product returned for it (title, brand, colour, bullet "
                    "points, description), with the ESCI relevance judgement; read from the Hugging Face mirror "
                    "tasksource/esci, which joins the dataset's examples and products files.",
            content_license="Apache-2.0",
            content_terms="Amazon Science released the queries, product texts and labels together under Apache-2.0 "
                          "(https://github.com/amazon-science/esci-data/blob/main/LICENSE); the mirror carries the "
                          "same licence (https://huggingface.co/datasets/tasksource/esci). The product texts are "
                          "Amazon catalogue listings written by sellers and published by Amazon in the dataset.",
            labelled_by="Amazon's trained human annotators: at least three judgements per query-product pair, "
                        "aggregated by majority vote (paper, section 2)",
            changes="US locale only; HTML tags stripped from descriptions and descriptions cut at 800 characters with "
                    "a marker; bullet points split into a list; one product per query.",
            selection="27 fixed 100-row pages of the mirror's train split; candidates walked in sha256 order of "
                      "example_id, one row per query, filled to fixed per-label quotas; pairs a careful reader could "
                      "label two ways were skipped by hand and are listed in COM1_SKIP.",
            citation="Reddy et al., Shopping Queries Dataset: A Large-Scale ESCI Benchmark for Improving Product "
                     "Search, arXiv:2206.06588, 2022.",
            bibtex="""@article{reddy2022shopping,
  title={Shopping Queries Dataset: A Large-Scale {ESCI} Benchmark for Improving Product Search},
  author={Reddy, Chandan K. and M{\\`a}rquez, Llu{\\'i}s and Valero, Fran and Rao, Nikhil and Zaragoza, Hugo and
          Bandyopadhyay, Sambaran and Biswas, Arnab and Xing, Anlu and Subbian, Karthik},
  journal={arXiv preprint arXiv:2206.06588},
  year={2022}
}""")
    dataset(id="amazon-berkeley-objects", name="Amazon Berkeley Objects (ABO)", tasks=["COM-2"],
            homepage="https://amazon-berkeley-objects.s3.amazonaws.com/index.html", license="CC-BY-4.0",
            license_url="https://amazon-berkeley-objects.s3.amazonaws.com/LICENSE-CC-BY-4.0.txt",
            content="One Amazon.com product listing's metadata (name, brand, bullet points, description, colour, "
                    "material, style, dimensions, weight) from the ABO listings shard listings_0.json.gz.",
            content_license="CC-BY-4.0",
            content_terms="The ABO site describes itself as \"A CC BY 4.0-licensed dataset of Amazon products with "
                          "metadata, catalog images, and 3D models\" and ships LICENSE-CC-BY-4.0.txt in the archive; "
                          "the metadata is Amazon's own catalogue data, released by Amazon under that licence.",
            labelled_by="the seller's own product_type field in the listing",
            changes="product_type and browse-node fields removed (they are the answer); hidden search keywords, "
                    "image, spin and 3D-model identifiers, marketplace and country fields removed; only en_US values "
                    "kept; dimensions and weight flattened to text.",
            selection="Listings for the US marketplace with an en_US name and one of eight product types, walked in "
                      "sha256 order of item_id and filled to per-type quotas; fabric swatches and listings with no "
                      "bullet point or description excluded by rule; hand-skips listed in COM2_SKIP.",
            citation="Collins et al., ABO: Dataset and Benchmarks for Real-World 3D Object Understanding, CVPR 2022.",
            bibtex="""@inproceedings{collins2022abo,
  title={{ABO}: Dataset and Benchmarks for Real-World {3D} Object Understanding},
  author={Collins, Jasmine and Goel, Shubham and Deng, Kenan and Luthra, Achleshwar and Xu, Leon and Gundogdu, Erhan
          and Zhang, Xi and Vicente, Tomas F. Yago and Dideriksen, Thomas and Arora, Himanshu and Guillaumin, Matthieu
          and Malik, Jitendra},
  booktitle={Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)},
  pages={21126--21136},
  year={2022}
}""")
    dataset(id="edgar-corpus-10k-business", name="EDGAR-CORPUS (10-K Item 1) with SEC EDGAR SIC codes",
            tasks=["COM-3"], homepage="https://huggingface.co/datasets/eloukas/edgar-corpus", license="Apache-2.0",
            license_url="https://huggingface.co/datasets/c3po-ai/edgar-corpus",
            content="The opening 2,000 characters of Item 1 (Business) of a company's Form 10-K for fiscal 2020, as "
                    "parsed by EDGAR-CORPUS, with the company's name replaced by \"[the Company]\"; the answer comes "
                    "from the SIC code in the filer's SEC EDGAR submissions record.",
            content_license="Public domain",
            content_terms="Form 10-K filings are public records filed with the US Securities and Exchange Commission "
                          "and published on EDGAR; the SEC states that its web content is in the public domain "
                          "(https://www.sec.gov/privacy#dissemination). EDGAR-CORPUS and its parquet mirror are "
                          "Apache-2.0 (https://huggingface.co/datasets/eloukas/edgar-corpus). The submissions API is "
                          "SEC open data (https://www.sec.gov/search-filings/edgar-application-programming-interfaces).",
            labelled_by="the SIC code SEC EDGAR records for the filer, mapped to its SIC division by code range",
            changes="Item 1 cut to its first 2,000 characters with a marker; the filer's current and former names and "
                    "listed aliases replaced by \"[the Company]\"; whitespace normalised.",
            selection="14 fixed 10-row pages of the year_2020 config; filings with an Item 1 of at least 6,000 "
                      "characters, walked in sha256 order of filename and filled to per-division quotas; filers "
                      "outside the seven divisions dropped by rule; at most one blank-check company; hand-skips "
                      "listed in COM3_SKIP.",
            citation="Loukas et al., EDGAR-CORPUS: Billions of Tokens Make The World Go Round, ECONLP 2021.",
            bibtex="""@inproceedings{loukas2021edgar,
  title={{EDGAR-CORPUS}: Billions of Tokens Make The World Go Round},
  author={Loukas, Lefteris and Fergadiotis, Manos and Androutsopoulos, Ion and Malakasiotis, Prodromos},
  booktitle={Proceedings of the Third Workshop on Economics and Natural Language Processing (ECONLP)},
  pages={13--18},
  year={2021}
}""")


# ---------------------------------------------------------------------------------------------------------------
# COM-1  ESCI: does this product match the query?
# ---------------------------------------------------------------------------------------------------------------
COM1_OPTIONS = {
    "exact": "The product is relevant for the query and satisfies all of the query's specifications.",
    "substitute": "The product fails some aspect of the query but can be used as a functional substitute.",
    "complement": "The product does not fulfil the query but could be used together with an exact match.",
    "irrelevant": "The product is irrelevant, or fails a central aspect of the query.",
}
COM1_LABELS = {"Exact": "exact", "Substitute": "substitute", "Complement": "complement", "Irrelevant": "irrelevant"}
COM1_QUOTA = {"exact": 8, "substitute": 8, "complement": 7, "irrelevant": 7}
COM1_BANNED = ["exact", "substitut", "complement", "irrelevant"]   # titles are the shopper's own query
ADULT = re.compile(r"\b(didlo|dildo|sex|sexy|penis|vagina|vibrator|anal|porn|nude)\b", re.I)
CJK = re.compile(r"[　-鿿＀-￯]")
TAGS = re.compile(r"<[^>]+>")

# example_id -> reason. Pairs passed over in rank order because a careful reader could label them two ways, or
# because the listing is not in English.
COM1_SKIP = {
    1632987: "Exact: a check-valve repair kit is not clearly a whole pump rebuild kit, and the listing has no details.",
    1217723: "Exact: a Signature-line shaping skinny jean for a 'levis skinny curvy' query; exact or substitute is arguable.",
    2007007: "Exact: the query 'this is not a drill' names no product type, so any product with the phrase is arguable.",
    1197247: "Exact: the Osmo kit teaches drawing and physics, not English; the label does not follow from the record.",
    1003510: "Substitute: the title says straight-leg but the bullets say 'skinny fit jean' and 'high-waisted'.",
    1974912: "Irrelevant: an ESL learner's textbook for a 'teaching english as a second language' query could be a substitute.",
    2006970: "Substitute: German-language edition; the listing is not in English.",
    1752825: "Complement: the primer-bulb and fuel-line kit includes a fuel filter, so exact or substitute is arguable.",
    178421: "Irrelevant: a stand for an Echo Show, which itself can serve as an Alexa alarm clock; complement is arguable.",
    84678: "Complement: a set of two candle holders for a '3 candle holder' query reads as a substitute.",
    1940564: "Complement: Switch accessories for a Nintendo DS game query; irrelevant is at least as defensible.",
    1298428: "Exact: a crystal-ball night light 'for film fans' with no Mario in the listing; the label does not follow.",
    744897: "Irrelevant: an electric fireplace with a heater for a 'without heater' query; substitute is arguable.",
    1632982: "Irrelevant: a pump antifreeze/lubricant for a 'pressure washer oil' query; substitute is arguable.",
    2233477: "Complement: a case made for the JBL Xtreme 3 for an 'xtreme 2' query; irrelevant is at least as defensible.",
    466193: "Complement: Echo Auto is itself car electronics, so exact is at least as defensible.",
    226303: "Complement: the query is in Spanish ('armas y proyectiles de juguete'), and the vest kit includes darts.",
    1632880: "Complement: an M-LOK pressure-switch mounting plate for a Picatinny-rail query; substitute is at least as defensible.",
    1874128: "Complement: a KINGMAX multitool for a 'sog multitool' query is a substitute, not a complement.",
}

# example_id -> rationale pointing at the evidence. Titles are built from the query, which never carries the label.
COM1_RATIONALE = {
    # exact
    1632898: "The query wants a pressure-washer hose and the product is a 50-foot pressure-washer hose with M22 fittings.",
    913545: "The chalkboard labels are sold as reusable jar labels that peel off and re-stick, which is what 'removable' asks for.",
    1099956: "JBL Reflect Mini earbuds with a 3.5 mm cable; the bullets say they are wired and not Bluetooth.",
    915674: "A twelve-colour set of extra-fine glitter sold for art and crafts, slime and scrapbooking.",
    2141643: "A USB-heated neck wrap sold as a hot compress for neck soreness, which is exactly a warm compress for the neck.",
    1206410: "An L-shaped sectional sofa whose chaise is reversible, so it can be set up left-facing.",
    2007058: "A men's T-shirt printed with the phrase 'This is Not A Drill', matching the query word for word.",
    1752761: "A 12 V lithium battery made for Ryobi CB120L/CB121L tools, matching both the brand and the voltage.",
    # substitute
    682321: "The query asks for disposable shavers; this is a reusable razor handle with replacement cartridges, so it "
            "does the same job without being disposable.",
    277938: "The shopper misspelt binoculars; a monocular serves the same purpose with one eyepiece instead of two.",
    130499: "The query asks for nine resistance loops; this is a set of three loop bands, the same product in a smaller count.",
    1690502: "A power reclining sofa with storage armrests and cup holders but no drop-down table, so it misses one "
             "feature of the query.",
    1151923: "A convertible sectional sofa that folds out, but the listing says it is sized for small spaces and never "
             "claims a king-size bed.",
    1879272: "Bluetooth patio speakers by Sound Appeal rather than Sonos; they fill the same role without being the brand asked for.",
    1231371: "An inflatable pool float with a canopy, but a generic tropical island rather than a Lightning McQueen design.",
    2175243: "A wide-mouth glass jar suitable for candy, but with a glass lid rather than the brushed tin lid the query names.",
    # complement
    1099963: "A carrying case made for the JBL Endurance Peak earbuds; it is not the earbuds but is used with them.",
    1752817: "A primer bulb and fuel line kit for Ryobi trimmers; it is fitted alongside a fuel filter but does not include one.",
    827519: "Floating practice golf balls are hit onto a floating green, so they go with the item searched for rather than being it.",
    1921742: "A Storm single-ball bowling bag carries the bowling ball the shopper is looking for; it is not the ball itself.",
    1879332: "An engraved card that slips into a wallet as a gift for a son; it goes inside the wallet rather than being one.",
    2233470: "A handle strap listed as designed for the JBL Xtreme 2 speaker; it is an add-on for the speaker, not the speaker.",
    827592: "Water gel beads sold as 'vase fillers for floating pearls': they suspend the pearls in a vase but are not pearls.",
    # irrelevant
    178544: "An Echo Dot smart speaker with no clock display and nothing to mount on a wall; it fails the central 'clock wall' part.",
    394616: "An ionic foot-bath detox machine for people, nothing to do with cleaning or resurfacing a bowling ball.",
    843170: "The query is a quotation about forgiveness, not a product; a forehead thermometer has no connection to it.",
    1830335: "The shopper wants a silver art-deco ring; the product is a Ring-brand security camera, matching only the word 'ring'.",
    1404078: "A women's packable down coat is not a hat, and nothing in the listing refers to Mount Shasta.",
    690858: "A toddler-sized Paw Patrol costume for a query that asks for an adult dog-catcher costume: wrong size and wrong character.",
    2054751: "The Trijicon RMR is a pistol reflex sight; this is a rail-mounted tactical flashlight, a different device.",
}


def _esci_product(r):
    bullets = [b.strip() for b in (r["product_bullet_point"] or "").split("\n") if b.strip()]
    desc = TAGS.sub(" ", (r["product_description"] or "").replace("<br>", "\n"))
    desc = re.sub(r"[ \t]+", " ", desc).strip()
    product = {"title": r["product_title"].strip()}
    if r["product_brand"]:
        product["brand"] = r["product_brand"]
    if r["product_color"]:
        product["color"] = r["product_color"]
    if bullets:
        product["bullet_points"] = bullets
    if desc:
        product["description"] = _cut(desc, 800)
    return product


def _com1():
    records = []
    for off in ESCI_OFFSETS:
        records += _hf_rows(f"esci/train-{off:07d}.json")
    # The mirror joins products by product_id without the locale, so a US example can appear two or three times
    # with the Japanese or Spanish product text; such example_ids are dropped by rule.
    copies = collections.Counter(r["example_id"] for r in records)
    taken = {k: 0 for k in COM1_QUOTA}
    seen_queries = set()
    picked = []
    for r in sorted(records, key=lambda r: rank(r["example_id"])):
        query = r["query"].strip()
        if (copies[r["example_id"]] > 1 or r["product_locale"] != "us" or not r["product_title"]
                or CJK.search(r["product_title"]) or len(query) > 100 or any(ord(c) > 127 for c in query)
                or ADULT.search(query)):
            continue
        gold = COM1_LABELS[r["esci_label"]]
        if r["query_id"] in seen_queries or taken[gold] >= COM1_QUOTA[gold]:
            continue
        if r["example_id"] in COM1_SKIP:
            continue
        seen_queries.add(r["query_id"])
        taken[gold] += 1
        picked.append((r, query, gold))
    assert taken == COM1_QUOTA, taken
    for r, query, gold in picked:
        assert r["example_id"] in COM1_RATIONALE, f"COM-1: no rationale for example {r['example_id']} ({gold}: {query!r})"
        rationale = COM1_RATIONALE[r["example_id"]]
        title = f"Search result · “{query}”"
        _no_words(title, COM1_BANNED, f"COM-1 {r['example_id']}")
        row("COM-1", f"esci-{r['example_id']}", title=title, gold=gold, rationale=rationale,
            state={"search_query": query, "marketplace": "amazon.com", "product": _esci_product(r)},
            source={**ESCI, "record_id": f"example_id {r['example_id']} (query_id {r['query_id']}, product "
                                         f"{r['product_id']})",
                    "original_label": r["esci_label"]})


# ---------------------------------------------------------------------------------------------------------------
# COM-2  ABO: what type of product is this?
# ---------------------------------------------------------------------------------------------------------------
COM2_TYPES = {  # option key -> (ABO product_type, description, quota)
    "chair": ("CHAIR", "A chair, stool, recliner or other single seat.", 4),
    "sofa": ("SOFA", "A sofa, loveseat or sectional.", 4),
    "table": ("TABLE", "A table, console, nightstand or other table-top furniture.", 4),
    "rug": ("RUG", "An area rug or runner.", 4),
    "lamp": ("LAMP", "A table, desk or floor lamp.", 4),
    "wall_art": ("WALL_ART", "A print, canvas or other art made to hang on a wall.", 4),
    "shoes": ("SHOES", "Footwear.", 3),
    "grocery": ("GROCERY", "Food, drink or other grocery-aisle goods.", 3),
}
COM2_BANNED = ["chair", "seat", "stool", "recliner", "sofa", "couch", "loveseat", "sectional", "table", "nightstand",
               "console", "rug", "runner", "lamp", "light", "art", "print", "canvas", "frame", "shoe", "boot",
               "sandal", "loafer", "sneaker", "grocery", "food", "snack", "organic"]
COM2_FIELDS = ["item_name", "brand", "bullet_point", "product_description", "color", "material", "style", "pattern",
               "item_shape", "fabric_type", "finish_type", "model_name", "model_number", "model_year"]

# item_id -> reason. Listings passed over in rank order.
COM2_SKIP = {
    "B074MG12PM": "GROCERY: a fizzing bath bomb; a reader would not call a bath product grocery.",
    "B07MBFDHRY": "TABLE: sold as a 'Garden Stool or Side Table', and stools fall under the chair option.",
}


def _abo_en(values):
    return [v["value"] for v in values or [] if v.get("language_tag") == "en_US" and str(v.get("value", "")).strip()]


def _abo_measure(m):
    v = m.get("normalized_value") or m
    return f"{v['value']} {v['unit']}"


def _abo_listing(r):
    out = {}
    for k in COM2_FIELDS:
        if k not in r:
            continue
        if k in ("model_number", "model_year"):
            vals = [str(v["value"]) for v in r[k] if str(v.get("value", "")).strip()]
        else:
            vals = _abo_en(r[k])
        if not vals:
            continue
        if k == "bullet_point":
            out["bullet_points"] = vals
        elif k == "product_description":
            out["description"] = _cut(TAGS.sub(" ", " ".join(vals)), 800)
        else:
            out[k] = vals[0] if len(vals) == 1 else vals
    if r.get("item_dimensions"):
        out["dimensions"] = ", ".join(f"{d} {_abo_measure(m)}" for d, m in r["item_dimensions"].items())
    if r.get("item_weight"):
        out["weight"] = _abo_measure(r["item_weight"][0])
    return out


def _com2():
    with gzip.open(SOURCE_DIR / "abo/listings_0.json.gz", "rt", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]
    by_type = {t: k for k, (t, _, _) in COM2_TYPES.items()}
    taken = {k: 0 for k in COM2_TYPES}
    picked = []
    for r in sorted(records, key=lambda r: rank(r["item_id"])):
        pt = (r.get("product_type") or [{}])[0].get("value")
        names = _abo_en(r.get("item_name"))
        if r.get("country") != "US" or pt not in by_type or not names or "swatch" in names[0].lower():
            continue
        if not (_abo_en(r.get("bullet_point")) or _abo_en(r.get("product_description"))):
            continue
        key = by_type[pt]
        if taken[key] >= COM2_TYPES[key][2] or r["item_id"] in COM2_SKIP:
            continue
        taken[key] += 1
        picked.append((r, key, pt))
    assert taken == {k: q for k, (_, _, q) in COM2_TYPES.items()}, taken
    for r, key, pt in picked:
        listing = _abo_listing(r)
        title = f"Amazon listing · item {r['item_id']}"
        row("COM-2", f"abo-{r['item_id']}", title=title, gold=key,
            rationale=f"The seller filed this listing under product type {pt}; the listing is named "
                      f"\"{_cut(listing['item_name'], 90)}\".",
            state={"marketplace": "amazon.com", "listing": listing},
            source={**ABO, "record_id": f"item_id {r['item_id']} (listings_0.json.gz)", "original_label": pt})


# ---------------------------------------------------------------------------------------------------------------
# COM-3  EDGAR-CORPUS Item 1 + SEC SIC code: which industry is this company in?
# ---------------------------------------------------------------------------------------------------------------
COM3_DIVISIONS = {  # key -> (SIC range, description)
    "mining": ((1000, 1499), "Mining and energy extraction: metal and coal mining, oil and gas extraction, drilling "
                             "and oilfield services (SIC 1000–1499)."),
    "manufacturing": ((2000, 3999), "Manufacturing: making goods, from food, apparel and chemicals to drugs, "
                                    "machinery, electronics and medical devices (SIC 2000–3999)."),
    "transport_comms_utilities": ((4000, 4999), "Transportation, communications and utilities: shipping, pipelines, "
                                                "telecoms, broadcasting, electric, gas, water, waste (SIC 4000–4999)."),
    "wholesale": ((5000, 5199), "Wholesale trade: distributing goods to businesses and resellers rather than to "
                                "consumers (SIC 5000–5199)."),
    "retail": ((5200, 5999), "Retail trade: selling goods to consumers through stores or online, including eating "
                             "and drinking places (SIC 5200–5999)."),
    "finance": ((6000, 6799), "Finance, insurance and real estate: banks, lenders, brokers, insurers, REITs, "
                              "investment vehicles and blank-check companies (SIC 6000–6799)."),
    "services": ((7000, 8999), "Services: software and IT, business and professional services, hotels, health care, "
                               "entertainment, equipment rental (SIC 7000–8999)."),
}
COM3_QUOTA = {"manufacturing": 6, "finance": 6, "services": 6, "transport_comms_utilities": 4, "mining": 4,
              "retail": 3, "wholesale": 1}   # one wholesaler among the 116 candidate filers
COM3_MIN_ITEM1, COM3_EXCERPT = 6000, 2000
COM3_BLANK_CHECK, COM3_MAX_BLANK_CHECKS = "6770", 1
NAME_SUFFIXES = re.compile(r"\b(inc|incorporated|corp|corporation|co|company|ltd|limited|llc|l\.l\.c|lp|l\.p|plc|"
                           r"holdings?|group|international|partnership|trust|bancorp|bancshares|n\.v|s\.a)\b\.?",
                           re.I)

# filename -> reason. Filings passed over in rank order.
COM3_SKIP = {
    "748268_2020.htm": "SIC 7372 software, but the 2020 filing describes designing and selling drones (Red Cat).",
    "1830029_2020.htm": "a blank-check company in 2020 whose SIC (6199) reflects the business it later merged with; "
                        "Horizon Acquisition is the one blank check kept.",
    "1604464_2020.htm": "clinical-stage biotech with no marketed product: the SEC files such companies under 2834/2836 "
                        "(manufacturing) or 8731 (research services) inconsistently, so services is defensible.",
    "1260990_2020.htm": "clinical-stage biotech with no marketed product (see 1604464).",
    "1413119_2020.htm": "a development-stage spider-silk fibre company; manufacturing (2820) or research services is arguable.",
    "1490873_2020.htm": "the opening 2,000 characters give the address, trading suspension and share history, not the business.",
    "1685237_2020.htm": "shell company; the opening is forward-looking-statement boilerplate with no business description.",
    "1371782_2020.htm": "an oil royalty trust managed by a bank trustee; finance is as defensible as mining from the text.",
    "778946_2020.htm": "timeshare sales and resort management (SIC 6531 real estate); services is defensible from the text.",
    "1383394_2020.htm": "SIC 1389 oilfield services, but the filing says the company moved to manufacturing from waste.",
    "771999_2020.htm": "SIC 2650 paperboard boxes, but the filing lists nine business lines from marketing to fintech.",
    "1522727_2020.htm": "natural-gas compression services (SIC 4922); the opening describes only the partnership structure, "
                        "and services or oilfield services is defensible.",
    "1497649_2020.htm": "a quartz-sand venture with a deposit and a planned factory; mining or manufacturing is arguable.",
    "1086745_2020.htm": "SIC 4899 communications, but after its 2020 merger the filer designs and manufactures electric "
                        "vehicles (AYRO).",
    "1553404_2020.htm": "the opening 2,000 characters are forward-looking-statement boilerplate with no business description.",
    "788611_2020.htm": "SIC 4700 transportation services (NextTrip), but the 2020 filing describes Sigma Labs' 3D-printing "
                       "quality-assurance software.",
}
# filename -> extra names used in the text for the filer (short names, brands, ticker) to redact, matched
# case-sensitively as whole words.
COM3_ALIASES = {
    "1004036_2020.htm": ["Tanger Factory Outlet Centers", "Tanger"],
    "1282224_2020.htm": ["Dolphin", "DLPN"],
    "876167_2020.htm": ["Progress"],
    "1350653_2020.htm": ["Alphatec"],
    "949039_2020.htm": ["Diamond Offshore"],
    "860731_2020.htm": ["Tyler"],
    "1428439_2020.htm": ["Roku"],
    "1169055_2020.htm": ["Noble"],
    "75208_2020.htm": ["Overseas Shipholding", "OSG"],
    "1573516_2020.htm": ["Murphy USA"],
    "1696558_2020.htm": ["Jerash Holdings", "Jerash"],
    "1065332_2020.htm": ["NIC"],
    "887919_2020.htm": ["Premier"],
    "1627606_2020.htm": ["DTEA"],
    "1661920_2020.htm": ["Lonestar"],
    "61339_2020.htm": ["MGE Energy", "MGE"],
    "1144215_2020.htm": ["Acuity"],
    "75208_2020.htm": ["Overseas Shipholding", "OSG", "www.osg.com"],
    "811156_2020.htm": ["CMS"],
    "1397911_2020.htm": ["LPL"],
    "1696558_2020.htm": ["Jerash Holdings", "Jerash", "www.jerashholdings.com"],
    "1573516_2020.htm": ["Murphy USA", "Murphy Express"],
}


def _division(sic):
    code = int(sic) if sic else -1
    for key, ((lo, hi), _) in COM3_DIVISIONS.items():
        if lo <= code <= hi:
            return key
    return None


def _name_variants(name):
    """The name as filed, without punctuation noise, and without corporate suffixes and EDGAR's /STATE/ tags."""
    clean = re.sub(r"/[A-Z]{2}/?|/\s*[A-Z]{2}$", " ", name)
    clean = re.sub(r"\s+", " ", clean).strip(" ,.")
    variants = {name.strip(), clean}
    short = NAME_SUFFIXES.sub(" ", clean)
    short = re.sub(r"\s+", " ", short).strip(" ,.&")
    if len(short) >= 5:
        variants.add(short)
    return {v for v in variants if len(v) >= 4}


def _redact(text, names, aliases):
    """Replace the filer's names (case-insensitive) and listed aliases (case-sensitive) with [the Company]."""
    for name, flags in [(n, re.I) for n in sorted(names, key=len, reverse=True)] + \
                       [(a, 0) for a in sorted(aliases, key=len, reverse=True)]:
        pattern = r"\b" + r"\s*".join(re.escape(part) for part in re.split(r"\s+", name)) + r"(?:'s|’s)?\b"
        text = re.sub(pattern, "[the Company]", text, flags=flags)
    text = re.sub(r"(\[the Company\]\s*)+", "[the Company] ", text)
    text = re.sub(r"\[the Company\]\s*,?\s*(Inc\.?|Incorporated|Corp\.?|Corporation|Ltd\.?|Limited|plc|LLC|L\.P\.|"
                  r"N\.V\.|Holdings?)(?=[\s,.;:)])", "[the Company]", text)
    text = re.sub(r"\[the Company\]\s+([,.;:)”\"'])", r"[the Company]\1", text)
    text = re.sub(r"\[the Company\]\.,", "[the Company],", text)                 # "…, Inc., incorporated" leftovers
    text = re.sub(r"\[the Company\]\.\s+(?=[a-z(“\"])", "[the Company] ", text)
    return text


def _com3():
    records = []
    for off in EDGAR_OFFSETS:
        records += _hf_rows(f"edgar-corpus-2020/train-{off:05d}.json")
    assert len({r["filename"] for r in records}) == len(records)
    candidates = [r for r in records if len(r["section_1"] or "") >= COM3_MIN_ITEM1]
    assert sorted(int(r["cik"]) for r in candidates) == COM3_CIKS, "COM3_CIKS must list every candidate filer"
    taken = {k: 0 for k in COM3_QUOTA}
    blank_checks = 0
    picked = []
    for r in sorted(candidates, key=lambda r: rank(r["filename"])):
        sub = json.loads((SOURCE_DIR / f"sec-submissions/CIK{int(r['cik']):010d}.json").read_text(encoding="utf-8"))
        key = _division(sub.get("sic"))
        if key is None or taken[key] >= COM3_QUOTA[key]:
            continue
        if sub.get("sic") == COM3_BLANK_CHECK:
            if blank_checks >= COM3_MAX_BLANK_CHECKS:
                continue
        if r["filename"] in COM3_SKIP:
            continue
        blank_checks += sub.get("sic") == COM3_BLANK_CHECK
        taken[key] += 1
        picked.append((r, sub, key))
    assert taken == COM3_QUOTA, taken
    for r, sub, key in picked:
        names = set()
        for n in [sub["name"]] + [f["name"] for f in sub.get("formerNames", [])]:
            names |= _name_variants(n)
        text = re.sub(r"\s+", " ", r["section_1"]).strip()
        excerpt = _redact(_cut(text, COM3_EXCERPT), names, COM3_ALIASES.get(r["filename"], []))
        lo, hi = COM3_DIVISIONS[key][0]
        row("COM-3", f"edgar-{r['cik']}-2020", gold=key,
            title=f"10-K Item 1 · fiscal 2020 · filer CIK {int(r['cik'])}",
            rationale=f"SEC EDGAR records the filer's SIC code as {sub['sic']} ({sub['sicDescription']}), which is in "
                      f"the {key.replace('_', ', ')} division (SIC {lo}–{hi}).",
            state={"filing": "Form 10-K for fiscal year 2020, Item 1 (Business), opening excerpt; the company's name "
                             "is replaced by [the Company]",
                   "item_1_excerpt": excerpt},
            source={**EDGAR, "record_id": f"EDGAR-CORPUS {r['filename']} (CIK {int(r['cik'])})",
                    "original_label": f"SIC {sub['sic']} {sub['sicDescription']}"})


# ---------------------------------------------------------------------------------------------------------------
def define():
    _datasets()
    task("COM-1", category=CATEGORY, name="Does this product match the query?",
         ask="How relevant is this product to the shopping query?",
         instruction="You are given a shopper's search query on amazon.com and one product returned for it. Judge "
                     "the product against the query using Amazon's ESCI scale: exact if it satisfies every "
                     "specification in the query; substitute if it misses some aspect but would do the same job; "
                     "complement if it does not fulfil the query but would be used together with a product that does; "
                     "irrelevant if it fails a central aspect of the query or has nothing to do with it.",
         options=COM1_OPTIONS, shape="classify", input_type="search query and product listing", modality="text",
         expertise="none", contamination="medium", label_origin="trained annotators")
    task("COM-2", category=CATEGORY, name="What type of product is this?",
         ask="What type of product is this listing?",
         instruction="You are given the metadata of one amazon.com product listing with its product-type field "
                     "removed. Choose the product type the seller filed it under.",
         options={k: d for k, (_, d, _) in COM2_TYPES.items()}, shape="classify", input_type="product listing",
         modality="text", expertise="none", contamination="low", label_origin="self-declared")
    task("COM-3", category=CATEGORY, name="Which industry is this company in?",
         ask="Which SIC division is this company in?",
         instruction="You are given the opening of Item 1 (Business) from a US public company's Form 10-K, with the "
                     "company's name removed. Choose the Standard Industrial Classification (SIC) division that the "
                     "SEC assigns to the company. Use the SIC rules: drug and biologics developers are manufacturing; "
                     "restaurants are retail trade; REITs and blank-check companies are finance; software, hospitals "
                     "and hotels are services; broadcasting, streaming and pipelines are transportation, "
                     "communications and utilities.",
         options={k: d for k, ((_, _), d) in COM3_DIVISIONS.items()}, shape="classify",
         input_type="10-K business description", modality="text", expertise="practitioner", contamination="medium",
         label_origin="objective record")
    _com1()
    _com2()
    _com3()
