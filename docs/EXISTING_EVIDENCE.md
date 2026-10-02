# Existing evidence and claim limits

This release carries forward historical evidence from upstream commit
`45195e866162df1cdf9de0169d2bf17347eb6abf`. It does not turn those runs into
prospective final-study results. The audit read committed reports, CSVs and
compact JSON; it did not load models, execute generated programs, run tests,
or rerun experiments.

Exact extracted values, task-bootstrap intervals, denominators and source Git
object identities are in [`observed_results.json`](../research/audit/observed_results.json).
The claim ledger and minimum remaining work are in
[`claims.json`](../research/audit/claims.json). Source objects can be read with
`git cat-file -p GIT_BLOB` in the pinned upstream repository. Public source
references use collection directories and object identities rather than numeric
randomization values embedded in legacy filenames. The historical identities
are preserved; new runs must have new immutable identities.

## What has actually completed

| Evidence | Status and permitted use |
|---|---|
| MBPP five-round trajectory | One historical training trajectory for Plain, projection, and SPECTRUM; 500 held-out tasks and 16 samples per task at every round. |
| MBPP final-checkpoint supplement | Separate 64-sample evaluation of the initial and final three students on the same 500-task benchmark. It does not supply intermediate 64-sample rounds. |
| SSD continuation | Separate completed five-round continuation with 16 samples per task; retain its own initial resampling. This is an adapted decoding recipe. |
| HumanEval+ and APPS Intro | Historical frozen final-checkpoint transfer for initial, Plain, projection, and SPECTRUM; respectively 164 and 200 tasks, 16 samples per task. Preserve the original evaluator/adaptation provenance. |
| Four-model, five-benchmark matrix | Twenty reported completed **base-model** evaluation cells. This is not trained SPECTRUM replication across models. MBPP uses 64 samples; the transfer cells use 16. |
| Small-task pilot | Exploratory single-round, 64-task, 64-sample extraction-sensitivity study. Exclude from full-benchmark confirmation. |
| Ten-round smoke run | Four evaluation tasks and four samples per task; a functional pipeline check, not research evidence. |
| SSD final 64-sample evaluation | Pending in the inspected archive; the retention record explicitly preserves the checkpoint for unfinished evaluation. |
| Natural Gate 0 | Incomplete. Existing real-task AST contrasts do not complete the natural iterative-collapse audit. |
| Prospective final experiment | Planned code and protocol; no outcomes are supplied by this release audit. |

Five rounds are five dependent updates in one trajectory. They are not five
independent repeats. The reported bootstrap intervals resample evaluation tasks
and do not estimate training-run variability.

## Main completed MBPP endpoint

The following is the historical **64-sample** pool, with 500 tasks and 32,000
samples per model. Percentages are displayed for pass rates. C64 is expected
correct AST class richness in 64 total draws; D4 is expected AST richness in
four correct draws on eligible tasks.

| Native student | pass@1 (%) | pass@16 (%) | pass@64 (%) | C64 | D4 | D4 eligible |
|---|---:|---:|---:|---:|---:|---:|
| Initial | 37.94375 | 65.69244 | 72.0 | 12.802 | 3.35837 | 322/500 |
| Plain | 41.446875 | 65.63637 | 70.4 | 8.506 | 2.85648 | 321/500 |
| Projection control | 41.765625 | 65.64610 | 70.2 | 8.388 | 2.80980 | 321/500 |
| SPECTRUM | 40.33125 | 66.22508 | 72.6 | 11.510 | 3.14329 | 323/500 |

Plain improves pass@1 but loses correct implementation breadth: C64 changes by
−4.296, paired 95% task-bootstrap interval [−4.918, −3.692]. Its pass@64 falls
by 1.6 percentage points, interval [−4.0, +0.8] points. That aggregate point
estimate supplies a concrete task-success consequence to examine, but the
interval includes zero. It does not prove that AST loss caused success loss,
nor that each natural example exhibits such a consequence.

SPECTRUM retains more C64 than Plain (+3.004 [2.568, 3.494]) and projection
(+3.122 [2.686, 3.596]), while remaining below the initial model
(−1.292 [−1.786, −0.780]). It has lower pass@1 than both trained controls and
fails the recorded absolute one-percentage-point noninferiority criterion.
Describe partial retention with an accuracy tradeoff, not universal improvement
or full preservation. Marginal D4 values use different eligible populations;
paired D4 effects must use the shared eligible task sets in the source JSON.

