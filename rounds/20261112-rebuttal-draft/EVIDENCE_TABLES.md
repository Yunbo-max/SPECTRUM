# Rebuttal evidence tables and source boundaries

Internal author document. Source snapshot: **0d9207e4422a6c98d02a37985271aef05d0cc3b3**; inspected on 2026-11-12. No new training, model inference, benchmark scoring, raw-program re-verification, or significance test was performed for this draft.

The new endpoint evidence is the 36 saved JSON metric files in [20261109-local-results/metrics](../20261109-local-results/metrics). Their file hashes and selected aggregates are preserved in [evidence_numbers.json](evidence_numbers.json). The configured arm identities are in [cases.json](../../experiments/iclr2027_rebuttal/cases.json). Saved metrics and completion receipts are not a substitute for the unuploaded raw generations and full checkpoint lineage.

All percentages below are pass rates; a difference in percentages is in percentage points. C64 is expected distinct correct normalized AST classes in 64 total draws, averaged across all 500 tasks. D4 uses four correct draws and is compared only on tasks eligible in both arms. These are implementation-structure proxies. No semantic-equivalence or algorithm-family guarantee is inferred.

## A. Three paired training seeds

The declared primary protocol is Qwen2.5-Coder-1.5B, MBPP500, round 5, 512-token generation cap, n=64 evaluation. Each pair compares the same round; these are not changes from the initial model.

| Seed | Plain / Fixed cases | Plain pass@1 | Fixed pass@1 | Plain pass@64 | Fixed pass@64 | Plain C64 | Fixed C64 |
|---|---|---:|---:|---:|---:|---:|---:|
| 43 | c36 / c01 | 41.4656% | 40.2437% | 71.20% | 72.40% | 8.158 | 10.870 |
| 44 | c06 / c07 | 41.3344% | 40.0625% | 71.60% | 72.80% | 8.484 | 11.498 |
| 45 | c08 / c09 | 41.5875% | 40.0906% | 70.20% | 71.20% | 8.314 | 11.156 |

C64 across-seed mean ± sample SD: **8.318667 ± 0.163050 → 11.174667 ± 0.314416**. The relative difference of the means is **+34.3324%**. Pass@64 means are **71.0000% → 72.1333%**; pass@1 means are **41.4625% → 40.1323%**. These SDs describe three training-seed outcomes; they are not confidence intervals or proof of noninferiority.

### Common-eligible descriptive comparisons

Read each task's saved correct-matched value at budget 4 and intersect task IDs with at least four correct samples in both arms. The audit JSON stores each intersection's ID hash. This is a descriptive comparison of saved evaluator labels, not a re-score of source programs.

| Left → right | Common eligible tasks | Left AST D4 | Right AST D4 | Δ AST D4 | Δ control-flow D4 |
|---|---:|---:|---:|---:|---:|
| c36 → c01 | 312 | 2.826590 | 3.088942 | +0.262353 | +0.002886 |
| c06 → c07 | 316 | 2.845768 | 3.134924 | +0.289156 | +0.023388 |
| c08 → c09 | 315 | 2.820047 | 3.120036 | +0.299989 | +0.052550 |
| c14 → c15 | 320 | 2.603311 | 2.766881 | +0.163570 | +0.108368 |
| c18 → c19 | 326 | 3.132076 | 3.557635 | +0.425559 | +0.100348 |
| c05 → c01 | 315 | 2.796235 | 3.089072 | +0.292837 | +0.039146 |
| c01 → c02 | 313 | 3.085808 | 3.276631 | +0.190824 | +0.044266 |
| c01 → c03 | 313 | 3.086446 | 3.194471 | +0.108025 | +0.036782 |
| c01 → c30 | 306 | 3.069985 | 3.328763 | +0.258778 | +0.179129 |

## B. Direction, information, and strong method controls

All are declared primary-setting r5 endpoints. c45 is a legacy reconstruction, not an independently reproduced official upstream SPD implementation. Random/isotropic do not support orientation necessity; their lower pass@1 is retained alongside higher C64. Replay tests one way of providing the same references and does not equalize information use or calibration computation.

