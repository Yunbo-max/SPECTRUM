# Full-spectrum learned gains: mathematical specification

Candidate: `spectrum-learned-gains-v1`. Parent source:
`b8bcc68f87a2a216ac048bc7fb36365c2002e8b0`.
Scope: the user-selected text SPECTRUM generation intervention only. This is a
mathematical construction awaiting independent review and native qualification,
not a claim of novelty, convergence, benchmark improvement or recursive stability.
No code, tests, model inference or scientific evaluation accompanies this card.

The user's exact implementation request was “你觉得这个好的话请你更新下code我来测试”.
It followed the objection to artificial two/three spectral groups and the
discussion of full-spectrum learned gains. This is one specified candidate,
not an open discovery search; the evidence batch therefore targets one candidate
and one selection. No additional candidates are invented to fill a quota.

## Data, model and intervention

At round r, theta_r is the current native student, with previous adapters merged
as required by the existing pipeline. The existing 50 calibration references are
retained in their recorded input order: first 40 are `fit`, last 10 are `guard`.
Store task IDs, content hashes and exact tokenized inputs. Reject missing,
duplicate, overlapping or truncated references rather than silently reducing the
split. These are training-side references, never benchmark evaluation labels.
The guard set is held out from gain fitting and covariance construction; it is
not a fresh scientific test set, particularly when reused across rounds.

For each fit example e, let L_e be mean selected completion next-token NLL,
with prompt/padding labels excluded. At each existing selected pre-RoPE,
pre-key-normalization K/V projection m, collect the gradient rows at every
nonpadding position, including prompt positions influenced by completion loss:

    g_e,t,m = d L_e / d h_e,t,m
    C_r,m = (1 / N_m) sum_e sum_t g_e,t,m^T g_e,t,m
    C_r,m = U_r,m diag(lambda_r,m) U_r,m^T.

N_m counts all nonpadding projection positions. This preserves the existing
per-example loss normalization and uncentered gradient-second-moment estimator.
C is not a raw-data covariance, a centered covariance or a parameter Hessian.
Only the fit references construct C. Recompute it on theta_r every round.

Learn full-spectrum gains a_m with positive configured floor a_min < 1:

    T_m(a_m) = U_m diag(a_m) U_m^T,
    a_min <= a_m,i <= 1,
    h'_m = h_m T_m                     [row-vector convention].

theta_r and U_m remain frozen throughout fitting. All gain-to-output paths stay
differentiable. Gains are shared over tokens at a module, not learned per token.
No artificial top/middle/tail bins, low-rank cut or spectral entropy gate is used.
Equal-eigenvalue eigenspaces receive one shared gain, including the full null
eigenspace: unequal gains there would depend on an arbitrary eigenvector basis.
The implementation must record a numerical eigenvalue-tie tolerance applied to
lambda/lambda_max and its resulting equivalence classes. Tying nearly equal eigenvalues is an explicit
numerical approximation, not an exact invariance theorem for distinct values.
Independent gains need not increase with eigenvalue and need not preserve the
largest-eigenvalue direction at gain 1. Those are deliberately not claimed.

Because U is orthogonal and a_min > 0, T is symmetric positive definite and
nonexpansive in activation Euclidean norm. This does not imply that the whole
transformer, logits, correct-answer probability or recursive training is
nonexpansive. Exactly a=1 recovers identity and the native model.

## Actual empirical objective

Use the first eight valid, distinct training prompts in the recorded train order,
with no reference-answer or correctness fields passed to probing. Generate one
native completion per prompt, at most 128 new tokens, before applying any T.
Use the declared ordinary native generation decoder and record its configuration,
model/tokenizer identities, stopping reason and exact prompt/completion token IDs.
The eight/128 default is a bounded development probe, not coverage of all tasks
or long-generation states. Prefixes are frozen for this round; do not regenerate
them while optimizing gains or decode/re-tokenize the stored continuation.

Let B_r contain the next-token prediction prefixes for those generated token
positions, excluding padding and prompt-only prediction positions. Both models
are evaluated on precisely the same stored prefixes, with no sampling derivative.
Use full-vocabulary softmax of raw model logits, not temperature/top-p-renormalized
decoder probabilities, for the following forward KL:

    F_r(a) = (1/40) sum_e mean_selected_token_NLL_e(theta_r, T(a))
    K_r(a) = (1/|B_r|) sum_h sum_v p_native(v|h)
                          * [log p_native(v|h) - log p_a(v|h)]
    minimize_a F_r(a), subject to K_r(a) <= delta and a in A.

A is the gain box intersected with equal-eigenspace tying constraints. Native
probabilities are detached; every K evaluation includes all selected modules
jointly. Recompute native logits per example as needed and release them, rather
than caching full-vocabulary logits for the whole probe corpus. Native and steered logits must be finite. Log-softmax/KL arithmetic must
be at least float32; materially negative KL is a numerical failure, not credit.
delta is a configured per-token KL budget, not a fitted result or a diversity
guarantee. Identity has K=0 and is feasible. On finite inputs and continuous
ideal-arithmetic model operations, compact A and continuity yield existence of
an optimum; this gives no convexity or guarantee that a practical solver finds it.

