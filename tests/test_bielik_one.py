import copy
import json
import unittest
from unittest.mock import patch

from decision_bench import adapters, bielik_one, config, runner
from decision_bench.errors import CallError
from decision_bench.corpus import JUDGMENT_POLICY, public_input
import fixtures


class BielikOne(unittest.TestCase):
    def model(self):
        return {"id": "fake-bielik", "provider": "bielik-one", "model": "decision", "vision": False,
                "request": {"read_twice": True, "read_twice_max_input_tokens": None, "permutations": 1,
                            "questions_before_state": False, "reasoning": "off", "temperature": {"choice": 2.2}}}

    def test_endpoint_and_preflight_use_environment(self):
        with fixtures.repo({"BIELIK_ONE_BASE_URL": "https://bielik.example.com/v1/"}):
            self.assertEqual(bielik_one.endpoint(), "https://bielik.example.com/v1/systemone")
            self.assertEqual(runner.endpoint_url(self.model()), bielik_one.endpoint())
            runner.preflight(self.model())
        with fixtures.repo({"BIELIK_ONE_BASE_URL": "https://bielik.example.com"}):
            self.assertEqual(bielik_one.endpoint(), "https://bielik.example.com/v1/systemone")
        with fixtures.repo():
            with self.assertRaises(CallError):
                runner.preflight(self.model())

    def test_endpoint_rejects_embedded_credentials_and_plain_remote_http(self):
        bad = ("http://remote.example.com/v1", "https://user:pass@bielik.example.com/v1",
               "https://bielik.example.com/v1?token=secret", "https://bielik.example.com/v1#fragment",
               "https://bielik.example.com/other", "https://bielik.example.com:bad/v1")
        for value in bad:
            with self.subTest(value=value), fixtures.repo({"BIELIK_ONE_BASE_URL": value}):
                with self.assertRaises(CallError):
                    bielik_one.endpoint()
        for value in ("http://localhost:8000/v1", "http://127.0.0.1:8000/v1", "http://[::1]:8000/v1"):
            with fixtures.repo({"BIELIK_ONE_BASE_URL": value}):
                self.assertTrue(bielik_one.endpoint().endswith("/v1/systemone"))

    def test_payload_reuses_systemone_without_gold_or_image_data(self):
        model = self.model()
        case = fixtures.ROWS[0]
        before = copy.deepcopy((model, case))
        result = {"resolved_model": "decision", "usage": {"input_tokens": 20, "output_tokens": 1}}
        reply = {"model": "decision", "answers": {}, "usage": {"input_tokens": 20, "output_tokens": 1}}
        with fixtures.repo({"BIELIK_ONE_BASE_URL": "http://localhost:8000/v1"}), \
                patch.object(adapters.urllib.request, "build_opener") as transport:
            response = transport.return_value.open.return_value.__enter__.return_value
            response.read.return_value = json.dumps(reply).encode()
            response.status = 200
            actual = adapters.call(model, case, 30, model["model"])
        self.assertEqual(actual["usage"]["input_tokens"], 20)
        request = transport.return_value.open.call_args.args[0]
        self.assertIsNone(request.get_header("Authorization"))
        payload = json.loads(request.data)
        public = public_input(case)
        self.assertEqual(payload["state"], public["state"])
        self.assertEqual(payload["model"], model["model"])
        q = payload["questions"]["decision"]
        self.assertEqual(q["instructions"], JUDGMENT_POLICY + public["questions"][0]["instructions"])
        self.assertEqual(q["criteria"], public["questions"][0]["options"])
        self.assertNotIn("gold", q)
        self.assertNotIn("images", payload)
        for key, value in model["request"].items():
            self.assertEqual(payload[key], value)
        self.assertEqual((model, case), before)

    def test_optional_key_and_errors_are_forwarded_without_fallback(self):
        error = CallError("rate limited", status=429, retryable=True)
        with fixtures.repo({"BIELIK_ONE_BASE_URL": "https://bielik.example.com/v1", "BIELIK_ONE_API_KEY": fixtures.FAKE_KEY}), \
                patch.object(adapters, "systemone", side_effect=error) as transport:
            with self.assertRaises(CallError) as caught:
                adapters.call(self.model(), fixtures.ROWS[0], 10)
        self.assertIs(caught.exception, error)
        self.assertEqual(transport.call_args.args[5], fixtures.FAKE_KEY)

    def test_model_override_is_rejected_before_transport(self):
        with patch.object(adapters, "systemone") as transport:
            with self.assertRaises(CallError) as caught:
                adapters.call(self.model(), fixtures.ROWS[0], 10, "another-model")
        self.assertEqual(caught.exception.status, "config_invalid")
        transport.assert_not_called()

    def test_legacy_native_provider_payloads_are_unchanged(self):
        case = fixtures.ROWS[0]
        expected = {"model": "native-model", "state": case["state"], "questions": {
            "decision": {"type": "choice", "instructions": JUDGMENT_POLICY + "Pick one.",
                         "criteria": {"b": "B", "a": "A"}}}}
        reply = {"model": "native-model", "answers": {}, "usage": {"input_tokens": 20, "output_tokens": 1}}
        env = {"TYPESAFE_API_KEY": fixtures.FAKE_KEY, "DJEV_API_KEY": fixtures.FAKE_KEY,
               "SARVAM_API_KEY": fixtures.FAKE_KEY, "LAYA_BASE_URL": "https://laya.example.com/v1",
               "LAYA_API_KEY": fixtures.FAKE_KEY}
        for provider in ("typesafe", "djev", "sarvam", "laya"):
            with self.subTest(provider=provider), fixtures.repo(env), \
                    patch.object(adapters.urllib.request, "build_opener") as opener:
                response = opener.return_value.open.return_value.__enter__.return_value
                response.read.return_value = json.dumps(reply).encode()
                response.status = 200
                adapters.call({"provider": provider, "model": "native-model", "vision": False}, case, 10)
                payload = opener.return_value.open.call_args.args[0].data
                self.assertEqual(payload, json.dumps(expected).encode())

    def test_shared_extra_cannot_replace_input_fields(self):
        for name in ("model", "state", "questions", "images"):
            with self.subTest(name=name), self.assertRaises(CallError):
                adapters.systemone(self.model(), fixtures.ROWS[0], 10, None,
                                   "https://bielik.example.com/v1/systemone", None, "Bielik", extra={name: "replace"})

    def test_new_credentials_are_redacted_and_removed_from_cli_environment(self):
        from decision_bench import openai_compat
        key = fixtures.FAKE_KEY
        base = "https://bielik.example.com/v1"
        with fixtures.repo({"BIELIK_ONE_BASE_URL": base, "BIELIK_ONE_API_KEY": key}):
            self.assertEqual(openai_compat.redact({"echo": key + " " + base}),
                             {"echo": "[REDACTED] [ENDPOINT]"})
        self.assertIn("BIELIK_ONE_API_KEY", adapters.HARNESS_SECRETS)
        self.assertIn("BIELIK_ONE_BASE_URL", adapters.HARNESS_SECRETS)

    def test_vision_and_unknown_payload_keys_are_rejected(self):
        with self.assertRaises(CallError):
            bielik_one.call(dict(self.model(), vision=True), fixtures.ROWS[0], 10)
        model = dict(self.model(), label="Fake", vendor="Test", request={"state": "replace"})
        with self.assertRaises(config.ConfigError):
            config._check_model(model)


if __name__ == "__main__":
    unittest.main()
