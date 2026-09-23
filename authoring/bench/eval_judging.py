"""Eval judging: EJ-1 (is this answer supported by its sources?) and EJ-2 (which of two responses is better?).
See authoring/bench/__init__.py and docs/tasks.md.

License rule: a dataset is used only if its own license AND the terms of the text inside it allow redistribution,
including commercial use. RAGTruth (MS MARCO passages, CNN/Daily Mail and other news) and LLMBar Natural
(AlpacaFarm, CC BY-NC 4.0) failed that rule and were replaced by the three datasets below. Model outputs inside a
dataset are fine.

EJ-1 — two datasets, half the rows each. Both are real model outputs whose grounding was judged by humans against
Wikipedia text (CC BY-SA 3.0), so every row can be checked against its sources in about a minute.

  HAGRID (Apache-2.0; Kamalloo et al., 2023), English dev split (hagrid/dev.jsonl). MIRACL's annotators wrote each
  question and marked the Wikipedia paragraphs relevant to it (the "quotes"; English Wikipedia, 1 February 2019
  dump, CC BY-SA 3.0). GPT-3.5 (gpt-3.5-turbo-0301) wrote answers that cite the quotes by number, and HAGRID's four
  trained annotators judged every answer sentence: "attributable" only if the quotes it cites fully support it.

    State: setting, user_message (the question), sources (every quote, numbered as the model saw them) and answer.
    Nothing is trimmed; states over HAGRID_MAX_CHARS are skipped.
    Label mapping (answer-level `attributable`, which HAGRID sets to 1 only when every sentence is 1):
      supported      attributable 1;
      not_supported  attributable 0.
    Exclusions, before sampling:
      - answers not judged for attributability, or with any unjudged sentence, or whose answer label disagrees with
        its sentence labels; answers judged uninformative (`informative` 0: they don't answer the question, so the
        row would test refusals, not grounding);
      - ARTEFACT RULE: answers whose sentence list repeats a sentence (after removing citation numbers). HAGRID
        sometimes lists one sentence once per cited quote with separate labels (e.g. the pope-smoke question,
        "Black smoke indicates a failed ballot" labelled six times), so the answer label is unreliable;
      - CITATION RULE: every sentence must cite at least one quote that exists; answers containing a URL (the
        model's invented reference lists) are skipped;
      - MULTI-CITATION RULE (not_supported): at least one unsupported sentence cites exactly one quote. HAGRID also
        marks a sentence unsupported when only some of its several cited quotes back it, which a reader asked
        "is it supported by the sources?" would not call unsupported;
      - EXTRACTIVE-NEGATIVE RULE (not_supported): among the unsupported sentences that cite one quote, at least
        one has HAGRID_MIN_NEW_WORDS content words (not stopwords or numbers) that its quote doesn't contain.
        Unsupported labels on near-copies of the cited quote are mostly annotation slips (e.g. query 108, "The Omo
        River is 760 kilometers long. [1]", where the quote says exactly that);
      - WEAK-ANNOTATION RULE: a sentence whose words (Jaccard >= 0.9, citations removed) match a sentence given the
        opposite label in any answer to the same question — the annotation disagrees with itself;
      - SENSITIVE rule (offensive content, and people as subjects of crime or harm): question, quotes or answer
        matching SENSITIVE (murder, rape, suicide, terrorism, arrests, convictions, ...). Every subject is a
        Wikipedia topic, so no row is centred on a private individual;
      - EXCLUDE: records read in review and left out, each with its reason (a label a skeptical reviewer could
        dispute from the row alone).
    Reader notes: HAGRID_NOTES says, for each not_supported row, what the passage lacks; it goes in the rationale
    after the annotators' judgement. The build fails if a sampled row lacks one.
    Sampling: each question is used at most once; candidates are ordered short states first
    (<= HAGRID_SHORT_CHARS), then by rank(record id); picks are greedy, taking the first candidate whose answer
    type (HAGRID's "short"/"long" prompt) has been used least within the label so far.

  BEGIN (CC BY 4.0; Dziri et al., TACL 2022), Wizard of Wikipedia part (begin/begin_{dev,test}_wow.tsv). Each
  record is one reply from a knowledge-grounded dialogue model (fine-tuned T5, GPT-2, DoHA or CTRL-dialog) to a
  crowdworker's message, given one Wikipedia sentence as knowledge. Three trained annotators labelled each reply;
  the label is their majority vote (examples where all three disagreed were removed by the authors). BEGIN's
  CMU-DoG and TopicalChat parts are not used: their knowledge includes movie reviews and news articles whose terms
  don't allow redistribution (TopicalChat is CDLA-Sharing-1.0).

    State: setting, user_message (the crowdworker's previous turn), sources (the knowledge sentence as [1]) and
    answer (the reply, verbatim: the models' tokenised spacing such as "it 's" is left as the annotators saw it).
    Label mapping: "Fully attributable" -> supported, "Not fully attributable" -> not_supported ("Generic" rows,
    6 in total, are not used). BEGIN's annotators were told that personal stories and opinions count as
    unsupported information; the EJ-1 instruction says so too.
    Exclusions, before sampling:
      - replies under BEGIN_MIN_WORDS words;
      - OVERLAP BAND: the share of reply words found in the knowledge must lie in BEGIN_OVERLAP. Near-copies are
        almost always attributable and off-topic replies almost always not, so outside the band surface overlap
        gives the label away;
      - SENSITIVE rule, as above (BEGIN was already filtered with the Perspective API for toxicity), and messages
        or replies containing an email address, URL or phone number;
      - EXCLUDE: records read in review and left out, each with its reason.
    Reader notes: BEGIN_TOPICS gives each sampled row a neutral title subject and one sentence on why the label
    holds (used in the rationale).
    Sampling: each knowledge sentence is used at most once (compared ignoring case and punctuation: WoW has
    lower-cased copies); candidates ordered by rank(record id); greedy, taking
    the first candidate whose model has been used least within the label so far.

  EJ-1 has HAGRID_PER_LABEL + BEGIN_PER_LABEL rows per label, shown in rank(row id) order.

EJ-2 — MT-Bench human judgments (CC BY 4.0; Zheng et al., NeurIPS 2023 Datasets and Benchmarks), "human" split,
read from the Hugging Face rows API pages in SOURCES (the parquet needs pyarrow). 3,355 pairwise votes by expert
judges (mostly graduate students with expertise in the question's topic, plus the authors) between responses from
GPT-4, GPT-3.5, Claude-v1, Vicuna-13B, Alpaca-13B and LLaMA-13B to the 80 MT-Bench questions, which LMSYS wrote
and also released in FastChat (Apache-2.0).

  Only turn 1 is used: the question and the two first-turn responses (the dataset stores the whole two-turn
  conversation with every vote; turn-1 votes judge the first answer only). Votes are grouped by question and
  unordered model pair. Label: the model every judge of that pair preferred.
  Exclusions, before sampling:
    - CLEAR-VERDICT RULE: fewer than MTB_MIN_JUDGES judges, or any tie, or any disagreement;
    - coding questions (121-130): judging them properly means running or tracing the code;
    - question 91 (answer as Elon Musk): the response impersonates a real, living person;
    - pairs involving LLaMA-13B: it is a base model, not an assistant, so its responses seldom make a real
      comparison;
    - either response over MTB_MAX_RESPONSE characters; identical responses; SENSITIVE matches in either response;
    - EXCLUDE: pairs read in review and left out, each with its reason: the preferred response breaks a stated
      constraint, both responses are wrong, or both meet every requirement and the preference is only style.
  Reader notes: MTB_NOTES gives each sampled pair a neutral title subject and one sentence on why the preferred
  response is better (the rationale).
  Sampling: MTB_PER_CATEGORY pairs from each of the seven remaining MT-Bench categories; each question used at most
  once; candidates ordered by rank(record id); greedy, taking the first candidate whose model pair has been used
  least so far. Order: the chosen rows are sorted by rank(record id) and the preferred response is shown as A on
  every other row (so exactly half the answers are A); `source.shown_order` records which model is A and
  `source.swapped` whether that differs from the dataset's model_a/model_b order in the pair's first vote.
"""
import collections
import csv
import json
import re

