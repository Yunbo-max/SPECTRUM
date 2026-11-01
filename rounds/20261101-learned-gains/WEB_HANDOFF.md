# Web → Local: full-spectrum learned gains

Parent source: `b8bcc68f87a2a216ac048bc7fb36365c2002e8b0`.
The delivery receipt supplies the new immutable commit; the parent is not the
revision to execute. Status: **generated_unexecuted**. No project tests, model
loading, inference, training or native scoring were run by Web.

Read [AGENTS](../../AGENTS.md), [current Local runbook](../../LOCAL_AGENT_RUNBOOK.md),
then the [complete Chinese command and acceptance guide](../../docs/SPECTRUM_LEARNED_GAINS_ZH.md),
including its [model/data acquisition](../../docs/SPECTRUM_LEARNED_GAINS_ZH.md#下载数据和模型).
The selected method's derivation and limitations are in [METHOD](METHOD.md).

## User-selected scope

The user approved implementation of the just-discussed continuous learned spectral
gain controller, rejecting arbitrary two/three spectral bins. This is one selected
method, not authorization to launch a new method search or a GPU sweep.

New method: `spectral_learned`. Each round recomputes reference-gradient geometry
on the current model, learns bounded non-expansive spectral gains with real output
KL checks, and retains identity as a feasible fallback. Equal eigenvalues share
gains by recorded numerical tolerances. Model weights and the current eigenspace
are frozen during gain learning. The actual folded BF16 operators are checked
before generation, then native weights are restored before ordinary LoRA SFT.

This delivery does not implement step-weighted SFT. The purpose is to isolate the
new generator control before changing what the student learns from each token.
It does not change the GUI branch, math/QA/ARC protocols, legacy fixed/decay/adaptive
methods or archived outputs.

## Inputs and fairness

Qwen2.5-Coder-7B-Instruct and the existing MBPP291/50/30/500 split; ten rounds,
16 raw training completions per question, 64 evaluation completions, 4096 generated
tokens and 6144 total SFT tokens. Decoding and LoRA settings otherwise follow the
existing 4096 protocol. No generated answer is checked for correctness to select
training data. The fixed references still provide supervision.

The same 50 reference answers are deterministically split into 40 fit and 10 guard.
Only fit references construct the eigenspace and provide optimizer gradients;
guard is a final-only veto, never an iterative optimizer or candidate-selection
signal: both the final differentiable-activation candidate and its actual folded
policy must pass, otherwise identity is returned without choosing another iterate.
It is not an independent test set. Eight
native training-prompt probes with at most 128 generated tokens measure forward
KL on the recorded prefixes. They neither use training reference answers nor
provide SFT examples. KL is computed from full-vocabulary raw-logit softmax before
temperature/top-p/top-k decoding. A finite probe KL bound is neither a bound on
the post-truncation decoder nor a global rollout guarantee.

Original controllers use all 50 anchors by default. A separate opt-in
`spectrum_7b_r10_spectral_4096_tau06_anchor40.yaml` control matches the fit subset;
it does not replace the old 50-anchor baseline or run automatically. Report this
information-allocation difference and extra calibration compute in comparisons.

## Ordered Local actions

1. Restore actual execution host, native code environment, GPU allocation, complete
   model/data fingerprints, live processes and finite authorized budget. Preserve
   live sealed jobs at their original revision and use a separate checkout.
2. Run the guide's authored new/legacy regression checks and validate the config.
   These are pending commands, not Web test results.
3. Run `scripts/qualify_learned_gains.py` with the real model and all intended
   fit/guard/probe inputs. Inspect final folded-path constraints, exact identities,
   exception restoration, peak memory and stage resources. A valid identity
   fallback is not a demonstrated method improvement or a software failure.
4. Qualify 6144-token LoRA training capacity separately. Calibration acceptance
   does not establish SFT capacity. Do not silently shorten or drop completions.
5. Explicitly launch `scripts/run_spectrum_learned_4096.sh` after those prerequisites.
   The launcher runs one arm in the foreground; it does not submit a cloud job.
6. Return the small JSON review bundle using `scripts/collect_learned_gains.py`,
   plus actual command/commit/config/environment and failed or unfinished stages.
   The guide gives exact argv and output paths.

Implementation files: [learned-gain solver](../../src/improving/learned_gains.py),
[pipeline](../../src/improving/pipeline.py),
[configuration](../../configs/spectrum_7b/spectrum_7b_r10_learned_4096.yaml),
[launcher](../../scripts/run_spectrum_learned_4096.sh).
Local software acceptance: [solver tests](../../tests/test_learned_gains.py),
[pipeline tests](../../tests/test_gain_pipeline.py) and the linked guide's retained
spectral/calibration/length/pipeline regression checks.

## Interpretation and pending evidence

The source implements a finite projected search with explicit empirical acceptance
checks, not an exact global solution or a proof of recursive improvement. The
reference NLL and KL are optimization proxies. Small output KL does not guarantee
correctness, retained correct-implementation coverage or stability outside probe
prefixes. Learnable spectral coefficients and KL-controlled intervention have
prior art; no priority claim follows from this implementation.

The user's reported ordering decay > adaptive > fixed is a hypothesis-generating
observation. The parent repository did not contain the corresponding latest raw
comparison packet. Preserve those runs and their identities; do not relabel them
as newly verified evidence for this controller.

Look for changes in native pass@1/pass@64 and correct-implementation coverage across
all rounds, alongside length/repetition/truncation, operator gains, fit/guard NLL,
probe KL, identity fallback frequency and calibration cost. If gains move almost
uniformly or a calibrated scalar/decay control performs equally well, the extra
direction-level freedom has not established value. Retain negative outcomes and
return one coherent packet before expanding the method or changing the loss.
