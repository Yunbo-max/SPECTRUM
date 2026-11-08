"""Reference-span SPD calibration shared by math, QA and safety domains.

Spans address characters in each task's reference, never the rendered prompt.
The pinned upstream collector uses fully-contained token offsets and causal CE.
"""
from pathlib import Path
import hashlib
import os
from uuid import uuid4

import torch

from . import modeling, spectral, spd_upstream
from .modeling import render_prompt
from .spd_upstream import UPSTREAM_COMMIT, projector_record, upstream
from .utils import stable_hash


def _positive_integer(value, name):
    if type(value) is not int or value < 1:
        raise ValueError(f'{name} must be a positive integer')
    return value


def _inputs(tokenizer, tasks, max_length):
    texts, all_spans, encodings = [], [], []
    for task in tasks:
        if task.get('split') != 'calibration':
            raise ValueError('SPD accepts only calibration split references')
        reference = task.get('reference')
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError('SPD requires a nonempty reference')
        relative = task.get('calibration_spans')
        if not isinstance(relative, (list, tuple)) or not relative:
            raise ValueError('SPD requires explicit reference-relative calibration_spans')
        intervals = []
        for raw_span in relative:
            span = ([raw_span.get("start"), raw_span.get("end")]
                    if isinstance(raw_span, dict) else raw_span)
            if (not isinstance(span, (list, tuple)) or len(span) != 2
                    or any(type(v) is not int for v in span)
                    or not 0 <= span[0] < span[1] <= len(reference)):
                raise ValueError('calibration_spans must be valid reference character intervals')
            if isinstance(raw_span, dict) and raw_span.get('text') != reference[span[0]:span[1]]:
                raise ValueError('calibration span text does not match the reference slice')
            intervals.append(span)
        prompt = render_prompt(tokenizer, task)
        text = prompt + reference
        spans = [(len(prompt) + a, len(prompt) + b) for a, b in intervals]
        encoded = tokenizer(text, truncation=False, return_offsets_mapping=True)
        ids, offsets = encoded['input_ids'], encoded['offset_mapping']
        if len(ids) < 2 or len(ids) > max_length:
            raise ValueError('SPD calibration text is empty or exceeds max_length; truncation forbidden')
        # Match upstream containment exactly, excluding position zero because
        # its label is removed by causal shifting. Every requested span must
        # have at least one usable target (whitespace-only spans are invalid).
        for a, b in spans:
            if not any(end > start and start >= a and end <= b for start, end in offsets[1:]):
                raise ValueError('calibration span has no supervised next-token target')
        texts.append(text)
        all_spans.append(spans)
        encodings.append({'input_ids': ids, 'offset_mapping': offsets,
                          'attention_mask': encoded.get('attention_mask')})
    return texts, all_spans, encodings


