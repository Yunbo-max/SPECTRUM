# Rebuttal software verification

This is software evidence, not a new model result.

The integrated source at commit `65a461eb822849ce8d9ed93641907dfbc465c00f`
passed the complete repository CPU suite: **530 passed, zero failed, zero
errors, zero skipped** (29.089 s) in GitHub Actions run `41745966306`.
The attached JUnit XML, tested-tree hash, environment and source archive bind
that statement to the exact integrated source. The integration worker used a
normal fast-forward push only after passing the full suite.

A subsequent preparation-resume repair preserves existing verified model
receipts, downloading only missing backbones and refusing corrupted snapshots.
Its two new tests failed before that repair and passed afterwards. The combined
local targeted set passed **47 tests**. The ordinary read-only CPU workflow runs
the full suite again on the final commit; consult that run for final counts.
The one-time write-enabled integration workflow has been removed.

The initial baseline check had 507 passes and two missing-EvalPlus dependency
failures. Installing the declared `evalplus` extra fixed the environment; this
was not an algorithmic improvement. No tests were removed or skipped to hide a
failure. A staging-source CI run before diagnostic integration was incomplete;
only the integrated/final source is the delivered experiment code.

No new GPU training, 7B memory qualification, generated-program benchmark,
method win, or complete rebuttal result is claimed by this delivery. Historical
results and data are unchanged. Core retains the original all-token SFT;
completion-only is a separately labeled matched four-arm ablation. PI-SPECTRUM,
Android GUI and adaptive SFT-KL merging are not part of this rebuttal update.
