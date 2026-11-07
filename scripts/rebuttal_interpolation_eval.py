#!/usr/bin/env python3
"""Post-training full-weight interpolation (evaluation only, no new LoRA/SFT).

Blends the frozen initial Qwen2.5-Coder checkpoint with a saved merged student:
theta(lambda) = theta_0 + lambda (theta_round - theta_0).
Evaluation uses the original 500 MBPP tasks and 64 draws. The method
neither modifies its source checkpoints nor tunes lambda on test outcomes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def interpolate_native_parameters(base, trained, alpha: float):
    """Parameter-wise FP32 interpolation; leaves tied weights from base tied."""
    import torch
    p0 = dict(base.named_parameters())
    p1 = dict(trained.named_parameters())
    if set(p0) != set(p1):
        raise ValueError("Training checkpoint differs from base parameter topology")
    if not p0:
        raise ValueError("Cannot interpolate empty model")
    for name, left in p0.items():
        right = p1[name]
        if left.shape != right.shape or not left.is_floating_point() or not right.is_floating_point():
            raise ValueError(f"Cannot interpolate incompatible parameter {name}")
        with torch.no_grad():
            native = left.detach().float()
            target = right.detach().to(device=left.device, dtype=torch.float32)
            native.add_(target - native, alpha=alpha)
            left.copy_(native.to(dtype=left.dtype))
    b0, b1 = dict(base.named_buffers()), dict(trained.named_buffers())
    if set(b0) != set(b1):
        raise ValueError("Training checkpoint differs from base buffer topology")
    for name, left in b0.items():
        right = b1[name]
        if left.shape != right.shape:
            raise ValueError(f"Changed nontrained buffer shape {name}")
        # Transformer geometry buffers are fixed and MUST not be smuggled from
        # another student; they should agree before mixing trainable weights.
        if not torch.equal(left.detach().cpu(), right.detach().cpu()):
            raise ValueError(f"Unexpected changed model buffer {name}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--method", required=True, choices=("plain", "spectral_soft"))
    p.add_argument("--alpha", required=True, type=float)
    p.add_argument("--round", type=int, default=5)
    p.add_argument("--samples", type=int, default=64)
    p.add_argument("--resume", action="store_true")
    args = p.parse_args(argv)
    if args.alpha not in (0.5, 0.75) or args.round != 5 or args.samples != 64:
        raise ValueError("Locked interpolation grid is alpha=0.5 or 0.75, round=5, eval@64")
    import torch
    from improving.data import read_jsonl
    from improving.modeling import load_model
    from improving.generation import generate_to_file
    from improving.pipeline import (checkpoint_fingerprint, evaluate_file,
                                   _preflight_verification, execution_runtime_identity)
    from improving.utils import atomic_json, stable_hash
    source = Path(args.run_dir).resolve()
    output = Path(args.output_dir).resolve()
    if output == source or source in output.parents or output in source.parents:
        raise ValueError("Interpolation output must not nest within or contain the training source")
    source_manifest = source / "manifest.json"
    manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
    config = manifest["config"]
    if args.method not in config["methods"] or args.round > config["rounds"]:
        raise ValueError("Requested method/round does not exist in training manifest")
    taskfile = source / "tasks" / "eval.jsonl"
    tasks = read_jsonl(taskfile)
    if (len(tasks) != 500 or len({t["task_id"] for t in tasks}) != 500
            or manifest.get("selected_task_ids", {}).get("eval") != [t["task_id"] for t in tasks]):
        raise ValueError("Missing immutable complete MBPP500 task universe")
    student = source / args.method / f"round_{args.round}" / "model"
    source_complete = source / args.method / f"round_{args.round}" / "complete.json"
    base_complete = source / "base" / "complete.json"
    if not all(p.is_file() for p in (student / "config.json", source_complete, base_complete)):
        raise FileNotFoundError("Missing original model or fully sealed student checkpoint")
    stage = json.loads(source_complete.read_text())
    if (stage.get("status") != "completed" or stage.get("checkpoint_status") == "pruned"
            or not any(n.startswith("model/") and n.endswith((".safetensors",".bin"))
                       for n in stage.get("files",{}))):
        raise ValueError("Student source is not a sealed full checkpoint")
    # Verify the original training seal before admitting current bytes as a
    # new interpolation source; a newly computed fingerprint alone is not
    # evidence that these are the weights that finished the source run.
    source_round = source_complete.parent.resolve()
    for relative, expected in stage["files"].items():
        path = (source_round / relative).resolve()
        if (not path.is_relative_to(source_round) or not path.is_file()
                or sha(path) != expected):
            raise ValueError(f"Training source failed its original completion seal: {relative}")
    model_cfg = config["model"]
    original_model = Path(model_cfg["name"])
    base_fingerprint = (checkpoint_fingerprint(original_model) if original_model.is_dir() else None)
    if manifest.get("local_base_fingerprint") and manifest["local_base_fingerprint"] != base_fingerprint:
        raise ValueError("Local initial model has changed from its training identity")
    student_fingerprint = checkpoint_fingerprint(student)
    evaluation = dict(config.get("evaluation", {}))
    evaluation.update(backend="bwrap", allow_unsafe_local=False,
                      workers=4, bootstrap_samples=2000,
                      ks=[1, 4, 8, 16, 32, 64],
                      correct_budget=4, correct_budgets=[4, 8, 16, 32, 64])
    runtime = {**execution_runtime_identity(evaluation),
               **_preflight_verification(evaluation)}
    if runtime.get("docker_image_id"):
        evaluation["docker_image"] = runtime["docker_image_id"]
    generation = {"temperature":.8, "top_p":.95, "top_k":0,
                  "max_prompt_tokens":1024, "max_new_tokens":512,
                  "samples":64, "batch_size":1,
                  "sequence_batch_size":1, "task_batch_size":1}
    protocol = {
        "purpose":"evaluation_only_full_parameter_interpolation",
        "source_run":str(source),"source_manifest_sha":sha(source_manifest),
        "source_method":args.method,"source_round":args.round,
        "alpha":args.alpha,"base_model":model_cfg,
        "base_fingerprint":base_fingerprint,
        "student_fingerprint":student_fingerprint,
        "eval_tasks_sha":sha(taskfile),"tasks":[t["task_id"] for t in tasks],
        "runtime":runtime,"generation":generation,"evaluation":evaluation,
        "training_performed":False,
    }
    fingerprint = stable_hash(protocol)
    output_manifest = output / "manifest.json"
    if output_manifest.exists():
        if not args.resume or json.loads(output_manifest.read_text()).get("fingerprint") != fingerprint:
            raise ValueError("Frozen interpolation protocol differs: use new output")
    else:
        if output.exists() and any(output.iterdir()):
            raise ValueError("Nonempty result directory without matching manifest")
        atomic_json(output_manifest, {"fingerprint":fingerprint,"protocol":protocol})
    finished = output / "interpolation_complete.json"
    if finished.exists():
        done = json.loads(finished.read_text())
        if done.get("protocol_fingerprint") != fingerprint:
            raise ValueError("Previously sealed interpolation belongs to another source")
        files = json.loads((output / "complete.json").read_text())["files"]
        if (not {"evaluation.jsonl", "evaluation.metrics.json", "evaluation.verified.jsonl"} <= set(files)
                or any(not (output/name).resolve().is_relative_to(output)
                       or not (output/name).is_file() or sha(output/name) != val
                       for name,val in files.items())):
            raise ValueError("Saved native interpolation result has failed integrity")
        print(json.dumps({"status":"already_complete","output_dir":str(output)}))
        return 0
    base, tokenizer = load_model(model_cfg)
    trained, _ = load_model(model_cfg, student)
    try:
        interpolate_native_parameters(base, trained, args.alpha)
    finally:
        del trained
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    base.eval()
    model_identity = stable_hash([fingerprint, "interpolated_native", args.alpha])
    path = output / "evaluation.jsonl"
    records = generate_to_file(base, tokenizer, tasks, path, generation, seed=config["seed"],
                               model_identity=model_identity, method=f"interp_{args.method}",
                               round_index=args.round, stage="evaluation", resume=args.resume)
    result = evaluate_file(tasks, records, path, evaluation,
                           expected_samples=64, seed=config["seed"])
    metric = output / "evaluation.metrics.json"
    verified = output / "evaluation.verified.jsonl"
    if (not metric.is_file() or not verified.is_file()
            or len(result.get("per_task", {})) != 500):
        raise RuntimeError("Interpolation finished without complete native 500-task verification")
    files = {f.name:sha(f) for f in (path, metric, verified)}
    atomic_json(output / "complete.json", {
        "status":"completed","protocol_fingerprint":fingerprint,
        "model_identity":model_identity,"files":files,
    })
    atomic_json(finished, {
        "status":"completed", "source_run":str(source),
        "source_method":args.method, "source_round":args.round,
        "alpha":args.alpha, "protocol_fingerprint":fingerprint,
        "training_performed":False, "task_count":500, "samples_per_task":64,
        "student_weights_saved_separately":False,
        "model_constructed_by_blending":True,
    })
    print(json.dumps({"status":"completed","output_dir":str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