def _operators(records, model, names, token_count):
    if set(records) != set(names):
        raise ValueError('SPD calibration topology mismatch')
    result = {}
    for name in names:
        record = records[name]
        operator = record.get('spd_operator')
        dimension = model.get_submodule(name).out_features
        rank = min(dimension // 2, token_count)
        if (not isinstance(operator, torch.Tensor) or not operator.is_floating_point()
                or operator.shape != (dimension, dimension) or not torch.isfinite(operator).all()
                or record.get('effective_rank') != rank or record.get('token_count') != token_count
                or not torch.allclose(operator, operator.T, atol=2e-5, rtol=0)
                or not torch.allclose(operator @ operator, operator, atol=2e-5, rtol=0)
                or abs(float(operator.trace()) - rank) > max(2e-5, rank * 2e-5)):
            raise ValueError('SPD cached projector invalid')
        result[name] = operator
    return result


def calibrate_domains(model, tokenizer, tasks, settings, output_dir, *, model_identity):
    """Return {native K/V module name: CPU float64 SPD projection matrix}.

    Save complete upstream-compatible records in ``output_dir/calibration.pt``.
    Defaults: layers [24, 47], half KV rank, all provided calibration examples,
    and a 4096-token cap. Caller supplies an immutable model/checkpoint identity.
    Cache mismatches fail; they never silently replace existing geometry.
    """
    tasks = list(tasks)
    count = _positive_integer(settings.get('max_examples', len(tasks)), 'max_examples')
    max_length = _positive_integer(settings.get('max_length', 4096), 'max_length')
    if len(tasks) < count:
        raise ValueError('SPD requires its full declared calibration subset')
    if settings.get('rank') is not None or settings.get('rank_fraction', .5) != .5:
        raise ValueError('Upstream SPD requires half KV rank')
    if not model_identity:
        raise ValueError('SPD requires an immutable model_identity')
    selected = tasks[:count]
    task_ids = [task.get('task_id') for task in selected]
    if any(not isinstance(t, str) or not t for t in task_ids) or len(set(task_ids)) != count:
        raise ValueError('SPD requires unique nonempty calibration task IDs')
    names = spectral.target_modules(model, layers=settings.get('layers', [24, 47]))
    if any(not name.startswith('model.layers.') for name in names):
        raise ValueError('Pinned SPD collector requires model.layers decoder topology')
    layers = sorted({int(name.split('.')[2]) for name in names})
    texts, spans, encodings = _inputs(tokenizer, selected, max_length)
    token_count = sum(len(e['input_ids']) for e in encodings)
    sources = [Path(__file__), Path(upstream.__file__), Path(spd_upstream.__file__),
               Path(modeling.__file__), Path(spectral.__file__)]
    metadata = {'upstream_commit': UPSTREAM_COMMIT, 'model_identity': model_identity,
                'settings': dict(settings), 'task_ids': task_ids,
                'tasks_sha256': stable_hash(selected), 'texts_sha256': stable_hash(texts),
                'spans_sha256': stable_hash(spans), 'tokenization_sha256': stable_hash(encodings),
                'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                'loss_definition': 'reference_span_contained_tokens_next_token_nll',
                'geometry': 'upstream_centered_float32_gradient_svd', 'rank_mode': 'half',
                'target_modules': names, 'token_lengths': [len(e['input_ids']) for e in encodings]}
    path = Path(output_dir) / 'calibration.pt'
    if path.exists():
        saved = torch.load(path, map_location='cpu', weights_only=True)
        if saved.get('format') != 'spd-domains-v1' or saved.get('metadata') != metadata:
            raise ValueError('SPD calibration identity mismatch')
        return _operators(saved['modules'], model, names, token_count)
    parameters = [(p, p.requires_grad, p.grad) for p in model.parameters()]
    modules = [(m, m.training, set(m._forward_hooks)) for m in model.modules()]
    try:
        for parameter, _, _ in parameters:
            parameter.requires_grad_(False)
            parameter.grad = None
        gradients = upstream.collect_kv_gradients(
            model, tokenizer, texts, layers, max_length=max_length,
            device=str(next(model.parameters()).device), label_char_spans=spans)
        records = {}
        for name in names:
            layer = int(name.split('.')[2])
            key = 'K_grads' if name.endswith('.k_proj') else 'V_grads'
            record = projector_record(gradients[layer][key])
            if record['token_count'] != token_count:
                raise ValueError('SPD gradient collection omitted calibration tokens')
            record['example_count'] = count
            records[name] = record
    finally:
        for parameter, flag, grad in parameters:
            parameter.requires_grad_(flag)
            parameter.grad = grad
        for module, training, previous_hooks in modules:
            module.training = training
            for key in set(module._forward_hooks) - previous_hooks:
                del module._forward_hooks[key]
                # Mirror RemovableHandle.remove for auxiliary hook registries.
                for registry in ('_forward_hooks_with_kwargs', '_forward_hooks_always_called'):
                    getattr(module, registry, {}).pop(key, None)
    operators = _operators(records, model, names, token_count)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.' + path.name + '.' + uuid4().hex)
    try:
        torch.save({'format': 'spd-domains-v1', 'metadata': metadata, 'modules': records}, temporary)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return operators
