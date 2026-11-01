# Source delivery review

Status: **generated_unexecuted**. This records source inspection, not executed
software tests, native model qualification or evidence of benchmark improvement.

The pre-code mathematical review and one-candidate selection are preserved in
`evidence/`. The user's selected scope is generation control for text SPECTRUM;
ordinary SFT is unchanged.

| Method requirement | Implementation | Source review finding |
|---|---|---|
| Recompute current-round geometry from fit references | `gain_pipeline.calibrate_learned_round`, existing `_calibrate` | Only fixed fit references construct the basis; guard and test labels are excluded |
| Full spectrum with tied degenerate eigenspaces | `learned_gains.spectral_groups`, `SpectralGainLinear` | No manually selected spectral bands; tied-coordinate gradients sum automatically |
| Freeze model/basis, learn signed gain utility | `_frozen_native`, `_fit_gradient` | Model parameters are frozen; activation residual is differentiable in gains, including preceding interventions |
| Finite box-constrained search | `fit_learned_operators` | Global gradient normalization, projected proposals and finite backtracking are explicit; no optimality claim |
| Native-to-candidate full-vocabulary KL | `forward_kl_sum`, `_probe_kl` | Same exact native prefixes; raw softmax, causally shifted response-only masks and token-mean KL |
| Final guard and deployment checks | `fit_learned_operators` | Final differentiable guard veto followed by actual folded fit/guard/KL checks; no iterative guard selection |
| Exact identity fallback and restoration | Core context managers and `run_experiment` | Identity selection bypasses folding; native weights are restored before ordinary SFT |
| Immutable continuation policy | `_load_artifact`, `validate_saved_learned_round` | Input/operator/audit hashes and settings bound; trained/completed resumes validate saved policy without refitting |

Independent math-to-code inspection by `spectrum_selective_sft_math` and
integration inspection by `learned_gain_core` identified and closed these issues:

- The final differentiable guard needed a finite-deterioration veto, in addition
  to the deployed folded guard check, to match the frozen mathematical method.
- A trained but not yet evaluated round needed file-only policy validation;
  it must not regenerate its probes or refit gains on the already trained student.
- Identity diagnostics must reflect actual folding bypass, rather than a
  hypothetical float32 identity multiplication.
- Loss of an operator artifact after its audit/provenance receipt exists must
  stop resumption even if training generation has not started.
- A new learned round after round one requires its immediate predecessor model;
  missing completion receipts plus pruned checkpoints cannot fall through to the
  base model while retaining a later-round model identity.

Authored regression sources cover calculus, eigenspace invariance, causal KL,
guard/fold rejection, state restoration, token identity and cache integrity.
They have **not been run**. AST parsing, shell syntax, YAML comparison and source
diff checks are static checks only; their delivery record is `static-checks.json`.

Remaining native work: execute the documented regressions, qualify the actual
7B calibration and 6144-token training memory, then compare native evaluation
across rounds. The small probe KL and reference CE cannot establish correctness,
diversity or recursive stability. A frequent identity fallback is a result to
report, not permission to suppress rounds or relax constraints retrospectively.
