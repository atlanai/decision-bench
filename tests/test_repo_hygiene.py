"""Nothing committed may carry a credential, an internal hostname or a local home path."""
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

from decision_bench import config, corpus

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("check_secrets", ROOT / "scripts/check_secrets.py")
check_secrets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_secrets)

# Assembled at runtime so this file does not contain the strings it looks for.
INTERNAL_HOST = "llm" + "proxy." + "at" + "lan" + ".dev"
COMPANY_URL = dict(check_secrets.PROJECT_RE)["company URL"]
HOME = re.compile(r"/" + r"Users/[A-Za-z]")


class RepoHygiene(unittest.TestCase):
    def test_only_this_public_repository_is_exempt_from_company_url_rule(self):
        base = "https://github.com/at" + "lanai/decision-bench"
        self.assertEqual(check_secrets.scan_text("README.md", base + "/issues"), [])
        for url in (base + "-private", base + "/../private", base.replace("github.com", "github.com.evil.test"),
                    base.replace("decision-bench", "private-repo")):
            self.assertTrue(check_secrets.scan_text("README.md", url), url)

    def test_scanner_finds_nothing_in_the_repository(self):
        findings = check_secrets.scan(ROOT)
        self.assertEqual(findings, [], "\n".join(f"{f[0]}:{f[1]} {f[2]}" for f in findings))

    def test_only_public_benchmark_dataset_is_exempt_on_hugging_face(self):
        base = "https://huggingface.co/datasets/at" + "lanai/decision-bench"
        self.assertEqual(check_secrets.scan_text("README.md", base), [])
        self.assertEqual(check_secrets.scan_text("README.md", base + "/blob/main/DATA_LICENSE.md"), [])
        for url in (base + "-private", base + "/../private", base.replace("decision-bench", "private"),
                    base.replace("huggingface.co", "huggingface.co.evil.test")):
            self.assertTrue(check_secrets.scan_text("README.md", url), url)

    def test_no_internal_host_company_url_or_home_path_in_committed_text(self):
        for rel in check_secrets.files(ROOT):
            if rel.startswith(check_secrets.THIRD_PARTY):
                continue
            data = (ROOT / rel).read_bytes()
            if b"\0" in data[:4096]:
                continue
            text = data.decode("utf-8", errors="replace")
            self.assertNotIn(INTERNAL_HOST, text, rel)
            self.assertTrue(all(check_secrets.public_repository_url(m.group(0))
                                for m in COMPANY_URL.finditer(text)), rel)
            self.assertIsNone(HOME.search(text), rel)

    def test_scanner_catches_planted_problems(self):
        planted = {
            "a.py": 'KEY = "sk-' + "a1B2c3D4" * 4 + '"\n',
            "b.md": "See https://" + INTERNAL_HOST + "/v1\n",
            "c.json": '{"path": "/' + 'Users/someone/project"}\n',
            "d.txt": "aws " + "AKIA" + "Q3EGRI5JHZ7PL2WX" + "\n",
            "e.py": 'password = "' + "Zx9qLm2Vt8Rw4Ny6Kp1Hs3Bd" + '"\n',
            "f.json": '{"' + "gateway_" + 'base_url": "https://gw.example.com"}\n',
            "g.md": "http://build." + "corp" + "/x and 10." + "1.2.3\n",
            "data/corpus/x/cases.jsonl": '{"text": "/' + 'Users/someone and AKIA' + 'Q3EGRI5JHZ7PL2WX"}\n',
            "ok.md": "AWS docs use AKIA" + "IOSFODNN7EXAMPLE as a placeholder; see https://example.com\n",
        }
        with tempfile.TemporaryDirectory() as tmp:
            for rel, text in planted.items():
                path = Path(tmp) / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            found = {(f[0], f[2]) for f in check_secrets.scan(tmp)}
        files = {f for f, _ in found}
        self.assertEqual(files, set(planted) - {"ok.md"})
        corpus_kinds = {k for f, k in found if f.startswith("data/corpus/")}
        self.assertEqual(corpus_kinds, {"AWS access key"})  # home paths are allowed in third-party data

    def test_model_config_has_no_endpoints_or_keys(self):
        corpus_root = corpus.ROOT
        self.assertEqual(corpus_root, ROOT)
        models = config.load_models()
        self.assertTrue(models)
        raw = json.loads((ROOT / "config/models.json").read_text())

        def walk(value, path=""):
            if isinstance(value, dict):
                for k, v in value.items():
                    self.assertNotIn(k.lower(), {"base_url", "url", "api_base", "api_key", "host", "endpoint",
                                                 "deploy" + "ment_id", "deploy" + "ment_ids"}, path + k)
                    walk(v, path + k + ".")
            elif isinstance(value, list):
                for v in value:
                    walk(v, path)
            elif isinstance(value, str) and "://" in value:
                self.assertTrue(path.endswith("pricing.source_url."), f"URL outside pricing.source_url at {path}")
        walk(raw)

    def test_local_files_are_ignored(self):
        text = (ROOT / ".gitignore").read_text().splitlines()
        for pattern in (".env", "runs/", "site/data.json", "site/corpus.json", "site/results/", "__pycache__/"):
            self.assertIn(pattern, text)


if __name__ == "__main__":
    unittest.main()