| Case | Setting | pass@1 (%) | pass@64 (%) | C64 |
|---|---|---:|---:|---:|
| [c36](../20261109-local-results/metrics/c36.evaluation.metrics.json) | Plain | 41.4656 | 71.20 | 8.158 |
| [c01](../20261109-local-results/metrics/c01.evaluation.metrics.json) | Fixed, 50 references | 40.2437 | 72.40 | 10.870 |
| [c02](../20261109-local-results/metrics/c02.evaluation.metrics.json) | Random soft | 39.2469 | 73.00 | 12.768 |
| [c03](../20261109-local-results/metrics/c03.evaluation.metrics.json) | Isotropic soft | 39.6031 | 72.60 | 11.888 |
| [c04](../20261109-local-results/metrics/c04.evaluation.metrics.json) | Matched residual blend | 42.0594 | 71.20 | 8.004 |
| [c45](../20261109-local-results/metrics/c45.evaluation.metrics.json) | Legacy hard-projection reconstruction | 41.6531 | 70.60 | 8.128 |
| [c05](../20261109-local-results/metrics/c05.evaluation.metrics.json) | Plain plus 50-reference replay | 41.7906 | 70.60 | 7.936 |
| [c27](../20261109-local-results/metrics/c27.evaluation.metrics.json) | Fixed, 40 references | 40.2781 | 72.60 | 11.134 |
| [c30](../20261109-local-results/metrics/c30.evaluation.metrics.json) | Implemented SSD recipe | 35.9188 | 72.00 | 12.048 |

## C. Common configured target-token setting

This is a materially adverse result for Fixed: pass@64 is 16 points below Plain. The target is a minimum with whole-record overshoot, not exact exposure or equal FLOPs. Uploaded receipts do not include the realized exposure/runtime ledger. Do not use the higher marginal conditional richness of a smaller eligible cohort to hide the full-population loss.

| Case | Setting | pass@1 (%) | pass@64 (%) | C64 |
|---|---|---:|---:|---:|
| [c10](../20261109-local-results/metrics/c10.evaluation.metrics.json) | Plain, 7.2M shifted-target minimum / round | 20.9500 | 45.40 | 5.666 |
| [c11](../20261109-local-results/metrics/c11.evaluation.metrics.json) | Fixed, same configured minimum | 9.0375 | 29.40 | 3.072 |
| [c44](../20261109-local-results/metrics/c44.evaluation.metrics.json) | Plain plus replay, same configured minimum | 20.6625 | 49.40 | 6.132 |

## D. Other trained models

Declared MBPP500, r5, n64, 512-token protocol, one paired seed per model. C64 increases by 38.1832% for Qwen3B and 17.6925% for DeepSeek6.7B; pass@64 changes by −1.2 and −0.2 points. The point estimates do not establish across-seed significance for these models.

| Case | Setting | pass@1 (%) | pass@64 (%) | C64 |
|---|---|---:|---:|---:|
| [c18](../20261109-local-results/metrics/c18.evaluation.metrics.json) | Qwen2.5-Coder-3B Plain | 50.6219 | 73.20 | 13.320 |
| [c19](../20261109-local-results/metrics/c19.evaluation.metrics.json) | Qwen2.5-Coder-3B Fixed | 49.8906 | 72.00 | 18.406 |
| [c14](../20261109-local-results/metrics/c14.evaluation.metrics.json) | DeepSeek-Coder-6.7B Plain | 47.4375 | 72.60 | 8.026 |
| [c15](../20261109-local-results/metrics/c15.evaluation.metrics.json) | DeepSeek-Coder-6.7B Fixed | 46.7938 | 72.40 | 9.446 |

## E. Strength, placement, and first-round operator reuse

The tested tau range shows a directional accuracy/richness trade-off, not insensitivity. c31 reuses the operator; it is not a control that freezes only the eigenvectors while relearning gains.

| Case | Setting | pass@1 (%) | pass@64 (%) | C64 |
|---|---|---:|---:|---:|
| [c36](../20261109-local-results/metrics/c36.evaluation.metrics.json) | Plain | 41.4656 | 71.20 | 8.158 |
| [c12](../20261109-local-results/metrics/c12.evaluation.metrics.json) | tau=0.5 | 41.3625 | 71.80 | 9.458 |
| [c01](../20261109-local-results/metrics/c01.evaluation.metrics.json) | tau=1 | 40.2437 | 72.40 | 10.870 |
| [c13](../20261109-local-results/metrics/c13.evaluation.metrics.json) | tau=2 | 38.9594 | 72.80 | 12.694 |
| [c23](../20261109-local-results/metrics/c23.evaluation.metrics.json) | Last layer only | 40.5344 | 72.40 | 9.970 |
| [c24](../20261109-local-results/metrics/c24.evaluation.metrics.json) | Middle layer only | 41.5031 | 71.60 | 8.870 |
| [c31](../20261109-local-results/metrics/c31.evaluation.metrics.json) | Reuse entire first-round operator | 40.0562 | 72.80 | 11.496 |

