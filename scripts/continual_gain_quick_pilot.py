#!/usr/bin/env python3
"""Shorter matched-task pilot for cg02 retention versus cg03 conflict."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO / "scripts" / "continual_gain_pilot.py"
PROTOCOL = "spectrum-continual-gains-quick-pilot-v1"
DEFAULT_ROOT = Path(
    "/mnt/c/ai/spectrum-run-artifacts/20261109/continual-gain-pilot-quick-v1")
TASKS_PER_DOMAIN = 32
SELECTION_SEED = "spectrum-continual-gain-quick-pilot-20261109"
TOKEN_LIMITS = {"math": 1024, "qa": 128}


def _load_base_runner():
    spec = importlib.util.spec_from_file_location("continual_gain_pilot_base", BASE_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load shared pilot runner: {BASE_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.TASK_COUNT = TASKS_PER_DOMAIN
    module.SELECTION_SEED = SELECTION_SEED
    module.PILOT_PROTOCOL = PROTOCOL
    module.DEFAULT_ROOT = DEFAULT_ROOT

    original_select = module.select_task_ids

    def select_quick_tasks(rows, count=None, seed=None, group_key="category"):
        return original_select(
            rows,
            count=TASKS_PER_DOMAIN if count is None else count,
            seed=SELECTION_SEED if seed is None else seed,
            group_key=group_key,
        )

    module.select_task_ids = select_quick_tasks
    original_load_inputs = module._load_inputs

    def load_quick_inputs(root):
        configs = original_load_inputs(root)
        for config in configs.values():
            for domain, token_limit in TOKEN_LIMITS.items():
                config["domains"][domain]["evaluation"]["max_new_tokens"] = token_limit
        return configs

    module._load_inputs = load_quick_inputs

    original_write_once = module.write_once

    def write_quick_report(path, value):
        if Path(path).name == "pilot_report.json":
            value = dict(value)
            value["interpretation"] = (
                "Exploratory quick pilot; one trajectory, 32 stratified tasks per domain, "
                "Math max_new_tokens=1024, QA max_new_tokens=128.")
        return original_write_once(path, value)

    module.write_once = write_quick_report
    return module


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write_plan_identity(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def plan(root=DEFAULT_ROOT, inputs=None):
    root = Path(root)
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"Quick-pilot output root must be empty: {root}")
    base = _load_base_runner()
    inputs = Path(inputs) if inputs else base.INPUT_ROOT
    manifest = base.plan(root, inputs)
    manifest["quick_runner_sha256"] = _sha256(Path(__file__))
    manifest["tasks_per_domain"] = TASKS_PER_DOMAIN
    manifest["evaluation"] = (
        "32 deterministic stratified tasks per domain; one sample each; shared RNG group; "
        "Math max_new_tokens=1024 and QA max_new_tokens=128")
    _write_plan_identity(root / "pilot_plan.json", manifest)
    return manifest


def _validate_plan(root, base):
    manifest = base.load_plan(root)
    if manifest.get("quick_runner_sha256") != _sha256(Path(__file__)):
        raise ValueError("Quick-pilot runner changed; prepare a fresh output root")
    if manifest.get("tasks_per_domain") != TASKS_PER_DOMAIN:
        raise ValueError("Unexpected task count in quick-pilot plan")
    config = base.read_json(Path(root) / "cg02" / "config.json")
    for domain, token_limit in TOKEN_LIMITS.items():
        if config["domains"][domain]["evaluation"]["max_new_tokens"] != token_limit:
            raise ValueError(f"Unexpected {domain} generation limit in quick-pilot config")
    return manifest


def run(root=DEFAULT_ROOT, *, execute=False, resume=False):
    base = _load_base_runner()
    _validate_plan(root, base)
    return base.run(root, execute=execute, resume=resume)


def report(root=DEFAULT_ROOT):
    base = _load_base_runner()
    _validate_plan(root, base)
    return base.report(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run", "report"))
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.command == "plan":
        result = plan(args.root, args.inputs)
    elif args.command == "run":
        result = run(args.root, execute=args.execute, resume=args.resume)
    else:
        result = report(args.root)
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
