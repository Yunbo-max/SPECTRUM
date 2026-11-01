"""Round-local learned-gain calibration, native probes and bound resume artifacts.

Only the explicitly selected ``spectral_learned`` arm uses this module. Reference
labels never enter the native probe or the ordinary generated-data SFT corpus.
"""
from __future__ import annotations

from collections.abc import Mapping
import json
import os
from pathlib import Path
import tempfile

import torch

from .generation import generate_to_file
from .modeling import collate_examples, encode_example, render_prompt
from .utils import atomic_json, stable_hash


INTEGRATION_DEFAULTS = {
    'guard_examples': 10,
    'probe_examples': 8,
    'probe_max_new_tokens': 128,
}


def split_gain_settings(calibration):
    """Validate one explicit controller; never combine learned gains with tau gates."""
    from .learned_gains import validate_gain_settings
    if not isinstance(calibration, Mapping):
        raise ValueError('calibration must be a mapping')
    if calibration.get('reestimate_each_round', True) is not True:
        raise ValueError('spectral_learned requires reestimate_each_round=true')
    if calibration.get('tau_mode') is not None or calibration.get('tau_decay') is not None:
        raise ValueError('spectral_learned cannot combine tau_mode or tau_decay')
    raw = calibration.get('gain_learning', {})
    if not isinstance(raw, Mapping):
        raise ValueError('calibration.gain_learning must be a mapping')
    integration = {key: raw.get(key, default) for key, default in INTEGRATION_DEFAULTS.items()}
    for key, value in integration.items():
        if type(value) is not int or value < 1:
            raise ValueError(f'gain_learning.{key} must be a positive integer')
    count = calibration.get('max_examples', 50)
    if type(count) is not int or count <= integration['guard_examples']:
        raise ValueError('max_examples must exceed guard_examples and leave a nonempty fit set')
    core = validate_gain_settings({key: value for key, value in raw.items()
                                   if key not in INTEGRATION_DEFAULTS})
    return core, integration


def split_gain_references(tasks, calibration):
    _, settings = split_gain_settings(calibration)
    count = calibration.get('max_examples', 50)
    if len(tasks) < count:
        raise ValueError('Insufficient calibration references for the declared fit/guard split')
    selected = list(tasks[:count])
    ids = [task['task_id'] for task in selected]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate fit/guard calibration task IDs')
    if any(not isinstance(task.get('reference'), str) or not task['reference'].strip()
           for task in selected):
        raise ValueError('Every fit/guard example requires a nonempty reference')
    guard_count = settings['guard_examples']
    return selected[:-guard_count], selected[-guard_count:]


def reference_batches(tokenizer, tasks, calibration):
    mode = calibration.get('span_mode', 'completion')
    if mode not in {'completion', 'explicit'}:
        raise ValueError('calibration.span_mode must be completion or explicit')
    batches = []
    for task in tasks:
        spans = task.get('calibration_spans') if mode == 'explicit' else None
        if mode == 'explicit' and not spans:
            raise ValueError('Explicit calibration requires spans on every fit/guard example')
        example = encode_example(
            tokenizer, render_prompt(tokenizer, task), task['reference'],
            max_length=calibration.get('max_length', 1536),
            loss_scope='completion', spans=spans)
        if example['truncated_tokens']:
            raise ValueError('Fit/guard reference truncated; increase calibration.max_length')
        batches.append(collate_examples([example], tokenizer.pad_token_id))
    return batches


def probe_batches(tokenizer, tasks, records, max_length):
    """Use exact native continuations, never decoded text or a fabricated EOS."""
    by_id = {}
    for record in records:
        key = record.get('task_id')
        if key in by_id or record.get('sample_id') != 0:
            raise ValueError('Probe requires exactly one native sample per task')
        by_id[key] = record
    if set(by_id) != {task['task_id'] for task in tasks}:
        raise ValueError('Probe task coverage mismatch')
    batches = []
    for task in tasks:
        record = by_id[task['task_id']]
        ids = record.get('completion_ids')
        if (not isinstance(ids, list) or not ids or
                any(type(token) is not int or token < 0 for token in ids)):
            raise ValueError('Native probe requires nonempty exact completion_ids')
        prompt = render_prompt(tokenizer, task)
        prefix = tokenizer.encode(prompt, add_special_tokens=False)
        if record.get('prompt_tokens') != len(prefix):
            raise ValueError('Probe prompt token count differs from the generation prefix')
        if record.get('prompt_sha256') != stable_hash(prompt):
            raise ValueError('Probe prompt/template hash mismatch')
        if record.get('generation_tokens') != len(ids):
            raise ValueError('Probe generated-token count mismatch')
        example = encode_example(tokenizer, prompt, '', max_length=max_length,
                                 loss_scope='completion', completion_ids=ids, append_eos=False)
        if example['truncated_tokens']:
            raise ValueError('Probe encoding truncated exact generated tokens')
        batches.append(collate_examples([example], tokenizer.pad_token_id))
    return batches


