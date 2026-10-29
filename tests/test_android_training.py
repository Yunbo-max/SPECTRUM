"""CPU contracts for Android visual token alignment and feedback gradients."""
from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest
import torch
import torch.nn.functional as F
from PIL import Image

from improving.android.model import QwenPolicy, add_feedback, configure_image_limits
from improving.android.training import (
    language_lora_targets, response_cross_entropy, response_forward,
    response_logits, token_kl, validate_training_examples,
)


def test_teacher_feedback_preserves_student_prompt():
    original = [{"role": "user", "content": [{"type": "image", "image": "screen.png"},
                                             {"type": "text", "text": "Open notes"}]}]
    before = deepcopy(original)
    teacher = add_feedback(original, "Verified result: task incomplete")
    assert original == before
    assert teacher[0]["content"][:2] == original[0]["content"]
    assert "task incomplete" in teacher[0]["content"][-1]["text"]
    assert "CURRENT screenshot" in teacher[0]["content"][-1]["text"]


def test_full_logit_alignment_handles_different_teacher_prompt_lengths():
    student = torch.arange(1 * 7 * 3).reshape(1, 7, 3)
    teacher = torch.arange(1 * 11 * 3).reshape(1, 11, 3)
    assert torch.equal(response_logits(student, 4, 3), student[:, 3:6])
    assert torch.equal(response_logits(teacher, 8, 3), teacher[:, 7:10])
    with pytest.raises(ValueError):
        response_logits(student, 6, 4)


def test_exact_kl_matches_reference_and_detaches_teacher():
    torch.manual_seed(1)
    student = torch.randn(1, 7, 9, requires_grad=True)
    teacher = torch.randn(1, 7, 9, requires_grad=True)
    actual = token_kl(student, teacher, chunk_size=2)
    lp = F.log_softmax(student, -1)
    lq = F.log_softmax(teacher.detach(), -1)
    reference = (lp.exp() * (lp - lq)).sum(-1).mean()
    torch.testing.assert_close(actual, reference)
    actual.backward()
    assert student.grad is not None and torch.isfinite(student.grad).all()
    assert teacher.grad is None


def test_sparse_kl_is_coarse_grained_and_finite():
    torch.manual_seed(4)
    student = torch.randn(5, 11, requires_grad=True)
    teacher = torch.randn(5, 11, requires_grad=True)
    coarse = token_kl(student, teacher, top_k=2, chunk_size=2)
    exact = token_kl(student, teacher, top_k=0)
    assert coarse >= -1e-6
    assert coarse <= exact + 1e-6  # KL data-processing inequality.
    coarse.backward()
    assert torch.isfinite(student.grad).all()
    assert teacher.grad is None


def test_sparse_full_union_has_no_nan_gradient():
    student = torch.tensor([[3., 2., 0.], [0., 4., 3.]], requires_grad=True)
    teacher = torch.tensor([[0., 2., 3.], [3., 4., 0.]], requires_grad=True)
    coarse = token_kl(student, teacher, top_k=2, chunk_size=1)
    exact = token_kl(student, teacher)
    torch.testing.assert_close(coarse, exact)
    coarse.backward()
    assert torch.isfinite(student.grad).all()
    assert teacher.grad is None


def test_sparse_duplicate_union_counts_each_token_once():
    student = torch.tensor([[4., 2., 0., -1.]], requires_grad=True)
    teacher = torch.tensor([[3., 1., -1., -2.]], requires_grad=True)
    loss = token_kl(student, teacher, top_k=2)
    assert abs(float(loss)) < 1e-6
    loss.backward()
    assert torch.isfinite(student.grad).all()


def test_response_only_ce_uses_every_continuation_token():
    torch.manual_seed(2)
    logits = torch.randn(1, 5, 7, requires_grad=True)
    labels = torch.tensor([[3, 4, 0, 1, 6]])
    loss = response_cross_entropy(logits, labels, chunk_size=2)
    expected = F.cross_entropy(logits.reshape(-1, 7), labels.reshape(-1))
    torch.testing.assert_close(loss, expected)
    loss.backward()
    assert torch.isfinite(logits.grad).all()


