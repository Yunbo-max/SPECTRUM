"""CPU/unit contracts for the label-free PI-SPECTRUM arm.

These are software assertions, not evidence of benchmark gains.
"""
from copy import deepcopy
from types import SimpleNamespace

import pytest
import torch
from torch import nn

from improving.pipeline import validate_config
from improving.pi_spectrum import (
    _pi_kl, _teacher_task, _plan_task, build_pi_pairs, choose_pi_tasks,
    collect_pi_covariances, public_task, solve_pi_gains, validate_pi_settings,
)
from improving.utils import stable_hash


def pi_config():
    return {
        "methods": ["spectral_pi"],
        "model": {"name": "mock-7b"},
        "data": {"train": "train.jsonl", "validation": "dev.jsonl",
                 "eval": "eval.jsonl"},
        "output_dir": "runs/pi-only-test",
        "pi_spectrum": {"fit_examples": 1, "guard_examples": 1, "probe_examples": 1},
        "generation": {"train_samples": 2, "eval_samples": 4,
                       "max_new_tokens": 8, "max_prompt_tokens": 32},
        "train": {"max_length": 64, "require_full_completion_targets": True},
        "evaluation": {"backend": "none", "ks": [1, 4]},
    }


def test_pi_config_has_no_calibration_split_or_27b_teacher():
    config = pi_config()
    assert validate_config(config)["methods"] == ["spectral_pi"]
    config["data"]["calibration"] = "gold.jsonl"
    with pytest.raises(ValueError, match="data keys"):
        validate_config(config)
    config = pi_config()
    config["methods"] = ["plain", "spectral_pi"]
    with pytest.raises(ValueError):
        validate_config(config)
    config = pi_config()
    config["train"]["fixed_anchor_replay"] = True
    with pytest.raises(ValueError, match="anchor"):
        validate_config(config)


@pytest.mark.parametrize("change", [
    {"fit_examples": 0}, {"guard_examples": 0}, {"probe_examples": 0},
    {"max_length": 20, "rollout_max_new_tokens": 64},
    {"plan_temperature": 0}, {"rollout_temperature": float("nan")},
    {"top_p": 1.1}, {"top_k": -1}, {"layers": [0, -2]},
    {"gain_learning": {"min_gain": 0}},
    {"unknown": "unsafe"},
])
def test_pi_settings_reject_invalid_input(change):
    with pytest.raises(ValueError):
        validate_pi_settings(change)


def task(index):
    return {
        "task_id": f"MBPP/{index}",
        "prompt": f"Write code for exercise {index}",
        "source": "mbpp", "split": "train",
        "reference": "SECRET LABEL - NEVER USE",
        "tests": "PRIVATE TESTS - NEVER USE",
        "calibration_spans": [[0, 4]],
        "correct": True,
    }


def test_teacher_training_inputs_never_receive_gold_or_verifier_fields():
    settings = validate_pi_settings({
        "fit_examples": 1, "guard_examples": 1, "probe_examples": 1,
    })
    train = [task(i) for i in range(3)]
    fit, guard, probe = choose_pi_tasks(train, settings)
    assert len(fit) == len(guard) == len(probe) == 1
    for sample in fit + guard + probe:
        assert set(sample) == {"task_id", "prompt", "source", "split"}
        assert "SECRET" not in str(sample)
        assert "PRIVATE TESTS" not in str(sample)
    assert "SECRET" not in _teacher_task(public_task(train[0]), "Try DP")["prompt"]
    assert "SECRET" not in _plan_task(public_task(train[0]))["prompt"]


class Tokenizer:
    chat_template = None
    pad_token_id = 0

    def encode(self, text, add_special_tokens=False):
        assert not add_special_tokens
        return [1 + (ord(char) % 60) for char in text]


