"""Native image-conditioned Qwen3-VL policy used by the Android study.

This module deliberately does not use the text-only SPECTRUM embedding loader.
Every forward retains the processor's visual tensors and native multimodal RoPE.
Heavy training dependencies are imported only when a policy is instantiated.
"""
from __future__ import annotations

import copy
import gc
from pathlib import Path
from typing import Any


def add_feedback(messages: list[dict], feedback: str | None) -> list[dict]:
    """Return a teacher prompt without modifying the student's recorded prompt."""
    out = copy.deepcopy(messages)
    if not out or out[-1].get("role") != "user":
        raise ValueError("Android prompts must end with a user turn")
    if not feedback:
        return out
    if not isinstance(feedback, str):
        raise TypeError("feedback must be a string")
    text = ("\nTraining-only hindsight evidence follows. It may describe another "
            "attempt from the same initial task; use the CURRENT screenshot and "
            "history to judge applicability. Do not claim unseen actions occurred "
            "in the current attempt. Re-evaluate the existing response using this "
            "evidence.\n<hindsight_evidence>\n" + feedback + "\n</hindsight_evidence>")
    content = out[-1].get("content", "")
    if isinstance(content, str):
        out[-1]["content"] = content + text
    elif isinstance(content, list):
        content.append({"type": "text", "text": text})
    else:
        raise TypeError("User content must be text or a list of multimodal blocks")
    return out


def _checked_messages(messages: list[dict], feedback: str | None) -> list[dict]:
    out = add_feedback(messages, feedback)
    image_count = 0
    for message in out:
        content = message.get("content", "")
        if isinstance(content, list):
            for block in content:
                if block.get("type") == "image":
                    value = block.get("image")
                    if not isinstance(value, str) or not Path(value).is_file():
                        raise ValueError("Image blocks must reference existing local screenshots")
                    block["image"] = str(Path(value).resolve())
                    image_count += 1
                elif block.get("type") not in {"text"}:
                    raise ValueError("Only local screenshot images and text are supported")
    if image_count == 0:
        raise ValueError("Android policy requires at least one actual screenshot")
    return out


def configure_image_limits(processor, min_pixels: int, max_pixels: int) -> None:
    """Synchronize native size fields and compatibility aliases before saving.

    Transformers 4.57.1's from_pretrained updates min/max aliases after image
    processor construction, leaving the saved ``size`` mapping at upstream
    defaults. Set both representations explicitly so reloads retain this study's
    pixel budget regardless of which representation the native processor uses.
    """
    if (type(min_pixels) is not int or type(max_pixels) is not int
            or min_pixels < 1 or max_pixels < min_pixels):
        raise ValueError("Image pixel limits must be positive integers with min <= max")
    image_processor = processor.image_processor
    image_processor.size = {"shortest_edge": min_pixels, "longest_edge": max_pixels}
    image_processor.min_pixels = min_pixels
    image_processor.max_pixels = max_pixels


