"""documents: document pages and meeting transcripts, three tasks.

DOC-1  Where is this page from?              DocLayNet v1.2 (CDLA-Permissive-1.0), IBM Research's human labels
       A rendered PDF page (image plus the PDF's own text cells) and the six DocLayNet document categories.
DOC-2  Decision, action item, or neither?    AMI Meeting Corpus manual annotations (CC BY 4.0)
       A 10-utterance window of a real meeting transcript with one utterance highlighted; the answer is what the
       corpus's summary annotators linked that utterance to.
DOC-3  Which summary is this meeting's?      AMI Meeting Corpus abstractive summaries (CC BY 4.0)
       A contiguous transcript window and four real annotator-written summaries, one of this meeting.

Dropped: "What kind of document is this page?" on RVL-CDIP. Its images are the IIT-CDIP tobacco-litigation
scans from the UCSF Industry Documents Library, whose copyright page says the creating companies "may still hold
the rights" and that material "cannot be 'substantially' reproduced ... without the copyright holder's
permission" (fair use only). That is not a redistribution licence, so no RVL-CDIP row was built.

Sampling rules (all deterministic, no model output):

DOC-1. Seventeen fixed 15-row windows of the DocLayNet test split are fetched through the Hugging Face
datasets-server rows API (DLN_OFFSETS below, chosen after probing where each document category sits in the
split; the FAA collection is avoided because its orders and handbooks read as manuals as much as regulations, so
"law or regulation" rows come from statute collections). Candidates are ordered by rank(page_hash). A page is
kept if its PDF text cells total at least 400 characters (so text-only models get a fair track) and at least 60%
of its letters are Latin script (a generalist reader must be able to read the page). At most 3 pages
per source PDF and 5 pages per category. The image is the dataset's own 1025x1025 page rendering (JPEG from the
rows API, under 400 KB unmodified); the text rendering lists every human-annotated layout block with its class
and the PDF text inside it, in top-to-bottom reading order.

DOC-2. Meetings with a summary-link file are visited in rank(meeting) order, at most one row per meeting, until
each class has 10 rows. Within a meeting, dialogue acts are candidates in rank(dialogue-act id) order:
  decision    linked to at least one sentence of the summary's <decisions> section and to none of <actions>;
              type Inform, Suggest or Assess; shares at least three content words (stemmed, stopwords removed)
              with a linked decision sentence; is not hedged ("maybe", "I think", "could": HEDGE), since a hedged
              suggestion is not itself a decision; mentions none of the money words in BRIEF_WORDS, because the
              selling price, profit target and cost ceiling are given to the team in the project brief and
              annotators filed those announcements inconsistently as decisions or as background.
  action item linked to at least one <actions> sentence and to none of <decisions>; type Inform, Suggest, Offer
              or Assess; shares at least three content words with a linked action sentence that names who will
              do it ("The industrial designer will ...", "The group will ...").
  neither     in the extractive summary and linked only to <abstract> sentences (never <decisions>, <actions> or
              <problems>); type Inform or Elicit-Inform; contains none of the commitment, planning or
              constraint words in NEITHER_EXCLUDE and none of BRIEF_WORDS.
Every candidate has at least 8 words, ends in sentence punctuation, is not a question and has no [unclear]
span. The window is the 5 non-empty dialogue acts before and after the highlighted one, in time order across
all speakers.

DOC-3. Meetings with an abstractive summary are visited in rank(meeting) order, at most one per meeting series
(e.g. ES2008), until 30 rows. The transcript window starts at the dialogue act 30% of the way through the
meeting and runs until 3,500 characters. For a scenario meeting the three distractors are the other three
meetings of the same series (the same team's kick-off, functional-design, conceptual-design and detailed-design
meetings), so the reader must tell which stage the excerpt is from; for a non-scenario meeting they are other
non-scenario meetings in rank(meeting + other) order. The row is kept only if the true summary shares at least
4 distinctive content words with the window and at least 2 more than any distractor does. The gold letter is
rank-assigned. Titles and states carry no meeting id, since AMI ids encode the meeting stage.
"""
from __future__ import annotations

import collections
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

from . import dataset, task, row, rank, SOURCES as SOURCE_DIR, ASSETS

MARK = "…[{} chars truncated]"

# ---------------------------------------------------------------- sources

