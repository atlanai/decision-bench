import json
import unittest
from unittest.mock import MagicMock, patch

from decision_bench import adapters, celeris, openai_compat
from decision_bench.errors import CallError

CASE = {"id": "row-1", "state": {"message": "Please help with billing."},
        "questions": [{"id": "q", "type": "choice", "instructions": "Route it.", "gold": "PRIVATE_GOLD",
                       "options": {"billing": "Billing", "technical": "Technical"},
                       "option_order": ["technical", "billing"]}]}
MODEL = {"id": "celeris-1.1-decision", "provider": "celeris", "model": "celeris-1.1-decision", "vision": True}


def opener_for(body):
    response = MagicMock(status=200)
    response.read.return_value = json.dumps(body).encode()
    response.__enter__.return_value = response
    opener = MagicMock()
    opener.open.return_value = response
    return opener


class Celeris(unittest.TestCase):
    BODY = {"model": "celeris-1.1-decision", "answers": {"q": {"type": "choice", "choice": "billing",
            "probabilities": {"billing": .9, "technical": .1}, "confidence": .8}}, "usage": {"input_tokens": 42}}

    def call(self, images):
        opener = opener_for(self.BODY)
        with patch.object(celeris, "env_value", side_effect={"CELERIS_API_KEY": "test-celeris-key"}.get), \
                patch.object(adapters, "image_assets", return_value=images), \
                patch.object(adapters.urllib.request, "build_opener", return_value=opener):
            out = adapters.call(MODEL, CASE, 10)
        return out, opener.open.call_args.args[0]

    def test_sends_native_question_with_images_under_x_celeris(self):
        out, req = self.call([("image/png", b"image")])
        sent = json.loads(req.data)
        self.assertEqual(req.full_url, celeris.URL)
        self.assertEqual(req.headers["Authorization"], "Bearer test-celeris-key")
        self.assertNotIn("PRIVATE_GOLD", req.data.decode())
        self.assertEqual(list(sent["questions"]["q"]["criteria"]), ["technical", "billing"])
        self.assertNotIn("images", sent)
        self.assertEqual(sent["x_celeris"]["images"], {"image_1": "data:image/png;base64,aW1hZ2U="})
        self.assertEqual(out["images_sent"], 1)
        self.assertNotIn("aW1hZ2U=", json.dumps(out["payload"]))
        self.assertEqual(out["source"], "native")
        self.assertEqual(out["usage"]["input_tokens"], 42)

    def test_text_row_sends_no_extension(self):
        out, req = self.call([])
        self.assertNotIn("x_celeris", json.loads(req.data))
        self.assertEqual(out["images_sent"], 0)

    def test_key_required(self):
        with patch.object(celeris, "env_value", return_value=None):
            with self.assertRaises(CallError) as cm:
                adapters.call(MODEL, CASE, 10)
        self.assertEqual(cm.exception.status, "auth_missing")

    def test_sends_the_configured_model(self):
        _, req = self.call([])
        self.assertEqual(json.loads(req.data)["model"], "celeris-1.1-decision")

    def test_api_model_rejected(self):
        with patch.object(celeris, "env_value", return_value="test-celeris-key"):
            with self.assertRaises(CallError) as cm:
                adapters.call(MODEL, CASE, 10, api_model="celeris-1-decision")
        self.assertEqual(cm.exception.status, "config_invalid")

    def test_key_redacted(self):
        with patch.object(openai_compat, "env_value", side_effect={"CELERIS_API_KEY": "test-celeris-key"}.get):
            self.assertNotIn("test-celeris-key", openai_compat.redact("key test-celeris-key"))


class SharedSystemOnePayload(unittest.TestCase):
    """Other System One adapters still send images in the top-level `images` list."""
    IMAGES = [("image/png", b"image")]

    def sent(self, model, env):
        opener = opener_for({"model": model["model"], "answers": {"q": {"type": "choice", "choice": "billing",
                            "probabilities": {"billing": .9, "technical": .1}}}, "usage": {"input_tokens": 42}})
        with patch.object(adapters, "env_value", side_effect=env.get), \
                patch.object(adapters, "image_assets", return_value=self.IMAGES), \
                patch.object(adapters.urllib.request, "build_opener", return_value=opener):
            out = adapters.call(model, CASE, 10)
        return json.loads(opener.open.call_args.args[0].data), out

    def test_vision_laya_sends_top_level_images(self):
        sent, out = self.sent({"id": "laya", "provider": "laya", "model": "convaiinnovations/laya", "vision": True},
                              {"LAYA_BASE_URL": "http://localhost:8000/v1"})
        self.assertEqual(sent["images"], ["data:image/png;base64,aW1hZ2U="])
        self.assertNotIn("x_celeris", sent)
        self.assertNotIn("aW1hZ2U=", json.dumps(out["payload"]))

    def test_vision_typesafe_sends_top_level_images(self):
        sent, _ = self.sent({"id": "t", "provider": "typesafe", "model": "jev", "vision": True},
                            {"TYPESAFE_API_KEY": "test-typesafe-key"})
        self.assertEqual(sent["images"], ["data:image/png;base64,aW1hZ2U="])

    def test_text_model_sends_no_images(self):
        sent, _ = self.sent({"id": "laya", "provider": "laya", "model": "convaiinnovations/laya"},
                            {"LAYA_BASE_URL": "http://localhost:8000/v1"})
        self.assertNotIn("images", sent)


if __name__ == "__main__":
    unittest.main()
