#!/usr/bin/env python3
"""Native 64-draw decoder-only ablation on frozen LoRA-merged students."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
POLICIES = {
    "cool": {"temperature": 0.6, "top_p": 0.95, "top_k": 0},
    "warm": {"temperature": 1.0, "top_p": 0.95, "top_k": 0},
    "ssd_recipe": {"temperature": 1.5, "top_p": 0.8, "top_k": 20},
}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--round", type=int, default=5)
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--decoder", required=True, choices=POLICIES)
    parser.add_argument("--methods", help="Selected comma-separated source model arms")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    if args.round < 1 or args.samples != 64:
        raise ValueError("Frozen decoder ablation uses round >=1 and exactly 64 eval samples")
    from improving.longitudinal import evaluate_checkpoints
    from improving.data import read_jsonl
    from improving.utils import atomic_json

    source = Path(args.run_dir).resolve()
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    source_config = manifest["config"]
    methods = (args.methods.split(",") if args.methods else source_config["methods"])
    if not methods or not set(methods).issubset(source_config["methods"]):
        raise ValueError("Methods must be nonempty and present in the original run")
    if len(read_jsonl(source / "tasks/eval.jsonl")) != 500:
        raise ValueError("Decoder control requires the original 500 MBPP tasks")
    for name in methods:
        if not (source / name / f"round_{args.round}" / "model/config.json").is_file():
            raise FileNotFoundError(f"Source model missing: {name} round {args.round}")
    overrides = {
        **POLICIES[args.decoder], "max_new_tokens": 512,
        "max_prompt_tokens": 1024, "batch_size": 1,
        "task_batch_size": 1, "sequence_batch_size": 1,
    }
    result = evaluate_checkpoints(
        source, args.output_dir, samples=64, rounds=[args.round],
        methods=methods,
        evaluation_overrides={"backend": "docker", "allow_unsafe_local": False},
        generation_overrides=overrides,
        bootstrap_samples=2000, resume=args.resume,
    )
    if result.get("status") != "completed":
        raise RuntimeError(f"Native decoder evaluation incomplete: {result}")
    expected = {"base"} | {f"{name}/round_{args.round}" for name in methods}
    if set(result["completed"]) != expected:
        raise RuntimeError("Missing native student evaluation or base evaluation")
    atomic_json(Path(args.output_dir) / "decoder_complete.json", {
        "status": "completed", "decoder": args.decoder,
        "training_decoder_unchanged": True,
        "student_training_performed": False,
        "source_run": str(source),
        "source_methods": methods,
        "round": args.round,
        "samples_per_task": 64,
        "eval_tasks": 500,
        "decoder": POLICIES[args.decoder],
        "results": result,
    })
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
