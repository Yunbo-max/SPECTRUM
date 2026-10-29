"""CPU numerical contracts; these do not qualify a real VLM or Android device."""
from types import SimpleNamespace

import pytest
import torch
from torch import nn

from improving.android.geometry import (
    _captured_native_outputs,
    _collect_moments,
    collect_operators,
    folded_operators,
    mix_moments,
    select_targets,
)
from improving.spectral import make_operator


def test_moment_mixture_is_psd_and_feedback_changes_preserved_axis():
    anchor = torch.diag(torch.tensor([9.0, 1.0]))
    feedback = torch.diag(torch.tensor([1.0, 9.0]))
    a, _ = mix_moments(anchor, feedback, alpha=0)
    f, receipt = mix_moments(anchor, feedback, alpha=0.9)
    assert torch.linalg.eigvalsh(f).min() >= 0
    assert f.trace().item() == pytest.approx(1)
    a_op, f_op = make_operator(a), make_operator(f)
    assert a_op[0, 0] > a_op[1, 1]
    assert f_op[1, 1] > f_op[0, 0]
    assert receipt["effective_alpha"] == 0.9
    assert receipt["fallback_reason"] is None


def test_tiny_feedback_does_not_normalize_noise_into_geometry():
    anchor = torch.diag(torch.tensor([4.0, 1.0], dtype=torch.float64))
    expected = anchor / anchor.trace()
    for feedback in (None, torch.zeros(2, 2), torch.diag(torch.tensor([0.0, 1e-30], dtype=torch.float64))):
        actual, receipt = mix_moments(anchor, feedback, alpha=0.9, trace_floor=1e-20)
        assert torch.equal(actual, expected)
        assert receipt["effective_alpha"] == 0
    with pytest.raises(ValueError, match="anchor has no"):
        mix_moments(torch.zeros(2, 2), torch.eye(2))
    with pytest.raises(ValueError, match="positive semidefinite"):
        mix_moments(torch.diag(torch.tensor([-1.0, 2.0])), None)


class _Block(nn.Module):
    def __init__(self):
        super().__init__()
        self.self_attn = nn.Module()
        self.self_attn.k_proj = nn.Linear(3, 3)
        self.self_attn.v_proj = nn.Linear(3, 3)

    def forward(self, hidden):
        k = self.self_attn.k_proj(hidden)
        v = self.self_attn.v_proj(hidden)
        return torch.tanh(hidden + torch.cumsum(k + v, dim=1))


class _VisualToy(nn.Module):
    def __init__(self):
        super().__init__()
        torch.manual_seed(3)
        self.config = SimpleNamespace(text_config=SimpleNamespace(num_hidden_layers=2))
        self.model = nn.Module()
        self.model.language_model = nn.Module()
        self.model.language_model.layers = nn.ModuleList([_Block(), _Block()])
        self.embedding = nn.Embedding(8, 3)
        self.lm_head = nn.Linear(3, 8)
        self.visual_calls = 0

    def forward(self, input_ids, attention_mask, pixel_values, image_grid_thw, logits_to_keep=None, use_cache=False):
        assert pixel_values is not None and image_grid_thw is not None
        assert use_cache is False
        self.visual_calls += 1
        hidden = self.embedding(input_ids) + pixel_values.sum() * torch.tensor([0.7, -0.2, 0.3])
        for layer in self.model.language_model.layers:
            hidden = layer(hidden)
        if logits_to_keep is not None:
            hidden = hidden[:, logits_to_keep]
        return SimpleNamespace(logits=self.lm_head(hidden))


class _Policy:
    checkpoint = "test-only-native-checkpoint"

    def __init__(self):
        self.model = _VisualToy()

    def encode_example(self, example, feedback=None):
        prefix = [1, 3, 2] if feedback else [1, 2]
        response = example["response_token_ids"]
        ids = torch.tensor([prefix + response])
        return {
            "inputs": {
                "input_ids": ids,
                "attention_mask": torch.ones_like(ids),
                "pixel_values": torch.tensor([[float(example.get("image_value", 0.2))]]),
                "image_grid_thw": torch.tensor([[1, 1, 1]]),
            },
            "prompt_length": len(prefix),
            "response_length": len(response),
        }


