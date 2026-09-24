"""Skill improvement (SK-1, SK-2): written examples, converted from reviewed cases.

No real, labelled, redistributable data exists for diagnosing or revising agent skills, so these rows are
written examples (badged as such, MIT). They are not new scenarios: each row is converted from a case that
was blind-reviewed and adjudicated before freezing (docs/adjudication.md):

- stress-v2 families "diagnosis" and "revision", versions A and B only (C and D are neutral-edit copies of
  A and B with the same answers, so they are left out);
- baseline v2.1 tasks SI1 (skill diagnosis), SI2 (revision selection) and SI3 (improvement verification).

Conversion keeps the artifacts (SKILL.md, trace, diff, eval table) and the deciding evidence. It changes
only the layout: traces become one line per span, eval JSON becomes a table, token counts and repeated
span ids are dropped, and long bodies are shortened with an explicit "…[trimmed]" marker.

Label mapping
- SK-1: not_followed -> step_skipped, missing -> step_missing, conflicting / ambiguous -> steps_conflict,
  environment -> environment, unknown -> cant_tell.
- SK-2 (stress-v2 revision): accept -> ship, reject -> dont_ship, insufficient -> not_enough_evidence.
- SK-2 (SI3 verification): improved -> ship, regressed -> dont_ship, insufficient -> not_enough_evidence,
  no_change -> dont_ship. SI3 defines no_change as valid runs in which the target criterion is not met; the
  SK-2 instruction says a change whose counted results show the problem not fixed does not ship.
- SK-2 (SI2 selection): each row is one candidate diff opened as a PR. The only eval results are the
  failing and regression cases on main, from before the change, so no counted result exists for any
  candidate. The adjudicated correct candidate therefore maps to not_enough_evidence. A wrong candidate
  whose diff itself breaks a constraint stated in the PR maps to dont_ship. SI2-04 ("none") is used only
  through such a candidate.
"""
import json

from . import task, row, ROOT

# The 35 reviewed source cases these rows are converted from, copied from the internal stress-v2 and v2.1 drafts.
SOURCE_CASES = ROOT / "authoring/bench/skill_sources.jsonl"
TRIM = "…[trimmed]"

SK1_INSTRUCTION = (
    "An evaluator failed this agent run. You have the SKILL.md the agent loaded for the run, the request where "
    "there is one, the run's trace, any other records captured from the same systems, and the evaluator's "
    "rubric item and finding. The rubric is applied after the run and is never shown to the agent. Identify "
    "the root cause the skill owner should act on. Judge what the agent did from the trace, not from its own "
    "messages. Answer cant_tell when the captured trace does not show what the agent did, or what the tool "
    "returned, at the step that decides it, even if one cause seems more likely.")

SK1_OPTIONS = {
    "step_skipped": "The skill clearly tells the agent what to do at the step the evaluator checks, nothing else in "
                    "the skill says otherwise, it was possible, and the trace shows the agent didn't do it.",
    "step_missing": "The skill never tells the agent to take the step the evaluator checks; the agent did what the "
                    "skill said.",
    "steps_conflict": "Two parts of the skill (steps, rules, notes or the example) both apply here and point "
                      "different ways, the skill doesn't say which wins, and the agent followed the one the "
                      "evaluator disagrees with.",
    "environment": "The agent attempted what the skill required, and a tool, permission, service or data source "
                   "failed outside its control.",
    "cant_tell": "The captured trace doesn't establish which of the other causes applies.",
}

SK2_INSTRUCTION = (
    "Review this proposed change to an agent skill and decide whether it should ship. The requirements are "
    "whatever the record sets out: the items in the skill's Hard requirements section, constraints stated in "
    "the PR description, cases that must stay green, and the target and guardrails of an eval config. Count "
    "only eval results from the proposed change that meet the run rules shown with them (suite, seeds, runs, "
    "model), and judge them by the pass rule shown (a per-case rule, or the config's target and guardrails). "
    "A change ships only when counted results show the reported problem fixed and every requirement covered "
    "by at least one passing eval case or guardrail. If the diff or the counted results show a requirement "
    "broken, or the problem not fixed, it does not ship; any eval case for a requirement that fails the pass "
    "rule shows that requirement broken, even if other cases for it pass. If nothing is shown broken but the "
    "fix or some requirement has no counted passing result, there is not enough evidence.")