class QwenPolicy:
    """Single-device BF16 native model; quantized/wrapped base models are rejected.

    Config sections: model (device, dtype, revision, local_files_only,
    attn_implementation, min_pixels, max_pixels, max_context_tokens), generation
    (max_new_tokens, temperature, top_p, top_k, do_sample).
    """

    def __init__(self, checkpoint: str, config: dict[str, Any]):
        import torch
        from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

        self.config = config
        self.checkpoint = str(checkpoint)
        settings = config.get("model", {})
        self.device = torch.device(settings.get("device", "cuda:0"))
        dtype_name = settings.get("dtype", "bfloat16")
        if dtype_name not in {"bfloat16", "float32"}:
            raise ValueError("Android native policy supports bfloat16 or float32, not quantization")
        if self.device.type == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("A CUDA device is required by this model configuration")
        dtype = getattr(torch, dtype_name)
        if self.device.type == "cuda" and dtype == torch.bfloat16 and not torch.cuda.is_bf16_supported():
            raise RuntimeError("Configured CUDA device does not support BF16")
        self.max_context_tokens = int(settings.get("max_context_tokens", 8192))
        if self.max_context_tokens < 2:
            raise ValueError("max_context_tokens must be at least 2")
        load = {"local_files_only": bool(settings.get("local_files_only", True)),
                "trust_remote_code": False}
        # A locally merged checkpoint must not inherit the upstream revision.
        if not Path(checkpoint).is_dir() and settings.get("revision"):
            load["revision"] = settings["revision"]
        min_pixels = int(settings.get("min_pixels", 65536))
        max_pixels = int(settings.get("max_pixels", 262144))
        self.processor = AutoProcessor.from_pretrained(
            checkpoint, min_pixels=min_pixels, max_pixels=max_pixels, **load)
        configure_image_limits(self.processor, min_pixels, max_pixels)
        self.model = Qwen3VLForConditionalGeneration.from_pretrained(
            checkpoint, dtype=dtype,
            attn_implementation=settings.get("attn_implementation", "sdpa"), **load)
        if getattr(self.model.config, "model_type", None) != "qwen3_vl":
            raise ValueError("This study qualifies only dense Qwen3-VL checkpoints")
        if getattr(self.model, "is_quantized", False):
            raise ValueError("Spectral folding requires unquantized native linear projections")
        self.model.to(self.device).eval()
        self.model.requires_grad_(False)
        self.processor.tokenizer.padding_side = "left"
        if self.processor.tokenizer.pad_token_id is None:
            self.processor.tokenizer.pad_token_id = self.processor.tokenizer.eos_token_id

    def encode(self, messages: list[dict], response_token_ids: list[int] | None = None,
               feedback: str | None = None) -> dict[str, Any]:
        """Encode the exact prompt plus optional sampled continuation, never truncate.

        Returns ``inputs`` (native model kwargs), ``prompt_length`` and
        ``response_length``. Metadata is not forwarded to the model. Prompt and
        teacher lengths may differ; continuation IDs are identical in both.
        """
        import torch

        prepared = _checked_messages(messages, feedback)
        encoded = self.processor.apply_chat_template(
            prepared, tokenize=True, add_generation_prompt=True,
            return_dict=True, return_tensors="pt")
        inputs = dict(encoded)
        if "pixel_values" not in inputs or "image_grid_thw" not in inputs:
            raise RuntimeError("Processor omitted native screenshot tensors")
        ids = inputs["input_ids"]
        if ids.ndim != 2 or ids.shape[0] != 1:
            raise ValueError("Android runtime currently requires microbatch size one")
        prompt_length = int(ids.shape[1])
        response_length = 0
        if response_token_ids is not None:
            if (not isinstance(response_token_ids, list) or not response_token_ids
                    or any(type(x) is not int or x < 0 for x in response_token_ids)):
                raise ValueError("response_token_ids must be a nonempty list of nonnegative integers")
            vocab_size = int(self.model.config.text_config.vocab_size)
            if max(response_token_ids) >= vocab_size:
                raise ValueError("Response token ID exceeds model vocabulary")
            continuation = torch.tensor([response_token_ids], dtype=ids.dtype)
            response_length = len(response_token_ids)
            inputs["input_ids"] = torch.cat((ids, continuation), dim=1)
            mask = inputs.get("attention_mask", torch.ones_like(ids))
            inputs["attention_mask"] = torch.cat((mask, torch.ones_like(continuation)), dim=1)
            for key in ("token_type_ids", "mm_token_type_ids"):
                if key in inputs:
                    inputs[key] = torch.cat((inputs[key], torch.zeros_like(continuation)), dim=1)
            if "position_ids" in inputs:
                raise RuntimeError("Unexpected processor position_ids; native Qwen3-VL must compute multimodal positions")
        total = prompt_length + response_length
        if total > self.max_context_tokens:
            raise ValueError(f"Context needs {total} tokens, configured maximum is {self.max_context_tokens}; no truncation performed")
        inputs = {key: value.to(self.device) if torch.is_tensor(value) else value
                  for key, value in inputs.items()}
        return {"inputs": inputs, "prompt_length": prompt_length,
                "response_length": response_length}

    def encode_example(self, example: dict, feedback: str | None = None) -> dict[str, Any]:
        ids = example.get("response_token_ids")
        if ids is None:
            text = example.get("response")
            if not isinstance(text, str) or not text:
                raise ValueError("Training response is empty")
            ids = self.processor.tokenizer.encode(text, add_special_tokens=False)
            eos = self.processor.tokenizer.eos_token_id
            if eos is not None and (not ids or ids[-1] != eos):
                ids.append(eos)
        return self.encode(example["messages"], ids, feedback=feedback)

    def generate(self, messages: list[dict]) -> dict[str, Any]:
        import torch

        encoded = self.encode(messages)
        cfg = self.config.get("generation", {})
        max_new = int(cfg.get("max_new_tokens", 256))
        if max_new < 1 or encoded["prompt_length"] + max_new > self.max_context_tokens:
            raise ValueError("Generation would exceed the declared context budget; no history is silently dropped")
        do_sample = bool(cfg.get("do_sample", True))
        kwargs = {"max_new_tokens": max_new, "do_sample": do_sample,
                  "use_cache": True, "pad_token_id": self.processor.tokenizer.pad_token_id}
        if do_sample:
            temperature = float(cfg.get("temperature", 0.7))
            if temperature <= 0:
                raise ValueError("Sampling temperature must be positive")
            kwargs.update(temperature=temperature, top_p=float(cfg.get("top_p", .8)),
                          top_k=int(cfg.get("top_k", 20)))
        self.model.eval()
        with torch.inference_mode():
            generated = self.model.generate(**encoded["inputs"], **kwargs)
        continuation = generated[0, encoded["prompt_length"]:].tolist()
        text = self.processor.tokenizer.decode(
            continuation, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        return {"response": text, "response_token_ids": continuation,
                "prompt_tokens": encoded["prompt_length"], "completion_tokens": len(continuation),
                "finish_reason": "length" if len(continuation) == max_new else "stop"}

    def close(self) -> None:
        import torch
        self.model = None
        self.processor = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