def _example(split="calibration", **kwargs):
    return {
        "messages": [{"role": "user", "content": [{"type": "image", "image": "test-only.png"}]}],
        "response": "synthetic unit-test output",
        "response_token_ids": [4, 5],
        "policy": "native",
        "split": split,
        "feedback": "test-only successful alternative",
        "episode_id": "unit-test-episode",
        **kwargs,
    }


def test_native_visual_moments_include_image_and_real_teacher_prefix():
    policy = _Policy()
    names = select_targets(policy.model, {"last_n_layers": 2})
    a = _collect_moments(policy, [_example(image_value=0.2)], names, "anchor", {})
    b = _collect_moments(policy, [_example(image_value=1.8)], names, "anchor", {})
    feedback = _collect_moments(policy, [_example("train")], names, "feedback", {"kl_top_k": 0})
    assert policy.model.visual_calls == 4  # two NLL passes, teacher and student KL
    for name in names:
        assert a[name]["example_count"] == 1
        assert a[name]["token_count"] == 4  # prompt positions included
        assert a[name]["target_token_count"] == 2
        assert not torch.allclose(a[name]["covariance"], b[name]["covariance"])
        assert feedback[name]["covariance"].trace() > 0
        assert all(p.grad is None for p in policy.model.parameters())


def test_capture_and_folding_restore_model_after_exception():
    policy = _Policy()
    model = policy.model
    model.train()
    model.embedding.eval()
    next(model.parameters()).requires_grad_(False)
    states = [(m, m.training) for m in model.modules()]
    requires = [(p, p.requires_grad) for p in model.parameters()]
    before = {name: p.detach().clone() for name, p in model.named_parameters()}
    names = select_targets(model, {"layers": [1]})
    with pytest.raises(RuntimeError, match="injected"):
        with _captured_native_outputs(model, names) as capture:
            capture["enabled"] = True
            encoded = policy.encode_example(_example())
            model(**encoded["inputs"])
            raise RuntimeError("injected")
    assert all(m.training == state for m, state in states)
    assert all(p.requires_grad == state for p, state in requires)
    assert all(not model.get_submodule(name)._forward_hooks for name in names)
    with pytest.raises(RuntimeError, match="generation"):
        with folded_operators(model, {name: torch.eye(3) * 0.5 for name in names}):
            assert not torch.equal(model.get_submodule(names[0]).weight, before[names[0] + ".weight"])
            raise RuntimeError("generation")
    assert all(torch.equal(p, before[name]) for name, p in model.named_parameters())


@pytest.mark.parametrize("split,policy_name", [("eval", "native"), ("calibration", "native"), ("train", "spectral")])
def test_feedback_rejects_evaluation_and_spectral_prefixes(split, policy_name):
    policy = _Policy()
    names = select_targets(policy.model, {"layers": [1]})
    with pytest.raises(ValueError):
        _collect_moments(policy, [_example(split, policy=policy_name)], names, "feedback", {})
    assert policy.model.visual_calls == 0


def test_missing_visual_tensor_is_not_silently_text_calibrated():
    policy = _Policy()
    encode = policy.encode_example

    def text_only(*args, **kwargs):
        encoded = encode(*args, **kwargs)
        del encoded["inputs"]["pixel_values"]
        return encoded

    policy.encode_example = text_only
    with pytest.raises(ValueError, match="pixel_values"):
        _collect_moments(policy, [_example()], select_targets(policy.model, {"layers": [1]}), "anchor", {})


def test_collect_bootstrap_persists_receipts_and_never_overwrites(tmp_path):
    policy = _Policy()
    operators, receipt = collect_operators(policy, [_example()], [], {"spectral": {"layers": [1]}}, tmp_path)
    assert len(operators) == 2
    assert all(info["effective_alpha"] == 0 for info in receipt["targets"].values())
    assert (tmp_path / "operators.pt").is_file()
    assert (tmp_path / "calibration.json").is_file()
    with pytest.raises(FileExistsError):
        collect_operators(policy, [_example()], [], {"spectral": {"layers": [1]}}, tmp_path)
