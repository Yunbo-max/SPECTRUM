"""No-download source/contract tests for the learned transfer suite."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]

def extra():
    spec=importlib.util.spec_from_file_location("learned_transfer", ROOT/"scripts/run_learned_extra_transfers.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_all_extra_transfers_are_heldout():
    mod=extra()
    assert set(mod.BENCHMARKS)=={"apps_intro","codecontests","livecodebench"}
    assert sum(mod.EXPECTED.values())==565
    assets=json.loads((ROOT/"configs/final/assets.json").read_text())
    for name in mod.BENCHMARKS:
        assert assets["datasets"][name]["training_allowed"] is False
        assert assets["datasets"][name]["expected_count"]==mod.EXPECTED[name]
        assert assets["datasets"][name]["evaluation_backend"]=="builtin"

def test_invalid_models_or_datasets_rejected():
    mod=extra()
    with pytest.raises(ValueError):
        mod.choice("unknown", mod.BENCHMARKS, "dataset")
    with pytest.raises(ValueError):
        mod.choice("unknown", mod.MODELS, "model")
    assert mod.choice("all", mod.MODELS, "model")==list(mod.MODELS)
