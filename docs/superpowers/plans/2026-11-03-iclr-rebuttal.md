# ICLR rebuttal implementation plan

Goal: preserve original algorithms and historical outputs while integrating reproducible multi-model Learned SPECTRUM evidence. Base 2212a4c; transfer diagnostics da70329.

1. Run the full CPU suite. The first baseline run had 507 passes and two missing-EvalPlus dependency errors; installing the declared evalplus extra resolved the baseline run (41743061887).
2. RED/GREEN: all-arm immediate-predecessor guard, non-ignored diagnostic config, four-arm three-state instrumentation, sealed metric corruption rejection.
3. Freeze shared data and private training seeds. Core Qwen 10 rounds x3 repeats; cross-family two backbones x5 rounds; mechanism and all-arm completion-only separately labeled.
4. Foreground explicit --execute driver, source/data/config checksums, independent job locks, task-level CI separate from training-seed dispersion. Preserve missing cells.
5. Verify the final source tree with the full pinned CPU suite before publishing. Local targeted tests: 45 passed. No new 7B GPU run or benchmark improvement is claimed.

Original all-token SFT, raw-completion retention, native-weight restoration and reference-based gain fitting remain unchanged. No PI, GUI or adaptive SFT merge is silently introduced. Existing other-domain entrypoints remain separate from this driver's all block.
