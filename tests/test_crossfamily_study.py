"""Source-authored software tests; fixtures are not scientific benchmark evidence."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO = Path(__file__).resolve().parents[1]


def module():
    spec = importlib.util.spec_from_file_location("crossfamily_test_entry", REPO / "scripts/run_crossfamily_study.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def prepared_plan(tmp_path, monkeypatch):
    runner = module()
    monkeypatch.setattr(runner, "sources", lambda: {"controlled.py": "a" * 64})
    args = SimpleNamespace(assets=str(REPO / "configs/crossfamily/assets.json"),
        protocol=str(REPO / "configs/crossfamily/protocol.json"),
        seed_file=str(tmp_path / "private/seed.json"), data_root=str(tmp_path / "data"),
        run_root=str(tmp_path / "run"))
    runner.init(args)
    data = Path(args.data_root)
    entries = {}
    for name, populations in (("mbpp", runner.COUNTS), ("humanevalplus", {"eval": 164})):
        folder = data / name
        folder.mkdir(parents=True)
        outputs = {}
        for split, count in populations.items():
            target = folder / f"{split}.jsonl"
            target.write_text("".join(json.dumps({"task_id": f"fixture-{name}-{split}/{i}",
                "prompt": f"software-only fixture {name} {split} {i}"}) + "\n" for i in range(count)))
            outputs[target.name] = {"sha256": runner.sha(target), "count": count, "bytes": target.stat().st_size}
        runner.save(folder / "manifest.json", {"name": name, "output_files": outputs})
        entries[name] = {"manifest_sha256": runner.sha(folder / "manifest.json"), "output_files": outputs}
        if name == "humanevalplus":
            fixture = folder / "HumanEvalPlus.jsonl"
            fixture.write_text('{"software_only_fixture": true}\n')
            entries[name]["native_fixture"] = {"path": str(fixture), "sha256": runner.sha(fixture)}
    runner.save(data / "prepared.json", {"protocol": runner.PROTOCOL,
        "assets_sha256": runner.digest(runner.assets(args.assets)),
        "seed_file_sha256": runner.sha(args.seed_file), "datasets": entries})
    runner.plan(args)
    return runner, args


def test_three_different_families_and_single_trajectory_protocol():
    runner = module()
    mapping = runner.assets(REPO / "configs/crossfamily/assets.json")
    protocol = runner.read(REPO / "configs/crossfamily/protocol.json")
    assert set(mapping["models"]) == {"qwen7b", "llama8b", "deepseek6.7b"}
    assert len({value["family"] for value in mapping["models"].values()}) == 3
    assert protocol["independent_training_trajectories"] == 1
    assert protocol["temperature_sweep"] is False
    assert protocol["evaluation"]["backend"] == "bwrap"
    assert not {"decoder_grid", "replicates", "seeds"} & protocol.keys()


def test_frozen_plan_rejects_changed_input_without_resampling(tmp_path, monkeypatch):
    runner, args = prepared_plan(tmp_path, monkeypatch)
    before = Path(args.run_root, "plan/manifest.json").read_bytes()
    target = Path(args.data_root, "mbpp/eval.jsonl")
    target.write_text(target.read_text() + '{"task_id":"fixture/extra"}\n')
    with pytest.raises(ValueError, match="Prepared input changed"):
        runner.load_plan(args)
    assert Path(args.run_root, "plan/manifest.json").read_bytes() == before


def test_frozen_plan_rejects_changed_source(tmp_path, monkeypatch):
    runner, args = prepared_plan(tmp_path, monkeypatch)
    monkeypatch.setattr(runner, "sources", lambda: {"controlled.py": "b" * 64})
    with pytest.raises(ValueError, match="Frozen source differs"):
        runner.load_plan(args)


def test_plan_rejects_forged_count_even_when_declared_hashes_match(tmp_path, monkeypatch):
    runner, args = prepared_plan(tmp_path, monkeypatch)
    target = Path(args.data_root, "mbpp/eval.jsonl")
    rows = target.read_text().splitlines()
    target.write_text("\n".join(rows[:-1]) + "\n")
    metadata_path = target.parent / "manifest.json"
    metadata = runner.read(metadata_path)
    metadata["output_files"]["eval.jsonl"]["sha256"] = runner.sha(target)
    runner.save(metadata_path, metadata)
    receipt_path = Path(args.data_root, "prepared.json")
    receipt = runner.read(receipt_path)
    receipt["datasets"]["mbpp"]["output_files"] = metadata["output_files"]
    receipt["datasets"]["mbpp"]["manifest_sha256"] = runner.sha(metadata_path)
    runner.save(receipt_path, receipt)
    with pytest.raises(ValueError, match="Incorrect actual population"):
        runner.snapshot_prepared(Path(args.data_root))


def test_private_seed_initialization_preserves_existing_trajectory(tmp_path):
    runner = module()
    args = SimpleNamespace(seed_file=str(tmp_path / "private.json"))
    runner.init(args)
    before = Path(args.seed_file).read_bytes()
    runner.init(args)
    assert Path(args.seed_file).read_bytes() == before
