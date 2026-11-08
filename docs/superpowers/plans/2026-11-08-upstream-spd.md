# Upstream SPD five-round baseline

Goal: integrate pinned gh540-svg/SPD caa408c699f13c209a6484f626939cf3a3dcbe18 as a separate c48/spd_upstream baseline.

Design: preserve upstream utility code and call its gradient collector, centered float32 SVD and half-KV-rank projector. Upstream aligned automatically routes code tasks to mbpp_solutions: use assertion-only next-token loss. Calibration text includes only the fixed 50 training-calibration tasks, their assertions and reference solutions. Adapt the published single-stage method to five successive teacher/student rounds, recomputing geometry each round. Keep existing rebuttal sampling, ordinary LoRA training and native evaluation budgets. Projection is folded into native K/V linear weights during synthesis; this is mathematically equivalent to upstream output hooks, with floating-point differences explicitly tested/documented. Never relabel c45.

The chosen approach integrates the upstream method into the existing matched five-round harness. Running the original main script instead would also execute unrelated baselines with different datasets/budgets and only one distillation stage. Renaming existing spd_hard would lose centered-gradient and loss differences.

Implementation:
- [x] Add failing tests for centered upstream parity, calibration provenance/restoration, c48 identity, and a real tiny five-round pipeline.
- [x] Vendor unmodified upstream utils with source attribution; add isolated adapter and method dispatch.
- [x] Append c48 and wrapper; document commands/adaptations.
- [x] Independent final code review: corrected aligned-to-assertion-only routing, tested RED then GREEN against upstream collector.
- [x] Frozen c48 local plan; dry-run command validated. 100 CPU tests passed, including upstream assertion-only parity and real tiny five-round training/resume. No production GPU work started.

Review focus: accidental test-reference leakage; upstream collector leaving parameter flags/hooks changed after failure; cached calibration accepting changed tasks/model/settings; five rounds using their preceding students; upstream code absent from source fingerprint; c45 identity remaining intact.

Ruling: use Qwen2.5-Coder-1.5B/MBPP main protocol (5 rounds, train16/eval64, generation512, same seed and fixed50 references), inferred from the current rebuttal task. Keep upstream calibration formatting and disclose its additional calibration assertion information. No claim of an unchanged reproduction of the upstream paper's full experimental recipe.
