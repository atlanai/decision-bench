"""Native decisions, evidence boundaries, accounting, and credential isolation."""
import json
import unittest
from unittest.mock import MagicMock, patch

from decision_bench import adapters, openai_compat, openrouter_decisions, runner
from decision_bench.errors import CallError
from test_adapters import CASE
from fixtures import repo


class OpenRouterDecisions(unittest.TestCase):
    MODEL = {"id": "decider", "provider": "openrouter-decisions",
             "model": "perplexity/pplx-decider-v1.1-27b", "vision": True}

    def test_native_image_request_preserves_probabilities_and_paid_usage(self):
        key = "synthetic-openrouter-key"
        answer = {"choice": "billing", "probabilities": {"billing": .901, "technical": .099}}
        body = {"model": self.MODEL["model"], "answers": {"q": answer},
                "usage": {"input_tokens": 500, "output_tokens": 0, "cost": .00001}, "debug": key}
        response = MagicMock(status=200)
        response.read.return_value = json.dumps(body).encode()
        response.__enter__.return_value = response
        with repo({"OPENROUTER_API_KEY": key}), \
                patch.object(adapters.urllib.request, "build_opener") as opener, \
                patch.object(openrouter_decisions, "image_assets", return_value=[("image/png", b"image")]):
            opener.return_value.open.return_value = response
            result = adapters.call(self.MODEL, CASE, 10)
        request = opener.return_value.open.call_args.args[0]
        sent = json.loads(request.data)
        self.assertEqual(request.full_url, openrouter_decisions.URL)
        self.assertEqual(request.get_header("Authorization"), "Bearer " + key)
        self.assertEqual(sent["state"][0], json.dumps(CASE["state"]))
        self.assertEqual(sent["state"][1]["image_url"]["url"], "data:image/png;base64,aW1hZ2U=")
        self.assertNotIn("PRIVATE_GOLD", request.data.decode())
        self.assertNotIn("row-1", request.data.decode())
        self.assertNotIn(key, json.dumps(result))
        self.assertEqual(result["response"]["answers"]["q"], answer)
        self.assertEqual((result["images_sent"], result["source"]), (1, "native"))
        self.assertEqual((result["cost_usd"], result["cost_basis"]), (.00001, "provider_reported"))
        self.assertEqual(result["usage"]["output_tokens"], 0)

    def test_preflight_requires_own_key_and_persistence_redacts_it(self):
        with repo({"DECISION_BENCH_API_KEY": "synthetic-" + "other-key"}):
            with self.assertRaises(CallError) as error:
                runner.preflight(self.MODEL)
            self.assertEqual(error.exception.status, "auth_missing")
        with repo({"OPENROUTER_API_KEY": "synthetic-" + "openrouter-key"}):
            runner.preflight(self.MODEL)
            self.assertEqual(openai_compat.redact("synthetic-openrouter-key"), "[REDACTED]")
        self.assertIn("OPENROUTER_API_KEY", adapters.HARNESS_SECRETS)
