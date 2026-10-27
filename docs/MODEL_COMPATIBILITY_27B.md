# Qwen3.8-27B text-path qualification

Status: `generated_unexecuted`. This is a source-reviewed adapter and input contract.
No 27B loading, generation, calibration, training, test, memory measurement or benchmark
has been executed by this Web delivery. Native acceptance is required before dispatch.

## Model identity and loading

- Repository: `Qwen/Qwen3.8-27B` (the released post-trained model).
- Immutable revision: `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`.
- Original architecture: `Qwen3_5ForConditionalGeneration`, `model_type=qwen3_5`.
- Selected path: official `Qwen3_5ForCausalLM`; `model.loader: qwen3_5_text`.
- Input protocol: text for math/QA and lossless text-encoded frames for ARC-AGI-3.
  This experiment does not use the vision encoder. It does not evaluate visual perception.
- Precision: unquantized BF16 native Linear projections. Quantized weights are rejected.
- Placement: one admitted CUDA device. Multi-device training is not implemented by
  changing `device_map` to `auto`; the actual host must qualify this single-device path.

The Transformers text class consumes the original checkpoint through its official
`qwen3_5_text` prefix conversion (`model.language_model.*` to `model.*`). It excludes
vision and MTP weights. Every required text weight must load; missing/mismatched
weights or unrecognized unexpected weights fail. A merged round checkpoint contains
the text configuration and reloads with the same `qwen3_5_text` loader.
Set `local_files_only: true` after acquisition; loading does not fetch hidden assets.
Full upstream model acquisition still retains tokenizer/config/generation config,
index and every referenced shard so that the original pinned snapshot is auditable.

```yaml
model:
  name: Qwen/Qwen3.8-27B
  revision: 1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0
  loader: qwen3_5_text
  local_files_only: true
  dtype: bfloat16
  device: cuda
  attn_implementation: sdpa
spectral:
  layers: [31, 63]
  projections: [k_proj, v_proj]
train:
  lora_target_modules: [q_proj, k_proj, v_proj, o_proj]
```

Thinking is a task-level, serialized protocol field, for example
`"chat_template_kwargs": {"enable_thinking": false}`. Generation, SFT and calibration
all call the same `render_prompt`. If a study uses thinking, it must freeze that mode
and its reasoning effort consistently; this delivery adds no temperature or mode sweep.

## What SPECTRUM changes

The text backbone has 64 layers: 48 Gated DeltaNet layers and 16 full-attention layers.
Full-attention indices are `3,7,11,15,19,23,27,31,35,39,43,47,51,55,59,63`.
The fixed spectral intervention selects indices 31 and 63: the lower middle and final
full-attention layers, chosen by topology before results. Hybrid models require explicit
layer indices; requesting a GDN layer is an error.

For each selected layer, SPECTRUM captures gradients at the raw `k_proj` and `v_proj`
outputs. For a row activation `h`, the intervention is `h T`; the temporary parameter
fold is `W' = T^T W`, `b' = T^T b`. This precedes per-head K normalization and RoPE.
The original tensors are restored after generation before student training. A scalar
K transform can be substantially canceled by K normalization; no post-normalization
interpretation or model-independent isotropic-control effect is claimed.

LoRA expands q/k/v/o into exact paths on all 16 full-attention layers. GDN, the FFNs
and the omitted vision encoder are not LoRA targets. Vanilla SD, adapted SSD and
SPECTRUM share this trainable parameter set. This is an attention-only adaptation of
the hybrid backbone, not a modification of its recurrent state or all 64 token mixers.

The same resolver preserves standard `model.layers` layouts for Qwen2.5, Llama and
DeepSeek-Coder. Nested `model.language_model.layers` is recognized for inspected
native wrappers; ambiguous/unsupported layouts fail rather than guessing.

## Native environment and acceptance

Use a separate Python 3.12 Conda environment. From the delivered repository:

```bash
python -m pip install -r requirements/multidomain-27b.txt
python -m pip install -e '.[test]'
python -m pip freeze > runs/private/multidomain-installed-packages.txt
python -m pytest tests/test_multidomain_modeling.py tests/test_modeling.py tests/test_spectral.py tests/test_training.py
```

These are Local harness payloads, not commands executed by Web. The environment uses Transformers 5.21.0, PEFT
0.21.2, Accelerate 1.15.0 and Datasets 5.1.0. The requirements file intentionally leaves
the CUDA-specific Torch build to actual host admission. Record its build, driver,
CUDA/runtime, full package resolution, GPU UUID and precision before the run. Do not
install the old `.[train]` extra here, or upgrade an active historical environment.

The added software tests exercise path/target/template contracts using small artificial
modules. They do not establish Qwen3.8 inference quality or 27B runtime compatibility.
After model and math input preparation, run the real pinned model qualification:

```bash
python scripts/qualify_reasoning_model.py --config configs/multidomain/text_math.json --output-dir runs/qualification/qwen38-27b-math
```

This verifies the complete snapshot manifest, selects one longest native training
prompt and one longest calibration reference by token length, then checks native
prompt/EOS generation, finite gradient covariances at all four selected projections,
folded forward and exact parameter restoration, one finite nonzero LoRA gradient
step, merge/save and merged-checkpoint reload. It writes a new checkpoint and
`qualification.json` with source/config/data/runtime bindings and measured peaks.
It never scores benchmark test questions or changes existing scientific checkpoints.
The output directory is fresh-only so failed attempts cannot be overwritten. A retry
uses a new output directory after the diagnosed repair.

Its pass qualifies these native interfaces on the selected development examples;
formal longest sequence shapes and ARC interaction/scoring still require their own
admission. Run all comparisons only after their actual dependencies pass.

27 billion BF16 parameters alone imply roughly 54 decimal GB before activations,
temporary logits, KV/recurrent state, adapters and optimizer tensors. This is an
arithmetic estimate, not a measured peak or a promise that one 80 GB card fits.
The 248,320-token vocabulary makes full-sequence calibration/training logits expensive.
Qualify the study's actual maximum lengths and microbatch 1 with gradient checkpointing;
record truncation and peak allocated/reserved memory. No automatic quantization,
precision change or context truncation is permitted to conceal an OOM.

The pinned native implementation has a Torch fallback for the GDN operators. This
delivery does not enable unpinned Hub kernels. Any optimized kernel installation is
a newly recorded environment requiring the same native numerical acceptance.

## Inspected primary sources

- [Pinned Qwen configuration](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/config.json)
- [Pinned Qwen model card](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/README.md)
- [Transformers native model](https://github.com/huggingface/transformers/blob/dded62b5e641816d552098b1b8de578d17121740/src/transformers/models/qwen3_5/modeling_qwen3_5.py)
- [Text weight conversion](https://github.com/huggingface/transformers/blob/dded62b5e641816d552098b1b8de578d17121740/src/transformers/conversion_mapping.py)
- [Official text-only usage](https://github.com/huggingface/transformers/blob/dded62b5e641816d552098b1b8de578d17121740/docs/source/en/model_doc/qwen3_5.md)
- [Transformers package contract](https://github.com/huggingface/transformers/blob/dded62b5e641816d552098b1b8de578d17121740/setup.py)
- [PEFT 0.21.2](https://github.com/huggingface/peft/releases/tag/v0.21.2)
- [Accelerate 1.15.0](https://github.com/huggingface/accelerate/releases/tag/v1.15.0)
- [Datasets 5.1.0](https://github.com/huggingface/datasets/releases/tag/5.1.0)
