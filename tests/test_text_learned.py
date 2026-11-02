"""CPU contract tests of additive learned methods in math and QA."""
import json
from pathlib import Path
import pytest
from improving.text_study import methods_for_config, validate_text_config

ROOT=Path(__file__).resolve().parents[1]

def load(name):
    return json.loads((ROOT/"configs/multidomain"/name).read_text())

@pytest.mark.parametrize("domain", ["math","qa"])
def test_learned_text_config_is_opt_in_and_has_matched_references(domain):
    old=load("text_"+domain+".json")
    new=load("text_"+domain+"_learned.json")
    assert "spectral_learned" not in methods_for_config(old)
    assert methods_for_config(new)[-1]=="spectral_learned"
    assert validate_text_config(new) is new
    assert new["calibration"]["matched_reference_fit_examples"]==54
    assert new["calibration"]["max_examples"]==64
    assert new["calibration"]["gain_learning"]["guard_examples"]==10
    assert new["output_dir"] != old["output_dir"]
    assert new["data"] == old["data"]

def test_learned_text_requires_fit_guard_control():
    cfg=load("text_math_learned.json")
    cfg["calibration"]["matched_reference_fit_examples"]=64
    with pytest.raises(ValueError,match="matched_reference"):
        validate_text_config(cfg)
    cfg=load("text_qa_learned.json")
    cfg["methods"]=["spectral_learned"]
    with pytest.raises(ValueError,match="historical methods"):
        methods_for_config(cfg)
