# SPECTRUM core audit and release controls

Source inspected: imported `yuhanlydia/improving` revision `45195e866162df1cdf9de0169d2bf17347eb6abf`, with targeted release edits in `src/improving/pipeline.py`, `src/improving/training.py`, and new `tests/test_final_core.py`.

Only source inspection and Python AST parsing were performed. No tests, training, model generation, generated-code execution, or GPU experiments were run. An independent source-only reviewer checked the mathematical protocol and the implementation changes and found no blocking defect. New tests are regression source, not passing test evidence.

## Actual mathematical method

For calibration reference example e, the loss is mean causal next-token NLL over the selected completion labels. Default completion mode selects all reference completion targets; explicit mode uses supplied character spans converted to token labels. Prompt targets are masked in calibration.

For each selected native K/V projection output h, the code differentiates that *per-example mean loss* with respect to h. It accumulates the uncentered gradient second moment

`C = sum_{e,t nonpadding} g[e,t] g[e,t]^T / N_nonpadding`.

Every nonpadding projection-output position contributes to the denominator, including prompt positions and positions whose gradient is zero. Prompt activations can affect completion loss through attention. This is neither a centered covariance nor an average of independently computed per-target-token Fisher outer products. Because each example loss is separately averaged over its targets, different reference lengths can change the relative weighting of their gradients.

With covariance eigenvalues lambda_j and lambda_max > 0, soft gains are

`s_j = 1 / (1 + tau * (1 - lambda_j/lambda_max))`.

Thus the maximum-eigenvalue subspace has gain 1, zero-eigenvalue directions have gain 1/(1+tau), and all gains lie in that interval. Overall scaling of C does not affect the operator. Hard projection uses the configured top eigenspace. `residual_blend` uses `P + rho*(I-P)`.

Existing controls were inspected and retained:

| Control | Implemented matching contract |
| --- | --- |
| `random_soft` | All soft gains retained; seeded Haar orthogonal eigenbasis, independently seeded per projection |
| `isotropic_soft` | Scalar gain `1 - ||I-T_soft||_F/sqrt(d)` |
| `matched_blend` | Same top eigenspace and rho `1 - ||I-T_soft||_F/sqrt(d-r)`; rejects infeasible matching |

All three match Frobenius distance from identity. Only random_soft matches the full soft eigenvalue spectrum. These do not match activation perturbation, output KL, folded parameter change, optimizer steps, or performance. Existing diagnostic fields correctly avoid those stronger claims.

## Folding, SFT, and evaluation

For a row output h and transformation hT, native linear weights and biases are folded as `T.T @ W` and `T.T @ b`. Products use float32 and are cast back to the original parameter dtype. All targets are validated and prepared before any mutation. Exact original tensors are backed up on CPU and restored in `finally`, including generation exceptions.

The fold context surrounds synthetic training generation and optional held-out generation-policy diagnostics only. It ends before SFT. The model then receives one fresh LoRA training run, which is merged into one checkpoint. Subsequent rounds start from that merged model. Post-training evaluation uses its native unfurled weights. There is no adapter pool and no accumulating intervention. Training completions are not verified, scored, quality filtered, AST filtered, or ranked before SFT.

Historical fixed-epoch SFT defaults to all-token loss, including prompt labels after the causal shift. Original sampled completion token IDs are retained when available. Padding masks by position, preserving real EOS labels even when PAD=EOS. Declared `max_length` truncation remains; its dropped-token count is now also audited per record. No extra label masking or final-example truncation is introduced by the budget control.

## Fixed references and fixed geometry

Default `calibration.reestimate_each_round: true` recalibrates the current unfurled student each round on the same ordered subset `calibration_tasks[:max_examples]`. This means fixed references, not fixed covariance. The references are never generated or selected from round outcomes.

`calibration.reestimate_each_round: false` is the existing fixed-geometry control; no new method name was needed. It uses the base/round-one calibration. Release changes additionally persist the actual matrices in `round_1/fixed_operators.pt` and reload them unchanged each round. The cache validates method, seed, operator settings, calibration-file hash, tensor names, shapes, dtype, finiteness, and exact tensor hashes. Later rounds reject missing original matrices instead of rebuilding them. Each temporary intervention still acts on that round's current student and is restored before learning.

Calibration artifacts now include and validate ordered reference content hashes, reference task IDs, model identity, loss/moment definitions, max length, span mode, and native output location. Reused artifacts additionally validate current target projection dimensions. Round provenance records matrix hashes, matrix source, and generation-only lifetime. Legacy artifacts without the new metadata are rejected, consistently with the full-run implementation-fingerprint rule; use a new output directory for this release.

## Bounded token-exposure control

Public config: `train.target_token_budget: <positive integer>`; omit or set null for unchanged fixed-epoch training.

For each already encoded record, the planner counts labels after the causal shift (`labels[1:] != -100`). This includes prompt targets in the default all-token mode. The budget is total supervised target-token *presentations per round*, not sampled completion tokens, FLOPs, equal optimizer steps, or exactly equal statistical weighting.

