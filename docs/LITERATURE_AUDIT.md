# SPECTRUM: bounded M-entry literature and experiment audit

Audit date / cutoff: 2026-10-02. Project target: Yunbo-max/SPECTRUM.
Scope: independent closest-work audit supporting a final executable experiment package. No GPU experiments or repository edits were performed in this audit. Scientific judgments are provisional pending source-code and per-task evidence checks by the implementation team. This is not an exhaustive novelty certification.

## Decision

**REPAIR EVIDENCE; no new method is required to proceed with the current implementation.** The important question remains whether repeated learning from a model's generated data preserves a usable distribution of different correct implementations, at an acceptable correctness and compute cost. The existing SPECTRUM results motivate that question, but do not establish superiority over every self-distillation alternative.

Keep "Looped Self-Distillation" as a clearly defined operational setting and SPECTRUM as the generation mechanism. Do not claim that iterative self-distillation, label-free self-teaching, diversity collapse, or spectral/proximal methods in general are first discoveries. Do not rename Vanilla SD as SSD.

The appropriate taxonomy is **sequence-level self-distillation / synthetic-data self-training**, with generation from the current or transformed current model. It is not the demonstration-conditioned, token-distribution KL algorithm often specifically called OPSD, and ordinary SFT is not RL.

## Closest primary evidence

