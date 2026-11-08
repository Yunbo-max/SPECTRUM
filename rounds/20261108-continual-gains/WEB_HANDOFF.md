# Web → Local: continual generation gains

Date: 8 November 2026. Repository: Yunbo-max/SPECTRUM, publication branch main.
Publication parent: `2c5fac3d030abd6afc189a9de57aa19e29eb6411`.
Design began at `44154a2ec882ea2b32c3d26203fae724ec15d6fb`; the subsequent
independent rebuttal-script repair is retained in this source delivery.
Source status: **generated_unexecuted**.

The owner chose conditional handling of new/old task conflicts in spectral-gain
gradients and requested code for testing. This delivery implements that bounded
extension. The design was written before the new implementation in
[METHOD.md](METHOD.md). No diffusion/ESRL implementation, reviewer claim, new
scientific result or GPU launch is part of the delivery.

## Read in this order

1. [Full guide, data/model preparation, exact cases and commands](../../docs/CONTINUAL_GAINS_ZH.md).
2. [Method contract](METHOD.md), particularly incoming-policy KL, explicit old FIT
   memory, fixed first-domain geometry and the two different retention limits.
3. [Case catalog](../../experiments/continual_gains/cases.json),
   [CLI](../../scripts/run_continual_gains.py),
   [core](../../src/improving/continual_gains.py), and
   [orchestration](../../src/improving/continual_gain_study.py).
4. [Source inspection record](SOURCE_REVIEW.md). This is not runtime acceptance.

## Intended bounded Local work

Restore actual host, environment, GPU allocation, active jobs and model/data
receipts. Use an isolated checkout pinned to the delivered commit and a fresh
output root. Preserve all historical source pins, sealed manifests, unfinished
attempts, model checkpoints and adverse outcomes. Do not change a live checkout.

Reuse the already prepared Math/QA inputs only after identity verification.
Otherwise run the guide's two explicit prepare_text_data commands sequentially.
They use the same pinned source pools and private seed; the new controller does
not add a large training corpus. Do not publish private seed values, data copies,
model weights or secrets. The current math grader is the explicitly configured
local subprocess backend, not a newly qualified Bubblewrap deployment.

Run the authored new software checks:

```bash
python -m pytest -q tests/test_continual_gains.py tests/test_continual_gain_study.py tests/test_continual_gain_cases.py
```

Relevant original gain/fold, generation, text-protocol and SFT checks are listed
in the source inspection record; execute them in the compatible Local environment.
Qualify actual 7B reference-gradient memory, causal targets, full-vocabulary KL,
actual-fold restoration, decoder context, complete checkpoint saving and native
grading before a full case. No Web toy execution can qualify these properties.

First comparison: frozen backbone, Math→QA, `cg00` native, `cg01` sequential,
`cg02` retention-only, `cg03` conflict projection plus retention. Each is a separate
bounded job. Example:

```bash
python scripts/continual_gain_cases/cg03.py plan --root runs/continual_gains_isolated_v1
python scripts/continual_gain_cases/cg03.py run --root runs/continual_gains_isolated_v1 --execute
python scripts/continual_gain_cases/cg03.py report --root runs/continual_gains_isolated_v1
```

Use host path overrides only in the first sealed plan. `run` without `--execute`
does not load a model. Explicit `--resume` requires identical bindings and committed
state; an evaluation interruption after committed SFT must not retrain the student.
Further cases are ready: reverse frozen order, then both self_distillation orders.
There is no automatic all-cases launch or concurrency/VRAM promise.

## Required evidence to return

- Exact source commit, case/config/plan/data/model/runtime identities and attempt logs.
- Fixed geometry and inherited gain hashes, entry and selected gains, gain audits,
  all per-old-domain limits/losses, guard and KL checks, projection/cast residuals,
  fallback reasons and failure receipts.
- Complete per-domain/per-stage native and controlled raw generation and native
  metrics, including task-level scores, denominators, parsing failures and truncation.
- Self-distillation raw training records, committed checkpoint receipts and hashes;
  confirmation that the saved student is native and each completed SFT ran once.
- Actual timing, memory and compute-accounting receipts. Compare projection with
  retention-only; equal calibration step counts do not imply equal compute.
- Source/operational failures separately from scientific negative results.

Source review and authored tests do not establish a passed software gate, model
capacity, old-task test retention or student improvement. Historical test results
from other commits are not evidence for this new path.
