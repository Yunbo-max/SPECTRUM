#!/usr/bin/env python3
"""One-case-at-a-time ICLR 2027 rebuttal orchestration (stdlib planning).

No case runs implicitly. Each case owns a frozen config, a distinct model
run root, local logs, and a completion receipt. A recorded historical result
is not copied or asserted as the output of a newly trained case.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[1]
SPEC = REPO / "experiments/iclr2027_rebuttal/cases.json"
ASSETS = REPO / "configs/final/assets.json"
DEFAULT_ROOT = "runs/iclr2027_rebuttal_isolated_v1"
DATA_COUNTS = {"train": 291, "calibration": 50, "validation": 30, "eval": 500}
DECODERS = {
    "cool": {"temperature": .6, "top_p": .95, "top_k": 0},
    "warm": {"temperature": 1., "top_p": .95, "top_k": 0},
    "ssd_recipe": {"temperature": 1.5, "top_p": .8, "top_k": 20},
}


def load_spec() -> dict:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    if spec["protocol"] != "iclr2027-spectrum-case-isolation-v1":
        raise ValueError("Unexpected frozen rebuttal protocol")
    rows = spec["cases"]
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)) or ids != [f"c{i:02d}" for i in range(len(rows))]:
        raise ValueError("Case IDs must be unique and consecutive c00..")
    if any(row["kind"] not in {"train", "transfer", "decoder", "audit", "semantic"} for row in rows):
        raise ValueError("Unknown case kind")
    return spec


def hbytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(obj: object) -> str:
    return hbytes(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode("utf-8"))


def file_sha(path: Path) -> str:
    sha = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def abs_path(value: str) -> Path:
    path = Path(value).expanduser()
    return (path if path.is_absolute() else REPO / path).resolve()


def store_once(path: Path, data: object) -> None:
    """Never overwrite a sealed plan/configuration. Retry is idempotent."""
    contents = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False,
                          allow_nan=False) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != contents:
            raise ValueError(f"Frozen path changed; choose a fresh root: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(contents)


def one_case(case_id: str) -> dict:
    if not case_id:
        raise ValueError("--case is required for plan/run/status")
    rows = {row["id"]: row for row in load_spec()["cases"]}
    if case_id not in rows:
        raise ValueError(f"Unknown case {case_id}")
    return rows[case_id]


def config_for(case: dict, args: argparse.Namespace, run_root: Path) -> dict:
    """Build a one-method, pinned, five-round config from existing native code."""
    p = REPO / "scripts/run_iclr2027.py"
    spec = importlib.util.spec_from_file_location("_rebuttal_native_planner", p)
    if spec is None or spec.loader is None:
        raise ImportError("Missing native experiment config builder")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    data_root = abs_path(args.data_root)
    native = SimpleNamespace(profile=args.profile, backend="docker",
                             allow_unsafe_local=False, workers=args.workers,
                             data_root=str(data_root))
    cfg = mod.native_config(native, case["model"], int(case["seed"]))
    assets = read_json(ASSETS)
    asset = assets["models"][case["model"]]
    name = asset["repo_id"]
    if args.model_root:
        candidate = abs_path(args.model_root) / name
        if not candidate.is_dir():
            raise FileNotFoundError(f"Explicit pinned model root missing: {candidate}")
        name = str(candidate)
    cfg["model"].update(name=name, revision=asset["revision"], local_files_only=bool(args.model_root))
    cfg["output_dir"] = str(run_root)
    cfg["label"] = case["id"]
    cfg["rebuttal_case"] = case["id"]
    cfg["rounds"] = int(case["rounds"])
    cfg["checkpoint_retention"] = "all"
    cfg["methods"] = [case["method"]]
    cfg["data"] = {split: str(data_root / f"{split}.jsonl") for split in DATA_COUNTS}
    cfg["data_limits"] = {}
    cfg["generation"].update(train_samples=case["train_samples"],
                             eval_samples=case["eval_samples"],
                             max_new_tokens=case["max_new_tokens"],
                             max_prompt_tokens=1024,
                             temperature=.8, top_p=.95, top_k=0)
    cfg["calibration"]["max_examples"] = int(case["calibration_examples"])
    cfg["calibration"]["tau"] = float(case.get("tau", 1.0))
    cfg["calibration"]["reestimate_each_round"] = case.get("reestimate_each_round", True)
    if "layers" in case:
        cfg["calibration"]["layers"] = case["layers"]
    cfg["train"]["loss_scope"] = "all"
    if case.get("anchor_replay"):
        cfg["train"]["fixed_anchor_replay"] = True
    if case.get("target_token_budget") is not None:
        cfg["train"]["target_token_budget"] = int(case["target_token_budget"])
    if case.get("training_decoder_overrides"):
        cfg["generation"]["training_decoder_overrides"] = case["training_decoder_overrides"]
    cfg["evaluation"].update(backend="docker", allow_unsafe_local=False,
                             workers=args.workers, bootstrap_samples=2000)
    cfg["diagnostics"].update(evaluate_generation_policy=False)
    return cfg


def build_plan(case: dict, args: argparse.Namespace) -> dict:
    root = abs_path(args.root)
    directory = root / case["id"]
    run_root = directory / "run"
    plan: dict = {
        "protocol": load_spec()["protocol"], "case": case,
        "case_spec_sha256": digest(case),
        "spec_file_sha256": file_sha(SPEC),
        "root": str(directory), "output": str(run_root),
        "kind": case["kind"], "status": "planned_not_executed",
        "run_command_requires_explicit_execute": True,
        "training_output_not_reused_from_historical_audit": True,
    }
    if case["kind"] == "train":
        cfg = config_for(case, args, run_root)
        plan["config_file"] = str(directory / "config.json")
        plan["config_sha256"] = digest(cfg)
        plan["command"] = [sys.executable, "-m", "improving", "run",
                           "--config", plan["config_file"], "--resume"]
        plan["max_requested_training_completions"] = 291 * case["train_samples"] * case["rounds"]
        plan["max_requested_native_eval_completions"] = 500 * case["eval_samples"] * (case["rounds"] + 1)
        # Check these against saved case settings, but do not require data/GPU at plan time.
        store_once(Path(plan["config_file"]), cfg)
    elif case["kind"] in ("transfer", "decoder"):
        if not args.source_run:
            raise ValueError(f"{case['id']} needs --source-run pointing to an actual sealed training root")
        source = abs_path(args.source_run)
        plan["source_run"] = str(source)
        plan["source_methods"] = args.source_methods or ""
        plan["round"] = case["round"]
        plan["samples"] = case["samples"]
        if case["kind"] == "transfer":
            plan["benchmark_root"] = str(abs_path(args.benchmark_root))
            plan["command"] = [
                sys.executable, "experiments/iclr2027/transfer.py",
                "--run-dir", str(source), "--benchmark", case["benchmark"],
                "--benchmark-root", plan["benchmark_root"], "--output-dir", str(run_root),
                "--round", str(case["round"]), "--samples", str(case["samples"]),
                "--bootstrap-samples", "2000", "--backend", "docker", "--resume",
            ]
            if args.source_methods:
                plan["command"] += ["--methods", args.source_methods]
        else:
            plan["command"] = [
                sys.executable, "scripts/rebuttal_decoder_eval.py",
                "--run-dir", str(source), "--output-dir", str(run_root),
                "--round", str(case["round"]), "--samples", str(case["samples"]),
                "--decoder", case["decoder"], "--resume"
            ]
            if args.source_methods:
                plan["command"] += ["--methods", args.source_methods]
    elif case["kind"] == "audit":
        plan["evidence_sha256"] = {name: file_sha(REPO / name) for name in case["evidence"]}
        plan["command"] = ["read_only_audit", case["id"]]
    else:
        if not args.task_file or len(args.evidence) < 2:
            raise ValueError("Semantic case needs --task-file and >=2 --evidence METHOD=/absolute/verified.jsonl")
        inputs = []
        for item in args.evidence:
            if "=" not in item:
                raise ValueError(f"Bad --evidence {item}; use METHOD=/path")
            name, value = item.split("=", 1)
            if not name or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_" for ch in name):
                raise ValueError("Evidence method names must be lowercase identifiers")
            path = abs_path(value)
            inputs.append({"method": name, "path": str(path), "sha256": file_sha(path)})
        if len({x["method"] for x in inputs}) != len(inputs):
            raise ValueError("Duplicate semantic method name")
        tasks = abs_path(args.task_file)
        plan["semantic_inputs"] = inputs
        plan["task_file"] = str(tasks)
        plan["task_file_sha256"] = file_sha(tasks)
        plan["command"] = [sys.executable, "scripts/rebuttal_semantic_blind.py",
                           "--plan", str(directory / "plan.json"), "--output-dir", str(run_root)]
    store_once(directory / "plan.json", plan)
    return plan


def read_plan(case: dict, args: argparse.Namespace) -> dict:
    directory = abs_path(args.root) / case["id"]
    plan = read_json(directory / "plan.json")
    if (plan["case"] != case or plan.get("spec_file_sha256") != file_sha(SPEC)
            or plan["case_spec_sha256"] != digest(case)
            or plan["protocol"] != load_spec()["protocol"]
            or plan["root"] != str(directory)):
        raise ValueError("Frozen case specification or output root changed")
    if case["kind"] == "train":
        cfg = read_json(Path(plan["config_file"]))
        if (digest(cfg) != plan["config_sha256"]
                or cfg["output_dir"] != plan["output"]
                or cfg["methods"] != [case["method"]]
                or cfg["model"]["revision"] != read_json(ASSETS)["models"][case["model"]]["revision"]):
            raise ValueError("Frozen training config or pinned model changed")
    elif case["kind"] == "audit":
        if {p: file_sha(REPO / p) for p in case["evidence"]} != plan["evidence_sha256"]:
            raise ValueError("Historic evidence changed since planning")
    elif case["kind"] == "semantic":
        if file_sha(Path(plan["task_file"])) != plan["task_file_sha256"]:
            raise ValueError("Task pool changed since blind selection was frozen")
        for row in plan["semantic_inputs"]:
            if file_sha(Path(row["path"])) != row["sha256"]:
                raise ValueError("Verified input programs changed since plan freeze")
    return plan


def verify_data(cfg: dict) -> None:
    """Check exact task populations before possibly expensive GPU loading."""
    ids_by_split = {}
    for name, count in DATA_COUNTS.items():
        path = Path(cfg["data"][name])
        if not path.is_file():
            raise FileNotFoundError(f"Missing prepared MBPP {name}: {path}")
        rows = []
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    record = json.loads(line)
                    if not isinstance(record.get("task_id"), str):
                        raise ValueError(f"Task without ID in {path}")
                    rows.append(record["task_id"])
        if len(rows) != count or len(set(rows)) != count:
            raise ValueError(f"{name}: expected {count} unique task IDs, got {len(rows)}")
        ids_by_split[name] = set(rows)
    for name, ids in ids_by_split.items():
        for other, second in ids_by_split.items():
            if name < other and ids & second:
                raise ValueError(f"Task ID overlap between {name} and {other}")
    if cfg["generation"]["eval_samples"] != 64 or cfg["generation"]["train_samples"] != 16:
        raise ValueError("Case train/eval budgets were altered")
    if cfg["generation"]["max_new_tokens"] != 512:
        raise ValueError("Original 1.5B comparator protocol requires 512 output tokens")


@contextmanager
def lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, f"pid={os.getpid()}\n".encode())
        yield
    finally:
        os.close(fd)
        path.unlink(missing_ok=True)


def inspect_training(plan: dict, case: dict, hashes: bool = False) -> dict:
    root = Path(plan["output"])
    status = {"case": case["id"], "kind": "train", "state": "pending",
              "expected_rounds": case["rounds"], "verified_rounds": 0,
              "issues": [], "endpoints": {}}
    if not root.exists():
        return status
    status["state"] = "partial"
    summary = root / "run_status.json"
    if not summary.is_file():
        status["issues"].append("No sealed run_status.json")
        return status
    done = read_json(summary)
    if (done.get("status") != "completed" or done.get("verification") != "completed"
            or done.get("rounds") != case["rounds"] or done.get("methods") != [case["method"]]):
        status["issues"].append("Native training has not sealed the declared full case")
        return status
    for r in range(1, case["rounds"] + 1):
        stage = root / case["method"] / f"round_{r}"
        marker = stage / "complete.json"
        metric = stage / "evaluation.metrics.json"
        if not (marker.is_file() and metric.is_file()):
            status["issues"].append(f"Round {r}: missing completion or metrics")
            continue
        receipt = read_json(marker)
        files = receipt.get("files", {})
        if (receipt.get("status") != "completed"
                or "evaluation.metrics.json" not in files
                or "evaluation.verified.jsonl" not in files):
            status["issues"].append(f"Round {r}: invalid native verification receipt")
            continue
        if hashes and file_sha(metric) != files["evaluation.metrics.json"]:
            status["issues"].append(f"Round {r}: checksum mismatch")
            continue
        row = read_json(metric)
        if row.get("task_count") != 500 or row.get("sample_count") != 32000:
            status["issues"].append(f"Round {r}: not 500 x 64 verified samples")
            continue
        values = row.get("pass_at_k", {})
        ast = row.get("implementation_coverage_at_k", {})
        matched = row.get("correct_matched_coverage_at_budgets", {})
        if not all(key in values for key in ("1", "16", "64")) or "64" not in ast:
            status["issues"].append(f"Round {r}: mandatory metrics missing")
            continue
        if r == case["rounds"]:
            status["endpoints"] = {
                "pass@1": values["1"]["mean"],
                "pass@16": values["16"]["mean"],
                "pass@64": values["64"]["mean"],
                "C64": ast["64"]["mean"],
                "D4": matched.get("4", {}).get("mean"),
                "D4_eligible": matched.get("4", {}).get("eligible_tasks"),
            }
        status["verified_rounds"] += 1
    base = root / "base" / "evaluation.metrics.json"
    if not base.is_file() or read_json(base).get("sample_count") != 32000:
        status["issues"].append("Base missing exact 500 x 64 evaluation")
    if not status["issues"] and status["verified_rounds"] == case["rounds"]:
        status["state"] = "complete"
        status["integrity"] = "metric_hash_checked" if hashes else "native_receipt_and_denominator_checked"
    return status


def inspect_eval(plan: dict, case: dict, hashes: bool = False) -> dict:
    out = Path(plan["output"])
    state = {"case": case["id"], "kind": case["kind"], "state": "pending",
             "issues": [], "stages": []}
    if not out.exists():
        return state
    state["state"] = "partial"
    marker = out / "transfer_complete.json" if case["kind"] == "transfer" else out / "decoder_complete.json"
    if not marker.is_file():
        state["issues"].append("No evaluation completion summary")
        return state
    receipt = read_json(marker)
    if receipt.get("status") != "completed":
        state["issues"].append("Summary does not assert completed")
        return state
    stage = out / "base" / "evaluation.metrics.json"
    if not stage.is_file():
        state["issues"].append("Missing original-model evaluation metrics")
        return state
    manifest = read_json(out / "manifest.json")
    selected = manifest.get("protocol", {}).get("methods", [])
    for method in selected:
        name = f"{method}/round_{case['round']}"
        metric = out / name / "evaluation.metrics.json"
        marker = out / name / "complete.json"
        if not (metric.is_file() and marker.is_file()):
            state["issues"].append(f"Missing evaluated source checkpoint: {name}")
            continue
        info = read_json(metric)
        if info.get("sample_count") != len(manifest["protocol"]["task_ids"]) * case["samples"]:
            state["issues"].append(f"Incorrect eval population: {name}")
        else:
            state["stages"].append(name)
    if not state["issues"] and state["stages"]:
        state["state"] = "complete"
    return state


def status_case(case: dict, args: argparse.Namespace) -> dict:
    try:
        plan = read_plan(case, args)
    except FileNotFoundError:
        return {"case": case["id"], "kind": case["kind"],
                "state": "unplanned", "historical_source_status": case["source_status"]}
    if case["kind"] == "train":
        data = inspect_training(plan, case, hashes=args.verify_hashes)
    elif case["kind"] in ("transfer", "decoder"):
        data = inspect_eval(plan, case, hashes=args.verify_hashes)
    else:
        done = Path(plan["root"]) / "case_receipt.json"
        data = {"case": case["id"], "kind": case["kind"],
                "state": ("historical_audit_only" if done.is_file() and case["kind"] == "audit"
                          else "annotation_packet_prepared" if done.is_file() else "planned")}
    data["historical_source_status"] = case["source_status"]
    data["output"] = plan["output"]
    return data


def execute_case(case: dict, args: argparse.Namespace) -> dict:
    plan = read_plan(case, args)
    if not args.execute:
        return {"case": case["id"], "dry_run": True,
                "command": plan["command"], "output": plan["output"],
                "source_status": case["source_status"]}
    if case["kind"] == "train" and case["source_status"].startswith("historical_complete") and not args.rerun_historical:
        raise ValueError("Historical case already has archived evidence; use --rerun-historical only when a new run is genuinely necessary")
    directory = Path(plan["root"])
    with lock(directory / "case.lock"):
        if case["kind"] == "train":
            cfg = read_json(Path(plan["config_file"]))
            verify_data(cfg)
            subprocess.run(plan["command"], cwd=REPO, check=True)
            state = inspect_training(plan, case, hashes=True)
            if state["state"] != "complete":
                raise RuntimeError(f"Training returned but native verification incomplete: {state['issues']}")
        elif case["kind"] in ("transfer", "decoder"):
            source = Path(plan["source_run"])
            if not (source / "manifest.json").is_file():
                raise FileNotFoundError("Source training manifest missing")
            chosen = plan["source_methods"].split(",") if plan["source_methods"] else read_json(source / "manifest.json")["config"]["methods"]
            for method in chosen:
                if not (source / method / f"round_{case['round']}" / "model/config.json").is_file():
                    raise FileNotFoundError(f"Source checkpoint missing or pruned: {method}, round {case['round']}")
            subprocess.run(plan["command"], cwd=REPO, check=True)
            state = inspect_eval(plan, case)
            if state["state"] != "complete":
                raise RuntimeError(f"Evaluation incomplete: {state['issues']}")
        elif case["kind"] == "audit":
            state = {"kind": "historical_evidence_audit", "no_new_experiment": True,
                     "evidence_files": plan["evidence_sha256"]}
        else:
            subprocess.run(plan["command"], cwd=REPO, check=True)
            state = {"kind": "blinded_annotation_packet", "manual_semantic_labels_not_collected": True}
        store_once(directory / "case_receipt.json", {
            "status": "completed", "case": case["id"], "kind": case["kind"],
            "plan_sha256": file_sha(directory / "plan.json"),
            "verified": state,
            "historical_source_status": case["source_status"],
            "no_experiment_if_kind_is_audit_or_semantic": case["kind"] in {"audit", "semantic"},
        })
        return state


def write_report(args: argparse.Namespace) -> dict:
    rows = [status_case(case, args) for case in load_spec()["cases"]]
    root = abs_path(args.root)
    report = root / "report"
    report.mkdir(parents=True, exist_ok=True)
    (report / "cases.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
    with (report / "cases.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["case","kind","state","historical_source_status","output"])
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name) for name in writer.fieldnames})
    return {"report": str(report), "case_count": len(rows),
            "new_completed_training_cases": sum(r["state"] == "complete" and r["kind"] == "train" for r in rows),
            "missing_or_unfinished": [r["case"] for r in rows if r["state"] not in {"complete","historical_audit_only","annotation_packet_prepared"}]}


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--case", help="Fixed case ID c00..c31")
    p.add_argument("command", choices=["list", "plan", "run", "status", "report"])
    p.add_argument("--root", default=DEFAULT_ROOT)
    p.add_argument("--data-root", default="data/mbpp")
    p.add_argument("--benchmark-root", default="data/iclr2027")
    p.add_argument("--model-root", help="Optional local pinned HF model root")
    p.add_argument("--profile", choices=["24gb","80gb"], default="80gb")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--source-run", help="Frozen MBPP source experiment directory")
    p.add_argument("--source-methods", help="Comma-separated selected source arms")
    p.add_argument("--task-file", help="Full immutable evaluation task JSONL, semantic case")
    p.add_argument("--evidence", action="append", default=[],
                   help="Verified code path: METHOD=/abs/path/to/evaluation.verified.jsonl")
    p.add_argument("--execute", action="store_true", help="Only explicit flag can launch any case")
    p.add_argument("--verify-hashes", action="store_true", help="Inspect metrics hashes against receipts")
    p.add_argument("--rerun-historical", action="store_true",
                   help="Explicitly re-run a fully archived historical study if indispensable")
    return p


def main(argv=None) -> int:
    args = make_parser().parse_args(argv)
    try:
        if args.command == "list":
            print(json.dumps(load_spec()["cases"], indent=2, ensure_ascii=False))
            return 0
        if args.command == "report":
            out = write_report(args)
        else:
            case = one_case(args.case)
            if args.command == "plan":
                if args.workers < 1:
                    raise ValueError("--workers must be positive")
                out = build_plan(case, args)
            elif args.command == "run":
                out = execute_case(case, args)
            else:
                out = status_case(case, args)
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError, ImportError, KeyError,
            subprocess.CalledProcessError) as exc:
        print(f"ICLR rebuttal case error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
