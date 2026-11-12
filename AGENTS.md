# SPECTRUM current agent entry

## Rebuttal writing decision — 12 November 2026

The owner selected writing from the available evidence rather than automatically
expanding the experiment matrix. Read the [current author packet](rounds/20261112-rebuttal-draft/README.md),
[18-issue map](rounds/20261112-rebuttal-draft/REVIEWER_COVERAGE_ZH.md), and
[source tables](rounds/20261112-rebuttal-draft/EVIDENCE_TABLES.md).

- Status is an author-review draft, not an OpenReview submission or a revised PDF.
- Prioritize supported strengths, with material adverse results in the replies
  to the questions they directly affect. Do not turn a small observed drop into
  a noninferiority/equivalence claim without the appropriate analysis.
- Fixed is the original main method. Learned, CGL, historical 4096 results and
  single-round n128 evidence keep their separate scope and provenance.
- Three review bodies/note IDs remain unavailable; the mapping covers 18 saved
  summaries, not independently verified completeness of the original reviews.
- Preserve the experimental catalogs, original results and live source pins.
  Do not launch new experiments or post comments as part of writing without
  applicable authorization. Existing authorized runtime work is not cancelled.
- Deliver the writing packet to main with expected-parent/readback checks.

## Selected continual-gain extension — 8 November 2026

Read [the guide](docs/CONTINUAL_GAINS_ZH.md),
[method](rounds/20261108-continual-gains/METHOD.md), and
[handoff](rounds/20261108-continual-gains/WEB_HANDOFF.md), including data/model
acquisition. The owner selected conditional conflict handling on generation-time
gain parameters; this is a bounded extension, not a new open discovery campaign.

- Web prepares source only. Status is generated_unexecuted: no project tests,
  model loads, scientific downloads or GPU jobs were run by this delivery.
- Cases cg00–cg15 have independent wrappers, plans, outputs and attempt logs.
  First intended comparison is cg00–cg03; reading the catalog starts no work.
- Freeze first-domain FIT geometry for the whole lineage. Inherit one reduced
  gain state; never reset it or silently rotate coordinates at a domain change.
- Historical FIT memory is explicit. Guard is final-only veto and evaluation
  labels never enter fitting. New/old gradients use the same current backbone,
  incoming state and geometry. No SFT/GRPO gradient surgery is added to students.
- Check every old-domain endpoint loss and actual cast/fold feasibility. Failed
  candidates restore incoming gains, not identity. KL is anchored to the incoming
  controlled policy; this is distinct from old round-local Learned.
- Frozen-backbone limits persist from domain exit. Self-distillation limits are
  calibration-entry limits on the current student, not a post-SFT no-forgetting
  guarantee. Report native and controlled evaluation for all domains each stage.
- Preserve committed checkpoint receipts on resume; do not repeat completed SFT
  after an evaluation interruption. Keep incompatible/partial attempts intact.
- Do not edit or renumber the old rebuttal catalog, the 72-case queue, the 14B SPD
  studies or historical results. Preserve live checkouts at their source pins.
- No diffusion, automatic broad sweep, runtime capacity claim or scientific PASS
  is part of this source delivery. Publish main with expected-head/readback checks.

## ICLR 2027 final rebuttal cases — 7 November 2026

