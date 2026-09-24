"""Security and parsing for the OpenAI-compatible provider. Uses a local fake endpoint only."""
import io
import json
import os
import unittest
import urllib.error
from unittest.mock import patch

from decision_bench import openai_compat as oc
from decision_bench.errors import CallError
from decision_bench.scoring import normalize_answers

from fake_server import FakeEndpoint

CASE = {"id": "row-1", "state": {"message": "A request"},
        "questions": [{"id": "q", "type": "choice", "instructions": "Classify", "options": {"a": "A", "b": "B"},
                       "gold": "a", "rationale": "PRIVATE_GOLD"}]}
MODEL = {"id": "m", "provider": "openai-compatible", "model": "fake/model-1",
         "request": {"response_format": "json_schema", "max_output_tokens": 128}}
ANSWER = {"answers": {"q": {"label": "a", "probabilities": {"a": .9, "b": .1}}}}
KEY = "fixture-key-0000"
REMOTE = {oc.BASE_ENV: "https://models.example.test/v1", oc.KEY_ENV: KEY}


def env(values):
    return patch.object(oc, "env_value", side_effect=lambda name: values.get(name))


def raw(content=None, finish="stop"):
    return {"id": "request-1", "model": "fake/model-1",
            "choices": [{"message": {"content": json.dumps(ANSWER) if content is None else content}, "finish_reason": finish}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20, "prompt_tokens_details": {"cached_tokens": 40},
                      "completion_tokens_details": {"reasoning_tokens": 5}}}


