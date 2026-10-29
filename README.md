# SPECTRUM

**Proximal Spectral Modulation for Looped Self-Distillation**

## Current experiment entry — 29 October 2026

[**Local: start here / 当前运行指南**](LOCAL_AGENT_RUNBOOK.md)
· [4096-token repair and commands](docs/SPECTRUM_4096_ZH.md)
· [Current handoff](rounds/20261029-length4096/WEB_HANDOFF.md)
· [Inputs and preparation](docs/SPECTRUM_4096_ZH.md#模型数据与执行)

| Experiment | Actual configured models | Data / scope |
|---|---|---|
| **Immediate 4096-token comparison** | **Qwen2.5-Coder-7B-Instruct** | MBPP291 train /50 anchor /30 development /500 test; Plain and SPECTRUM,10 rounds,64 evaluation samples per task |
| Cross-family code | Qwen2.5-Coder-7B-Instruct; Llama-3.1-8B-Instruct; DeepSeek-Coder-6.7B-Instruct | MBPP500 + HumanEval+164; unchanged five-round512-token main protocol |
| Mathematics | **Qwen2.5-7B-Instruct** | PRM-released MATH training pool → MATH500,16 samples per task |
| QA | **Qwen2.5-7B-Instruct** | MMLU auxiliary training → MMLU-Pro12,032; GPQA Diamond is optional and disabled by default |
| Interactive agents | **Qwen3.8-27B** text decoder | ARC-AGI-3: train ls20 /calibration ft09 /heldout vc33; long-context recursive qualification blocked |

The immediate repair uses4096 new tokens and6144 total SFT tokens with explicit
rejection of additional training truncation. Both arms use fresh output roots;
the old512-token configurations, archived qz payloads and historical results remain.
Tau, sampling and training settings otherwise retain the old ten-round comparison.
Longer generation is a diagnostic change, not a demonstrated cure for collapse.

The other three-method studies compare Vanilla SD, the repository SSD adaptation
and SPECTRUM over five rounds, one training trajectory per method. Math and QA
independently start from the same7B base; ARC uses a separate27B base.
See [code](docs/CROSSFAMILY_CODE.md), [math/QA](docs/TEXT_TASKS.md),
[ARC](docs/ARC_AGI3.md) and the [27B adapter](docs/MODEL_COMPATIBILITY_27B.md).

ARC currently allows32K input but only16K training/calibration. Its SPECTRUM arm
also needs a genuine replay-verified successful calibration trajectory. Neither
blocker establishes model failure; the public heldout game is not the full leaderboard.

This delivery is **generated_unexecuted**: source/configuration review and static
syntax checks are distinct from pending Local tests, GPU capacity qualification,
training and native scoring. Existing run status and success are not inferred from
code or launch payloads. The [27 October handoff](rounds/20261027-multidomain/WEB_HANDOFF.md)
and older release design below remain dated historical records.

SPECTRUM studies what a model retains when it repeatedly learns from its own
generated code. Each round estimates loss-sensitive key/value geometry using
the same fixed reference anchor, temporarily modulates the generator, and trains
one native student on every raw completion. Generation weights are restored
before LoRA training; final inference needs no spectral intervention.

The fixed anchor supplies initial reference information that is reused for
calibration. Generated training completions are not checked, ranked, filtered,
or given quality-dependent loss weights. Evaluation tests are separate. The
anchor-replay **control** deliberately uses the references as supervised training
examples and is labeled separately.

## Earlier release design (historical)

This repository continues the implementation from
[`yuhanlydia/improving`](https://github.com/yuhanlydia/improving) at commit
`45195e866162df1cdf9de0169d2bf17347eb6abf`. The release keeps the original SPECTRUM
definition and adds a fixed validation matrix, controls, pinned assets and a
complete result exporter. Historical results are developmental evidence; the
new experiment cells remain unrun until the commands below are executed.

**Release reference:** [原版运行指南（中文）](docs/RUN_FINAL_ZH.md)
· [Experiment contract](docs/FINAL_EXPERIMENTS.md)
· [Exact models and datasets](docs/DATA_MODELS.md)
· [Research audit](docs/AUTORESEARCH_CHECK.md)
· [Existing evidence](docs/EXISTING_EVIDENCE.md)
· [Related-work audit](docs/LITERATURE_AUDIT.md)

### Earlier four-backbone plan

| Alias | Hugging Face model | Main comparison | Independent training replicates |
|---|---|---|---:|
| `qwen1.5b` | `Qwen/Qwen2.5-Coder-1.5B-Instruct` | Vanilla SD / SSD / SPECTRUM, five rounds | 3 |
| `qwen3b` | `Qwen/Qwen2.5-Coder-3B-Instruct` | Same three methods, five rounds | 1 |
| `qwen7b` | `Qwen/Qwen2.5-Coder-7B-Instruct` | Same three methods, five rounds | 1 |
| `deepseek6.7b` | `deepseek-ai/deepseek-coder-6.7b-instruct` | Same three methods, five rounds | 1 |

All four are **planned trained-method comparisons**, not an initial-model-only
matrix. Qwen uses grouped-query attention; DeepSeek uses multi-head attention.
Full model revisions and layer/head dimensions are in
[`configs/final/assets.json`](configs/final/assets.json).

### Five evaluation datasets

| Dataset | Evaluation tasks | Role |
|---|---:|---|
| MBPP | 500 | In-domain, rounds 0–5; separate 291 training / 50 anchor / 30 validation tasks |
| HumanEval+ | 164 | Frozen-student transfer, official EvalPlus checks |
| APPS Intro | 200 | Frozen transfer, fixed adapted evaluation |
| CodeContests | 165 | Frozen transfer, full official test population with adapted evaluation |
| LiveCodeBench | 200 | Frozen transfer, fixed release/time window with adapted evaluation |

Every final evaluation uses 64 samples per task. All reported pass@k values and
correct-implementation metrics come from the same pool. The transfer benchmarks
provide no training or calibration signal. The three adapted competition
protocols are not official leaderboard reproductions.

## Earlier release execution notes (historical)

Follow the [ordered Local command cards](LOCAL_AGENT_RUNBOOK.md#calibrate-debug-then-dispatch).
The current host route is native Conda. The earlier release guide documents a Docker
path; it is retained as historical implementation reference, not the current host's
launch instruction. Native isolation/scorer integration must be qualified before
release execution. `--allow-unsafe-local` does not establish isolation.
The SPECTRUM training path requires a compatible BF16 GPU; the research branch's
FP16 author-checkpoint evaluation is a different protocol. The `improving` import/CLI
name is retained for compatibility.

The private randomization file is generated once, is ignored by Git, and must be
kept with local run artifacts. Public report tables use `r1/r2/r3` labels.
Planning loads no model and launches no experiment. **There is no automatic
full-grid execution.** Use `run --block all` only to request the entire fixed
matrix. Other blocks are `scale`, `mechanism`, `token_matched`, `diagnostic`,
`transfer`, and `decoder`; transfer/decoder require their source students.

Schedule the independent core jobs on the actual allocated devices through the
Local harness; three replicates do not imply three available GPUs. Never give two
processes the same job; file locks reject that conflict. Repeating a compatible command
resumes sealed work. An interrupted SFT stage restarts that stage, rather than
restoring optimizer steps. Do not change code, data, hardware profile or configs
inside an active plan; create a new run root for changed conditions.

## What the controls answer

- **Projection / random orientation / isotropic gain:** does full-rank,
  loss-sensitive orientation matter beyond generic attenuation?
- **Fixed initial geometry:** is per-round recalibration useful?
- **Fixed-anchor replay:** is directly learning the same reference answers an
  adequate simpler alternative?
- **Matched SFT token exposure:** do benefits persist when every arm sees the
  same prescribed supervised-token budget, with all raw records retained?
- **Decoder robustness:** do round-five comparisons survive alternative fixed
  native decoding policies? Initial-model decoding-only scores are retained.
- **Strength and loss scope:** report the predeclared sensitivity results without
  replacing the original method after seeing test outcomes.

## Outputs and completion

`runs/spectrum_release_v1/release_report/` contains editable CSV tables and a
Markdown/JSON index: endpoints, trajectories, paired differences, correct-count
eligibility, retention, independent-replicate summaries, ablations, decoder
effects, generator-to-student diagnostics, resource use and operator diagnostics.
Missing results are `x`, never zero. All effect signs are retained.

The full fixed plan has **40 jobs: 13 training jobs, 24 transfer jobs, 3 decoder
jobs; 134 method–replicate–rounds and 7,106,080 fresh-run generated candidates**.
It is a substantial study, not a smoke run. Run the core block first; inspect
the frozen plan before launching other blocks. Candidate counts are not measured
GPU hours. Keep all checkpoints; see the storage discussion in the run guide.

Completion means the planned artifacts exist and validate, not that SPECTRUM
wins. It does not trigger extra hyperparameter searches or favorable-result
selection. Three independent core replicates and one replicate per scale model
must not be pooled as if all tasks or training runs were independent.

## Verification status of this code release

For the 2026-10-27 amendment, source review and static syntax/JSON checks are
separate from pending Local tests. Primary metrics now follow the manifest;
paired task eligibility is explicit; new run fingerprints bind installed training
dependencies and runtime identity. These changes do not retroactively certify old
runs or provide bitwise reproducibility across arbitrary hosts.

The following describes the original release preparation:

Source review, Python/JSON parsing and CLI help checks were performed. Regression
test sources were added. In accordance with the request for code without running
experiments, **no pytest suite, model download, training, benchmark, or generated
program execution was performed during this release**. GPU memory profiles are
conservative configurations, not measured memory guarantees.

Historical scripts/configs are retained for provenance and compatibility. The
supported final entrypoints are `prepare_final_data.py`, `run_release_study.py`,
and `report_release_study.py`; earlier `run_final_study.py` plans are a different
protocol and must not be mixed with this release.
