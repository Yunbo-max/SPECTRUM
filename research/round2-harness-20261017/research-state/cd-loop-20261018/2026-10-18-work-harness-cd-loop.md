# Work Harness C/D Math-Code Loop Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. User explicitly approved the design and requested implementation; preserve that authorization.

**Goal:** Make the approved C/D experimental research loop executable in Work Harness, with targeted B revisits and independently verified automatic E entry.

**Architecture:** Explicit `work-harness-cd-v1` profile selects a pinned 84-node catalog. A small runtime module owns typed revisit validation, retained invalidations, and problem/scaleup evidence contracts. Scoped canonical admission enables diagnosis/development without pretending it passed legacy Gate0; old profiles retain exact behavior.

**Tech Stack:** Python standard library, SQLite CAS state, immutable JSON pins, Markdown Skill sources, existing native runner and evaluator.

**Spec:** docs/superpowers/specs/2026-10-18-work-harness-c-d-math-code-loop-design.md

## Global Constraints

- Work Harness only; no changes to other five plugins or direct cache edits.
- Keep user-selected GPU, serial execution, independent reviewer, actual native evaluation and E fairness/freeze obligations.
- Preserve all prior receipts, failures, task identities, exposure, cumulative budgets and pauses.
- No arbitrary navigation, invented scientific PASS or new aggregate limits.
- Portable behavior tests run on authorized 4090; Mac orchestrates and installs only.
- Running projects adopt only at a quiet reconciled boundary with revision CAS and immutable source/adoption evidence.

## Review Focus

- Old schema/profile recovery must not reinterpret past acceptances.
- Revisit cannot reset attempts or overwrite artifact identities; changed evidence invalidates dependent scientific gates.
- A successful command or valid JSON cannot satisfy scientific scaleup.
- Direct task forgery and changed pins must fail at dispatch including remote native preflight.
- Pending/unknown work and pause must prevent adoption, never duplicate native jobs.

### Task 1: Versioned scientific guidance and catalog

Files: new assets/skill-sequence-cd-v1.json, references/cd-math-code-loop.md, references/nodes/cd-v1/*.md, existing selected policy/entry docs.
Interfaces: same 84 IDs and catalog shape; profile selects new file; old file unchanged.
- [x] Rewrite C/D node names/requirements and concrete math-code workflow, preserving official benchmark/baseline/model/data evaluation.
- [x] Add source precedence and explicit profile init example; keep legacy behavior documented.
- [x] Check every source exists and node inventory has 84 unique IDs on GPU.

### Task 2: Typed local loops and scientific acceptance

Files: src/research_autopilot/cd_flow.py, skill_sequence.py, program.py; tests/runtime/test_cd_flow.py.
Interfaces: profile(), catalog_path(), initialize_state(), context(), validate_revisit(), apply_revisit(), return_from_visit(), validate_gate(); ResearchProgram.adopt_cd_flow(...expected_revision).
- [x] Write behavior tests for profile/cursor, legal B visit/return, C/D rewind, stale gate rejection, quiet adoption CAS and retained budget/history.
- [x] Run tests on GPU; observe missing feature failures.
- [x] Implement profile-aware bindings/catalog, review-approved typed revisit requests and append-only invalidation receipts with epoch identities.
- [x] Implement problem/scaleup artifacts, real run receipt checks, same gate context for worker/reviewer, automatic D-to-E after acceptance.
- [x] Implement explicit adoption keeping historical state/source refs and pending obligations.
- [x] Run behavior tests on GPU and retain output.

### Task 3: Scoped scientific task admission

Files: src/research_autopilot/cd_admission.py, admission.py, skills/research-autopilot/scripts/research_cd.py, tests/runtime/test_cd_admission.py; program decision/proposal integration.
Interfaces: decision_refs(project, reference, goal_id, previous_ref, receipt_refs); prepare_task/check_task/validate_decision_binding; trusted sequence_binding profile/catalog/epoch and verified_ref after D.
- [x] Write scoped admission tests, run RED remotely.
- [x] Implement pinned C/D decisions and math-code experiment evidence; C/D treatment uses explicit development purpose with unchanged native protocol/scorer/time/coverage validation.
- [x] Bind E admission to program-owned scaleup receipt while retaining full frozen matrix/native scientific closure.
- [x] Recheck identical admission on remote native prelaunch; run targeted plus legacy regression tests remotely.

### Task 4: Integration, review, package and adoption

Files: plugin/version metadata, export manifest, maintenance logs, source install receipt; migration helper/runbook where required.
- [x] Run runtime, Skill and package regression checks on GPU; record failures honestly and fix affected behavior.
- [x] Obtain independent whole-change review; address important findings with regression checks.
- [x] Bump only Work Harness version; rebuild inventories, update marketplace source, reinstall via Codex CLI and verify installed identity/version.
- [x] Publish source/evidence to authorized SPECTRUM branch preserving concurrent writes, or verified ZIP fallback if remote unavailable.
- [x] Adopt into live project only at quiet boundary after backup/CAS, then observe next real packet; otherwise retain concrete pending adoption instruction and report exact boundary.
