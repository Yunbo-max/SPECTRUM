"""Small v2 runner contract tests; no GPU, downloads, or experiment launches.

These tests are authored for Local execution. Writing this file is not evidence
that the tests have passed or that a host can run the experiment configurations.
"""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def mod():
    spec = importlib.util.spec_from_file_location(
        "rebuttal_cases_contract", ROOT / "scripts/rebuttal_cases.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def arguments(mod, tmp_path):
    return mod.make_parser().parse_args([
        "plan", "--root", str(tmp_path / "cases"),
        "--data-root", str(tmp_path / "mbpp"), "--workers", "2",
    ])


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
                    encoding="utf-8")


def reseal(mod, stage):
    files = {str(path.relative_to(stage)): mod.file_sha(path)
             for path in sorted(stage.rglob("*"))
             if path.is_file() and path.name != "complete.json"}
    write_json(stage / "complete.json", {"status": "completed", "files": files})


@pytest.fixture
def planned(mod, tmp_path, monkeypatch):
    """Use the native config builder, then isolate the executable source seal."""
    a = arguments(mod, tmp_path)
    case = mod.one_case("c02")
    counts = {"train": 2, "calibration": 1, "validation": 1, "eval": 2}
    monkeypatch.setattr(mod, "DATA_COUNTS", counts)
    for split, count in counts.items():
        write_jsonl(Path(a.data_root) / f"{split}.jsonl", [
            {"task_id": f"{split}/{index}", "split": split,
             "prompt": f"def distinct_{split}_{index}():\n    pass\n"}
            for index in range(count)
        ])
    cfg = mod.config_for(case, a, Path(a.root) / case["id"] / "run")
    source_root = tmp_path / "isolated_source"
    source = source_root / "src/improving/fixture.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    assets = source_root / "configs/final/assets.json"
    assets.parent.mkdir(parents=True)
    assets.write_bytes(mod.ASSETS.read_bytes())
    monkeypatch.setattr(mod, "REPO", source_root)
    monkeypatch.setattr(mod, "ASSETS", assets)

    def prepared_config(selected, options, output):
        assert selected == case
        value = deepcopy(cfg)
        value["output_dir"] = str(output)
        return value

    monkeypatch.setattr(mod, "config_for", prepared_config)
    plan = mod.build_plan(case, a)
    return SimpleNamespace(mod=mod, args=a, case=case, plan=plan, source=source)


@pytest.fixture
def evaluation_stage(mod, tmp_path):
    stage = tmp_path / "evaluation"
    task_ids = ["eval/0", "eval/1"]
    rows = [{"task_id": task_id, "sample_id": sample_id,
             "completion": "def candidate():\n    return 1\n"}
            for task_id in task_ids for sample_id in range(64)]
    write_jsonl(stage / "evaluation.jsonl", rows)
    write_jsonl(stage / "evaluation.verified.jsonl", [
        {**row, "code": row["completion"], "correct": True, "status": "passed"}
        for row in rows
    ])
    # This mapping is the shape produced by pipeline.evaluate_file, which passes
    # an explicit count for every task into summarize_records.
    metrics = {
        "protocol": {"expected_samples": {task_id: 64 for task_id in task_ids}},
        "aggregate": {
            "task_count": 2, "sample_count": 128,
            "pass_at_k": {key: {"mean": 1.0} for key in ("1", "16", "64")},
            "implementation_proxy": {"coverage_at_k": {"64": {"mean": 1.0}}},
        },
        "per_task": {task_id: {"sample_count": 64} for task_id in task_ids},
    }
    write_json(stage / "evaluation.metrics.json", metrics)
    write_json(stage / "diagnostic.json", {"value": 1})
    reseal(mod, stage)
    return stage, task_ids, metrics


