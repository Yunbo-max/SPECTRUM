"""Authored software contracts; execute on Local, not evidence of method gains.

The models below have known logits and derivatives. They exercise actual native
folding, shared warm starts, separate old-domain constraints and failure cleanup.
"""
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace

import pytest
import torch
from torch import nn

import improving.continual_gains as gains
from improving.learned_gains import SpectralGainLinear
from improving.spectral import folded_operators


class GainLM(nn.Module):
    """Logits [0, a_0-center, center-a_0] at the selected position."""

    def __init__(self, *, center=0.0, zero_signal=False):
        super().__init__()
        self.embedding = nn.Embedding(4, 2).double()
        self.k_proj = nn.Linear(2, 2, bias=True).double()
        self.head = nn.Linear(2, 3, bias=False).double()
        self.config = SimpleNamespace(use_cache=True, text_config=SimpleNamespace(use_cache=True))
        self.is_gradient_checkpointing = False
        self.center, self.fail = center, None
        with torch.no_grad():
            self.embedding.weight.fill_(1.)
            self.k_proj.weight.copy_(torch.eye(2, dtype=torch.float64))
            self.k_proj.bias.zero_()
            self.head.weight.copy_(torch.tensor([[0., 0.], [1., 0.], [-1., 0.]], dtype=torch.float64))
            if zero_signal:
                self.head.weight.zero_()

    def get_input_embeddings(self):
        return self.embedding

    def forward(self, *, input_ids, attention_mask, use_cache=False):
        assert use_cache is False
        hidden = self.k_proj(self.embedding(input_ids))
        if self.fail == 'always' or (self.fail == 'wrapper' and isinstance(self.k_proj, SpectralGainLinear)):
            raise RuntimeError('synthetic forward failure')
        offset = torch.tensor([self.center, 0.], dtype=hidden.dtype, device=hidden.device)
        return SimpleNamespace(logits=self.head((hidden - offset) * attention_mask.unsqueeze(-1)))


def example(target=0, marker=1):
    return {'input_ids': torch.tensor([[marker, 0, 0]]),
            'attention_mask': torch.tensor([[1, 1, 0]]),
            'labels': torch.tensor([[-100, target, -100]])}


def geometry(model):
    return gains.build_gain_geometry(model, {
        'k_proj': {'covariance': torch.diag(torch.tensor([1., 4.], dtype=torch.float64))}})


def run_fit(model, *, initial=None, memories=None, limits=None, mode='conflict',
            target=0, guard_target=None, settings=None):
    cfg = {'max_steps': 1, 'learning_rate': .2, 'max_backtracks': 0,
           'kl_budget': 1., 'guard_tolerance': 0., 'projection_max_cycles': 200}
    cfg.update(settings or {})
    return gains.fit_continual_operators(
        model, [example(target, 1)], [example(target if guard_target is None else guard_target, 2)],
        [example(0, 3)], geometry(model), initial_gains=initial,
        retention_batches=memories, retention_limits=limits, mode=mode, settings=cfg)


def snapshot(model):
    return {'tensors': deepcopy(model.state_dict()),
            'parameters': {name: id(p) for name, p in model.named_parameters()},
            'flags': {name: p.requires_grad for name, p in model.named_parameters()},
            'grads': {name: None if p.grad is None else p.grad.clone()
                      for name, p in model.named_parameters()},
            'states': {name: m.training for name, m in model.named_modules()},
            'cache': (model.config.use_cache, model.config.text_config.use_cache),
            'projection': model.k_proj}


def assert_restored(model, before):
    assert model.k_proj is before['projection']
    assert {name: id(p) for name, p in model.named_parameters()} == before['parameters']
    assert {name: p.requires_grad for name, p in model.named_parameters()} == before['flags']
    assert {name: m.training for name, m in model.named_modules()} == before['states']
    assert (model.config.use_cache, model.config.text_config.use_cache) == before['cache']
    for name, value in model.state_dict().items():
        assert torch.equal(value, before['tensors'][name])
    for name, parameter in model.named_parameters():
        original = before['grads'][name]
        assert (parameter.grad is None) == (original is None)
        if original is not None:
            assert torch.equal(parameter.grad, original)


