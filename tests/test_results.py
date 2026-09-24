"""End to end against a local fake endpoint: run, publish to results/, validate, and build the site data."""
import argparse
import json
import unittest
from unittest.mock import patch

from decision_bench import __main__ as cli
from decision_bench import report, results, runner
from decision_bench.corpus import load_cases, load_manifest

import fixtures
from fake_server import FakeEndpoint


def run_args(**kw):
    base = dict(model="fake-model", run_id=None, api_model=None, jobs=2, timeout=5, max_attempts=2, limit=None,
                ids=None, retry_errors=False)
    base.update(kw)
    return argparse.Namespace(**base)


class EmptyResults(unittest.TestCase):
    def test_report_works_with_no_results(self):
        with fixtures.repo() as root:
            out = report.build()
            data = json.loads((root / "site/data.json").read_text())
            self.assertEqual(data["runs"], [])
            self.assertEqual(data["results"], [])
            self.assertEqual(data["leaderboard"], [])
            self.assertEqual(len(data["cases"]), 3)
            self.assertEqual(data["suite"], "mini")
            self.assertEqual({m["id"] for m in data["models"]},
                             {"fake-model", "fake-typesafe", "fake-laya", "fake-claude"})
            corpus_rows = json.loads((root / "site/corpus.json").read_text())
            self.assertEqual(corpus_rows[0]["questions"][0]["rationale"], "RATIONALE_r1")  # reader fields kept
            self.assertEqual(corpus_rows[0]["source"]["dataset"], "SOURCE_DATASET")
            self.assertFalse((root / "site/datasets.json").exists())
            self.assertEqual(out["inventory"]["cases"], 3)
            (root / "data/datasets.json").write_text('{"datasets": []}')
            (root / "results").mkdir()
            (root / "results/README.md").write_text("format")
            report.build()
            self.assertTrue((root / "site/datasets.json").exists())
            self.assertTrue((root / "site/results/README.md").exists())
            self.assertEqual(cli.main(["validate"]), 0)


