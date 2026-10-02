"""Regression sources for the release controls (not part of a GPU experiment)."""
from copy import deepcopy
import json
import random

import pytest
import torch
from torch import nn

from improving.calibration import load_calibration
from improving.modeling import collate_examples, encode_example
from improving.pipeline import (
    _anchor_replay_records, _calibrate, _fixed_operators, _operator_fingerprints,
    validate_config,
)
from improving.spectral import folded_operators, make_operator, target_modules
from improving.training import plan_token_exposure, train_on_records
from tests.helpers import tiny_model_and_tokenizer


@pytest.mark.parametrize('budget', [21, 42, 47, 100])
def test_token_budget_retains_every_record_and_has_strict_whole_record_bound(budget):
    counts = [3, 7, 11]
    before = counts.copy()
    rng_state = random.getstate()
    indices, stats = plan_token_exposure(counts, budget, seed=19)
    assert counts == before
    assert random.getstate() == rng_state
    assert (indices, stats) == plan_token_exposure(counts, budget, seed=19)
    assert sorted(indices[:len(counts)]) == list(range(len(counts)))
    for start in range(0, len(indices) - len(counts) + 1, len(counts)):
        assert sorted(indices[start:start + len(counts)]) == list(range(len(counts)))
    actual = sum(counts[index] for index in indices)
    assert actual == stats['actual_supervised_target_tokens']
    assert 0 <= actual - budget < max(counts)
    assert stats['target_token_overshoot'] == actual - budget
    assert stats['completed_corpus_passes'] == len(indices) // len(counts)
    assert stats['partial_corpus_pass_records'] == len(indices) % len(counts)
    assert stats['record_exposure_counts'] == [indices.count(index) for index in range(len(counts))]


@pytest.mark.parametrize('budget', [True, False, 0, -1, 20, 30.5, '42'])
def test_token_budget_rejects_invalid_or_corpus_dropping_budgets(budget):
    with pytest.raises(ValueError, match='target_token_budget'):
        plan_token_exposure([3, 7, 11], budget)


@pytest.mark.parametrize('counts', [[], [0], [-1, 5], [True, 5], [2.5, 5]])
def test_token_budget_requires_positive_integer_target_counts(counts):
    with pytest.raises(ValueError, match='target tokens'):
        plan_token_exposure(counts, 100)


def test_target_accounting_uses_causal_labels_all_scope_and_preserved_eos_ids():
    _, tokenizer = tiny_model_and_tokenizer()
    prompt = 'Write a function'
    completion_ids = tokenizer.encode('return 1', add_special_tokens=False) + [tokenizer.eos_token_id]
    all_tokens = encode_example(tokenizer, prompt, '', max_length=64,
                                loss_scope='all', completion_ids=completion_ids)
    completion_only = encode_example(tokenizer, prompt, '', max_length=64,
                                     loss_scope='completion', completion_ids=completion_ids)
    all_count = sum(token != -100 for token in all_tokens['labels'][1:])
    completion_count = sum(token != -100 for token in completion_only['labels'][1:])
    assert completion_count == len(completion_ids)
    assert all_count == len(all_tokens['input_ids']) - 1
    assert all_count > completion_count
    assert all_tokens['input_ids'][-1] == tokenizer.eos_token_id
    shorter = encode_example(tokenizer, prompt, '', max_length=5,
                              loss_scope='all', completion_ids=completion_ids)
    assert shorter['truncated_tokens'] == 1
    batch = collate_examples([all_tokens, shorter], tokenizer.eos_token_id)
    assert int((batch['labels'][:, 1:] != -100).sum()) == all_count + 4
    assert batch['labels'][0, -1] == tokenizer.eos_token_id  # Real EOS is supervised.
    assert batch['labels'][1, -1] == -100  # Padding with the same token ID is masked.


def test_token_budget_training_records_all_raw_rows_and_scheduler_steps(tmp_path):
    model, tokenizer = tiny_model_and_tokenizer()
    tasks = [{'task_id': 'fixture/train', 'prompt': 'Write a function',
              'source': 'fixture', 'split': 'train'}]
    records = [{'task_id': 'fixture/train', 'sample_id': index, 'completion': completion,
                'correct': bool(index % 2)}
               for index, completion in enumerate(['return 1', '', 'def f ( ) : return 2'])]
    encoded = [encode_example(tokenizer, tasks[0]['prompt'], record['completion'],
                              max_length=64, loss_scope='all') for record in records]
    counts = [sum(token != -100 for token in example['labels'][1:]) for example in encoded]
    budget = sum(counts) + 1
    indices, plan = plan_token_exposure(counts, budget, seed=7)
    settings = {'epochs': 99, 'target_token_budget': budget, 'batch_size': 2,
                'gradient_accumulation_steps': 3, 'max_length': 64, 'lora_rank': 2,
                'lora_alpha': 2, 'lora_dropout': 0., 'gradient_checkpointing': False}
    _, stats = train_on_records(model, tokenizer, tasks, records, settings, tmp_path / 'model', seed=7)
    assert stats['epochs'] is None and stats['configured_epochs'] == 99
    assert stats['configured_epochs_applied'] is False
    assert stats['examples'] == stats['raw_records_retained'] == 3
    assert stats['all_raw_records_retained'] and stats['all_raw_records_exposed']
    assert not stats['quality_filtering'] and not stats['budget_label_masking']
    assert stats['actual_supervised_target_tokens'] == plan['actual_supervised_target_tokens']
    assert stats['record_exposures'] == len(indices)
    assert stats['optimizer_steps'] == 1  # Two microbatches; final incomplete accumulation.
    assert [row['exposures'] for row in stats['record_retention']] == plan['record_exposure_counts']
    assert json.loads((tmp_path / 'model' / 'training_stats.json').read_text()) == stats


