"""Identity, information-flow and resume contracts for the learned-gain arm."""
from copy import deepcopy
from pathlib import Path

import pytest
import torch

from improving import gain_pipeline as pipeline
from improving.data import read_jsonl, write_jsonl
from improving.pipeline import _tau_for_round, validate_config
from improving.utils import stable_hash


class Tokenizer:
    """Deterministic tokenizer fixture; no model assets or network access."""

    pad_token_id = 0
    eos_token_id = 1
    chat_template = None

    def encode(self, text, *, add_special_tokens=False):
        assert add_special_tokens is False
        return [ord(character) % 23 + 2 for character in text]


def task(identifier, *, reference="r"):
    split = identifier.split("/")[0]
    return {"task_id": identifier, "prompt": identifier, "reference": reference,
            "source": "software_fixture", "split": split, "tests": "not a learning input"}


def calibration():
    return {"max_examples": 3, "max_length": 64,
            "gain_learning": {"guard_examples": 1, "probe_examples": 1,
                              "probe_max_new_tokens": 2, "max_steps": 1}}


def record(item, tokenizer, ids=None):
    ids = [6, 7] if ids is None else ids
    return {"task_id": item["task_id"], "sample_id": 0,
            "completion": "This text must never be retokenized",
            "completion_ids": ids, "prompt_tokens": len(tokenizer.encode(item["prompt"])),
            "generation_tokens": len(ids), "prompt_sha256": stable_hash(item["prompt"]),
            "finish_reason": "length"}


def test_fit_guard_partition_preserves_fixed_order_and_keeps_labels_disjoint():
    tasks = [task(f"calibration/{i}") for i in range(4)]
    before = deepcopy(tasks)
    fit, guard = pipeline.split_gain_references(tasks, calibration())
    assert [row["task_id"] for row in fit] == ["calibration/0", "calibration/1"]
    assert [row["task_id"] for row in guard] == ["calibration/2"]
    assert tasks == before
    assert {row["task_id"] for row in fit}.isdisjoint(row["task_id"] for row in guard)
    with pytest.raises(ValueError, match="Insufficient"):
        pipeline.split_gain_references(tasks[:2], calibration())
    with pytest.raises(ValueError, match="Duplicate"):
        pipeline.split_gain_references([tasks[0], tasks[0], tasks[2]], calibration())
    bad = deepcopy(tasks)
    bad[2]["reference"] = ""
    with pytest.raises(ValueError, match="reference"):
        pipeline.split_gain_references(bad, calibration())


def test_probe_uses_exact_tokens_and_does_not_add_eos_to_length_capped_output():
    tokenizer = Tokenizer()
    item = task("train/0", reference="unused")
    generated = record(item, tokenizer)
    batch, = pipeline.probe_batches(tokenizer, [item], [generated], 64)
    prefix = tokenizer.encode(item["prompt"])
    assert batch["input_ids"].tolist() == [prefix + [6, 7]]
    assert batch["labels"].tolist() == [[-100] * len(prefix) + [6, 7]]
    assert batch["input_ids"][0, -1].item() != tokenizer.eos_token_id
    with_eos = record(item, tokenizer, [6, tokenizer.eos_token_id])
    with_eos["finish_reason"] = "eos"
    eos_batch, = pipeline.probe_batches(tokenizer, [item], [with_eos], 64)
    assert eos_batch["input_ids"].tolist() == [prefix + [6, tokenizer.eos_token_id]]


@pytest.mark.parametrize("change", [
    {"completion_ids": []}, {"completion_ids": [True]},
    {"completion_ids": [-1]}, {"completion_ids": "6,7"},
    {"prompt_tokens": 999}, {"prompt_sha256": "changed-template"},
    {"generation_tokens": 3}, {"sample_id": 1}, {"task_id": "train/other"},
])
def test_incompatible_probe_receipts_are_rejected(change):
    tokenizer = Tokenizer()
    item = task("train/0")
    generated = {**record(item, tokenizer), **change}
    with pytest.raises(ValueError):
        pipeline.probe_batches(tokenizer, [item], [generated], 64)


