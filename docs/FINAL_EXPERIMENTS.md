# Final experimental contract

Status: implemented experiment plan; execution and scientific conclusions pending.
Planning seals the current source, prepared snapshots, asset revisions, private
randomization and commands. Historical results stay separate from these runs.

## Main scientific question

When a model repeatedly learns its own unselected completions, can a temporary
reference-calibrated generation intervention preserve more correct implementation
breadth in the subsequent native student, at an explicit correctness and resource
cost? This question remains about coding, not an asserted general lifelong-learning
law. Looped Self-Distillation names the outer learning protocol; earlier iterative
self-distillation is acknowledged.

## Fixed finite matrix

| Block | Backbones / replicates | Arms | Rounds per arm | Training arm-rounds |
|---|---|---|---:|---:|
| `core` | Qwen Coder 1.5B, three independent replicates | Vanilla SD, SSD, SPECTRUM | 5 | 45 |
| `scale` | Qwen Coder 3B, 7B; DeepSeek Coder 6.7B; one replicate each | Same three | 5 | 45 |
| `mechanism` | Qwen Coder 1.5B, core replicate r1 | Projection, random soft, isotropic soft, fixed geometry, fixed-anchor replay | 5 | 25 |
| `token_matched` | Qwen Coder 1.5B, r1 | Vanilla SD, SSD, SPECTRUM | 5 | 15 |
| `diagnostic` | Qwen Coder 1.5B, r1 | tau=0.5; tau=2; completion-only Vanilla/SPECTRUM | 1 | 4 |
| **Training total** | 13 grouped jobs | | | **134** |
| `transfer` | Six core/scale source jobs | Each initial model and each final student on four transfer datasets | Evaluation only | 24 jobs |
| `decoder` | Core Qwen Coder 1.5B r1 | Each initial model and three final students under three alternative decoders | Evaluation only | 3 jobs |

Each grouped training job evaluates one shared initial model, then maintains
separate method lineages from that initial model. Every method starts from the
same pinned weights; it does not train on another method's checkpoint.

## Generation, calibration and training

The main round uses 291 MBPP training prompts × 16 raw completions = 4,656
synthetic records. Prompts/anchor/validation/test remain disjoint and fixed.
SPECTRUM recalibrates from the same 50 reference completions before every round.
Completion loss masks prompt targets, but K/V output-gradient collection includes
every nonpadding position, including prompt positions and zero gradients.

The uncentered gradient second moment is normalized by its maximum eigenvalue.
For normalized eigenvalue mu, the SPECTRUM gain is `1 / (1 + tau * (1 - mu))`.
Tau is fixed to 1 in the main study. Operators are folded into native K/V weights
and biases before RoPE; restoration precedes ordinary single-LoRA SFT.
This is a local invertible linear map at finite strength, not a theorem of
semantic diversity preservation.

| Setting | Frozen value |
|---|---|
| Main synthesis and native decoder | temperature 0.8, top-p 0.95, top-k 0 |
| SSD synthesis decoder | temperature 1.5, top-p 0.8, top-k 20 |
| MBPP prompt / completion cap | 1,024 / 512 tokens |
| Transfer prompt / completion cap | 4,096 / 1,024 tokens |
| Calibration / SFT maximum length | 1,536 tokens |
| Main SFT | one epoch, all nonpadding causal targets including prompt |
| Microbatch / gradient accumulation | 1 / 16 |
| AdamW learning rate / weight decay | 1e-5 / 0.01 |
| Cosine warmup / max gradient norm | 0.03 / 1.0 |
| LoRA targets | q_proj, k_proj, v_proj, o_proj |
| LoRA rank / alpha / dropout | 8 / 8 / 0.05 |
| Precision / quantization | BF16 dense parameters / none |
| Gradient checkpointing | non-reentrant |
| Native evaluation | 64 samples per task at every MBPP round and final transfer |
| Generator diagnostics | same fixed 128 MBPP test tasks × 16 samples each round |
| Checkpoints | all retained, fifth round is the predeclared endpoint |

SSD is an **adaptation of its decoding recipe to the common loop**: same prompts,
record count, LoRA schedule and native evaluation decoder as the other arms.
It is not a full reproduction of the original paper's scale, task mixture or
best tuned inference recipe. This distinction must remain in the paper.

## Mechanism and information controls

