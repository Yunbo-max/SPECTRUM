"""Bounded continual calibration of shared spectral-gain coordinates.

The caller owns the fixed first-domain geometry and the historical FIT memory.
Only the reduced gains are fitted here. This is a finite numerical procedure,
not a guarantee about test performance or an exact quadratic-program solver.
The incoming *folded, controlled* policy anchors KL and fallback; it need not
be the native policy. Guard data is a final veto and never selects a step.
"""
from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any

import torch
from torch import Tensor

from .learned_gains import (
    CORE_DEFAULTS, NUMERICAL_TOLERANCE, SpectralGainLinear, _examples,
    _fit_gradient, _frozen_native, _installed, _logits, _mean_nll, _set_gains,
    forward_kl_sum, spectral_groups, validate_gain_settings,
)
from .spectral import _covariance_eigh, _native_linear, folded_operators


CONTINUAL_DEFAULTS = {
    **CORE_DEFAULTS,
    'retention_tolerance': 0.0,
    'projection_max_cycles': 100,
    'projection_tolerance': 1e-10,
}


def validate_continual_settings(settings: Mapping[str, Any] | None = None) -> dict:
    if settings is None:
        settings = {}
    if not isinstance(settings, Mapping):
        raise ValueError('continual gain settings must be a mapping')
    unknown = set(settings) - set(CONTINUAL_DEFAULTS)
    if unknown:
        raise ValueError(f'Unknown continual gain settings: {sorted(unknown)}')
    cfg = validate_gain_settings({key: value for key, value in settings.items()
                                  if key in CORE_DEFAULTS})
    for key in ('retention_tolerance', 'projection_tolerance'):
        value = settings.get(key, CONTINUAL_DEFAULTS[key])
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < 0):
            raise ValueError(f'{key} must be finite and nonnegative')
        cfg[key] = float(value)
    cycles = settings.get('projection_max_cycles', CONTINUAL_DEFAULTS['projection_max_cycles'])
    if type(cycles) is not int or cycles < 1:
        raise ValueError('projection_max_cycles must be a positive integer')
    cfg['projection_max_cycles'] = cycles
    return cfg


def _validated_geometry(geometry):
    if not isinstance(geometry, Mapping) or not geometry:
        raise ValueError('geometry must be a nonempty module mapping')
    result = {}
    for name, record in geometry.items():
        if not isinstance(name, str) or not name or not isinstance(record, Mapping):
            raise ValueError('geometry requires nonempty module names and records')
        if not all(key in record for key in ('basis', 'eigenvalues', 'group_ids')):
            raise ValueError(f'incomplete gain geometry for {name}')
        basis, eigs, groups = (record[key] for key in ('basis', 'eigenvalues', 'group_ids'))
        if (not isinstance(eigs, Tensor) or not eigs.is_floating_point()
                or eigs.ndim != 1 or not eigs.numel()
                or not torch.isfinite(eigs).all() or bool((eigs < 0).any())
                or float(eigs[-1]) <= 0 or bool((eigs[1:] < eigs[:-1]).any())):
            raise ValueError(f'invalid eigenvalues for {name}')
        dimension = eigs.numel()
        if (not isinstance(basis, Tensor) or not basis.is_floating_point()
                or basis.shape != (dimension, dimension) or not torch.isfinite(basis).all()):
            raise ValueError(f'invalid basis for {name}')
        basis = basis.detach().to(device='cpu', dtype=torch.float64).clone()
        if not torch.allclose(basis.T @ basis, torch.eye(dimension, dtype=torch.float64),
                              rtol=1e-6, atol=1e-8):
            raise ValueError(f'nonorthonormal gain basis for {name}')
        if (not isinstance(groups, Tensor) or groups.dtype != torch.long
                or groups.shape != (dimension,) or bool((groups < 0).any())):
            raise ValueError(f'invalid group_ids for {name}')
        groups = groups.detach().cpu().clone()
        unique = groups.unique(sorted=True)
        if (not torch.equal(unique, torch.arange(len(unique)))
                or bool((groups[1:] < groups[:-1]).any())):
            raise ValueError(f'group_ids must be ordered and contiguous for {name}')
        result[name] = {'basis': basis,
                        'eigenvalues': eigs.detach().to(device='cpu', dtype=torch.float64).clone(),
                        'group_ids': groups}
    return result


