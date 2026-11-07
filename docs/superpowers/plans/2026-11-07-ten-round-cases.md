# Ten-round cases implementation plan

**Goal:** A Python-readable finite queue with one method per training case and ten rounds.
**Architecture:** New isolated checkout; immutable study settings; shared base evaluation per model; per-method worker selection; explicit dependency graph for final-checkpoint transfer. Planning does not launch GPU work.
**Spec:** User requests each case to contain one method, ten rounds, and stop/clean the previous queue first.

## Constraints

- Preserve previous outputs, configurations, seeds, local modifications and code checkout.
- Plain, SSD, SPECTRUM remain independent lineages, each beginning at the original model.
- Qwen MBPP training is not automatically repeated; importing old checkpoints requires explicit provenance.
- HumanEval+, APPS, CodeContests, LiveCodeBench are heldout transfer datasets, not training datasets.
- Base is round zero; transfer selects round ten. ARC remains explicitly blocked pending native qualification.
- Scheduler starts one command at a time, verifies dependencies, and caps each GPU at 85,000 MiB.
- New queue remains stopped after preparation, matching the user's stop request.

## Work

- [x] Stop previous scheduler and scientific processes; archive/remove only stale locks.
- [x] Add and test explicit single-method / base-only code execution and optional base exclusion in transfer.
- [x] Generate immutable JSON/CSV matrix, configurations and dependencies using prepared local assets.
- [x] Implement explicit single-case execution and dependency-aware Python queue.
- [x] Validate all cases and run CPU-only regression tests; verify no experiment was restarted.

Evidence: 64 CPU regression tests passed across pipeline, matrix, transfer, and reporting. The generated matrix check verified 72 cases with no GPU work started. Independent review is recorded separately. Planning retains four Qwen source requirements, four ARC blocks, and twelve Qwen transfer dependencies rather than manufacturing completion.

## Review focus

Wrong method execution; repeated base generation; transfer before round-ten completion; configuration/source drift; duplicate queue ownership; shared GPU memory stopping multiple jobs; misleading completion when jobs remain blocked.
