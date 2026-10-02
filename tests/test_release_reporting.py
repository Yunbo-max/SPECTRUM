"""Source tests for release evidence; no training or generated-code execution.

These tests are supplied for the authorized validation run. They are not run as
part of the code-only release preparation task.
"""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import types

import pytest


def reporter():
    path = Path(__file__).parents[1] / "scripts" / "report_release_study.py"
    spec = importlib.util.spec_from_file_location("report_release_study_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_stage(module, *, method="plain", replicate="r1", model="qwen1.5b", block="core", job="job-001"):
    from improving.metrics import summarize_records
    records = [{"task_id": task, "sample_id": sample, "correct": sample < count,
                "code": f"def solve():\n return {sample % 4}",
                "evaluation_provenance": {"backend": "docker", "protocol_version": "task-tests-v2",
                                          "code_extraction": "first_fence"}}
               for task, count in (("a", 16), ("b", 8), ("c", 4)) for sample in range(64)]
    summary = summarize_records(records, ks=(1, 8, 16, 32, 64), correct_budget=4,
                                correct_budgets=(4, 8, 16), bootstrap_samples=0,
                                expected_samples={task: 64 for task in ("a", "b", "c")})
    summary["protocol"]["evaluation_task_harnesses"] = {task: "harness" for task in ("a", "b", "c")}
    return {"job_id": job, "block": block, "model_key": model, "replicate_id": replicate,
            "dataset": "mbpp", "method": method, "round": 5, "stage": "evaluation",
            "samples_per_task": 64, "planned_tasks": 3, "status": "available", "reason": "",
            "summary": summary, "_seed": 987654321,
            "_budget": {"protocol": {"settings": {"samples": 64, "temperature": 0.8}, "seed": 987654321,
                                      "format": "chat"}}, "_prompts": {task: "f" * 64 for task in ("a", "b", "c")}}


def test_paired_D_uses_common_cohort_not_marginal_difference():
    module = reporter()
    reference = synthetic_stage(module)
    candidate = copy.deepcopy(reference)
    candidate["method"] = "spectral_soft"
    # Different correct-count eligibility makes the marginal difference wrong.
    for stage, values in ((reference, {"a": 1.0, "b": 2.0, "c": None}),
                          (candidate, {"a": 3.0, "b": None, "c": 8.0})):
        for task, value in values.items():
            stage["summary"]["per_task"][task]["implementation_proxy"]["correct_matched_coverage_at_budgets"]["8"] = value
    row = next(row for row in module._pair(reference, candidate, "same_round_method", bootstraps=100) if row["metric"] == "D8")
    assert row["mean"] == row["ci95_low"] == row["ci95_high"] == 2.0
    assert row["eligible_task_ids"] == ["a"]
    assert row["eligible_tasks"] == 1 and row["total_tasks"] == 3
    assert row["reference_eligible_tasks"] == row["candidate_eligible_tasks"] == 2


def test_paired_effect_retains_negative_and_never_sets_success():
    module = reporter()
    reference = synthetic_stage(module)
    candidate = copy.deepcopy(reference)
    candidate["method"] = "spectral_soft"
    for row in candidate["summary"]["per_task"].values():
        row["pass_at_k"]["1"] -= 0.05
    rows = module._pair(reference, candidate, "same_round_method", bootstraps=50)
    observed = next(row for row in rows if row["metric"] == "pass@1")
    assert observed["mean"] == pytest.approx(-0.05)
    assert observed["ci95_high"] < 0
    primary = module._primary(rows)
    assert all(row["decision"] == "not_thresholded" for row in primary)
    assert all("success" not in row for row in primary)


def test_retention_covers_C64_and_all_correct_budgets_on_own_base():
    module = reporter()
    base = synthetic_stage(module, method="base")
    base["round"] = 0
    student = copy.deepcopy(base)
    student.update(method="spectral_soft", round=5)
    ratios = module._retention(base, student, 40)
    assert {row["metric"] for row in ratios} == {"C64", "D4", "D8", "D16"}
    assert all(row["mean"] == pytest.approx(1) for row in ratios)
    assert next(row for row in ratios if row["metric"] == "D16")["eligible_tasks"] == 1


def test_pairs_reject_cross_model_and_cross_replicate_inference():
    module = reporter()
    reference = synthetic_stage(module)
    for change in ({"model_key": "qwen7b"}, {"replicate_id": "r2"}):
        candidate = {**reference, **change, "method": "spectral_soft"}
        assert all(row["status"] == "incomparable" for row in module._pair(reference, candidate, "same_round_method", bootstraps=0))


def test_replicate_summary_separates_models_blocks_and_actual_counts():
    module = reporter()
    stages = [synthetic_stage(module, replicate=replicate, job=f"core-{replicate}") for replicate in ("r1", "r2", "r3")]
    stages += [synthetic_stage(module, model=model, block="scale", job=model) for model in ("qwen3b", "qwen7b")]
    stages += [synthetic_stage(module, block="token_matched", job="tokens")]
    rows = [row for stage in stages for row in module._estimates(stage, 0)]
    summaries = module._replicate_rows(rows, [], stages)
    assert {row["model_key"] for row in summaries} == {"qwen1.5b", "qwen3b", "qwen7b"}
    assert all(row["replicate_count"] == 3 for row in summaries if row["block"] == "core")
    single = [row for row in summaries if row["block"] in {"scale", "token_matched"}]
    assert all(row["replicate_count"] == 1 and row["sample_sd"] is None for row in single)
    assert all(row["ci95_low"] is row["ci95_high"] is None for row in summaries)
    # Losing one core trajectory changes the actual count, not its planned count.
    for row in rows:
        if row["block"] == "core" and row["replicate_id"] == "r3":
            row.update(status="pending", mean=None)
    partial = [row for row in module._replicate_rows(rows, [], stages) if row["block"] == "core"]
    assert all(row["replicate_count"] == 2 and row["planned_replicate_count"] == 3 and row["status"] == "partial" for row in partial)


def test_missing_plan_retains_every_round_primary_arm_and_redacts_private_seeds(tmp_path, monkeypatch):
    module = reporter()
    jobs = [{"job_id": f"private-seed-{987654321 + index}", "kind": "training", "block": "core",
             "model_key": "qwen1.5b", "replicate_id": f"r{index + 1}", "seed": 987654321 + index,
             "config": str(tmp_path / f"private-seed-{987654321 + index}.json"), "config_sha256": "a" * 64,
             "output_dir": str(tmp_path / "runs" / f"private-seed-{987654321 + index}"),
             "methods": ["plain", "ssd", "spectral_soft"], "rounds": 5, "samples_per_task": 64, "task_count": 500}
            for index in range(3)]
    manifest = {"jobs": jobs, "run_root": str(tmp_path / "runs"), "protocol": {"seed": 987654321}}
    manifest_path = tmp_path / "private-manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    runner = types.ModuleType("run_release_study")
    runner.load_manifest = lambda *args, **kwargs: manifest
    runner.digest = lambda value: "a" * 64
    runner.job_status = lambda *args, **kwargs: {"status": "pending", "issues": ["private-seed-987654321"]}
    monkeypatch.setitem(sys.modules, "run_release_study", runner)
    output = tmp_path / "public-report"
    result = module.build_report(manifest_path, output, bootstrap_samples=0)
    report = json.loads((output / "summary.json").read_text())
    assert result["status"] == "incomplete"
    assert len(report["endpoints"]) == 3 * 4
    assert len(report["trajectories"]) == 3 * 16 * 9
    assert len(report["retention"]) == 3 * 16 * 4
    assert len(report["primary_comparisons"]) == 3 * 2 * 9
    assert {row["reference"] for row in report["primary_comparisons"]} == {"plain", "ssd"}
    assert all(row["mean"] is None for row in report["trajectories"])
    assert all(row["replicate_count"] == 0 and row["planned_replicate_count"] == 3 for row in report["replicate_summary"])
    for path in output.iterdir():
        text = path.read_text()
        assert "987654321" not in text and "987654322" not in text and "987654323" not in text
        assert "private-seed" not in text and '"seed"' not in text
    assert "x" in (output / "trajectories.csv").read_text()


def test_transfer_declares_64_draws_and_requested_student_round():
    module = reporter()
    job = {"kind": "transfer", "student_round": 5, "rounds": [5]}
    assert module._rounds(job) == [5]
    assert module._metric_names(64) == ["pass@1", "pass@8", "pass@16", "pass@32", "pass@64", "C64", "D4", "D8", "D16"]
    assert module._metric_names(16) == ["pass@1", "pass@8", "pass@16", "C16", "D4", "D8", "D16"]


@pytest.mark.parametrize("kind,method,expected", [
    ("training", "base", {"model_loading", "evaluation"}),
    ("training", "plain", {"model_loading", "training_generation", "generation_policy", "sft", "post_training_evaluation"}),
    ("training", "spectral_soft", {"model_loading", "training_generation", "generation_policy", "sft", "post_training_evaluation", "calibration"}),
    ("transfer", "plain", {"model_loading", "evaluation_generation", "verification_and_metrics"}),
])
def test_absent_planned_resources_remain_pending_and_block_completion(tmp_path, kind, method, expected):
    module = reporter()
    stage = synthetic_stage(module, method=method)
    stage["_directory"] = tmp_path
    resources, _ = module._auxiliary(stage, {"kind": kind})
    resource_rows = {row["resource_stage"]: row for row in resources}
    for name in expected:
        assert resource_rows[f"{name}.resources.json"]["status"] == "pending"
    # This is the same acceptance predicate used by build_report's completion
    # gate; an empty directory cannot look complete through an empty glob.
    assert not all(row["status"] in {"available", "recorded_unsealed"} for row in resources)


def test_decoder_recipes_have_separate_replicate_groups():
    module = reporter()
    stages = []
    for decoder in ("cool", "warm", "ssd_recipe"):
        stage = synthetic_stage(module, block="decoder", job=f"decoder-{decoder}")
        stage["decoder_id"] = decoder
        stages.append(stage)
    rows = [row for stage in stages for row in module._estimates(stage, 0)]
    summaries = module._replicate_rows(rows, [], stages)
    assert {row["decoder_id"] for row in summaries} == {"cool", "warm", "ssd_recipe"}
    assert all(row["replicate_count"] == 1 and row["sample_sd"] is None for row in summaries)


def test_fixed_geometry_and_anchor_controls_have_public_condition_labels():
    module = reporter()
    fixed = {"job_id": "mechanism-fixed-r1", "block": "mechanism"}
    anchor = {"job_id": "mechanism-anchor-replay-r1", "block": "mechanism"}
    assert module._condition(fixed) == "fixed_round1_geometry"
    assert module._condition(anchor) == "fixed_anchor_replay"


def test_tampered_sealed_artifact_is_rejected(tmp_path):
    module = reporter()
    artifact = tmp_path / "evaluation.metrics.json"
    artifact.write_text("{}")
    marker = {"status": "completed", "files": {artifact.name: module._sha(artifact)}}
    (tmp_path / "complete.json").write_text(json.dumps(marker))
    artifact.write_text('{"changed": true}')
    with pytest.raises(ValueError, match="hash mismatch"):
        module._seal(tmp_path, [artifact.name])


def test_record_scan_rejects_duplicate_sample_and_retains_error_counts(tmp_path):
    module = reporter()
    stage = synthetic_stage(module)
    path = tmp_path / "evaluation.verified.jsonl"
    row = {"task_id": "a", "sample_id": 0, "correct": True, "prompt_sha256": "f" * 64}
    path.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n")
    stage["_records_path"] = path
    with pytest.raises(ValueError, match="Duplicate"):
        module._scan(stage)
