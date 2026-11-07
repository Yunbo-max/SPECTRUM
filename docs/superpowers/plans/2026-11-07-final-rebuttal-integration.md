# SPECTRUM final rebuttal integration plan

> For agentic workers: continue the approved specture2 authoring task. This is
> repository integration and repair, with Web source review; Local execution
> remains pending. Do not run research code or tests from the Web controller.

**Goal:** Deliver one reviewer-mapped, independently launchable experiment catalog
to `Yunbo-max/SPECTRUM/main`, preserving existing runs and the separate ten-round
expansion queue.

**Architecture:** Integrate the more complete c00–c36 branch into current main,
retain its stable case IDs, and append the missing matched learned-gain controls.
One writer publishes; independent reviewers inspect mapping, runtime contracts
and evidence. Frozen manifests bind source/config/data and every case has its own
logs, checkpoint root and native completion checks.

**Tech stack:** Existing Python/PyTorch/PEFT code, JSON/YAML configurations,
native MBPP verifier and EvalPlus 0.3.1 through the existing bubblewrap boundary.

**Spec:** User's 7 November request to finish specture2, map every reviewer issue,
complete isolated case code, update GitHub and return the plan for confirmation;
the prior case specs and learned-gains METHOD.md remain the scientific sources.

## Global constraints

- Original-paper protocol: 1.5B, five rounds, 512 output tokens, 16 train draws,
  64 eval draws, MBPP291/50/30/500; independent paired lineages 43/44/45.
- Learned extension: 7B, ten rounds, 4096 output tokens, ordinary LoRA SFT.
  Learned spectral gains are neither token loss weights nor learned LoRA scales.
- No correctness filtering, external teacher, held-out tuning, synthetic benchmark
  substitution or fabricated passed-test/result receipts.
- Preserve historical outputs, failures and unfinished tasks at original revisions.
- New commands use native scoring and execute only on explicit Local dispatch.
- Publish complete source/design to main after source review and exact readback.

## Review focus

- Source-specific ablations must reject mismatched tau/ref counts/decoder settings.
- Separate methods and source-checkpoint evaluations must never share writable roots.
- A completion marker alone cannot replace exact native samples and file hashes.
- Longer learned protocols must not be compared directly with 512-token baselines.
- Human annotation preparation and historical audit must never become new results.

## Tasks

- [x] Recover current main, both unfinished case branches, historical audit and math.
- [x] Merge the c00–c36 lineage while preserving main's 72-case expansion queue.
- [x] Repair source/data sealing, native backend, execution logs and result checks.
- [x] Add individually launchable 7B learned/fixed/decay/adaptive controls and fair replay.
- [x] Retain three-state diagnostics and effective operator/cost diagnostics.
- [x] Complete reviewer map, honest response draft, download/run/collect guide.
- [x] Independently source-review integration; keep actual Local tests pending.
- [ ] Publish to main with expected-parent protection and exact-commit readback.

Planned Local checks are listed in the final runbook. No checkmark in this plan
is evidence of GPU execution, software acceptance or scientific effectiveness.
