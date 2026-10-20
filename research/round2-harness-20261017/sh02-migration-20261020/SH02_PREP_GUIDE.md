# SH02 preparation and explicit start points

Python/CUDA packages install from the Tsinghua PyPI mirror. Pinned model files
remain in the verified ModelScope cache, and the pinned LiveCodeBench test data
remains in the verified domestic HF mirror cache.

## Prepare while the instance has no GPU

Start/resume preparation with:

```bash
cd /root/rivermind-data/spectrum-harness/project/research-state/sh02-migration-20261020
/opt/conda/bin/python start_preparation.py
```

This starts `install_environment.py` and the CPU-safe bootstrap if they are not
already active. The launcher records process identities and logs, and does not
start model inference. Once installation succeeds,
`bootstrap_and_base.py` checks imports and package consistency, prepares the
official evaluator/runtime and confirms the fixed dataset selection. It writes
`preparation-completed.json` and exits before any GPU smoke or benchmark run.
The environment report records whether a GPU was attached; no-GPU startup is a
valid preparation state.

## Start only when ready

After attaching the intended T4, run the FP16 engine, three-sample, resume, and
configuration-rejection smoke checks explicitly:

```bash
cd /root/rivermind-data/spectrum-harness/project/research-state/sh02-migration-20261020
/root/rivermind-data/spectrum-harness/venv-sh02/bin/python start_fp16_smoke.py
```

The smoke script never starts formal scoring. After it passes, formal base
scoring requires a separate explicit invocation:

```bash
/root/rivermind-data/spectrum-harness/venv-sh02/bin/python start_formal_base.py --start
```

The formal run uses FP16, context 17,920 and a 16,384-token generation cap. The
cap is below the author's 65,536-token budget and must be reported as a protocol
limitation. Both launchers retain command, log, exit, and result evidence.
