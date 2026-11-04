"""Three-state diagnostics for learned SPECTRUM self-distillation.

The same fixed *development* tasks are evaluated at P_r (native, pre-SFT),
Q_r (spectrally steered, pre-SFT), and P_{r+1} (native, post-SFT). All three
use identical sample budgets/decoder settings, native task tests, and the same
task-level bootstrap unit. Nothing in this module changes gain fitting, chooses
training examples, or reads held-out MBPP500 data.

No full-trajectory KL or theoretical bound is inferred from short probe KL.
"""
from __future__ import annotations

from contextlib import nullcontext
import json
from pathlib import Path
from typing import Any, Mapping


ROLES = ("pre_native", "pre_spectral", "post_native")


def transfer_settings(config: dict) -> dict | None:
    diagnostics = config.get("diagnostics", {})
    raw = diagnostics.get("transfer_gap")
    if raw is None or raw is False:
        return None
    if not isinstance(raw, Mapping) or raw.get("enabled") is not True:
        raise ValueError("diagnostics.transfer_gap requires enabled=true")
    if config.get("methods") != ["spectral_learned"]:
        raise ValueError("Transfer-gap instrumentation is initially restricted to spectral_learned-only runs")
    rounds = raw.get("rounds")
    if (not isinstance(rounds, list) or not rounds or
            any(type(x) is not int or x < 1 or x > config["rounds"] for x in rounds) or
            len(set(rounds)) != len(rounds) or rounds != sorted(rounds)):
        raise ValueError("transfer_gap.rounds must be distinct, ordered, in-range positive round numbers")
    sample_count = raw.get("samples")
    if type(sample_count) is not int or sample_count < 64:
        raise ValueError("transfer_gap.samples must be >=64 to report pass@64 and C64")
    task_count = raw.get("validation_task_count")
    if type(task_count) is not int or task_count != 30:
        raise ValueError("Transfer-gap contract requires the complete frozen 30-task MBPP validation split")
    generation = {}
    for key in ("batch_size", "task_batch_size", "sequence_batch_size",
                "max_prompt_tokens", "max_new_tokens"):
        value = raw.get(key)
        if type(value) is not int or value < 1:
            raise ValueError(f"transfer_gap.{key} must be a positive integer")
        generation[key] = value
    if generation["max_new_tokens"] != config["generation"]["max_new_tokens"]:
        raise ValueError("Development generation must match 4096-token main study cap")
    if generation["max_prompt_tokens"] != config["generation"]["max_prompt_tokens"]:
        raise ValueError("Development prompt cap must match native generation cap")
    if generation["batch_size"] > generation["sequence_batch_size"]:
        raise ValueError("Transfer-gap batch_size must fit sequence_batch_size")
    backend = config.get("evaluation", {}).get("backend", "docker")
    if backend not in {"docker", "bwrap", "local"}:
        raise ValueError("Transfer-gap verification backend must be docker, bwrap or explicitly enabled local")
    if backend == "local" and not config.get("evaluation", {}).get("allow_unsafe_local"):
        raise ValueError("Local transfer-gap verification requires allow_unsafe_local=true")
    if raw.get("reference_nll_each_round") is not True:
        raise ValueError("Require post-SFT fit/guard reference NLL each round")
    # This deliberately leaves SFT/fit/probe config unchanged.
    return {**generation, "samples": sample_count, "rounds": rounds,
            "validation_task_count": task_count, "reference_nll_each_round": True}


def should_evaluate(config: dict, round_index: int) -> bool:
    settings = transfer_settings(config)
    return settings is not None and round_index in settings["rounds"]


def validate_development_tasks(tasks: list[dict], train_tasks: list[dict],
                               calibration_tasks: list[dict], evaluation_tasks: list[dict],
                               expected: int = 30) -> None:
    from .data import assert_disjoint_splits, validate_tasks
    if len(tasks) != expected or any(row.get("split") != "validation" for row in tasks):
        raise ValueError(f"Use exactly {expected} original validation tasks; never test tasks")
    validate_tasks(tasks)
    assert_disjoint_splits({
        "train": train_tasks, "calibration": calibration_tasks,
        "validation": tasks, "eval": evaluation_tasks,
    })


