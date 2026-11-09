#!/usr/bin/env python3
"""One-case-at-a-time ICLR 2027 rebuttal orchestration.

Planning reads and freezes prepared inputs; it never loads a model. Execution
requires --execute. Each case owns its config, model root, attempt logs, and
receipts. Historical results are not adopted as newly executed case outputs.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from types import SimpleNamespace
from uuid import uuid4

REPO = Path(__file__).resolve().parents[1]
SPEC = REPO / "experiments/iclr2027_rebuttal/cases.json"
ASSETS = REPO / "configs/final/assets.json"
DEFAULT_ROOT = "runs/iclr2027_rebuttal_isolated_v2"
PROTOCOL = "iclr2027-spectrum-case-isolation-v2"
DATA_COUNTS = {"train": 291, "calibration": 50, "validation": 30, "eval": 500}
EVAL_FILES = {"evaluation.metrics.json", "evaluation.verified.jsonl", "evaluation.jsonl"}
MODEL_SUFFIXES = {".safetensors", ".bin", ".json", ".txt", ".model", ".jinja"}
DECODERS = {
    "cool": {"temperature": .6, "top_p": .95, "top_k": 0},
    "warm": {"temperature": 1., "top_p": .95, "top_k": 0},
    "ssd_recipe": {"temperature": 1.5, "top_p": .8, "top_k": 20},
    "nucleus_tight": {"temperature": .8, "top_p": .8, "top_k": 0},
}


def load_spec() -> dict:
    spec = read_json(SPEC)
    if spec["protocol"] != PROTOCOL:
        raise ValueError("Unexpected frozen rebuttal protocol")
    rows = spec["cases"]
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)) or ids != [f"c{i:02d}" for i in range(len(rows))]:
        raise ValueError("Case IDs must be unique and consecutive c00..")
    if any(row["kind"] not in {"train", "transfer", "decoder", "audit", "semantic", "interpolate"} for row in rows):
        raise ValueError("Unknown case kind")
    return spec


def hbytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(obj: object) -> str:
    # Match improving.utils.stable_hash, including its JSON whitespace. Native
    # evaluation receipts use that function to seal their protocol object.
    return hbytes(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                             allow_nan=False).encode("utf-8"))


def file_sha(path: Path) -> str:
    sha = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def abs_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    return (path if path.is_absolute() else REPO / path).resolve()


def store_once(path: Path, data: object) -> None:
    """Publish an entire file without replacing an existing frozen object."""
    contents = (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False,
                           allow_nan=False) + "\n").encode("utf-8")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.is_symlink() or path.read_bytes() != contents:
                raise ValueError(f"Frozen path changed; choose a fresh root: {path}")
    finally:
        temporary.unlink(missing_ok=True)


def one_case(case_id: str) -> dict:
    if not case_id:
        raise ValueError("--case is required for plan/run/status")
    rows = {row["id"]: row for row in load_spec()["cases"]}
    if case_id not in rows:
        raise ValueError(f"Unknown case {case_id}")
    return rows[case_id]


def read_records(path: Path):
    with Path(path).open(encoding="utf-8") as stream:
        for index, line in enumerate(stream, 1):
            if line.strip():
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError(f"Non-object JSONL record: {path}:{index}")
                yield row


def task_identity(paths: dict, counts: dict | None = None) -> dict:
    """Freeze the exact bytes, ordered IDs and population of each task split."""
    identity, seen_ids, seen_prompts = {}, {}, {}
    for split, value in paths.items():
        path = abs_path(value)
        if not path.is_file():
            raise FileNotFoundError(f"Missing prepared {split} tasks: {path}")
        before = file_sha(path)
        rows = list(read_records(path))
        ids = [row.get("task_id") for row in rows]
        if not rows or any(not isinstance(item, str) or not item for item in ids):
            raise ValueError(f"Task IDs must be nonempty strings: {path}")
        if len(set(ids)) != len(ids) or (counts and len(ids) != counts[split]):
            raise ValueError(f"{split}: expected {counts.get(split) if counts else 'unique'} task IDs, got {len(ids)}")
        for row in rows:
            if row.get("split", split) != split:
                raise ValueError(f"Task declares the wrong split: {row['task_id']}")
            for value, seen, kind in [(row["task_id"], seen_ids, "task ID"), *[
                    (" ".join(str(row[key]).split()), seen_prompts, "normalized prompt")
                    for key in ("prompt", "original_prompt") if row.get(key)]]:
                if value in seen and seen[value] != split:
                    raise ValueError(f"Cross-split {kind} overlap: {seen[value]} and {split}")
                seen[value] = split
        if file_sha(path) != before:
            raise ValueError(f"Task file changed while being frozen: {path}")
        identity[split] = {"path": str(path), "sha256": before,
                           "count": len(ids), "task_ids": ids}
    return identity


def verify_data(cfg: dict, case: dict | None = None) -> dict:
    """Check exact populations and the case-declared budget before GPU loading."""
    if set(cfg["data"]) != set(DATA_COUNTS) or cfg.get("data_limits"):
        raise ValueError("Case requires all four complete MBPP task splits")
    gen = cfg["generation"]
    if gen["eval_samples"] != 64 or gen["train_samples"] != 16:
        raise ValueError("Case train/eval budgets were altered")
    cap = case["max_new_tokens"] if case else gen["max_new_tokens"]
    if cap not in (512, 4096) or gen["max_new_tokens"] != cap:
        raise ValueError("Output-token limit differs from the declared 512/4096-token case")
    if case and (cfg["rounds"] != case["rounds"] or cfg["methods"] != [case["method"]]):
        raise ValueError("Case method or round count was altered")
    if cfg["evaluation"].get("backend") not in ("bwrap", "local") or (
            cfg["evaluation"].get("backend") == "local"
            and cfg["evaluation"].get("allow_unsafe_local") is not True):
        raise ValueError("New cases require bwrap verification or explicitly enabled local execution")
    return task_identity(cfg["data"], DATA_COUNTS)


def template_for(case: dict) -> Path | None:
    if not case.get("template_config"):
        return None
    path = abs_path(case["template_config"])
    if not path.is_relative_to(REPO.resolve()) or not path.is_file():
        raise ValueError("Case template must be a real file inside the repository")
    return path


def config_for(case: dict, args: argparse.Namespace, run_root: Path) -> dict:
    """Specialize an existing native config/template without changing its source."""
    template = template_for(case)
    if template:
        if template.suffix.lower() == ".json":
            cfg = read_json(template)
        else:
            import yaml  # Templates alone require PyYAML; ordinary planning is stdlib.
            cfg = yaml.safe_load(template.read_text(encoding="utf-8"))
        if not isinstance(cfg, dict):
            raise ValueError("Training template must contain a configuration mapping")
    else:
        spec = importlib.util.spec_from_file_location("_rebuttal_native_planner", REPO / "scripts/run_iclr2027.py")
        if spec is None or spec.loader is None:
            raise ImportError("Missing native experiment config builder")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        native = SimpleNamespace(profile=args.profile, backend=args.eval_backend,
                                 allow_unsafe_local=(args.eval_backend == "local"),
                                 workers=args.workers, data_root=str(abs_path(args.data_root)))
        cfg = mod.native_config(native, case["model"], int(case["seed"]))
    asset = read_json(ASSETS)["models"][case["model"]]
    name = asset["repo_id"]
    if args.model_root:
        candidate = abs_path(args.model_root) / name
        if not candidate.is_dir():
            raise FileNotFoundError(f"Explicit pinned model root missing: {candidate}")
        name = str(candidate)
    cfg["model"].update(name=name, revision=asset["revision"], local_files_only=bool(args.model_root))
    cfg.update(output_dir=str(run_root), label=case["id"], rebuttal_case=case["id"],
               seed=int(case["seed"]), rounds=int(case["rounds"]), checkpoint_retention="all",
               methods=[case["method"]], data_limits={})
    cfg["data"] = {split: str(abs_path(args.data_root) / f"{split}.jsonl") for split in DATA_COUNTS}
    cfg["generation"].update(train_samples=case["train_samples"], eval_samples=case["eval_samples"],
                             max_new_tokens=case["max_new_tokens"],
                             max_prompt_tokens=case.get("max_prompt_tokens", 1024),
                             temperature=.8, top_p=.95, top_k=0)
    # Probed generation triples (batch_size, task_batch_size, sequence_batch_size),
    # measured 2026-11-08 on one H100 80GB with the repo venv; device-reserved peaks
    # 71.5-72.5 GiB, below the 76.9 GiB checkpoint-save danger band. See
    # runs/batch_probe_20261108/PROBE_REPORT.md section 3.1. Every arm in a group
    # shares the same triple so batching does not shift the batch_seed RNG stream.
    # qwen7b uses S=256 (16, 16, 256): the real pipeline keeps the SFT model plus a
    # freshly loaded eval checkpoint (~30 GiB for 7B) resident during dev_generation
    # and post-training evaluation. Probe S=512 (40.1 GiB single-copy) + 30 GiB hit
    # the 79.18 GiB wall at 71.9 allocated; S=768 OOMs at 78.2. S=256 leaves ~22 GiB
    # of headroom; every stage of the group shares this triple.
    _probed_generation = {
        "qwen1.5b": (64, 38, 2432),      # qwen15b_train_512 / qwen15b_mbpp_eval_1024_512
        "qwen3b": (16, 120, 1920),       # qwen3b_train_512
        "deepseek6.7b": (16, 9, 144),    # deepseek67b_train_512
        "qwen7b": (16, 11, 176),         # qwen7b_train_4096: real-run slope ~0.31 GiB/S
                                       # (S=64 -> 18.3 GiB, S=256 -> OOM at 78.2). S=176
                                       # lands ~53 GiB base eval (~3x the S=64 point, per
                                       # user 2026-11-09: keep sustained >=40 GiB), with
                                       # ~20 GiB headroom below the wall.
    }.get(case["model"])
    if _probed_generation:
        cfg["generation"].update(batch_size=_probed_generation[0],
                                 task_batch_size=_probed_generation[1],
                                 sequence_batch_size=_probed_generation[2])
    calibration = cfg.setdefault("calibration", {})
    calibration.update(max_examples=int(case["calibration_examples"]), tau=float(case.get("tau", 1.0)),
                       reestimate_each_round=case.get("reestimate_each_round", True))
    if "layers" in case:
        calibration["layers"] = case["layers"]
    calibration.update(case.get("calibration_overrides", {}))
    if case["method"] != "spectral_learned":
        calibration.pop("gain_learning", None)
        calibration.pop("matched_reference_fit_examples", None)
    # These cases control the operator/update, never per-token loss weights.
    if case.get("token_loss_reweighting", False) or float(case.get("lora_update_scale", 1.0)) != 1.0:
        raise ValueError("This catalog does not implement token weighting or a nonunit LoRA update scale")
    cfg["train"]["loss_scope"] = "all"
    cfg["train"]["fixed_anchor_replay"] = bool(case.get("anchor_replay", False))
    if case.get("target_token_budget"):
        cfg["train"]["target_token_budget"] = int(case["target_token_budget"])
    else:
        cfg["train"].pop("target_token_budget", None)
    if case.get("training_decoder_overrides"):
        cfg["generation"]["training_decoder_overrides"] = case["training_decoder_overrides"]
    else:
        cfg["generation"].pop("training_decoder_overrides", None)
    cfg["evaluation"].update(backend=args.eval_backend,
                             allow_unsafe_local=(args.eval_backend == "local"),
                             workers=args.workers, bootstrap_samples=2000)
    diagnostic_rounds = case.get("diagnostic_rounds", [1, case["rounds"]])
    if not diagnostic_rounds or any(type(r) is not int or not 1 <= r <= case["rounds"] for r in diagnostic_rounds):
        raise ValueError("Diagnostic rounds must belong to this case")
    cfg.setdefault("diagnostics", {}).update(
        evaluate_generation_policy=False,
        transfer_gap={"enabled": True, "rounds": diagnostic_rounds, "samples": 64,
                      "validation_task_count": 30,
                      "max_prompt_tokens": cfg["generation"]["max_prompt_tokens"],
                      "max_new_tokens": cfg["generation"]["max_new_tokens"],
                      "batch_size": _probed_generation[0] if _probed_generation else 1,
                      "task_batch_size": _probed_generation[1] if _probed_generation else 1,
                      "sequence_batch_size": _probed_generation[2] if _probed_generation else 1,
                      "reference_nll_each_round": True},
        operator_probe={"enabled": True, "examples": 8, "max_new_tokens": 128, "kl_chunk_tokens": 32})
    return cfg


def implementation_identity(case: dict) -> dict:
    """Include the complete executable Python inventory, not a six-file subset."""
    paths = set()
    for directory in ("src", "scripts", "experiments/iclr2027", "experiments/iclr2027_rebuttal"):
        paths.update(path for path in (REPO / directory).rglob("*.py") if path.is_file())
    paths.update(path for path in (REPO / "pyproject.toml", ASSETS) if path.is_file())
    paths.update(path for path in REPO.glob("requirements*.txt") if path.is_file())
    template = template_for(case)
    if template:
        paths.add(template)
    files = {str(path.relative_to(REPO)): file_sha(path) for path in sorted(paths)}
    return {"sha256": digest(files), "files": files}


def model_identity(settings: dict, verify_hashes: bool = True, frozen: dict | None = None) -> dict:
    """Pin remote revisions or all local tokenizer/configuration/weight files."""
    value = {"settings": settings}
    local = abs_path(settings["name"])
    if local.is_dir():
        files = {str(p.relative_to(local)): p for p in sorted(local.rglob("*"))
                 if p.is_file() and p.suffix in MODEL_SUFFIXES and p.name != "training_stats.json"}
        if "config.json" not in files or not any(p.suffix in {".safetensors", ".bin"} for p in files.values()):
            raise ValueError(f"Local source model has no retained full weights/config: {local}")
        if verify_hashes or frozen is None:
            seals = {name: file_sha(path) for name, path in files.items()}
        else:
            seals = frozen.get("files", {})
            if set(files) != set(seals):
                raise ValueError("Local source model file inventory changed")
        value.update(path=str(local), files=seals, sha256=digest(seals))
    elif settings.get("local_files_only"):
        raise FileNotFoundError(f"Pinned local model is missing: {local}")
    elif not re.fullmatch(r"[0-9a-fA-F]{40}", str(settings.get("revision", ""))):
        raise ValueError("Remote source model requires an immutable 40-character revision")
    return value


def ensure_nonoverlap(source: Path, output: Path) -> None:
    source, output = source.resolve(), output.resolve()
    if source == output or source.is_relative_to(output) or output.is_relative_to(source):
        raise ValueError("Dependency source and case output must not overlap")


def sealed_files(stage: Path, *, hashes: bool, required: set | None = None,
                 completed: bool = True, complete_inventory: bool = False) -> dict:
    receipt = read_json(stage / "complete.json")
    files = receipt.get("files")
    if not isinstance(files, dict) or not files or (completed and receipt.get("status") != "completed"):
        raise ValueError(f"Missing completed file seal: {stage}")
    if not (required or set()) <= set(files):
        raise ValueError(f"Missing required sealed files: {stage}")
    for name, expected in files.items():
        rel = PurePosixPath(name)
        path = (stage / name).resolve()
        if rel.is_absolute() or ".." in rel.parts or not path.is_relative_to(stage.resolve()):
            raise ValueError(f"Sealed file escapes its stage: {name}")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected) or not path.is_file():
            raise ValueError(f"Missing or invalid sealed file: {stage / name}")
        if hashes and file_sha(path) != expected:
            raise ValueError(f"Checksum mismatch: {stage / name}")
    if complete_inventory:
        actual = {str(p.relative_to(stage)) for p in stage.rglob("*")
                  if p.is_file() and p.name != "complete.json" and ".parts" not in str(p)}
        if actual != set(files):
            raise ValueError(f"Stage contains unsealed or omitted files: {stage}")
    return receipt


def source_methods(value: str | None, available: list) -> list:
    selected = value.split(",") if value else list(available)
    if (not selected or len(set(selected)) != len(selected)
            or any(not re.fullmatch(r"[a-z][a-z0-9_]*", name) for name in selected)
            or any(name not in available for name in selected)):
        raise ValueError("Source methods must be unique exact names from the source manifest")
    return selected


def dependency_identity(source: Path, selected: list, round_number: int, *, hashes: bool = True,
                        frozen: dict | None = None) -> dict:
    manifest_path = source / "manifest.json"
    manifest = read_json(manifest_path)
    cfg = manifest["config"]
    if not isinstance(manifest.get("fingerprint"), str) or not manifest["fingerprint"]:
        raise ValueError("Source manifest has no native protocol fingerprint")
    if round_number < 1 or round_number > int(cfg["rounds"]):
        raise ValueError("Requested source round is outside the training configuration")
    source_methods(",".join(selected), cfg["methods"])
    tasks = task_identity({name: source / "tasks" / f"{name}.jsonl" for name in DATA_COUNTS}, DATA_COUNTS)
    declared_ids = manifest.get("selected_task_ids", {})
    if any(declared_ids.get(split) != info["task_ids"] for split, info in tasks.items()):
        raise ValueError("Source task snapshots do not match the source manifest")
    stages = {}
    # Freeze the full trajectory actually used to produce each requested source.
    # Native base receipts predate the status field and use integrity_schema=2.
    base = sealed_files(source / "base", hashes=hashes, required=EVAL_FILES, completed=False)
    stages["base"] = {"marker_sha256": file_sha(source / "base/complete.json"), "files": base["files"]}
    for method in selected:
        for index in range(1, round_number + 1):
            label = f"{method}/round_{index}"
            stage = source / label
            seal = sealed_files(stage, hashes=hashes,
                                required=EVAL_FILES | {"train.jsonl", "training_stats.json", "model/config.json"},
                                complete_inventory=True)
            if not any(name.startswith("model/") and name.endswith((".safetensors", ".bin")) for name in seal["files"]):
                raise ValueError(f"Source checkpoint missing or pruned: {label}")
            stages[label] = {"marker_sha256": file_sha(stage / "complete.json"), "files": seal["files"]}
    base_model = model_identity(cfg["model"], hashes, (frozen or {}).get("model"))
    return {"source_run": str(source), "manifest_sha256": file_sha(manifest_path),
            "native_fingerprint": manifest["fingerprint"], "config_sha256": digest(cfg),
            "model": base_model, "data": tasks, "seed": cfg.get("seed"),
            "methods": selected, "round": round_number, "stages": stages}


def semantic_source_identity(path, expected_taskfile) -> dict:
    """Admit only a sealed, comparable original-protocol round-5 program pool."""
    path, expected_taskfile = abs_path(path), abs_path(expected_taskfile)
    stage = path.parent
    if path.name != "evaluation.verified.jsonl" or stage.name != "round_5":
        raise ValueError("Semantic evidence must be a native round_5/evaluation.verified.jsonl")
    method, source = stage.parent.name, stage.parent.parent
    manifest = read_json(source / "manifest.json")
    cfg = manifest["config"]
    source_methods(method, cfg["methods"])
    generation = cfg.get("generation", {})
    required_generation = {"train_samples": 16, "eval_samples": 64,
                           "max_prompt_tokens": 1024, "max_new_tokens": 512,
                           "temperature": .8, "top_p": .95, "top_k": 0}
    if (type(cfg.get("rounds")) is not int or cfg["rounds"] != 5 or cfg.get("data_limits")
            or type(cfg.get("seed")) is not int
            or any(generation.get(key) != value for key, value in required_generation.items())):
        raise ValueError("Semantic sources require the original five-round n16/n64 1024/512 protocol and .8/.95/0 decoder")
    asset = read_json(ASSETS)["models"]["qwen1.5b"]
    model = cfg.get("model", {})
    if model.get("revision") != asset["revision"]:
        raise ValueError("Semantic sources require the pinned original Qwen 1.5B revision")
    local_model = abs_path(model.get("name", ""))
    if local_model.is_dir():
        architecture = read_json(local_model / "config.json")
        if any(architecture.get(key) != asset[key] for key in
               ("model_type", "hidden_size", "num_hidden_layers", "num_attention_heads", "num_key_value_heads")):
            raise ValueError("Semantic source local model is not the original Qwen 1.5B architecture")
    elif model.get("name") != asset["repo_id"]:
        raise ValueError("Semantic source model must be the original Qwen 1.5B checkpoint")
    completion = next((candidate for candidate in
                       (source / f"run_status.{method}.json", source / "run_status.json")
                       if candidate.is_file() and (lambda value:
                           value.get("status") == "completed" and value.get("verification") == "completed"
                           and value.get("rounds") == 5 and method in value.get("methods", []))
                       (read_json(candidate))), None)
    if completion is None:
        raise ValueError("Semantic source has no completed native five-round run receipt")
    expected = task_identity({"eval": expected_taskfile}, {"eval": 500})["eval"]
    dependency = dependency_identity(source, [method], 5, hashes=True)
    if (dependency["data"]["eval"]["sha256"] != expected["sha256"]
            or dependency["data"]["eval"]["task_ids"] != expected["task_ids"]):
        raise ValueError("Semantic source differs from the exact frozen 500-task evaluation file")
    dependency["completion_receipt"] = {"file": str(completion.relative_to(source)),
                                        "sha256": file_sha(completion)}
    for number in range(1, 6):
        exact_records(source / method / f"round_{number}" / "train.jsonl",
                      dependency["data"]["train"]["task_ids"], 16)
    metrics = inspect_stage(stage, expected["task_ids"], 64, hashes=True, trained=True)
    seal = read_json(stage / "complete.json")
    budget_file = stage / "evaluation.jsonl.budget.json"
    if budget_file.name not in seal["files"]:
        raise ValueError("Semantic source lacks its sealed native generation protocol")
    budget = read_json(budget_file)
    native = budget.get("protocol", {})
    native_settings = {key: value for key, value in generation.items()
                       if key not in {"train_samples", "eval_samples"}}
    native_settings["samples"] = 64
    if (native.get("model_identity") != seal.get("model_identity") or not seal.get("model_identity")
            or native.get("method") != method or native.get("round") != 5
            or native.get("seed") != cfg["seed"] or native.get("stage") != "evaluation"
            or native.get("settings") != native_settings
            or budget.get("samples") != 500 * 64 or budget.get("tasks") != 500):
        raise ValueError("Semantic source native generation model, round, seed or decoder differs from its receipt")
    metric_protocol = metrics.get("protocol", {})
    verifier = metric_protocol.get("evaluation")
    evaluation = cfg.get("evaluation", {})
    if (metric_protocol.get("evaluation_provenance_status") != "task_local_v2"
            or not isinstance(verifier, dict) or verifier.get("provenance_version") != 2
            or verifier.get("protocol_version") != "task-tests-v2"
            or verifier.get("backend") not in {"bwrap", "docker"}
            or verifier.get("backend") != evaluation.get("backend", "docker")
            or verifier.get("code_extraction") != evaluation.get("code_extraction", "strict")):
        raise ValueError("Semantic source requires complete native verifier and extraction provenance")
    raw_fields, raw_hashes = None, {}
    for row in read_records(stage / "evaluation.jsonl"):
        if raw_fields is None:
            raw_fields = set(row)
        if set(row) != raw_fields:
            raise ValueError("Native generation records have inconsistent fields")
        raw_hashes[(row["task_id"], row["sample_id"])] = digest(row)
    harnesses, prompts, correct_counts = {}, {}, Counter()
    for row in read_records(path):
        key = (row["task_id"], row["sample_id"])
        if (not raw_fields <= set(row)
                or digest({field: row[field] for field in raw_fields}) != raw_hashes[key]
                or type(row.get("correct")) is not bool
                or row["correct"] != (row.get("status") == "passed")
                or row.get("method") != method or row.get("round") != 5 or row.get("seed") != cfg["seed"]
                or type(row.get("prompt_tokens")) is not int or not 1 <= row["prompt_tokens"] <= 1024
                or type(row.get("generation_tokens")) is not int or not 1 <= row["generation_tokens"] <= 512
                or not isinstance(row.get("completion_ids"), list)
                or len(row["completion_ids"]) != row["generation_tokens"]):
            raise ValueError("Verified semantic records differ from their original native samples")
        provenance = row.get("evaluation_provenance")
        if not isinstance(provenance, dict):
            raise ValueError("Semantic source has unqualified verifier records")
        shared = dict(provenance)
        harness = shared.pop("task_harness_sha256", None)
        prompt = row.get("prompt_sha256")
        if (shared != verifier or row.get("evaluation_backend") != verifier["backend"]
                or row.get("evaluation_protocol") != verifier["protocol_version"]
                or row.get("code_extraction") != verifier["code_extraction"]
                or any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
                       for value in (harness, prompt))
                or harnesses.get(key[0], harness) != harness or prompts.get(key[0], prompt) != prompt):
            raise ValueError("Semantic verifier, harness or rendered prompt identity is inconsistent")
        harnesses[key[0]], prompts[key[0]] = harness, prompt
        correct_counts[key[0]] += int(row["correct"])
    sys.path.insert(0, str(REPO / "src"))
    from improving.verification import _task_harness, _test_code
    from improving.utils import stable_hash
    actual_harnesses = {task["task_id"]: stable_hash(_task_harness(task, _test_code(task)))
                        for task in read_records(expected_taskfile)}
    if (harnesses != metric_protocol.get("evaluation_task_harnesses") or harnesses != actual_harnesses
            or any(metrics["per_task"][task].get("correct_count") != correct_counts[task]
                   for task in expected["task_ids"])
            or metrics["aggregate"].get("correct_count") != sum(correct_counts.values())):
        raise ValueError("Semantic source metrics disagree with verified native records")
    common = {
        "schema_version": 1, "model": {"repo_id": asset["repo_id"], "revision": asset["revision"],
            "settings": {key: value for key, value in model.items() if key not in {"name", "local_files_only"}},
            "files": dependency["model"].get("files")},
        "seed": cfg["seed"], "data_seed": cfg.get("data_seed", 42), "rounds": 5,
        "train_samples": 16, "eval_samples": 64,
        "generation": {key: value for key, value in native_settings.items() if key != "training_decoder_overrides"},
        "data": {split: {key: value for key, value in info.items() if key != "path"}
                 for split, info in dependency["data"].items()},
        "metric_protocol": {key: metric_protocol.get(key) for key in
                            ("ks", "correct_budget", "correct_budgets", "proxy_version", "metric_versions", "sampling")},
        "verifier": verifier, "task_harnesses": harnesses, "rendered_prompt_hashes": prompts,
    }
    return {"source_run": str(source), "source_method": method, "source_round": 5,
            "verified_sha256": file_sha(path), "dependency": dependency, "common_protocol": common}


def benchmark_identity(root: Path, benchmark: str) -> dict:
    directory = root / benchmark
    manifest = read_json(directory / "manifest.json")
    outputs = manifest.get("output_files", {})
    if manifest.get("name") != benchmark or "eval.jsonl" not in outputs:
        raise ValueError("Prepared benchmark manifest has the wrong name or no evaluation snapshot")
    files = {}
    for filename, detail in outputs.items():
        path = (directory / filename).resolve()
        if not path.is_relative_to(directory.resolve()) or not path.is_file():
            raise ValueError("Prepared benchmark file is absent or outside its directory")
        value = file_sha(path)
        if value != detail.get("sha256"):
            raise ValueError(f"Prepared benchmark changed after preparation: {path}")
        files[filename] = value
    tasks = task_identity({"eval": directory / "eval.jsonl"})["eval"]
    if tasks["count"] != outputs["eval.jsonl"].get("count"):
        raise ValueError("Prepared benchmark count differs from its manifest")
    return {"manifest_sha256": file_sha(directory / "manifest.json"), "files": files, "tasks": tasks}


def validate_unused_selectors(case: dict, args: argparse.Namespace) -> None:
    dependency = case["kind"] in {"transfer", "decoder", "interpolate"}
    if (args.source_run or args.source_methods) and not dependency:
        raise ValueError("Source selectors apply only to dependent evaluation cases")
    if (args.task_file or args.evidence) and case["kind"] != "semantic":
        raise ValueError("Task/evidence selectors apply only to the semantic case")
    if case["kind"] == "interpolate" and args.source_methods not in (None, "", case["method"]):
        raise ValueError("Interpolation source method is fixed by its case")



def backend_matches_plan(plan: dict, protocol: dict) -> bool:
    """Dependent-case receipts may be sandboxed (bwrap) or explicitly local.

    Plans made after the --eval-backend option record their backend and must
    match exactly. Legacy plans (frozen before the option existed) accept the
    two honest combinations, since their runs were launched with either the
    delivered bwrap default or an explicit local override.
    """
    backend = protocol.get("evaluation", {}).get("backend")
    unsafe = protocol.get("evaluation", {}).get("allow_unsafe_local")
    if "eval_backend" in plan:
        return backend == plan["eval_backend"] and unsafe is (plan["eval_backend"] == "local")
    return (backend, unsafe) in (("bwrap", False), ("local", True))


def build_plan(case: dict, args: argparse.Namespace) -> dict:
    validate_unused_selectors(case, args)
    if args.workers < 1:
        raise ValueError("--workers must be positive")
    directory = abs_path(args.root) / case["id"]
    run_root = directory / "run"
    if directory.is_symlink() or run_root.is_symlink():
        raise ValueError("Case directories cannot be symlink aliases")
    if run_root.exists() and any(run_root.iterdir()) and not (directory / "plan.json").is_file():
        raise ValueError("Existing case output has no frozen plan; use a fresh root")
    plan = {"protocol": load_spec()["protocol"], "case": case, "case_spec_sha256": digest(case),
            "spec_file_sha256": file_sha(SPEC), "root": str(directory), "output": str(run_root),
            "kind": case["kind"], "status": "planned_not_executed",
            "run_command_requires_explicit_execute": True,
            "training_output_not_reused_from_historical_audit": True,
            "implementation": implementation_identity(case)}
    cfg = None
    if case["kind"] == "train":
        cfg = config_for(case, args, run_root)
        plan["data_identity"] = verify_data(cfg, case)
        plan["model_identity"] = model_identity(cfg["model"])
        plan["config_file"] = str(directory / "config.json")
        plan["config_sha256"] = digest(cfg)
        plan["command"] = [sys.executable, "-m", "improving", "run", "--config", plan["config_file"], "--resume"]
        plan["max_requested_training_completions"] = DATA_COUNTS["train"] * case["train_samples"] * case["rounds"]
        plan["max_requested_native_eval_completions"] = DATA_COUNTS["eval"] * case["eval_samples"] * (case["rounds"] + 1)
    elif case["kind"] in {"transfer", "decoder", "interpolate"}:
        if not args.source_run:
            raise ValueError(f"{case['id']} needs --source-run pointing to an actual sealed training root")
        source = abs_path(args.source_run)
        ensure_nonoverlap(source, directory)
        cfg_source = read_json(source / "manifest.json")["config"]
        selected = source_methods(case["method"] if case["kind"] == "interpolate" else args.source_methods,
                                  cfg_source["methods"])
        plan.update(source_run=str(source), source_methods=",".join(selected), round=case["round"], samples=case["samples"],
                    eval_backend=args.eval_backend)
        plan["source_identity"] = dependency_identity(source, selected, case["round"])
        common = ["--run-dir", str(source), "--output-dir", str(run_root),
                  "--round", str(case["round"]), "--samples", str(case["samples"]), "--resume"]
        if case["kind"] == "interpolate":
            plan["command"] = [sys.executable, "scripts/rebuttal_interpolation_eval.py", *common,
                               "--method", case["method"], "--alpha", str(case["alpha"])]
        elif case["kind"] == "transfer":
            plan["benchmark_root"] = str(abs_path(args.benchmark_root))
            plan["benchmark_identity"] = benchmark_identity(Path(plan["benchmark_root"]), case["benchmark"])
            fit = {name: item["path"] for name, item in plan["source_identity"]["data"].items() if name != "eval"}
            task_identity({**fit, "eval": plan["benchmark_identity"]["tasks"]["path"]})
            backend_args = ["--backend", args.eval_backend]
            if args.eval_backend == "local":
                backend_args.append("--allow-unsafe-local")
            plan["command"] = [sys.executable, "experiments/iclr2027/transfer.py", *common,
                               "--benchmark", case["benchmark"], "--benchmark-root", plan["benchmark_root"],
                               "--bootstrap-samples", "2000", *backend_args, "--methods", ",".join(selected)]
        else:
            plan["command"] = [sys.executable, "scripts/rebuttal_decoder_eval.py", *common,
                               "--decoder", case["decoder"], "--methods", ",".join(selected)]
    elif case["kind"] == "audit":
        plan["evidence_sha256"] = {name: file_sha(REPO / name) for name in case["evidence"]}
        plan["command"] = ["read_only_audit", case["id"]]
    else:
        if not args.task_file or len(args.evidence) < 2:
            raise ValueError("Semantic case needs --task-file and >=2 --evidence METHOD=/absolute/verified.jsonl")
        tasks = abs_path(args.task_file)
        ensure_nonoverlap(tasks, directory)
        inputs = []
        common_protocol = None
        for item in args.evidence:
            if "=" not in item:
                raise ValueError(f"Bad --evidence {item}; use METHOD=/path")
            name, value = item.split("=", 1)
            if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
                raise ValueError("Evidence method names must be lowercase identifiers")
            path = abs_path(value)
            ensure_nonoverlap(path, directory)
            identity = semantic_source_identity(path, tasks)
            ensure_nonoverlap(Path(identity["source_run"]), directory)
            if name != identity["source_method"]:
                raise ValueError("Semantic evidence method label differs from its native source arm")
            if common_protocol is not None and identity["common_protocol"] != common_protocol:
                raise ValueError("Semantic source arms have different native comparison protocols")
            common_protocol = identity["common_protocol"]
            inputs.append({"method": name, "path": str(path), "sha256": identity["verified_sha256"],
                           "source_identity": identity})
        if len({x["method"] for x in inputs}) != len(inputs):
            raise ValueError("Duplicate semantic method name")
        plan.update(semantic_inputs=inputs, semantic_common_protocol=common_protocol,
                    task_file=str(tasks), task_file_sha256=file_sha(tasks))
        plan["command"] = [sys.executable, "scripts/rebuttal_semantic_blind.py", "--plan", str(directory / "plan.json"),
                           "--output-dir", str(run_root)]
    plan["plan_fingerprint"] = digest(plan)
    # All validation is complete before publishing configuration or plan files.
    if cfg is not None:
        store_once(Path(plan["config_file"]), cfg)
    store_once(directory / "plan.json", plan)
    store_once(directory / "plan.sha256.json", {"sha256": file_sha(directory / "plan.json")})
    return plan


def read_plan(case: dict, args: argparse.Namespace, *, hashes: bool = True) -> dict:
    validate_unused_selectors(case, args)
    directory = abs_path(args.root) / case["id"]
    path = directory / "plan.json"
    plan = read_json(path)
    seal = read_json(directory / "plan.sha256.json")
    unsigned = {key: value for key, value in plan.items() if key != "plan_fingerprint"}
    if (directory.is_symlink() or (directory / "run").is_symlink()
            or file_sha(path) != seal.get("sha256") or digest(unsigned) != plan.get("plan_fingerprint")
            or plan["case"] != case or plan.get("spec_file_sha256") != file_sha(SPEC)
            or plan["case_spec_sha256"] != digest(case) or plan["protocol"] != load_spec()["protocol"]
            or plan["root"] != str(directory) or plan["output"] != str(directory / "run")):
        raise ValueError("Frozen plan, case specification or output root changed")
    if implementation_identity(case) != plan["implementation"]:
        raise ValueError("Executable source/config template changed since planning; choose a fresh root")
    if case["kind"] == "train":
        if plan["config_file"] != str(directory / "config.json"):
            raise ValueError("Frozen config path changed")
        cfg = read_json(Path(plan["config_file"]))
        if (digest(cfg) != plan["config_sha256"] or cfg["output_dir"] != plan["output"]
                or cfg["model"]["revision"] != read_json(ASSETS)["models"][case["model"]]["revision"]):
            raise ValueError("Frozen training config or pinned model changed")
        if verify_data(cfg, case) != plan["data_identity"]:
            raise ValueError("Prepared training data changed since planning")
        if model_identity(cfg["model"], hashes, plan["model_identity"]) != plan["model_identity"]:
            raise ValueError("Pinned local model changed since planning")
    elif case["kind"] in {"transfer", "decoder", "interpolate"}:
        source = Path(plan["source_run"])
        ensure_nonoverlap(source, directory)
        if args.source_run and abs_path(args.source_run) != source:
            raise ValueError("--source-run differs from the frozen plan")
        if args.source_methods and args.source_methods != plan["source_methods"]:
            raise ValueError("--source-methods differs from the frozen plan")
        identity = dependency_identity(source, plan["source_methods"].split(","), case["round"],
                                       hashes=hashes, frozen=plan["source_identity"])
        if identity != plan["source_identity"]:
            raise ValueError("Dependency source model/data/round/method identity changed since planning")
        if case["kind"] == "transfer" and benchmark_identity(Path(plan["benchmark_root"]), case["benchmark"]) != plan["benchmark_identity"]:
            raise ValueError("Prepared transfer benchmark changed since planning")
    elif case["kind"] == "audit":
        if {p: file_sha(REPO / p) for p in case["evidence"]} != plan["evidence_sha256"]:
            raise ValueError("Historic evidence changed since planning")
    else:
        if args.task_file and abs_path(args.task_file) != Path(plan["task_file"]):
            raise ValueError("--task-file differs from the frozen plan")
        if args.evidence and args.evidence != [f"{r['method']}={r['path']}" for r in plan["semantic_inputs"]]:
            raise ValueError("--evidence differs from the frozen plan")
        if file_sha(Path(plan["task_file"])) != plan["task_file_sha256"]:
            raise ValueError("Task pool changed since blind selection was frozen")
        if not isinstance(plan.get("semantic_common_protocol"), dict) or len(plan["semantic_inputs"]) < 2:
            raise ValueError("Semantic plan lacks qualified, comparable native source identities")
        if len({row["method"] for row in plan["semantic_inputs"]}) != len(plan["semantic_inputs"]):
            raise ValueError("Semantic plan has duplicate source arms")
        for row in plan["semantic_inputs"]:
            identity = semantic_source_identity(row["path"], plan["task_file"])
            ensure_nonoverlap(Path(identity["source_run"]), directory)
            if (identity != row.get("source_identity") or identity["verified_sha256"] != row["sha256"]
                    or identity["source_method"] != row["method"]
                    or identity["common_protocol"] != plan["semantic_common_protocol"]):
                raise ValueError("Semantic source identity or comparison protocol changed since plan freeze")
    return plan


@contextmanager
def lock(path: Path):
    """Hold one stable inode; the OS releases the lock after its last owner exits.

    The descriptor is passed to the owned worker so a killed wrapper cannot
    permit another same-case writer while that worker is still alive. Do not
    unlink this file or explicitly unlock the shared open-file description.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"Case already has an active writer: {path}") from exc
        token = f"pid={os.getpid()} token={uuid4().hex} acquired_at={now()}\n"
        os.ftruncate(fd, 0)
        os.write(fd, token.encode())
        os.fsync(fd)
        yield fd
    finally:
        os.close(fd)


