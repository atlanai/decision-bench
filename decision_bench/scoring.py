"""Answer parsing and per-question scoring. Exact label match is the score; probabilities feed calibration."""
from __future__ import annotations

import math


def normalize_answers(raw, case, source="verbalized"):
    """Validate a parsed response. Raises ValueError on a missing answer, wrong labels or bad probabilities.

    `source` is "verbalized" (label + probabilities), "native" (choice + probabilities),
    "native-renormalized", or "label-only" (accuracy without calibration).
    The returned label is the model's own; it is never replaced by the argmax."""
    answers = raw.get("answers", {}) if isinstance(raw, dict) else {}
    out = {}
    for q in case["questions"]:
        a = answers.get(q["id"]) if isinstance(answers, dict) else None
        if not isinstance(a, dict):
            raise ValueError(f"Missing answer: {q['id']}")
        if source == "label-only":
            label = a.get("label")
            if label not in q["options"]:
                raise ValueError(f"Wrong label: {q['id']}")
            out[q["id"]] = {"label": label, "probabilities": None,
                             "probability_source": source, "label_is_argmax": None}
            continue
        probs = a.get("probabilities", {})
        if not isinstance(probs, dict):
            raise ValueError(f"Invalid probabilities: {q['id']}")
        probs = {str(k): v for k, v in probs.items()}
        label = a.get("choice") if source == "native" else a.get("label")
        label = str(label) if label is not None else None
        abstained = source == "native-renormalized" and label is None
        if set(probs) != set(q["options"]) or (label not in q["options"] and not abstained):
            raise ValueError(f"Wrong labels: {q['id']}")
        if any(not isinstance(v, (float, int)) or isinstance(v, bool) or not math.isfinite(v) or v < 0 or v > 1
               for v in probs.values()):
            raise ValueError(f"Invalid probability: {q['id']}")
        total = sum(probs.values())
        if total == 0 or abs(total - 1) > 0.02:
            raise ValueError(f"Probability sum {total}: {q['id']}")
        norm = {k: v / total for k, v in probs.items()}
        out[q["id"]] = {"label": label, "probabilities": norm, "raw_probability_sum": total,
                        "probability_source": source,
                        "label_is_argmax": None if abstained else norm[label] >= max(norm.values()) - 1e-9}
    return out


def score_answer(gold, label, probabilities=None):
    row = {"gold": gold, "label": label, "correct": label is not None and label == gold}
    if label is not None and probabilities:
        p = probabilities
        row.update(confidence=p[label], probabilities=p,
                   brier=sum((p[k] - int(k == gold)) ** 2 for k in p),
                   log_loss=-math.log(max(p.get(gold, 0), 1e-12)))
    return row


def score(case, answers):
    rows = []
    for q in case["questions"]:
        a = answers.get(q["id"])
        row = {"question_id": q["id"], "type": q["type"],
               **score_answer(q["gold"], a["label"] if a else None, a["probabilities"] if a else None)}
        if a:
            row.update(probability_source=a["probability_source"], label_is_argmax=a["label_is_argmax"])
        rows.append(row)
    return rows