def test_pi_rollout_positions_match_teacher_without_retokenising_suffix():
    tok = Tokenizer()
    t = public_task(task(1))
    plan_prompt = _plan_task(t)["prompt"]
    ids = [7, 3, 8, 6]
    plans = [{"task_id": t["task_id"], "sample_id": 0,
              "completion": "Use a loop and seen set",
              "prompt_sha256": stable_hash(plan_prompt)}]
    rolls = [{"task_id": t["task_id"], "sample_id": 0,
              "completion_ids": ids, "generation_tokens": len(ids),
              "prompt_tokens": len(tok.encode(t["prompt"])),
              "prompt_sha256": stable_hash(t["prompt"])}]
    pairs = build_pi_pairs(tok, [t], plans, rolls, max_length=2048)
    pair = pairs[0]
    assert pair["student_ids"][-4:] == ids
    assert pair["teacher_ids"][-4:] == ids
    assert pair["teacher_start"] > pair["student_start"]
    assert pair["targets"] == 4
    rolls[0]["prompt_sha256"] = "mismatch"
    with pytest.raises(ValueError, match="SHA"):
        build_pi_pairs(tok, [t], plans, rolls, max_length=2048)


def test_pi_kl_computes_tokenwise_teacher_student_difference():
    q = torch.tensor([[0.8, 0.1, 0.1], [0.2, 0.6, 0.2]], dtype=torch.float32)
    logits = q.log()[None].detach().requires_grad_(True)
    pair = {"student_start": 0, "targets": 2, "teacher_p": q}
    loss = _pi_kl(logits, pair)
    assert abs(float(loss.detach())) < 1e-6
    loss.backward()
    assert logits.grad is not None
    assert torch.linalg.vector_norm(logits.grad) < 1e-6

    shifted = (q.log() + torch.tensor([1., -1., 0.]))[None].detach().requires_grad_(True)
    loss = _pi_kl(shifted, pair)
    assert float(loss) > 0
    loss.backward()
    assert torch.linalg.vector_norm(shifted.grad) > 0


class TinyLM(nn.Module):
    """A tiny frozen causal model with inspectable pre-RoPE K/V equivalent."""
    def __init__(self):
        super().__init__()
        self.embedding = nn.Embedding(16, 2)
        self.k_proj = nn.Linear(2, 2, bias=True)
        self.head = nn.Linear(2, 3, bias=False)
        self.config = SimpleNamespace(use_cache=True)
        self.is_gradient_checkpointing = False
        with torch.no_grad():
            self.embedding.weight.fill_(1)
            self.k_proj.weight.copy_(torch.eye(2))
            self.k_proj.bias.zero_()
            self.head.weight.copy_(torch.tensor([
                [0., 0.], [2., 0.], [-2., 0.],
            ]))

    def get_input_embeddings(self):
        return self.embedding

    def forward(self, *, input_ids=None, inputs_embeds=None,
                attention_mask=None, use_cache=False):
        if inputs_embeds is None:
            inputs_embeds = self.embedding(input_ids)
        state = self.k_proj(inputs_embeds)
        return SimpleNamespace(logits=self.head(state))


def synthetic_target(model):
    ids = [1, 2, 3, 4]
    native = model(input_ids=torch.tensor([ids])).logits[:, :2, :][0].detach().cpu()
    return {
        "task_id": "MBPP/1", "student_ids": ids, "student_start": 0,
        "targets": 2, "native_logits": native,
        "teacher_p": torch.tensor([[.90, .05, .05], [.90, .05, .05]]),
    }


def test_pi_gradient_geometry_and_fitted_operator_restore_frozen_model():
    model = TinyLM()
    original = deepcopy(model.state_dict())
    target = synthetic_target(model)
    cov = collect_pi_covariances(model, [target], ["k_proj"])
    assert cov["k_proj"]["covariance"].shape == (2, 2)
    assert float(cov["k_proj"]["covariance"].trace()) > 0
    operators, audit = solve_pi_gains(
        model, [target], [target], [target], cov,
        {"max_steps": 2, "learning_rate": .2, "kl_budget": 1.0}
    )
    assert set(operators) == {"k_proj"}
    assert audit["selected_identity"] == audit["identity_fallback"]
    assert isinstance(audit["accepted_steps"], int)
    eig = torch.linalg.eigvalsh(operators["k_proj"])
    assert float(eig.min()) >= .1 - 1e-6
    assert float(eig.max()) <= 1 + 1e-6
    for name, value in original.items():
        torch.testing.assert_close(value, model.state_dict()[name])
    assert model.config.use_cache is True
