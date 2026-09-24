import unittest

from decision_bench.metrics import (attempt_totals, consolidate_attempts, paired_comparison, quantile, reliability,
                                    risk_coverage, summarize, wilson)


class Metrics(unittest.TestCase):
    def test_quantile_interpolates(self):
        self.assertEqual(quantile([10, 20, 30, 40], .5), 25)
        self.assertIsNone(quantile([], .95))

    def test_wilson_matches_known_values(self):
        lo, hi = wilson(81, 100)
        self.assertAlmostEqual(lo, 0.7222, places=4)
        self.assertAlmostEqual(hi, 0.8749, places=4)
        self.assertEqual(wilson(0, 0), [None, None])

    def test_zero_errors_still_has_uncertainty(self):
        lo, hi = wilson(10, 10)
        self.assertLess(lo, 1)
        self.assertAlmostEqual(hi, 1)

    def test_ece_denominator_ignores_missing_confidence(self):
        r = reliability([{"confidence": .8, "correct": True}, {"confidence": .8, "correct": False}, {"correct": False}])
        self.assertEqual(r["valid_count"], 2)
        self.assertAlmostEqual(r["ece"], .3)

    def test_coverage_includes_unanswered_questions(self):
        r = risk_coverage([{"confidence": .9, "correct": True}, {"correct": False}])
        self.assertEqual(r[0]["coverage"], .5)

    def test_confidence_ties_kept_together(self):
        r = risk_coverage([{"confidence": .9, "correct": True}, {"confidence": .9, "correct": False}])
        self.assertTrue(all(x["accepted"] in [0, 2] for x in r))

    def test_paired_comparison_uses_shared_rows_and_task_clusters(self):
        left = [{"case_id": "a", "scores": [{"question_id": "q", "correct": True}]},
                {"case_id": "b", "scores": [{"question_id": "q", "correct": False}]}]
        right = [{"case_id": "a", "scores": [{"question_id": "q", "correct": False}]},
                 {"case_id": "missing", "scores": [{"question_id": "q", "correct": True}]}]
        result = paired_comparison(left, right, {"a": {"task": "A"}, "b": {"task": "B"}}, repetitions=50)
        self.assertEqual(result["cases"], 1)
        self.assertEqual(result["a_only_correct"], 1)
        self.assertEqual(result["accuracy_difference"], 1)
        self.assertEqual(result["cluster_bootstrap_ci95"], [1, 1])

    def test_paid_retry_and_incomplete_attempt_remain_in_run_metrics(self):
        record = {"case_id": "c", "status": "ok", "duration_ms": 10,
                  "scores": [{"question_id": "q", "gold": "a", "label": "a", "correct": True}]}
        case = {"task": "T", "category": "C", "source_kind": "real"}
        ledger = [{"attempt_id": "first", "case_id": "c", "event": "started"},
                  {"attempt_id": "first", "case_id": "c", "event": "finished", "status": "invalid_output",
                   "cost_usd": .2, "cost_basis": "test", "usage": {"input_tokens": 100}},
                  {"attempt_id": "second", "case_id": "c", "event": "started"},
                  {"attempt_id": "second", "case_id": "c", "event": "finished", "status": "ok", "cost_usd": .3,
                   "cost_basis": "test", "usage": {"input_tokens": 150}},
                  {"attempt_id": "orphan", "case_id": "c", "event": "started"}]
        m = summarize([record], {"c": case}, ledger)
        self.assertEqual((m["attempts"], m["retries"], m["attempt_errors"], m["incomplete_attempts"]), (3, 2, 1, 1))
        self.assertEqual(m["cost_usd"], .5)
        self.assertAlmostEqual(m["cost_coverage"], 2 / 3)
        self.assertEqual(m["tokens"]["input_tokens"], 250)
        self.assertEqual(m["correct"], 1)
        self.assertEqual(m["slices"]["category"][0]["wilson95"], wilson(1, 1))
        self.assertEqual(m["confusion"], {"T": {"a → a": 1}})

    def test_failed_row_is_wrong_and_an_operational_error(self):
        records = [{"case_id": "c", "status": "invalid_output", "duration_ms": 5,
                    "scores": [{"question_id": "q", "gold": "a", "label": None, "correct": False}]}]
        m = summarize(records, {"c": {"task": "T", "category": "C"}}, [])
        self.assertEqual((m["accuracy"], m["operational_errors"], m["wrong_decisions"]), (0, 1, 0))
        self.assertIsNone(m["cost_usd"])

    def test_duplicate_start_cannot_erase_completed_receipt(self):
        events = [{"attempt_id": "a", "case_id": "c", "event": "finished", "cost_usd": 0, "status": "ok"},
                  {"attempt_id": "a", "case_id": "c", "event": "started"}]
        total = attempt_totals(consolidate_attempts(events))
        self.assertEqual((total["attempts"], total["cost_coverage"], total["cost_usd"]), (1, 1, 0))

    def test_rate_limited_attempt_does_not_lower_cost_coverage(self):
        attempts = [{"attempt_id": "a", "case_id": "c", "event": "finished", "status": "429"},
                    {"attempt_id": "b", "case_id": "c", "event": "finished", "status": "ok", "cost_usd": .01,
                     "cost_basis": "provider_reported"}]
        total = attempt_totals(attempts)
        self.assertEqual((total["cost_coverage"], total["cost_usd"], total["cost_bases"]),
                         (1, .01, ["provider_reported"]))
        self.assertEqual(attempt_totals(attempts[:1])["cost_usd"], 0)

    def test_only_orphan_attempt_cost_is_unknown(self):
        total = attempt_totals([{"attempt_id": "a", "case_id": "c", "event": "started"}])
        self.assertIsNone(total["cost_usd"])
        self.assertEqual((total["cost_coverage"], total["incomplete_attempts"]), (0, 1))


if __name__ == "__main__":
    unittest.main()
