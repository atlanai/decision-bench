from __future__ import annotations

import hashlib

CASES = []
DIFFICULTY = {
    "H1": "The deciding fact is stated in one place.",
    "H2": "Needs a careful reading of wording or a close label boundary.",
    "H3": "Needs evidence combined across records, times, or policy clauses.",
    "H4": "Needs an exception, a gap in the evidence, or a confusable dependency resolved.",
}
PROVENANCE = ("Authored fictional case written in the format of a real work artifact; MIT licensed. "
              "Not a production record.")


def option_order(ident, options, kind):
    """Deterministic per-case presentation order. Scores and yes/no keep their natural order."""
    keys = list(options)
    if kind != "choice":
        return keys
    return sorted(keys, key=lambda k: hashlib.sha256(f"{ident}:{k}".encode()).hexdigest())


def question(ident, instruction, options, gold, rationale, *, ask=None, kind="choice", qid="decision"):
    q = {"id": qid, "type": kind, "instructions": instruction, "options": options,
         "option_order": option_order(ident, options, kind), "gold": gold, "rationale": rationale}
    if ask:
        q["ask"] = ask
    return q


def group(task, workload, family, instruction, options, rows, *, ask=None, policy=None, kind="choice", tags=()):
    """Add one task type.

    `ask` is the short question a reader sees in the viewer (e.g. "May the agent run this action now?").
    Each row is either a tuple (id, title, difficulty, state, gold, rationale) or a dict with those keys plus
    optional `summary` (one line describing this specific case), `why_hard` (why this case is difficult),
    `questions` (extra question dicts built with `question()`), and `tags`.
    """
    for row in rows:
        if not isinstance(row, dict):
            row = dict(zip(("id", "title", "difficulty", "state", "gold", "rationale"), row))
        ident, difficulty, state = row["id"], row["difficulty"], row["state"]
        if policy:
            state = {"policy": policy, "record": state}
        c = {"id": ident, "title": row["title"], "task": task, "workload": workload, "family": family,
             "difficulty": difficulty, "difficulty_reason": row.get("why_hard") or DIFFICULTY[difficulty],
             "split": "challenge" if difficulty == "H4" else "core", "modality": "text",
             "tags": list(tags) + list(row.get("tags", ())), "provenance": PROVENANCE,
             "state": state,
             "questions": [question(ident, instruction, options, row["gold"], row["rationale"], ask=ask, kind=kind)]
                          + list(row.get("questions", ())),
             "assets": []}
        if row.get("summary"):
            c["summary"] = row["summary"]
        CASES.append(c)


SUPPORT = {"supports": "The evidence supports the whole claim.",
           "contradicts": "The evidence contradicts at least one material part of the claim.",
           "insufficient": "The evidence neither establishes nor contradicts the whole claim."}
YESNO = {"yes": "The stated condition is established by the evidence.", "no": "The stated condition is not established by the evidence."}
