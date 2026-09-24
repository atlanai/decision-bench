"""Viewer optimisation must preserve every row and its published answers."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from decision_bench.viewer import write_viewer


class ViewerTests(unittest.TestCase):
    def test_details_reconstruct_source_without_mutation(self):
        source = {'corpus_sha256': 'corpus-v1', 'runs': [], 'cases': [
            {'id': 'row/../unsafe', 'state': {'text': '<record>'}, 'provenance': {'id': 'original'},
             'questions': [{'gold': 'A', 'options': {'A': 'Yes'}}]},
            {'id': 'unanswered', 'state': {}, 'questions': []}],
            'results': [{'run_id': 'run-1', 'case_id': 'row/../unsafe', 'output_text': 'raw answer',
                         'tokens': {'input': 5, 'output': 2, 'provider_detail': {'cached': 0}},
                         'scores': [{'label': 'A', 'correct': True, 'probabilities': {'A': 1}}]}]}
        original = copy.deepcopy(source)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = write_viewer(source, root)
            self.assertEqual(source, original)
            self.assertEqual(json.loads((root / 'viewer.json').read_text()), index)
            for summary, full in zip(index['cases'], source['cases']):
                self.assertNotIn('state', summary)
                self.assertRegex(summary['detail_url'], r'^details/[a-f0-9]{64}\.json$')
                detail = json.loads((root / summary['detail_url']).read_text())
                self.assertEqual(detail['case'], full)
                self.assertEqual(detail['corpus_sha256'], source['corpus_sha256'])
                self.assertEqual(detail['results'], [r for r in source['results'] if r['case_id'] == full['id']])
            result = index['results'][0]
            self.assertNotIn('output_text', result)
            self.assertNotIn('probabilities', result['scores'][0])
            self.assertEqual(result['scores'][0]['correct'], True)
            self.assertEqual(result['tokens'], {'input': 5, 'output': 2})
            repeat = write_viewer(source, root)
            self.assertEqual(repeat, index)
            source['results'][0]['output_text'] = 'corrected raw answer'
            updated = write_viewer(source, root)
            self.assertNotEqual(updated['cases'][0]['detail_url'], index['cases'][0]['detail_url'])
            self.assertEqual(updated['cases'][1]['detail_url'], index['cases'][1]['detail_url'])