SK2_OPTIONS = {
    "ship": "Ship: counted results show the problem fixed, every requirement has a passing case or guardrail, "
            "and nothing in the diff breaks one.",
    "dont_ship": "Don't ship: the diff or the counted results show a requirement broken or the problem not fixed.",
    "not_enough_evidence": "Hold: nothing is shown broken, but the fix or at least one requirement has no "
                           "counted passing result.",
}


# --------------------------------------------------------------------------------------------- formatting

def _load():
    cases = {}
    for line in SOURCE_CASES.read_text().splitlines():
        if line.strip():
            c = json.loads(line)
            cases[c["id"]] = c
    return cases


def _j(v):
    return json.dumps(v, ensure_ascii=False)


def _block(label, text, indent="    "):
    lines = text.split("\n")
    return [f"{indent}{label}"] + [f"{indent}  {x}" for x in lines]


def _value(label, v, indent="    "):
    """One span attribute: JSON on one line, multi-line strings as an indented block."""
    if isinstance(v, str):
        return _block(label, v, indent) if "\n" in v else [f"{indent}{label} {v}"]
    if isinstance(v, dict):
        long = {k: x for k, x in v.items() if isinstance(x, str) and "\n" in x}
        if long:
            short = {k: (f"<{k} below>" if k in long else x) for k, x in v.items()}
            out = [f"{indent}{label} {_j(short)}"]
            for k, x in long.items():
                out += _block(f"{k}:", x, indent + "  ")
            return out
    return [f"{indent}{label} {_j(v)}"]


def _trace(t):
    """Span list -> one line per span (time, name, status, duration), with inputs and outputs underneath."""
    spans = t["spans"]
    root = spans[0]
    rid = root.get("span_id") or root.get("spanID")
    attrs = dict(root.get("attributes") or root.get("tags") or {})
    status = root.get("status", {}).get("code") if isinstance(root.get("status"), dict) else None
    ident = t.get("trace_id") or t.get("traceID")
    head = [f"trace {ident}", root.get("name") or root.get("operationName"), f"{root['duration_ms'] / 1000:.1f} s"]
    if t.get("service"):
        head.insert(1, f"service {t['service']}")
    if t.get("source"):
        head.append(t["source"])
    if status:
        head.append(status)
    out = [" · ".join(head)]
    tools = attrs.pop("agent.tools", None)
    if tools:
        out.append("tools: " + ", ".join(tools))
    out += [f"{k}: {v if isinstance(v, str) else _j(v)}" for k, v in attrs.items()]
    out.append("")
    for s in spans[1:]:
        name = (s.get("name") or s.get("operationName")).replace("tool.call ", "tool ")
        start = (s.get("start_time") or s.get("start") or s.get("startTime"))[11:23]
        a = {k: v for k, v in (s.get("attributes") or s.get("tags") or {}).items() if not k.startswith("gen_ai.")}
        if name == "skill.load":
            out.append(f"{start}   skill.load   {a['skill.name']} {a['skill.version']} "
                       f"({', '.join(a['skill.files'])})")
            continue
        code = s.get("status", {}).get("code", "") if isinstance(s.get("status"), dict) else ""
        line = f"{start}   {name}   " + (f"{code} · " if code and code != "OK" else "") + f"{s['duration_ms']:,} ms"
        parent = s.get("parent_span_id") or s.get("parentSpanID")
        if parent != rid:
            line += f"   span {s.get('span_id') or s.get('spanID')}, parent {parent}"
        out.append(line)
        for key in ("input", "args"):
            if key in a:
                out += _value("in ", a.pop(key))
        for key in ("output", "result"):
            if key in a:
                out += _value("→" if name.startswith("llm") else "out", a.pop(key))
        for k, v in a.items():
            out += _value(f"{k}:", v)
    for k, v in t.items():
        if k not in ("spans", "trace_id", "traceID", "service", "source"):
            out.append(f"{k}: {v if isinstance(v, str) else _j(v)}")
    return "\n".join(out)