class FakeProcessor:
    def apply_chat_template(self, messages, **kwargs):
        # Visual fields carry sentinels; teacher gets a longer prompt.
        teacher = "hindsight_evidence" in str(messages)
        ids = torch.tensor([[1, 2, 3, 4, 5]] if teacher else [[1, 2, 3]])
        return {"input_ids": ids, "attention_mask": torch.ones_like(ids),
                "pixel_values": torch.tensor([[11., 12., 13.]]),
                "image_grid_thw": torch.tensor([[1, 2, 2]])}


def toy_policy(tmp_path):
    screenshot = tmp_path / "screen.png"
    Image.new("RGB", (32, 32)).save(screenshot)
    policy = QwenPolicy.__new__(QwenPolicy)
    policy.device = torch.device("cpu")
    policy.processor = FakeProcessor()
    policy.max_context_tokens = 20
    policy.model = SimpleNamespace(config=SimpleNamespace(text_config=SimpleNamespace(vocab_size=20)))
    messages = [{"role": "user", "content": [{"type": "image", "image": str(screenshot)},
                                              {"type": "text", "text": "Find item"}]}]
    return policy, messages


def test_visual_inputs_and_sampled_ids_survive_teacher_reprompt(tmp_path):
    policy, messages = toy_policy(tmp_path)
    student = policy.encode(messages, [7, 8, 9])
    teacher = policy.encode(messages, [7, 8, 9], "Found target via search")
    assert student["prompt_length"] == 3
    assert teacher["prompt_length"] == 5
    assert student["response_length"] == teacher["response_length"] == 3
    for key in ["pixel_values", "image_grid_thw"]:
        torch.testing.assert_close(student["inputs"][key], teacher["inputs"][key])
    assert student["inputs"]["input_ids"].tolist() == [[1, 2, 3, 7, 8, 9]]
    assert teacher["inputs"]["input_ids"].tolist() == [[1, 2, 3, 4, 5, 7, 8, 9]]
    assert student["inputs"]["attention_mask"].shape == (1, 6)


def test_context_overflow_and_missing_vision_fail_instead_of_truncating(tmp_path):
    policy, messages = toy_policy(tmp_path)
    policy.max_context_tokens = 4
    with pytest.raises(ValueError, match="no truncation"):
        policy.encode(messages, [7, 8])
    with pytest.raises(ValueError, match="screenshot"):
        policy.encode([{"role": "user", "content": "text only"}])
    with pytest.raises(ValueError, match="nonempty"):
        policy.encode(messages, [])


def test_response_forward_selects_shifted_positions_and_preserves_vision(tmp_path):
    policy, messages = toy_policy(tmp_path)
    encoded = policy.encode(messages, [7, 8, 9])
    class TinyForward:
        def __call__(self, **kwargs):
            assert kwargs["logits_to_keep"].tolist() == [2, 3, 4]
            assert kwargs["pixel_values"].tolist() == [[11., 12., 13.]]
            assert kwargs["use_cache"] is False
            return SimpleNamespace(logits=torch.zeros(1, 3, 20))
    assert response_forward(TinyForward(), encoded).shape == (1, 3, 20)


def example():
    return {"split": "train", "policy": "native", "messages": [{"role": "user", "content": "x"}],
            "response_token_ids": [1, 2], "feedback": "Verified successful attempt"}


def test_validation_prevents_eval_leakage_and_spectral_prefix_distillation():
    good = example()
    validate_training_examples([good], True)
    for change, match in [({"split": "eval"}, "train split"),
                           ({"policy": "spectral"}, "native student"),
                           ({"feedback": ""}, "evidence"),
                           ({"response_token_ids": None, "response": "x"}, "exact sampled")]:
        with pytest.raises(ValueError, match=match):
            validate_training_examples([{**good, **change}], True)
    with pytest.raises(ValueError, match="No usable"):
        validate_training_examples([], True)


