# SPECTRUM — ICLR 2027 point-by-point response draft

**Submission:** 45902. **Reviewers:** w3G2, FUKc, ygkV. **Prepared:** 2026-11-07.

**Status: author-review draft with pending evidence slots. This document has not been submitted to OpenReview. Creating case specifications or diagnostic code does not constitute a completed experiment.**

## Review provenance and the scope of completeness

The issue labels W1–W3, F1–F6, and Y1–Y9 below reproduce the **18 concern summaries recorded in the repository**, not verbatim reviewer quotations. The source is [`reviewer_case_mapping.json`](../experiments/iclr2027_rebuttal/reviewer_case_mapping.json), originating in commit `d033641`. Complete original reviews and their OpenReview note identifiers were not recovered during this continuation. The wording and subdivision of every original question must therefore be checked against the original reviews before submission. Coverage of these 18 recorded issues must not be described as independently verified completeness of the original reviews.

The execution catalog is [`cases.json`](../experiments/iclr2027_rebuttal/cases.json). Preserve the meanings of c00–c36 from `d033641`; c37–c47 extend that catalog, bringing it to 48 case identities. These identities include audits, frozen evaluations, annotation preparation, and training; they are not 48 completed training trajectories. A different, 27-case branch at `6f4d2a0` reused many of the same identifiers for different experiments. Its identifiers are not interchangeable with this document's identifiers.

Source records used for this draft:

- [`reviewer_case_mapping.json`](../experiments/iclr2027_rebuttal/reviewer_case_mapping.json): concern summaries and initial case associations.
- [`cases.json`](../experiments/iclr2027_rebuttal/cases.json): current case identities, protocol parameters, and historical inventory labels.
- [`REBUTTAL_GAPS.md`](../research/audit-20261107/REBUTTAL_GAPS.md), [`SOURCE_PATHS.md`](../research/audit-20261107/SOURCE_PATHS.md), and [`EXPERIMENT_INVENTORY.csv`](../research/audit-20261107/EXPERIMENT_INVENTORY.csv): earlier recovery audit and evidence locations.
- [`ICLR2027_LEARNED_GAIN_REVISION_GUIDE.md`](ICLR2027_LEARNED_GAIN_REVISION_GUIDE.md): boundaries of the learned-gain extension and metric-label caveats.
- [`rebuttal_case_analysis.py`](../scripts/rebuttal_case_analysis.py) and [`rebuttal_semantic_blind.py`](../scripts/rebuttal_semantic_blind.py): planned paired analysis and preparation of blinded annotation packets. Source inspection is not a native execution receipt.

## Protocol boundaries shared by all responses

| Evidence block | Prespecified scope | What it can establish |
|---|---|---|
| Original primary study | Qwen 1.5B; five rounds; 512 generated tokens; 16 training draws and native 64-draw evaluation; original MBPP 291 training / 50 reference / 30 development / 500 test split | Original Fixed-versus-Plain results and the corresponding mechanism, information, and budget controls |
| Independent training replication | Paired Plain/Fixed lineages at seeds 43, 44, and 45: c36/c01, c06/c07, c08/c09 | Across-training-run variation within the original setting; paired task resampling alone does not provide this |
| Model and transfer checks | Trained 3B and DeepSeek 6.7B pairs; frozen-checkpoint HumanEval+ and adapted APPS evaluation | Setting-specific external checks with their own task populations and denominators |
| Historical five-round 7B comparison | Previously reported 7B trajectories at five rounds and 4,096 generated tokens; recovered through c00/c25 and the revision guide | Historical cross-size evidence, pending provenance and native-output checks; its completion state is separate from the new ten-round cases |
| Post-submission gain extension | Qwen 7B; ten rounds; 4,096 generated tokens; 16 training draws and native 64-draw evaluation; seed 43; c37–c43 | A single-seed comparison of gain choices and accuracy–diversity trade-offs, reported separately at rounds 5 and 10 |
| Historical audit | c00 and c25 | Recovery and interpretation of existing evidence; neither case creates a new training trajectory |

