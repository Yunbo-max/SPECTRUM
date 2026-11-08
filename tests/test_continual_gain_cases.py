"""Authored Local contract tests; never executed as part of Web delivery.

Synthetic task/model bytes test admission and isolation only. They do not qualify
native data, load a model, train, grade answers, or establish research outcomes.
"""
from __future__ import annotations

import builtins
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def cli():
    spec = importlib.util.spec_from_file_location(
        "continual_gain_case_contract", ROOT / "scripts/run_continual_gains.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
                    encoding="utf-8")


@pytest.fixture
def prepared(cli, tmp_path, monkeypatch):
    # Bound the artificial evaluation files. Production denominator constants
    # are asserted separately and are never changed in repository source.
    monkeypatch.setattr(cli, "NATIVE_EVALUATION_COUNTS",
                        {"math": {"math500": 2}, "qa": {"mmlu_pro": 3}})
    seed_path = tmp_path / "private/seed.json"
    write_json(seed_path, {"schema": 1, "seed": 19})
    model = tmp_path / "model"
    write_json(model / "config.json", {"model_type": "software-fixture"})
    write_json(model / "tokenizer.json", {"software_fixture": True})
    write_json(model / "model.safetensors.index.json",
               {"weight_map": {"fixture.weight": "model-00001-of-00001.safetensors"}})
    (model / "model-00001-of-00001.safetensors").write_bytes(b"not a loadable model\n")
    args = cli.make_parser().parse_args([
        "plan", "--case", "cg01", "--root", str(tmp_path / "cases"),
        "--seed-file", str(seed_path), "--model-path", str(model),
        "--math-data-root", str(tmp_path / "data/math"),
        "--qa-data-root", str(tmp_path / "data/qa"),
    ])
    case = cli.one_case("cg01")
    config = cli.config_for(case, args, cli.case_directory(case, args))
    for domain in ("math", "qa"):
        current = config["domains"][domain]
        directory = Path(current["data"]["output_dir"])
        counts = {split: current["data"][split + "_size"] for split in cli.SPLITS[:-1]}
        counts["eval"] = sum(cli.NATIVE_EVALUATION_COUNTS[domain].values())
        hashes = {}
        for split, count in counts.items():
            benchmark = next(iter(cli.NATIVE_EVALUATION_COUNTS[domain])) if split == "eval" else domain + "_train"
            rows = [{"task_id": f"{domain}/{split}/{index}", "split": split,
                     "prompt": f"Artificial {domain} {split} question {index}",
                     "original_prompt": f"Artificial {domain} {split} question {index}",
                     "reference": "Artificial reference", "answer": "A", "benchmark": benchmark}
                    for index in range(count)]
            path = directory / f"{split}.jsonl"
            write_jsonl(path, rows)
            hashes[path.name] = cli.file_sha(path)
        sources = {}
        if domain == "math":
            sources["prm800k"] = {}
            for name in ("grader.py", "math_normalize.py"):
                relative = "prm800k/grading/" + name
                path = directory / "sources/prm800k" / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# Artificial grading receipt only.\n", encoding="utf-8")
                sources["prm800k"][relative] = {"sha256": cli.file_sha(path)}
        write_json(directory / "manifest.json", {
            "schema": 1,
            "identity": {"domain": domain, "data": deepcopy(current["data"]),
                         "seed_sha256": cli.digest(19),
                         "builder_sha256": cli.file_sha(ROOT / "src/improving/text_tasks.py")},
            "sources": sources, "counts": counts, "output_hashes": hashes,
            "evaluation_counts": cli.NATIVE_EVALUATION_COUNTS[domain],
        })
    # An isolated executable source lets mutation tests leave the repository
    # unchanged while exercising both source freeze and revalidation.
    source = tmp_path / "source/implementation.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")

    def isolated_source():
        files = {"implementation.py": cli.file_sha(source)}
        return {"files": files, "sha256": cli.digest(files)}

    monkeypatch.setattr(cli, "source_identity", isolated_source)
    return SimpleNamespace(cli=cli, args=args, case=case, config=config, source=source,
                           seed=seed_path, model=model, root=tmp_path / "cases")


