"""Every provider attempt, including a retry, must pass through the pacer."""
import argparse
import unittest
from unittest.mock import patch

from decision_bench import runner
from decision_bench.errors import CallError
import fixtures
from test_runner import response


class RunnerPacingTest(unittest.TestCase):
    def test_retry_is_paced_and_limits_are_recorded(self):
        args = argparse.Namespace(model="fake-typesafe", run_id="paced-run", api_model=None,
                                  jobs=1, timeout=5, max_attempts=2, limit=1, ids=None,
                                  retry_errors=False, rpm=60.0, global_rpm=120.0)
        outcomes = [CallError("busy", retryable=True, status=429), None]

        def fake_call(model, case, timeout, api_model=None):
            error = outcomes.pop(0)
            if error:
                raise error
            return response(case)

        with fixtures.repo({"TYPESAFE_API_KEY": fixtures.FAKE_KEY}), \
                patch.object(runner.RequestPacer, "wait", return_value=0.25) as paced, \
                patch.object(runner.time, "sleep"):
            with patch.object(runner.adapters, "call", side_effect=fake_call):
                meta = runner.run(args)
            row = runner.read_jsonl(runner.runs_dir() / "paced-run/results.jsonl")[0]
        self.assertEqual(paced.call_count, 2)
        self.assertEqual(meta["executions"][-1]["rpm"], 60.0)
        self.assertEqual(meta["executions"][-1]["global_rpm"], 120.0)
        self.assertEqual(row["rate_wait_ms"], 500.0)
        self.assertEqual(row["status"], "ok")


if __name__ == "__main__":
    unittest.main()
