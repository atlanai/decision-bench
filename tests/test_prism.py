import unittest
from unittest.mock import patch

from decision_bench import adapters, openai_compat, prism, runner
from decision_bench.errors import CallError

ENV = {"PRISM_BASE_URL": "https://prism.example", "PRISM_API_KEY": "test-prism-key"}


class PrismEndpoint(unittest.TestCase):
    def test_root_and_v1_urls(self):
        for base in ("https://prism.example", "https://prism.example/v1/"):
            with patch.object(prism, "env_value", return_value=base):
                self.assertEqual(prism.endpoint(), "https://prism.example/v1/systemone")

    def test_unset_url_is_config_missing(self):
        with patch.object(prism, "env_value", return_value=None):
            with self.assertRaises(CallError) as cm:
                prism.endpoint()
        self.assertEqual(cm.exception.status, "config_missing")

    def test_invalid_urls(self):
        for base in ("http://prism.example", "https://key@prism.example", "https://prism.example?key=secret",
                     "https://prism.example/other", "https://prism.example#fragment"):
            with self.subTest(base=base), patch.object(prism, "env_value", return_value=base):
                with self.assertRaises(CallError):
                    prism.endpoint()

    def test_remote_key_required_before_a_run(self):
        with patch.object(prism, "env_value", side_effect={"PRISM_BASE_URL": "https://prism.example"}.get):
            with self.assertRaises(CallError) as cm:
                runner.preflight({"provider": "prism"})
        self.assertEqual(cm.exception.status, "auth_missing")

    def test_native_dispatch(self):
        model = {"provider": "prism", "model": "sarvamai/prism"}
        with patch.object(prism, "env_value", side_effect=ENV.get), \
                patch.object(adapters, "systemone", return_value={"raw": {"latency_ms": 42}}) as call:
            result = adapters.call(model, {"id": "test"}, 60)
        self.assertEqual(call.call_args.args[4], "https://prism.example/v1/systemone")
        self.assertEqual(call.call_args.args[5], "test-prism-key")
        self.assertEqual(result["provider_duration_ms"], 42)

    def test_key_and_host_are_redacted(self):
        with patch.object(openai_compat, "env_value", side_effect=ENV.get):
            cleaned = openai_compat.redact("test-prism-key https://prism.example prism.example")
        self.assertNotIn("test-prism-key", cleaned)
        self.assertNotIn("prism.example", cleaned)


if __name__ == "__main__":
    unittest.main()