For column notation h'_t=T h_t the signed derivative at an intervention is

    d F / d a_m,i = sum_t (u_m,i^T h_t) * (u_m,i^T grad_h'_t F).

The sum also includes examples and all occurrences sharing that gain. It is the
direct local chain-rule contribution; dependencies through preceding interventions
must remain in the graph. Unlike squared gradient energies, this derivative can
distinguish helpful from harmful shrinkage on the fitted references.

## Bounded solver and acceptance

Implement a finite projected-gradient line search, not an exact optimizer:

Represent the gains as a=B b, where each column of B indicates exactly one
equal-eigenvalue eigenspace, not a hand-chosen spectral band. Each component of b
is one shared gain; grad_b F=B^T grad_a F sums the direction gradients in that
eigenspace. The optimizer uses these reduced coordinates, whose Euclidean metric
differs from projecting a gradient step in the expanded a coordinates.

1. Start at b=1 (hence a=1); store the native fit/guard losses and exact probe IDs.
2. Compute grad_b F at the current feasible b with model/U frozen. An optional
   common max-absolute gradient normalization is only a scalar step-size rescaling,
   not independent coordinate clipping or a Fisher preconditioner.
3. For a finite decreasing list of step sizes eta, propose
   b_try=clip(b - eta grad_b F, a_min, 1), then a_try=B b_try.
   Recompute actual F(a_try) and K(a_try) on all frozen inputs.
4. Accept only a finite candidate that improves current fit CE beyond a recorded
   numerical improvement tolerance and satisfies the declared KL budget. Stop if
   none is accepted, the projected direction is zero, or the configured finite
   iteration budget is exhausted. Keep all proposal/accept/reject diagnostics.
5. Inspect guard CE once for the final fit-selected candidate. If its mean
   completion NLL exceeds native guard NLL by more than the declared tolerance,
   return identity. Do not use the guard to choose iterations, step sizes, gains
   or alternative candidates. A fallback is an observed controller decision,
   not a failed task score or permission to omit the round.

Projecting a gradient proposal is mathematically different from elementwise
clipping a supposed full-Fisher optimal solution. No Fisher inverse, approximate
KL bound, KKT certificate or convergence claim is used by this solver. Each
accepted iterate is empirically feasible only on the finite recorded probe and
under its measured arithmetic. The guard is a developmental veto, not a
statistical confidence statement or a correctness oracle. Keep identity if no
candidate passes. Invalid data/model/topology cannot be disguised as a successful
identity calibration; report an explicit blocked/error state.

## Folding, generation and ordinary SFT

The existing generator temporarily folds T into each native Linear:

    W_fold = T^T W,    b_fold = T^T b.

This equals h -> h T in exact arithmetic at the same pre-RoPE site. In production,
the existing fold computes float32 products and casts to the original dtype,
normally BF16. Differentiable activation multiplication and folded forward need
not produce the same outputs. Before training-data generation, evaluate the
actual folded model on the complete fit, guard and frozen prefix probe; record
folded-versus-activation fit-CE differences and native-relative probe-KL
differences, together with the actual folded fit/guard losses and probe KL.
No uncomputed logit-discrepancy metric is implied. Retain
the operator only if actual folded KL is within budget, actual folded fit CE
retains the declared improvement over native, and actual folded guard CE is
within its native-relative tolerance. Otherwise restore native weights exactly
and return identity with a specific fallback reason. Nonfinite results reject
the candidate. Identity fallback should bypass transformation arithmetic rather
than numerically fold a reconstructed U U^T matrix.

Use the accepted folded operator only for generation. Restore original parameters
exactly before LoRA SFT and native evaluation, even on exceptions. Keep all raw
generated records under the existing training policy. Ordinary SFT loss, labels,
LoRA settings, epoch/token budget, generation decoding and benchmark scorer are
unchanged. In particular, the previously discussed weighted/selected-step SFT is
NOT part of this candidate. Do not add calibration reference replay to SFT.

## Predictions, comparisons and limits

The exact scale counterexample motivates replacing the old entropy signal:
if C_r=c C_1 for c>0, both normalized C and spectral entropy are unchanged, so
the old entropy gate cannot respond to that change. A conjugate rotation also
preserves eigenvalue entropy while changing T's action in activation coordinates.
These show insufficient identification by entropy, not the measured cause of
the user's reported adaptive underperformance or proof decay must improve.

The new calibration uses signed reference response and actual output KL, so
rounds with unchanged entropy can receive different interventions. Finite-probe
KL compliance, fit/guard behavior, gains, identity fallbacks and fold drift are
directly observable implementation predictions. Benchmark improvement and slower
recursive degradation remain hypotheses. A completed ten-round comparison with
no native-score benefit, excessive identity fallbacks, or unacceptable calibration
cost can refute the practical advantage; do not redefine success as lower fit CE.

For the first developmental test retain fixed-tau, entropy-adaptive and current
decay outputs and compare the new arm with the unchanged native benchmark/scorer,
initial checkpoint, training split, generation/SFT budgets and one training
trajectory per arm. This is not a temperature or training-seed sweep. Account
separately for the new probe and calibration cost. Fair isolation additionally
requires controls using the same 40 fit references for their basis; old 50-ref
curves alone cannot attribute a difference solely to the gain-selection rule.
All arms' calibration information access must be disclosed. This card is not a
frozen complete experiment protocol or authorization to execute it.

Closest sources and their coverage are retained in `evidence/source-screen.json`.
Full-spectrum coefficient learning, reference-based fitting and KL constraints
are established general ideas. The deliverable is a specific adaptation for the
existing recursive generation pipeline, with no priority/first-method claim.