from . import task, row, rank, dataset, SOURCES as SOURCE_DIR

HAGRID_REV = "b2a085913606be3c4f2f1a8bff1810e38bade8fa"         # huggingface.co/datasets/miracl/hagrid
HAGRID_GITHUB_REV = "7ffab03942e93d3138b0dbd14ad0a844f8a075d5"  # github.com/project-miracl/hagrid
BEGIN_REV = "6e65f0d5a1ed1b9574643a7640ff1678d4e979b5"          # github.com/google/BEGIN-dataset
MTB_REV = "f7d2896d2cc5d80f8b55c2bbc722613555233c25"            # huggingface.co/datasets/lmsys/mt_bench_human_judgments
FASTCHAT_REV = "587d5cfa1609a43d192cedb8441cac3c17db105d"       # github.com/lm-sys/FastChat
MTB_ROWS = ("https://datasets-server.huggingface.co/rows?dataset=lmsys/mt_bench_human_judgments&config=default"
            "&split=human&offset={offset}&length=100")
MTB_TOTAL = 3355
BEGIN_RAW = f"https://raw.githubusercontent.com/google/BEGIN-dataset/{BEGIN_REV}/wow"
SOURCES = [
    {"dataset": "HAGRID, English dev split",
     "url": f"https://huggingface.co/datasets/miracl/hagrid/resolve/{HAGRID_REV}/hagrid-v1.0-en/dev.jsonl",
     "path": "hagrid/dev.jsonl"},
    {"dataset": "HAGRID", "url": f"https://raw.githubusercontent.com/project-miracl/hagrid/{HAGRID_GITHUB_REV}/LICENSE",
     "path": "hagrid/LICENSE"},
    {"dataset": "BEGIN, Wizard of Wikipedia dev", "url": f"{BEGIN_RAW}/begin_dev_wow.tsv",
     "path": "begin/begin_dev_wow.tsv"},
    {"dataset": "BEGIN, Wizard of Wikipedia test", "url": f"{BEGIN_RAW}/begin_test_wow.tsv",
     "path": "begin/begin_test_wow.tsv"},
    {"dataset": "BEGIN", "url": f"{BEGIN_RAW}/LICENSE", "path": "begin/LICENSE"},
    {"dataset": "BEGIN", "url": f"{BEGIN_RAW}/NOTICE", "path": "begin/NOTICE"},
    *({"dataset": "MT-Bench human judgments, human split, rows API page", "url": MTB_ROWS.format(offset=o),
       "path": f"mt-bench-human-judgments/rows/human-{o:05d}.json"} for o in range(0, MTB_TOTAL, 100)),
    {"dataset": "MT-Bench human judgments (dataset card, states the license)",
     "url": f"https://huggingface.co/datasets/lmsys/mt_bench_human_judgments/raw/{MTB_REV}/README.md",
     "path": "mt-bench-human-judgments/README.md"},
    {"dataset": "FastChat (MT-Bench questions)",
     "url": f"https://raw.githubusercontent.com/lm-sys/FastChat/{FASTCHAT_REV}/LICENSE",
     "path": "mt-bench-human-judgments/FASTCHAT-LICENSE"},
]

CATEGORY = "eval-judging"

SENSITIVE = re.compile(
    r"\b(murder\w*|homicide|kill(ed|ing|er|s)?|rap(e|ed|es|ist)|sexual(ly)? (assault|abuse)\w*|molest\w*|"
    r"suicid\w*|terror\w*|massacre\w*|genocide|tortur\w*|lynch\w*|abuse[ds]?|arrest\w*|convicted|conviction|"
    r"indict\w*|sentenced|prison\w*|inmate\w*|porn\w*|slave\w*|nazi\w*|holocaust|overdose\w*)\b", re.I)
CONTACT = re.compile(r"\S+@\S+\.\w+|https?://|www\.|\b\d{3}[-. ]\d{3}[-. ]\d{4}\b")
WIKIPEDIA_TERMS = "https://en.wikipedia.org/wiki/Wikipedia:Copyrights"

# ----------------------------------------------------------------------------------------------------------- EJ-1

