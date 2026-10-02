"""Offline protocol checks. These tests never execute generated/reference code."""
import copy
import json
from pathlib import Path

import pytest

from improving import benchmarks
from improving.final_data import load_final_assets

ASSETS = Path(__file__).resolve().parents[1] / "configs" / "final" / "assets.json"


def _assets(tmp_path, transform):
    value = json.loads(ASSETS.read_text())
    transform(value)
    path = tmp_path / "assets.json"
    path.write_text(json.dumps(value))
    return path


def test_final_assets_have_exact_populations_and_four_trained_models():
    assets = load_final_assets(ASSETS)
    assert len(assets["models"]) == 4
    assert assets["datasets"]["mbpp"]["expected_split_counts"] == {
        "train": 291, "calibration": 50, "validation": 30, "eval": 500}
    assert assets["datasets"]["codecontests"]["limit"] is None
    assert assets["datasets"]["codecontests"]["expected_count"] == 165


@pytest.mark.parametrize("kind,key", [("models", "qwen1.5b"), ("datasets", "mbpp")])
def test_final_assets_refuse_moving_revisions(tmp_path, kind, key):
    path = _assets(tmp_path, lambda value: value[kind][key].update(revision="main"))
    with pytest.raises(ValueError, match="commit SHA"):
        load_final_assets(path)


def test_final_assets_refuse_replaced_model_or_population(tmp_path):
    path = _assets(tmp_path, lambda value: value["models"]["qwen3b"].update(repo_id="another/model"))
    with pytest.raises(ValueError, match="unexpected final backbone"):
        load_final_assets(path)
    path = _assets(tmp_path, lambda value: value["datasets"]["codecontests"].update(limit=200))
    with pytest.raises(ValueError, match="population limit"):
        load_final_assets(path)


def _lcb_row(identifier, contest_date):
    return {"question_id": identifier, "platform": "fixture", "contest_date": contest_date,
        "question_content": f"Task {identifier}", "public_test_cases":
        json.dumps([{"input": "", "output": "", "testtype": "stdin"}]),
        "private_test_cases": "[]", "metadata": "{}"}


def _patch_download(monkeypatch, rows):
    monkeypatch.setattr(benchmarks, "_hf_revision", lambda *_: "a" * 40)
    monkeypatch.setattr(benchmarks, "_download_jsonl", lambda *_: (copy.deepcopy(rows), {}))


def test_lcb_window_is_half_open_and_selected_independently_of_fixture_contents(tmp_path, monkeypatch):
    rows = [_lcb_row("before", "2024-06-30T23:59:59Z"),
            _lcb_row("start", "2024-07-01T00:00:00Z"),
            _lcb_row("middle", "2024-09-12T00:00:00Z"),
            _lcb_row("end", "2025-01-01T00:00:00Z")]
    _patch_download(monkeypatch, rows)
    manifest = benchmarks.prepare_benchmark("livecodebench", tmp_path / "data",
        revision="a" * 40, seed=17, lcb_start_date="2024-07-01", lcb_end_date="2025-01-01",
        limit=2, expected_count=2)
    assert manifest["output_task_ids"]["eval"] == ["LiveCodeBench/fixture/middle", "LiveCodeBench/fixture/start"]
    assert manifest["source_count"] == 4
    assert manifest["exclusion_counts"]["predeclared_contest_date_outside_window"] == 2
    assert manifest["source_metadata"]["date_window"]["task_count"] == 2
    assert not manifest["reference_program_execution"]


def test_fixed_population_refuses_insufficient_eligible_tasks(tmp_path, monkeypatch):
    _patch_download(monkeypatch, [_lcb_row("one", "2024-08-01")])
    with pytest.raises(ValueError, match="expected exactly 2"):
        benchmarks.prepare_benchmark("livecodebench", tmp_path / "data", revision="a" * 40,
            expected_count=2, limit=2)
    assert not (tmp_path / "data" / "manifest.json").exists()


def test_lcb_date_bounds_are_required_together_before_download(tmp_path):
    with pytest.raises(ValueError, match="Both date bounds"):
        benchmarks.prepare_benchmark("livecodebench", tmp_path, lcb_start_date="2024-07-01")


def test_lcb_date_normalizes_timezone_to_utc():
    assert str(benchmarks._lcb_date("2024-07-01T00:30:00+01:00")) == "2024-06-30"