def test_probe_never_silently_truncates_or_accepts_duplicate_samples():
    tokenizer = Tokenizer()
    item = task("train/0")
    generated = record(item, tokenizer)
    with pytest.raises(ValueError, match="truncat"):
        pipeline.probe_batches(tokenizer, [item], [generated], len(item["prompt"]) + 1)
    with pytest.raises(ValueError, match="one native sample"):
        pipeline.probe_batches(tokenizer, [item], [generated, generated], 64)


@pytest.mark.parametrize("update", [
    {"reestimate_each_round": False}, {"tau_decay": .8}, {"tau_mode": "adaptive"},
    {"gain_learning": {"guard_examples": 3}},
    {"gain_learning": {"guard_examples": 1, "probe_examples": 0}},
    {"gain_learning": {"guard_examples": 1, "probe_max_new_tokens": True}},
    {"gain_learning": {"guard_examples": 1, "unknown_option": 1}},
])
def test_learned_controller_rejects_incompatible_or_ambiguous_settings(update):
    settings = {**calibration(), **update}
    with pytest.raises((ValueError, TypeError)):
        pipeline.split_gain_settings(settings)


def test_pipeline_config_enforces_learned_constraints_and_preserves_old_tau_rules():
    config = {
        "model": {"name": "fixture"}, "output_dir": "fixture-run",
        "methods": ["spectral_learned"], "calibration": calibration(),
        "data": {name: f"{name}.jsonl" for name in ("train", "calibration", "validation", "eval")},
    }
    validate_config(config)
    bad = deepcopy(config)
    bad["calibration"]["tau_mode"] = "adaptive"
    with pytest.raises(ValueError):
        validate_config(bad)
    assert _tau_for_round({"tau": 1.}, 9) == 1.
    assert _tau_for_round({"tau": 1., "tau_decay": .8}, 3) == pytest.approx(.8 ** 2)
    assert _tau_for_round({"tau": 1., "tau_mode": "adaptive", "tau_gamma": 5.},
                          3, entropy_ratio=1.1) == pytest.approx(1.1 ** 5)


def artifact_case():
    protocol = {"model_identity": "round-one-native", "round": 1,
                "probe_hash": "original-prefixes", "settings": {"kl_budget": .02}}
    operators = {"k_proj": torch.eye(2, dtype=torch.float64)}
    audit = {"selected_identity": True, "fallback_reason": "no_improving_candidate"}
    covariances = {"k_proj": {"covariance": torch.diag(torch.tensor([1., 4.]))}}
    return protocol, operators, audit, covariances


def test_operator_cache_roundtrip_binds_model_probe_settings_and_audit(tmp_path):
    protocol, operators, audit, covariances = artifact_case()
    path = tmp_path / "learned_operators.pt"
    pipeline._save_artifact(path, protocol, operators, audit)
    restored, restored_audit = pipeline._load_artifact(path, protocol, covariances, .1)
    assert restored_audit == audit
    assert torch.equal(restored["k_proj"], operators["k_proj"])
    for change in ({"model_identity": "different-checkpoint"}, {"round": 2},
                   {"probe_hash": "different-prefixes"}, {"settings": {"kl_budget": .2}}):
        with pytest.raises(ValueError, match="protocol"):
            pipeline._load_artifact(path, {**protocol, **change}, covariances, .1)


@pytest.mark.parametrize("corruption", ["operator", "audit", "identity", "bounds", "nan"])
def test_operator_cache_rejects_corruption_and_false_identity(tmp_path, corruption):
    from improving.pipeline import _operator_fingerprints
    protocol, operators, audit, covariances = artifact_case()
    path = tmp_path / "learned_operators.pt"
    pipeline._save_artifact(path, protocol, operators, audit)
    saved = torch.load(path, weights_only=True)
    if corruption == "audit":
        saved["audit"]["fallback_reason"] = "rewritten"
    else:
        if corruption == "operator":
            # Make the replacement semantically admissible so the content hash,
            # rather than the identity/bounds check, must catch this alteration.
            saved["audit"]["selected_identity"] = False
            saved["audit_sha256"] = stable_hash(saved["audit"])
        value = {"operator": .9, "identity": .8, "bounds": 1.2, "nan": float("nan")}[corruption]
        saved["operators"]["k_proj"] *= value
        if corruption in {"identity", "bounds", "nan"}:
            # Even an internally rehashed artifact must obey semantic bounds.
            saved["operator_sha256"] = _operator_fingerprints(saved["operators"])
    torch.save(saved, path)
    with pytest.raises(ValueError):
        pipeline._load_artifact(path, protocol, covariances, .1)


