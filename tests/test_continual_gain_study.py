Warning: truncated output (original token count: 6810)
Total output lines: 514

"""Authored Local-only orchestration contracts; not executed by Web.

Artificial artifact bytes exercise stage ownership and interruption recovery.
They are deliberately not loadable model checkpoints or benchmark evidence.
"""
from __future__ import annotations

import builtins
from contextlib import nullcontext
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def study():
    spec = importlib.util.spec_from_file_location(
        "improving.continual_gain_study_contract", ROOT / "src/improving/continual_gain_study.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_config(name="frozen_math_qa"):
    return json.loads((ROOT / "configs/continual_gains" / (name + ".json")).read_text())


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def fake_module(monkeypatch, name, **attributes):
    module = ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)
    return module


def test_first_domain_and_stage_order_are_explicit_and_not_reordered(study):
    forward = study.stage_schedule(load_config("frozen_math_qa"))
    reverse = study.stage_schedule(load_config("self_distill_qa_math"))
    assert [(item["domain"], item["round"]) for item in forward] == [(None, 0), ("math", 1), ("qa", 1)]
    assert [(item["domain"], item["round"]) for item in reverse] == [(None, 0), ("qa", 1), ("math", 1)]
    assert forward[1]["name"] != reverse[1]["name"]
    assert [item["index"] for item in forward] == [0, 1, 2]


@pytest.mark.parametrize("mutation", ["future_repeat", "other_seed", "different_backbone", "shortened_sft", "replay"])
def test_incompatible_shared_linea…5810 tokens truncated…study, tmp_path, monkeypatch):
    config = load_config()
    root = tmp_path / "study"
    config["output_dir"] = str(root)
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.split(".")[0] in {"torch", "transformers", "datasets", "peft"}:
            pytest.fail(f"Saved-artifact reporting imported a model dependency: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    empty = study.summarize_continual_gain_study(config)
    assert empty["status"] == "unstarted" and empty["methods"] == {}
    assert not root.exists()
    method_root = root / "conflict"
    write_json(method_root / "partial.json", {"partial": True})
    partial = study.summarize_continual_gain_study(config)
    assert partial["status"] == "incomplete"
    assert partial["reason"] == "artifacts_without_study_manifest"
    # Isolate report-state handling from native input admission, which is
    # exercised independently above and by the CLI binding contracts.
    monkeypatch.setattr(study, "_assert_external", lambda *args, **kwargs: None)
    binding = {"schema": 1, "protocol": study.PROTOCOL, "config": config,
               "config_sha256": study._digest(config), "runtime": {"software_fixture": True}}
    write_json(root / "study_manifest.json", binding)
    write_json(method_root / "manifest.json", {"schema": 1, "method": "conflict",
                                               "study_sha256": study._digest(binding),
                                               "output_dir": str(method_root)})
    partial = study.summarize_continual_gain_study(config)
    assert partial["status"] == "incomplete"
    assert partial["methods"]["conflict"]["reason"] == "geometry_not_committed"
    write_json(method_root / "run_complete.json", {"status": "completed"})
    with pytest.raises(ValueError, match="completion exists without"):
        study.summarize_continual_gain_study(config)
