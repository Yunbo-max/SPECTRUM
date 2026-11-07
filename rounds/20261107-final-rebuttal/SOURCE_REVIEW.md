# Final rebuttal source review

Scope: versioned source/design review for the existing SPECTRUM method and its
recorded reviewer questions. This is not a new method-discovery campaign and
does not constitute runtime, GPU-capacity or scientific acceptance.

## Independent review areas

| Area | Reviewed obligation | Evidence level |
|---|---|---|
| Reviewer coverage | 18 recovered concerns mapped to stable c00–c47 cases; original/extension separation, adverse-outcome wording, no claimed human labels | Source and recorded-review summaries |
| Runtime contracts | Per-case immutable plan/output, data/source/model/dependency identity, logs, exact task and sample populations, resume isolation | Source and authored acceptance tests |
| Historical evidence | Trace original audit sources, incompatible protocols, all calibration/decoder/budget identities; preserve partial and failed outcomes | Audit summaries and source; raw GPU files unavailable here |
| Mechanism measurements | Actual operator hashes, exact-token raw-logit KL, pre/post-SFT DEV30 ordering, causal NLL masks, common-eligible D4 | Independent source inspection |
| Native HumanEval+ | Full official fixture copied and sealed for fresh preparations; historical manifests preserved | Source inspection and authored regression cases |
| Semantic audit | Prospective 40-task selection, blinded sample key, genuine human-label requirement, missing-label denominators | Source inspection and authored checks |

## Findings addressed in this integration

- Both unfinished rebuttal branches existed with conflicting case IDs. Preserve
  the 37-case lineage and append controls rather than silently renumbering.
- Preserve the main branch's 72-case independent-method queue while integrating
  the case catalog and the learned multi-model code that was already on the
  research branch. No old run configuration is overwritten.
- Add Fixed40/Learned40+10/Fixed50, matched-budget replay, original SPD-hard
  recovery and independent top-p evaluation/training controls.
- Restore the real post-reference-NLL `target_mask` fix, using `_examples`
  before `_mean_nll`; retain missing-pre-SFT failure on student resume.
- Fresh HumanEval+ preparation previously omitted the complete native fixture;
  it now copies the exact official bytes and seals them in `output_files`.
- Separate finite-prefix raw-logit KL observation from enforced output-KL
  matching, and separate human sampled-correct D4 from full-benchmark claims.
- Prevent native weight interpolation from adopting changed source weights
  solely because a fresh hash can be calculated; verify the original seal.
- Each wrapper has a fixed case ID; a caller cannot reroute c02 by supplying a
  second `--case` option. Missing/failed scientific outputs remain unavailable.

## Focused review follow-up

The independent reviewer identified native `expected_samples` mapping handling,
interrupted-process lock lifetime, and c26 input comparability as material
acceptance boundaries. The mapping now checks the exact task-to-count object;
the advisory lock's descriptor is inherited by the owned worker; c26 binds and
rechecks the source trajectory, data, native verifier, exact sample population
and common protocol both in its plan and at packet execution. Root read back
these changes. Their runtime regression checks remain a Local obligation.

Historical-analysis review also caught a JSON hash spelling mismatch and
unfinished schema wiring. Root aligned it with the actual native producer,
repaired split names, SFT seed, teacher/student identities and main error
handling, and retained explicit unqualified states. Original native historical
manifests may qualify only through their own reconstructed fingerprint and
complete metadata; no new plan or completion seal is fabricated for history.
The independent final source pass found no remaining blocking analyzer schema
mismatch. The original audit's conflicting status summaries remain qualified
as historical summaries, not raw-level verification.

The 7.2M token protocol is a common target minimum with bounded whole-record
overshoot, not exact equality of actual tokens. This distinction is now in the
run guide, response drafts and machine-readable reviewer map.

## Validation disclosure

Web reviewed source and documentation, used Git whitespace/conflict checks and
stdlib AST/JSON/link inspection: 175 Python source files, 33 JSON files, all
48 case entrypoints and all 18 issue mappings; no missing checked links or Git
whitespace/conflict errors. See [the inspection record](SOURCE_INSPECTION.json).
No generated project module was imported or
executed, and no pytest, GPU job, model load, inference, benchmark or human label
was run/produced here. Local acceptance commands are enumerated in the final
guide. The earlier main queue's “64 CPU tests passed” is a historical record,
not a passed gate for this source integration.

GitHub publication is to be verified against the exact resulting `main` head.
That publication receipt is distinct from experimental completion. See the
delivery response for the read-back source commit; pin Local to that revision.
