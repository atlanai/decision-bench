"""The server and shared provider path, using a fake model and a local HTTP server only."""
import copy
from concurrent.futures import ThreadPoolExecutor
from http.server import HTTPServer
import importlib.util
import json
from pathlib import Path
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from decision_bench import adapters, corpus, quyet

spec = importlib.util.spec_from_file_location("serve_quyet", Path(__file__).resolve().parents[1] / "scripts/serve_quyet.py")
serve = importlib.util.module_from_spec(spec)
spec.loader.exec_module(serve)


class QuestionError(ValueError):
    pass


class Model:
    def __init__(self):
        self.calls = []
        self.error = None
        self.active = self.peak_active = 0
        self.delay = 0
        self.response = {"model": "Quyet-1.2-Large", "answers": {
            "q": {"type": "choice", "choice": "b", "confidence": .75,
                  "probabilities": {"b": .75, "a": .25}}},
            "usage": {"input_tokens": 31, "output_tokens": 0}, "warnings": []}

    def predict(self, state, questions, *, strict):
        self.calls.append((state, questions, strict))
        if self.error:
            raise self.error
        self.active += 1
        self.peak_active = max(self.peak_active, self.active)
        time.sleep(self.delay)
        self.active -= 1
        return self.response


class Server(unittest.TestCase):
    def setUp(self):
        self.model = Model()
        self.server = HTTPServer(("127.0.0.1", 0), serve.handler(self.model, QuestionError, "test-key"))
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .01})
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.body = {"model": serve.MODEL, "state": {"text": "Do not alter this."}, "questions": {
            "q": {"type": "choice", "instructions": "Choose exactly.", "criteria": {"b": "Second", "a": "First"}}}}

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()

    def post(self, body, key="test-key", path="/v1/systemone"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data,
                                     headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
        try:
            response = urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            return response.status, json.loads(response.read())

    def test_request_and_package_response_are_unchanged(self):
        original = copy.deepcopy(self.model.response)
        status, result = self.post(self.body)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(result.pop("latency_ms"), 0)
        self.assertEqual(result, original)
        self.assertEqual(self.model.response, original)
        self.assertEqual(self.model.calls, [(self.body["state"], self.body["questions"], True)])
        self.assertEqual(list(self.model.calls[0][1]["q"]["criteria"]), ["b", "a"])

    def test_shared_systemone_payload_and_native_readout(self):
        case = {"id": "private-row-id", "state": self.body["state"], "questions": [{
            "id": "q", "type": "choice", "instructions": "Choose exactly.",
            "options": {"a": "First", "b": "Second"}, "option_order": ["b", "a"],
            "gold": "b", "rationale": "NOT_MODEL_INPUT"}], "images": ["not-sent"]}
        env = {"QUYET_BASE_URL": self.base, "QUYET_API_KEY": "test-key"}
        with patch.object(quyet, "env_value", side_effect=env.get):
            result = adapters.call({"provider": "quyet", "model": serve.MODEL, "vision": False}, case, 5)
        expected = {"q": {"type": "choice", "instructions": corpus.JUDGMENT_POLICY + "Choose exactly.",
                          "criteria": {"b": "Second", "a": "First"}}}
        self.assertEqual(self.model.calls, [(self.body["state"], expected, True)])
        self.assertEqual(result["payload"], {"model": serve.MODEL, "state": self.body["state"], "questions": expected})
        self.assertEqual(result["response"]["answers"], self.model.response["answers"])
        self.assertEqual(result["usage"]["input_tokens"], 31)
        self.assertEqual(result["usage"]["output_tokens"], 0)
        self.assertEqual(result["images_sent"], 0)
        self.assertIsNone(result["cost_usd"])
        self.assertGreaterEqual(result["provider_duration_ms"], 0)

    def test_invalid_bearer_rejected_before_model(self):
        self.assertEqual(self.post(self.body, key="wrong")[0], 401)
        self.assertEqual(self.model.calls, [])

    def test_images_rejected_even_when_empty(self):
        for images in ([], None, ["image"]):
            with self.subTest(images=images):
                status, result = self.post({**self.body, "images": images})
                self.assertEqual(status, 400)
                self.assertIn("images are not supported", result["error"])
        self.assertEqual(self.model.calls, [])

    def test_question_error_is_http_400_with_message(self):
        self.model.error = QuestionError("input exceeds 32768 tokens; no truncation")
        self.assertEqual(self.post(self.body), (400, {"error": str(self.model.error)}))

    def test_unexpected_failure_is_not_substituted(self):
        self.model.error = RuntimeError("test model failed")
        with patch.object(serve.traceback, "print_exc") as log:
            status, response = self.post(self.body)
        self.assertEqual(status, 500)
        self.assertEqual(response, {"error": "model inference failed; see server log"})
        log.assert_called_once()

    def test_bad_json_shape_and_wrong_model(self):
        for body in (b"{broken", [], {**self.body, "model": "other"}, {**self.body, "extra": 1}, {}):
            with self.subTest(body=body):
                self.assertEqual(self.post(body)[0], 400)
        self.assertEqual(self.model.calls, [])

    def test_unknown_path(self):
        self.assertEqual(self.post(self.body, path="/other")[0], 404)
        self.assertEqual(self.model.calls, [])

    def test_single_request_at_a_time(self):
        self.model.delay = .02
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(self.post, [self.body] * 3))
        self.assertTrue(all(status == 200 for status, _ in results))
        self.assertEqual(self.model.peak_active, 1)
        self.assertEqual(len(self.model.calls), 3)


class BindPolicy(unittest.TestCase):
    def test_loopback_does_not_need_a_key(self):
        for host in ("127.0.0.1", "127.0.0.2", "::1", "localhost"):
            serve.require_key(host, "")

    def test_non_loopback_needs_a_key(self):
        for host in ("0.0.0.0", "::", "server.example"):
            with self.subTest(host=host), self.assertRaisesRegex(ValueError, "QUYET_API_KEY"):
                serve.require_key(host, "")
            serve.require_key(host, "test-key")


if __name__ == "__main__":
    unittest.main()
