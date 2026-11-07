#!/usr/bin/env python3
"""ICLR 2027 SPECTRUM: one case == one frozen config, process and output root.

stdlib-only preview/plan/status. Only 'run --execute' imports the native CUDA
pipeline as a subprocess. Archived evidence is never silently retrained.
No GUI/PI, per-token reweighting, beta-LoRA scaling or reward filtering.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "configs/rebuttal_cases_20261107/cases.json"
MODEL_ASSETS = ROOT / "configs/final/assets.json"
DATA_COUNTS = {"train": 291, "calibration": 50, "validation": 30, "eval": 500}
INPUT_SOURCES = [
    CASES_PATH, MODEL_ASSETS, ROOT / "scripts/run_iclr2027.py",
    ROOT / "src/improving/pipeline.py",
    ROOT / "src/improving/training.py",
    ROOT / "src/improving/spectral.py",
]

def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def sha(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def dump(path: Path, item):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("x", encoding="utf-8") as f:
        json.dump(item, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write("\n")
    os.replace(tmp, path)

def immutable(path: Path, item):
    if path.exists():
        if read(path) != item:
            raise ValueError(f"Sealed plan/config differs: {path}; choose a new root")
    else:
        dump(path, item)

def registry():
    data = read(CASES_PATH)
    if data["protocol"] != "SPECTRUM_ICLR2027_ISOLATED_CASES_V1":
        raise ValueError("Unexpected case manifest protocol")
    cases = data["cases"]
    if len(cases) != len({c["id"] for c in cases}):
        raise ValueError("Duplicate case ID")
    return {c["id"]: c for c in cases}

def data_identity(data_root: Path):
    paths = {k: data_root / f"{k}.jsonl" for k in DATA_COUNTS}
    seen_ids, seen_prompts, report = set(), set(), {}
    for split, path in paths.items():
        ids, prompts, count = set(), set(), 0
        with path.open(encoding="utf-8") as f:
            for no, line in enumerate(f, 1):
                if not line.strip():
                    continue
                obj = json.loads(line)
                task_id, prompt = obj.get("task_id"), obj.get("prompt")
                if not isinstance(task_id, str) or not task_id:
                    raise ValueError(f"Bad task ID: {path}:{no}")
                if not isinstance(prompt, str) or not prompt.strip():
                    raise ValueError(f"Bad task prompt: {path}:{no}")
                key = " ".join(prompt.split())
                if task_id in ids or key in prompts or task_id in seen_ids or key in seen_prompts:
                    raise ValueError(f"Leaked or duplicated task: {path}:{no}")
                if split == "calibration" and not obj.get("reference"):
                    raise ValueError(f"Missing calibration reference {path}:{no}")
                ids.add(task_id); prompts.add(key); count += 1
        if count != DATA_COUNTS[split]:
            raise ValueError(f"{split}: found {count}; expected {DATA_COUNTS[split]}")
        seen_ids.update(ids); seen_prompts.update(prompts)
        report[split] = {"path": str(path.resolve()), "count": count, "sha256": sha(path)}
    return report

def native_case_config(case, args, run_output: Path, data_root: Path):
    # Existing pinned, tested, stdlib-only initial protocol. No new learning math.
    s = importlib.util.spec_from_file_location("iclr2027_case_native_config",
                                                ROOT / "scripts/run_iclr2027.py")
    module = importlib.util.module_from_spec(s)
    s.loader.exec_module(module)
    a = SimpleNamespace(profile=args.profile, data_root=str(data_root),
                        backend="docker", allow_unsafe_local=False, workers=4)
    cfg = module.native_config(a, case["model"], case["seed"])
    asset = read(MODEL_ASSETS)["models"][case["model"]]
    cfg["model"]["revision"] = asset["revision"]
    cfg["methods"] = [case["method"]]
    cfg["rounds"] = case["rounds"]
    cfg["output_dir"] = str(run_output)
    cfg["checkpoint_retention"] = "all"
    cfg["generation"]["train_samples"] = 16
    cfg["generation"]["eval_samples"] = 64
    cfg["generation"]["max_new_tokens"] = 512
    cfg["train"]["loss_scope"] = "all"
    cfg["calibration"]["max_examples"] = 50
    cfg["calibration"]["layers"] = None  # original middle+last setting
    cfg["calibration"]["tau"] = 1.0
    cfg["diagnostics"]["evaluate_generation_policy"] = False
    overrides = case.get("overrides", {})
    allowed = {"fixed_anchor_replay", "reestimate_each_round", "max_examples",
               "tau", "temperature", "eval_samples"}
    if set(overrides) - allowed:
        raise ValueError(f"Unrecognized/unreviewed case override: {case['id']}")
    for key, value in overrides.items():
        if key == "fixed_anchor_replay":
            cfg["train"]["fixed_anchor_replay"] = value
        elif key == "reestimate_each_round":
            cfg["calibration"]["reestimate_each_round"] = value
        elif key in {"max_examples", "tau"}:
            cfg["calibration"][key] = value
        elif key == "temperature":
            cfg["generation"]["temperature"] = value
        elif key == "eval_samples":
            cfg["generation"]["eval_samples"] = value
    cfg["label"] = f"iclr2027_{case['id']}"
    return cfg

def source_identity():
    return {str(p.relative_to(ROOT)): sha(p) for p in INPUT_SOURCES}

def case_dir(args, case):
    root = Path(args.root).expanduser().resolve()
    path = (root / "cases" / case["id"]).resolve()
    if root == Path("/") or not path.is_relative_to(root):
        raise ValueError("Invalid experiment root")
    return path

def plan(case, args):
    if case["mode"] != "train":
        return {"case": case["id"], "status": "archived_evidence_only",
                "note": case["purpose"], "new_run_started": False}
    target = case_dir(args, case)
    if (target / "output").exists() and not (target / "plan.json").exists():
        raise ValueError("Unsealed case output exists; refusing to adopt")
    ds = data_identity(Path(args.data_root).expanduser().resolve())
    cfg = native_case_config(case, args, target / "output",
                             Path(args.data_root).expanduser().resolve())
    plan_item = {"protocol": "iclr2027_case_frozen_v1", "case": case,
                 "source_sha256": source_identity(), "dataset": ds,
                 "profile": args.profile, "config_sha256": hashlib.sha256(
                     (json.dumps(cfg, sort_keys=True, separators=(",", ":")) + "\n").encode()
                 ).hexdigest(),
                 "output_dir": cfg["output_dir"],
                 "state": "planned_not_executed"}
    # A complete case plan is immutable: no changing seeds after seeing outcomes.
    immutable(target / "config.json", cfg)
    immutable(target / "plan.json", plan_item)
    return {"case": case["id"], "status": "planned_not_executed",
            "config": str(target / "config.json"), "output": str(target / "output"),
            "data": {k: v["count"] for k, v in ds.items()},
            "command": f"python scripts/rebuttal_cases/{case['id']}.py run --execute",
            "expected_training_records": 291 * 16 * case["rounds"],
            "expected_native_test_draws": 500 * 64 * (1 + case["rounds"])}

def verify_plan(case, args):
    target = case_dir(args, case)
    cfg, plan_item = read(target / "config.json"), read(target / "plan.json")
    if plan_item["case"] != case or cfg != native_case_config(
            case, args, target / "output",
            Path(args.data_root).expanduser().resolve()):
        raise ValueError("Config mismatch; source or runtime settings changed")
    if plan_item["source_sha256"] != source_identity():
        raise ValueError("Source code drift since case was planned; new root required")
    if plan_item["dataset"] != data_identity(Path(args.data_root).expanduser().resolve()):
        raise ValueError("Dataset identity drift; new root required")
    return cfg, target

@contextmanager
def exclusive(path: Path):
    # Other unrelated cases may run on separate GPUs, same case may not overlap.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(f"pid={os.getpid()}\n")
        yield
    finally:
        # Never erase a lock owned by another process.
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        if text == f"pid={os.getpid()}\n":
            path.unlink()

def run(case, args):
    if case["mode"] != "train":
        raise ValueError(f"{case['id']} is archive-only; do not retrain its historical result")
    if not args.execute:
        return {"case": case["id"], "status": "dry_run",
                "action": "Use run --execute after verifying the frozen plan"}
    cfg, path = verify_plan(case, args)
    with exclusive(path / "run.lock"):
        command = [sys.executable, "-m", "improving", "run",
                   "--config", str(path / "config.json"), "--resume"]
        receipt = {"case": case["id"], "command": command,
                   "working_dir": str(ROOT), "started_utc_epoch": time.time(),
                   "config_sha256": sha(path / "config.json"),
                   "status": "running", "gpu_started": True}
        dump(path / "run_receipt.json", receipt)
        with (path / "run.log").open("a", encoding="utf-8") as log:
            p = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                               check=False)
        receipt.update(exit_code=p.returncode,
                       ended_utc_epoch=time.time(),
                       status=("process_exited_zero_verify_complete_artifacts"
                               if p.returncode == 0 else "process_failed"))
        dump(path / "run_receipt.json", receipt)
        if p.returncode != 0:
            raise RuntimeError(f"Case {case['id']} failed with {p.returncode}. Inspect {path/'run.log'}")
    return status(case, args)

def status(case, args):
    if case["mode"] == "archive":
        # Never classify old unimported evaluation as verified from a named job.
        return {"case": case["id"], "status": "archived_requires_local_receipt_check",
                "purpose": case["purpose"], "new_run_started": False}
    target = case_dir(args, case)
    plan_path = target / "plan.json"
    if not plan_path.exists():
        return {"case": case["id"], "status": "not_planned"}
    if not (target / "output" / "run_status.json").exists():
        receipt = target / "run_receipt.json"
        return {"case": case["id"], "status": "not_verified_complete",
                "process": read(receipt) if receipt.exists() else None}
    state = read(target / "output" / "run_status.json")
    method = case["method"]
    final = target / "output" / method / f"round_{case['rounds']}"
    metrics = final / "evaluation.metrics.json"
    complete = final / "complete.json"
    verified = (state.get("status") == "completed"
                and state.get("verification") == "completed"
                and metrics.exists() and complete.exists())
    return {"case": case["id"],
            "status": "completed_with_native_metric_receipt" if verified else "not_verified_complete",
            "native_round": case["rounds"], "run_status": state.get("status"),
            "verification": state.get("verification"),
            "metrics_file": str(metrics) if metrics.exists() else None,
            "complete_file": str(complete) if complete.exists() else None,
            "warning": "A filename check is not a re-execution of task verifiers; native source receipts govern correctness."}

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["preview", "plan", "run", "status"])
    p.add_argument("--case", required=True)
    p.add_argument("--root", default="runs/iclr2027_rebuttal_isolated_v1")
    p.add_argument("--data-root", default="data/mbpp")
    p.add_argument("--profile", choices=["24gb", "80gb"], default="80gb")
    p.add_argument("--execute", action="store_true")
    args = p.parse_args(argv)
    cases = registry()
    if args.case not in cases:
        p.error(f"Unknown case {args.case}; choose {', '.join(cases)}")
    case = cases[args.case]
    if args.command != "run" and args.execute:
        p.error("--execute is only accepted for run")
    try:
        if args.command == "preview":
            result = {"case": case, "cost_note": "512-token original protocol; 4096 historical experiments are separate"}
        elif args.command == "plan":
            result = plan(case, args)
        elif args.command == "run":
            result = run(case, args)
        else:
            result = status(case, args)
    except (ValueError, FileNotFoundError, FileExistsError, OSError, RuntimeError) as exc:
        print(f"{case['id']}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
