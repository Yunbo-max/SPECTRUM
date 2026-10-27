# Three-family code experiments

This is the current code-study entry for the 27 October 2026 user decision.
Source delivery is `generated_unexecuted`: the Web session did not load models,
run software tests, train, or score programs. Run the commands below through the
qualified Local native harness in the separate GPU checkout. Historical release
plans and results remain unchanged.

| Alias | Initial model | Role |
|---|---|---|
| `qwen7b` | `Qwen/Qwen2.5-Coder-7B-Instruct` | Current 7B main experiment |
| `llama8b` | `meta-llama/Llama-3.1-8B-Instruct` | Different model family |
| `deepseek6.7b` | `deepseek-ai/deepseek-coder-6.7b-instruct` | Different model family |

Immutable model and dataset revisions are in
[`configs/crossfamily/assets.json`](../configs/crossfamily/assets.json).
DeepSeek and Llama share a Llama-style Transformers implementation; this matrix
tests different released model families, not three unrelated architecture designs.
Llama access is gated: the user must already have accepted the official repository
access conditions at [Meta's model page](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct).
Use existing local Hugging Face authentication; never put tokens into this repository.
An access failure blocks that model only. `--model qwen7b` and `--model deepseek6.7b`
remain independent commands.

## Fixed experiment

Each model starts from its own pinned original checkpoint and runs Vanilla SD
(`plain`), the repository SSD adaptation (`ssd`), and SPECTRUM (`spectral_soft`)
for five rounds. The original model is evaluated once. There is one independent
training trajectory per model and method, with no temperature sweep or additional
training-seed grid. All methods use the same original inputs, native chat template,
LoRA settings, round count and student evaluation decoder within each model.

- MBPP main: training 291, fixed reference calibration 50, validation 30,
  complete original test 500. Preparation retains original test rows and rejects
  split overlap. The label is **MBPP500 original-tests function-interface protocol**,
  not MBPP+378, the author LCB study, or a leaderboard substitute.
- Each training question produces 16 raw completions per round. No correctness,
  syntax, length or AST filtering selects the synthetic training corpus.
- Each test question produces 64 completions. Primary outcomes are pass@1,
  pass@64, correct-solution coverage C64, and the existing correct-count-matched
  AST proxy D4. Retain all denominators and eligibility counts.
- The common student evaluation decoder is temperature 0.8, top-p 0.95, top-k 0.
  The existing SSD adaptation uses its fixed synthesis decoder 1.5/0.8/20.
  This is an adapted method comparison, not reproduction of Apple-released weights.
- HumanEval+ transfer: initial checkpoint and each round-5 student, all 164
  official tasks, 64 completions per task, official EvalPlus 0.3.1 base-and-plus
  tests with fixture v0.1.10. No target training or calibration. Generation has a
  fixed 1,024-token output cap for every transfer arm.
- Checkpoint retention is `latest`: completed earlier round weights are pruned
  after their successor finishes; raw generations and metrics remain. Round-5
  checkpoints are retained for transfer. Do not request earlier transfer rounds
  from this storage profile.

The complete matrix is 9 trained arms × 5 rounds = 45 arm-rounds, plus 3 initial
MBPP evaluations and 12 HumanEval+ model conditions. Task-bootstrap intervals
describe these trained trajectories; they do not estimate variance across
independent training runs. No cross-model pooled significance is implied.

## Environment and acquisition

Use the existing native code environment, not the separate 27B hybrid-model
environment. Its project requirements remain the `train`, `evalplus`, `analysis`
and `test` extras in [`pyproject.toml`](../pyproject.toml), including
Transformers 4.51.3, PEFT 0.15.2 and EvalPlus 0.3.1. Install into an isolated
Conda environment and preserve the actual resolved package/CUDA receipt:

```bash
python -m pip install -e '.[train,evalplus,analysis,test]'
python scripts/check_native_sandbox.py --output runs/private/native-sandbox.json
python scripts/run_crossfamily_study.py init
python scripts/run_crossfamily_study.py download --model all
python scripts/run_crossfamily_study.py prepare
python scripts/run_crossfamily_study.py plan
```

The sandbox qualification must pass on the actual Linux host before candidate
execution. There is no unsafe-local or Docker fallback in this new plan.

`init` creates and preserves one private randomization file at
`runs/private/crossfamily_code_v1.json`; it does not print numeric seeds.
`download` uses immutable official HF revisions, checks the indexed native
safetensors shards and every root-level loader/tokenizer sidecar, verifies sizes
and upstream LFS hashes when supplied, and writes per-model receipts under
`runs/crossfamily_code_v1/assets/`. Alternative original-format weight copies
are not downloaded. Missing-file capacity is checked before the model snapshot.
Existing exact-revision cache files are reused. A partial download can be resumed
by issuing the same command. No access grant or disk deletion is automated.

`prepare` downloads only the pinned MBPP and native HumanEval+ inputs. It writes
`data/crossfamily/prepared.json`, complete split/task manifests and hashes, and
the exact HumanEval+ fixture for the offline evaluator. It does not execute
reference or generated programs. A changed source, private seed, split population
or prepared file requires a new data directory; it is never silently overwritten.

`plan` freezes the three job configs and source/data identities at
`runs/crossfamily_code_v1/plan/manifest.json`. It neither downloads weights nor
starts workloads. The defaults in
[`configs/crossfamily/protocol.json`](../configs/crossfamily/protocol.json)
use inference sequence batch 1, BF16 dense weights, training microbatch 1 and
gradient accumulation 16. These are conservative starting settings, not measured
VRAM guarantees. Record actual host GPU/CPU/RAM/storage and qualify the native
forward, covariance, fold/unfold and LoRA update before the full comparison.
Use development/validation inputs for operational qualification. If an operational
setting must change, edit the protocol before freezing a fresh root, keeping the
scientific budget and within-model controls matched.

DeepSeek has a 4,096-wide K/V projection versus Qwen7B's 512; its dense covariance
and eigendecomposition need substantially more CPU memory/time. Do not confuse
similar total parameter counts with identical calibration costs. The download
receipts expose actual weight bytes; reserve disk for the three retained final
students per model, a transient predecessor, generations and metrics in addition
to the shared model cache. No host resource availability is assumed here.

## Run, resume and collect

Run one model at a time on the allocated GPU. Each command runs the full main
experiment followed by its official transfer evaluation:

```bash
python scripts/run_crossfamily_study.py run --model qwen7b
python scripts/run_crossfamily_study.py run --model llama8b
python scripts/run_crossfamily_study.py run --model deepseek6.7b
python scripts/run_crossfamily_study.py status
```

Alternatively, `run --model all` executes those three model jobs sequentially.
`--stage train` and `--stage transfer` separate training from transfer when the
Local harness assigns different resource windows. Transfer requires the completed
initial model and three final checkpoints; it never retrains missing weights.
Commands resume exact compatible outputs automatically and reject source,
runtime, data, model or sampling differences. A lock file is ownership evidence,
not proof that its PID is still the same process: reconcile actual host/session
state before recovering an interrupted owner, and do not blindly delete locks.

Main results live in `runs/crossfamily_code_v1/jobs/MODEL/`, with raw per-task
generations, verified outputs, metrics and each round's completion hashes.
`longitudinal/` contains the existing paired task analyses and all available
round trajectories. Official transfer results and their native scorer artifacts
live in `runs/crossfamily_code_v1/transfer/MODEL/`. `status` reports stored markers
only; it is not live liveness or integrity verification.

For each completed cell, return its exact execution commit, actual environment
and host receipt, frozen manifest, raw output hashes, native scorer replay,
resource measurements, all negative/incomplete rows, and the generated reports.
An initial model load or software test is not a scientific completion receipt.
Do not mix the historical 1.5B study, this 7B-family study, or different decoder
and native-dataset protocols into one controlled-difference table.
