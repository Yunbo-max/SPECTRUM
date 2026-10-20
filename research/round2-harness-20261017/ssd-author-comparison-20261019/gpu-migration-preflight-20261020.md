# SH02 GPU migration preflight — 2026-10-20

The user provided SSH access to a new host and asked to migrate the ongoing comparison. This is a read-only capability check plus remote access setup, not a model result.

## Verified hardware and software

- GPU: NVIDIA Tesla T4, compute capability 7.5, 15,360 MiB VRAM.
- Driver: 580.119.02; CUDA toolkit/runtime reported by the host: 13.0.
- Python: 3.12.13; PyTorch: 2.12.1+cu130.
- Native BF16 capability check: `torch.cuda.is_bf16_supported(including_emulation=False)` -> `False`.
- Default PyTorch check: `torch.cuda.is_bf16_supported()` -> `True`; this default permits emulation. It does not establish native BF16 arithmetic or BF16 Tensor Core support.
- Disk at preflight: root overlay 30 GiB free. No inference workload was running.
- vLLM, Transformers, datasets and EvalPlus were not installed at preflight. A Python 3.12/CUDA13 environment still needs compatible upstream dependencies and an actual T4 engine-startup check.

NVIDIA's compute-capability table lists FP16 Tensor Core support at 7.5 and BF16 support starting at 8.0. PyTorch documents the `including_emulation=True` default for its dtype check. Current vLLM installation docs list T4/compute capability 7.5 as supported; this is compatibility guidance, not evidence that the local environment is installed or that the research run has succeeded.

Sources:
- https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/compute-capabilities.html
- https://docs.pytorch.org/docs/stable/generated/torch.cuda.is_bf16_supported.html
- https://docs.vllm.ai/en/stable/getting_started/installation/gpu/index.html?device=cuda

## Migration and scientific comparability

A dedicated local SSH identity and alias `spectrum-harness-gpu-sh02` were configured for unattended Harness access. The private key stays outside the repository. The old hn01 SSH endpoint still refuses connections, so its current process state remains unknown. Last durable snapshot: runner65584 identity matched, two complete base repeats, seed2 at75/131; a later78/131 observation was not persisted.

The old base-generation config was BF16 with max_model_len67072 and max_tokens65536. Do not assume this context fits 15GiB T4 VRAM. Probe engine initialization, free KV cache and throughput on T4. The new host must use native FP16. Keep context/output caps equal across all migrated base and SimpleSD conditions; disclose and audit any reduction from the author's 65536 output budget. Existing hn01 BF16 repeats 00 and01 remain preserved historical data and must not be pooled into migrated FP16 estimates. Old host job state must be reconciled before considering any transfer or duplicate launch.

The project synchronization to `/root/rivermind-data/spectrum-harness/project` and official-code/model setup were initiated after preflight. No model weights, vLLM install, evaluation, or new GPU inference is claimed complete in this record. See `gpu-migration-status-20261020.md` for the durable handoff and next steps.
