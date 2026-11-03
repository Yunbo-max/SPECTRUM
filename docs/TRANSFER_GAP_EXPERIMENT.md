# Transfer Gap Experiment (2026-11-03)

Status: source delivered; no GPU, benchmark, software qualification run is
claimed. Independent branch and output root; do NOT resume old 10-round runs
with new source hashes. Uses unmodified learned-gain optimizer and ordinary SFT.

## Hypotheses and decisive observations

H1 (transfer gap): the current learned generator Q_r may improve correct
solution likelihood or development performance, but the merged native student
P_{r+1} loses some of that improvement. Contrast the three matched states:
P_r (pre_native), Q_r (pre_spectral), P_{r+1} (post_native).
Only when A(Q_r)>A(P_r) and A(P_{r+1})<A(Q_r) on held-out development tasks
can we say that the net observed loss is in the transfer stage.

H2 (correct-set redistribution): gains in Pass@1 could concentrate solved
questions while degrading low-success tasks or observed AST diversity.
Measure per-task 64-draw correct counts, Pass@1, Pass@64, AST C64 and
correct-count-matched D4. Pass@64 alone is NOT AST diversity.

Pre-registered diagnostic rounds: 1, 5, 8, 10. Additionally measure the
training-side reference NLL transfer gap at EVERY round. Only the
30 frozen MBPP validation tasks are used in these extra comparisons.
The 50 calibration tasks remain 40 fit / 10 guard and the 291 train tasks
produce the existing unfiltered SFT corpus. The 500 MBPP test tasks are
not used to select the method or diagnose hyperparameters; the original
complete test evaluation stays available for final reporting.

At a measured round, use 30 tasks x 64 samples x 3 states = 5,760 extra
completions. Four rounds require 23,040 extra completions, each up to
4,096 tokens. This is nontrivial GPU and isolated-code-evaluator cost.

## Metrics and mathematical commitments

A in [P_r,Q_r,P_{r+1}] is the *same native verifier* task-macro score.
For any A, report
    exploration_gain = A(Q_r)-A(P_r)
    student_transfer = A(P_{r+1})-A(Q_r)
    native_to_next = A(P_{r+1})-A(P_r)
The last equals the sum of the first two exactly for matched aggregate
definitions. Paired task bootstrap reports 95% intervals, conditional on
one training trajectory; with only 30 dev tasks, CIs may be wide.
Report each task's correct count, AST labels and D4 eligibility.
Do not compare D4 means when eligibility populations differ without
reporting the common-eligible task subset.

Reference NLL gap:
    G_fit=FitNLL(P_{r+1})-FitNLL(Q_r)
    G_guard=GuardNLL(P_{r+1})-GuardNLL(Q_r)
where Q_r is the EXACT chosen folded gain operator from the round's
learned_gains.json. P_{r+1} is measured after ordinary LoRA SFT,
using the same 40/10 references. These are training-side proxies,
not validation or verified success scores.

No theoretical claim that short-prefix KL (8 probes x <=128 tokens,
full vocabulary on native logits) bounds actual 4096-token generation,
top-p sampling, P_{r+1} dynamics, or multi-round correct AST richness.
Neither sparse success nor finite-sample nonobservation proves
support disappearance.

If H1 is confirmed, the NEXT research phase is a separately
pre-registered Gradient Alignment test: compare the reference gradient
and pre-update LoRA SFT gradient, and estimate whether the sign predicts
post-update reference NLL. This proposed P1 experiment is NOT
implemented or scored in this branch, and requires separate math and
backprop qualification. Do not mix a new training loss into this P0/H2 study.

## Commands

Use a separate checkout on the execution host, and do not change original
training source code in an existing checkout.

    git fetch origin research/spectrum-transfer-gap-20261103
    git worktree add ../SPECTRUM-transfer-gap origin/research/spectrum-transfer-gap-20261103
    cd ../SPECTRUM-transfer-gap
    python -m pip install -e '.[train,test,analysis]'
    docker pull python:3.11-slim
    docker info

