"""bench-v3 category 4: trace routing. See authoring/bench/__init__.py and docs/tasks.md.

TR-1  which offered function an agent should call (BFCL v3 Live), or none of them;
TR-2  which support queue owns a bank customer's chat message (BANKING77);
TR-3  which product team owns a consumer's complaint narrative (CFPB Consumer Complaint Database).

Every task walks its source records in rank() order, applies written filters, and takes the first records that
survive. Records passed over by hand are listed in a SKIP table with the reason, so the selection can be checked.
Each dataset's license, and the terms of the text inside it, are declared in `_datasets`.
"""
import csv
import json
import re

from . import dataset, task, row, rank, SOURCES as SOURCE_DIR

BFCL_BASE = "https://huggingface.co/datasets/gorilla-llm/Berkeley-Function-Calling-Leaderboard/resolve/main/"
SOURCES = [
    {"dataset": "BFCL v3 Live", "url": BFCL_BASE + "BFCL_v3_live_multiple.json", "path": "bfcl/BFCL_v3_live_multiple.json"},
    {"dataset": "BFCL v3 Live", "url": BFCL_BASE + "possible_answer/BFCL_v3_live_multiple.json",
     "path": "bfcl/possible_answer/BFCL_v3_live_multiple.json"},
    {"dataset": "BFCL v3 Live", "url": BFCL_BASE + "BFCL_v3_live_irrelevance.json",
     "path": "bfcl/BFCL_v3_live_irrelevance.json"},
    {"dataset": "BANKING77",
     "url": "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/test.csv",
     "path": "banking77/test.csv"},
]
# CFPB narratives: the public CFPB search API no longer returns narrative text, and the full CSV is ~1 GB, so we
# read 16 fixed 100-row pages of a CC0 Hugging Face mirror of the CFPB database (the "has-text" config) through
# the Hugging Face rows API. The mirror's rows are shuffled, so fixed offsets give a mix of products and years.
CFPB_MIRROR = "BEE-spoke-data/consumer-finance-complaints"
CFPB_OFFSETS = [50_000 + 100_000 * k for k in range(16)]
SOURCES += [{"dataset": "CFPB Consumer Complaint Database",
             "url": ("https://datasets-server.huggingface.co/rows?dataset=BEE-spoke-data%2Fconsumer-finance-complaints"
                     f"&config=has-text&split=train&offset={off}&length=100"),
             "path": f"cfpb/rows-{off:07d}.json"} for off in CFPB_OFFSETS]

CATEGORY = "trace-routing"


def _no_words(title, banned, where):
    low = title.lower()
    hits = [w for w in banned if w in low]
    assert not hits, f"{where}: title {title!r} contains queue words {hits}"


# ---------------------------------------------------------------------------------------------------------------
# TR-1  BFCL v3 Live: live_multiple (one expected call) and live_irrelevance (no call expected)
# ---------------------------------------------------------------------------------------------------------------
BFCL = dict(dataset_id="bfcl-v3-live",
            dataset="BFCL v3 Live (Berkeley Function-Calling Leaderboard)", license="Apache-2.0",
            url="https://huggingface.co/datasets/gorilla-llm/Berkeley-Function-Calling-Leaderboard",
            citation="Patil et al., The Berkeley Function Calling Leaderboard (BFCL): From Tool Use to Agentic "
                     "Evaluation of Large Language Models, ICML 2025.")
NONE_KEY = "none"
NONE_TEXT = "None of the offered functions can do this request."

# Written filters (both files): one user message and no system prompt; request ≤ 1,500 characters and plain ASCII
# (English); 2–8 offered functions with distinct names; one row per BFCL function set (the middle number of the id).
# live_multiple only: the ground truth is exactly one call; a function already used as an answer is not used again;
#   at most 4 rows from Schema-Guided Dialogue services (names like Flights_4_…), which dominate the file.
# live_irrelevance only: the request has at least 5 words (drops greetings and fragments) and the tools are not
#   Schema-Guided Dialogue services (BFCL marks those irrelevant because details are missing, not because no tool fits).
TR1_TOOL_ROWS, TR1_SGD_ROWS, TR1_NONE_ROWS = 18, 4, 8
SGD = re.compile(r"^[A-Z][A-Za-z]+_\d+_")