def build_gain_geometry(model, covariances, settings=None):
    """Build CPU geometry once, from the caller's declared first-domain FIT set.

    Each record has ``basis``, ``eigenvalues``, and ``group_ids`` tensors. This
    function never collects data or refits the geometry at a domain boundary.
    """
    cfg = validate_continual_settings(settings)
    if not isinstance(covariances, Mapping) or not covariances:
        raise ValueError('nonempty module covariances are required')
    geometry, seen = {}, set()
    for name, record in covariances.items():
        native = _native_linear(model, name)
        if id(native) in seen:
            raise ValueError('multiple gain names refer to the same module')
        seen.add(id(native))
        if not isinstance(record, Mapping) or 'covariance' not in record:
            raise ValueError(f'missing covariance for {name}')
        _, eigenvalues, basis = _covariance_eigh(record['covariance'])
        if basis.shape[0] != native.out_features:
            raise ValueError(f'covariance dimension disagrees with target {name}')
        geometry[name] = {
            'basis': basis.detach().cpu().clone(),
            'eigenvalues': eigenvalues.detach().cpu().clone(),
            'group_ids': spectral_groups(eigenvalues, cfg['degeneracy_rtol'], cfg['degeneracy_atol']),
        }
    return geometry


def _validated_state(geometry, state, min_gain=0.0):
    if not isinstance(state, Mapping) or set(state) != set(geometry):
        raise ValueError('gain state module names must exactly match the geometry')
    result = {}
    for name, record in geometry.items():
        value = state[name]
        count = int(record['group_ids'][-1]) + 1
        if (not isinstance(value, Tensor) or not value.is_floating_point()
                or value.shape != (count,)):
            raise ValueError(f'gain state for {name} must have {count} finite gains in [{min_gain}, 1] and > 0')
        value = value.detach().to(device='cpu', dtype=torch.float64).clone()
        if (not torch.isfinite(value).all() or bool((value <= 0).any())
                or bool((value < min_gain).any()) or bool((value > 1).any())):
            raise ValueError(f'gain state for {name} must have {count} finite gains in [{min_gain}, 1] and > 0')
        result[name] = value
    return result


def identity_gain_state(geometry):
    """Return independent CPU float64 reduced coordinates, one per tied group."""
    geometry = _validated_geometry(geometry)
    return {name: torch.ones(int(record['group_ids'][-1]) + 1, dtype=torch.float64)
            for name, record in geometry.items()}


def _operators(geometry, state):
    result = {}
    for name, record in geometry.items():
        basis = record['basis']
        gains = state[name][record['group_ids']]
        # Preserve exact identity, rather than introducing an U @ U.T roundtrip.
        result[name] = (torch.eye(len(gains), dtype=torch.float64)
                        + (basis * (gains - 1).unsqueeze(0)) @ basis.T)
    return result


def operators_from_gain_state(geometry, state):
    """Validate and convert reduced gains to CPU float64 deployment operators.

    The general state contract is 0 < gain <= 1. The fit function additionally
    checks the configured lower bound, which is not an argument of this helper.
    """
    geometry = _validated_geometry(geometry)
    return _operators(geometry, _validated_state(geometry, state))


def _flatten(values):
    return torch.cat([value.detach().to(device='cpu', dtype=torch.float64).reshape(-1)
                      for value in values])


def _unit_gradients(gradients):
    units, zeros = {}, []
    for name, gradient in gradients.items():
        if (not isinstance(gradient, Tensor) or not gradient.is_floating_point() or gradient.ndim != 1
                or not torch.isfinite(gradient).all()):
            raise ValueError('projection gradients must be finite vectors')
        value = gradient.detach().to(device='cpu', dtype=torch.float64)
        scale = float(value.abs().max())
        if scale == 0:
            zeros.append(name)
        else:
            scaled = value / scale
            units[name] = scaled / torch.linalg.vector_norm(scaled)
    return units, zeros