def test_catalog_preserves_order_and_independent_method_outputs(cli, tmp_path):
    assert cli.NATIVE_EVALUATION_COUNTS == {"math": {"math500": 500}, "qa": {"mmlu_pro": 12032}}
    originals = {domain: (ROOT / f"configs/multidomain/text_{domain}_learned.json").read_bytes()
                 for domain in ("math", "qa")}
    args = cli.make_parser().parse_args(["plan", "--root", str(tmp_path / "cases")])
    paths = set()
    for case in cli.load_spec()["cases"]:
        config = cli.config_for(case, args, cli.case_directory(case, args))
        assert config["order"] == case["order"]
        assert config["backbone_update"] == case["backbone_update"]
        assert config["domains"]["math"]["train"] == json.loads(originals["math"])["train"]
        assert config["domains"]["qa"]["train"] == json.loads(originals["qa"])["train"]
        assert config["domains"]["math"]["evaluation"]["samples"] == 16
        assert config["domains"]["qa"]["evaluation"]["samples"] == 1
        assert (ROOT / case["entrypoint"]).is_file()
        paths.add(config["output_dir"])
    assert len(paths) == 16
    assert cli.load_spec()["initial_batch"] == ["cg00", "cg01", "cg02", "cg03"]
    for domain, original in originals.items():
        assert (ROOT / f"configs/multidomain/text_{domain}_learned.json").read_bytes() == original


def test_plan_and_unadmitted_run_never_import_or_launch_study(prepared, monkeypatch):
    p = prepared
    real_import = builtins.__import__

    def forbid_project_import(name, *args, **kwargs):
        if name.split(".")[0] in {"improving", "torch", "transformers", "datasets"}:
            pytest.fail(f"Planning attempted a project/model import: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", forbid_project_import)
    monkeypatch.setattr(p.cli, "_study_api", lambda: pytest.fail("Dry run invoked the study API"))
    first = p.cli.build_plan(p.case, p.args)
    assert p.cli.build_plan(p.case, p.args) == first
    assert p.cli.read_plan(p.case, p.args) == first
    run_args = p.cli.make_parser().parse_args(["run", "--root", str(p.root)])
    result = p.cli.execute_case(p.case, run_args)
    assert result["dry_run"] is True
    directory = p.cli.case_directory(p.case, p.args)
    assert not (directory / "study").exists()
    assert not (directory / "attempts").exists()
    assert not (directory / "attempt.log").exists()


def test_two_cases_share_inputs_but_never_share_outputs(prepared):
    p = prepared
    first = p.cli.build_plan(p.case, p.args)
    other = p.cli.one_case("cg02")
    second = p.cli.build_plan(other, p.args)
    assert first["inputs"] == second["inputs"]
    assert first["config_file"] != second["config_file"]
    assert p.cli.read_json(first["config_file"])["output_dir"] != p.cli.read_json(second["config_file"])["output_dir"]
    write_json(Path(first["root"]) / "study/sentinel.json", {"belongs_to": "cg01"})
    assert not (Path(second["root"]) / "study/sentinel.json").exists()


@pytest.mark.parametrize("changed", ["data", "source", "seed", "model", "config"])
def test_frozen_input_mutation_blocks_execution_before_attempt(prepared, monkeypatch, changed):
    p = prepared
    plan = p.cli.build_plan(p.case, p.args)
    if changed == "source":
        p.source.write_text("VALUE = 2\n", encoding="utf-8")
    elif changed == "seed":
        write_json(p.seed, {"schema": 1, "seed": 20})
    elif changed == "model":
        (p.model / "model-00001-of-00001.safetensors").write_bytes(b"different fixture\n")
    elif changed == "config":
        config = p.cli.read_json(plan["config_file"])
        config["order"].reverse()
        write_json(Path(plan["config_file"]), config)
    else:
        directory = Path(p.config["domains"]["qa"]["data"]["output_dir"])
        path = directory / "train.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows[0]["prompt"] = "Changed input after the case was sealed"
        write_jsonl(path, rows)
        # Even an internally re-sealed prepared manifest cannot replace the
        # exact data that an already planned case admitted.
        manifest = p.cli.read_json(directory / "manifest.json")
        manifest["output_hashes"]["train.jsonl"] = p.cli.file_sha(path)
        write_json(directory / "manifest.json", manifest)
    monkeypatch.setattr(p.cli, "_study_api", lambda: pytest.fail("Changed inputs reached execution"))
    args = p.cli.make_parser().parse_args(["run", "--root", str(p.root), "--execute", "--resume"])
    with pytest.raises(ValueError, match="changed|Changed"):
        p.cli.execute_case(p.case, args)
    assert not (Path(plan["root"]) / "attempts").exists()


