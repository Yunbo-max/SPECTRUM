"""Authored Local-only orchestration contracts; not executed by Web.

Artificial artifact bytes exercise stage ownership and interruption recovery.
They are deliberately not loadable model checkpoints or benchmark evidence.
"""
from __future__ import annotations

import builtins
from contextlib import nullcontext
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def study():
    spec = importlib.util.spec_from_file_location(
        "improving.continual_gain_study_contract", ROOT / "src/improving/continual_gain_study.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_config(name="frozen_math_qa"):
    return json.loads((ROOT / "configs/continual_gains" / (name + ".json")).read_text())


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def fake_module(monkeypatch, name, **attributes):
    module = ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)
    return module


def test_first_domain_and_stage_order_are_explicit_and_not_reordered(study):
    forward = study.stage_schedule(load_config("frozen_math_qa"))
    reverse = study.stage_schedule(load_config("self_distill_qa_math"))
    assert [(item["domain"], item["round"]) for item in forward] == [(None, 0), ("math", 1), ("qa", 1)]
    assert [(item["domain"], item["round"]) for item in reverse] == [(None, 0), ("qa", 1), ("math", 1)]
    assert forward[1]["name"] != reverse[1]["name"]
    assert [item["index"] for item in forward] == [0, 1, 2]


@pytest.mark.parametrize("mutation", ["future_repeat", "other_seed", "different_backbone", "shortened_sft", "replay"])
def test_incompatible_shared_lineage_is_rejected_before_model_loading(study, mutation):
    config = load_config()
    if mutation == "future_repeat":
        config["order"] = ["math", "math"]
    elif mutation == "other_seed":
        config["domains"]["qa"]["seed_file"] = "another-private-seed.json"
    elif mutation == "different_backbone":
        config["domains"]["qa"]["model"]["name"] = "another-model"
    elif mutation == "shortened_sft":
        config["domains"]["qa"]["train"]["max_length"] = 2048
    else:
        config["domains"]["math"]["train"]["fixed_anchor_replay"] = True
    with pytest.raises(ValueError):
        study.validate_continual_config(config)


def test_math_text_recipe_accepts_one_answer_only_for_explicit_pilot(study):
    from improving.text_study import validate_text_config
    config = load_config()["domains"]["math"]
    config["evaluation"].update(
        samples=1, profile="matched_pilot_v1", task_ids=["math/pilot/1"])
    assert validate_text_config(config) == config


def test_pilot_evaluation_accepts_explicit_matched_subset(study):
    config = load_config()
    for domain in ("math", "qa"):
        evaluation = config["domains"][domain]["evaluation"]
        evaluation["samples"] = 1
        evaluation["profile"] = "matched_pilot_v1"
        evaluation["task_ids"] = [f"{domain}/pilot/{index:03d}" for index in range(100)]
    assert study.validate_continual_config(config) == config


@pytest.mark.parametrize("task_ids", [[], ["math/pilot/001", "math/pilot/001"], [""]])
def test_pilot_evaluation_rejects_empty_duplicate_or_invalid_ids(study, task_ids):
    config = load_config()
    evaluation = config["domains"]["math"]["evaluation"]
    evaluation["samples"] = 1
    evaluation["task_ids"] = task_ids
    with pytest.raises(ValueError):
        study.validate_continual_config(config)


def test_evaluation_subset_preserves_declared_id_order_and_rejects_unknown_ids(study):
    rows = [{"task_id": "a"}, {"task_id": "b"}, {"task_id": "c"}]
    assert [row["task_id"] for row in study._select_evaluation_rows(
        {"task_ids": ["c", "a"]}, rows)] == ["c", "a"]
    with pytest.raises(ValueError, match="unknown"):
        study._select_evaluation_rows({"task_ids": ["missing"]}, rows)


def test_pilot_policies_share_generation_random_stream(study):
    config = load_config()
    config["domains"]["math"]["evaluation"].update(
        samples=1, task_ids=["math/pilot/1"], rng_group="paired-pilot-v1")
    assert study._evaluation_rng_group(config, "retention", "native") == "paired-pilot-v1"
    assert study._evaluation_rng_group(config, "conflict", "controlled") == "paired-pilot-v1"