def _stage_binding(identity: str, role: str, tasks: list[dict],
                   settings: dict, evaluation: dict, seed: int, round_index: int) -> dict:
    from .utils import stable_hash
    if role not in ROLES:
        raise ValueError("Unknown transfer-gap stage")
    return {"schema": 1, "model_identity": identity, "role": role,
            "task_records_sha256": stable_hash(tasks),
            "generation": settings, "evaluation": evaluation,
            "seed": seed, "round": round_index,
            "purpose": "heldout-development-three-state-measurement",
            "training_use": False}


def _check_complete(directory: Path, binding: dict) -> dict | None:
    from .pipeline import file_sha
    marker = directory / "complete.json"
    if not marker.exists():
        return None
    state = json.loads(marker.read_text())
    if state.get("binding") != binding:
        raise ValueError(f"Transfer-gap stage identity differs: {directory}")
    required = ("binding.json", "evaluation.jsonl", "evaluation.verified.jsonl",
                "evaluation.metrics.json")
    if not all(relative in state.get("files", {}) for relative in required):
        raise ValueError("Transfer-gap completion receipt is missing necessary native scoring files")
    for relative, checksum in state["files"].items():
        file = directory / relative
        if not file.is_file() or file_sha(file) != checksum:
            raise ValueError(f"Transfer-gap stage file changed or is missing: {file}")
    return json.loads((directory / "evaluation.metrics.json").read_text())


def evaluate_state(model, tokenizer, tasks: list[dict], directory: str | Path,
                   *, config: dict, evaluation: dict, identity: str,
                   role: str, round_index: int, seed: int, resume: bool) -> dict:
    """Evaluate a single native/intervened policy. Caller owns the weight-fold scope."""
    from .generation import generate_to_file
    from .pipeline import evaluate_file, file_sha, record_stage
    from .utils import atomic_json, stable_hash

    transfer = transfer_settings(config)
    if transfer is None or round_index not in transfer["rounds"]:
        raise ValueError("Transfer-gap stage is not configured for this round")
    if role not in ROLES:
        raise ValueError("Invalid transfer-gap role")
    if len(tasks) != transfer["validation_task_count"]:
        raise ValueError("Development population changed")
    generation = {k: config["generation"][k] for k in
                  ("temperature", "top_p", "top_k")}
    generation.update({k: transfer[k] for k in
                       ("samples", "batch_size", "task_batch_size",
                        "sequence_batch_size", "max_prompt_tokens", "max_new_tokens")})
    verification = dict(evaluation)
    verification["ks"] = [1, 4, 8, 16, 32, 64]
    verification["correct_budget"] = 4
    verification["correct_budgets"] = [4, 8, 16, 32, 64]
    directory = Path(directory)
    binding = _stage_binding(identity, role, tasks, generation, verification,
                             seed, round_index)
    complete = _check_complete(directory, binding)
    if complete is not None:
        return complete
    bound = directory / "binding.json"
    if bound.is_file():
        if json.loads(bound.read_text()) != binding:
            raise ValueError("Previous development stage has different task/policy identity")
        if not resume:
            raise FileExistsError("Interrupted development run requires explicit --resume")
    elif directory.exists() and any(directory.iterdir()):
        raise ValueError("Existing development data lack their protocol binding")
    else:
        atomic_json(bound, binding)
    # Important: all three roles use the SAME RNG seed material by choosing the
    # same stage='transfer_gap'; method and checkpoint hashes are still bound in
    # their respective manifests. This gives a common RNG stream, not a guaranteed
    # coupling of the three autoregressive trajectories.
    destination = directory / "evaluation.jsonl"
    with record_stage(directory, "dev_generation"):
        records = generate_to_file(
            model, tokenizer, tasks, destination, generation,
            seed=seed, model_identity=identity, method=role,
            round_index=round_index, stage="transfer_gap", resume=resume)
    with record_stage(directory, "dev_verification"):
        summary = evaluate_file(
            tasks, records, destination, verification,
            expected_samples=generation["samples"], seed=seed)
    if set(summary.get("per_task", {})) != {task["task_id"] for task in tasks}:
        raise ValueError("Incomplete development task population")
    files = {str(path.relative_to(directory)): file_sha(path)
             for path in directory.rglob("*")
             if path.is_file() and not any(p.endswith(".parts") for p in path.parts)
             and path.name != "complete.json"}
    atomic_json(directory / "complete.json",
                {"binding": binding, "files": files, "status": "complete"})
    return summary


