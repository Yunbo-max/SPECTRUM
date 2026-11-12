# Response to Reviewer w3G2

Thank you for asking us to establish repeatability and distinguish the operator's mathematical properties from its empirical mechanism. The new experiments provide evidence for correct-implementation retention and clarify the scope of that evidence.

**Repeatability and the meaning of diversity.** We now report three paired, independently trained Plain/SPECTRUM lineages using Qwen2.5-Coder-1.5B, five rounds, a 512-token generation limit, and 64 samples on all 500 MBPP evaluation tasks. Mean correct AST richness C64 increases from **8.319 ± 0.163 to 11.175 ± 0.314**, or **34.3%**; ± denotes the sample standard deviation across training seeds. Pass@64 increases from **71.00% to 72.13%**, while pass@1 changes from **41.46% to 40.13%**.

For conditional D4, we use the intersection of tasks with at least four correct samples from each method. D4 is the expected number of distinct normalized AST classes among four correct samples. The three paired D4 improvements are **+0.262, +0.289, and +0.300**, on **312, 316, and 315** common tasks. Thus, the positive AST-richness effect persists after controlling the correct-sample budget and task eligibility. C64 and pass@64 retain the full 500-task denominator.

These metrics quantify correct implementation structure. We do not equate an AST class with an algorithm family; human algorithm-family labels are not yet available, and control-flow effects are weaker. The manuscript wording will make this scope explicit.

**Orientation, attenuation, and the hard-projection comparison.** The additional operator controls give the following fifth-round results:

| Generator intervention | pass@1 (%) | pass@64 (%) | C64 |
|---|---:|---:|---:|
| Legacy hard-projection reconstruction | 41.65 | 70.6 | 8.128 |
| Fixed SPECTRUM | 40.24 | 72.4 | 10.870 |
| Random-basis soft gains | 39.25 | 73.0 | 12.768 |
| Isotropic attenuation | 39.60 | 72.6 | 11.888 |

The soft intervention improves high-budget coverage and richness over this hard-projection control, with an accuracy trade-off. Random and isotropic controls achieve higher C64 and pass@64, with lower pass@1, so these results **do not establish that the gradient-derived orientation is necessary**. We will remove that stronger interpretation.

Randomization preserves the gain spectrum constructed from each arm's current covariance; isotropic attenuation matches Frobenius displacement from identity. Independent recursive lineages need not have identical numerical spectra, and these constructions do not enforce equal output-distribution KL. The mechanism comparison currently uses one seed.

**Contribution and theoretical scope.** For a nonzero positive-semidefinite calibration covariance, the fixed operator has gains
$g_i=[1+\tau(1-\lambda_i/\lambda_{\max})]^{-1}$.
For finite $\tau\geq0$, these lie in $[1/(1+\tau),1]$: the intervention attenuates rather than deletes eigendirections. The inverse form is a classical proximal construction; its full-rank property does not guarantee global semantic diversity.

We will make the reference-gradient ancestry explicit. The contribution is the concrete generation-time intervention and the empirical retention question under repeated raw-output self-distillation. Ordinary SFT remains unchanged, with no correctness filtering or token-loss reweighting. The strongest supported finding is the reproducible increase in correct structural richness over Plain, together with measured success-rate and accuracy trade-offs.