def test_interrupted_operator_save_keeps_prior_artifact_and_cleans_temporary(tmp_path, monkeypatch):
    protocol, operators, audit, covariances = artifact_case()
    path = tmp_path / "learned_operators.pt"
    pipeline._save_artifact(path, protocol, operators, audit)
    original = path.read_bytes()

    def interrupted_save(value, stream):
        stream.write(b"partial data")
        raise OSError("simulated interrupted write")

    monkeypatch.setattr(torch, "save", interrupted_save)
    with pytest.raises(OSError, match="interrupted write"):
        pipeline._save_artifact(path, protocol, operators, audit)
    assert path.read_bytes() == original
    assert sorted(p.name for p in tmp_path.iterdir()) == ["learned_operators.pt"]
    pipeline._load_artifact(path, protocol, covariances, .1)


def test_round_probe_strips_labels_fit_excludes_guard_and_resume_does_not_refit(tmp_path, monkeypatch):
    import improving.calibration as calibration_module
    import improving.learned_gains as core
    import improving.pipeline as main
    tokenizer = Tokenizer()
    anchors = [task(f"calibration/{i}") for i in range(3)]
    train = [task("train/0", reference="MUST_NOT_ENTER_PROBE")]
    calls = {"fit": 0, "calibration_ids": []}

    def fake_calibrate(model, tok, tasks, settings, path, model_identity):
        calls["calibration_ids"].append([row["task_id"] for row in tasks])
        assert settings["max_examples"] == 2
        Path(path).write_bytes(b"fixed-software-fixture-covariance")
        return {"k_proj": {"covariance": torch.diag(torch.tensor([1., 4.], dtype=torch.float64))}}

    def fake_generate(model, tok, tasks, output_path, settings, **kwargs):
        assert all("reference" not in row and "tests" not in row for row in tasks)
        assert settings["samples"] == 1 and settings["max_new_tokens"] == 2
        if Path(output_path).exists() and kwargs["resume"]:
            return read_jsonl(output_path)
        rows = [record(row, tok) for row in tasks]
        write_jsonl(output_path, rows)
        return rows

    def fake_fit(model, fit_batches, guard_batches, probe_batches, covariances, settings):
        calls["fit"] += 1
        assert len(fit_batches) == 2 and len(guard_batches) == len(probe_batches) == 1
        assert probe_batches[0]["labels"][0, -2:].tolist() == [6, 7]
        return {"k_proj": torch.eye(2, dtype=torch.float64)}, {
            "selected_identity": True, "fallback_reason": "software_fixture_no_signal"}

    monkeypatch.setattr(main, "_calibrate", fake_calibrate)
    monkeypatch.setattr(pipeline, "generate_to_file", fake_generate)
    monkeypatch.setattr(core, "fit_learned_operators", fake_fit)
    args = (None, tokenizer, anchors, train, calibration(), {"max_prompt_tokens": 32},
            tmp_path, "native-checkpoint-one")
    first = pipeline.calibrate_learned_round(*args, seed=3, round_index=1, resume=False)
    second = pipeline.calibrate_learned_round(*args, seed=3, round_index=1, resume=True)
    assert calls["fit"] == 1
    assert calls["calibration_ids"] == [["calibration/0", "calibration/1"]] * 2
    assert torch.equal(first[0]["k_proj"], second[0]["k_proj"])
    assert first[2:] == second[2:]
    assert first[3]["fit_task_ids"] == ["calibration/0", "calibration/1"]
    assert first[3]["guard_task_ids"] == ["calibration/2"]
    assert first[3]["probe_task_ids"] == ["train/0"]
    assert first[3]["sft_loss"] == "unchanged_uniform_model_loss"
    changed = deepcopy(calibration())
    changed["gain_learning"]["kl_budget"] = .3
    changed_args = (*args[:4], changed, *args[5:])
    with pytest.raises(ValueError, match="protocol"):
        pipeline.calibrate_learned_round(*changed_args, seed=3, round_index=1, resume=True)
    assert calls["fit"] == 1

    # Once training is committed, receipt validation must require no model,
    # generation, or gain refit; it must verify the original inputs in place.
    monkeypatch.setattr(calibration_module, "load_calibration", lambda path: {
        "metadata": {"model_identity": "native-checkpoint-one"}, "modules": first[1]})

    def forbidden_recalibration(*args, **kwargs):
        pytest.fail("Committed policy verification must not regenerate or refit")

    monkeypatch.setattr(pipeline, "generate_to_file", forbidden_recalibration)
    monkeypatch.setattr(core, "fit_learned_operators", forbidden_recalibration)
    monkeypatch.setattr(main, "_calibrate", forbidden_recalibration)
    saved_args = (tmp_path, "native-checkpoint-one", calibration(), anchors, train)
    pipeline.validate_saved_learned_round(*saved_args, seed=3, round_index=1)
    probe_path = tmp_path / "gain_probe.jsonl"
    original_probe = probe_path.read_bytes()
    probe_path.unlink()
    with pytest.raises(ValueError, match="missing gain_probe"):
        pipeline.validate_saved_learned_round(*saved_args, seed=3, round_index=1)
    probe_path.write_bytes(original_probe)
    for name in ("gain_probe.jsonl", "gain_inputs.json"):
        path = tmp_path / name
        original = path.read_bytes()
        path.write_text('{"tampered": true}\n')
        with pytest.raises(ValueError, match="integrity"):
            pipeline.validate_saved_learned_round(*saved_args, seed=3, round_index=1)
        path.write_bytes(original)
    pipeline.validate_saved_learned_round(*saved_args, seed=3, round_index=1)


