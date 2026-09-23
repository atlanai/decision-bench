"""Contract and policy checks: CP-1 (does this NDA say this?). See authoring/bench/__init__.py and docs/tasks.md.

CP-1 — ContractNLI (CC BY 4.0; Koreeda and Manning, Findings of EMNLP 2021), test split. Each row pairs one real
NDA with one of the dataset's 17 fixed hypotheses. The state is the hypothesis exactly as the dataset words it
("statement") and the full agreement text ("agreement"); only agreements of at most MAX_CHARS characters are used,
so no evidence is cut and a not_addressed answer can be checked against the whole document. The title carries a
plain-English question for the hypothesis (QUESTIONS) and a short name for the agreement (AGREEMENTS).

Label mapping: Entailment -> yes, Contradiction -> says_opposite, NotMentioned -> not_addressed.

Exclusions, applied before sampling:
  - EXCLUDE: pairs left out after a manual review of label defensibility (a skeptical reviewer could defend a
    second label from the text), each with its reason — carried over unchanged from the reviewed draft
    (authoring/real/contractnli.py);
  - Entailment or Contradiction labels with no evidence span;
  - consent-gated permissions: a Contradiction of "may share with third parties" (nda-7) or "may make copies"
    (nda-17) whose evidence mentions consent, approval or authorisation (then "may, in some circumstances" is
    arguably true);
  - copyright notices (license policy): an agreement whose text carries a copyright notice (COPYRIGHT_NOTICE: "©",
    "(c) 2019", "Copyright 2019", "All rights reserved") is not reproduced in full. None of the sampled agreements
    carries one, so no row changed when this rule was added.

Contact details: e-mail addresses and phone/fax numbers printed in notice clauses and signature blocks are
replaced with "[e-mail removed]" / "[phone removed]" (EMAIL, PHONE) in the text shown. No hypothesis turns on them.
Names, titles and postal addresses of the signing organisations are kept, as filed.

License: ContractNLI is CC BY 4.0 (its LICENSE, and its TERMS, which also give a copyright-infringement notice
address). The agreements themselves are SEC EDGAR exhibits or NDA templates found on the web; see `_datasets`.

Sampling: for each label, scarcest first (Contradiction, Entailment, NotMentioned), candidate (document,
hypothesis) pairs are ordered by rank(f"{doc_id}:{hypothesis_id}") and taken greedily while the pair is not
excluded, the document has not been used by another row, and the hypothesis has fewer than PER_STATEMENT rows,
until PER_LABEL rows are taken.
"""
import json
import re

from . import dataset, task, row, rank, SOURCES as SOURCE_DIR

SOURCES = [
    {"dataset": "ContractNLI v1.0, test split", "url": "https://stanfordnlp.github.io/contract-nli/resources/contract-nli.zip",
     "zip_member": "contract-nli/test.json", "path": "contractnli/test.json"},
]

CONTRACTNLI = dict(dataset_id="contractnli", dataset="ContractNLI", license="CC BY 4.0", url="https://stanfordnlp.github.io/contract-nli/",
                   citation="Koreeda and Manning, ContractNLI: A Dataset for Document-level Natural Language "
                            "Inference for Contracts, Findings of EMNLP 2021.",
                   labelled_by="ContractNLI's annotators, who also marked the evidence spans")
MAX_CHARS = 10000
PER_LABEL = 10
PER_STATEMENT = 2
LABELS = {"Entailment": "yes", "Contradiction": "says_opposite", "NotMentioned": "not_addressed"}

# Records reviewed and left out because a skeptical reviewer could defend a second label from the text.
# Keyed by (document id, hypothesis id). Documented, not model-derived. (From authoring/real/contractnli.py.)
EXCLUDE = {
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
}
COPYRIGHT_NOTICE = re.compile(r"©|\(c\)\s*(19|20)\d\d|\bcopyright\s+(\(c\)\s*)?(19|20)\d\d|all rights reserved",
                              re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?<![\w$])(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)\s?|\d{3}[\s.-])\d{3}[\s.-]\d{4}"
                   r"(?:,?\s*ext\.?\s*\d+)?(?!\d)")
CONSENT_GATED = {"nda-7", "nda-17"}
CONSENT = re.compile(r"consent|approv|authori[sz]|permission", re.I)