def _eval_table(e):
    head = (f"{e['run']} · base {e['base']} → head {e['head']} · {e['runs_per_case']} runs per case · "
            f"seeds {e['seeds']}")
    out = [head, f"pass rule: {e['pass_rule']}"]
    if e.get("pass_rate"):
        out.append(f"pass rate: base {e['pass_rate']['base']} · head {e['pass_rate']['head']}")
    rows = [("case", "covers", "base", "head")]
    rows += [(c["case"] + (" (flaky)" if "flaky" in c.get("tags", ()) else ""), c["covers"], c["base"], c["head"])
             for c in e["cases"]]
    w = [max(len(r[i]) for r in rows) for i in range(3)]
    out.append("")
    out += [f"{r[0].ljust(w[0])}   {r[1].ljust(w[1])}   {r[2].ljust(w[2])}   {r[3]}" for r in rows]
    return "\n".join(out)


def _edit(text, edits):
    for old, new in edits:
        assert old in text, f"edit target not found: {old[:60]!r}"
        text = text.replace(old, new)
    return text


def _rubric(r):
    return f"{r['id']} · {r['text']}"


# --------------------------------------------------------------------------------------------- SK-1 rows

def _sk1_stress(c, trims=()):
    s = c["state"]
    return {
        "request": s["request"],
        "SKILL.md": s["agent_skill"].rstrip(),
        "trace": _edit(_trace(s["trace"]), trims),
        "evaluator": {"rubric": _rubric(s["evaluator_rubric"]), "finding": s["evaluator_finding"]},
    }


def _sk1_base(c, rubric, finding, extra=(), trims=()):
    s = c["state"]
    trace = s.get("trace") or s.get("trace_export")
    state = {"SKILL.md": s["skill_md"].rstrip(), "trace": _edit(_trace(trace), trims)}
    for key in extra:
        state[key] = s[key]
    state["evaluator"] = {"rubric": rubric, "finding": finding}
    return state


_ROWS_05 = (r'"rows": "[{\"gl\":\"6410\",\"name\":\"Contractors\",\"plan\":\"884000.00\",'
            r'\"actual\":\"1103512.40\"} …[5,480 chars truncated]"',
            '"rows": [{"gl": "6410", "name": "Contractors", "plan": "884000.00", "actual": "1103512.40"}, '
            + TRIM + ']')
_BODY_05B = ('"body": "Opex came in 3.8% over plan ($412,960.18), mostly contractor spend in Platform Eng (GL 6410, '
             '+$219,512.40) and a one-off audit fee booked in September instead of Q4. …[3,587 chars truncated]',
             TRIM)

