"""Regression sources for complete SFT targets and round-aware diagnostics.

These tests are authored for Local acceptance; they are not experiment results.
"""
from copy import deepcopy

import pytest
import torch
from torch import nn

from improving.pipeline import _operator_diagnostics, _operators, validate_config
from improving.training import train_on_records
from tests.helpers import tiny_model_and_tokenizer


def _config():
    return {
        'model': {'name': 'fixture/model'},
        'data': {split: f'{split}.jsonl'
                 for split in ('train', 'calibration', 'validation', 'eval')},
        'output_dir': 'fixture/output', 'methods': ['plain'],
        'generation': {'max_prompt_tokens': 2048, 'max_new_tokens': 4096},
        'train': {'max_length': 6144, 'require_full_completion_targets': True},
    }


def test_length_contract_accepts_exact_capacity_and_rejects_one_token_short():
    config = _config()
    assert validate_config(config) is config
    config['train']['max_length'] -= 1
    with pytest.raises(ValueError, match='max_prompt_tokens.*max_new_tokens'):
        validate_config(config)


def test_legacy_configuration_retains_declared_truncation_behavior():
    config = _config()
    config['train'] = {'max_length': 1536}
    assert validate_config(config) is config
    config['train']['require_full_completion_targets'] = False
    assert validate_config(config) is config


def test_full_target_default_limits_agree_with_default_generator_limits():
    config = _config()
    config['generation'] = {}
    config['train'] = {'require_full_completion_targets': True}
    assert validate_config(config) is config


@pytest.mark.parametrize('section,key,value', [
    ('generation', 'max_prompt_tokens', True),
    ('generation', 'max_new_tokens', 4096.0),
    ('generation', 'max_new_tokens', 0),
    ('train', 'max_length', -1),
    ('train', 'require_full_completion_targets', 'true'),
])
def test_full_target_contract_rejects_ambiguous_or_invalid_limits(section, key, value):
    config = _config()
    config[section][key] = value
    with pytest.raises(ValueError, match=key):
        validate_config(config)


def test_direct_train_rejects_nonboolean_contract_before_loading_dependencies(tmp_path):
    with pytest.raises(ValueError, match='require_full_completion_targets must be boolean'):
        train_on_records(None, None, None, None,
                         {'require_full_completion_targets': 1}, tmp_path / 'model')


def test_truncated_record_aborts_before_lora_and_preserves_inputs(tmp_path, monkeypatch):
    model, tokenizer = tiny_model_and_tokenizer()
    tasks = [{'task_id': 'fixture/train', 'prompt': 'Write a function',
              'source': 'fixture', 'split': 'train'}]
    records = [{'task_id': 'fixture/train', 'sample_id': 0, 'completion': 'return 1',
                'completion_ids': [11, 12, tokenizer.eos_token_id], 'finish_reason': 'eos'}]
    before_model = deepcopy(model.state_dict())
    before_records = deepcopy(records)

    def unexpected_adapter(*args, **kwargs):
        raise AssertionError('Length rejection must precede adapter/model mutation')

    monkeypatch.setattr('peft.get_peft_model', unexpected_adapter)
    with pytest.raises(ValueError, match='forbids SFT truncation'):
        train_on_records(model, tokenizer, tasks, records,
                         {'max_length': 5, 'require_full_completion_targets': True},
                         tmp_path / 'model')
    assert records == before_records
    assert not (tmp_path / 'model').exists()
    assert all(torch.equal(value, before_model[name])
               for name, value in model.state_dict().items())


def test_full_target_training_keeps_eos_and_length_capped_records(tmp_path):
    model, tokenizer = tiny_model_and_tokenizer()
    tasks = [{'task_id': 'fixture/train', 'prompt': 'Write a function',
              'source': 'fixture', 'split': 'train'}]
    records = [
        {'task_id': 'fixture/train', 'sample_id': 0, 'completion': 'return 1',
         'completion_ids': [11, 12, tokenizer.eos_token_id], 'finish_reason': 'eos'},
        {'task_id': 'fixture/train', 'sample_id': 1, 'completion': 'return 2',
         'completion_ids': [11, 13], 'finish_reason': 'length', 'correct': False},
    ]
    _, stats = train_on_records(model, tokenizer, tasks, records, {
        'max_length': 6, 'require_full_completion_targets': True,
        'loss_scope': 'completion', 'epochs': 1, 'batch_size': 2,
        'gradient_accumulation_steps': 1, 'lora_rank': 2, 'lora_alpha': 2,
        'lora_dropout': 0., 'gradient_checkpointing': False,
    }, tmp_path / 'model')
    assert stats['require_full_completion_targets']
    assert stats['truncated_tokens'] == 0
    assert stats['raw_records_retained'] == 2
    assert stats['all_raw_records_exposed'] and not stats['quality_filtering']
    # Real EOS remains a target; a length-capped record receives no artificial EOS.
    assert [row['supervised_target_tokens'] for row in stats['record_retention']] == [3, 2]
    assert stats['truncation_policy'] == 'reject_any_sft_truncation; no_record_filtering'


@pytest.mark.parametrize('method', ['random_soft', 'isotropic_soft', 'matched_blend'])
def test_later_round_matching_diagnostics_use_actual_decayed_tau(method):
    model = nn.Sequential(nn.Linear(4, 4))
    covariances = {'0': {'covariance': torch.diag(
        torch.tensor([4., 1., 0., 0.], dtype=torch.float64))}}
    settings = {'tau': .8, 'tau_decay': .5, 'rank': 2}
    operators = _operators(covariances, method, settings, 7, round_index=3)
    result = _operator_diagnostics(model, operators, covariances, method, settings,
                                   round_index=3)['0']
    assert result['reference_tau'] == pytest.approx(.2)
    assert result['matching_absolute_error'] < 1e-12
    assert result['spectral_soft_distance_from_identity'] == pytest.approx(
        result['frobenius_distance_from_identity'])
    if method == 'matched_blend':
        assert result['matched_rho'] == pytest.approx(result['eigenvalue_min'])


def test_fixed_geometry_diagnostics_keep_round_one_strength():
    model = nn.Sequential(nn.Linear(2, 2))
    covariances = {'0': {'covariance': torch.diag(torch.tensor([1., 0.]))}}
    settings = {'tau': 1., 'tau_decay': .5}
    operators = _operators(covariances, 'spectral_soft', settings, 7)
    result = _operator_diagnostics(model, operators, covariances, 'spectral_soft',
                                   settings)['0']
    assert result['reference_tau'] == 1.
    assert result['eigenvalue_min'] == pytest.approx(.5)
