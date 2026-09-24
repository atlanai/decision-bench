"""Native Tev1 transport and honest accuracy-only scoring."""
import json
import unittest
from unittest.mock import MagicMock, patch
from decision_bench import adapters, tev1, results, metrics
from decision_bench.scoring import normalize_answers, score
from decision_bench.errors import CallError
from test_adapters import CASE

MODEL = {'provider': 'tev1', 'model': 'together/Tev1-4B-experimental'}

class Tev1Tests(unittest.TestCase):
    def invoke(self, content='B'):
        response = MagicMock(status=200)
        response.read.return_value = json.dumps({'model': MODEL['model'], 'choices': [
            {'message': {'content': content}, 'finish_reason': 'stop', 'logprobs': {'content': []}}],
            'usage': {'prompt_tokens': 100, 'completion_tokens': 1}, 'debug': 'test-together-key'}).encode()
        response.__enter__.return_value = response
        opener = MagicMock()
        opener.open.return_value = response
        with patch.object(tev1, 'env_value', return_value='test-together-key'), patch.object(
                tev1.urllib.request, 'build_opener', return_value=opener) as build:
            result = adapters.call(MODEL, CASE, 20)
        self.assertEqual(build.call_args.args, (tev1.openai_compat.NoRedirect,))
        return result, opener.open.call_args.args[0]

    def test_native_payload_maps_letter_and_omits_gold(self):
        out, req = self.invoke()
        payload = json.loads(req.data)
        decision = json.loads(payload['messages'][1]['content'])
        expected = next(o['key'] for o in decision['options'] if o['label'] == 'B')
        answers = normalize_answers(out['response'], CASE, out['source'])
        self.assertEqual(answers['q']['label'], expected)
        self.assertIsNone(answers['q']['probabilities'])
        self.assertNotIn('brier', score(CASE, answers)[0])
        self.assertNotIn('confidence', score(CASE, answers)[0])
        self.assertNotIn('PRIVATE_GOLD', req.data.decode())
        self.assertNotIn('row-1', req.data.decode())
        self.assertEqual(payload['chat_template_kwargs'], {'enable_thinking': False})
        self.assertEqual(payload['response_format'], {'type': 'regex', 'pattern': '(A|B)'})
        self.assertEqual(req.full_url, tev1.URL)
        self.assertNotIn('test-together-key', json.dumps(out))
        self.assertEqual(out['usage']['input_tokens'], 100)

    def test_explanation_is_invalid_not_silently_parsed(self):
        out, _ = self.invoke('B because billing')
        with self.assertRaises(ValueError):
            normalize_answers(out['response'], CASE, out['source'])

    def test_missing_credential_fails_before_network(self):
        with patch.object(tev1, 'env_value', return_value=None):
            with self.assertRaises(CallError) as ctx:
                tev1.completion(MODEL, CASE, 10)
            self.assertEqual(ctx.exception.status, 'auth_missing')

    def test_label_only_export_and_summary_keep_calibration_unavailable(self):
        out, _ = self.invoke()
        answers = normalize_answers(out['response'], CASE, out['source'])
        record = {'case_id': CASE['id'], 'status': 'ok', 'answers': answers,
                  'scores': score(CASE, answers), 'duration_ms': 100, 'output_text': 'B'}
        public = results.predictions_from_run([record], [], {CASE['id']: {**CASE, 'task': 'routing', 'category': 'support'}})
        self.assertIsNone(public[0]['confidence'])
        self.assertIsNone(public[0]['probabilities'])
        summary = metrics.summarize([record], {CASE['id']: {**CASE, 'task': 'routing', 'category': 'support'}}, [])
        self.assertEqual(summary['operational_errors'], 0)
        self.assertIsNone(summary['brier'])
        self.assertIsNone(summary['log_loss'])
        self.assertEqual(summary['reliability']['valid_count'], 0)
