#!/usr/bin/env python3
"""Small matched validation pilot for continual spectral-gain retention."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

INPUT_ROOT = Path("/mnt/c/ai/spectrum-run-artifacts/20261108/continual-gains/cases")
DEFAULT_ROOT = Path("/mnt/c/ai/spectrum-run-artifacts/20261109/continual-gain-pilot-v3")
PILOT_PROTOCOL = "spectrum-continual-gains-matched-pilot-v1"
TASK_COUNT = 100
SELECTION_SEED = "spectrum-continual-gain-pilot-20261109"
CASES = (("cg02", "retention"), ("cg03", "conflict"))
GIB = 1024 ** 3


def _study_api():
    import importlib
    source = str(REPO / "src")
    if source in sys.path:
        sys.path.remove(source)
    sys.path.insert(0, source)
    return importlib.import_module("improving.continual_gain_study")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_once(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != payload:
            raise ValueError(f"Refusing to overwrite a different pilot artifact: {path}")
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    os.replace(temporary, path)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def jsonl_rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").split("\n") if line.strip()]


def select_task_ids(rows, count=TASK_COUNT, seed=SELECTION_SEED, group_key="category"):
    """Select a deterministic proportional sample, stratified by benchmark group."""
    if type(count) is not int or count < 1 or count > len(rows):
        raise ValueError("Pilot task count must fit the evaluation population")
    ids = [row.get("task_id") for row in rows]
    if any(not isinstance(value, str) or not value for value in ids) or len(ids) != len(set(ids)):
        raise ValueError("Evaluation rows need unique nonempty task IDs")
    groups = {}
    for row in rows:
        group = str(row.get(group_key, "unknown"))
        groups.setdefault(group, []).append(row)
    quotas = {key: count * len(group) // len(rows) for key, group in groups.items()}
    remainder = count - sum(quotas.values())
    order = sorted(groups, key=lambda key: (-(count * len(groups[key]) % len(rows)), key))
    for key in order[:remainder]:
        quotas[key] += 1
    selected = set()
    for key, group in groups.items():
        ranked = sorted(group, key=lambda row: (
            hashlib.sha256(f"{seed}\0{row['task_id']}".encode("utf-8")).hexdigest(),
            row["task_id"]))
        selected.update(row["task_id"] for row in ranked[:quotas[key]])
    return [task_id for task_id in ids if task_id in selected]


def _load_inputs(root):
    configs = {}
    for case_id, _ in CASES:
        config = read_json(root / case_id / "config.json")
        if config.get("backbone_update") != "frozen" or config.get("order") != ["math", "qa"]:
            raise ValueError(f"{case_id} is not the approved frozen Math→QA case")
        if config.get("rounds_per_domain") != 1:
            raise ValueError("The pilot uses exactly one stage per domain")
        configs[case_id] = config
    left, right = (configs[case] for case, _ in CASES)
    normalize = lambda value: {key: item for key, item in value.items() if key != "output_dir"}
    if normalize(left) != normalize(right):
        raise ValueError("cg02 and cg03 must have identical non-method experiment settings")
    return configs


def plan(root=DEFAULT_ROOT, inputs=INPUT_ROOT):
    root, inputs = Path(root), Path(inputs)
    configs = _load_inputs(inputs)
    selected, input_hashes = {}, {}
    for domain in ("math", "qa"):
        data_root = Path(configs["cg02"]["domains"][domain]["data"]["output_dir"])
        eval_path = data_root / "eval.jsonl"
        rows = jsonl_rows(eval_path)
        selected[domain] = select_task_ids(
            rows, group_key=("level" if domain == "math" else "category"))
        input_hashes[domain] = {
            "manifest_sha256": sha256(data_root / "manifest.json"),
            "eval_sha256": sha256(eval_path),
            "task_ids_sha256": hashlib.sha256(
                json.dumps(selected[domain], separators=(",", ":")).encode()).hexdigest(),
            "population": len(rows), "selected": len(selected[domain]),
        }
    for case_id, _ in CASES:
        config = configs[case_id]
        config["output_dir"] = str(root / case_id / "study")
        config["pilot_protocol"] = PILOT_PROTOCOL
        for domain in ("math", "qa"):
            evaluation = config["domains"][domain]["evaluation"]
            evaluation["samples"] = 1
            evaluation["profile"] = "matched_pilot_v1"
            evaluation["task_ids"] = selected[domain]
            evaluation["rng_group"] = PILOT_PROTOCOL
        write_once(root / case_id / "config.json", config)
    selection = {
        "protocol": PILOT_PROTOCOL, "selection_seed": SELECTION_SEED,
        "tasks_per_domain": TASK_COUNT, "task_ids": selected, "inputs": input_hashes,
    }
    write_once(root / "task_selection.json", selection)
    study = _study_api()
    pilot_plan = {
        "protocol": PILOT_PROTOCOL, "cases": [{"id": case, "method": method} for case, method in CASES],
        "backbone_update": "frozen", "order": ["math", "qa"], "rounds_per_domain": 1,
        "training_and_calibration": "unchanged 1024 training tasks; 54 FIT and 10 guard references",
        "evaluation": "100 deterministic stratified tasks per domain; one sample each; shared RNG group",
        "data_inputs": input_hashes, "source_identity": study.source_identity(),
        "pilot_source_sha256": sha256(Path(__file__)),
        "configs": {case: sha256(root / case / "config.json") for case, _ in CASES},
        "task_selection_sha256": sha256(root / "task_selection.json"),
        "limits": {"gpu": 1, "process_budget_gib": 28, "device_stop_gib": 83},
    }
    write_once(root / "pilot_plan.json", pilot_plan)
    return pilot_plan


def load_plan(root):
    root = Path(root)
    manifest = read_json(root / "pilot_plan.json")
    if manifest.get("protocol") != PILOT_PROTOCOL:
        raise ValueError("Unexpected pilot plan protocol")
    if sha256(Path(__file__)) != manifest["pilot_source_sha256"]:
        raise ValueError("Pilot runner source changed; prepare a fresh output root")
    study = __import__("improving.continual_gain_study", fromlist=["source_identity"])
    if study.source_identity() != manifest["source_identity"]:
        raise ValueError("Continual-gain source changed after planning")
    for case_id, _ in CASES:
        config_path = root / case_id / "config.json"
        if sha256(config_path) != manifest["configs"][case_id]:
            raise ValueError(f"Pilot config changed for {case_id}")
    if sha256(root / "task_selection.json") != manifest["task_selection_sha256"]:
        raise ValueError("Pilot task selection changed")
    config = read_json(root / "cg02" / "config.json")
    for domain, expected in manifest["data_inputs"].items():
        data_root = Path(config["domains"][domain]["data"]["output_dir"])
        if (sha256(data_root / "manifest.json") != expected["manifest_sha256"]
                or sha256(data_root / "eval.jsonl") != expected["eval_sha256"]):
            raise ValueError(f"Prepared {domain} evaluation input changed")
    return manifest


def run(root=DEFAULT_ROOT, *, execute=False, resume=False):
    if not execute:
        raise ValueError("GPU work requires the explicit --execute flag")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "1":
        raise RuntimeError("Continual-gain pilot is restricted to physical GPU 1")
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable")
    free, total = torch.cuda.mem_get_info()
    budget, reserve = 28 * GIB, 12 * GIB
    if free < budget + reserve:
        raise RuntimeError("GPU1 admission requires a 28 GiB budget plus 12 GiB reserve")
    torch.cuda.set_per_process_memory_fraction(budget / total, device=0)
    study = _study_api()
    root = Path(root)
    load_plan(root)
    outcomes = []
    for case_id, method in CASES:
        config = read_json(root / case_id / "config.json")
        method_root = Path(config["output_dir"]) / method
        if (method_root / "run_complete.json").exists():
            result = study.summarize_continual_gain_study(config)
        else:
            result = study.run_continual_gain_study(
                config, method, resume=resume or (method_root / "manifest.json").exists())
        outcome = {"case": case_id, "method": method,
                   "status": result["status"], "report": result.get("report", result)}
        outcomes.append(outcome)
        write_once(root / case_id / "run_result.json", outcome)
    return {"status": "completed", "pilot_root": str(root), "cases": outcomes}


def report(root=DEFAULT_ROOT):
    root = Path(root)
    load_plan(root)
    study = _study_api()
    results = {}
    for case_id, method in CASES:
        config = read_json(root / case_id / "config.json")
        summary = study.summarize_continual_gain_study(config)
        results[method] = summary["methods"].get(method, {})
    if any(value.get("status") != "complete" for value in results.values()):
        raise RuntimeError("Wait for both pilot methods to complete before comparing results")
    compact = {}
    for method, summary in results.items():
        matrix = summary.get("accuracy_matrix", [])
        def accuracy(stage, domain):
            return next(row["metrics"]["accuracy"] for row in matrix
                        if row["stage"] == stage and row["evaluated_domain"] == domain
                        and row["policy"] == "controlled")
        math_exit, math_final = accuracy(1, "math"), accuracy(2, "math")
        compact[method] = {
            "math_at_exit": math_exit, "math_after_qa": math_final,
            "math_retention_delta": math_final - math_exit,
            "qa_after_learning": accuracy(2, "qa"),
            "controller_stages": summary.get("completed_stages", []),
            "backward_changes": summary.get("backward_changes", []),
        }
    output = {
        "protocol": PILOT_PROTOCOL, "pilot_root": str(root), "results": compact,
        "projection_vs_retention_math_delta": (
            compact["conflict"]["math_retention_delta"]
            - compact["retention"]["math_retention_delta"]),
        "projection_vs_retention_qa_accuracy_delta": (
            compact["conflict"]["qa_after_learning"]
            - compact["retention"]["qa_after_learning"]),
        "interpretation": "Exploratory matched-task pilot; one trajectory and 100 tasks per domain.",
    }
    write_once(root / "pilot_report.json", output)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run", "report"))
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--inputs", type=Path, default=INPUT_ROOT)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.command == "plan":
        result = plan(args.root, args.inputs)
    elif args.command == "run":
        result = run(args.root, execute=args.execute, resume=args.resume)
    else:
        result = report(args.root)
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()

