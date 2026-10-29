"""Acquire and pin public source/model assets without starting an emulator."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

UI_URL = "https://github.com/ui-voyager/UI-Voyager.git"
UI_REVISION = "67b65e2be093753ecaa2964f48739339b870813e"
MODEL_ID = "Qwen/Qwen3-VL-4B-Instruct"
MODEL_REVISION = "ebb281ec70b05090aa6165b016eac8ec08e71b17"


def atomic_json(path: str | Path, value) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_upstream(path: str | Path) -> dict:
    path = Path(path).resolve()
    head = subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    if head != UI_REVISION:
        raise ValueError(f"UI-Voyager checkout must be {UI_REVISION}, found {head}")
    dirty = subprocess.check_output(["git", "-C", str(path), "status", "--porcelain", "--untracked-files=no"], text=True)
    if dirty:
        raise ValueError("Pinned UI-Voyager source has tracked modifications; use a clean checkout")
    required = ["cores/fork_algorithm.py", "cores/fork_utils.py", "androidworld/android_world/registry.py"]
    return {"path": str(path), "revision": head,
            "files": {name: file_sha256(path / name) for name in required}}


def acquire(config: dict, *, source_only: bool = False) -> dict:
    upstream = Path(config["android"]["upstream_root"]).expanduser().resolve()
    if not upstream.exists():
        upstream.parent.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, GIT_LFS_SKIP_SMUDGE="1")
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", UI_URL, str(upstream)], check=True, env=env)
        subprocess.run(["git", "-C", str(upstream), "checkout", "--detach", UI_REVISION], check=True, env=env)
    receipt = {"upstream": verify_upstream(upstream)}
    if source_only:
        return receipt
    from huggingface_hub import snapshot_download
    model = config["model"]
    repo_id, revision = model.get("repo_id", MODEL_ID), model.get("revision", MODEL_REVISION)
    if repo_id != MODEL_ID or revision != MODEL_REVISION:
        raise ValueError("This first experiment pins Qwen3-VL-4B-Instruct; qualify another model separately")
    checkpoint = Path(snapshot_download(repo_id=repo_id, revision=revision,
                                       allow_patterns=["*.json", "*.safetensors", "*.txt", "*.jinja", "*.model"]))
    files = sorted(p for p in checkpoint.iterdir() if p.is_file())
    if not any(p.suffix == ".safetensors" for p in files):
        raise RuntimeError("Model download has no safetensors weights")
    index_path = checkpoint / "model.safetensors.index.json"
    if index_path.exists():
        index = json.loads(index_path.read_text())
        missing = set(index["weight_map"].values()) - {p.name for p in files}
        if missing:
            raise RuntimeError(f"Incomplete model shards: {sorted(missing)}")
    receipt["model"] = {"repo_id": repo_id, "revision": revision, "checkpoint": str(checkpoint),
                        "files": {p.name: {"bytes": p.stat().st_size, "sha256": file_sha256(p)} for p in files}}
    destination = Path(config["assets_receipt"])
    if destination.exists() and json.loads(destination.read_text()) != receipt:
        raise ValueError("Existing asset receipt differs; preserve it and use a new study root")
    atomic_json(destination, receipt)
    return receipt


def resolve_checkpoint(config: dict) -> str:
    explicit = config["model"].get("checkpoint")
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not (path / "config.json").is_file():
            raise FileNotFoundError(f"No local checkpoint at {path}")
        return str(path)
    receipt = json.loads(Path(config["assets_receipt"]).read_text())
    path = Path(receipt["model"]["checkpoint"])
    if receipt["model"]["revision"] != MODEL_REVISION:
        raise ValueError("Model acquisition receipt has an unexpected revision")
    for name, item in receipt["model"]["files"].items():
        target = path / name
        if not target.is_file() or target.stat().st_size != item["bytes"]:
            raise ValueError(f"Model asset missing or changed size: {name}")
        if file_sha256(target) != item["sha256"]:
            raise ValueError(f"Model asset hash differs from acquisition receipt: {name}")
    return str(path)