def exact_records(path: Path, task_ids: list, samples: int) -> None:
    counts, seen = Counter(), set()
    expected = set(task_ids)
    for row in read_records(path):
        key = (row.get("task_id"), row.get("sample_id"))
        if (key[0] not in expected or type(key[1]) is not int or not 0 <= key[1] < samples
                or key in seen):
            raise ValueError(f"Unexpected or duplicate task/sample record: {path}")
        seen.add(key)
        counts[key[0]] += 1
    if set(counts) != expected or any(counts[key] != samples for key in expected):
        raise ValueError(f"Not exactly {len(expected)} x {samples} unique task/sample records: {path}")


def inspect_stage(stage: Path, task_ids: list, samples: int, *, hashes: bool,
                  trained: bool = False, base: bool = False, protocol_fingerprint: str | None = None) -> dict:
    required = EVAL_FILES | ({"train.jsonl", "training_stats.json", "model/config.json"} if trained else set())
    seal = sealed_files(stage, hashes=hashes, required=required, completed=not base, complete_inventory=trained)
    if trained and not any(name.startswith("model/") and name.endswith((".safetensors", ".bin")) for name in seal["files"]):
        raise ValueError("Retained full checkpoint weights are missing")
    if protocol_fingerprint and seal.get("protocol_fingerprint") != protocol_fingerprint:
        raise ValueError("Stage receipt belongs to another evaluation protocol")
    metrics = read_json(stage / "evaluation.metrics.json")
    aggregate, per_task = metrics.get("aggregate", {}), metrics.get("per_task", {})
    declared_samples = metrics.get("protocol", {}).get("expected_samples")
    expected_samples = {task_id: samples for task_id in task_ids}
    # Native evaluation records a task-to-count map. Historical scalar receipts
    # are allowed only with the exact population and per-task counts below.
    sample_contract_matches = (
        isinstance(declared_samples, dict) and declared_samples == expected_samples
        and all(type(value) is int for value in declared_samples.values())
    ) or (type(declared_samples) is int and declared_samples == samples)
    if (len(task_ids) != len(set(task_ids)) or set(per_task) != set(task_ids)
            or aggregate.get("task_count") != len(task_ids)
            or aggregate.get("sample_count") != len(task_ids) * samples
            or not sample_contract_matches
            or any(row.get("sample_count") != samples for row in per_task.values())):
        raise ValueError(f"Incorrect per-task evaluation population: {stage}")
    values = aggregate.get("pass_at_k", {})
    proxy = aggregate.get("implementation_proxy", {})
    coverage = proxy.get("coverage_at_k", {})
    if not all(key in values for key in ("1", "16", "64")) or "64" not in coverage:
        raise ValueError("Mandatory native pass/coverage metrics are missing")
    if hashes:
        exact_records(stage / "evaluation.jsonl", task_ids, samples)
        exact_records(stage / "evaluation.verified.jsonl", task_ids, samples)
    return metrics


