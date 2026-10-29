"""Small deterministic data-contract tests; no model or emulator is used."""
import copy
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from PIL import Image

from improving.android.data import feedback_examples, success_examples, validate_episodes
from improving.android.baseline import (
    UI_VOYAGER_REVISION, _as_author_step, _verify_author_checkout, build_grsd_examples,
)


def episode(identifier="e1", instance="i1", success=False, policy="native", split="train"):
    return {
        "episode_id": identifier, "instance_id": instance, "task_name": "Task",
        "goal": "Find contact", "split": split, "policy": policy, "success": success,
        "checkpoint": "checkpoint-0", "round": 0,
        "steps": [{"index": 0, "messages": [{"role": "user", "content": [
            {"type": "text", "text": "Find contact"},
            {"type": "image", "image": "/raw/screen.png"},
        ]}], "response": "original", "response_token_ids": [8, 3, 9],
            "screenshot": "/raw/screen.png", "action": {"action_type": "click", "x": 12},
            "feedback": "failure", "action_error": None}],
    }


def test_success_keeps_sampled_ids_and_does_not_mutate_raw():
    raw = episode(success=True)
    examples = success_examples([raw])
    assert examples[0]["response_token_ids"] == [8, 3, 9]
    examples[0]["response_token_ids"].append(7)
    examples[0]["messages"][0]["content"][0]["text"] = "changed"
    assert raw["steps"][0]["response_token_ids"] == [8, 3, 9]
    assert raw["steps"][0]["messages"][0]["content"][0]["text"] == "Find contact"


def test_success_retains_malformed_steps_inside_verified_success():
    raw = episode(success=True)
    raw["steps"][0]["action"] = None
    raw["steps"][0]["action_error"] = "Invalid JSON"
    assert len(success_examples([raw])) == 1


def test_calibration_requires_explicit_split():
    raw = episode(success=True, split="calibration")
    with pytest.raises(ValueError, match="Unexpected split"):
        success_examples([raw])
    assert success_examples([raw], split="calibration")[0]["split"] == "calibration"


@pytest.mark.parametrize("builder", [success_examples, feedback_examples])
def test_evaluation_cannot_enter_training_views(builder):
    with pytest.raises(ValueError, match="Unexpected split"):
        builder([episode(), episode("eval", success=True, split="eval")])


def test_feedback_cannot_borrow_success_from_different_instance():
    native = episode()
    other = episode("other", "i2", success=True, policy="spectral")
    examples, receipt = feedback_examples([native, other])
    assert examples == []
    assert receipt["counts"]["skipped_no_informative_feedback"] == 1


def test_feedback_spectral_success_is_evidence_never_student():
    native = episode()
    source = episode("spectral", success=True, policy="spectral")
    source["steps"][0]["response_token_ids"] = [99, 99]
    examples, receipt = feedback_examples([native, source])
    assert len(examples) == 1
    assert examples[0]["policy"] == "native"
    assert examples[0]["response_token_ids"] == [8, 3, 9]
    assert examples[0]["feedback_episode_ids"] == ["spectral"]
    assert "not proof" in examples[0]["feedback"]
    assert receipt["teacher_target_correctness_verified"] is False


def test_success_feedback_preserves_model_action_schema_and_coordinates():
    from improving.android.prompting import parse_mobile_action
    native = episode()
    source = episode("spectral", success=True, policy="spectral")
    response = '<tool_call>{"name":"mobile_use","arguments":{"action":"click","coordinate":[999,999]}}</tool_call>'
    source["steps"][0]["response"] = response
    source["steps"][0]["action"] = parse_mobile_action(response, 1080, 2400)
    assert source["steps"][0]["action"] == {"action_type": "click", "x": 1079, "y": 2399}
    examples, _ = feedback_examples([native, source])
    evidence = examples[0]["feedback"]
    assert response in evidence
    assert "original model response" in evidence.lower()
    assert "1079" not in evidence and "2399" not in evidence
    assert '"action_type"' not in evidence


def test_binary_failure_is_not_rich_feedback_but_actual_error_is():
    native = episode()
    assert feedback_examples([native])[0] == []
    native["steps"][0]["action_error"] = "The tool call could not be parsed as JSON"
    examples, _ = feedback_examples([native])
    assert len(examples) == 1
    assert "could not be parsed" in examples[0]["feedback"]
    assert examples[0]["feedback_episode_ids"] == []