TR1_SKIP = {
    "live_multiple_998-229-0": "third row from the Instana monitoring API; two are enough for one product.",
    "live_multiple_210-91-4": "about a named individual's CV (Adriel); avoided for privacy.",
    "live_multiple_60-22-7": "request is in Indonesian.",
    "live_multiple_1026-255-0": "BFCL has the same request with a different answer (live_multiple_1035-263-0); the "
                                "two token functions are not separable.",
    "live_multiple_219-94-1": "request is garbled ('max entries per pages … from today to 15:30 to 15:32').",
    "live_multiple_991-222-0": "third row from the Instana monitoring API.",
    "live_multiple_676-163-1": "another plain weather lookup (live_multiple_960-205-0 is already used).",
    "live_irrelevance_756-267-0": "not a user request ('The user did not provide a query').",
    "live_irrelevance_489-142-0": "asks what the assistant can do; not a task.",
    "live_irrelevance_571-179-0": "reschedule_event arguably fits 'Schedule my next gym session'.",
    "live_irrelevance_255-54-0": "the Dockerfile and Kubernetes tools each fit a step of the request.",
    "live_irrelevance_268-57-3": "refers to an image that is not included.",
    "live_irrelevance_256-55-0": "the Dockerfile, Kubernetes and repo-analysis tools each fit a step of the request.",
    "live_irrelevance_517-155-0": "the request embeds its own function list in the text.",
    "live_irrelevance_247-48-2": "the UI-widget tools could be used to start collecting the booking details.",
    "live_irrelevance_282-64-0": "get_sensor_readings_latest arguably answers it.",
    "live_irrelevance_850-340-0": "a pasted Python error, not a request.",
    "live_irrelevance_798-305-2": "a pasted shell error, not a request.",
    "live_irrelevance_774-283-0": "a meeting transcript may list the user's tasks, so getMeetingTranscriptFunc arguably fits.",
    "live_irrelevance_171-25-0": "todo.add fits ('Go for shopping at 9 pm' reads as a to-do item).",
    "live_irrelevance_872-357-0": "run_ireg fits.",
    "live_irrelevance_174-27-1": "order_status_check fits; only the order id is missing.",
    "live_irrelevance_757-268-0": "not a user request ('The user did not provide a query').",
    "live_irrelevance_138-13-4": "OpenWeatherMap.get_current_weather arguably fits a weather request for a campsite.",
    "live_irrelevance_773-282-0": "not a user request ('The user did not provide a query').",
    "live_irrelevance_714-237-1": "unclear request ('Help find a convenient store 19/03/2024 12.00').",
    "live_irrelevance_803-305-7": "a pasted terminal banner, not a request.",
    "live_irrelevance_712-236-0": "get_service_providers can filter by number of jobs done, so it fits.",
}

# record id -> (title, rationale)
TR1_NOTES = {
    "live_multiple_246-110-0": ("Tool call · software inventory API",
                                "The user asks for the application's version, which get_version returns with no parameters."),
    "live_multiple_123-46-2": ("Tool call · driver-assist calculations",
                               "The request gives both vehicles' speeds, accelerations and the gap, exactly the inputs of the time-to-collision function."),
    "live_multiple_85-38-2": ("Tool call · data server setup",
                              "A Rich Data Services server for mobile telecommunications is an MTNA RDS server, not a PostgreSQL one."),
    "live_multiple_229-103-0": ("Tool call · mixed utility tools",
                                "Looking up an employee's contact details by id is what get_contact_information does."),
    "live_multiple_923-191-11": ("Tool call · home-services marketplace",
                                 "Finding a housekeeper by district, date and service is a provider search; no provider id is known yet."),
    "live_multiple_1031-259-0": ("Tool call · monitoring dashboards",
                                 "The user wants to fetch one existing dashboard, not create or delete one."),
    "live_multiple_8-4-0": ("Tool call · smart-home assistant",
                            "A cooking question is best served by the recipe search, which can filter by cuisine."),
    "live_multiple_941-195-0": ("Tool call · speaker controls", "The user asks to play a song."),
    "live_multiple_960-205-0": ("Tool call · lookup assistant",
                                "A dedicated current-weather function fits better than a general web search."),
    "live_multiple_1009-238-0": ("Tool call · website monitoring settings",
                                 "The user wants to read (not set) the website's geo mapping rules; the geo location configuration is a different setting."),
    "live_multiple_258-122-0": ("Tool call · project security API",
                                "The user wants the project's details for a name and version, not a vulnerability or violations badge."),
    "live_multiple_95-41-2": ("Tool call · data project tools",
                              "Closing and archiving a project by id is what close_project does."),
    "live_multiple_193-87-0": ("Tool call · calculator and clock", "Multiplying two numbers needs the product function, not sum."),
    "live_multiple_151-58-5": ("Tool call · IoT sensor platform",
                               "The most recent reading for each metric from each sensor is what the latest-readings function returns."),
    "live_multiple_223-97-0": ("Tool call · file, ride and vision tools", "The user asks to list a directory's contents."),
    "live_multiple_938-194-0": ("Tool call · phone assistant",
                                "The Spotify function searches for and plays the song and takes a volume, so one call does it all."),
    "live_multiple_221-95-0": ("Tool call · ride and vision tools", "The user asks to segment the objects in an image."),
    "live_multiple_243-107-4": ("Tool call · content-creation agent",
                                "Finding a recent news article needs a web search; there is no URL to scrape yet."),
    "live_multiple_503-149-0": ("Tool call · flights and trains",
                                "The user wants a one-way flight search with a seating class."),
    "live_multiple_494-148-4": ("Tool call · events and payments",
                                "The user wants options for a music event, a search rather than a ticket purchase."),
    "live_multiple_597-158-3": ("Tool call · hotel booking",
                                "No hotel has been chosen yet, so the agent must search before it can reserve."),
    "live_multiple_289-129-4": ("Tool call · therapy and movies",
                                "The user wants to find a psychologist in a city; there is no therapist to book yet."),
    "live_irrelevance_824-317-0": ("Tool call · thermodynamics calculators",
                                   "The tools calculate boiling point, gas pressure and heat; none gives a freezing point."),
    "live_irrelevance_727-243-0": ("Tool call · Jira admin API",
                                   "The tools list priorities, resolutions, fields and server info; none searches for issues."),
    "live_irrelevance_793-302-0": ("Tool call · travel and translation tools",
                                   "Weather, rides and translation cannot differentiate a function."),
    "live_irrelevance_764-274-0": ("Tool call · meeting-room booking",
                                   "The tools list users and meeting rooms; nothing lists bathrooms."),
    "live_irrelevance_273-58-0": ("Tool call · search and image generation",
                                  "The tools search the web and generate images; none writes a poem."),
    "live_irrelevance_280-62-0": ("Tool call · weather and stock quotes",
                                  "The tools give weather and stock prices; neither gives the price of water."),
    "live_irrelevance_550-169-3": ("Tool call · content tools, food order",
                                   "The tools make images, audio, files and web searches; none places a food order."),
    "live_irrelevance_761-272-0": ("Tool call · home-services lookups",
                                   "The tools find providers, profiles, promotions and past bookings; none makes a reservation."),
}


