"""UI-Voyager GRSD construction using the pinned author's implementation.

This adapter does not vendor or reinterpret the screenshot matching algorithm.
It calls the external MIT-licensed `cores/fork_algorithm.py` from UI-Voyager.
Our record format, controlled model/init/budget, and trainer differ from the
paper's full training setup; results must be called a controlled adaptation.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
from collections import defaultdict
from typing import Iterable

from .data import step_example, validate_episodes

UI_VOYAGER_REVISION = "67b65e2be093753ecaa2964f48739339b870813e"


def _verify_author_checkout(root: Path) -> dict:
    root = root.resolve()
    try:
        revision = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True, stderr=subprocess.PIPE
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(f"UI-Voyager must be an explicit git checkout: {root}") from exc
    if revision != UI_VOYAGER_REVISION:
        raise ValueError(f"UI-Voyager revision {revision} != pinned {UI_VOYAGER_REVISION}")
    files = ("cores/fork_algorithm.py", "cores/fork_utils.py")
    check = subprocess.run(
        ["git", "-C", str(root), "diff", "HEAD", "--exit-code", "--", *files],
        capture_output=True, text=True, check=False,
    )
    if check.returncode:
        raise ValueError("Pinned UI-Voyager fork files have local modifications")
    hashes = {}
    for name in files:
        path = root / name
        if not path.is_file():
            raise FileNotFoundError(path)
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"revision": revision, "file_sha256": hashes}


def _module_from_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import upstream module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_author_algorithm(upstream_root: str | Path):
    root = Path(upstream_root).resolve()
    receipt = _verify_author_checkout(root)
    # The author uses `from fork_utils import ...`. Isolate that temporary alias
    # from any pre-existing module with the same generic name in the process.
    previous = sys.modules.get("fork_utils")
    try:
        utilities = _module_from_path("_spectrum_ui_fork_utils", root / "cores/fork_utils.py")
        sys.modules["fork_utils"] = utilities
        algorithm = _module_from_path("_spectrum_ui_fork_algorithm", root / "cores/fork_algorithm.py")
    except ImportError as exc:
        raise ImportError("UI-Voyager GRSD requires its pinned fork code, OpenCV and scikit-image") from exc
    finally:
        if previous is None:
            sys.modules.pop("fork_utils", None)
        else:
            sys.modules["fork_utils"] = previous
    return algorithm, receipt


def _as_author_step(step: dict) -> dict:
    """Matcher sees current screenshot/current response, never an earlier reply.

    The author's matching utility selects the *first* assistant conversation.
    Passing our entire chat history would accidentally select a prior action.
    Student training context is preserved separately in the output example.
    """
    screenshot = Path(step.get("screenshot", ""))
    if not screenshot.is_file():
        raise FileNotFoundError(f"GRSD screenshot missing: {screenshot}")
    from PIL import Image
    with Image.open(screenshot) as image:
        image.verify()
    return {
        "index": step["index"],
        "images": [str(screenshot.resolve())],
        "conversations": [{"role": "assistant", "content": step["response"]}],
    }


def build_grsd_examples(
    episodes: Iterable[dict], upstream_root: str | Path, config: dict | None = None
) -> tuple[list[dict], dict]:
    """Author screenshot/action matching, then failure prompt + success target.

    Pairing never crosses task-instance parameters. `shortest_base` and
    `all_pairs` are the author's released pairing options. Original sampled
    success token IDs are substituted along with their text, rather than
    silently leaving the failed response IDs attached to the new label.
    """
    cfg = (config or {}).get("baseline", config or {})
    mode = cfg.get("grsd_pairing", "shortest_base")
    threshold = float(cfg.get("ssim_threshold", 0.95))
    if mode not in {"shortest_base", "all_pairs"} or not 0.8 <= threshold <= 1.0:
        raise ValueError("GRSD requires shortest_base/all_pairs and SSIM threshold in [0.8, 1]")
    rows = validate_episodes(episodes)
    if any(row["policy"] != "native" for row in rows):
        raise ValueError("UI-Voyager baseline requires native collection only")
    algorithm, upstream_receipt = _load_author_algorithm(upstream_root)
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[row["instance_id"]].append(row)
    examples = []
    pairs = 0
    empty_targets = 0
    mixed_instances = 0
    try:
        for instance_id, group in sorted(groups.items()):
            successful = sorted(
                (row for row in group if row["success"] and row["steps"]),
                key=lambda row: (len(row["steps"]), row["episode_id"]),
            )
            failed = [row for row in group if not row["success"] and row["steps"]]
            if not successful or not failed:
                continue
            mixed_instances += 1
            if mode == "shortest_base":
                successful = successful[:1]
            converted = {
                row["episode_id"]: [_as_author_step(step) for step in row["steps"]]
                for row in successful + failed
            }
            for success in successful:
                for failure in failed:
                    pairs += 1
                    matches, _, _ = algorithm._backward_state_match(
                        converted[success["episode_id"]], converted[failure["episode_id"]], threshold
                    )
                    for failed_index, success_index in matches:
                        teacher_step = success["steps"][success_index]
                        if not teacher_step["response_token_ids"]:
                            empty_targets += 1
                            continue
                        student_step = failure["steps"][failed_index]
                        example = step_example(failure, student_step)
                        example["response"] = teacher_step["response"]
                        example["response_token_ids"] = list(teacher_step["response_token_ids"])
                        example["target_origin"] = "grsd_successful_peer"
                        example["teacher_episode_id"] = success["episode_id"]
                        example["teacher_step_index"] = success_index
                        example["student_original_response"] = student_step["response"]
                        example["student_original_response_token_ids"] = list(student_step["response_token_ids"])
                        examples.append(example)
    finally:
        algorithm.clear_image_caches()
    return examples, {
        "kind": "ui_voyager_author_grsd_controlled_adaptation",
        "upstream": upstream_receipt,
        "pairing": mode,
        "ssim_threshold": threshold,
        "input_episodes": len(rows),
        "mixed_instances": mixed_instances,
        "pairs": pairs,
        "examples": len(examples),
        "skipped_empty_targets": empty_targets,
        "same_instance_only": True,
        "matching_function": "cores/fork_algorithm.py::_backward_state_match",
    }