def test_unfolded_identity_diagnostics_do_not_report_float32_rounding_as_intervention():
    from improving.pipeline import _operator_diagnostics
    model = torch.nn.Module()
    model.k_proj = torch.nn.Linear(2, 2, bias=False).double()
    with torch.no_grad():
        model.k_proj.weight.fill_(1. + 1e-10)
    operators = {"k_proj": torch.eye(2, dtype=torch.float64)}
    covariances = {"k_proj": {"covariance": torch.eye(2, dtype=torch.float64)}}
    before = model.k_proj.weight.detach().clone()
    skipped = _operator_diagnostics(model, operators, covariances, "spectral_learned", {},
                                    folding_applied=False)["k_proj"]
    applied = _operator_diagnostics(model, operators, covariances, "spectral_learned", {},
                                    folding_applied=True)["k_proj"]
    assert skipped["folding_applied"] is False
    assert skipped["folded_weight_delta_frobenius"] == 0.
    assert skipped["folded_weight_relative_delta"] == 0.
    assert applied["folded_weight_delta_frobenius"] > 0.
    assert torch.equal(model.k_proj.weight, before)


@pytest.mark.parametrize("committed_file", [
    "train.jsonl", "training_stats.json", "generation_policy.jsonl",
    "learned_gains.json", "gain_provenance.json",
])
def test_lost_operator_cache_cannot_be_replaced_after_policy_commit(tmp_path, committed_file):
    (tmp_path / committed_file).write_text("[]\n")
    with pytest.raises(ValueError, match="Committed policy or generated data exists"):
        pipeline.calibrate_learned_round(
            None, Tokenizer(), [task(f"calibration/{i}") for i in range(3)],
            [task("train/0")], calibration(), {"max_prompt_tokens": 32}, tmp_path,
            "native-checkpoint", seed=3, round_index=1, resume=True)

