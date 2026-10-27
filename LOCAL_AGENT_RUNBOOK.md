# Local Codex: start here

Current round: [20261027-validation](rounds/20261027-validation/WEB_HANDOFF.md).
Status: `generated_unexecuted`; this Web delivery has not run project code, tests,
inference or training. Read [the complete design](docs/VALIDATION_20261027_ZH.md)
and [evidence inventory](rounds/20261027-validation/evidence.json) before acting.
The existing [release contract](docs/FINAL_EXPERIMENTS.md) still defines all40 jobs.

## Restore the project and actual host

The user's Local controller owns SSH and the authenticated delivery checkout.
The GPU host owns native Conda environments, inputs, workloads and raw outputs.
No remote Codex or GitHub token is needed. Do not copy private credentials into this repository.

| Fact | Source/status | Action before an affected launch |
|---|---|---|
| main code audited | `5b8c3f93d1c0122006d8c1c9c42379bb31f2f694` | Use the delivered commit in a separate checkout; preserve active run sources |
| newer research evidence | `923e84ca9b92d111535ae245e137601b8856bbf8` | Read its pinned records, not main's older Oct17 state |
| historical SH02 project | `/root/rivermind-data/spectrum-harness/project` | Confirm actual path, content and ownership after reconnecting |
| historical SH02 interpreter | `/root/rivermind-data/spectrum-harness/venv-sh02/bin/python` | Read actual `environment.json`; do not replace with base Conda blindly |
| current SSH alias/access, GPU allocation/UUID/VRAM/CPU/RAM/disk | unresolved in this Web session; Oct27 auth failed | Restore locally and record actual inventory; no guessed GPU count/profile |
| former hn01 | BF16/RTX4090 evidence, old partial samples | Reconcile process/output state if reachable; do not assume still running |
| SH02 latest persisted state | preparation complete, no GPU, watcher waiting | Inspect boot/process/start identity, locks and output hashes before resume |

Never decide from a stale PID alone. Inspect `gpu-auto-runner.json`, installation,
preparation, smoke and condition markers together with live processes. The research
branch's `start_preparation.py` also starts a watcher that can run formal inference
when a GPU appears; it is **not** a read-only or preparation-only command.

All executable project stages below are payloads for the existing admitted Local
`run_harness.py` on the restored GPU host, not instructions to launch now from Web.
Local resolves the installed harness path, actual working directory/interpreter,
resource limits and plan digest from its existing controller records. A missing
harness path or host fact remains pending; this document does not invent a new daemon.
Git reading/staging and SSH inventory are controller operations. Keep the original
research branch checkout separate from the newly delivered main checkout.

## Download datasets and models

Run input preparation as CPU tasks in the admitted native environment, with exclusive
cache-write ownership. Reuse matching complete assets; preserve partial downloads.
Before admission measure available disk and read required sizes from pinned source
metadata. Download time, full-study checkpoint storage and current network access are
not measured here. Never evict a live model/checkpoint to make room automatically.

### Existing author-SimpleSD comparison

