# GPU-host software checks

Host: authorized spectrum-harness-gpu-hn01, isolated /root/rivermind-data/spectrum-harness/code-tests/stage-repair.

The source is the .7 working tree based on a99fff9ac79a318f2d269e993825fa0e0124d628; exact delivered inventory is EXPORT_MANIFEST.json. These checks and synthetic subprocess fixtures are software evidence, not SPECTRUM scientific results.

- red.log: expected initial scorer-before-stage failure.
- combined.log: initial 118 runtime checks passed before review fixes.
- review-fixes*.log: retained intermediate integration/fixture failures.
- full-stage-chain*.log: actual NativeWorker/collection, stage protocol lineage and controller-history fixtures; successful follow-up 3 checks.
- final-runtime.log: 121 runtime checks passed after substantive review fixes.
- final-stage.log: final stage suite after adding predecessor transitive input transport.
- legacy-runner.log: 36 unchanged runner/Harness checks passed.
- guard-red.log, guard-green.log: host-guard regression, 18 checks passed in final run.
- b02-software.log: 52 existing B02 diagnostic software checks passed on pinned MBPP inputs in isolated GPU-host copy. No training, predictions or scoring implied.
- node-check.log/build.log: actual export/package validation on GPU host; build revision denotes the observed base until final source commit packaging is recorded separately.
