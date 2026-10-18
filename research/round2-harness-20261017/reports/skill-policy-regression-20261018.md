# Skill test failures repaired — 2026-10-18

Source commit: `b5869c2467df0efaef96f3254852523c181a75b1`.
Source base: `486d8ec0c256a0b6e22527c8ebe836a35d468091`.

Eight failures came from obsolete prose/profile assertions, not demonstrated
runtime failures. They assumed the Chat starter and old global cooperation
prerequisites. Current Work Harness uses local/SSH execution and applies shared
claims to actual concurrent independent participants.

The narrow fix migrates those eight exact-text assertions to documented
independent agent scenarios, preserves all executable tests and leaves production
instructions/runtime unchanged. Agent decisions preserve real goal scope,
remaining budgets, truthful continuation, solo startup, shared task ownership,
access/authority boundaries and incremental synchronization.

## Verification

All executable verification ran on the authorized hn01 host:

- Pre-change targeted checks reproduced exactly the same eight failures.
- Final full Skill suite: **933 tests, 924 passed, 9 existing skipped, zero errors/failures** (74.596s).
- Plugin suite: **34 passed** (51.428s).
- Canonical 84-node check: no errors.
- Eight independent agent-consumption cases met their substantive boundaries;
  these are manual acceptance cases, not automated unittest passes.
- Independent diff review found no substantive regression.

An initial full rerun used system Python and had two missing-SciPy errors. The
existing configured venv already had SciPy 1.17.0; rerunning with its explicit
interpreter resolved both. All failed and successful logs are retained.

## Deployment scope

This is source test maintenance. The running installed `.11` Skill and program
remain pinned to their existing bytes; no restart/adoption is necessary for a
test-only change. Do not claim installed package tests were changed or a fresh
479-test runtime rerun occurred. Existing research can continue independently.

Artifacts: `../runtime-fixes/skill-policy-regression-20261018/` contains the exact
source patch, repeatable scenario inputs, coverage mapping, independent decisions
and original GPU-host logs.
