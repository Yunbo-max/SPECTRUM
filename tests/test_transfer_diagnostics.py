"""No-GPU tests of transfer-gap config, task isolation and three-state metrics."""
import copy
import pytest

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
        ("max_new_tokens", 256, "declared main study token cap"),
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


def test_post_sft_reference_nll_uses_causally_shifted_target_masks(monkeypatch):
    """Regression for the recovered target_mask failure; does not load a model."""
    import torch
    from improving import gain_pipeline, learned_gains
    from improving.transfer_diagnostics import post_reference_nll

    batch = {"input_ids": torch.tensor([[1, 2, 3]]),
             "attention_mask": torch.tensor([[1, 1, 1]]),
             "labels": torch.tensor([[-100, -100, 3]])}
    monkeypatch.setattr(gain_pipeline, "split_gain_references", lambda refs, settings: (["fit"], ["guard"]))
    monkeypatch.setattr(gain_pipeline, "reference_batches", lambda *args: [batch])
    observed = []

    def nll(model, examples):
        assert examples[0]["target_mask"].tolist() == [[False, True]]
        assert examples[0]["target_count"] == 1
        observed.append(True)
        return .75

    monkeypatch.setattr(learned_gains, "_mean_nll", nll)

    class State:
        training = True

        def eval(self):
            self.training = False

        def train(self, value):
            self.training = value

    model = State()
    result = post_reference_nll(model, None, [], {}, {
        "native": {"fit_nll": 1., "guard_nll": 1.},
        "selected": {"fit_nll": .8, "guard_nll": .9}, "selected_identity": False})
    assert observed == [True, True]
    assert result["fit_transfer_gap"] == pytest.approx(-.05)
    assert model.training is True
