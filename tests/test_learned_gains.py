"""Software contracts for learned spectral gains; not benchmark evidence.

These regression sources are authored for the native execution host. Synthetic
small tensors/models below test calculus, state restoration and acceptance rules,
not the scientific effectiveness of recursive self-distillation.
"""
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace

import pytest
import torch
from torch import nn

import improving.learned_gains as gains
from improving.spectral import folded_operators


class ControlledCausalLM(nn.Module):
    """Shrinking coordinate zero helps target 0 and hurts target 1.

    At a prefix of length n, native logits are [0, n, -n]. This makes
    acceptance/veto expectations independent of a randomly initialized model.
    """

    def __init__(self, *, zero_signal=False):
        super().__init__()
        self.embedding = nn.Embedding(3, 2)
        self.k_proj = nn.Linear(2, 2, bias=True)
        self.head = nn.Linear(2, 3, bias=False)
        self.config = SimpleNamespace(use_cache=True)
        self.is_gradient_checkpointing = False
        self.fail = False
        with torch.no_grad():
            self.embedding.weight.fill_(1.)
            self.k_proj.weight.copy_(torch.eye(2))
            self.k_proj.bias.zero_()
            self.head.weight.copy_(torch.tensor([[0., 0.], [1., 0.], [-1., 0.]]))
            if zero_signal:
                self.head.weight.zero_()

    def get_input_embeddings(self):
        return self.embedding

    def forward(self, *, input_ids=None, inputs_embeds=None, attention_mask,
                use_cache=False):
        assert use_cache is False
        if inputs_embeds is None:
            inputs_embeds = self.embedding(input_ids)
        hidden = self.k_proj(inputs_embeds)
        if self.fail:
            raise RuntimeError("controlled forward failure")
        context = (hidden * attention_mask.unsqueeze(-1)).cumsum(dim=1)
        return SimpleNamespace(logits=self.head(context))


def case(target=0):
    return {
        "input_ids": torch.tensor([[1, 2, 0, 0]]),
        "attention_mask": torch.tensor([[1, 1, 1, 0]]),
        "labels": torch.tensor([[-100, target, target, -100]]),
    }


def covariance():
    return {"k_proj": {"covariance": torch.diag(torch.tensor([1., 4.], dtype=torch.float64))}}


def fit(model, *, guard_target=0, settings=None):
    effective = {"max_steps": 2, "learning_rate": .2, "max_backtracks": 4,
                 "kl_budget": 1., "guard_tolerance": 0.}
    effective.update(settings or {})
    return gains.fit_learned_operators(
        model, [case()], [case(guard_target)], [case()], covariance(), effective)


def snapshot(model):
    return {
        "tensors": deepcopy(model.state_dict()),
        "parameters": {name: id(p) for name, p in model.named_parameters()},
        "flags": {name: p.requires_grad for name, p in model.named_parameters()},
        "grads": {name: None if p.grad is None else p.grad.clone()
                  for name, p in model.named_parameters()},
        "states": {name: m.training for name, m in model.named_modules()},
        "cache": model.config.use_cache,
        "projection": model.k_proj,
    }


def assert_restored(model, before):
    assert model.k_proj is before["projection"]
    assert {name: id(p) for name, p in model.named_parameters()} == before["parameters"]
    assert {name: p.requires_grad for name, p in model.named_parameters()} == before["flags"]
    assert {name: m.training for name, m in model.named_modules()} == before["states"]
    assert model.config.use_cache == before["cache"]
    for name, tensor in model.state_dict().items():
        assert torch.equal(tensor, before["tensors"][name])
    for name, parameter in model.named_parameters():
        expected = before["grads"][name]
        assert (parameter.grad is None) == (expected is None)
        if expected is not None:
            assert torch.equal(parameter.grad, expected)


