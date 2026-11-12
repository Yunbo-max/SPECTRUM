# Response to Reviewer ygkV — replication and interpretation

The main protocol uses Qwen2.5-Coder-1.5B, five rounds, a 512-token generation limit, and 64 evaluation samples per MBPP task. Model and transfer extensions are identified separately below.

**Reference access.** Plain with supervised replay of the same 50 reference answers reaches pass@64 **70.6%** and C64 **7.936**, compared with **72.4% and 10.870** for Fixed. Its pass@1 is higher, **41.79% versus 40.24%**. This replay control does not reproduce Fixed's richness benefit. Using 40 rather than 50 calibration references gives similar Fixed results, **72.6% / 11.134**.

Under the separately configured 7.2M-target-token-per-round setting, however, Fixed underperforms Plain and replay: pass@64 is **29.4% versus 45.4% and 49.4%**. We retain this boundary and do not claim equal total compute or budget-independent superiority. Realized training-exposure and runtime accounting are still incomplete.

**Trained replication and extraction.** Three independently trained Plain/Fixed pairs yield pass@64 gains of **1.2, 1.2, and 1.0 percentage points** and C64 gains of **2.712, 3.014, and 2.842**. Mean C64 rises from **8.319 ± 0.163 to 11.175 ± 0.314**; ± is sample standard deviation across training seeds.

Trained Qwen2.5-Coder-3B and DeepSeek-Coder-6.7B pairs also increase C64, from **13.320 to 18.406** and **8.026 to 9.446**, respectively. Their pass@64 changes are −1.2 and −0.2 points. These results address trained-model replication. Initial-model matrix entries and the extraction-changing pilot are not used as substitutes for trained comparisons.

**Transfer denominators and semantic scope.** For the main three seed pairs, common-eligible D4 increases by **0.262/0.289/0.300** on **312/316/315** tasks eligible for both methods. We report these denominators alongside C64 and pass@64 on all 500 tasks.

Historical frozen-checkpoint transfer uses 16 samples per task:

| Benchmark | Plain pass@16 (%) | Fixed pass@16 (%) | Plain C16 | Fixed C16 |
|---|---:|---:|---:|---:|
| HumanEval+, 164 tasks | 86.59 | 86.59 | 5.848 | 6.000 |
| Adapted APPS Intro, 200 tasks | 35.50 | 34.00 | 1.930 | 1.845 |

The transfer evidence is mixed, and a conditional richness result cannot establish improved task success. We do not claim a new 64-sample transfer result from these 16-sample evaluations.

AST normalization retains some distinctions in names and literals, so AST classes are not algorithm identities. The main seed's control-flow D4 increase is only **0.0029**, substantially smaller than the AST-D4 increase of **0.2624** on the same 312 tasks. Human algorithm-family labels are not yet available; our claim is correct structural richness.

**SSD and accuracy.** Under common native evaluation, Fixed gives **40.24%/72.4%/10.870** for pass@1/pass@64/C64, while the implemented SSD recipe gives **35.92%/72.0%/12.048**. SSD has greater richness; Fixed has higher single-sample accuracy in this comparison. We will present both as substantive trade-off points.

Across the three seed pairs and the two trained-model extensions under the main protocol, the consistent finding is greater correct AST richness than Plain. We will state this contribution precisely, alongside the stronger alternatives and the settings where success-rate gains do not follow.
