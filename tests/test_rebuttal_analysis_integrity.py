"""Authored Local checks of evidence admission; fixtures are not research data."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_hash_spelling_matches_both_native_producers():
    analysis, runner = load("rebuttal_case_analysis"), load("rebuttal_cases")
    from improving.utils import stable_hash
    value = {"source": "test-only", "nested": [1, {"a": False}], "number": .8}
    assert analysis._digest(value) == runner.digest(value) == stable_hash(value)
    assert analysis._native_digest(value) == stable_hash(value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_evidence_never_enters_a_table(value):
    analysis = load("rebuttal_case_analysis")
    with pytest.raises(analysis.QualificationError):
        analysis._finite({"metric": value})
    assert not analysis._number(True)


def samples():
    raw = [{"task_id": "Test/0", "sample_id": i, "completion": f"value={i}"} for i in range(64)]
    verified = [{**row, "correct": i < 5, "status": "passed" if i < 5 else "failed"}
                for i, row in enumerate(raw)]
    return raw, verified


@pytest.mark.parametrize("corruption", ["missing", "duplicate", "changed_text", "wrong_correctness"])
def test_sealed_sample_contract_rejects_incomplete_or_changed_evidence(corruption):
    analysis = load("rebuttal_case_analysis")
    raw, verified = samples()
    assert len(analysis._sample_coverage(raw, verified, ["Test/0"])) == 64
    if corruption == "missing":
        verified.pop()
    elif corruption == "duplicate":
        verified[-1] = deepcopy(verified[0])
    elif corruption == "changed_text":
        verified[0]["completion"] = "edited"
    else:
        verified[0]["correct"] = False
    with pytest.raises(analysis.QualificationError):
        analysis._sample_coverage(raw, verified, ["Test/0"])


def test_native_n16_mapping_cannot_be_relabelled_as_n64():
    analysis = load("rebuttal_case_analysis")
    with pytest.raises(analysis.QualificationError, match="n=64"):
        analysis._validate_values({"per_task": {"Test/0": {}}, "aggregate": {},
            "protocol": {"expected_samples": {"Test/0": 16}}}, {}, {"Test/0": {}})


def binding_fixture(tmp_path):
    runner, analysis = load("rebuttal_cases"), load("rebuttal_case_analysis")
    case = runner.one_case("c01")
    directory = tmp_path / "c01"
    run = directory / "run"
    args = runner.make_parser().parse_args(["plan", "--data-root", str(tmp_path / "data"), "--profile", "24gb"])
    cfg = runner.config_for(case, args, run)
    path = run / "spectral_soft" / "round_5" / "evaluation.metrics.json"
    path.parent.mkdir(parents=True)
    names = ["pipeline.py", "generation.py", "training.py", "metrics.py", "verification.py"]
    manifest = {"config": cfg, "fingerprint": "0" * 64,
        "implementation_hashes": {name: "a" * 64 for name in names}, "selected_task_ids": {},
        "evaluation_runtime": {}, "training_runtime": {}, "local_base_fingerprint": None}
    plan = {"protocol": runner.PROTOCOL, "case": case, "case_spec_sha256": runner.digest(case),
        "implementation": {"files": {"src/improving/" + name: "a" * 64 for name in names}}}

    def write():
        plan["config_sha256"] = runner.digest(cfg)
        plan["plan_fingerprint"] = runner.digest({k: v for k, v in plan.items() if k != "plan_fingerprint"})
        (directory / "config.json").write_text(json.dumps(cfg))
        (directory / "plan.json").write_text(json.dumps(plan))
        (directory / "plan.sha256.json").write_text(json.dumps({"sha256": runner.file_sha(directory / "plan.json")}))
        (run / "manifest.json").write_text(json.dumps(manifest))

    write()
    return analysis, case, cfg, path, write


@pytest.mark.parametrize("section,key,value", [
    ("calibration", "tau", 2.), ("calibration", "layers", [27]),
    ("calibration", "max_examples", 40), ("calibration", "reestimate_each_round", False),
    ("train", "fixed_anchor_replay", True), ("train", "target_token_budget", 7200000),
    ("generation", "training_decoder_overrides", {"temperature": 1.}),
])
def test_self_consistent_hashes_do_not_authorize_a_different_case(tmp_path, section, key, value):
    analysis, case, cfg, path, write = binding_fixture(tmp_path)
    analysis._case_binding(path, case)
    cfg[section][key] = value
    write()  # valid file hashes, wrong scientific case identity
    with pytest.raises(analysis.QualificationError):
        analysis._case_binding(path, case)


def test_posthoc_manifest_is_not_a_training_case(tmp_path):
    analysis = load("rebuttal_case_analysis")
    case = load("rebuttal_cases").one_case("c01")
    path = tmp_path / "source" / "spectral_soft" / "round_5" / "evaluation.metrics.json"
    path.parent.mkdir(parents=True)
    (path.parents[2] / "manifest.json").write_text(json.dumps({
        "purpose": "saved_checkpoint_evaluation_without_training", "protocol": {}}))
    with pytest.raises(analysis.QualificationError):
        analysis._case_binding(path, case)


def test_incompatible_evaluators_and_empty_common_d4_remain_visible():
    analysis = load("rebuttal_case_analysis")
    with pytest.raises(analysis.QualificationError, match="differ"):
        analysis.comparable({"_qualification": {"comparison_signature": {"verifier": "a"}}},
                            {"_qualification": {"comparison_signature": {"verifier": "b"}}})
    entry = {"pass_at_k": {"1": .5, "16": 1., "64": 1.},
             "implementation_proxy": {"coverage_at_k": {"64": 1.},
                                      "correct_matched_coverage_at_budgets": {"4": None}}}
    metric = {"per_task": {f"Test/{i}": deepcopy(entry) for i in range(500)}}
    result = analysis.paired(metric, metric, nboot=100)
    assert result["D4"]["estimate_right_minus_left"] is None
    assert result["D4"]["ci95_task_bootstrap"] is None
    assert result["D4"]["eligible_both"] == 0
