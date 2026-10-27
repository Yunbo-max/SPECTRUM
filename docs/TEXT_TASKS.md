# Math and QA: one 27B model, separate recursive training

Status: source delivered as `generated_unexecuted`. These commands are complete
entry points for the admitted Local native harness. No model, experiment, or
software test was executed in the Web authoring session.

Both studies start independently from the same pinned `Qwen/Qwen3.8-27B` model
(`1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`), using its official text backbone and
fixed non-thinking chat mode. The model's full-attention K/V projections at
zero-based layers 31 and 63 are SPECTRUM's calibration/intervention targets.
Gated-delta layers are outside that intervention. LoRA SFT targets the native
Q/K/V/O projections in full-attention layers. See
[MODEL_COMPATIBILITY_27B.md](MODEL_COMPATIBILITY_27B.md) for the source audit.

## Exact matrix

| Study | Self-generated training prompts | Fixed reference calibration | Evaluation each round |
|---|---|---|---|
| Math | 1,024 sampled before outcomes from PRM's released 12,000-question train split | 64 disjoint training questions, released reference solutions | All 500 released MATH-500 questions, 16 responses/question |
| QA | 1,024 sampled before outcomes from MMLU `all/auxiliary_train` | 64 disjoint auxiliary questions, reference answer labels | All MMLU-Pro 12,032 questions and GPQA Diamond 198 questions, one response/question |

Each study also reserves 64 development questions. Train/calibration/development
assignment is one fixed private randomization, saved with permissions `0600` at
`runs/private/multidomain_seed.json`. This is not a multi-training-seed study.
Evaluation questions are never used for generation of training data or gradient
calibration. GPQA's HF split is named `train`; here the entire Diamond split is
**evaluation only**. Exact normalized-question overlaps and duplicates are removed
only from the training pool and recorded. This check is not semantic decontamination.

Four arms: initial model; five rounds of Vanilla SD (`plain`), SSD adaptation
(`ssd`), and SPECTRUM (`spectral_soft`). Every trained arm begins at the same
initial checkpoint and generates a fresh raw corpus at each round. All raw
responses are retained without correctness, reward, length, or text-diversity
selection. Training uses completion targets only and one epoch, LoRA rank/alpha
8, batch 1, accumulation 16, learning rate 1e-5. Prompts are never silently
truncated; training context covers the entire declared generation budget.

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
| [GPQA](https://huggingface.co/datasets/Idavidrein/gpqa) | `83022cefff930aea54f654c0b282e74b9eeda5c6` | `gpqa_diamond.csv`, 198 evaluation questions |

PRM's train/test downloads are 10,896,985 and 446,564 bytes. Their SHA256 values
come from the official Git LFS pointers. Grader sources and license are verified
against Git blob identities before import. HF datasets are revision-pinned;
prepared JSONL, native split fingerprints, GPQA CSV digest, complete denominators
and selection exclusions are saved in `data/multidomain/{math,qa}/manifest.json`.
All data stay on the execution host. Do not publish GPQA questions or private
randomization records to the public repository.

Use the new 27B environment, not the older Transformers 4.51.3 coding environment.
PRM grading additionally requires `sympy==1.13.3` and `pylatexenc==2.10` as pinned
in the new environment requirements. GPQA requires accepting its official HF
access terms and existing user-side HF authentication; absent access blocks QA
preparation without substituting another dataset.

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

Model acquisition is the separate
[`prepare_reasoning_model.py`](../scripts/prepare_reasoning_model.py) entry.
Inference insists on `local_files_only=true`, and fingerprints every model shard.
No runtime can silently replace the pinned model with a newly downloaded version.

## Native scoring protocol

Math uses the final balanced `\\boxed{...}` answer and the unchanged
`grade_answer` from the pinned OpenAI PRM800K grader. Extraction is declared
separately from answer equivalence. Every grader call runs inside the native
Bubblewrap namespace boundary, with no network, read-only trusted runtime/source
files, and a 10-second wall-time/2 GiB address-space limit. It never imports the
SymPy parser into the training process. An unparsed answer or a parser timeout
counts as incorrect and is separately counted. Failure to start the sandbox or
import the grader is an infrastructure error and blocks scoring rather than
turning every prediction into a failure.

MMLU-Pro uses the author's five demonstrations per category and exact three-stage
answer parser from `TIGER-AI-Lab/MMLU-Pro@f418b116db00b065c2aea046518d8fcf74d39872`.
The primary metric counts unparsed output wrong. The author's random-guess
fallback is retained as a separately named secondary score using fixed per-item
randomization. GPQA uses the author's base question/choice format and parser
patterns from `idavidrein/gpqa@56686c06f5e19865c153de0fdb11be3890014df7`, with a
fixed per-question choice permutation and a single-response CoT instruction.

These are native datasets and author grading/extraction, under the declared
SPECTRUM chat/sampling protocol. They are **not claimed to reproduce the exact
author leaderboard run**: MMLU-Pro's author command uses greedy decoding and
context-dependent demonstration reduction; this study keeps five examples and
the common sampled decoder. GPQA's original two-call zero-shot CoT procedure
and old hard-coded question skip are not used. All 198 Diamond items remain.

Reports contain accuracy, complete denominators, per-task accuracy, unparsed and
truncated response counts, grader timeouts and output-token use. Math additionally
reports unbiased pass@1/4/16 from the same 16 responses. QA does not report any-hit pass@k. No AST or surface-text diversity
score is relabeled as mathematical reasoning diversity. Final SPECTRUM-versus-
Vanilla/SSD contrasts include paired task bootstrap intervals conditional on the
single trained trajectory; they do not quantify training-run variability.

## Qualify, run, resume, and report

First run the shared model and native sandbox qualification from the main
runbook on the actual allocated GPU. Use the 64 development items for operational
context/memory checks. A BF16 27B model has approximately 54 GB of parameter data
before activations, KV cache, calibration tensors or optimizer state; hardware
capacity and throughput remain unmeasured. Do not silently switch to a 4-bit
checkpoint, shorten outputs, drop questions, or change precision after freezing.

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
At a round boundary, at least two full checkpoint copies plus the HF base cache
may coexist (approximately 162 GB before other files); final checkpoints across
three methods remain (approximately 162 GB per domain, plus the shared base).
Use `"all"` **before** starting if every intermediate weight is required; that
is approximately 810 GB per domain before base/cache/temporary save overhead.
Historical or other-lineage checkpoints are never cleaned by this policy.

For a separate transfer/retention evaluation, use a compatible saved 27B text
checkpoint explicitly:

```bash
python scripts/run_text_study.py --config configs/multidomain/text_qa.json --method spectral_soft --evaluate-only --checkpoint runs/multidomain/math-qwen38-27b/spectral_soft/round_5/model
```

This writes a separately identified transfer result. It does not enter the QA
training trajectory. Main results live in
`runs/multidomain/{math,qa}-qwen38-27b/report.json`; each round retains raw
predictions, verified records, metrics, resource attempts, checkpoint provenance
and explicit completion hashes. Return aggregate tables, source/run identities
and native replay receipts; retain private prompts and generated data locally.