def endpoints(metrics: dict) -> dict:
    aggregate = metrics["aggregate"]
    values = aggregate["pass_at_k"]
    proxy = aggregate["implementation_proxy"]
    matched = proxy.get("correct_matched_coverage_at_budgets", {}).get("4", {})
    return {"pass@1": values["1"]["mean"], "pass@16": values["16"]["mean"],
            "pass@64": values["64"]["mean"], "C64": proxy["coverage_at_k"]["64"]["mean"],
            "D4": matched.get("mean"), "D4_eligible": matched.get("eligible_tasks")}


def inspect_training(plan: dict, case: dict, hashes: bool = False) -> dict:
    root = Path(plan["output"])
    status = {"case": case["id"], "kind": "train", "state": "pending", "expected_rounds": case["rounds"],
              "verified_rounds": 0, "verified_stages": [], "issues": [], "endpoints": {}}
    if not root.exists():
        return status
    status["state"] = "partial"
    try:
        done = read_json(root / "run_status.json")
        if (done.get("status") != "completed" or done.get("verification") != "completed"
                or done.get("rounds") != case["rounds"] or done.get("methods") != [case["method"]]):
            raise ValueError("Native training has not sealed the declared full case")
        manifest = read_json(root / "manifest.json")
        if digest(manifest["config"]) != plan["config_sha256"]:
            raise ValueError("Native manifest configuration differs from this frozen case")
        task_ids = plan["data_identity"]["eval"]["task_ids"]
        snapshots = task_identity({name: root / "tasks" / f"{name}.jsonl" for name in DATA_COUNTS}, DATA_COUNTS)
        if any(snapshots[name]["task_ids"] != info["task_ids"]
               or manifest.get("selected_task_ids", {}).get(name) != info["task_ids"]
               for name, info in plan["data_identity"].items()):
            raise ValueError("Native task snapshots differ from the declared case population")
        if hashes:
            for name, info in plan["data_identity"].items():
                # The native writer normalizes JSONL whitespace; compare records as well as IDs.
                if digest(list(read_records(Path(info["path"])))) != digest(list(read_records(Path(snapshots[name]["path"])))):
                    raise ValueError(f"Native {name} task records differ from frozen inputs")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        status["issues"].append(str(exc))
        return status
    stages = [("base", False)] + [(f"{case['method']}/round_{r}", True) for r in range(1, case["rounds"] + 1)]
    for name, trained in stages:
        try:
            metrics = inspect_stage(root / name, task_ids, case["eval_samples"], hashes=hashes,
                                    trained=trained, base=not trained)
            if trained and hashes:
                exact_records(root / name / "train.jsonl", plan["data_identity"]["train"]["task_ids"], case["train_samples"])
            status["verified_stages"].append(name)
            status["verified_rounds"] += int(trained)
            if name.endswith(f"/round_{case['rounds']}"):
                status["endpoints"] = endpoints(metrics)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            status["issues"].append(f"{name}: {exc}")
    if not status["issues"] and len(status["verified_stages"]) == case["rounds"] + 1:
        status.update(state="complete", integrity="all_sealed_files_and_exact_records_checked" if hashes else "receipts_and_per_task_denominators_checked")
    return status