## The SSD result must remain visible

These values belong to the **16-sample** historical evaluations, not the
64-sample table above.

| Final student | pass@1 (%) | pass@16 (%) | C16 | D4 | D4 eligible |
|---|---:|---:|---:|---:|---:|
| Plain | 41.3000 | 66.0 | 3.090 | 2.74669 | 268/500 |
| SSD recipe adaptation | 35.9625 | 65.6 | 3.710 | 3.26758 | 255/500 |
| SPECTRUM | 40.1750 | 67.2 | 3.606 | 2.99713 | 263/500 |
| Projection control | 41.3500 | 65.6 | 3.066 | 2.690 | 262/500 |

SSD has higher C16 and marginal D4 than SPECTRUM, whereas SPECTRUM has higher
pass@1 and reported pass@16. This is an unfavorable result for a claim of
SPECTRUM diversity dominance and must not be hidden. D4 eligibility differs,
and the audit did not construct a new paired cross-run SSD test. The three
non-SSD pass@16 values above are transcribed from the historical manuscript's
design table; this audit did not recompute them from raw outcomes. All other
listed SSD values are directly supported by its trajectory CSV.

The SSD initial evaluation is a separate sample pool from the original initial
model evaluation. Never pool it silently. Never fill the missing final n=64 SSD
cell with an n=16 score or the single-round pilot.

## Transfer is mixed

| Historical frozen transfer | Plain pass@16 (%) | SPECTRUM pass@16 (%) | Plain C16 | SPECTRUM C16 |
|---|---:|---:|---:|---:|
| HumanEval+ | 86.58537 | 86.58537 | 5.84756 | 6.00000 |
| APPS Intro, adapted | 35.5 | 34.0 | 1.930 | 1.845 |

These point estimates do not establish a universal transfer advantage. The
APPS result is unfavorable on both displayed endpoints. The completed base-model
matrix is useful context but cannot replace missing trained-method comparisons,
SSD transfer, independent repetitions, or geometry controls.

## Natural Gate 0 and claims still missing evidence

The archived task-level examples select equal-correct-count HumanEval+/APPS
cases with both signs of AST richness difference. They are real-task AST
contrasts, not an audited sequence showing initial behavior, an intervention
generator, and post-SFT retention with semantic strategy labels. Natural Gate 0
therefore remains incomplete. Do not invent per-case frequencies, lost
strategies, failure consequences, annotations, or example programs to fill it.

AST fingerprints describe implementations rather than distinct algorithms.
Historical strategy-label outputs contain unavailable/partial entries; zero
entries in those reports are not evidence that semantic coverage was measured
as zero. A semantic-algorithm claim requires actual independent annotation, or
the paper must retain the AST-proxy scope.

Plain and SSD do not use the reference anchor used for SPECTRUM calibration.
Projection shares that anchor and is therefore an information-matched design
control. No completed anchor-only SFT control isolates the information advantage.
No completed strength sweep or randomized-direction control establishes that the
calibrated orientation is necessary. Candidate counts and update schedules were
matched, but generated-token counts and compute were not equal by assumption.

The novelty claim must concern the specific spectral generation intervention
and the measured retention question. Do not claim the first iterative
self-distillation method.

## Minimum remaining work

1. Complete the bounded natural-case audit with actual programs, explicit case
   selection, shared denominators, and measured consequences or clear absence
   of such evidence. Preserve the negative cases.
2. Execute the frozen finite Plain/SSD/SPECTRUM study with the same native
   evaluation policy, independent training replications, every required round,
   and retained checkpoints. Record failures and missing cells rather than
   substituting zeros or historical results.
3. Collect aligned intervention-generator and native-student diagnostics to
   separate generation-time behavior from what SFT retains.
4. Run the approved bounded strength, loss, and geometry diagnostics. If the
   paper claims to exclude reference-information advantage, add the bounded
   anchor-only control before making that claim; otherwise qualify the claim.
5. Complete fixed transfer for the main comparators, report task eligibility,
   paired intervals, realized lengths and resource costs, then write the paper
   after the finite plan finishes regardless of effect direction. Additional
   models or a wider parameter search are not prerequisites for that bounded
   conclusion.