The originally submitted Fixed method remains the main method. The 7B extension learns spectral gains over the 40-fit/10-guard calibration split and uses ordinary SFT with LoRA update scale 1 and no token-loss reweighting; it does not learn a token-loss weighting or a LoRA update scale. Previously reported five-round 7B evidence has its own historical status. A ten-round case evaluated at round 5 is not automatically the same historical trajectory, and a recovered five-round result does not establish completion through round 10. Its results must not replace or be pooled with the original 1.5B, five-round results. A historical run is reusable only after its data split, model revision, checkpoint lineage, sample counts, decoding settings, length limits, and evaluator identity have been checked. A historical `source_status` label is an inventory description, not a new qualification receipt.

The updated runner specification includes DEV30 diagnostics at the **pre-native, pre-spectral, and post-native** stages, at rounds 1 and 5 for the primary setting and 1, 5, and 10 for the extension. It also includes an output-KL diagnostic on **8 training prompts × 128 raw-logit probe tokens for each arm**. These are code-supported diagnostic outputs to obtain and verify during native execution. This draft contains no newly observed diagnostic values. Training-prompt probes are not an independent test set; equal projection norm is not equal output KL.

For every pending result below, retain the case identity, source revision, sealed run receipt, evaluated checkpoint, task-level metric file, sample count, and denominator. Do not replace missing values with zero or treat a failed/partial run as a completed negative result.

## Reviewer w3G2

### W1 — Gradient-derived orientation versus ordinary attenuation

**Recorded concern:** the contribution of the gradient-derived basis is not isolated from the effect of reducing update strength.

**Cases:** c01 versus c02, c03, and c04; c45 for the original hard-SPD comparator; c27 as an auxiliary reference-count control.

**Response draft.** We agree that a comparison between a hard projection and a soft operator does not by itself identify a benefit from the gradient-derived orientation. The revised comparison separates three questions. The random-basis control c02 preserves the soft gain eigenvalues while changing the basis; the isotropic control c03 matches the specified operator-strength criterion without selecting directions; and c04 matches the residual/blend strength for the continuous-versus-binary comparison. The recovered hard-SPD trajectory c45 provides the original baseline context after its identity is verified. The 40-reference case c27 addresses the amount of calibration information and is not itself an orientation ablation.

For these comparisons, we will report the configured gain spectrum, realized operator/update statistics, and measured output KL alongside native pass@1, pass@64, C64, and conditional D4. The KL probe measures a further difference between the arms; it does not enforce equality of that difference. Consequently, any remaining KL mismatch will be disclosed when interpreting an apparent orientation advantage.

**Pending evidence:** `[W1: c01/c02/c03/c04/c45 run identities; operator statistics; output-KL probe values; paired performance/richness estimates and uncertainty; matched-strength definition.]`

**Claim decision:** if random-basis or isotropic attenuation performs comparably, remove the claim that the particular gradient-derived orientation is necessary. If the controls differ substantially in realized output KL, state that the proposed comparison has not fully separated orientation from functional perturbation strength.

### W2 — Repeatable correct-solution retention and the meaning of AST richness

**Recorded concern:** conditional AST richness alone does not establish repeatable retention of distinct correct solutions.

**Cases:** all three paired lineages c36/c01, c06/c07, c08/c09; c16; c26.

**Response draft.** We distinguish repeatability across training runs from uncertainty over sampled test tasks, and syntactic diversity from algorithmic diversity. The primary replication unit is an independently trained student lineage. We will present all three paired Plain/Fixed seeds, including incomplete or failed lineages in the status ledger, and compute across-run variation only from completed, protocol-matched pairs. The original mapping named c07 and c09 without their Plain partners; the complete comparison also requires c06 and c08.

For conditional D4, the paired comparison will use the same eligible tasks for both arms and show the eligible-task count and eligibility rule. Full-population correctness and coverage will be reported alongside the conditional statistic, so losing difficult tasks cannot be hidden by a changing denominator. Frozen HumanEval+ evaluation c16 checks transfer at native 64-draw sampling. Case c26 adds a blinded human algorithm-family assessment; preparation of the packet is only the first stage and is not a completed semantic result. The separate [`rebuttal_semantic_summary.py`](../scripts/rebuttal_semantic_summary.py) can summarize completed human labels after annotation and adjudication. This is sampled-correct human D4 over 40 preselected tasks with at most 8 verified-correct programs per arm; it is not a 500-task semantic pass@64 evaluation.

**Pending evidence:** `[W2: three paired-seed results and SD; per-round full-task correctness/coverage; common-eligible D4 estimates and task counts; c16 results; completed c26 annotations and disagreements.]`

