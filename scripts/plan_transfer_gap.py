#!/usr/bin/env python3
"""Pretraining-free transfer-gap evaluation cost estimate from the frozen config."""
import json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
cfg = yaml.safe_load((ROOT/"configs/spectrum_7b/transfer_gap_learned_4096.yaml").read_text())
scope = cfg["diagnostics"]["transfer_gap"]
roles = ("pre_native", "pre_spectral", "post_native")
n = len(scope["rounds"]) * scope["validation_task_count"] * scope["samples"] * len(roles)
print(json.dumps({
    "status": "plan_only",
    "development_rounds": scope["rounds"],
    "development_tasks": scope["validation_task_count"],
    "samples_per_policy_state": scope["samples"],
    "states": roles,
    "extra_development_completions": n,
    "max_new_tokens_each": scope["max_new_tokens"],
    "additional_reference_NLL_measurements": cfg["rounds"],
    "existing_base_and_MBPP500_evaluation_still_runs": True,
    "actual_generation_tokens_GPU_hours_and_disk_use": "unknown_before_native_run",
},indent=2))
