Warning: truncated output (original token count: 18077)
Total output lines: 1332

"""Independent continual calibration of shared spectral gains.

Only run_continual_gain_study imports model dependencies. The configuration
validator and saved-artifact summary use the standard library. Historical text
studies, their configs, and their output directories are never modified.
"""
from __future__ import annotations

from collections import Counter
from contextlib import contextmanager, nullcontext
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import gc
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from uuid import uuid4

PROTOCOL = "spectrum-continual-gains-v1"
METHODS = ("native", "sequential", "retention", "conflict")
DOMAINS = ("math", "qa")
REPO = Path(__file__).resolve().parents[2]
MODEL_SUFFIXES = {".safetensors", ".bin", ".json", ".txt", ".model", ".jinja"}
CORE_KEYS = {
    "max_steps", "learning_rate", "min_gain", "kl_budget", "max_backtracks",
    "backtrack_factor", "min_improvement", "guard_tolerance", "degeneracy_rtol",
    "degeneracy_atol", "kl_chunk_tokens", "retention_tolerance",
    "projection_max_cycles", "projection_tolerance",
}


def _path(value):
    path = Path(value).expanduser()
    return (path if path.is_absolute() else REPO / path).resolve()


def _sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            result.update(block)
    return result.hexdigest()


def _digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"),
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def _rows(path):
    with Path(path).open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if line.strip():
                value = json.loads(line, parse_constant=lambda item: (
                    _ for _ in ()).throw(ValueError(item)))
                if not isinstance(value, dict):
                    raise ValueError(f"Non-object record at {path}:{number}")
                yield value


def _write_once_json(path, value):
    """Publish atomically and never replace a previously frozen object."""
    path = Path(path)
    body = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                       allow_nan=False) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.is_symlink() or path.read_bytes() != body:
                raise ValueError(f"Frozen object differs; use a fresh lineage: {path}")
    finally:
        temporary.unlink(missing_ok=True)


def _nonoverlap(first, second):
    first, second = _path(first), _path(second)
    if first == second or first.is_relative_to(second) or second.is_relative_to(first):
        raise ValueError(f"Source and output directories overlap: {first}, {second}")


def _tree_files(directory, *, omit=()):
    directory = Path(directory)
    files = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Output artifacts cannot be symlinks: {path}")
        if path.is_file():
            relative = path.relative_to(directory).as_posix()
            if relative not in set(omit):
                if path.name.startswith(".") and path.name.endswith(".tmp"):
                    raise ValueError(f"Uncommitted temporary artifact: {path}")
                files[relative] = _sha(path)
    return files


def _validate_files(directory, files, *, inventory=False, omit=()):
    directory = Path(directory)
    if not isinstance(files, dict) or not files:
        raise ValueError(f"Missing nonempty file inventory: {directory}")
    for name, expected in files.items():
        relative = PurePosixPath(name)
        path = directory / name
        if (relative.is_absolute() or ".." in relative.parts
                or not re.fullmatch(r"[0-9a-f]{64}", str(expected))
                or path.is_symlink() or not path.is_file()
                or not path.resolve().is_relative_to(directory.resolve())
                or _sha(path) != expected):
            raise ValueError(f"Sealed artifact changed or escaped its root: {path}")
    if inventory and _tree_files(directory, omit=omit) != files:
        raise ValueError(f"Sealed file inventory changed: {directory}")


def _seal(directory, binding, extra=None):
    directory = Path(directory)
    receipt = {"schema": 1, "status": "completed", "binding": binding,
               "binding_sha256": _digest(binding),
               "files": _tree_files(directory, omit=("complete.json",))}
    if extra:
        if set(extra).intersection(receipt):
            raise ValueError("Receipt extras cannot replace integrity fields")
        receipt.update(extra)
    _write_once_json(directory / "complete.json", receipt)
    return receipt