def inspect_eval(plan: dict, case: dict, hashes: bool = False) -> dict:
    out = Path(plan["output"])
    state = {"case": case["id"], "kind": case["kind"], "state": "pending", "issues": [], "stages": []}
    if not out.exists():
        return state
    state["state"] = "partial"
    try:
        marker = "transfer_complete.json" if case["kind"] == "transfer" else "decoder_complete.json"
        receipt = read_json(out / marker)
        manifest = read_json(out / "manifest.json")
        protocol = manifest["protocol"]
        selected = plan["source_identity"]["methods"]
        if (receipt.get("status") != "completed" or receipt.get("source_run") != plan["source_run"]
                or protocol.get("source_run") != plan["source_run"]
                or protocol.get("source_manifest_sha256") != plan["source_identity"]["manifest_sha256"]
                or protocol.get("methods") != selected or protocol.get("rounds") != [case["round"]]
                or protocol.get("include_base") is not True or manifest.get("fingerprint") != digest(protocol)
                or not backend_matches_plan(plan, protocol)):
            raise ValueError("Evaluation source, selected methods, round or runtime differs from the frozen case")
        if case["kind"] == "transfer":
            expected = plan["benchmark_identity"]["tasks"]
            if (receipt.get("benchmark") != case["benchmark"] or receipt.get("student_round") != case["round"]
                    or receipt.get("training_on_target") is not False or receipt.get("calibration_on_target") is not False):
                raise ValueError("Transfer summary does not establish frozen target-only evaluation")
        else:
            expected = plan["source_identity"]["data"]["eval"]
            if (receipt.get("round") != case["round"] or receipt.get("source_methods") != selected
                    or receipt.get("student_training_performed") is not False
                    or receipt.get("training_decoder_unchanged") is not True):
                raise ValueError("Decoder summary has a different source/round or performed training")
            if any(protocol["generation"].get(key) != value for key, value in DECODERS[case["decoder"]].items()):
                raise ValueError("Evaluation decoder differs from its case")
        task_ids = expected["task_ids"]
        if (protocol.get("task_ids") != task_ids or protocol.get("task_sha256") != expected["sha256"]
                or receipt.get("samples_per_task") != case["samples"]):
            raise ValueError("Evaluation task identity or sampling count differs from the plan")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        state["issues"].append(str(exc))
        return state
    for name in ["base", *[f"{method}/round_{case['round']}" for method in selected]]:
        try:
            inspect_stage(out / name, task_ids, case["samples"], hashes=hashes,
                          protocol_fingerprint=manifest["fingerprint"])
            state["stages"].append(name)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            state["issues"].append(f"{name}: {exc}")
    if not state["issues"] and len(state["stages"]) == len(selected) + 1:
        state.update(state="complete", integrity="all_sealed_files_and_exact_records_checked" if hashes else "receipts_and_per_task_denominators_checked")
    return state


