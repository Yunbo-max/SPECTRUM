# .14: legacy export compatibility repair

Worker151 reached a nonterminal dependency checkpoint: e1a87 predictions existed, but incomplete legacy sample metadata and contrast baseline F versus unchanged arm.name decoder-only could not satisfy both scoring validation and exact protocol matching. The owner asked whether repair was proceeding; maintenance took over this runtime dependency under existing debug authorization.

Source f7771d4ff34c35c65a29536174a73bea850b819e, based on a192921a695f9fabfd11060880587dd65aed1bfd. Fixes:

- Effective-manifest helper handles legacy selection:null; invalid non-object values remain errors. New scored protocols omit null to satisfy the existing schema.
- Directional manifest completion fills only absent benchmark/test/sampling/budget metadata from the original generation contract. All original fields, ordered sample IDs, multiplicity and unknown metadata remain exact. Conflicting existing metadata is rejected. A missing denominator requires explicit sample-count units and equals original ID count; native definition and actual scorer must independently agree.
- Contrast labels may canonicalize only to unchanged original arm names. Role, code, revision, controls, sampling/budget, metrics, tests and seeds remain fixed.
- Descriptor must point to the original generation protocol. Existing outer checks still bind original prediction hash/path, completed registered native receipts, retained archives and role/group/seed.

This is metadata compatibility, not scientific acceptance. It does not force a Docker dependency, change benchmark tests, regenerate outputs or endorse the old F/P/A research plan.

## GPU-host evidence

The initial targeted8-test run reproduced null-selection error and compatible-metadata rejection (one error, one failure). Final targeted suite has10tests including same-ID reorder, sample substitution, multiplicity, denominator units, changed labels/sampling/budget, arm substitutions and invalid selection. Independent review inspected actual implementation; its reorder-test correction was adopted.

A maintenance probe on the original remote project passed _samples, _prediction_ids and matches_scored_protocol for all500 tasks×16 predictions. Prediction hash remained6b103c3a5855a195f9df478d6297970a4044f1048662fc19684b80cf016ab7f8. The probe protocol is deliberately only a stage-derived compatibility input, not a fully qualified scored protocol. Original program/stage/prediction files were not modified.

The sustained worker should now construct the complete successor scorer/definition contract and score original predictions, retaining all evaluation and lineage duties.

## Installed continuation

Main and private Codex profiles installed .14,418 Skill files per profile and36 runtime modules byte-verified. Source adoption revision415 preserved cumulative usage and accepted evidence; resume416 and actual worker152 dispatch417 retained C/B02. Runtime source and remote Skill were changed only with all previous tasks terminal. The existing checkpoint was consumed through the changed source policy; no repeated generation was launched by maintenance.

Full GPU-host regressions completed:489 runtime tests passed (including10 new metadata cases),933 Skill tests with924 passed and9existing skips,34 plugin tests passed; node validation and ZIP/wheel builds succeeded. Logs are retained. The final same-ID reorder correction is covered by the full runtime suite.