def test_undersized_budget_fails_before_lora_mutation(tmp_path, monkeypatch):
    model, tokenizer = tiny_model_and_tokenizer()
    tasks = [{'task_id': 'fixture/train', 'prompt': 'Write a function',
              'source': 'fixture', 'split': 'train'}]
    records = [{'task_id': 'fixture/train', 'sample_id': 0, 'completion': 'return 1'}]
    before = deepcopy(model.state_dict())
    def unexpected_adapter(*args, **kwargs):
        raise AssertionError('Budget validation must precede model mutation')
    monkeypatch.setattr('peft.get_peft_model', unexpected_adapter)
    with pytest.raises(ValueError, match='below one complete corpus'):
        train_on_records(model, tokenizer, tasks, records,
                         {'target_token_budget': 1, 'max_length': 64}, tmp_path / 'model')
    assert not (tmp_path / 'model').exists()
    for name, tensor in model.state_dict().items():
        assert torch.equal(tensor, before[name])


def test_reestimated_geometry_keeps_fixed_references_and_fixed_mode_loads_old_geometry(tmp_path, monkeypatch):
    model, tokenizer = tiny_model_and_tokenizer()
    tasks = [{'task_id': 'fixture/anchor', 'prompt': 'Write a function',
              'reference': 'return 1', 'source': 'fixture', 'split': 'calibration'}]
    calls = []
    def fake_collect(current_model, batches, names):
        calls.append((id(current_model), deepcopy(batches)))
        return {name: {'covariance': torch.eye(current_model.get_submodule(name).out_features),
                       'token_count': 4} for name in names}
    monkeypatch.setattr('improving.calibration.collect_covariances', fake_collect)
    settings = {'max_examples': 1, 'max_length': 64}
    first = tmp_path / 'round_1.pt'
    second = tmp_path / 'round_2.pt'
    _calibrate(model, tokenizer, tasks, settings, first, 'base')
    _calibrate(model, tokenizer, tasks, settings, second, 'trained-round-1')
    assert len(calls) == 2
    first_metadata, second_metadata = load_calibration(first)['metadata'], load_calibration(second)['metadata']
    assert first_metadata['model_identity'] != second_metadata['model_identity']
    assert first_metadata['reference_sha256'] == second_metadata['reference_sha256']
    assert first_metadata['task_ids'] == second_metadata['task_ids']
    _calibrate(model, tokenizer, tasks, settings, first, 'base')
    assert len(calls) == 2
    changed = [{**tasks[0], 'reference': 'return 2'}]
    with pytest.raises(ValueError, match='fixed-reference protocol mismatch'):
        _calibrate(model, tokenizer, changed, settings, first, 'base')


def test_fixed_operators_reload_exact_matrices_without_redecomposition(tmp_path, monkeypatch):
    covariance = torch.diag(torch.tensor([4., 1., 0., 0.], dtype=torch.float64))
    covariances = {'k_proj': {'covariance': covariance}}
    calibration_path, path = tmp_path / 'calibration.pt', tmp_path / 'fixed_operators.pt'
    calibration_path.write_bytes(b'fixed round-one calibration bytes')
    settings = {'tau': 1., 'rank': 2}
    first = _fixed_operators(covariances, 'random_soft', settings, 42, path, calibration_path)
    def unexpected_refit(*args, **kwargs):
        raise AssertionError('Fixed geometry must reuse actual saved matrices')
    monkeypatch.setattr('improving.pipeline._operators', unexpected_refit)
    second = _fixed_operators(covariances, 'random_soft', settings, 42, path,
                              calibration_path, require_existing=True)
    assert torch.equal(first['k_proj'], second['k_proj'])
    assert _operator_fingerprints(first) == _operator_fingerprints(second)
    with pytest.raises(ValueError, match='requires saved round-1 operators'):
        _fixed_operators(covariances, 'random_soft', settings, 42, tmp_path / 'missing.pt',
                         calibration_path, require_existing=True)
    artifact = torch.load(path, weights_only=True)
    artifact['operators']['k_proj'][0, 0] += .1
    torch.save(artifact, path)
    with pytest.raises(ValueError, match='integrity failure'):
        _fixed_operators(covariances, 'random_soft', settings, 42, path, calibration_path)


