"""support: consumer complaints from the CFPB Consumer Complaint Database.

SUP-1  which of seven product teams owns a consumer's complaint narrative (ported from bench-v3 TR-3 and grown
       from 4 to 5 rows per team; the 28 v3 rows are kept unchanged);
SUP-2  what the complaint is about: eight issue groups drawn from the CFPB "Issue" field that a support desk
       would route on, 4 rows each.

Both tasks read the "has-text" config of the CC0 Hugging Face mirror BEE-spoke-data/consumer-finance-complaints
through the Hugging Face rows API, in fixed 100-row pages (the mirror is shuffled, so fixed offsets give a mix of
products and years). SUP-1 reads the 16 pages bench-v3 used, so that its v3 rows survive; SUP-2 reads those and 16
more pages, and never uses a narrative that SUP-1 uses.

Written sampling rules (both tasks): narrative of 250–1,800 characters after stripping; prepaid-card sub-products
excluded; candidates walked in rank() order of the complaint id and the first that pass are taken. SUP-2 also drops,
by regex, template letters that carry no story (sworn statements, statute citations, "This is my Nth request"
identity-theft forms). Narratives passed over by hand are in SUP1_SKIP and SUP2_SKIP with the reason, so the
selection can be checked.

Not built: a third task, "How was it resolved?" (the CFPB "Company response to consumer" field), was tried and
dropped: in a blind read of 24 narratives that clearly ask for something, the recorded outcome could be called from
the narrative on only 16, and several outcomes are indefensible from the record alone (a denied auto-loan
application and a private-mortgage-insurance question both "closed with monetary relief"; identical identity-theft
template letters closed with non-monetary relief by one bureau and with an explanation by another). The outcome is
a fact about the company, not about the complaint. See the module report for details.
"""
import json
import re

from . import dataset, task, row, rank, SOURCES as SOURCE_DIR

CATEGORY = "support"
CFPB_MIRROR = "BEE-spoke-data/consumer-finance-complaints"
CFPB_OFFSETS_V3 = [50_000 + 100_000 * k for k in range(16)]      # the pages bench-v3 TR-3 read; SUP-1 uses these
CFPB_OFFSETS_MORE = [100_000 + 100_000 * k for k in range(16)]   # added for SUP-2
CFPB_OFFSETS = CFPB_OFFSETS_V3 + CFPB_OFFSETS_MORE
SOURCES = [{"dataset": "CFPB Consumer Complaint Database",
            "url": ("https://datasets-server.huggingface.co/rows?dataset=BEE-spoke-data%2Fconsumer-finance-complaints"
                    f"&config=has-text&split=train&offset={off}&length=100"),
            "path": f"cfpb/rows-{off:07d}.json"} for off in CFPB_OFFSETS]

CFPB = dict(dataset_id="cfpb-complaints",
            dataset="CFPB Consumer Complaint Database", license="CC0 1.0 (public domain)",
            url="https://www.consumerfinance.gov/data-research/consumer-complaints/",
            citation="Consumer Financial Protection Bureau, Consumer Complaint Database; narratives are published "
                     "with the consumer's consent and scrubbed of personal information by the CFPB (shown as XXXX). "
                     "Read through the CC0 Hugging Face mirror BEE-spoke-data/consumer-finance-complaints.")
MIN_CHARS, MAX_CHARS = 250, 1800
PREPAID = {"General-purpose prepaid card", "Government benefit card", "Gift card", "Payroll card"}


def _no_words(title, banned, where):
    low = title.lower()
    hits = [w for w in banned if w in low]
    assert not hits, f"{where}: title {title!r} contains answer words {hits}"


def _narrative(r):
    return (r["Consumer complaint narrative"] or "").strip()


def _records(offsets):
    records = []
    for off in offsets:
        page = json.loads((SOURCE_DIR / f"cfpb/rows-{off:07d}.json").read_text(encoding="utf-8"))
        assert not any(r["truncated_cells"] for r in page["rows"]), off
        records += [r["row"] for r in page["rows"]]
    assert len({r["Complaint ID"] for r in records}) == len(records)
    return records


def _eligible(r):
    return r["Sub-product"] not in PREPAID and MIN_CHARS <= len(_narrative(r)) <= MAX_CHARS


