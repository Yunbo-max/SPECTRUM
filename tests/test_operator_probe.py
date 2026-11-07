"""Authored engineering checks; run on Local before accepting this source."""
import copy
import json

import pytest

from improving.operator_probe import prompt_only_tasks, probe_settings, validate_probe_receipt


def test_probe_does_not_copy_reference_tests_or_scoring_fields():
    task = {'task_id': 'engineering-input', 'prompt': 'some prompt',
            'reference': 'private reference', 'tests': ['not for probe'],
            'correct': True, 'split': 'train', 'source': 'fixture'}
    original = copy.deepcopy(task)
    result = prompt_only_tasks([task], 1)
    assert result == [{'task_id': task['task_id'], 'prompt': task['prompt'],
                       'split': 'train', 'source': 'fixture'}]
    assert task == original


@pytest.mark.parametrize('value', [True, 0, -1, 1.5, '8'])
def test_invalid_probe_count_cannot_silently_change_population(value):
    with pytest.raises(ValueError):
        probe_settings({'diagnostics': {'operator_probe': {'enabled': True, 'examples': value}}})


def test_disabled_probe_does_not_change_historical_config():
    assert probe_settings({}) is None
    assert probe_settings({'diagnostics': {'operator_probe': False}}) is None


def test_post_sft_missing_probe_fails_instead_of_recreating_teacher(tmp_path):
    with pytest.raises(ValueError, match='pre-SFT'):
        validate_probe_receipt(tmp_path, 'original-native-state')


def test_saved_probe_rejects_different_native_model(tmp_path):
    (tmp_path / 'operator_probe_complete.json').write_text(json.dumps({
        'status': 'completed', 'binding': {'model_identity': 'other-native-state'}}))
    with pytest.raises(ValueError, match='different native'):
        validate_probe_receipt(tmp_path, 'original-native-state')