def test_catalog_has_48_stable_separate_entrypoints(mod):
    spec = mod.load_spec()
    assert spec["protocol"] == "iclr2027-spectrum-case-isolation-v2"
    assert mod.DEFAULT_ROOT == "runs/iclr2027_rebuttal_isolated_v2"
    assert [case["id"] for case in spec["cases"]] == [f"c{i:02d}" for i in range(48)]
    assert all((ROOT / "scripts/rebuttal_cases" / f"{case['id']}.py").is_file()
               for case in spec["cases"])


def test_core_configs_use_native_bwrap_and_separate_outputs(mod, tmp_path):
    a = arguments(mod, tmp_path)
    configs = []
    for identifier in ("c01", "c02", "c03", "c04"):
        case = mod.one_case(identifier)
        cfg = mod.config_for(case, a, Path(a.root) / identifier / "run")
        configs.append(cfg)
        assert cfg["methods"] == [case["method"]]
        assert cfg["rounds"] == 5 and cfg["checkpoint_retention"] == "all"
        assert cfg["generation"]["train_samples"] == 16
        assert cfg["generation"]["eval_samples"] == 64
        assert cfg["generation"]["max_new_tokens"] == 512
        assert cfg["evaluation"]["backend"] == "bwrap"
        assert cfg["evaluation"]["allow_unsafe_local"] is False
        assert cfg["train"]["loss_scope"] == "all"
        assert len(cfg["model"]["revision"]) == 40
    assert len({cfg["output_dir"] for cfg in configs}) == 4
    assert all(cfg["generation"] == configs[0]["generation"] for cfg in configs)


@pytest.mark.parametrize("profile", ["24gb", "80gb"])
def test_4096_templates_keep_conservative_batches(mod, tmp_path, profile):
    a = arguments(mod, tmp_path)
    a.profile = profile
    for identifier in (f"c{i:02d}" for i in range(37, 44)):
        case = mod.one_case(identifier)
        template = mod.template_for(case)
        original = template.read_bytes()
        cfg = mod.config_for(case, a, Path(a.root) / identifier / "run")
        assert template.read_bytes() == original
        assert cfg["rounds"] == 10 and cfg["methods"] == [case["method"]]
        assert cfg["generation"]["max_new_tokens"] == 4096
        assert all(cfg["generation"][key] == 1
                   for key in ("batch_size", "task_batch_size", "sequence_batch_size"))
        assert cfg["evaluation"]["backend"] == "bwrap"
        assert cfg["train"]["loss_scope"] == "all"
        assert cfg["diagnostics"]["transfer_gap"]["rounds"] == [1, 5, 10]
        assert cfg["diagnostics"]["transfer_gap"]["reference_nll_each_round"] is True
        assert cfg["diagnostics"]["operator_probe"]["enabled"] is True
        assert ("gain_learning" in cfg["calibration"]) == (case["method"] == "spectral_learned")


def test_replay_budget_and_training_decoder_are_explicit(mod, tmp_path):
    a = arguments(mod, tmp_path)
    replay = mod.config_for(mod.one_case("c44"), a, tmp_path / "c44/run")
    assert replay["train"]["fixed_anchor_replay"] is True
    assert replay["train"]["target_token_budget"] == 7_200_000
    decoder = mod.config_for(mod.one_case("c47"), a, tmp_path / "c47/run")["generation"]
    assert decoder["training_decoder_overrides"] == mod.DECODERS["nucleus_tight"]
    assert {key: decoder[key] for key in ("temperature", "top_p", "top_k")} == {
        "temperature": .8, "top_p": .95, "top_k": 0,
    }


def test_planning_is_repeatable_and_run_requires_execute(planned, monkeypatch):
    p = planned
    assert p.mod.build_plan(p.case, p.args) == p.plan
    assert p.mod.read_plan(p.case, p.args) == p.plan

    def forbidden_process(*args, **kwargs):
        pytest.fail("Dry-run planning attempted to launch a process")

    monkeypatch.setattr(p.mod.subprocess, "run", forbidden_process)
    result = p.mod.execute_case(p.case, p.args)
    assert result["dry_run"] is True
    assert not Path(p.plan["output"]).exists()
    assert not (Path(p.plan["root"]) / "attempts").exists()


