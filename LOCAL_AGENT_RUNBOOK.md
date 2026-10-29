# Current Local entry — 29 October 2026

Repo: **Yunbo-max/SPECTRUM**, branch **main**. Read the delivered immutable revision.
Current handoff: [4096-token repair](rounds/20261029-length4096/WEB_HANDOFF.md).
Exact inputs, preparation, commands, qualification and result return:
[4096-token guide](docs/SPECTRUM_4096_ZH.md), especially
[model/data preparation](docs/SPECTRUM_4096_ZH.md#模型数据与执行).
Status: **generated_unexecuted**, not a GPU qualification or scientific result.

## Current task and ordered actions

1. Restore the actual execution host, existing environment, GPU allocation, data,
   model fingerprints and finite compute authorization. Keep live jobs on their
   original pinned revision; stage this repair in a separate checkout.
2. Reuse the complete Qwen2.5-Coder-7B-Instruct model and MBPP291/50/30/500 split.
   Follow the linked guide's verified source interfaces if input assets are absent.
3. On that host, run the guide's authored regression tests and native development
   capacity checks for4096 generated /6144 total training tokens. No such tests
   or memory measurements were executed by Web. Preserve both arms' sample counts.
4. Run the explicit new entry after qualification:

   ```bash
   bash scripts/run_spectrum_r10_4096.sh plain
   bash scripts/run_spectrum_r10_4096.sh spectral
   ```

   `both` is an explicit serial request; `--resume` is only for compatible new4096
   runs. Old512 directories/configs/qz commands are not this repair's destinations.
5. Return the guide's actual per-round results, raw outputs, configuration and
   resource receipts. Keep missing/failed work visible. Longer completions alone
   do not establish improved correctness or multi-round stability.

## Actual broader configuration inventory

| Block | Model | Default benchmark | Protocol |
|---|---|---|---|
| Immediate length diagnostic | Qwen2.5-Coder-7B-Instruct | MBPP500 | Plain/SPECTRUM,10 rounds,4096 output |
| Cross-family | Qwen Coder7B /Llama8B /DeepSeek Coder6.7B | MBPP500 +HumanEval+164 | Three methods,5 rounds; unchanged512 main generation |
| Math | Qwen2.5-7B-Instruct | MATH500 | Three methods,5 rounds;4096 output |
| QA | Qwen2.5-7B-Instruct | MMLU-Pro12,032 | Three methods,5 rounds; GPQA not enabled |
| ARC | Qwen3.8-27B text | ls20 /ft09 /vc33 | Three methods,5 rounds; context qualification blocked |

Use the updated [code](docs/CROSSFAMILY_CODE.md), [text](docs/TEXT_TASKS.md)
and [ARC](docs/ARC_AGI3.md) guides. In particular the current7B math/QA configs
use local model paths and cannot be fed to the historical hybrid27B qualifier.
Actual configs currently select local grading in several blocks; do not describe
these as qualified bubblewrap runs. Restore and verify the real evaluator on host.

ARC inference permits32000 prompt tokens while training/calibration allow16384;
known multi-frame examples described in commits reach about25K. This is unresolved,
not a27B capability verdict. A true calibration-game WIN is an additional SPECTRUM
prerequisite. Do not silently drop frames, use heldout labels, or raise memory claims
without evidence. This repair does not alter the ARC method or observation protocol.

## Historical 27 October runbook — retained for provenance

The text below is the original27B plan, **not current command cards**. Its shared27B
math/QA model, GPQA default, hybrid qualification commands and sandbox assumptions
were superseded by later configuration commits. Use the current entry and updated
domain guides above. Preserve already-running attempts at their sealed versions.

# Current Local runbook: three code families and one 27B reasoning model

Decision: 27 October 2026. Repo: **Yunbo-max/SPECTRUM**, branch **main**.
Read [the current handoff](rounds/20261027-multidomain/WEB_HANDOFF.md) at the delivered commit.
Status: **generated_unexecuted**. Web prepared/reviewed source, but did not run
project tests, download scientific assets, load models, train or score experiments.

This is the current entry. The old40-job plan, three-training-seed core,
temperature scans and1.5B main model are **not the default queue**.
Their files/results remain historical. The former runbook is available
[at its original commit](https://github.com/Yunbo-max/SPECTRUM/blob/1bb86ee5b19d23056c8c5332c7ad8c600e1c4aa6/LOCAL_AGENT_RUNBOOK.md).
Preserve existing running jobs, checkouts, environments, data and randomization.

## Experiment matrix

| Block | Initial model(s) | Data and outcomes | Detail |
|---|---|---|---|
| Code | Qwen2.5-Coder-7B-Instruct; Llama-3.1-8B-Instruct; DeepSeek-Coder-6.7B-Instruct | MBPP500 main; HumanEval+164 transfer | [Code guide](docs/CROSSFAMILY_CODE.md) |
| Math | Qwen3.8-27B text decoder | Full MATH500, accuracy/pass@k | [Text guide](docs/TEXT_TASKS.md) |
| QA | Same original Qwen3.8-27B | Full MMLU-Pro12032 and GPQA Diamond198, accuracy | [Text guide](docs/TEXT_TASKS.md) |
| Interactive | Same original Qwen3.8-27B | ARC-AGI-3 public holdout, native scorecard/levels/actions/tokens/time | [ARC guide](docs/ARC_AGI3.md) |

Every trained arm starts from its own common initial checkpoint: Vanilla SD
(`plain`), fixed-decoder SSD adaptation (`ssd`), SPECTRUM (`spectral_soft`);
five rounds, **one training trajectory per arm**, no temperature/seed sweep.
Multiple generated samples and rounds are not independent training repetitions.
SSD's synthesis decoder defines that baseline; it is not a sweep. Retain round0.

The code models are different released families, although Llama/DeepSeek use
related decoder implementations. Math and QA independently start from the same
original27B weights. ARC uses that original model with a fixed interactive wrapper.
Public three-game ARC evaluation is not the full competition or hidden test.

Qwen3.8-27B pin: `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`.
SPECTRUM targets raw K/V in full-attention layers31/63, before normalization/RoPE;
LoRA targets Q/K/V/O in the16 full-attention layers. GDN is outside this intervention.
See [model compatibility](docs/MODEL_COMPATIBILITY_27B.md).

## Restore host and prepare environments

The Local controller owns SSH/authenticated checkout. Native scientific commands
run on the actual allocated Linux GPU host through the existing admitted harness.
Restore real SSH alias, checkout/Conda paths, GPU UUID/VRAM, CPU/RAM/disk and live
process/lock ownership. These host facts were unavailable to Web. No allocation is
assumed. Do not restart historical watchers or infer liveness from saved PIDs.

All commands use the delivered repo root. Use **two separate native Conda environments**:

```bash
conda create -n spectrum-code-20261027 python=3.11 pip -y
conda activate spectrum-code-20261027
python -m pip install -e '.[train,evalplus,analysis,test]'
mkdir -p runs/private
python -m pip freeze > runs/private/code-environment.txt
```

```bash
conda create -n spectrum-27b-20261027 python=3.12 pip -y
conda activate spectrum-27b-20261027
python -m pip install -r requirements/arc3.txt
python -m pip install -e '.[test]'
mkdir -p runs/private
python -m pip freeze > runs/private/reasoning-environment.txt
```

Resolve a Torch build compatible with the actual CUDA driver before admission,
then preserve exact installed packages. Never install legacy `[train]` in the27B
environment: it pins a different Transformers generation. ARC Git dependencies need Git.
Install Linux **bubblewrap and libseccomp** through the host native package manager.
Qualify user/PID/network namespaces. Conda alone is not a sandbox; there is no
Docker/unsafe-local fallback in this queue. See [native scoring](docs/NATIVE_SCORING.md).
Use existing local authentication; no tokens in commands, receipts or GitHub.

## Download datasets and models

Code environment, CPU preparation:

```bash
python scripts/check_native_sandbox.py --output runs/private/native-sandbox-code.json
python scripts/run_crossfamily_study.py init
python scripts/run_crossfamily_study.py download --model all
python scripts/run_crossfamily_study.py prepare
python scripts/run_crossfamily_study.py plan
```

Pins: `configs/crossfamily/assets.json`. Llama needs existing official gated access.
If unavailable, use `download --model qwen7b` and `--model deepseek6.7b`; only
Llama remains pending. Download verifies indexed shards, tokenizer/config and LFS
hashes. Preparation retains MBPP291/50/30/500 and all164 HumanEval+ tasks.
The main protocol is original-tests MBPP500, not MBPP+378.

27B environment, shared model and independent data:

```bash
python scripts/prepare_reasoning_model.py --config configs/multidomain/text_math.json
python scripts/prepare_reasoning_model.py --config configs/multidomain/text_math.json --verify-only
python scripts/check_native_sandbox.py --output runs/private/native-sandbox-27b.json
python scripts/prepare_text_data.py --config configs/multidomain/text_math.json
python scripts/prepare_text_data.py --config configs/multidomain/text_qa.json
python scripts/prepare_arc3.py --config configs/multidomain/arc3.json
python scripts/prepare_arc3.py --config configs/multidomain/arc3.json --verify-only
```

The shared model downloads once to the normal HF cache, including all snapshot
files, native tokenizer/chat template/generation config and indexed shards.
`data/multidomain/reasoning-model.json` records bytes/hashes. Formal model loading
is offline. GPQA may need existing dataset access. Math uses immutable PRM800K
splits and the unchanged author grader inside the native sandbox. QA preserves
test populations and declared author parsing/prompt adaptations. No heldout
question provides a training/calibration label. The domain guides specify inputs,
source pins, access routes and actual preparation outputs.

ARC preparation downloads and initializes official game code on the native host;
exact versions/source/human-baseline metadata are frozen. Default: training/dev
ls20, calibration ft09, heldout vc33. Expand with an explicit `--split-file` in a
new data directory. Preserve the shared private `runs/private/multidomain_seed.json`.

## Calibrate, debug, then dispatch

Use real native development inputs before expensive jobs. Tests delivered here
have not been executed. Run applicable tests from the delivered tree through the
native harness; code/sandbox tests use the code environment, hybrid/domain tests
the27B environment. Exact source-only test files are listed in the handoff.

```bash
python scripts/check_native_sandbox.py --output runs/private/native-sandbox-qualified.json
python scripts/qualify_reasoning_model.py --config configs/multidomain/text_math.json --output-dir runs/qualification/qwen38-27b-math
python scripts/run_arc3_study.py --config configs/multidomain/arc3.json baseline
```

The27B qualifier uses actual pinned weights and prepared development examples:
finite K/V gradients, folded-forward/exact restoration, one LoRA update, saved
merged checkpoint and reload. It creates a separate full checkpoint and measures
resources. Its inputs do not establish worst-case capacity; inspect longer native
development cases before formal dispatch. It never changes original cached weights.

27B BF16 text weights alone are roughly54GB decimal. Actual peak also includes
activations/KV/calibration; no80GB fit is guaranteed. Native folding does not permit
silently switching to4-bit weights. Batch1 is the default. Capacity failures need
a qualified new configuration/root, not silent truncation or a changed method budget.
For operational qualification allow at most three batching candidates (1,2,4),
one repair/recheck per identified cause and two GPU hours before review. Preserve
effective training batch, precision and scientific sample budgets. Changed batching
can change RNG: freeze a new root after qualification. This cap is setup only,
not the complete experiment queue. Ready independent cells may continue.

Code, one allocated GPU job at a time:

```bash
python scripts/run_crossfamily_study.py run --model qwen7b
python scripts/run_crossfamily_study.py run --model llama8b
python scripts/run_crossfamily_study.py run --model deepseek6.7b
python scripts/run_crossfamily_study.py status
```

Math (repeat four method commands with `text_qa.json` for QA):

```bash
python scripts/run_text_study.py --config configs/multidomain/text_math.json --method base
python scripts/run_text_study.py --config configs/multidomain/text_math.json --method plain
python scripts/run_text_study.py --config configs/multidomain/text_math.json --method ssd
python scripts/run_text_study.py --config configs/multidomain/text_math.json --method spectral_soft
python scripts/run_text_study.py --config configs/multidomain/text_math.json --report
```

ARC obtains real calibration reference actions before SPECTRUM:

```bash
python scripts/run_arc3_study.py --config configs/multidomain/arc3.json collect-reference
python scripts/run_arc3_study.py --config configs/multidomain/arc3.json run --method plain
python scripts/run_arc3_study.py --config configs/multidomain/arc3.json run --method ssd
python scripts/run_arc3_study.py --config configs/multidomain/arc3.json run --method spectral_soft
python scripts/run_arc3_study.py --config configs/multidomain/arc3.json status
```

If collection does not yield a replay-verified WIN, use the documented
`import-reference` with a genuine successful calibration-game recording.
Vanilla/SSD and other domains remain independent. No fabricated success or heldout
game becomes calibration. All synthetic training actions, including failures and
malformed outputs, remain in action-only SFT.

Math/QA/ARC require `--resume`; code commands resume compatible sealed work
automatically. Reconcile live host/lock/attempt identity first. Changed source,
model, data, decoder or runtime needs a new output root. Latest-checkpoint retention
removes only already replaced same-lineage weights after successor sealing.
Raw predictions/statistics/hashes remain. Budget disk for three retained students
per domain, transient replacements, original snapshots and qualification checkpoint.

## Diagnose and return

| Observation | Inspect and act |
|---|---|
| Access/download/weights | Verify official pins, manifest and local authentication; acquire missing authorized bytes |
| Sandbox/namespace | Inspect qualification stderr; fix native setup, no unsafe fallback or wrong-answer substitution |
| Hybrid load/topology | Preserve loader report; qualify official text extraction and exact full-attention modules |
| OOM/context overflow | Inspect development IDs/tokens/peaks; qualify a new resource/configuration profile |
| ARC no progress/invalid actions | Inspect raw frames/action feedback on training/dev game; preserve failures |
| ARC no reference | Import an actual replay-verified calibration recording; other cells stay independent |
| Resume mismatch | Restore exact sealed identity or start new root; never rewrite fingerprint |
| Score/denominator anomaly | Replay pinned native scorer on saved predictions; retain original and correction |

Return execution commit/dirty patch, actual environment/resources/attempt receipts,
private randomization identity (not its number), frozen inputs/checkpoint hashes,
raw native outputs, scorer replay, all rounds/methods including failures, reports
and costs. Status is saved state, not fresh liveness or scientific verification.
Publish scoped return packets under `research/multidomain-20261027/returns/` in
this repo. Keep weights, gated datasets, credentials and seed values out of Git.
No new HF output destination is assumed.