DLN_DATASET = "docling-project/DocLayNet-v1.2"
DLN_LEN = 15
# Test-split offsets by category (probed 2026-09-23): financial 0–1500 and 4750+; scientific 1550–2400; laws
# 2450–2500 (Botswana, China), 2800–3450 (FAA, Japan), 4700 (Russia); tenders 2550–2750; manuals 3500–3950
# and 4500–4600; patents 4000–4450.
DLN_OFFSETS = [300, 1200, 4800,            # financial reports
               1600, 1900, 2300,           # scientific articles
               2450, 2500, 3350, 4700,     # laws and regulations (statute collections)
               2560, 2700,                 # government tenders
               3600, 3800, 4520,           # manuals
               4050, 4250, 4450]           # patents
DLN_URL = ("https://datasets-server.huggingface.co/rows?dataset=docling-project%2FDocLayNet-v1.2"
           "&config=default&split=test&offset={off}&length={n}")

AMI_ZIP = "https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip"

SOURCES = [{"dataset": "DocLayNet v1.2", "url": DLN_URL.format(off=off, n=DLN_LEN),
            "path": f"doclaynet/test-{off:05d}.json"} for off in DLN_OFFSETS] + [
           {"dataset": "AMI Meeting Corpus manual annotations 1.6.2", "url": AMI_ZIP,
            "path": "ami/ami_public_manual_1.6.2.zip"}]

ASSET_DIR = ASSETS / "documents"


def _datasets():
    dataset(
        id="doclaynet", name="DocLayNet v1.2", tasks=["DOC-1"],
        homepage="https://github.com/DS4SD/DocLayNet",
        license="CDLA-Permissive-1.0",
        license_url="https://huggingface.co/datasets/docling-project/DocLayNet-v1.2",
        content="A page image rendered from a public PDF (annual report, SEC filing, arXiv paper, statute, EU tender, "
                "IBM manual or patent) with the PDF's own text cells and IBM's human layout annotation.",
        content_license="CDLA-Permissive-1.0",
        content_terms="IBM Research releases the page images, text cells and annotations under CDLA-Permissive-1.0 "
                      "(LICENSE in the repository and the dataset card). The paper says the documents were chosen under "
                      "'open intellectual property constraints' and that 'a large effort went into ensuring that all "
                      "documents are free to use' (Pfitzmann et al. 2022, section 3).",
        labelled_by="DocLayNet's own doc_category metadata, assigned by the dataset's curators when the documents were "
                    "collected (human labels)",
        changes="Nothing changed in the image. The text rendering is built from the dataset's pdf_cells grouped by its "
                "annotated layout boxes and truncated with a marker when over 5,000 characters. File names and "
                "collection names are kept out of the state.",
        selection="Seventeen fixed 15-row windows of the test split; pages ordered by rank(page_hash), kept if their text "
                  "cells total 400+ characters, at most 3 per source PDF and 5 per category.",
        citation="Pfitzmann, Auer, Dolfi, Nassar and Staar (2022). DocLayNet: A Large Human-Annotated Dataset for "
                 "Document-Layout Segmentation. KDD 2022.",
        bibtex="""@inproceedings{pfitzmann2022doclaynet,
  title     = {DocLayNet: A Large Human-Annotated Dataset for Document-Layout Segmentation},
  author    = {Pfitzmann, Birgit and Auer, Christoph and Dolfi, Michele and Nassar, Ahmed S. and Staar, Peter},
  booktitle = {Proceedings of the 28th ACM SIGKDD Conference on Knowledge Discovery and Data Mining},
  pages     = {3743--3751},
  year      = {2022},
  doi       = {10.1145/3534678.3539043}
}""")
    dataset(
        id="ami", name="AMI Meeting Corpus (manual annotations 1.6.2)", tasks=["DOC-2", "DOC-3"],
        homepage="https://groups.inf.ed.ac.uk/ami/corpus/",
        license="CC-BY-4.0",
        license_url="https://groups.inf.ed.ac.uk/ami/corpus/license.shtml",
        content="Human transcripts of recorded English meetings (mostly a role-played four-person design team, some "
                "real research meetings), with the corpus's dialogue-act segmentation and its annotator-written "
                "abstractive summaries (abstract, decisions, actions, problems) linked to the transcript.",
        content_license="CC-BY-4.0",
        content_terms="LICENCE.txt in the annotation release: 'The AMI corpus and its annotations are released under the "
                      "Creative Commons Attribution 4.0 International Public License'. Participants consented to public "
                      "release (https://groups.inf.ed.ac.uk/ami/corpus/ethicsandconsent.shtml); speakers appear only as "
                      "roles or letters.",
        labelled_by="the corpus's trained summary annotators: DOC-2 from which summary section (decisions, actions, "
                    "abstract) they linked the utterance to; DOC-3 from which meeting a summary belongs to (objective record)",
        changes="Words are joined into utterances with the corpus's punctuation; vocal sounds appear as [laugh] etc. and "
                "disfluency markers as '--'. Speakers are shown by role and channel letter. Windows are cut as the module "
                "docstring says.",
        selection="Meetings in rank order, one row per meeting (DOC-2) or per series (DOC-3); dialogue acts and "
                  "distractor summaries in rank order under the written filters in the module docstring.",
        citation="Carletta et al. (2005). The AMI Meeting Corpus: A Pre-announcement. MLMI 2005.",
        bibtex="""@inproceedings{carletta2005ami,
  title     = {The {AMI} Meeting Corpus: A Pre-announcement},
  author    = {Carletta, Jean and Ashby, Simone and Bourban, Sebastien and Flynn, Mike and Guillemot, Mael and
               Hain, Thomas and Kadlec, Jaroslav and Karaiskos, Vasilis and Kraaij, Wessel and Kronenthal, Melissa and
               Lathoud, Guillaume and Lincoln, Mike and Lisowska, Agnes and McCowan, Iain and Post, Wilfried and
               Reidsma, Dennis and Wellner, Pierre},
  booktitle = {Machine Learning for Multimodal Interaction (MLMI 2005)},
  series    = {Lecture Notes in Computer Science},
  volume    = {3869},
  pages     = {28--39},
  year      = {2006},
  doi       = {10.1007/11677482_3}
}""")


