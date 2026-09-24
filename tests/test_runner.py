"""Resume, retries and the attempt ledger, with the provider call mocked."""
import argparse
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from decision_bench import runner
from decision_bench.errors import CallError

import fixtures

ENV = {"TYPESAFE_API_KEY": fixtures.FAKE_KEY}


def args(model="fake-typesafe", **kw):
    base = dict(model=model, run_id="test-run", api_model=None, jobs=1, timeout=5, max_attempts=2, limit=None,
                ids=None, retry_errors=False)
    base.update(kw)
    return argparse.Namespace(**base)


def response(case, label="a", cost=.01):
    return {"raw": {"model": "test"}, "source": "native", "resolved_model": "test",
            "response": {"answers": {"decision": {"choice": label, "probabilities": {"a": .9, "b": .1} if label == "a"
                                                  else {"a": .1, "b": .9}}}},
            "usage": {"input_tokens": 20, "output_tokens": 3}, "cost_usd": cost, "cost_basis": "test",
            "payload": {"state": case["state"]}, "output_text": "{}"}


class Runner(unittest.TestCase):
    def test_laya_endpoint_is_frozen_and_remote_key_is_required(self):
        with fixtures.repo({"LAYA_BASE_URL": "https://api.example.com/v1"}):
            with self.assertRaises(CallError) as cm:
                runner.prepare(args(model="fake-laya"))
            self.assertEqual(cm.exception.status, "auth_missing")
        with fixtures.repo({"LAYA_BASE_URL": "http://localhost:8000/v1"}):
            _, _, cfg, run_id = runner.prepare(args(model="fake-laya", run_id=None))
            self.assertTrue(cfg["endpoint_id"].startswith("endpoint-"))
            self.assertNotIn("localhost", json.dumps(cfg))
            self.assertTrue(run_id.startswith("fake-laya-mini-"))

    def test_resume_skips_success_and_keeps_retry_attempts(self):
        with fixtures.repo(ENV) as root, patch.object(runner.time, "sleep"), \
                patch.object(runner, "git_revision", return_value={"commit": None, "dirty": False}):
            calls = [CallError("busy", retryable=True, status=429)] + [None] * 3

            def fake(model, case, timeout, api_model=None):
                outcome = calls.pop(0)
                if outcome:
                    raise outcome
                return response(case)
            with patch.object(runner.adapters, "call", side_effect=fake) as call:
                first = runner.run(args())
                self.assertEqual(call.call_count, 4)
                self.assertEqual(first["status"], "completed")
            with patch.object(runner.adapters, "call") as call:
                runner.run(args())
                call.assert_not_called()
            folder = root / "runs/test-run"
            results = runner.read_jsonl(folder / "results.jsonl")
            self.assertEqual(len(results), 3)
            r1 = next(r for r in results if r["case_id"] == "r1")
            self.assertEqual([a["status"] for a in r1["attempts"]], ["429", "ok"])
            self.assertEqual((r1["cost_coverage"], r1["known_attempt_cost_usd"]), (1, .01))
            self.assertNotIn("error", r1)
            self.assertEqual(len(runner.read_jsonl(folder / "attempts.jsonl")), 8)
            meta = json.loads((folder / "run.json").read_text())
            self.assertEqual(len(meta["executions"]), 2)
            self.assertEqual(meta["config"]["corpus_sha256"], json.loads(
                (root / "data/corpus/mini/manifest.json").read_text())["sha256"])

    def test_retry_errors_reruns_only_failed_rows(self):
        with fixtures.repo(ENV), patch.object(runner.time, "sleep"):
            with patch.object(runner.adapters, "call", side_effect=lambda m, c, t, a=None:
                              response(c) if c["id"] != "r2" else (_ for _ in ()).throw(CallError("bad", status=400))):
                self.assertEqual(runner.run(args())["status"], "completed_with_errors")
            with patch.object(runner.adapters, "call", side_effect=lambda m, c, t, a=None: response(c)) as call:
                self.assertEqual(runner.run(args(retry_errors=True))["status"], "completed")
                self.assertEqual([x.args[1]["id"] for x in call.call_args_list], ["r2"])

    def test_changed_configuration_cannot_resume(self):
        with fixtures.repo(ENV), patch.object(runner.adapters, "call", side_effect=lambda m, c, t, a=None: response(c)):
            runner.run(args())
            with self.assertRaises(ValueError) as cm:
                runner.run(args(api_model="other-model"))
            self.assertIn("api_model", str(cm.exception))
            runner.run(args(jobs=2, timeout=9))  # operational settings are not part of the frozen config

    def test_default_run_id_is_deterministic_and_marks_subsets(self):
        with fixtures.repo(ENV):
            _, _, cfg, run_id = runner.prepare(args(run_id=None))
            self.assertEqual(run_id, runner.prepare(args(run_id=None))[3])
            self.assertTrue(run_id.startswith("fake-typesafe-mini-"))
            self.assertTrue(runner.prepare(args(run_id=None, limit=1))[3].endswith("-subset"))
            self.assertNotEqual(runner.prepare(args(run_id=None, ids="r1"))[3], run_id)

    def test_price_table_fills_missing_cost(self):
        with fixtures.repo({"DECISION_BENCH_BASE_URL": "http://localhost:9/v1"}), patch.object(runner.adapters, "call",
                                                                                              side_effect=lambda m, c, t, a=None: response(c, cost=None) | {"cost_basis": "unavailable"}):
            runner.run(args(model="fake-model"))
            rows = runner.read_jsonl(runner.runs_dir() / "test-run/results.jsonl")
        self.assertEqual(rows[0]["cost_basis"], "price_table_estimate")
        self.assertAlmostEqual(rows[0]["cost_usd"], (20 * 1.0 + 3 * 2.0) / 1e6)

    def test_failed_call_usage_is_in_attempt_ledger(self):
        error = CallError("output failed", status="model_error",
                          metadata={"usage": {"input_tokens": 100, "output_tokens": 20}, "cost_usd": .02, "cost_basis": "test"})
        with fixtures.repo(ENV), patch.object(runner.adapters, "call", side_effect=error), \
                patch.object(runner.adapters, "executable", return_value="claude"):
            meta = runner.run(args(model="fake-claude", max_attempts=1))
            record = runner.read_jsonl(runner.runs_dir() / "test-run/results.jsonl")[0]
        self.assertEqual(meta["status"], "completed_with_errors")
        self.assertEqual(record["known_attempt_cost_usd"], .02)
        self.assertEqual(record["attempts"][0]["usage"]["input_tokens"], 100)
        self.assertFalse(record["scores"][0]["correct"])

    def test_unknown_ids_and_bad_run_ids_are_rejected(self):
        with fixtures.repo(ENV):
            with self.assertRaises(ValueError):
                runner.prepare(args(ids="r1,nope"))
            with self.assertRaises(ValueError):
                runner.prepare(args(run_id="../escape"))
            with self.assertRaises(ValueError):
                runner.prepare(args(model="not-configured"))

    def test_preflight_fails_before_creating_a_run(self):
        with fixtures.repo():
            for model in ("fake-typesafe", "fake-model"):
                with self.assertRaises(CallError):
                    runner.run(args(model=model))
            with patch.object(runner.adapters.shutil, "which", return_value=None), self.assertRaises(CallError):
                runner.run(args(model="fake-claude"))
            self.assertFalse(runner.runs_dir().exists())

    def test_live_reader_ignores_only_unfinished_final_json(self):
        with fixtures.repo(ENV) as root:
            p = Path(root) / "live.jsonl"
            p.write_text('{"complete":true}\n{"incomplete":')
            self.assertEqual(runner.read_jsonl(p, allow_partial=True), [{"complete": True}])
            with self.assertRaises(json.JSONDecodeError):
                runner.read_jsonl(p)
            p.write_text('{"complete":true}\nbroken\n')
            with self.assertRaises(json.JSONDecodeError):
                runner.read_jsonl(p, allow_partial=True)


if __name__ == "__main__":
    unittest.main()