def _first_sentence(text, limit=200):
    text = " ".join(text.split())
    m = re.search(r"(?<=[a-z0-9)'\"])\.\s+(?=[A-Z])", text)
    s = text[:m.start() + 1] if m else text
    return s if len(s) <= limit else s[:limit - 1].rsplit(" ", 1)[0] + "…"


def _params(fn):
    props = fn.get("parameters", {}).get("properties", {})
    need = set(fn.get("parameters", {}).get("required", []))
    req = [p for p in props if p in need]
    opt = [p for p in props if p not in need]
    if not props:
        return "No parameters."
    parts = []
    if req:
        parts.append("required: " + ", ".join(req))
    if opt:
        parts.append("optional: " + ", ".join(opt))
    text = "; ".join(parts)
    return text[0].upper() + text[1:] + "."


def _bfcl_request(r):
    turns = r["question"]
    if len(turns) != 1 or [m["role"] for m in turns[0]] != ["user"]:
        return None
    text = turns[0][0]["content"].strip()
    if len(text) > 1500 or any(ord(c) > 127 for c in text):
        return None
    names = [f["name"] for f in r["function"]]
    if not 2 <= len(names) <= 8 or len(set(names)) != len(names):
        return None
    return text


def _tr1():
    src = SOURCE_DIR / "bfcl"
    multiple = [json.loads(line) for line in open(src / "BFCL_v3_live_multiple.json", encoding="utf-8")]
    answers = {a["id"]: a["ground_truth"]
               for a in map(json.loads, open(src / "possible_answer/BFCL_v3_live_multiple.json", encoding="utf-8"))}
    irrelevance = [json.loads(line) for line in open(src / "BFCL_v3_live_irrelevance.json", encoding="utf-8")]
    group = lambda r: r["id"].rsplit("_", 1)[1].split("-")[1]
    picked = []  # (record, request, gold)

    seen_groups, used_gold, n_tool, n_sgd = set(), set(), 0, 0
    for r in sorted(multiple, key=lambda r: rank(r["id"])):
        text = _bfcl_request(r)
        gt = answers.get(r["id"])
        if text is None or not gt or len(gt) != 1 or group(r) in seen_groups:
            continue
        gold = next(iter(gt[0]))
        if gold in used_gold:
            continue
        seen_groups.add(group(r))
        if r["id"] in TR1_SKIP:
            continue
        sgd = bool(SGD.match(gold))
        if (sgd and n_sgd >= TR1_SGD_ROWS) or (not sgd and n_tool >= TR1_TOOL_ROWS):
            continue
        assert gold in {f["name"] for f in r["function"]}, r["id"]
        used_gold.add(gold)
        n_sgd, n_tool = n_sgd + sgd, n_tool + (not sgd)
        picked.append((r, text, gold))
    assert (n_tool, n_sgd) == (TR1_TOOL_ROWS, TR1_SGD_ROWS), (n_tool, n_sgd)

    seen_groups, n_none = set(), 0
    for r in sorted(irrelevance, key=lambda r: rank(r["id"])):
        text = _bfcl_request(r)
        if text is None or group(r) in seen_groups or len(text.split()) < 5:
            continue
        if any(SGD.match(f["name"]) for f in r["function"]):
            continue
        seen_groups.add(group(r))
        if r["id"] in TR1_SKIP:
            continue
        if n_none == TR1_NONE_ROWS:
            break
        n_none += 1
        picked.append((r, text, NONE_KEY))
    assert n_none == TR1_NONE_ROWS

    for r, text, gold in picked:
        assert r["id"] in TR1_NOTES, f"TR-1: no notes for {r['id']}"
        title, rationale = TR1_NOTES[r["id"]]
        tools = [{"name": f["name"], "description": _first_sentence(f["description"]), "parameters": _params(f)}
                 for f in r["function"]]
        options = {t["name"]: t["description"] for t in tools}
        options[NONE_KEY] = NONE_TEXT
        irrelevant = gold == NONE_KEY
        row("TR-1", r["id"].replace("_", "-"), title=title, gold=gold, rationale=rationale, options=options,
            state={"user_request": text, "available_tools": tools},
            source={**BFCL, "record_id": r["id"],
                    "original_label": ("live_irrelevance: no function call expected" if irrelevant else
                                       f"ground-truth call: {gold}"),
                    "labelled_by": ("the BFCL authors, who marked the request as one no offered function should "
                                    "answer" if irrelevant else "the BFCL authors' human-verified ground truth")})