def _step_feasibility(step, lower, upper, gradients, tolerance):
    """Report every halfspace and box residual, also for the cast actual step."""
    units, zeros = _unit_gradients(gradients)
    normalized = {name: float(torch.dot(unit, step)) for name, unit in units.items()}
    raw = {name: float(torch.dot(gradient.detach().cpu().double(), step))
           for name, gradient in gradients.items()}
    box = max(0.0, float((lower - step).max()), float((step - upper).max()))
    halfspace = max([0.0, *normalized.values()])
    finite = bool(torch.isfinite(step).all()) and all(math.isfinite(v) for v in raw.values())
    return {'feasible': finite and box <= tolerance and halfspace <= tolerance,
            'box_residual': box, 'halfspace_residual': halfspace,
            'normalized_old_gradient_dot_step': normalized,
            'old_gradient_dot_step': raw, 'zero_gradient_domains': zeros}


def project_gain_step(proposed_step, current_gains, old_gradients, *, min_gain=0.1,
                      max_cycles=100, tolerance=1e-10):
    """Finite Dykstra projection onto ALL old halfspaces and the gain box.

    Inputs/outputs are reduced-coordinate vectors, not full spectral directions.
    Norm-normalized halfspace residuals make ``tolerance`` invariant to rescaling
    an old loss. A feasible result may be returned at the cycle cap; the audit
    does not assert convergence or an exact Euclidean projection. The caller
    must recheck feasibility after converting the candidate to its gain dtype.
    """
    if (type(max_cycles) is not int or max_cycles < 1 or isinstance(tolerance, bool)
            or not isinstance(tolerance, (int, float)) or not math.isfinite(tolerance)
            or tolerance < 0 or isinstance(min_gain, bool)
            or not isinstance(min_gain, (int, float)) or not math.isfinite(min_gain)
            or not 0 < min_gain <= 1 or not isinstance(old_gradients, Mapping)):
        raise ValueError('invalid bounded projection settings')
    if (not isinstance(proposed_step, Tensor) or not proposed_step.is_floating_point()
            or proposed_step.ndim != 1 or not proposed_step.numel()
            or not isinstance(current_gains, Tensor) or not current_gains.is_floating_point()
            or current_gains.shape != proposed_step.shape
            or not torch.isfinite(proposed_step).all() or not torch.isfinite(current_gains).all()):
        raise ValueError('projection requires matching finite nonempty gain/step vectors')
    current = current_gains.detach().cpu().double()
    proposed = proposed_step.detach().cpu().double()
    if bool((current < min_gain).any()) or bool((current > 1).any()):
        raise ValueError('incoming projection coordinates must lie inside the gain box')
    if any(not isinstance(g, Tensor) or g.shape != current.shape for g in old_gradients.values()):
        raise ValueError('old gradients must use the same reduced gain coordinates')
    units, zeros = _unit_gradients(old_gradients)
    lower, upper = min_gain - current, 1 - current
    point = proposed.clone()
    corrections = [torch.zeros_like(point) for _ in range(len(units) + 1)]
    converged, change = False, 0.0
    for cycle in range(max_cycles):
        before = point.clone()
        for index, unit in enumerate(units.values()):
            shifted = point + corrections[index]
            violation = torch.dot(unit, shifted).clamp_min(0)
            projected = shifted - violation / torch.dot(unit, unit) * unit
            corrections[index] = shifted - projected
            point = projected
        shifted = point + corrections[-1]
        projected = torch.maximum(lower, torch.minimum(upper, shifted))
        corrections[-1] = shifted - projected
        point = projected
        change = float((point - before).abs().max())
        residuals = _step_feasibility(point, lower, upper, old_gradients, tolerance)
        if residuals['feasible'] and change <= tolerance:
            converged = True
            break
    stats = {
        'algorithm': 'bounded_dykstra_halfspaces_and_box', 'cycles': cycle + 1,
        'max_cycles': max_cycles, 'converged': converged, 'last_cycle_change': change,
        'exact_projection_claimed': False, 'tolerance': tolerance,
        'active_old_domains': list(units), 'zero_gradient_domains': zeros,
        'proposed_conflict_domains': [name for name, unit in units.items()
                                      if float(torch.dot(unit, proposed)) > tolerance],
        'proposal': _step_feasibility(proposed, lower, upper, old_gradients, tolerance),
        'old_gradient_norms': {name: float(torch.linalg.vector_norm(value.detach().cpu().double()))
                               for name, value in old_gradients.items()},
        # For d0 = -eta * g_new / max(abs(g_new)), negate the descent cosine
        # to recover the gradient-gradient cosine used in conflict plots.
        'new_old_gradient_cosines': {
            name: (-float(torch.dot(units[name], proposed / torch.linalg.vector_norm(proposed)))
                   if name in units and bool((proposed != 0).any()) else None)
            for name in old_gradients},
        'distance_from_proposal': float(torch.linalg.vector_norm(point - proposed)),
        **residuals,
    }
    return point, stats