**Claim decision:** if the effect is unstable across seeds or is limited to syntax, describe retention only at the level supported by the evidence. Do not infer repeatability from multiple samples of one trained model.

### W3 — Presentation, soundness, and novelty

**Recorded concern:** the explanation and positioning of the method overstate what the operator and available evidence establish.

**Cases and text work:** c00, c25, c45; revisions to the method derivation, related work, claims, and limitations.

**Response draft.** We will make the reference-gradient construction and its relationship to the preceding SPD approach explicit. The proximal form is a classical mathematical construction; the empirical question is whether the particular calibrated operator helps preserve useful solutions under looped self-distillation. The derivation of an operator and evidence for the usefulness of its orientation are separate obligations. The main text will state the calibrated-direction hypothesis as a hypothesis unless W1's controls support the stronger interpretation.

Learned-Gain SPECTRUM is a post-submission gain-design extension. It retains the gradient-derived basis, uses additional fitting and guard information, and is not an ablation of that basis. We will keep this extension separate from the originally submitted Fixed method and verify that edits target the actual submitted anonymous manuscript, rather than assuming an available repository draft is identical.

**Pending author work:** `[W3: exact related-work citations and ancestry wording; final derivation/assumptions; revised claim sentences and manuscript locations; original-review wording check.]`

**Claim decision:** an audit file alone does not close this concern. The response needs the actual textual corrections and, where a causal claim remains, its empirical support.


Budget wording: 7.2M is a common per-round minimum target-token budget. Whole-record stopping permits bounded overshoot smaller than the longest encoded record. Report each arm’s actual target count and overshoot; do not claim exact token equality.

## Reviewer FUKc

### F1 — One model setting and one training seed

**Cases:** c36/c01, c06/c07, c08/c09; c18/c19; c14/c15. c37–c43 are a separately labelled extension.

**Response draft.** The revision plan adds independent Plain/Fixed training pairs for seeds 44 and 45 to the original seed-43 pair, a trained 3B pair, and a trained DeepSeek 6.7B pair. An evaluation of the initial model is not a trained replication. We will report the completed pairs, across-run standard deviation for the primary setting, and setting-specific effects without merging incompatible protocols.

The 7B ten-round extension supplies another setting but only one training seed. It therefore cannot resolve the request for independent-seed stability by itself. Previously recovered DeepSeek runs with a different length limit will remain separately labelled unless a protocol-identical counterpart can be established.

**Pending evidence:** `[F1: all paired completion states; primary across-seed results; 3B and DeepSeek native results; exact model revisions and training/evaluation protocols.]`

**Claim decision:** if only the original lineage is complete, retain the single-seed limitation. Report a failed replication as a failed execution, not as corroborating evidence.

### F2 — Unequal access to the 50 reference solutions

**Cases:** c36, c01, c05, c27; c10/c11/c44 for the joint information-and-token-budget check.

**Response draft.** The reference solutions provide additional supervised information, and the comparison must acknowledge this. Case c05 gives Plain access to the same 50 answers through replay. Comparing c01 with c27 also tests Fixed with 50 versus 40 fit references. The Plain baseline c36 remains necessary to identify the incremental effect of reference replay.

Case c44 combines replay of the 50 answers with the same 7.2M shifted-target-token budget used in c10 and c11. This makes the information control interpretable under a common student-training token allowance. It does not make reference-gradient computation, calibration work, or the way the information is used identical between methods. We will report those costs separately.

For the learned extension, 40 fit plus 10 guard references are all calibration information; the guard set is not an independent evaluation set.

**Pending evidence:** `[F2: c36/c05 and c01/c27 contrasts; c10/c11/c44 budget receipts; identity of the replayed references; added supervised-token and calibration-cost accounting.]`

**Claim decision:** if reference replay closes the gap, explain the contribution of access to the answers instead of attributing the entire difference to the spectral operator.

### F3 — Unequal token exposure and calibration cost

**Cases:** c10, c11, c44; c05 for the unconstrained replay contrast.

**Response draft.** Cases c10, c11, and c44 specify the same total student-training allowance of 7.2M shifted target tokens. The completed reports must show realized token counts by round, including reference replay, and whether each arm actually meets the common allowance. Token matching must be demonstrated from the receipts rather than inferred from the configuration alone.

