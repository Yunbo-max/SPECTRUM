# GPU migration handoff — 2026-10-20

The user requested migration to a different GPU host. Research authorization and the current SSD comparison remain in force; this is a host change, not a new study.

## Current reachable state

- The previously configured SSH alias `spectrum-harness-gpu-hn01` targets the old hn01 endpoint. A fresh connection on 2026-10-20 returned `Connection refused` before authentication. The remote host/process state is therefore unknown, not confirmed stopped or failed.
- The latest durable remote snapshot is `ssd-author-comparison-20261019/progress-observation.json`: runner PID 65584 matched its recorded identity; repeats 00 and 01 were complete; seed 2 was at 75/131. A subsequent 78/131 observation was not persisted. The completed repeats and their per-repeat audits are retained in this branch.
- The work plan is the upstream SSD author-code LiveCodeBench comparison. The base condition uses Qwen3-4B-Instruct-2507; SimpleSD-4B-Instruct is the paired released checkpoint. Do not start duplicate work on another host until the old endpoint's actual state and transferable outputs are reconciled.
- Official Qwen-author MBPP/EvalPlus evaluation and the sanitizer diagnosis are complete and recorded separately. They do not depend on this GPU migration.

## Migration procedure after new endpoint access is supplied/configured

1. Connect read-only first; inspect GPU hardware, disk, model/data cache, running PIDs, process identity, lock owner, active stage, exit records and output hashes on both hosts.
2. Preserve and transfer durable inputs, code, exact environment/source revisions, completed repeats, logs and partial outputs. Use checksummed resumable transfer. Never copy SSH passwords or tokens into this branch.
3. Determine whether the old runner finished or remains active. If still active, coordinate its stop only after confirming checkpoint/output state; do not launch a duplicate. Continue from the last complete repeat or task where the author pipeline permits exact resumption.
4. Probe the new GPU's actual VRAM, compute capability, CUDA/PyTorch/vLLM compatibility, storage and throughput. Adapt execution capacity while preserving author model, prompt, sampling, test and scoring semantics; record any necessary deviations.
5. Resume the existing sequential comparison and push subsequent evidence to this SPECTRUM branch.

## Status

The user has asked that the GitHub branch be updated first. This file records the request and known handoff. No new GPU endpoint details were present in the session, so no connection to a guessed host or migration of live files was attempted. Research goal remains incomplete.
