"""Drex provider configuration and native System One request."""
import json
import unittest
from unittest.mock import MagicMock, patch

from decision_bench import adapters, drex, openai_compat, runner
from decision_bench.errors import CallError
from test_adapters import CASE
from test_runner import args

import fixtures


class Drex(unittest.TestCase):
    MODEL = {"id": "drex-max", "provider": "drex", "model": "drex-max", "vision": True}

    def test_endpoint_requires_https_and_key(self):
        with patch.object(drex, "env_value", side_effect={"DREX_BASE_URL": "https://console.example/v1"}.get):
            self.assertEqual(drex.endpoint(), "https://console.example/v1/systemone")
            with self.assertRaises(CallError) as cm:
                drex.api_key()
            self.assertEqual(cm.exception.status, "auth_missing")
        for base in ("http://console.example/v1", "https://user:pass@console.example/v1",
                     "https://console.example/v1?key=x", "https://console.example/v2"):
            with self.subTest(base=base), patch.object(drex, "env_value", return_value=base):
                with self.assertRaises(CallError) as cm:
                    drex.endpoint()
                self.assertEqual(cm.exception.status, "config_invalid")

    def test_native_choice_request_and_redaction(self):
        key = "synthetic-drex-key"
        base = "https://console.example/v1"
        body = {"model": "drex-max", "answers": {"q": {"choice": "billing",
                "probabilities": {"billing": 0.9, "technical": 0.1}}},
                "usage": {"input_tokens": 42, "output_tokens": 3}, "debug": key}
        response = MagicMock(status=200)
        response.read.return_value = json.dumps(body).encode()
        response.__enter__.return_value = response
        opener = MagicMock()
        opener.open.return_value = response
        settings = {"DREX_BASE_URL": base, "NACE_API_KEY": key}
        with patch.object(drex, "env_value", side_effect=settings.get), \
                patch.object(adapters.urllib.request, "build_opener", return_value=opener):
            out = adapters.call(self.MODEL, CASE, 10)
        req = opener.open.call_args.args[0]
        self.assertEqual(req.full_url, base + "/systemone")
        self.assertEqual(req.headers["Authorization"], "Bearer " + key)
        self.assertEqual(json.loads(req.data)["model"], "drex-max")
        self.assertNotIn("PRIVATE_GOLD", req.data.decode())
        self.assertEqual(out["source"], "native")
        self.assertEqual(out["response"]["answers"]["q"]["choice"], "billing")
        self.assertNotIn(key, json.dumps(out))

    def test_preflight_and_endpoint_id(self):
        with fixtures.repo({"DREX_BASE_URL": "https://console.example/v1", "NACE_API_KEY": "synthetic-drex-key"}):
            with patch("decision_bench.config.load_models", return_value=[self.MODEL]):
                _, _, cfg, _ = runner.prepare(args(model="drex-max", run_id=None))
            self.assertEqual(cfg["provider"], "drex")
            self.assertEqual(cfg["endpoint_id"], openai_compat.endpoint_id("https://console.example/v1/systemone"))
            self.assertNotIn("console.example", json.dumps(cfg))


if __name__ == "__main__":
    unittest.main()
