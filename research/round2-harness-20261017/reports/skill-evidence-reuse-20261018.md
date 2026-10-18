# Reusable Harness Skill update .5

用户澄清：将证据复用规则写入通用 Skill，使下一次研究自动采用，而不仅是本轮项目交接。

Source commit: 2828edfb4ed64c5d05402769e4622d5ed4efcc63

- Added references/evidence-reuse-and-stage-dependencies.md and linked it from SKILL.md, S01/E01/B02 source lists, their node instructions, relevant scientific source sections and runtime guidance for worker/reviewer.
- S01 reuses sufficient benchmark/metric/comparison evidence; E01 reuses actual working target/environment/assets; B02 analyzes existing results and requests targeted diagnostics only for essential missing evidence.
- Changed claims, configuration or allocation still require relevant checks. Missing evidence is not scientific success; independent review, full coverage and native admission remain.
- Installed research-autopilot-harness 0.4.0-harness.5 through local marketplace. installed=true, enabled=true; installed Skill/runtime inventory exactly matches source hashes.
- GPU host refreshed export inventory and checked 84 nodes / 221 edges with errors=[]. This documentation/package update did not run unit tests, model/scoring experiments or a new end-to-end research cycle; future agent behavior is not guaranteed by the structural checks.
- Current live research keeps its existing pinned Skill/catalog and receives the previously saved project instruction. New programs created with this installed version load the new reusable rules; existing pinned programs require explicit migration rather than silent overwrite.
