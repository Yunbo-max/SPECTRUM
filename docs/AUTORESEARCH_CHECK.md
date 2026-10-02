# running-autoresearch check: SPECTRUM

Date: 2026-10-02. Entry **M**: existing method, implementation and recorded results.
Mode: audit → evidence-repair implementation. Destination: `Yunbo-max/SPECTRUM`.
No new method search, model generation, training, benchmark execution or paper
claim certification was performed in this development session.

## Decision

**Keep the current method and original problem; complete the discriminating
comparisons.** The scientific value is measuring and attempting to retain the
distribution inside correct code outputs across repeated student updates.
Naming an outer loop is not itself a new self-improvement capability.

| Check | Evidence / decision |
|---|---|
| Natural observation | Historical MBPP shows rising pass@1 and falling correct AST richness over repeated learning. Aggregate curves are not a complete per-task natural-failure census. |
| Task consequence | Vanilla's recorded pass@64 decreases at the point estimate, with a task interval crossing zero. Correct AST richness loss is larger. Do not turn this into a proven causal lifelong-learning failure. |
| Strong simple baseline | SSD is indispensable: its historical n16 richness exceeds SPECTRUM on some endpoints. Its formal n64 fifth-round comparison was missing. |
| Extra information | SPECTRUM uses fixed references; Vanilla/SSD do not. A new direct fixed-anchor replay control tests a simpler use of that information. |
| Resource alternative | Record count did not match tokens. New whole-record exposure controls match a declared SFT target budget, with measured overshoot and resource costs. |
| Geometry necessity | Projection, spectrum-matched random orientation, matched isotropic gain and fixed round-one geometry isolate separate design choices. |
| Decoder alternative | Three fixed evaluation decoder variants plus the common decoder retain initial-model and student results; no best-policy selection. |
| Generalization | New scale jobs actually train the methods on four backbones; the historical 20-cell initial-model matrix cannot substitute. Transfer stays within coding. |
| Prior-work collision | Iterative SD, raw-output SD and SD diversity loss already have precedents. Keep the conditional-correct retention question and explicitly test the full-rank generation mechanism. |
| Formal gate | Natural Gate 0 and exhaustive collision ADVANCE are **not certified**. This is a bounded retrospective audit and implementation of evidence repair, not an invented PASS. |

## Original problem retained

1. **Failure:** a more accurate student may sample fewer distinct correct
   implementations when it becomes the next teacher.
2. **Population:** held-out executable coding tasks under fixed sampling budgets.
3. **Prevalence:** unknown at the per-task joint-event level until a recorded
   census is computed; existing macro curves establish a population-average
   observation, not a universal per-task event.
4. **Consequence:** finite-budget correct-class discovery and multi-sample
   success, with actual resource cost reported.
5. **Simplest alternatives:** standard self-distillation, SSD/decoding changes,
   simple reference replay and generic attenuation.
6. **Falsifiable mechanism prediction:** refreshed loss-sensitive orientation
   yields retention in native students beyond what fixed or generic operators
   and equalized supervision exposure provide. If it does not, the claimed
   necessity of that component is unsupported.

This original question is not replaced by a progressively narrower novelty claim
such as “the first named loop on this one Python benchmark.” Source review and
bounded literature retrieval support planning; they cannot certify prevalence,
novelty, semantic diversity or an empirical outcome before the experiments run.

## Authoritative evidence and implementation

- Source implementation: `yuhanlydia/improving` commit
  `45195e866162df1cdf9de0169d2bf17347eb6abf`.
- Historical inventory: `EXISTING_EVIDENCE.md` and
  `research/audit/observed_results.json`; positive and mixed evidence retained.
- Claim boundaries: `research/audit/claims.json`.
- Primary-source literature: `LITERATURE_AUDIT.md`, with captured retrieval
  responses under `research/audit/`.
- Actual current method/control semantics: `CORE_AUDIT.md` and
  `FINAL_EXPERIMENTS.md`.
- Model/data lock: `configs/final/assets.json`, including source revisions,
  population sizes, architectures and evaluator labels.

## Important wording for the next manuscript

Allowed: “We study conditional-correct implementation retention across a
self-distillation loop”; “a fixed anchor is reused without ongoing generated-
sample assessment”; “local full rank avoids exact linear erasure”; and whichever
comparative benefits/trade-offs the completed matrix supports.

Unsupported: “first iterative self-distillation”; “fully unsupervised/no external
information”; “ordinary SFT is reinforcement learning”; “full rank proves
semantic diversity”; “all diversity metrics exceed SSD”; “all four models have
already been trained”; “a baseline-only matrix proves method generalization”.

No automatic result-sign gate starts extra experiments. A full software report
can be complete while the scientific comparison is mixed or inconclusive.
