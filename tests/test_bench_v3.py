"""Contracts for the committed corpus: fixed tasks, attributed real rows, no answer leaks, no live secrets."""
import collections
import json
import re
import unittest

from decision_bench import corpus
from decision_bench.corpus import load_cases, load_manifest, public_input, user_message, validate_against_manifest


class BenchV3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_cases()
        cls.manifest = load_manifest()

    def test_manifest_matches_rows(self):
        validate_against_manifest(self.rows, self.manifest)
        self.assertEqual(corpus.digest(self.rows), self.manifest["sha256"])

    def test_every_task_has_rows_and_uses_every_fixed_option(self):
        by_task = collections.defaultdict(list)
        for r in self.rows:
            by_task[r["task"]].append(r)
        self.assertEqual(set(by_task), set(self.manifest["tasks"]))
        for task, rows in by_task.items():
            golds = {r["questions"][0]["gold"] for r in rows}
            options = rows[0]["questions"][0]["options"]
            if all(r["questions"][0]["options"] == options for r in rows):
                self.assertEqual(golds, set(options), task)

    def test_real_rows_are_attributed(self):
        for r in self.rows:
            if r["source_kind"] == "real":
                for key in ("dataset", "license", "url", "record_id", "labelled_by"):
                    self.assertTrue(r["source"].get(key), f"{r['id']} missing {key}")

    def test_reader_fields_never_reach_models(self):
        for r in self.rows:
            sent = user_message(r)
            q = r["questions"][0]
            self.assertNotIn(q["rationale"], sent, r["id"])
            self.assertNotIn('"gold"', sent, r["id"])
            self.assertNotIn(r["id"], sent, r["id"])
            for key in ("note", "summary", "provenance"):
                if r.get(key):
                    self.assertNotIn(r[key], sent, f"{r['id']} {key}")
            if r.get("source"):
                self.assertNotIn(json.dumps(r["source"], ensure_ascii=False), sent, r["id"])
                self.assertNotIn(r["source"].get("url", "\0"), sent, r["id"])
            self.assertEqual(set(public_input(r)), {"state", "questions"})

    def test_no_live_secret_formats(self):
        text = "\n".join(json.dumps(r, ensure_ascii=False) for r in self.rows)
        for pattern in (r"AKIA[0-9A-Z]{16}", r"gh[pousr]_[A-Za-z0-9]{30,}", r"xox[baprs]-[A-Za-z0-9-]{10,}",
                        r"[sr]k_live_[A-Za-z0-9]{20,}", r"AIza[0-9A-Za-z_-]{35}", r"-----BEGIN [A-Z ]*PRIVATE KEY"):
            self.assertIsNone(re.search(pattern, text), pattern)


if __name__ == "__main__":
    unittest.main()