# ---------------------------------------------------------------- DOC-1: DocLayNet

DLN_CATEGORIES = {"financial_reports": "financial_report", "scientific_articles": "scientific_article",
                  "laws_and_regulations": "law_or_regulation", "government_tenders": "government_tender",
                  "manuals": "manual", "patents": "patent"}
DLN_LAYOUT = {1: "Caption", 2: "Footnote", 3: "Formula", 4: "List-item", 5: "Page-footer", 6: "Page-header",
              7: "Picture", 8: "Section-header", 9: "Table", 10: "Text", 11: "Title"}
DLN_PER_CATEGORY = 5
DLN_PER_DOCUMENT = 3
DLN_MIN_TEXT = 400
DLN_MIN_LATIN = 0.6
DLN_MAX_RENDER = 5000


def _dln_rows():
    for off in DLN_OFFSETS:
        path = SOURCE_DIR / f"doclaynet/test-{off:05d}.json"
        for item in json.loads(path.read_text())["rows"]:
            yield off, item["row_idx"], item["row"]


def _dln_blocks(r):
    """Layout blocks in reading order: (class, text) from the human boxes and the PDF cells inside them."""
    blocks = []
    for bbox, cat, cells in zip(r["bboxes"], r["category_id"], r["pdf_cells"]):
        lines = collections.defaultdict(list)
        for c in cells:
            if c["text"].strip():
                lines[round(c["bbox"][1] / 6)].append((c["bbox"][0], c["text"].strip()))
        text = "\n".join(" ".join(t for _, t in sorted(lines[y])) for y in sorted(lines))
        blocks.append((bbox[1], bbox[0], DLN_LAYOUT.get(cat, "Block"), text))
    blocks.sort(key=lambda b: (round(b[0] / 25), b[1]))
    return [(cls, text) for _, _, cls, text in blocks]


def _dln_render(blocks):
    out = []
    for cls, text in blocks:
        out.append(f"[{cls}] {text}" if text else f"[{cls}] (no text)")
    s = "\n\n".join(out)
    if len(s) > DLN_MAX_RENDER:
        s = s[:DLN_MAX_RENDER] + MARK.format(len(s) - DLN_MAX_RENDER)
    return s


def _dln_counts(blocks):
    """A neutral, record-derived description of the page: '2 section headers, 7 text blocks, 1 table'."""
    names = {"Caption": "caption", "Footnote": "footnote", "Formula": "formula", "List-item": "list item",
             "Page-footer": "page footer", "Page-header": "page header", "Picture": "picture",
             "Section-header": "section header", "Table": "table", "Text": "text block", "Title": "title"}
    c = collections.Counter(names[cls] for cls, _ in blocks if cls in names)
    parts = []
    for name in ["title", "section header", "text block", "list item", "table", "picture", "caption", "formula",
                 "footnote", "page header", "page footer"]:
        n = c.get(name)
        if n:
            parts.append(f"{n} {name}{'s' if n > 1 else ''}")
    return ", ".join(parts) or "no annotated blocks"


