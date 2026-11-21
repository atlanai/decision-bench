import unittest
from unittest.mock import patch

from decision_bench import adapters, openai_compat, quyet, runner
from decision_bench.errors import CallError

ENV = {"QUYET_BASE_URL": "https://quyet.example", "QUYET_API_KEY": "test-quyet-key"}


class QuyetEndpoint(unittest.TestCase):
    def test_root_and_v1_urls(self):
        for base in ("https://quyet.example", "https://quyet.example/v1/"):
            with patch.object(quyet, "env_value", return_value=base):
                self.assertEqual(quyet.endpoint(), "https://quyet.example/v1/systemone")

    def test_unset_url_is_config_missing(self):
        with patch.object(quyet, "env_value", return_value=None):
            with self.assertRaises(CallError) as cm:
                quyet.endpoint()
        self.assertEqual(cm.exception.status, "config_missing")

    def test_invalid_urls(self):
        for base in ("http://quyet.example", "https://key@quyet.example", "https://quyet.example?key=secret",
                     "https://quyet.example/other", "https://quyet.example#fragment"):
            with self.subTest(base=base), patch.object(quyet, "env_value", return_value=base):
                with self.assertRaises(CallError):
                    quyet.endpoint()

    def test_remote_key_required_before_a_run(self):
        with patch.object(quyet, "env_value", side_effect={"QUYET_BASE_URL": "https://quyet.example"}.get):
            with self.assertRaises(CallError) as cm:
                runner.preflight({"provider": "quyet"})
        self.assertEqual(cm.exception.status, "auth_missing")

    def test_native_dispatch(self):
        model = {"provider": "quyet", "model": "Quyet-1.2-Large"}
        with patch.object(quyet, "env_value", side_effect=ENV.get), \
                patch.object(adapters, "systemone", return_value={"raw": {"latency_ms": 42}}) as call:
            result = adapters.call(model, {"id": "test"}, 60)
        self.assertEqual(call.call_args.args[4], "https://quyet.example/v1/systemone")
        self.assertEqual(call.call_args.args[5], "test-quyet-key")
        self.assertEqual(result["provider_duration_ms"], 42)

    def test_key_and_host_are_redacted(self):
        with patch.object(openai_compat, "env_value", side_effect=ENV.get):
            cleaned = openai_compat.redact("test-quyet-key https://quyet.example quyet.example")
        self.assertNotIn("test-quyet-key", cleaned)
        self.assertNotIn("quyet.example", cleaned)


if __name__ == "__main__":
    unittest.main()