## F. Frozen Fixed-checkpoint decoding

The uploaded c20/c21/c22/c46 receipts list base and spectral_soft/round_5. Their metric files support the Fixed endpoint shown here. Do not label the first SUMMARY row as a Plain r5 checkpoint or claim a fully evidenced Plain-by-Fixed grid.

| Case | Setting | pass@1 (%) | pass@64 (%) | C64 |
|---|---|---:|---:|---:|
| [c20](../20261109-local-results/metrics/c20.evaluation.metrics.json) | T=.6, p=.95, k=0 | 42.0656 | 70.40 | 9.288 |
| [c01](../20261109-local-results/metrics/c01.evaluation.metrics.json) | T=.8, p=.95, k=0 | 40.2437 | 72.40 | 10.870 |
| [c21](../20261109-local-results/metrics/c21.evaluation.metrics.json) | T=1, p=.95, k=0 | 37.5656 | 72.20 | 12.240 |
| [c22](../20261109-local-results/metrics/c22.evaluation.metrics.json) | T=1.5, p=.8, k=20 | 34.7188 | 72.60 | 12.428 |
| [c46](../20261109-local-results/metrics/c46.evaluation.metrics.json) | T=.8, p=.8, k=0 | 42.2156 | 70.20 | 8.736 |

## G. Synthesis-only decoder controls

These trained endpoints return to the common evaluation decoder. c29 and c30 implement the same bundled recipe and are not two algorithmic baselines. T and p single-parameter controls are separate from that bundled recipe.

| Case | Setting | pass@1 (%) | pass@64 (%) | C64 |
|---|---|---:|---:|---:|
| [c36](../20261109-local-results/metrics/c36.evaluation.metrics.json) | Plain default | 41.4656 | 71.20 | 8.158 |
| [c28](../20261109-local-results/metrics/c28.evaluation.metrics.json) | Plain synthesis T=1 | 39.0781 | 73.00 | 9.932 |
| [c29](../20261109-local-results/metrics/c29.evaluation.metrics.json) | Plain synthesis SSD recipe | 35.9281 | 72.40 | 11.994 |
| [c30](../20261109-local-results/metrics/c30.evaluation.metrics.json) | SSD method label; same synthesis recipe | 35.9188 | 72.00 | 12.048 |
| [c47](../20261109-local-results/metrics/c47.evaluation.metrics.json) | Plain synthesis top-p=.8 | 42.8687 | 70.40 | 6.734 |

## H. Full-weight interpolation

Convention: theta_alpha=(1-alpha)*theta_0+alpha*theta_r5. Plain interpolation is an effective competing trade-off; the same interpolation also changes Fixed. The shared pass@64/C64 endpoints are reported descriptively; the entire metric-protocol objects contain different correct-budget lists. No training-time KL-to-initial baseline was implemented.

| Case | Setting | pass@1 (%) | pass@64 (%) | C64 |
|---|---|---:|---:|---:|
| [c32](../20261109-local-results/metrics/c32.evaluation.metrics.json) | Plain, alpha=.5 | 39.2719 | 73.40 | 10.778 |
| [c33](../20261109-local-results/metrics/c33.evaluation.metrics.json) | Plain, alpha=.75 | 40.4531 | 71.00 | 9.384 |
| [c34](../20261109-local-results/metrics/c34.evaluation.metrics.json) | Fixed, alpha=.5 | 38.5750 | 73.60 | 12.426 |
| [c35](../20261109-local-results/metrics/c35.evaluation.metrics.json) | Fixed, alpha=.75 | 39.2781 | 72.60 | 11.388 |

## I. Historical frozen transfer, n16

Source: [observed_results.json](../../research/audit/observed_results.json), studies frozen_humaneval_transfer_n16 and frozen_apps_transfer_n16; interpretation in [EXISTING_EVIDENCE.md](../../docs/EXISTING_EVIDENCE.md). These are MBPP-trained 1.5B r5 checkpoints transferred without target training. They are historical aggregate records; complete task-level transfer artifacts are not present in this source snapshot.