SK1_STRESS = [
    # (source id, record id, title, gold, rationale, note, trims)
    ("stress-diagnosis-01-a", "stress-01a", "Report export skill · EMEA pipeline link shared before the file was done · A",
     "steps_conflict",
     "Step 3 and the example say to send the link as soon as the job is accepted, the Checks section says to share it "
     "only after checking the finished file, nothing says which wins, and the agent followed step 3.",
     "Pair with B: the same run, but here the skill's Checks section asks for the row-count check.",
     ()),
    ("stress-diagnosis-01-b", "stress-01b", "Report export skill · EMEA pipeline link shared before the file was done · B",
     "step_missing",
     "Nothing in this version of the skill asks for the file to be opened or its rows counted; the agent sent the link "
     "on acceptance exactly as step 3 says, and the row check exists only in the rubric.",
     "Pair with A: the same run; this version's Checks section is about filters, not row counts.",
     ()),
    ("stress-diagnosis-02-a", "stress-02a", "Contract packet summary · renewal note without the signed addendum · A",
     "environment",
     "The agent tried to extract the .docx addendum twice as step 2 asks, and both calls failed with a converter worker "
     "exit (code 137), so the addendum's text never reached it.",
     "Pair with B: same skill and ticket; here the agent does try to read the .docx.",
     ()),
    ("stress-diagnosis-02-b", "stress-02b", "Contract packet summary · renewal note without the signed addendum · B",
     "steps_conflict",
     "The agent skipped the .docx under the Notes rule to skip non-PDF attachments, which contradicts step 2's "
     "\"summarise every attachment\", and the skill never says which wins.",
     "Pair with A: same skill and ticket; here the agent skips the .docx without trying it.",
     ()),
    ("stress-diagnosis-03-a", "stress-03a", "Vendor bank change · AP-7781 left open after the bank update · A",
     "environment",
     "The agent called payments.verify_account as step 3 says, and the call was refused with a 403 because the API key "
     "lacks the payouts:verify scope.",
     "Pair with B: identical run, except that here the verify_account span was captured.",
     ()),
    ("stress-diagnosis-03-b", "stress-03b", "Vendor bank change · AP-7781 left open after the bank update · B",
     "cant_tell",
     "The LLM turn issued payments.verify_account, but that call's span is not in the export (the exporter reports one "
     "dropped span), so nothing shows what it returned.",
     "Pair with A: identical run, except that the verify_account span was dropped by the exporter.",
     ()),
    ("stress-diagnosis-04-a", "stress-04a", "Postmortem writer · INC-3318 page published with a Stripe key · A",
     "step_missing",
     "This version of the skill says nothing about scanning for or removing credentials; the agent quoted log lines and "
     "published as the steps describe, and the scan exists only in the rubric.",
     "Pair with B: the same run, except that B's step 3 adds a scan_secrets.py step and B loads that script with the skill.",
     ()),
    ("stress-diagnosis-04-b", "stress-04b", "Postmortem writer · INC-3318 page published with a Stripe key · B",
     "step_skipped",
     "Step 3 tells the agent to run scan_secrets.py on the draft, the script was loaded with the skill and shell.exec was "
     "available, and the trace goes from fs.write straight to publishing.",
     "Pair with A: the same run; only this version of the skill has the scan step and loads the script.",
     ()),
    ("stress-diagnosis-05-a", "stress-05a", "Finance report publisher · September variance report in the sandbox workspace · A",
     "cant_tell",
     "The create_report input and the LLM turn that issued it were over the tracer's 4,096-byte limit, so nothing shows "
     "whether the agent passed a wrong id, none, or ws_8KD2 that the API then replaced with the default.",
     "Pair with B: same run; B's tracer recorded the create_report arguments. The skill itself says the API falls back "
     "to the default workspace when the given one can't be written to, which is why the outcome alone doesn't decide it.",
     (_ROWS_05,)),
    ("stress-diagnosis-05-b", "stress-05b", "Finance report publisher · September variance report in the sandbox workspace · B",
     "step_skipped",
     "The recorded arguments show the agent passed workspace_id ws_8KD3, the sandbox, although list_workspaces returned "
     "ws_8KD2 for Finance – Shared and step 2 says to pass the exact match.",
     "Pair with A: same run; here the create_report arguments were captured.",
     (_ROWS_05, _BODY_05B)),
]


