# Release reporting contract

`scripts/report_release_study.py` is a derived-artifact exporter for the fixed
release manifest. It does not load weights, train, execute generated programs,
or modify experiment artifacts. The older final-study report is unchanged.

After an authorized experiment run, use:

```bash
python scripts/report_release_study.py --manifest /absolute/run/root/plan/manifest.json
```

The default destination is `release_report` beneath the planned run root.
`--output-dir` can select a separate destination. A report cannot overwrite a
source run. `--bootstrap-samples` defaults to 2,000; zero disables intervals for
development checks and does not create a confidence claim.

No experiment or report was executed while preparing this implementation.
Source tests in `tests/test_release_reporting.py` are provided for the later
authorized validation run. Source syntax was inspected without importing the
application or launching a test suite.

## Evidence requirements

Every planned job, initial model, method, and requested round has a public row,
even when its files are absent. Native and transfer evaluation use 64 draws per
task; generator diagnostics retain their separately declared smaller draw
budget. The exporter checks the planned configuration identity, completion
hashes, transfer protocol identity, task snapshots, prompt fingerprints,
sample-ID uniqueness, correctness totals, and declared metric protocol.

Missing files yield pending rows. A checksum or protocol mismatch yields
invalid rows. A comparison with mismatched task, prompt, metric, evaluator,
replicate, model, or decoder identity yields incomparable rows. These states
are not converted into zeros. CSV and Markdown missing values are `x`; JSON
uses `null`. Complete/incomplete describes retained planned evidence and does
not depend on the sign or magnitude of an observed effect.

Resource stages are enumerated prospectively for the initial model, training
rounds (including calibration when applicable), and transfer/decoder evaluation.
Missing compute records remain visible as pending rows and block completed
status. Native initial-model resource files written outside the completion
seal are marked `recorded_unsealed`; their values are never presented as sealed
evidence. Operator diagnostics require their own completion hashes.

## Statistical contract

- Report native pass@1, pass@8, pass@16, pass@32, pass@64, C64, D4, D8, and D16 for each model,
  experimental block, replicate, method, and round.
- C64 is correct Python AST richness at the total draw budget. D metrics are
  AST richness conditional on the stated number of correct draws. Neither
  establishes semantic algorithm identity.
- A paired difference bootstraps direct candidate-minus-reference task values
  on the intersection of eligible tasks. It never subtracts two marginal
  D-metric means. Exports include common task IDs, common-cohort means, and the
  marginal and paired eligibility counts.
- Own-base retention uses the ratio of macro richness on the common eligible
  task set, with paired task resampling, for C64 and every D metric. It does
  not mean persistence of particular algorithms. A zero baseline or empty
  common cohort is unavailable.
- Task intervals are pointwise 95% intervals. They do not estimate training
  replicate variation or provide multiplicity-controlled success decisions.
- Replicate summaries retain model, block, dataset, decoder, method, and round.
  They show planned and observed replicate counts, individual replicate values,
  the observed comparable mean, and sample SD only at two or more replicates.
  Partial means are marked partial. There are no invented training-replicate
  intervals and no cross-model or cross-condition pooling.
- Prospective primary comparisons are the round-five core-model native
  SPECTRUM–Vanilla and SPECTRUM–SSD effects, separately. Without a registered
  numerical success rule their decision is `not_thresholded`. Negative and
  inconclusive effects remain in every output.

## Public outputs

| File | Contents |
|---|---|
| `REPORT.md` | Endpoint table and interpretation boundaries |
| `summary.json` | Complete public report, status, and stage checksums |
| `endpoints.csv` | Initial models and each job's final planned round |
| `trajectories.csv` | Every round, metric, replicate, and task interval |
| `retention.csv` | Every round's own-base C64/D4/D8/D16 retention |
| `paired_differences.csv` | Own-base, adjacent-round, and same-round method effects |
| `primary_comparisons.csv` | Separate prospective round-five core comparisons |
| `replicate_summary.csv` | Levels, method effects, retention, and actual replicate counts |
| `ablations.csv` | Explicit cross-job mechanism and sensitivity controls |
| `decoder_effects.csv` | Fixed decoder effects and their matching main-decoder source |
| `teacher_student.csv` | Aligned previous model, generator, and native student |
| `errors.csv` | Recorded verification phase/type counts |
| `resources.csv` | Token exposure, resource usage, and missing diagnostic rows |
| `operators.csv` | Average scaling and nonscalar directionality |

Fixed-geometry and other mechanism outcomes remain control jobs, even when
they share the `spectral_soft` method name. A job's explicit `comparison_job`
selects the full SPECTRUM run for a cross-job control comparison. All fixed
decoder recipes are retained; decoder conditions are never selected by their
observed performance. Same-decoder paired effects are valid only when the
remaining declared protocol checks pass.

Generator/student diagnostics align the saved task subset and leading sample
IDs to a common draw budget, including pass@1, pass@8, and pass@16 when using
the planned 16 diagnostic draws. SSD generator/native effects are marked
incomparable because the generator changes decoding; the aligned levels and
previous-native to student-native difference remain available.

Numeric random seeds are private bookkeeping. Public files use replicate
labels and stable `job-NNN` aliases in immutable manifest order. Raw manifests,
source paths, configurations, exception text, and numeric seed fields are not
exported. The manifest checksum and stage metric/seal checksums preserve
traceability to the private source records.