# ---------------------------------------------------------------------------------------------------------------
# TR-2  BANKING77: one bank, ten confusable queues about cards, payments, transfers and cash
# ---------------------------------------------------------------------------------------------------------------
BANKING77 = dict(dataset_id="banking77",
                 dataset="BANKING77", license="CC BY 4.0", url="https://github.com/PolyAI-LDN/task-specific-datasets",
                 citation="Casanueva et al., Efficient Intent Detection with Dual Sentence Encoders, NLP4ConvAI 2020.",
                 labelled_by="the dataset's human annotators")
# queue key -> (BANKING77 intent, one-line description)
TR2_QUEUES = {
    "card_not_arrived": ("card_arrival", "A card that was ordered or sent has not arrived yet."),
    "card_not_working": ("card_not_working", "The customer has the card but it does not work."),
    "lost_or_stolen_card": ("lost_or_stolen_card", "The card has been lost or stolen."),
    "card_payment_pending": ("pending_card_payment", "A card payment is still showing as pending."),
    "card_payment_declined": ("declined_card_payment", "A card payment was declined."),
    "transfer_not_received": ("transfer_not_received_by_recipient",
                              "A transfer went out but the recipient has not got the money."),
    "transfer_failed": ("failed_transfer", "A transfer failed or was returned."),
    "top_up_failed": ("top_up_failed", "Adding money to the account (a top-up) did not work."),
    "unknown_cash_withdrawal": ("cash_withdrawal_not_recognised", "A cash withdrawal the customer did not make."),
    "exchange_fee": ("exchange_charge", "What exchanging currency costs."),
}
TR2_PER_QUEUE = 3
# Words that would hint at a queue; neutral titles must avoid them.
TR2_BANNED = ["card", "arriv", "lost", "stole", "pending", "declin", "transfer", "top", "withdraw", "cash",
              "exchange", "fee", "fail", "work", "receiv", "payment", "recogni", "charge", "cost"]

# Test-split row (0-based) -> reason. Messages passed over in rank order because they genuinely fit two queues.
TR2_SKIP = {
    19: "card_arrival: asks 'Is it lost?', which could go to the lost-or-stolen queue.",
    387: "card_not_working: 'I can't use my card' could equally be a declined payment.",
    1814: "declined_card_payment: 'Why doesn't the card payment work' could equally be a card that does not work.",
    867: "transfer_not_received_by_recipient: 'a transaction … taking a long time to go through' could be a pending "
         "card payment.",
    866: "transfer_not_received_by_recipient: 'waiting for my transaction to go through' could be a pending card payment.",
}