def test_feedback_bounds_only_teacher_context_and_reports_truncation():
    native = episode()
    source = episode("source", success=True, policy="spectral")
    source["steps"][0]["action"] = {"text": "x" * 2000}
    source["steps"][0]["response"] = "x" * 2000
    examples, receipt = feedback_examples([native, source], {"max_feedback_chars": 512})
    assert len(examples[0]["feedback"]) <= 512
    assert examples[0]["feedback"].endswith("[Evidence truncated]")
    assert examples[0]["response_token_ids"] == native["steps"][0]["response_token_ids"]
    assert receipt["counts"]["truncated_feedback_examples"] == 1


def test_empty_sample_is_audited_without_inventing_tokens():
    raw = episode()
    raw["steps"][0]["response_token_ids"] = []
    examples, receipt = feedback_examples([raw])
    assert examples == []
    assert receipt["counts"]["skipped_empty_continuation"] == 1
    assert raw["steps"][0]["response_token_ids"] == []


def test_colliding_identity_and_duplicate_episode_rejected():
    first = episode()
    with pytest.raises(ValueError, match="Duplicate episode_id"):
        validate_episodes([first, copy.deepcopy(first)])
    second = episode("e2")
    second["goal"] = "Delete a contact"
    with pytest.raises(ValueError, match="inconsistent"):
        validate_episodes([first, second])


def _save_screen(path):
    Image.new("RGB", (64, 128), color=(90, 60, 30)).save(path)


def test_author_conversion_uses_current_response_not_prior_assistant(tmp_path):
    raw = episode()
    step = raw["steps"][0]
    path = tmp_path / "s.png"
    _save_screen(path)
    step["screenshot"] = str(path)
    step["messages"].insert(0, {"role": "assistant", "content": "old action"})
    converted = _as_author_step(step)
    assert converted["conversations"] == [{"role": "assistant", "content": "original"}]


def test_grsd_uses_failure_prompt_and_success_ids_with_provenance(tmp_path):
    native = episode()
    source = episode("success", success=True)
    path = tmp_path / "s.png"
    _save_screen(path)
    for row in (native, source):
        row["steps"][0]["screenshot"] = str(path)
    source["steps"][0]["response"] = "corrected"
    source["steps"][0]["response_token_ids"] = [42, 5]
    source["steps"][0]["messages"][0]["content"][0]["text"] = "successful history"
    calls = []
    module = SimpleNamespace(
        _backward_state_match=lambda a, b, threshold: (calls.append((a, b, threshold)) or [(0, 0)], {}, {}),
        clear_image_caches=lambda: None,
    )
    with patch("improving.android.baseline._load_author_algorithm", return_value=(module, {"revision": UI_VOYAGER_REVISION})):
        examples, receipt = build_grsd_examples([native, source], tmp_path)
    assert len(calls) == 1
    assert examples[0]["messages"] == native["steps"][0]["messages"]
    assert examples[0]["response"] == "corrected"
    assert examples[0]["response_token_ids"] == [42, 5]
    assert examples[0]["student_original_response_token_ids"] == [8, 3, 9]
    assert examples[0]["teacher_episode_id"] == "success"
    assert receipt["same_instance_only"] is True
    assert native["steps"][0]["response"] == "original"


def test_grsd_rejects_spectral_baseline_data(tmp_path):
    with pytest.raises(ValueError, match="native collection"):
        build_grsd_examples([episode(policy="spectral")], tmp_path)


def test_grsd_missing_image_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        _as_author_step(episode()["steps"][0])


def test_upstream_revision_pin_is_enforced(tmp_path):
    with patch("improving.android.baseline.subprocess.check_output", return_value="wrong\n"):
        with pytest.raises(ValueError, match="pinned"):
            _verify_author_checkout(tmp_path)


def test_real_pinned_author_matcher(tmp_path):
    root = os.environ.get("SPECTRUM_UI_VOYAGER_ROOT")
    if not root:
        pytest.skip("Set SPECTRUM_UI_VOYAGER_ROOT for pinned upstream integration")
    native = episode()
    source = episode("success", success=True)
    path = tmp_path / "same-screen.png"
    _save_screen(path)
    for row in (native, source):
        row["steps"][0]["screenshot"] = str(path)
    native["steps"][0]["response"] = '<tool_call>{"name":"mobile_use","arguments":{"action":"wait","time":1}}</tool_call>'
    source["steps"][0]["response"] = '<tool_call>{"name":"mobile_use","arguments":{"action":"click","coordinate":[1,2]}}</tool_call>'
    source["steps"][0]["response_token_ids"] = [31, 32]
    examples, receipt = build_grsd_examples([native, source], root)
    assert len(examples) == 1
    assert examples[0]["response_token_ids"] == [31, 32]
    assert receipt["upstream"]["revision"] == UI_VOYAGER_REVISION