| Benchmark | Tasks | n | Plain pass@16 | Fixed pass@16 | Plain C16 | Fixed C16 |
|---|---:|---:|---:|---:|---:|---:|
| HumanEval+ | 164 | 16 | 86.58537% | 86.58537% | 5.847561 | 6.000000 |
| APPS Intro, adapted verifier | 200 | 16 | 35.5% | 34.0% | 1.930 | 1.845 |

Do not subtract marginal D4 means with different eligible populations. The n64 HumanEval+ rerun c16 was stopped; new APPS c17 is reported completed but has no uploaded numeric payload in this snapshot. Neither fact supplies a new n64 or n128 effect estimate.

## J. Historical 4096-token cross-family records (separate protocol)

Source: [EXPERIMENT_INVENTORY.csv](../../research/audit-20261107/EXPERIMENT_INVENTORY.csv) and [SOURCE_PATHS.md](../../research/audit-20261107/SOURCE_PATHS.md). These are five-round, MBPP500, n64 audit summaries, not the new ten-round trajectory and not the 512-token primary protocol. Retain this provenance if using them as an optional supplement.

| Model | Method | pass@1 (%) | pass@64 (%) | C64 |
|---|---|---:|---:|---:|
| Qwen2.5-Coder-7B | Plain | 59.900 | 82.4 | 9.174 |
| Qwen2.5-Coder-7B | SSD | 56.706 | 84.2 | 13.730 |
| Qwen2.5-Coder-7B | Fixed | 56.853 | 84.8 | 14.570 |
| Qwen2.5-Coder-7B | Learned | 58.925 | 82.8 | 10.186 |
| Llama-3.1-8B | Plain | 45.450 | 62.2 | 4.852 |
| Llama-3.1-8B | SSD | 44.259 | 67.0 | 7.258 |
| Llama-3.1-8B | Fixed | 44.147 | 66.0 | 7.066 |

Fixed versus Plain increases pass@64/C64 here; SSD is stronger than Fixed on both those endpoints for Llama. Learned's higher pass@1 than Fixed on Qwen7B comes with lower pass@64/C64. Do not relabel the historical sub-one D4_cond_cov column as the [1,4]-valued D4 estimand. DeepSeek's historical 4096 endpoints have mismatched r4/r5 completion and are not a matched final-round comparison.

## K. Historical true n128 result: one 7B round

Source: [OPERATOR_ABLATION.csv](../../research/audit-20261107/OPERATOR_ABLATION.csv), spectrum_7b_highk_v1. Qwen2.5-Coder-7B, MBPP500, 512-token limit, n128, one training round, one seed; summary evidence only.

| State | pass@64 (%) | pass@128 (%) | C64 |
|---|---:|---:|---:|
| Initial model | 80.6409 | 82.0 | 19.7881 |
| Plain r1 | 80.349 | 82.2 | 17.1824 |
| Fixed r1 | 80.735 | 82.8 | 18.2185 |

The +0.6-point pass@128 effect is against Plain, corresponding to three net additional solved tasks out of 500. Fixed retains more C64 than Plain but does not exceed the initial model. This is not a multi-round or cross-model n128 result. Training-sample labels such as ts128 do not imply n128 evaluation.

## L. Status claims excluded from completed-effect prose

- All 36 newly uploaded metric files use 500 tasks ×64 samples; none contains a new n128 evaluation.
- The 20-cell four-model/five-benchmark matrix is initial-model-only evidence. Gemma3-4B, Qwen3-8B, CodeContests, and LiveCodeBench entries cannot establish trained SPECTRUM gains.
- MATH500 has a completed status record with missing numerical outcomes; QA is partial and its inventory/config sample counts disagree. No new math/QA or CGL benefit is inferred.
- cg00–cg15 have no uploaded effect metrics. Software checks and configurations are not retention results.
- The Nov12 7B report mixes observed and explicitly extrapolated later rounds. No extrapolated row is used here.
- c26 human semantic labels are incomplete. The primary evidence is structural, and conditional task populations must remain visible.
- The original review bodies and anonymous submitted manuscript have not been independently recovered for this writing pass. The 18-issue map is a recovered summary; exact review wording and manuscript locations still need author comparison.

## M. Source and arithmetic review

The JSON companion preserves all 36 endpoint summaries, source SHA-256 digests, nine common-eligible comparisons, and three-seed mean/sample SD. It was produced with standard-library reading and arithmetic only. There is no new scientific execution receipt or claim of acceptance. The English comments have no identifying repository URLs; internal source links remain in this packet.
