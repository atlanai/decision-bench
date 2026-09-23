"""Published metrics remain valid across Python float-summation implementations."""
import unittest

from decision_bench.results import _same_scores


class ScorePrecision(unittest.TestCase):
    def test_accepts_observed_cross_version_rounding(self):
        self.assertTrue(_same_scores({"macro_task_f1": 0.9402988755701946, "rows": 1071},
                                     {"macro_task_f1": 0.9402988755701949, "rows": 1071}))

    def test_rejects_changed_scores_counts_and_structure(self):
        expected = {"accuracy": .9, "rows": 1071, "interval": [.85, .95]}
        for changed in ({**expected, "accuracy": .900001}, {**expected, "rows": 1070},
                        {**expected, "rows": 1071.0}, {**expected, "interval": [.85]},
                        {**expected, "accuracy": float("nan")}, {**expected, "accuracy": float("inf")},
                        {**expected, "accuracy": True}, {"accuracy": .9}):
            with self.subTest(changed=changed):
                self.assertFalse(_same_scores(expected, changed))
