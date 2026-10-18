# B/C: what the current comparison can and cannot establish

The released SSD card reports LCBv6 pass@1/pass@5 improving from34.0/41.0 to41.5/56.8. These are author-reported values, not our results. They already argue against assuming a general loss of useful sampling coverage after SSD. The ongoing baseline/SSD comparison is a reproduction and diagnostic control; an overall accuracy or pass@5 improvement would not itself be a new research finding. [Checkpoint card](https://huggingface.co/apple/SimpleSD-4B-instruct), checked2026-10-18.

The same card explicitly gives training sampling T=1.6, top-p=.8, top-k=20. This resolves the distinction from the released repository's example data-generation config (T=1.5 and shortest-10% filtering). Use1.6 for a null tied to this released checkpoint; do not infer its training recipe from the example config. The current evaluation temperatures remain base.7 and SSD1.1.

The paper's Section3.3/Figure2 already compares SSD against a broader base-temperature sweep, and AppendicesA/B/C analyze conditional support compression, temperature composition and context-dependent effects. A result from only our two matched temperatures cannot refute or replace that stronger comparison. Likewise, an entropy change, rank change, or generic lock/fork story alone is not a new D mechanism. Sources: saved SSD.txt, Section3.3, AppendixA, AppendixB, AppendixC.4; [paper](https://arxiv.org/abs/2604.01193).

## An explicit decoder null

For a prefix h, let p(v|h) be the base distribution. Let S(h) be the support retained by the actual training sampler after temperature a, top-k, then top-p. An ideal, unrestricted student that exactly fits that conditional target has

q(v|h) = 1[v in S(h)] p(v|h)^(1/a) / Z(h).

Before any further evaluation truncation, decoding q at temperature b gives probabilities proportional to 1[v in S(h)] p(v|h)^(1/(a b)). The mask survives. Therefore replacing the whole procedure with a single base temperature a*b generally fails when S(h) was formed under a different temperature. The top-p operation renormalizes within the top-k survivors; its order matters. This is an implication of the paper's existing idealization, not a claimed novel theorem.

An explicit nested-sampler control would first determine S(h) at a=1.6, then temper within that fixed support by b, then apply the evaluation top-k/top-p operation. It needs no additional model or correctness information. It tests the exact-fit conditional null, not finite-training equivalence: the real model has finite capacity, different prefix occupancy, nonzero tail probabilities, and parameter sharing across contexts. The paper's already analyzed ideal kernel means this would be a strong explanatory control, not automatically a new method. Do not launch it merely because it is implementable; first inspect the actual base/SSD outcomes and the remaining question.

## What would warrant further C work

Use native per-task outcomes to distinguish aggregate changes, task discordances, extraction failures, timeouts and output caps. A task with zero successes in10 samples does not establish zero support. A handful of base-only successes among many SSD-only successes does not establish a systematic conditional weakness. Any proposed condition should have a coherent external meaning, survive decoder and realized-cost controls, and be checked with independent evidence before D/E. If no substantive weakness remains, record the negative result and revisit the research question.

Current runtime uses vLLM0.10.0 with PyTorch-native seeded sampling; the paper names vLLM0.11.0 at b8b302c. This is a declared dependency adaptation, not bitwise reproduction. A source audit is retained in sampler-source-audit; no running environment is being upgraded. Preserve both the source-level ordering and remaining implementation differences when reporting results.
