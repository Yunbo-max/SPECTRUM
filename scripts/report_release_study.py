#!/usr/bin/env python3
"""Export the fixed release study from sealed artifacts, without running models.

All planned stages survive missing data. Native estimates and paired task CIs
are separate from training-replicate variability. Numeric random seeds remain
private: exported identities use model, experimental block, and replicate ID.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import statistics
import sys


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# These helpers read/hash files or atomically write derived exports. No source
# experiment file, checkpoint, or old reporting implementation is modified.
from report_final_study import _csv, _read, _rows, _seal, _sha, _write

BOOTSTRAPS = 2000
MAIN_METHODS = ("plain", "ssd", "spectral_soft")
RICHNESS_METRICS = ("C64", "D4", "D8", "D16")
META = ("job_id", "block", "condition", "model_key", "replicate_id", "dataset", "decoder_id", "method", "round", "stage")


def _path(value):
    path = Path(value)
    return path.resolve() if path.is_absolute() else (REPO / path).resolve()


def _rounds(job):
    if job["kind"] == "transfer":
        return [job["student_round"]]
    rounds = job["rounds"]
    if type(rounds) is int and rounds > 0:
        return list(range(1, rounds + 1))
    if (not isinstance(rounds, list) or not rounds or
            any(type(index) is not int or index < 1 for index in rounds) or
            len(set(rounds)) != len(rounds)):
        raise ValueError("Rounds must be a positive integer or unique positive integer list")
    return sorted(rounds)


def _metric_names(samples=64):
    return ([f"pass@{k}" for k in (1, 8, 16, 32, 64) if k <= samples] +
            [f"C{samples}"] + [f"D{k}" for k in (4, 8, 16) if k <= samples])


def _validate_jobs(manifest):
    jobs = manifest.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("Release manifest must contain planned jobs")
    identifiers = [job.get("job_id") for job in jobs]
    if any(not isinstance(item, str) or not item for item in identifiers) or len(set(identifiers)) != len(identifiers):
        raise ValueError("Planned job IDs must be unique nonempty strings")
    for job in jobs:
        if job.get("kind") not in {"training", "transfer"}:
            raise ValueError("Unknown planned job kind")
        if job.get("block") not in {"core", "scale", "mechanism", "token_matched", "diagnostic", "transfer", "decoder"}:
            raise ValueError("Unknown experimental block")
        if not job.get("model_key") or job.get("replicate_id") not in {"r1", "r2", "r3"}:
            raise ValueError("Every job requires a model key and public replicate label")
        if type(job.get("seed")) is not int or not job.get("output_dir"):
            raise ValueError("Every job requires a private random seed and output directory")
        methods = job.get("methods")
        if not isinstance(methods, list) or not methods or len(set(methods)) != len(methods):
            raise ValueError("Methods must be a unique nonempty list")
        if job.get("samples_per_task", 64) != 64:
            raise ValueError("Release native evaluation requires 64 samples per task")
        if job.get("comparison_job") and job["comparison_job"] not in identifiers:
            raise ValueError("Comparison job is absent from the fixed manifest")
        _rounds(job)
    return jobs


def _meta(stage):
    return {key: stage.get(key, "main") if key in {"decoder_id", "condition"} else stage[key] for key in META}


def _condition(job, config=None):
    """Human-readable control labels without copying private config or job IDs."""
    config = config or {}
    train, calibration = config.get("train", {}), config.get("calibration", {})
    label = job["job_id"]
    if job["block"] == "mechanism":
        if train.get("fixed_anchor_replay") or "anchor-replay" in label:
            return "fixed_anchor_replay"
        if calibration.get("reestimate_each_round") is False or "mechanism-fixed" in label:
            return "fixed_round1_geometry"
        return "covariance_geometry_controls"
    if job["block"] == "diagnostic":
        if train.get("loss_scope") == "completion" or "completion" in label:
            return "completion_only_loss"
        tau = calibration.get("tau")
        if isinstance(tau, (int, float)) and not isinstance(tau, bool):
            return f"tau_{tau:g}"
        return "tau_0.5" if "tau-half" in label else "tau_2" if "tau-two" in label else "strength_sensitivity"
    if job["block"] == "token_matched":
        return "fixed_supervised_token_exposure"
    return job.get("decoder_id", "main")


def _failure(error):
    # Exception text and filesystem paths may include private random seeds.
    # Report stable categories; the original immutable manifest identifies runs.
    if isinstance(error, FileNotFoundError):
        return "pending", "Missing planned artifact, task snapshot, or completion seal"
    return "invalid", "Artifact identity, checksum, protocol, or retained-record validation failed"


def _output_identity(job):
    from run_release_study import digest
    stored = _read(_path(job["output_dir"]) / "manifest.json")
    if job["kind"] == "training":
        if digest(stored.get("config")) != job["config_sha256"]:
            raise ValueError("Stored training configuration differs from plan")
    else:
        protocol = stored.get("protocol", {})
        if (protocol.get("source_run") != job["source_run"] or
                protocol.get("methods") != job["methods"] or
                protocol.get("rounds") != [job["student_round"]] or
                protocol.get("seed") != job["seed"] or
                protocol.get("generation", {}).get("samples") != job["samples_per_task"] or
                protocol.get("task_sha256") != job["task_sha256"] or
                len(protocol.get("task_ids", [])) != job["task_count"] or not stored.get("fingerprint")):
            raise ValueError("Stored transfer identity differs from plan")
        if any(protocol.get("generation", {}).get(key) != setting
               for key, setting in job.get("generation_overrides", {}).items()):
            raise ValueError("Stored decoder differs from the fixed robustness recipe")
    return stored


def _values(summary, metric):
    def get(row):
        if metric.startswith("pass@"):
            return row["pass_at_k"][metric[5:]]
        proxy = row["implementation_proxy"]
        return proxy["coverage_at_k"][metric[1:]] if metric.startswith("C") else proxy["correct_matched_coverage_at_budgets"][metric[1:]]
    output = {task: get(row) for task, row in summary["per_task"].items()}
    if any(value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value))
           for value in output.values()):
        raise ValueError("Metric contains a nonfinite or nonnumeric value")
    return output


def _scan(stage):
    samples, summary = stage["samples_per_task"], stage["summary"]
    seen, correct, prompts, errors = defaultdict(set), Counter(), {}, Counter()
    for row in _rows(stage["_records_path"]):
        task, sample = row.get("task_id"), row.get("sample_id")
        if task not in summary["per_task"] or type(sample) is not int or not 0 <= sample < samples:
            raise ValueError("Unexpected retained task or sample ID")
        if sample in seen[task] or type(row.get("correct")) is not bool:
            raise ValueError("Duplicate retained key or invalid correctness")
        seen[task].add(sample)
        correct[task] += row["correct"]
        fingerprint = row.get("prompt_sha256")
        if (not isinstance(fingerprint, str) or len(fingerprint) != 64 or
                any(char not in "0123456789abcdef" for char in fingerprint) or
                (task in prompts and prompts[task] != fingerprint)):
            raise ValueError("Missing or inconsistent prompt fingerprints")
        prompts[task] = fingerprint
        detail = row.get("verification_error") or {}
        detail = detail if isinstance(detail, dict) else {}
        errors[(str(row.get("status", "unknown")), str(row.get("finish_reason", "unknown")),
                str(detail.get("phase") or "unavailable"), str(detail.get("exception_type") or "unavailable"))] += 1
    for task, row in summary["per_task"].items():
        if len(seen[task]) != samples or correct[task] != row["correct_count"]:
            raise ValueError("Retained records disagree with sealed metrics")
    return prompts, [{**_meta(stage), "status": "available", "verification_status": key[0],
                     "finish_reason": key[1], "failure_phase": key[2], "exception_type": key[3],
                     "count": count, "fraction": count / (samples * len(summary["per_task"]))}
                    for key, count in sorted(errors.items())]


def _load_stage(job, public_id, method, round_index, stage_kind="evaluation", config=None, config_error=None):
    directory = _path(job["output_dir"]) / ("base" if method == "base" else f"{method}/round_{round_index}")
    diagnostic = stage_kind == "generation_policy"
    settings = (config or {}).get("diagnostics", {})
    samples = (settings.get("eval_samples") or 16) if diagnostic else job.get("samples_per_task", 64)
    count = (settings.get("eval_task_limit") or 128) if diagnostic else job.get("task_count", 500)
    stage = {"job_id": public_id, "block": job["block"], "model_key": job["model_key"],
             "condition": _condition(job, config),
             "replicate_id": job["replicate_id"], "dataset": job.get("benchmark", job.get("dataset", "mbpp")),
             "decoder_id": job.get("decoder_id", "main"),
             "method": method, "round": round_index, "stage": stage_kind,
             "samples_per_task": samples, "planned_tasks": count, "status": "pending", "reason": "",
             "_directory": directory, "_seed": job["seed"], "_source_job": job["job_id"]}
    filenames = [f"{stage_kind}.metrics.json", f"{stage_kind}.jsonl.budget.json", f"{stage_kind}.verified.jsonl"]
    try:
        if config_error:
            raise config_error
        stored = _output_identity(job)
        seal = _seal(directory, filenames)
        if job["kind"] == "transfer" and _read(directory / "complete.json").get("protocol_fingerprint") != stored["fingerprint"]:
            raise ValueError("Transfer stage has a different protocol fingerprint")
        summary = _read(directory / filenames[0])
        per_task = summary.get("per_task", {})
        if not isinstance(per_task, dict) or len(per_task) != count or any(row.get("sample_count") != samples for row in per_task.values()):
            raise ValueError("Task or sample counts differ from plan")
        tasks_path = _path(job["output_dir"]) / "tasks" / ("generation_diagnostic.jsonl" if diagnostic else "eval.jsonl")
        tasks = list(_rows(tasks_path))
        if len(tasks) != count or {row["task_id"] for row in tasks} != set(per_task):
            raise ValueError("Saved tasks differ from metric task universe")
        if diagnostic and (set(stored.get("generation_diagnostic_task_ids", [])) != set(per_task) or
                           stored.get("generation_diagnostic_samples") != samples):
            raise ValueError("Generation diagnostic identity differs")
        if not summary.get("protocol", {}).get("evaluation"):
            raise ValueError("Missing declared evaluator identity")
        budget = _read(directory / filenames[1])
        protocol = budget.get("protocol", {})
        if (not protocol.get("prompts") or not isinstance(protocol.get("settings"), dict) or
                protocol["settings"].get("samples") != samples or budget.get("tasks") != count or
                budget.get("samples") != samples * count):
            raise ValueError("Missing or inconsistent prompt and decoding protocol")
        for metric in _metric_names(samples):
            _values(summary, metric)
        stage.update(summary=summary, _budget=budget, _records_path=directory / filenames[2],
                     metrics_sha256=_sha(directory / filenames[0]), seal_sha256=seal["marker_sha256"])
        stage["_prompts"], stage["_errors"] = _scan(stage)
        stage["status"] = "available"
    except (OSError, ValueError, KeyError, TypeError) as error:
        stage["status"], stage["reason"] = _failure(error)
        stage.pop("summary", None)
    return stage


def _signature(stage, *, aligned=False, across_replicates=False):
    protocol = stage["_budget"]["protocol"]
    settings = dict(protocol["settings"])
    if aligned:
        settings.pop("samples", None)
    result = {"settings": settings, "prompts": stage["_prompts"], "format": protocol.get("format")}
    if not across_replicates:
        result["seed"] = protocol.get("seed")
    result["metrics"] = {key: stage["summary"]["protocol"].get(key) for key in (
        "ks", "correct_budget", "correct_budgets", "proxy_version", "metric_versions", "sampling",
        "evaluation", "evaluation_task_harnesses")}
    return result


def _comparable(reference, candidate, *, aligned=False):
    if reference["model_key"] != candidate["model_key"] or reference["replicate_id"] != candidate["replicate_id"]:
        raise ValueError("Cannot pair different models or training replicates")
    if _signature(reference, aligned=aligned) != _signature(candidate, aligned=aligned):
        raise ValueError("Task, prompt, metric, evaluator, or decoding identity differs")
    from improving.metrics import compare_summaries
    compare_summaries(reference["summary"], candidate["summary"], bootstrap_samples=0)


def _estimate(values, seed, bootstraps):
    from improving.longitudinal import _estimate as estimate
    return estimate(values, bootstraps, seed)


def _flat(estimate):
    interval = estimate.get("ci95")
    return {"mean": estimate.get("mean"), "ci95_low": interval[0] if interval else None,
            "ci95_high": interval[1] if interval else None,
            "eligible_tasks": estimate.get("eligible_tasks"), "total_tasks": estimate.get("total_tasks"),
            "eligible_task_ids": estimate.get("eligible_task_ids", []),
            "bootstrap_valid_replicates": estimate.get("bootstrap_valid_replicates", 0)}


def _empty(stage):
    return {"mean": None, "ci95_low": None, "ci95_high": None,
            "eligible_tasks": None, "total_tasks": stage["planned_tasks"],
            "eligible_task_ids": [], "bootstrap_valid_replicates": 0}


def _estimates(stage, bootstraps=BOOTSTRAPS):
    rows = []
    for metric in _metric_names(stage["samples_per_task"]):
        row = {**_meta(stage), "metric": metric, "status": stage["status"], "reason": stage["reason"], **_empty(stage)}
        if stage["status"] == "available":
            row.update(_flat(_estimate(_values(stage["summary"], metric), stage["_seed"], bootstraps)))
            if row["mean"] is None:
                row.update(status="unavailable", reason="No eligible tasks for this metric")
        rows.append(row)
    return rows


def _pair(reference, candidate, kind, *, bootstraps=BOOTSTRAPS, aligned=False, same_decoder=True):
    common = {**_meta(candidate), "reference_job": reference["job_id"], "candidate_job": candidate["job_id"],
              "reference_block": reference["block"], "candidate_block": candidate["block"],
              "reference_condition": reference.get("condition", "main"), "candidate_condition": candidate.get("condition", "main"),
              "reference": reference["method"], "candidate": candidate["method"],
              "reference_round": reference["round"], "reference_stage": reference["stage"],
              "kind": kind, "direction": "candidate_minus_reference", "same_decoder": same_decoder}
    status, reason = "available", ""
    try:
        if reference["status"] != "available" or candidate["status"] != "available":
            status, reason = "pending", "Missing or invalid sealed comparison stage"
        elif not same_decoder:
            status, reason = "incomparable", "SSD generator uses a different decoder; teacher/native effects are not identified"
        else:
            _comparable(reference, candidate, aligned=aligned)
    except (ValueError, KeyError, TypeError):
        status, reason = "incomparable", "Model, task, prompt, metric, evaluator, or decoding protocols differ"
    rows = []
    for metric in _metric_names(candidate["samples_per_task"]):
        row = {**common, "metric": metric, "status": status, "reason": reason, **_empty(candidate)}
        if status == "available":
            left, right = _values(reference["summary"], metric), _values(candidate["summary"], metric)
            # Bootstrap the paired common-eligible tasks directly. In particular,
            # never subtract marginal D means with different eligible cohorts.
            differences = {task: right[task] - left[task] for task in left
                           if left[task] is not None and right.get(task) is not None}
            row.update(_flat(_estimate(differences, candidate["_seed"], bootstraps)))
            row["total_tasks"] = candidate["planned_tasks"]
            row["reference_eligible_tasks"] = sum(value is not None for value in left.values())
            row["candidate_eligible_tasks"] = sum(value is not None for value in right.values())
            row["reference_common_mean"] = statistics.mean(left[task] for task in differences) if differences else None
            row["candidate_common_mean"] = statistics.mean(right[task] for task in differences) if differences else None
            if not differences:
                row.update(status="unavailable", reason="No common eligible tasks for this metric")
        rows.append(row)
    return rows


def _retention(base, stage, bootstraps=BOOTSTRAPS):
    from improving.longitudinal import _retention_ratio
    status, reason = "available", ""
    if base["status"] != "available" or stage["status"] != "available":
        status, reason = "pending", "Missing or invalid own-base or student stage"
    else:
        try:
            _comparable(base, stage)
        except (ValueError, KeyError, TypeError):
            status, reason = "incomparable", "Own-base and student protocols differ"
    rows = []
    for metric in RICHNESS_METRICS:
        row = {**_meta(stage), "metric": metric, "status": status, "reason": reason,
               "definition": "student/base ratio of macro richness on common eligible tasks", **_empty(stage)}
        if status == "available":
            ratio = _retention_ratio(_values(base["summary"], metric), _values(stage["summary"], metric), bootstraps, stage["_seed"])
            row.update(_flat({**ratio, "mean": ratio["mean_ratio"]}))
            if row["mean"] is None:
                row.update(status="unavailable", reason="No common eligible tasks or zero own-base richness")
        rows.append(row)
    return rows


def _endpoint(stage, estimates, retention):
    row = {**_meta(stage), "status": stage["status"], "reason": stage["reason"],
           "samples_per_task": stage["samples_per_task"], "planned_tasks": stage["planned_tasks"]}
    for estimate in estimates:
        metric = estimate["metric"]
        for source, suffix in (("mean", ""), ("ci95_low", "_ci95_low"), ("ci95_high", "_ci95_high"),
                               ("eligible_tasks", "_eligible_tasks"), ("status", "_status")):
            row[metric + suffix] = estimate[source]
    for ratio in retention:
        metric = ratio["metric"] + "_retention"
        row.update({metric: ratio["mean"], metric + "_ci95_low": ratio["ci95_low"],
                    metric + "_ci95_high": ratio["ci95_high"], metric + "_status": ratio["status"]})
    row["richness_retention"] = row.get("C64_retention")
    return row


def _replicate_rows(trajectories, pairs, stages, retention=()):
    groups = defaultdict(dict)
    signatures = defaultdict(dict)
    stage_map = {(stage["job_id"], stage["method"], stage["round"], stage["stage"]): stage for stage in stages}
    for kind, source in (("level", trajectories), ("paired_effect", pairs), ("retention", retention)):
        for row in source:
            if row["block"] not in {"core", "scale", "transfer", "token_matched", "decoder"}:
                continue
            if kind == "paired_effect" and row["kind"] != "same_round_method":
                continue
            reference = row.get("reference", "") if kind == "paired_effect" else ""
            key = (kind, row["block"], row["model_key"], row["dataset"], row.get("decoder_id", "main"),
                   row["method"], reference, row["round"], row["metric"])
            replicate = row["replicate_id"]
            if replicate in groups[key]:
                raise ValueError("Duplicate model/block/replicate summary identity")
            groups[key][replicate] = row["mean"] if row["status"] == "available" else None
            if row["status"] == "available":
                stage = stage_map[(row["job_id"], row["method"], row["round"], row["stage"])]
                signature = [_signature(stage, across_replicates=True)]
                if kind == "paired_effect":
                    before = stage_map[(row["reference_job"], reference, row["reference_round"], row["reference_stage"])]
                    signature.append(_signature(before, across_replicates=True))
                elif kind == "retention":
                    before = stage_map[(row["job_id"], "base", 0, row["stage"])]
                    signature.append(_signature(before, across_replicates=True))
                signatures[key][replicate] = signature
    output = []
    for key, values in sorted(groups.items()):
        kind, block, model, dataset, decoder, method, reference, round_index, metric = key
        planned = sorted(values)
        available = [replicate for replicate in planned if values[replicate] is not None]
        observed = [values[replicate] for replicate in available]
        comparable = bool(available) and all(signatures[key][replicate] == signatures[key][available[0]] for replicate in available)
        status = ("available" if len(available) == len(planned) else "partial") if comparable else "incomparable_protocols" if available else "pending"
        output.append({"kind": kind, "block": block, "model_key": model, "dataset": dataset,
                       "decoder_id": decoder, "method": method, "reference": reference, "round": round_index, "metric": metric,
                       "status": status, "planned_replicates": planned, "available_replicates": available,
                       "replicate_values": values, "planned_replicate_count": len(planned), "replicate_count": len(observed),
                       "mean": statistics.mean(observed) if comparable else None,
                       "sample_sd": statistics.stdev(observed) if comparable and len(observed) > 1 else None,
                       "ci95_low": None, "ci95_high": None,
                       "uncertainty": "Descriptive between-training-replicate sample SD; undefined at n=1; no training-replicate CI"})
    return output


def _aligned(stage, tasks, samples, bootstraps):
    from improving.metrics import summarize_records
    rows = [row for row in _rows(stage["_records_path"]) if row["task_id"] in tasks and row["sample_id"] < samples]
    summary = summarize_records(rows, ks=[k for k in (1, 8, 16, 32, 64) if k <= samples], correct_budget=4,
                                correct_budgets=[k for k in (4, 8, 16) if k <= samples],
                                expected_samples={task: samples for task in tasks}, bootstrap_samples=0, seed=stage["_seed"])
    return {**stage, "summary": summary, "samples_per_task": samples, "planned_tasks": len(tasks),
            "_prompts": {task: stage["_prompts"][task] for task in tasks}}


def _teacher_rows(previous, teacher, student, bootstraps):
    context = {**_meta(teacher), "sampling": "Fixed diagnostic tasks and equal leading sample-ID budgets"}
    metrics = _metric_names(teacher["samples_per_task"])
    roles = ("previous_native", "teacher_policy", "student_native")
    try:
        if any(stage["status"] != "available" for stage in (previous, teacher, student)):
            raise FileNotFoundError("Missing diagnostic stage")
        tasks = set(teacher["summary"]["per_task"])
        aligned = [_aligned(stage, tasks, teacher["samples_per_task"], bootstraps) for stage in (previous, teacher, student)]
        rows = []
        for role, stage in zip(roles, aligned):
            rows.extend({**row, **context, "kind": "level", "role": role, "source_method": stage["method"],
                         "source_round": stage["round"]} for row in _estimates(stage, bootstraps))
        for left, right, kind in ((0, 1, "teacher_minus_previous"), (1, 2, "student_minus_teacher"), (0, 2, "student_minus_previous")):
            rows.extend({**row, **context, "kind": kind, "role": "paired_change"} for row in
                        _pair(aligned[left], aligned[right], kind, bootstraps=bootstraps, aligned=True,
                              same_decoder=teacher["method"] != "ssd" or (left, right) == (0, 2)))
        return rows
    except (OSError, ValueError, KeyError, TypeError):
        return [{**context, "metric": metric, "kind": kind, "role": role, "status": "pending",
                 "reason": "Missing, invalid, or unalignable fixed generator/student diagnostic", **_empty(teacher)}
                for kind, role in [("level", role) for role in roles] +
                [(kind, "paired_change") for kind in ("teacher_minus_previous", "student_minus_teacher", "student_minus_previous")]
                for metric in metrics]


def _auxiliary(stage, job):
    resources, operators = [], []
    if stage["stage"] != "evaluation":
        return resources, operators
    directory = stage["_directory"]
    planned = ["evaluation.jsonl.budget.json"]
    if job["kind"] == "transfer":
        resource_stages = ("model_loading", "evaluation_generation", "verification_and_metrics")
    elif stage["method"] == "base":
        resource_stages = ("model_loading", "evaluation")
    else:
        planned += ["training_stats.json", "train.jsonl.budget.json", "generation_policy.jsonl.budget.json"]
        resource_stages = ("model_loading", "training_generation", "generation_policy", "sft", "post_training_evaluation")
        if stage["method"] not in {"plain", "ssd"}:
            resource_stages += ("calibration",)
    planned += [f"{name}.resources.json" for name in resource_stages]
    planned = list(dict.fromkeys(planned + [path.name for path in sorted(directory.glob("*.resources.json"))]))
    fields = ("examples", "optimizer_steps", "epochs", "loss_scope", "supervised_tokens_per_epoch",
              "target_token_budget", "actual_supervised_target_tokens", "target_token_overshoot",
              "target_token_overshoot_upper_bound_exclusive", "supervised_target_tokens_by_origin",
              "all_raw_records_retained", "all_raw_records_exposed", "fixed_anchor_replay", "anchor_reference_records",
              "raw_records_received", "raw_records_retained", "training_records_received", "training_records_retained",
              "training_budget_mode", "configured_epochs", "configured_epochs_applied", "record_exposures",
              "truncated_examples", "truncated_tokens",
              "trainable_parameter_count", "mean_loss", "samples", "generation_tokens", "prompt_tokens",
              "length_capped_samples", "elapsed_seconds", "cuda_peak_allocated_bytes", "cuda_peak_reserved_bytes")
    for filename in planned:
        row = {**_meta(stage), "resource_stage": filename, "status": "pending"}
        try:
            unsealed_base = (stage["method"] == "base" and filename.endswith(".resources.json") and
                             filename not in _read(directory / "complete.json").get("files", {}))
            if not unsealed_base:
                _seal(directory, [filename])
            data = _read(directory / filename)
            row.update(status="recorded_unsealed" if unsealed_base else "available", **{key: data.get(key) for key in fields})
        except (OSError, ValueError, KeyError, TypeError) as error:
            row["status"], row["reason"] = _failure(error)
        resources.append(row)
    if job["kind"] == "training" and stage["method"] not in {"base", "plain", "ssd"}:
        try:
            _seal(directory, ["operator_diagnostics.json"])
            data = _read(directory / "operator_diagnostics.json")
            if not isinstance(data, dict) or not data:
                raise ValueError("Missing operator diagnostics")
            for layer, values in sorted(data.items()):
                operators.append({**_meta(stage), "layer": layer, "status": "available",
                                  **{key: values.get(key) for key in ("dimension", "eigenvalue_min", "eigenvalue_max",
                                     "mean_eigenvalue", "nonscalar_frobenius_norm", "nonscalar_fraction_of_operator_norm",
                                     "operator_frobenius_norm", "frobenius_distance_from_identity", "matching_contract",
                                     "matching_absolute_error", "activation_rms_matched", "output_kl_matched", "folded_weight_relative_delta")}})
        except (OSError, ValueError, KeyError, TypeError) as error:
            status, reason = _failure(error)
            operators.append({**_meta(stage), "status": status, "reason": reason})
    return resources, operators


def _primary(pairs):
    return [{**row, "prospective": True, "endpoint": "round_5_native_student", "decision": "not_thresholded",
             "decision_reason": "No numerical success threshold or multiplicity-adjusted decision rule is registered"}
            for row in pairs if row["block"] == "core" and row["round"] == 5 and
            row["kind"] == "same_round_method" and row["candidate"] == "spectral_soft" and row["reference"] in {"plain", "ssd"}]


def _markdown(report):
    lines = ["# Fixed SPECTRUM release study", "", f"Artifact completion: **{report['status']}**.", "",
             "All planned cells are retained. Missing values are `x`; negative and inconclusive effects are retained. "
             "Completion is independent of effect sign and does not assert that SPECTRUM wins.", "",
             "The prospective primary comparisons are round-5 native SPECTRUM versus Vanilla and versus SSD, separately, "
             "on the three-replicate core model. No automatic PASS threshold is defined. Scale models, mechanisms, "
             "token-matched training, diagnostics, and transfers remain separate experimental blocks.", "",
             "C64 is correct Python AST richness at 64 total draws. D4/D8/D16 are correct-conditioned AST richness. "
             "These are implementation proxies, not algorithm identities. Paired effects use the same eligible tasks in both arms, "
             "with that cohort explicitly exported. Retention is a ratio of task-macro richness versus the same replicate's initial model, "
             "not survival of particular algorithms.", "",
             f"Intervals use {report['bootstrap']['samples']:,} task-bootstrap draws and are pointwise. "
             "They describe task uncertainty, not training-replicate variability. Replicate tables provide actual replicate counts "
             "and descriptive sample SD when at least two comparable replicates are available. Single-replicate scale models have no "
             "training-replicate interval or SD. Models and experimental blocks are never pooled.", "",
             "## Planned endpoints", "",
             "| Job | Block | Condition | Model | Replicate | Decoder | Method | Round | Status | pass@1 | pass@8 | pass@16 | pass@32 | pass@64 | C64 | D4 | D8 | D16 | C64 retention |",
             "|---|---|---|---|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    def cell(value):
        return "x" if value is None else f"{value:.4f}" if isinstance(value, float) else str(value).replace("|", "/")
    for row in report["endpoints"]:
        keys = ("job_id", "block", "condition", "model_key", "replicate_id", "decoder_id", "method", "round", "status", "pass@1", "pass@8", "pass@16", "pass@32", "pass@64", "C64", "D4", "D8", "D16", "C64_retention")
        lines.append("| " + " | ".join(cell(row.get(key)) for key in keys) + " |")
    lines += ["", "## Evidence and interpretation", "",
              "- `trajectories.csv` and `retention.csv` retain every planned round and replicate, including missing stages.",
              "- `primary_comparisons.csv` keeps SPECTRUM–Vanilla and SPECTRUM–SSD separate. `paired_differences.csv` includes all requested directions and adjacent-round changes.",
              "- `replicate_summary.csv` reports observed replicate values and completion counts; partial means are explicitly marked partial.",
              "- `ablations.csv` records mechanism and sensitivity controls, including fixed geometry, without treating them as additional full-SPECTRUM replicates.",
              "- `decoder_effects.csv` retains every fixed decoder recipe and the matching main-decoder source comparison. Comparisons use the same decoder within each pair; recipes are not selected by observed performance.",
              "- `teacher_student.csv` aligns tasks and leading sample IDs before intervention, under the generating policy, and after SFT. SSD generator/native comparisons are marked incomparable when decoding differs.",
              "- `resources.csv` and `operators.csv` describe recorded compute, token counts, average operator scaling, and nonscalar directionality. Missing diagnostics are not inferred; base resources outside the completion seal are marked recorded_unsealed.",
              "- Transfer results preserve each dataset's recorded evaluator identity; adapted benchmark protocols must not be presented as official leaderboard scores.",
              "- Public artifacts use replicate labels. Job aliases follow immutable manifest order; private seed values, configurations, and source paths are excluded.",
              "", "Source runs were read only. This command did not load model weights, train models, or execute generated programs.", ""]
    return "\n".join(lines)


def build_report(manifest_path, output_dir=None, *, bootstrap_samples=BOOTSTRAPS):
    from run_release_study import digest, job_status, load_manifest
    if type(bootstrap_samples) is not int or bootstrap_samples < 0:
        raise ValueError("Bootstrap samples must be a nonnegative integer")
    manifest_path = Path(manifest_path).resolve()
    manifest = load_manifest(manifest_path, verify_inputs=False)
    jobs = _validate_jobs(manifest)
    output = _path(output_dir) if output_dir else _path(manifest.get("run_root") or manifest_path.parent) / "release_report"
    if any(output.is_relative_to(_path(job["output_dir"])) or _path(job["output_dir"]).is_relative_to(output) for job in jobs):
        raise ValueError("Report output must be separate from source job directories")
    aliases = {job["job_id"]: f"job-{index:03d}" for index, job in enumerate(jobs, 1)}
    stages, teachers, statuses, resources, operators, errors, stage_map = [], [], [], [], [], [], {}
    for job in jobs:
        config, config_error = None, None
        if job["kind"] == "training":
            try:
                config = _read(_path(job["config"]))
                if not job.get("config_sha256") or digest(config) != job["config_sha256"]:
                    raise ValueError("Planned training configuration changed")
            except (OSError, ValueError, KeyError, TypeError) as error:
                config_error = error
        local = []
        for method, index in [("base", 0)] + [(method, index) for index in _rounds(job) for method in job["methods"]]:
            stage = _load_stage(job, aliases[job["job_id"]], method, index, config=config, config_error=config_error)
            stages.append(stage)
            local.append(stage)
            stage_map[(job["job_id"], method, index)] = stage
            if job["kind"] == "training" and method != "base":
                teacher = _load_stage(job, aliases[job["job_id"]], method, index, "generation_policy", config, config_error)
                teachers.append(teacher)
                local.append(teacher)
            resource, operator = _auxiliary(stage, job)
            resources.extend(resource)
            operators.extend(operator)
        for stage in local:
            errors.extend(stage.get("_errors", [{**_meta(stage), "status": stage["status"], "reason": stage["reason"], "count": None}]))
        native = job_status(job, verify_hashes=False)
        auxiliary_ok = all(row["status"] in {"available", "recorded_unsealed"} for row in resources + operators
                           if row["job_id"] == aliases[job["job_id"]])
        completed = native["status"] == "completed" and all(stage["status"] == "available" for stage in local) and auxiliary_ok
        statuses.append({"job_id": aliases[job["job_id"]], "block": job["block"], "model_key": job["model_key"],
                         "condition": _condition(job, config),
                         "replicate_id": job["replicate_id"], "dataset": job.get("benchmark", job.get("dataset", "mbpp")),
                         "decoder_id": job.get("decoder_id", "main"),
                         "status": "completed" if completed else "incomplete", "planned_stages": len(local),
                         "available_stages": sum(stage["status"] == "available" for stage in local),
                         "reason": "" if completed else "One or more planned stages, diagnostics, or native completion checks are incomplete"})
    trajectories, endpoints, pairs, retention, ablations = [], [], [], [], []
    for job in jobs:
        base = stage_map[(job["job_id"], "base", 0)]
        for method, index in [("base", 0)] + [(method, index) for index in _rounds(job) for method in job["methods"]]:
            stage = stage_map[(job["job_id"], method, index)]
            estimates = _estimates(stage, bootstrap_samples)
            ratios = _retention(base, stage, bootstrap_samples)
            trajectories.extend(estimates)
            retention.extend(ratios)
            if index in {0, max(_rounds(job))}:
                endpoints.append(_endpoint(stage, estimates, ratios))
            if index:
                pairs.extend(_pair(base, stage, "initial_model", bootstraps=bootstrap_samples))
                previous = stage_map.get((job["job_id"], method, index - 1))
                if previous:
                    pairs.extend(_pair(previous, stage, "adjacent_round", bootstraps=bootstrap_samples))
        for index in _rounds(job):
            for reference, candidate in (("plain", "spectral_soft"), ("ssd", "spectral_soft"), ("plain", "ssd")):
                if reference in job["methods"] and candidate in job["methods"]:
                    pairs.extend(_pair(stage_map[(job["job_id"], reference, index)], stage_map[(job["job_id"], candidate, index)],
                                       "same_round_method", bootstraps=bootstrap_samples))
            comparison_job = job.get("comparison_job")
            if comparison_job:
                full = stage_map.get((comparison_job, "spectral_soft", index))
                if full is None:
                    raise ValueError("Planned cross-job comparison has no full-SPECTRUM round")
                for method in job["methods"]:
                    ablations.extend(_pair(stage_map[(job["job_id"], method, index)], full,
                                           f"full_spectrum_vs_{job['block']}_control", bootstraps=bootstrap_samples))
    teacher_student = []
    for teacher in teachers:
        job_id, method, index = teacher["_source_job"], teacher["method"], teacher["round"]
        previous = stage_map.get((job_id, "base" if index == 1 else method, index - 1))
        if previous is None:
            previous = {**teacher, "status": "pending"}
        teacher_student.extend(_teacher_rows(previous, teacher, stage_map[(job_id, method, index)], bootstrap_samples))
    decoder_sources = {aliases[source] for job in jobs if job["block"] == "decoder"
                       for source in ([job["source_job"]] if job.get("source_job") else job.get("depends_on", [])) if source in aliases}
    decoder_effects = [row for row in pairs if row["round"] == 5 and
                       (row["block"] == "decoder" or row["job_id"] in decoder_sources) and
                       row["kind"] in {"same_round_method", "initial_model"}]
    report = {"schema_version": 1, "study": "SPECTRUM fixed release study", "manifest_sha256": _sha(manifest_path),
              "status": "completed" if all(row["status"] == "completed" for row in statuses) else "incomplete",
              "primary_decision": "not_thresholded", "bootstrap": {"samples": bootstrap_samples, "confidence": 0.95,
                  "unit": "tasks; common eligible paired tasks for differences", "multiplicity": "pointwise, not adjusted",
                  "training_replicate_uncertainty": False}, "jobs": statuses,
              "endpoints": endpoints, "trajectories": trajectories, "retention": retention,
              "paired_differences": pairs, "primary_comparisons": _primary(pairs),
              "replicate_summary": _replicate_rows(trajectories, pairs, stages, retention), "ablations": ablations,
              "decoder_effects": decoder_effects,
              "teacher_student": teacher_student, "errors": errors, "resources": resources, "operators": operators,
              "stages": [{key: value for key, value in stage.items() if not key.startswith("_") and key != "summary"}
                         for stage in stages + teachers]}
    for name in ("endpoints", "trajectories", "retention", "paired_differences", "primary_comparisons", "replicate_summary",
                 "ablations", "decoder_effects", "teacher_student", "errors", "resources", "operators"):
        _csv(output / f"{name}.csv", report[name])
    _write(output / "summary.json", json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    _write(output / "REPORT.md", _markdown(report))
    return {"status": report["status"], "output_dir": str(output), "planned_jobs": len(jobs),
            "completed_jobs": sum(row["status"] == "completed" for row in statuses), "primary_decision": "not_thresholded"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir")
    parser.add_argument("--bootstrap-samples", type=int, default=BOOTSTRAPS)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(build_report(args.manifest, args.output_dir, bootstrap_samples=args.bootstrap_samples), indent=2))
    except (OSError, ValueError, KeyError, TypeError, ImportError) as error:
        parser.exit(2, f"error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
