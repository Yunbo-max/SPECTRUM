# Web → Local: 4096-token length-budget repair

Parent source: `ab6f28a9eae9912acfbd27a6409195be46d1ff94`.
Status: **generated_unexecuted**; source/config/navigation review only.
Read [AGENTS](../../AGENTS.md), [current runbook](../../LOCAL_AGENT_RUNBOOK.md), then
[exact commands, inputs, checks and return files](../../docs/SPECTRUM_4096_ZH.md).

The user's decision is to raise the existing7B generation cap to4096 and align
training length. This is a bounded repair/diagnostic of the existing method, not
a new algorithm or evidence that longer generation fixes recursive collapse.
Both ten-round arms retain the same decoding, LoRA and tau; fresh4096 output roots
preserve original512 runs and archived launch payloads. Cross-family/math/QA/ARC
configs are unchanged. README/domain guides now describe their actual defaults.

Before native execution, restore actual host, environment, model/data hashes and
existing budgets. Run the documented regression tests and qualify6144-token SFT
capacity using native development inputs. No GPU/model/test result was produced
by Web. Record the delivered SHA from the delivery receipt, not this parent SHA,
in the new run. Do not update any live sealed job to the new implementation.

Hypothesis: some observed failures may reflect a512-token ceiling and repeated
SFT truncation. Relevant outcomes are unchanged native pass@1/pass@64/coverage,
EOS/length-cap/repetition statistics and zero additional SFT truncation. Longer
completion without recovered correctness does not confirm that hypothesis.
Preserve every round and negative result. Historical512 versus fresh4096 curves
are a developmental comparison with changed source/budget, not compute-matched
prospective confirmation. CPU tests or a completed run cannot establish benefit.

Known independent ARC blockers:32K inference versus16K training/calibration,
genuine successful calibration reference availability, and coordinate loss in
the secondary action-diversity statistic. ARC native scores were not changed.
No ARC benchmark run or claim of27B failure is supplied by this handoff.