class PublishFlow(unittest.TestCase):
    def setUp(self):
        self.server = FakeEndpoint(fail_first=1).__enter__()
        self.repo = fixtures.repo({"DECISION_BENCH_BASE_URL": self.server.url,
                                   "DECISION_BENCH_API_KEY": fixtures.FAKE_KEY})
        self.root = self.repo.__enter__()
        self.sleep = patch.object(runner.time, "sleep")
        self.sleep.start()

    def tearDown(self):
        self.sleep.stop()
        self.repo.__exit__(None, None, None)
        self.server.__exit__(None, None, None)

    def test_run_publish_validate_report(self):
        meta = runner.run(run_args(jobs=1))
        run_id = meta["id"]
        self.assertEqual(meta["status"], "completed")
        out = results.publish(run_id)
        folder = self.root / "results/mini/fake-model"
        self.assertEqual(out["rows"], 3)
        self.assertEqual(sorted(p.name for p in folder.iterdir()),
                         ["README.md", "metadata.json", "predictions.jsonl", "scores.json"])
        metadata = json.loads((folder / "metadata.json").read_text())
        predictions = [json.loads(line) for line in (folder / "predictions.jsonl").read_text().splitlines()]
        scores = json.loads((folder / "scores.json").read_text())
        # The fake answers the first option in presentation order, which is "b" for every row.
        self.assertEqual([(p["row_id"], p["answer"], p["gold"], p["correct"]) for p in predictions],
                         [("r1", "b", "a", False), ("r2", "b", "b", True), ("r3", "b", "a", False)])
        first = predictions[0]
        self.assertEqual([a["status"] for a in first["attempts"]], ["429", "ok"])  # the retry is kept
        self.assertEqual(first["tokens"]["input"], 100)
        self.assertAlmostEqual(first["cost_usd"], .0005)
        self.assertIsNotNone(first["output_text"])
        self.assertAlmostEqual(first["confidence"], .8)
        self.assertEqual(scores["overall"]["correct"], 1)
        self.assertEqual(scores["overall"]["rows"], 3)
        self.assertEqual([c["id"] for c in scores["by_category"]], ["alpha", "beta"])
        self.assertEqual(scores["by_category"][0]["name"], "Alpha")
        self.assertEqual(len(scores["overall"]["wilson95"]), 2)
        self.assertEqual(metadata["model"]["api_model"], "fake/model-1")
        self.assertEqual(metadata["corpus"]["sha256"], load_manifest()["sha256"])
        self.assertTrue(metadata["coverage"]["full"])
        self.assertTrue(metadata["run"]["endpoint_id"].startswith("endpoint-"))
        published = "".join(p.read_text() for p in folder.iterdir())
        for secret in (fixtures.FAKE_KEY, "127.0.0.1", self.server.url, "chatcmpl-1", "internal-deployment", str(self.root)):
            self.assertNotIn(secret, published)
        board = json.loads((self.root / "results/mini/leaderboard.json").read_text())
        self.assertEqual([m["model_id"] for m in board["models"]], ["fake-model"])
        self.assertTrue((self.root / "results/mini/leaderboard.md").exists())
        self.assertEqual(results.check_published(load_cases(), load_manifest()), [])

        data = report.build()
        self.assertEqual([r["source"] for r in data["runs"]], ["published"])
        run = data["runs"][0]
        self.assertEqual(run["metrics"]["correct"], 1)
        self.assertEqual(run["metrics"]["attempts"], 4)
        self.assertEqual(run["model"]["label"], "Fake Model")
        self.assertEqual(run["files"]["predictions"], "results/mini/fake-model/predictions.jsonl")
        self.assertEqual(len(data["results"]), 3)
        self.assertTrue((self.root / "site/results/mini/fake-model/predictions.jsonl").exists())
        site_text = (self.root / "site/data.json").read_text()
        self.assertNotIn(fixtures.FAKE_KEY, site_text)
        self.assertNotIn("127.0.0.1", site_text)

        # Tampering with a published answer is caught by validate.
        predictions[0]["correct"] = True
        (folder / "predictions.jsonl").write_text("".join(json.dumps(p) + "\n" for p in predictions))
        self.assertTrue(results.check_published(load_cases(), load_manifest()))

    def test_publish_refuses_partial_runs_unless_forced_and_replaces_previous(self):
        partial = runner.run(run_args(limit=2))
        with self.assertRaises(ValueError) as cm:
            results.publish(partial["id"])
        self.assertIn("2 of 3", str(cm.exception))
        out = results.publish(partial["id"], force=True)
        self.assertTrue(out["warnings"])
        full = runner.run(run_args())
        results.publish(full["id"])
        metadata = json.loads((self.root / "results/mini/fake-model/metadata.json").read_text())
        self.assertEqual(metadata["run"]["run_id"], full["id"])
        self.assertNotIn("published_with_warnings", metadata)

    def test_publish_refuses_other_corpus_even_with_force(self):
        meta = runner.run(run_args())
        path = self.root / "runs" / meta["id"] / "run.json"
        stored = json.loads(path.read_text())
        stored["config"]["corpus_sha256"] = "0" * 64
        path.write_text(json.dumps(stored))
        for force in (False, True):
            with self.assertRaises(ValueError):
                results.publish(meta["id"], force=force)

    def test_publish_refuses_running_status(self):
        meta = runner.run(run_args())
        path = self.root / "runs" / meta["id"] / "run.json"
        stored = json.loads(path.read_text())
        stored["status"] = "running"
        path.write_text(json.dumps(stored))
        with self.assertRaises(ValueError):
            results.publish(meta["id"])

    def test_include_runs_previews_local_runs(self):
        meta = runner.run(run_args(limit=1))
        self.assertEqual(report.build()["runs"], [])
        data = report.build(include_runs=True)
        self.assertEqual([(r["id"], r["source"]) for r in data["runs"]], [(meta["id"], "local")])
        self.assertFalse(data["runs"][0]["coverage"]["full"])
        self.assertEqual(data["comparisons"], [])

    def test_cli_models_remote_prints_ids_only(self):
        with patch("builtins.print") as printed:
            self.assertEqual(cli.main(["models", "--remote"]), 0)
        self.assertEqual([c.args[0] for c in printed.call_args_list], ["fake/model-1", "fake/model-2"])
        self.assertFalse((self.root / "config/gateway-inventory.json").exists())


if __name__ == "__main__":
    unittest.main()