def test_signed_gain_derivative_matches_chain_rule_and_finite_difference():
    linear = nn.Linear(2, 2, bias=True).double().requires_grad_(False)
    with torch.no_grad():
        linear.weight.copy_(torch.tensor([[1., .2], [-.3, .8]], dtype=torch.float64))
        linear.bias.copy_(torch.tensor([.1, -.2], dtype=torch.float64))
    angle = torch.tensor(.4, dtype=torch.float64)
    basis = torch.stack((torch.stack((angle.cos(), -angle.sin())),
                         torch.stack((angle.sin(), angle.cos()))))
    wrapper = gains.SpectralGainLinear(linear, basis, torch.tensor([0, 1]))
    x = torch.tensor([[1., -2.], [.5, 3.]], dtype=torch.float64)
    upstream = torch.tensor([[2., -.5], [-1., 1.]], dtype=torch.float64)
    with torch.no_grad():
        wrapper.gains.copy_(torch.tensor([.6, .8], dtype=wrapper.gains.dtype))
    derivative, = torch.autograd.grad((wrapper(x) * upstream).sum(), wrapper.gains)
    expected = ((linear(x) @ basis) * (upstream @ basis)).sum(dim=0)
    torch.testing.assert_close(derivative.double(), expected, rtol=1e-9, atol=1e-10)
    initial = wrapper.gains.detach().clone()
    epsilon = 1e-5
    for i in range(2):
        with torch.no_grad():
            wrapper.gains.copy_(initial)
            wrapper.gains[i] += epsilon
            plus = float((wrapper(x) * upstream).sum())
            wrapper.gains.copy_(initial)
            wrapper.gains[i] -= epsilon
            minus = float((wrapper(x) * upstream).sum())
            wrapper.gains.copy_(initial)
        assert (plus - minus) / (2 * epsilon) == pytest.approx(float(expected[i]), rel=1e-7, abs=1e-8)
    assert derivative.min() < 0 < derivative.max()  # Actual signed utility, not squared energy.


def test_ties_are_scale_invariant_without_artificial_spectral_bands():
    distinct = torch.arange(1., 9., dtype=torch.float64)
    assert gains.spectral_groups(distinct).tolist() == list(range(8))
    values = torch.tensor([0., 0., 1., 1., 4.], dtype=torch.float64)
    expected = [0, 0, 1, 1, 2]
    assert gains.spectral_groups(values).tolist() == expected
    assert gains.spectral_groups(values * 1e8).tolist() == expected
    # A chain of close neighbours must not merge an arbitrarily broad band.
    values = torch.tensor([0., .75e-6, 1.5e-6, 1.], dtype=torch.float64)
    assert gains.spectral_groups(values, rtol=0., atol=1e-6).tolist() == [0, 0, 1, 2]


def test_equal_eigenspace_rotation_does_not_change_intervention():
    linear = nn.Linear(3, 3, bias=False).double().requires_grad_(False)
    with torch.no_grad():
        linear.weight.copy_(torch.eye(3, dtype=torch.float64))
    angle = torch.tensor(.61, dtype=torch.float64)
    rotation = torch.eye(3, dtype=torch.float64)
    rotation[:2, :2] = torch.stack((torch.stack((angle.cos(), -angle.sin())),
                                  torch.stack((angle.sin(), angle.cos()))))
    groups = gains.spectral_groups(torch.tensor([1., 1., 4.], dtype=torch.float64))
    first = gains.SpectralGainLinear(linear, torch.eye(3, dtype=torch.float64), groups)
    rotated = gains.SpectralGainLinear(linear, rotation, groups)
    with torch.no_grad():
        first.gains.copy_(torch.tensor([.3, .9], dtype=first.gains.dtype))
        rotated.gains.copy_(first.gains)
    x = torch.tensor([[1., 2., 3.], [-2., .5, 1.]], dtype=torch.float64)
    torch.testing.assert_close(first(x), rotated(x), atol=1e-12, rtol=1e-12)


def test_full_vocabulary_forward_kl_uses_only_requested_positions():
    p = torch.tensor([.7, .2, .1], dtype=torch.float64)
    q = torch.tensor([.1, .3, .6], dtype=torch.float64)
    native = torch.stack((p.log(), p.log(), p.log()))
    candidate = torch.stack((q.flip(0).log() * 100, q.log(), q.log() * -100))
    mask = torch.tensor([False, True, False])
    total, count, _, _ = gains.forward_kl_sum(native, candidate, mask, chunk_tokens=1)
    expected = float((p * (p.log() - q.log())).sum())
    reverse = float((q * (q.log() - p.log())).sum())
    assert count == 1
    assert total == pytest.approx(expected, rel=2e-6, abs=2e-7)
    assert abs(total - reverse) > .01
    zero, same_count, _, _ = gains.forward_kl_sum(native, native, mask, chunk_tokens=2)
    assert same_count == 1 and zero == pytest.approx(0., abs=1e-7)