Use the existing per-file ModelScope revision/size/SHA manifest at
[`author-pair-file-manifest.json`](https://github.com/Yunbo-max/SPECTRUM/blob/923e84ca9b92d111535ae245e137601b8856bbf8/research/round2-harness-20261017/upstream-evaluation-20261018/author-pair-file-manifest.json).
The historical deployed fetcher verifies every required file, bounded curl resume,
disk space and the shared pipeline lock. After resolving the historical path map,
its exact source-inspected payloads are:

```bash
cd /root/rivermind-data/spectrum-harness/project/research-state/sh02-migration-20261020
/opt/conda/bin/python fetch_assets.py --model base
/opt/conda/bin/python fetch_assets.py --model ssd
```

These two tasks are sequential because they share a lock/cache. Each produces
`base-assets-verified.json` or `ssd-assets-verified.json`; verify source identity before use.
Do not replace these model bytes with current HF HEADs and label it a resume.
Keep tokenizer/config/shard index and every shard, not weights alone.

The dataset is `test6.jsonl` at LCB revision
`0fe84c3912ea0c4d4a78037083943e8f0c4dd505`, SHA256
`bb4c364f71921c4495a6ad15abe1a927350b720009f4933e2e71f8af0f6fd1f5`.
The existing data/source acquisition payload is:

```bash
cd /root/rivermind-data/spectrum-harness/project/research-state/sh02-migration-20261020
/opt/conda/bin/python prepare_sources.py
```

This restores the pinned author archive and 134,303,240-byte dataset using the
recorded SHA256, then writes `source-data-verification.json`; it does not execute
benchmark code. Preserve the source-resolution input and use one cache writer.
Restore and verify the downloaded cache and prerequisite completion markers before
bootstrapping: `installation-exit.json`, `base-assets-verified.json`,
`ssd-assets-verified.json`, and `source-data-verification.json`. Missing prerequisites
make bootstrap wait; it does not install dependencies or download inputs.
The bootstrap performs environment inspection, protected test decoding, native software
probes, date selection and preparation completion. Review the exact
[`bootstrap_and_base.py`](https://github.com/Yunbo-max/SPECTRUM/blob/923e84ca9b92d111535ae245e137601b8856bbf8/research/round2-harness-20261017/sh02-migration-20261020/bootstrap_and_base.py)
before using this preparation-only entry (not `start_preparation.py`):

```bash
cd /root/rivermind-data/spectrum-harness/project/research-state/sh02-migration-20261020
/root/rivermind-data/spectrum-harness/venv-sh02/bin/python bootstrap_and_base.py
```

It must finish its CPU preparation stage without scientific inference. Local checks
the deployed bytes against the pinned source before admission, preserves old markers
and confirms the decoder/test manifest hash listed in evidence.json. Do not run
downloaded/generated programs outside the already qualified native OS boundary.

### SPECTRUM release: four models and five datasets

The complete inventory/pins/consumers are in
[`configs/final/assets.json`](configs/final/assets.json) and
[DATA_MODELS.md](docs/DATA_MODELS.md). Native Conda preparation uses the source-pinned
Transformers4.51.3/PEFT0.15.2/Accelerate1.6.0/Datasets3.5.1/EvalPlus0.3.1 family;
resolve a compatible permitted Torch build on the actual host, then export the
installed Conda/pip environment before workloads. Do not mutate an active environment.
The project entry is `python -m pip install -e '.[train,analysis,evalplus,test]'` from
the delivered checkout. Requested version ranges are not a resolved environment lock.

Model acquisition payload, from the delivered checkout in that environment:

```bash
python - <<'PY'
import json
from huggingface_hub import snapshot_download
assets = json.load(open('configs/final/assets.json'))
for alias in ('qwen1.5b', 'qwen3b', 'qwen7b', 'deepseek6.7b'):
    model = assets['models'][alias]
    snapshot_download(repo_id=model['repo_id'], revision=model['revision'])
PY
```

No filters remove tokenizer/index/config/shard files. The fixed-revision HF cache
preserves the canonical repo identity used by `run_release_study.py`; use that cache
with `HF_HUB_OFFLINE=1` for admitted workloads after verifying completeness.
Snapshot download is not a scientific result. Local records actual file sizes/hashes,
matches available upstream LFS identities, and rejects missing shards, HTML or LFS-pointer files.
The old planner's shared `/inspire/...` directory heuristic does not establish revision
provenance and is overwritten by the release planner. Do not fix this by removing the
pin or faking `_commit_hash`; an arbitrary shared export needs a separately verified
canonical-revision/file manifest before an offline-path feature can be qualified.

Dataset acquisition and native builder payloads, from the same delivered checkout:

```bash
python scripts/run_release_study.py init-seeds --output runs/private/seeds.json
python scripts/prepare_final_data.py --assets configs/final/assets.json --output-dir data/final --seed-file runs/private/seeds.json
```

`init-seeds` is **new-study only**: preserve an existing private file and skip this
command when restoring it. Do not print its numbers. `prepare_final_data.py` downloads
the pinned original dataset splits and the EvalPlus fixture through the inspected
native builders; no model is loaded. Required outputs are `data/final/assets.lock.json`,
`benchmark_registry.json`, `contamination_audit.json`, the MBPP four JSONL splits,
and each benchmark's `eval.jsonl`/`manifest.json`. Expected counts are291/50/30/500,
164,200,165,200. Record all source and output hashes. A cached dataset repo alone does
not prove these native outputs exist. Failures block their consumers, not an already
qualified independent author-LCB task. Current planner requires all five prepared
datasets even to freeze core: account for this existing dependency, do not forge a registry.

## Calibrate, debug, then dispatch

### Ownership and finite development bounds

One Local coordinator owns manifests/leases/result collection. One environment worker
owns cache writes and native isolation. One independent reviewer checks scorer/protocol
parity and report reconstruction. GPU workloads start exclusively on an actually allocated
device; CPU preparation/scoring can overlap within measured RAM/CPU/I/O limits. Never
infer three available GPUs from the three training repeats. Preserve harness-assigned
device visibility. Same-card concurrency needs measured headroom and explicit admission.

For this handoff's new operational qualification, allow at most three candidate settings
per workload shape, one repair-and-recheck per identified cause, and at most two GPU hours
total for new qualification. Record spent time and stop at the remaining bound. These are
preparation caps, not estimates of the full study. Existing running contracts retain their
own bounds. Use actual outer/inner timeout and remaining allocation; if missing, scientific
dispatch stays pending. No new scientific repeats are authorized by these debugging limits.

Release inference batch candidates are1,2,4, starting at1; freeze only a setting that fits
representative published development examples including longest shapes. Measure throughput,
GPU allocated/reserved/host peaks, wall time, truncation, CPU/RAM and disk. Keep main precision,
sample IDs, task count, sampling policy, train microbatch1/accumulation16 and optimizer schedule
fixed. Batch changes require checking per-case RNG/ordering; unproven equivalence means a new
protocol identity. Never silently use FP16 for the BF16 SPECTRUM training path.

### Ordered command cards

| Stage | Actual payload / source | Output and acceptance |
|---|---|---|
| Source acceptance, delivered main | `python -m pytest tests/test_release_reporting.py tests/test_pipeline.py` | Through native harness only; save logs/exit; pipeline tests include tiny software model fixtures and generated fixture code, so require qualified containment. No benchmark claim |
| Native scorer qualification | Restore the research branch's unchanged author scorer + protected wrapper; inspect `native-failure-semantics.md` and actual deployed sources | Released tasks, exact labels/tests, extraction and early-stop/timeout semantics; trusted native-output replay. Software probes alone do not establish model performance |
| SH02 inference qualification | From historical SH02 state directory: `/root/rivermind-data/spectrum-harness/venv-sh02/bin/python start_fp16_smoke.py` | Software/import/generation/resume rejection logs; after live host/lock restoration; never main SPECTRUM BF16 qualification |
| Author formal base | Same directory/interpreter, `start_formal_base.py --start` | Full131×10 generation + author scoring underFP16/16,384; no other live owner |
| Remaining author conditions | Three exact cards below, one at a time | Full generation, native outputs and sealed config; preserve all signs |
| Freeze SPECTRUM study | `scripts/run_release_study.py plan` with actual supported profile and native backend | **Pending native execution-boundary integration.** Existing local flag is not sandbox evidence. Do not default toDocker; do not invent a launch-ready command until wrapper/isolation is qualified |
| Run an admitted release job | `python scripts/run_release_study.py run --manifest runs/spectrum_release_v1/plan/manifest.json --job core-qwen1.5b-r1` | Only after a newly qualified frozen plan; r2/r3 analogous, separate ownership. No `--block all` by default |
| Monitor/report | `python scripts/run_release_study.py status --manifest runs/spectrum_release_v1/plan/manifest.json` and `python scripts/run_release_study.py report --manifest runs/spectrum_release_v1/plan/manifest.json` | Status is stored evidence, not fresh liveness. Rebuild all available and missing rows; preserve primary/secondary and four-wayeligibility |

Historical SH02 payloads, only after source/path/identity/lock/environment qualification:

```bash
cd /root/rivermind-data/spectrum-harness/project/research-state/sh02-migration-20261020
/root/rivermind-data/spectrum-harness/venv-sh02/bin/python run_condition.py --model ssd --temperature 1.1 --max-tokens 16384 --max-model-len 17920 --name ssd-fp16-t1.1-cap16384
/root/rivermind-data/spectrum-harness/venv-sh02/bin/python run_condition.py --model base --temperature 1.1 --max-tokens 16384 --max-model-len 17920 --name base-fp16-t1.1-cap16384
/root/rivermind-data/spectrum-harness/venv-sh02/bin/python run_condition.py --model ssd --temperature 0.7 --max-tokens 16384 --max-model-len 17920 --name ssd-fp16-t0.7-cap16384
```

These are three separately admitted tasks, not an unreviewed shell queue. A baseline
truncation review records protocol limits; it does not select which unfavorable condition
to omit. Use the existing analyzer after complete native results:

```bash
cd /root/rivermind-data/spectrum-harness/project/research-state
/root/rivermind-data/spectrum-harness/venv-sh02/bin/python ssd-author-comparison-20261019/analyze_condition.py --root sh02-migration-20261020 base-fp16-t0.7-cap16384 ssd-fp16-t1.1-cap16384
/root/rivermind-data/spectrum-harness/venv-sh02/bin/python ssd-author-comparison-20261019/analyze_condition.py --root sh02-migration-20261020 base-fp16-t0.7-cap16384 ssd-fp16-t0.7-cap16384
/root/rivermind-data/spectrum-harness/venv-sh02/bin/python ssd-author-comparison-20261019/analyze_condition.py --root sh02-migration-20261020 base-fp16-t1.1-cap16384 ssd-fp16-t1.1-cap16384
```

Analyzer compatibility checks remain enabled. This command family does not merge
hn01BF16/65,536 with SH02FP16/16,384. Do not execute the bare upstream evaluator
without the established containment wrapper.
Successful condition evidence includes `results.json`, `results-binding.json`,
`generation-completed.json` and `pipeline-completed.json`; a base-stage marker alone
is insufficient. The analyzer writes `analysis.json` and `per-task-analysis.json`
inside each condition, and `comparison-<first>-vs-<second>.json` at the SH02 state root.

### Failure routing

| Observation | Read / distinguish | Bounded repair and required recheck |
|---|---|---|
| Remote auth fails / GPU absent | Oct27 auth record, live access/allocation | Restore existing authorized local access; keep scientific state pending; no invented process status |
| Missing model or wrongrevision | assets.json, actual HF cache snapshot, historical per-file manifests; `modeling.py` | Acquire only missing pinned input; hash all required files; arbitrary shared-copy provenance remains unresolved |
| Bad format / score collapse | original prompt,raw/extracted code, native scorer output, MBPP635 history | Fix demonstrated interface defect; replay same predictions, retain old outcome; never tune extraction to success |
| Native scoring unavailable | actual OS boundary and scorer entry | Block affected scoring; qualify native route; no unsafe-local/container fallback |
| OOM / slow batches | recorded shape, VRAM/CPU/I/O and time | Within finite candidates adjust operational batch only, restore/reconcile failed attempt; no precision/budget change hidden |
| Resume rejects new runtime | `pipeline.py` training_runtime/evaluation_runtime and old manifest | Use matching old environment or new run root; never rewrite a fingerprint to pass |
| Primary count/eligibility wrong | reporter plus targeted tests; original per-task records | Source repair then targeted recheck; regenerate report, retain old export and diff |
| Corrupt/missing scientific cell | marker/file hashes, task/sample multiplicity | Retain incomplete status; retry only supported interrupted work with matching identity, never score aszero |

## Collection and return

Actual harness attempt receipts determine stdout/stderr/context/status paths; retain them,
not guessed UUIDs. Collect through existing SSH, check file identities on both ends, and
write the return packet specified in [WEB_HANDOFF.md](rounds/20261027-validation/WEB_HANDOFF.md).
Include every trial, outcome, unfinished condition and actual cumulative costs. Recompute
native scores from saved predictions on the qualified host, rebuild reports, compare to
sealed summaries, and retain discrepancies. Static booleans are not fresh scorer replay.
Current destination is `Yunbo-max/SPECTRUM`; no new HF output target is inferred. Keep bulk
models/private data/seed values outside public source. Push only authorized scoped changes
with expected-parent protection and exact-head readback. Do not mutate a running revision.
