"""Training views over immutable AndroidWorld trajectory records.

Raw episodes remain the source of truth. These builders never repair a sampled
response or borrow an evaluation trajectory as training feedback.
"""
from __future__ import annotations

import copy
import json
from collections import Counter, defaultdict
from typing import Any, Iterable


def validate_episodes(episodes: Iterable[dict], *, split: str = "train") -> list[dict]:
    """Validate provenance before selecting any training examples.

    An unexpected split is an error, not a row silently filtered out. In
    particular a mixed train/evaluation file can never become a training set.
    """
    if split not in {"train", "calibration"}:
        raise ValueError("Training views only accept train or calibration splits")
    rows = list(episodes)
    identities: dict[str, tuple[str, str]] = {}
    seen: set[str] = set()
    for episode in rows:
        for name in ("episode_id", "instance_id", "task_name", "goal"):
            if not isinstance(episode.get(name), str) or not episode[name]:
                raise ValueError(f"Episode requires nonempty {name}")
        if episode.get("split") != split:
            raise ValueError(f"Unexpected split {episode.get('split')!r}; expected {split!r}")
        if episode.get("policy") not in {"native", "spectral"}:
            raise ValueError("Episode policy must be native or spectral")
        if not isinstance(episode.get("success"), bool):
            raise ValueError("Episode success must be a bool from the native verifier")
        if episode["episode_id"] in seen:
            raise ValueError(f"Duplicate episode_id: {episode['episode_id']}")
        seen.add(episode["episode_id"])
        identity = (episode["task_name"], episode["goal"])
        previous = identities.setdefault(episode["instance_id"], identity)
        if previous != identity:
            raise ValueError("An instance_id refers to inconsistent tasks or goals")
        if not isinstance(episode.get("steps"), list):
            raise ValueError("Episode steps must be a list")
        for position, step in enumerate(episode["steps"]):
            if step.get("index") != position:
                raise ValueError("Step indexes must be contiguous and zero based")
            if not isinstance(step.get("messages"), list) or not step["messages"]:
                raise ValueError("Step messages must contain its original prompt")
            if not isinstance(step.get("response"), str):
                raise ValueError("Step response must preserve original text")
            tokens = step.get("response_token_ids")
            if not isinstance(tokens, list) or any(type(t) is not int or t < 0 for t in tokens):
                raise ValueError("Step response_token_ids must preserve sampled nonnegative IDs")
    return rows


def step_example(episode: dict, step: dict) -> dict:
    """Copy one sampled continuation without re-tokenizing its text."""
    return {
        "messages": copy.deepcopy(step["messages"]),
        "response": step["response"],
        "response_token_ids": list(step["response_token_ids"]),
        "episode_id": episode["episode_id"],
        "instance_id": episode["instance_id"],
        "task_name": episode["task_name"],
        "step_index": step["index"],
        "policy": episode["policy"],
        "split": episode["split"],
        "checkpoint": episode.get("checkpoint"),
        "round": episode.get("round"),
    }


def success_examples(episodes: Iterable[dict], *, split: str = "train") -> list[dict]:
    """All nonempty sampled targets from native-verifier-successful episodes.

    Empty continuations contain no target token and therefore no SFT loss; their
    original records remain in the raw episode corpus. No step correctness or
    action-format filter is applied within a successful episode.
    """
    return [
        step_example(episode, step)
        for episode in validate_episodes(episodes, split=split)
        if episode["success"]
        for step in episode["steps"]
        if step["response_token_ids"]
    ]


def _error_feedback(step: dict) -> str:
    """Only typed actual action errors qualify without a successful peer."""
    error = step.get("action_error")
    if isinstance(error, str) and error.strip():
        return error.strip()
    if step.get("feedback_kind") in {"action_error", "execution_error"}:
        feedback = step.get("feedback")
        if isinstance(feedback, str) and feedback.strip():
            return feedback.strip()
    return ""


def _success_path(episode: dict) -> str:
    lines = []
    for step in episode["steps"]:
        action = step.get("action")
        rendered = json.dumps(action, ensure_ascii=False, sort_keys=True) if action is not None else step["response"]
        lines.append(f"Step {step['index']}: {rendered}")
    return "\n".join(lines)


def feedback_examples(episodes: Iterable[dict], config: dict | None = None) -> tuple[list[dict], dict]:
    """Native student prefixes with same-instance verified experience as context.

    The teacher receives an actual successful action path, not a fabricated
    explanation or purported step-level ground truth. Path context is explicitly
    bounded; student prompts and sampled continuation IDs are never truncated.
    """
    cfg = (config or {}).get("feedback", config or {})
    max_successes = int(cfg.get("max_successes", 1))
    max_chars = int(cfg.get("max_feedback_chars", 12000))
    if max_successes < 1 or max_chars < 512:
        raise ValueError("Feedback requires max_successes >= 1 and max_feedback_chars >= 512")
    rows = validate_episodes(episodes)
    successes: dict[str, list[dict]] = defaultdict(list)
    counts: Counter = Counter()
    for episode in rows:
        if episode["success"] and episode["steps"]:
            successes[episode["instance_id"]].append(episode)
    for candidates in successes.values():
        candidates.sort(key=lambda e: (len(e["steps"]), e["episode_id"]))
    examples: list[dict] = []
    for episode in rows:
        counts["input_episodes"] += 1
        if episode["policy"] != "native":
            counts["spectral_evidence_episodes"] += 1
            continue
        peers = successes.get(episode["instance_id"], [])[:max_successes]
        for step in episode["steps"]:
            counts["native_steps"] += 1
            if not step["response_token_ids"]:
                counts["skipped_empty_continuation"] += 1
                continue
            error = _error_feedback(step)
            if not peers and not error:
                counts["skipped_no_informative_feedback"] += 1
                continue
            prefix = (
                "Retrospective evidence for this same task instance. You are judging the "
                "student's original next-token choices from its actual screenshot and "
                "history. A successful path is a reference experience, not proof that its "
                "next action is valid in the student's current state.\n"
            )
            parts = [prefix]
            if error:
                parts.append("Actual action error at this step:\n" + error + "\n")
            for peer in peers:
                parts.append("Native task verifier accepted this complete attempt:\n" + _success_path(peer) + "\n")
            feedback = "\n".join(parts)
            original_chars = len(feedback)
            if original_chars > max_chars:
                feedback = feedback[: max_chars - len("\n[Evidence truncated]")] + "\n[Evidence truncated]"
                counts["truncated_feedback_examples"] += 1
                counts["feedback_chars_removed"] += original_chars - len(feedback)
            example = step_example(episode, step)
            example.update({
                "feedback": feedback,
                "feedback_episode_ids": [peer["episode_id"] for peer in peers],
                "feedback_source_policies": [peer["policy"] for peer in peers],
                "feedback_original_chars": original_chars,
                "feedback_has_action_error": bool(error),
            })
            examples.append(example)
    counts["examples"] = len(examples)
    return examples, {
        "kind": "same_instance_native_prefix_feedback",
        "counts": dict(counts),
        "max_successes": max_successes,
        "max_feedback_chars": max_chars,
        "successful_path_is_not_step_label": True,
        "teacher_target_correctness_verified": False,
    }
