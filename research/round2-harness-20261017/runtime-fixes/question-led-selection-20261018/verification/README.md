# Verification

All executable tests/builds ran on the authorized spectrum-harness-gpu-hn01 GPU host in isolated code-test directories.

- Runtime: 479 tests, all passed.
- Skill: 933 tests, 924 passed and 9 existing skips.
- Plugin: 34 tests, all passed.
- Node registry check and plugin/wheel builds completed.
- The 8 obsolete prose checks removed in prior commit b5869c2 remain independently described scenarios, not hidden automatic passes.
- See independent-review.md for source and four forward scenario reviews.

Separate local supervisor correction: observe() incorrectly rejected an available RSS sample when a short-lived owned process lacked creation identity. Reproduction: 21 tests, 2 failures; after correction: 21 passed. Signalling still requires identity validation. Thresholds and failure behavior for genuinely unavailable memory/PS/disk data are unchanged. Historical stop records contained only observation_unavailable, so this demonstrated race is not asserted as the unique cause of all prior stops.

Install verification compares every installed runtime Python module and every Skill file in main and private Codex profiles with immutable source. Administrative installation and parity checks run on the local orchestrator.