def inspect_interpolation(plan: dict, case: dict, hashes: bool = False) -> dict:
    root = Path(plan["output"])
    status = {"case": case["id"], "kind": "interpolate", "state": "pending", "issues": []}
    if not root.exists():
        return status
    status["state"] = "partial"
    try:
        done = read_json(root / "interpolation_complete.json")
        manifest = read_json(root / "manifest.json")
        protocol = manifest["protocol"]
        expected = plan["source_identity"]["data"]["eval"]
        if (done.get("status") != "completed" or done.get("source_run") != plan["source_run"]
                or done.get("source_method") != case["method"] or done.get("source_round") != case["round"]
                or done.get("alpha") != case["alpha"] or done.get("training_performed") is not False
                or done.get("protocol_fingerprint") != manifest.get("fingerprint")
                or manifest.get("fingerprint") != digest(protocol)
                or protocol.get("source_run") != plan["source_run"]
                or protocol.get("source_manifest_sha") != plan["source_identity"]["manifest_sha256"]
                or protocol.get("source_method") != case["method"] or protocol.get("source_round") != case["round"]
                or protocol.get("alpha") != case["alpha"] or protocol.get("training_performed") is not False
                or protocol.get("eval_tasks_sha") != expected["sha256"] or protocol.get("tasks") != expected["task_ids"]
                or done.get("samples_per_task") != case["samples"] or done.get("task_count") != expected["count"]
                or not backend_matches_plan(plan, protocol)):
            raise ValueError("Interpolation source, alpha, round, task identity or runtime differs from its case")
        metrics = inspect_stage(root, expected["task_ids"], case["samples"], hashes=hashes,
                                protocol_fingerprint=manifest["fingerprint"])
        status.update(state="complete", endpoints=endpoints(metrics),
                      integrity="all_sealed_files_and_exact_records_checked" if hashes else "receipts_and_per_task_denominators_checked")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        status["issues"].append(str(exc))
    return status