# row -> (title, rationale)
TR2_NOTES = {
    3: ("In-app chat · wants an expected date", "The customer is waiting for a card and asks when it will arrive."),
    39: ("In-app chat · asks about something sent", "The card has been sent and the customer wants to track it."),
    24: ("In-app chat · still waiting, asks where", "The card has not arrived and the customer asks where it is."),
    390: ("In-app chat · suspects a fault", "The customer has the card and it seems broken."),
    380: ("In-app chat · very short complaint", "The customer has their physical card and it does not work."),
    375: ("In-app chat · one-line why question", "The customer asks why their card is not working."),
    470: ("In-app chat · asks how to report", "The customer wants to report the card lost or stolen."),
    473: ("In-app chat · worried short message", "The customer believes the card was stolen."),
    469: ("In-app chat · angry one-liner", "The customer says someone stole the card."),
    1633: ("In-app chat · shopping this morning", "A purchase made by card this morning is showing as pending."),
    1619: ("In-app chat · short status complaint", "The customer says a card payment is pending."),
    1636: ("In-app chat · asks what a term means",
           "The customer asks what a pending transaction means; no transfer is mentioned."),
    1805: ("In-app chat · problem at a shop", "The card was declined when paying in a shop."),
    1800: ("In-app chat · short message, no context", "The customer says the card was declined."),
    1828: ("In-app chat · repeated problem, asks help", "Payments on the new card keep being declined."),
    862: ("In-app chat · friend still waiting", "Money was sent to a friend hours ago and has not reached them."),
    870: ("In-app chat · other person cannot access it", "The money was sent and the recipient cannot get it."),
    854: ("In-app chat · completed, other side waiting", "The transfer was completed but the recipient has not got it."),
    2319: ("In-app chat · attempt went nowhere", "The customer tried to send money and it did not go through."),
    2294: ("In-app chat · asks why, very short", "The customer says the transfer failed."),
    2287: ("In-app chat · keeps coming back", "The transfer to a friend keeps being returned."),
    2678: ("In-app chat · informal, no punctuation", "The customer says the top-up is not working."),
    2665: ("In-app chat · asks how it went wrong", "The customer says the top-up failed."),
    2649: ("In-app chat · didn't go through, asks why", "The customer's top-up did not go through."),
    2729: ("In-app chat · app shows something unexpected", "The app shows an ATM withdrawal the customer did not make."),
    2742: ("In-app chat · unauthorised 500 pounds", "The customer did not make a £500 cash withdrawal on the account."),
    2753: ("In-app chat · statement shows something unfamiliar",
           "The statement shows an ATM withdrawal the customer did not make."),
    2773: ("In-app chat · short question about extras", "The customer asks whether exchanging currencies costs extra."),
    2779: ("In-app chat · asks what extras apply", "The customer asks about extra costs when exchanging currency."),
    2768: ("In-app chat · asks how much, in general", "The customer asks how much it costs to exchange currencies."),
}