def test_compatible_direction_is_unchanged():
    proposed = torch.tensor([-.1, -.2], dtype=torch.float64)
    result, audit = gains.project_gain_step(proposed, torch.tensor([.6, .6], dtype=torch.float64),
                                            {'old': torch.tensor([2., 1.], dtype=torch.float64)})
    torch.testing.assert_close(result, proposed, atol=1e-12, rtol=0)
    assert audit['feasible'] and audit['converged']
    assert audit['proposed_conflict_domains'] == []
    assert audit['new_old_gradient_cosines']['old'] > 0


def test_single_conflict_matches_conditional_gradient_surgery():
    new = torch.tensor([1., -2.], dtype=torch.float64)
    old = torch.tensor([1., 1.], dtype=torch.float64)
    expected_safe_gradient = new - torch.dot(new, old) / torch.dot(old, old) * old
    # The .1 coefficient here already includes the global gradient normalization.
    result, audit = gains.project_gain_step(-.1 * new, torch.full((2,), .5, dtype=torch.float64),
                                            {'old': old}, tolerance=1e-12)
    torch.testing.assert_close(result, -.1 * expected_safe_gradient, atol=1e-12, rtol=0)
    assert audit['feasible']
    assert audit['proposal']['old_gradient_dot_step']['old'] > 0
    assert audit['old_gradient_dot_step']['old'] <= 1e-12
    assert audit['new_old_gradient_cosines']['old'] < 0
    assert audit['old_gradient_norms']['old'] == pytest.approx(2 ** .5)


def test_multiple_old_halfspaces_need_more_than_one_pairwise_pass():
    old = {'first': torch.tensor([1., 0.], dtype=torch.float64),
           'second': torch.tensor([-1., 1.], dtype=torch.float64)}
    proposed = torch.ones(2, dtype=torch.float64)
    current = torch.full((2,), .5, dtype=torch.float64)
    short, short_audit = gains.project_gain_step(proposed, current, old, max_cycles=1, tolerance=1e-12)
    assert not short_audit['feasible']
    assert torch.dot(old['first'], short) > 0
    result, audit = gains.project_gain_step(proposed, current, old, max_cycles=200, tolerance=1e-12)
    assert audit['feasible'] and audit['cycles'] > 1
    assert all(torch.dot(g, result) <= 1e-12 for g in old.values())
    torch.testing.assert_close(result, torch.zeros_like(result), atol=2e-12, rtol=0)
    assert not audit['exact_projection_claimed']


def test_box_and_halfspaces_are_projected_jointly():
    proposed = torch.tensor([.3, .8], dtype=torch.float64)
    current = torch.tensor([.5, .9], dtype=torch.float64)
    old = {'diagonal': torch.tensor([1., -1.], dtype=torch.float64),
           'other': torch.tensor([-1., -1.], dtype=torch.float64)}
    clipped = torch.minimum(proposed, 1 - current)
    assert torch.dot(old['diagonal'], clipped) > 0, 'box clipping alone reintroduces the conflict'
    result, audit = gains.project_gain_step(proposed, current, old, tolerance=1e-12, max_cycles=200)
    assert audit['feasible']
    torch.testing.assert_close(result, torch.tensor([.1, .1], dtype=torch.float64), atol=2e-12, rtol=0)
    assert bool((current + result <= 1 + 1e-12).all())
    assert all(torch.dot(g, result) <= 1e-12 for g in old.values())


def test_float32_cast_can_reintroduce_conflict_and_is_rechecked():
    native = nn.Linear(2, 2, bias=False)
    wrapper = SpectralGainLinear(native, torch.eye(2, dtype=torch.float64), torch.tensor([0, 1]))
    current = torch.tensor([.25, .75], dtype=torch.float64)
    old = {'old': torch.tensor([-1., 1.], dtype=torch.float64)}
    direction, audit = gains.project_gain_step(torch.tensor([.1, .1], dtype=torch.float64), current, old)
    assert audit['feasible']
    actual = gains._flatten(gains._cast_candidate({'target': wrapper}, current + direction, .1)) - current
    checked = gains._step_feasibility(actual, .1 - current, 1 - current, old, 1e-10)
    assert checked['old_gradient_dot_step']['old'] > 1e-8
    assert not checked['feasible']