def test_reused_operator_never_accumulates_across_student_updates():
    model = nn.Sequential(nn.Linear(3, 2))
    operator = make_operator(torch.diag(torch.tensor([3., 1.])), tau=2)
    for update in (0., .25):
        with torch.no_grad():
            model[0].weight.add_(update)
        current = deepcopy(model.state_dict())
        with folded_operators(model, {'0': operator}):
            torch.testing.assert_close(model[0].weight, operator.float().T @ current['0.weight'])
        assert all(torch.equal(tensor, current[name]) for name, tensor in model.state_dict().items())


def test_anchor_replay_is_explicit_fixed_reference_copy_without_quality_fields():
    tasks = [{'task_id': f'fixture/{index}', 'prompt': 'Write a function',
              'reference': f'return {index}', 'source': 'fixture', 'split': 'calibration'}
             for index in range(3)]
    before = deepcopy(tasks)
    selected, records = _anchor_replay_records(tasks, {'max_examples': 2}, round_index=2)
    assert tasks == before and selected == tasks[:2]
    assert [record['completion'] for record in records] == [task['reference'] for task in tasks[:2]]
    assert all(record['record_origin'] == 'fixed_anchor_reference' for record in records)
    assert all('correct' not in record and 'completion_ids' not in record for record in records)
    _, later = _anchor_replay_records(tasks, {'max_examples': 2}, round_index=5)
    assert [{key: value for key, value in row.items() if key != 'round'} for row in later] == [
        {key: value for key, value in row.items() if key != 'round'} for row in records]


def test_anchor_replay_sft_separates_synthetic_and_reference_exposures(tmp_path):
    model, tokenizer = tiny_model_and_tokenizer()
    tasks = [{'task_id': f'fixture/{split}', 'prompt': 'Write a function',
              'source': 'fixture', 'split': split} for split in ('train', 'calibration')]
    records = [{'task_id': 'fixture/train', 'sample_id': 0, 'completion': ''},
               {'task_id': 'fixture/calibration', 'sample_id': 0, 'completion': 'return 1',
                'record_origin': 'fixed_anchor_reference'}]
    settings = {'fixed_anchor_replay': True, 'epochs': 1, 'batch_size': 2,
                'gradient_accumulation_steps': 1, 'max_length': 64, 'lora_rank': 2,
                'lora_alpha': 2, 'gradient_checkpointing': False}
    _, stats = train_on_records(model, tokenizer, tasks, records, settings, tmp_path / 'model')
    assert stats['examples'] == stats['training_records_received'] == 2
    assert stats['raw_records_received'] == stats['raw_records_retained'] == 1
    assert stats['anchor_reference_records'] == 1 and stats['fixed_anchor_replay']
    assert stats['all_raw_records_retained'] and stats['all_training_records_exposed']
    assert all(value > 0 for value in stats['supervised_target_tokens_by_origin'].values())
    assert sum(stats['supervised_target_tokens_by_origin'].values()) == stats['actual_supervised_target_tokens']


@pytest.mark.parametrize('architecture,kv_heads', [('qwen2', 1), ('llama', 4)])
def test_native_projection_shapes_support_gqa_and_mha(architecture, kv_heads):
    from transformers import LlamaConfig, LlamaForCausalLM, Qwen2Config, Qwen2ForCausalLM
    config_type, model_type = ((Qwen2Config, Qwen2ForCausalLM) if architecture == 'qwen2'
                              else (LlamaConfig, LlamaForCausalLM))
    model = model_type(config_type(vocab_size=23, hidden_size=32, intermediate_size=48,
                                  num_hidden_layers=2, num_attention_heads=4,
                                  num_key_value_heads=kv_heads))
    names = target_modules(model)
    assert len(names) == 2  # Middle and final layer coincide in this two-layer fixture.
    assert all(model.get_submodule(name).out_features == kv_heads * 8 for name in names)
    before = {name: model.get_submodule(name).weight.detach().clone() for name in names}
    operators = {name: torch.eye(kv_heads * 8) * .75 for name in names}
    with folded_operators(model, operators):
        for name in names:
            torch.testing.assert_close(model.get_submodule(name).weight, before[name] * .75)
    assert all(torch.equal(model.get_submodule(name).weight, before[name]) for name in names)


@pytest.mark.parametrize('train,methods', [
    ({'target_token_budget': True}, ['plain']),
    ({'target_token_budget': -1}, ['spectral_soft']),
    ({'fixed_anchor_replay': 'yes'}, ['plain']),
    ({'fixed_anchor_replay': True}, ['spectral_soft']),
    ({'fixed_anchor_replay': True}, ['plain', 'spectral_soft']),
])
def test_final_controls_reject_ambiguous_configuration(train, methods):
    config = {'model': {'name': 'fixture'}, 'output_dir': 'run', 'methods': methods,
              'data': {name: f'{name}.jsonl' for name in ('train', 'calibration', 'validation', 'eval')},
              'train': train}
    with pytest.raises(ValueError):
        validate_config(config)
