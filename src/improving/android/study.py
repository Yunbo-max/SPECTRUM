"""One AndroidWorld study: shared RFT, UI-Voyager GRSD, feedback SPECTRUM.

Every completed stage has a receipt. Partial collection/training is kept and is
never silently retried or converted into a zero score. No GPU import for plan.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import random
import sys
import time

from .assets import atomic_json, file_sha256, resolve_checkpoint, verify_upstream

ARMS = ("ui_voyager", "feedback_spectrum")


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def validate_config(config: dict) -> None:
    study = config["study"]
    for key in ("rounds", "group_size"):
        value = study[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"study.{key} must be a positive integer")
    if study["group_size"] % 2:
        raise ValueError("group_size must be even for equal native/spectral collection")
    if study.get("spectral_fraction", 0.5) != 0.5:
        raise ValueError("The first study uses spectral_fraction=0.5")
    warmup = study.get("warmup_rounds", 3)
    if not isinstance(warmup, int) or isinstance(warmup, bool) or warmup < 0:
        raise ValueError("warmup_rounds must be a nonnegative integer")
    if not 0 <= config["spectral"].get("alpha", .5) <= 1:
        raise ValueError("spectral.alpha must lie in [0,1]")
    if config["spectral"].get("tau", 1.) < 0:
        raise ValueError("spectral.tau must be nonnegative")


def load_config(path: str | Path) -> dict:
    path = Path(path).expanduser().resolve()
    config = json.loads(path.read_text())
    root = Path(__file__).resolve().parents[3]
    for key in ("output_dir", "manifest", "assets_receipt"):
        value = Path(config[key]).expanduser()
        config[key] = str(value.resolve() if value.is_absolute() else (root / value).resolve())
    for key in ("upstream_root",):
        value = Path(config["android"][key]).expanduser()
        config["android"][key] = str(value.resolve() if value.is_absolute() else (root / value).resolve())
    if config["model"].get("checkpoint"):
        value = Path(config["model"]["checkpoint"]).expanduser()
        config["model"]["checkpoint"] = str(value.resolve() if value.is_absolute() else (root / value).resolve())
    validate_config(config)
    return config


def source_fingerprint() -> str:
    here = Path(__file__).resolve().parent
    files = sorted(here.glob("*.py")) + [here.parent / "spectral.py"]
    return digest({str(p.relative_to(here.parent)): file_sha256(p) for p in files})


def runtime_fingerprint() -> dict:
    versions = {}
    for package in ("torch", "torchvision", "transformers", "peft", "accelerate", "numpy",
                    "Pillow", "android_env", "scikit-image", "opencv-python", "opencv-python-headless"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return {"python": sys.version, "packages": versions}


def stage_config(config: dict, identity: str) -> dict:
    """Private, stable stage randomization; no extra training-seed sweep."""
    result = deepcopy(config)
    seed = int(config.get("runtime_seed", 0))
    result["runtime_seed"] = int(digest([seed, identity])[:15], 16)
    return result


def load_operators(path: Path) -> dict:
    import torch
    bundle = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(bundle, dict) or not isinstance(bundle.get("operators"), dict) or not bundle["operators"]:
        raise ValueError("Invalid saved geometry bundle")
    return bundle["operators"]


def seal_study(root: Path, config: dict, manifest: dict, source: str, inputs: dict | None = None) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    value = {"schema_version": 1, "config": config, "manifest_sha256": digest(manifest),
             "source_sha256": source, "inputs": inputs or {}}
    value["identity"] = digest(value)
    path = root / "study.json"
    if path.exists():
        if json.loads(path.read_text()).get("identity") != value["identity"]:
            raise ValueError("Study identity changed; start a new output_dir, do not overwrite prior runs")
    else:
        atomic_json(path, value)
    return value


@contextmanager
def study_lock(root: Path):
    import fcntl
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".run.lock").open("a+") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("Another process owns this Android study") from error
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def read_complete_stage(path: Path) -> dict | None:
    if not path.exists():
        return None
    receipt = path / "complete.json"
    if not receipt.is_file():
        raise RuntimeError(f"Incomplete stage preserved at {path}; inspect it before explicit recovery")
    value = json.loads(receipt.read_text())
    for name, expected in value.get("artifacts", {}).items():
        target = path / name
        if not target.is_file() or file_sha256(target) != expected:
            raise ValueError(f"Completed stage artifact changed: {target}")
    for name, expected in value.get("external_artifacts", {}).items():
        target = Path(name)
        if not target.is_file() or file_sha256(target) != expected:
            raise ValueError(f"External stage artifact changed: {target}")
    return value


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def summarize_episodes(episodes: list[dict], *, expected: int | None = None) -> dict:
    if expected is not None and len(episodes) != expected:
        raise ValueError(f"Received {len(episodes)} episodes, expected {expected}; incomplete evaluation")
    if len({row["episode_id"] for row in episodes}) != len(episodes):
        raise ValueError("Duplicate episode IDs")
    if not episodes:
        raise ValueError("No episodes to summarize")
    if any(type(row.get("success")) is not bool for row in episodes):
        raise ValueError("Episode success must be a native verifier boolean")
    steps = [step for row in episodes for step in row["steps"]]
    paths = {digest([step.get("action") for step in row["steps"]]) for row in episodes if row["success"]}
    per_instance: dict[str, list[bool]] = {}
    for row in episodes:
        per_instance.setdefault(row.get("instance_id", row["episode_id"]), []).append(row["success"])
    return {"episodes": len(episodes), "successes": sum(row["success"] for row in episodes),
            "success_rate": sum(row["success"] for row in episodes) / len(episodes),
            "instances": len(per_instance), "instances_with_success": sum(any(v) for v in per_instance.values()),
            "environment_steps": len(steps),
            "response_tokens": sum(len(s.get("response_token_ids", [])) for s in steps),
            "invalid_actions": sum(bool(s.get("action_error")) for s in steps),
            "exact_success_action_sequences": len(paths),
            "diversity_note": "Exact serialized action sequence proxy; not semantic path richness or matched-correct coverage"}


def checkpoint_files(checkpoint: str) -> list[Path]:
    root = Path(checkpoint)
    if not (root / "config.json").is_file():
        raise FileNotFoundError(f"Checkpoint config missing: {root}")
    return sorted(p.resolve() for p in root.iterdir() if p.is_file() and
                  p.suffix in {".json", ".safetensors", ".txt", ".jinja", ".model"})


def example_images(rows: list[dict]) -> list[Path]:
    result = set()
    for row in rows:
        for step in row.get("steps", [row]):
            for key in ("screenshot", "after_screenshot"):
                if isinstance(step.get(key), str):
                    result.add(Path(step[key]).expanduser().resolve())
            for message in step.get("messages", []):
                content = message.get("content", [])
                if not isinstance(content, list):
                    continue
                for block in content:
                    if block.get("type") == "image" and isinstance(block.get("image"), str):
                        result.add(Path(block["image"]).expanduser().resolve())
    return sorted(result)


def _finish(path: Path, receipt: dict, artifacts: list[str] = (), external_paths=()) -> dict:
    receipt = dict(receipt, artifacts={name: file_sha256(path / name) for name in artifacts},
                   external_artifacts={str(p): file_sha256(p) for p in sorted(set(external_paths))})
    atomic_json(path / "complete.json", receipt)
    return receipt


def _instances(manifest: dict, split: str) -> list[dict]:
    rows = [row for row in manifest["instances"] if row["split"] == split]
    if not rows:
        raise ValueError(f"No {split} instances in frozen manifest")
    return rows


def _collect(checkpoint: str, instances: list[dict], path: Path, config: dict,
             repeats: int, *, policy_name: str = "native", round_index: int = 0,
             policy=None, operators=None) -> list[dict]:
    done = read_complete_stage(path)
    if done is not None:
        if done["checkpoint"] != checkpoint or done["policy"] != policy_name or done["repeats"] != repeats:
            raise ValueError("Collection receipt identity mismatch")
        return load_jsonl(path / "records.jsonl")
    from .model import QwenPolicy
    from .environment import collect_episodes
    from contextlib import nullcontext
    own_policy = policy is None
    path.mkdir(parents=True)
    started = time.monotonic()
    settings = stage_config(config, str(path))
    settings.setdefault("collection", {})["repeats"] = repeats
    if own_policy:
        policy = QwenPolicy(checkpoint, settings)
    try:
        import torch
        torch.manual_seed(settings["runtime_seed"])
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(settings["runtime_seed"])
        if operators is not None:
            from ..spectral import folded_operators
            context = folded_operators(policy.model, operators)
        else:
            context = nullcontext()
        with context:
            episodes = collect_episodes(instances, policy.generate, path / "raw", settings,
                                        policy=policy_name, checkpoint=checkpoint, round_index=round_index)
        metrics = summarize_episodes(episodes, expected=len(instances) * repeats)
        write_jsonl(path / "records.jsonl", episodes)
        _finish(path, {"checkpoint": checkpoint, "policy": policy_name, "repeats": repeats,
                       "round": round_index, "elapsed_seconds": time.monotonic() - started,
                       "metrics": metrics}, ["records.jsonl"],
                checkpoint_files(checkpoint) + example_images(episodes))
        return episodes
    finally:
        if own_policy and policy is not None:
            policy.close()


def _train(checkpoint: str, examples: list[dict], path: Path, config: dict, kind: str) -> str:
    done = read_complete_stage(path)
    if done is not None:
        if done["input_checkpoint"] != checkpoint or done["kind"] != kind:
            raise ValueError("Training receipt identity mismatch")
        target = done["checkpoint"]
        if not (Path(target) / "config.json").exists():
            raise FileNotFoundError(f"Completed checkpoint missing: {target}")
        return target
    path.mkdir(parents=True)
    write_jsonl(path / "examples.jsonl", examples)
    if not examples:
        _finish(path, {"kind": kind, "input_checkpoint": checkpoint, "checkpoint": checkpoint,
                       "training": {"status": "no_update", "reason": "no_usable_supervision",
                                    "examples": 0, "optimizer_steps": 0}},
                ["examples.jsonl"], checkpoint_files(checkpoint))
        return checkpoint
    from .training import train_sft, train_feedback
    target = path / "checkpoint"
    function = train_feedback if kind == "feedback" else train_sft
    result = function(checkpoint, examples, str(target), stage_config(config, str(path)))
    _finish(path, {"kind": kind, "input_checkpoint": checkpoint, "checkpoint": str(target),
                   "training": result}, ["examples.jsonl"],
            checkpoint_files(checkpoint) + checkpoint_files(str(target)) + example_images(examples))
    return str(target)


def run_study(config: dict, arm: str = "both", *, warmup_only: bool = False) -> dict:
    validate_config(config)
    verify_upstream(config["android"]["upstream_root"])
    manifest = json.loads(Path(config["manifest"]).read_text())
    train_instances, eval_instances = _instances(manifest, "train"), _instances(manifest, "eval")
    initial = resolve_checkpoint(config)
    root = Path(config["output_dir"])
    from .data import success_examples, feedback_examples
    with study_lock(root):
        seal_study(root, config, manifest, source_fingerprint(),
                   inputs={"checkpoint": {str(p): file_sha256(p) for p in checkpoint_files(initial)},
                           "runtime": runtime_fingerprint()})
        config = deepcopy(config)
        config["runtime_seed"] = int(manifest["seed"])
        checkpoint = initial
        group_size = config["study"]["group_size"]
        for r in range(1, config["study"].get("warmup_rounds", 3) + 1):
            stage = root / "shared" / f"rft_{r:02d}"
            episodes = _collect(checkpoint, train_instances, stage / "collect", config, group_size, round_index=r)
            checkpoint = _train(checkpoint, success_examples(episodes), stage / "train", config, "rft")
        atomic_json(root / "shared_initialization.json", {"checkpoint": checkpoint, "initial_checkpoint": initial})
        if warmup_only:
            return {"status": "warmup_complete", "checkpoint": checkpoint}
        _collect(checkpoint, eval_instances, root / "shared" / "evaluation", config, 1)
        shared_checkpoint = checkpoint
        for method in (ARMS if arm == "both" else (arm,)):
            if method not in ARMS:
                raise ValueError(f"Unknown arm {method}")
            checkpoint = shared_checkpoint
            previous_feedback: list[dict] = []
            anchors: list[dict] = []
            if method == "feedback_spectrum":
                calibration = _collect(shared_checkpoint, _instances(manifest, "calibration"),
                                       root / "shared" / "anchor_collection", config,
                                       config["study"].get("anchor_repeats", group_size))
                anchors = success_examples(calibration, split="calibration")
                if not anchors:
                    raise RuntimeError("No native verified calibration success; spectral arm cannot fabricate its anchor")
                random.Random(stage_config(config, "fixed_anchor_order")["runtime_seed"]).shuffle(anchors)
            for r in range(1, config["study"]["rounds"] + 1):
                stage = root / method / f"round_{r:02d}"
                if method == "ui_voyager":
                    episodes = _collect(checkpoint, train_instances, stage / "collect", config, group_size, round_index=r)
                    from .baseline import build_grsd_examples
                    examples, evidence = build_grsd_examples(episodes, config["android"]["upstream_root"], config)
                    atomic_json(stage / "supervision.json", evidence)
                    checkpoint = _train(checkpoint, examples, stage / "train", config, "grsd")
                else:
                    from .model import QwenPolicy
                    from .geometry import collect_operators
                    policy = QwenPolicy(checkpoint, config)
                    try:
                        geometry = stage / "geometry"
                        completed = read_complete_stage(geometry)
                        if completed is None:
                            calibration_started = time.monotonic()
                            operators, receipt = collect_operators(policy, anchors, previous_feedback, config, geometry)
                            _finish(geometry, {"checkpoint": checkpoint, "calibration": receipt,
                                               "elapsed_seconds": time.monotonic() - calibration_started},
                                    ["operators.pt", "calibration.json"],
                                    checkpoint_files(checkpoint) + example_images(anchors) + example_images(previous_feedback))
                        else:
                            if completed["checkpoint"] != checkpoint:
                                raise ValueError("Geometry checkpoint mismatch")
                            operators = load_operators(geometry / "operators.pt")
                        native = _collect(checkpoint, train_instances, stage / "collect_native", config, group_size // 2,
                                          round_index=r, policy=policy)
                        spectral = _collect(checkpoint, train_instances, stage / "collect_spectral", config, group_size // 2,
                                            round_index=r, policy_name="spectral", policy=policy, operators=operators)
                    finally:
                        policy.close()
                    examples, evidence = feedback_examples(native + spectral, config)
                    atomic_json(stage / "supervision.json", evidence)
                    checkpoint = _train(checkpoint, examples, stage / "train", config, "feedback")
                    previous_feedback = examples
                _collect(checkpoint, eval_instances, stage / "evaluation", config, 1, round_index=r)
                atomic_json(stage / "round.json", {"arm": method, "round": r, "checkpoint": checkpoint})
        return report(config)


def report(config: dict) -> dict:
    root = Path(config["output_dir"])
    rows = []
    for path in [root / "shared" / "evaluation"] + [root / arm / f"round_{r:02d}" / "evaluation"
                                                    for arm in ARMS for r in range(1, config["study"]["rounds"] + 1)]:
        marker = path / "complete.json"
        if marker.is_file():
            value = read_complete_stage(path)
            rows.append({"stage": str(path.relative_to(root)), **value["metrics"], "checkpoint": value["checkpoint"]})
        else:
            rows.append({"stage": str(path.relative_to(root)), "status": "incomplete" if path.exists() else "not_run"})
    costs = {}
    cost_roots = {"shared": root / "shared", **{arm: root / arm for arm in ARMS},
                  "spectral_reference_acquisition": root / "shared" / "anchor_collection"}
    for category, cost_root in cost_roots.items():
        total = {"collection_episodes": 0, "environment_steps": 0, "generated_response_tokens": 0,
                 "optimizer_steps": 0, "trained_response_token_presentations": 0,
                 "teacher_prompt_token_presentations": 0, "no_update_stages": 0,
                 "collection_seconds": 0.0, "training_seconds": 0.0, "calibration_seconds": 0.0}
        for marker in cost_root.glob("**/complete.json"):
            if category == "shared" and "anchor_collection" in marker.relative_to(cost_root).parts:
                continue
            value = json.loads(marker.read_text())
            if "metrics" in value:
                total["collection_episodes"] += value["metrics"]["episodes"]
                total["environment_steps"] += value["metrics"]["environment_steps"]
                total["generated_response_tokens"] += value["metrics"]["response_tokens"]
                total["collection_seconds"] += value.get("elapsed_seconds", 0.)
            if "training" in value:
                train = value["training"]
                total["optimizer_steps"] += train.get("optimizer_steps", 0)
                total["trained_response_token_presentations"] += train.get("response_token_presentations", 0)
                total["teacher_prompt_token_presentations"] += train.get("teacher_prompt_token_presentations", 0)
                total["training_seconds"] += train.get("elapsed_seconds", 0.)
                total["no_update_stages"] += train.get("status") == "no_update"
            if "calibration" in value:
                total["calibration_seconds"] += value.get("elapsed_seconds", 0.)
        costs[category] = total
    result = {"protocol": "controlled_ui_voyager_comparison", "evaluations": rows, "costs": costs,
              "budget_note": "Refinement rollout attempts and available optimizer updates are matched. Actual actions/tokens/FLOPs are not matched. shared/anchor_collection is additional spectral-reference acquisition; it is not used by GRSD. Calibration/teacher costs must be reported separately.",
              "note": "One training trajectory per arm; no statistical claim of replicated training runs. Missing cells remain missing."}
    if root.exists():
        atomic_json(root / "report.json", result)
    return result
