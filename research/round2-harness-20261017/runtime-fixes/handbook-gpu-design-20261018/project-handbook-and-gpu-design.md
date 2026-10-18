# Living project handbook and GPU-aware experiment design

## One research memory from A through E

At A intake (P01/P02), create a concise project handbook in the existing research
memory, normally research-state/project-handbook.md. Reuse an equivalent existing
file rather than creating parallel sources of truth. At later-stage adoption,
bootstrap it from attributable existing records; do not restart A or invent history.
Read it on resume and before consequential design. Update the relevant portions
within the same worker after B/C/D/E decisions, measurements and negative results.
A review reads the current version and linked evidence. This is a working manual,
not an extra form, acceptance gate, database or separate agent assignment.

Keep these useful sections, allowing unknown/provisional entries at intake:
- Owner objective, motivation and intended scope; distinguish these from hypotheses.
- Gap and rival explanations, with core paper/code and checked discussion sources.
- Current idea, mathematical mechanism, conditional predictions and falsifiers.
- Experiment design: question, model/data/native evaluation, strong/simple controls,
  scientific hyperparameters, fair budgets, development exposure and acceptance scope.
- Execution profile: authorized target alias, observed hardware/allocation/free memory,
  environment/model/code revisions, per-stage parameters and measured feasibility.
- Evidence and decisions: link raw results/receipts, negative findings and uncertainty;
  explain changed assumptions, next discriminating experiment and unresolved gaps.

B updates sources and uncertainty; C updates conditions, failure/dependency evidence
and controls; D updates the mechanism and mathematics-to-code tests; E updates the
frozen confirmatory design, coverage and outcomes. Preserve old decisions/profiles
through Git or linked dated records. Pin immutable dated handbook snapshots for
active tasks/reviews; update the living index separately, never overwrite a pinned
version. Summaries never replace raw evidence. Record
provenance and observation time; never put passwords or private keys in the handbook.
An idea can be rejected; cache, hardware convenience or old memory cannot establish
scientific fit. Link question-led-experiment-selection.md when revising that fit.

## Design the question and execution profile together

Before substantial experiments, attach a plausible hardware plan to the scientific
design using the actual authorized GPU. Restore known target facts, inspect volatile
free capacity, and separate training, generation and scoring profiles. A nominal
4090/24 GB inventory is not a promise that a model, length or batch fits. Account
for weights, activations, gradients, optimizer state, KV cache and temporary buffers.
State which settings are scientific and which are operational. Use model/task/code
choices that answer the question, then adapt execution or explicitly narrow the
claim if resources cannot support that design. Do not silently replace a required
model with an easier cached one. Use measured GPU debugging to revise the plan.

Read single-experiment-batching.md. For the owner's single 4090, a supported initial
candidate ladder is 128 -> 64 -> 32 -> 16 -> 8 -> 4 -> 2 -> 1. Start at 128 when
plausible for this workload; skip sizes already excluded by reliable measurements,
memory estimates, native constraints or fixed effective-batch semantics and record
why. This is neither a requirement to provoke OOM nor a universal maximum/minimum.
An unchanged qualified profile can be reused. Run a short representative pilot in
the actual GPU environment, including the largest permitted shapes and real stage
peaks. Step down on memory failure or inadequate headroom. Stop at a stable, useful
throughput setting; compare lower candidates when measurement warrants it. Do not
run the entire ladder mechanically. All probes count against existing authority.

Name each native knob and unit: examples per device, live decoding sequences, tokens
per batch or tasks per wrapper. For generation, task_batch_size times samples per
prompt can exceed the number of live sequences; inspect the scheduler/chunking instead
of calling all these knobs batch_size. Record samples per problem separately from
execution concurrency. Decode limits and scoring concurrency have separate costs.

Consider supported precision, gradient accumulation, checkpointing, attention/cache
implementation, token/sequence limits, padding/bucketing and loader/prefetch settings.
Choose relevant knobs rather than requiring every optimization. Operational changes
must preserve scientific semantics: effective training batch, optimizer updates,
loss weighting and learning-rate schedule; sample IDs/randomness, number of outputs
and evaluation protocol. Gradient accumulation is not generally equivalent for
batch-dependent layers/losses. Dtype, quantization, context truncation, effective
batch or decoding changes may alter the claim: record and validate them as design
changes, apply fair comparator treatment, and version a successor to frozen work.
Never quietly reduce task difficulty or scientific sample count to fit memory.

Record attempted configuration, useful tokens/examples per second, peak allocated
and reserved VRAM, observed headroom, elapsed time and OOM/error outcomes using
existing pilot logs and receipts. Peak telemetry is evidence, not a new schema or
required universal percentage. High GPU utilization/VRAM occupation alone is not
the objective; prefer useful throughput and reliable completion. Keep one active
experiment, release only its owned failed attempt, retain failures and requalify
material workload changes. Update the handbook with the measured selection and
why it was chosen, never present a suggested batch as already qualified.
