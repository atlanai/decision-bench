import unittest
from unittest.mock import patch

from decision_bench import adapters, openai_compat, sieve
from decision_bench.errors import CallError


class SieveEndpoint(unittest.TestCase):
    def test_root_and_v1_urls(self):
        for base in ("http://localhost:8020", "http://localhost:8020/v1/", "https://bench.example"):
            with patch.object(sieve, "env_value", return_value=base):
                self.assertEqual(sieve.endpoint(), base.rstrip("/").removesuffix("/v1") + "/v1/decide")

    def test_invalid_urls(self):
        for base in ("", "http://bench.example", "https://key@bench.example", "https://bench.example?key=secret",
                     "https://bench.example/other", "https://bench.example#fragment"):
            with self.subTest(base=base), patch.object(sieve, "env_value", return_value=base):
                with self.assertRaises(CallError):
                    sieve.endpoint()

    def test_key_is_optional(self):
        with patch.object(sieve, "env_value", return_value=None):
            self.assertIsNone(sieve.api_key("http://localhost:8020/v1/decide"))

    def test_native_dispatch(self):
        model = {"provider": "sieve", "model": "sthanika-ai/Sieve-31B-v3"}
        values = {"SIEVE_BASE_URL": "http://localhost:8020"}
        with patch.object(sieve, "env_value", side_effect=values.get), \
                patch.object(adapters, "systemone", return_value={"raw": {"latency_ms": 42}}) as call:
            result = adapters.call(model, {"id": "test"}, 60)
        self.assertEqual(call.call_args.args[4], "http://localhost:8020/v1/decide")
        self.assertEqual(result["provider_duration_ms"], 42)
        self.assertEqual(result["images_sent"], 0)

    def test_secret_and_host_redaction(self):
        values = {"SIEVE_API_KEY": "test-sieve-key", "SIEVE_BASE_URL": "https://bench.example"}
        with patch.object(openai_compat, "env_value", side_effect=values.get):
            cleaned = openai_compat.redact("test-sieve-key https://bench.example bench.example")
        self.assertNotIn("test-sieve-key", cleaned)
        self.assertNotIn("bench.example", cleaned)


if __name__ == "__main__":
    unittest.main()
