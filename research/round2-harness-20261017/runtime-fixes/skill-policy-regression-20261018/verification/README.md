# Skill policy regression repair

## Cause and scope

The pre-change GPU-host reproduction has the same two Chat-policy and six
cooperation-policy failures as the .11 baseline. These assertions match obsolete
sentences/profile assumptions. Current Work Harness deliberately permits solo
local/SSH preparation without a global registry, uses edition-specific execution,
and requires shared claims for actual independent concurrent participants.
Current guidance retains goal scope, truthful continuation, provenance and authority.

No production Skill instructions, executable runtime, live program pins, worker
or installed .11 package are changed by this repair. This is source test maintenance.
Changing installed test bytes would change its pinned Skill digest without adding
research behavior, so the current live procedure is preserved.

## Replacement coverage

Eight brittle prose assertions are retired, not disabled/skipped or replaced by
matching a different sentence. Their substantive decisions are covered by the
independent eight-case fixture tests/skill-policy-scenarios.json and observed
answers in agent-validation.md. This manual acceptance is separate from automated
regression and does not certify a running research service.

| Retired prose assertion | Behavioral case |
|---|---|
| test_current_chat_starter_is_first_and_preserves_scope | scope-and-target |
| test_web_contract_keeps_host_boundary_and_goal_review | continuation-evidence |
| test_entry_binds_github_before_first_task | solo-startup; local-advance-shared-claim |
| test_optional_cross_chat_read_path_removed | conversation-source |
| test_conversation_visibility_is_not_a_prerequisite | conversation-unavailable |
| test_scope_is_cooperation_not_research_sources_or_user_authority | source-authority |
| test_existing_advance_is_not_shared_admission | local-advance-shared-claim |
| test_no_scheduler_or_full_context_requirement | coordination-limits |

Existing executable coverage remains unchanged, including
`test_chat_research_goal.py` preflight-not-completion, bounded scope completion,
independent goal review, goal-revision usage retention, exhausted-budget retention
and tampered goal-source rejection; `test_chat_cycle.py` unknown-attempt no-replay,
partial/resume identity and budget preservation, pending delivery and next-action
behavior. These tests exercise the local helpers, not distributed ownership or
all agent-policy decisions. Remaining prose lints in the suite were outside this
narrow eight-failure repair.

## Reproduction and verification host

All executable checks run on the authorized hn01 GPU host, in the isolated
/root/rivermind-data/spectrum-harness/code-tests/skill-policy-regression tree.
They are CPU software checks on that host; no GPU science result is implied.
The first synchronization attempt failed because the isolated directory did not
exist. It was created and the same source was synced; no scientific job was affected.

Commands:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/research-autopilot/tests -p test_chat_goal_policy.py -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/research-autopilot/tests -p test_project_cooperation.py -v
PYTHONDONTWRITEBYTECODE=1 python3 scripts/refresh_edition_export.py --base-revision 486d8ec0c256a0b6e22527c8ebe836a35d468091
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/research-autopilot/tests -p 'test_*.py' -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/plugins -p 'test_*.py' -q
```

See original before/after logs and final results below. Test counts are reported
separately from agent scenarios; removed prose assertions are not counted as passes.

## Interpreter correction

The initial full rerun used system python3. It ran 933 tests with no assertion
failures but two errors because that interpreter has no SciPy:
`test_frozen_bootstrap_is_repeatable_and_not_a_point_verdict` and
`test_paired_t_reports_wider_small_sample_interval_than_normal`.
The error was `SCIPY_ANALYSIS_UNAVAILABLE`, backed by ModuleNotFoundError.
The already configured research venv has SciPy 1.17.0. No dependency installation
or production code change was needed. The final rerun uses the explicit existing
interpreter; retain skill-after.log as the initial failed-environment attempt.

```sh
PYTHONDONTWRITEBYTECODE=1 /root/rivermind-data/spectrum-harness/venv/bin/python -m unittest discover -s skills/research-autopilot/tests -p 'test_*.py' -q
```

## Final observed results

- Pre-change targeted reproduction: 7 Chat checks / 2 failures and 26 cooperation
  checks / 6 failures, matching the original eight names.
- Correct-interpreter full Skill suite: **933 tests in 74.596s, OK (skipped=9)**:
  924 passed, 9 existing edition-specific skips, zero failures/errors.
- Plugin suite: **34 tests in 51.428s, OK**.
- Canonical node/source check: 84 nodes, 16 regions, 221 edges, no errors.
- Independent agent-consumption cases: eight reviewed, all satisfy their intended
  substantive boundaries; see agent-validation.md for decisions and limitations.
- Independent source review: no substantive regression identified.

The suite has 933 rather than 941 automated tests because eight obsolete text
assertions were explicitly migrated to independent scenario acceptance. They are
not counted as automated passes. No runtime source changed, so the earlier 479-test
runtime result is not represented as a fresh rerun in this repair.
The collector_failed_after_dispatch line is the intentional injected persistence
failure exercised by an existing test, followed by successful suite completion.
