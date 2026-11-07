"""No GPU/download/network; contract checks for separately resumable rebuttal cases."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "scripts/rebuttal_cases.py"


def runner():
    spec = importlib.util.spec_from_file_location("rebuttal_cases_contract", FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def args(tmp_path):
    return SimpleNamespace(
        root=str(tmp_path / "cases"), data_root=str(tmp_path / "mbpp"),
        benchmark_root=str(tmp_path / "benchmarks"), model_root=None,
        profile="80gb", workers=2, source_run=None, source_methods=None,
        task_file=None, evidence=[], execute=False, verify_hashes=False,
        rerun_historical=False,
    )


def test_all_case_ids_have_independent_python_entrypoints():
    mod = runner()
    cases = mod.load_spec()["cases"]
    assert len(cases) == 36
    assert [x["id"] for x in cases] == [f"c{idx:02d}" for idx in range(36)]
    for x in cases:
        path = ROOT / "scripts/rebuttal_cases" / f"{x['id']}.py"
        assert path.is_file()
        import ast
        ast.parse(path.read_text(encoding="utf-8"))
        assert x["id"] in path.read_text(encoding="utf-8")
        assert x["priority"] in {"P0", "P1", "P2"}
        assert x["reviewers"]
    assert not any(x["kind"] == "train" and x.get("method") == "spectral_learned" for x in cases)


def test_core_trials_have_identical_budget_and_separate_checkpoint_roots(tmp_path):
    mod, a = runner(), args(tmp_path)
    configs = {ident: mod.config_for(mod.one_case(ident), a,
              tmp_path / "cases" / ident / "run")
              for ident in ("c01", "c02", "c03", "c04", "c06", "c07",
                            "c08", "c09", "c10", "c11", "c23", "c24")}
    for ident, cfg in configs.items():
        assert cfg["methods"] == [mod.one_case(ident)["method"]]
        assert cfg["generation"]["train_samples"] == 16
        assert cfg["generation"]["eval_samples"] == 64
        assert cfg["generation"]["max_new_tokens"] == 512
        assert cfg["generation"]["temperature"] == .8
        assert cfg["generation"]["top_p"] == .95
        assert cfg["rounds"] == 5
        assert cfg["checkpoint_retention"] == "all"
        assert cfg["train"]["epochs"] == 1
        assert cfg["train"]["loss_scope"] == "all"
        assert cfg["model"]["revision"]
    assert len({cfg["output_dir"] for cfg in configs.values()}) == len(configs)
    for ident in ("c01", "c02", "c03", "c04"):
        assert configs[ident]["seed"] == 43
        assert configs[ident]["calibration"]["max_examples"] == 50
        assert configs[ident]["generation"] == configs["c01"]["generation"]
    assert configs["c01"]["model"] == configs["c02"]["model"]
    assert configs["c07"]["seed"] == configs["c06"]["seed"] == 44
    assert configs["c09"]["seed"] == configs["c08"]["seed"] == 45
    assert configs["c23"]["calibration"]["layers"] == [27]
    assert configs["c24"]["calibration"]["layers"] == [14]


def test_reference_budget_decoder_and_architecture_not_misrepresented(tmp_path):
    mod, a = runner(), args(tmp_path)
    for ident in ("c05", "c10", "c11", "c14", "c15", "c18", "c19",
                  "c27", "c28", "c29", "c30", "c31"):
        cfg = mod.config_for(mod.one_case(ident), a, tmp_path / ident)
        assert len(cfg["methods"]) == 1
        assert cfg["evaluation"]["backend"] == "docker"
        assert not cfg["evaluation"]["allow_unsafe_local"]
        if ident == "c05":
            assert cfg["methods"] == ["plain"]
            assert cfg["train"]["fixed_anchor_replay"] is True
        if ident in ("c10", "c11"):
            assert cfg["train"]["target_token_budget"] == 7200000
        if ident == "c27":
            assert cfg["calibration"]["max_examples"] == 40
        if ident in ("c28","c29"):
            assert cfg["generation"]["temperature"] == .8
            assert cfg["generation"]["training_decoder_overrides"]["temperature"] > .8
        if ident == "c31":
            assert cfg["calibration"]["reestimate_each_round"] is False
    a_model = mod.config_for(mod.one_case("c14"), a, tmp_path / "c14")
    q_model = mod.config_for(mod.one_case("c18"), a, tmp_path / "c18")
    assert a_model["model"]["name"].startswith("deepseek-ai/")
    assert q_model["model"]["name"].startswith("Qwen/")


def test_frozen_plan_per_case_and_no_implicit_execution(tmp_path, monkeypatch):
    mod, a = runner(), args(tmp_path)
    plans = {}
    for ident in ("c02","c03","c07"):
        c = mod.one_case(ident)
        plan = mod.build_plan(c, a)
        assert mod.build_plan(c, a) == plan  # immutable/idempotent
        assert Path(plan["config_file"]).is_file()
        assert not Path(plan["output"]).exists()  # no GPU/model run at planning
        plans[ident] = plan
    assert len({p["output"] for p in plans.values()}) == 3
    assert mod.read_plan(mod.one_case("c03"), a) == plans["c03"]
    monkeypatch.setattr(mod.subprocess, "run",
                        lambda *args, **kwargs: (_ for _ in ()).throw(
                            AssertionError("planning/dry-run must not launch anything")))
    dry = mod.execute_case(mod.one_case("c02"), a)
    assert dry["dry_run"] is True
    assert dry["command"][1:4] == ["-m", "improving", "run"]
    a.execute = True
    with pytest.raises(FileNotFoundError, match="prepared MBPP"):
        mod.execute_case(mod.one_case("c02"), a)


def test_corrupt_or_modified_plan_refused(tmp_path):
    mod, a = runner(), args(tmp_path)
    c = mod.one_case("c02")
    plan = mod.build_plan(c, a)
    changed = json.loads(Path(plan["config_file"]).read_text())
    changed["generation"]["temperature"] = 9.0
    Path(plan["config_file"]).write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="Frozen training config"):
        mod.read_plan(c, a)


def test_transfer_and_decoder_plan_requires_explicit_source(tmp_path):
    mod, a = runner(), args(tmp_path)
    for ident in ("c16","c17","c20","c21","c22","c32","c33","c34","c35"):
        with pytest.raises(ValueError, match="source-run"):
            mod.build_plan(mod.one_case(ident), a)
    a.source_run = str(tmp_path / "external_model_root")
    a.source_methods = "spectral_soft"
    one = mod.build_plan(mod.one_case("c16"), a)
    two = mod.build_plan(mod.one_case("c21"), a)
    assert "experiments/iclr2027/transfer.py" in one["command"]
    assert "scripts/rebuttal_decoder_eval.py" in two["command"]
    assert one["output"] != two["output"]
    assert one["samples"] == two["samples"] == 64
    interp = mod.build_plan(mod.one_case("c32"), a)
    assert "scripts/rebuttal_interpolation_eval.py" in interp["command"]
    assert interp["source_methods"] == "plain"
    assert interp["output"] not in {one["output"],two["output"]}


def test_nontrain_audit_never_claims_new_results(tmp_path):
    mod, a = runner(), args(tmp_path)
    case = mod.one_case("c00")
    plan = mod.build_plan(case, a)
    assert plan["status"] == "planned_not_executed"
    assert "evidence_sha256" in plan
    st = mod.status_case(case, a)
    assert st["state"] == "planned"
    result = mod.execute_case(case, a)
    assert result["dry_run"] is True
    a.execute = True
    result = mod.execute_case(case, a)
    assert result["no_new_experiment"] is True
    assert mod.status_case(case, a)["state"] == "historical_audit_only"


def test_actual_nested_eval_schema_and_d4_disambiguation(tmp_path):
    mod, a = runner(), args(tmp_path)
    case = mod.one_case("c02")
    plan = mod.build_plan(case, a)
    root = Path(plan["output"])
    root.mkdir(parents=True)
    (root / "run_status.json").write_text(json.dumps({
        "status": "completed", "verification": "completed",
        "methods": ["random_soft"], "rounds": 5}))
    aggregate = {
        "task_count": 500, "sample_count": 32000,
        "pass_at_k": {k: {"mean": .5} for k in ("1","16","64")},
        "implementation_proxy": {
            "coverage_at_k": {"64": {"mean": 11.0}},
            "correct_matched_coverage_at_budgets": {
                "4": {"mean": 3.3, "eligible_tasks": 400}},
        },
    }
    metrics = {"protocol": {"expected_samples":64}, "aggregate": aggregate,
               "per_task": {f"Mbpp/{k}": {} for k in range(500)}}
    base = root / "base"
    base.mkdir()
    (base / "complete.json").write_text("{}")
    (base / "evaluation.metrics.json").write_text(json.dumps(metrics))
    required = ("evaluation.metrics.json","evaluation.verified.jsonl",
                "evaluation.jsonl","train.jsonl","training_stats.json",
                "model/config.json","model/model.safetensors")
    for round_num in range(1,6):
        stage = root / "random_soft" / f"round_{round_num}"
        for name in required:
            target = stage / name
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(json.dumps(metrics) if name == "evaluation.metrics.json" else "{}")
        seals = {name: mod.file_sha(stage / name) for name in required}
        (stage / "complete.json").write_text(json.dumps({"status":"completed","files":seals}))
    outcome = mod.inspect_training(plan,case,hashes=True)
    assert outcome["state"] == "complete"
    assert outcome["verified_rounds"] == 5
    assert outcome["endpoints"]["C64"] == 11.0
    assert outcome["endpoints"]["D4"] == 3.3
    assert outcome["endpoints"]["D4_eligible"] == 400
    final = root / "random_soft" / "round_5" / "evaluation.metrics.json"
    final.write_text("{}",encoding="utf-8")
    bad = mod.inspect_training(plan,case,hashes=True)
    assert bad["state"] == "partial"
    assert bad["issues"]


def test_historical_case_must_be_explicitly_rerun(tmp_path):
    mod, a = runner(), args(tmp_path)
    case = mod.one_case("c01")
    mod.build_plan(case,a)
    a.execute = True
    with pytest.raises(ValueError, match="Historical"):
        mod.execute_case(case,a)


def test_source_generation_override_is_training_only_and_AST_valid():
    import ast
    source = (ROOT / "src/improving/pipeline.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert "training_decoder_overrides" in source
    assert "training_settings.update(gen['training_decoder_overrides'])" in source
    assert "Do not leak this control into held-out evaluation" in source
    assert any(isinstance(x,ast.FunctionDef) and x.name=="validate_config" for x in tree.body)


def test_semantic_script_uses_blinded_ids_and_human_annotation():
    text = (ROOT / "scripts/rebuttal_semantic_blind.py").read_text(encoding="utf-8")
    import ast
    ast.parse(text)
    assert "packet_created_no_human_labels" in text
    assert "semantic_effect_established" in text
    assert "private_method_key.jsonl" in text


def test_interpolation_never_updates_student_weights_and_locks_alpha():
    import ast
    text = (ROOT/"scripts/rebuttal_interpolation_eval.py").read_text()
    tree = ast.parse(text)
    assert "training_performed" in text
    assert "interpolate_native_parameters" in text
    assert "alpha not in (0.5, 0.75)" in text
    assert any(isinstance(x,ast.FunctionDef) and x.name=="main" for x in tree.body)


def test_single_train_method_per_interpolation_source():
    mod = runner()
    for ident in ("c32", "c33", "c34", "c35"):
        item = mod.one_case(ident)
        assert item["kind"] == "interpolate"
        assert item["round"] == 5 and item["samples"] == 64
        assert item["method"] in {"plain","spectral_soft"}
        assert item["alpha"] in (0.5,0.75)