def _sk1_baseline(cases):
    rows = []
    c = cases["skill-diagnosis-01"]
    rows.append(("base-01", "skill-diagnosis-01", "Warehouse backfill · analyst told fct_orders was there while the run was queued",
                 _sk1_base(c, "dh-eval-044 · C3 · Reply only states what the run shows.",
                           "data-help-agent eval · FAIL on C3. Reply at 10:02:11 said the data was available; the "
                           "analyst queried at 10:03 and got 0 rows.",
                           extra=("airflow_dag_run", "slack_thread_after")),
                 "step_missing",
                 "Neither the steps nor the example say to wait for or check the DAG run before replying; the tools "
                 "returned normally and the run later finished successfully at 10:08:50.",
                 None))
    c = cases["skill-diagnosis-02"]
    rows.append(("base-02", "skill-diagnosis-02", "PR review bot · three inline comments on the refunds handler",
                 _sk1_base(c, "rb-eval-117 · R2 · Inline comments only on added/modified lines.",
                           "review-bot eval · FAIL on R2. Offending comment: 2291847710 (internal/refunds/handler.go, "
                           "line 131). Criteria R1, R3, R4 pass."),
                 "step_skipped",
                 "The hunk starts at new line 118 and the added lines are 123–129, so line 131 is context, and the "
                 "skill says plainly never to post an inline comment on an unchanged line.",
                 "Count the hunk lines from @@ +118: lines 118–122 are context, 123–129 are added, 130–133 are context."))
    c = cases["skill-diagnosis-03"]
    rows.append(("base-03", "skill-diagnosis-03", "Lead enrichment · Okonkwo Agritech still without firmographics after 15 minutes",
                 _sk1_base(c, "enrich-eval-209 · E1 · New company has industry, employee count and HQ country within "
                              "15 min of creation.",
                           "revops eval · FAIL on E1. Company 18842003117: all three empty at 14:33:30 UTC.",
                           extra=("clearwave_status_page",)),
                 "environment",
                 "The agent made three attempts with the 20 s and 40 s Retry-After waits and set pending_retry as step 3 "
                 "directs, and Clearwave's status page shows a Company API outage covering the run.",
                 None))
    c = cases["skill-diagnosis-04"]
    rows.append(("base-04", "skill-diagnosis-04", "PO approval routing · no Finance approver on REQ-2026-01394",
                 _sk1_base(c, "po-eval-063 · P2 · Finance approver present when required.",
                           "procurement eval · FAIL on P2. REQ-2026-01394 total USD 10,682.08; fin-approvals not in "
                           "chain."),
                 "steps_conflict",
                 "Step 3 says \"order total\", but the example treats USD 9,870.00 before tax as under the USD 10,000 "
                 "threshold, and the agent used the example's pre-tax basis for USD 9,646.00.",
                 "Baseline label: ambiguous (the step and the example disagree about which amount the threshold uses)."))
    c = cases["skill-diagnosis-05"]
    finding = c["state"]["evaluator_finding"].split(" · FAIL on criterion S1 ")
    rows.append(("base-05", "skill-diagnosis-05", "Exec scheduling · Tuesday lease meeting booked for Thursday 8 Oct",
                 _sk1_base(c, "sched-eval-031 · S1 · Meeting on the requested day, or requester confirmed another day.",
                           "ceo-office eval · FAIL on S1. " + finding[1].split("\" ", 1)[1].replace(
                               "(the Jaeger export above)", "(the Jaeger export)")),
                 "cant_tell",
                 "The root span reports 7 tool calls and 5 LLM turns over 4 minutes, but only 3 tool spans survive, two "
                 "with missing parents, and the evaluator checked for a confirmation in that same export.",
                 "Rewritten in baseline v2.1 after adjudication so that the evaluator's finding visibly rests on the "
                 "same incomplete export (docs/adjudication.md)."))
    return rows


# --------------------------------------------------------------------------------------------- SK-2 rows

def _sk2_stress(c):
    s = c["state"]
    pr = s["pull_request"]
    return {
        "pull_request": {"title": f"#{pr['number']} {pr['title']}", "author": pr["author"],
                         "description": pr["description"]},
        "diff": pr["diff"],
        f"SKILL.md ({s['skill_file']['ref']})": s["skill_file"]["content"].rstrip(),
        "eval": _eval_table(s["eval"]),
    }