Equal student-training token exposure does not imply equal total compute. We will separately report synthesis and evaluation draws, supervised-reference usage, reference-gradient/calibration work, gain-fitting work where applicable, and measured runtime or a stated compute estimate with its method. If a reliable FLOP estimate is unavailable, we will say so rather than present equal-FLOP claims. Ordinary SFT and LoRA update scale 1 remain explicit, so an unreported loss reweighting or update-scale change cannot be mistaken for the operator effect.

**Pending evidence:** `[F3: actual per-round and total shifted-token counts; replay inclusion; generation totals; calibration and training timing; hardware context; FLOPs estimate or explicit unavailable status.]`

**Claim decision:** describe the result as student-token matched only when that condition is satisfied. Do not describe it as total-compute matched without additional evidence.

### F4 — Unmatched attenuation in the projection comparison

**Cases:** c01–c04 and c45; scheduled DEV30 and output-KL diagnostics.

**Response draft.** We agree that different attenuation strengths can confound a comparison between operators. The random, isotropic, and matched-residual controls are designed to isolate progressively narrower alternatives. We will specify exactly which quantity is matched in each arm and show the realized statistics. The round-1 and round-5 DEV30 diagnostics and raw-logit output-KL probes provide additional evidence about functional perturbation and the timing of changes.

Matching a gain spectrum or Frobenius norm does not guarantee equal output KL. We will report measured KL and any mismatch, and will avoid interpreting a norm-matched control as a fully function-matched intervention.

**Pending evidence:** `[F4: matching definitions; pre-native/pre-spectral/post-native DEV30 records; realized strength and KL; final paired outcome table.]`

**Claim decision:** if the benefit disappears after the strength controls, narrow the mechanism claim to attenuation or stabilization as supported by the results.

### F5 — Superficial AST variation and weak control-flow evidence

**Cases:** c26, c00; task-level verified-program artifacts from the compared arms.

**Response draft.** Exact-code, AST, and control-flow statistics measure different structural properties and will be labelled as proxies. None guarantees a distinct algorithm. We will document the treatment of literals, names, and formatting and retain the control-flow result even if it is weak.

Case c26 prepares a blinded packet from a prespecified set of 40 tasks, with up to eight verified-correct programs per arm. Task selection occurs before observing the method outcomes; missing correct programs and per-arm coverage are retained. Human annotation must assign algorithm families, record uncertainty, and document disagreements and adjudication. The case currently separates packet preparation from that human stage; a generated packet is not evidence of semantic diversity.

**Pending evidence:** `[F5: packet and selection manifest; annotation taxonomy and instructions; completed labels; disagreements/adjudication; coverage counts; semantic-family comparison and uncertainty.]`

**Claim decision:** if the manual assessment does not support the AST effect, restrict the claim to structural diversity and report the semantic result directly.

### F6 — Accuracy trade-offs and transfer without consistent task-success gains

**Cases:** primary c36/c01/c30/c45; transfer c16/c17; interpolation c32–c35; extension c37–c43 interpreted through c25.

**Response draft.** We will report a joint accuracy–diversity comparison rather than present richness as an unconditional improvement. The primary table will include Plain, Fixed, SSD, and the recovered hard-SPD baseline under the same protocol, with pass@1, pass@64, C64, and common-eligible D4. The interpolation cases provide additional trade-off points where their parent checkpoint identity is verified.

HumanEval+ and adapted APPS will be reported separately on their full test populations, with the eligible populations for conditional metrics shown explicitly. A transferred-diversity increase does not demonstrate higher task success. The negative APPS result must remain visible. The 7B learned and adaptive-gain comparison is a separate single-seed table; lower richness or coverage for Learned must not be hidden by an improvement in pass@1.

**Pending evidence:** `[F6: primary frontier; all transfer success metrics and denominators; paired conditional metrics; interpolation points; separate 7B round-5/round-10 frontier.]`

**Claim decision:** describe the supported trade-off. If an arm is dominated on the measured quantities, report that result instead of calling it Pareto superior.

## Reviewer ygkV

### Y1 — Near-uniform shrinkage at tau = 1

**Cases:** c01–c04 and c45; operator and output-KL diagnostics.