def _cast_candidate(wrappers, vector, min_gain):
    values, offset = [], 0
    for wrapper in wrappers.values():
        parameter = wrapper.gains
        value = vector[offset:offset + parameter.numel()].to(device=parameter.device,
                                                            dtype=parameter.dtype)
        # Rounding the lower bound down would silently violate the declared box.
        lower = torch.tensor(min_gain, device=parameter.device, dtype=parameter.dtype)
        if float(lower) < min_gain:
            lower = torch.nextafter(lower, torch.full_like(lower, math.inf))
        values.append(value.clamp_min(lower).clamp_max(1).detach().clone())
        offset += parameter.numel()
    return values


def _state(wrappers):
    return {name: wrapper.gains.detach().cpu().double().clone()
            for name, wrapper in wrappers.items()}


def _retention_nlls(model, memories, wrappers=None):
    return {name: _mean_nll(model, examples, wrappers) for name, examples in memories.items()}


def _violations(losses, limits):
    return {name: {'nll': value, 'limit': limits[name]}
            for name, value in losses.items()
            if not math.isfinite(value) or value > limits[name] + NUMERICAL_TOLERANCE}


def _incoming_probe_kl(model, examples, incoming_operators, chunk_tokens, *,
                       wrappers=None, candidate_operators=None):
    """Stream one probe at a time; the left policy always uses actual folding.

    When differentiable wrappers are installed, temporarily expose their native
    Linear modules for the incoming forward, then restore the same wrappers.
    This avoids substituting a native-policy or wrapper-only KL anchor and avoids
    caching all full-vocabulary probe logits at once.
    """
    total, count, minimum, clamped = 0.0, 0, math.inf, 0
    with torch.no_grad():
        for example in examples:
            if wrappers is not None:
                originals = {name: wrapper.linear for name, wrapper in wrappers.items()}
                with _installed(model, originals):
                    with folded_operators(model, incoming_operators):
                        incoming = _logits(model, example)[:, :-1].detach().cpu()
                candidate = _logits(model, example, wrappers)[:, :-1]
            else:
                with folded_operators(model, incoming_operators):
                    incoming = _logits(model, example)[:, :-1].detach().cpu()
                with folded_operators(model, candidate_operators):
                    candidate = _logits(model, example)[:, :-1]
            value, n, low, negative = forward_kl_sum(
                incoming, candidate, example['target_mask'], chunk_tokens)
            total += value
            count += n
            minimum = min(minimum, low)
            clamped += negative
            del incoming, candidate
    return {'mean': total / count, 'sum': total, 'tokens': count,
            'minimum_raw_token_kl': minimum, 'clamped_negative_tokens': clamped}