def test_lora_targets_exclude_visual_and_fail_on_wrapped_projection():
    class TinyModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.config = SimpleNamespace(text_config=SimpleNamespace(num_hidden_layers=1))
            self.model = torch.nn.Module()
            self.model.visual = torch.nn.Linear(3, 3)
            self.model.language_model = torch.nn.Module()
            layer = torch.nn.Module()
            layer.self_attn = torch.nn.Module()
            for name in ["q_proj", "k_proj", "v_proj", "o_proj"]:
                setattr(layer.self_attn, name, torch.nn.Linear(3, 3))
            self.model.language_model.layers = torch.nn.ModuleList([layer])
    model = TinyModel()
    targets = language_lora_targets(model)
    assert len(targets) == 4 and all("language_model.layers.0.self_attn" in x for x in targets)
    model.model.language_model.layers[0].self_attn.k_proj = torch.nn.Sequential(torch.nn.Linear(3, 3))
    with pytest.raises(TypeError, match="Non-native"):
        language_lora_targets(model)


def test_tiny_native_qwen3vl_visual_lora_teacher_and_merge():
    """Actual pinned architecture, real vision tensors, LoRA, native merge; no downloads."""
    transformers = pytest.importorskip("transformers")
    peft = pytest.importorskip("peft")
    cfg = transformers.Qwen3VLConfig(
        image_token_id=90, vision_start_token_id=91, vision_end_token_id=92,
        video_token_id=93,
        text_config={"vocab_size": 100, "hidden_size": 32, "intermediate_size": 64,
                     "num_hidden_layers": 2, "num_attention_heads": 4,
                     "num_key_value_heads": 2, "head_dim": 8,
                     "max_position_embeddings": 128,
                     "rope_scaling": {"rope_type": "default", "mrope_section": [1, 1, 2],
                                      "mrope_interleaved": True}},
        vision_config={"depth": 2, "hidden_size": 32, "intermediate_size": 64,
                       "num_heads": 4, "patch_size": 2, "spatial_merge_size": 2,
                       "temporal_patch_size": 2, "out_hidden_size": 32,
                       "num_position_embeddings": 16, "deepstack_visual_indexes": [0, 1]},
    )
    torch.manual_seed(42)
    base = transformers.Qwen3VLForConditionalGeneration(cfg).float().eval()
    base.requires_grad_(False)
    pixel_values = torch.randn(4, 24)  # four actual 2x2x2 RGB patches
    def encoded(ids, prompt):
        return {"inputs": {"input_ids": torch.tensor([ids]),
                           "attention_mask": torch.ones(1, len(ids), dtype=torch.long),
                           "pixel_values": pixel_values,
                           "image_grid_thw": torch.tensor([[1, 2, 2]])},
                "prompt_length": prompt, "response_length": 2}
    student = encoded([1, 91, 90, 92, 7, 8], 4)
    teacher = encoded([1, 91, 90, 92, 5, 6, 7, 8], 6)
    targets = language_lora_targets(base)
    model = peft.get_peft_model(base, peft.LoraConfig(
        task_type="CAUSAL_LM", r=2, lora_alpha=4, target_modules=targets,
        lora_dropout=0., bias="none"))
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    with model.disable_adapter(), torch.no_grad():
        before_teacher = response_forward(model, teacher).clone()
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=.01)
    model.train()
    prediction = response_forward(model, student)
    loss = token_kl(prediction, before_teacher, chunk_size=1)
    loss.backward()
    grads = [p.grad for p in model.parameters() if p.requires_grad and p.grad is not None]
    assert grads and all(torch.isfinite(g).all() for g in grads)
    assert sum(float(g.abs().sum()) for g in grads) > 0
    optimizer.step()
    model.eval()
    with model.disable_adapter(), torch.no_grad():
        after_teacher = response_forward(model, teacher)
    torch.testing.assert_close(before_teacher, after_teacher, rtol=0, atol=0)
    with torch.no_grad():
        adapted = response_forward(model, student).clone()
    model.gradient_checkpointing_disable()
    merged = model.merge_and_unload(safe_merge=True).eval()
    with torch.no_grad():
        native = response_forward(merged, student)
    torch.testing.assert_close(adapted, native, rtol=1e-4, atol=1e-5)
    assert not any("lora" in name for name, _ in merged.named_parameters())


