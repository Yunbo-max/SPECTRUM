# Response to Reviewer ygkV — mechanism and controls

Thank you for the concrete suggestions. The additional controls document the accuracy–richness trade-off and delimit the role of orientation. Unless stated otherwise, the results below use Qwen2.5-Coder-1.5B, five rounds, a 512-token generation limit, and 64 evaluation samples on each of 500 MBPP tasks.

**Shrinkage and orientation.** Random-basis soft gains and isotropic attenuation obtain pass@64/C64 of **73.0%/12.768** and **72.6%/11.888**, versus **72.4%/10.870** for Fixed. Their pass@1 is lower, **39.25% and 39.60%**, versus **40.24%**. We therefore interpret these as competing trade-off points and do not claim that the gradient-derived orientation is necessary. The controls preserve the constructed gain spectrum or match Frobenius displacement from identity; neither enforces equal output KL.

**Strength, layer placement, and geometry refresh.** The five-round sensitivity results are:

| Setting | pass@1 (%) | pass@64 (%) | C64 |
|---|---:|---:|---:|
| Plain | 41.47 | 71.2 | 8.158 |
| $\tau=0.5$ | 41.36 | 71.8 | 9.458 |
| $\tau=1$ | 40.24 | 72.4 | 10.870 |
| $\tau=2$ | 38.96 | 72.8 | 12.694 |
| Last layer only | 40.53 | 72.4 | 9.970 |
| Middle layer only | 41.50 | 71.6 | 8.870 |
| Reuse first-round operator | 40.06 | 72.8 | 11.496 |

These results show a controllable accuracy–richness trade-off over the tested strengths. Single-layer interventions still increase C64 relative to Plain, while the default placement gives a larger increase. Reusing the first-round operator also retains the benefit; refreshing the geometry every round is therefore not demonstrated to be necessary.

**Evaluation decoding versus synthetic-data generation.** On the frozen Fixed student, evaluation temperatures **0.6/0.8/1.0** give pass@1 **42.07%/40.24%/37.57%** and C64 **9.288/10.870/12.240**. Tightening evaluation top-p from 0.95 to 0.8 gives pass@1 **42.22%**, pass@64 **70.2%**, and C64 **8.736**. These are Fixed-checkpoint decoding controls.

Separately, changing only Plain's synthesis temperature to 1.0, then using the common evaluation decoder, gives **39.08%/73.0%/9.932** for pass@1/pass@64/C64. Tightening only synthesis top-p to 0.8 gives **42.87%/70.4%/6.734**. Thus, simpler decoder changes are effective alternatives with different trade-offs. The bundled SSD recipe is reported separately; duplicate case names for the same recipe are not counted as different algorithms.

**Interpolation with the initial model.** We evaluated
$\theta_\alpha=(1-\alpha)\theta_0+\alpha\theta_5$:

| Parent / coefficient | pass@1 (%) | pass@64 (%) | C64 |
|---|---:|---:|---:|
| Plain / 0.50 | 39.27 | 73.4 | 10.778 |
| Plain / 0.75 | 40.45 | 71.0 | 9.384 |
| Fixed / 0.50 | 38.58 | 73.6 | 12.426 |
| Fixed / 0.75 | 39.28 | 72.6 | 11.388 |

Plain interpolation is a strong alternative; applying the same coefficient to Fixed can further increase richness. The comparison implemented here is weight interpolation. We have not run a separate training-time KL-to-initial-model baseline.
