"""CLI and TypeSafe adapters, with subprocess and HTTP mocked. No model is called."""
import io
import json
import os
import unittest
import urllib.error
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from decision_bench import adapters
from decision_bench.errors import CallError

CASE = {"id": "row-1", "state": {"message": "Please help with billing."},
        "questions": [{"id": "q", "type": "choice", "instructions": "Choose a team.",
                       "options": {"billing": "Billing", "technical": "Technical"}, "gold": "billing",
                       "rationale": "PRIVATE_GOLD"}]}
ANSWER = {"answers": {"q": {"label": "billing", "probabilities": {"billing": .8, "technical": .2}}}}
SONNET = {"id": "s", "provider": "claude-cli", "model": "claude-sonnet-5", "request": {"reasoning_effort": "low"}}
HAIKU = {"id": "h", "provider": "claude-cli", "model": "claude-haiku-4-5-20251001", "request": {"reasoning_effort": None}}
CODEX = {"id": "c", "provider": "codex-cli", "model": "gpt-6-luna", "request": {"reasoning_effort": "low"}}


def which(name):
    return f"/opt/tools/bin/{name}"


class ClaudeAndCodex(unittest.TestCase):
    def run_cli(self, model, stdout, returncode=0, env=None):
        proc = SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")
        with patch.object(adapters.shutil, "which", side_effect=which), \
                patch.object(adapters.subprocess, "run", return_value=proc) as call, \
                patch.dict(os.environ, env or {}):
            return adapters.call(model, CASE, 10), call

    def test_claude_structured_result_preserves_cache_usage_and_model(self):
        response = {"structured_output": ANSWER, "is_error": False, "total_cost_usd": .003, "duration_api_ms": 120,
                    "usage": {"input_tokens": 100, "output_tokens": 20, "cache_read_input_tokens": 50,
                              "cache_creation_input_tokens": 25}, "modelUsage": {"claude-sonnet-5": {}}}
        out, call = self.run_cli(SONNET, json.dumps(response))
        self.assertEqual(out["usage"]["input_tokens"], 175)
        self.assertEqual(out["usage"]["cached_input_tokens"], 50)
        self.assertEqual(out["resolved_model"], "claude-sonnet-5")
        self.assertEqual((out["cost_usd"], out["cost_basis"]), (.003, "provider_reported"))
        self.assertNotIn("PRIVATE_GOLD", call.call_args.kwargs["input"])
        self.assertNotIn("row-1", call.call_args.kwargs["input"])
        cmd = call.call_args.args[0]
        self.assertEqual(cmd[cmd.index("--tools") + 1], "")
        self.assertIn("--safe-mode", cmd)
        self.assertEqual(cmd[cmd.index("--effort") + 1], "low")
        self.assertEqual(out["command"][0], "claude")  # no local install path is recorded
        self.assertEqual(json.loads(out["output_text"]), ANSWER)

    def test_cli_runs_in_an_empty_directory_without_harness_secrets(self):
        env = {"DECISION_BENCH_API_KEY": "harness-key", "TYPESAFE_API_KEY": "ts-key",
               "LAYA_API_KEY": "laya-key", "LAYA_BASE_URL": "http://localhost:8000/v1"}
        response = {"structured_output": ANSWER, "is_error": False, "usage": {}}
        _, call = self.run_cli(SONNET, json.dumps(response), env=env)
        child = call.call_args.kwargs["env"]
        self.assertNotIn("DECISION_BENCH_API_KEY", child)
        self.assertNotIn("TYPESAFE_API_KEY", child)
        self.assertNotIn("LAYA_API_KEY", child)
        self.assertNotIn("LAYA_BASE_URL", child)
        self.assertIn("decision-bench-", str(call.call_args.kwargs["cwd"]))

    def test_effort_comes_from_config(self):
        _, call = self.run_cli(HAIKU, json.dumps({"structured_output": ANSWER, "usage": {}, "is_error": False}))
        self.assertNotIn("--effort", call.call_args.args[0])

    def test_missing_cli_is_a_config_error(self):
        with patch.object(adapters.shutil, "which", return_value=None):
            with self.assertRaises(CallError) as cm:
                adapters.call(SONNET, CASE, 10)
        self.assertEqual(cm.exception.status, "config_missing")
        self.assertFalse(cm.exception.retryable)

    def test_claude_nonzero_json_auth_error_remains_readable(self):
        stdout = json.dumps({"is_error": True, "result": "Not logged in · Please run /login", "usage": {}})
        with self.assertRaises(CallError) as cm:
            self.run_cli(SONNET, stdout, returncode=1)
        self.assertEqual(cm.exception.status, "auth_missing")
        self.assertEqual(str(cm.exception), "Not logged in · Please run /login")
        self.assertFalse(cm.exception.retryable)

    def test_failed_claude_call_retains_reported_paid_usage(self):
        response = {"is_error": True, "result": "Structured output retries exhausted", "total_cost_usd": .02,
                    "usage": {"input_tokens": 70, "cache_read_input_tokens": 30, "output_tokens": 20},
                    "modelUsage": {"claude-sonnet-5": {}}}
        with self.assertRaises(CallError) as cm:
            self.run_cli(SONNET, json.dumps(response), returncode=1)
        self.assertEqual(cm.exception.metadata["cost_usd"], .02)
        self.assertEqual(cm.exception.metadata["usage"]["input_tokens"], 100)
        self.assertEqual(cm.exception.status, "model_error")

    def test_codex_tool_use_is_a_protocol_failure(self):
        events = [{"type": "item.completed", "item": {"type": "command_execution", "command": "cat gold.json"}},
                  {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(ANSWER)}},
                  {"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 20}}]
        with self.assertRaises(CallError) as cm:
            self.run_cli(CODEX, "\n".join(json.dumps(e) for e in events))
        self.assertEqual(cm.exception.status, "protocol_violation")

    def test_codex_reports_usage_and_leaves_cost_to_the_price_table(self):
        events = [{"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(ANSWER)}},
                  {"type": "turn.completed", "usage": {"input_tokens": 1000, "cached_input_tokens": 800, "output_tokens": 100}}]
        out, call = self.run_cli(CODEX, "\n".join(json.dumps(e) for e in events))
        self.assertIsNone(out["cost_usd"])
        self.assertIsNone(out["resolved_model"])
        self.assertEqual(out["usage"]["cached_input_tokens"], 800)
        self.assertIn('model_reasoning_effort="low"', call.call_args.args[0])
        self.assertNotIn("PRIVATE_GOLD", call.call_args.kwargs["input"])


class TypeSafe(unittest.TestCase):
    MODEL = {"id": "jev", "provider": "typesafe", "model": "jev-1.13.0"}

    def test_requires_key(self):
        with patch.object(adapters, "env_value", return_value=None):
            with self.assertRaises(CallError) as cm:
                adapters.call(self.MODEL, CASE, 10)
        self.assertEqual(cm.exception.status, "auth_missing")

    def test_payload_and_native_answer(self):
        body = json.dumps({"model": "jev-1.13.0", "answers": {"q": {"choice": "billing",
                           "probabilities": {"billing": .9, "technical": .1}}}, "usage": {"input_tokens": 50}})
        response = MagicMock(status=200)
        response.read.return_value = body.encode()
        response.__enter__.return_value = response
        opener = MagicMock()
        opener.open.return_value = response
        with patch.object(adapters, "env_value", return_value="ts-test-key"), \
                patch.object(adapters.urllib.request, "build_opener", return_value=opener):
            out = adapters.call(self.MODEL, CASE, 10)
        req = opener.open.call_args.args[0]
        sent = json.loads(req.data)
        self.assertEqual(req.full_url, adapters.TYPESAFE_URL)
        self.assertNotIn("PRIVATE_GOLD", req.data.decode())
        self.assertEqual(sent["questions"]["q"]["criteria"], CASE["questions"][0]["options"])
        self.assertEqual(out["source"], "native")
        self.assertEqual(out["usage"]["input_tokens"], 50)
        self.assertNotIn("ts-test-key", json.dumps(out))

    def test_http_error_body_does_not_echo_key(self):
        error = urllib.error.HTTPError(adapters.TYPESAFE_URL, 401, "Unauthorized", {}, io.BytesIO(b"bad key ts-test-key"))
        opener = MagicMock()
        opener.open.side_effect = error
        with patch.object(adapters, "env_value", return_value="ts-test-key"), \
                patch.object(adapters.urllib.request, "build_opener", return_value=opener):
            with self.assertRaises(CallError) as cm:
                adapters.call(self.MODEL, CASE, 10)
        self.assertNotIn("ts-test-key", str(cm.exception))
        self.assertFalse(cm.exception.retryable)


class Laya(unittest.TestCase):
    MODEL = {"id": "laya", "provider": "laya", "model": "convaiinnovations/laya"}

    def test_local_endpoint_sends_native_question_without_key(self):
        body = json.dumps({"model": "convaiinnovations/laya", "answers": {"q": {"choice": "billing",
                          "probabilities": {"billing": .9, "technical": .1}}}, "usage": {"input_tokens": 42}})
        response = MagicMock(status=200)
        response.read.return_value = body.encode()
        response.__enter__.return_value = response
        opener = MagicMock()
        opener.open.return_value = response
        with patch.object(adapters, "env_value", side_effect={"LAYA_BASE_URL": "http://localhost:8000/v1"}.get), \
                patch.object(adapters.urllib.request, "build_opener", return_value=opener):
            out = adapters.call(self.MODEL, CASE, 10)
        req = opener.open.call_args.args[0]
        self.assertEqual(req.full_url, "http://localhost:8000/v1/systemone")
        self.assertNotIn("Authorization", req.headers)
        self.assertNotIn("PRIVATE_GOLD", req.data.decode())
        self.assertEqual(json.loads(req.data)["questions"]["q"]["criteria"], CASE["questions"][0]["options"])
        self.assertEqual(out["source"], "native")
        self.assertEqual(out["usage"]["input_tokens"], 42)

    def test_remote_endpoint_requires_key_and_rejects_insecure_http(self):
        with patch.object(adapters, "env_value", side_effect={"LAYA_BASE_URL": "https://api.impossibl.com/v1"}.get):
            with self.assertRaises(CallError) as cm:
                adapters.call(self.MODEL, CASE, 10)
        self.assertEqual(cm.exception.status, "auth_missing")
        with patch.object(adapters, "env_value", side_effect={"LAYA_BASE_URL": "http://api.impossibl.com/v1"}.get):
            with self.assertRaises(CallError) as cm:
                adapters.laya_endpoint()
        self.assertEqual(cm.exception.status, "config_invalid")


if __name__ == "__main__":
    unittest.main()