def test_fixed_update_budget_covers_full_passes_before_repeating():
    from improving.android.training import plan_training_batches
    groups, report = plan_training_batches(5, 3, max_updates=4, seed=234)
    flattened = [x for group in groups for x in group]
    assert len(groups) == 4 and all(len(group) == 3 for group in groups)
    assert len(flattened) == 12
    assert sorted(flattened[:5]) == list(range(5))
    assert sorted(flattened[5:10]) == list(range(5))
    assert report["unique_examples_used"] == 5
    assert report["completed_corpus_passes"] == 2
    assert sorted(report["example_exposure_counts"]) == [2, 2, 2, 3, 3]
    assert groups == plan_training_batches(5, 3, max_updates=4, seed=234)[0]
    assert "234" not in report["randomization_sha256"] or len(report["randomization_sha256"]) == 64
    assert "seed" not in report


def test_short_update_budget_and_epoch_boundaries_are_explicit():
    from improving.android.training import plan_training_batches
    groups, report = plan_training_batches(10, 2, max_updates=2, seed=1)
    assert len(groups) == 2
    assert report["unique_examples_used"] == 4
    assert report["total_examples"] == 10
    assert report["example_presentations"] == 4
    assert report["completed_corpus_passes"] == 0
    epochs, report = plan_training_batches(5, 3, epochs=2, seed=1)
    assert [len(group) for group in epochs] == [3, 2, 3, 2]
    assert report["example_exposure_counts"] == [2] * 5
    for bad in [0, -1, True, 1.5]:
        with pytest.raises(ValueError):
            plan_training_batches(5, 3, max_updates=bad, seed=1)
    with pytest.raises(ValueError, match="runtime_seed"):
        plan_training_batches(5, 3, seed=None)


@pytest.mark.parametrize("mode", ["sft", "feedback"])
def test_training_entrypoint_honors_update_budget_with_native_visual_model(tmp_path, monkeypatch, mode):
    transformers = pytest.importorskip("transformers")
    pytest.importorskip("peft")
    import improving.android.training as training
    cfg = transformers.Qwen3VLConfig(
        image_token_id=90, vision_start_token_id=91, vision_end_token_id=92, video_token_id=93,
        text_config={"vocab_size": 100, "hidden_size": 32, "intermediate_size": 64,
                     "num_hidden_layers": 2, "num_attention_heads": 4, "num_key_value_heads": 2,
                     "head_dim": 8, "max_position_embeddings": 128,
                     "rope_scaling": {"rope_type": "default", "mrope_section": [1, 1, 2],
                                      "mrope_interleaved": True}},
        vision_config={"depth": 2, "hidden_size": 32, "intermediate_size": 64, "num_heads": 4,
                       "patch_size": 2, "spatial_merge_size": 2, "temporal_patch_size": 2,
                       "out_hidden_size": 32, "num_position_embeddings": 16,
                       "deepstack_visual_indexes": [0, 1]},
    )
    class ProcessorStub:
        def save_pretrained(self, path):
            (path / "processor_fixture.txt").write_text("CPU test fixture, not a deployed processor")
    class TinyPolicy:
        def __init__(self, checkpoint, config):
            self.model = transformers.Qwen3VLForConditionalGeneration(cfg).float().eval()
            self.model.requires_grad_(False)
            self.device = torch.device("cpu")
            self.processor = ProcessorStub()
            self.pixels = torch.randn(4, 24)
        def encode_example(self, example, feedback=None):
            ids = [1, 91, 90, 92] + ([5, 6] if feedback else []) + example["response_token_ids"]
            return {"inputs": {"input_ids": torch.tensor([ids]),
                               "attention_mask": torch.ones(1, len(ids), dtype=torch.long),
                               "pixel_values": self.pixels,
                               "image_grid_thw": torch.tensor([[1, 2, 2]])},
                    "prompt_length": len(ids) - 2, "response_length": 2}
        def close(self):
            self.model = None
    monkeypatch.setattr(training, "QwenPolicy", TinyPolicy)
    config = {"runtime_seed": 777, "train": {"max_updates": 2, "epochs": 99,
               "gradient_accumulation_steps": 2, "lora_rank": 2, "lora_alpha": 4,
               "learning_rate": .01, "gradient_checkpointing": True}}
    examples = [{**example(), "response_token_ids": [7, 8]} for _ in range(3)]
    run = training.train_feedback if mode == "feedback" else training.train_sft
    receipt = run("fixture", examples, tmp_path / mode, config)
    assert receipt["optimizer_steps"] == 2
    assert receipt["example_presentations"] == 4
    assert receipt["response_token_presentations"] == 8
    assert receipt["total_examples"] == 3
    assert receipt["unique_examples_used"] == 3
    assert receipt["epochs"] is None and receipt["epochs_applied"] is None
    assert receipt["status"] == "completed"
    assert (tmp_path / mode / "android_training_receipt.json").is_file()
    # The actual saved native architecture can be loaded, without LoRA wrappers.
    restored = transformers.Qwen3VLForConditionalGeneration.from_pretrained(tmp_path / mode)
    assert not any("lora" in name for name, _ in restored.named_parameters())
    with pytest.raises(FileExistsError):
        run("fixture", examples, tmp_path / mode, config)