def _read_seal(directory, binding=None):
    directory = Path(directory)
    marker = directory / "complete.json"
    if not marker.exists():
        return None
    value = _json(marker)
    if (value.get("schema") != 1 or value.get("status") != "completed"
            or _digest(value.get("binding")) != value.get("binding_sha256")
            or (binding is not None and value.get("binding") != binding)):
        raise ValueError(f"Completed stage has another binding: {directory}")
    _validate_files(directory, value.get("files"), inventory=True, omit=("complete.json",))
    return value


@contextmanager
def _exclusive(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(f"Another process owns this lineage: {path}") from error
        os.ftruncate(descriptor, 0)
        os.write(descriptor, json.dumps({
            "pid": os.getpid(), "acquired_at": datetime.now(timezone.utc).isoformat(),
        }).encode())
        os.fsync(descriptor)
        yield descriptor
    finally:
        # Closing the last open descriptor releases the OS lock. Keep its inode.
        os.close(descriptor)


def validate_continual_config(config):
    """Validate the bounded two-domain protocol without importing model code."""
    if not isinstance(config, dict) or config.get("protocol") != PROTOCOL:
        raise ValueError(f"Expected protocol {PROTOCOL}")
    if set(config.get("domains", {})) != set(DOMAINS):
        raise ValueError("Provide complete math and qa configurations")
    if config.get("order") not in (["math", "qa"], ["qa", "math"]):
        raise ValueError("Order must contain math and qa exactly once")
    if config.get("backbone_update") not in ("frozen", "self_distill"):
        raise ValueError("backbone_update must be frozen or self_distill")
    if type(config.get("rounds_per_domain")) is not int or config["rounds_per_domain"] < 1:
        raise ValueError("rounds_per_domain must be a positive integer")
    if not isinstance(config.get("output_dir"), str) or not config["output_dir"]:
        raise ValueError("An independent output_dir is required")
    if not isinstance(config.get("seed_file"), str) or not config["seed_file"]:
        raise ValueError("Use the existing prepared-data seed_file")
    controller = config.get("controller", {})
    if not isinstance(controller, dict) or set(controller) - CORE_KEYS:
        raise ValueError("Unknown continual controller settings")
    for key, value in controller.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"Controller setting must be finite numeric: {key}")
    for domain in DOMAINS:
        item = config["domains"][domain]
        if not isinstance(item, dict) or item.get("domain") != domain:
            raise ValueError("Embedded text-domain configuration has the wrong domain")
        if _path(item["seed_file"]) != _path(config["seed_file"]):
            raise ValueError("Both prepared domains must use the selected private seed file")
        if item.get("include_gpqa", False):
            raise ValueError("This protocol uses MMLU-Pro only; GPQA is a separate experiment")
        data, calibration = item["data"], item["calibration"]
        if any(data.get(key) != expected for key, expected in (
                ("train_size", 1024), ("calibration_size", 64), ("validation_size", 64))):
            raise ValueError("Preserve full prepared 1024/64/64 training-side splits")
        gains = calibration.get("gain_learning", {})
        if (calibration.get("max_examples") != 64 or gains.get("guard_examples", 10) != 10
                or calibration.get("matched_reference_fit_examples") != 54):
            raise ValueError("Each domain uses exactly 54 FIT and 10 final-veto guard references")
        if calibration.get("span_mode", "completion") != "completion":
            raise ValueError("Use the native completion-reference calibration targets")
        evaluation = item["evaluation"]
        task_ids = evaluation.get("task_ids")
        if task_ids is None:
            if evaluation["samples"] != (16 if domain == "math" else 1):
                raise ValueError("Native populations require MATH500 x16 and MMLU-Pro x1")
        elif (evaluation.get("profile") != "matched_pilot_v1"
              or evaluation.get("samples") != 1
              or not isinstance(task_ids, lis…13077 tokens truncated…_exits, "evaluation_sampling_round": 0,
        })
    report = summarize_continual_gain_study(config)
    return {"status": "completed", "method": method, "output_dir": str(method_root),
            "stages": completed, "report": report}