def fit_continual_operators(model, fit_batches, guard_batches, probe_batches,
                            geometry, *, initial_gains=None, retention_batches=None,
                            retention_limits=None, mode='conflict', settings=None):
    """Return ``(operators, selected_cpu_gain_state, JSON-compatible audit)``.

    ``retention_batches`` maps old-domain names to FIT memory batches. Explicit
    ``retention_limits`` are absolute per-domain mean-example NLL limits, with
    exactly the same keys. Otherwise limits are fixed at this call's actual
    incoming controlled losses plus ``retention_tolerance``. Sequential mode
    reports those losses/limits but does not enforce them. Retention mode enforces
    endpoints; conflict additionally projects every proposed reduced-gain step.

    The caller provides disjoint current FIT/guard examples, pinned geometry and
    native-generated training probe prefixes. Probe labels select positions only.
    Invalid inputs and runtime exceptions propagate with model state restored.
    Nonfinite candidate evaluations are recorded rejections. Any final veto
    returns the exact incoming state, even if explicit limits were already
    infeasible on entry; that infeasibility remains explicit in the audit.
    """
    cfg = validate_continual_settings(settings)
    if mode not in {'sequential', 'retention', 'conflict'}:
        raise ValueError('mode must be sequential, retention, or conflict')
    fit, guard, probe = (_examples(batches, role) for batches, role in (
        (fit_batches, 'fit'), (guard_batches, 'guard'), (probe_batches, 'probe')))
    if retention_batches is None:
        retention_batches = {}
    if (not isinstance(retention_batches, Mapping)
            or any(not isinstance(name, str) or not name for name in retention_batches)):
        raise ValueError('retention_batches must map nonempty domain names to FIT batches')
    memories = {name: _examples(batches, f'retention:{name}')
                for name, batches in retention_batches.items()}
    explicit_limits = None
    if retention_limits is not None:
        if not isinstance(retention_limits, Mapping) or set(retention_limits) != set(memories):
            raise ValueError('retention_limits keys must exactly match retention_batches')
        explicit_limits = {}
        for name, value in retention_limits.items():
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or value < 0):
                raise ValueError('retention limits must be finite nonnegative absolute NLL values')
            explicit_limits[name] = float(value)
    geometry = _validated_geometry(geometry)
    for name, record in geometry.items():
        expected = spectral_groups(record['eigenvalues'], cfg['degeneracy_rtol'], cfg['degeneracy_atol'])
        if not torch.equal(record['group_ids'], expected):
            raise ValueError(f'fixed geometry group_ids disagree with configured numerical ties for {name}')
    if initial_gains is None:
        initial_gains = {name: torch.ones(int(record['group_ids'][-1]) + 1, dtype=torch.float64)
                         for name, record in geometry.items()}
    incoming_state = _validated_state(geometry, initial_gains, cfg['min_gain'])
    originals = {name: _native_linear(model, name) for name in geometry}
    if len({id(module) for module in originals.values()}) != len(originals):
        raise ValueError('multiple gain names refer to the same module')
    target_parameters = [p for module in originals.values()
                         for p in (module.weight, module.bias) if p is not None]
    if len({id(p) for p in target_parameters}) != len(target_parameters):
        raise ValueError('gain target modules must not share parameter tensors')
    for name, module in originals.items():
        if module.out_features != geometry[name]['basis'].shape[0]:
            raise ValueError(f'geometry dimension disagrees with target {name}')
    wrappers = {name: SpectralGainLinear(module, geometry[name]['basis'], geometry[name]['group_ids'])
                for name, module in originals.items()}
    _set_gains(wrappers, _cast_candidate(wrappers, _flatten(incoming_state.values()), cfg['min_gain']))
    incoming_operators = _operators(geometry, incoming_state)
    enforce_retention = mode != 'sequential'
    audit = {
        'format_version': 1, 'method': mode, 'settings': cfg,
        'solver': 'finite_backtracking_with_bounded_dykstra' if mode == 'conflict' else 'finite_backtracking_with_box',
        'numerical_tolerance': NUMERICAL_TOLERANCE,
        'kl_direction': 'incoming_controlled_to_candidate_full_vocabulary',
        'kl_anchor_implementation': 'actual_folded_incoming_policy',
        'kl_position_policy': 'selected_causally_shifted_nonpadding_probe_targets',
        'kl_budget': cfg['kl_budget'],
        'nll_reduction': 'mean_of_per_example_mean_selected_token_nll',
        'guard_policy': 'final_candidate_then_folded_veto_only',
        'retention_enforced': enforce_retention,
        'limit_source': 'explicit' if explicit_limits is not None else 'incoming_plus_tolerance',
        'examples': {'fit': len(fit), 'guard': len(guard), 'probe': len(probe),
                     'retention': {name: len(examples) for name, examples in memories.items()}},
        'history': [], 'modules': {}, 'selected_incoming': True,
        'fallback_reason': None, 'global_optimum_claimed': False,
        'initial_cast_max_abs_delta': float((_flatten(_state(wrappers).values())
                                             - _flatten(incoming_state.values())).abs().max()),
    }
    with _frozen_native(model):
        with folded_operators(model, incoming_operators):
            baseline = {'fit_nll': _mean_nll(model, fit), 'guard_nll': _mean_nll(model, guard),
                        'retention_nlls': _retention_nlls(model, memories)}
        baseline['probe_kl'] = _incoming_probe_kl(
            model, probe, incoming_operators, cfg['kl_chunk_tokens'],
            candidate_operators=incoming_operators)
        limits = (explicit_limits if explicit_limits is not None else
                  {name: value + cfg['retention_tolerance']
                   for name, value in baseline['retention_nlls'].items()})
        if not all(math.isfinite(value) for value in limits.values()):
            raise ValueError('derived retention limits are nonfinite')
        audit.update(baseline=baseline, limits=limits,
                     guard_limit=baseline['guard_nll'] + cfg['guard_tolerance'],
                     baseline_retention_violations=_violations(baseline['retention_nlls'], limits))
        accepted_steps, stop_reason = 0, 'maximum_steps_reached'
        with _installed(model, wrappers):
            current_fit = _mean_nll(model, fit, wrappers)
            current_old = _retention_nlls(model, memories, wrappers)
            current_kl = _incoming_probe_kl(model, probe, incoming_operators,
                                           cfg['kl_chunk_tokens'], wrappers=wrappers)
            audit['wrapper_initial'] = {'fit_nll': current_fit,
                                        'retention_nlls': dict(current_old), 'probe_kl': current_kl}
            for step in range(cfg['max_steps']):
                previous = [wrapper.gains.detach().clone() for wrapper in wrappers.values()]
                previous_vector = _flatten(previous)
                gradients = _fit_gradient(model, fit, wrappers)
                gradient = _flatten(gradients)
                magnitude = float(gradient.abs().max())
                if step == 0:
                    for name, value in zip(wrappers, gradients):
                        audit['modules'][name] = {'initial_group_gradient': value.cpu().double().tolist()}
                if magnitude == 0:
                    stop_reason = 'zero_current_gain_gradient'
                    break
                old_gradients = ({name: _flatten(_fit_gradient(model, examples, wrappers))
                                  for name, examples in memories.items()} if mode == 'conflict' else {})
                accepted = False
                for backtrack in range(cfg['max_backtracks'] + 1):
                    rate = cfg['learning_rate'] * cfg['backtrack_factor'] ** backtrack
                    proposal = -rate * (gradient / magnitude)
                    item = {'step': step + 1, 'backtrack': backtrack, 'step_size': rate,
                            'gradient_max_abs': magnitude, 'accepted': False}
                    if mode == 'conflict':
                        direction, projection = project_gain_step(
                            proposal, previous_vector, old_gradients, min_gain=cfg['min_gain'],
                            max_cycles=cfg['projection_max_cycles'], tolerance=cfg['projection_tolerance'])
                        item['projection'] = projection
                        if not projection['feasible']:
                            item['reason'] = 'bounded_projection_infeasible'
                            audit['history'].append(item)
                            continue
                    else:
                        direction = proposal
                    candidate = _cast_candidate(wrappers, previous_vector + direction, cfg['min_gain'])
                    actual_step = _flatten(candidate) - previous_vector
                    actual_check = _step_feasibility(
                        actual_step, cfg['min_gain'] - previous_vector, 1 - previous_vector,
                        old_gradients, cfg['projection_tolerance'])
                    item['actual_step'] = actual_check
                    if not actual_check['feasible']:
                        item['reason'] = 'cast_step_infeasible'
                        audit['history'].append(item)
                        continue
                    if bool((actual_step == 0).all()):
                        item['reason'] = 'actual_step_is_zero'
                        audit['history'].append(item)
                        break
                    _set_gains(wrappers, candidate)
                    try:
                        candidate_fit = _mean_nll(model, fit, wrappers)
                        candidate_old = _retention_nlls(model, memories, wrappers)
                        item.update(fit_nll=candidate_fit, retention_nlls=candidate_old,
                                    retention_violations=_violations(candidate_old, limits))
                        if candidate_fit >= current_fit - cfg['min_improvement']:
                            item['reason'] = 'insufficient_fit_improvement'
                        elif enforce_retention and item['retention_violations']:
                            item['reason'] = 'retention_limit_exceeded'
                        else:
                            kl = _incoming_probe_kl(model, probe, incoming_operators,
                                                    cfg['kl_chunk_tokens'], wrappers=wrappers)
                            item['probe_kl'] = kl
                            if kl['mean'] > cfg['kl_budget'] + NUMERICAL_TOLERANCE:
                                item['reason'] = 'incoming_probe_kl_budget_exceeded'
                            else:
                                accepted = True
                                accepted_steps += 1
                                current_fit, current_old, current_kl = candidate_fit, candidate_old, kl
                                item.update(accepted=True, reason='fit_improved_and_constraints_satisfied')
                    except FloatingPointError as error:
                        item.update(reason='nonfinite_candidate', error=str(error))
                    finally:
                        if not accepted:
                            _set_gains(wrappers, previous)
                    audit['history'].append(item)
                    if accepted:
                        break
                if not accepted:
                    _set_gains(wrappers, previous)
                    stop_reason = 'no_accepted_backtracking_step'
                    break
            audit.update(accepted_steps=accepted_steps, stop_reason=stop_reason)
            wrapper_guard, guard_error = None, None
            try:
                wrapper_guard = _mean_nll(model, guard, wrappers)
            except FloatingPointError as error:
                guard_error = str(error)
            audit['wrapper'] = {'fit_nll': current_fit, 'guard_nll': wrapper_guard,
                                'retention_nlls': current_old, 'probe_kl': current_kl,
                                'guard_error': guard_error}
            candidate_state = _state(wrappers)
            candidate_operators = _operators(geometry, candidate_state)
        audit['folded_candidate'] = None
        if not accepted_steps:
            audit['fallback_reason'] = 'no_feasible_improving_update'
        elif guard_error is not None:
            audit['fallback_reason'] = 'nonfinite_wrapper_guard'
        elif wrapper_guard > audit['guard_limit'] + NUMERICAL_TOLERANCE:
            audit['fallback_reason'] = 'wrapper_guard_deteriorated'
        else:
            try:
                with folded_operators(model, candidate_operators):
                    actual = {'fit_nll': _mean_nll(model, fit),
                              'guard_nll': _mean_nll(model, guard),
                              'retention_nlls': _retention_nlls(model, memories)}
                actual['probe_kl'] = _incoming_probe_kl(
                    model, probe, incoming_operators, cfg['kl_chunk_tokens'],
                    candidate_operators=candidate_operators)
                audit['folded_candidate'] = actual
                failures = []
                if actual['fit_nll'] >= baseline['fit_nll'] - cfg['min_improvement']:
                    failures.append('folded_fit_not_improved')
                if actual['guard_nll'] > audit['guard_limit'] + NUMERICAL_TOLERANCE:
                    failures.append('folded_guard_deteriorated')
                if enforce_retention and _violations(actual['retention_nlls'], limits):
                    failures.append('folded_retention_limit_exceeded')
                if actual['probe_kl']['mean'] > cfg['kl_budget'] + NUMERICAL_TOLERANCE:
                    failures.append('folded_incoming_probe_kl_budget_exceeded')
                audit['selected_incoming'] = bool(failures)
                audit['fallback_reason'] = ','.join(failures) if failures else None
            except FloatingPointError as error:
                audit['folded_candidate'] = {'error': str(error)}
                audit['fallback_reason'] = 'nonfinite_folded_candidate'
        selected_state = incoming_state if audit['selected_incoming'] else candidate_state
        operators = incoming_operators if audit['selected_incoming'] else candidate_operators
        audit['selected'] = dict(baseline if audit['selected_incoming'] else audit['folded_candidate'])
        audit['selected_retention_violations'] = _violations(audit['selected']['retention_nlls'], limits)
        audit['selected_retention_feasible'] = not bool(audit['selected_retention_violations'])
        projection_items = [item['projection'] for item in audit['history'] if 'projection' in item]
        audit['projection_stats'] = {
            'calls': len(projection_items),
            'cycles': sum(item['cycles'] for item in projection_items),
            'unconverged_calls': sum(not item['converged'] for item in projection_items),
            'infeasible_calls': sum(not item['feasible'] for item in projection_items),
            'cast_rejections': sum(item['reason'] == 'cast_step_infeasible' for item in audit['history']),
            'conflicting_proposals': sum(bool(item['proposed_conflict_domains']) for item in projection_items),
            'exact_projection_claimed': False,
        }
        for name, record in geometry.items():
            audit['modules'].setdefault(name, {}).update({
                'dimension': len(record['eigenvalues']),
                'gain_parameters': len(selected_state[name]),
                'group_ids': record['group_ids'].tolist(),
                'incoming_group_gains': incoming_state[name].tolist(),
                'candidate_group_gains': candidate_state[name].tolist(),
                'selected_group_gains': selected_state[name].tolist(),
            })
    return operators, {name: value.clone() for name, value in selected_state.items()}, audit