SK2_STRESS = [
    ("stress-revision-01-a", "stress-01a", "Export-report PR #418 · wait for the export before saying ready · A",
     "dont_ship",
     "The new step 7 sends to everyone named in the request and the new example sends straight to an outside address, "
     "so the diff removes the confirmation HR-2 requires.",
     "Pair with B: same fix and same eval; A drops the outside-recipient confirmation, B keeps it. No eval case covers "
     "HR-2 in either."),
    ("stress-revision-01-b", "stress-01b", "Export-report PR #418 · wait for the export before saying ready · B",
     "not_enough_evidence",
     "The fix passes and HR-1 and HR-3 have passing cases, and the diff keeps the outside-recipient confirmation, but no "
     "eval case covers HR-2, so keeping it is not shown.",
     "Pair with A: here the confirmation survives in step 7 and in the example."),
    ("stress-revision-02-a", "stress-02a", "Invoice-intake PR #1187 · normalise document numbers before dedupe · A",
     "dont_ship",
     "credit_note_links_original, an HR-2 case, drops from 5/5 to 3/5 and fails the pass rule, so a hard requirement is "
     "shown broken despite the higher pass rate.",
     "Pair with B: identical diff; only the eval results differ."),
    ("stress-revision-02-b", "stress-02b", "Invoice-intake PR #1187 · normalise document numbers before dedupe · B",
     "ship",
     "The AP-1432 repro passes and every hard-requirement case passes on the head; the one case still below 5/5, "
     "handwritten_po_reference, covers no hard requirement.",
     "Pair with A: identical diff; here credit_note_links_original stays at 5/5."),
    ("stress-revision-03-a", "stress-03a", "Dashboard-report PR #256 · workspace lookup and read-back change · A",
     "ship",
     "The lookup now takes an id or an exact name match and the read-back compares against the user's request; the "
     "BIOPS-611 repro passes and HR-1, HR-2 and HR-3 all have passing cases.",
     "Pair with B: same PR text and eval results; the diffs differ."),
    ("stress-revision-03-b", "stress-03b", "Dashboard-report PR #256 · workspace lookup and read-back change · B",
     "dont_ship",
     "The diff pins every finance report to ws_4TQ9 and keeps first-result lookup elsewhere, so a Finance US request "
     "would land in the wrong workspace, breaking HR-1 even though every case passes.",
     "Pair with A: same eval results. Adjudicated: the diff alone is enough to break HR-1 (docs/adjudication.md)."),
    ("stress-revision-04-a", "stress-04a", "Capture-payment PR #733 · retry once on PSP timeout · A",
     "not_enough_evidence",
     "The retry reuses the capture key and the PAY-2207 repro, HR-1 and HR-3 cases pass, but no eval case covers HR-2, "
     "so the no-double-capture guarantee is untested.",
     "Pair with B: same eval; A's retry reuses order.capture_key, B's generates a new key."),
    ("stress-revision-04-b", "stress-04b", "Capture-payment PR #733 · retry once on PSP timeout · B",
     "dont_ship",
     "The retry sends a fresh uuid4 Idempotency-Key, which the diff itself shows breaks HR-2: a capture that succeeded "
     "behind the 504 could be captured again.",
     "Pair with A: same eval; only the retry's key differs."),
    ("stress-revision-05-a", "stress-05a", "Contract-extract PR #92 · split by page · A",
     "not_enough_evidence",
     "The last-page repro passes and HR-1 and HR-3 have passing cases, but the only HR-2 case was skipped on the head, "
     "so DOCX tracked-change handling is untested after a split change that touches DOCX.",
     "Pair with B: identical diff; here docx_tracked_changes was skipped by a CI timeout."),
    ("stress-revision-05-b", "stress-05b", "Contract-extract PR #92 · split by page · B",
     "ship",
     "The DOC-918 repro passes and every hard requirement, including the DOCX tracked-changes case for HR-2, has a "
     "passing case on the head.",
     "Pair with A: identical diff; here docx_tracked_changes ran and passed."),
]

