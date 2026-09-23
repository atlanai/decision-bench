"""What the model sees, and how answers are parsed and scored."""
import json
import unittest

from decision_bench.corpus import prompt, public_input, response_schema, user_message, validate
from decision_bench.scoring import normalize_answers, score

from fixtures import ROWS

CASE = {"id": "gold-must-not-leak", "title": "T", "task": "X", "category": "c", "provenance": "p",
        "state": {"text": "The request was cancelled."},
        "questions": [{"id": "q", "type": "choice", "instructions": "Which status?",
                       "options": {"cancelled": "Cancelled", "done": "Complete"},
                       "gold": "cancelled", "rationale": "SECRET_ORACLE"}]}
READER_ONLY = ("TITLE_", "PROVENANCE_", "NOTE_", "SOURCE_DATASET", "ASK_", "RATIONALE_")


class Contracts(unittest.TestCase):
    def test_public_input_is_an_allowlist(self):
        for r in ROWS:
            for sent in (json.dumps(public_input(r)), user_message(r), prompt(r)):
                for marker in READER_ONLY:
                    self.assertNotIn(marker, sent)
                self.assertNotIn('"gold"', sent)
                self.assertNotIn(r["id"], sent)
        self.assertEqual(set(public_input(ROWS[0])), {"state", "questions"})
        self.assertEqual(set(public_input(ROWS[0])["questions"][0]), {"id", "type", "instructions", "options"})

    def test_wrong_label_is_not_replaced_with_argmax(self):
        a = normalize_answers({"answers": {"q": {"label": "done", "probabilities": {"cancelled": .9, "done": .1}}}}, CASE)
        self.assertFalse(score(CASE, a)[0]["correct"])
        self.assertFalse(a["q"]["label_is_argmax"])

    def test_invalid_outputs_rejected(self):
        for probabilities in [{"cancelled": .9, "done": .9}, {"cancelled": float("nan"), "done": 0},
                              {"cancelled": 1.1, "done": -.1}, {"cancelled": 1}, {"cancelled": True, "done": 0}]:
            with self.assertRaises(ValueError):
                normalize_answers({"answers": {"q": {"label": "cancelled", "probabilities": probabilities}}}, CASE)
        for raw in [{}, {"answers": {}}, {"answers": {"q": {"label": "other", "probabilities": {"cancelled": 1, "done": 0}}}},
                    {"answers": []}, []]:
            with self.assertRaises(ValueError):
                normalize_answers(raw, CASE)

    def test_rounding_tolerance_then_normalized(self):
        a = normalize_answers({"answers": {"q": {"label": "done", "probabilities": {"cancelled": .5, "done": .51}}}}, CASE)
        self.assertAlmostEqual(sum(a["q"]["probabilities"].values()), 1)
        self.assertAlmostEqual(a["q"]["raw_probability_sum"], 1.01)

    def test_native_choice_field(self):
        a = normalize_answers({"answers": {"q": {"choice": "cancelled", "probabilities": {"cancelled": .7, "done": .3}}}},
                              CASE, "native")
        self.assertTrue(score(CASE, a)[0]["correct"])

    def test_failed_request_counts_as_incorrect(self):
        row = score(CASE, {})[0]
        self.assertFalse(row["correct"])
        self.assertNotIn("confidence", row)

    def test_brier_and_log_loss(self):
        a = normalize_answers({"answers": {"q": {"label": "cancelled", "probabilities": {"cancelled": .8, "done": .2}}}}, CASE)
        self.assertAlmostEqual(score(CASE, a)[0]["brier"], .08)
        self.assertAlmostEqual(score(CASE, a)[0]["log_loss"], .2231435513)

    def test_schema_lists_allowed_labels_in_presentation_order(self):
        schema = response_schema(ROWS[0])["properties"]["answers"]["properties"]["decision"]
        self.assertEqual(schema["properties"]["label"]["enum"], ["b", "a"])
        self.assertEqual(list(public_input(ROWS[0])["questions"][0]["options"]), ["b", "a"])

    def test_validate_rejects_unsupported_rows(self):
        validate(ROWS)
        bad = [dict(ROWS[0], assets=[{"path": "x.png"}]), dict(ROWS[0], questions=ROWS[0]["questions"] * 2),
               dict(ROWS[0], questions=[dict(ROWS[0]["questions"][0], gold="zzz")]),
               dict(ROWS[0], questions=[dict(ROWS[0]["questions"][0], type="score")]),
               dict(ROWS[0], questions=[dict(ROWS[0]["questions"][0], option_order=["a"])])]
        for case in bad:
            with self.assertRaises(AssertionError):
                validate([case])
        with self.assertRaises(AssertionError):
            validate([ROWS[0], ROWS[0]])


if __name__ == "__main__":
    unittest.main()