def test_real_fit_improves_target_and_checks_folded_probe_kl_with_causal_mask():
    model = ControlledCausalLM()
    operators, audit = fit(model)
    assert not audit["selected_identity"]
    assert operators["k_proj"].dtype == torch.float64
    assert operators["k_proj"].device.type == "cpu"
    assert float(operators["k_proj"][0, 0]) < .999
    assert float(operators["k_proj"][1, 1]) == pytest.approx(1., abs=1e-6)
    assert audit["folded_candidate"]["fit_nll"] < audit["native"]["fit_nll"]
    assert audit["folded_candidate"]["guard_nll"] <= audit["native"]["guard_nll"] + 1e-6
    batch = case()
    with torch.no_grad():
        native = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"]).logits
        with folded_operators(model, operators):
            candidate = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"]).logits
        # Independent calculation: exactly positions 0 and 1 predict valid labels.
        logp = native[0, :2].double().log_softmax(-1)
        logq = candidate[0, :2].double().log_softmax(-1)
        expected_kl = float((logp.exp() * (logp - logq)).sum(-1).mean())
    assert audit["folded_candidate"]["probe_kl"]["mean"] == pytest.approx(expected_kl, rel=3e-5, abs=2e-6)
    assert audit["folded_candidate"]["probe_kl"]["tokens"] == 2
    assert audit["folded_candidate"]["probe_kl"]["mean"] <= 1.


def test_kl_budget_can_reject_a_fit_improvement_without_using_guard():
    operators, audit = fit(ControlledCausalLM(), settings={
        "max_steps": 1, "max_backtracks": 0, "learning_rate": .3, "kl_budget": 0.,
    })
    assert audit["selected_identity"]
    assert audit["accepted_steps"] == 0
    assert audit["history"][0]["fit_nll"] < audit["native"]["fit_nll"]
    assert audit["history"][0]["reason"] == "probe_kl_budget_exceeded"
    assert torch.equal(operators["k_proj"], torch.eye(2, dtype=torch.float64))


@pytest.mark.parametrize("zero_signal,guard_target", [(True, 0), (False, 1)])
def test_no_signal_or_adverse_guard_returns_exact_identity(zero_signal, guard_target):
    operators, audit = fit(ControlledCausalLM(zero_signal=zero_signal), guard_target=guard_target)
    assert audit["selected_identity"]
    assert audit["fallback_reason"]
    assert torch.equal(operators["k_proj"], torch.eye(2, dtype=torch.float64))
    if not zero_signal:
        assert audit["accepted_steps"] > 0
        assert audit["wrapper"]["fit_nll"] < audit["native"]["fit_nll"]
        assert audit["wrapper"]["guard_nll"] > audit["native"]["guard_nll"]
        assert audit["fallback_reason"] == "wrapper_guard_deteriorated"
        assert audit["folded_candidate"] is None


@pytest.mark.parametrize("fail", [False, True])
def test_calibration_restores_weights_modules_flags_and_existing_gradients(fail):
    model = ControlledCausalLM()
    model.head.eval()
    model.embedding.requires_grad_(False)
    model.k_proj.weight.grad = torch.ones_like(model.k_proj.weight) * .123
    before = snapshot(model)
    model.fail = fail
    if fail:
        with pytest.raises(RuntimeError, match="controlled forward failure"):
            fit(model)
    else:
        fit(model)
    assert_restored(model, before)


def test_actual_folded_policy_is_checked_before_acceptance(monkeypatch):
    native_folding = gains.folded_operators
    calls = []

    @contextmanager
    def adversarial_folding(model, operators):
        # Emulates a fold-path mismatch: the differentiable candidate is good,
        # but the actual generator doubles the harmful first coordinate.
        calls.append(True)
        with native_folding(model, {name: torch.eye(op.shape[0], dtype=op.dtype) * 2
                                    for name, op in operators.items()}):
            yield model

    monkeypatch.setattr(gains, "folded_operators", adversarial_folding)
    model = ControlledCausalLM()
    before = snapshot(model)
    operators, audit = fit(model)
    assert calls, "A wrapper-only feasibility check is not sufficient"
    assert audit["selected_identity"]
    assert "fold" in audit["fallback_reason"].lower()
    assert torch.equal(operators["k_proj"], torch.eye(2, dtype=torch.float64))
    assert_restored(model, before)


@pytest.mark.parametrize("settings", [
    {"unknown_key": 1}, {"max_steps": True}, {"max_steps": 0},
    {"learning_rate": 0.}, {"learning_rate": float("nan")},
    {"min_gain": 0.}, {"min_gain": 1.1}, {"kl_budget": -1.},
    {"max_backtracks": 1.5}, {"backtrack_factor": 1.},
    {"guard_tolerance": -1.}, {"degeneracy_rtol": float("inf")},
    {"kl_chunk_tokens": 0},
])
def test_invalid_gain_settings_fail_before_model_mutation(settings):
    with pytest.raises((ValueError, TypeError)):
        gains.validate_gain_settings(settings)

