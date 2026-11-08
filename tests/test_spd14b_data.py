import importlib.util
from pathlib import Path
import unittest
spec = importlib.util.spec_from_file_location('spddata', Path(__file__).parents[1] / 'scripts/prepare_spd14b_data.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
class SPDDataTests(unittest.TestCase):
    def test_nested_final_box(self):
        ref = r'Earlier \boxed{1}; final \boxed{\frac{2}{3}}.'
        self.assertEqual(ref[slice(*m.boxed_span(ref))], r'\frac{2}{3}')
        with self.assertRaises(ValueError):
            m.boxed_span(r'bad \boxed{abc')
    def test_overlap_normalizes_unicode_whitespace(self):
        with self.assertRaises(ValueError):
            m.assert_disjoint({'train': [{'original_prompt': '\uff21  b'}], 'eval': [{'original_prompt': 'A\nb'}]})
    def test_safety_stratified_preserves_response(self):
        rows = [{'instruction': f'Question {i}', 'label': str(i % 2), 'response': '<think>Reasoning</think>\nAnswer  '} for i in range(100)]
        rows.append(dict(rows[0]))
        sizes = {'train': 20, 'calibration': 10, 'validation': 10, 'eval': 10}
        splits, audit = m.safety_splits(rows, sizes, 42)
        self.assertEqual(audit['duplicate_prompts'], 1)
        m.assert_disjoint(splits)
        for data in splits.values():
            self.assertEqual(sum(r['label'] == '0' for r in data), len(data)//2)
            self.assertTrue(all(r['reference'] == rows[0]['response'] for r in data))
        self.assertEqual(splits, m.safety_splits(rows, sizes, 42)[0])
    def test_qa_span_letter_only(self):
        row = m.add_spans({'reference': 'The answer is (C).', 'answer': 'C'}, 'qa')
        a,b = row['calibration_spans'][0]
        self.assertEqual(row['reference'][a:b], 'C')
if __name__ == '__main__':
    unittest.main()