| Work / version read | Verified computation and setting | Consequence for SPECTRUM | Exact locator / depth |
| --- | --- | --- | --- |
| [SSD, 2604.01193v1](https://arxiv.org/html/2604.01193v1) | Samples under temperature and truncation, trains on raw unverified output with SFT. Practical implementation removes empty responses/single-line stubs. Studies decoding sweeps, support compression, exploration and transfer. | "No correctness filtering" is prior art. Qualify an actual SSD recipe rather than a weak arbitrary temperature. Compare conditional-correct implementation breadth, which pass@k alone does not identify. | Sections 2, 3.1, 3.3–3.4, 4; lines 132–184, Appendix B; D2 scientific read. |
| [SPD, 2605.22675v1](https://arxiv.org/html/2605.22675v1) | Computes masked correctness-span gradients of K/V activations from a small prompt-answer calibration set, uses top singular vectors for low-rank projection hooks during generation, removes hooks before SFT on raw samples. | Closest method ancestor. A shared-anchor projection control isolates one design choice but is not necessarily a faithful reproduction of published SPD if masks/layers/decoder differ. Full-rank modulation, folding, and recalibration must be specified separately. | Sections 3.1–3.3; equations 6–10; Appendix A.1 and Table 7; lines 110–165, 342–378; D2. |
| [SCoder, 2509.07858v1](https://arxiv.org/html/2509.07858v1) | Explicit iterative self-distillation of a code-data synthesizer; multi-checkpoint generation, multi-aspect scoring, and gradient-based influence selection against a proprietary reference set. | Iterative coding SD already exists. SPECTRUM's all-raw synthetic corpus and direct native-student retention endpoint differ. Initial fixed reference information itself is not unique. | Section 3.3, Figure 2; lines 120–128 and subsequent selection method; D2. |
| [SD-Zero, 2604.12002v1](https://arxiv.org/html/2604.12002v1) | Trains a self-reviser from successful revisions, then distills reward-conditioned teacher token feedback into generator; explicitly refreshes teacher from student for further evolution. | Iterative SD capability has been demonstrated; distinguish ongoing binary outcome feedback and reverse-KL teacher supervision from SPECTRUM raw-corpus SFT. | Section 3.4 and Figure 5, lines 192–198; Algorithm 1 lines 375–380; D2. |
| [CRISP, 2603.05433v7](https://arxiv.org/html/2603.05433v7) | Periodically refreshed teacher is the same model with a conciseness instruction; student rollouts receive token reverse-KL supervision, without GT answers or reward. Refresh interval controls compression and instability. | "First repeated self-distillation without external evaluation" is not safe. Its goal and objective differ, but the outer self-teaching concept is established. | Sections 3.3–3.4, Algorithm 1, Section 5.3.3; lines 167–223, 354–362; D2. |
| [Nicolicioiu et al., 2606.26091v1](https://arxiv.org/html/2606.26091v1) | Demonstration-conditioned self-distillation tilts an optimal policy by expected pointwise conditional mutual information. Studies semantic and functional diversity on graph paths and science QA, with fresh on-policy rollouts during training. | Accuracy/diversity separation is prior work. It is inaccurate to call this a single frozen dataset trained once: teacher and rollouts evolve during optimization. Our finite-corpus round protocol and conditional implementation occupancy are different, but "more rounds" alone is not a contribution. | Sections 2–4; Proposition 2; Section 4.2 lines 183–190; D2. |
| [iSDFT, 2609.24646v2](https://arxiv.org/html/2609.24646v2) | KL-proximal token target constrained by teacher information, plus fixed base-policy KL anchoring; demonstration-driven acquisition and cross-domain retention. | New positioning evidence since the prior draft. Not the same operator: iSDFT acts on probability targets, SPECTRUM on generation K/V geometry. Do not claim proximal retention broadly as new. | Sections 2–3; equations 3–4, Algorithm 1, lines 101–170; D2. |

Primary background: [Rao et al. 2023](https://aclanthology.org/2023.findings-emnlp.812/) explicitly uses iterative contexts/rationales with critic/NLI filtering (D1 abstract); [SIKeD](https://aclanthology.org/2025.findings-acl.513/) blends external-teacher data with self-generated strategy-specific data iteratively (D1 abstract). [Mobahi et al. 2020](https://research.google/pubs/self-distillation-amplifies-regularization-in-hilbert-space/) analyzes iterative SD as spectral regularization in a Hilbert-space setting (D1 abstract, not a transformer/KV result). [Gerstgrasser et al.](https://arxiv.org/html/2404.01413v2) studies data replacement versus accumulation and distributional collapse (D1/D2 triage). These establish genealogy; their theorems cannot be transferred directly to SPECTRUM's deep, finite-data pipeline.

[UA-RL](https://aclanthology.org/2026.findings-acl.1982/) is a correctness-and-uniqueness reward method (D1 abstract, full HTML unavailable in this audit). It belongs in related work; a benchmark comparison would use additional ongoing feedback and should not be labeled an equal-information baseline. No exact implementation claim is made from its abstract.

Conference acceptance status does not determine whether a publicly available prior method exists. The cited versions, not an assumed venue outcome, determine comparison.

## Parent problem and importance check

- **Natural failure:** after repeated post-training on self-generated code, the native student's tested correctness can increase while the number and distribution of structurally distinct correct implementations contract.
- **Population:** held-out executable coding tasks, not all reasoning, natural language, or all agents.
- **Prevalence:** aggregate MBPP curves alone do not establish how many tasks exhibit joint correctness gain and richness loss. Derive the per-task census from saved records; retain unaffected and conflicting cases.
- **Consequence:** measure finite-budget correct-class discovery and multi-sample solve probability. Claiming harm to future learning additionally needs generator-to-student transmission or a downstream task effect; richness is an interpretable repertoire proxy, not by itself proved practical harm.
- **Strongest simple alternatives:** qualified SSD / decoder-only temperature and truncation, fixed-budget replay, and direct use of the same fixed anchor.
- **Falsifiable prediction:** at controlled training exposure and decoding, refreshed loss-sensitive orientation preserves more correct implementation richness in native students than equally strong generic attenuation and a fixed operator.

Natural Gate 0 / final novelty ADVANCE are **not certified by this bounded literature audit**. Existing task records and executable-baseline qualification must determine them. The retained problem remains scientifically consequential, but adding several exclusions to a title does not establish new importance.

## Decisive experiments, ranked

1. **Primary five-round comparison, all methods under one protocol.** Initial model, Vanilla SD, qualified SSD, SPECTRUM. Evaluate rounds 0–5 with the identical native evaluation decoder and task IDs. Generate 64 outputs per task where feasible, retain all per-sample records, then estimate pass@1/8/16/32/64, correct AST richness C_k and correct-count-matched D_b. No verifier outcome may flow into synthesis, sample weighting, checkpoint selection or hyperparameter selection on test. Hold the information source fixed.

2. **Simplest alternative / correctness–diversity frontier.** Sweep a small predeclared training-decoder grid on development tasks only; include a decoder-only baseline and SSD. Either fix a common evaluation decoder for the primary contrast or give every method the same development decoder search budget, reporting the common-decoder result as well. Do not choose different temperatures by held-out test outcomes. Compare paired D_b at comparable correctness; plot both axes rather than invent a combined score. Existing SSD exceeds SPECTRUM on some diversity metrics, so this is a necessity check, not a decorative baseline.

3. **Budget control.** Existing equal record counts do not imply equal token or optimizer exposure. Report synthesis tokens, nonpadding SFT tokens, steps, calibration cost, runtime, truncation and empty-output counts. Add a deterministic matched-training-token child protocol, preserving raw records and masking only predetermined budget-excess targets or using another explicitly documented budget rule. Keep it separate from the all-record equal-epoch historical protocol. Match loss reduction, prompt masking and EOS behavior; otherwise the treatment changes in more than geometry.

4. **Directional mechanism.** Compare SPECTRUM T=U diag(g) U^T with (a) isotropic alpha I and (b) Q diag(g) Q^T where Q is fixed random orthogonal per layer/run. The random control matches the entire eigenvalue spectrum. Pick alpha with a declared attenuation norm, preferably alpha=1-||I-T||_F/sqrt(d) for matching displacement from identity, and log the remaining scale mismatch. These distinguish useful orientation from merely rescaling K/V. A nonempty measured anchor gradient is necessary, but not proof of semantic strategy directions.

5. **Recalibration and generation-to-student transmission.** Fresh C_t versus fixed C_0, identical anchor and tau. Evaluate native teacher before intervention, temporary generation policy, and native learned student on the same held-out prompts. Record whether an immediate generation effect survives removal and learning. This is required for a causal story about refreshed geometry; a round-five student comparison alone cannot identify that chain.

6. **Fixed-reference contribution.** Add direct SFT on the same anchor (or anchor replay under an explicitly matched token budget) followed by Vanilla looping. This provides the strongest simple use of the extra reference information. Distinguish initial-data acquisition from repeated reuse: an anchor reused each round is fixed supervision, not calibration used only once. A shuffled anchor can be diagnostic but is not a strong competitor.

7. **Breadth / robustness after the primary mechanism passes.** Repeat the strongest arms across independent training trajectories and at least one genuinely different model family. Frozen-student transfer to HumanEval+ and APPS Intro tests benchmark transfer, while CodeContests/LiveCodeBench test harder competitive coding with pinned versions/time windows. These are all coding domains; they do not establish transfer to mathematical proofs or writing. A 4x5 initial-model matrix alone is not a method-generalization experiment.

A fifth-round 64-sample SSD evaluation is especially valuable: it closes the currently missing high-budget comparator rather than expanding to unrelated benchmarks. Avoid running every possible full-factorial control for five rounds; qualify controls with the smallest decisive stage, then spend compute on the predeclared longitudinal question.

## Required evaluator and inference details

- For i.i.d. draws of one task with correctness probability a and conditional class masses q_j, pass@k=1-(1-a)^k; C_k=sum_j[1-(1-a q_j)^k]; D_b=sum_j[1-(1-q_j)^b]. This is an occupancy identity, not a novel deep-model theorem.
- Finite-pool estimators must use without-replacement combinatorics (rarefaction), not plugging empirical q into the population formula and presenting the biased plug-in as exact.
- D_b is defined only when a pool has at least b correct outputs. Compare methods on common eligible tasks; report that denominator and marginal eligibility. Do not substitute marginal eligible means for paired causal contrasts.
- C_k measures expected count, not class-identity retention. If the paper says preservation of the initial repertoire, add initial-class overlap as a separate secondary analysis with finite-sample detection caveats.
- AST normalization must be deterministic and saved with version/hash; exact-program, AST, and control-flow proxies can support robustness but do not establish algorithmic or semantic equivalence.
- Evaluate generated code in a constrained execution environment; finite tests operationalize correctness and are not perfect semantic proofs.
- Task bootstrap quantifies task uncertainty, not training variability. Independent trajectory replication should be reported separately; numeric seed disclosure in narrative is not required, but local run manifests need reproducible identifiers.
- Preserve old and prospective protocol identities. Prior inspected runs are developmental evidence. All new planned results remain pending until actual execution; never fill missing cells with estimated favorable numbers.

## Mathematical claim boundaries

Full-rank finite-strength T avoids exact local linear deletion and admits standard norm/resolvent bounds. It does not prove more correct algorithms, nondecreasing entropy, unchanged attention behavior, or monotonic lifelong improvement. K/V directions are sensitivity directions, not strategy labels. Weight folding is an exact implementation equivalence only at the declared linear-output location (including bias), before any transformations that do not commute with T. Numeric finite-precision conditioning should be logged.

SPECTRUM can be positioned as a principled, inspectable intervention whose semantic benefit is empirical. Its standard quadratic proximal derivation is a rationale and local guarantee, not a novel proximal theorem.

## Search coverage and handoff

Exact query families, tool responses, versions and retrieval failures are in literature_audit_raw.json and literature_audit_background_raw.json. Full primary sections were read for the six requested seeds plus the new iSDFT work; background papers are explicitly lower-depth. Two providers were used for discovery/verification. No two-empty-batch saturation, comprehensive forward citation traversal, or complete collision proof was performed. Therefore say **bounded audit with identified obligations**, not "no prior work exists" or "novelty certified."

Allowed current framing: "We study correct-solution retention across repeated self-distillation and test a full-rank, reference-calibrated generation mechanism."
Unsupported current framing: "We invented iterative SD"; "no external information"; "first diversity-collapse finding"; "all diversity metrics beat SSD"; "full rank theoretically prevents semantic collapse"; "all model/data cells demonstrate trained-method generalization."