def pre_stages_sealed(directory: str | Path, *, config: dict, tasks: list[dict],
                      evaluation: dict, identity: str, round_index: int, seed: int) -> bool:
    """Do not recreate P_r/Q_r from P_(r+1) after SFT has started."""
    settings = transfer_settings(config)
    if settings is None or round_index not in settings["rounds"]:
        return True
    generation = {k: config["generation"][k] for k in
                  ("temperature", "top_p", "top_k")}
    generation.update({k: settings[k] for k in
                       ("samples", "batch_size", "task_batch_size",
                        "sequence_batch_size", "max_prompt_tokens", "max_new_tokens")})
    verification = dict(evaluation)
    verification.update(ks=[1, 4, 8, 16, 32, 64],
                        correct_budget=4, correct_budgets=[4, 8, 16, 32, 64])
    for role in ROLES[:2]:
        stage = Path(directory) / role
        binding = _stage_binding(identity, role, tasks, generation, verification,
                                  seed, round_index)
        if _check_complete(stage, binding) is None:
            raise RuntimeError(f"Cannot recover {role} after SFT: pre-SFT evidence missing")
    return True


def post_reference_nll(model, tokenizer, references: list[dict],
                       calibration_settings: dict, gain_audit: dict) -> dict:
    """Measure identical train-side fit/guard reference NLL AFTER SFT, not test NLL."""
    from .gain_pipeline import reference_batches, split_gain_references
    from .learned_gains import _examples, _mean_nll

    fit, guard = split_gain_references(references, calibration_settings)
    native = gain_audit["native"]
    selected = gain_audit["selected"]
    before = bool(model.training)
    try:
        model.eval()
        after_fit = _mean_nll(model, _examples(reference_batches(tokenizer, fit, calibration_settings), 'fit'))
        after_guard = _mean_nll(model, _examples(reference_batches(tokenizer, guard, calibration_settings), 'guard'))
    finally:
        model.train(before)
    return {
        "definition": "post_native_NLL_minus_pre_spectral_NLL_on_same_training_side_references",
        "pre_native_fit_nll": native["fit_nll"],
        "pre_spectral_fit_nll": selected["fit_nll"],
        "post_native_fit_nll": after_fit,
        "fit_transfer_gap": after_fit - selected["fit_nll"],
        "pre_native_guard_nll": native["guard_nll"],
        "pre_spectral_guard_nll": selected["guard_nll"],
        "post_native_guard_nll": after_guard,
        "guard_transfer_gap": after_guard - selected["guard_nll"],
        "fit_change_native_to_native": after_fit - native["fit_nll"],
        "guard_change_native_to_native": after_guard - native["guard_nll"],
        "identity_fallback": bool(gain_audit["selected_identity"]),
        "caveat": ("Reference NLL is a training-side proxy. A positive transfer gap "
                   "does not by itself prove deterioration of held-out task success."),
    }


def _performance(data: dict) -> dict:
    result = data["aggregate"]
    return {
        "tasks": result["task_count"],
        "success_probability": result["correct_fraction"]["mean"],
        "pass@1": result["pass_at_k"]["1"]["mean"],
        "pass@16": result["pass_at_k"]["16"]["mean"],
        "pass@64": result["pass_at_k"]["64"]["mean"],
        "C64_AST": result["implementation_proxy"]["coverage_at_k"]["64"]["mean"],
        "D4_AST": result["implementation_proxy"]["correct_matched_coverage_at_budgets"]["4"]["mean"],
        "D4_eligible_tasks": result["implementation_proxy"]["correct_matched_coverage_at_budgets"]["4"]["eligible_tasks"],
    }