SK2_VERIFY = [
    ("skill-verify-01", "verify-01", "invoice-extract v6 → v7 · PO numbers from the remittance block and footer",
     "ship",
     "The target goes from 4/20 to 17/20 (+65 pp, above the 25 pp bar), core stays at 36/40 pooled, and no core case "
     "loses more than one seed.",
     "Baseline label: improved."),
    ("skill-verify-02", "verify-02", "returns-reply v8 → v9 · return label and drop-off options up front",
     "dont_ship",
     "ret-h-044 fails seed 2 on the candidate and the pii guardrail allows zero failures, which outweighs the "
     "+73.3 pp target gain.",
     "Baseline label: regressed."),
    ("skill-verify-03", "verify-03", "meeting-actions v3 → v4 · action items phrased as questions",
     "dont_ship",
     "The runs are valid, but the target goes only from 6/15 to 7/15 (+6.7 pp against a 20 pp bar), so the change "
     "doesn't fix the problem it targets.",
     "Baseline label: no_change (valid evidence, target missed). Under this task's rule, results that show the problem "
     "not fixed mean don't ship."),
    ("skill-verify-04", "verify-04", "crm-dedupe v11 → v12 · domain plus fuzzy-name matching",
     "dont_ship",
     "dd-h-022 goes from 5/5 to 3/5, breaking the no-merge guardrail's max_case_drop of 1 even though pooled no-merge "
     "accuracy is unchanged.",
     "Baseline label: regressed."),
    ("skill-verify-05", "verify-05", "sentry-triage v5 → v6 · group by the top in-app frame",
     "not_enough_evidence",
     "The baseline ran on the @20250929 snapshot and the candidate on @20251001 although the config requires the same "
     "model in both arms, so the gain can't be credited to the skill.",
     "Baseline label: insufficient."),
    ("skill-verify-06", "verify-06", "expense-policy-answers v2 → v3 · per-diem from the country table",
     "not_enough_evidence",
     "The config requires 5 seeds per case and the candidate ran only seed 1, so pooled gains and per-case drops "
     "can't be computed as defined.",
     "Baseline label: insufficient."),
]

SK2_SELECT = [
    # (source id, candidate, record id, title, gold, rationale, note, extra state keys)
    ("skill-revision-01", "a", "select-01a", "sql-analyst PR #512 · fiscal quarters from dim_date · candidate A",
     "not_enough_evidence",
     "The diff routes FY quarters to the fiscal columns and keeps calendar quarters for \"Q2 2025\", breaking nothing, "
     "but the only eval results are from main before the change.",
     "Baseline SI2 answer: candidate A is the one that fixes both failing cases within the constraints. It has not "
     "been run, so under this task's rule it holds.",
     ()),
    ("skill-revision-02", "b", "select-02b", "order-status-reply PR #88 · carrier ETA wording · candidate B",
     "not_enough_evidence",
     "The diff quotes the carrier's window, explains exceptions and keeps the late-order handoff and tracking link, but "
     "no eval has run on it; the results shown are from main.",
     "Baseline SI2 answer: candidate B. Pair with candidate C, the same PR with a different diff.",
     ()),
    ("skill-revision-02", "c", "select-02c", "order-status-reply PR #88 · carrier ETA wording · candidate C",
     "dont_ship",
     "The diff deletes step 3, the late-order handoff that the PR description says must be kept and that regression "
     "case zd-eval-0290 depends on.",
     "Pair with candidate B, which keeps step 3.",
     ()),
    ("skill-revision-03", "c", "select-03c", "review-bot PR #1043 · skip generated files · candidate C",
     "not_enough_evidence",
     "The header and .gitattributes rule catches both failing files and still reviews the 1,240-line ledger file and "
     "tools/codegen (its marker is on line 41), but no eval has run on the change.",
     "Baseline SI2 answer: candidate C.",
     ("repo_gitattributes",)),
    ("skill-revision-04", "b", "select-04b", "pipeline-freshness-alerts PR #377 · fewer weekend pages · candidate B",
     "dont_ship",
     "The diff raises the paging threshold for every tier-1 table to 72 hours, against the DP-SLA-4 constraint in the PR "
     "that tier-1 tables page within 3 hours of expected arrival.",
     "Baseline SI2 answer: none of the three candidates; this row shows candidate B.",
     ("catalog_excerpt",)),
]


