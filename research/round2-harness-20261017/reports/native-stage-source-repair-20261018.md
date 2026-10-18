# Work Harness .7 native-stage integration

This repair implements the adopted C/D loop's deferred-scoring policy. It does not change the scientific meaning of B05, M05 or E, and does not qualify a project_custom scorer.

## Concrete fault and repair

The ordinary scientific runner required a fully qualified scoring protocol before any job; C/D native admission also required a complete baseline/control batch in each task. Consequently scorer-independent preparation, calibration, training and export could not be represented honestly. Existing SPECTRUM wrappers additionally expected future controller/attempt IDs before dispatch.

The explicit `development_stage` route binds a developmental stage program to the complete eventual comparison and retained scoring obligations. Exact stage descriptors pin one job, model/data/selection inputs, code and consumed predecessors. Runtime context is created only after actual authorization and includes controller and native attempt identity. NativeBridge v2 binds the actual controller claim; legacy identities remain v1.

Stage files use an exclusive declared publication namespace. The runner publishes successful workspace outputs, and both Harness result verification and controller collection verify those exact paths/hashes. Missing output or prior-file collision fails the run. Scored lineage and both M05 method checks verify the later scored protocol against the pinned export program and descriptor. Final scoring validation remains unchanged.

Predecessor receipts are checked against registered controller history at intake and claim, using the current database transaction when present. They must be observed decision evidence and at least one actual predecessor output must be consumed by the next job. A completed-looking JSON is insufficient.

## Independent review

The independent reviewer found three important integration defects: M05 retained direct protocol equality, predecessor metadata was unauthenticated, and random workspace outputs could not satisfy predeclared controller paths. All were addressed. Follow-up review found a nested SQLite write transaction in the new history check; this now uses the existing transaction. GPU regression fixtures cover authentic history, fabricated history, output publication, actual NativeWorker completion/collection and scored lineage. These are software fixtures, never scientific results.

## Delivery limits

Source validation, installed plugin state, explicit live adoption and actual experiment progress have separate receipts. The B02 project still needs its versioned wrapper adapter to consume runtime context and avoid duplicate publication. Its 52 existing software checks passed on hn01, but that does not establish F/P/A training, prediction export or benchmark scores.
