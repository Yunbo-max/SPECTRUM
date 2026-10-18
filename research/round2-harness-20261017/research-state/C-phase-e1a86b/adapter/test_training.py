"""Authored, NOT RUN. Numeric software fixtures are not benchmark cases/scorers."""
import json
import tempfile
import unittest
from pathlib import Path

from training_instrumented import (
    accumulation_divisor, plan_token_exposure, target_breakdown,
    Telemetry, validate_training_contract,
)


class TokenExposureTests(unittest.TestCase):
    def test_whole_records_all_exposed_and_strict_overshoot(self):
        # Token counts only: no fabricated executable program or scoring sample.
        counts = [3, 7, 2, 11]
        indices, stats = plan_token_exposure(counts, 100, seed=44)
        self.assertEqual(set(indices), set(range(4)))
        self.assertGreaterEqual(sum(counts[i] for i in indices), 100)
        self.assertLess(sum(counts[i] for i in indices), 111)
        self.assertEqual(stats['record_exposure_counts'],
                         [indices.count(i) for i in range(4)])
        for start in range(0, len(indices) - 3, 4):
            self.assertEqual(sorted(indices[start:start + 4]), list(range(4)))
        self.assertEqual((indices, stats), plan_token_exposure(counts, 100, seed=44))
        self.assertTrue(stats['full_permutation_sha256'])

    def test_exact_full_corpus(self):
        indices, stats = plan_token_exposure([2, 3, 5], 10, seed=44)
        self.assertEqual(sorted(indices), [0, 1, 2])
        self.assertEqual(stats['target_token_overshoot'], 0)
        self.assertEqual(stats['completed_corpus_passes'], 1)

    def test_no_filtering_to_fit_budget(self):
        with self.assertRaises(ValueError):
            plan_token_exposure([2, 3, 5], 9, seed=44)
        for counts in [[], [0], [-1], [True], [1.5]]:
            with self.assertRaises(ValueError):
                plan_token_exposure(counts, 100, seed=44)

    def test_upstream_exposure_equivalence(self):
        # Requires pinned bfc0095 improving source on hn01; never run locally.
        from improving.training import plan_token_exposure as upstream
        for counts, budget in [([3, 7, 2, 11], 100), ([2, 3, 5], 10)]:
            observed_indices, observed = plan_token_exposure(counts, budget, seed=44)
            expected_indices, expected = upstream(counts, budget, seed=44)
            self.assertEqual(observed_indices, expected_indices)
            for key, value in expected.items():
                self.assertEqual(observed[key], value)

    def test_final_group_divisor(self):
        self.assertEqual([accumulation_divisor(i, 19, 16) for i in range(19)],
                         [16] * 16 + [3] * 3)
        self.assertEqual(accumulation_divisor(31, 32, 16), 16)
        with self.assertRaises(ValueError):
            accumulation_divisor(19, 19, 16)

    def test_shifted_prompt_completion_targets(self):
        example = {'input_ids': [8, 9, 10, 11, 12],
                   'labels': [8, 9, 10, 11, 12], 'truncated_tokens': 2}
        result = target_breakdown(example, 3)
        self.assertEqual(result['prompt_targets'], 2)
        self.assertEqual(result['completion_targets'], 2)
        self.assertEqual(result['supervised_target_tokens'], 4)
        self.assertEqual(result['truncated_tokens'], 2)
        example['labels'] = [-100, -100, -100, 11, 12]
        self.assertEqual(target_breakdown(example, 3)['prompt_targets'], 0)

    def test_contract_refuses_changed_batch_or_budget(self):
        settings = dict(batch_size=1, gradient_accumulation_steps=16,
                        max_length=1536, loss_scope='all', target_token_budget=7200000,
                        epochs=1, learning_rate=1e-5, weight_decay=.01,
                        warmup_ratio=.03, max_grad_norm=1, lora_rank=8,
                        lora_alpha=8, lora_dropout=.05, gradient_checkpointing=True)
        validate_training_contract(settings, 44)
        for key, value in [('batch_size', 2), ('target_token_budget', 7200001),
                           ('loss_scope', 'completion')]:
            with self.assertRaises(ValueError):
                validate_training_contract(dict(settings, **{key: value}), 44)
        with self.assertRaises(ValueError):
            validate_training_contract(settings, 43)

    def test_telemetry_rejects_unknown_attempt_and_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'attempt'
            telemetry = Telemetry(path)
            telemetry.write('invocation.json', {'status': 'started'})
            with self.assertRaises(FileExistsError):
                Telemetry(path)
            with self.assertRaises(FileExistsError):
                telemetry.write('invocation.json', {'status': 'completed'})
            telemetry.append('observed.jsonl', {'index': 0})
            telemetry.append('observed.jsonl', {'index': 1})
            self.assertEqual([json.loads(x)['index'] for x in
                              (path / 'observed.jsonl').read_text().splitlines()], [0, 1])


if __name__ == '__main__':
    unittest.main()