def _dln_candidates():
    cands = []
    for off, idx, r in _dln_rows():
        m = r["metadata"]
        blocks = _dln_blocks(r)
        text = "".join(t for _, t in blocks)
        letters = re.findall(r"[^\W\d_]", text)
        if len(text) < DLN_MIN_TEXT or not letters:
            continue
        if sum(1 for ch in letters if ch.isascii() or "À" <= ch <= "ɏ") < DLN_MIN_LATIN * len(letters):
            continue  # a generalist reader must be able to read the page: mostly Latin script
        cands.append(dict(offset=off, idx=idx, row=r, meta=m, blocks=blocks, key=rank(m["page_hash"])))
    cands.sort(key=lambda c: c["key"])
    per_cat = collections.Counter()
    per_doc = collections.Counter()
    chosen = []
    for c in cands:
        cat, doc = c["meta"]["doc_category"], c["meta"]["original_filename"]
        if per_cat[cat] >= DLN_PER_CATEGORY or per_doc[doc] >= DLN_PER_DOCUMENT:
            continue
        per_cat[cat] += 1
        per_doc[doc] += 1
        chosen.append(c)
    return chosen


def _dln_asset_path(meta):
    return ASSET_DIR / f"doc-1-{meta['page_hash'][:16]}.jpg"


def _doc1():
    titles = set()
    for c in _dln_candidates():
        m, blocks = c["meta"], c["blocks"]
        path = _dln_asset_path(m)
        counts = _dln_counts(blocks)
        title = f"Document page · {counts}"
        if title in titles:
            title += f" · {m['page_hash'][:6]}"
        titles.add(title)
        def wordy(t):
            return len(re.findall(r"[^\W\d_]{3,}", t)) >= 2
        heading = next((t.replace("\n", " ") for cls, t in blocks if cls in ("Title", "Section-header") and wordy(t)),
                       None)
        heading = heading or next((t.replace("\n", " ") for cls, t in blocks if wordy(t)), "")
        heading = heading[:140] + ("…" if len(heading) > 140 else "")
        gold = DLN_CATEGORIES[m["doc_category"]]
        rationale = (f"DocLayNet's metadata files this page under doc_category '{m['doc_category']}' (collection "
                     f"'{m['collection']}'); the first heading on the page reads: \"{heading}\".")
        row("DOC-1", m["page_hash"][:16],
            title=title,
            state={"page": "One page of a PDF document, rendered at 1025×1025 pixels (see image).",
                   "layout_blocks": counts,
                   "text_rendering": _dln_render(blocks)},
            gold=gold, rationale=rationale,
            note=f"Page {m['page_no']} of {m['num_pages']} of the source PDF (DocLayNet test split).",
            source=dict(dataset_id="doclaynet", dataset="DocLayNet v1.2", license="CDLA-Permissive-1.0",
                        url=f"https://huggingface.co/datasets/{DLN_DATASET}/viewer/default/test?row={c['idx']}",
                        citation="Pfitzmann et al. (2022), KDD.", record_id=m["page_hash"],
                        original_label=m["doc_category"], labelled_by="DocLayNet doc_category metadata (human labels)",
                        collection=m["collection"], original_filename=m["original_filename"], page_no=m["page_no"]),
            assets=[{"path": str(path.relative_to(ASSETS.parent.parent)), "mime_type": "image/jpeg",
                     "alt_text": f"A rendered document page with {counts}.",
                     "width": c["row"]["image"]["width"], "height": c["row"]["image"]["height"]}],
            tags=["document-page", "layout"])


def prepare_assets():
    """Download the page images of the chosen DOC-1 rows (run once after fetch_sources; URLs are short-lived)."""
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for c in _dln_candidates():
        path = _dln_asset_path(c["meta"])
        if path.exists():
            continue
        req = urllib.request.Request(c["row"]["image"]["src"], headers={"User-Agent": "DecisionBench/4 (asset fetch)"})
        data = urllib.request.urlopen(req, timeout=120).read()
        assert data[:3] == b"\xff\xd8\xff", f"{path}: not a JPEG"
        assert len(data) <= 400_000, f"{path}: {len(data)} bytes, over 400 KB"
        path.write_bytes(data)
        print(f"saved {len(data):>7,} bytes  {path.name}")


# ---------------------------------------------------------------- AMI parsing

NITE = "{http://nite.sourceforge.net/}"
NID = NITE + "id"
ROLE_NAMES = {"PM": "Project Manager", "ID": "Industrial Designer", "UI": "User Interface Designer",
              "ME": "Marketing Expert"}