def summarize_continual_gain_study(config):
    """Read and verify saved evidence without importing a model dependency.

    Complete refers only to the methods actually started in this isolated root.
    Unstarted methods are not silently required or reported as successful. The
    report keeps native and controlled results separate; a negative final-minus-
    exit delta is an observed decline, not a calibration constraint guarantee.
    Full per-task data remain in the sealed metrics/response files.
    """
    validate_continual_config(config)
    root = _path(config["output_dir"])
    result = {
        "schema": 1, "protocol": PROTOCOL, "output_dir": str(root),
        "status": "unstarted", "backbone_update": config["backbone_update"],
        "order": list(config["order"]), "rounds_per_domain": config["rounds_per_domain"],
        "evaluation_sampling_round": 0, "methods": {},
        "uncertainty": "one trajectory; no training-seed variability estimate",
        "retention_interpretation": (
            "old FIT limits fixed at domain exit; test retention is measured separately"
            if config["backbone_update"] == "frozen" else
            "entry-relative gain constraints do not guarantee post-SFT or lifelong retention"),
    }
    manifest_path = root / "study_manifest.json"
    if not manifest_path.exists():
        if root.exists() and any(path.name != ".study.lock" for path in root.iterdir()):
            result.update(status="incomplete", reason="artifacts_without_study_manifest")
        return result
    binding = _json(manifest_path)
    if (binding.get("schema") != 1 or binding.get("protocol") != PROTOCOL
            or binding.get("config") != config
            or binding.get("config_sha256") != _digest(config)):
        raise ValueError("Report configuration differs from the sealed study")
    _assert_external(binding)
    context = {"binding": binding}
    schedule = stage_schedule(config)
    result["study_manifest_sha256"] = _sha(manifest_path)
    result["study_sha256"] = _digest(binding)
    result["runtime"] = binding["runtime"]
    for method in METHODS:
        method_root = root / method
        if not method_root.exists():
            continue
        if method_root.is_symlink():
            raise ValueError("A method output cannot alias another lineage")
        item = {"status": "incomplete", "output_dir": str(method_root),
                "completed_stages": [], "accuracy_matrix": [], "backward_changes": []}
        result["methods"][method] = item
        method_manifest = method_root / "manifest.json"
        if not method_manifest.exists():
            item["reason"] = "missing_method_manifest"
            continue
        expected_manifest = {"schema": 1, "method": method,
                             "study_sha256": _digest(binding), "output_dir": str(method_root)}
        if _json(method_manifest) != expected_manifest:
            raise ValueError("Report method manifest belongs to another study")
        geometry_dir = method_root / "geometry"
        geometry_seal = _read_seal(geometry_dir)
        if geometry_seal is None:
            item["reason"] = "geometry_not_committed"
            if (method_root / "run_complete.json").exists():
                raise ValueError("Run completion exists without its committed geometry")
            continue
        metadata = _json(geometry_dir / "metadata.json")
        geometry_binding = geometry_seal["binding"]
        first_domain = config["order"][0]
        if (metadata.get("binding") != geometry_binding
                or geometry_binding.get("source_domain") != first_domain
                or geometry_binding.get("fit_task_ids") != binding["data"][first_domain]["fit_task_ids"]
                or geometry_binding.get("base_checkpoint_identity") != binding["base_model"]["identity"]):
            raise ValueError("Reported geometry has another first-domain FIT source")
        geometry = {"receipt_sha256": _sha(geometry_dir / "complete.json"), "metadata": metadata}
        state = _validate_gain_values(metadata["initial_state"], metadata,
                                      binding["effective_controller"]["min_gain"])
        if not _identity_state(state):
            raise ValueError("Reported initial gains must be identity")
        checkpoint = {"path": binding["base_model"]["path"],
                      "identity": binding["base_model"]["identity"]}
        memory_exits, previous_receipt, completion_entries = {}, None, []
        stage_evaluations = {}
        for stage_info in schedule:
            stage = method_root / stage_info["name"]
            stage_binding = _stage_binding(config, binding, stage_info, checkpoint, state,
                                           previous_receipt, memory_exits, geometry, method)
            inspected = _inspect_stage(config, context, stage, stage_binding, geometry,
                                       state, memory_exits, method)
            if inspected is None:
                item["reason"] = "stage_not_committed"
                item["next_stage"] = stage_info
                item["partial_artifacts"] = {
                    "controller_receipt_present": (stage / "controller/complete.json").is_file(),
                    "checkpoint_receipt_present": (stage / "checkpoint.json").is_file(),
                    "presence_is_not_completion": True,
                }
                break
            state, checkpoint, memory_exits = (inspected[key] for key in
                                               ("state", "checkpoint", "memory_exits"))
            previous_receipt = _sha(stage / "complete.json")
            entry = {"stage": stage_info, "receipt_sha256": previous_receipt,
                     "checkpoint_identity": checkpoint["identity"],
                     "gain_state_sha256": _digest(state)}
            completion_entries.append(entry)
            audit = _json(stage / "controller/audit.json")
            item["completed_stages"].append({
                **entry, "controller_audit": str(stage / "controller/audit.json"),
                "selected_incoming": audit.get("selected_incoming"),
                "accepted_steps": audit.get("accepted_steps"),
                "fallback_reason": audit.get("fallback_reason"),
                "projection_stats": audit.get("projection_stats"),
                "selected_retention_feasible": audit.get("selected_retention_feasible"),
                "resource_files": [str(path) for path in sorted(stage.rglob("*.resources.json"))],
                "reference_losses": str(stage / "reference_losses.json"),
            })
            stage_evaluations[stage_info["index"]] = inspected["evaluations"]
            for domain in DOMAINS:
                benchmark = "math500" if domain == "math" else "mmlu_pro"
                for role in ("native", "controlled"):
                    metrics = inspected["evaluations"][domain][role][benchmark]
                    compact = {key: value for key, value in metrics.items()
                               if not key.startswith("per_task_") and not isinstance(value, (dict, list))}
                    item["accuracy_matrix"].append({
                        "stage": stage_info["index"], "learned_domain": stage_info["domain"],
                        "domain_round": stage_info["round"], "evaluated_domain": domain,
                        "policy": role, "benchmark": benchmark, "metrics": compact,
                        "metrics_file": str(stage / "evaluation" / domain / role / "metrics.json"),
                    })
        completion_path = method_root / "run_complete.json"
        all_stages = len(completion_entries) == len(schedule)
        if completion_path.exists():
            expected = {"schema": 1, "status": "completed", "study_sha256": _digest(binding),
                        "method": method, "stages": completion_entries,
                        "last_checkpoint": checkpoint, "last_gain_state_sha256": _digest(state),
                        "memory_exits": memory_exits, "evaluation_sampling_round": 0}
            if not all_stages or _json(completion_path) != expected:
                raise ValueError("Run completion disagrees with the verified stage chain")
            item["status"] = "complete"
            item["run_complete_sha256"] = _sha(completion_path)
        elif all_stages:
            item["reason"] = "stages_complete_but_run_receipt_missing; resume_to_commit"
        if all_stages:
            final_index = schedule[-1]["index"]
            for domain in config["order"][:-1]:
                exit_index = memory_exits[domain]["exit_stage"]
                benchmark = "math500" if domain == "math" else "mmlu_pro"
                for role in ("native", "controlled"):
                    before = stage_evaluations[exit_index][domain][role][benchmark]["accuracy"]
                    after = stage_evaluations[final_index][domain][role][benchmark]["accuracy"]
                    item["backward_changes"].append({
                        "domain": domain, "policy": role, "exit_stage": exit_index,
                        "final_stage": final_index, "exit_accuracy": before, "final_accuracy": after,
                        "delta_final_minus_exit": after - before,
                        "negative_means": "observed_old_domain_accuracy_decline",
                    })
            item["final_gain_state_sha256"] = _digest(state)
            item["final_checkpoint"] = checkpoint
            item["memory_exits"] = memory_exits
    if result["methods"]:
        result["status"] = ("complete" if all(item["status"] == "complete"
                                             for item in result["methods"].values()) else "incomplete")
    return result
