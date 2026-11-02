#!/usr/bin/env python3
"""Prepare and evaluate frozen cross-family learned-SPECTRUM checkpoints.

Additional code-domain transfer: APPS Intro, CodeContests and LiveCodeBench.
HumanEval+ is already covered by run_crossfamily_study.py transfer.
This module NEVER trains on transfer tasks and never uses target tests as labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
BENCHMARKS = ("apps_intro", "codecontests", "livecodebench")
MODELS = ("qwen7b", "llama8b", "deepseek6.7b")
EXPECTED = {"apps_intro": 200, "codecontests": 165, "livecodebench": 200}


def full_path(value):
    p = Path(value).expanduser()
    return (p if p.is_absolute() else ROOT / p).resolve()


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def choice(value, allowed, label):
    selected = list(allowed) if value == "all" else [value]
    if not selected or any(v not in allowed for v in selected):
        raise ValueError(f"Invalid {label}: {value}")
    return selected


def crossfamily(args):
    manifest = load(full_path(args.crossfamily_root) / "plan" / "manifest.json")
    methods = manifest["settings"]["methods"]
    if ("spectral_learned" not in methods or
            methods != ["plain", "ssd", "spectral_soft", "spectral_learned"] or
            manifest["settings"]["generation"]["max_new_tokens"] != 4096):
        raise ValueError("Requires the sealed new cross-family 4096-token learned study")
    if not manifest.get("source_files") or not manifest.get("config_files"):
        raise ValueError("Incomplete cross-family source manifest")
    return manifest


def _asset_inputs(args):
    from improving.final_data import load_final_assets
    mapping = load_final_assets(full_path(args.assets))
    cross = crossfamily(args)
    mbpp = Path(cross["data_root"]) / "mbpp"
    fit_paths = [mbpp / f"{key}.jsonl" for key in ("train", "calibration", "validation")]
    if any(not p.is_file() for p in fit_paths):
        raise FileNotFoundError("Prepare the cross-family MBPP splits first")
    return mapping, cross, fit_paths


def prepare(args):
    """Pin published task populations before any learned checkpoint is evaluated."""
    from improving.benchmarks import prepare_benchmark
    from improving.utils import atomic_json, stable_hash
    mapping, cross, fit_paths = _asset_inputs(args)
    seed = json.loads(Path(cross["seed_file"]).read_text())["data_seed"]
    output = full_path(args.data_root)
    records = {}
    for name in BENCHMARKS:
        spec = mapping["datasets"][name]
        extras = {}
        if name == "livecodebench":
            extras.update(lcb_release=spec["release"], lcb_start_date=spec["start_date"],
                          lcb_end_date=spec["end_date"])
        folder = output / name
        meta = prepare_benchmark(name, folder, revision=spec["revision"],
                                 seed=seed, calibration_size=50, validation_size=30,
                                 limit=spec["limit"], exclusions_from=fit_paths,
                                 expected_count=EXPECTED[name],
                                 reject_training_overlap=(name == "codecontests"), **extras)
        records[name] = {
            "tasks": str(folder / "eval.jsonl"),
            "tasks_sha256": sha(folder / "eval.jsonl"),
            "manifest_sha256": sha(folder / "manifest.json"),
            "count": meta["output_files"]["eval.jsonl"]["count"],
            "label": spec["evaluation_label"],
            "revision": spec["revision"],
            "evaluation_backend": meta["evaluation_backend"],
        }
    receipt = {
        "protocol": "learned-crossfamily-extra-transfers-v1",
        "assets_sha256": stable_hash(mapping),
        "seed_sha256": sha(cross["seed_file"]),
        "fit_split_sha256": {p.name: sha(p) for p in fit_paths},
        "transfer_benchmarks": records, "training_on_transfer": False,
        "native_execution": False,
    }
    dest = output / "prepared.json"
    if dest.exists():
        if load(dest) != receipt:
            raise ValueError("Prepared transfer identity changed; use a fresh data root")
    else:
        atomic_json(dest, receipt)
    return receipt


def verify(args):
    """Full metadata/source/task-hash verification without executing code."""
    from improving.utils import stable_hash
    mapping, cross, fit_paths = _asset_inputs(args)
    root = full_path(args.data_root)
    receipt = load(root / "prepared.json")
    if (receipt.get("protocol") != "learned-crossfamily-extra-transfers-v1"
            or receipt.get("training_on_transfer") is not False
            or receipt["assets_sha256"] != stable_hash(mapping)
            or receipt["seed_sha256"] != sha(cross["seed_file"])
            or receipt["fit_split_sha256"] != {p.name: sha(p) for p in fit_paths}
            or set(receipt["transfer_benchmarks"]) != set(BENCHMARKS)):
        raise ValueError("Frozen extra transfer identity or train/test separation changed")
    for name, entry in receipt["transfer_benchmarks"].items():
        if (entry["count"] != EXPECTED[name]
                or sha(entry["tasks"]) != entry["tasks_sha256"]
                or sha(root / name / "manifest.json") != entry["manifest_sha256"]
                or entry["evaluation_backend"] != "builtin"):
            raise ValueError(f"{name}: official transfer task files changed")
    return cross, receipt


def plan(args):
    cross, receipt = verify(args)
    return {
        "status": "planned_not_run", "training_root": str(full_path(args.crossfamily_root)),
        "models": choice(args.model, MODELS, "model"),
        "datasets": choice(args.dataset, BENCHMARKS, "dataset"),
        "methods": ["base", *cross["settings"]["methods"]],
        "num_tasks": {name: receipt["transfer_benchmarks"][name]["count"]
                      for name in choice(args.dataset, BENCHMARKS, "dataset")},
        "samples_per_task": int(args.samples),
        "source_round": int(cross["settings"]["rounds"]),
        "real_verification": "required; no training on evaluation targets",
    }


def run(args):
    from improving.longitudinal import evaluate_checkpoints, export_longitudinal
    cfg, receipt = verify(args)
    result = []
    for alias in choice(args.model, MODELS, "model"):
        source = Path(cfg["run_root"]) / "jobs" / alias
        for method in cfg["settings"]["methods"]:
            if not (source / method / f"round_{cfg['settings']['rounds']}" / "model" / "config.json").is_file():
                raise ValueError(f"Missing retained {alias}/{method} final checkpoint")
        if not (source / "base" / "complete.json").is_file():
            raise ValueError(f"Missing original base evaluation: {alias}")
        for name in choice(args.dataset, BENCHMARKS, "dataset"):
            output = full_path(args.crossfamily_root) / "transfer_extra" / alias / name
            records = evaluate_checkpoints(
                source, output, samples=args.samples,
                rounds=[cfg["settings"]["rounds"]],
                methods=list(cfg["settings"]["methods"]),
                eval_tasks_path=receipt["transfer_benchmarks"][name]["tasks"],
                generation_overrides={
                    "max_prompt_tokens": args.max_prompt_tokens,
                    "max_new_tokens": args.max_new_tokens,
                    "batch_size": 1, "sequence_batch_size": 1, "task_batch_size": 1,
                },
                evaluation_overrides={
                    "backend": cfg["settings"]["evaluation"]["backend"],
                    "allow_unsafe_local": cfg["settings"]["evaluation"].get("allow_unsafe_local", False),
                },
                bootstrap_samples=2000, resume=True)
            if records.get("status") != "completed":
                raise RuntimeError(f"Incomplete {alias}/{name} transfer: {records}")
            export_longitudinal(output, bootstrap_samples=2000)
            result.append({"model": alias, "dataset": name, "status": "completed",
                           "output_dir": str(output),
                           "official_leaderboard": False})
    return {"results": result, "training_on_transfer": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "plan", "run"))
    parser.add_argument("--assets", default="configs/final/assets.json")
    parser.add_argument("--crossfamily-root", default="runs/crossfamily_learned_r5_4096")
    parser.add_argument("--data-root", default="data/crossfamily_learned_transfers")
    parser.add_argument("--model", choices=("all", *MODELS), default="all")
    parser.add_argument("--dataset", choices=("all", *BENCHMARKS), default="all")
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--max-new-tokens", type=int, default=4096)
    parser.add_argument("--max-prompt-tokens", type=int, default=4096)
    args = parser.parse_args()
    if args.samples < 1 or args.max_new_tokens < 1 or args.max_prompt_tokens < 1:
        parser.error("Positive sample and token counts are required")
    result = {"prepare": prepare, "plan": plan, "run": run}[args.command](args)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