def status_case(case: dict, args: argparse.Namespace) -> dict:
    path = abs_path(args.root) / case["id"] / "plan.json"
    if not path.is_file():
        return {"case": case["id"], "kind": case["kind"], "state": "unplanned", "historical_source_status": case["source_status"]}
    try:
        plan = read_plan(case, args, hashes=args.verify_hashes)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {"case": case["id"], "kind": case["kind"], "state": "blocked", "issues": [str(exc)],
                "historical_source_status": case["source_status"]}
    if case["kind"] == "train":
        data = inspect_training(plan, case, hashes=args.verify_hashes)
    elif case["kind"] in {"transfer", "decoder"}:
        data = inspect_eval(plan, case, hashes=args.verify_hashes)
    elif case["kind"] == "interpolate":
        data = inspect_interpolation(plan, case, hashes=args.verify_hashes)
    else:
        done = Path(plan["root"]) / "case_receipt.json"
        data = {"case": case["id"], "kind": case["kind"], "state": "planned"}
        if done.is_file():
            receipt = read_json(done)
            if receipt.get("status") == "completed" and receipt.get("plan_sha256") == file_sha(path):
                data["state"] = "historical_audit_only" if case["kind"] == "audit" else "annotation_packet_prepared"
    data.update(historical_source_status=case["source_status"], output=plan["output"])
    return data


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def execute_case(case: dict, args: argparse.Namespace) -> dict:
    plan = read_plan(case, args)
    if not args.execute:
        return {"case": case["id"], "dry_run": True, "command": plan["command"],
                "output": plan["output"], "source_status": case["source_status"]}
    if case["kind"] == "train" and case["source_status"].startswith("historical_complete") and not args.rerun_historical:
        raise ValueError("Historical case has archived evidence; use --rerun-historical to create an explicit fresh run")
    directory = Path(plan["root"])
    with lock(directory / "case.lock") as lock_fd:
        attempt = directory / "attempts" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid4().hex[:8])
        attempt.mkdir(parents=True, exist_ok=False)
        started = now()
        log = {"case": case["id"], "started_at": started, "command": plan["command"],
               "plan_sha256": file_sha(directory / "plan.json"), "implementation_sha256": plan["implementation"]["sha256"],
               "pid": os.getpid(), "stdout": str(attempt / "stdout.log"), "stderr": str(attempt / "stderr.log")}
        store_once(attempt / "started.json", log)
        returncode, failure, state = None, None, None
        try:
            with (attempt / "stdout.log").open("xb") as stdout, (attempt / "stderr.log").open("xb") as stderr:
                # Lock first, then recheck every dependency before executing a resume.
                read_plan(case, args)
                if case["kind"] == "audit":
                    returncode = 0
                    state = {"kind": "historical_evidence_audit", "no_new_experiment": True,
                             "evidence_files": plan["evidence_sha256"]}
                else:
                    process = subprocess.run(plan["command"], cwd=REPO, stdout=stdout, stderr=stderr,
                                             check=False, pass_fds=(lock_fd,))
                    returncode = process.returncode
                    if returncode:
                        raise RuntimeError(f"Case process exited {returncode}; logs: {attempt}")
                    # Refuse successful completion if files changed during the run.
                    read_plan(case, args)
                    if case["kind"] == "train":
                        state = inspect_training(plan, case, hashes=True)
                    elif case["kind"] in {"transfer", "decoder"}:
                        state = inspect_eval(plan, case, hashes=True)
                    elif case["kind"] == "interpolate":
                        state = inspect_interpolation(plan, case, hashes=True)
                    else:
                        state = {"kind": "blinded_annotation_packet", "manual_semantic_labels_not_collected": True}
                    if case["kind"] != "semantic" and state["state"] != "complete":
                        raise RuntimeError(f"Native completion checks failed: {state['issues']}")
            store_once(directory / "case_receipt.json", {
                "status": "completed", "case": case["id"], "kind": case["kind"],
                "plan_sha256": log["plan_sha256"], "verified": state,
                "historical_source_status": case["source_status"],
                "no_experiment_if_kind_is_audit_or_semantic": case["kind"] in {"audit", "semantic"}})
            return state
        except BaseException as exc:
            failure = {"type": type(exc).__name__, "message": str(exc)}
            raise
        finally:
            store_once(attempt / "exit.json", {**log, "ended_at": now(), "returncode": returncode,
                       "status": "completed" if failure is None else "failed", "error": failure,
                       "verified": state, "stdout_sha256": file_sha(attempt / "stdout.log") if (attempt / "stdout.log").is_file() else None,
                       "stderr_sha256": file_sha(attempt / "stderr.log") if (attempt / "stderr.log").is_file() else None})