- Projection keeps the top half of native output dimensions under the same
  reference geometry. It is a design control, not a claim to reproduce every
  published SPD implementation choice.
- Random soft matches the full gain spectrum and uses a seeded random orthogonal
  basis. It tests whether loss-sensitive orientation matters.
- Isotropic soft matches the Frobenius distance from the identity using one
  scalar gain. It does not also match activation displacement or output KL.
- Fixed geometry stores the exact round-one operator tensors and reuses them
  on later native students. It does not compose interventions into saved weights.
- Fixed-anchor replay retains every synthetic record and adds one copy of the
  same 50 references to each round's corpus. It uses Vanilla synthesis. This is
  a simple supervised, equal-reference-access baseline; extra tokens and any
  difference in label scope are reported.

Mechanism arms use the same private r1 trajectory randomization as the main
reference. They are not five independent replicates merely because there are
five rounds.

## Matched token exposure

The separate token block prescribes **7,200,000 supervised causal targets per
round per arm**. Every generated record is encoded and exposed at least once;
complete corpus permutations are repeated until the budget is reached. The
last whole record remains intact. With maximum length 1,536, the actual count
exceeds the target by at most 1,534 tokens. This is at most 0.022% mismatch.

The target exceeds `291 * 16 * (1536 - 1) = 7,146,960`, so even the largest
permitted corpus can receive one complete exposure without discarding records.
This block can require several passes over short corpora, and is intentionally
more expensive than the one-epoch main comparison. The same per-example loss
definition is retained. Optimizer steps, generation tokens, calibration cost
and wall time need not match. The report must say **matched supervised-token
exposure**, not equal compute or an exact floating-point token identity.

## Decoder robustness

Keep the original common decoder result. On core r1, evaluate the same initial
model and all three round-five students with three further fixed policies:

| Decoder ID | Temperature | top-p | top-k |
|---|---:|---:|---:|
| `cool` | 0.6 | 0.95 | 0 |
| `warm` | 1.0 | 0.95 | 0 |
| `ssd_recipe` | 1.5 | 0.8 | 20 |

Report every policy as a secondary sensitivity grid; select none as a new main
winner. The initial model under these policies is the decoding-only comparison.
No decoder result feeds back into synthesis or training. Decoder conditions are
separate groups, not extra independent training replicates.

## Metrics and analysis

Use pass@1/8/16/32/64, correct AST richness C64, and correct-count-matched richness
D4/D8/D16. The implementation uses finite-pool rarefaction. D comparisons use
common eligible tasks and disclose the number; marginal eligible means cannot
be subtracted and called paired effects. Initial-relative richness is a ratio
of expected class counts, not identity overlap of algorithms. AST is a structural
proxy, not semantic algorithm equivalence.

Primary comparisons: fifth-round SPECTRUM versus Vanilla SD, and SPECTRUM versus
SSD, separately, on the three independent core trajectories. Scale, transfer,
mechanism, exposure and one-round diagnostics remain separately labeled.
Pointwise paired task-bootstrap intervals use 2,000 resamples. Replicate means
and sample SD are descriptive, and only computed within a compatible model,
block and condition. A single-replicate scale result does not receive a claimed
training-variance estimate. No post-hoc composite score is used to manufacture
an overall win.

Generator diagnostics compare the same tasks and leading sample IDs before
modulation, during generation, and after native-student learning. They establish
transmission only to the extent supported by recorded contrasts; SSD synthesis
uses a different decoder and must be marked accordingly. Diagnostics never
determine the samples retained for training.

## Completion and interpretation

The code stops when selected planned jobs are complete, regardless of effect
sign. It never extends the number of rounds or samples to chase a favorable
outcome. The finite plan is frozen before model generation. Missing or corrupted
artifacts make a cell incomplete, not a model failure score.

The software does **not** certify a research Gate A or assign PASS from a positive
point estimate. The historical audit lacks a completed natural-failure census
and strongest-alternative qualification; it is an evidence-repair starting point.
This release freezes the contrasts and data collection needed for that judgment.
If SSD or simple controls match the joint endpoints, report that result and limit
the claimed need for spectral geometry. If refreshed geometry gives no advantage
over fixed geometry, do not claim recalibration is necessary. Better AST richness
alone does not prove general continual learning, mathematical transfer or
lifelong self-improvement.
