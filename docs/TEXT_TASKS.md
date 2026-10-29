# Math and QA: one 7B model, separate recursive training

Status: source delivered as `generated_unexecuted`. These commands are complete
entry points for the admitted Local native harness. No model, experiment, or
software test was executed in the Web authoring session.

The current executable configurations, checked on 29 October 2026, start math
and QA independently from the same **Qwen2.5-7B-Instruct** local checkpoint:
`/inspire/hdd/global_public/public_models/Qwen/Qwen2.5-7B-Instruct`.
Both use `loader: causal_lm`, BF16 and SDPA, with SPECTRUM targeting K/V at
zero-based layers **14 and 27**. LoRA trains native Q/K/V/O attention projections.
The text runner binds the actual local checkpoint file hashes; these configs do
not declare an immutable Hugging Face revision for that preinstalled directory.

The earlier 27B text-study description is historical. **ARC still uses the
separate Qwen3.8-27B configuration** and its hybrid-model adapter; see
[MODEL_COMPATIBILITY_27B.md](MODEL_COMPATIBILITY_27B.md). Do not mix the 7B text
studies with old 27B results or acquisition/qualification receipts.

## Exact matrix

| Study | Self-generated training prompts | Fixed reference calibration | Evaluation each round |
|---|---|---|---|
| Math | 1,024 sampled before outcomes from PRM's released 12,000-question train split | 64 disjoint training questions, released reference solutions | All 500 released MATH-500 questions, 16 responses/question |
| QA | 1,024 sampled before outcomes from MMLU `all/auxiliary_train` | 64 disjoint auxiliary questions, reference answer labels | All MMLU-Pro 12,032 questions, one response/question |

GPQA Diamond is an **optional 198-question evaluation**, not part of the current
default QA config. The implementation enables it only with top-level
`include_gpqa: true`. Adding it requires an explicit amended config, existing
dataset access and fresh prepared-data/run directories. The default
`text_qa.json` omits the flag, so its expected evaluation population is MMLU-Pro
alone. An implemented GPQA parser is not evidence that GPQA was evaluated.

Each study also reserves 64 development questions. Train/calibration/development
assignment is one fixed private randomization, saved with permissions `0600` at
`runs/private/multidomain_seed.json`. This is not a multi-training-seed study.
Evaluation questions are never used for generation of training data or gradient
calibration. If GPQA is enabled, its HF split is named `train`, but the entire
Diamond split is **evaluation only**. Exact normalized-question overlaps and duplicates are removed
only from the training pool and recorded. This check is not semantic decontamination.

Four arms: initial model; five rounds of Vanilla SD (`plain`), SSD adaptation
(`ssd`), and SPECTRUM (`spectral_soft`). Every trained arm begins at the same
initial checkpoint and generates a fresh raw corpus at each round. All raw
responses are retained without correctness, reward, length, or text-diversity
selection. Training uses completion targets only and one epoch, LoRA rank/alpha
8, batch 1, accumulation 16, learning rate 1e-5. Prompts are never silently
truncated; training context covers the entire declared synthesis budget.
Math permits 4,096 prompt + 4,096 generated tokens within an 8,192-token SFT
context. QA permits 8,192 prompt + 2,048 generated tokens within 10,240 tokens.
Evaluation has its own prompt allowance and does not enter SFT.

Synthesis/evaluation use one fixed decoder per role. Vanilla/SPECTRUM use
temperature 0.7, top-p 0.8, top-k 20. SSD adaptation uses synthesis temperature
1.5, top-p 0.8, top-k 20 and the common evaluation decoder. It is an explicitly
named adaptation, not the author's released SimpleSD weight comparison. There
is no temperature grid or independent training-repeat axis.

## Input sources and acquisition

The implementation pins the following source identities in
[`text_tasks.py`](../src/improving/text_tasks.py):