HAGRID = dict(dataset_id="hagrid", dataset="HAGRID",
              license="Apache-2.0, with Wikipedia passages under CC BY-SA 3.0",
              url="https://huggingface.co/datasets/miracl/hagrid",
              citation="Kamalloo et al., HAGRID: A Human-LLM Collaborative Dataset for Generative Information-Seeking "
                       "with Attribution, arXiv:2307.16883, 2023.",
              labelled_by="HAGRID's trained annotators, who judged whether each answer sentence is fully supported by "
                          "the passages it cites")
BEGIN = dict(dataset_id="begin", dataset="BEGIN (Wizard of Wikipedia part)",
             license="CC BY 4.0, with a Wikipedia sentence under CC BY-SA 3.0",
             url="https://github.com/google/BEGIN-dataset",
             citation="Dziri et al., Evaluating Attribution in Dialogue Systems: The BEGIN Benchmark, TACL 2022.",
             labelled_by="the majority of three trained BEGIN annotators")
HAGRID_PER_LABEL = 7
BEGIN_PER_LABEL = 7
HAGRID_MAX_CHARS = 9000
HAGRID_SHORT_CHARS = 4500
HAGRID_MIN_NEW_WORDS = 3
STOPWORDS = set("a an the of in on at to for by with from and or but is are was were be been being it its this that "
                "these those as which who whom whose what when where why how has have had do does did not no yes can "
                "could will would should may might also than then there their they them he she his her we our you "
                "your i me my so such into over under about after before during between both each other some any all "
                "most more many much very".split())
BEGIN_MIN_WORDS = 8
BEGIN_OVERLAP = (0.4, 0.85)
LABELS = {1: "supported", 0: "not_supported"}
BEGIN_LABELS = {"Fully attributable": "supported", "Not fully attributable": "not_supported"}
SETTINGS = {"hagrid": "Answer a question from the Wikipedia passages provided, citing them by number",
            "begin": "Reply in a chat, using the Wikipedia sentence provided as knowledge"}
BEGIN_MODELS = {"t5": "a fine-tuned T5 dialogue model", "gpt2": "a fine-tuned GPT-2 dialogue model",
                "doha": "DoHA, a fine-tuned BART dialogue model",
                "ctrl": "CTRL-dialog, a controllable T5 dialogue model"}

# Records read in review and left out: {record id: reason}. Applied with the written rules above.
EXCLUDE = {
    "hagrid-dev-533-1": "Labelled not supported, but the passage does describe a two-chamber legislature with a "
                        "Senate; the answer just doesn't answer the question.",
    "hagrid-dev-812-0": "Labelled not supported for \"originates from the Sierra Nevada\"; the passage puts the "
                        "headwaters on the Sierra Crest and describes the Sierra Nevada snowpack, so a reviewer could "
                        "call it supported.",
    "hagrid-dev-2204-1": "Labelled supported, but the passage never calls Windows XP abandonware; it only describes "
                         "the end of support.",
    "hagrid-dev-1369-1": "Labelled supported, but the answer opens with \"Yes\" to whether peers get a salary, which "
                         "the passage (and the rest of the answer) contradicts.",
    "hagrid-dev-3295-1": "Labelled supported, but the passage links the colours to compass directions and organs, "
                         "not to regions of Korea as the answer says.",
    "mtbench-q85-alpaca-13b-vs-gpt-4": "The preferred GPT-4 response uses two paragraphs where the question asks "
                                       "for fewer than two; a reviewer could prefer the other on that constraint.",
    "mtbench-q86-claude-v1-vs-gpt-4": "Both paragraphs meet every requirement (smells, sounds, sights); the "
                                      "preference is a matter of style.",
    "mtbench-q152-gpt-3.5-turbo-vs-gpt-4": "Both responses answer fully, stage by stage; the preference is a matter "
                                           "of depth and style.",
    "mtbench-q104-claude-v1-vs-vicuna-13b-v1.2": "Both answers are wrong (David has no brothers), so a reviewer could "
                                                 "call it a tie.",
    "mtbench-q83-claude-v1-vs-gpt-4": "Both outlines break the 200-word limit, and the preferred one is longer (268 "
                                      "words, while claiming 160) and fills in invented specifications; a reviewer "
                                      "could prefer the other.",
    "mtbench-q85-claude-v1-vs-gpt-4": "Both responses use two paragraphs where the question asks for fewer than two; "
                                      "the preference is a matter of style.",
    "mtbench-q98-claude-v1-vs-gpt-4": "Both stay in character and answer the question; the preference is a matter "
                                      "of style.",
    "mtbench-q86-gpt-3.5-turbo-vs-gpt-4": "Both paragraphs meet every requirement (smells, sounds, sights); the "
                                          "preference is a matter of style.",
    "begin-wow-test-3183": "Labelled fully attributable, but the reply adds \"he is a hero\", an opinion the knowledge "
                           "doesn't support.",
    "begin-wow-test-3001": "Labelled fully attributable, but the knowledge only says the store is \"asserted to be\" "
                           "the largest; the reply states it as fact.",
    "begin-wow-test-682": "Labelled fully attributable, but the garbled reply says the US and Canada call the sport "
                          "gridiron; the knowledge says they call it football.",
    "begin-wow-test-221": "Labelled not fully attributable, but every claim (500 million copies, seventy-three "
                          "languages) is in the knowledge.",
}

# For each sampled not_supported HAGRID answer: one sentence saying what the passage lacks, written for readers (the
# label itself is HAGRID's). The build fails if a sampled record lacks one.
HAGRID_NOTES = {
    "dev-701-0": "The passage says Kanelos opened a candy store and renamed it; it never mentions the mints.",
    "dev-3430-0": "The passage never says the PWA was a New Deal agency, and the last sentence cites an encyclopedia "
                  "that isn't among the passages.",
    "dev-1145-0": "That sentence cites passage [1], about a Rome Metro station; the antibiotic details are in passage "
                  "[2].",
    "dev-983-0": "Passage [2] doesn't say hassium was made only in laboratories, that it decays by alpha decay or that "
                 "hassium-277 is its most stable isotope.",
    "dev-565-1": "Passage [1] calls the sundial a common time-measuring instrument of the past, not the first.",
    "dev-2241-1": "The passage is about Jessica Jones and never mentions Dani Cage or any film.",
    "dev-2149-1": "Passage [4] says brightness can be measured in lumens or candelas; it doesn't say lumens are the "
                  "most common.",
}

