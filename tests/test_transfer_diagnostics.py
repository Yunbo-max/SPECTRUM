"""No-GPU tests of transfer-gap config, task isolation and three-state metrics."""
import copy
import pytest
import torch
from torch import nn
from types import SimpleNamespace

from improving.transfer_diagnostics import (
    ROLES, compare_three_states, transfer_settings, validate_development_tasks,
)
from improving.metrics import summarize_records


def configuration():
    return {
        "methods": ["spectral_learned"], "rounds": 10,
        "generation": {"max_new_tokens": 4096, "max_prompt_tokens": 2048,
                       "temperature": .8, "top_p": .95, "top_k": 0},
        "evaluation": {"backend": "docker", "allow_unsafe_local": False},
        "diagnostics": {"transfer_gap": {
            "enabled": True, "rounds": [1, 5, 8, 10],
            "samples": 64, "validation_task_count": 30,
            "batch_size": 1, "task_batch_size": 1, "sequence_batch_size": 1,
            "max_prompt_tokens": 2048, "max_new_tokens": 4096,
            "reference_nll_each_round": True,
        }},
    }


def test_transfer_settings_requires_heldout_full_dev_and_isolated_verifier():
    cfg = configuration()
    assert transfer_settings(cfg)["samples"] == 64
    for field, value, match in [
        ("samples", 16, ">=64"),
        ("validation_task_count", 29, "30-task"),
        ("max_new_tokens", 256, "4096-token"),
        ("rounds", [1, 5, 5], "distinct"),
    ]:
        invalid = copy.deepcopy(cfg)
        invalid["diagnostics"]["transfer_gap"][field] = value
        with pytest.raises(ValueError, match=match):
            transfer_settings(invalid)
    invalid = copy.deepcopy(cfg)
    invalid["evaluation"]["backend"] = "local"
    invalid["evaluation"]["allow_unsafe_local"] = False
    with pytest.raises(ValueError, match="allow_unsafe_local"):
        transfer_settings(invalid)
    local = copy.deepcopy(cfg)
    local["evaluation"]["backend"] = "local"
    local["evaluation"]["allow_unsafe_local"] = True
    assert transfer_settings(local)["samples"] == 64


def task(label, split):
    return {"task_id": f"Fixture/{label}", "split": split,
            "source": "synthetic-test-only", "prompt": f"Test {label}"}


def test_dev_cannot_be_calibration_or_eval_or_train():
    dev = [task(f"dev{i}", "validation") for i in range(30)]
    train = [task("train", "train")]
    cal = [task("cal", "calibration")]
    test = [task("test", "eval")]
    validate_development_tasks(dev, train, cal, test)
    with pytest.raises(ValueError, match="validation"):
        validate_development_tasks([*dev[:-1], test[0]], train, cal, test)
    with pytest.raises(ValueError):
        validate_development_tasks(dev, train, [dev[0]], test)


def fake_summary(task_correct_counts):
    rows = []
    for task_id, correct in task_correct_counts.items():
        for i in range(64):
            yes = i < correct
            rows.append({"task_id": task_id, "sample_id": i,
                         "correct": yes,
                         "code": ("def f(x):\n    return x" if i % 2 == 0
                                  else "def f(x):\n    return x+1"),
                         "completion": "program"})
    return summarize_records(rows, ks=[1, 4, 8, 16, 32, 64],
                             correct_budget=4, correct_budgets=[4, 8, 16, 32, 64],
                             bootstrap_samples=10,
                             expected_samples={task: 64 for task in task_correct_counts})


def test_three_state_telescoping_and_correct_ast_reallocation():
    a = fake_summary({"dev/a": 10, "dev/b": 0})
    b = fake_summary({"dev/a": 20, "dev/b": 1})
    c = fake_summary({"dev/a": 25, "dev/b": 0})
    result = compare_three_states(dict(zip(ROLES, (a, b, c))),
                                  seed=11, bootstrap_samples=20)
    pair = result["paired_task_differences"]
    for metric in ("1", "16", "64"):
        total = (pair["spectral_exploration"]["pass_at_k"][metric]["mean"] +
                 pair["student_transfer"]["pass_at_k"][metric]["mean"])
        assert total == pytest.approx(
            pair["native_to_next_native"]["pass_at_k"][metric]["mean"])
    assert result["observed_rare_correctness"]["spectral_correct_then_post_zero"] == ["dev/b"]
    assert result["states"]["pre_spectral"]["C64_AST"] is not None
    assert result["states"]["pre_native"]["D4_eligible_tasks"] == 1


class _NLLModel(nn.Module):
    """Tiny decoder whose logits keep every reference next-token target selectable."""

    def __init__(self):
        super().__init__()
        self.embedding = nn.Embedding(64, 8)
        self.config = SimpleNamespace(use_cache=True)
        self.is_gradient_checkpointing = False

    def get_input_embeddings(self):
        return self.embedding

    def forward(self, *, input_ids=None, attention_mask=None, use_cache=False):
        assert use_cache is False
        batch, sequence = input_ids.shape
        return SimpleNamespace(logits=torch.zeros(batch, sequence, 64))


class _Tokenizer:
    pad_token_id = 0
    eos_token_id = 1
    chat_template = None

    def encode(self, text, *, add_special_tokens=False):
        assert add_special_tokens is False
        return [ord(character) % 23 + 2 for character in text]


def test_post_reference_nll_uses_selected_targets_without_target_mask_error():
    from improving.transfer_diagnostics import post_reference_nll
    from improving.gain_pipeline import split_gain_references

    references = [{"task_id": f"cal/{i}", "prompt": f"p{i}", "reference": "abc",
                   "source": "fixture", "split": "calibration"} for i in range(4)]
    calibration = {"max_examples": 4, "max_length": 64, "span_mode": "completion",
                   "gain_learning": {"guard_examples": 1}}
    fit, guard = split_gain_references(references, calibration)
    assert len(fit) == 3 and len(guard) == 1
    audit = {
        "native": {"fit_nll": 0.9, "guard_nll": 0.7},
        "selected": {"fit_nll": 0.8, "guard_nll": 0.65},
        "selected_identity": False,
    }
    result = post_reference_nll(_NLLModel().eval(), _Tokenizer(), references, calibration, audit)
    assert isinstance(result["post_native_fit_nll"], float)
    assert isinstance(result["post_native_guard_nll"], float)
    assert result["fit_transfer_gap"] == pytest.approx(
        result["post_native_fit_nll"] - result["pre_spectral_fit_nll"])
    assert result["guard_transfer_gap"] == pytest.approx(
        result["post_native_guard_nll"] - result["pre_spectral_guard_nll"])
