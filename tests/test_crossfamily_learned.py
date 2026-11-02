"""Contract tests for additive cross-family learned-gain protocol.

No model/download/benchmark execution is performed here.
"""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]

def runner():
    spec = importlib.util.spec_from_file_location(
        "crossfamily_learned", ROOT / "scripts" / "run_crossfamily_study.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def test_historical_protocol_unchanged_and_learned_only_additive():
    r = runner()
    historical = json.loads((ROOT / "configs/crossfamily/protocol.json").read_text())
    learned = json.loads((ROOT / "configs/crossfamily/protocol_learned_4096.json").read_text())
    assert r.methods_for_protocol(historical) == r.METHODS
    assert r.methods_for_protocol(learned) == r.SUPPORTED_METHODS
    assert learned["generation"]["max_new_tokens"] == 4096
    assert learned["train"]["max_length"] >= (learned["generation"]["max_prompt_tokens"]
                                                + learned["generation"]["max_new_tokens"])
    assert learned["calibration"]["gain_learning"]["guard_examples"] == 10
    assert learned["calibration"]["max_examples"] == 50
    assert learned["transfer"]["samples"] == 64
    assert learned["evaluation"]["backend"] == "docker"
    assert learned["evaluation"]["allow_unsafe_local"] is False

def test_invalid_learned_reference_splits_rejected():
    r=runner()
    bad = json.loads((ROOT / "configs/crossfamily/protocol_learned_4096.json").read_text())
    bad["calibration"]["gain_learning"]["guard_examples"] = 50
    with pytest.raises(ValueError, match="fit/guard"):
        r.methods_for_protocol(bad)
    bad["calibration"]["gain_learning"]["guard_examples"] = 10
    bad["methods"] = ["spectral_learned"]
    with pytest.raises(ValueError, match="historical three"):
        r.methods_for_protocol(bad)
