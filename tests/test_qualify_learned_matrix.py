"""Pure configuration tests for multi-model qualification."""
import importlib.util,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]

def module():
    spec=importlib.util.spec_from_file_location("qualify_matrix",ROOT/"scripts/qualify_learned_matrix.py")
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test_text_qualification_uses_native_synthesis():
    q=module()
    cfg=json.loads((ROOT/"configs/multidomain/text_math_learned.json").read_text())
    inputs,gen=q.settings_for(cfg)
    assert inputs["calibration"].name=="calibration.jsonl"
    assert gen["samples"]==1
    assert cfg["calibration"]["max_examples"]==64

def test_code_qualification_uses_full_4096_budget():
    q=module()
    p=json.loads((ROOT/"configs/crossfamily/protocol_learned_4096.json").read_text())
    assert "spectral_learned" in p["methods"]
    assert p["generation"]["max_new_tokens"]==4096
    assert p["train"]["max_length"]>=4096+p["generation"]["max_prompt_tokens"]
