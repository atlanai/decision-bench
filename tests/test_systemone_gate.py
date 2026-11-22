"""The bearer key and model gate that the Modal System One servers (serve_prism.py, serve_amos.py) run on every request."""
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("systemone_gate",
                                              Path(__file__).resolve().parents[1] / "scripts/systemone_gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

KEY = "k" * 24
MODEL = "owner/model@revision"


class RequireKey(unittest.TestCase):
    def test_missing_key_stops_the_deploy(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(SystemExit) as raised:
            gate.require_key("SERVE_API_KEY")
        self.assertIn("SERVE_API_KEY", str(raised.exception))

    def test_short_key_stops_the_deploy_without_echoing_it(self):
        with patch.dict(os.environ, {"SERVE_API_KEY": "s" * 23}), self.assertRaises(SystemExit) as raised:
            gate.require_key("SERVE_API_KEY")
        self.assertNotIn("s" * 23, str(raised.exception))

    def test_key_of_24_characters_is_returned(self):
        with patch.dict(os.environ, {"SERVE_API_KEY": KEY}):
            self.assertEqual(gate.require_key("SERVE_API_KEY"), KEY)


class Refusal(unittest.TestCase):
    def test_right_key_and_model_is_answered(self):
        self.assertIsNone(gate.refusal(f"Bearer {KEY}", {"model": MODEL}, KEY, MODEL))

    def test_missing_wrong_or_unprefixed_key_is_401(self):
        for authorization in ("", f"Bearer {'x' * 24}", KEY, f"bearer {KEY}", f"Bearer {KEY} "):
            with self.subTest(authorization=authorization):
                self.assertEqual(gate.refusal(authorization, {"model": MODEL}, KEY, MODEL),
                                 (401, "invalid bearer key"))

    def test_other_or_missing_model_is_422_naming_the_served_model(self):
        for body in ({"model": "other"}, {}):
            with self.subTest(body=body):
                self.assertEqual(gate.refusal(f"Bearer {KEY}", body, KEY, MODEL),
                                 (422, f"this endpoint serves {MODEL}"))

    def test_key_is_checked_before_the_model(self):
        self.assertEqual(gate.refusal("", {"model": "other"}, KEY, MODEL)[0], 401)


if __name__ == "__main__":
    unittest.main()