**Response draft.** We agree that near-uniform shrinkage would weaken an explanation based on selecting particular directions. We will report the realized gain distribution at the configured tau and compare it with the same-spectrum random basis and strength-matched isotropic operator. A formal spectral representation is insufficient evidence that the orientation matters. The controls and their output-KL measurements will determine how narrowly the mechanism can be described.

**Pending evidence:** `[Y1: realized spectrum and dispersion; c01/c02/c03/c04 comparisons; KL mismatch; retained or removed orientation claim.]`

**Claim decision:** if the spectrum is effectively uniform or the isotropic control matches the outcomes, describe the observed result as shrinkage/stabilization unless additional evidence identifies an orientation effect.

### Y2 — Tau, layer choice, and refreshing the geometry

**Cases:** c12/c13 with c01; c23/c24 with c01; c31 with c01. Historical tau evidence is audited under c00. Extension c41/c42/c43 addresses separate gain schedules.

**Response draft.** The primary five-round controls vary tau through c12 and c13, restrict the operator to the last or middle layer through c23 and c24, and freeze the first-round geometry through c31. Each comparison must use the same original-setting baseline c01. These controls test strength, layer placement, and geometry refresh as distinct choices.

The recovered 7B one-round tau grid is useful exploratory evidence but has different sample counts and length settings from the primary five-round study. We will label it separately. Likewise, the ten-round fixed, tau-decay, and entropy-adaptive cases c41–c43 examine long-run gain schedules and do not substitute for the original-setting sensitivity controls.

**Pending evidence:** `[Y2: primary multi-round tau/layer/refresh outcomes; exact selected layers; geometry-refresh provenance; separately labelled historical tau table; extension schedule outcomes.]`

**Claim decision:** state any sensitivity or failure and do not infer robustness over a wider parameter range than was evaluated.

### Y3 — Temperature/top-p alternatives and SSD frontier points

**Cases:** c20–c22 and c46 for frozen decoding; c28/c29 and c47 for synthesis-only training; c30; parent primary checkpoints c36/c01. Extension SSD is c38.

**Response draft.** We distinguish changes to evaluation decoding from changes to the synthetic training distribution. Cases c20 and c21 evaluate frozen checkpoints at cooler and warmer temperatures; c22 uses the bundled SSD decoding recipe. Cases c28 and c29 specify Plain trajectories with alternative synthesis settings and evaluation with the common native evaluator. In the current repository, SSD changes the synthesis decoder to temperature 1.5 / top-p 0.8 / top-k 20, making c29 and c30 the same training intervention when the remaining configuration and lineage match. Preserve both case identities for traceability, but do not count them as distinct algorithms or require a duplicate rerun when an equivalent sealed c30 trajectory can satisfy c29. The frozen-decoder case c22 remains a different intervention.

Two additional cases isolate top-p while holding temperature and top-k fixed. Case c46 evaluates frozen round-5 checkpoints with `nucleus_tight` (temperature 0.8, top-p 0.8, top-k 0; n64), compared with the common evaluation decoder (0.8 / 0.95 / 0). Case c47 trains a five-round Plain trajectory with synthesis top-p 0.8 and the remaining synthesis settings held to the Plain baseline, then uses the common native evaluation decoder (0.8 / 0.95 / 0). Thus evaluation-only and synthesis-only top-p changes have separate case identities. These cases supply executable comparisons; their native outcomes remain pending. We will report the exact tested configurations and reconcile the original review wording when it becomes available.

**Pending evidence:** `[Y3: frozen-checkpoint decoder grid including c46; synthesis-only training results including c47; SSD native n64 evaluation; exact temperature/top-p/top-k settings and parent identities; original-review wording check.]`

**Claim decision:** if a decoding or synthesis alternative attains the same frontier, report it. Do not attribute a bundled recipe's effect to a single decoding parameter.

### Y4 — Weight interpolation or a KL-to-initial-model baseline

**Cases:** c32/c33 for Plain and c34/c35 for Fixed, using interpolation coefficients 0.5 and 0.75 and verified round-5 parent checkpoints.

**Response draft.** The catalog includes full-weight interpolation with the initial model for both final Plain and Fixed checkpoints. We will report the exact interpolation convention, parent checkpoint identities, and native evaluation results alongside the un-interpolated endpoints.

