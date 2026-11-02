"""Preflight protocol is stdlib-only; testing it does not fetch any models."""
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_full_static_preflight():
    spec=importlib.util.spec_from_file_location("static_learned",ROOT/"scripts/preflight_learned_full_matrix.py")
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    result=obj.check()
    assert result["status"]=="static_preflight_passed"
    assert result["gpu_checked"] is False
    assert result["scientific_results"] is False
