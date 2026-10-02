# SPECTRUM final validation implementation plan

**Goal:** provide one finite, reproducible experiment release for the existing
SPECTRUM method, with explicit model/data identities and no automatic search.

**Architecture:** retain the audited `improving` generator/calibration/LoRA
pipeline. A new release planner seals prepared data, source files, model revisions,
private randomization, and a finite job graph. A separate reporter reads sealed
artifacts without executing programs or selecting favorable outcomes.

**Authorization and scope:** the user requested implementation and publication to
`Yunbo-max/SPECTRUM`. No GPU experiment, benchmark, weight download, dependency
installation, or candidate-code execution is part of this development session.
The historical request for code without tests is honored: add regression tests,
perform syntax/source/configuration review, and distinguish that from executed tests.

## Design decisions

- Preserve SPECTRUM: tau=1, fixed reference examples, current-model K/V loss
  geometry, temporary full-rank modulation, restored native weights, unfiltered
  single-LoRA SFT, and native inference.
- Main comparisons: Vanilla SD, SSD decoding-recipe adaptation, SPECTRUM.
  Projection remains a design control. Never label Vanilla SD as SSD.
- MBPP trains all students; HumanEval+, APPS Intro, CodeContests and a fixed
  LiveCodeBench snapshot evaluate frozen transfer. No target-test tuning.
- Train Qwen2.5-Coder 1.5B/3B/7B and DeepSeek-Coder 6.7B, rather than presenting
  initial-model-only scores as cross-model validation of SPECTRUM.
- Main 1.5B trajectory uses three independent training replicates; scale uses
  one per additional backbone. Numeric randomization values stay in ignored
  local run manifests; public report tables use replicate labels.
- Every round uses the same native decoder and 64 evaluation samples. Each
  synthesized corpus has 291 prompts x 16 completions. No verifier sees the
  training path.
- Fixed geometry, random orientation, isotropic attenuation and projection
  compare five-round endpoints. A separate five-round token-budget block
  preserves every record and matches supervised token exposures, within one
  whole-record overshoot; it does not claim equal FLOPs or wall time.
- Strength and loss-scope diagnostics are predeclared one-round comparisons,
  never retrospectively promoted into the main method.
- Completion is determined by the job graph, not effect sign or significance.

## Tasks

1. **Audit evidence and related work.** Record historical positive/mixed results,
   source commit, unresolved necessity tests and permitted claims. Do not label
   retrospective evidence as prospective confirmation or certify an exhaustive
   novelty search.
2. **Pin assets and preparation.** Add `configs/final/assets.json` and
   `scripts/prepare_final_data.py`; verify exact splits, deterministic population
   selection, provenance and overlap checks. Add test source for revision/count
   rejection and date windows.
3. **Complete core controls.** Persist fixed operators across rounds; add a
   whole-record token-budget exposure scheduler with explicit token accounting.
   Add test source for restoration, local operator bounds, corpus retention and
   budget overshoot.
4. **Seal a finite plan.** Add `scripts/run_release_study.py`: private seed setup,
   plan/status/run/report, source/data/config identity, per-job locks, strict
   dependency checks, resume and execution ledger. Source imports during planning
   must not load a model. Add test source for changed assets, missing dependencies,
   job budgets and duplicate jobs.
5. **Report all endpoints.** Add `scripts/report_release_study.py`: compare paired
   tasks on common eligibility, keep model/block/replicate identities separate,
   show missing cells and all signs, summarize resources and generator/student
   transmission. No pseudo-replication over shared tasks.
6. **Review and publish.** Parse Python and configuration syntax, inspect all
   integration paths, independently review the changed release, and push to the
   named empty repository. No benchmark performance is claimed by this release.

## Review focus

Missing/changed data must fail before loading weights; replay must not duplicate
completed stages; model identities must not be hard-coded to 1.5B; control blocks
must not be pooled with main results; a missing or failing evaluator must not be
reported as a zero model score. Public reports must not expose private numeric
randomization values.