@pytest.mark.parametrize('mode', ['retention', 'conflict'])
def test_zero_old_gradient_still_requires_actual_endpoint_retention(mode):
    model = GainLM(center=.5)
    initial = {'k_proj': torch.tensor([.5, 1.], dtype=torch.float64)}
    memories = {'balanced': [example(1), example(2)]}
    _, state, audit = run_fit(model, initial=initial, memories=memories, mode=mode, target=1)
    assert audit['selected_incoming']
    assert torch.equal(state['k_proj'], initial['k_proj'])
    item = audit['history'][0]
    assert item['fit_nll'] < audit['baseline']['fit_nll']
    assert item['reason'] == 'retention_limit_exceeded'
    assert item['retention_nlls']['balanced'] > audit['limits']['balanced'] + 1e-6
    if mode == 'conflict':
        assert item['projection']['zero_gradient_domains'] == ['balanced']


def test_sequential_reports_old_domains_without_enforcing_them():
    model = GainLM(center=.5)
    _, _, audit = run_fit(model, initial={'k_proj': torch.tensor([.5, 1.], dtype=torch.float64)},
                          memories={'old': [example(1), example(2)]}, mode='sequential', target=1)
    assert not audit['selected_incoming']
    assert not audit['retention_enforced']
    assert audit['selected']['retention_nlls']['old'] > audit['limits']['old']
    assert not audit['selected_retention_feasible']


def test_each_old_domain_has_its_own_endpoint_limit_even_if_mean_improves():
    _, _, audit = run_fit(GainLM(), memories={'helps': [example(0)], 'hurts': [example(1)]},
                          mode='retention')
    item = audit['history'][0]
    assert item['reason'] == 'retention_limit_exceeded'
    assert sum(item['retention_nlls'].values()) < sum(audit['baseline']['retention_nlls'].values())
    assert set(item['retention_violations']) == {'hurts'}
    assert audit['selected_incoming']


def test_selected_gains_warm_start_next_stage_without_touching_native_weights():
    model = GainLM()
    before = snapshot(model)
    fixed = geometry(model)
    first_ops, first_state, first = run_fit(model, mode='sequential')
    second_ops, second_state, second = gains.fit_continual_operators(
        model, [example(0, 1)], [example(0, 2)], [example(0, 3)], fixed,
        initial_gains=first_state, mode='sequential',
        settings={'max_steps': 1, 'learning_rate': .1, 'kl_budget': 1.})
    assert not first['selected_incoming'] and not second['selected_incoming']
    assert second['baseline']['fit_nll'] == pytest.approx(first['selected']['fit_nll'], abs=1e-12)
    assert second_state['k_proj'][0] < first_state['k_proj'][0] < 1
    assert second_ops['k_proj'][0, 0] < first_ops['k_proj'][0, 0]
    assert second['modules']['k_proj']['incoming_group_gains'] == first_state['k_proj'].tolist()
    assert_restored(model, before)


def test_kl_is_anchored_to_incoming_controlled_policy_not_native():
    model = GainLM()
    initial = {'k_proj': torch.tensor([.5, 1.], dtype=torch.float64)}
    ops, _, audit = run_fit(model, initial=initial, settings={'learning_rate': .05, 'kl_budget': .005})
    assert not audit['selected_incoming']
    batch = example()
    with torch.no_grad():
        native = model(input_ids=batch['input_ids'], attention_mask=batch['attention_mask']).logits[0, 0]
        with folded_operators(model, gains.operators_from_gain_state(geometry(model), initial)):
            incoming = model(input_ids=batch['input_ids'], attention_mask=batch['attention_mask']).logits[0, 0]
        with folded_operators(model, ops):
            selected = model(input_ids=batch['input_ids'], attention_mask=batch['attention_mask']).logits[0, 0]
    def kl(left, right):
        logp, logq = left.log_softmax(-1), right.log_softmax(-1)
        return float((logp.exp() * (logp - logq)).sum())
    assert audit['selected']['probe_kl']['mean'] == pytest.approx(kl(incoming, selected), abs=1e-12)
    assert kl(native, selected) > audit['kl_budget'] > kl(incoming, selected)
    assert audit['baseline']['probe_kl']['mean'] == pytest.approx(0., abs=1e-12)


