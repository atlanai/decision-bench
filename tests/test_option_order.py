import json
import unittest

from authoring.common import option_order
from decision_bench.corpus import canonical, public_input, response_schema, validate


class OptionOrderTest(unittest.TestCase):
    def case(self):
        options = {"supports": "s", "contradicts": "c", "insufficient": "i"}
        return {"id": "x-01", "title": "t", "task": "EJ-1", "category": "eval-judging", "provenance": "p",
                "state": {"x": 1}, "assets": [],
                "questions": [{"id": "decision", "type": "choice", "instructions": "Classify.", "options": options,
                               "option_order": option_order("x-01", options, "choice"), "gold": "supports",
                               "rationale": "Because.", "ask": "Is the claim supported?"}]}

    def test_presentation_order_survives_canonical_json(self):
        case = json.loads(canonical(self.case()))
        order = case["questions"][0]["option_order"]
        self.assertEqual(list(public_input(case)["questions"][0]["options"]), order)
        schema = response_schema(case)["properties"]["answers"]["properties"]["decision"]
        self.assertEqual(schema["properties"]["label"]["enum"], order)
        validate([case])

    def test_order_is_deterministic_and_varies_by_case(self):
        opts = {k: k for k in "abcdef"}
        self.assertEqual(option_order("x-1", opts, "choice"), option_order("x-1", opts, "choice"))
        self.assertNotEqual(option_order("x-1", opts, "choice"), option_order("x-2", opts, "choice"))

    def test_reader_fields_are_not_sent_to_models(self):
        sent = json.dumps(public_input(self.case()))
        self.assertNotIn("Is the claim supported?", sent)
        self.assertNotIn("Because.", sent)


if __name__ == "__main__":
    unittest.main()
