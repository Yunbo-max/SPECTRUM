#!/usr/bin/env python3
"""Read-only, task-paired rebuttal table builder for sealed MBPP native metrics.

Use --input cNN=/path/to/evaluation.metrics.json to bind recovered historical
evidence only when its native manifest, exact case settings, inputs and sealed
outcomes establish its identity; otherwise mark it unqualified. A posthoc
checkpoint manifest is not a training-case identity.
Otherwise read each new independent case root. No training, no
execution, no model calls; never compare n16 with n64 or 512 with 4096.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import math
import ast
import random
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
CASES = ROOT / "experiments/iclr2027_rebuttal/cases.json"

PAIRS = [
    ("c36","c01"), ("c01","c02"), ("c01","c03"), ("c01","c04"), ("c06","c07"),
    ("c08","c09"), ("c10","c11"), ("c01","c05"), ("c01","c27"),
    ("c01","c12"), ("c01","c13"), ("c14","c15"), ("c18","c19"),
    ("c01","c31"), ("c01","c23"), ("c01","c24"), ("c01","c28"),
    ("c01","c29"), ("c01","c30"),
    ("c37","c39"), ("c39","c40"), ("c39","c41"),
    ("c41","c42"), ("c41","c43"), ("c37","c38"),
    ("c10","c44"), ("c11","c44"), ("c01","c45"), ("c36","c47"),
]


def hash_file(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as f:
        for data in iter(lambda:f.read(1<<20),b""):
            result.update(data)
    return result.hexdigest()


def metric_file(case_id, root: Path, cases: dict, explicit: dict) -> Path:
    if case_id in explicit:
        return explicit[case_id]
    row = cases[case_id]
    if row["kind"] != "train":
        raise ValueError(f"{case_id} is not a native training case")
    return root / case_id / "run" / row["method"] / f"round_{row['rounds']}" / "evaluation.metrics.json"


class QualificationError(ValueError):
    """A source remains visible even when it cannot support a final comparison."""

    def __init__(self, status: str, reason: str):
        super().__init__(reason)
        self.status = status


def _require(condition, message, status="integrity_mismatch"):
    if not condition:
        raise QualificationError(status, message)


def _finite(value, context="JSON"):
    if isinstance(value, float):
        _require(math.isfinite(value), f"Nonfinite number in {context}")
    elif isinstance(value, dict):
        for key, item in value.items():
            _finite(item, f"{context}.{key}")
    elif isinstance(value, list):
        for item in value:
            _finite(item, context)


def _json(path: Path):
    _require(path.is_file(), f"Missing original evidence file: {path}", "unsupported_metadata")
    try:
        result = json.loads(path.read_text(encoding="utf-8"),
                            parse_constant=lambda token: (_ for _ in ()).throw(
                                ValueError(f"Nonfinite JSON constant: {token}")))
    except (ValueError, UnicodeError) as exc:
        raise QualificationError("integrity_mismatch", f"Invalid JSON in {path}: {exc}") from exc
    _finite(result, str(path))
    return result


def _digest(value):
    # Match the final case runner and improving.utils.stable_hash exactly.
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode("utf-8")).hexdigest()


def _native_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode("utf-8")).hexdigest()


def _number(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def _equal_number(actual, expected, context):
    if expected is None:
        _require(actual is None, f"Unexpected value for ineligible {context}")
    else:
        _require(_number(actual) and math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-10),
                 f"Incorrect {context}: {actual!r}; expected {expected!r}")


def _rows(path: Path):
    _require(path.is_file(), f"Missing raw evidence: {path}", "unsupported_metadata")
    result = []
    try:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                row = json.loads(line, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
                _require(isinstance(row, dict), f"Non-object record {path}:{line_number}")
                _finite(row, str(path))
                result.append(row)
    except (ValueError, UnicodeError) as exc:
        if isinstance(exc, QualificationError):
            raise
        raise QualificationError("integrity_mismatch", f"Invalid JSONL {path}: {exc}") from exc
    return result


def _required_fields(obj, fields, context):
    _require(isinstance(obj, dict) and all(key in obj for key in fields),
             f"Missing explicit {context} metadata: {fields}", "unsupported_metadata")


def _check_subset(actual, expected, context):
    _required_fields(actual, expected, context)
    for key, value in expected.items():
        _require(actual[key] == value, f"Case binding mismatch: {context}.{key}")


def _case_binding(path, case):
    """Qualify v2 cases or original native manifests; never create a new seal."""
    _require(case.get("kind") == "train", "Only native training cases are supported", "unsupported_format")
    run_root = path.parents[2]
    case_root = run_root.parent
    plan_path = case_root / "plan.json"
    manifest = _json(run_root / "manifest.json")
    _required_fields(manifest, ["config", "fingerprint", "implementation_hashes", "selected_task_ids",
                                "evaluation_runtime", "training_runtime", "local_base_fingerprint"], "training manifest")
    cfg = manifest["config"]
    implementation = manifest["implementation_hashes"]
    _require(isinstance(implementation, dict) and
             {"pipeline.py", "generation.py", "training.py", "metrics.py", "verification.py"} <= set(implementation)
             and all(isinstance(value, str) and len(value) == 64 for value in implementation.values()),
             "Native implementation identity is incomplete", "unsupported_metadata")
    if plan_path.is_file():
        plan = _json(plan_path)
        _require(plan.get("protocol") == "iclr2027-spectrum-case-isolation-v2",
                 "Unsupported original case-plan format", "unsupported_format")
        plan_seal = _json(case_root / "plan.sha256.json")
        _require(plan_seal.get("sha256") == hash_file(plan_path), "Frozen plan file hash mismatch")
        unsigned = {key: value for key, value in plan.items() if key != "plan_fingerprint"}
        _require(plan.get("plan_fingerprint") == _digest(unsigned), "Frozen plan fingerprint mismatch")
        _require(plan.get("case") == case and plan.get("case_spec_sha256") == _digest(case),
                 "Source belongs to a different case specification")
        _require(plan.get("config_sha256") == _digest(cfg), "Training config differs from original frozen plan")
        _require(_json(case_root / "config.json") == cfg, "Stored config and executed manifest disagree")
        frozen_implementation = plan.get("implementation", {}).get("files", {})
        _require(all(frozen_implementation.get("src/improving/" + name) == checksum
                     for name, checksum in manifest["implementation_hashes"].items()),
                 "Executed native implementation differs from frozen source")
        _check_subset(cfg, {"rebuttal_case": case["id"], "methods": [case["method"]]}, "case config")
        binding_format = "frozen_v2_case"
    else:
        # This in-memory descriptor is not a replacement plan or a new receipt.
        # The original native fingerprint is reconstructed below from actual
        # inputs and its recorded implementation/runtime, before admission.
        plan = {}
        binding_format = "original_native_manifest"
    plan = {**plan, "_source_root": str(run_root), "_binding_format": binding_format}
    _required_fields(cfg, ["seed", "rounds", "methods", "model", "generation",
                           "calibration", "train", "evaluation", "data"], "training config")
    _check_subset(cfg, {"seed": case["seed"], "rounds": case["rounds"]}, "config")
    _require(case["method"] in cfg["methods"] and not cfg.get("data_limits"), "Wrong source method or reduced task populations")
    _require(path.parent.parent.name == case["method"] and
             path.parent.name == f"round_{case['rounds']}", "Method/final round path mismatch")
    assets = _json(ROOT / "configs/final/assets.json")["models"][case["model"]]
    model = cfg["model"]
    _required_fields(model, ["name"], "pinned model")
    _require(str(model["name"]) == assets["repo_id"] or
             str(model["name"]).endswith("/" + assets["repo_id"]), "Model repository mismatch")
    resolved = model.get("revision") or _json(run_root / "base/complete.json").get("resolved_revision")
    _require(resolved == assets["revision"], "Model revision must be pinned or resolved in the original base receipt", "unsupported_metadata")
    generation = cfg["generation"]
    _check_subset(generation, {"train_samples": case["train_samples"], "eval_samples": 64,
                              "max_new_tokens": case["max_new_tokens"],
                              "max_prompt_tokens": case.get("max_prompt_tokens", 1024),
                              "temperature": .8, "top_p": .95, "top_k": 0}, "generation")
    _require(generation.get("training_decoder_overrides", {}) == case.get("training_decoder_overrides", {}),
             "Training decoder override mismatch")
    cal = cfg["calibration"]
    train = cfg["train"]
    # Templates declare all nondefault calibration/training controls. The original
    # config digest above remains authoritative; current templates only constrain it.
    template = case.get("template_config")
    if template:
        template_path = ROOT / template
        _require(template_path.is_file(), f"Missing declared template {template}", "unsupported_metadata")
        try:
            if template_path.suffix == ".json":
                base = _json(template_path)
            else:
                import yaml
                base = yaml.safe_load(template_path.read_text(encoding="utf-8"))
        except ImportError as exc:
            raise QualificationError("unsupported_metadata", "PyYAML required to qualify this declared template") from exc
        expected_cal = dict(base["calibration"])
        expected_train = dict(base["train"])
    else:
        expected_cal = {"max_length": 1536, "span_mode": "completion", "layers": None,
                        "rank_fraction": .5, "tau": 1.0, "rho": .5}
        expected_train = {"epochs": 1, "batch_size": 1, "gradient_accumulation_steps": 16,
                          "max_length": 1536, "learning_rate": 1e-5, "weight_decay": .01,
                          "warmup_ratio": .03, "max_grad_norm": 1.0, "lora_rank": 8,
                          "lora_alpha": 8, "lora_dropout": .05,
                          "gradient_checkpointing": True}
    expected_cal.update(max_examples=case["calibration_examples"], tau=case.get("tau", 1.0),
                        reestimate_each_round=case.get("reestimate_each_round", True))
    if "layers" in case:
        expected_cal["layers"] = case["layers"]
    expected_cal.update(case.get("calibration_overrides", {}))
    if case["method"] != "spectral_learned":
        expected_cal.pop("gain_learning", None)
        expected_cal.pop("matched_reference_fit_examples", None)
        _require("gain_learning" not in cal and "matched_reference_fit_examples" not in cal,
                 "Unexpected learned-gain controls in fixed/baseline case")
    cal_view = cal
    if binding_format == "original_native_manifest" and "reestimate_each_round" not in cal:
        if case["method"] not in {"plain", "ssd"}:
            provenance = _json(path.parent / "calibration_provenance.json")
            wanted = "reestimated" if case.get("reestimate_each_round", True) else "fixed_round_1"
            _require(provenance.get("mode") == wanted, "Historical geometry refresh provenance differs")
        cal_view = {**cal, "reestimate_each_round": case.get("reestimate_each_round", True)}
    _check_subset(cal_view, expected_cal, "calibration")
    expected_train.update(loss_scope="all", fixed_anchor_replay=bool(case.get("anchor_replay", False)))
    if case.get("target_token_budget"):
        expected_train["target_token_budget"] = case["target_token_budget"]
    else:
        _require("target_token_budget" not in train, "Unexpected target-token budget")
    train_view = ({**train, "fixed_anchor_replay": train.get("fixed_anchor_replay", False)}
                  if binding_format == "original_native_manifest" else train)
    _check_subset(train_view, expected_train, "train")
    _require(not case.get("token_loss_reweighting", False) and case.get("lora_update_scale", 1) == 1,
             "Unsupported loss reweighting or LoRA update scaling", "unsupported_format")
    evaluation = cfg["evaluation"]
    if binding_format == "frozen_v2_case":
        _check_subset(evaluation, {"backend": "bwrap", "allow_unsafe_local": False}, "evaluation")
    else:
        _require(evaluation.get("backend") in {"docker", "bwrap", "local"}, "Missing original verifier", "unsupported_metadata")
    return plan, manifest, assets


def _input_identity(plan, manifest):
    cfg = manifest["config"]
    required_counts = {"train": 291, "calibration": 50, "validation": 30, "eval": 500}
    _require(set(cfg["data"]) == set(required_counts), "Native data splits are incomplete")
    identities, tasks = {}, {}
    for split, count in required_counts.items():
        source = Path(cfg["data"][split])
        _require(source.is_file(), f"Original {split} source must be available for read-only qualification: {source}",
                 "unsupported_metadata")
        rows = _rows(source)
        ids = [row["task_id"] for row in rows]
        info = {"sha256": hash_file(source), "count": len(rows), "task_ids": ids}
        if "data_identity" in plan:
            expected = plan["data_identity"].get(split, {})
            _require(all(expected.get(k) == info[k] for k in info), f"Original {split} source differs from case plan")
        _require(len(rows) == count and len(set(ids)) == count,
                 f"Wrong {split} size or duplicate task identity")
        _require(ids == manifest["selected_task_ids"].get(split),
                 f"Selected {split} task identity/order mismatch")
        snapshot = Path(plan["_source_root"]) / "tasks" / f"{split}.jsonl"
        _require(_rows(snapshot) == rows, f"Original {split} snapshot differs from native inputs")
        identities[split] = info
        tasks[split] = {row["task_id"]: row for row in rows}
    seen = set()
    for split in required_counts:
        _require(not (seen & tasks[split].keys()), f"Overlapping task IDs across split {split}")
        seen.update(tasks[split])
    fingerprint = _native_digest({"config": cfg,
        "data": {split: info["sha256"] for split, info in identities.items()},
        "implementation": manifest["implementation_hashes"],
        "evaluation_runtime": manifest["evaluation_runtime"], "training_runtime": manifest["training_runtime"]})
    _require(_native_digest([fingerprint, manifest["local_base_fingerprint"]]) == manifest["fingerprint"],
             "Original native config/data/implementation/runtime fingerprint mismatch")
    return identities, tasks


def _harness_hash(task):
    tests = task["tests"]
    _require(isinstance(tests, str) and bool(tests.strip()), "Missing native tests", "unsupported_metadata")
    try:
        defines_check = any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "check"
                            for node in ast.parse(tests).body)
    except SyntaxError as exc:
        raise QualificationError("integrity_mismatch", "Invalid native test source") from exc
    if task.get("test_mode") == "check" or defines_check:
        _require(bool(task.get("entry_point")), "Missing check entry point", "unsupported_metadata")
        tests += f"\ncheck({task['entry_point']})\n"
    value = {"task_id": task["task_id"], "tests": tests, "test_mode": task.get("test_mode"),
             "entry_point": task.get("entry_point"), "completion_mode": task.get("completion_mode"),
             "continuation_prefix": task.get("code_prefix", task["prompt"])
             if task.get("completion_mode") == "continuation" else None}
    return _native_digest(value)


def _sample_coverage(raw, verified, task_ids, samples=64):
    expected = {(tid, sid) for tid in task_ids for sid in range(samples)}
    def index(rows):
        result = {}
        for row in rows:
            _required_fields(row, ["task_id", "sample_id", "completion"], "sample")
            key = (row["task_id"], row["sample_id"])
            _require(type(row["sample_id"]) is int and key in expected and key not in result,
                     "Duplicate, unexpected, or mistyped sample key")
            _require(isinstance(row["completion"], str), "Completion must be text")
            result[key] = row
        _require(set(result) == expected, "Incomplete verified/raw sample coverage")
        return result
    raw_index, verified_index = index(raw), index(verified)
    for key, row in raw_index.items():
        checked = verified_index[key]
        _require(all(field in checked and checked[field] == value for field, value in row.items()),
                 f"Verifier changed or dropped raw sample fields: {key}")
        _require(type(checked.get("correct")) is bool, f"Missing boolean correctness for {key}")
        _require(checked["correct"] == (checked.get("status") == "passed"), f"Outcome/status mismatch for {key}")
    return verified_index


def _validate_values(obj, verified_index, tasks):
    from improving.metrics import implementation_proxy
    entries, agg, protocol = obj["per_task"], obj["aggregate"], obj["protocol"]
    _require(set(entries) == set(tasks), "Metric task identities differ from verified sources")
    expected_n = protocol.get("expected_samples")
    _require((type(expected_n) is int and expected_n == 64) or (isinstance(expected_n, dict) and set(expected_n) == set(tasks)
                                 and all(type(n) is int and n == 64 for n in expected_n.values())),
             "Final protocol requires n=64; n=16 history is supplementary", "protocol_mismatch")
    required = ("1", "16", "64")
    total_correct = 0
    for tid, item in entries.items():
        correct = sum(verified_index[(tid, sid)]["correct"] for sid in range(64))
        total_correct += correct
        _require(item.get("sample_count") == 64 and item.get("correct_count") == correct,
                 f"Metric/outcome count mismatch for {tid}")
        for k in required:
            ki = int(k)
            value = 1 - (math.comb(64-correct, ki) / math.comb(64, ki) if 64-correct >= ki else 0)
            _equal_number(item.get("pass_at_k", {}).get(k), value, f"{tid} pass@{k}")
        proxy = item.get("implementation_proxy", {})
        counts = proxy.get("counts", {})
        _require(isinstance(counts, dict) and all(type(n) is int and n > 0 for n in counts.values()),
                 f"Invalid AST label counts for {tid}")
        labeled = sum(counts.values())
        recomputed = Counter()
        for sid in range(64):
            record = verified_index[(tid, sid)]
            if record["correct"]:
                label = implementation_proxy(record.get("code", record["completion"]))
                if label is not None:
                    recomputed[label] += 1
        _require(dict(recomputed) == counts, f"AST label counts disagree with verified program text for {tid}")
        _require(labeled <= correct and proxy.get("labeled_correct_count") == labeled and
                 proxy.get("unique_label_count") == (len(counts) if labeled == correct else None), f"Inconsistent AST counts for {tid}")
        expected_status = "no_correct" if correct == 0 else "complete" if labeled == correct else "incomplete"
        _require(proxy.get("status") == expected_status, f"Incorrect AST coverage status for {tid}")
        coverage = len(counts) if labeled == correct else None
        diversity = (sum(1 - (math.comb(correct-n, 4)/math.comb(correct, 4) if correct-n >= 4 else 0)
                         for n in counts.values()) if labeled == correct and correct >= 4 else None)
        _equal_number(proxy.get("coverage_at_k", {}).get("64"), coverage, f"{tid} C64")
        _equal_number(proxy.get("correct_matched_coverage_at_budgets", {}).get("4"), diversity, f"{tid} D4")
    _require(agg.get("task_count") == 500 and agg.get("sample_count") == 32000 and
             agg.get("correct_count") == total_correct, "Aggregate count mismatch")
    for field in ("pass@1", "pass@16", "pass@64", "C64", "D4"):
        values = [_task_value(entries[tid], field) for tid in sorted(entries)]
        available = [value for value in values if value is not None]
        if field.startswith("pass@"):
            summary = agg.get("pass_at_k", {}).get(field.split("@")[1], {})
        else:
            proxy = agg.get("implementation_proxy", {})
            summary = (proxy.get("coverage_at_k", {}).get("64", {}) if field == "C64" else
                       proxy.get("correct_matched_coverage_at_budgets", {}).get("4", {}))
        _equal_number(summary.get("mean"), sum(available)/len(available) if available else None,
                      f"aggregate {field}")
        _require(summary.get("eligible_tasks") == len(available) and summary.get("total_tasks") == 500,
                 f"Aggregate eligibility mismatch for {field}")


def load_metric(path: Path, case: dict) -> dict:
    path = path.expanduser().resolve()
    plan, manifest, assets = _case_binding(path, case)
    cfg = manifest["config"]
    identities, tasks = _input_identity(plan, manifest)
    seal = _json(path.parent / "complete.json")
    _require(seal.get("status") == "completed", "Round is not completed", "incomplete_source")
    run_root = path.parents[2]
    for stage in [run_root / "base", *[run_root / case["method"] / f"round_{r}" for r in range(1, case["rounds"] + 1)]]:
        recorded = _json(stage / "complete.json")
        _require(stage.name == "base" or recorded.get("status") == "completed", "An earlier native round is incomplete", "incomplete_source")
        _require(isinstance(recorded.get("files"), dict) and recorded["files"], "Missing original stage file seal", "unsupported_metadata")
        for relative, expected in recorded["files"].items():
            file = (stage / relative).resolve()
            _require(file.is_relative_to(stage.resolve()) and file.is_file() and hash_file(file) == expected,
                     f"Original stage artifact changed: {file}")
    required_files = (path.name, "evaluation.jsonl", "evaluation.verified.jsonl",
                      "evaluation.jsonl.budget.json", "train.jsonl", "train.jsonl.budget.json", "training_stats.json")
    for name in required_files:
        source = path.parent / name
        _require(source.is_file() and seal.get("files", {}).get(name) == hash_file(source),
                 f"Missing or mismatched sealed raw/verified/metric/statistics hash: {name}")
    obj = _json(path)
    _required_fields(obj, ["protocol", "aggregate", "per_task"], "native metric")
    protocol = obj["protocol"]
    _require(protocol.get("evaluation_provenance_status") == "task_local_v2",
             "Legacy/missing verifier provenance is not final evidence", "unsupported_metadata")
    verifier = protocol.get("evaluation", {})
    _required_fields(verifier, ["provenance_version", "backend", "code_extraction", "timeout",
                                "protocol_version", "runner_sha256"], "verifier")
    if verifier.get("backend") == "bwrap":
        _required_fields(verifier, ["native_sandbox"], "native sandbox")
    _check_subset(verifier, {"provenance_version": 2, "backend": cfg["evaluation"]["backend"],
                              "code_extraction": cfg["evaluation"]["code_extraction"],
                              "timeout": float(cfg["evaluation"]["timeout"]),
                              "protocol_version": "task-tests-v2"}, "verifier")
    raw = _rows(path.parent / "evaluation.jsonl")
    checked = _sample_coverage(raw, _rows(path.parent / "evaluation.verified.jsonl"), tasks["eval"])
    harnesses = {tid: _harness_hash(task) for tid, task in tasks["eval"].items()}
    _require(protocol.get("evaluation_task_harnesses") == harnesses, "Metric source-test harness hashes mismatch")
    for row in checked.values():
        _check_subset(row, {"seed": case["seed"], "method": case["method"], "round": case["rounds"]}, "sample")
        provenance = row.get("evaluation_provenance", {})
        _require(provenance.get("task_harness_sha256") == harnesses[row["task_id"]] and
                 {key: value for key, value in provenance.items() if key != "task_harness_sha256"} == verifier,
                 "Sample verifier/harness differs from metric provenance")
    for stage, filename, n in (("evaluation", "evaluation", 64), ("training", "train", case["train_samples"])):
        budget = _json(path.parent / f"{filename}.jsonl.budget.json")
        emitted = budget.get("protocol", {})
        settings = {key: value for key, value in cfg["generation"].items() if key not in ("train_samples", "eval_samples")}
        settings["samples"] = n
        if stage == "training":
            if case["method"] == "ssd":
                settings.update(temperature=1.5, top_p=.8, top_k=20)
            else:
                settings.update(settings.get("training_decoder_overrides", {}))
            settings.pop("training_decoder_overrides", None)
        _check_subset(emitted, {"seed": case["seed"], "method": case["method"], "round": case["rounds"],
                                "stage": stage, "settings": settings}, f"{stage} generation")
        teacher_stage = (run_root / "base" if case["rounds"] == 1 else
                         run_root / case["method"] / f"round_{case['rounds'] - 1}")
        identity = seal.get("model_identity") if stage == "evaluation" else _json(teacher_stage / "complete.json").get("model_identity")
        _require(emitted.get("model_identity") == identity and
                 isinstance(emitted.get("model_identity"), str), f"{stage} model lineage receipt mismatch")
        expected_count = 500 if stage == "evaluation" else 291
        _require(budget.get("tasks") == expected_count and budget.get("samples") == expected_count*n,
                 f"{stage} sample budget mismatch")
    training = _rows(path.parent / "train.jsonl")
    # Training also preserves all task/sample identities; correctness is not a filter.
    keys = [(row.get("task_id"), row.get("sample_id")) for row in training]
    _require(len(keys) == len(set(keys)) and set(keys) ==
             {(tid, sid) for tid in tasks["train"] for sid in range(case["train_samples"])},
             "Training raw corpus is incomplete or duplicated")
    stats = _json(path.parent / "training_stats.json")
    _check_subset(stats, {"seed": case["seed"] + case["rounds"], "loss_scope": "all",
                           "fixed_anchor_replay": bool(case.get("anchor_replay", False)),
                           "quality_filtering": False, "budget_label_masking": False,
                           "all_raw_records_retained": True}, "training statistics")
    _require(stats.get("raw_records_received") == 291*case["train_samples"] and
             stats.get("raw_records_retained") == 291*case["train_samples"], "Raw training count mismatch")
    _require(stats.get("anchor_reference_records") == (50 if case.get("anchor_replay") else 0),
             "Anchor replay record count mismatch")
    if case.get("target_token_budget"):
        _require(stats.get("training_budget_mode") == "target_tokens_whole_records" and
                 _number(stats.get("actual_supervised_target_tokens")) and
                 stats["actual_supervised_target_tokens"] >= case["target_token_budget"],
                 "Target token budget was not satisfied")
        extra = stats.get("target_token_overshoot")
        bound = stats.get("target_token_overshoot_upper_bound_exclusive")
        _require(type(extra) is int and type(bound) is int and 0 <= extra < bound
                 and extra == stats["actual_supervised_target_tokens"] - case["target_token_budget"],
                 "Whole-record token budget overshoot is not correctly bounded")
    else:
        _require(stats.get("training_budget_mode") == "fixed_epochs", "Unexpected training budget mode")
    _require(stats.get("all_raw_records_exposed") is True and stats.get("all_training_records_exposed") is True,
             "Not every raw/reference record was exposed to SFT")
    _finite(obj, "metrics")
    _validate_values(obj, checked, tasks["eval"])
    _required_fields(protocol, ["metric_versions", "proxy_version", "sampling", "correct_budget", "ks"], "metric definition")
    _require(protocol["sampling"] == "without_replacement" and 4 in protocol.get("correct_budgets", []),
             "Incompatible coverage estimator")
    signature = {"model": assets, "base_fingerprint": manifest["local_base_fingerprint"],
                 "seed": case["seed"], "rounds": case["rounds"],
                 "inputs": identities, "evaluation_settings": {
                     key: value for key, value in cfg["generation"].items()
                     if key not in ("training_decoder_overrides", "batch_size", "task_batch_size", "sequence_batch_size")},
                 "training_core": {key: value for key, value in cfg["train"].items()
                                   if key not in ("fixed_anchor_replay", "target_token_budget")},
                 "metric_versions": protocol["metric_versions"], "proxy_version": protocol["proxy_version"],
                 "sampling": protocol["sampling"], "verifier": verifier, "task_harnesses": harnesses}
    obj["_qualification"] = {"status": "validated", "comparison_signature": signature,
                              "binding_format": plan["_binding_format"],
                              "plan_sha256": (hash_file(path.parents[3] / "plan.json")
                                              if plan["_binding_format"] == "frozen_v2_case" else None),
                              "manifest_sha256": hash_file(path.parents[2] / "manifest.json"),
                              "verified_sha256": hash_file(path.parent / "evaluation.verified.jsonl"),
                              "actual_supervised_target_tokens": stats.get("actual_supervised_target_tokens"),
                              "target_token_overshoot": stats.get("target_token_overshoot"),
                              "scope": "sealed native raw outcomes with AST text/count recomputation; no candidate programs or models executed"}
    return obj


def comparable(a, b):
    _required_fields(a, ["_qualification"], "qualified left source")
    _required_fields(b, ["_qualification"], "qualified right source")
    _require(a["_qualification"]["comparison_signature"] == b["_qualification"]["comparison_signature"],
             "Actual input/model/revision/training-core/evaluation/verifier protocols differ", "not_comparable")


def _task_value(entry: dict, field: str):
    if field.startswith("pass@"):
        return entry["pass_at_k"].get(field.split("@")[1])
    proxy = entry.get("implementation_proxy", {})
    if field == "C64":
        return proxy.get("coverage_at_k", {}).get("64")
    if field == "D4":
        return proxy.get("correct_matched_coverage_at_budgets", {}).get("4")
    raise ValueError(field)


def paired(a: dict, b: dict, *, nboot=2000, seed=20261107) -> dict:
    common = sorted(set(a["per_task"]) & set(b["per_task"]))
    if len(common) != 500 or set(a["per_task"]) != set(b["per_task"]):
        raise ValueError("Paired comparisons require identical 500-task identities")
    out = {"paired_task_count":500, "bootstrap_unit":"task_not_independent_training_seed"}
    for field in ("pass@1","pass@16","pass@64","C64","D4"):
        va = [_task_value(a["per_task"][k],field) for k in common]
        vb = [_task_value(b["per_task"][k],field) for k in common]
        both = [i for i in range(len(common)) if va[i] is not None and vb[i] is not None]
        only_a = sum(va[i] is not None and vb[i] is None for i in range(len(common)))
        only_b = sum(va[i] is None and vb[i] is not None for i in range(len(common)))
        neither = len(common)-len(both)-only_a-only_b
        if any(not _number(va[i]) or not _number(vb[i]) for i in both):
            raise ValueError(f"Nonfinite or nonnumeric field {field}")
        if field != "D4" and len(both) != 500:
            raise ValueError(f"Incomplete or nonnumeric field {field}")
        if not both:
            out[field] = {"estimate_right_minus_left":None,"ci95_task_bootstrap":None,"eligible_both":0,
                          "only_left":only_a,"only_right":only_b,"neither":neither}
            continue
        differences = [float(vb[i])-float(va[i]) for i in both]
        mean = sum(differences)/len(differences)
        rng = random.Random(seed + {"pass@1":1,"pass@16":16,"pass@64":64,"C64":1064,"D4":2004}[field])
        boot = []
        for _ in range(nboot):
            boot.append(sum(differences[rng.randrange(len(differences))]
                            for _ in differences)/len(differences))
        boot.sort()
        out[field] = {
            "estimate_right_minus_left":mean,
            "ci95_task_bootstrap":[boot[int(0.025*(nboot-1))],
                                   boot[int(0.975*(nboot-1))]],
            "eligible_both":len(both),"only_left":only_a,
            "only_right":only_b,"neither":neither,
        }
    return out


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",default="runs/iclr2027_rebuttal_isolated_v2")
    parser.add_argument("--output-dir",required=True)
    parser.add_argument("--input",action="append",default=[],
                        help="CASE=/absolute/sealed/evaluation.metrics.json (recovered historical result)")
    parser.add_argument("--pair",action="append",default=[],
                        help="LEFT:RIGHT case comparison; if omitted use fixed canonical pair set")
    parser.add_argument("--bootstrap",type=int,default=2000)
    args=parser.parse_args(argv)
    if args.bootstrap < 100:
        raise ValueError("At least 100 task bootstrap draws required")
    rows=json.loads(CASES.read_text(encoding="utf-8"))["cases"]
    cases={x["id"]:x for x in rows}
    external={}
    for raw in args.input:
        if "=" not in raw:
            raise ValueError(f"Expected CASE=/path, got {raw}")
        key,path=raw.split("=",1)
        if key not in cases or key in external:
            raise ValueError("Unknown or repeated explicit case input")
        external[key]=Path(path).expanduser().resolve()
    pairs=[]
    for raw in args.pair:
        if ":" not in raw:raise ValueError("Use LEFT:RIGHT --pair syntax")
        left,right=raw.split(":",1)
        if left not in cases or right not in cases or left==right:
            raise ValueError("Unknown or identical pair ID")
        pairs.append((left,right))
    if not pairs:
        pairs=PAIRS
    root=Path(args.root).expanduser().resolve()
    sources={}
    for left,right in pairs:
        for ident in (left,right):
            if ident in sources:
                continue
            path=metric_file(ident,root,cases,external)
            if not path.is_file():
                sources[ident]={"status":"missing","path":str(path)}
                continue
            try:
                metric=load_metric(path, cases[ident])
                sources[ident]={"status":"validated","path":str(path),
                                "sha256":hash_file(path),"metric":metric,
                                "qualification": metric["_qualification"]}
            except (QualificationError, OSError, KeyError, TypeError, ValueError) as exc:
                sources[ident]={"status":getattr(exc, "status", "unsupported_metadata"),
                                "path":str(path), "reason":str(exc)}
    results=[]
    for left,right in pairs:
        if sources[left]["status"] != "validated" or sources[right]["status"] != "validated":
            results.append({"left":left,"right":right,"status":"missing_source",
                            "left_status":sources[left]["status"],"right_status":sources[right]["status"]})
            continue
        # Protocol-level comparability is validated explicitly by the reviewer
        # case spec; different model, seed, data/length should not be paired here.
        aa,bb=cases[left],cases[right]
        if aa["model"]!=bb["model"] or aa["seed"]!=bb["seed"] or aa["max_new_tokens"]!=bb["max_new_tokens"]:
            raise ValueError(f"Cannot pair mismatched model/seed/length: {left} vs {right}")
        try:
            comparable(sources[left]["metric"], sources[right]["metric"])
            result=paired(sources[left]["metric"],sources[right]["metric"], nboot=args.bootstrap)
        except (QualificationError, ValueError) as exc:
            results.append({"left":left,"right":right,"status":"not_comparable","reason":str(exc)})
            continue
        results.append({"left":left,"right":right,"status":"paired_500_tasks",**result})
    # Independent lineages are the units for across-run variation, not
    # the five correlated distillation rounds or the 500 test questions.
    completed = {(row["left"],row["right"]):row for row in results
                 if row["status"] == "paired_500_tasks"}
    fixed_plain_pairs = [("c36","c01"),("c06","c07"),("c08","c09")]
    seed_variation = {}
    for metric in ("pass@1","pass@64","C64","D4"):
        values = []
        for left,right in fixed_plain_pairs:
            row = completed.get((left,right))
            if row is not None and row[metric].get("estimate_right_minus_left") is not None:
                values.append({"plain":left,"fixed":right,
                               "delta_fixed_minus_plain":row[metric]["estimate_right_minus_left"],
                               "common_eligible_tasks":row[metric]["eligible_both"]})
        mean = sum(x["delta_fixed_minus_plain"] for x in values)/len(values) if values else None
        variance = (sum((x["delta_fixed_minus_plain"]-mean)**2 for x in values)
                    /(len(values)-1)) if len(values)>1 else None
        seed_variation[metric] = {
            "n_independent_training_pairs":len(values),
            "planned_independent_pairs":3,
            "per_seed":values,"mean_delta":mean,
            "sample_standard_deviation":variance**.5 if variance is not None else None,
            "unit":"paired_independent_training_lineage",
        }
    out=Path(args.output_dir).expanduser().resolve()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError("Use a fresh empty --output-dir; never overwrite prior evidence analysis")
    out.mkdir(parents=True,exist_ok=True)
    payload={"protocol":"iclr2027-100percent-readonly-task-paired-v2",
             "status":"observed_where_validated_not_imputed",
             "sources":{k:{k2:v2 for k2,v2 in v.items() if k2!="metric"} for k,v in sources.items()},
             "comparisons":results,
             "independent_training_seed_summary":seed_variation,
             "limitations":["Within-run task bootstrap is not independent training variation.",
                            "Correct-conditioned D4 is evaluated on common eligible tasks only.",
                            "Different benchmark versions/generation policies cannot be combined.",
                            "Original native historical manifests require recoverable pinned identity and full provenance; unsupported/posthoc formats stay unqualified.",
                            "Matched target-token budgets permit bounded whole-record overshoot; report actual counts."],
             }
    (out/"pairwise.json").write_text(json.dumps(payload,indent=2,ensure_ascii=False,allow_nan=False)+"\n")
    with (out/"pairwise.csv").open("w",newline="",encoding="utf-8") as handle:
        w=csv.DictWriter(handle,fieldnames=["left","right","status","metric",
                                            "right_minus_left","ci95_low","ci95_high",
                                            "eligible_both","only_left","only_right","neither"])
        w.writeheader()
        for row in results:
            if row["status"]!="paired_500_tasks":
                w.writerow({"left":row["left"],"right":row["right"],"status":row["status"]})
                continue
            for key in ("pass@1","pass@16","pass@64","C64","D4"):
                value=row[key]
                bounds=value.get("ci95_task_bootstrap") or [None,None]
                w.writerow({"left":row["left"],"right":row["right"],"status":row["status"],
                            "metric":key,"right_minus_left":value.get("estimate_right_minus_left"),
                            "ci95_low":bounds[0],"ci95_high":bounds[1],
                            "eligible_both":value["eligible_both"],
                            "only_left":value["only_left"],"only_right":value["only_right"],
                            "neither":value["neither"]})
    print(json.dumps({"output_dir":str(out),"compared":sum(r["status"]=="paired_500_tasks" for r in results),
                      "missing":sum(r["status"]=="missing_source" for r in results)}))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
