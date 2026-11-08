"""Pinned upstream SPD geometry, adapted to the matched multi-round harness.

Upstream: https://github.com/gh540-svg/SPD at caa408c699f13c209a6484f626939cf3a3dcbe18.
The unchanged utility module supplies gradient collection and centered SVD.
Only training-calibration references are admitted; no heldout labels are read.
"""
from pathlib import Path
import os
import hashlib
from uuid import uuid4

import torch

from . import _spd_upstream_utils as upstream
from .spectral import target_modules
from .utils import stable_hash

UPSTREAM_COMMIT = 'caa408c699f13c209a6484f626939cf3a3dcbe18'


def projector_record(gradients):
    if gradients.ndim != 2 or min(gradients.shape) < 2 or not torch.isfinite(gradients).all():
        raise ValueError('SPD requires finite nonempty gradient matrices')
    basis, singular, rank = upstream.extract_subspace(gradients, half_rank=True)
    centered = gradients.float() - gradients.float().mean(0, keepdim=True)
    if not float(centered.square().sum()) > 0:
        raise ValueError('SPD calibration has no centered gradient signal')
    gram = centered.double().T @ centered.double()
    return {'covariance': gram / len(centered), 'second_moment_sum': gram,
            'token_count': len(centered), 'effective_rank': rank,
            'singular_values': singular.cpu(),
            'spd_operator': upstream.compute_projection_matrix(basis).cpu().double()}


def calibration_texts(tasks):
    texts = []
    for task in tasks:
        if task.get('split') != 'calibration':
            raise ValueError('Upstream SPD accepts only the frozen calibration split')
        prompt, reference, tests = task.get('original_prompt'), task.get('reference'), task.get('tests')
        if not all(isinstance(v, str) and v.strip() for v in (prompt, reference, tests)):
            raise ValueError('SPD calibration requires original_prompt, reference and tests')
        # Exactly the code-task aligned formatting in upstream ssd_subspace.py.
        texts.append(f'Instruction: {prompt}\nYour code should pass these tests:\n{tests}\nCode: {reference}')
    return texts


def assertion_spans(tasks, texts):
    """Equivalent to upstream mbpp_solutions spans for prepared MBPP tests.

    The prepared format joins MBPP's individual assertions with newlines.
    Reject unsupported multiline/setup records instead of changing label scope.
    """
    all_spans = []
    for task, text in zip(tasks, texts):
        assertions = task['tests'].splitlines()
        if not assertions or any(not a.lstrip().startswith('assert ') for a in assertions):
            raise ValueError('SPD needs individual MBPP assertion lines, not setup/multiline tests')
        spans = []
        for assertion in assertions:
            start = 0
            while True:
                pos = text.find(assertion, start)
                if pos < 0:
                    break
                spans.append((pos, pos + len(assertion)))
                start = pos + len(assertion)
        all_spans.append(spans)
    return all_spans


def calibrate(model, tokenizer, tasks, settings, path, model_identity):
    count = int(settings.get('max_examples', 50))
    if count < 1 or len(tasks) < count:
        raise ValueError('SPD requires its full declared calibration subset')
    selected = tasks[:count]
    texts = calibration_texts(selected)
    spans = assertion_spans(selected, texts)
    names = target_modules(model, layers=settings.get('layers'))
    layers = sorted({int(name.split('.layers.')[1].split('.')[0]) for name in names})
    max_length = int(settings.get('max_length', 4096))
    # Upstream silently truncates; this adaptation rejects truncated references.
    lengths = [len(tokenizer(text, truncation=False)['input_ids']) for text in texts]
    if any(n < 2 or n > max_length for n in lengths):
        raise ValueError('SPD calibration text exceeds max_length or is empty; no silent truncation')
    for text, selected_spans in zip(texts, spans):
        offsets = tokenizer(text, return_offsets_mapping=True, truncation=False)['offset_mapping']
        if not any(te > ts and ts >= cs and te <= ce
                   for ts, te in offsets[1:] for cs, ce in selected_spans):
            raise ValueError('SPD calibration has no assertion next-token labels')
    metadata = {'upstream_commit': UPSTREAM_COMMIT,
                'upstream_utils_sha256': hashlib.sha256(Path(upstream.__file__).read_bytes()).hexdigest(),
                'model_identity': model_identity, 'settings': settings,
                'task_ids': [t['task_id'] for t in selected], 'texts_sha256': stable_hash(texts),
                'loss_definition': 'upstream_mbpp_solutions_assertion_only_next_token_nll',
                'assertion_spans_sha256': stable_hash(spans),
                'geometry': 'centered_float32_gradient_svd', 'rank_mode': 'half',
                'target_modules': list(names), 'token_lengths': lengths}
    path = Path(path)
    if path.exists():
        saved = torch.load(path, map_location='cpu', weights_only=True)
        if saved.get('format') != 'spd-upstream-v1' or saved.get('metadata') != metadata:
            raise ValueError('SPD calibration identity mismatch')
        records = saved['modules']
        if set(records) != set(names):
            raise ValueError('SPD calibration topology mismatch')
        for name, record in records.items():
            p = record['spd_operator']
            dim = model.get_submodule(name).out_features
            if p.shape != (dim, dim) or not torch.isfinite(p).all() or not torch.allclose(p @ p, p, atol=2e-5):
                raise ValueError('SPD cached projector invalid')
        return records
    parameters = [(p, p.requires_grad, p.grad) for p in model.parameters()]
    modules = [(m, m.training, set(m._forward_hooks)) for m in model.modules()]
    try:
        # The upstream collector turns on K/V parameter grads; other weights
        # are frozen to avoid unnecessary parameter-gradient buffers.
        for p, _, _ in parameters:
            p.requires_grad_(False)
        gradients = upstream.collect_kv_gradients(model, tokenizer, texts, layers,
            max_length=max_length, device=str(next(model.parameters()).device), label_char_spans=spans)
        records = {}
        for name in names:
            layer = int(name.split('.layers.')[1].split('.')[0])
            key = 'K_grads' if name.endswith('.k_proj') else 'V_grads'
            record = projector_record(gradients[layer][key])
            if record['token_count'] != sum(lengths):
                raise ValueError('SPD gradient collection omitted calibration tokens')
            record['example_count'] = len(texts)
            records[name] = record
    finally:
        for p, flag, grad in parameters:
            p.requires_grad_(flag)
            p.grad = grad
        for module, training, previous_hooks in modules:
            module.training = training
            for key in set(module._forward_hooks) - previous_hooks:
                del module._forward_hooks[key]
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.' + path.name + '.' + uuid4().hex)
    try:
        torch.save({'format':'spd-upstream-v1','metadata':metadata,'modules':records}, temporary)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return records
