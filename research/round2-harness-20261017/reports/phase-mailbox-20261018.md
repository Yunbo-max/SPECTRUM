# Work Harness .9: controller-owned dispatch and B-memory/C loop

## Change

The .8 sustained worker called phase-native directly, which tried to open the
runtime database outside its actual sandbox write scope. A live worker heartbeat
was insufficient evidence of experiment progress. .9 makes the worker submit
atomic project-local requests; the existing dispatcher owns database writes and
native SSH execution. Existing request identity, fences, native admission,
accounting, target, receipts and scientific gates remain intact.

The dispatcher serves one native call while pumping model logs/heartbeats. The
client never opens SQLite. Native failures return to the sustained worker for
repair. Unknown jobs retain their original identities and reconciliation duties.

Before B02/B03/B04, retrieve the shared B research memory. If it does not answer
the current question, use B's paper/code/Xiaohongshu methods to refresh the exact
gap, update memory and return to C. Mathematical predictions and actual benchmark
experiments determine advancement, experiment revision or problem reselection.
Write results and boundaries back into memory, including negative results. These
are milestones in one sustained worker; B05 independent review, D verification
and formal E remain required.

## Verification

All software tests and package builds ran natively on the authorized hn01 GPU
host. Initial runtime suite: 458 passed. Final runtime suite: **460 passed in 217.589s**. Plugin suite: **34 passed**.
Node traceability check: no errors. Logs retain the intermediate short-lease
fixture failure and the successful 17.617s isolated real mailbox check.

Independent static review identified FIFO reads and directory replacement at the
mailbox input boundary. Both were repaired and received behavior tests. Final
review found no important remaining issue. A real subprocess with SQLite calls
forbidden is served by CommandWorker's actual heartbeat pump and NativeWorker;
it obtains a real native receipt while execution exceeds a short parent lease.

## Deployment and continuation

Source: `1b4f0a369fe8bca4b3d3437546bd4a3f1aebff48`.
Plugin: `0.4.0-harness.9`, installed and enabled in main and private profiles.
Both installed Skill trees match all 414 source files; all 35 runtime Python
modules match source. GPU Skill digest matches adopted source.

Quiet adoption revision258 preserved all accepted research evidence and budgets.
The same C phase was resumed under the user instruction; actual dispatch observation
will be recorded separately. No new scientific result is implied by maintenance.

Shared research memory navigation: `research-state/B-C-memory-index.md`.

## Actual worker submission readback

Actual task `harness.planner.000080`, run `3f2589c132774b9da7bfc3b4e4c3ffa1`,
uses `controller-owned-mailbox`; current consumer and service heartbeats are live.
The real sandboxed worker has submitted requests and received controller validation
responses, with no readonly database error. The retained old preparation request
needs coverage-field and code-mapping corrections. At this observation no new
production native receipt exists; the same worker is correcting its artifacts.
The GPU-host integration test receipt is software verification, not a production
research result.
