# Final study: data and model contract

`configs/final/assets.json` is the machine-readable source of truth. Its four model revisions and four Hugging Face dataset revisions are full immutable commit hashes, verified against the original repositories on 2026-10-02. HumanEval+ instead pins EvalPlus 0.3.1 and fixture release v0.1.10. This document specifies the final experiment, not measured results. No model weights, training run, or benchmark execution was used to produce the specification.

## Training, anchors, validation and evaluation

| Dataset | Population in final study | Role | Preparation path |
|---|---:|---|---|
| MBPP `full` | 291 train; 50 calibration anchors; 30 validation; 500 test | Only source of training, anchors and validation; in-domain evaluation | `data/final/mbpp/` |
| HumanEval+ | All 164 problems | Transfer evaluation only | `data/final/benchmarks/humanevalplus/` |
| APPS introductory | Fixed 200 from official test, introductory difficulty | Transfer evaluation only, adapted verifier | `data/final/benchmarks/apps_intro/` |
| CodeContests | All 165 official test problems | Transfer evaluation only, adapted verifier | `data/final/benchmarks/codecontests/` |
| LiveCodeBench | Fixed 200 from `release_v5`, UTC contest dates in `[2024-07-01, 2025-01-01)` | Transfer evaluation only, adapted verifier | `data/final/benchmarks/livecodebench/` |

MBPP's original `full/train` has 374 problems. The existing protocol first removes original-prompt duplicates against the untouched 500-problem official test set, then removes remaining train-pool duplicates by lowest numeric problem ID. The final expected clean pool is 371. The preparation command asserts the resulting 291/50/30/500 counts; it aborts on drift instead of silently changing the experiment. The official MBPP validation and prompt splits are unused. The study's 30-problem validation set is a disjoint partition of the cleaned official training pool.

The private data seed determines the shuffled MBPP partitions and the APPS/LiveCodeBench samples. Transfer candidates are sorted lexicographically by task ID before the seeded shuffle; the selected IDs are sorted again for evaluation. Date and difficulty filters and exact overlap removal are fixed before any model generation. No task is selected or discarded based on model success, reference execution, answer difficulty as measured by a model, or test outcomes. The private manifests record actual selected IDs, seed, source revision, all exclusions, source metadata, and output SHA-256 hashes. All trained methods, seeds and checkpoints must use this same prepared population.

For LiveCodeBench, `release_v5` means exactly `test.jsonl`, `test2.jsonl`, `test3.jsonl`, `test4.jsonl`, and `test5.jsonl` at the pinned repository revision. The date range is an additional fixed filter, not a moving “latest” setting. Selection must yield exactly 200 problems or preparation fails. The July–December 2024 window does **not** establish that the problems were absent from any model's pretraining or instruction tuning.

## Verifier meaning

MBPP uses its published original test list and setup code, with the repository's function-interface prompt. Only the callable signature is derived from the reference AST; reference behavior is not inserted into the prompt. HumanEval+ retains original continuation prompts and delegates correctness to the pinned EvalPlus base **and** plus tests through the existing Docker bridge. Any code extraction policy is recorded in evaluator provenance. Its original tests are not substituted with hand-written assertions.

APPS, CodeContests and LiveCodeBench use **adapted verification**, not official leaderboard execution. Standard-input problems are prompted as `solve(stdin: str) -> str`; their outputs use whitespace-token equality without numerical tolerance. Published callable interfaces are preserved, with `Solution()` used when the starter declares that class; outputs use JSON structural equality. All available selected-problem fixtures are retained. CodeContests combines public, private and generated fixtures; LiveCodeBench combines public and private fixtures. These protocols can yield different scores from the benchmarks' original harnesses. Reports must preserve the adapted label.

The final execution protocol uses bounded Docker evaluation. An explicitly enabled legacy unsafe local backend is a separate diagnostic mode and must not be reported as the final Docker result. Dataset preparation only parses and serializes fixtures; it executes no candidate or reference programs.

## Contamination checks and limits

The exact-match check normalizes Unicode with NFKC, collapses whitespace and hashes both original and prepared prompts. Every transfer target is checked against MBPP train, calibration and validation. MBPP and HumanEval+ overlap aborts; CodeContests overlap also aborts to preserve its full official denominator. APPS and LiveCodeBench exact matches are removed and logged before their fixed-size selection. MBPP partition overlap is rejected by task ID and normalized prompt. A final audit reports exact prompt overlaps across evaluation benchmarks without changing any denominator.

These checks do not detect paraphrases, similar solutions, benchmark exposure during model pretraining, or every possible semantic overlap. No “contamination-free” claim follows from this audit. Evaluation datasets provide no calibration anchors or training solutions. Prepared data and private seed records must remain outside the public result package when their contents expose seed values.

## Four fully trained backbones

All four rows are final training backbones: each receives the prescribed training arms, independent runs and checkpoint evaluation. A frozen initial-model-only score is a baseline, not evidence that an additional backbone was trained.

