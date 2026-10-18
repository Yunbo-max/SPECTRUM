# B01 native qualification route and RTX4090 migration — 2026-10-18

## Source repair and validation
Root cause: B01 requires an available/qualified evaluator but its frozen catalog allows only source work. Completed source acquisition and repeated review left evaluation_identity unsatisfied with no executable qualification action. New runtime commit61b6e723501b301f37e0daed5ec83fa2d387573e adds an explicit owner-authorized B01 qualification opt-in. Catalog hash and skill digest remain unchanged; original accepted nodes, attempts, coverage, failures and cumulative use are preserved.

The new API records an immutable authorization adoption at a quiet active/decide boundary, rejects stale revisions, paused/active/unknown tasks and null authorization. Only native_purpose=qualification, research_scope=diagnostic on the fixed target is admitted; per-proposal max_tasks1 and per-task3600seconds do not create an aggregate research cap. Existing v4 decisions, canonical no-treatment validation and independent review remain required.

50 focused/B01/controller/command-receipt tests passed on hn01 RTX4090 server under Python3.12; tested program.py,skill_sequence.py and test_b01_qualification.py hashes match adopted local bytes. Independent static review found and then confirmed correction of null authorization adoption. No local test execution was used for this patch.

Broader admission tests:7failures/14 on both unchanged32e3746 and patchedcode. A diagnostic replay reports old fixture missing current research_scope method/diagnostic. These failures are retained; full regression success is not claimed. Admission was not weakened to make old fixtures pass.

## Latest execution host and readiness
Only spectrum-harness-gpu-hn01 is the new target. Hardware RTX4090,24564MiB, compute capability8.9, cgroup memory.max107374182400bytes and cpu.max1500000/100000. Systemtorch2.12.1+cu130 executed small FP32,FP16,BF16 matrix multiplications, allfinite/maxerror0. NativeBF16true. This is a capability smoke, not model/training/scorer qualification. The fixed projectvenv torch2.7.1+cu126 and pinned train dependencies are separately installing from Tsinghua; setup/environment-status.json and environment.log are authoritative. Preparation PID287 uses the single setup/prepare_environment.py; do not duplicate. It then downloads existing model/data revisions via hf-mirror.

The same namespace probe returnedEPERM here. SSH works. This limits that isolation approach only; do not execute untrusted generated programs without their required controls or call the scorerqualified. Independent training/generation/export does not inherit an offline scorer dependency. Do not confuse systemtorch with the separately installing venv.

Remote SPECTRUM sourcebfc00951726a79b50fb8d75c16479903c9d3290e was cloned via Gitbundle and read back. Remote native skillroot remains /root/rivermind-data/spectrum-harness/skill. Parent GPU/source probes are supplemental observations, not invented native_harness receipts or scientificscores.

## Adoption and continuation
Same database moved fromrevision88 (quietB01) to89 (explicit source/target amendment) to90 (B01 qualification authorization). See research-state/b01-hn01-source-target-adoption-20261018.json and research-state/harness/adoptions/b01-qualification-000090.json. User instruction is research-state/gpu-switch-hn01-20261018.md; effective contract program.b01-hn01-20261018.json. Nextworker should use the new qualification packet to prepare admissible real plans, not repeat the exhausted read-only directory search or return tasks=[] as readiness. Preserve original B01 requirements, full500 denominator,setup/challenge/prompt distinctions and unresolved semanticmetric limits.