# For each sampled BEGIN reply: a neutral subject for the title and one sentence saying why the label holds, written
# for readers (the label itself is BEGIN's). The build fails if a sampled record lacks one.
BEGIN_TOPICS = {
    "wow-test-3127": ("Nirvana's breakthrough single",
                      "The knowledge says Nirvana's breakthrough came with \"Smells Like Teen Spirit\" from their "
                      "1991 album, which is all the reply says."),
    "wow-test-2875": ("rock and roll's leading figure",
                      "The knowledge mentions his network TV appearances and chart-topping records, which is all the "
                      "reply says."),
    "wow-test-2961": ("cardigan sweaters",
                      "The reply only repeats that a cardigan is a knitted garment with an open front."),
    "wow-test-750": ("largest US state",
                     "The reply's one claim, that it is the largest US state, is in the knowledge (which adds \"by "
                     "area\")."),
    "wow-dev-402": ("blues and jazz festivals",
                    "The reply restates the knowledge: some festivals are for-profit, others benefit a charity."),
    "wow-test-1739": ("Dream Theater",
                      "The only claim, that Dream Theater is a progressive metal band, is in the knowledge; \"That's "
                      "awesome\" adds no information."),
    "wow-test-2849": ("Dylan's Candy Bar locations",
                      "The cities listed are exactly those in the knowledge."),
    "wow-test-1747": ("Instagram's apps",
                      "\"I prefer facebook\" is a personal opinion, and the rest garbles the knowledge's release "
                      "dates."),
    "wow-test-2808": ("cheerleading's global spread",
                      "The knowledge credits ESPN's 1997 broadcast; the reply says the BBC."),
    "wow-test-3070": ("ski jumping venues",
                      "The reply adds \"we'll test them in the Olympics\", which the knowledge doesn't support."),
    "wow-test-258": ("Greyhound buses",
                     "\"They are quite cheap\" is not in the knowledge, which only gives the number of destinations."),
    "wow-test-522": ("management accounting",
                     "\"I love management accounting\" is a personal opinion the knowledge can't support."),
    "wow-test-2011": ("an island's geography",
                      "The reply adds a question about North Korea and a personal \"No\" that the knowledge doesn't "
                      "support."),
    "wow-test-1786": ("Imperial Roman army",
                      "The knowledge gives the army's dates; nothing in it says the army fought a civil war."),
}

NUMBERS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}
CITE = re.compile(r"\[\s*(\d+(?:\s*[,\-–]\s*\d+)*)\s*\]")


def _cited(text):
    out = set()
    for m in CITE.finditer(text):
        for part in re.split(r"\s*,\s*", m.group(1)):
            ends = [int(x) for x in re.split(r"\s*[\-–]\s*", part)]
            out |= set(range(ends[0], ends[-1] + 1))
    return out


def _words(text):
    return re.findall(r"[a-z0-9]+", CITE.sub(" ", text).lower())


def _new_words(text, known):
    """Content words of `text` (not stopwords or numbers) that don't occur in `known`."""
    return {w for w in _words(text) if w not in STOPWORDS and w not in known and not w.isdigit()}


def _clip(text, n):
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[:n - 3].rsplit(" ", 1)[0] + "..."


def _hagrid_state(r, a):
    return {"setting": SETTINGS["hagrid"], "user_message": r["query"],
            "sources": [f"[{q['idx']}] {q['text']}" for q in r["quotes"]], "answer": a["answer"]}


def _hagrid_label(r, ai):
    """The row's gold label, or None if a written rule excludes it."""
    a = r["answers"][ai]
    sentences = a["sentences"]
    judged = [s.get("attributable") for s in sentences]
    if a.get("attributable") not in LABELS or None in judged or (a["attributable"] == 1) != all(judged):
        return None
    if a.get("informative") != 1 or CONTACT.search(a["answer"]):
        return None
    texts = [" ".join(_words(s["text"])) for s in sentences]
    if len(set(texts)) < len(texts):                                   # artefact rule
        return None
    quotes = {q["idx"] for q in r["quotes"]}
    cites = [_cited(s["text"]) for s in sentences]
    if any(not c or c - quotes for c in cites):                        # citation rule
        return None
    if a["attributable"] == 0:
        deciding = [s["text"] for s, c in zip(sentences, cites) if s["attributable"] == 0 and len(c) == 1]
        if not deciding:
            return None                                                # multi-citation rule
        by_idx = {q["idx"]: set(_words(q["text"])) for q in r["quotes"]}
        if max(len(_new_words(t, by_idx[min(_cited(t))])) for t in deciding) < HAGRID_MIN_NEW_WORDS:
            return None                                                # extractive-negative rule
    others = [(set(_words(s["text"])), s["attributable"]) for b in r["answers"] for s in b["sentences"]
              if s.get("attributable") is not None]
    for s in sentences:
        mine = set(_words(s["text"]))
        if any(label != s["attributable"] and mine and len(mine & w) / len(mine | w) >= 0.9 for w, label in others):
            return None                                                # weak-annotation rule
    return LABELS[a["attributable"]]


def _hagrid():
    records = [json.loads(line) for line in (SOURCE_DIR / "hagrid/dev.jsonl").read_text().splitlines() if line]
    pool = collections.defaultdict(list)
    for r in records:
        for ai, a in enumerate(r["answers"]):
            rid = f"dev-{r['query_id']}-{ai}"
            state = _hagrid_state(r, a)
            text = json.dumps(state, ensure_ascii=False)
            if f"hagrid-{rid}" in EXCLUDE or len(text) > HAGRID_MAX_CHARS or SENSITIVE.search(text):
                continue
            gold = _hagrid_label(r, ai)
            if gold:
                pool[gold].append((rid, r, ai, len(text)))
    chosen, used_queries = [], set()
    for gold in ("not_supported", "supported"):                        # scarcer label first
        cands = sorted(pool[gold], key=lambda t: (t[3] > HAGRID_SHORT_CHARS, rank(f"hagrid-{t[0]}")))
        used = collections.Counter()
        for _ in range(HAGRID_PER_LABEL):
            cands = [t for t in cands if t[1]["query_id"] not in used_queries]
            pick = min(cands, key=lambda t: used[t[1]["answers"][t[2]]["answer_type"]])
            used_queries.add(pick[1]["query_id"])
            used[pick[1]["answers"][pick[2]]["answer_type"]] += 1
            chosen.append((gold, pick))
    return chosen