STOP = set("""a an the and or but so of to in on at for with from by as is are was were be been being am do does did
have has had will would shall should can could may might must this that these those it its they them their there
here we our us you your i me my he she his her him who what which when where why how not no yes if then than also
very just about into over under out up down off again more most some any all each other such only own same too
than because while after before during through between um uh mm hmm yeah okay like know think mean really kind
sort thing things going gonna get got want well right actually maybe something anything everything one two three
four five six seven eight nine ten twenty thirty hundred remote control team meeting project""".split())
NEITHER_EXCLUDE = re.compile(r"\b(we'll|we will|i'll|i will|you'll|you will|gonna|going to|let's|lets|should|"
                             r"decide|decided|decision|agreed|agree|need to|needs to|have to|has to|must|action|"
                             r"will|plan|plans|planning|planned|may not|cannot|can't|we're not|we are not|"
                             r"maximum|minimum|at most|no more than)\b", re.I)
BRIEF_WORDS = re.compile(r"\b(euro|euros|cost|costs|price|prices|profit|million|sell|selling|sold|budget|"
                         r"international)\b", re.I)
ACTION_AGENT = re.compile(r"^The\s+\w[\w\s-]*?\b(will|are to|is to|were asked|was asked|were instructed|"
                          r"was instructed)\b", re.I)
HEDGE = re.compile(r"\b(maybe|perhaps|i think|i guess|i thought|could|might|possibly|probably|i'd say|i would say)\b",
                   re.I)
DOC2_MIN_OVERLAP = 3


class Ami:
    def __init__(self):
        self.z = zipfile.ZipFile(SOURCE_DIR / "ami/ami_public_manual_1.6.2.zip")
        self.names = set(self.z.namelist())
        self.datypes = {e.get(NID): e.get("gloss") for e in self._xml("ontologies/da-types.xml").iter() if e.get(NID)}
        self.meetings = {}
        for m in self._xml("corpusResources/meetings.xml"):
            self.meetings[m.get("observation")] = dict(
                type=m.get("type"), description=(m.get("description") or "").strip(" -"),
                roles={s.get("nxt_agent"): s.get("role") for s in m})
        self.with_links = sorted(n.split("/")[1].split(".")[0] for n in self.names if n.endswith(".summlink.xml"))
        self.with_abstract = sorted(n.split("/")[1].split(".")[0] for n in self.names if n.endswith(".abssumm.xml"))
        self._cache = {}

    def _xml(self, name):
        return ET.fromstring(self.z.read(name))

    @staticmethod
    def _href(href):
        m = re.match(r"([^#]+)#id\(([^)]+)\)(?:\.\.id\(([^)]+)\))?$", href.strip())
        return m.group(1), m.group(2), m.group(3)

    def _ordered(self, name):
        els = [e for e in self._xml(name).iter() if e.get(NID)]
        return els, {e.get(NID): i for i, e in enumerate(els)}

    @staticmethod
    def _token(el):
        tag = el.tag.split("}")[-1]
        if tag == "w":
            return el.text or "", bool(el.get("punc"))
        if tag == "vocalsound":
            return f"[{el.get('type') or 'sound'}]", False
        if tag == "disfmarker":
            return "--", False
        if tag == "gap":
            return "[unclear]", False
        return "", False

    def speaker(self, meeting, agent):
        role = self.meetings.get(meeting, {}).get("roles", {}).get(agent)
        return f"{ROLE_NAMES[role]} ({agent})" if role in ROLE_NAMES else f"Speaker {agent}"

    def describe(self, meeting):
        info = self.meetings.get(meeting, {})
        if info.get("type") == "scenario":
            return ("AMI scenario meeting: a four-person design team (project manager, industrial designer, user "
                    "interface designer, marketing expert) developing a new TV remote control")
        return "AMI non-scenario meeting: a real working meeting of a research group"

    def dialogue_acts(self, meeting):
        """All dialogue acts of a meeting in time order: id, agent, type, text, start, nwords."""
        if meeting in self._cache:
            return self._cache[meeting]
        out = []
        for agent in "ABCDE":
            wn, dn = f"words/{meeting}.{agent}.words.xml", f"dialogueActs/{meeting}.{agent}.dialog-act.xml"
            if wn not in self.names or dn not in self.names:
                continue
            wels, widx = self._ordered(wn)
            dels, _ = self._ordered(dn)
            for d in dels:
                if d.tag.split("}")[-1] != "dact":
                    continue
                words = []
                for c in d.findall(f"{NITE}child"):
                    _, a, b = self._href(c.get("href"))
                    if a in widx:
                        i, j = widx[a], widx[b] if b in widx else widx[a]
                        words += wels[i:j + 1]
                typ = None
                for p in d.findall(f"{NITE}pointer"):
                    if p.get("role") == "da-aspect":
                        typ = self.datypes.get(self._href(p.get("href"))[1])
                text = ""
                for w in words:
                    s, punc = self._token(w)
                    if s:
                        text += s if (punc or not text) else " " + s
                starts = [float(w.get("starttime")) for w in words if w.get("starttime")]
                nwords = sum(1 for w in words if w.tag.split("}")[-1] == "w" and not w.get("punc"))
                if starts:
                    out.append(dict(id=d.get(NID), agent=agent, type=typ, text=text.strip(), start=min(starts),
                                    nwords=nwords))
        out.sort(key=lambda d: (d["start"], d["agent"]))
        self._cache[meeting] = out
        return out

    def abstract(self, meeting):
        """sentence id -> (section, text) for abstract / decisions / actions / problems."""
        sents = {}
        for sec in self._xml(f"abstractive/{meeting}.abssumm.xml"):
            for s in sec:
                sents[s.get(NID)] = (sec.tag.split("}")[-1], re.sub(r"\s+", " ", s.text or "").strip())
        return sents

    def links(self, meeting):
        """dialogue-act id -> set of abstract sentence ids (the corpus's summary links)."""
        out = collections.defaultdict(set)
        for sl in self._xml(f"extractive/{meeting}.summlink.xml"):
            ext = [self._href(p.get("href"))[1] for p in sl if p.get("role") == "extractive"]
            abs_ = [self._href(p.get("href"))[1] for p in sl if p.get("role") == "abstractive"]
            for e in ext:
                out[e].update(abs_)
        return out

    def in_extractive(self, meeting, da_ids_in_order):
        """Set of dialogue-act ids covered by the extractive summary, resolving id ranges by document order."""
        name = f"extractive/{meeting}.extsumm.xml"
        covered = set()
        if name not in self.names:
            return covered
        order = {d: i for i, d in enumerate(da_ids_in_order)}
        for ext in self._xml(name):
            for c in ext.findall(f"{NITE}child"):
                _, a, b = self._href(c.get("href"))
                if a in order and (b is None or b in order):
                    i, j = order[a], order[b] if b else order[a]
                    covered.update(da_ids_in_order[i:j + 1])
        return covered


