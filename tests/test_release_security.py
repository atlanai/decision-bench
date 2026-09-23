"""Publication boundaries with synthetic credentials only; no external requests."""
import io
import json
import unittest
from unittest.mock import MagicMock, patch

from decision_bench import adapters, corpus, results, runner
from fixtures import repo
from test_adapters import CASE, ANSWER
from test_repo_hygiene import check_secrets


class ReleaseSecurity(unittest.TestCase):
    def test_native_success_scrubs_credentials_in_keys_values_and_output(self):
        key = "synthetic-native-credential"
        url = "https://models.example.test/v1/systemone"
        body = {**ANSWER, key: "debug", "debug": [key, url, "models.example.test"],
                "authorization": "another-sensitive-value", "usage": {"input_tokens": 42}}
        response = MagicMock(status=200)
        response.read.return_value = json.dumps(body).encode()
        response.__enter__.return_value = response
        with repo(), patch.object(adapters.urllib.request, "build_opener") as opener:
            opener.return_value.open.return_value = response
            result = adapters.systemone({"model": "test"}, CASE, 10, None, url, key, "Test")
        encoded = json.dumps(result)
        for value in (key, url, "models.example.test", "another-sensitive-value"):
            self.assertNotIn(value, encoded)
        self.assertEqual(result["response"]["answers"], ANSWER["answers"])
        self.assertEqual(result["usage"]["input_tokens"], 42)

    def test_persistence_redacts_all_configured_provider_keys(self):
        settings = {"DECISION_BENCH_API_KEY": "synthetic-" + "openai-key", "TYPESAFE_API_KEY": "synthetic-ts-key",
                    "LAYA_API_KEY": "synthetic-laya-key", "LAYA_BASE_URL": "https://models.example.test/v1"}
        with repo(settings) as root:
            path = root / "record.json"
            runner.write_json(path, {settings["LAYA_API_KEY"]: list(settings.values())})
            text = path.read_text()
            for value in settings.values():
                self.assertNotIn(value, text)
            self.assertNotIn("models.example.test", text)

    def test_image_paths_cannot_escape_assets_even_through_symlinks(self):
        with repo() as root:
            assets = root / "data/assets"
            assets.mkdir()
            (assets / "safe.png").write_bytes(b"test-image")
            (root / ".env").write_text("PRIVATE_TEST_VALUE")
            (assets / "linked.png").symlink_to(root / ".env")
            self.assertEqual(corpus.asset_path("data/assets/safe.png"), (assets / "safe.png").resolve())
            for path in (".env", "data/assets/../../.env", str(root / ".env"), "data/assets/linked.png"):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    corpus.image_assets({"assets": [{"path": path, "mime_type": "image/png"}]})

    def test_export_redacts_old_output_and_errors_with_current_credentials(self):
        key = "synthetic-export-key"
        with repo({"LAYA_API_KEY": key}):
            case = corpus.load_cases()[0]
            records = [{"case_id": case["id"], "status": "error", "output_text": key, "error": key}]
            exported = results.predictions_from_run(records, [], {case["id"]: case})
        self.assertNotIn(key, json.dumps(exported))
        self.assertEqual(exported[0]["output_text"], "[REDACTED]")

    def test_scanner_checks_provider_keys_in_data_without_echoing_them(self):
        keys = ["sk-" + "a1B2c3D4" * 4, "github_pat_" + "a1B2c3D4" * 5, "imp-rt-" + "a1B2c3D4" * 4]
        for key in keys:
            findings = check_secrets.scan_text("data/corpus/test/cases.jsonl", key)
            self.assertTrue(findings)
            self.assertNotIn(key, repr(findings))
            with patch.object(check_secrets, "scan", return_value=findings), \
                    patch.object(check_secrets, "files", return_value=["test"]), \
                    patch("sys.stdout", new_callable=io.StringIO) as output:
                self.assertEqual(check_secrets.main(["scanner"]), 1)
                self.assertNotIn(key, output.getvalue())