| Input | Immutable revision | Native use |
|---|---|---|
| [OpenAI PRM800K](https://github.com/openai/prm800k) | `7ecc794703b2877f63226f2477a49b34f9b25163` | Released MATH 12,000/500 split and unchanged answer grader |
| [MMLU](https://huggingface.co/datasets/cais/mmlu) | `c30699e8356da336a370243923dbaf21066bb9fe` | Auxiliary training split only |
| [MMLU-Pro](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro) | `b189ec765aa7ed75c8acfea42df31fdae71f97be` | Test plus its 70 released prompt demonstrations |
| [GPQA](https://huggingface.co/datasets/Idavidrein/gpqa) | `83022cefff930aea54f654c0b282e74b9eeda5c6` | Optional `gpqa_diamond.csv`, 198 evaluation questions |

PRM's train/test downloads are 10,896,985 and 446,564 bytes. Their SHA256 values
come from the official Git LFS pointers. Grader sources and license are verified
against Git blob identities before import. HF datasets are revision-pinned;
prepared JSONL, native split fingerprints, GPQA CSV digest when enabled, complete denominators
and selection exclusions are saved in `data/multidomain/{math,qa}/manifest.json`.
All data stay on the execution host. Do not publish GPQA questions or private
randomization records to the public repository.

Use an existing qualified environment that supports the configured Qwen2.5
`causal_lm` loader and the text-study dependencies; record its actual package
versions. PRM grading additionally requires `sympy==1.13.3` and
`pylatexenc==2.10`, as listed in the multidomain requirements. Do not upgrade a
running environment to the separate hybrid-27B stack merely because the earlier
guide named 27B. Optional GPQA requires accepting its official HF access terms
and existing user-side HF authentication. Missing GPQA access does not block the
default MMLU-Pro-only QA configuration.

From the delivered repository root, through the admitted Local harness:

```bash
python scripts/prepare_text_data.py --config configs/multidomain/text_math.json
python scripts/prepare_text_data.py --config configs/multidomain/text_qa.json
```

Preparation downloads the actual splits, prepares every native evaluation item,
audits separation and writes checksums. It does not load a model. Matching
prepared outputs are verified and reused; changed configuration/source/data
requires a new directory. A partial download remains `.partial` until verified.
Run these shared-cache writers sequentially.

The current configs expect the preinstalled local 7B checkpoint above. Check that
its complete weights, tokenizer and model metadata are available before running;
change an unavailable host-specific path only in a new run configuration.
Inference uses `local_files_only=true` and fingerprints the local checkpoint.
[`prepare_reasoning_model.py`](../scripts/prepare_reasoning_model.py) requires a
Hugging Face repository name and an immutable `model.revision`; it is not a
download command for these local-path configs, which have no revision field.
The old 27B acquisition commands must not be run with the current math/QA JSON.

## Native scoring protocol

Math uses the final balanced `\\boxed{...}` answer and the unchanged
`grade_answer` from the pinned OpenAI PRM800K grader. Extraction is declared
separately from answer equivalence. **The current math config selects
`math_sandbox.backend: local`**: the grader runs in a plain subprocess with a
10-second timeout, not inside Bubblewrap. This path does not enforce the
configured `memory_mb` address-space limit or provide namespace/network
isolation. It keeps SymPy parsing outside the training process. The optional
native Bubblewrap path remains available for a separately qualified host/config;
its isolation must not be attributed to current local-backend runs. An unparsed
answer or parser timeout counts as incorrect and is separately counted. A grader
process/import failure is an infrastructure error and blocks scoring rather than
turning every prediction into a failure.

MMLU-Pro uses the author's five demonstrations per category and exact three-stage
answer parser from `TIGER-AI-Lab/MMLU-Pro@f418b116db00b065c2aea046518d8fcf74d39872`.
The primary metric counts unparsed output wrong. The author's random-guess
fallback is retained as a separately named secondary score using fixed per-item
randomization. When enabled, GPQA uses the author's base question/choice format and parser
patterns from `idavidrein/gpqa@56686c06f5e19865c153de0fdb11be3890014df7`, with a
fixed per-question choice permutation and a single-response CoT instruction.

These are native datasets and author grading/extraction, under the declared
SPECTRUM chat/sampling protocol. They are **not claimed to reproduce the exact
author leaderboard run**: MMLU-Pro's author command uses greedy decoding and
context-dependent demonstration reduction; this study keeps five examples and
the common sampled decoder. GPQA's original two-call zero-shot CoT procedure
and old hard-coded question skip are not used. All 198 Diamond items remain when
that optional evaluation is enabled.

Reports contain accuracy, complete denominators, per-task accuracy, unparsed and
truncated response counts, grader timeouts and output-token use. Math additionally
reports unbiased pass@1/4/16 from the same 16 responses. QA does not report any-hit pass@k. No AST or surface-text diversity
score is relabeled as mathematical reasoning diversity. Final SPECTRUM-versus-
Vanilla/SSD contrasts include paired task bootstrap intervals conditional on the
single trained trajectory; they do not quantify training-run variability.

## Qualify, run, resume, and report

Qualify the current local 7B model, configured grading backend and the native
fold/restore/LoRA path on the actual allocated GPU. Use the 64 development items
for operational context/memory checks. The existing
`qualify_reasoning_model.py` explicitly requires `qwen3_5_text`; it does not
qualify these `causal_lm` configs. No replacement 7B qualification receipt is
claimed by this documentation update. Determine capacity from actual model
bytes and measured activations/KV/calibration overhead, not the old 27B estimate.
Do not silently switch to 4-bit weights, shorten outputs, drop questions or change
precision after freezing.

Run the following four commands for math, then the same commands with
`text_qa.json`. Each method owns its own output lock and independent lineage:

```bash
python scripts/run_text_study.py --config configs/multidomain/text_math.json --method base
python scripts/run_text_study.py --config configs/multidomain/text_math.json --method plain
python scripts/run_text_study.py --config configs/multidomain/text_math.json --method ssd
python scripts/run_text_study.py --config configs/multidomain/text_math.json --method spectral_soft
python scripts/run_text_study.py --config configs/multidomain/text_math.json --report
```

The same command with `--resume` resumes compatible saved generation chunks or
evaluation following an atomically recorded checkpoint. It rejects changed
model/data/code/runtime/decoder identities. A checkpoint without its commit
receipt is retained as an interrupted save and requires explicit reconciliation.
No completed row or missing row is reported as an inferred zero.

Default `checkpoint_retention="latest"` deletes only the previous checkpoint
inside the same newly created method lineage after its descendant checkpoint,
full evaluation and checksums are sealed. Predictions, covariance artifacts,
training statistics, checkpoint hashes and a pruning receipt are retained.
At a round boundary, predecessor and successor checkpoints plus the original
local model may coexist. Three final method checkpoints remain per domain;
temporary atomic saves need additional space. Budget using the actual 7B
checkpoint sizes. Use `"all"` **before** starting if all 15 method-round
checkpoints per domain are required, plus the original model and temporary files.
Historical or other-lineage checkpoints are never cleaned by this policy.

For a separate transfer/retention evaluation, use a compatible saved 7B text
checkpoint explicitly:

```bash
python scripts/run_text_study.py --config configs/multidomain/text_qa.json --method spectral_soft --evaluate-only --checkpoint runs/multidomain/math-qwen25-7b-instruct/spectral_soft/round_5/model
```

This writes a separately identified transfer result. It does not enter the QA
training trajectory. Main results live in
`runs/multidomain/math-qwen25-7b-instruct/report.json` and
`runs/multidomain/qa-qwen25-7b/report.json`; each round retains raw
predictions, verified records, metrics, resource attempts, checkpoint provenance
and explicit completion hashes. Return aggregate tables, source/run identities
and native replay receipts; retain private prompts and generated data locally.
