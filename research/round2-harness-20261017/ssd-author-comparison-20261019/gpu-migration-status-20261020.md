# GPU migration handoff — 2026-10-20

The user requested migration to a different GPU host. Research authorization and the current SSD comparison remain in force; this is a host change, not a new study.

## Current reachable state

- The previously configured SSH alias `spectrum-harness-gpu-hn01` targets the old hn01 endpoint. A fresh connection on 2026-10-20 returned `Connection refused` before authentication. The remote host/process state is therefore unknown, not confirmed stopped or failed.
- The latest durable remote snapshot is `ssd-author-comparison-20261019/progress-observation.json`: runner PID 65584 matched its recorded identity; repeats 00 and 01 were complete; seed 2 was at 75/131. A subsequent 78/131 observation was not persisted. The completed repeats and their per-repeat audits are retained in this branch.
- The work plan is the upstream SSD author-code LiveCodeBench comparison. The base condition uses Qwen3-4B-Instruct-2507; SimpleSD-4B-Instruct is the paired released checkpoint. Do not start duplicate work on another host until the old endpoint's actual state and transferable outputs are reconciled.
- Official Qwen-author MBPP/EvalPlus evaluation and the sanitizer diagnosis are complete and recorded separately. They do not depend on this GPU migration.

## SH02 / T4 access and preflight

The user supplied SH02 access on 2026-10-20. Alias `spectrum-harness-gpu-sh02` connects successfully. The host is a Tesla T4 (compute capability 7.5, 15 GiB VRAM), driver 580.119.02, CUDA 13.0, Python 3.12.13, and PyTorch 2.12.1+cu130. `torch.cuda.is_bf16_supported(including_emulation=False)` is false; the default check is true because it allows emulation. Use native FP16. vLLM/model dependencies are not yet installed and no model inference has run on SH02.

The broad first rsync was stopped because it included large, irrelevant upstream Git trees. A focused transfer is needed for project guidance, SSD author-adapted code, and durable result records. The host currently has about 30 GiB free. The preflight and scientific comparability notes are in `gpu-migration-preflight-20261020.md`.

Do not pool old hn01 BF16 samples with new T4 FP16 samples. Original condition scripts currently hard-code BF16 and a 65,536-token output cap; create a separate FP16 run and probe feasible context on T4 before generation. Any shorter cap is a documented protocol deviation and requires matched base/SimpleSD settings. Preserve all existing BF16 files.

The old hn01 endpoint still refuses SSH, so its process state remains unknown. The last durable snapshot remains two completed base repeats and seed 2 at 75/131; do not claim the old runner stopped or completed.

## Local Harness recovery

The local host guard stopped because stale PID records included macOS services whose process creation identity could not be read. The guard interpreted an unreadable identity as a confirmed live research worker. The guard now only blocks on a PID whose recorded and current creation identities can both be read and match; it still refuses to signal a process without a verified identity. Swap usage alone is not a stop condition when memory pressure is at warning level and existing disk/RSS conditions pass. This is supervisor recovery, not evidence of a GPU experiment.

Research remains active. No SH02 inference result is claimed until environment installation, model/dataset verification, and an actual run are recorded.

## Status

The user has asked that the GitHub branch be updated first. This file records the request and known handoff. No new GPU endpoint details were present in the session, so no connection to a guessed host or migration of live files was attempted. Research goal remains incomplete.