def test_metadata_validation_never_imports_model_dependencies(study, monkeypatch):
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.split(".")[0] in {"torch", "transformers", "datasets", "peft"}:
            pytest.fail(f"Read-only validation imported a model dependency: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    config = load_config()
    assert study.validate_continual_config(config) == config
    assert len(study.stage_schedule(config)) == 3


@pytest.fixture
def committed_checkpoint(study, tmp_path):
    stage = tmp_path / "stage_001_math_r1"
    model = stage / "model"
    write_json(model / "config.json", {"model_type": "software-fixture"})
    write_json(model / "tokenizer.json", {"software_fixture": True})
    (model / "model.safetensors").write_bytes(b"artificial, never loaded\n")
    stats = {"training_complete": True, "epochs": 1}
    # Native training writes indented insertion-order JSON; the stage writer
    # sorts keys. Equivalent objects legitimately have different file hashes.
    (model / "training_stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    write_json(stage / "training_stats.json", stats)
    write_json(stage / "effective_train.json", {"loss_scope": "completion", "require_full_completion_targets": True})
    stage.joinpath("synthetic.jsonl").write_text(
        json.dumps({"task_id": "fixture/train", "sample_id": 0, "completion": "raw answer"}) + "\n",
        encoding="utf-8")
    binding = {"incoming_checkpoint": {"identity": "parent-checkpoint"},
               "stage": {"index": 1, "domain": "math", "round": 1}}
    selection = "a" * 64
    write_json(stage / "synthetic.receipt.json", {
        "schema": 1,
        "binding": {"stage_binding_sha256": study._digest(binding), "selection_sha256": selection},
        "files": {"synthetic.jsonl": study._sha(stage / "synthetic.jsonl")},
    })
    receipt = {"schema": 1, "stage_binding_sha256": study._digest(binding),
               "selection_sha256": selection, "parent_checkpoint_identity": "parent-checkpoint",
               "checkpoint_identity": study._digest(study._model_files(model)),
               "files": {path.name: study._sha(path) for path in model.iterdir() if path.is_file()},
               "synthetic_sha256": study._sha(stage / "synthetic.jsonl"),
               "synthetic_receipt_sha256": study._sha(stage / "synthetic.receipt.json"),
               "effective_train_sha256": study._sha(stage / "effective_train.json"),
               "training_stats_sha256": study._sha(model / "training_stats.json"),
               "stage_training_stats_sha256": study._sha(stage / "training_stats.json")}
    write_json(stage / "checkpoint.json", receipt)
    return stage, binding, selection, receipt


def test_committed_student_survives_incomplete_stage_evaluation(study, committed_checkpoint):
    stage, binding, selection, receipt = committed_checkpoint
    assert not (stage / "complete.json").exists(), "evaluation has not been committed"
    assert study._sha(stage / "training_stats.json") != study._sha(stage / "model/training_stats.json")
    assert study._check_checkpoint(stage, binding, selection) == receipt
    # An incomplete evaluation is separate evidence; it must not invalidate or
    # erase a previously committed training boundary.
    write_json(stage / "evaluation/math/native/partial.json", {"rows": 1})
    assert study._check_checkpoint(stage, binding, selection) == receipt


@pytest.mark.parametrize("mutation", ["weights", "synthetic", "stats", "stage_stats", "synthetic_receipt",
                                      "effective_train", "extra_weight", "parent", "selection"])
def test_resume_rejects_changed_committed_training_identity(study, committed_checkpoint, mutation):
    stage, binding, selection, _ = committed_checkpoint
    if mutation == "weights":
        (stage / "model/model.safetensors").write_bytes(b"changed checkpoint\n")
    elif mutation == "synthetic":
        (stage / "synthetic.jsonl").write_text("different training records\n", encoding="utf-8")
    elif mutation == "stats":
        write_json(stage / "model/training_stats.json", {"epochs": 2})
    elif mutation == "stage_stats":
        write_json(stage / "training_stats.json", {"epochs": 2})
    elif mutation == "synthetic_receipt":
        write_json(stage / "synthetic.receipt.json", {"schema": 1, "different_source": True})
    elif mutation == "effective_train":
        write_json(stage / "effective_train.json", {"loss_scope": "all"})
    elif mutation == "extra_weight":
        (stage / "model/uncommitted.safetensors").write_bytes(b"unexpected shard\n")
    elif mutation == "parent":
        binding = deepcopy(binding)
        binding["incoming_checkpoint"]["identity"] = "another-parent"
    else:
        selection = "b" * 64
    with pytest.raises(ValueError):
        study._check_checkpoint(stage, binding, selection)


@pytest.mark.parametrize("partial_name", ["model", ".model.saving-interrupted"])
def test_uncommitted_student_is_never_treated_as_a_safe_restart(study, tmp_path, partial_name):
    stage = tmp_path / "stage"
    (stage / partial_name).mkdir(parents=True)
    with pytest.raises(ValueError, match="Uncommitted checkpoint"):
        study._check_checkpoint(stage, {"incoming_checkpoint": {"identity": "parent"}}, "a" * 64)


@pytest.mark.parametrize("mutation", ["changed", "missing", "added", "wrong_binding"])
def test_complete_stage_requires_exact_artifact_inventory(study, tmp_path, mutation):
    directory = tmp_path / "stage"
    write_json(directory / "result.json", {"known_result": 1})
    binding = {"method": "conflict", "domain": "math", "input_sha256": "a" * 64}
    study._seal(directory, binding)
    assert study._read_seal(directory, binding)["status"] == "completed"
    if mutation == "changed":
        write_json(directory / "result.json", {"known_result": 2})
    elif mutation == "missing":
        (directory / "result.json").unlink()
    elif mutation == "added":
        write_json(directory / "posthoc_selection.json", {"picked_another": True})
    else:
        binding = {**binding, "method": "sequential"}
    with pytest.raises(ValueError):
        study._read_seal(directory, binding)


def test_prepared_input_change_is_rejected_on_resume(study, tmp_path, monkeypatch):
    path = tmp_path / "old_fit.jsonl"
    path.write_text("frozen fit memory\n", encoding="utf-8")
    source = {"source.py": "b" * 64}
    monkeypatch.setattr(study, "source_identity", lambda: source)
    binding = {"source_files": source, "external_files": {str(path): study._sha(path)}}
    study._assert_external(binding, model=False)
    path.write_text("replacement fit memory\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Prepared input"):
        study._assert_external(binding, model=False)


def test_complete_population_check_keeps_missing_and_duplicate_answers_invalid(study, tmp_path):
    path = tmp_path / "responses.jsonl"
    records = [{"task_id": task, "sample_id": index, "completion": "fixture", "correct": False}
               for task in ("first", "second") for index in range(2)]
    path.write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
    study._exact_records(path, ["first", "second"], 2, scored=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in records[:-1]), encoding="utf-8")
    with pytest.raises(ValueError, match="Missing full"):
        study._exact_records(path, ["first", "second"], 2, scored=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in records + [records[0]]), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        study._exact_records(path, ["first", "second"], 2, scored=True)


def test_geometry_uses_only_first_domain_fit_and_is_never_reestimated(study, tmp_path, monkeypatch):
    import torch

    config = load_config("frozen_math_qa")
    fit = [{"task_id": f"math/fit/{index}", "reference": "first-domain fit"} for index in range(54)]
    guard = [{"task_id": f"math/guard/{index}", "reference": "guard must not build U"} for index in range(10)]
    modules = {"k_proj": {"basis": torch.eye(2, dtype=torch.float64),
                           "eigenvalues": torch.tensor([1., 2.], dtype=torch.float64),
                           "group_ids": torch.tensor([0, 1])}}
    collected = []

    def calibrate(model, tokenizer, tasks, settings, path, identity):
        collected.append((deepcopy(tasks), deepcopy(settings), identity))
        assert tasks == fit and len(tasks) == 54
        assert not {row["task_id"] for row in guard}.intersection(row["task_id"] for row in tasks)
        Path(path).write_bytes(b"artificial calibration artifact\n")
        return {"k_proj": {"covariance": torch.diag(torch.tensor([1., 2.], dtype=torch.float64))}}

    fake_module(monkeypatch, "improving.pipeline", _calibrate=calibrate,
                record_stage=lambda *args, **kwargs: nullcontext())
    fake_module(monkeypatch, "improving.continual_gains",
                build_gain_geometry=lambda *args, **kwargs: modules,
                identity_gain_state=lambda value: {"k_proj": torch.ones(2, dtype=torch.float64)},
                operators_from_gain_state=lambda value, state: {"k_proj": torch.diag(state["k_proj"])})
    monkeypatch.setattr(study, "_load_model", lambda *args: (object(), object()))
    monkeypatch.setattr(study, "_release", lambda: None)
    context = {
        "base_model": {"path": str(tmp_path / "never-loaded-base"), "identity": "base-fixture"},
        "binding": {"source_files": {"fixture.py": "a" * 64}},
        "domains": {
            "math": {"config": config["domains"]["math"], "fit": fit, "guard": guard,
                     "core": {"min_gain": .1}},
            "qa": {"fit": [{"task_id": "qa/future", "reference": "future labels must not build U"}]},
        },
    }
    first = study._geometry(config, context, tmp_path / "lineage")
    assert first["metadata"]["binding"]["source_domain"] == "math"
    assert first["metadata"]["binding"]["fit_task_ids"] == [row["task_id"] for row in fit]
    assert collected[0][1]["max_examples"] == 54
    # Resume reads the frozen geometry even though future-domain labels are
    # now different; none of those labels supplied the original geometry.
    context["domains"]["qa"]["fit"][0]["reference"] = "changed future-domain fixture"
    second = study._geometry(config, context, tmp_path / "lineage")
    assert second["receipt_sha256"] == first["receipt_sha256"]
    assert len(collected) == 1


@pytest.mark.parametrize("backbone", ["frozen", "self_distill"])
def test_controller_inherits_shared_gains_and_uses_protocol_specific_old_limits(
        study, tmp_path, monkeypatch, backbone):
    import torch

    config = load_config(backbone + "_math_qa")
    calls, encoded_tasks = [], []
    incoming = {"k_proj": torch.tensor([.8, .9], dtype=torch.float64)}
    selected = {"k_proj": torch.tensor([.7, .9], dtype=torch.float64)}
    operator = lambda value, state: {"k_proj": torch.diag(state["k_proj"])}

    def fit(model, fit_batches, guard_batches, probe_batches, geometry, **kwargs):
        calls.append(kwargs)
        assert torch.equal(kwargs["initial_gains"]["k_proj"], incoming["k_proj"])
        assert set(kwargs["retention_batches"]) == {"math"}
        return operator(geometry, selected), selected, {"selected": {"retention_nlls": {"math": 1.2}}}

    def references(tokenizer, tasks, settings):
        encoded_tasks.append([task["task_id"] for task in tasks])
        return [{"input_ids": torch.tensor([[1, 2]]), "attention_mask": torch.tensor([[1, 1]]),
                 "labels": torch.tensor([[-100, 2]])}]

    def generate(model, tokenizer, tasks, path, generation, **kwargs):
        rows = [{"task_id": task["task_id"], "sample_id": 0, "completion": "native probe"}
                for task in tasks]
        Path(path).write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        return rows

    fake_module(monkeypatch, "improving.continual_gains",
                fit_continual_operators=fit, operators_from_gain_state=operator)
    fake_module(monkeypatch, "improving.gain_pipeline", reference_batches=references,
                probe_batches=lambda *args: [{"input_ids": torch.tensor([[1, 2]])}])
    fake_module(monkeypatch, "improving.generation", generate_to_file=generate)
    fake_module(monkeypatch, "improving.pipeline", record_stage=lambda *args, **kwargs: nullcontext())
    domains = {}
    for domain in ("math", "qa"):
        domains[domain] = {
            "config": config["domains"][domain], "core": {"min_gain": .1},
            "integration": {"probe_examples": 8, "probe_max_new_tokens": 128},
            "fit": [{"task_id": f"{domain}/fit/{index}", "reference": "FIT"} for index in range(54)],
            "guard": [{"task_id": f"{domain}/guard/{index}", "reference": "GUARD"} for index in range(10)],
            "splits": {"train": [{"task_id": f"{domain}/train/{index}", "prompt": "training prompt",
                                    "source": "software-fixture", "split": "train"} for index in range(8)]},
        }
    context = {"domains": domains, "seed": 19,
               "binding": {"effective_controller": {"min_gain": .1},
                           "data": {domain: {
                               "fit_task_ids": [row["task_id"] for row in item["fit"]],
                               "guard_task_ids": [row["task_id"] for row in item["guard"]],
                           } for domain, item in domains.items()}}}
    geometry = {"modules": {}, "metadata": {"modules": {"k_proj": {"gain_parameters": 2}}},
                "receipt_sha256": "c" * 64}
    memory_exits = {"math": {"retention_limit": 1.25}}
    binding = {"stage": {"domain": "qa", "index": 2, "round": 1},
               "incoming_checkpoint": {"identity": "current-student"},
               "retention_anchor": "fixed_domain_exit" if backbone == "frozen" else "current_backbone_entry"}
    state, _, _, _ = study._select_controller(
        config, context, tmp_path / "stage", binding, geometry, incoming,
        memory_exits, "conflict", object(), object(), False)
    assert torch.equal(state["k_proj"], selected["k_proj"])
    assert calls[0]["retention_limits"] == ({"math": 1.25} if backbone == "frozen" else None)
    assert encoded_tasks == [
        [row["task_id"] for row in domains["qa"]["fit"]],
        [row["task_id"] for row in domains["qa"]["guard"]],
        [row["task_id"] for row in domains["math"]["fit"]],
    ]
    # None intentionally delegates the self-distill limit to the core's actual
    # incoming-policy loss on the CURRENT student, not an old fixed threshold.


def test_resume_orchestrator_uses_committed_student_without_refit_generation_or_sft(
        study, committed_checkpoint, tmp_path, monkeypatch):
    stage, original_binding, selection_sha, receipt = committed_checkpoint
    config = load_config("self_distill_math_qa")
    parent = tmp_path / "parent"
    write_json(parent / "config.json", {"model_type": "parent-software-fixture"})
    (parent / "model.safetensors").write_bytes(b"immutable artificial parent\n")
    parent_identity = study._digest(study._model_files(parent))
    binding = deepcopy(original_binding)
    binding["incoming_checkpoint"] = {"path": str(parent), "identity": parent_identity}
    binding["retention_anchor"] = "current_backbone_incoming_controller_at_calibration_entry"
    synthetic_receipt = study._json(stage / "synthetic.receipt.json")
    synthetic_receipt["binding"]["stage_binding_sha256"] = study._digest(binding)
    write_json(stage / "synthetic.receipt.json", synthetic_receipt)
    receipt = {**receipt, "stage_binding_sha256": study._digest(binding),
               "parent_checkpoint_identity": parent_identity,
               "synthetic_receipt_sha256": study._sha(stage / "synthetic.receipt.json")}
    write_json(stage / "checkpoint.json", receipt)
    assert not (stage / "complete.json").exists()
    incoming, selected = {"k_proj": [.8, .9]}, {"k_proj": [.7, .9]}
    geometry = {"receipt_sha256": "c" * 64}
    context = {"binding": {"effective_controller": {"min_gain": .1}}}
    controller = (selected, {"fixture_operator": True}, {"selected": {"fit_nll": 1.3}}, selection_sha)
    loads, evaluated, checked = [], [], []

    def forbidden(*args, **kwargs):
        pytest.fail("Committed student was refitted, regenerated, or trained a second time")

    fake_module(monkeypatch, "improving.pipeline", record_stage=lambda *args, **kwargs: nullcontext())
    fake_module(monkeypatch, "improving.continual_gains",
                operators_from_gain_state=lambda *args: {"fixture_operator": True},
                fit_continual_operators=forbidden)
    fake_module(monkeypatch, "improving.generation", generate_to_file=forbidden)
    fake_module(monkeypatch, "improving.training", train_on_records=forbidden)
    monkeypatch.setattr(study, "_controller_binding", lambda *args: {"fixture": "sealed controller"})
    monkeypatch.setattr(study, "_read_selection", lambda *args: controller)
    monkeypatch.setattr(study, "_select_controller", forbidden)
    monkeypatch.setattr(study, "_generate_and_train", forbidden)
    monkeypatch.setattr(study, "_assert_external", lambda *args, **kwargs: None)
    monkeypatch.setattr(study, "_release", lambda: None)
    real_check = study._check_checkpoint

    def checkpoint_check(*args):
        checked.append(args)
        return real_check(*args)

    monkeypatch.setattr(study, "_check_checkpoint", checkpoint_check)
    student, tokenizer = object(), object()

    def load(config, path):
        loads.append(Path(path))
        return student, tokenizer

    monkeypatch.setattr(study, "_load_model", load)
    monkeypatch.setattr(study, "_reference_losses", lambda *args: {
        "math": {"controlled": {"fit_nll": 1.4}, "fit_task_ids": ["math/fit/fixture"]},
    })

    def evaluate(config, context, directory, stage_binding, geometry, state,
                 operators, model, tok, checkpoint_identity, method, resume):
        assert model is student and tok is tokenizer
        assert state == selected and resume is True
        evaluated.append(checkpoint_identity)
        write_json(Path(directory) / "artificial_evaluation.json", {"resumed_student": checkpoint_identity})

    monkeypatch.setattr(study, "_evaluate_all_domains", evaluate)

    def inspect(config, context, directory, stage_binding, geometry, incoming_state, memory, method):
        seal = study._read_seal(directory, stage_binding)
        if seal is None:
            return None
        return {"state": selected, "checkpoint": seal["output_checkpoint"],
                "memory_exits": seal["memory_exits"], "receipt": seal}

    monkeypatch.setattr(study, "_inspect_stage", inspect)
    result = study._run_stage(config, context, stage, binding, geometry,
                              incoming, {}, "conflict", True)
    assert len(checked) == 1 and checked[0][2] == selection_sha
    assert loads == [stage / "model"]
    assert evaluated == [receipt["checkpoint_identity"]]
    assert result["checkpoint"] == {"path": str(stage / "model"), "identity": receipt["checkpoint_identity"]}
    assert (stage / "complete.json").is_file()


def test_domain_exit_memory_is_not_reset_at_later_stages(study):
    config = load_config("frozen_math_qa")
    first = {"index": 1, "domain": "math", "round": 1}
    losses = {"math": {"controlled": {"fit_nll": 1.2}, "fit_task_ids": ["math/fit/0"]}}
    memory = study._next_memory(config, first, {}, losses,
                                {"selected": {"fit_nll": 1.2}}, {"k_proj": [.8, .9]})
    assert memory["math"]["retention_limit"] == 1.2
    second_losses = {"qa": {"controlled": {"fit_nll": 1.8}, "fit_task_ids": ["qa/fit/0"]}}
    after_qa = study._next_memory(config, {"index": 2, "domain": "qa", "round": 1},
                                  memory, second_losses, {"selected": {"fit_nll": 1.8}}, {"k_proj": [.7, .9]})
    assert after_qa["math"] == memory["math"]
    with pytest.raises(ValueError, match="overwrite"):
        study._next_memory(config, first, memory, losses, {}, {"k_proj": [.6, .9]})
    config["backbone_update"] = "self_distill"
    fresh = study._next_memory(config, first, {}, losses, {}, {"k_proj": [.8, .9]})
    assert fresh["math"]["retention_limit"] is None


def test_summary_is_stdlib_only_and_never_promotes_partial_artifacts(study, tmp_path, monkeypatch):
    config = load_config()
    root = tmp_path / "study"
    config["output_dir"] = str(root)
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.split(".")[0] in {"torch", "transformers", "datasets", "peft"}:
            pytest.fail(f"Saved-artifact reporting imported a model dependency: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    empty = study.summarize_continual_gain_study(config)
    assert empty["status"] == "unstarted" and empty["methods"] == {}
    assert not root.exists()
    method_root = root / "conflict"
    write_json(method_root / "partial.json", {"partial": True})
    partial = study.summarize_continual_gain_study(config)
    assert partial["status"] == "incomplete"
    assert partial["reason"] == "artifacts_without_study_manifest"
    # Isolate report-state handling from native input admission, which is
    # exercised independently above and by the CLI binding contracts.
    monkeypatch.setattr(study, "_assert_external", lambda *args, **kwargs: None)
    binding = {"schema": 1, "protocol": study.PROTOCOL, "config": config,
               "config_sha256": study._digest(config), "runtime": {"software_fixture": True}}
    write_json(root / "study_manifest.json", binding)
    write_json(method_root / "manifest.json", {"schema": 1, "method": "conflict",
                                               "study_sha256": study._digest(binding),
                                               "output_dir": str(method_root)})
    partial = study.summarize_continual_gain_study(config)
    assert partial["status"] == "incomplete"
    assert partial["methods"]["conflict"]["reason"] == "geometry_not_committed"
    write_json(method_root / "run_complete.json", {"status": "completed"})
    with pytest.raises(ValueError, match="completion exists without"):
        study.summarize_continual_gain_study(config)