def _row(task_id, r, key, title, rationale, labelled_by, original_label):
    cid = r["Complaint ID"]
    row(task_id, f"cfpb-{cid}", title=title, gold=key, rationale=rationale,
        state={"channel": "CFPB complaint form", "date_received": r["Date received"], "narrative": _narrative(r)},
        source={**CFPB, "record_id": f"Complaint ID {cid}", "original_label": original_label,
                "labelled_by": labelled_by})


# ---------------------------------------------------------------------------------------------------------------
# SUP-1  seven product teams (ported from bench-v3 TR-3)
# ---------------------------------------------------------------------------------------------------------------
# team key -> (CFPB product names across the database's history, one-line description)
SUP1_TEAMS = {
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
SUP1_PER_TEAM = 5
SUP1_LABELLED_BY = "the consumer's own product choice when filing"
SUP1_BANNED = ["credit", "report", "debt", "collect", "mortgage", "card", "bank", "account", "checking", "saving",
               "student", "loan", "money", "transfer", "wallet"]

# Complaint ID -> reason. Narratives passed over in rank order (the v3 table plus three for the fifth rows).
SUP1_SKIP = {
    3404351: "credit_reporting: the hard pulls come from a debt buyer, so debt collection fits too.",
    7575929: "credit_reporting: sworn-statement template letter.",
    6428964: "credit_reporting: statute-citation template letter with no story.",
    6485988: "credit_reporting: identity-theft template letter followed by hundreds of XXXX redactions.",
    4840308: "credit_reporting: four-sentence boilerplate demand ('avoid future litigation') with no story.",
    4762809: "debt_collection: asks for the debt to be deleted from the credit report, so credit reporting fits too.",
    5627290: "debt_collection: statute-citation template letter with no story.",
    2951045: "debt_collection: asks for a discharged debt to be deleted from the credit report, so credit reporting "
             "fits too.",
    3009822: "mortgage: names no product at all; the narrative is about retaliation for earlier complaints.",
    4544122: "bank_account: a disputed card charge with no account type named; credit card fits equally.",
    2050392: "bank_account: names a private individual that the CFPB scrub missed.",
    3404238: "bank_account: the old account is now with a collector who threatens to sue; debt collection fits too.",
    4759436: "money_transfer: also a credit card refund and a checking account reversal; three teams fit.",
    6392755: "money_transfer: describes a closed business bank account; bank account fits better.",
}

# Complaint ID -> (title, rationale)
SUP1_NOTES = {
    7964837: ("Consumer complaint · asks to remove unrecognised inquiries",
              "The consumer wants unauthorised inquiries removed from their credit report."),
    6055191: ("Consumer complaint · identity theft, letters ignored",
              "The consumer says Equifax will not block an identity-theft item from their report."),
    2645828: ("Consumer complaint · disputes unanswered past 30 days",
              "The complaint is about credit bureaus not investigating disputes within 30 days."),
    2647617: ("Consumer complaint · inquiries despite a verification statement",
              "The consumer blames the credit bureaus for granting inquiries despite a verification statement."),
    7817733: ("Consumer complaint · mailed letters, no response",
              "The consumer has mailed letters to the credit bureaus about misleading information and had no "
              "response; the bureaus are the subject."),
    2494709: ("Consumer complaint · calls to the workplace continue",
              "A collector keeps calling the consumer's job after being told to stop."),
    2126521: ("Consumer complaint · calls about an unfamiliar old bill",
              "A collection agency calls twice a week about an old bill and threatens garnishment."),
    2117481: ("Consumer complaint · vet bill amount grew",
              "A collection agency is asking for more than the original vet bill and ignores requests for a breakdown."),
    4512121: ("Consumer complaint · validation letter left unanswered",
              "The consumer asked a collector to validate a medical debt and got no proper answer."),
    1517103: ("Consumer complaint · voicemail only, already discharged",
              "Focus Receivables Management keeps calling about an unnamed debt the consumer says was discharged in "
              "bankruptcy, and no one will say what it is for."),
    3123088: ("Consumer complaint · modification paperwork keeps going missing",
              "The servicer keeps losing loan-modification paperwork while threatening foreclosure."),
    4759553: ("Consumer complaint · spouse refused information on the home",
              "The home-loan servicer will not talk to the spouse still living in the house."),
    1883468: ("Consumer complaint · new servicer, unclear due date",
              "The home loan moved to a new lender and the consumer is unsure when payment is due."),
    2941241: ("Consumer complaint · payment posted 20 days late",
              "A payment to the company servicing the home loan took 20 days to post."),
    2645305: ("Consumer complaint · payments sent back after servicer change",
              "Ocwen took over the home loan, returned the consumer's cashier's checks, demands $5,900 and "
              "threatens foreclosure."),
    5250958: ("Consumer complaint · out-of-state charges, fraud claim denied",
              "Chase denied a fraud claim for charges on the consumer's credit card."),
    2867009: ("Consumer complaint · sign-up bonus points never came",
              "American Express has not paid a sign-up bonus after the spending requirement was met."),
    4842375: ("Consumer complaint · three store lines closed after overpayment",
              "Synchrony closed three store credit cards and gave a reason the consumer disputes."),
    3172972: ("Consumer complaint · limit lowered without notice",
              "The store card's limit was cut without notice and the consumer cannot log in to pay."),
    7737249: ("Consumer complaint · paid in full, charges added anyway",
              "American Express added a finance charge, a late fee and trailing interest to a card balance the "
              "consumer says was paid in full by the due date."),
    4513755: ("Consumer complaint · overdraft after a subscription change",
              "The credit union charged an overdraft fee because of how it processed a purchase."),
    2153243: ("Consumer complaint · opening bonus refused",
              "TD Bank refused a new checking-account bonus over an account the consumer never opened."),
    4891437: ("Consumer complaint · fees from non-recurring payments",
              "Wells Fargo charged overdraft fees on the consumer's checking account."),
    1680253: ("Consumer complaint · transactions reordered to raise fees",
              "The bank reordered transactions so that more overdraft fees applied."),
    6729896: ("Consumer complaint · closed, fees still unexplained",
              "The consumer's now-closed Wells Fargo account carried unexplained monthly fees and overdraft fees, "
              "which belong to a checking account."),
    5931580: ("Consumer complaint · forbearance-period refund delayed",
              "The consumer asked for a refund of federal student loan payments made during forbearance."),
    2648580: ("Consumer complaint · repayment plan refused after layoff",
              "Navient refused a repayment plan and reported the loan negatively during deferment."),
    3154160: ("Consumer complaint · recruited without a diploma",
              "The consumer took out loans for a college they left and asks how to recoup them."),
    7931820: ("Consumer complaint · automatic payments not processed",
              "Nelnet keeps failing to process the consumer's automatic student loan payments."),
    4820759: ("Consumer complaint · employment form unprocessed for months",
              "An employment certification form for loan forgiveness has sat unprocessed at AES/PHEAA, a student "
              "loan servicer, and the consumer cannot get through about their loans."),
    5793286: ("Consumer complaint · refund cashed out by a thief",
              "Cash App let a thief cash out a refund after the consumer reported the card stolen."),
    2746998: ("Consumer complaint · rent payment stuck after deactivation",
              "A payment app is holding money a friend sent and has deactivated the account."),
    4515260: ("Consumer complaint · under review for months, no answers",
              "Coinbase has held the consumer's account in review for months."),
    2791756: ("Consumer complaint · locked out after a laptop theft",
              "The consumer cannot get funds out of a Coinbase wallet after losing access."),
    4512245: ("Consumer complaint · closed for no reason, no help for months",
              "PayPal closed the consumer's account and will not help restore it; PayPal is a payment and digital "
              "wallet service."),
}


def _sup1():
    """Returns the complaint ids used, so SUP-2 can avoid them."""
    records = [r for r in _records(CFPB_OFFSETS_V3) if _eligible(r)]
    used = set()
    for key, (products, _) in SUP1_TEAMS.items():
        pool = sorted((r for r in records if r["Product"] in products), key=lambda r: rank(r["Complaint ID"]))
        chosen = [r for r in pool if r["Complaint ID"] not in SUP1_SKIP][:SUP1_PER_TEAM]
        assert len(chosen) == SUP1_PER_TEAM, key
        for r in chosen:
            cid = r["Complaint ID"]
            assert cid in SUP1_NOTES, f"SUP-1: no notes for complaint {cid} ({key})"
            title, rationale = SUP1_NOTES[cid]
            _no_words(title, SUP1_BANNED, f"SUP-1 complaint {cid}")
            label = r["Product"] + (f" / {r['Sub-product']}" if r["Sub-product"] else "")
            _row("SUP-1", r, key, title, rationale, SUP1_LABELLED_BY, label)
            used.add(cid)
    assert len(used) == len(SUP1_TEAMS) * SUP1_PER_TEAM
    return used


# ---------------------------------------------------------------------------------------------------------------
# SUP-2  eight issue groups from the CFPB "Issue" field
# ---------------------------------------------------------------------------------------------------------------
# group key -> (CFPB issue names across the database's history, one-line description)
SUP2_GROUPS = {
    "incorrect_info_on_report": (
        ["Incorrect information on your report", "Incorrect information on credit report"],
        "Something on the consumer's credit report is wrong or out of date: an item that is not theirs, a wrong "
        "status, balance or date."),
    "debt_not_owed": (
        ["Attempts to collect debt not owed", "Cont'd attempts collect debt not owed"],
        "A collector is pursuing a debt the consumer says is not owed: not theirs, already paid, discharged, or "
        "never their responsibility."),
    "collector_conduct": (
        ["Communication tactics", "Threatened to contact someone or share information improperly",
         "Took or threatened to take negative or legal action", "Taking/threatening an illegal action",
         "Improper contact or sharing of info"],
        "How a collector behaves: repeated calls, calls at work or to other people, abusive language, threats of "
        "arrest, lawsuits or garnishment."),
    "trouble_during_payment": (
        ["Trouble during payment process", "Problem when making payments"],
        "A payment on a loan or card went wrong: autopay failed, payment not posted or misapplied, escrow or fees "
        "added, or a late mark that followed."),
    "managing_an_account": (
        ["Managing an account"],
        "Using a checking or savings account: access, deposits and withdrawals, debit or ATM card problems, fees, "
        "interest, banking errors."),
    "purchase_dispute": (
        ["Problem with a purchase shown on your statement"],
        "A charge on a credit card statement the consumer disputes: goods not received, overcharged, billed for "
        "something not bought, dispute not resolved."),
    "closing_an_account": (
        ["Closing an account", "Closing your account"],
        "An account was closed, or cannot be: closed by the company without a reason, funds not returned after "
        "closing, a fee to close."),
    "struggling_to_pay": (
        ["Struggling to pay mortgage", "Struggling to repay your loan", "Struggling to pay your loan",
         "Struggling to pay your bill", "Problems when you are unable to pay", "Loan modification,collection,foreclosure"],
        "The consumer cannot afford the payments and wants help: modification, lower payment, forbearance, short "
        "sale, or a hardship request was refused."),
}
SUP2_PER_GROUP = 4
SUP2_LABELLED_BY = "the consumer's own issue choice when filing"
# Template letters carry no story; dropped by rule before ranking.
SUP2_TEMPLATE = re.compile(r"penalty of perjury|15 U\.?S\.?C|U\.S\.C\.|This is my \w+ request|"
                           r"in accordance with the Fair Credit Reporting Act|NOTICE OF PENDING LITIGATION", re.I)
SUP2_BANNED = ["report", "bureau", "incorrect", "inaccura", "debt", "collect", "owe", "call", "harass", "threat",
               "payment", "pay", "escrow", "account", "manag", "fee", "purchase", "dispute", "charge", "statement",
               "clos", "struggl", "afford", "modif", "hardship", "refund"]

# Complaint ID -> reason. Narratives passed over in rank order because a second option is arguable, the story is
# missing, or no option fits.
SUP2_SKIP = {
    3219256: "incorrect_info_on_report: paid collection accounts reappearing on the report; debt not owed fits too.",
    5931833: "incorrect_info_on_report: calls the collection 'bogus' while complaining about its date; debt not "
             "owed is arguable.",
    5887885: "incorrect_info_on_report: garbled identity-theft template ('block the noteworthy of any information').",
    4762809: "debt_not_owed: asks for the debt to be deleted from the credit report; incorrect information fits too.",
    2703360: "debt_not_owed: says only that the debt was not validated; nothing about whether it is owed.",
    3033538: "debt_not_owed: also says the collector continues to call and harass, so collector conduct is arguable.",
    2951045: "debt_not_owed: asks for a discharged debt to be deleted from the credit report; incorrect information "
             "fits too.",
    7772369: "debt_not_owed: an unanswered validation request and a derogatory item on the report; the narrative only "
             "calls the debt 'assumed', so incorrect information is arguable.",
    2532562: "collector_conduct: a demand letter that contradicts a payment agreement; no threat or contact problem "
             "is described.",
    4159266: "trouble_during_payment: a goodwill-deletion request that describes no payment problem beyond one "
             "missed payment.",
    3009822: "trouble_during_payment: names no product or payment; the narrative is about retaliation for earlier "
             "complaints.",
    3640064: "trouble_during_payment: a refused modification and a forced short sale read as struggling to pay.",
    7313432: "managing_an_account: the bank closed the new account and is holding the deposits; closing an account "
             "fits too.",
    7975430: "purchase_dispute: mostly about thirty calls from the card issuer; the disputed purchases are secondary.",
    3901783: "closing_an_account: garbled; unclear whether the demand comes from the bank or a scammer.",
    6841765: "closing_an_account: a wire that never arrived and daily fraud blocks; managing an account is arguable.",
    2770971: "closing_an_account: years of monthly fees on an idle HSA as well as a fee to close; managing an "
             "account is arguable.",
    2938196: "closing_an_account: a trustee-to-trustee transfer not processed for four months; managing an account "
             "is arguable.",
    6162058: "closing_an_account: a late grandfather's safe deposit box, not a deposit account; no option fits well.",
    1516905: "struggling_to_pay: daily calls after changing the phone number several times; collector conduct fits "
             "better.",
    3475144: "struggling_to_pay: asks for a reconveyance of a discharged second mortgage; no hardship or repayment "
             "problem is described.",
    2849997: "struggling_to_pay: asks about joining a class action against a closed school; not about repayment.",
    3505340: "struggling_to_pay: also says a collector is calling a co-worker with a similar name; collector conduct "
             "is arguable.",
    4331533: "struggling_to_pay: a goodwill letter to remove pandemic-era late marks 'reported in error'; incorrect "
             "information is arguable.",
    6109965: "struggling_to_pay: the servicer entered and damaged a late father's home before its sale; no option "
             "fits well.",
}

# Complaint ID -> (title, rationale)
SUP2_NOTES = {
    4553732: ("Consumer complaint · seven years have passed",
              "A bankruptcy more than seven years old still appears on all three credit reports; the consumer says "
              "the item is out of date."),
    2551145: ("Consumer complaint · mailed check lost, two late marks",
              "The lender reported two 30-day late payments the consumer says never happened after a mailed payment "
              "was lost and replaced; the complaint is about what the bureau shows."),
    2755469: ("Consumer complaint · resolved in my favor, balance still shows",
              "The card issuer confirmed the fraud and said the bureaus were told to remove the account, yet the "
              "credit report still shows a $2,100 balance."),
    7373791: ("Consumer complaint · dates differ from one file to another",
              "Account statuses and dates differ between the bureaus' files (paid on one, open on another, a "
              "derogatory on only one); the consumer calls the entries misleading."),
    2740207: ("Consumer complaint · award letter faxed more than once",
              "The hospital's financial assistance covered the $340 bill, but the collector refuses to honor the "
              "award letter and wants payment."),
    5011160: ("Consumer complaint · appeared out of nowhere, wrong person",
              "A collector the consumer has never heard from is pursuing $4,000 he says he does not owe; they have "
              "the wrong person."),
    7941557: ("Consumer complaint · letter arrives years after a tenant left",
              "A former tenant took over the consumer's account by posing as his wife; he says the $45 the collector "
              "now wants is not his responsibility."),
    4402032: ("Consumer complaint · everyone is baffled how they got it",
              "IQ Data is collecting and adding interest on a balance the consumer already paid through a "
              "garnishment; the creditor and its attorney say they never used IQ Data."),
    1820514: ("Consumer complaint · business line rang three times in a day",
              "A collector called the consumer's business line three times in one day and again after being asked "
              "to stop."),
    2987882: ("Consumer complaint · asked four times, still happening",
              "Ally keeps calling numbers the consumer asked it not to call, reaching other people about the debt."),
    2816973: ("Consumer complaint · two answers on the balance, then a supervisor",
              "The consumer describes a manager who was rude, refused to give her name and said 'you either pay or "
              "see what happens'."),
    2891912: ("Consumer complaint · they want a social first",
              "The collector calls the consumer's cell daily, will not describe the debt without a Social Security "
              "number, and is now said to be filing a garnishment."),
    4306568: ("Consumer complaint · bills stopped arriving at the credit union",
              "Automatic payments through a bill-pay service stopped reaching the servicer, producing late fees and "
              "a delinquency the consumer blames on the two companies."),
    4402500: ("Consumer complaint · 25 years, then mail went elsewhere",
              "Autopay on a store card stopped after the consumer's mail was redirected; she says no one told her the "
              "payment was not being made."),
    3838739: ("Consumer complaint · confusing website, then a smaller limit",
              "The consumer thought a payment had been submitted on a confusing website; it had not, and the "
              "servicer reported a 30-day late."),
    3349644: ("Consumer complaint · taxes and insurance handled directly",
              "The servicer added $260 of escrow charges for taxes and insurance the consumer already pays directly, "
              "making the account delinquent."),
    5113884: ("Consumer complaint · locked out again on a Sunday",
              "Navy Federal has again blocked the consumer's access to the account after a suspicious-activity alert, "
              "and the security department is closed until Tuesday."),
    7328811: ("Consumer complaint · pennies on the dollar",
              "The consumer says TD Bank has paid far less interest on savings balances than advertised and has not "
              "followed up."),
    2720717: ("Consumer complaint · nothing changed on my end",
              "Citibank started charging a monthly fee on a checking account after 4.5 years of waivers, $430 in "
              "total, with no change in how the consumer uses it."),
    5729689: ("Consumer complaint · phone and cards taken together",
              "Money was moved out of the consumer's Chime checking account after his phone and debit cards were "
              "stolen; Chime says no error was made."),
    2499951: ("Consumer complaint · eight weeks, nothing arrived",
              "The consumer paid $470 by card for boots that never arrived and Citi closed the dispute against her."),
    5931607: ("Consumer complaint · the same $200 every month",
              "USAA keeps adding a $200 item to each statement after a one-time credit, and charges interest when the "
              "consumer deducts it."),
    3172905: ("Consumer complaint · four swipes for one exit",
              "An airport parking lot charged the card four times for one $5 exit and Citi's dispute process demands "
              "letters and receipts."),
    2821551: ("Consumer complaint · catalogue never came",
              "The consumer paid $2,700 with a Discover card for products and a website that were never delivered "
              "and asks for the money back."),
    5076061: ("Consumer complaint · rental assistance deposit, then an email",
              "Current closed the consumer's account by email without a reason and has not returned about $15,000 "
              "that was in it."),
    7941441: ("Consumer complaint · wrong apartment number on the envelope",
              "After Citi closed the account, the check for the remaining balance went to the wrong apartment and "
              "months later the money still has not arrived."),
    3858067: ("Consumer complaint · joint owners wait on a home office",
              "Joint account holders cannot get the bank to release a late mother's CD funds; the branch is waiting "
              "on head-office approval."),
    7975433: ("Consumer complaint · five letters in the mail, no reason given",
              "Citibank closed five of the consumer's credit card accounts and refuses to say why except by mail."),
    2759407: ("Consumer complaint · co-signer and I failed the program twice",
              "The consumer and co-signer cannot afford the $1,100 monthly payment and Sallie Mae's rate-reduction "
              "program has turned them down twice."),
    2447590: ("Consumer complaint · five months skipped, then a bigger number",
              "The consumer stopped paying to qualify for a modification, and the approved modification raised the "
              "payment from $3,600 to $4,100, which he cannot afford."),
    2500094: ("Consumer complaint · between jobs for a year after graduating",
              "After deferment the consumer's cheapest payment is $1,200 a month and she asks Navient for a lower "
              "payment."),
    2721105: ("Consumer complaint · review dates keep moving, sale date does not",
              "Wells Fargo has stopped reviewing the consumer's short-sale and mortgage-assistance requests while a "
              "foreclosure sale date stands."),
}


def _sup2(exclude):
    records = [r for r in _records(CFPB_OFFSETS) if _eligible(r) and r["Complaint ID"] not in exclude
               and not SUP2_TEMPLATE.search(_narrative(r))]
    for key, (issues, _) in SUP2_GROUPS.items():
        pool = sorted((r for r in records if r["Issue"] in issues), key=lambda r: rank(r["Complaint ID"]))
        chosen = [r for r in pool if r["Complaint ID"] not in SUP2_SKIP][:SUP2_PER_GROUP]
        assert len(chosen) == SUP2_PER_GROUP, key
        for r in chosen:
            cid = r["Complaint ID"]
            assert cid in SUP2_NOTES, f"SUP-2: no notes for complaint {cid} ({key})"
            title, rationale = SUP2_NOTES[cid]
            _no_words(title, SUP2_BANNED, f"SUP-2 complaint {cid}")
            label = r["Issue"] + (f" / {r['Sub-issue']}" if r["Sub-issue"] else "")
            _row("SUP-2", r, key, title, rationale, SUP2_LABELLED_BY, label)


def _datasets():
    dataset(id="cfpb-complaints", name="CFPB Consumer Complaint Database", tasks=["SUP-1", "SUP-2"],
            homepage=CFPB["url"], license="CC0-1.0",
            license_url="https://huggingface.co/datasets/BEE-spoke-data/consumer-finance-complaints/blob/"
                        "088cc7308d4afc2a880f2329d08e2f7a09188ec6/README.md",
            content="Complaint narratives that US consumers wrote to the Consumer Financial Protection Bureau and "
                    "agreed to have published, with the product and issue they chose when filing; read from a "
                    "February 2024 Hugging Face mirror (BEE-spoke-data/consumer-finance-complaints) of the CFPB "
                    "database.",
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
            labelled_by="the consumer's own product choice (SUP-1) or issue choice (SUP-2) when filing",
            changes="None to the narrative (surrounding whitespace stripped); only the date received is kept from "
                    "the other fields. CFPB product and issue names are grouped under short team and issue keys.",
            selection="Narratives of 250–1,800 characters from fixed 100-row pages of the mirror (16 pages for "
                      "SUP-1, 32 for SUP-2), in sha256 order of the complaint id: 5 per product team and 4 per "
                      "issue group, minus template letters and the complaints in SUP1_SKIP and SUP2_SKIP; SUP-2 "
                      "never reuses a SUP-1 narrative.",
            citation=CFPB["citation"],
            bibtex="""@misc{cfpb_complaints,
  author       = {{Consumer Financial Protection Bureau}},
  title        = {Consumer Complaint Database},
  howpublished = {\\url{https://www.consumerfinance.gov/data-research/consumer-complaints/}},
  note         = {Narratives read from the Hugging Face mirror BEE-spoke-data/consumer-finance-complaints (February 2024)}
}""")


def define():
    _datasets()
    task("SUP-1", category=CATEGORY, name="Which team owns this complaint?",
         ask="Which product team owns this complaint?",
         instruction="Route the consumer's complaint to the product team that owns it, using the narrative alone.",
         options={k: d for k, (_, d) in SUP1_TEAMS.items()},
         shape="route", input_type="consumer complaint narrative", modality="text", expertise="none",
         contamination="medium", label_origin="self-declared")
    task("SUP-2", category=CATEGORY, name="What is the complaint about?",
         ask="What is this complaint about?",
         instruction="Classify the consumer's complaint by the issue it raises, using the narrative alone. Choose "
                     "the issue the consumer is complaining about, not the product involved.",
         options={k: d for k, (_, d) in SUP2_GROUPS.items()},
         shape="classify", input_type="consumer complaint narrative", modality="text", expertise="none",
         contamination="medium", label_origin="self-declared")
    used = _sup1()
    _sup2(used)
