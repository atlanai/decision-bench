"""legal: contracts, clauses and terms of service. Four tasks, all from expert-annotated public corpora.

LEG-1 "Does the NDA say this?" — ContractNLI (CC BY 4.0; Koreeda and Manning 2021), test split. One real NDA
   and one of the dataset's fixed hypotheses; answer yes / says the opposite / not addressed. A port of the v3 task
   CP-1 with the same EXCLUDE table, consent-gating rule, copyright-notice
   rule and contact-detail scrubbing, grown from 30 to 33 rows (11 per label).
LEG-2 "What kind of clause is this?" — CUAD (CC BY 4.0; Hendrycks et al. 2021), test split. One clause that CUAD's
   lawyer-supervised reviewers highlighted, shown with one sentence of context either side; pick which of six
   clause types it is. Five rows per type, one row per contract.
LEG-3 "Is this term unfair, and how?" — UNFAIR-ToS as packaged in LexGLUE (CC BY 4.0; Lippi et al. 2019, Chalkidis
   et al. 2022), test split. One sentence from a real terms-of-service document with its neighbouring sentences;
   pick which of the eight potentially-unfair clause types the annotators tagged, or "not unfair" for none.
LEG-4 "Does the contract cover this?" — CUAD test split. One CUAD clause type with CUAD's own definition, and a
   continuous 2,000–5,000 character excerpt of a contract; yes when the excerpt holds a reviewer-marked clause of
   that type, no when the reviewers found no such clause anywhere in the contract and the excerpt passes a written
   cue screen that keeps anything resembling one out.

Written sampling rules are in each task's section below; every candidate list is ordered by rank() and taken
greedily. Nothing in a row was written for the benchmark: hypotheses, clause definitions, contract text and
terms-of-service sentences are the datasets' own. E-mail addresses and phone/fax numbers are replaced with
placeholders wherever they occur (EMAIL, PHONE), as v3 did.
"""
import json
import re

from . import dataset, task, row, rank, SOURCES as SOURCE_DIR

LEXGLUE_WINDOWS = list(range(0, 1700, 100))   # the 1,607-row test split, in datasets-server windows of 100
SOURCES = [
    {"dataset": "ContractNLI v1.0, test split", "url": "https://stanfordnlp.github.io/contract-nli/resources/contract-nli.zip",
     "zip_member": "contract-nli/test.json", "path": "contractnli/test.json"},
    {"dataset": "CUAD v1, test split (SQuAD format)",
     "url": "https://raw.githubusercontent.com/TheAtticusProject/cuad/7aad649183846688381a147eeb3601aff590fe4a/data.zip",
     "zip_member": "test.json", "path": "cuad/test.json"},
] + [
    {"dataset": "LexGLUE unfair_tos, test split",
     "url": "https://datasets-server.huggingface.co/rows?dataset=coastalcph/lex_glue&config=unfair_tos&split=test"
            f"&offset={o}&length=100",
     "path": f"lexglue-unfair-tos/test-{o}.json"}
    for o in LEXGLUE_WINDOWS
]

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?<![\w$])(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)\s?|\d{3}[\s.-])\d{3}[\s.-]\d{4}"
                   r"(?:,?\s*ext\.?\s*\d+)?(?!\d)")
SEC_TERMS = ("The SEC says \"Information presented on sec.gov is considered public information and may be copied "
             "or further distributed by users of the web site without the SEC's permission\" "
             "(https://www.sec.gov/privacy).")


def _redact(text):
    return PHONE.sub("[phone removed]", EMAIL.sub("[e-mail removed]", text))


