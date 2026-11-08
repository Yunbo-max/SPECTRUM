# Continual calibration in spectral-gain coordinates

Status: design and source preparation; generated_unexecuted.
Design parent: 44154a2ec882ea2b32c3d26203fae724ec15d6fb (main, 8 November 2026).
Publication parent: 2c5fac3d030abd6afc189a9de57aa19e29eb6411; retain its
independent rebuttal-plan inspection repair without changing the selected method.
The owner explicitly selected the existing discussion's CGL-inspired new/old
task conflict mechanism and requested code for testing. This is one bounded
extension of Learned SPECTRUM, not a new open-ended discovery search. Diffusion
and random parameter populations are excluded from this implementation.

## Object and information access

Use the existing K/V output intervention T_m = U_m diag(a_m) U_m^T. Tie only
numerically equal eigenspaces, as in the parent Learned solver. Optimize the
reduced shared-gain coordinates b. Within each experiment lineage, estimate U
once on the first domain's FIT references and freeze it for the whole sequence.
Never construct the initial geometry from future-domain labels. Retain and
inherit one shared b; do not switch to independent domain adapters or silently
reset b at domain changes. The backbone and U are frozen during every gain fit.

Current training-side calibration files supply FIT/guard splits (54/10 in the
existing math/QA configs). Keep seen-domain FIT references as declared memory;
they supply old-task gradients and endpoint constraints, never student SFT data.
Guard examples only veto the final selected candidate; they never supply a
gradient, choose a step or select another candidate. Evaluation labels never
enter fitting, geometry, candidate selection, or the replay memory.

This is a historical-calibration-memory setting. CGL itself computes SFT/GRPO
gradients on current-task data under a different no-history protocol; we borrow
conditional conflict handling, not its exact objectives or its data-access claim.

## Selected construction

At one calibration call, F(b) is current-domain mean per-example completion NLL,
R_j(b) is the same loss on old-domain j's FIT memory. Compute all gradients at
the same b, current backbone and fixed U. For a proposed descent step
d0 = -eta grad F / max(abs(grad F)), the conflict arm approximately projects d0
onto the intersection of g_j^T d <= 0 for each old domain and
a_min - b <= d <= 1 - b. Use bounded Dykstra projection and explicitly verify
feasibility; never claim an exact quadratic-program solution or convergence.
Ignore exactly zero old gradients in direction projection, but not in endpoint
checks. Project in the actual reduced gain coordinates, not activation or LoRA
gradient coordinates. Recheck the actual cast/boxed step, since clipping alone
can reintroduce conflicts.

For one unconstrained old domain with g_old dot g_new < 0, this reduces to
g_safe = g_new - (g_new dot g_old)/(g_old dot g_old) g_old. For several old domains,
one pass of pairwise projection is insufficient; check every inequality.

Accept a finite candidate only if current FIT improves, each required old-domain
NLL stays under its recorded limit, and full-vocabulary forward KL from the
INCOMING controlled policy to the candidate stays within the declared budget
on fixed native-generated training prefixes. This incoming-policy KL differs
from the parent identity-anchored round-local experiment and makes the inherited
controller feasible at the start of a new domain. Do not call the new naive arm
an unchanged reproduction of the old round-local Learned algorithm.

Recheck the final candidate through the actual weight-folding path, including
current FIT/guard, every old-domain NLL and incoming-policy KL. On rejection,
restore the incoming gains exactly; identity fallback would erase inherited
control. Invalid inputs or runtime exceptions remain errors. Save every rejected
step, conflict statistic, projection residual, loss limit and fallback reason.

## What the constraints mean

Taylor expansion gives R_j(b+d) = R_j(b) + g_j^T d + O(||d||^2); direction
feasibility is only first order. Endpoint checks are needed even when old
gradients vanish, as at a KL anchor or a local optimum. Finite calibration
constraints do not guarantee test accuracy, useful diversity or absence of
backbone forgetting.

Two explicit protocols use the same controller and native scorers:

* frozen: no student update; inherited a is the only learned state. Old-domain
  limits are fixed at that domain's exit, plus a declared tolerance, not reset
  per optimizer step. This directly tests controller interference.
* self_distill: generate current-domain data using T, restore native weights,
  then ordinary unweighted LoRA SFT on all raw generated records. Inherit the
  student and shared a. Because SFT may already change old-task losses, retention
  limits are measured at each calibration entry on the CURRENT backbone and
  incoming a. They bound the additional effect of gain calibration only; they
  are not a lifelong or post-SFT no-forgetting guarantee. Report all-domain
  native and controlled generation after each stage.

## Comparisons and falsification

Four independently launched/saved arms: native (a=1), sequential (warm-start
current-domain fitting), retention (same fitting plus endpoint old-domain
constraints), conflict (same constraints plus direction projection). Match
geometry source, references, decoder, gain budget, SFT settings and evaluation.
Compare math->QA and QA->math to expose first-domain geometry/order dependence.
Existing prepared MATH500 and MMLU-Pro splits and scorers are reused in full;
development subsets do not replace the final populations.
Evaluation uses the same task/sample random streams across stages and methods:
the generation sampler's evaluation round index is fixed at zero, while actual
stage and policy identities remain in directories and sealed receipts. This
avoids adding a new evaluation randomization merely because a frozen backbone
advanced to the next calibration stage. Synthesis and probe generation retain
their declared stage identities. It is not an independent-seed repeat.

The mechanism fails to add practical value if conflict projection improves only
FIT loss or its diagnostic cosine, adds substantial cost without controlled
generation gains, or cannot outperform retention-only checking at the same
declared budget. Student effects and controller effects are separate outcomes.
No experimental improvement is asserted by this source delivery.

## Sources already read for the selected extension

* CGL v2, sections 3 and 5.3: https://arxiv.org/html/2603.02951v2
* Existing method: rounds/20261101-learned-gains/METHOD.md
* Existing gain, text data, generation, folding, SFT and scoring implementations.
* Diffusion literature was discussed but is not part of this implementation.

## Source interfaces

The new core is separate from learned_gains.py. It provides build_gain_geometry,
identity_gain_state, operators_from_gain_state, and fit_continual_operators.
The fit returns (operators, selected_gain_state, audit), accepts explicit old
FIT batches and optional absolute per-domain loss limits, and supports modes
sequential/retention/conflict. The orchestration pins geometry/state/input hashes
and writes independent stage receipts, inherited student checkpoints, evaluation
records and a complete cross-stage report.