def test_pinned_real_processor_and_tool_call_decoding(tmp_path):
    """Optional metadata-only integration; no model weights or network in tests.

    Set SPECTRUM_ANDROID_PROCESSOR_PATH to the pinned metadata-only snapshot.
    """
    import os
    snapshot = os.environ.get("SPECTRUM_ANDROID_PROCESSOR_PATH")
    if not snapshot:
        pytest.skip("Set SPECTRUM_ANDROID_PROCESSOR_PATH for real processor integration")
    transformers = pytest.importorskip("transformers")
    processor = transformers.AutoProcessor.from_pretrained(
        snapshot, local_files_only=True, min_pixels=65536, max_pixels=262144)
    configure_image_limits(processor, 65536, 262144)
    screenshot = tmp_path / "native_processor_screen.png"
    Image.new("RGB", (720, 1280), (120, 150, 100)).save(screenshot)
    messages = [{"role": "user", "content": [
        {"type": "image", "image": str(screenshot)}, {"type": "text", "text": "Open Notes."}]}]
    response = ('Thought: Open the app.\nAction: Tap Notes.\n<tool_call>\n'
                '{"name":"mobile_use","arguments":{"action":"click","coordinate":[100,200]}}'
                '\n</tool_call>')
    ids = processor.tokenizer.encode(response, add_special_tokens=False)
    decoded = processor.tokenizer.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    assert decoded == response
    assert "<tool_call>" in decoded and "</tool_call>" in decoded
    policy = QwenPolicy.__new__(QwenPolicy)
    policy.processor = processor
    policy.device = torch.device("cpu")
    policy.max_context_tokens = 8192
    model_config = transformers.AutoConfig.from_pretrained(snapshot, local_files_only=True)
    policy.model = SimpleNamespace(config=model_config)
    student = policy.encode(messages, ids)
    teacher = policy.encode(messages, ids, "The recorded attempt did not finish the task.")
    assert teacher["prompt_length"] > student["prompt_length"]
    assert teacher["response_length"] == student["response_length"] == len(ids)
    for encoded in [student, teacher]:
        assert encoded["inputs"]["input_ids"][0, -len(ids):].tolist() == ids
        assert encoded["inputs"]["pixel_values"].numel() > 0
        assert encoded["inputs"]["image_grid_thw"].shape == (1, 3)
    torch.testing.assert_close(student["inputs"]["pixel_values"], teacher["inputs"]["pixel_values"])
    torch.testing.assert_close(student["inputs"]["image_grid_thw"], teacher["inputs"]["image_grid_thw"])
    assert processor.image_processor.size["longest_edge"] == 262144
    grid = student["inputs"]["image_grid_thw"][0]
    processed_pixels = int(grid[1] * grid[2]) * processor.image_processor.patch_size**2
    assert 65536 <= processed_pixels <= 262144
    # Saved metadata must not silently restore the upstream 16M-pixel budget.
    processor.save_pretrained(tmp_path / "saved_processor")
    reloaded = transformers.AutoProcessor.from_pretrained(tmp_path / "saved_processor", local_files_only=True)
    assert reloaded.image_processor.size["longest_edge"] == 262144
