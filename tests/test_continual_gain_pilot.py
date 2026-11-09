"""Deterministic sampling contracts for the explicitly approved validation pilot."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def pilot():
    spec = importlib.util.spec_from_file_location(
        "continual_gain_pilot_contract", ROOT / "scripts/continual_gain_pilot.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_selection_is_reproducible_stratified_and_in_input_order(pilot):
    rows = ([{"task_id": f"a/{index}", "group": "a"} for index in range(10)]
            + [{"task_id": f"b/{index}", "group": "b"} for index in range(30)])
    first = pilot.select_task_ids(rows, count=20, seed="fixed", group_key="group")
    second = pilot.select_task_ids(rows, count=20, seed="fixed", group_key="group")
    assert first == second
    assert len(first) == 20
    assert sum(task_id.startswith("a/") for task_id in first) == 5
    assert first == [row["task_id"] for row in rows if row["task_id"] in set(first)]


def test_selection_rejects_bad_counts_and_duplicate_ids(pilot):
    with pytest.raises(ValueError):
        pilot.select_task_ids([{"task_id": "a"}], count=2)
    with pytest.raises(ValueError):
        pilot.select_task_ids([{"task_id": "a"}, {"task_id": "a"}], count=1)


def test_jsonl_reader_preserves_unicode_next_line_character(pilot, tmp_path):
    path = tmp_path / "eval.jsonl"
    path.write_text('{"task_id":"x","prompt":"left\u0085right"}\n', encoding="utf-8")
    assert pilot.jsonl_rows(path) == [{"task_id": "x", "prompt": "left\u0085right"}]


def test_core_module_resolves_from_current_checkout(pilot, monkeypatch):
    import sys
    source = str(ROOT / "src")
    monkeypatch.setattr(sys, "path", [entry for entry in sys.path if entry != source])
    pilot._study_api()
    assert sys.path[0] == source