class Endpoint(unittest.TestCase):
    def test_base_url_rules(self):
        for url in ["https://user:pw@models.example.test/v1", "https://models.example.test/v1?key=1",
                    "http://models.example.test/v1", "ftp://models.example.test", "not a url"]:
            with env({oc.BASE_ENV: url}), self.assertRaises(CallError, msg=url):
                oc.base_url()
        with env({oc.BASE_ENV: "http://localhost:4000/v1/"}):
            self.assertEqual(oc.base_url(), "http://localhost:4000/v1")
        with env({}), self.assertRaises(CallError) as cm:
            oc.base_url()
        self.assertEqual(cm.exception.status, "config_missing")

    def test_remote_endpoint_requires_a_key_local_does_not(self):
        with env({oc.BASE_ENV: "https://models.example.test/v1"}), self.assertRaises(CallError) as cm:
            oc.api_key(oc.base_url())
        self.assertEqual(cm.exception.status, "auth_missing")
        with env({oc.BASE_ENV: "http://127.0.0.1:9/v1"}):
            self.assertIsNone(oc.api_key(oc.base_url()))

    def test_openai_api_key_is_never_read(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-should-not-be-used"}, clear=False), \
                env({oc.BASE_ENV: "https://models.example.test/v1"}), self.assertRaises(CallError):
            oc.api_key(oc.base_url())

    def test_credential_is_only_sent_to_the_configured_origin(self):
        with env(REMOTE), self.assertRaises(CallError) as cm:
            oc.request("https://other.example.test/v1/models")
        self.assertEqual(cm.exception.status, "config_invalid")
        self.assertIsNone(oc.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.example.test"))

    def test_endpoint_id_is_opaque(self):
        ident = oc.endpoint_id("https://models.example.test/v1")
        self.assertTrue(ident.startswith("endpoint-"))
        self.assertNotIn("example", ident)
        self.assertEqual(ident, oc.endpoint_id("https://models.example.test/v1/"))

    def test_error_body_is_scrubbed_of_key_and_endpoint(self):
        body = f"bad credential {KEY} at https://models.example.test/v1 (models.example.test)"
        error = urllib.error.HTTPError("https://models.example.test/v1/models", 401, "Unauthorized", {}, io.BytesIO(body.encode()))
        with env(REMOTE), patch.object(oc.urllib.request, "build_opener") as opener:
            opener.return_value.open.side_effect = error
            with self.assertRaises(CallError) as cm:
                oc.request("https://models.example.test/v1/models")
        text = str(cm.exception) + json.dumps(cm.exception.raw)
        self.assertNotIn(KEY, text)
        self.assertNotIn("models.example.test", text)
        self.assertIn("[REDACTED]", text)
        self.assertFalse(cm.exception.retryable)

    def test_redact_masks_sensitive_keys(self):
        with env(REMOTE):
            out = oc.redact({"Authorization": "Bearer x", "nested": [{"api_key": "y", "text": f"{KEY}!"}]})
        self.assertEqual(out, {"Authorization": "[REDACTED]", "nested": [{"api_key": "[REDACTED]", "text": "[REDACTED]!"}]})


class Completion(unittest.TestCase):
    def complete(self, response, headers=None, model=MODEL):
        with env(REMOTE), patch.object(oc, "request", return_value=(response, headers or {}, 200, 150)) as call:
            return oc.completion(model, CASE, 30), call

    def test_payload_excludes_reader_fields_and_uses_schema(self):
        payload = oc.payload_for(CASE, "fake/model-1", MODEL["request"])
        text = json.dumps(payload)
        self.assertNotIn("PRIVATE_GOLD", text)
        self.assertNotIn("row-1", text)
        self.assertEqual(payload["response_format"]["type"], "json_schema")
        self.assertEqual(payload["max_tokens"], 128)
        self.assertNotIn("temperature", payload)
        p2 = oc.payload_for(CASE, "x", {"token_limit_field": "max_completion_tokens", "reasoning_effort": "low",
                                        "response_format": "json_object", "temperature": 0})
        self.assertEqual((p2["max_completion_tokens"], p2["reasoning_effort"], p2["temperature"]), (4096, "low", 0))
        self.assertEqual(p2["response_format"], {"type": "json_object"})

    def test_usage_cost_and_identity(self):
        headers = {"x-litellm-response-cost": "0.001", "x-litellm-response-duration-ms": "130",
                   "x-litellm-model-id": "deployment-should-not-be-kept"}
        r, _ = self.complete(raw(), headers)
        self.assertEqual((r["cost_usd"], r["cost_basis"]), (.001, "provider_reported"))
        self.assertEqual((r["usage"]["input_tokens"], r["usage"]["cached_input_tokens"]), (100, 40))
        self.assertEqual(r["provider_duration_ms"], 130)
        self.assertNotIn("x-litellm-model-id", json.dumps(r["raw"]["headers"]))
        self.assertEqual(normalize_answers(r["response"], CASE)["q"]["label"], "a")
        self.assertTrue(r["endpoint_id"].startswith("endpoint-"))
        self.assertNotIn("example", json.dumps({k: v for k, v in r.items() if k != "raw"}))

    def test_openrouter_style_usage_cost(self):
        response = raw()
        response["usage"]["cost"] = 0.0021
        self.assertEqual(self.complete(response)[0]["cost_usd"], .0021)

    def test_absent_cost_is_unknown_and_explicit_zero_is_known(self):
        self.assertIsNone(self.complete(raw())[0]["cost_usd"])
        self.assertEqual(self.complete(raw(), {"x-litellm-response-cost": "0"})[0]["cost_usd"], 0)

    def test_invalid_output_keeps_paid_usage(self):
        r, _ = self.complete(raw("not json"), {"x-litellm-response-cost": "0.002"})
        self.assertEqual((r["cost_usd"], r["usage"]["output_tokens"]), (.002, 20))
        self.assertIn("Invalid response JSON", r["output_validation_error"])
        with self.assertRaises(ValueError):
            normalize_answers(r["response"], CASE)

    def test_only_one_complete_fence_is_unwrapped(self):
        fenced = "```json\n" + json.dumps(ANSWER) + "\n```"
        r, _ = self.complete(raw(fenced))
        self.assertEqual(r["output_wrapper_normalization"], "single_markdown_code_fence")
        self.assertEqual(r["output_text"], fenced)
        self.assertEqual(normalize_answers(r["response"], CASE)["q"]["label"], "a")
        strict = dict(MODEL, request={"json_wrapper_policy": "strict"})
        for text, model in [("Explanation: " + json.dumps(ANSWER), MODEL), (fenced, strict)]:
            with self.assertRaises(ValueError):
                normalize_answers(self.complete(raw(text), model=model)[0]["response"], CASE)

    def test_truncation_and_tool_calls_are_invalid(self):
        with self.assertRaises(ValueError):
            normalize_answers(self.complete(raw(finish="length"))[0]["response"], CASE)
        response = raw()
        response["choices"][0]["message"]["tool_calls"] = [{"id": "t"}]
        with self.assertRaises(ValueError):
            normalize_answers(self.complete(response)[0]["response"], CASE)


class LocalEndpoint(unittest.TestCase):
    def test_round_trip_and_list_models(self):
        with FakeEndpoint() as server, env({oc.BASE_ENV: server.url, oc.KEY_ENV: KEY}):
            r = oc.completion(MODEL, CASE, 10)
            self.assertEqual(oc.list_models(), ["fake/model-1", "fake/model-2"])
        post = server.requests[0]
        self.assertEqual(post["path"], "/v1/chat/completions")
        self.assertEqual(post["headers"]["Authorization"], "Bearer " + KEY)
        self.assertEqual(post["body"]["model"], "fake/model-1")
        self.assertNotIn("PRIVATE_GOLD", json.dumps(post["body"]))
        self.assertEqual(normalize_answers(r["response"], CASE)["q"]["label"], "a")  # the fake picks the first option
        self.assertEqual(r["cost_usd"], .0005)


if __name__ == "__main__":
    unittest.main()
