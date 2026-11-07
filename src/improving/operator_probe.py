"""Observe actual folded-policy KL without fitting or selecting an intervention.

The existing MBPP training prompts supply native prefixes, with answer/test fields
removed. This is a finite-prefix raw-logit diagnostic, not benchmark success or
a claim that equal Frobenius displacement implies equal output KL.
"""
from __future__ import annotations

import json
import math
from pathlib import Path


def probe_settings(config):
    raw = config.get('diagnostics', {}).get('operator_probe')
    if raw is None or raw is False:
        return None
    if not isinstance(raw, dict) or raw.get('enabled') is not True:
        raise ValueError('diagnostics.operator_probe requires enabled=true')
    if set(raw) - {'enabled', 'examples', 'max_new_tokens', 'kl_chunk_tokens'}:
        raise ValueError('Unknown operator_probe field')
    out = {}
    for key, default in (('examples', 8), ('max_new_tokens', 128), ('kl_chunk_tokens', 32)):
        value = raw.get(key, default)
        if type(value) is not int or value < 1:
            raise ValueError(f'operator_probe.{key} must be a positive integer')
        out[key] = value
    return out


def prompt_only_tasks(tasks, count):
    if len(tasks) < count:
        raise ValueError('Insufficient native training prompts for the frozen probe')
    result = [{key: row[key] for key in
               ('task_id', 'prompt', 'source', 'split', 'chat_template_kwargs') if key in row}
              for row in tasks[:count]]
    if (len({row.get('task_id') for row in result}) != count
            or any(not isinstance(row.get('prompt'), str) or not row['prompt'] for row in result)):
        raise ValueError('Probe requires unique task IDs and nonempty original prompts')
    return result


def validate_probe_receipt(directory, model_identity, binding=None):
    from .pipeline import file_sha
    root = Path(directory)
    receipt = root / 'operator_probe_complete.json'
    if not receipt.is_file():
        raise ValueError('Missing pre-SFT operator diagnostic; restore its original artifacts')
    saved = json.loads(receipt.read_text())
    actual_binding = saved.get('binding', {})
    if (saved.get('status') != 'completed'
            or actual_binding.get('model_identity') != model_identity
            or (binding is not None and actual_binding != binding)):
        raise ValueError('Operator probe belongs to a different native policy or operator')
    files = saved.get('files', {})
    if not {'operator_probe.jsonl', 'operator_probe_binding.json', 'operator_response.json'} <= set(files):
        raise ValueError('Incomplete operator probe receipt')
    for relative, expected in files.items():
        path = (root / relative).resolve()
        if (not path.is_relative_to(root.resolve()) or not path.is_file()
                or file_sha(path) != expected):
            raise ValueError(f'Changed operator probe artifact: {relative}')
    response = json.loads((root / 'operator_response.json').read_text())
    if response.get('binding') != actual_binding:
        raise ValueError('Operator response binding differs from its sealed receipt')
    return response


def observe_operator_response(model, tokenizer, train_tasks, operators, directory,
                              *, config, identity, method, round_index, seed,
                              selected_identity=False, resume=False):
    from .gain_pipeline import probe_batches
    from .generation import generate_to_file
    from .learned_gains import _examples, _probe_kl
    from .pipeline import _operator_fingerprints, file_sha, record_stage
    from .utils import atomic_json, stable_hash

    settings = probe_settings(config)
    if settings is None:
        return None
    tasks = prompt_only_tasks(train_tasks, settings['examples'])
    generation = config['generation']
    native_decoder = {
        'samples': 1, 'batch_size': 1, 'task_batch_size': 1, 'sequence_batch_size': 1,
        'max_prompt_tokens': generation['max_prompt_tokens'],
        'max_new_tokens': settings['max_new_tokens'],
        'temperature': generation['temperature'], 'top_p': generation['top_p'],
        'top_k': generation['top_k'],
    }
    effective = {} if selected_identity or operators is None else operators
    binding = {
        'schema_version': 1, 'model_identity': identity, 'method': method,
        'round': round_index, 'seed': seed,
        'task_ids': [row['task_id'] for row in tasks],
        'prompt_records_sha256': stable_hash(tasks), 'native_decoder': native_decoder,
        'operator_sha256': _operator_fingerprints(effective),
        'selected_identity': bool(selected_identity), 'settings': settings,
        'selection_use': False, 'training_use': False,
    }
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    if (root / 'operator_probe_complete.json').is_file():
        return validate_probe_receipt(root, identity, binding)
    bound = root / 'operator_probe_binding.json'
    if bound.is_file():
        if not resume or json.loads(bound.read_text()) != binding:
            raise ValueError('Operator probe changed or interrupted attempt lacks --resume')
    else:
        if (root / 'operator_probe.jsonl').exists() or (root / 'operator_response.json').exists():
            raise ValueError('Unbound operator probe artifacts cannot be reused')
        atomic_json(bound, binding)
    prior_training = bool(model.training)
    try:
        model.eval()
        with record_stage(root, 'operator_probe_generation'):
            records = generate_to_file(
                model, tokenizer, tasks, root / 'operator_probe.jsonl', native_decoder,
                seed=seed, model_identity=identity, method='operator_native_probe',
                round_index=round_index, stage='operator_probe', resume=resume)
        batches = probe_batches(tokenizer, tasks, records,
                                native_decoder['max_prompt_tokens'] + settings['max_new_tokens'])
        examples = _examples(batches, 'operator-probe')
        with record_stage(root, 'operator_probe_kl'):
            kl = _probe_kl(model, examples, settings['kl_chunk_tokens'], operators=effective)
    finally:
        model.train(prior_training)
    if not math.isfinite(kl['mean']) or kl['tokens'] < 1:
        raise ValueError('Operator diagnostic returned no finite selected-prefix KL')
    response = {
        'binding': binding, 'raw_logit_forward_kl': kl,
        'definition': 'full-vocabulary KL(native || actual folded policy) on native training-prompt prefixes',
        'output_kl_matched': False, 'updates_method_parameters': False,
        'correctness_tests_used': False, 'reference_answers_used': False,
        'limitations': [
            'Finite eight-prompt/128-token diagnostic, not a full-trajectory bound.',
            'Raw-logit distributions precede temperature/top-p/top-k transformations.',
            'SSD can change decoding while leaving these raw logits unchanged.',
            'Values from different learned students are not a common-state causal comparison.',
        ],
    }
    atomic_json(root / 'operator_response.json', response)
    names = ('operator_probe.jsonl', 'operator_probe_binding.json', 'operator_response.json')
    atomic_json(root / 'operator_probe_complete.json', {
        'status': 'completed', 'binding': binding,
        'files': {name: file_sha(root / name) for name in names},
    })
    return response
