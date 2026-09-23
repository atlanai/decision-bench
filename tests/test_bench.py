"""Contracts for the active corpus: fixed tasks with labels, attributed real rows, no answer leaks, no secrets,
image rows with files and text renderings."""
import collections
import json
import re
import unittest

from decision_bench.corpus import ROOT, corpus_path, load_cases, load_manifest, public_input


class ActiveCorpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_cases(corpus_path())
        cls.manifest = load_manifest()

    def test_every_task_has_rows_and_uses_every_fixed_option(self):
        by_task = collections.defaultdict(list)
        for r in self.rows:
            by_task[r["task"]].append(r)
        self.assertEqual(set(by_task), set(self.manifest["tasks"]))
        for task, rows in by_task.items():
            golds = collections.Counter(r["questions"][0]["gold"] for r in rows)
            options = rows[0]["questions"][0]["options"]
            if all(r["questions"][0]["options"] == options for r in rows):
                self.assertEqual(set(golds), set(options), task)
            top = golds.most_common(1)[0][1]
            self.assertLessEqual(top, 0.6 * len(rows) + 1e-9, f"{task}: one answer dominates")

    def test_task_labels_are_published(self):
        if self.manifest.get("version", "").startswith("3."):
            self.skipTest("v3 manifests carry no task labels")
        for task, t in self.manifest["tasks"].items():
            for key in ("category", "name", "ask", "shape", "input_type", "modality", "expertise", "contamination",
                        "label_origin", "options", "rows", "length", "datasets"):
                self.assertIn(key, t, f"{task} missing {key}")

    def test_real_rows_are_attributed(self):
        for r in self.rows:
            if r.get("source_kind", "real") == "real":
                for key in ("dataset_id", "dataset", "license", "url", "record_id", "labelled_by"):
                    self.assertTrue(r["source"].get(key), f"{r['id']} missing {key}")

    def test_reader_fields_never_reach_models(self):
        for r in self.rows:
            sent = json.dumps(public_input(r), ensure_ascii=False)
            self.assertNotIn(r["questions"][0]["rationale"], sent, r["id"])
            self.assertNotIn(r["title"], sent, r["id"])
            if r.get("note"):
                self.assertNotIn(r["note"], sent, r["id"])

    def test_titles_do_not_state_the_answer(self):
        for r in self.rows:
            gold = r["questions"][0]["gold"].lower().replace("_", " ")
            if len(gold) > 2:
                self.assertIsNone(re.search(rf"\b{re.escape(gold)}\b", r["title"].lower().replace("_", " ")), r["id"])

    def test_image_rows_have_files_and_a_text_rendering(self):
        for r in self.rows:
            for a in r.get("assets", []):
                path = ROOT / a["path"]
                self.assertTrue(path.is_file(), f"{r['id']}: missing {a['path']}")
                self.assertLessEqual(path.stat().st_size, 400_000, f"{r['id']}: {a['path']} over 400 KB")
                self.assertTrue(a.get("alt_text"), f"{r['id']}: asset without alt text")
            if r.get("assets"):
                self.assertTrue(r["state"], f"{r['id']}: image row without a text state")

    def test_no_live_secret_formats(self):
        text = "\n".join(json.dumps(r, ensure_ascii=False) for r in self.rows)
        for pattern in (r"AKIA[0-9A-Z]{16}", r"gh[pousr]_[A-Za-z0-9]{30,}", r"xox[baprs]-[A-Za-z0-9-]{10,}",
                        r"[sr]k_live_[A-Za-z0-9]{20,}", r"AIza[0-9A-Za-z_-]{35}", r"-----BEGIN [A-Z ]*PRIVATE KEY"):
            self.assertIsNone(re.search(pattern, text), pattern)


if __name__ == "__main__":
    unittest.main()