def _tr2():
    with open(SOURCE_DIR / "banking77/test.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    options = {k: d for k, (_, d) in TR2_QUEUES.items()}
    for key, (intent, _) in TR2_QUEUES.items():
        pool = sorted((rank(r["text"]), n) for n, r in enumerate(rows) if r["category"] == intent)
        chosen = [n for _, n in pool if n not in TR2_SKIP][:TR2_PER_QUEUE]
        for n in chosen:
            assert n in TR2_NOTES, f"TR-2: no notes for row {n} ({intent})"
            title, rationale = TR2_NOTES[n]
            _no_words(title, TR2_BANNED, f"TR-2 row {n}")
            row("TR-2", f"banking77-test-{n:04d}", title=title, gold=key, rationale=rationale,
                state={"channel": "in-app chat", "message": rows[n]["text"]},
                source={**BANKING77, "record_id": f"test.csv data row {n} (0-based)", "original_label": intent})


# ---------------------------------------------------------------------------------------------------------------
# TR-3  CFPB complaint narratives: seven product teams
# ---------------------------------------------------------------------------------------------------------------
CFPB = dict(dataset_id="cfpb-complaints",
            dataset="CFPB Consumer Complaint Database", license="CC0 1.0 (public domain)",
            url="https://www.consumerfinance.gov/data-research/consumer-complaints/",
            citation="Consumer Financial Protection Bureau, Consumer Complaint Database; narratives are published "
                     "with the consumer's consent and scrubbed of personal information by the CFPB (shown as XXXX). "
                     "Read through the CC0 Hugging Face mirror BEE-spoke-data/consumer-finance-complaints.",
            labelled_by="the consumer's own product choice when filing")
# team key -> (CFPB product names across the database's history, one-line description)
TR3_TEAMS = {
    "credit_reporting": (["Credit reporting, credit repair services, or other personal consumer reports",
                          "Credit reporting or other personal consumer reports", "Credit reporting"],
                         "Credit reports and credit bureaus: wrong or unknown items, disputes, inquiries."),
    "debt_collection": (["Debt collection"], "Collectors pursuing a debt: calls, letters, validation, threats."),
    "mortgage": (["Mortgage"], "Home loans: servicing, payments, escrow, modification, foreclosure."),
    "credit_card": (["Credit card or prepaid card", "Credit card"],
                    "Credit cards: charges and disputes, fees, rewards, limits, closures."),
    "bank_account": (["Checking or savings account", "Bank account or service"],
                     "Checking and savings accounts: deposits, overdrafts, fees, opening or closing."),
    "student_loan": (["Student loan"], "Student loans: servicers, repayment plans, forgiveness, refunds."),
    "money_transfer": (["Money transfer, virtual currency, or money service", "Money transfers"],
                       "Payment apps, digital wallets, wires, and virtual-currency services."),
}
TR3_PER_TEAM = 4
TR3_MIN_CHARS, TR3_MAX_CHARS = 250, 1800
PREPAID = {"General-purpose prepaid card", "Government benefit card", "Gift card", "Payroll card"}
TR3_BANNED = ["credit", "report", "debt", "collect", "mortgage", "card", "bank", "account", "checking", "saving",
              "student", "loan", "money", "transfer", "wallet"]

# Complaint ID -> reason. Narratives passed over in rank order.
TR3_SKIP = {
    3404351: "credit_reporting: the hard pulls come from a debt buyer, so debt collection fits too.",
    7575929: "credit_reporting: sworn-statement template letter.",
    6428964: "credit_reporting: statute-citation template letter with no story.",
    6485988: "credit_reporting: identity-theft template letter followed by hundreds of XXXX redactions.",
    4762809: "debt_collection: asks for the debt to be deleted from the credit report, so credit reporting fits too.",
    5627290: "debt_collection: statute-citation template letter with no story.",
    4544122: "bank_account: a disputed card charge with no account type named; credit card fits equally.",
    2050392: "bank_account: names a private individual that the CFPB scrub missed.",
    3404238: "bank_account: the old account is now with a collector who threatens to sue; debt collection fits too.",
    4759436: "money_transfer: also a credit card refund and a checking account reversal; three teams fit.",
    6392755: "money_transfer: describes a closed business bank account; bank account fits better.",
}

# Complaint ID -> (title, rationale)
TR3_NOTES = {
    7964837: ("Consumer complaint · asks to remove unrecognised inquiries",
              "The consumer wants unauthorised inquiries removed from their credit report."),
    6055191: ("Consumer complaint · identity theft, letters ignored",
              "The consumer says Equifax will not block an identity-theft item from their report."),
    2645828: ("Consumer complaint · disputes unanswered past 30 days",
              "The complaint is about credit bureaus not investigating disputes within 30 days."),
    2647617: ("Consumer complaint · inquiries despite a verification statement",
              "The consumer blames the credit bureaus for granting inquiries despite a verification statement."),
    2494709: ("Consumer complaint · calls to the workplace continue",
              "A collector keeps calling the consumer's job after being told to stop."),
    2126521: ("Consumer complaint · calls about an unfamiliar old bill",
              "A collection agency calls twice a week about an old bill and threatens garnishment."),
    2117481: ("Consumer complaint · vet bill amount grew",
              "A collection agency is asking for more than the original vet bill and ignores requests for a breakdown."),
    4512121: ("Consumer complaint · validation letter left unanswered",
              "The consumer asked a collector to validate a medical debt and got no proper answer."),
    3123088: ("Consumer complaint · modification paperwork keeps going missing",
              "The servicer keeps losing loan-modification paperwork while threatening foreclosure."),
    4759553: ("Consumer complaint · spouse refused information on the home",
              "The home-loan servicer will not talk to the spouse still living in the house."),
    1883468: ("Consumer complaint · new servicer, unclear due date",
              "The home loan moved to a new lender and the consumer is unsure when payment is due."),
    2941241: ("Consumer complaint · payment posted 20 days late",
              "A payment to the company servicing the home loan took 20 days to post."),
    5250958: ("Consumer complaint · out-of-state charges, fraud claim denied",
              "Chase denied a fraud claim for charges on the consumer's credit card."),
    2867009: ("Consumer complaint · sign-up bonus points never came",
              "American Express has not paid a sign-up bonus after the spending requirement was met."),
    4842375: ("Consumer complaint · three store lines closed after overpayment",
              "Synchrony closed three store credit cards and gave a reason the consumer disputes."),
    3172972: ("Consumer complaint · limit lowered without notice",
              "The store card's limit was cut without notice and the consumer cannot log in to pay."),
    4513755: ("Consumer complaint · overdraft after a subscription change",
              "The credit union charged an overdraft fee because of how it processed a purchase."),
    2153243: ("Consumer complaint · opening bonus refused",
              "TD Bank refused a new checking-account bonus over an account the consumer never opened."),
    4891437: ("Consumer complaint · fees from non-recurring payments",
              "Wells Fargo charged overdraft fees on the consumer's checking account."),
    1680253: ("Consumer complaint · transactions reordered to raise fees",
              "The bank reordered transactions so that more overdraft fees applied."),
    5931580: ("Consumer complaint · forbearance-period refund delayed",
              "The consumer asked for a refund of federal student loan payments made during forbearance."),
    2648580: ("Consumer complaint · repayment plan refused after layoff",
              "Navient refused a repayment plan and reported the loan negatively during deferment."),
    3154160: ("Consumer complaint · recruited without a diploma",
              "The consumer took out loans for a college they left and asks how to recoup them."),
    7931820: ("Consumer complaint · automatic payments not processed",
              "Nelnet keeps failing to process the consumer's automatic student loan payments."),
    5793286: ("Consumer complaint · refund cashed out by a thief",
              "Cash App let a thief cash out a refund after the consumer reported the card stolen."),
    2746998: ("Consumer complaint · rent payment stuck after deactivation",
              "A payment app is holding money a friend sent and has deactivated the account."),
    4515260: ("Consumer complaint · under review for months, no answers",
              "Coinbase has held the consumer's account in review for months."),
    2791756: ("Consumer complaint · locked out after a laptop theft",
              "The consumer cannot get funds out of a Coinbase wallet after losing access."),
}


def _tr3():
    records = []
    for off in CFPB_OFFSETS:
        page = json.loads((SOURCE_DIR / f"cfpb/rows-{off:07d}.json").read_text(encoding="utf-8"))
        assert not any(r["truncated_cells"] for r in page["rows"]), off
        records += [r["row"] for r in page["rows"]]
    options = {k: d for k, (_, d) in TR3_TEAMS.items()}
    for key, (products, _) in TR3_TEAMS.items():
        pool = [r for r in records if r["Product"] in products and r["Sub-product"] not in PREPAID
                and TR3_MIN_CHARS <= len((r["Consumer complaint narrative"] or "").strip()) <= TR3_MAX_CHARS]
        pool.sort(key=lambda r: rank(r["Complaint ID"]))
        chosen = [r for r in pool if r["Complaint ID"] not in TR3_SKIP][:TR3_PER_TEAM]
        assert len(chosen) == TR3_PER_TEAM, key
        for r in chosen:
            cid = r["Complaint ID"]
            assert cid in TR3_NOTES, f"TR-3: no notes for complaint {cid} ({key})"
            title, rationale = TR3_NOTES[cid]
            _no_words(title, TR3_BANNED, f"TR-3 complaint {cid}")
            label = r["Product"] + (f" / {r['Sub-product']}" if r["Sub-product"] else "")
            row("TR-3", f"cfpb-{cid}", title=title, gold=key, rationale=rationale,
                state={"channel": "CFPB complaint form", "date_received": r["Date received"],
                       "narrative": r["Consumer complaint narrative"].strip()},
                source={**CFPB, "record_id": f"Complaint ID {cid}", "original_label": label})


def _datasets():
    dataset(id="bfcl-v3-live", name="BFCL v3 Live (Berkeley Function-Calling Leaderboard)", tasks=["TR-1"],
            homepage="https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard",
            license="Apache-2.0",
            license_url="https://huggingface.co/datasets/gorilla-llm/Berkeley-Function-Calling-Leaderboard/blob/"
                        "61fc0608cfd831fcfbbaa676ebdfef0ed963eeda/README.md",
            content="User requests and function definitions that users and partners sent to BFCL's hosted "
                    "function-calling endpoint in 2024, cleaned up by the BFCL authors.",
            content_license="Apache-2.0",
            content_terms="The Hugging Face card and the GitHub repository (ShishirPatil/gorilla) are Apache-2.0. The "
                          "BFCL V2 blog (https://gorilla.cs.berkeley.edu/blogs/12_bfcl_v2_live.html) says the "
                          "queries are \"real-world user-provided data to our hosted model end-point through "
                          "partnerships, and public access on our website\", with sensitive information replaced by "
                          "generic placeholders; no other terms are stated for them.",
            labelled_by="the BFCL authors' human-verified ground truth (live_multiple) or their marking that no "
                        "offered function fits (live_irrelevance)",
            changes="Each function is shown as its name, the first sentence of its description and its parameter "
                    "names; the request is verbatim. A \"none\" option is added.",
            selection="Single-turn English requests with 2–8 offered functions, one per function set and answer, in "
                      "sha256 order: 18 tool rows, 4 Schema-Guided Dialogue rows, 8 irrelevance rows, minus the "
                      "records in TR1_SKIP.",
            citation=BFCL["citation"],
            bibtex="""@inproceedings{patil2025bfcl,
  title     = {The Berkeley Function Calling Leaderboard ({BFCL}): From Tool Use to Agentic Evaluation of Large Language Models},
  author    = {Shishir G. Patil and Huanzhi Mao and Fanjia Yan and Charlie Cheng-Jie Ji and Vishnu Suresh and Ion Stoica and Joseph E. Gonzalez},
  booktitle = {Proceedings of the 42nd International Conference on Machine Learning},
  series    = {Proceedings of Machine Learning Research},
  volume    = {267},
  pages     = {48371--48392},
  publisher = {PMLR},
  year      = {2025},
  url       = {https://proceedings.mlr.press/v267/patil25a.html}
}""")
    dataset(id="banking77", name="BANKING77", tasks=["TR-2"], homepage=BANKING77["url"], license="CC-BY-4.0",
            license_url="https://github.com/PolyAI-LDN/task-specific-datasets/blob/master/LICENSE",
            content="Short English customer-service messages about online banking, each labelled with one of 77 "
                    "intents, released by PolyAI.",
            content_license="CC-BY-4.0",
            content_terms="Written for the dataset by PolyAI (the Hugging Face card lists language_creators "
                          "\"expert-generated\"); the whole dataset is CC BY 4.0, with no other upstream terms.",
            labelled_by=BANKING77["labelled_by"],
            changes="None: messages are shown verbatim; ten intents are renamed as queue keys (TR2_QUEUES).",
            selection="Test-split messages of ten confusable intents, in sha256 order of the text, 3 per queue, "
                      "minus the rows in TR2_SKIP.",
            citation=BANKING77["citation"],
            bibtex="""@inproceedings{casanueva-etal-2020-efficient,
  title     = {Efficient Intent Detection with Dual Sentence Encoders},
  author    = {Casanueva, I{\\~n}igo and Tem{\\v{c}}inas, Tadas and Gerz, Daniela and Henderson, Matthew and Vuli{\\'c}, Ivan},
  booktitle = {Proceedings of the 2nd Workshop on Natural Language Processing for Conversational AI},
  year      = {2020},
  publisher = {Association for Computational Linguistics},
  pages     = {38--45},
  doi       = {10.18653/v1/2020.nlp4convai-1.5},
  url       = {https://aclanthology.org/2020.nlp4convai-1.5/}
}""")
    dataset(id="cfpb-complaints", name="CFPB Consumer Complaint Database", tasks=["TR-3"], homepage=CFPB["url"],
            license="CC0-1.0",
            license_url="https://huggingface.co/datasets/BEE-spoke-data/consumer-finance-complaints/blob/"
                        "088cc7308d4afc2a880f2329d08e2f7a09188ec6/README.md",
            content="Complaint narratives that US consumers wrote to the Consumer Financial Protection Bureau and "
                    "agreed to have published, with the product they chose when filing; read from a February 2024 "
                    "Hugging Face mirror (BEE-spoke-data/consumer-finance-complaints) of the CFPB database.",
            content_license="Public domain",
            content_terms="The mirror is marked CC0-1.0. The CFPB says \"Information created by the CFPB is in the "
                          "public domain\" (https://www.consumerfinance.gov/privacy/website-privacy-policy/); the "
                          "narratives are written by consumers, published only with their consent and scrubbed of "
                          "personal information by the CFPB (shown as XXXX). On 14 August 2026 the CFPB stopped "
                          "publishing narratives and said it \"considers previously published narratives to be in "
                          "the public domain for Freedom of Information Act (FOIA) purposes\" (https://www."
                          "consumerfinance.gov/about-us/newsroom/the-cfpb-to-cease-discretionary-publication-of-"
                          "complaint-narratives-and-visualizations/). No license or restriction from the consumers "
                          "themselves is known.",
            labelled_by=CFPB["labelled_by"],
            changes="None to the narrative (surrounding whitespace stripped); only the date received is kept from "
                    "the other fields.",
            selection="Narratives of 250–1,800 characters from 16 fixed 100-row pages of the mirror, in sha256 order "
                      "of the complaint id, 4 per product team, minus the complaints in TR3_SKIP.",
            citation=CFPB["citation"],
            bibtex="""@misc{cfpb_complaints,
  author       = {{Consumer Financial Protection Bureau}},
  title        = {Consumer Complaint Database},
  howpublished = {\\url{https://www.consumerfinance.gov/data-research/consumer-complaints/}},
  note         = {Narratives read from the Hugging Face mirror BEE-spoke-data/consumer-finance-complaints (February 2024)}
}""")


def define():
    _datasets()
    task("TR-1", category=CATEGORY, name="Tool selection",
         ask="Which tool should the agent call for this request?",
         instruction="Pick the one offered function the agent should call to handle the user's request. Choose "
                     "none if no offered function can do it.",
         options={"<function name>": "One of the functions offered in this row.", NONE_KEY: NONE_TEXT},
         per_row_options=True)
    task("TR-2", category=CATEGORY, name="Support queue routing",
         ask="Which team should handle this customer message?",
         instruction="Route the bank customer's chat message to the support queue that owns it.",
         options={k: d for k, (_, d) in TR2_QUEUES.items()})
    task("TR-3", category=CATEGORY, name="Complaint routing",
         ask="Which product team owns this complaint?",
         instruction="Route the consumer's complaint to the product team that owns it, using the narrative alone.",
         options={k: d for k, (_, d) in TR3_TEAMS.items()})
    _tr1()
    _tr2()
    _tr3()
