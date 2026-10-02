"""Data-only final-protocol preparation with immutable assets and count gates.

No model is instantiated, no weights downloaded, and no candidate/reference
program executed here. All output-derived files are outside this API's inputs.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .benchmarks import BENCHMARKS, HF_REPOSITORIES, HUMANEVAL_RELEASE, prepare_benchmark
from .data import read_jsonl
from .utils import atomic_json, stable_hash

MODEL_ALIASES = ("qwen1.5b", "qwen3b", "qwen7b", "deepseek6.7b")
EXPECTED_COUNTS = {"mbpp": 500, "humanevalplus": 164, "apps_intro": 200,
                   "codecontests": 165, "livecodebench": 200}
MBPP_COUNTS = {"train": 291, "calibration": 50, "validation": 30, "eval": 500}


def load_final_assets(path: str | Path) -> dict[str, Any]:
    """Reject branches, truncated commits, accidental dataset/model substitutions."""
    assets = json.loads(Path(path).read_text(encoding="utf-8"))
    if assets.get("protocol") != "spectrum-final-data-v1" or assets.get("schema_version") != 1:
        raise ValueError("Unsupported final asset protocol/schema")
    if set(assets.get("models", {})) != set(MODEL_ALIASES):
        raise ValueError("Final assets must contain exactly the four trained backbone aliases")
    if set(assets.get("datasets", {})) != set(BENCHMARKS):
        raise ValueError("Final assets must contain exactly the five evaluation datasets")
    expected_models = {
        "qwen1.5b": "Qwen/Qwen2.5-Coder-1.5B-Instruct",
        "qwen3b": "Qwen/Qwen2.5-Coder-3B-Instruct",
        "qwen7b": "Qwen/Qwen2.5-Coder-7B-Instruct",
        "deepseek6.7b": "deepseek-ai/deepseek-coder-6.7b-instruct",
    }
    for alias, model in assets["models"].items():
        if model.get("repo_id") != expected_models[alias]:
            raise ValueError(f"{alias}: unexpected final backbone")
        if not re.fullmatch(r"[0-9a-f]{40}", str(model.get("revision", ""))):
            raise ValueError(f"{alias}: final models require an immutable full commit SHA")
        if model.get("trust_remote_code") is not False:
            raise ValueError(f"{alias}: final loader does not enable remote code")
    for name, spec in assets["datasets"].items():
        if name == "humanevalplus":
            if spec.get("revision") != HUMANEVAL_RELEASE or spec.get("evalplus_version") != "0.3.1":
                raise ValueError("HumanEval+ requires fixture v0.1.10 and evalplus==0.3.1")
        elif (spec.get("repo_id") != HF_REPOSITORIES[name] or
              not re.fullmatch(r"[0-9a-f]{40}", str(spec.get("revision", "")))):
            raise ValueError(f"{name}: final datasets require the official repository and full commit SHA")
        if spec.get("expected_count") != EXPECTED_COUNTS[name]:
            raise ValueError(f"{name}: population differs from the final protocol")
        expected_limit = 200 if name in {"apps_intro", "livecodebench"} else None
        if spec.get("limit") != expected_limit:
            raise ValueError(f"{name}: incorrect final population limit")
        directory = "mbpp" if name == "mbpp" else f"benchmarks/{name}"
        if spec.get("directory") != directory:
            raise ValueError(f"{name}: expected final data directory {directory}")
    if assets["datasets"]["mbpp"].get("expected_split_counts") != MBPP_COUNTS:
        raise ValueError("MBPP requires train291/calibration50/validation30/eval500")
    lcb = assets["datasets"]["livecodebench"]
    if (lcb.get("release"), lcb.get("start_date"), lcb.get("end_date")) != (
            "release_v5", "2024-07-01", "2025-01-01"):
        raise ValueError("LiveCodeBench final release and half-open date window changed")
    return assets


def prepare_final_data(assets_path: str | Path, output_dir: str | Path, *,
                       split_seed: int) -> dict[str, Any]:
    """Prepare exact populations with a caller-provided, privately recorded seed."""
    if type(split_seed) is not int or split_seed < 0:
        raise ValueError("split_seed must be an explicit nonnegative integer")
    assets = load_final_assets(assets_path)
    root = Path(output_dir).resolve()
    lock = root / "assets.lock.json"
    if lock.is_file() and json.loads(lock.read_text()) != assets:
        raise ValueError("Final assets changed; use a new output directory")
    # Freeze source revisions and population policy before any downloads.
    atomic_json(lock, assets)
    registry = {"protocol": "spectrum-final-data-v1", "training_dataset": "mbpp",
                "assets_sha256": stable_hash(assets), "benchmarks": {}}
    for name in BENCHMARKS:
        spec = assets["datasets"][name]
        directory = root / spec["directory"]
        exclusions = [] if name == "mbpp" else [root / "mbpp" / f"{split}.jsonl"
                            for split in ("train", "calibration", "validation")]
        kwargs = {}
        if name == "livecodebench":
            kwargs = {"lcb_release": spec["release"], "lcb_start_date": spec["start_date"],
                      "lcb_end_date": spec["end_date"]}
        manifest = prepare_benchmark(name, directory, revision=spec["revision"],
            seed=split_seed, calibration_size=50, validation_size=30,
            limit=spec["limit"], exclusions_from=exclusions,
            expected_count=spec["expected_count"],
            expected_split_counts=MBPP_COUNTS if name == "mbpp" else None,
            # Preserve the full official MBPP/HumanEval+/CodeContests populations.
            # Any overlap aborts; APPS/LCB remove exact overlap before fixed sampling.
            reject_training_overlap=name == "codecontests", **kwargs)
        tasks_path = directory / "eval.jsonl"
        registry["benchmarks"][name] = {
            "directory": str(directory), "tasks": str(tasks_path),
            "manifest": str(directory / "manifest.json"),
            "task_count": manifest["output_files"]["eval.jsonl"]["count"],
            "evaluation_backend": manifest["evaluation_backend"],
            "evaluation_protocols": manifest["evaluation_protocols"],
            "evaluation_label": spec["evaluation_label"],
            "revision": spec["revision"], "request_sha256": manifest["request_sha256"],
            "tasks_sha256": manifest["output_files"]["eval.jsonl"]["sha256"],
            "manifest_sha256": hashlib.sha256((directory / "manifest.json").read_bytes()).hexdigest(),
        }
    # Cross-target overlap is reported, never used to change a fixed denominator.
    from .data import prompt_fingerprint
    seen, overlaps = {}, []
    for name, entry in registry["benchmarks"].items():
        for task in read_jsonl(entry["tasks"]):
            fingerprint = prompt_fingerprint(task.get("original_prompt", task["prompt"]))
            for previous in seen.get(fingerprint, []):
                if previous["benchmark"] != name:
                    overlaps.append({"left": previous, "right": {"benchmark": name,
                        "task_id": task["task_id"]}, "prompt_fingerprint": fingerprint})
            seen.setdefault(fingerprint, []).append({"benchmark": name, "task_id": task["task_id"]})
    audit = {"protocol": "normalized-exact-prompts-v1", "cross_evaluation_overlaps": overlaps,
             "training_overlap_policy": "exclude before APPS/LCB selection; abort for full official test populations",
             "limits": "Does not establish absence of paraphrase, solution, or model-pretraining contamination",
             "outcome_dependent_selection": False, "candidate_program_execution": False}
    atomic_json(root / "contamination_audit.json", audit)
    registry["contamination_audit"] = str(root / "contamination_audit.json")
    registry["complete"] = True
    atomic_json(root / "benchmark_registry.json", registry)
    return registry
