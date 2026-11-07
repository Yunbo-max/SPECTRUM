"""Fresh native preparation carries official fixtures; frozen files stay sealed.

Authored for Local software acceptance. No model or benchmark program executes.
"""
import hashlib
import json
import pytest
from improving import benchmarks


def test_native_fixture_is_in_preparation_seal_and_tampering_is_rejected(tmp_path, monkeypatch):
    fixture = tmp_path / "official.jsonl"
    fixture.write_text("official-fixture-test-bytes\n")
    checksum = hashlib.sha256(fixture.read_bytes()).hexdigest()
    tasks = [{"task_id": f"HumanEval/{i}", "prompt": f"Prompt {i}",
              "source": "evalplus/HumanEvalPlus", "split": "eval"} for i in range(164)]
    monkeypatch.setattr(benchmarks, "_humanevalplus", lambda: (tasks, {
        "dataset_sha256": checksum, "native_fixture_path": str(fixture), "task_count": 164}))
    target = tmp_path / "prepared"
    manifest = benchmarks.prepare_benchmark("humanevalplus", target, revision="v0.1.10")
    assert manifest["output_files"]["HumanEvalPlus.jsonl"]["sha256"] == checksum
    assert "native_fixture_path" not in manifest["source_metadata"]
    assert (target / "HumanEvalPlus.jsonl").read_bytes() == fixture.read_bytes()
    assert benchmarks.prepare_benchmark("humanevalplus", target, revision="v0.1.10") == manifest
    (target / "HumanEvalPlus.jsonl").write_text("edited")
    with pytest.raises(ValueError, match="changed or incomplete"):
        benchmarks.prepare_benchmark("humanevalplus", target, revision="v0.1.10")


def test_old_manifest_is_never_silently_upgraded(tmp_path, monkeypatch):
    fixture = tmp_path / "official.jsonl"
    fixture.write_text("official-fixture-test-bytes\n")
    checksum = hashlib.sha256(fixture.read_bytes()).hexdigest()
    monkeypatch.setattr(benchmarks, "_humanevalplus", lambda: ([{
        "task_id": f"HumanEval/{i}", "prompt": f"Prompt {i}",
        "source": "evalplus/HumanEvalPlus", "split": "eval"} for i in range(164)], {
        "dataset_sha256": checksum, "native_fixture_path": str(fixture)}))
    target = tmp_path / "prepared"
    manifest = benchmarks.prepare_benchmark("humanevalplus", target)
    del manifest["output_files"]["HumanEvalPlus.jsonl"]
    (target / "HumanEvalPlus.jsonl").unlink()
    (target / "manifest.json").write_text(json.dumps(manifest))
    previous = (target / "manifest.json").read_bytes()
    benchmarks.prepare_benchmark("humanevalplus", target)
    assert (target / "manifest.json").read_bytes() == previous
    assert not (target / "HumanEvalPlus.jsonl").exists()