Read [the final guide](docs/ICLR2027_FINAL_CASES_ZH.md),
[reviewer coverage](docs/ICLR2027_REVIEWER_COVERAGE_ZH.md),
[current handoff](rounds/20261107-final-rebuttal/WEB_HANDOFF.md), and
[input acquisition](docs/ICLR2027_FINAL_CASES_ZH.md#download-datasets-and-models).

- Current task is source preparation for the user's experiment confirmation;
  no new GPU jobs, background queue or project tests were launched by Web.
- Canonical cases are c00–c47 in `experiments/iclr2027_rebuttal/cases.json`.
  Each has its own wrapper, frozen plan, output, process lock and attempt logs.
  A different 27-case branch reuses IDs with different meanings; never mix it in.
- Original 1.5B/five-round/512 study and 7B/ten-round/4096 extension remain
  distinct. Preserve main's separate 72-case queue and all old configurations.
- Reuse history only after actual source/data/decoder/native receipts match.
  Resume old jobs only at their original source revision; do not remove seals.
- Fixed remains the paper's method. Learned fits full-spectrum K/V gains,
  uses ordinary raw-output LoRA SFT, unit adapter merge, no token-loss weights.
- Use native bwrap scoring after host qualification. Fresh HumanEval+ data
  must include the sealed official fixture, not prompts alone.
- Status is generated_unexecuted. Source inspection and authored tests do not
  establish runtime correctness, GPU capacity or scientific benefit. Run the
  guide's Local gates before a separately admitted, bounded harness job.
- Recover actual host/GPU/process/lease facts before choosing concurrency;
  no capacity or runtime promise is inferred from the 24gb/80gb profile names.
- Reviewer mapping covers 18 recovered summaries; original verbatim review
  bodies have not been independently recovered. Human semantic labels and all
  missing experiment results remain pending. Preserve adverse results.

## Selected text extension — 1 November 2026

For the user's learned-gain test, read [LOCAL_AGENT_RUNBOOK.md](LOCAL_AGENT_RUNBOOK.md),
[current handoff](rounds/20261101-learned-gains/WEB_HANDOFF.md), and the
[exact guide](docs/SPECTRUM_LEARNED_GAINS_ZH.md), including its
[input acquisition](docs/SPECTRUM_LEARNED_GAINS_ZH.md#下载数据和模型).

- The new arm is `spectral_learned`, with a fresh run directory. Preserve all old
  fixed/decay/entropy-adaptive configurations, results and running checkouts.
- Same 50 reference answers: fixed 40 fit / 10 guard. Fit only supplies the
  eigenspace and gain gradients; guard is final-only veto, not an independent test.
  Native probe prefixes come only from training prompts, without answer scoring.
- Learn full-spectrum gains; tie only numerically equal eigenvalues. Keep exact
  token identities, actual folded-operator checks and identity fallback receipts.
- Ordinary SFT remains unchanged. No step-weighted loss, raw-output correctness
  filtering, external teacher, GUI modification or new test-label access is added.
- This source delivery is generated_unexecuted. Local must run the authored
  software checks, qualify native 7B memory, preserve failures and return actual
  diagnostics. Do not interpret source review as passed tests or scientific gains.
- An unchanged old algorithm does not imply an unchanged source fingerprint;
  resume old runs only at their original revision. Do not delete manifests to
  force compatibility. Use expected-head publication and exact readback.

## Previous text entry — 29 October 2026

Read [LOCAL_AGENT_RUNBOOK.md](LOCAL_AGENT_RUNBOOK.md), then
[the current handoff](rounds/20261029-length4096/WEB_HANDOFF.md) at the delivered commit.
The acquisition and qualification sections are part of the entry.

- Current scope: code on Qwen2.5-Coder7B, Llama3.1-8B and DeepSeekCoder6.7B;
  math/QA independently use Qwen2.5-7B-Instruct; ARC uses Qwen3.8-27B.
- Immediate task: new4096-token Qwen Coder7B/MBPP ten-round pair; read
  [exact inputs/commands](docs/SPECTRUM_4096_ZH.md). Preserve old512 configurations
  and output roots; no automatic tau decay or cross-family protocol change.
- One training trajectory per method; no mandatory temperature/training-seed
  sweeps. The old40-job/1.5B matrix is historical, not the default new queue.
- Delivery is generated_unexecuted. Source review/authored tests are not actual
  software acceptance or scientific PASS. Qualify on the real native host.
- Separate legacy-code and27B native Conda environments. Actual current configs
  select local grading in several blocks; this is not evidence of bubblewrap
  qualification. Check actual evaluator/host receipts before scientific claims.
- Preserve historical data/results, running checkouts, sealed protocols, private
  randomization and unfavorable outcomes. Never conflate MBPP500, MBPP+378,
  HumanEval+164 or the historical author-LCB protocols.
- Qwen3.8 is hybrid: explicit full-attention K/V targets only; this is not GDN or
  vision adaptation. ARC uses deterministic all-frame text observations.
- ARC calibration requires real successful independent-game trajectories and native
  replay. Heldout games never supply training/calibration references. The current
  ARC32K-inference/16K-training length mismatch remains unresolved.
- Restore actual SSH/GPU/process/lease state before native Local-harness execution.
  Do not infer liveness from saved status or restart unknown historical watchers.
- Return raw receipts/outputs/native replay. Keep secrets, bulk gated data/model
  weights and seed values out of public Git. Publish with expected-head readback.
