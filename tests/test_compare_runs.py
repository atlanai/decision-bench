"""The pass rule that decides a provider review: the submitted count passes when it is not above our max + 2 sd."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / ".claude/skills/review-provider-pr/compare_runs.py"
spec = importlib.util.spec_from_file_location("compare_runs", SCRIPT)
compare_runs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compare_runs)

CELERIS_RERUNS = [1005, 1003, 1003, 1003, 1004, 1001, 1005]


class PassRule(unittest.TestCase):
    def test_a_count_above_our_range_fails(self):
        mean, sd, limit, passed = compare_runs.pass_rule(CELERIS_RERUNS, 1008)
        self.assertAlmostEqual(limit, 1007.8, places=1)
        self.assertFalse(passed)

    def test_a_count_inside_our_range_passes(self):
        self.assertTrue(compare_runs.pass_rule(CELERIS_RERUNS, 1007)[3])

    def test_identical_runs_still_allow_one_row_of_noise(self):
        mean, sd, limit, passed = compare_runs.pass_rule([1003, 1003, 1003], 1005)
        self.assertEqual((mean, sd, limit), (1003, 1.0, 1005.0))
        self.assertTrue(passed)

    def test_one_run_uses_the_floor(self):
        self.assertEqual(compare_runs.pass_rule([1003], 1006)[2:], (1005.0, False))

    def test_a_count_below_ours_is_not_inflation(self):
        self.assertTrue(compare_runs.pass_rule(CELERIS_RERUNS, 990)[3])


if __name__ == "__main__":
    unittest.main()