def _task_evidence(summaries: dict[str, dict]) -> dict:
    ids = sorted(summaries["pre_native"]["per_task"])
    if any(sorted(data["per_task"]) != ids for data in summaries.values()):
        raise ValueError("Three-state task universe mismatch")
    table = {}
    for task in ids:
        item = {}
        for role in ROLES:
            data = summaries[role]["per_task"][task]
            item[role] = {
                "samples": data["sample_count"], "correct": data["correct_count"],
                "pass@1": data["pass_at_k"]["1"],
                "pass@64": data["pass_at_k"]["64"],
                "C64_AST": data["implementation_proxy"]["coverage_at_k"]["64"],
                "D4_AST": data["implementation_proxy"]["correct_matched_coverage_at_budgets"]["4"],
                "observed_correct_AST_labels": sorted(data["implementation_proxy"]["counts"]),
            }
        table[task] = item
    return table


def compare_three_states(summaries: dict[str, dict], *, seed: int,
                         bootstrap_samples: int = 2000) -> dict:
    """Paired task bootstrap; no claim of trajectory-level KL from pass@k."""
    from .metrics import compare_summaries
    if set(summaries) != set(ROLES):
        raise ValueError("All three policy states are required")
    for data in summaries.values():
        if 64 not in data["protocol"].get("ks", []):
            raise ValueError("Three-state evidence must evaluate pass@64")
    # differences are always second minus first
    pairs = {
        "spectral_exploration": ("pre_native", "pre_spectral"),
        "student_transfer": ("pre_spectral", "post_native"),
        "native_to_next_native": ("pre_native", "post_native"),
    }
    comparisons = {}
    for name, (left, right) in pairs.items():
        comparisons[name] = compare_summaries(
            summaries[left], summaries[right],
            bootstrap_samples=bootstrap_samples, seed=seed)
    per_task = _task_evidence(summaries)
    # These are finite-sample observed category changes, NOT a support theorem.
    lost, gained, concentration = [], [], []
    for task, item in per_task.items():
        before = item["pre_spectral"]["correct"]
        after = item["post_native"]["correct"]
        if before > 0 and after == 0:
            lost.append(task)
        if before == 0 and after > 0:
            gained.append(task)
        if before >= 1 and after > before:
            concentration.append(task)
    return {
        "schema_version": 1,
        "measurement": "matched_native_spectral_post_student_heldout_development",
        "states": {role: _performance(summaries[role]) for role in ROLES},
        "paired_task_differences": comparisons,
        "per_task": per_task,
        "observed_rare_correctness": {
            "spectral_correct_then_post_zero": lost,
            "spectral_zero_then_post_correct": gained,
            "post_correct_sample_count_increased": concentration,
        },
        "limitations": [
            "Development-only: do not select methods/checkpoints using MBPP500 test outcomes.",
            "30 dev tasks yield broad uncertainty; consider replication before strong conclusions.",
            "Pass@64 is a solved-task probability, not AST richness; C64 and D4 measure AST proxies.",
            "D4 is conditional on >=4 observed correct completions; eligible-task counts may differ.",
            "Finite-sample missing correct paths do not prove loss of support.",
            "This does not estimate complete-trajectory KL or justify a multi-round TV bound.",
            "Stage data share decoding settings and RNG seed material, not identical continuations.",
        ],
    }


def collect_round_report(directory: str | Path, reference_nll: dict, *,
                         seed: int, bootstrap_samples: int = 2000) -> dict:
    from .utils import atomic_json
    directory = Path(directory)
    summaries = {}
    for role in ROLES:
        path = directory / role / "evaluation.metrics.json"
        if not (directory / role / "complete.json").is_file():
            raise ValueError(f"Missing sealed transfer-gap {role} policy state")
        summaries[role] = json.loads(path.read_text())
    result = compare_three_states(summaries, seed=seed, bootstrap_samples=bootstrap_samples)
    result["reference_nll"] = reference_nll
    atomic_json(directory / "report.json", result)
    return result