# Plain-English question for each hypothesis (titles only; "yes" means the dataset's Entailment), the thing the
# agreement asserts when it contradicts the hypothesis, and the clause family whose absence makes it NotMentioned.
QUESTIONS = {
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
CLAIMS = {
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
CONTRA_GLOSS = {"nda-1": "some confidential information is protected without being marked or identified",
                "nda-2": "confidential information also covers non-technical information",
                "nda-3": "confidential information must be in tangible form, so oral disclosures are not covered",
                "nda-4": "the recipient may use residual knowledge beyond the stated purpose",
                "nda-5": "the recipient may not share the information with its employees",
                "nda-7": "only the recipient's own employees may receive the information",
                "nda-16": "the recipient need not return or destroy the information",
                "nda-17": "the recipient may not copy the information",
                "nda-19": "the obligations end with the agreement",
                "nda-20": "all the information must be returned or destroyed, leaving nothing retained"}
ABSENT = {
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
CUES = {"nda-1": r"mark|identif|designat", "nda-2": r"technical|business|financial|commercial|pricing|customer",
        "nda-3": r"oral|verbal", "nda-4": r"purpose|residual|use", "nda-5": r"employee",
        "nda-7": r"consultant|advis|agent|counsel|third|contractor|individuals|representative",
        "nda-8": r"notif|notice", "nda-10": r"existence|terms|fact", "nda-11": r"reverse|decompil|disassembl",
        "nda-12": r"independent", "nda-13": r"third|other than|source|free of", "nda-15": r"licen|right",
        "nda-16": r"return|destr", "nda-17": r"cop(y|ies)|reproduc", "nda-18": r"solicit|hire",
        "nda-19": r"surviv|years|terminat", "nda-20": r"retain|return|destr|cop(y|ies)"}
CONTRA_CUES = {"nda-1": r"orally|reasonabl", "nda-3": r"tangible|writing"}

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
}
# What a sampled NotMentioned agreement does say nearby, so the rationale points at its own text (optional).
NM_NOTES = {
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


def _redact(text):
    return PHONE.sub("[phone removed]", EMAIL.sub("[e-mail removed]", text))


def _excluded(doc, hyp, ann):
    if (doc["id"], hyp) in EXCLUDE or COPYRIGHT_NOTICE.search(doc["text"]):
        return True
    if ann["choice"] != "NotMentioned" and not ann["spans"]:
        return True
    evidence = " ".join(doc["text"][doc["spans"][i][0]:doc["spans"][i][1]] for i in ann["spans"])
    return ann["choice"] == "Contradiction" and hyp in CONSENT_GATED and bool(CONSENT.search(evidence))


def _quote(doc, hyp, span_ids, contra=False, limit=200):
    texts = [" ".join(doc["text"][doc["spans"][i][0]:doc["spans"][i][1]].split()) for i in sorted(span_ids)]
    body = [t for t in texts if len(t) >= 25 and not t.endswith(":")] or texts
    cue = CONTRA_CUES.get(hyp, CUES[hyp]) if contra else CUES[hyp]
    hit = next(((t, m) for t in body for m in [re.search(cue, t, re.I)] if m), None)
    pick, start = (hit[0], hit[1].start()) if hit else (body[0], 0)
    if len(pick) <= limit:
        return pick
    lo = 0 if start < limit * 0.6 else pick.rfind(" ", 0, max(0, start - 100)) + 1
    out = pick[lo:lo + limit - 6].rsplit(" ", 1)[0]
    return ("..." if lo else "") + out + "..."


def _rationale(doc, hyp, ann, gold):
    if gold == "not_addressed":
        note = NM_NOTES.get((doc["id"], hyp))
        return f"The agreement has no clause settling this: it lacks {ABSENT[hyp]}." + (f" {note}" if note else "")
    claim = CLAIMS[hyp] if gold == "yes" else CONTRA_GLOSS[hyp]
    return f"The agreement says {claim}: \"{_quote(doc, hyp, ann['spans'], gold == 'says_opposite')}\""


def _sample(data):
    docs = [d for d in data["documents"] if len(d["text"]) <= MAX_CHARS]
    used_docs, per_statement, chosen = set(), {}, []
    for label in ("Contradiction", "Entailment", "NotMentioned"):
        pool = [(d, h, a) for d in docs for h, a in d["annotation_sets"][0]["annotations"].items()
                if a["choice"] == label and h in QUESTIONS]
        pool.sort(key=lambda t: rank(f"{t[0]['id']}:{t[1]}"))
        taken = 0
        for d, h, a in pool:
            if taken == PER_LABEL:
                break
            if d["id"] in used_docs or per_statement.get(h, 0) >= PER_STATEMENT or _excluded(d, h, a):
                continue
            used_docs.add(d["id"])
            per_statement[h] = per_statement.get(h, 0) + 1
            chosen.append((d, h, a))
            taken += 1
        assert taken == PER_LABEL, f"CP-1: only {taken} {label} rows"
    return sorted(chosen, key=lambda t: rank(f"{t[0]['id']}:{t[1]}"))


def _datasets():
    dataset(id="contractnli", name="ContractNLI", tasks=["CP-1"], homepage=CONTRACTNLI["url"], license="CC-BY-4.0",
            license_url="https://stanfordnlp.github.io/contract-nli/resources/contract-nli.zip",
            content="Full texts of real non-disclosure agreements: exhibits filed with the US SEC (EDGAR) and NDA "
                    "templates or forms that companies, universities and public bodies posted on the web, collected "
                    "by the ContractNLI authors (Hitachi America).",
            content_license="CC-BY-4.0",
            content_terms="The dataset zip holds LICENSE (CC BY 4.0) and TERMS (saved as data/sources/contractnli/"
                          "LICENSE and LICENSE-TERMS). Hitachi America's TERMS grant use \"in accordance with "
                          "the terms and conditions of the Creative Commons Attribution 4.0 International Public License\" and give a notice "
                          "address for anyone who believes the dataset \"incorporates any of your work\". The SEC "
                          "says \"Information presented on sec.gov is considered public information and may be "
                          "copied or further distributed by users of the web site without the SEC's permission\" "
                          "(https://www.sec.gov/privacy). The web templates carry no license of their own; "
                          "agreements with a copyright notice are not used (COPYRIGHT_NOTICE), and each row links "
                          "the agreement's original URL (document_url). Some agreements name business contacts in "
                          "their notice clauses; their phone numbers and e-mail addresses are removed.",
            labelled_by=CONTRACTNLI["labelled_by"],
            changes="The hypothesis and the full agreement text are shown as ContractNLI has them, except that "
                    "e-mail addresses and phone/fax numbers are replaced with placeholders; the labels are renamed (Entailment -> yes, Contradiction -> says_opposite, NotMentioned -> "
                    "not_addressed).",
            selection="Test-split agreements of at most 10,000 characters, 10 pairs per label in sha256 order of "
                      "(document, hypothesis), one row per agreement, at most 2 per hypothesis, minus the pairs "
                      "excluded by the rules above.",
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


def define():
    _datasets()
    task("CP-1", category="contract-policy", name="NDA clause check", ask="Does this NDA say this?",
         instruction=(
             "You review NDAs for a legal operations team. Read the statement and the full agreement. Decide "
             "whether the agreement states it, states the opposite, or doesn't address it. Judge only from the "
             "agreement's own wording. In the statement, 'Receiving Party' is the party that receives confidential "
             "information, 'Disclosing Party' the party that shares it, and 'Agreement' this agreement; in a mutual "
             "NDA each party is both. 'Not addressed' means no clause settles the point either way."),
         options={"yes": "Yes: the agreement's wording makes the statement true.",
                  "says_opposite": "Says the opposite: the agreement's wording makes the statement false.",
                  "not_addressed": "Not addressed: no clause settles the point, so the statement is neither true "
                                   "nor false under the agreement."})
    data = json.loads((SOURCE_DIR / "contractnli/test.json").read_text())
    hypotheses = data["labels"]
    for d, h, a in _sample(data):
        if d["id"] not in AGREEMENTS:
            raise KeyError(f"CP-1: add a short name for document {d['id']} ({d['file_name']}): {d['text'][:200]!r}")
        gold = LABELS[a["choice"]]
        row("CP-1", f"contractnli-{d['id']}-{h}", title=f"{AGREEMENTS[d['id']]} · {QUESTIONS[h]}",
            state={"statement": hypotheses[h]["hypothesis"], "agreement": _redact(d["text"])},
            gold=gold, rationale=_rationale(d, h, a, gold), tags=(h,),
            source={**CONTRACTNLI, "record_id": f"test document {d['id']} ({d['file_name']}), hypothesis {h}",
                    "original_label": a["choice"], "document_url": d["url"]})