def test_final_guard_veto_restores_incoming_instead_of_identity():
    initial = {'k_proj': torch.tensor([.7, .9], dtype=torch.float64)}
    model = GainLM()
    ops, state, audit = run_fit(model, initial=initial, guard_target=1, settings={'max_steps': 2})
    assert audit['accepted_steps'] == 2, 'the adverse guard must not select or stop intermediate iterates'
    assert audit['selected_incoming'] and audit['fallback_reason'] == 'wrapper_guard_deteriorated'
    assert torch.equal(state['k_proj'], initial['k_proj'])
    expected = gains.operators_from_gain_state(geometry(model), initial)
    assert torch.equal(ops['k_proj'], expected['k_proj'])
    assert not torch.equal(ops['k_proj'], torch.eye(2, dtype=torch.float64))


def test_explicit_limits_remain_absolute_and_are_not_reset_per_step():
    limits = {'old': 10.}
    _, _, audit = run_fit(GainLM(), memories={'old': [example(1)]}, limits=limits,
                          mode='retention', settings={'max_steps': 2})
    assert audit['limits'] == limits and audit['limit_source'] == 'explicit'
    assert audit['accepted_steps'] == 2
    assert len(audit['history']) == 2
    assert all(not item['retention_violations'] for item in audit['history'])


def test_infeasible_incoming_explicit_limit_is_reported_on_fallback():
    _, _, audit = run_fit(GainLM(), memories={'old': [example(1)]}, limits={'old': 0.}, mode='retention')
    assert audit['selected_incoming']
    assert set(audit['baseline_retention_violations']) == {'old'}
    assert not audit['selected_retention_feasible']
    assert set(audit['selected_retention_violations']) == {'old'}


@pytest.mark.parametrize('failure', [None, 'always', 'wrapper'])
def test_all_native_state_is_restored_on_success_or_forward_exception(failure):
    model = GainLM()
    model.head.eval()
    model.embedding.requires_grad_(False)
    model.k_proj.weight.grad = torch.full_like(model.k_proj.weight, .123)
    model.fail = failure
    before = snapshot(model)
    if failure:
        with pytest.raises(RuntimeError, match='synthetic forward failure'):
            run_fit(model)
    else:
        run_fit(model)
    assert_restored(model, before)


@pytest.mark.parametrize('raise_error', [False, True])
def test_actual_folded_candidate_is_checked_and_fold_exceptions_restore_state(monkeypatch, raise_error):
    real_fold = gains.folded_operators
    checked = []

    @contextmanager
    def bad_candidate_fold(model, operators):
        # Initial a=1 and its probe anchor remain correct. Only the learned
        # candidate's deployment path is altered, after the wrapper fit.
        candidate = float(operators['k_proj'][0, 0]) < .999
        effective = ({name: torch.eye(op.shape[0], dtype=op.dtype) * 2
                      for name, op in operators.items()} if candidate else operators)
        with real_fold(model, effective):
            if candidate:
                checked.append(True)
                if raise_error:
                    raise RuntimeError('synthetic folded failure')
            yield model

    monkeypatch.setattr(gains, 'folded_operators', bad_candidate_fold)
    model = GainLM()
    before = snapshot(model)
    if raise_error:
        with pytest.raises(RuntimeError, match='synthetic folded failure'):
            run_fit(model)
    else:
        _, state, audit = run_fit(model)
        assert audit['accepted_steps'] == 1
        assert audit['selected_incoming']
        assert 'folded_fit_not_improved' in audit['fallback_reason']
        assert torch.equal(state['k_proj'], torch.ones(2, dtype=torch.float64))
    assert checked
    assert_restored(model, before)


