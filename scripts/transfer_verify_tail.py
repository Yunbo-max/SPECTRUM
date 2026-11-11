#!/usr/bin/env python3
"""CPU-only verification tail for transfer evaluations whose GPU jobs were
recycled during CPU-bound verification (qz auto-recycle: GPU<40 for 3h).

Mirrors experiments/iclr2027/transfer.py but performs no generation and
loads no model: every stage with existing evaluation.jsonl but no
complete.json is verified and sealed here, on a host without GPUs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
BENCHMARKS = ("humanevalplus", "apps_intro", "codecontests", "livecodebench")


def _sha(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _read(path: Path):
    return json.loads(path.read_text())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--benchmark", choices=BENCHMARKS, required=True)
    parser.add_argument("--benchmark-root", default="data/iclr2027")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--round", type=int, default=5)
    parser.add_argument("--methods", help="Comma-separated source method keys; default all")
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--memory-mb", type=int, default=1024)
    parser.add_argument("--backend", choices=["docker", "local", "bwrap"], default="local")
    parser.add_argument("--allow-unsafe-local", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Accepted for command parity")
    args = parser.parse_args()
    os.chdir(REPO)
    try:
        from improving.data import assert_disjoint_splits, read_jsonl
        from improving.pipeline import evaluate_file, checkpoint_fingerprint
        from improving.utils import atomic_json, stable_hash

        root = Path(args.run_dir)
        source = _read(root / "manifest.json")
        config = source["config"]
        task_path = Path(args.benchmark_root) / args.benchmark / "eval.jsonl"
        prepared = _read(task_path.parent / "manifest.json")
        if prepared.get("name") != args.benchmark:
            raise ValueError("Prepared benchmark manifest names a different dataset")
        tasks = read_jsonl(task_path)
        splits = {name: read_jsonl(root / "tasks" / f"{name}.jsonl")
                  for name in ("train", "calibration", "validation")}
        splits["eval"] = tasks
        assert_disjoint_splits(splits)
        evaluation = dict(config.get("evaluation", {}))
        evaluation.update(timeout=args.timeout, memory_mb=args.memory_mb,
                          backend=args.backend, allow_unsafe_local=args.allow_unsafe_local)
        callback = None
        if args.benchmark == "humanevalplus":
            from improving.benchmarks import make_humanevalplus_evaluator
            settings = {"backend": args.backend, "allow_unsafe_local": args.allow_unsafe_local,
                        "parallel": min(4, evaluation.get("workers", 4))}
            callback, _ = make_humanevalplus_evaluator(task_path, settings=settings)
        methods = args.methods.split(",") if args.methods else None
        selected = list(config["methods"] if methods is None else methods)
        if not set(selected) <= set(config["methods"]):
            raise ValueError("Requested methods are absent from the source training manifest")

        output = Path(args.output_dir)
        manifest = _read(output / "manifest.json")
        fingerprint = manifest["fingerprint"]
        protocol = manifest["protocol"]
        seed = int(config.get("seed", 42))
        verify = evaluate_file if callback is None else callback
        settings = config["model"]
        local_base = Path(settings["name"])
        local_base_sha = checkpoint_fingerprint(local_base) if local_base.is_dir() else None
        jobs = [("base", 0, None)] + [(method, args.round, root / method / f"round_{args.round}" / "model")
                                      for method in selected]
        completed = []
        for method, index, checkpoint in jobs:
            name = "base" if method == "base" else f"{method}/round_{index}"
            directory = output / name
            marker = directory / "complete.json"
            if marker.exists():
                completed.append(name)
                continue
            path = directory / "evaluation.jsonl"
            if not path.is_file():
                raise ValueError(f"Generation output missing, cannot verify: {path}")
            records = read_jsonl(path)
            identity = stable_hash([settings, local_base_sha])
            from improving.pipeline import record_stage
            with record_stage(directory, "verification_and_metrics"):
                summary = verify(tasks, records, path, evaluation,
                                 expected_samples=args.samples, seed=seed)
            if set(summary.get("per_task", {})) != {task["task_id"] for task in tasks}:
                raise ValueError("Evaluator did not return the complete task universe")
            expected = [path, path.with_suffix(".verified.jsonl"), path.with_suffix(".metrics.json")]
            if any(not item.exists() for item in expected):
                raise ValueError("Evaluator must preserve verified programs and full metrics")
            files = {str(item.relative_to(directory)): _sha(item) for item in directory.rglob("*")
                     if item.is_file() and ".parts" not in item.parts
                     and not any(part.endswith(".parts") for part in item.parts)
                     and item.name != "complete.json"}
            atomic_json(marker, {"status": "completed", "protocol_fingerprint": fingerprint,
                                 "model_identity": identity, "files": files})
            completed.append(name)
            print(f"verified {name}", flush=True)
        status = {"status": "completed", "completed": completed,
                  "unavailable_checkpoints": [], "missing_checkpoints": [],
                  "training_performed": False, "output_dir": str(output)}
        atomic_json(output / "run_status.json", status)
        atomic_json(output / "transfer_complete.json", {
            "status": "completed", "benchmark": args.benchmark,
            "source_run": str(root.resolve()), "student_round": args.round,
            "task_count": len(tasks), "samples_per_task": args.samples,
            "training_on_target": False, "calibration_on_target": False,
            "generation": protocol.get("generation"), "results": status,
            "evaluation_protocol": "official_evalplus_base_and_plus" if callback else
                "recorded_function_or_stdin_adapter_with_benchmark_tests"})
        print(json.dumps(status, indent=2))
        return 0
    except (ValueError, FileNotFoundError, ImportError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
