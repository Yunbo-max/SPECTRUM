# Interpreting the ten-sample comparison

This note precedes any native LCB correctness results. It constrains what we can infer; it does not change the author protocol or prescribe additional rounds. Exact numerical references were computed with Python's standard library on hn01 and saved in finite-sample-reference.json. They are analytic examples, not model scores.

For a task with independent success probability p, zero successes in n trials occurs with probability (1-p)^n. After zero of ten, the exact one-sided 95% upper confidence endpoint is 1-0.05^(1/10)=0.25887. After ten of ten, the corresponding lower endpoint is 0.74113. Neither observation establishes a support floor or ceiling. These are pointwise IID statements, not simultaneous intervals for 131 tasks or guarantees under correlated generation.

Task discordances alone are also insufficient. If two equally capable independent samplers both have task success probability p, the chance that one has any success and the other has none is z(1-z), where z=(1-p)^10. For the deliberately simplified p=0.1 case, this is 0.2271 in each direction: roughly 29.75 one-direction discordant tasks out of 131 despite identical success probabilities. Actual task heterogeneity and shared seeds differ from this illustration. We must not fit this toy null to the benchmark by assuming all tasks share the observed overall pass rate.

The native pass@5 estimator from ten completions is 1-C(10-c,5)/C(10,5). A single observed success makes a task estimate jump from 0 to 0.5; two successes give 0.77778. This is a valid estimator under its sampling assumptions, but task-level values are coarse and noisy. Aggregate paired intervals are more informative than naming individual losses. The existing analyzer's task bootstrap is explicitly conditional on the sampled completions and does not include training uncertainty or fully characterize repeated generation uncertainty.

## How this affects the next interpretation

Report both directions of any-success discordance, total paired changes in pass@1/pass@5, and the already available dataset difficulty categories. These categories have an external meaning but should remain exploratory subgroup descriptions, not evidence that difficulty is the causal mechanism. Inspect output extraction, test execution reasons and termination before attributing a difference to model behavior.

A condition chosen after reading failures must be labeled discovery. It needs independent confirmation before supporting a new method. Selecting tasks on baseline success and then comparing SSD creates selection bias; reusing the selected outcomes as confirmation would preserve that bias. Do not define a condition as merely the set of tasks on which SSD lost.

Continue recommended-decoder and crossed-decoder comparisons before claiming a weight effect. Equal token ceilings and equal sample counts do not equal realized compute. Report generated tokens and elapsed time alongside correctness. Reordering completions by their observed lengths, retaining the shortest successful answer, or stopping at the first privately verified success would use information unavailable to an unverified deployment policy; such curves cannot be presented as an ordinary decoding policy without declaring that information.

No numerical sample-size target follows from this note. For illustration only, p=0.1 requires 29 independent trials for at least a 95% chance of one success. This is neither proof of support nor an instruction to repeat every task 29 times. Any further computation must answer a concrete remaining question after the current evidence is examined.