def _hagrid_rationale(rid, r, ai, gold):
    if gold == "supported":
        return "HAGRID's annotators judged every sentence of the answer fully supported by the passages it cites."
    bad = [s for s in r["answers"][ai]["sentences"] if s["attributable"] == 0]
    first = next(s for s in bad if len(_cited(s["text"])) == 1)
    n = len(bad) - 1
    more = f"; they marked {NUMBERS.get(n, n)} other sentence{'s' if n != 1 else ''} too" if n else ""
    quote = _clip(first["text"].lstrip(" .;,"), 220)
    if rid not in HAGRID_NOTES:
        raise KeyError(f"EJ-1: add a note for HAGRID {rid}: {quote}")
    return f'HAGRID\'s annotators judged "{quote}" not supported by the passage it cites{more}. {HAGRID_NOTES[rid]}'


def _begin_records():
    out = []
    for split in ("dev", "test"):
        with open(SOURCE_DIR / f"begin/begin_{split}_wow.tsv", newline="") as f:
            for i, x in enumerate(csv.DictReader(f, delimiter="\t")):
                out.append((f"wow-{split}-{i}", x))
    return out


def _overlap(x):
    known = set(_words(x["knowledge"]))
    words = _words(x["response"])
    return sum(w in known for w in words) / max(1, len(words))


def _begin():
    pool = collections.defaultdict(list)
    for rid, x in _begin_records():
        gold = BEGIN_LABELS.get(x["begin_label"])
        text = " ".join((x["knowledge"], x["message"], x["response"]))
        if not gold or f"begin-{rid}" in EXCLUDE or len(_words(x["response"])) < BEGIN_MIN_WORDS \
                or not BEGIN_OVERLAP[0] <= _overlap(x) <= BEGIN_OVERLAP[1] \
                or SENSITIVE.search(text) or CONTACT.search(x["message"] + " " + x["response"]):
            continue
        pool[gold].append((rid, x))
    chosen, used_knowledge = [], set()
    for gold in ("supported", "not_supported"):                        # scarcer label first
        cands = sorted(pool[gold], key=lambda t: rank(f"begin-{t[0]}"))
        used = collections.Counter()
        for _ in range(BEGIN_PER_LABEL):
            cands = [t for t in cands if " ".join(_words(t[1]["knowledge"])) not in used_knowledge]
            pick = min(cands, key=lambda t: used[t[1]["model_name"]])
            used_knowledge.add(" ".join(_words(pick[1]["knowledge"])))
            used[pick[1]["model_name"]] += 1
            chosen.append((gold, pick))
    return chosen


# ----------------------------------------------------------------------------------------------------------- EJ-2

MTB = dict(dataset_id="mt-bench-human", dataset="MT-Bench human judgments", license="CC BY 4.0",
           url="https://huggingface.co/datasets/lmsys/mt_bench_human_judgments",
           citation="Zheng et al., Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena, NeurIPS 2023 Datasets and "
                    "Benchmarks.")
MTB_MIN_JUDGES = 2
MTB_MAX_RESPONSE = 3000
MTB_PER_CATEGORY = 4
MTB_CATEGORIES = {"writing": range(81, 91), "roleplay": range(91, 101), "reasoning": range(101, 111),
                  "math": range(111, 121), "extraction": range(131, 141), "stem": range(141, 151),
                  "humanities": range(151, 161)}                      # coding (121-130) is excluded
MTB_EXCLUDED_QUESTIONS = {91}
MTB_EXCLUDED_MODELS = {"llama-13b"}
MTB_MODELS = {"gpt-4": "GPT-4", "gpt-3.5-turbo": "GPT-3.5", "claude-v1": "Claude-v1",
              "vicuna-13b-v1.2": "Vicuna-13B", "alpaca-13b": "Alpaca-13B", "llama-13b": "LLaMA-13B"}

