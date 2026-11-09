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
              or not isinstance(task_ids, list) or not task_ids
              or any(not isinstance(task_id, str) or not task_id for task_id in task_ids)
              or len(task_ids) != len(set(task_ids))):
            raise ValueError("Pilot evaluation requires the explicit one-sample matched-pilot profile and unique task_ids")
        for phase in ("synthesis", "evaluation"):
            spec = item[phase]
            for key in ("samples", "batch_size", "task_batch_size", "sequence_batch_size",
                        "max_new_tokens", "max_prompt_tokens"):
                if type(spec.get(key)) is not int or spec[key] < 1:
                    raise ValueError(f"Invalid {domain}.{phase}.{key}")
        train = item["train"]
        if (train.get("loss_scope") != "completion" or train.get("fixed_anchor_replay", False)
                or train.get("token_loss_reweighting", False)
                or float(train.get("lora_update_scale", 1)) != 1):
            raise ValueError("Use ordinary completion-target LoRA SFT on current-domain raw samples")
        if train["max_length"] < item["synthesis"]["max_prompt_tokens"] + item["synthesis"]["max_new_tokens"]:
            raise ValueError("Training context must retain every generated completion target")
        _nonoverlap(config["output_dir"], data["output_dir"])
    first, second = (config["domains"][domain] for domain in DOMAINS)
    if first["model"] != second["model"]:
        raise ValueError("One shared backbone, loader and tokenizer configuration is required")
    if first["calibration"].get("layers") != second["calibration"].get("layers"):
        raise ValueError("Fixed geometry requires the same exact K/V target layers")
    if first["calibration"]["gain_learning"] != second["calibration"]["gain_learning"]:
        raise ValueError("Match gain solver and probe budgets between domains")
    _nonoverlap(config["domains"]["math"]["data"]["output_dir"],
                config["domains"]["qa"]["data"]["output_dir"])
    return config


def stage_schedule(config):
    validate_continual_config(config)
    result = [{"index": 0, "domain": None, "round": 0, "name": "stage_000_baseline"}]
    for domain in config["order"]:
        for round_number in range(1, config["rounds_per_domain"] + 1):
            index = len(result)
            result.append({"index": index, "domain": domain, "round": round_number,
                           "name": f"stage_{index:03d}_{domain}_r{round_number}"})
    return result


def source_identity():
    """Freeze the executable source inventory, including controller and launchers."""
    files = set()
    for directory in ("src", "scripts"):
        files.update(path for path in (REPO / directory).rglob("*.py") if path.is_file())
    files.update(path for path in REPO.glob("requirements*.txt") if path.is_file())
    if (REPO / "pyproject.toml").is_file():
        files.add(REPO / "pyproject.toml")
    return {path.relative_to(REPO).as_posix(): _sha(path) for path in sorted(files)}


def _model_files(path):
    path = Path(path)
    files = {item.name: _sha(item) for item in sorted(path.iterdir())
             if item.is_file() and item.suffix in MODEL_SUFFIXES
             and item.name != "training_stats.json"}
    if "config.json" not in files or not any(name.endswith((".safetensors", ".bin")) for name in files):
        raise ValueError(f"Full native model weights and config are required: {path}")
    for name in files:
        if name.endswith(".index.json"):
            index = _json(path / name)
            for shard in set(index.get("weight_map", {}).values()):
                if shard not in files:
                    raise ValueError(f"Missing checkpoint shard {shard}: {path}")
    return files


def _base_model_binding(settings):
    path = _path(settings["name"])
    if not path.is_dir():
        if Path(settings["name"]).is_absolute() or not re.fullmatch(
                r"[0-9a-f]{40}", str(settings.get("revision", ""))):
            raise FileNotFoundError("Prepare the complete local model snapshot before running")
        from huggingface_hub import snapshot_download
        path = Path(snapshot_download(repo_id=settings["name"],
                                     revision=settings["revision"], local_files_only=True)).resolve()
    files = _model_files(path)
    return {"path": str(path), "files": files, "identity": _digest(files)}


def _assert_external(binding, *, model=True):
    if source_identity() != binding["source_files"]:
        raise ValueError("Executable source changed; resume only at the frozen revision")
    for filename, checksum in binding["external_files"].items():
        if not Path(filename).is_file() or _sha(filename) != checksum:
            raise ValueError(f"Prepared input or private seed changed: {filename}")
    if model:
        base = binding["base_model"]
        if _model_files(Path(base["path"])) != base["files"]:
            raise ValueError("Original base model/tokenizer changed")


