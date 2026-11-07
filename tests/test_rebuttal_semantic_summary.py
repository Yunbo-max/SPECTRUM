"""Local acceptance: unknown semantic labels never become diversity evidence."""
import importlib.util
from pathlib import Path
import pytest


def module():
    path = Path(__file__).resolve().parents[1] / "scripts/rebuttal_semantic_summary.py"
    spec = importlib.util.spec_from_file_location("rebuttal_semantic_summary", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_unresolved_and_insufficient_correct_pools_remain_unavailable():
    m = module()
    assert m.expected_richness(["a", "a", "a", "a"]) == pytest.approx(1.)
    assert m.expected_richness(["a", "b", "c", "d"]) == pytest.approx(4.)
    assert m.expected_richness(["a", "b", "c", None]) is None
    assert m.expected_richness(["a", "b", "c"]) is None


def test_no_common_eligible_tasks_is_not_zero_effect():
    result = module().paired_interval([])
    assert result["mean"] is None and result["ci_low"] is None
    assert result["eligible_tasks"] == 0