def test_folded_old_domain_failure_vetoes_an_otherwise_good_candidate(monkeypatch):
    model = GainLM()
    with torch.no_grad():
        # Current FIT/guard/probe use coordinate zero; old FIT uses coordinate one.
        model.embedding.weight[:, 0] = 1
        model.embedding.weight[:, 1] = 0
        model.embedding.weight[0] = torch.tensor([0., 1.], dtype=torch.float64)
        model.head.weight.copy_(torch.tensor([[0., 0.], [1., 1.], [-1., -1.]], dtype=torch.float64))
    real_fold = gains.folded_operators

    @contextmanager
    def old_domain_fold_mismatch(native, operators):
        effective = {name: op.clone() for name, op in operators.items()}
        if float(effective['k_proj'][0, 0]) < .999:
            effective['k_proj'][1, 1] = 2.
        with real_fold(native, effective):
            yield native

    monkeypatch.setattr(gains, 'folded_operators', old_domain_fold_mismatch)
    before = snapshot(model)
    _, _, audit = run_fit(model, memories={'old': [example(0, 0)]})
    assert audit['accepted_steps'] == 1
    assert audit['wrapper']['retention_nlls']['old'] <= audit['limits']['old'] + 1e-6
    assert audit['folded_candidate']['fit_nll'] < audit['baseline']['fit_nll']
    assert audit['folded_candidate']['guard_nll'] < audit['baseline']['guard_nll']
    assert audit['folded_candidate']['probe_kl']['mean'] < audit['kl_budget']
    assert audit['fallback_reason'] == 'folded_retention_limit_exceeded'
    assert audit['selected_incoming']
    assert_restored(model, before)


def test_nonfinite_candidate_is_a_recorded_rejection_with_incoming_fallback(monkeypatch):
    model = GainLM()
    native_forward = model.forward

    def forward(**kwargs):
        output = native_forward(**kwargs)
        if isinstance(model.k_proj, SpectralGainLinear) and float(model.k_proj.gains[0]) < .9:
            output.logits = output.logits * float('nan')
        return output

    monkeypatch.setattr(model, 'forward', forward)
    before = snapshot(model)
    _, state, audit = run_fit(model)
    assert audit['history'][0]['reason'] == 'nonfinite_candidate'
    assert audit['selected_incoming']
    assert torch.equal(state['k_proj'], torch.ones(2, dtype=torch.float64))
    assert_restored(model, before)


@pytest.mark.parametrize('limits', [{}, {'other': 1.}, {'old': -1.}, {'old': float('nan')}, {'old': True}])
def test_invalid_or_unbound_limits_fail_before_any_forward(limits):
    model = GainLM()
    model.fail = 'always'
    before = snapshot(model)
    with pytest.raises(ValueError, match='retention'):
        run_fit(model, memories={'old': [example()]}, limits=limits)
    assert_restored(model, before)


@pytest.mark.parametrize('settings', [
    {'projection_max_cycles': 0}, {'projection_max_cycles': True},
    {'projection_tolerance': -1.}, {'projection_tolerance': float('inf')},
    {'retention_tolerance': -1.}, {'retention_tolerance': True}, {'unknown': 1},
])
def test_invalid_continual_settings(settings):
    with pytest.raises(ValueError):
        gains.validate_continual_settings(settings)


def test_geometry_ties_and_state_binding_are_explicit():
    model = GainLM()
    fixed = gains.build_gain_geometry(model, {'k_proj': {'covariance': torch.eye(2, dtype=torch.float64)}})
    assert fixed['k_proj']['group_ids'].tolist() == [0, 0]
    identity = gains.identity_gain_state(fixed)
    assert identity['k_proj'].shape == (1,)
    ops = gains.operators_from_gain_state(fixed, {'k_proj': torch.tensor([.5], dtype=torch.float64)})
    torch.testing.assert_close(ops['k_proj'], torch.eye(2, dtype=torch.float64) * .5)
    with pytest.raises(ValueError, match='module names'):
        gains.operators_from_gain_state(fixed, {'wrong': identity['k_proj']})
    with pytest.raises(ValueError, match='gain state'):
        gains.operators_from_gain_state(fixed, {'k_proj': torch.ones(2, dtype=torch.float64)})
    bad = deepcopy(fixed)
    bad['k_proj']['basis'][0, 0] = 2
    with pytest.raises(ValueError, match='orthonormal'):
        gains.identity_gain_state(bad)


def test_invalid_warm_start_lower_bound_is_not_silently_clamped():
    model = GainLM()
    before = snapshot(model)
    with pytest.raises(ValueError, match='gain state'):
        run_fit(model, initial={'k_proj': torch.tensor([.09, 1.], dtype=torch.float64)})
    assert_restored(model, before)
