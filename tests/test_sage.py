"""Sage contract and credential boundary tests; no live calls."""
import io
import json
import unittest
import urllib.error
from unittest.mock import MagicMock, patch
from decision_bench import adapters, sage
from decision_bench.errors import CallError
from decision_bench.scoring import normalize_answers
from test_adapters import CASE

MODEL = {"id": "sage", "provider": "sage", "model": "levanto-sage-v1.1"}


class SageTests(unittest.TestCase):
    def invoke(self, chosen='billing', probs=None, error=None):
        body = {"id": "q", "kind": "choice", "result": {"chosen": chosen, "probabilities": probs or [
            {"option": "billing", "probability": .8}, {"option": "technical", "probability": .4}]},
            "meta": {"model": "levanto-sage-v1.1", "latency_ms": 123}, "debug": "test-sage-secret"}
        response = MagicMock(status=200)
        response.read.return_value = json.dumps(body).encode()
        response.__enter__.return_value = response
        opener = MagicMock()
        opener.open.return_value = response
        if error:
            opener.open.side_effect = error
        with patch.object(sage, 'env_value', return_value='test-sage-secret'), patch.object(
                sage.urllib.request, 'build_opener', return_value=opener) as build:
            out = adapters.call(MODEL, CASE, 10)
        self.assertEqual(build.call_args.args, (sage.openai_compat.NoRedirect,))
        return out, opener.open.call_args.args[0]

    def test_payload_conversion_and_redaction(self):
        out, req = self.invoke()
        self.assertEqual(req.full_url, sage.URL)
        self.assertEqual(req.get_header('Authorization'), 'Bearer test-sage-secret')
        payload = json.loads(req.data)
        self.assertEqual(payload['reasoning'], 'auto')
        self.assertEqual(payload['question']['kind'], 'choice')
        self.assertNotIn('PRIVATE_GOLD', req.data.decode())
        self.assertNotIn('row-1', req.data.decode())
        self.assertNotIn('grounding', req.data.decode())
        self.assertNotIn('test-sage-secret', json.dumps(out))
        normalized = normalize_answers(out['response'], CASE, out['source'])
        self.assertAlmostEqual(normalized['q']['probabilities']['billing'], 2/3)
        self.assertEqual(normalized['q']['probability_source'], 'native-renormalized')
        self.assertEqual(out['raw']['result']['probabilities'][0]['probability'], .8)
        self.assertEqual(out['provider_duration_ms'], 123)
        self.assertIsNone(out['cost_usd'])

    def test_abstention_is_not_replaced(self):
        out, _ = self.invoke(chosen=None)
        self.assertIsNone(out['response']['answers']['q']['label'])
        with self.assertRaises(ValueError):
            normalize_answers(out['response'], CASE, out['source'])

    def test_invalid_probability_rejected(self):
        with self.assertRaises(CallError):
            self.invoke(probs=[{'option': 'billing', 'probability': -1},
                               {'option': 'technical', 'probability': 2}])

    def test_credit_error_is_not_retried_and_key_is_redacted(self):
        error = urllib.error.HTTPError(sage.URL, 402, 'Payment required', {},
                                      io.BytesIO(b'test-sage-secret insufficient credits'))
        with self.assertRaises(CallError) as ctx:
            self.invoke(error=error)
        self.assertEqual(ctx.exception.status, 402)
        self.assertFalse(ctx.exception.retryable)
        self.assertNotIn('test-sage-secret', str(ctx.exception))

    def test_missing_key_and_override(self):
        with patch.object(sage, 'env_value', return_value=None):
            with self.assertRaises(CallError) as ctx:
                sage.completion(MODEL, CASE, 10)
            self.assertEqual(ctx.exception.status, 'auth_missing')
        with self.assertRaises(CallError):
            sage.completion(MODEL, CASE, 10, 'another-model')