# For each sampled pair, keyed by row record id: a neutral subject for the title and one sentence saying why the
# preferred response is better, written for readers (the label itself is the MT-Bench judges'). In the sentence,
# {W} is the preferred response's letter and {L} the other's. The build fails if a sampled pair lacks one.
MTB_NOTES = {
    "q81-alpaca-13b-vs-gpt-3.5-turbo": (
        "travel blog post about Hawaii",
        "{W} is an engaging post that describes each cultural experience and attraction (the Polynesian Cultural "
        "Center, the North Shore, Pearl Harbor, local food); {L} is one short paragraph that only names them."),
    "q88-claude-v1-vs-vicuna-13b-v1.2": (
        "opening paragraph about time travel",
        "{W} shows the discovery through concrete details (a faded room, an old phone, a date five years back); {L} "
        "states the premise in general terms."),
    "q89-alpaca-13b-vs-claude-v1": (
        "four headlines on bio-energy",
        "{W}'s four headlines are catchy and each addresses the ethics (sustainable waste sources); {L}'s are "
        "generic, and only one mentions ethics."),
    "q90-alpaca-13b-vs-gpt-3.5-turbo": (
        "correcting grammar in one paragraph",
        "{W} fixes the errors; {L} leaves many in place (\"where is her purse\", \"ain't no sure\", \"didn't "
        "heard\", \"did you found\")."),
    "q92-claude-v1-vs-gpt-3.5-turbo": (
        "Sheldon's opinion on hand dryers",
        "{W} answers in Sheldon's emphatic, opinionated voice; {L} gives a bland, balanced answer that doesn't sound "
        "like the character."),
    "q97-gpt-3.5-turbo-vs-gpt-4": (
        "maths teacher explaining probability",
        "{W} teaches step by step, as the role asks: the formula, two worked examples and links to resources; {L} "
        "explains more briefly and lists probability types without examples."),
    "q99-gpt-3.5-turbo-vs-vicuna-13b-v1.2": (
        "rhyming proof that root 2 is irrational",
        "{W} gives an actual proof in rhyme (p/q in lowest terms leads to both being even), though longer than ten "
        "lines; {L} proves nothing and wrongly says the decimal can't be found."),
    "q100-alpaca-13b-vs-vicuna-13b-v1.2": (
        "100-year-old tree facing deforesters",
        "{W} answers in character as the tree, as asked; {L} steps out of the role to say it is an AI language model."),
    "q102-alpaca-13b-vs-gpt-4": (
        "where the White House is",
        "{W} sees the trick and says the White House is in Washington, D.C.; {L} places it among the three "
        "buildings described."),
    "q106-gpt-4-vs-vicuna-13b-v1.2": (
        "prices of oranges, apples and bananas",
        "{W}'s \"true\" is right: bananas cost more than oranges, which cost more than apples; {L} says false."),
    "q108-claude-v1-vs-gpt-4": (
        "odd word out among car terms",
        "{W} picks \"car\", the whole of which the other three are parts; {L} picks \"tyre\" with a muddled reason."),
    "q110-alpaca-13b-vs-claude-v1": (
        "which recess situation to report",
        "{W} picks (c), the girls surrounding another girl and taking her backpack, and explains why; {L} picks "
        "the girl reading alone, which shows no sign of bullying."),
    "q112-alpaca-13b-vs-gpt-4": (
        "startup's two-year software spending",
        "{W}'s $12,000 ($8,000 + $4,000) is right; {L}'s $16,000 is wrong."),
    "q115-claude-v1-vs-gpt-3.5-turbo": (
        "passengers who boarded at the terminal",
        "{W}'s 38 is right (x/2 + 6 = 25); {L} sets up the same equation and then solves it wrongly (50)."),
    "q118-gpt-3.5-turbo-vs-vicuna-13b-v1.2": (
        "remainder of twice the number divided by 4",
        "{W}'s 0 is right (2x = 20a + 8); {L}'s algebra goes wrong and gives 4."),
    "q120-gpt-3.5-turbo-vs-gpt-4": (
        "value of f(2)",
        "{W}'s f(2) = 32 - 18 - 14 = 0 is right; {L} makes an arithmetic slip and says 14."),
    "q131-claude-v1-vs-vicuna-13b-v1.2": (
        "rating three movie reviews",
        "{W}'s [5, 1, 3] matches the reviews (phenomenal, worst, okay); {L} rates the glowing review 3 and the "
        "neutral one 2."),
    "q137-alpaca-13b-vs-vicuna-13b-v1.2": (
        "named entities in news article",
        "{W} puts the three people, Faraday, Daimler AG and Berlin in the right groups (it misses Volkswagen); {L} "
        "lists two of the people as organisations."),
    "q139-claude-v1-vs-gpt-4": (
        "variable names from three equations",
        "{W} returns valid JSON with one list per equation; {L}'s output is not valid JSON (variable lists as keys) "
        "and counts the function comb as a variable."),
    "q140-gpt-4-vs-vicuna-13b-v1.2": (
        "monthly high and low closing prices",
        "{W} returns the requested CSV with the right values; {L} writes buggy Python instead of extracting them."),
    "q144-claude-v1-vs-gpt-4": (
        "central dogma of molecular biology",
        "{W} covers all three processes (replication, transcription, translation) and Crick; {L} leaves out "
        "replication."),
    "q147-gpt-3.5-turbo-vs-gpt-4": (
        "bridge in an earthquake zone",
        "{W} gives specific engineering measures (site investigation, seismic codes, isolators, ductile materials, "
        "redundancy); {L} stays general."),
    "q148-alpaca-13b-vs-gpt-4": (
        "solar water heating design",
        "{W} describes the components (collectors, tank, heat exchanger, backup, pump and controller) and a "
        "five-step workflow, as asked; {L} gives five one-line steps and no components."),
    "q150-gpt-4-vs-vicuna-13b-v1.2": (
        "Alps, Rhine, settlement and farming",
        "{W} gives three distinct, explained impacts; {L} repeats itself and claims the Rhine limited the land "
        "available for settlement."),
    "q151-alpaca-13b-vs-gpt-3.5-turbo": (
        "GDP, inflation, unemployment and policy",
        "{W} explains how fiscal and monetary policy move each indicator, with examples; {L} mostly defines the "
        "terms."),
    "q154-alpaca-13b-vs-claude-v1": (
        "drama lesson plan on the Opium Wars",
        "{W} is a timed three-day plan with specific drama activities and historical scenes; {L} is a thin outline "
        "with no timings or content."),
    "q158-claude-v1-vs-gpt-3.5-turbo": (
        "methods Socrates used",
        "{W} explains several methods (questioning, seeking definitions, challenging conventions, professed "
        "ignorance); {L} describes only the Socratic method."),
    "q159-alpaca-13b-vs-gpt-3.5-turbo": (
        "business etiquette in Japan",
        "{W} explains specific norms (bowing, two-handed business cards, punctuality, gifts, dining); {L} lists a "
        "few in one sentence."),
}


def _category(qid):
    return next((c for c, ids in MTB_CATEGORIES.items() if qid in ids), None)


def _mtbench():
    votes, first = collections.defaultdict(list), {}
    for o in range(0, MTB_TOTAL, 100):
        page = json.loads((SOURCE_DIR / f"mt-bench-human-judgments/rows/human-{o:05d}.json").read_text())
        for item in page["rows"]:
            r = item["row"]
            if r["turn"] != 1:
                continue
            key = (r["question_id"], *sorted((r["model_a"], r["model_b"])))
            votes[key].append((r["judge"], {"model_a": r["model_a"], "model_b": r["model_b"]}.get(r["winner"], "tie")))
            first.setdefault(key, r)
    pool = collections.defaultdict(list)
    for key, vs in votes.items():
        qid, m1, m2 = key
        winners = {w for _, w in vs}
        r = first[key]
        responses = {r["model_a"]: r["conversation_a"][1]["content"], r["model_b"]: r["conversation_b"][1]["content"]}
        rid = f"q{qid}-{m1}-vs-{m2}"
        if len(vs) < MTB_MIN_JUDGES or len(winners) != 1 or "tie" in winners or f"mtbench-{rid}" in EXCLUDE \
                or not _category(qid) or qid in MTB_EXCLUDED_QUESTIONS or {m1, m2} & MTB_EXCLUDED_MODELS \
                or max(map(len, responses.values())) > MTB_MAX_RESPONSE \
                or " ".join(responses[m1].split()) == " ".join(responses[m2].split()) \
                or any(SENSITIVE.search(t) for t in responses.values()):
            continue
        pool[_category(qid)].append((rid, key, winners.pop(), vs, r, responses))
    chosen, used = [], collections.Counter()
    for cat in MTB_CATEGORIES:
        cands = sorted(pool[cat], key=lambda t: rank(f"mtbench-{t[0]}"))
        used_q = set()
        for _ in range(MTB_PER_CATEGORY):
            cands = [t for t in cands if t[1][0] not in used_q]
            pick = min(cands, key=lambda t: used[t[1][1:]])
            used_q.add(pick[1][0])
            used[pick[1][1:]] += 1
            chosen.append(pick)
    return sorted(chosen, key=lambda t: rank(f"mtbench-{t[0]}"))


