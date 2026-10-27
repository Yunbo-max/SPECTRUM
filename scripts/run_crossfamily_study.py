#!/usr/bin/env python3
"""Prepare and run the fixed three-family code study (one training trajectory).

`init`, `plan` and `status` use the standard library. Downloads, data preparation,
training and scoring run only when their explicit command is selected. Scientific
execution belongs to the user's qualified native GPU host and harness.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import sys
import tempfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
MODELS = ("qwen7b", "llama8b", "deepseek6.7b")
METHODS = ("plain", "ssd", "spectral_soft")
COUNTS = {"train": 291, "calibration": 50, "validation": 30, "eval": 500}
PROTOCOL = "spectrum-crossfamily-code-v1"


def path(value):
    result = Path(value).expanduser()
    return (result if result.is_absolute() else REPO / result).resolve()


def read(value):
    return json.loads(Path(value).read_text(encoding="utf-8"))


def sha(value):
    digest = hashlib.sha256()
    with Path(value).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode()).hexdigest()


def save(destination, value, *, immutable=False):
    destination = Path(destination)
    if destination.exists() and immutable:
        if read(destination) != value:
            raise ValueError(f"Frozen input changed: {destination}; use a new study directory")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent,
                                     prefix="." + destination.name, delete=False) as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
        temporary = stream.name
    os.replace(temporary, destination)


def assets(value):
    result = read(value)
    if result.get("protocol") != PROTOCOL or set(result.get("models", {})) != set(MODELS):
        raise ValueError("Require the three-family crossfamily asset manifest")
    if len({m["family"] for m in result["models"].values()}) != 3:
        raise ValueError("Code models must be from three different declared families")
    for model in result["models"].values():
        if not re.fullmatch(r"[0-9a-f]{40}", model.get("revision", "")):
            raise ValueError("Every model needs a full immutable revision")
    return result


def seed_values(value):
    result = read(value)
    if result.get("protocol") != PROTOCOL or any(
            type(result.get(k)) is not int or result[k] < 0 for k in ("data_seed", "training_seed")):
        raise ValueError("Use init to create the private single-trajectory seed file")
    return result


def init(args):
    target = path(args.seed_file)
    if target.exists():
        seed_values(target)
    else:
        save(target, {"protocol": PROTOCOL, "data_seed": secrets.randbits(31),
                      "training_seed": secrets.randbits(31), "trajectory_label": "r1"}, immutable=True)
        target.chmod(0o600)
    return {"private_seed_file": str(target), "trajectories": 1}


def selected_models(args):
    return list(MODELS) if args.model == "all" else [args.model]


def download(args):
    from huggingface_hub import HfApi, hf_hub_download, snapshot_download
    from huggingface_hub.constants import HF_HUB_CACHE
    mapping, root = assets(path(args.assets)), path(args.run_root)
    output = []
    for alias in selected_models(args):
        model = mapping["models"][alias]
        cache = Path(HF_HUB_CACHE)
        cache.mkdir(parents=True, exist_ok=True)
        existing = cache / ("models--" + model["repo_id"].replace("/", "--")) / "snapshots" / model["revision"]
        local_ready = existing.is_dir() and (existing / "config.json").is_file() and (
            existing / "model.safetensors.index.json").is_file()
        if local_ready:
            # Local snapshot is already populated (including staged symlinks for a
            # gated model). Skip hub metadata/network and construct the receipt
            # directly from the on-disk bytes.
            index = read(existing / "model.safetensors.index.json")
            weights = set(index["weight_map"].values())
            names = {name: None for name in weights}
            for name in sorted(existing.iterdir()):
                if name.name.endswith((".json", ".txt", ".tiktoken")) or name.name.startswith(("tokenizer", "LICENSE", "NOTICE", "README")):
                    names[name.name] = None
            required = set(names)
            if not {"config.json"} <= required:
                raise ValueError(f"{alias}: incomplete local snapshot")
            snapshot = existing
        else:
            info = HfApi().model_info(model["repo_id"], revision=model["revision"], files_metadata=True)
            if info.sha != model["revision"]:
                raise ValueError(f"{alias}: upstream resolved a different model revision")
            names = {entry.rfilename: entry for entry in info.siblings}
            index_name = "model.safetensors.index.json"
            if index_name in names:
                index = read(hf_hub_download(model["repo_id"], index_name, revision=model["revision"]))
                weights = set(index["weight_map"].values())
            elif "model.safetensors" in names:
                weights = {"model.safetensors"}
            else:
                raise ValueError(f"{alias}: expected native safetensors weights")
            # Preserve all root-level tokenizer/config/processor assets and every indexed
            # weight shard. Do not also fetch alternative original PyTorch weight copies.
            sidecars = {name for name in names if "/" not in name and (
                name.endswith((".json", ".model", ".tiktoken", ".txt", ".jinja")) or
                name.startswith(("tokenizer", "LICENSE", "NOTICE", "README")))}
            required = weights | sidecars
            if not required <= names.keys() or "config.json" not in required:
                raise ValueError(f"{alias}: incomplete published model index/config")
            # Existing cache bytes can be reused. Require capacity for missing files,
            # rather than assuming a model-size or host-disk allowance.
            missing_bytes = sum(names[name].size or 0 for name in required if not (existing / name).is_file())
            if shutil.disk_usage(cache).free < missing_bytes + 1024**3:
                raise RuntimeError(f"{alias}: insufficient cache disk for missing files plus 1 GiB margin")
            snapshot = Path(snapshot_download(model["repo_id"], revision=model["revision"],
                                              allow_patterns=sorted(required)))
        files = {}
        for name in sorted(required):
            local = snapshot / name
            if not local.is_file() or local.stat().st_size <= 0:
                raise ValueError(f"{alias}: missing/empty model file {name}")
            with local.open("rb") as stream:
                prefix = stream.read(128)
            if prefix.startswith(b"version https://git-lfs") or prefix.lower().startswith(b"<!doctype html"):
                raise ValueError(f"{alias}: model file is a pointer/error document: {name}")
            expected = names.get(name)
            actual = sha(local)
            if expected is not None and getattr(expected, "size", None) is not None and local.stat().st_size != expected.size:
                raise ValueError(f"{alias}: size mismatch for {name}")
            lfs = getattr(expected, "lfs", None) if expected is not None else None
            upstream_sha = (lfs.get("sha256") if isinstance(lfs, dict) else getattr(lfs, "sha256", None))
            if upstream_sha is not None and upstream_sha != actual:
                raise ValueError(f"{alias}: LFS checksum mismatch for {name}")
            files[name] = {"sha256": actual, "bytes": local.stat().st_size,
                           "upstream_lfs_sha256": upstream_sha}
        receipt = {"protocol": PROTOCOL, "repo_id": model["repo_id"],
                   "revision": model["revision"], "snapshot": str(snapshot.resolve()), "files": files}
        save(root / "assets" / f"{alias}.json", receipt, immutable=True)
        output.append({"model": alias, "files": len(files),
                       "bytes": sum(x["bytes"] for x in files.values()), "verified": True})
    return {"downloads": output}


def prepare(args):
    from improving.benchmarks import prepare_benchmark
    mapping, data, seeds = assets(path(args.assets)), path(args.data_root), seed_values(path(args.seed_file))
    save(data / "assets.lock.json", mapping, immutable=True)
    entries = {}
    for name in ("mbpp", "humanevalplus"):
        spec = mapping["datasets"][name]
        folder = data / name
        exclusions = [] if name == "mbpp" else [data / "mbpp" / f"{split}.jsonl"
                    for split in ("train", "calibration", "validation")]
        manifest = prepare_benchmark(name, folder, revision=spec["revision"],
            seed=seeds["data_seed"], calibration_size=50, validation_size=30,
            exclusions_from=exclusions, expected_count=500 if name == "mbpp" else 164,
            expected_split_counts=COUNTS if name == "mbpp" else None)
        if name == "humanevalplus":
            # Carry the exact native fixture into the offline sandbox. Prepared
            # prompts alone do not contain the official extended test inputs.
            from evalplus.data.utils import get_dataset_metadata
            _, fixture = get_dataset_metadata("HumanEvalPlus", spec["revision"], False, False)
            expected = read(folder / "dataset_metadata.json")["datasets"]["HumanEvalPlus"]["sha256"]
            if sha(fixture) != expected:
                raise ValueError("Official HumanEval+ fixture differs from prepared metadata")
            target = folder / "HumanEvalPlus.jsonl"
            if target.exists() and sha(target) != expected:
                raise ValueError("Frozen HumanEval+ fixture changed")
            if not target.exists():
                shutil.copyfile(fixture, target)
        entries[name] = {"manifest": str(folder / "manifest.json"),
                         "manifest_sha256": sha(folder / "manifest.json"),
                         "output_files": manifest["output_files"]}
        if name == "humanevalplus":
            entries[name]["native_fixture"] = {"path": str(target), "sha256": expected}
    receipt = {"protocol": PROTOCOL, "assets_sha256": digest(mapping),
               "seed_file_sha256": sha(path(args.seed_file)), "datasets": entries}
    save(data / "prepared.json", receipt, immutable=True)
    return {"prepared": str(data / "prepared.json"), "mbpp": COUNTS, "humanevalplus": 164}


def sources():
    files = list((REPO / "src/improving").glob("*.py")) + [Path(__file__)]
    return {str(f.relative_to(REPO)): sha(f) for f in sorted(files)}


def snapshot_prepared(data):
    receipt = read(data / "prepared.json")
    if (receipt.get("protocol") != PROTOCOL
            or set(receipt.get("datasets", {})) != {"mbpp", "humanevalplus"}):
        raise ValueError("Run prepare before plan")
    result = {str(data / "prepared.json"): sha(data / "prepared.json")}
    for name, entry in receipt["datasets"].items():
        if name == "humanevalplus" and "native_fixture" not in entry:
            raise ValueError("Missing official HumanEval+ native fixture receipt")
        manifest_path = data / name / "manifest.json"
        if sha(manifest_path) != entry["manifest_sha256"]:
            raise ValueError(f"Prepared manifest changed: {name}")
        native_manifest = read(manifest_path)
        if native_manifest.get("name") != name or native_manifest.get("output_files") != entry["output_files"]:
            raise ValueError(f"Prepared manifest does not match its receipt: {name}")
        expected_counts = COUNTS if name == "mbpp" else {"eval": 164}
        for split, count in expected_counts.items():
            filename = f"{split}.jsonl"
            if entry["output_files"].get(filename, {}).get("count") != count:
                raise ValueError(f"Incorrect fixed population: {name}/{split}")
            rows = [json.loads(line) for line in (data / name / filename).read_text().splitlines() if line.strip()]
            if len(rows) != count or len({row["task_id"] for row in rows}) != count:
                raise ValueError(f"Incorrect actual population or duplicate IDs: {name}/{split}")
        result[str(manifest_path)] = sha(manifest_path)
        if "native_fixture" in entry:
            fixture = entry["native_fixture"]
            if sha(fixture["path"]) != fixture["sha256"]:
                raise ValueError("Official HumanEval+ fixture changed")
            result[fixture["path"]] = fixture["sha256"]
        for filename, expected in entry["output_files"].items():
            value = data / name / filename
            if sha(value) != expected["sha256"]:
                raise ValueError(f"Prepared input changed: {value}")
            result[str(value)] = expected["sha256"]
    return receipt, result


def plan(args):
    mapping, protocol = assets(path(args.assets)), read(path(args.protocol))
    if (protocol.get("protocol") != PROTOCOL or protocol.get("models") != list(MODELS)
            or protocol.get("methods") != list(METHODS)
            or protocol.get("independent_training_trajectories") != 1
            or protocol.get("temperature_sweep") is not False):
        raise ValueError("Require the fixed three-family, one-trajectory protocol")
    if protocol["evaluation"]["backend"] not in ("bwrap", "local"):
        raise ValueError("Require the bwrap or explicitly enabled local evaluation backend")
    if protocol["evaluation"]["backend"] == "local" and not protocol["evaluation"].get("allow_unsafe_local"):
        raise ValueError("Local evaluation requires allow_unsafe_local=true")
    data, root = path(args.data_root), path(args.run_root)
    seeds = seed_values(path(args.seed_file))
    prepared, input_files = snapshot_prepared(data)
    if prepared["assets_sha256"] != digest(mapping) or prepared["seed_file_sha256"] != sha(path(args.seed_file)):
        raise ValueError("Prepared data and requested assets/randomization differ")
    configs = {}
    for alias in MODELS:
        model = mapping["models"][alias]
        config = {"label": f"crossfamily-{alias}-r1", "seed": seeds["training_seed"],
            "data_seed": seeds["data_seed"], "model": {"name": model["repo_id"],
                "revision": model["revision"], "device": "auto", "dtype": "bfloat16",
                "attn_implementation": "sdpa", "local_files_only": True},
            "data": {split: str(data / "mbpp" / f"{split}.jsonl") for split in COUNTS},
            "data_limits": {}, "output_dir": str(root / "jobs" / alias),
            **{key: protocol[key] for key in ("methods", "rounds", "checkpoint_retention",
                "generation", "train", "evaluation", "diagnostics")},
            "calibration": {**protocol["calibration"], "layers": model["layers"]}}
        destination = root / "plan" / "configs" / f"{alias}.json"
        save(destination, config, immutable=True)
        configs[alias] = {"path": str(destination), "sha256": sha(destination),
                          "output_dir": config["output_dir"]}
    manifest = {"protocol": PROTOCOL, "source_status": "generated_unexecuted",
        "run_root": str(root), "data_root": str(data), "assets": mapping,
        "settings": protocol, "input_files": input_files, "source_files": sources(),
        "config_files": configs, "seed_file": str(path(args.seed_file)),
        "seed_file_sha256": sha(path(args.seed_file)), "training_trajectories_per_model": 1,
        "jobs": [{"model": alias, "stages": ["train", "transfer"], "replicate": "r1"} for alias in MODELS]}
    save(root / "plan" / "manifest.json", manifest, immutable=True)
    return {"manifest": str(root / "plan" / "manifest.json"), "models": list(MODELS),
            "training_arms": 9, "arm_rounds": 45, "transfer_model_conditions": 12,
            "temperature_sweep": False, "training_trajectories_per_model": 1}


def load_plan(args):
    manifest = read(path(args.run_root) / "plan" / "manifest.json")
    if manifest.get("protocol") != PROTOCOL or manifest["source_files"] != sources():
        raise ValueError("Frozen source differs; preserve this run and create a new plan/root")
    for filename, expected in manifest["input_files"].items():
        if sha(filename) != expected:
            raise ValueError(f"Prepared input changed: {filename}")
    if sha(manifest["seed_file"]) != manifest["seed_file_sha256"]:
        raise ValueError("Private randomization file changed")
    for entry in manifest["config_files"].values():
        if sha(entry["path"]) != entry["sha256"]:
            raise ValueError("Frozen job configuration changed")
    return manifest


@contextmanager
def lock(root, alias):
    file = root / "locks" / f"{alias}.lock"
    file.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = os.open(file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise RuntimeError(f"Job ownership lock exists: {file}; reconcile the live process before recovery") from error
    try:
        with os.fdopen(handle, "w") as stream:
            json.dump({"pid": os.getpid(), "model": alias}, stream)
        yield
    finally:
        file.unlink(missing_ok=True)


def verify_model(manifest, alias):
    receipt = read(Path(manifest["run_root"]) / "assets" / f"{alias}.json")
    expected = manifest["assets"]["models"][alias]
    if any(receipt[key] != expected[key] for key in ("repo_id", "revision")):
        raise ValueError(f"{alias}: model receipt identity differs")
    for filename, value in receipt["files"].items():
        if sha(Path(receipt["snapshot"]) / filename) != value["sha256"]:
            raise ValueError(f"{alias}: downloaded model bytes changed")


def transfer(manifest, alias):
    from improving.benchmarks import make_humanevalplus_evaluator
    from improving.longitudinal import evaluate_checkpoints, export_longitudinal
    from improving.data import read_jsonl, assert_disjoint_splits
    root, data = Path(manifest["run_root"]), Path(manifest["data_root"])
    source = root / "jobs" / alias
    settings = manifest["settings"]["transfer"]
    tasks = data / "humanevalplus" / "eval.jsonl"
    assert_disjoint_splits({**{key: read_jsonl(source / "tasks" / f"{key}.jsonl")
        for key in ("train", "calibration", "validation")}, "eval": read_jsonl(tasks)})
    backend = manifest["settings"]["evaluation"].get("backend", "local")
    allow_unsafe = manifest["settings"]["evaluation"].get("allow_unsafe_local", True)
    callback, identity = make_humanevalplus_evaluator(tasks, settings={"backend": backend,
        "allow_unsafe_local": allow_unsafe, "parallel": settings["parallel"],
        "prepared_dataset_dir": str(tasks.parent)})
    output = root / "transfer" / alias
    result = evaluate_checkpoints(source, output, samples=settings["samples"],
        rounds=[settings["round"]], methods=list(METHODS), eval_tasks_path=tasks,
        generation_overrides={"max_prompt_tokens": settings["max_prompt_tokens"],
            "max_new_tokens": settings["max_new_tokens"], "batch_size": settings["sequence_batch_size"],
            "sequence_batch_size": settings["sequence_batch_size"], "task_batch_size": 1},
        evaluation_overrides={"backend": backend, "allow_unsafe_local": allow_unsafe},
        bootstrap_samples=settings["bootstrap_samples"],
        resume=True, evaluator=callback, evaluator_identity=identity)
    if result.get("status") != "completed":
        raise RuntimeError(f"HumanEval+ incomplete; see {output}")
    export_longitudinal(output, bootstrap_samples=settings["bootstrap_samples"])
    save(output / "transfer_complete.json", {"status": "completed", "benchmark": "humanevalplus",
        "evaluation_protocol": "official_evalplus_base_and_plus", "task_count": 164,
        "samples_per_task": settings["samples"], "student_round": settings["round"],
        "training_on_target": False, "result": result})
    return result


def run(args):
    from improving.pipeline import run_experiment
    from improving.longitudinal import export_longitudinal
    manifest = load_plan(args)
    root = Path(manifest["run_root"])
    os.environ["HF_HUB_OFFLINE"] = "1"
    results = []
    for alias in selected_models(args):
        with lock(root, alias):
            verify_model(manifest, alias)
            if args.stage in ("train", "all"):
                config = read(manifest["config_files"][alias]["path"])
                result = run_experiment(config, resume=True)
                export_longitudinal(config["output_dir"], bootstrap_samples=2000)
                results.append({"model": alias, "stage": "train", "result": result})
            if args.stage in ("transfer", "all"):
                results.append({"model": alias, "stage": "transfer", "result": transfer(manifest, alias)})
    return {"results": results}


def status(args):
    root = path(args.run_root)
    manifest = read(root / "plan" / "manifest.json")
    rows = []
    for alias in MODELS:
        source = root / "jobs" / alias
        completed = {method: [number for number in range(1, manifest["settings"]["rounds"] + 1)
            if (source / method / f"round_{number}" / "complete.json").is_file()] for method in METHODS}
        rows.append({"model": alias, "base_marker": (source / "base/complete.json").is_file(),
            "round_markers": completed,
            "transfer_marker": (root / "transfer" / alias / "transfer_complete.json").is_file(),
            "lock_present": (root / "locks" / f"{alias}.lock").is_file()})
    return {"status_basis": "stored markers only; not live process state or integrity verification", "models": rows}


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--assets", default="configs/crossfamily/assets.json")
    common.add_argument("--protocol", default="configs/crossfamily/protocol.json")
    common.add_argument("--data-root", default="data/crossfamily")
    common.add_argument("--run-root", default="runs/crossfamily_code_v1")
    common.add_argument("--seed-file", default="runs/private/crossfamily_code_v1.json")
    sub = result.add_subparsers(dest="command", required=True)
    for name in ("init", "download", "prepare", "plan", "run", "status"):
        current = sub.add_parser(name, parents=[common])
        if name in ("download", "run"):
            current.add_argument("--model", choices=(*MODELS, "all"), default="all")
        if name == "run":
            current.add_argument("--stage", choices=("train", "transfer", "all"), default="all")
    return result


def main():
    args = parser().parse_args()
    os.chdir(REPO)
    try:
        result = globals()[args.command](args)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, RuntimeError, FileNotFoundError, ImportError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
