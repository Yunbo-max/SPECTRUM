# Work Harness .13: living project handbook and GPU-aware design

Owner requested a project manual initialized in A, updated throughout B/C/D/E with motivation/gap/idea/experimental design and actual GPU-informed settings; for the4090 consider batch128 down through8 or smaller.

Source a192921a695f9fabfd11060880587dd65aed1bfd, based on .12 source7df65f88d1bc0eaa5ade738f5c2f6b3d8222622b. Guidance is wired into the entry Skill, A P01/P02, GPU references, sustained worker and both review paths. No schema, acceptance requirement, per-call gate or extra agent stage was added.

The manual links raw sources, mathematical predictions, controls, design, hardware profiles, failed/negative results and next decisions. Existing projects bootstrap from real records without restarting A. Active jobs/reviews bind immutable snapshots while the living manual evolves. SPECTRUM now has research-state/project-handbook.md; its historical hypothesis and1.5B/MBPP configuration remain provisional.

The4090 candidate ladder is128,64,32,16,8,4,2,1 when supported and plausible. It is not a requirement to force OOM, test every size or discard a qualified profile. Models/data remain chosen for the scientific question. Actual per-stage peaks, throughput and headroom guide execution. Units distinguish tasks, live sequences, tokens, per-problem samples and training effective batch. Precision, accumulation, checkpointing, cache/attention, lengths and loader settings are considered when relevant; semantic changes need an explicit design revision and fair comparisons.128 remains unmeasured for successor workloads.

Verification ran on the authorized GPU host:479 runtime tests passed;933 Skill tests comprised924 passed and9existing skips;34 plugin tests passed, then the plugin suite was rerun after the final immutable-snapshot wording. Node validation and package builds succeeded. Independent source review and4forward scenario judgments are retained separately from automated tests.

Main/private Codex installed .13. Parity check verified36 runtime modules and418 Skill files in each profile. Live source adoption revision410 preserves cumulative usage and accepted evidence. The interrupted local .12 worker was confirmed absent and reconciled cancelled; all retained native work reached terminal state before adoption. The e1a88 manifest bridge software check completed with raw outputs retained; it does not establish scientific scoring or C acceptance. Old8,000 generations remain unscored.

Actual continuation: revision 412, C/B02, harness.planner.000151 running under .13. This is a live dispatch observation, not C acceptance or proof of calibrated batch128.
