# Web to Local: cross-family code and 27B multi-domain study

Status: **generated_unexecuted**. User authorized source/configuration delivery to
Yunbo-max/SPECTRUM main. No model/scientific runtime was executed by Web.
Parent: `1bb86ee5b19d23056c8c5332c7ad8c600e1c4aa6`. The publication receipt supplies
the delivered commit; a file cannot contain its own future commit ID.

Read [AGENTS](../../AGENTS.md), [runbook](../../LOCAL_AGENT_RUNBOOK.md),
[code](../../docs/CROSSFAMILY_CODE.md), [text](../../docs/TEXT_TASKS.md),
[ARC](../../docs/ARC_AGI3.md), [native scoring](../../docs/NATIVE_SCORING.md) and
[model adapter](../../docs/MODEL_COMPATIBILITY_27B.md). These entries replace the
old40-job default. No historical numerical result or dataset has been rewritten.

## Scope and construction

Three code-model families retain Qwen2.5-Coder7B as the main model. Base + Vanilla
+ SSD adaptation + SPECTRUM; five recursive rounds, one trajectory, no seed/temperature
grid. Independent math/QA training starts from the same original27B checkpoint;
full MATH500/MMLU-Pro/GPQA Diamond evaluation is separate from code-trained transfer.

ARC uses pinned native SDK/engine, all-frame lossless text observations, bounded
legal-action interaction, raw-action SFT and native scorecards. Default train/dev
ls20, calibration ft09, heldout vc33; a small public holdout extension, not full
competition evaluation. Larger registered splits are explicit new prepared inputs.

The existing gradient-second-moment operator and temporary raw K/V folding remain.
Hybrid27B intervention is layers31/63; Q/K/V/O LoRA covers native full-attention layers.
Native student evaluation needs no spectral operator. Compare correctness and
code/math task coverage along the loop, QA accuracy and native ARC outcomes.
AST breadth is a code proxy, not a general reasoning-diversity metric.

## Local acceptance

The runbook supplies actual environment/acquisition/verification/qualification/
per-cell execution/status/resume/return commands. Restore real host, GPU, storage,
runtime and access. No passing host admission, software test, scorer replay or
capability is assumed. This is an existing-method expansion, not a new idea pool.

Run source-delivered contract tests in their matching native environments:
`tests/test_multidomain_modeling.py`, `tests/test_crossfamily_study.py`,
`tests/test_arc3_contracts.py`, and the native sandbox/domain tests present in this
delivery. Qualify the actual native boundary and official scorer; real27B
development-model calibration/folding/LoRA/reload; ARC frame/action/replay/scorecards.
Tests and qualification examples do not replace complete benchmark populations.
All base/method/round cells are required; missing is never silently scored zero.

ARC SPECTRUM requires a genuine successful calibration recording. Collection/import
replay-verifies it. Failure blocks only its consumer; synthetic student corpora remain
unfiltered. Latest-checkpoint pruning is scoped to replaced new-lineage weights,
preserving raw artifacts and hashes. Changed identities use new output roots.

Return under `research/multidomain-20261027/returns/<actual-attempt-id>/`: exact
execution commit, environment/resource/attempt receipts, input/checkpoint hashes,
raw native outputs, replayed scores, all rounds/methods/failures, costs and remaining
prerequisites. Actual IDs come from native receipts. No remote LLM agent or GitHub
token is required on the GPU host. See [source inventory](evidence.json).