| Alias | Exact repository | Layers | Hidden width | Query/KV heads | Head width | K or V output width | Model type | License recorded upstream |
|---|---|---:|---:|---:|---:|---:|---|---|
| `qwen1.5b` | `Qwen/Qwen2.5-Coder-1.5B-Instruct` | 28 | 1536 | 12 / 2 | 128 | 256 | `qwen2` | Apache-2.0 |
| `qwen3b` | `Qwen/Qwen2.5-Coder-3B-Instruct` | 36 | 2048 | 16 / 2 | 128 | 256 | `qwen2` | Qwen Research |
| `qwen7b` | `Qwen/Qwen2.5-Coder-7B-Instruct` | 28 | 3584 | 28 / 4 | 128 | 512 | `qwen2` | Apache-2.0 |
| `deepseek6.7b` | `deepseek-ai/deepseek-coder-6.7b-instruct` | 32 | 4096 | 32 / 32 | 128 | 4096 | `llama` | DeepSeek custom model license |

The Qwen models use native `Qwen2ForCausalLM` with grouped-query attention; DeepSeek uses native `LlamaForCausalLM` with multi-head attention. They load without remote model code. The projection hook path is `model.layers.<layer>.self_attn.{k_proj,v_proj}`. The method acts on complete native K/V projection outputs before rotary position encoding, rather than on a post-RoPE cache or separate per-head subspaces. The Qwen K/V projections include bias under the pinned Transformers implementation; DeepSeek's model config explicitly disables attention bias. Architecture compatibility is a source-level assessment until the requested runtime validation is performed.

| Asset | Pinned revision |
|---|---|
| Qwen Coder 1.5B Instruct | `2e1fd397ee46e1388853d2af2c993145b0f1098a` |
| Qwen Coder 3B Instruct | `488639f1ff808d1d3d0ba301aef8c11461451ec5` |
| Qwen Coder 7B Instruct | `c03e6d358207e414f1eca0bb1891e29f1db0e242` |
| DeepSeek Coder 6.7B Instruct | `e5d64addd26a6a1db0f9b863abf6ee3141936807` |
| MBPP | `4bb6404fdc6cacfda99d4ac4205087b89d32030c` |
| APPS | `21e74ddf8de1a21436da12e3e653065c5213e9d1` |
| CodeContests | `802411c3010cb00d1b05bad57ca77365a3c699d6` |
| LiveCodeBench | `0fe84c3912ea0c4d4a78037083943e8f0c4dd505` |

## Preparation command and outputs

After creating the private seed manifest with the final runner, prepare data once:

```bash
python scripts/prepare_final_data.py \
  --assets configs/final/assets.json \
  --seed-file runs/private/seeds.json \
  --output-dir data/final
```

The seed manifest must contain an integer `data_seed`. An explicit `--split-seed` can replace `--seed-file`, but there is no numeric default and no example exposing a real seed. Reusing a prepared directory requires an exact request match and intact checksums. Changing assets or selection settings requires a new output directory. The command does not start model training or evaluation.

`data/final/assets.lock.json` freezes the specification before download. Each dataset writes its task JSONL and `manifest.json`; MBPP also writes its train/calibration/validation files and decontamination manifest, and HumanEval+ writes official fixture metadata. The final `benchmark_registry.json` is created only after all five preparations pass their population gates. It records evaluator labels, task hashes, manifest hashes and the contamination-audit path. Keep this registry with the run's provenance.

## Primary sources

- [MBPP dataset and official split metadata](https://huggingface.co/datasets/google-research-datasets/mbpp/tree/4bb6404fdc6cacfda99d4ac4205087b89d32030c)
- [APPS test files](https://huggingface.co/datasets/codeparrot/apps/tree/21e74ddf8de1a21436da12e3e653065c5213e9d1)
- [CodeContests official split metadata](https://huggingface.co/datasets/deepmind/code_contests/blob/802411c3010cb00d1b05bad57ca77365a3c699d6/dataset_infos.json)
- [LiveCodeBench release-to-file mapping](https://huggingface.co/datasets/livecodebench/code_generation_lite/blob/0fe84c3912ea0c4d4a78037083943e8f0c4dd505/code_generation_lite.py)
- [EvalPlus v0.3.1 HumanEval fixture loader](https://github.com/evalplus/evalplus/blob/v0.3.1/evalplus/data/humaneval.py)
- [Qwen 1.5B configuration](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct/blob/2e1fd397ee46e1388853d2af2c993145b0f1098a/config.json)
- [Qwen 3B configuration](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct/blob/488639f1ff808d1d3d0ba301aef8c11461451ec5/config.json)
- [Qwen 7B configuration](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct/blob/c03e6d358207e414f1eca0bb1891e29f1db0e242/config.json)
- [DeepSeek 6.7B configuration](https://huggingface.co/deepseek-ai/deepseek-coder-6.7b-instruct/blob/e5d64addd26a6a1db0f9b863abf6ee3141936807/config.json)

Repository license labels are recorded for provenance, not homogenized across models. LiveCodeBench's card says `cc` while its builder declares `MIT License`; its collected problem statements retain their original-source rights. Consult the pinned upstream license files before redistribution.