def _prepare_inputs(config):
    """Resolve and seal existing prepared inputs; never acquire data."""
    from .data import assert_disjoint_splits
    from .gain_pipeline import split_gain_settings, split_gain_references
    from .continual_gains import validate_continual_settings
    from .text_tasks import private_seed, verify_prepared_data
    from .text_study import validate_text_config, validate_prepared_binding, _binding, _preflight_math
    seed = private_seed(_path(config["seed_file"]))
    domains, external, data_binding, runtime = {}, {}, {}, {}
    external[str(_path(config["seed_file"]))] = _sha(_path(config["seed_file"]))
    combined = {name: [] for name in ("train", "calibration", "validation", "eval")}
    effective_core = None
    for domain in DOMAINS:
        cfg = config["domains"][domain]
        validate_text_config(cfg)
        root = _path(cfg["data"]["output_dir"])
        splits, manifest = verify_prepared_data(root)
        validate_prepared_binding(cfg, manifest, seed)
        fit, guard = split_gain_references(splits["calibration"], cfg["calibration"])
        if len(fit) != 54 or len(guard) != 10:
            raise ValueError("Prepared reference population differs from the declared 54/10 split")
        core, integration = split_gain_settings(cfg["calibration"])
        core.update(config.get("controller", {}))
        core = validate_continual_settings(core)
        if effective_core is not None and core != effective_core:
            raise ValueError("Controller settings differ between domains")
        effective_core = core
        runtime_cfg = deepcopy(cfg)
        runtime_cfg["data"]["output_dir"] = str(root)
        _preflight_math(runtime_cfg)
        domain_runtime = _binding(cfg, manifest, seed)
        runtime[domain] = {key: value for key, value in domain_runtime.items()
                           if key in ("runtime", "scorer_dependencies", "scoring_runtime")}
        files = {str(root / "manifest.json"): _sha(root / "manifest.json")}
        for name, expected in manifest["output_hashes"].items():
            target = (root / name).resolve()
            if not target.is_relative_to(root) or _sha(target) != expected:
                raise ValueError("Prepared data path or checksum changed")
            files[str(target)] = expected
        if domain == "math":
            for name in ("grader.py", "math_normalize.py"):
                path = root / "sources/prm800k/prm800k/grading" / name
                files[str(path)] = _sha(path)
        external.update(files)
        data_binding[domain] = {
            "manifest_sha256": files[str(root / "manifest.json")],
            "files": files, "counts": manifest["counts"],
            "evaluation_counts": manifest["evaluation_counts"],
            "task_ids": {name: [row["task_id"] for row in rows] for name, rows in splits.items()},
            "fit_task_ids": [row["task_id"] for row in fit],
            "guard_task_ids": [row["task_id"] for row in guard],
        }
        domains[domain] = {"config": runtime_cfg, "splits": splits, "fit": fit, "guard": guard,
                           "core": core, "integration": integration}
        for split in combined:
            combined[split].extend(splits[split])
    assert_disjoint_splits(combined)
    base = _base_model_binding(config["domains"][config["order"][0]]["model"])
    _nonoverlap(config["output_dir"], base["path"])
    binding = {"schema": 1, "protocol": PROTOCOL, "config": config,
               "config_sha256": _digest(config), "seed_sha256": _digest(seed),
               "source_files": source_identity(), "external_files": external,
               "data": data_binding, "base_model": base, "runtime": runtime,
               "effective_controller": effective_core, "checkpoint_retention": "all",
               "geometry_policy": "first_domain_fit_only_once",
               "guard_policy": "current_guard_final_veto_only; old_guards_diagnostic_only",
               "memory_policy": "seen_domain_fit_only; never_student_sft"}
    return {"seed": seed, "domains": domains, "binding": binding, "base_model": base}


def _check_checkpoint(stage, stage_binding, selection_sha256):
    """A committed checkpoint is sufficient to skip generation and SFT on resume."""
    stage = Path(stage)
    receipt_path, model_path = stage / "checkpoint.json", stage / "model"
    if not receipt_path.exists():
        if model_path.exists() or any(stage.glob(".model.saving-*")):
            raise ValueError("Uncommitted checkpoint exists; preserve it and reconcile the interrupted save")
        return None
    value = _json(receipt_path)
    if (value.get("schema") != 1 or value.get("stage_binding_sha256") != _digest(stage_binding)
            or value.get("selection_sha256") != selection_sha256
            or value.get("parent_checkpoint_identity") != stage_binding["incoming_checkpoint"]["identity"]):
        raise ValueError("Committed checkpoint has another parent or gain selection")
    _validate_files(model_path, value.get("files"), inventory=True)
    if _digest(_model_files(model_path)) != value.get("checkpoint_identity"):
        raise ValueError("Committed student model identity changed")
    bound_files = {
        "synthetic.jsonl": "synthetic_sha256",
        "synthetic.receipt.json": "synthetic_receipt_sha256",
        "effective_train.json": "effective_train_sha256",
        "training_stats.json": "stage_training_stats_sha256",
        "model/training_stats.json": "training_stats_sha256",
    }
    if any(_sha(stage / name) != value.get(key) for name, key in bound_files.items()):
        raise ValueError("Checkpoint training inputs, provenance or statistics changed")
    if _json(stage / "training_stats.json") != _json(model_path / "training_stats.json"):
        raise ValueError("Checkpoint and stage training statistics disagree")
    synthesis = _json(stage / "synthetic.receipt.json")
    if (synthesis.get("schema") != 1
            or synthesis.get("binding", {}).get("stage_binding_sha256") != _digest(stage_binding)
            or synthesis.get("binding", {}).get("selection_sha256") != selection_sha256):
        raise ValueError("Committed synthesis has another stage or controller")
    _validate_files(stage, synthesis.get("files"))
    return value


def _exact_records(path, task_ids, samples, *, scored=False):
    counts, seen = Counter(), set()
    expected = set(task_ids)
    for row in _rows(path):
        task, sample = row.get("task_id"), row.get("sample_id")
        if (task not in expected or type(sample) is not int or not 0 <= sample < samples
                or (task, sample) in seen or not isinstance(row.get("completion"), str)
                or (scored and type(row.get("correct")) is not bool)):
            raise ValueError(f"Invalid, duplicate or out-of-budget record: {path}")
        counts[task] += 1
        seen.add((task, sample))
    if set(counts) != expected or any(counts[task] != samples for task in expected):
        raise ValueError(f"Missing full native task/sample population: {path}")


def _select_evaluation_rows(evaluation, rows):
    requested = evaluation.get("task_ids")
    if requested is None:
        return list(rows)
    if (not isinstance(requested, list) or not requested
            or any(not isinstance(task_id, str) or not task_id for task_id in requested)
            or len(requested) != len(set(requested))):
        raise ValueError("Evaluation task_ids must be nonempty, valid and unique")
    by_id = {row.get("task_id"): row for row in rows}
    missing = [task_id for task_id in requested if task_id not in by_id]
    if missing:
        raise ValueError(f"Evaluation subset contains unknown task IDs: {missing[:3]}")
    return [by_id[task_id] for task_id in requested]