def _sk2_select(c, cand, extra):
    s = c["state"]
    title, _, body = s["pr"].partition("\n")
    state = {"pull_request": {"title": title, "description": body.strip()},
             "diff": s[f"candidate_{cand}"],
             "SKILL.md (main, excerpt)": s["skill_excerpt"]}
    for key in extra:
        state[key] = s[key]
    state["eval_on_main"] = "\n".join(
        ["ref: main", "", "FAILING"] + _cases_text(s["failing_cases"])
        + ["", "PASSING (regression suite)"] + _cases_text(s["regression_cases_currently_passing"]))
    return state


def _cases_text(cases):
    out = []
    for c in cases:
        c = dict(c)
        ident = c.pop("id")
        subject = next((c.pop(k) for k in ("question", "scenario", "file") if k in c), "")
        out.append(f"{ident}   {subject}".rstrip())
        for k in ("expected", "actual"):
            if k in c:
                out.append(f"    {k}: {c.pop(k)}")
        for k, v in c.items():
            if isinstance(v, str) and "\n" in v:
                out += _block(f"{k}:", v)
            else:
                out.append(f"    {k}: {v if isinstance(v, str) else _j(v)}")
    return out


def _sk2_verify(c):
    s = c["state"]
    order = ("pr", "pr_comment", "eval_config", "runs", "results", "failure_samples")
    assert set(s) <= set(order), set(s) - set(order)
    return {("pull_request" if k == "pr" else k): s[k] for k in order if k in s}


# --------------------------------------------------------------------------------------------- define

def define():
    cases = _load()
    task("SK-1", category="skill-improvement", name="Skill failure diagnosis",
         ask="Why did the skill fail on this run?", instruction=SK1_INSTRUCTION, options=SK1_OPTIONS)
    task("SK-2", category="skill-improvement", name="Skill change review",
         ask="Should this skill change ship?", instruction=SK2_INSTRUCTION, options=SK2_OPTIONS)

    for source, rid, title, gold, rationale, note, trims in SK1_STRESS:
        row("SK-1", rid, title=title, state=_sk1_stress(cases[source], trims), gold=gold, rationale=rationale,
            note=note, tags=(f"from:stress-v2/{source}",))
    for rid, source, title, state, gold, rationale, note in _sk1_baseline(cases):
        row("SK-1", rid, title=title, state=state, gold=gold, rationale=rationale, note=note,
            tags=(f"from:v2.1/{source}",))

    for source, rid, title, gold, rationale, note in SK2_STRESS:
        row("SK-2", rid, title=title, state=_sk2_stress(cases[source]), gold=gold, rationale=rationale, note=note,
            tags=(f"from:stress-v2/{source}",))
    for source, rid, title, gold, rationale, note in SK2_VERIFY:
        row("SK-2", rid, title=title, state=_sk2_verify(cases[source]), gold=gold, rationale=rationale, note=note,
            tags=(f"from:v2.1/{source}",))
    for source, cand, rid, title, gold, rationale, note, extra in SK2_SELECT:
        row("SK-2", rid, title=title, state=_sk2_select(cases[source], cand, extra), gold=gold, rationale=rationale,
            note=note, tags=(f"from:v2.1/{source}", f"candidate:{cand}"))