The budget must be at least one full encoded corpus pass. Smaller budgets fail explicitly before LoRA/model mutation, so all raw completions remain in the corpus and are exposed at least once. A local seeded RNG produces permutations of the full record list. Training uses complete passes and then a prefix of the final permutation, including the complete crossing record. No correctness or code content enters ordering. It does not reorder by length or selectively drop long records. The plan is made before batching, and there is no second DataLoader shuffle.

For budget B, actual count A, and maximum per-record count n_max, `0 <= A-B < n_max`. This is a bounded matching control; it is not claimed to hit an exact integer count. Choose the common B prospectively large enough for every arm and round; do not change it separately after observing corpus sizes. Effective targets are counted after normal declared max-length encoding; raw completion text and sampled IDs remain in the generation artifact.

Token mode explicitly supersedes epochs, records `epochs: null`, preserves the configured positive epoch value as inactive provenance, sizes scheduler steps from the actual planned loader, and handles final incomplete gradient accumulation. Existing microbatch-mean loss normalization is preserved, so target presentations should not be described as perfectly equal loss weight.

New statistics include requested and actual targets, overshoot and strict bound, full/partial corpus passes, plan hash, optimizer steps, raw/total record retention, per-record exposure/truncation counts, and exposure tokens by synthetic/reference origin. Default fixed-epoch behavior and existing metric calculations remain unchanged.

## Optional reference-information control

Public config: `train.fixed_anchor_replay: true`, valid only in a separate config with `methods: [plain]`.

The pipeline preserves all synthetic rows in `train.jsonl` and appends one reference copy per same fixed calibration-subset task to the SFT corpus each round. It saves the added rows separately in `anchor_replay.jsonl`, plus task IDs, reference hash, origin accounting, and explicit supervised-replay provenance. One copy in the corpus is repeated under the configured epoch or token-exposure protocol; it is not necessarily exactly one optimizer exposure per round. All rows remain subject to the same SFT loss scope and declared max length.

This baseline controls access to the calibration reference tasks. It is explicitly supervised replay, not an all-synthetic main-method run. It can train more reference labels than explicit calibration spans, and default fixed-epoch replay has more training tokens/compute. Provenance states both limitations. Combining it with a common target-token budget is permitted if that budget covers the entire combined corpus.

## Model architecture compatibility

The implementation targets exact native `model.layers.i.self_attn.k_proj` and `v_proj` Linear outputs before RoPE/key normalization. Transform dimension is the native projection's output width, not the number of query heads or model hidden width. It mixes the complete output space across KV heads. GQA and MHA both fit this implementation; the headwise interpretation differs. Quantized, adapter-wrapped, fused, or nonnative projections are rejected rather than guessed.

Official config values checked by the model-spec audit:

| Instruct model | Native family | Layers | Hidden width | Q heads | KV heads | Head width | K/V output width |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen2.5-Coder-1.5B | qwen2 | 28 | 1536 | 12 | 2 | 128 | 256 |
| Qwen2.5-Coder-3B | qwen2 | 36 | 2048 | 16 | 2 | 128 | 256 |
| Qwen2.5-Coder-7B | qwen2 | 28 | 3584 | 28 | 4 | 128 | 512 |
| DeepSeek-Coder-6.7B | llama | 32 | 4096 | 32 | 32 | 128 | 4096 |

Sources: official Hugging Face model `config.json` files at the following resolved revisions:

- `Qwen/Qwen2.5-Coder-1.5B-Instruct`: `2e1fd397ee46e1388853d2af2c993145b0f1098a`.
- `Qwen/Qwen2.5-Coder-3B-Instruct`: `488639f1ff808d1d3d0ba301aef8c11461451ec5`.
- `Qwen/Qwen2.5-Coder-7B-Instruct`: `c03e6d358207e414f1eca0bb1891e29f1db0e242`.
- `deepseek-ai/deepseek-coder-6.7b-instruct`: `e5d64addd26a6a1db0f9b863abf6ee3141936807`.

This is config/topology compatibility evidence, not a runtime qualification of four downloaded models. DeepSeek's 4096-dimensional dense covariance has 64x the entries of a 512-dimensional Qwen-7B covariance. Dense eigendecomposition is cubic in that width, so DeepSeek calibration can be materially more expensive despite similar parameter count. Four float64 4096x4096 matrices alone occupy approximately 512 MiB; covariance/eigenbasis/moment-sum copies increase CPU footprint. No runtime or GPU memory estimate was measured.

## Verification provided

AST parsing succeeded for `spectral.py`, `calibration.py`, `training.py`, `pipeline.py`, `generation.py`, and `tests/test_final_core.py`; no imports or executable model/test work occurred in that check.

New unexecuted regression source covers deterministic budget planning and strict overshoot, invalid/undersized budgets, causal/EOS/padding/truncation token counts, budget-mode scheduler and full retention, validation before LoRA mutation, fixed-reference metadata, exact matrix cache reuse and corruption/missing-cache rejection, nonaccumulating fold restoration, anchor origin accounting, plain-only config validation, and GQA/MHA native projection shapes. Existing spectrum, matched-control, fold/logit, and calibration tests were inspected rather than duplicated or run.