def _evaluation_task_ids(config, domain, available):
    requested = config["domains"][domain]["evaluation"].get("task_ids")
    if requested is None:
        return list(available)
    if not isinstance(requested, list) or len(requested) != len(set(requested)):
        raise ValueError("Evaluation task_ids must be unique")
    unknown = set(requested) - set(available)
    if unknown:
        raise ValueError(f"Evaluation subset contains unknown task IDs: {sorted(unknown)[:3]}")
    return list(requested)


def _verify_evaluation(directory, domain, task_ids, samples=None):
    benchmark, default_samples = ("math500", 16) if domain == "math" else ("mmlu_pro", 1)
    samples = default_samples if samples is None else samples
    metrics = _json(Path(directory) / "metrics.json")
    if set(metrics) != {benchmark}:
        raise ValueError("Evaluation contains another benchmark population")
    value = metrics[benchmark]
    if (value.get("tasks") != len(task_ids) or value.get("samples") != len(task_ids) * samples
            or value.get("samples_per_task") != samples
            or set(value.get("per_task_accuracy", {})) != set(task_ids)):
        raise ValueError("Evaluation metric denominator differs from the complete native population")
    _exact_records(Path(directory) / "evaluation.jsonl", task_ids, samples)
    _exact_records(Path(directory) / "evaluation.scored.jsonl", task_ids, samples, scored=True)
    return metrics


def _load_model(config, checkpoint):
    from .modeling import load_model
    return load_model(config["domains"][config["order"][0]]["model"], Path(checkpoint))


def _release():
    import torch
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _state_json(state):
    return {name: (list(value) if isinstance(value, list)
                   else value.detach().to(device="cpu").double().tolist())
            for name, value in sorted(state.items())}


def _validate_gain_values(value, metadata, minimum):
    if set(value) != set(metadata["modules"]):
        raise ValueError("Gain state modules differ from the immutable geometry")
    result = {}
    for name, record in metadata["modules"].items():
        gains = value[name]
        if (not isinstance(gains, list) or len(gains) != record["gain_parameters"]
                or any(isinstance(item, bool) or not isinstance(item, (int, float))
                       or not math.isfinite(item) or not minimum <= item <= 1 for item in gains)):
            raise ValueError(f"Gain state shape, finiteness or bounds changed: {name}")
        result[name] = list(gains)
    return result


def _state_tensors(value, metadata, minimum):
    import torch
    values = _validate_gain_values(value, metadata, minimum)
    return {name: torch.tensor(gains, dtype=torch.float64) for name, gains in values.items()}


def _operator_hashes(operators):
    return {name: hashlib.sha256(value.detach().to(device="cpu").double().contiguous()
                                 .numpy().tobytes()).hexdigest()
            for name, value in sorted(operators.items())}


def _identity_state(state):
    return all(all(value == 1.0 for value in gains) for gains in _state_json(state).values())


def _policy_context(model, operators, state):
    from .spectral import folded_operators
    return nullcontext() if _identity_state(state) else folded_operators(model, operators)


