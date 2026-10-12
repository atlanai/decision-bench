import unittest
from unittest.mock import patch

from decision_bench import adapters, kev, openai_compat
from decision_bench.errors import CallError


class KevEndpoint(unittest.TestCase):
    def test_root_and_v1_urls(self):
        for base in ("https://bench.example", "https://bench.example/v1/"):
            with patch.object(kev, "env_value", return_value=base):
                self.assertEqual(kev.endpoint(), "https://bench.example/v1/systemone")

    def test_invalid_urls(self):
        for base in ("", "http://bench.example", "https://key@bench.example", "https://bench.example?key=secret", "https://bench.example/other", "https://bench.example#fragment"):
            with self.subTest(base=base), patch.object(kev, "env_value", return_value=base):
                with self.assertRaises(CallError):
                    kev.endpoint()

    def test_remote_key_required(self):
        with patch.object(kev, "env_value", return_value=None):
            with self.assertRaises(CallError) as cm:
                kev.api_key("https://bench.example/v1/systemone")
        self.assertEqual(cm.exception.status, "auth_missing")

    def test_native_dispatch(self):
        model = {"provider": "kev", "model": "kev-latest"}
        values = {"KEV_BASE_URL": "https://bench.example", "KEV_API_KEY": "test-kev-key"}
        with patch.object(kev, "env_value", side_effect=values.get), patch.object(adapters, "systemone", return_value={"raw": {"latency_ms": 42}}) as call:
            result = adapters.call(model, {"id": "test"}, 60)
        self.assertEqual(call.call_args.args[4], "https://bench.example/v1/systemone")
        self.assertEqual(result["provider_duration_ms"], 42)
        self.assertEqual(result["images_sent"], 0)

    def test_global_secret_and_host_redaction(self):
        values = {"KEV_API_KEY": "test-kev-key", "KEV_BASE_URL": "https://bench.example"}
        with patch.object(openai_compat, "env_value", side_effect=values.get):
            cleaned = openai_compat.redact("test-kev-key https://bench.example bench.example")
        self.assertNotIn("test-kev-key", cleaned)
        self.assertNotIn("bench.example", cleaned)