def _content_words(text):
    words = re.findall(r"[a-z][a-z'-]+", text.lower())
    return {w.strip("'-") for w in words if len(w) >= 4 and w not in STOP}


def _stem(w):
    for suf in ("ing", "ers", "er", "es", "ed", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[:-len(suf)]
    return w


def _overlap(a, b):
    return len({_stem(w) for w in _content_words(a)} & {_stem(w) for w in _content_words(b)})


# ---------------------------------------------------------------- DOC-2: decision / action / neither

DOC2_PER_CLASS = 10
DOC2_TYPES = {"decision": {"Inform", "Suggest", "Assess"},
              "action_item": {"Inform", "Suggest", "Offer", "Assess"},
              "neither": {"Inform", "Elicit-Inform"}}
DOC2_BEFORE, DOC2_AFTER = 5, 5


def _doc2_label(da, secs):
    if "decisions" in secs and "actions" not in secs:
        return "decision"
    if "actions" in secs and "decisions" not in secs:
        return "action_item"
    if secs == {"abstract"}:
        return "neither"
    return None


def _doc2(ami):
    counts = collections.Counter()
    for meeting in sorted(ami.with_links, key=rank):
        if all(counts[k] >= DOC2_PER_CLASS for k in DOC2_TYPES):
            break
        das = ami.dialogue_acts(meeting)
        sents, links = ami.abstract(meeting), ami.links(meeting)
        # Per-agent document order is what NXT ranges refer to; ids within one file are in that order already.
        by_agent = collections.defaultdict(list)
        for d in das:
            by_agent[d["agent"]].append(d["id"])
        in_ext = set()
        for agent_ids in by_agent.values():
            in_ext |= ami.in_extractive(meeting, agent_ids)
        cands = []
        for d in das:
            secs = {sents[a][0] for a in links.get(d["id"], ()) if a in sents}
            label = _doc2_label(d, secs) if secs else None
            if not label or counts[label] >= DOC2_PER_CLASS:
                continue
            text = d["text"]
            if (d["nwords"] < 8 or d["type"] not in DOC2_TYPES[label] or not text.endswith((".", "!"))
                    or "[unclear]" in text):
                continue
            linked = [sents[a] for a in links[d["id"]] if a in sents]
            if label == "neither":
                if d["id"] not in in_ext or NEITHER_EXCLUDE.search(text) or BRIEF_WORDS.search(text):
                    continue
                evidence = [t for sec, t in linked if sec == "abstract"]
            elif label == "decision":
                if BRIEF_WORDS.search(text) or HEDGE.search(text):
                    continue
                evidence = [t for sec, t in linked if sec == "decisions" and _overlap(text, t) >= DOC2_MIN_OVERLAP]
                if not evidence:
                    continue
            else:
                evidence = [t for sec, t in linked if sec == "actions" and _overlap(text, t) >= DOC2_MIN_OVERLAP
                            and ACTION_AGENT.match(t)]
                if not evidence:
                    continue
            cands.append((rank(d["id"]), d, label, evidence))
        if not cands:
            continue
        _, d, label, evidence = min(cands)
        counts[label] += 1
        nonempty = [x for x in das if x["nwords"] > 0 or x["text"]]
        i = next(k for k, x in enumerate(nonempty) if x["id"] == d["id"])
        window = nonempty[max(0, i - DOC2_BEFORE): i + DOC2_AFTER + 1]
        turns = [{"speaker": ami.speaker(meeting, x["agent"]), "text": x["text"],
                  **({"highlighted": True} if x["id"] == d["id"] else {})} for x in window]
        if label == "neither":
            rationale = ("The corpus's summary annotators linked this utterance only to the general summary sentence "
                         f"\"{evidence[0]}\", not to any decision or action item of the meeting.")
        elif label == "decision":
            rationale = f"The summary annotators linked this utterance to the meeting's decision \"{evidence[0]}\"."
        else:
            rationale = f"The summary annotators linked this utterance to the meeting's action item \"{evidence[0]}\"."
        speaker = ami.speaker(meeting, d["agent"])
        row("DOC-2", d["id"],
            title=f"Meeting transcript · {meeting}, {speaker.split(' (')[0].lower()} speaking",
            state={"meeting": ami.describe(meeting),
                   "transcript": turns,
                   "highlighted_utterance": f"{speaker}: {d['text']}"},
            gold=label, rationale=rationale,
            note=f"AMI meeting {meeting}; dialogue act {d['id']} (type {d['type']}).",
            source=dict(dataset_id="ami", dataset="AMI Meeting Corpus", license="CC-BY-4.0",
                        url="https://groups.inf.ed.ac.uk/ami/corpus/", citation="Carletta et al. (2005), MLMI.",
                        record_id=d["id"], original_label=f"summlink → {label}",
                        labelled_by="AMI summary annotators (links from utterances to summary sentences)",
                        meeting=meeting),
            tags=["meeting", "transcript"])
    missing = {k: DOC2_PER_CLASS - counts[k] for k in DOC2_TYPES if counts[k] < DOC2_PER_CLASS}
    assert not missing, f"DOC-2 short of rows: {missing}"


# ---------------------------------------------------------------- DOC-3: which summary

DOC3_ROWS = 30
DOC3_WINDOW_CHARS = 3500
DOC3_START = 0.30
DOC3_MIN_TRUE = 4
DOC3_MARGIN = 2


def _series(meeting):
    return meeting[:6]


def _doc3(ami):
    abstracts = {}
    for m in ami.with_abstract:
        text = " ".join(t for sec, t in ami.abstract(m).values() if sec == "abstract")
        if text:
            abstracts[m] = text
    scenario = {m for m in abstracts if ami.meetings.get(m, {}).get("type") == "scenario"}
    used_series, titles = set(), set()
    n = 0
    for meeting in sorted(abstracts, key=rank):
        if n >= DOC3_ROWS:
            break
        if _series(meeting) in used_series or f"words/{meeting}.A.words.xml" not in ami.names:
            continue
        if meeting in scenario:
            distractors = sorted(m for m in scenario if _series(m) == _series(meeting) and m != meeting)
            if len(distractors) != 3:
                continue
        else:
            others = [m for m in abstracts if m not in scenario and _series(m) != _series(meeting)]
            others.sort(key=lambda m: rank(f"{meeting}:{m}"))
            distractors = others[:3]
        das = [d for d in ami.dialogue_acts(meeting) if d["text"]]
        if len(das) < 40:
            continue
        start = int(len(das) * DOC3_START)
        lines, size = [], 0
        for d in das[start:]:
            line = f"{ami.speaker(meeting, d['agent'])}: {d['text']}"
            if size + len(line) > DOC3_WINDOW_CHARS and lines:
                break
            lines.append(line)
            size += len(line) + 1
        window = "\n".join(lines)
        true_score = _overlap(window, abstracts[meeting])
        best_other = max(_overlap(window, abstracts[m]) for m in distractors)
        if true_score < DOC3_MIN_TRUE or true_score < best_other + DOC3_MARGIN:
            continue
        used_series.add(_series(meeting))
        n += 1
        letters = sorted("abcd", key=lambda k: rank(f"{meeting}:{k}"))
        gold = letters[0]
        assigned = {gold: meeting}
        for k, m in zip([k for k in sorted("abcd") if k != gold], distractors):
            assigned[k] = m
        minute = int(das[start]["start"] // 60)
        title = f"Meeting transcript · {len(lines)} utterances from minute {minute}"
        if title in titles:
            title += f" · {rank(meeting)[:6]}"
        titles.add(title)
        row("DOC-3", meeting,
            title=title,
            state={"meeting": ami.describe(meeting),
                   "transcript_excerpt": window,
                   "candidate_summaries": {k: abstracts[assigned[k]] for k in sorted("abcd")}},
            gold=gold,
            rationale=(f"Summary {gold} is the corpus's abstractive summary of this meeting ({meeting}); the other three "
                       f"summarise meetings {', '.join(distractors)}."),
            options={k: f"Summary {k}" for k in sorted("abcd")},
            note=f"Excerpt starts at utterance {start + 1} of {len(das)}.",
            source=dict(dataset_id="ami", dataset="AMI Meeting Corpus", license="CC-BY-4.0",
                        url="https://groups.inf.ed.ac.uk/ami/corpus/", citation="Carletta et al. (2005), MLMI.",
                        record_id=meeting, original_label=f"abstract of {meeting}",
                        labelled_by="the corpus: each abstractive summary is filed under its meeting (objective record)",
                        distractors=distractors),
            tags=["meeting", "summary"])
    assert n >= 20, f"DOC-3: only {n} rows"


# ---------------------------------------------------------------- define

def define():
    _datasets()
    task("DOC-1", category="documents", name="Where is this page from?",
         ask="What kind of document is this page from?",
         instruction="You are shown one page of a PDF document as an image, with a text rendering of its annotated "
                     "layout blocks. Decide which kind of document the page comes from, using its content, structure "
                     "and typography.",
         options={"financial_report": "An annual report or SEC filing of a company.",
                  "scientific_article": "A research paper, for example from arXiv.",
                  "law_or_regulation": "A statute, act, constitution or regulation.",
                  "government_tender": "A public procurement document: tender specifications, draft contract, annex.",
                  "manual": "A product or technical manual or handbook.",
                  "patent": "A patent application or granted patent."},
         shape="classify", input_type="document page", modality="text+image", expertise="none",
         contamination="medium", label_origin="human experts")
    task("DOC-2", category="documents", name="Decision, action item, or neither?",
         ask="Is the highlighted utterance a decision, an action item, or neither?",
         instruction="You are shown a short window of a meeting transcript with one utterance highlighted. Decide "
                     "whether that utterance states a decision the meeting reached, assigns an action item (a task "
                     "someone will do after the meeting), or does neither.",
         options={"decision": "The utterance states something the meeting decided or settled.",
                  "action_item": "The utterance assigns or commits to a task to be done after the meeting.",
                  "neither": "The utterance informs, asks or discusses without deciding or assigning anything."},
         shape="classify", input_type="meeting transcript", modality="text", expertise="none",
         contamination="medium", label_origin="trained annotators")
    task("DOC-3", category="documents", name="Which summary is this meeting's?",
         ask="Which of the four summaries describes this meeting?",
         instruction="You are shown an excerpt of a meeting transcript and four summaries written by annotators. "
                     "Exactly one summarises the meeting the excerpt comes from; the others summarise different "
                     "meetings. Pick the one that matches.",
         options={"a": "Summary a", "b": "Summary b", "c": "Summary c", "d": "Summary d"},
         shape="locate", input_type="meeting transcript", modality="text", expertise="none",
         contamination="high", label_origin="objective record", per_row_options=True)
    _doc1()
    ami = Ami()
    _doc2(ami)
    _doc3(ami)


if __name__ == "__main__":
    prepare_assets()