Copy configs/spectrum_7b/transfer_gap_learned_4096.yaml to a host-local
configuration if the model path is different. Set a NEW output_dir.
Re-use the exact prepared MBPP291/50/30/500 splits; missing split
files must be prepared via the repository's pinned data command.

    python -m pytest tests/test_transfer_diagnostics.py tests/test_learned_gains.py tests/test_gain_pipeline.py tests/test_pipeline.py -q
    python -m improving.cli validate --config configs/spectrum_7b/transfer_gap_learned_4096.yaml
    python scripts/qualify_learned_gains.py --config configs/spectrum_7b/transfer_gap_learned_4096.yaml --output-dir runs/qualification/transfer_gap_learned_round1
    python -m improving.cli run --config configs/spectrum_7b/transfer_gap_learned_4096.yaml

Exact resume after a qualified interrupted stage (source/config/data must
remain identical):

    python -m improving.cli run --config configs/spectrum_7b/transfer_gap_learned_4096.yaml --resume

The source computes new P_r and Q_r development evidence *before* SFT,
seals each stage with its checkpoint identity and file hashes, then
after LoRA merge computes P_{r+1} and the reference NLL gap. It refuses
to reconstruct old pre-SFT states from a post-SFT checkpoint.
The final summaries live at
    runs/spectrum_transfer_gap_20261103/learned_7b_r10/spectral_learned/round_R/transfer_gap/report.json
and
    .../round_R/reference_transfer_nll.json

A read-only post-run summary (it verifies each saved report checksum against
the completed round receipt; no model, Docker or generation):

    python scripts/plan_transfer_gap.py
    python scripts/report_transfer_gap.py \
      --run-dir runs/spectrum_transfer_gap_20261103/learned_7b_r10

This outputs all ten rows, with uncompleted rounds marked missing. The
unmeasured development rounds still have reference-fit/guard NLL gaps.

## Interpretation rules and follow-up experiments

The MBPP500 results helped motivate this hypothesis in the historical work.
Therefore MBPP500 is NOT a newly untouched confirmation set for a redesigned
SPECTRUM 2. Design hyperparameters with the existing dev set, freeze the method
before new independent HumanEval+/APPS/LCB evaluations, and run independent
training seeds for stronger evidence. Development effects on 30 tasks are
exploratory and may be too noisy for effects of only a few percentage points.

Predeclared decision matrix:
- If pre_spectral > pre_native on native dev success metrics but post_native <
  pre_spectral, the *observed* gap is in spectral-to-student transfer.
- If pre_spectral is not better than pre_native, local fit-reference NLL is
  a weak generator-selection proxy; do not blame SFT without stronger evidence.
- If post_native > pre_spectral, do not claim a transfer problem; it may be
  student generalization rather than copying the intervention.
- If Pass@1 improves but AST-C64/D4 falls with stable common eligibility,
  study mode/correct-set concentration; don't mistake Pass@64 for AST richness.
- If any proposed comparison is non-inferior only on a changed eligibility
  subset, report raw per-task counts and the paired common-eligible cohort.

P1 (NOT implemented in this diagnostic): collect g_ref and g_SFT from the SAME
initial LoRA trainable coordinates at pre-SFT theta_r for rounds 1/5/8/10;
estimate alignment cos(g_ref,g_SFT) with frozen fit references and native/spectral
training completions. Compare gradient sign and predicted first-order change
against observed post-SFT fit/guard NLL. Repeat across 3 seeds. The
Adam/LoRA multi-step optimizer means Taylor prediction is diagnostic, NOT an
exact equality or theorem. Use fixed train-side inputs only for gradients.

P2 (ONLY if P0/P1 support the hypothesis): introduce Transfer-Aware Gains
with an auxiliary update-alignment term, while keeping the same reference
fit/guard and token budgets. Compare:
plain 4096, fixed tau with matched 40 reference examples, original learned,
learned with additional student-transfer guard, and isotropic/random gain
control. Hold out a fresh independent downstream benchmark for final evaluation.

## Safety and failure policies

Untrusted generated Python is executed only using an isolation-qualified
Docker/bwrap backend, not shared-host subprocess evaluation.
The report includes resource/time receipts for each of three states.
Full MBPP500 still runs after SFT under the original benchmark protocol.
Result rows are absent until real execution. Identity fallbacks and failed
rounds remain first-class outcomes.

No new code in this diagnostic changes generation gain fitting, LoRA SFT
sampling, correctness filtering, or method selection.