@pytest.mark.parametrize("changed", ["config", "source", "data"])
def test_changed_frozen_inputs_block_resume(planned, changed):
    p = planned
    if changed == "config":
        path = Path(p.plan["config_file"])
        cfg = p.mod.read_json(path)
        cfg["generation"]["temperature"] = .9
        write_json(path, cfg)
        message = "Frozen training config"
    elif changed == "source":
        p.source.write_text("VALUE = 2\n", encoding="utf-8")
        message = "Executable source"
    else:
        path = Path(p.args.data_root) / "train.jsonl"
        rows = list(p.mod.read_records(path))
        rows[0]["prompt"] = "def changed_input():\n    return 7\n"
        write_jsonl(path, rows)
        message = "Prepared training data"
    with pytest.raises(ValueError, match=message):
        p.mod.read_plan(p.case, p.args)


def test_exact_native_sample_mapping_is_accepted(mod, evaluation_stage):
    stage, task_ids, metrics = evaluation_stage
    assert mod.inspect_stage(stage, task_ids, 64, hashes=True) == metrics


@pytest.mark.parametrize("declared", [
    {"eval/0": 64},
    {"eval/0": 64, "eval/1": 63},
    {"eval/0": 64, "eval/1": 64, "extra": 64},
    {"eval/0": 64.0, "eval/1": 64},
])
def test_inexact_sample_mapping_is_rejected(mod, evaluation_stage, declared):
    stage, task_ids, metrics = evaluation_stage
    metrics["protocol"]["expected_samples"] = declared
    write_json(stage / "evaluation.metrics.json", metrics)
    reseal(mod, stage)
    with pytest.raises(ValueError, match="per-task evaluation population"):
        mod.inspect_stage(stage, task_ids, 64, hashes=True)


def test_legacy_scalar_still_requires_exact_per_task_counts(mod, evaluation_stage):
    stage, task_ids, metrics = evaluation_stage
    metrics["protocol"]["expected_samples"] = 64
    write_json(stage / "evaluation.metrics.json", metrics)
    reseal(mod, stage)
    mod.inspect_stage(stage, task_ids, 64, hashes=True)
    metrics["per_task"][task_ids[0]]["sample_count"] = 63
    write_json(stage / "evaluation.metrics.json", metrics)
    reseal(mod, stage)
    with pytest.raises(ValueError, match="per-task evaluation population"):
        mod.inspect_stage(stage, task_ids, 64, hashes=True)


def test_resealed_duplicate_sample_cannot_satisfy_counts(mod, evaluation_stage):
    stage, task_ids, _ = evaluation_stage
    path = stage / "evaluation.verified.jsonl"
    rows = list(mod.read_records(path))
    rows[1] = dict(rows[0])
    write_jsonl(path, rows)
    reseal(mod, stage)
    with pytest.raises(ValueError):
        mod.inspect_stage(stage, task_ids, 64, hashes=True)


def test_hash_verification_includes_nonrequired_sealed_files(mod, evaluation_stage):
    stage, task_ids, _ = evaluation_stage
    write_json(stage / "diagnostic.json", {"value": 2})
    with pytest.raises(ValueError, match="Checksum mismatch"):
        mod.inspect_stage(stage, task_ids, 64, hashes=True)


def test_flock_excludes_live_writer_and_reuses_existing_inode(mod, tmp_path):
    path = tmp_path / "case.lock"
    path.write_text("stale metadata from a dead process\n", encoding="utf-8")
    inode = path.stat().st_ino
    with mod.lock(path) as descriptor:
        assert os.fstat(descriptor).st_ino == inode
        assert f"pid={os.getpid()}" in path.read_text(encoding="utf-8")
        with pytest.raises(RuntimeError, match="active writer"):
            with mod.lock(path):
                pytest.fail("Second writer acquired an already-held lock")
    assert path.is_file() and path.stat().st_ino == inode
    with mod.lock(path) as descriptor:
        assert os.fstat(descriptor).st_ino == inode