# --------------------------------------------------------------------------------------------------------- define

def define():
    dataset(id="hagrid", name="HAGRID", tasks=["EJ-1"], homepage="https://github.com/project-miracl/hagrid",
            license="Apache-2.0",
            license_url=f"https://github.com/project-miracl/hagrid/blob/{HAGRID_GITHUB_REV}/LICENSE",
            content="A question written by MIRACL's annotators, the English Wikipedia paragraphs they marked "
                    "relevant to it, and an answer GPT-3.5 (gpt-3.5-turbo-0301) wrote from those paragraphs, citing "
                    "them by number.",
            content_license="CC-BY-SA-3.0",
            content_terms="The paragraphs are English Wikipedia text (MIRACL's 1 February 2019 dump), licensed by "
                          f"Wikipedia's contributors under CC BY-SA 3.0 and the GFDL ({WIKIPEDIA_TERMS}); each row "
                          "links the Wikipedia articles its paragraphs come from and carries CC BY-SA 3.0. The "
                          "questions (MIRACL) and HAGRID's answers and labels are Apache-2.0.",
            labelled_by="HAGRID's four trained annotators, who judged whether each answer sentence is fully "
                        "supported by the passages it cites",
            changes="None: the question, every passage and the answer are shown in full, as the model received and "
                    "wrote them.",
            selection="English dev answers judged for attributability, filtered by the written rules in "
                      "authoring/bench/eval_judging.py (consistent and informative answers, every sentence cited, "
                      "no self-contradicting labels, no sensitive topics) and a review that left out answers a "
                      "reviewer could label either way (listed with reasons), then balanced across labels and answer "
                      "types in a fixed hash order; one answer per question.",
            citation=HAGRID["citation"],
            bibtex="""@article{kamalloo2023hagrid,
  title   = {{HAGRID}: A Human-{LLM} Collaborative Dataset for Generative Information-Seeking with Attribution},
  author  = {Kamalloo, Ehsan and Jafari, Aref and Zhang, Xinyu and Thakur, Nandan and Lin, Jimmy},
  journal = {arXiv preprint arXiv:2307.16883},
  year    = {2023}
}""")
    dataset(id="begin", name="BEGIN (Wizard of Wikipedia part)", tasks=["EJ-1"],
            homepage="https://github.com/google/BEGIN-dataset", license="CC-BY-4.0",
            license_url=f"https://github.com/google/BEGIN-dataset/blob/{BEGIN_REV}/wow/LICENSE",
            content="A crowdworker's chat message and one Wikipedia sentence from the Wizard of Wikipedia dataset, "
                    "and the reply a fine-tuned dialogue model (T5, GPT-2, DoHA or CTRL-dialog) generated from them.",
            content_license="CC-BY-SA-3.0",
            content_terms="The knowledge sentence is Wikipedia text (CC BY-SA 3.0, "
                          f"{WIKIPEDIA_TERMS}); the chat messages are Wizard of Wikipedia (Facebook, CC BY 4.0, "
                          "https://github.com/facebookresearch/ParlAI/blob/main/parlai/tasks/wizard_of_wikipedia/"
                          "LICENSE_DOCUMENTATION); BEGIN's replies and labels are CC BY 4.0 (see begin/NOTICE). "
                          "Rows carry CC BY-SA 3.0.",
            labelled_by="the majority vote of three trained BEGIN annotators",
            changes="None: the message, knowledge sentence and reply are shown verbatim, including the models' "
                    "tokenised spacing.",
            selection="Fully and not fully attributable replies of at least eight words whose word overlap with the "
                      "knowledge is between 40% and 85%, without sensitive topics and without replies a review found "
                      "mislabelled (listed with reasons), balanced across labels and the four models in a fixed hash "
                      "order; one reply per knowledge sentence.",
            citation=BEGIN["citation"],
            bibtex="""@article{dziri2022begin,
  title   = {Evaluating Attribution in Dialogue Systems: The {BEGIN} Benchmark},
  author  = {Dziri, Nouha and Rashkin, Hannah and Linzen, Tal and Reitter, David},
  journal = {Transactions of the Association for Computational Linguistics},
  volume  = {10},
  pages   = {1066--1083},
  year    = {2022},
  doi     = {10.1162/tacl_a_00506}
}""")
    dataset(id="mt-bench-human", name="MT-Bench human judgments", tasks=["EJ-2"],
            homepage="https://huggingface.co/datasets/lmsys/mt_bench_human_judgments", license="CC-BY-4.0",
            license_url=f"https://huggingface.co/datasets/lmsys/mt_bench_human_judgments/blob/{MTB_REV}/README.md",
            content="One of the 80 MT-Bench questions written by LMSYS, and the first-turn responses of two of six "
                    "models (GPT-4, GPT-3.5, Claude-v1, Vicuna-13B, Alpaca-13B, LLaMA-13B).",
            content_license="CC-BY-4.0",
            content_terms="Questions and responses are part of the CC BY 4.0 dataset; the questions are also "
                          "released in FastChat under Apache-2.0 (https://github.com/lm-sys/FastChat/blob/"
                          f"{FASTCHAT_REV}/LICENSE).",
            labelled_by="MT-Bench's expert judges (mostly graduate students with expertise in the question's topic), "
                        "unanimous across at least two judges",
            changes="Only the first turn is shown. The two responses are shown in a fixed order that puts the "
                    "preferred one first on every other row; each row records the order.",
            selection="Turn-1 pairs judged by at least two experts who all preferred the same response (no ties), "
                      "excluding coding questions, a question asking the model to be a real living person, "
                      "LLaMA-13B (a base model) and pairs a review found arguable either way (listed with reasons); "
                      "four pairs from each of seven categories in a fixed hash order.",
            citation=MTB["citation"],
            bibtex="""@inproceedings{zheng2023judging,
  title     = {Judging {LLM}-as-a-Judge with {MT}-Bench and Chatbot Arena},
  author    = {Zheng, Lianmin and Chiang, Wei-Lin and Sheng, Ying and Zhuang, Siyuan and Wu, Zhanghao and
               Zhuang, Yonghao and Lin, Zi and Li, Zhuohan and Li, Dacheng and Xing, Eric P. and Zhang, Hao and
               Gonzalez, Joseph E. and Stoica, Ion},
  booktitle = {Advances in Neural Information Processing Systems 36, Datasets and Benchmarks Track},
  year      = {2023},
  note      = {arXiv:2306.05685}
}""")

    task("EJ-1", category=CATEGORY, name="Answer grounding", ask="Is this answer supported by its sources?",
         instruction=(
             "You review answers from assistants that were given source text to work from. Each record gives the "
             "setting, the user's message, the sources the assistant was given and its answer. Judge the answer "
             "only against the sources, not against your own knowledge of the world: a claim that may be true but "
             "that the sources don't state is not supported, and neither is a personal story or opinion the "
             "assistant presents as its own. When the answer cites passages by number, each sentence must be "
             "supported by a passage it cites. Rewording is fine as long as the meaning is unchanged."),
         options={"supported": "Supported: every claim in the answer is backed by the sources.",
                  "not_supported": "Not supported: at least one claim is not backed by the sources (added, "
                                   "contradicted, or a personal story or opinion)."})
    rows = []
    for gold, (rid, r, ai, _) in _hagrid():
        a = r["answers"][ai]
        articles = sorted({q["docid"].split("#")[0] for q in r["quotes"]}, key=int)
        rows.append((f"hagrid-{rid}", dict(
            title="Wikipedia answer · " + _clip(r["query"].strip().rstrip("?"), 70), state=_hagrid_state(r, a),
            gold=gold, rationale=_hagrid_rationale(rid, r, ai, gold),
            note="Answer written by GPT-3.5 (gpt-3.5-turbo-0301).", tags=("HAGRID",),
            source={**HAGRID, "record_id": f"dev.jsonl query_id {r['query_id']}, answers[{ai}]",
                    "original_label": {"attributable": a["attributable"],
                                       "sentences": [s["attributable"] for s in a["sentences"]]},
                    "wikipedia_articles": [f"https://en.wikipedia.org/?curid={d}" for d in articles]})))
    for gold, (rid, x) in _begin():
        if rid not in BEGIN_TOPICS:
            raise KeyError(f"EJ-1: add a neutral topic for BEGIN {rid}: {_clip(x['knowledge'], 160)}")
        split, line = rid.split("-")[1:]
        rows.append((f"begin-{rid}", dict(
            title="Chat reply · " + BEGIN_TOPICS[rid][0],
            state={"setting": SETTINGS["begin"], "user_message": x["message"], "sources": [f"[1] {x['knowledge']}"],
                   "answer": x["response"]},
            gold=gold,
            rationale=BEGIN_TOPICS[rid][1] + (" BEGIN's annotators (majority of three) judged it fully attributable."
                                              if gold == "supported" else
                                              " BEGIN's annotators (majority of three) judged it not fully "
                                              "attributable."),
            note=f"Reply written by {BEGIN_MODELS[x['model_name']]}.", tags=("BEGIN",),
            source={**BEGIN, "record_id": f"wow/begin_{split}_wow.tsv, data row {line} (0-based, after the header)",
                    "original_label": x["begin_label"], "model": x["model_name"]})))
    for rid, kw in sorted(rows, key=lambda t: rank(t[0])):
        row("EJ-1", rid, **kw)

    task("EJ-2", category=CATEGORY, name="Response quality (pairwise)", ask="Which response is better?",
         instruction=(
             "You compare two assistant responses to the same user question for an evaluation team. Pick the "
             "response that follows the user's instructions and answers the question better, considering "
             "helpfulness, relevance, accuracy, depth, creativity and level of detail. Check facts and arithmetic "
             "yourself. Don't let the order of the responses or their length decide: a longer response is not "
             "better if it is wrong or misses what was asked."),
         options={"A": "Response A is better.", "B": "Response B is better."})
    for k, (rid, key, winner, vs, r, responses) in enumerate(_mtbench()):
        qid, m1, m2 = key
        loser = m2 if winner == m1 else m1
        gold = "A" if k % 2 == 0 else "B"
        shown = (winner, loser) if gold == "A" else (loser, winner)
        if rid not in MTB_NOTES:
            raise KeyError(f"EJ-2: add a topic and reason for MT-Bench {rid} ({winner} preferred): "
                           f"{_clip(r['conversation_a'][0]['content'], 160)}")
        topic, why = MTB_NOTES[rid]
        judges = len(vs)
        label = "STEM" if _category(qid) == "stem" else _category(qid)
        row("EJ-2", f"mtbench-{rid}", title=f"MT-Bench {label} question · {topic}",
            state={"question": r["conversation_a"][0]["content"], "response_A": responses[shown[0]],
                   "response_B": responses[shown[1]]},
            gold=gold, rationale=why.format(W=gold, L="B" if gold == "A" else "A"),
            note=f"Response A: {MTB_MODELS[shown[0]]}; response B: {MTB_MODELS[shown[1]]}.",
            tags=(_category(qid),),
            source={**MTB, "record_id": f"human split, question_id {qid}, turn 1, {m1} vs {m2}",
                    "original_label": {"winner": winner, "votes": [{"judge": j, "winner": w} for j, w in vs]},
                    "labelled_by": f"{judges} MT-Bench expert judges, all preferring the same response",
                    "shown_order": {"A": shown[0], "B": shown[1]},
                    "swapped": shown[0] != r["model_a"]})
