# SPECTRUM agent entry

Before setup, acceptance, execution or repair, read
[LOCAL_AGENT_RUNBOOK.md](LOCAL_AGENT_RUNBOOK.md) and
[the current Web handoff](rounds/20261027-validation/WEB_HANDOFF.md) at the delivered commit.
The [download section](LOCAL_AGENT_RUNBOOK.md#download-datasets-and-models) and
[calibration/debug section](LOCAL_AGENT_RUNBOOK.md#calibrate-debug-then-dispatch) are part of this entry.

- Current delivery is `generated_unexecuted`: source review is not a test or scientific PASS.
- Preserve all historical results, existing private randomization, active plans and sealed outputs.
  Never substitute MBPP500, MBPP+378, author LCB131 or adapted LCB200 for one another.
- Keep numerical random seeds in private artifacts; public reports use replicate labels.
- Native Conda is the current host route. No automatic container fallback. Generated code
  needs a qualified OS isolation boundary; Conda and `allow_unsafe_local` are not that boundary.
- Executable research work belongs to the admitted Local harness on the restored GPU host.
  Resolve real process/lock/resource state before resuming. `start_preparation.py` on the
  research branch can start a watcher that later launches inference; it is not read-only setup.
- Do not add winner-dependent repeats, change tests, weaken checks, or omit unfavorable cells.
  Publish source fixes with expected-head readback, preserving concurrent work and pinned runs.