def _quote(text, cues, limit=220):
    """The words that decide it: a window of `limit` characters around the first match of the first cue in
    `cues` (a regex or a list of regexes tried in order) that matches, or the start of the text."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cues = [cues] if isinstance(cues, str) else list(cues or [])
    m = next((m for c in cues for m in [re.search(c, text, re.I)] if m), None)
    start = m.start() if m else 0
    lo = 0 if start < limit * 0.6 else text.rfind(" ", 0, max(0, start - 100)) + 1
    out = text[lo:lo + limit - 6].rsplit(" ", 1)[0]
    return ("..." if lo else "") + out + "..."


# ======================================================================================================================
# LEG-1 — ContractNLI. Everything in this section is carried over from v3 CP-1;
# PER_LABEL changed (10 -> 11), the newly sampled agreements got short names (AGREEMENTS) and one newly sampled pair
# was excluded after review (NDA_EXCLUDE, last entry).
# ======================================================================================================================

CONTRACTNLI = dict(dataset_id="contractnli", dataset="ContractNLI", license="CC BY 4.0", url="https://stanfordnlp.github.io/contract-nli/",
                   citation="Koreeda and Manning, ContractNLI: A Dataset for Document-level Natural Language "
                            "Inference for Contracts, Findings of EMNLP 2021.",
                   labelled_by="ContractNLI's annotators, who also marked the evidence spans")
NDA_MAX_CHARS = 10000
NDA_PER_LABEL = 11
NDA_PER_STATEMENT = 2
NDA_LABELS = {"Entailment": "yes", "Contradiction": "says_opposite", "NotMentioned": "not_addressed"}

# Records reviewed and left out because a skeptical reviewer could defend a second label from the text.
# Keyed by (document id, hypothesis id). Documented, not model-derived. (From v3 / authoring/real/contractnli.py.)
NDA_EXCLUDE = {
    (5, "nda-3"): "Labelled Contradiction, but the definition covers information 'in oral, written or electronic form'.",
    (401, "nda-19"): "Labelled Contradiction, but duties run five years from disclosure, past the two-year exchange term.",
    (213, "nda-10"): "Labelled Entailment, but the bracketed template text makes the terms, 'but not the existence', secret.",
    (42, "nda-2"): "Labelled Contradiction on a broad definition; a near-identical definition in doc 51 is NotMentioned.",
    (51, "nda-2"): "Labelled NotMentioned, but 'all information' disclosed is arguably not limited to technical information.",
    (127, "nda-13"): "Labelled Entailment, but the exception never mentions third parties.",
    (558, "nda-17"): "Labelled NotMentioned, but the agreement lets each party retain one copy.",
    (60, "nda-16"): "Labelled NotMentioned, but the agreement requires return on request, which a reviewer may read as covering termination.",
    (301, "nda-19"): "Labelled NotMentioned, but clause 4 imposes no-use and no-retention duties on termination.",
    (40, "nda-17"): "Labelled NotMentioned, but 'all copies thereof shall be returned' can be read as allowing copies.",
    (74, "nda-2"): "Labelled NotMentioned, but confidential information is defined as student and employee records, "
                   "which is not technical information.",
    (83, "nda-5"): "Labelled NotMentioned, but 'any disclosure' without consent is prohibited, which may cover employees.",
    (452, "nda-5"): "Labelled NotMentioned, but the contractor may not disclose 'to any other party', which may cover employees.",
    (85, "nda-1"): "Labelled NotMentioned, but clause 1 lists the disclosed material, which may count as identifying it.",
    (80, "nda-17"): "Labelled Contradiction, but the ban covers only copies that may become a public record.",
    # added in v4 when the task grew to 11 rows per label
    (57, "nda-5"): "Labelled NotMentioned, but clause 2.1(c) bars disclosure 'to anyone else' and the exceptions in 2.4 "
                   "never mention employees, so a reviewer could defend says_opposite (as for 83 and 452 above).",
}
COPYRIGHT_NOTICE = re.compile(r"©|\(c\)\s*(19|20)\d\d|\bcopyright\s+(\(c\)\s*)?(19|20)\d\d|all rights reserved",
                              re.I)
CONSENT_GATED = {"nda-7", "nda-17"}
CONSENT = re.compile(r"consent|approv|authori[sz]|permission", re.I)

# Plain-English question for each hypothesis (titles only; "yes" means the dataset's Entailment), the thing the
# agreement asserts when it contradicts the hypothesis, and the clause family whose absence makes it NotMentioned.
NDA_QUESTIONS = {
    "nda-1": "must all confidential information be expressly identified?",
    "nda-2": "does only technical information count as confidential?",
    "nda-3": "can orally shared information be confidential?",
    "nda-4": "may the information be used only for the agreement's purpose?",
    "nda-5": "may the recipient share with employees?",
    "nda-7": "may the recipient share with advisors or other third parties?",
    "nda-8": "must the recipient give notice before a compelled disclosure?",
    "nda-10": "must the agreement's existence be kept secret?",
    "nda-11": "is reverse engineering banned?",
    "nda-12": "may the recipient independently develop similar information?",
    "nda-13": "may the recipient get similar information from third parties?",
    "nda-15": "does the recipient get no rights to the information?",
    "nda-16": "must the information be returned or destroyed at the end?",
    "nda-17": "may the recipient make copies in some cases?",
    "nda-18": "is soliciting the discloser's people banned?",
    "nda-19": "do some obligations survive termination?",
    "nda-20": "may the recipient keep some information after returning it?",
}
NDA_CLAIMS = {
    "nda-1": "confidential information must be expressly marked or identified",
    "nda-2": "only technical information counts as confidential",
    "nda-3": "information shared orally can be confidential",
    "nda-4": "the information may be used only for the agreement's purpose",
    "nda-5": "the recipient may share with its employees",
    "nda-7": "the recipient may share with advisors or other third parties",
    "nda-8": "the recipient must give notice before a legally compelled disclosure",
    "nda-10": "the existence of the agreement itself is confidential",
    "nda-11": "the recipient may not reverse engineer",
    "nda-12": "the recipient may independently develop similar information",
    "nda-13": "the recipient may obtain similar information from a third party",
    "nda-15": "no rights or license to the information are granted",
    "nda-16": "information must be returned or destroyed at the end",
    "nda-17": "the recipient may make copies in some cases",
    "nda-18": "the recipient may not solicit the discloser's people",
    "nda-19": "some obligations survive termination",
    "nda-20": "the recipient may keep some information after return or destruction",
}
NDA_CONTRA_GLOSS = {"nda-1": "some confidential information is protected without being marked or identified",
                    "nda-2": "confidential information also covers non-technical information",
                    "nda-3": "confidential information must be in tangible form, so oral disclosures are not covered",
                    "nda-4": "the recipient may use residual knowledge beyond the stated purpose",
                    "nda-5": "the recipient may not share the information with its employees",
                    "nda-7": "only the recipient's own employees may receive the information",
                    "nda-16": "the recipient need not return or destroy the information",
                    "nda-17": "the recipient may not copy the information",
                    "nda-19": "the obligations end with the agreement",
                    "nda-20": "all the information must be returned or destroyed, leaving nothing retained"}
NDA_ABSENT = {
    "nda-1": "any requirement that information be marked, labelled or identified as confidential",
    "nda-2": "any wording on whether confidential information is limited to technical information",
    "nda-3": "any clause on whether orally or verbally disclosed information is covered",
    "nda-4": "any use restriction tying confidential information to a stated purpose",
    "nda-5": "any clause permitting disclosure to the recipient's employees",
    "nda-7": "any clause permitting disclosure to consultants, agents, advisors or other third parties",
    "nda-8": "any notice requirement for disclosures compelled by law, regulation or court order",
    "nda-10": "any clause keeping the existence or negotiation of the agreement confidential",
    "nda-11": "any prohibition on reverse engineering, decompiling or disassembling",
    "nda-12": "any exception or permission for independently developed information",
    "nda-13": "any exception for information received from a third party",
    "nda-15": "any no-license or no-grant-of-rights clause",
    "nda-16": "any return-or-destroy obligation on termination",
    "nda-17": "any clause on making copies or reproductions of confidential information",
    "nda-18": "any non-solicitation clause covering employees or representatives",
    "nda-19": "any survival clause or confidentiality period that outlasts the agreement",
    "nda-20": "any clause allowing retention of copies after return or destruction (e.g. archival or legal copies)",
}
# Words that locate the operative evidence span for each hypothesis (used only to pick the quoted span).
NDA_CUES = {"nda-1": r"mark|identif|designat", "nda-2": r"technical|business|financial|commercial|pricing|customer",
            "nda-3": r"oral|verbal", "nda-4": r"purpose|residual|use", "nda-5": r"employee",
            "nda-7": r"consultant|advis|agent|counsel|third|contractor|individuals|representative",
            "nda-8": r"notif|notice", "nda-10": r"existence|terms|fact", "nda-11": r"reverse|decompil|disassembl",
            "nda-12": r"independent", "nda-13": r"third|other than|source|free of", "nda-15": r"licen|right",
            "nda-16": r"return|destr", "nda-17": r"cop(y|ies)|reproduc", "nda-18": r"solicit|hire",
            "nda-19": r"surviv|years|terminat", "nda-20": r"retain|return|destr|cop(y|ies)"}
NDA_CONTRA_CUES = {"nda-1": r"orally|reasonabl", "nda-3": r"tangible|writing"}

# Short, neutral name for each sampled agreement (titles only; the build fails if a sampled document lacks one).
AGREEMENTS = {
    22: "Norwegian MoD–Gripen NDA", 24: "Ready4S mutual NDA", 42: "BCG mutual NDA", 43: "BEE Online NDA",
    48: "Basic one-way NDA template", 60: "Mohican North Star casino NDA", 66: "DEFTA Group NDA",
    67: "Blank one-way NDA template (2009)", 84: "Haldex NDA", 90: "Michigan Trauma Registry data use agreement",
    138: "Last Man Stands NDA", 157: "Anderson Cargo Services mutual NDA", 181: "Acumen Business Systems mutual NDA",
    213: "Urban Wind Turbines NDA", 218: "Design 1st mutual NDA", 225: "ResRequest partner NDA",
    289: "Accruence mutual NDA", 293: "P.L. Berry inventor secrecy agreement", 307: "PromonLogicalis NDA",
    310: "National Archives NDA", 321: "Pitch Deck Fire workshop NDA", 354: "McMaster University mutual NDA",
    357: "UALR standard NDA", 413: "Intel corporate NDA", 451: "Novell–SilverStream mutual NDA",
    471: "Nanolution–NaturalNano joint research NDA", 493: "Symmetrex–Morgan Beaumont mutual NDA",
    497: "Cyberlux mutual NDA", 540: "Oracle strategic-matters NDA", 543: "Packeteer–Blue Coat NDA",
    # added for v4 (LEG-1 grew from 10 to 11 rows per label)
    51: "Biocidal Products Regulation data-sharing confidentiality template", 57: "PwC Annex III NDA",
    77: "Helukabel supplier confidentiality agreement", 190: "itagg mutual NDA",
    455: "Consumers On-Line Development Group non-circumvention NDA",
}
# What a sampled NotMentioned agreement does say nearby, so the rationale points at its own text (optional).
NDA_NM_NOTES = {
    (213, "nda-8"): "Clause 3 exempts disclosures required by law or court order but asks for no notice.",
    (80, "nda-8"): "It ties confidentiality to state and federal law but has no clause on compelled disclosure.",
    (218, "nda-10"): "It protects the information disclosed but not the agreement or the parties' discussions.",
    (471, "nda-18"): "It limits disclosure to officers and employees but places no limit on soliciting or hiring them.",
    (354, "nda-18"): "It governs disclosure to employees, agents and consultants but not soliciting them.",
    (446, "nda-15"): "The one-page agreement bars disclosure and use of Navidec's trade secrets and is silent on rights.",
    (225, "nda-16"): "It restricts publishing and distributing the material but never requires giving it back.",
    (455, "nda-16"): "The short agreement covers confidentiality and arbitration only.",
    (293, "nda-12"): "Its exceptions cover prior possession, public information and third-party sources, not own development.",
    (497, "nda-11"): "It bars disclosure, copying and use outside the joint project; reverse engineering is not mentioned.",
    (389, "nda-11"): "It restricts use to GSEnergy's review and analysis; reverse engineering is not mentioned.",
    (60, "nda-3"): "It defines confidential information by subject matter without saying whether oral disclosures count.",
    (67, "nda-10"): "It protects the information the Disclosing Party shares and says nothing about keeping the agreement "
                    "itself secret.",
    (90, "nda-19"): "It can be ended on 60 days' written notice and says nothing about which duties continue afterwards.",
    (293, "nda-16"): "The one-page secrecy agreement covers confidentiality, non-use and three exceptions only.",
}


def _nda_excluded(doc, hyp, ann):
    if (doc["id"], hyp) in NDA_EXCLUDE or COPYRIGHT_NOTICE.search(doc["text"]):
        return True
    if ann["choice"] != "NotMentioned" and not ann["spans"]:
        return True
    evidence = " ".join(doc["text"][doc["spans"][i][0]:doc["spans"][i][1]] for i in ann["spans"])
    return ann["choice"] == "Contradiction" and hyp in CONSENT_GATED and bool(CONSENT.search(evidence))


def _nda_quote(doc, hyp, span_ids, contra=False, limit=200):
    texts = [" ".join(doc["text"][doc["spans"][i][0]:doc["spans"][i][1]].split()) for i in sorted(span_ids)]
    body = [t for t in texts if len(t) >= 25 and not t.endswith(":")] or texts
    cue = NDA_CONTRA_CUES.get(hyp, NDA_CUES[hyp]) if contra else NDA_CUES[hyp]
    hit = next(((t, m) for t in body for m in [re.search(cue, t, re.I)] if m), None)
    pick, start = (hit[0], hit[1].start()) if hit else (body[0], 0)
    if len(pick) <= limit:
        return pick
    lo = 0 if start < limit * 0.6 else pick.rfind(" ", 0, max(0, start - 100)) + 1
    out = pick[lo:lo + limit - 6].rsplit(" ", 1)[0]
    return ("..." if lo else "") + out + "..."


def _nda_rationale(doc, hyp, ann, gold):
    if gold == "not_addressed":
        note = NDA_NM_NOTES.get((doc["id"], hyp))
        return f"The agreement has no clause settling this: it lacks {NDA_ABSENT[hyp]}." + (f" {note}" if note else "")
    claim = NDA_CLAIMS[hyp] if gold == "yes" else NDA_CONTRA_GLOSS[hyp]
    return f"The agreement says {claim}: \"{_nda_quote(doc, hyp, ann['spans'], gold == 'says_opposite')}\""


def _nda_sample(data):
    docs = [d for d in data["documents"] if len(d["text"]) <= NDA_MAX_CHARS]
    used_docs, per_statement, chosen = set(), {}, []
    for label in ("Contradiction", "Entailment", "NotMentioned"):
        pool = [(d, h, a) for d in docs for h, a in d["annotation_sets"][0]["annotations"].items()
                if a["choice"] == label and h in NDA_QUESTIONS]
        pool.sort(key=lambda t: rank(f"{t[0]['id']}:{t[1]}"))
        taken = 0
        for d, h, a in pool:
            if taken == NDA_PER_LABEL:
                break
            if d["id"] in used_docs or per_statement.get(h, 0) >= NDA_PER_STATEMENT or _nda_excluded(d, h, a):
                continue
            used_docs.add(d["id"])
            per_statement[h] = per_statement.get(h, 0) + 1
            chosen.append((d, h, a))
            taken += 1
        assert taken == NDA_PER_LABEL, f"LEG-1: only {taken} {label} rows"
    return sorted(chosen, key=lambda t: rank(f"{t[0]['id']}:{t[1]}"))


def _leg1():
    task("LEG-1", category="legal", name="Does the NDA say this?", ask="Does the agreement say this, the opposite, or neither?",
         instruction=(
             "You review NDAs for a legal operations team. Read the statement and the full agreement. Decide "
             "whether the agreement states it, states the opposite, or doesn't address it. Judge only from the "
             "agreement's own wording. In the statement, 'Receiving Party' is the party that receives confidential "
             "information, 'Disclosing Party' the party that shares it, and 'Agreement' this agreement; in a mutual "
             "NDA each party is both. 'Not addressed' means no clause settles the point either way."),
         options={"yes": "Yes: the agreement's wording makes the statement true.",
                  "says_opposite": "Says the opposite: the agreement's wording makes the statement false.",
                  "not_addressed": "Not addressed: no clause settles the point, so the statement is neither true "
                                   "nor false under the agreement."},
         shape="verify", input_type="non-disclosure agreement", modality="text", expertise="none",
         contamination="high", label_origin="trained annotators", abstain="not_addressed")
    data = json.loads((SOURCE_DIR / "contractnli/test.json").read_text())
    hypotheses = data["labels"]
    for d, h, a in _nda_sample(data):
        if d["id"] not in AGREEMENTS:
            raise KeyError(f"LEG-1: add a short name for document {d['id']} ({d['file_name']}): {d['text'][:200]!r}")
        gold = NDA_LABELS[a["choice"]]
        row("LEG-1", f"contractnli-{d['id']}-{h}", title=f"{AGREEMENTS[d['id']]} · {NDA_QUESTIONS[h]}",
            state={"statement": hypotheses[h]["hypothesis"], "agreement": _redact(d["text"])},
            gold=gold, rationale=_nda_rationale(d, h, a, gold), tags=(h,),
            source={**CONTRACTNLI, "record_id": f"test document {d['id']} ({d['file_name']}), hypothesis {h}",
                    "original_label": a["choice"], "document_url": d["url"]})


# ======================================================================================================================
# CUAD (shared by LEG-2 and LEG-4)
# ======================================================================================================================

CUAD = dict(dataset_id="cuad", dataset="CUAD (Contract Understanding Atticus Dataset) v1", license="CC BY 4.0",
            url="https://www.atticusprojectai.org/cuad",
            citation="Hendrycks, Burns, Chen and Ball, CUAD: An Expert-Annotated NLP Dataset for Legal Contract "
                     "Review, NeurIPS 2021 Datasets and Benchmarks.",
            labelled_by="The Atticus Project's reviewers (law students and lawyers, working under experienced "
                        "attorneys), who highlighted each clause")
# CUAD category -> option key. Six types a careful reader can tell apart from the clause text.
CLAUSE_TYPES = {"Governing Law": "governing_law", "Cap On Liability": "cap_on_liability",
                "Anti-Assignment": "anti_assignment", "License Grant": "license_grant", "Non-Compete": "non_compete",
                "Termination For Convenience": "termination_for_convenience"}
CLAUSE_OPTIONS = {
    "governing_law": "Governing law: which state's or country's law governs the contract.",
    "cap_on_liability": "Cap on liability: a ceiling on what a party can be liable for, or a time limit on bringing claims.",
    "anti_assignment": "Anti-assignment: a party needs the other's consent, or must give notice, to assign the contract.",
    "license_grant": "License grant: one party grants the other a licence to intellectual property, products or data.",
    "non_compete": "Non-compete: a party is restricted from competing with the other or from operating in a sector or territory.",
    "termination_for_convenience": "Termination for convenience: a party may end the contract without cause, on notice.",
}
# Words that locate the operative wording inside a span (used only to pick the quoted words in rationales).
CLAUSE_CUES = {
    "governing_law": [r"governed by|laws? of the|laws? of [A-Z]", r"govern|construed"],
    "cap_on_liability": [r"(not|no event|never) exceed|exceed", r"in no event|no event", r"limited to|not be liable|shall not be liable",
                         r"exclusive remedy", r"liab", r"damages"],
    "anti_assignment": [r"(not|neither|no party may|may not)[^.;]{0,60}assign|assign[^.;]{0,80}(consent|approv)", r"assign"],
    "license_grant": [r"grants? (to )?[^.;]{0,80}licen|hereby grants?|licen[sc]e to|right to use|shall have the right", r"licen|grant"],
    "non_compete": [r"not[^.;]{0,120}compet|competitive business|compet[^.;]{0,40}(with|business)", r"compet"],
    "termination_for_convenience": [r"without cause|for convenience|any reason|no reason|at any time|upon[^.;]{0,40}notice", r"terminat"],
}
# LEG-4 negative screen: a "no" excerpt may not contain anything that resembles the clause type (conservative).
ABSENCE_SCREEN = {
    "governing_law": r"govern(ed|ing)\s+(by|law)|laws?\s+of\s+the\s+(state|commonwealth|province|republic)|"
                     r"laws?\s+of\s+[A-Z][a-z]+|construed\s+(in\s+accordance|under|according)|conflicts?\s+of\s+laws?",
    "cap_on_liability": r"liab|damages",
    "anti_assignment": r"assign|(transfer|pledg|encumb)[^.;]{0,100}(consent|approv|prohibit|shall not|may not)|"
                       r"(shall not|may not|not be)[^.;]{0,60}(transfer|pledg|encumb)|successors and assigns",
    "license_grant": r"licen[sc]|rights? to use|entitled to use|permi(t|ssion) to use|use of (the |any |such )?(mark|name|logo|"
                     r"trademark|software|patent|technolog|intellectual|know-how|data)|sublicen|grants? (to|.{0,40}right)",
    "non_compete": r"compet",
    "termination_for_convenience": r"terminat[^.;]{0,220}(convenience|any\s+reason|no\s+reason|without\s+cause|"
                                   r"at\s+any\s+time|notice)|(convenience|without\s+cause|any\s+reason)[^.;]{0,120}terminat",
}
SENTENCE_END = re.compile(r"(?<=[.!?;])[\"'”’)\]]?\s+(?=[A-Z(\[\"“0-9])|\n\s*\n|\n(?=\s*(\d+\.|\([a-z0-9]+\)|[A-Z]{2,}))")
FORM_DATE = re.compile(r"_(\d{4})(\d\d)(\d\d)_|_(\d\d)_(\d\d)_(\d{4})-")
# OCR damage shows up as function words glued to the next word ("ofthis", "ofDefault"). Contracts with more than
# OCR_GLUED_MAX such tokens per 1,000 words are not used by either CUAD task (test split: only contract 35, at 12.9;
# the next is 0.24).
OCR_GLUED = re.compile(r"\b(?:of|to|in|and|for|the|this|that|shall|such)(?:the|this|that|such|and|any|all|its|their|which|[A-Z][a-z]{3,})\b")
OCR_GLUED_MAX = 2.0


def _cuad_docs():
    data = json.loads((SOURCE_DIR / "cuad/test.json").read_text())
    docs = []
    for i, d in enumerate(data["data"]):
        p = d["paragraphs"][0]
        words = len(re.findall(r"[A-Za-z]{2,}", p["context"]))
        if len(OCR_GLUED.findall(p["context"])) / max(1, words) * 1000 > OCR_GLUED_MAX:
            continue
        spans, impossible = {}, set()
        for q in p["qas"]:
            cat = q["id"].split("__")[-1]
            spans[cat] = sorted({(a["answer_start"], a["answer_start"] + len(a["text"])) for a in q["answers"]})
            if q["is_impossible"]:
                impossible.add(cat)
            if "Details:" in q["question"]:
                CUAD_DEFINITIONS.setdefault(cat, " ".join(q["question"].split("Details:", 1)[1].split()))
        docs.append({"index": i, "title": d["title"], "text": p["context"], "spans": spans, "impossible": impossible})
    return docs


CUAD_DEFINITIONS = {}   # CUAD category -> the dataset's own "Details:" definition, read from the records


def _cuad_title(doc):
    """Neutral title: the agreement type from CUAD's file name (falling back to its Document Name annotation) and
    the exhibit's filing date from the file name (falling back to the filer's name). Anything after " - " or
    "between" in the file name (counterparties, sometimes individuals) is dropped."""
    m = re.search(r".*EX-\d[\w.()]*?[-_](.+)$", doc["title"]) or re.search(r"\s-\s(.+)$", doc["title"])
    name = m.group(1) if m else ""
    name = re.split(r"\s+-\s+|\s+between\s+|\s+by\s+and\s+|\bdated\b", name, flags=re.I)[0].strip(" _-")
    name = re.sub(r"\bA_R\b", "Amended and Restated", name)
    name = re.sub(r"(?<=[A-Za-z])\d+$", "", name).strip()          # "Franchise Agreement1"
    words = [w for w in re.findall(r"[A-Za-z]{5,}", name)]
    if len(name) < 4 or any(w.lower() not in doc["text"].lower() for w in words):
        names = [" ".join(doc["text"][s:e].split()) for s, e in doc["spans"].get("Document Name", [])]
        names = [n.strip(" (") for n in names if 4 <= len(n) <= 80 and n.count("(") == n.count(")")] or ["Agreement"]
        name = min(names, key=len)
    if any(w.isupper() and len(w) > 3 for w in name.split()):      # all-caps file names
        name = name.title()
    name = re.sub(r"\s+", " ", name)
    if len(name) > 60:
        name = name[:60].rsplit(" ", 1)[0] + "…"
    m = FORM_DATE.search(doc["title"])
    when = (f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m and m.group(1) else
            f"{m.group(6)}-{m.group(4)}-{m.group(5)}" if m else None)
    if when:
        return f"{name} · SEC exhibit filed {when}"
    filer = re.split(r"_| - ", doc["title"])[0].strip().title()
    return f"{name} · SEC exhibit ({filer})"


def _sentence_before(text, pos, limit):
    """One sentence of context ending at `pos`, at most `limit` characters, cut with a marker if longer."""
    head = text[max(0, pos - limit * 3):pos]
    ends = [m.end() for m in SENTENCE_END.finditer(head)]
    ends = [e for e in ends if e < len(head.rstrip())]
    start = ends[-2] if len(ends) >= 2 else (0 if pos <= limit * 3 else None)
    ctx = head[start:] if start is not None else head
    ctx = " ".join(ctx.split())
    if len(ctx) > limit:
        ctx = "…" + ctx[-limit:].split(" ", 1)[-1]
    return ctx


def _sentence_after(text, pos, limit):
    tail = text[pos:pos + limit * 3]
    ends = [m.end() for m in SENTENCE_END.finditer(tail)]
    ends = [e for e in ends if e > len(tail) - len(tail.lstrip())]
    end = ends[1] if len(ends) >= 2 else (len(tail) if pos + limit * 3 >= len(text) else None)
    ctx = tail[:end] if end is not None else tail
    ctx = " ".join(ctx.split())
    if len(ctx) > limit:
        ctx = ctx[:limit].rsplit(" ", 1)[0] + "…"
    return ctx


# ----------------------------------------------------------------------------------------------------------------------
# LEG-2 — which clause type. Rules: a candidate is one reviewer-highlighted span of one of the six CLAUSE_TYPES, of
# SPAN_MIN–SPAN_MAX characters, whose excerpt (span plus one sentence either side) does not touch any span of another
# of the six types in the same contract, and whose exact span is not also highlighted under another of the six.
# Spans that end in a colon (a lead-in whose operative list follows) or contain redaction markers (REDACTED) are
# skipped. Types are filled scarcest first; candidates are ordered by rank(f"{contract}:{type}:{start}"); one row per
# contract; CLAUSES_PER_TYPE rows per type. Hand-drops go in CLAUSE_SKIP, keyed (contract index, type, span start
# or 0 for any), with the reason.
# ----------------------------------------------------------------------------------------------------------------------

CLAUSES_PER_TYPE = 5
SPAN_MIN, SPAN_MAX = 120, 1600
CONTEXT_CHARS = 350
REDACTED = re.compile(r"\[\*+\]|\{\*+\}|\*{3,}|\[REDACTED\]|\[\.\.\.\]", re.I)
CLAUSE_SKIP = {
    (20, "license_grant", 0): "The span is the tail of a sentence cut by a page break ('Airspan Products to Distributor's "
                              "customers ... does not transfer any right'); the grant itself is on the previous page.",
    (45, "termination_for_convenience", 0): "Both highlighted spans are mechanics ('may terminate ... as follows:', 'If "
                                            "Capital Resources elects to terminate ... shall be notified'); the words "
                                            "that make it a termination without cause are not in either span.",
    (40, "non_compete", 0): "The span is a promise not to transfer proprietary battery technology to third parties; a "
                            "reader could defend anti_assignment as well as non_compete.",
}


def _overlaps(a, b):
    return a[0] < b[1] and b[0] < a[1]


def _clause_candidates(docs):
    for doc in docs:
        for cat, key in CLAUSE_TYPES.items():
            others = [s for c, k in CLAUSE_TYPES.items() if c != cat for s in doc["spans"].get(c, [])]
            for start, end in doc["spans"].get(cat, []):
                if not SPAN_MIN <= end - start <= SPAN_MAX or (start, end) in others:
                    continue
                span = doc["text"][start:end].strip()
                if span.endswith(":") or REDACTED.search(span):     # incomplete lead-ins; redacted exhibits
                    continue
                if any(k[:2] == (doc["index"], key) and k[2] in (0, start) for k in CLAUSE_SKIP):
                    continue
                window = (max(0, start - CONTEXT_CHARS * 3), min(len(doc["text"]), end + CONTEXT_CHARS * 3))
                if any(_overlaps(window, o) for o in others):
                    continue
                yield doc, cat, key, start, end


def _leg2(docs):
    assert len(docs) == 101, f"LEG-2: expected 101 usable test contracts, got {len(docs)}"
    task("LEG-2", category="legal", name="What kind of clause is this?", ask="Which of these clause types is this?",
         instruction=(
             "You are sorting clauses pulled from real commercial contracts (SEC exhibits) for a contract-review "
             "team. You see one clause that expert reviewers highlighted, with up to one sentence of surrounding "
             "text before and after it for context. Decide which of the six clause types the highlighted clause "
             "is. Judge from the clause's own wording; the context is there only to help you read it."),
         options=CLAUSE_OPTIONS, shape="classify", input_type="contract clause", modality="text", expertise="none",
         contamination="high", label_origin="human experts")
    pool = list(_clause_candidates(docs))
    order = {cat: i for i, cat in enumerate(sorted(CLAUSE_TYPES, key=lambda c: sum(1 for p in pool if p[1] == c)))}
    used, taken, chosen = set(), {}, []
    for cat in sorted(CLAUSE_TYPES, key=order.get):
        for doc, c, key, start, end in sorted((p for p in pool if p[1] == cat),
                                              key=lambda p: rank(f"{p[0]['title']}:{p[1]}:{p[3]}")):
            if taken.get(key, 0) >= CLAUSES_PER_TYPE:
                break
            if doc["index"] in used:
                continue
            used.add(doc["index"])
            taken[key] = taken.get(key, 0) + 1
            chosen.append((doc, c, key, start, end))
        assert taken.get(key, 0) == CLAUSES_PER_TYPE, f"LEG-2: only {taken.get(key, 0)} {cat} rows"
    for doc, cat, key, start, end in sorted(chosen, key=lambda p: rank(f"{p[0]['title']}:{p[1]}:{p[3]}")):
        clause = " ".join(doc["text"][start:end].split())
        state = {"clause": _redact(clause),
                 "context_before": _redact(_sentence_before(doc["text"], start, CONTEXT_CHARS)),
                 "context_after": _redact(_sentence_after(doc["text"], end, CONTEXT_CHARS))}
        state = {k: v for k, v in state.items() if v}
        row("LEG-2", f"cuad-{doc['index']}-{key}", title=_cuad_title(doc), state=state, gold=key,
            rationale=f"CUAD's reviewers highlighted this as \"{cat}\" ({CUAD_DEFINITIONS[cat]}); the deciding "
                      f"words: \"{_quote(clause, CLAUSE_CUES[key])}\"",
            tags=(key,),
            source={**CUAD, "record_id": f"test contract {doc['index']} ({doc['title']}), category {cat}, "
                                         f"span at character {start}",
                    "original_label": cat, "labelled_by": CUAD["labelled_by"]})
    return used


# ----------------------------------------------------------------------------------------------------------------------
# LEG-4 — does the contract cover this. Rules: contracts not used by LEG-2, one row per contract. For each of the six
# types, COVERAGE_PLAN gives (yes, no) counts. A "yes" excerpt is a 2,000–5,000 character window snapped to line or
# sentence boundaries that contains one whole reviewer-highlighted span of the type (span at most SPAN_MAX_COVER
# characters); the span's position inside the window is set by rank. A "no" excerpt comes from a contract whose
# reviewers marked the type as absent (is_impossible), starting at a line boundary chosen by rank, and must pass
# ABSENCE_SCREEN (no wording resembling the type) and be running prose (_prose: LETTER_RATIO of letters, at least
# MIN_SENTENCES full sentences, no signature page or notice-address block). Positive spans follow the LEG-2 span
# rules (no lead-in ending in a colon, no redaction markers). Candidates are ordered by rank(f"{contract}:{type}")
# for negatives and rank(f"{contract}:{type}:{start}") for positives.
# ----------------------------------------------------------------------------------------------------------------------

# (yes, no) rows per type; governing law has few usable negatives (19 test contracts lack one, several of them
# signature-page joint filing agreements), so it carries 2 and cap on liability carries 3.
COVERAGE_PLAN = {"governing_law": (3, 2), "cap_on_liability": (2, 3), "anti_assignment": (2, 3),
                 "license_grant": (3, 2), "non_compete": (2, 3), "termination_for_convenience": (3, 2)}
EXCERPT_MIN, EXCERPT_MAX = 2000, 5000
SPAN_MAX_COVER = 3000
LETTER_RATIO = 0.62
MIN_SENTENCES = 5          # a "no" excerpt must carry at least this many sentences of 80+ characters (prose, not tables)
SIGNATURES = re.compile(r"/s/|\bBy:\s|\bName:\s|\bTitle:\s|IN WITNESS WHEREOF|_{6,}")
NOTICE_BLOCK = re.compile(r"\bAttn\b|\bAttention:|with a copy to|\bFax\b|Facsimile|Telephone|\bTel\.|\bEsq\b|\b[A-Z]{2},?\s+\d{5}\b")
COVERAGE_SKIP = {
    (45, "termination_for_convenience"): "CUAD's spans are an automatic termination when the Shares are not sold and "
                                         "notice mechanics; the excerpt would not show a clear without-cause right.",
}


def _snap_start(text, pos):
    """Move `pos` back to the start of a line or sentence (within 400 characters), else keep it."""
    lo = max(0, pos - 400)
    nl = text.rfind("\n", lo, pos)
    if nl >= 0:
        return nl + 1
    ends = [m.end() for m in SENTENCE_END.finditer(text[lo:pos])]
    return lo + ends[-1] if ends else pos


def _snap_end(text, pos):
    hi = min(len(text), pos + 400)
    nl = text.find("\n", pos, hi)
    if nl >= 0:
        return nl
    ends = [m.end() for m in SENTENCE_END.finditer(text[pos:hi])]
    return pos + ends[0] if ends else pos


def _window_size(key_):
    return 2400 + int(rank(key_)[:8], 16) % 2000          # 2,400–4,399 characters before snapping


def _prose(text):
    """Running contract text: mostly letters, several full sentences, no signature page or notice-address block."""
    letters = sum(ch.isalpha() for ch in text)
    if letters / max(1, len(text)) < LETTER_RATIO:
        return False
    sentences = [x for x in SENTENCE_END.split(text) if x and len(x.strip()) >= 80]
    return len(sentences) >= MIN_SENTENCES and len(SIGNATURES.findall(text)) <= 1 and not NOTICE_BLOCK.search(text)


def _excerpt(doc, start, end):
    body = doc["text"][start:end].strip("\n")
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(doc["text"]) else ""
    return {"contract_excerpt": _redact(prefix + body + suffix),
            "excerpt_position": f"characters {start:,}–{end:,} of a {len(doc['text']):,}-character contract"}


def _positive_window(doc, span, key):
    s, e = span
    size = _window_size(f"{doc['title']}:{key}:{s}")
    if e - s > SPAN_MAX_COVER or e - s > size - 400:
        size = min(EXCERPT_MAX - 400, e - s + 1200)
    room = size - (e - s)
    before = int(room * (0.15 + (int(rank(f"{doc['title']}:{key}:{s}:pos")[:4], 16) % 1000) / 1000 * 0.7))
    start = _snap_start(doc["text"], max(0, s - before))
    end = _snap_end(doc["text"], min(len(doc["text"]), start + size))
    if end < e:
        end = _snap_end(doc["text"], e)
    if EXCERPT_MIN <= end - start <= EXCERPT_MAX and start <= s and e <= end:
        return start, end
    return None


def _negative_window(doc, key):
    text = doc["text"]
    size = _window_size(f"{doc['title']}:{key}")
    if len(text) < size + 200:
        return None
    starts = [m.end() for m in re.finditer(r"\n", text) if m.end() + size <= len(text)]
    for pos in sorted(starts, key=lambda p: rank(f"{doc['title']}:{key}:{p}"))[:40]:
        end = _snap_end(text, pos + size)
        chunk = text[pos:end]
        if not EXCERPT_MIN <= len(chunk) <= EXCERPT_MAX or not _prose(chunk):
            continue
        if re.search(ABSENCE_SCREEN[key], chunk, re.I):
            continue
        return pos, end
    return None


def _leg4(docs, used):
    task("LEG-4", category="legal", name="Does the contract cover this?", ask="Does this excerpt contain that clause type?",
         instruction=(
             "You are doing contract diligence. You see one clause type with the definition the reviewers worked "
             "from, and one continuous excerpt (2,000–5,000 characters) of a real commercial contract filed with "
             "the SEC. Answer yes if the excerpt contains a clause of that type. Answer no if it does not: for those "
             "rows the expert reviewers found no such clause anywhere in the whole contract, so nothing in the "
             "excerpt should read as one. Judge only from the excerpt's wording; the surrounding contract is not "
             "shown."),
         options={"yes": "Yes: the excerpt contains a clause of this type.",
                  "no": "No: the excerpt contains no clause of this type (and the reviewers found none in the contract)."},
         shape="detect", input_type="contract excerpt", modality="text", expertise="practitioner",
         contamination="medium", label_origin="human experts")
    chosen = []
    for cat, key in sorted(CLAUSE_TYPES.items(), key=lambda kv: sum(1 for d in docs if d["spans"].get(kv[0]))):
        want_yes, want_no = COVERAGE_PLAN[key]
        positives = [(d, s) for d in docs if d["index"] not in used for s in d["spans"].get(cat, [])
                     if s[1] - s[0] <= SPAN_MAX_COVER and (d["index"], key) not in COVERAGE_SKIP
                     and not d["text"][s[0]:s[1]].strip().endswith(":") and not REDACTED.search(d["text"][s[0]:s[1]])]
        got = 0
        for d, s in sorted(positives, key=lambda p: rank(f"{p[0]['title']}:{key}:{p[1][0]}")):
            if got == want_yes:
                break
            if d["index"] in used:
                continue
            window = _positive_window(d, s, key)
            if window is None:
                continue
            used.add(d["index"])
            got += 1
            chosen.append((d, cat, key, "yes", window, s))
        assert got == want_yes, f"LEG-4: only {got} yes rows for {cat}"
        negatives = [d for d in docs if d["index"] not in used and cat in d["impossible"] and not d["spans"].get(cat)
                     and (d["index"], key) not in COVERAGE_SKIP]
        got = 0
        for d in sorted(negatives, key=lambda d: rank(f"{d['title']}:{key}")):
            if got == want_no:
                break
            if d["index"] in used:
                continue
            window = _negative_window(d, key)
            if window is None:
                continue
            used.add(d["index"])
            got += 1
            chosen.append((d, cat, key, "no", window, None))
        assert got == want_no, f"LEG-4: only {got} no rows for {cat}"
    for d, cat, key, gold, (start, end), span in sorted(chosen, key=lambda c: rank(f"{c[0]['title']}:{c[2]}")):
        state = {"clause_type": cat, "clause_type_definition": CUAD_DEFINITIONS[cat], **_excerpt(d, start, end)}
        if gold == "yes":
            clause = " ".join(d["text"][span[0]:span[1]].split())
            rationale = (f"The excerpt contains the clause CUAD's reviewers highlighted as \"{cat}\": "
                         f"\"{_quote(clause, CLAUSE_CUES[key])}\"")
            record = f"span at character {span[0]}"
        else:
            rationale = (f"CUAD's reviewers marked \"{cat}\" as absent from this whole contract, and the excerpt has "
                         f"no wording of that kind (screen: /{ABSENCE_SCREEN[key]}/ does not match).")
            record = "no span (is_impossible)"
        row("LEG-4", f"cuad-{d['index']}-{key}", title=f"{_cuad_title(d)} · {cat.lower()}?",
            state=state, gold=gold, rationale=rationale, tags=(key, gold),
            source={**CUAD, "record_id": f"test contract {d['index']} ({d['title']}), category {cat}, {record}, "
                                         f"excerpt characters {start}–{end}",
                    "original_label": "has answer span" if gold == "yes" else "is_impossible (no span)"})


# ======================================================================================================================
# LEG-3 — UNFAIR-ToS (LexGLUE). Rules: the 1,607 test sentences fall into ten terms-of-service documents in order
# (TOS_DOCUMENTS gives the first row of each; verified sentence by sentence against the Sentences/ files of the
# original CLAUDETTE ToS corpus). A candidate is a sentence of TOS_MIN_CHARS–TOS_MAX_CHARS characters with exactly
# one tag (multi-tag sentences skipped), or with no tag and none of the FAIR_SCREEN cue words (so an untagged sentence
# is far from every category). Neighbouring sentences come from the same document only. Rows per label from
# TOS_PLAN, at most TOS_PER_DOCUMENT per document, candidates ordered by rank(f"unfair_tos:test:{row}").
# ======================================================================================================================

LEXGLUE = dict(dataset_id="lexglue-unfair-tos", dataset="UNFAIR-ToS (LexGLUE)", license="CC BY 4.0",
               url="https://huggingface.co/datasets/coastalcph/lex_glue",
               citation="Lippi et al., CLAUDETTE: an automated detector of potentially unfair clauses in online "
                        "terms of service, Artificial Intelligence and Law 2019; packaged in Chalkidis et al., LexGLUE, "
                        "ACL 2022.",
               labelled_by="the CLAUDETTE project's legal annotators (Lippi et al. 2019), who tagged each sentence")
TOS_LABELS = ["Limitation of liability", "Unilateral termination", "Unilateral change", "Content removal",
              "Contract by using", "Choice of law", "Jurisdiction", "Arbitration"]
TOS_KEYS = {"Limitation of liability": "limitation_of_liability", "Unilateral termination": "unilateral_termination",
            "Unilateral change": "unilateral_change", "Content removal": "content_removal",
            "Contract by using": "contract_by_using", "Choice of law": "choice_of_law", "Jurisdiction": "jurisdiction",
            "Arbitration": "arbitration"}
TOS_OPTIONS = {
    "not_unfair": "Not unfair: the sentence is none of the eight potentially-unfair clause types.",
    "limitation_of_liability": "Limitation of liability: the provider excludes or caps its liability, or disclaims warranties.",
    "unilateral_termination": "Unilateral termination: the provider may suspend or terminate the service or the user's account at will.",
    "unilateral_change": "Unilateral change: the provider may change the terms or the service on its own.",
    "content_removal": "Content removal: the provider may remove, delete or refuse the user's content at its discretion.",
    "contract_by_using": "Contract by using: the user is bound simply by using or accessing the service.",
    "choice_of_law": "Choice of law: which country's or state's law governs the terms.",
    "jurisdiction": "Jurisdiction: which courts or place will hear disputes.",
    "arbitration": "Arbitration: disputes go to (usually binding) arbitration rather than court.",
}
TOS_CUES = {"limitation_of_liability": r"liab|warrant|responsib|damages|as is",
            "unilateral_termination": r"terminat|suspend|discontinu|cancel|close|deactivat|disabl",
            "unilateral_change": r"chang|modif|amend|updat|revis|alter",
            "content_removal": r"remov|delet|take down|un-share|edit|refuse",
            "contract_by_using": r"by (using|accessing|continuing|visiting|browsing|registering|creating)|deemed|constitut",
            "choice_of_law": r"govern|laws? of", "jurisdiction": r"court|jurisdiction|venue|forum",
            "arbitration": r"arbitrat"}
FAIR_SCREEN = re.compile(
    r"liab|warrant|indemnif|damages|as is|responsib|terminat|suspend|discontinu|cancel|deactivat|disabl|remov|delet|"
    r"take down|modif|chang|amend|updat|revis|alter|arbitrat|govern|law|jurisdiction|court|venue|forum|dispute|"
    r"by (using|accessing|continuing|visiting|browsing|registering|creating)|deemed|constitut|sole discretion|"
    r"at any time|for any reason|without notice", re.I)
TOS_DOCUMENTS = [(0, "Academia.edu"), (193, "Amazon"), (325, "Netflix"), (411, "Snap"), (579, "Twitter"),
                 (659, "LinkedIn"), (853, "Duolingo"), (993, "Uber"), (1111, "Evernote"), (1347, "eBay")]
TOS_ROWS = 1607
TOS_MIN_CHARS, TOS_MAX_CHARS = 60, 600
TOS_PLAN = {"not_unfair": 9, "limitation_of_liability": 3, "unilateral_termination": 3, "unilateral_change": 3,
            "content_removal": 3, "contract_by_using": 3, "choice_of_law": 3, "jurisdiction": 3, "arbitration": 3}
TOS_PER_DOCUMENT = 5
TOS_SKIP = {
}


def _detok(text):
    """Undo the corpus tokenisation (PTB quotes and spaced punctuation); the text stays lower-cased as published."""
    t = text.replace("``", '"').replace("''", '"')
    t = re.sub(r"\s+([,.;:!?%)\]])", r"\1", t)
    t = re.sub(r"([(\[$])\s+", r"\1", t)
    t = re.sub(r"\s+(n't|'s|'re|'ve|'ll|'d|'m)\b", r"\1", t)
    t = re.sub(r'"\s+([^"]*?)\s+"', r'"\1"', t)
    return " ".join(t.split())


def _tos_rows():
    rows = []
    for o in LEXGLUE_WINDOWS:
        data = json.loads((SOURCE_DIR / f"lexglue-unfair-tos/test-{o}.json").read_text())
        rows += [r["row"] for r in data["rows"]]
    assert len(rows) == TOS_ROWS, f"LEG-3: expected {TOS_ROWS} test rows, got {len(rows)}"
    return rows


def _tos_document(i):
    starts = [s for s, _ in TOS_DOCUMENTS]
    k = max(j for j, s in enumerate(starts) if s <= i)
    end = starts[k + 1] if k + 1 < len(starts) else TOS_ROWS
    return TOS_DOCUMENTS[k][1], starts[k], end


def _tos_candidates(rows):
    for i, r in enumerate(rows):
        text = _detok(r["text"])
        if not TOS_MIN_CHARS <= len(text) <= TOS_MAX_CHARS or i in TOS_SKIP:
            continue
        if len(r["labels"]) > 1:
            continue
        if r["labels"]:
            yield i, TOS_KEYS[TOS_LABELS[r["labels"][0]]], text
        elif not FAIR_SCREEN.search(text):
            yield i, "not_unfair", text


def _leg3():
    task("LEG-3", category="legal", name="Is this term unfair, and how?", ask="Is this term unfair, and how?",
         instruction=(
             "You screen consumer terms of service for potentially unfair terms, following the eight clause types "
             "that legal researchers flag under EU consumer law. You see one sentence from a real terms-of-service "
             "document, lower-cased as published, with the sentence before and after it for context. Decide which "
             "one type the sentence itself is, or 'not unfair' if it is none of them. Judge the sentence, not its "
             "neighbours. A sentence that names the governing law, the courts or arbitration counts as that type "
             "whatever it chooses."),
         options=TOS_OPTIONS, shape="classify", input_type="terms-of-service sentence", modality="text",
         expertise="none", contamination="high", label_origin="human experts")
    rows = _tos_rows()
    pool = sorted(_tos_candidates(rows), key=lambda c: rank(f"unfair_tos:test:{c[0]}"))
    per_doc, taken, chosen = {}, {}, []
    for key in sorted(TOS_PLAN, key=lambda k: sum(1 for c in pool if c[1] == k)):
        for i, k, text in pool:
            if k != key:
                continue
            if taken.get(key, 0) >= TOS_PLAN[key]:
                break
            name = _tos_document(i)[0]
            if per_doc.get(name, 0) >= TOS_PER_DOCUMENT:
                continue
            per_doc[name] = per_doc.get(name, 0) + 1
            taken[key] = taken.get(key, 0) + 1
            chosen.append((i, key, text))
        assert taken.get(key, 0) == TOS_PLAN[key], f"LEG-3: only {taken.get(key, 0)} {key} rows"
    for i, key, text in sorted(chosen, key=lambda c: rank(f"unfair_tos:test:{c[0]}")):
        name, start, end = _tos_document(i)
        state = {"sentence": _redact(text)}
        if i > start:
            state["previous_sentence"] = _redact(_detok(rows[i - 1]["text"]))
        if i + 1 < end:
            state["next_sentence"] = _redact(_detok(rows[i + 1]["text"]))
        label = TOS_LABELS[rows[i]["labels"][0]] if rows[i]["labels"] else "none"
        if key == "not_unfair":
            rationale = (f"The annotators tagged no clause type on this sentence, and it contains none of the cue "
                         f"words of the eight types; it reads: \"{_quote(text, None, 160)}\"")
        else:
            rationale = f"The annotators tagged this sentence \"{label}\": \"{_quote(text, TOS_CUES[key], 200)}\""
        row("LEG-3", f"unfair-tos-test-{i}", title=f"{name} terms of service · sentence {i - start + 1} of {end - start}",
            state=state, gold=key, rationale=rationale, tags=(key,),
            source={**LEXGLUE, "record_id": f"unfair_tos test row {i} ({name}, sentence {i - start + 1})",
                    "original_label": label})


# ======================================================================================================================

def _datasets():
    dataset(id="contractnli", name="ContractNLI", tasks=["LEG-1"], homepage=CONTRACTNLI["url"], license="CC-BY-4.0",
            license_url="https://stanfordnlp.github.io/contract-nli/resources/contract-nli.zip",
            content="Full texts of real non-disclosure agreements: exhibits filed with the US SEC (EDGAR) and NDA "
                    "templates or forms that companies, universities and public bodies posted on the web, collected "
                    "by the ContractNLI authors (Hitachi America).",
            content_license="CC-BY-4.0",
            content_terms="The dataset zip holds LICENSE (CC BY 4.0) and TERMS (saved as data/sources/contractnli/"
                          "LICENSE and LICENSE-TERMS). Hitachi America's TERMS grant use \"in accordance with "
                          "the terms and conditions of the Creative Commons Attribution 4.0 International Public License\" and give a notice "
                          f"address for anyone who believes the dataset \"incorporates any of your work\". {SEC_TERMS} "
                          "The web templates carry no license of their own; "
                          "agreements with a copyright notice are not used (COPYRIGHT_NOTICE), and each row links "
                          "the agreement's original URL (document_url). Some agreements name business contacts in "
                          "their notice clauses; their phone numbers and e-mail addresses are removed.",
            labelled_by=CONTRACTNLI["labelled_by"],
            changes="The hypothesis and the full agreement text are shown as ContractNLI has them, except that "
                    "e-mail addresses and phone/fax numbers are replaced with placeholders; the labels are renamed "
                    "(Entailment -> yes, Contradiction -> says_opposite, NotMentioned -> not_addressed).",
            selection="Test-split agreements of at most 10,000 characters, 11 pairs per label in sha256 order of "
                      "(document, hypothesis), one row per agreement, at most 2 per hypothesis, minus the pairs "
                      "excluded by the rules in authoring/bench/legal.py.",
            citation=CONTRACTNLI["citation"],
            bibtex="""@inproceedings{koreeda-manning-2021-contractnli-dataset,
  title     = {{ContractNLI}: A Dataset for Document-level Natural Language Inference for Contracts},
  author    = {Koreeda, Yuta and Manning, Christopher},
  booktitle = {Findings of the Association for Computational Linguistics: EMNLP 2021},
  year      = {2021},
  address   = {Punta Cana, Dominican Republic},
  publisher = {Association for Computational Linguistics},
  pages     = {1907--1919},
  doi       = {10.18653/v1/2021.findings-emnlp.164},
  url       = {https://aclanthology.org/2021.findings-emnlp.164/}
}""")
    dataset(id="cuad", name="CUAD (Contract Understanding Atticus Dataset) v1", tasks=["LEG-2", "LEG-4"],
            homepage="https://www.atticusprojectai.org/cuad", license="CC-BY-4.0",
            license_url="https://huggingface.co/datasets/theatticusproject/cuad",
            content="Clauses and continuous excerpts from real commercial contracts (supply, distribution, licence, "
                    "endorsement, hosting and similar agreements) that public companies filed as exhibits with the US "
                    "SEC (EDGAR), collected and annotated by The Atticus Project.",
            content_license="CC-BY-4.0",
            content_terms="The Atticus Project publishes CUAD under CC BY 4.0: its project page "
                          "(https://www.atticusprojectai.org/cuad) carries the licence in its header and the Hugging "
                          "Face dataset card (https://huggingface.co/datasets/theatticusproject/cuad) declares "
                          f"license: cc-by-4.0 (saved as data/sources/cuad/LICENSE-CARD.md and LICENSE-README.txt). {SEC_TERMS} "
                          "Notice clauses in these contracts name business contacts; their phone/fax numbers and "
                          "e-mail addresses are removed.",
            labelled_by=CUAD["labelled_by"],
            changes="Clause spans and excerpts are shown as CUAD's text files have them, whitespace collapsed inside "
                    "a clause, with e-mail addresses and phone/fax numbers replaced by placeholders; excerpts are cut at "
                    "line or sentence boundaries and marked with an ellipsis and a character range. The clause-type "
                    "definitions are CUAD's own 'Details' text.",
            selection="Test-split contracts (102). LEG-2: five highlighted spans per clause type, one per contract, "
                      "excluding spans whose surroundings touch another of the six types. LEG-4: contracts not used by "
                      "LEG-2; per type, 2–3 excerpts holding a highlighted span and 2–3 from contracts marked as "
                      "lacking the type whose excerpt passes a written cue screen. All in sha256 order.",
            citation=CUAD["citation"],
            bibtex="""@inproceedings{hendrycks2021cuad,
  title     = {{CUAD}: An Expert-Annotated {NLP} Dataset for Legal Contract Review},
  author    = {Hendrycks, Dan and Burns, Collin and Chen, Anya and Ball, Spencer},
  booktitle = {Proceedings of the Neural Information Processing Systems Track on Datasets and Benchmarks},
  year      = {2021},
  url       = {https://arxiv.org/abs/2103.06268}
}""")
    dataset(id="lexglue-unfair-tos", name="UNFAIR-ToS (LexGLUE)", tasks=["LEG-3"], homepage=LEXGLUE["url"],
            license="CC-BY-4.0", license_url="https://huggingface.co/datasets/coastalcph/lex_glue",
            content="Single sentences (with their neighbours) from the public terms of service of ten online platforms "
                    "(Academia.edu, Amazon, Netflix, Snap, Twitter, LinkedIn, Duolingo, Uber, Evernote, eBay) as "
                    "collected in 2017–2018 by the CLAUDETTE project (Lippi et al. 2019) and repackaged in LexGLUE.",
            content_license="CC-BY-4.0",
            content_terms="LexGLUE's dataset card declares license: cc-by-4.0 (saved as data/sources/lexglue-unfair-tos/"
                          "LICENSE-CARD.md); the CLAUDETTE authors published the same sentences with their tags at "
                          "https://claudette.eui.eu/corpora/ without a separate licence statement. The sentences are "
                          "short excerpts of terms of service that the platforms posted publicly for all users to read; "
                          "each row shows at most three consecutive sentences. Contact details, if any, are removed.",
            labelled_by=LEXGLUE["labelled_by"],
            changes="Sentences are shown as LexGLUE has them (lower-cased) with the corpus tokenisation undone "
                    "(PTB quotes and spaces before punctuation); labels renamed to snake_case keys and 'not_unfair' "
                    "for an untagged sentence.",
            selection="Test-split sentences of 60–600 characters with exactly one tag, or with no tag and none of the "
                      "cue words of the eight types; 9 untagged and 3 per type, at most 5 per document, in sha256 "
                      "order of the row index; neighbours come from the same document only.",
            citation=LEXGLUE["citation"],
            bibtex="""@article{lippi2019claudette,
  title     = {{CLAUDETTE}: an automated detector of potentially unfair clauses in online terms of service},
  author    = {Lippi, Marco and Pa{\\l}ka, Przemys{\\l}aw and Contissa, Giuseppe and Lagioia, Francesca and Micklitz, Hans-Wolfgang and Sartor, Giovanni and Torroni, Paolo},
  journal   = {Artificial Intelligence and Law},
  volume    = {27},
  pages     = {117--139},
  year      = {2019},
  doi       = {10.1007/s10506-019-09243-2}
}
@inproceedings{chalkidis-etal-2022-lexglue,
  title     = {{LexGLUE}: A Benchmark Dataset for Legal Language Understanding in {E}nglish},
  author    = {Chalkidis, Ilias and Jana, Abhik and Hartung, Dirk and Bommarito, Michael and Androutsopoulos, Ion and Katz, Daniel Martin and Aletras, Nikolaos},
  booktitle = {Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics},
  year      = {2022},
  doi       = {10.18653/v1/2022.acl-long.297}
}""")


def define():
    _datasets()
    _leg1()
    docs = _cuad_docs()
    used = _leg2(docs)
    _leg3()
    _leg4(docs, used)
