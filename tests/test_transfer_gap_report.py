"""Read-only cumulative report does not invent unavailable experimental cells."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]


def report():
    spec = importlib.util.spec_from_file_location(
        "gap_report_cli", ROOT / "scripts" / "report_transfer_gap.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def config():
    return {
        "methods": ["spectral_learned"], "rounds": 10,
        "generation": {"max_new_tokens": 4096, "max_prompt_tokens": 2048},
        "evaluation": {"backend": "bwrap", "allow_unsafe_local": False},
        "diagnostics": {"transfer_gap": {
            "enabled": True, "rounds": [1, 5, 8, 10], "samples": 64,
            "validation_task_count": 30, "max_prompt_tokens": 2048,
            "max_new_tokens": 4096, "reference_nll_each_round": True,
            "batch_size": 1, "task_batch_size": 1, "sequence_batch_size": 1,
        }},
    }


def test_missing_rounds_remain_explicitly_incomplete(tmp_path):
    study = tmp_path / "trial"
    study.mkdir()
    (study / "manifest.json").write_text(json.dumps({
        "config": config(),
        "selected_task_ids": {"validation": [f"MBPP/{i}" for i in range(30)]},
    }))
    value = report().summarize(study)
    assert len(value["per_round"]) == 10
    assert all(row["status"] == "missing_or_incomplete"
               for row in value["per_round"])
    assert value["configured_dev_rounds"] == [1, 5, 8, 10]


def test_no_trajectory_kl_claim_in_report_contract(tmp_path):
    root = tmp_path / "empty"
    root.mkdir()
    with pytest.raises(FileNotFoundError):
        report().summarize(root)