The recorded concern asks for weight interpolation **or** a KL-to-initial-model baseline. We select the interpolation alternative, implemented by c32–c35, and its native outcomes remain pending. The current c00–c47 catalog does not implement a dedicated training-time KL-to-initial-model baseline, and we make no claim to have run one. Neither a learned-gain guard nor the output-KL diagnostic is that training baseline. This distinction defines the selected comparison; it does not add a second mandatory alternative to the repository summary. As for every recorded concern, the full original wording must still be reconciled before submission.

**Pending evidence:** `[Y4: four interpolation outcomes and checkpoint identities; coefficient convention and both endpoints; original-review wording check for the selected interpolation alternative.]`

**Claim decision:** claim coverage of the interpolation alternative only. Do not state that a KL-regularized training baseline has been run.

### Y5 — Plain's access to the same reference answers

**Cases:** c36/c05; c01/c27; c10/c11/c44.

**Response draft.** The replay control makes the 50 answers available to Plain, while the 40-versus-50 Fixed comparison checks sensitivity to reference count. The additional budget-constrained replay case c44 permits a comparison with c10 and c11 under a common student-training token allowance. These comparisons address reference access and token exposure, while the costs of using the answers through replay, gradients, and calibration remain separately disclosed.

**Pending evidence:** `[Y5: replay and reference-count contrasts; matched-token receipts; reference-set identity and accounting.]`

**Claim decision:** retain any evidence that reference access explains the observed advantage. Do not describe the learned 10-example guard as a held-out test.

### Y6 — Replication, initial-model-only appendix entries, and changed extraction in a pilot

**Cases:** c00; full seed pairs c36/c01, c06/c07, c08/c09; c14/c15; c18/c19; c25 for extension provenance.

**Response draft.** We will distinguish trained student results from initial-model evaluation and pilot results. The replication table requires independently completed trajectories under the same extraction and evaluation protocol, not an initial-checkpoint matrix. All three primary pairs include both Plain and Fixed. The trained second-family and size comparisons will show exact checkpoint and evaluator identities.

A pilot that changed extraction rules will be labelled exploratory and excluded from the confirmatory table unless both arms are reevaluated under a common, declared protocol. Historical recovery and a run continuation also require the original source revision and checkpoint lineage; a partial eight-round run is not a completed ten-round result.

**Pending evidence:** `[Y6: trained-lineage manifests; source/evaluator revisions; pilot extraction comparison; matched reevaluation or explicit exclusion; complete versus partial run ledger.]`

**Claim decision:** retain limitations for every setting that lacks a trained, matched comparison. Do not use the single-seed 7B extension to imply three-seed confirmation.

### Y7 — Small eligible transfer populations and negative APPS outcomes

**Cases:** c16/c17, supplemented by c26's separately scoped annotation evidence.

**Response draft.** Frozen native 64-draw evaluation will report task success on the full HumanEval+ and adapted APPS populations. Conditional D4 will be computed on a common eligible cohort for each pair, with the number and identity of eligible tasks and uncertainty reported. A small eligible cohort limits the strength of the conclusion even when a conditional estimate is large.

The APPS result, including a negative effect or no improvement, will remain in the response. The adaptation and extraction protocol will be documented, and the human annotation subset will not be presented as the full transfer benchmark.

**Pending evidence:** `[Y7: frozen parent checkpoints; benchmark/version and adaptation manifests; full-population success; common-eligible task counts and intervals; negative outcomes.]`

**Claim decision:** restrict transfer claims to the measured benchmark, population, and metric. Do not convert diversity-only evidence into a success claim.

### Y8 — Literals/names retained in ASTs and weak control-flow results

**Cases:** c26 and audited metric definitions under c00.

**Response draft.** We will describe which identifiers and literals the AST representation preserves and how this can count superficial variants. Exact, AST, and control-flow summaries will be reported together with a blinded manual algorithm-family assessment, rather than treating an AST signature as semantic equivalence. Annotation uncertainty and disagreement will remain visible, and the task-selection/coverage manifest will show which examples could actually be assessed.

**Pending evidence:** `[Y8: exact normalizer specification; verified-program examples chosen through the prespecified blind procedure; completed semantic labels; disagreements; control-flow and AST results.]`

**Claim decision:** if the evidence supports only structural variation, use that wording throughout the manuscript and response.

### Y9 — SSD can have higher diversity and Fixed can have lower pass@1

