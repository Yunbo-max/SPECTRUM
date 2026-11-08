# Continual-gain source review

Scope: the owner's selected extension of generation-time spectral gains to a
sequential Math/QA study. This is source preparation and independent source
review, not executed software acceptance or scientific validation.

## Design obligations

| Area | Reviewed obligation | Evidence type |
|---|---|---|
| Gain coordinates | Same frozen first-domain FIT geometry, tied equal eigenspaces, one inherited reduced gain vector | Method contract and core source |
| Conflict direction | New/old gradients at the same current model and gain state; all old halfspaces and box constraints | Core and authored analytic fixtures |
| Finite steps | Cast-step feasibility plus every old-domain endpoint loss, not just a gradient cosine or mean old loss | Core source and authored counterexamples |
| KL and guard | Incoming actual-folded policy anchors full-vocabulary KL; guard is final-veto only | Core and authored independent KL check |
| Recovery | Exact incoming gains on veto, exact native modules/weights/flags on exceptions | Core and authored restoration fixtures |
| Information access | Old FIT references are explicit memory; no future labels in geometry; no guard/eval gradients | Design, configuration and runner review |
| Student behavior | All raw current-domain samples, ordinary LoRA SFT after native restoration; no gradient surgery on student parameters | Existing training path and new orchestration |
| Isolation | Sixteen fixed wrappers, immutable per-case inputs/source plans, separate outputs, attempts and process locks | CLI source and authored contract tests |
| Sequential state | Persist U/a, distinguish fixed exit limits from current-student entry limits, committed checkpoint reuse | Runner source and authored interruption contracts |
| Evaluation | Complete native populations, common evaluation random streams, native and controlled policies per domain/stage | Runner/source contracts; no scores produced |

## Review findings and qualifications

- CGL's conditional SFT/GRPO conflict rule is an inspiration. This implementation
  explicitly uses historical reference memory and gain-space constraints; it does
  not inherit CGL's no-history information-access claim or demonstrate novelty of
  gradient projection itself.
- A per-domain gain reset or a new eigenbasis at each domain would not preserve
  the selected shared-coordinate object. The fixed first-domain basis and reverse
  order comparison make this assumption visible.
- Multiple halfspaces and box clipping must be handled jointly. Finite Dykstra
  iterations and explicit residuals are used; convergence/exact projection is not
  asserted. A zero old gradient still receives an actual endpoint loss check.
- The fold path can differ numerically from differentiable activation wrappers.
  Both are checked, and selected native parameters are restored before SFT.
- A nonidentity incoming controller is not necessarily inside a native-policy KL
  ball. The new KL anchor is the incoming controlled policy, stated in the method,
  audit and guide; the naive sequential arm is correspondingly a new baseline.
- Strict float32 cast feasibility at normalized tolerance 1e-10 can reject updates.
  Rejection/cast statistics and incoming fallback are explicit. Actual acceptance
  rates need Local measurements; source review does not justify silently relaxing
  the predeclared tolerance.
- Frozen-backbone limits persist from domain exit. In self_distillation, SFT can
  move old-task performance before the next calibration, so the entry-relative
  controller constraint is not a lifelong or post-SFT retention guarantee.
- Equal step/backtracking limits are not equal compute: conflict computes old
  gradients. Report actual resource receipts and compare against retention-only.
- The original local math scorer remains local. No new sandbox qualification,
  native memory capacity, successful data/model acquisition or benchmark result
  is claimed by this delivery.

## Cross-review repairs included

The core, CLI/configuration and stage orchestration received independent source
review, followed by root readback. The completed-stage path reconstructs the
same evaluation binding used by execution, including the selected gains,
geometry receipt, checkpoint, task files, decoder, private seed digest and common
evaluation sampling round. It cannot adopt another controller's evaluation solely
because the native student checkpoint matches.

Checkpoint recovery verifies the raw corpus, synthesis receipt and its inventory,
effective training recipe, model files and both copies of training statistics.
The two statistics files can use different JSON formatting: each has its own
byte hash and their parsed content must agree. A committed student with unfinished
evaluation skips controller fitting, corpus generation and SFT. The corresponding
authored test exercises the actual stage branch, with these operations forbidden.

Reference diagnostics restore each module's train/eval flag separately. Merged
controller overrides are fully validated before model loading/calibration. The
report path uses the same metadata-only controller/evaluation binding helpers as
execution, and distinguishes absent, incomplete and fully committed trajectories.

The only main-branch advance during integration was retained by fast-forward:
`2c5fac3d030abd6afc189a9de57aa19e29eb6411`, repairing an independent rebuttal-plan
inspection. This change does not overwrite or renumber the old study catalogs.
No remaining blocking mismatch was found in this source review; runtime behavior
and actual numerical rejection rates remain unverified.

## Local checks pending

New authored tests:

```bash
python -m pytest -q tests/test_continual_gains.py tests/test_continual_gain_study.py tests/test_continual_gain_cases.py
```

Relevant original regression checks for the reused gain, fold, raw-generation,
text-data and ordinary training boundaries:

```bash
python -m pytest -q tests/test_learned_gains.py tests/test_gain_pipeline.py tests/test_spectral.py tests/test_generation.py tests/test_training.py tests/test_text_contracts.py tests/test_text_learned.py
```

These commands have **not** been run by Web. Toy logits and fake artifact bytes
in software fixtures cannot substitute for the real 7B fold/gradient/KL/checkpoint
and full native scoring qualification required by the Local handoff.

## Inspection disclosure

The final source-only inspection is recorded separately in
[SOURCE_INSPECTION.json](SOURCE_INSPECTION.json). It uses stdlib parsing, literal
configuration comparisons, link/file inventory checks and Git whitespace/diff
inspection. It does not import or execute project modules, run pytest, download
scientific inputs, load a model, train, generate responses or score a benchmark.
Independent code review is also source-level evidence only.

The delivered commit is identified in the publication response after exact
GitHub main/file readback. That source publication is distinct from experimental
completion; all new native experiments remain pending.
