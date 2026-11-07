# Web → Local: final SPECTRUM rebuttal cases

Date: 7 November 2026. Repository: `Yunbo-max/SPECTRUM`; publication target:
literal `main`. Status: **generated_unexecuted_pending_local_acceptance**.

## User-authorized deliverable

Continue specture2; prepare the final experiments for every recorded reviewer
concern, one launchable file and save root per case; fill uncovered comparisons;
update GitHub; return a reviewable summary for the user's confirmation.
The current turn authorizes source publication. It does not dispatch new GPU
experiments, restart an old queue, schedule automation or submit a rebuttal.

## Read these first

1. [Final experiment/run guide](../../docs/ICLR2027_FINAL_CASES_ZH.md), including
   [complete pinned input acquisition](../../docs/ICLR2027_FINAL_CASES_ZH.md#download-datasets-and-models).
2. [Every recorded reviewer concern](../../docs/ICLR2027_REVIEWER_COVERAGE_ZH.md)
   and [English response draft](../../docs/ICLR2027_REVIEWER_RESPONSES.md).
3. [48-case catalog](../../experiments/iclr2027_rebuttal/cases.json) and
   [machine-readable mapping](../../experiments/iclr2027_rebuttal/reviewer_case_mapping.json).
4. [Workflow checkpoint](WORKFLOW_CHECKPOINT.json) and
   [source-review record](SOURCE_REVIEW.md).

## Integration provenance

Main before integration: `5c8d1ebc587c57c84b6c0fb2ff7545fdade67117`.
The c00–c36 lineage comes from `d033641eee45236477f05cd587bb992ad1a899df`.
The alternate c00–c26 branch `6f4d2a050ce6ea66e6d35f1077c94464558f73b7`
uses conflicting IDs and was not adopted wholesale. Its three-state diagnostic
source was selectively reviewed and integrated. The repaired post-reference NLL
conversion is grounded in `118d39c31d0181d858110ac3eda9b4297015d667`.
Local historical evidence inventory came from `9d9ff1dad6bfa5d337bceab82282f11a33858afd`;
raw GPU directories were not mounted or reverified in Web.

The final publication commit containing this file is the delivered source
identity. Read its exact Git SHA on GitHub and pin the Local checkout to that
revision. Never substitute a guessed commit or a previous branch SHA.

## What changed

- Stable c00–c36 meanings plus c37–c47 appended controls; 48 wrapper files.
  One case per invocation, frozen config/data/source/dependency identity,
  nonoverlapping output, exclusive lock, per-attempt stdout/stderr/exit receipts.
- New work uses bwrap. Fresh HumanEval+ preparation carries the official
  complete fixture and records its checksum; old preparations remain frozen.
- Original 1.5B/five-round/512 controls and 7B/ten-round/4096 extension are
  separate. Main's existing 72-case ten-round queue remains intact.
- Missing direction/strength, information/token, seed/family, layer/refresh,
  decoder/synthesis, weight interpolation and human semantic comparisons have
  explicit cases. Independent top-p controls are c46/c47.
- The matched-token trio c10/c11/c44 includes all 50 replay references in the
  same 7.2M shifted supervised-token target minimum per round, with declared
  whole-record bounded overshoot and separately reported actual counts.
- Learned gains are compared with Fixed40 and Fixed50 and existing schedules.
  Ordinary LoRA SFT is unchanged: no learned loss weights or adapter update scale.
- Optional pre-native/pre-spectral/post-native DEV30 measurements, post-SFT
  reference NLL and finite-prefix raw-logit KL are preserved as diagnostics.
  They do not establish theoretical trajectory bounds or tune on heldout tests.
- c26 prepares a salted blinded packet; its separate annotation summary accepts
  human-reviewed labels, reports missing judgments and the common-eligible
  sampled-correct human D4. It never invents semantic pass@64.
- Historical analysis validates actual provenance and keeps incompatible,
  incomplete or missing evidence visible. Completion is not inferred from a
  status word or from a few metrics in an audit CSV.

## Evidence status and limitations

No project import, pytest, model load, generation, training or native benchmark
execution was performed by Web. Authored tests and successful source parsing are
engineering preparation, not Local acceptance. The old main queue's 64-test
record predates this integration.

Review coverage is against **18 recovered project summaries** for w3G2, FUKc and
ygkV; verbatim original review note bodies were not recovered. Before submitting,
check the original text for omitted subquestions. The known “interpolation or
KL-to-initial” request is covered by the selected interpolation alternative;
dedicated training-time KL-to-initial is unimplemented and unclaimed.

The historical audit has contradictory aggregate/arm-level statements. Do not
promote Fixed seed44/45, Llama Learned, r8/10 runs or SSD final n64 to complete
without raw receipts. Existing summaries do not prove Learned dominates Fixed
or SSD. Normalized `D4_cond_cov` is not the unnormalized correct-sample richness.

## Next Local actions

Recover the actual execution host/environment, source revision, model/data
fingerprints, active processes, GPU lease, memory and finite budget. Preserve
historical checkouts and directories; use a separate checkout for this source.
Run the guide's authored software acceptance and native sandbox checks. Qualify
real maximum-length memory before choosing concurrency. Host/VRAM/run time are
unknown here; profile names do not certify them.

Audit and reuse admissible history first. Prepare only selected cases. Each
explicit `cNN.py run --execute` is an inner foreground command for the existing
Local research harness. Freeze an actual experiment-run-plan and resource
envelope before executing; this handoff contains no invented approved digest.

Return full sealed raw evidence, per-task summaries, across-seed variation,
operator/cost diagnostics, exit logs and unresolved failures. Keep unfavorable
outcomes. Fill the reply draft only after these outcomes support the wording.