def _save_artifact(path, protocol, operators, audit):
    from .pipeline import _operator_fingerprints
    path = Path(path)
    artifact = {'format_version': 1, 'protocol': protocol, 'operators': operators,
                'operator_sha256': _operator_fingerprints(operators),
                'audit': audit, 'audit_sha256': stable_hash(audit)}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f'.{path.name}.',
                                         suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            torch.save(artifact, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _load_artifact(path, protocol, covariances, min_gain):
    from .pipeline import _operator_fingerprints
    artifact = torch.load(path, map_location='cpu', weights_only=True)
    if (not isinstance(artifact, dict) or artifact.get('format_version') != 1
            or artifact.get('protocol') != protocol):
        raise ValueError('Learned operator protocol mismatch; do not refit a cached generation policy')
    operators, audit = artifact.get('operators'), artifact.get('audit')
    if not isinstance(operators, dict) or set(operators) != set(covariances):
        raise ValueError('Learned operator module mismatch')
    if (not isinstance(audit, dict) or type(audit.get('selected_identity')) is not bool
            or artifact.get('audit_sha256') != stable_hash(audit)):
        raise ValueError('Learned operator audit integrity failure')
    for name, operator in operators.items():
        if (not isinstance(operator, torch.Tensor) or operator.dtype != torch.float64
                or operator.shape != covariances[name]['covariance'].shape
                or not torch.isfinite(operator).all()
                or not torch.allclose(operator, operator.T, atol=1e-9, rtol=1e-7)):
            raise ValueError('Learned operator tensor mismatch')
        values = torch.linalg.eigvalsh(operator)
        if float(values.min()) < min_gain - 1e-6 or float(values.max()) > 1 + 1e-6:
            raise ValueError('Learned operator gain bounds violated')
        if audit['selected_identity'] and not torch.equal(
                operator, torch.eye(operator.shape[0], dtype=torch.float64)):
            raise ValueError('Identity fallback artifact contains a nonidentity operator')
    if artifact.get('operator_sha256') != _operator_fingerprints(operators):
        raise ValueError('Learned operator integrity failure')
    return operators, audit


def _bind_json(path, value):
    path = Path(path)
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError(f'Learned calibration receipt mismatch: {path.name}')
    else:
        atomic_json(path, value)


def validate_saved_learned_round(directory, model_identity, calibration_settings,
                                 calibration_tasks, train_tasks, *, seed, round_index):
    """Validate committed generation policy without loading/refitting its model.

    Needed after SFT has finished: the loaded student is then a different model,
    so regenerating a lost probe or refitting missing operators is forbidden.
    """
    from .calibration import load_calibration
    from .pipeline import _operator_fingerprints, file_sha
    directory = Path(directory)
    required = ('calibration.pt', 'gain_probe.jsonl', 'gain_inputs.json',
                'learned_operators.pt', 'learned_gains.json', 'gain_provenance.json')
    for name in required:
        if not (directory / name).is_file():
            raise ValueError(f'Committed learned policy is missing {name}; restore the original artifact')
    core, integration = split_gain_settings(calibration_settings)
    fit, guard = split_gain_references(calibration_tasks, calibration_settings)
    stored = torch.load(directory / 'learned_operators.pt', map_location='cpu', weights_only=True)
    protocol = stored.get('protocol') if isinstance(stored, dict) else None
    if not isinstance(protocol, dict):
        raise ValueError('Committed learned policy has no valid protocol')
    encoded = json.loads((directory / 'gain_inputs.json').read_text())
    expected = {
        'model_identity': model_identity, 'round': round_index, 'seed': seed,
        'calibration_sha256': file_sha(directory / 'calibration.pt'),
        'native_probe_sha256': file_sha(directory / 'gain_probe.jsonl'),
        'encoded_inputs_sha256': stable_hash(encoded),
        'core_settings': core, 'integration_settings': integration,
        'fit_task_ids': [task['task_id'] for task in fit],
        'guard_task_ids': [task['task_id'] for task in guard],
        'probe_task_ids': [task['task_id'] for task in train_tasks[:integration['probe_examples']]],
    }
    if any(protocol.get(key) != value for key, value in expected.items()):
        raise ValueError('Committed learned policy input or protocol integrity failure')
    calibration = load_calibration(directory / 'calibration.pt')
    if calibration['metadata'].get('model_identity') != model_identity:
        raise ValueError('Committed learned covariance model identity mismatch')
    operators, audit = _load_artifact(directory / 'learned_operators.pt', protocol,
                                     calibration['modules'], core['min_gain'])
    if json.loads((directory / 'learned_gains.json').read_text()) != audit:
        raise ValueError('Committed learned gain audit integrity failure')
    provenance = {**protocol, 'operators_file': 'learned_operators.pt',
                  'operators_file_sha256': file_sha(directory / 'learned_operators.pt'),
                  'operator_sha256': _operator_fingerprints(operators),
                  'selected_identity': audit['selected_identity'],
                  'intervention_lifetime': 'generation_only_restored_before_sft_and_native_evaluation'}
    if json.loads((directory / 'gain_provenance.json').read_text()) != provenance:
        raise ValueError('Committed learned policy provenance integrity failure')


def calibrate_learned_round(model, tokenizer, calibration_tasks, train_tasks,
                            calibration_settings, generation_settings, directory,
                            model_identity, *, seed, round_index, resume):
    """Return operators, fit covariances, audit and immutable policy provenance."""
    from .learned_gains import fit_learned_operators
    from .pipeline import _calibrate, _operator_fingerprints, file_sha, record_stage
    core, integration = split_gain_settings(calibration_settings)
    fit, guard = split_gain_references(calibration_tasks, calibration_settings)
    if len(train_tasks) < integration['probe_examples']:
        raise ValueError('Insufficient training prompts for the declared native probe')
    # Strip answer/tests fields entirely. Original prompts/templates remain unchanged.
    probe_tasks = [{key: task[key] for key in (
        'task_id', 'prompt', 'source', 'split', 'chat_template_kwargs') if key in task}
        for task in train_tasks[:integration['probe_examples']]]
    probe_ids = [task['task_id'] for task in probe_tasks]
    anchor_ids = {task['task_id'] for task in fit + guard}
    if len(set(probe_ids)) != len(probe_ids) or anchor_ids.intersection(probe_ids):
        raise ValueError('Native probe and calibration task IDs must be unique and disjoint')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    artifact_path = directory / 'learned_operators.pt'
    if not artifact_path.exists() and any((directory / name).exists() for name in (
            'train.jsonl', 'train.jsonl.parts', 'training_stats.json', 'generation_policy.jsonl',
            'gain_provenance.json', 'learned_gains.json')):
        raise ValueError('Committed policy or generated data exists without its learned operators; restore the original artifact')
    fit_settings = {**calibration_settings, 'max_examples': len(fit)}
    calibration_path = directory / 'calibration.pt'
    with record_stage(directory, 'calibration'):
        covariances = _calibrate(model, tokenizer, fit, fit_settings,
                                 calibration_path, model_identity)
    probe_settings = {
        'samples': 1, 'batch_size': 1, 'task_batch_size': 1, 'sequence_batch_size': 1,
        'max_new_tokens': integration['probe_max_new_tokens'],
        'max_prompt_tokens': generation_settings.get('max_prompt_tokens', 2048),
        'temperature': generation_settings.get('temperature', .8),
        'top_p': generation_settings.get('top_p', .95),
        'top_k': generation_settings.get('top_k', 0),
    }
    probe_path = directory / 'gain_probe.jsonl'
    if artifact_path.exists() and not probe_path.exists():
        raise ValueError('Learned operators require their original native probe file')
    with record_stage(directory, 'gain_probe'):
        records = generate_to_file(
            model, tokenizer, probe_tasks, probe_path, probe_settings, seed=seed,
            model_identity=model_identity, method='spectral_learned_native_probe',
            round_index=round_index, stage='gain_probe', resume=resume)
    fit_batches = reference_batches(tokenizer, fit, calibration_settings)
    guard_batches = reference_batches(tokenizer, guard, calibration_settings)
    native_probe_batches = probe_batches(
        tokenizer, probe_tasks, records,
        probe_settings['max_prompt_tokens'] + probe_settings['max_new_tokens'])
    encoded = {name: [{key: value.tolist() for key, value in batch.items()} for batch in batches]
               for name, batches in [('fit', fit_batches), ('guard', guard_batches),
                                     ('probe', native_probe_batches)]}
    _bind_json(directory / 'gain_inputs.json', encoded)
    protocol = {
        'format_version': 1, 'model_identity': model_identity, 'round': round_index,
        'seed': seed, 'calibration_sha256': file_sha(calibration_path),
        'native_probe_sha256': file_sha(probe_path),
        'encoded_inputs_sha256': stable_hash(encoded), 'core_settings': core,
        'integration_settings': integration, 'probe_settings': probe_settings,
        'fit_task_ids': [task['task_id'] for task in fit],
        'guard_task_ids': [task['task_id'] for task in guard], 'probe_task_ids': probe_ids,
        'kl_definition': 'native_to_steered_full_vocabulary_raw_logits_response_prefix_token_mean',
        'reference_policy': 'fixed_reference_subset_fit_prefix_guard_suffix',
        'sft_loss': 'unchanged_uniform_model_loss', 'quality_filtering': False,
    }
    if artifact_path.exists():
        operators, audit = _load_artifact(artifact_path, protocol, covariances, core['min_gain'])
    else:
        with record_stage(directory, 'gain_learning'):
            operators, audit = fit_learned_operators(
                model, fit_batches, guard_batches, native_probe_batches, covariances, core)
        _save_artifact(artifact_path, protocol, operators, audit)
    _bind_json(directory / 'learned_gains.json', audit)
    provenance = {**protocol, 'operators_file': artifact_path.name,
                  'operators_file_sha256': file_sha(artifact_path),
                  'operator_sha256': _operator_fingerprints(operators),
                  'selected_identity': audit['selected_identity'],
                  'intervention_lifetime': 'generation_only_restored_before_sft_and_native_evaluation'}
    _bind_json(directory / 'gain_provenance.json', provenance)
    return operators, covariances, audit, provenance