def write_report(args: argparse.Namespace) -> dict:
    rows = [status_case(case, args) for case in load_spec()["cases"]]
    report = abs_path(args.root) / "report"
    report.mkdir(parents=True, exist_ok=True)
    (report / "cases.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
    with (report / "cases.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["case", "kind", "state", "historical_source_status", "output"])
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name) for name in writer.fieldnames})
    return {"report": str(report), "case_count": len(rows),
            "new_completed_training_cases": sum(r["state"] == "complete" and r["kind"] == "train" for r in rows),
            "missing_or_unfinished": [r["case"] for r in rows if r["state"] not in {"complete", "historical_audit_only", "annotation_packet_prepared"}]}


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", help="Fixed case ID from the current catalog")
    parser.add_argument("command", choices=["list", "plan", "run", "status", "report"])
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--data-root", default="data/mbpp")
    parser.add_argument("--benchmark-root", default="data/iclr2027")
    parser.add_argument("--model-root", help="Optional local pinned HF model root")
    parser.add_argument("--profile", choices=["24gb", "80gb"], default="80gb")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--source-run", help="Frozen, sealed MBPP source experiment directory")
    parser.add_argument("--source-methods", help="Comma-separated exact selected source method names")
    parser.add_argument("--task-file", help="Full immutable evaluation task JSONL, semantic case")
    parser.add_argument("--evidence", action="append", default=[], help="Verified code path: METHOD=/abs/path/to/evaluation.verified.jsonl")
    parser.add_argument("--execute", action="store_true", help="Only explicit flag can launch a case")
    parser.add_argument("--verify-hashes", action="store_true", help="Inspect every sealed file and every task/sample ID")
    parser.add_argument("--rerun-historical", action="store_true", help="Explicitly reproduce a fully archived historical study in a fresh root")
    parser.add_argument("--eval-backend", choices=["bwrap", "local"], default="bwrap",
                        help="Native evaluation isolation: bwrap sandbox (default) or "
                             "unsafe local execution for hosts without user namespaces")
    return parser


def main(argv=None) -> int:
    tokens = list(sys.argv[1:] if argv is None else argv)
    try:
        if sum(token == "--case" or token.startswith("--case=") for token in tokens) > 1:
            raise ValueError("A wrapper's fixed --case cannot be overridden with another selector")
        args = make_parser().parse_args(tokens)
        if args.execute and args.command != "run":
            raise ValueError("--execute is only valid for run")
        if args.command == "list":
            if args.case:
                raise ValueError("list enumerates the full catalog; use status for a selected case")
            print(json.dumps(load_spec()["cases"], indent=2, ensure_ascii=False))
            return 0
        if args.command == "report":
            if args.case:
                raise ValueError("report covers all cases; use status for a selected case")
            result = write_report(args)
        else:
            case = one_case(args.case)
            if args.command == "plan":
                result = build_plan(case, args)
            elif args.command == "run":
                result = execute_case(case, args)
            else:
                result = status_case(case, args)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError, ImportError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(f"ICLR rebuttal case error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