def test_reduced_native_population_is_rejected_before_sealing(prepared):
    p = prepared
    directory = Path(p.config["domains"]["math"]["data"]["output_dir"])
    path = directory / "eval.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()][:-1]
    write_jsonl(path, rows)
    manifest = p.cli.read_json(directory / "manifest.json")
    manifest["counts"]["eval"] -= 1
    manifest["evaluation_counts"]["math500"] -= 1
    manifest["output_hashes"]["eval.jsonl"] = p.cli.file_sha(path)
    write_json(directory / "manifest.json", manifest)
    with pytest.raises(ValueError, match="complete native"):
        p.cli.build_plan(p.case, p.args)
    assert not (p.cli.case_directory(p.case, p.args) / "plan.json").exists()


def test_explicit_execution_records_bound_attempt_and_forwards_resume(prepared, monkeypatch):
    p = prepared
    plan = p.cli.build_plan(p.case, p.args)
    calls = []

    def run(config, method, resume=False):
        calls.append((config, method, resume, Path.cwd()))
        print("artificial runner output")
        return {"status": "completed", "method": method, "report": {"status": "complete"}}

    monkeypatch.setattr(p.cli, "_study_api", lambda: (
        run, lambda config: pytest.fail("Already verified report was needlessly recomputed")))
    args = p.cli.make_parser().parse_args(["run", "--root", str(p.root), "--execute", "--resume"])
    result = p.cli.execute_case(p.case, args)
    assert result["status"] == "completed"
    assert len(calls) == 1 and calls[0][1:] == ("sequential", True, ROOT)
    assert calls[0][0] == p.cli.read_json(plan["config_file"])
    directory = Path(plan["root"])
    events = [json.loads(line) for line in (directory / "attempt.log").read_text().splitlines()]
    assert [row["event"] for row in events] == ["started", "completed"]
    assert all(row["plan_sha256"] == p.cli.file_sha(directory / "plan.json") for row in events)
    assert "seed" not in events[0]
    assert (directory / ".case.lock").exists()


def test_failed_execution_keeps_attempt_evidence(prepared, monkeypatch):
    p = prepared
    plan = p.cli.build_plan(p.case, p.args)

    def fail(config, method, resume=False):
        raise RuntimeError("Artificial interrupted stage")

    monkeypatch.setattr(p.cli, "_study_api", lambda: (fail, lambda config: {"status": "partial"}))
    args = p.cli.make_parser().parse_args(["run", "--root", str(p.root), "--execute"])
    with pytest.raises(RuntimeError, match="interrupted"):
        p.cli.execute_case(p.case, args)
    directory = Path(plan["root"])
    events = [json.loads(line) for line in (directory / "attempt.log").read_text().splitlines()]
    assert [row["event"] for row in events] == ["started", "failed"]
    attempt = directory / "attempts" / events[-1]["attempt"]
    assert "Artificial interrupted stage" in (attempt / "stderr.log").read_text()
    assert (attempt / "exit.json").is_file()


def test_wrapper_cannot_be_rebound_to_another_case(cli, tmp_path):
    with pytest.raises(SystemExit):
        cli.main(["plan", "--case", "cg03", "--root", str(tmp_path)], fixed_case="cg00")
    assert not (tmp_path / "cg00").exists()