**Cases:** primary c36/c01/c30/c45; extension c37–c43; c25 for historical recovery only.

**Response draft.** We will show SSD as a substantive comparator and retain every metric on which it or Plain is stronger. The comparison will include pass@1, pass@64, C64, and common-eligible D4 under the same native evaluation settings. A method can preserve more distinct correct programs while reducing one-sample accuracy; that is a trade-off, not universal superiority.

The 7B learned-gain cases will be shown separately at rounds 5 and 10. Any gain in pass@1 accompanied by lower coverage or richness will be stated directly. The fixed, learned, decay, and adaptive arms will not be selectively compared across different rounds or generation budgets.

**Pending evidence:** `[Y9: primary Plain/Fixed/SSD/hard-SPD table; reproducible SSD n64 metrics; separate extension table at both report rounds; uncertainty and all adverse differences.]`

**Claim decision:** use a setting-specific frontier statement only where supported. Preserve dominated points and negative comparisons in the table.

## How the new learned-gain cases answer the recorded concerns

| Case | Ten-round 7B arm | Main role |
|---|---|---|
| c37 | Plain | Matched extension baseline |
| c38 | SSD | Strong alternative and frontier comparison |
| c39 | Fixed with 40 fit references | Fixed counterpart using the same fit subset as Learned |
| c40 | Learned with 40 fit + 10 guard references | Gain-adaptivity extension; additional guard information and fitting cost disclosed |
| c41 | Fixed with all 50 references | Reference-count check and fixed-schedule reference |
| c42 | Fixed-gain rule with tau decay 0.8 | Prespecified gain-schedule comparison |
| c43 | Entropy-adaptive tau, gamma 5 | Adaptive-strength comparison |

The main contrasts are c40/c39 for gain design with a common fit subset, c39/c41 for reference-count sensitivity, c37/c38/c39/c40 for the extension frontier, and c41/c42/c43 for fixed versus decayed/adaptive strength. Even c40/c39 is not a pure gain-rule-only causal comparison: Learned has guard information and additional fitting/probe computation. Both methods still use the gradient-derived basis. These cases therefore do not answer W1/Y1 on their own.

Case c25 remains the audit of historical learned and long-run evidence. It cannot replace launch support and sealed native outputs for c37–c43. Historical completed candidates may be reused after identity checks; partially completed c41/c43 must be labelled partial until a valid continuation or replacement trajectory completes. Report the actual state instead of inferring completion from a terminal folder name.

## Evidence slots and remaining obligations before submission

| Slot | Required evidence or decision | Current interpretation |
|---|---|---|
| Original-review alignment | Complete review text/note IDs and confirmation of each question's wording | Not independently recovered; current coverage is of 18 repository summaries |
| Mechanism | c01–c04 and c45 outcomes, realized strength, and output KL | Instrumentation and plans are not observed results |
| Repeatability | Three complete paired primary lineages, paired task analysis, across-run variation | Historical statuses require verification; missing partners cannot be omitted |
| Information and budget | c05/c27 and c10/c11/c44 outcomes with realized counts and costs | Student-token matching does not equal total-compute matching |
| Semantic validity | Completed c26 human annotation and disagreement records | Packet preparation alone leaves this obligation open |
| Baseline coverage | c32–c35 interpolation outcomes for the selected Y4 alternative; c46/c47 isolated top-p outcomes | Comparisons have case identities; native results remain pending. Dedicated KL-to-initial training is not the selected alternative and is not implemented or claimed |
| Transfer/frontier | Native n64 transfer and SSD results, denominators, negative effects | No pooling across tasks, sample counts, lengths, or rounds |
| Learned extension | c37–c43 identity-checked round-5 and round-10 outputs | Separate single-seed evidence with calibration/compute confounds |
| Manuscript changes | Actual claim edits, related-work corrections, anonymous source and final table locations | Textual obligations cannot be marked complete by case registration |

Do not use the historical normalized field `D4_cond_cov` as the original unscaled D4 richness statistic. Recover the intended metric definition and recompute from verified task-level programs when necessary, as required by the learned-gain revision guide. Preserve the original paper's headline pending its own verification; do not silently replace it with a different model, round count, or metric.

This draft intentionally contains no newly asserted numerical results. Fill each pending slot only from the corresponding verified evidence, update the status of every unresolved obligation, and remove author-facing instructions before posting a response.