def _save_geometry_tensor(path, value):
    import torch
    path = Path(path)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            torch.save(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            raise FileExistsError(f"Geometry tensor is immutable: {path}")
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _geometry(config, context, method_root):
    import torch
    from .continual_gains import build_gain_geometry, identity_gain_state, operators_from_gain_state
    from .pipeline import _calibrate, record_stage
    first_domain = config["order"][0]
    item = context["domains"][first_domain]
    directory = Path(method_root) / "geometry"
    binding = {
        "schema": 1, "source_domain": first_domain,
        "base_checkpoint_identity": context["base_model"]["identity"],
        "fit_task_ids": [task["task_id"] for task in item["fit"]],
        "fit_records_sha256": _digest(item["fit"]),
        "calibration": item["config"]["calibration"],
        "core_settings": item["core"],
        "source_files": context["binding"]["source_files"],
        "policy": "first_domain_fit_only_once; frozen_for_entire_lineage",
    }
    receipt = _read_seal(directory, binding)
    if receipt is None:
        if directory.exists() and any(directory.iterdir()):
            raise ValueError("Uncommitted geometry exists; preserve it and reconcile before resume")
        directory.mkdir(parents=True, exist_ok=True)
        model = tokenizer = None
        try:
            with record_stage(directory, "model_loading"):
                model, tokenizer = _load_model(config, context["base_model"]["path"])
            calibration = {**item["config"]["calibration"], "max_examples": len(item["fit"])}
            with record_stage(directory, "calibration"):
                covariances = _calibrate(
                    model, tokenizer, item["fit"], calibration,
                    directory / "calibration.pt", context["base_model"]["identity"])
            with record_stage(directory, "geometry"):
                geometry = build_gain_geometry(model, covariances, settings=item["core"])
                initial = identity_gain_state(geometry)
                operators_from_gain_state(geometry, initial)
            metadata = {
                "schema": 1, "binding": binding,
                "modules": {name: {"output_dimension": int(record["basis"].shape[0]),
                                   "gain_parameters": int(record["group_ids"].max()) + 1}
                            for name, record in geometry.items()},
                "initial_state": _state_json(initial),
            }
            _save_geometry_tensor(directory / "geometry.pt",
                                  {"schema": 1, "binding": binding, "modules": geometry})
            _write_once_json(directory / "metadata.json", metadata)
            receipt = _seal(directory, binding)
        finally:
            del model, tokenizer
            _release()
    artifact = torch.load(directory / "geometry.pt", map_location="cpu", weights_only=True)
    if artifact.get("schema") != 1 or artifact.get("binding") != binding:
        raise ValueError("Geometry tensor belongs to another first-domain calibration")
    geometry = artifact["modules"]
    metadata = _json(directory / "metadata.json")
    if metadata.get("binding") != binding:
        raise ValueError("Geometry metadata binding differs")
    initial = _state_tensors(metadata["initial_state"], metadata, item["core"]["min_gain"])
    operators_from_gain_state(geometry, initial)
    if not _identity_state(initial):
        raise ValueError("The lineage must start from identity gains")
    return {"modules": geometry, "metadata": metadata, "initial": initial,
            "receipt_sha256": _sha(directory / "complete.json"),
            "binding_sha256": receipt["binding_sha256"]}


def _controller_binding(context, stage_binding, geometry, incoming_state, memory_exits, method):
    domain = stage_binding["stage"]["domain"]
    data = context["binding"]["data"]
    return {
        "schema": 1, "stage_binding_sha256": _digest(stage_binding),
        "geometry_sha256": geometry["receipt_sha256"],
        "incoming_state_sha256": _digest(_state_json(incoming_state)),
        "method": method, "domain": domain,
        "settings": context["binding"]["effective_controller"],
        "fit_task_ids": data[domain]["fit_task_ids"] if domain else [],
        "guard_task_ids": data[domain]["guard_task_ids"] if domain else [],
        "memory_fit_task_ids": {old: data[old]["fit_task_ids"] for old in memory_exits},
        "retention_anchor": stage_binding["retention_anchor"],
        "frozen_exit_limits": {old: info["retention_limit"] for old, info in memory_exits.items()}
        if stage_binding["retention_anchor"] == "fixed_domain_exit" else None,
    }


def _read_selection(directory, binding, geometry, minimum):
    from .continual_gains import operators_from_gain_state
    directory = Path(directory)
    receipt = _read_seal(directory, binding)
    if receipt is None:
        if any((directory / name).exists() for name in ("gains.json", "audit.json", "selection.json")):
            raise ValueError("Uncommitted gain selection exists; preserve and reconcile it")
        return None
    state_value, audit, selection = (_json(directory / name)
                                    for name in ("gains.json", "audit.json", "selection.json"))
    state = _state_tensors(state_value, geometry["metadata"], minimum)
    operators = operators_from_gain_state(geometry["modules"], state)
    if (selection["state_sha256"] != _digest(state_value)
            or selection["geometry_sha256"] != geometry["receipt_sha256"]
            or selection["incoming_state_sha256"] != binding["incoming_state_sha256"]
            or selection["operators_sha256"] != _operator_hashes(operators)):
        raise ValueError("Selected gains or operators differ from their bound state")
    return state, operators, audit, _sha(directory / "complete.json")


def _select_controller(config, context, stage, stage_binding, geometry,
                       incoming_state, memory_exits, method, model, tokenizer, resume):
    from .continual_gains import fit_continual_operators, operators_from_gain_state
    from .gain_pipeline import reference_batches, probe_batches
    from .generation import generate_to_file
    from .pipeline import record_stage
    directory = Path(stage) / "controller"
    binding = _controller_binding(context, stage_binding, geometry, incoming_state, memory_exits, method)
    minimum = binding["settings"]["min_gain"]
    saved = _read_selection(directory, binding, geometry, minimum)
    if saved is not None:
        return saved
    _write_once_json(directory / "binding.json", binding)
    domain = stage_binding["stage"]["domain"]
    if domain is None or method == "native":
        state = incoming_state
        if not _identity_state(state):
            raise ValueError("Native and baseline states must have identity gains")
        operators = operators_from_gain_state(geometry["modules"], state)
        audit = {"method": "native" if domain else "baseline", "selected_incoming": True,
                 "controller_fitting_performed": False, "history": [],
                 "reference_diagnostics": "../reference_losses.json",
                 "guard_use": "diagnostic_only", "limits": binding["frozen_exit_limits"] or {}}
    else:
        item = context["domains"][domain]
        current_cfg = item["config"]
        fit = reference_batches(tokenizer, item["fit"], current_cfg["calibration"])
        guard = reference_batches(tokenizer, item["guard"], current_cfg["calibration"])
        memories = {
            old: reference_batches(tokenizer, context["domains"][old]["fit"],
                                   context["domains"][old]["config"]["calibration"])
            for old in memory_exits
        }
        count = item["integration"]["probe_examples"]
        if len(item["splits"]["train"]) < count:
            raise ValueError("Insufficient native training prompts for the declared probe")
        probe_tasks = [
            {key: task[key] for key in ("task_id", "prompt", "source", "split", "chat_template_kwargs")
             if key in task}
            for task in item["splits"]["train"][:count]
        ]
        reference_ids = {task["task_id"] for task in item["fit"] + item["guard"]}
        reference_ids.update(task["task_id"] for old in memory_exits
                             for task in context["domains"][old]["fit"])
        if reference_ids.intersection(task["task_id"] for task in probe_tasks):
            raise ValueError("Probe prompts overlap current or retained reference examples")
        generation = {
            "samples": 1, "batch_size": 1, "task_batch_size": 1, "sequence_batch_size": 1,
            "max_new_tokens": item["integration"]["probe_max_new_tokens"],
            "max_prompt_tokens": current_cfg["synthesis"]["max_prompt_tokens"],
            **{key: current_cfg["synthesis"][key] for key in ("temperature", "top_p", "top_k")},
        }
        # Native backbone prefixes, without reference answers or gain folding.
        with record_stage(directory, "native_probe"):
            records = generate_to_file(
                model, tokenizer, probe_tasks, directory / "probe.jsonl", generation,
                seed=context["seed"], model_identity=stage_binding["incoming_checkpoint"]["identity"],
                method="continual_native_probe", round_index=stage_binding["stage"]["index"],
                stage="continual_gain_probe", resume=resume)
        _exact_records(directory / "probe.jsonl", [task["task_id"] for task in probe_tasks], 1)
        probe = probe_batches(tokenizer, probe_tasks, records,
                              generation["max_prompt_tokens"] + generation["max_new_tokens"])
        encoded = {
            "fit": [{key: value.tolist() for key, value in batch.items()} for batch in fit],
            "guard": [{key: value.tolist() for key, value in batch.items()} for batch in guard],
            "probe": [{key: value.tolist() for key, value in batch.items()} for batch in probe],
            "memory_fit": {
                old: [{key: value.tolist() for key, value in batch.items()} for batch in batches]
                for old, batches in memories.items()
            },
            "probe_task_ids": [task["task_id"] for task in probe_tasks],
            "probe_sha256": _sha(directory / "probe.jsonl"),
        }
        _write_once_json(directory / "encoded_inputs.json", encoded)
        limits = binding["frozen_exit_limits"] if config["backbone_update"] == "frozen" else None
        with record_stage(directory, "controller_fitting"):
            operators, state, audit = fit_continual_operators(
                model, fit, guard, probe, geometry["modules"], initial_gains=incoming_state,
                retention_batches=memories, retention_limits=limits,
                mode=method, settings=item["core"])
        reconstructed = operators_from_gain_state(geometry["modules"], state)
        if _operator_hashes(reconstructed) != _operator_hashes(operators):
            raise ValueError("Controller returned operators inconsistent with its shared gains")
        if set(audit["selected"]["retention_nlls"]) != set(memories):
            raise ValueError("Controller omitted old-domain FIT diagnostics")
    state_value = _state_json(state)
    _state_tensors(state_value, geometry["metadata"], minimum)
    _write_once_json(directory / "gains.json", state_value)
    _write_once_json(directory / "audit.json", audit)
    _write_once_json(directory / "selection.json", {
        "schema": 1, "geometry_sha256": geometry["receipt_sha256"],
        "incoming_state_sha256": binding["incoming_state_sha256"],
        "state_sha256": _digest(state_value), "operators_sha256": _operator_hashes(operators),
        "controller_intervention": "shared_output_spectral_gains; ordinary_SFT_unchanged",
        "retention_anchor": binding["retention_anchor"],
        "old_guards_used_for_steps": False,
    })
    _seal(directory, binding)
    return state, operators, audit, _sha(directory / "complete.json")


def _reference_losses(context, domains, model, tokenizer, operators, state):
    from .gain_pipeline import reference_batches
    from .learned_gains import _examples, _mean_nll
    result = {}
    previous = [(module, module.training) for module in model.modules()]
    try:
        model.eval()
        for domain in domains:
            item = context["domains"][domain]
            batches = {role: _examples(reference_batches(
                tokenizer, item[role], item["config"]["calibration"]), role)
                for role in ("fit", "guard")}
            native = {f"{role}_nll": _mean_nll(model, examples) for role, examples in batches.items()}
            with _policy_context(model, operators, state):
                controlled = {f"{role}_nll": _mean_nll(model, examples)
                              for role, examples in batches.items()}
            result[domain] = {"native": native, "controlled": controlled,
                              "fit_task_ids": [task["task_id"] for task in item["fit"]],
                              "guard_task_ids": [task["task_id"] for task in item["guard"]],
                              "use": "measurement_only; never_candidate_selection"}
    finally:
        for module, training in previous:
            module.training = training
    return result


def _evaluation_binding(config, context, stage_binding, geometry, state,
                        checkpoint_identity, domain, role):
    """Build the same evaluation identity at execution and metadata inspection."""
    if domain not in DOMAINS or role not in ("native", "controlled"):
        raise ValueError("Unknown evaluation domain or policy")
    data = context["binding"]["data"][domain]
    policy = {"checkpoint_identity": checkpoint_identity, "role": role,
              "geometry_sha256": geometry["receipt_sha256"],
              "gain_state_sha256": _digest(_state_json(state)) if role == "controlled" else None}
    return {
        "schema": 1, "stage_binding_sha256": _digest(stage_binding),
        "domain": domain, "policy": policy, "policy_identity": _digest(policy),
        "task_ids": _evaluation_task_ids(
            config, domain, data["task_ids"]["eval"]),
        "task_file_sha256": data["files"][
            str(_path(config["domains"][domain]["data"]["output_dir"]) / "eval.jsonl")],
        "evaluation_settings": config["domains"][domain]["evaluation"],
        "seed_sha256": context["binding"]["seed_sha256"],
        "evaluation_sampling_round": 0,
    }


def _evaluation_rng_group(config, method, role, domain=None):
    domain = domain or config["order"][0]
    evaluation = config["domains"][domain]["evaluation"]
    if "task_ids" in evaluation:
        value = evaluation.get("rng_group", "continual_gain_pilot_shared")
        if not isinstance(value, str) or not value:
            raise ValueError("Pilot RNG group must be a nonempty string")
        return value
    return f"continual_{method}_{role}"


def _evaluate_all_domains(config, context, stage, stage_binding, geometry,
                          state, operators, model, tokenizer, checkpoint_identity,
                          method, resume):
    from .pipeline import record_stage
    from .text_study import _evaluate
    result = {}
    for domain in DOMAINS:
        item = context["domains"][domain]
        result[domain] = {}
        selected_rows = _select_evaluation_rows(
            item["config"]["evaluation"], item["splits"]["eval"])
        task_ids = [task["task_id"] for task in selected_rows]
        samples = item["config"]["evaluation"]["samples"]
        for role in ("native", "controlled"):
            directory = Path(stage) / "evaluation" / domain / role
            binding = _evaluation_binding(
                config, context, stage_binding, geometry, state, checkpoint_identity, domain, role)
            if _read_seal(directory, binding) is None:
                _write_once_json(directory / "binding.json", binding)
                with record_stage(directory, "whole_policy_evaluation"):
                    with (_policy_context(model, operators, state) if role == "controlled" else nullcontext()):
                        _evaluate(
                            item["config"], model, tokenizer, selected_rows, directory,
                            binding["policy_identity"], context["seed"],
                            _evaluation_rng_group(config, method, role, domain), 0, resume)
                _verify_evaluation(directory, domain, task_ids, samples)
                _seal(directory, binding)
            result[domain][role] = _verify_evaluation(directory, domain, task_ids, samples)
    return result


def _stage_binding(config, binding, stage_info, checkpoint, incoming_state,
                   previous_receipt, memory_exits, geometry, method):
    return {
        "schema": 1, "study_sha256": _digest(binding), "method": method,
        "stage": stage_info, "geometry_sha256": geometry["receipt_sha256"],
        "incoming_checkpoint": checkpoint, "incoming_state_sha256": _digest(_state_json(incoming_state)),
        "previous_stage_receipt_sha256": previous_receipt, "memory_exits": memory_exits,
        "backbone_update": config["backbone_update"],
        "retention_anchor": ("fixed_domain_exit" if config["backbone_update"] == "frozen"
                             else "current_backbone_incoming_controller_at_calibration_entry"),
        "evaluation_sampling_round": 0,
    }


def _next_memory(config, stage_info, previous, reference_losses, audit, state_value):
    result = deepcopy(previous)
    domain = stage_info["domain"]
    if domain is None or stage_info["round"] != config["rounds_per_domain"]:
        return result
    if domain in result:
        raise ValueError("A domain exit cannot overwrite its original retention anchor")
    post_fit = reference_losses[domain]["controlled"]["fit_nll"]
    selected_fit = audit.get("selected", {}).get("fit_nll", post_fit)
    if any(isinstance(value, bool) or not isinstance(value, (int, float))
           or not math.isfinite(value) or value < 0 for value in (post_fit, selected_fit)):
        raise ValueError("Domain exit requires finite measured reference NLL")
    tolerance = float(config.get("controller", {}).get("retention_tolerance", 0.0))
    result[domain] = {
        "exit_stage": stage_info["index"],
        "fit_task_ids": reference_losses[domain]["fit_task_ids"],
        "gain_state_sha256": _digest(state_value),
        "selected_fit_nll_before_sft": selected_fit,
        "controlled_fit_nll_at_exit": post_fit,
        "retention_limit": (selected_fit + tolerance
                            if config["backbone_update"] == "frozen" else None),
        "limit_policy": ("fixed_domain_exit_selected_fit_plus_tolerance"
                         if config["backbone_update"] == "frozen" else
                         "remeasure_each_calibration_entry_on_current_backbone"),
    }
    return result


def _inspect_stage(config, context, stage, stage_binding, geometry,
                   incoming_state, memory_exits, method):
    """Verify a completed stage using only JSON, file hashes and native records."""
    stage = Path(stage)
    complete = _read_seal(stage, stage_binding)
    if complete is None:
        return None
    controller_binding = _controller_binding(
        context, stage_binding, geometry, incoming_state, memory_exits, method)
    controller = _read_seal(stage / "controller", controller_binding)
    if controller is None:
        raise ValueError("Completed stage lacks a sealed controller")
    state = _validate_gain_values(_json(stage / "controller/gains.json"), geometry["metadata"],
                                 context["binding"]["effective_controller"]["min_gain"])
    if (method == "native" or stage_binding["stage"]["domain"] is None) and not _identity_state(state):
        raise ValueError("Native and baseline stages must retain identity gains")
    selection = _json(stage / "controller/selection.json")
    selection_sha = _sha(stage / "controller/complete.json")
    if (selection.get("state_sha256") != _digest(state)
            or selection.get("incoming_state_sha256") != stage_binding["incoming_state_sha256"]
            or selection.get("geometry_sha256") != geometry["receipt_sha256"]
            or complete.get("gain_state_sha256") != _digest(state)
            or complete.get("controller_complete_sha256") != selection_sha):
        raise ValueError("Completed stage gain inheritance changed")
    trained = config["backbone_update"] == "self_distill" and stage_binding["stage"]["index"] > 0
    if trained:
        checkpoint_receipt = _check_checkpoint(stage, stage_binding, selection_sha)
        if checkpoint_receipt is None:
            raise ValueError("Completed self-distillation stage lacks a committed checkpoint")
        checkpoint = {"path": str(stage / "model"),
                      "identity": checkpoint_receipt["checkpoint_identity"]}
    else:
        if (stage / "model").exists() or (stage / "checkpoint.json").exists():
            raise ValueError("Frozen/baseline stage unexpectedly contains a student update")
        checkpoint = stage_binding["incoming_checkpoint"]
    if complete.get("output_checkpoint") != checkpoint:
        raise ValueError("Completed stage checkpoint chain changed")
    audit = _json(stage / "controller/audit.json")
    reference_losses = _json(stage / "reference_losses.json")
    expected_domains = list(memory_exits)
    current = stage_binding["stage"]["domain"]
    if current and current not in expected_domains:
        expected_domains.append(current)
    if set(reference_losses) != set(expected_domains):
        raise ValueError("Reference diagnostic domains differ from the seen-domain history")
    for domain, measured in reference_losses.items():
        if (measured.get("fit_task_ids") != context["binding"]["data"][domain]["fit_task_ids"]
                or measured.get("guard_task_ids") != context["binding"]["data"][domain]["guard_task_ids"]):
            raise ValueError("Reference diagnostic population changed")
        for role in ("native", "controlled"):
            for key in ("fit_nll", "guard_nll"):
                value = measured[role][key]
                if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                    raise ValueError("Nonfinite post-stage reference diagnostic")
    expected_memory = _next_memory(config, stage_binding["stage"], memory_exits,
                                   reference_losses, audit, state)
    if (_json(stage / "memory_exits.json") != expected_memory
            or complete.get("memory_exits") != expected_memory):
        raise ValueError("Frozen domain-exit retention limits or memory lineage changed")
    evaluations = {}
    for domain in DOMAINS:
        evaluations[domain] = {}
        for role in ("native", "controlled"):
            directory = stage / "evaluation" / domain / role
            evaluation_binding = _evaluation_binding(
                config, context, stage_binding, geometry, state, checkpoint["identity"], domain, role)
            receipt = _read_seal(directory, evaluation_binding)
            if receipt is None:
                raise ValueError("Completed stage evaluation belongs to another policy")
            task_ids = _evaluation_task_ids(
                config, domain, context["binding"]["data"][domain]["task_ids"]["eval"])
            evaluations[domain][role] = _verify_evaluation(
                directory, domain, task_ids, config["domains"][domain]["evaluation"]["samples"])
    return {"state": state, "checkpoint": checkpoint, "memory_exits": expected_memory,
            "receipt": complete, "evaluations": evaluations}


def _generate_and_train(config, context, stage, stage_binding, selection_sha,
                        state, operators, model, tokenizer, method, resume):
    from .generation import generate_to_file
    from .pipeline import record_stage
    from .training import train_on_records, validate_full_completion_targets
    stage = Path(stage)
    if _check_checkpoint(stage, stage_binding, selection_sha) is not None:
        raise ValueError("A committed checkpoint must be resumed without replaying SFT")
    domain = stage_binding["stage"]["domain"]
    item = context["domains"][domain]
    tasks = item["splits"]["train"]
    synthetic_receipt = stage / "synthetic.receipt.json"
    synthetic_binding = {"stage_binding_sha256": _digest(stage_binding),
                         "selection_sha256": selection_sha,
                         "task_ids": [task["task_id"] for task in tasks],
                         "generation": item["config"]["synthesis"]}
    if synthetic_receipt.exists():
        saved = _json(synthetic_receipt)
        if saved.get("binding") != synthetic_binding:
            raise ValueError("Synthesis binding differs from the committed controller")
        _validate_files(stage, saved["files"])
        records = list(_rows(stage / "synthetic.jsonl"))
    else:
        with record_stage(stage, "synthesis"):
            with _policy_context(model, operators, state):
                records = generate_to_file(
                    model, tokenizer, tasks, stage / "synthetic.jsonl", item["config"]["synthesis"],
                    seed=context["seed"], model_identity=_digest({
                        "checkpoint": stage_binding["incoming_checkpoint"]["identity"],
                        "selection_sha256": selection_sha}),
                    method=f"continual_{method}", round_index=stage_binding["stage"]["index"],
                    stage="continual_synthesis", resume=resume)
        generated_files = {
            name: value for name, value in _tree_files(stage).items()
            if name.startswith("synthetic.jsonl") or name == "synthesis.resources.json"
        }
        _write_once_json(synthetic_receipt, {"schema": 1, "binding": synthetic_binding,
                                            "files": generated_files})
    _exact_records(stage / "synthetic.jsonl", [task["task_id"] for task in tasks],
                   item["config"]["synthesis"]["samples"])
    # The folding context has exited. Only current-domain raw records enter SFT.
    training = deepcopy(item["config"]["train"])
    training["require_full_completion_targets"] = True
    validate_full_completion_targets(training, item["config"]["synthesis"])
    _write_once_json(stage / "effective_train.json", training)
    with record_stage(stage, "sft"):
        model, stats = train_on_records(
            model, tokenizer, tasks, records, training, stage / "model",
            seed=context["seed"] + stage_binding["stage"]["index"])
    if (stats.get("truncated_tokens") != 0
            or stats.get("training_records_received") != len(records)
            or stats.get("training_records_retained") != len(records)
            or stats.get("raw_records_retained") != len(records)
            or stats.get("anchor_reference_records") != 0
            or stats.get("all_raw_records_exposed") is not True):
        raise ValueError("Student checkpoint is unqualified: not every raw target was retained and exposed")
    if getattr(model, "is_gradient_checkpointing", False):
        raise ValueError("Merged student must disable gradient checkpointing before controller diagnostics")
    _write_once_json(stage / "training_stats.json", stats)
    files = _tree_files(stage / "model")
    receipt = {
        "schema": 1, "stage_binding_sha256": _digest(stage_binding),
        "selection_sha256": selection_sha,
        "parent_checkpoint_identity": stage_binding["incoming_checkpoint"]["identity"],
        "checkpoint_identity": _digest(_model_files(stage / "model")), "files": files,
        "synthetic_sha256": _sha(stage / "synthetic.jsonl"),
        "synthetic_receipt_sha256": _sha(synthetic_receipt),
        "training_stats_sha256": _sha(stage / "model/training_stats.json"),
        "stage_training_stats_sha256": _sha(stage / "training_stats.json"),
        "effective_train_sha256": _sha(stage / "effective_train.json"),
        "all_raw_records_retained": True, "training_domain": domain,
    }
    _assert_external(context["binding"])
    _write_once_json(stage / "checkpoint.json", receipt)
    return model, receipt


def _run_stage(config, context, stage, stage_binding, geometry,
               incoming_state, memory_exits, method, resume):
    """Resume a committed student by evaluation only, without fitting or SFT."""
    from .pipeline import record_stage
    from .continual_gains import operators_from_gain_state
    stage = Path(stage)
    inspected = _inspect_stage(config, context, stage, stage_binding, geometry,
                               incoming_state, memory_exits, method)
    if inspected is not None:
        return inspected
    _write_once_json(stage / "binding.json", stage_binding)
    controller_binding = _controller_binding(
        context, stage_binding, geometry, incoming_state, memory_exits, method)
    selected = _read_selection(
        stage / "controller", controller_binding, geometry,
        context["binding"]["effective_controller"]["min_gain"])
    trained = config["backbone_update"] == "self_distill" and stage_binding["stage"]["index"] > 0
    if selected is None and ((stage / "checkpoint.json").exists() or (stage / "model").exists()
                             or any(stage.glob(".model.saving-*"))):
        raise ValueError("A checkpoint exists without its committed controller selection")
    checkpoint_receipt = (_check_checkpoint(stage, stage_binding, selected[3])
                          if trained and selected is not None else None)
    parent = stage_binding["incoming_checkpoint"]
    if _digest(_model_files(parent["path"])) != parent["identity"]:
        raise ValueError("Inherited parent model changed before loading")
    load_path = stage / "model" if checkpoint_receipt is not None else Path(parent["path"])
    model = tokenizer = None
    try:
        with record_stage(stage, "model_loading"):
            model, tokenizer = _load_model(config, load_path)
        if selected is None:
            selected = _select_controller(
                config, context, stage, stage_binding, geometry, incoming_state,
                memory_exits, method, model, tokenizer, resume)
        state, operators, audit, selection_sha = selected
        if trained and checkpoint_receipt is None:
            model, checkpoint_receipt = _generate_and_train(
                config, context, stage, stage_binding, selection_sha,
                state, operators, model, tokenizer, method, resume)
        # This branch also handles interruption after checkpoint.json was committed.
        # It never calls controller fitting, synthesis or SFT for that checkpoint.
        checkpoint = ({"path": str(stage / "model"), "identity": checkpoint_receipt["checkpoint_identity"]}
                      if trained else parent)
        domains = list(memory_exits)
        current = stage_binding["stage"]["domain"]
        if current and current not in domains:
            domains.append(current)
        reference_path = stage / "reference_losses.json"
        if not reference_path.exists():
            with record_stage(stage, "post_reference_nll"):
                losses = _reference_losses(context, domains, model, tokenizer, operators, state)
            _write_once_json(reference_path, losses)
        else:
            losses = _json(reference_path)
        _evaluate_all_domains(
            config, context, stage, stage_binding, geometry, state, operators,
            model, tokenizer, checkpoint["identity"], method, resume)
        next_memory = _next_memory(config, stage_binding["stage"], memory_exits,
                                   losses, audit, _state_json(state))
        _write_once_json(stage / "memory_exits.json", next_memory)
        if _digest(_model_files(parent["path"])) != parent["identity"]:
            raise ValueError("Inherited parent model changed while this stage was running")
        _assert_external(context["binding"])
        _seal(stage, stage_binding, {
            "gain_state_sha256": _digest(_state_json(state)),
            "controller_complete_sha256": selection_sha,
            "output_checkpoint": checkpoint, "memory_exits": next_memory,
        })
        return _inspect_stage(config, context, stage, stage_binding, geometry,
                              incoming_state, memory_exits, method)
    finally:
        del model, tokenizer
        _release()


def run_continual_gain_study(config, method, resume=False):
    """Run one isolated method/order/backbone lineage with full native evaluation."""
    validate_continual_config(config)
    if method not in METHODS:
        raise ValueError(f"Unknown continual method: {method}")
    config = deepcopy(config)
    context = _prepare_inputs(config)
    binding = context["binding"]
    root = _path(config["output_dir"])
    method_root = root / method
    with _exclusive(root / ".study.lock"):
        allowed = {"study_manifest.json", ".study.lock", *METHODS}
        if any(path.name not in allowed for path in root.iterdir()):
            raise ValueError("Study root contains unrelated files; use a fresh isolated directory")
        _write_once_json(root / "study_manifest.json", binding)
    with _exclusive(method_root / ".writer.lock"):
        manifest_path = method_root / "manifest.json"
        if manifest_path.exists() and not resume:
            raise FileExistsError("Existing method lineage requires explicit resume=True")
        if not manifest_path.exists() and any(path.name != ".writer.lock" for path in method_root.iterdir()):
            raise ValueError("Unbound method artifacts exist; preserve them and use a fresh directory")
        _write_once_json(manifest_path, {
            "schema": 1, "method": method, "study_sha256": _digest(binding),
            "output_dir": str(method_root),
        })
        _assert_external(binding)
        geometry = _geometry(config, context, method_root)
        incoming_state = geometry["initial"]
        checkpoint = {"path": context["base_model"]["path"], "identity": context["base_model"]["identity"]}
        previous_receipt, memory_exits, completed = None, {}, []
        for stage_info in stage_schedule(config):
            stage = method_root / stage_info["name"]
            stage_binding = _stage_binding(
                config, binding, stage_info, checkpoint, incoming_state,
                previous_receipt, memory_exits, geometry, method)
            result = _run_stage(
                config, context, stage, stage_binding, geometry,
                incoming_state, memory_exits, method, resume)
            if result is None:
                raise RuntimeError("Stage returned without a committed completion receipt")
            incoming_state = _state_tensors(
                result["state"], geometry["metadata"], binding["effective_controller"]["min_gain"])
            checkpoint, memory_exits = result["checkpoint"], result["memory_exits"]
            previous_receipt = _sha(stage / "complete.json")
            completed.append({"stage": stage_info, "receipt_sha256": previous_receipt,
                              "checkpoint_identity": checkpoint["identity"],
                              "gain_state_sha256": _digest(result["state"])})
        _write_once_json(method_root / "run_complete.json", {
            "schema": 1, "status": "completed", "study_sha256": _digest(binding),
            "method": method, "stages": completed,
            "last_checkpoint": checkpoint, "last_gain_state_sha256": _digest(_state_json(incoming_state)),
            "memory_exits": memory_exits, "evaluation_sampling_round": 0,
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
