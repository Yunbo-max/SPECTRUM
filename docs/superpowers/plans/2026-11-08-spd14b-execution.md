# Qwen2.5-14B SPD execution plan

User-authorized scope: three independent domain trajectories, five distillation rounds each, two SFT epochs per round, physical generation/SFT batch two, at most 4096 newly generated tokens. Preserve all earlier MBPP and other experiment outputs. The initial native model is evaluated before training and each merged round is evaluated independently.

## Frozen study choices

- Qwen/Qwen2.5-14B-Instruct revision cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8, native BF16, no quantization.
- Math: 1024 PRM training prompts, 50 CAL, 64 DEV; MATH-500 500 heldout problems.
- QA: 1024 MMLU auxiliary training prompts, 50 CAL, 64 DEV; GPQA Diamond 198 heldout problems.
- Safety: 1024 SafeChain training prompts, 50 CAL, 64 DEV, 500 heldout prompts. Initial-model-selected reference snippets are fixed across rounds and describe safety relevance, not independently established correctness.
- One sampled response per prompt per stage. All raw synthesis responses enter ordinary LoRA SFT without correctness filtering. Two epochs, microbatch two, accumulation one, rank/alpha eight, learning rate 1e-5. Calibration and temporary generation operators are distinct from ordinary SFT loss.
- SPD uses the pinned upstream centered gradient SVD and half-KV-rank projectors at layers 24 and 47. Geometry is recomputed using each round's predecessor model; operators are removed before training and heldout evaluation.
- Native PRM grading inside bubblewrap for math; fixed GPQA parser for QA. Safety generations remain explicitly unscored until an independent evaluator is specified; do not manufacture safety accuracy.

## Acceptance and execution

1. Verify all pinned asset files and deterministic disjoint prepared splits.
2. CPU tests cover span identities, hook restoration, cached annotations, runner orchestration and interrupted-run recovery.
3. Run actual 14B inference and native scoring, then actual batch-two training memory qualification in /root/ai-venvs/spectrum/bin/python. Qualification using other dependency environments does not qualify production.
4. Run separate two-example, one-round smoke trajectories through actual calibration, projected synthesis, two-epoch SFT, checkpoint and evaluation. These are engineering tests, not benchmark results.
5. Only after successful checks launch formal trajectories with separate output directories, locks, source/runtime/data/model manifests, stage receipts and bounded outer processes. Use CUDA_VISIBLE_DEVICES explicitly.
6. Keep at least 12 GiB device headroom including pre-existing workloads; choose concurrency from actual calibration/training peaks. A PyTorch allocator cap does not guarantee that unrelated processes will not grow.
7. Keep raw outputs and diagnostic receipts. Retain latest own full checkpoint after a successor training/evaluation seal; preserve historical independent experiments. Do not store bulk datasets/model weights in Git.

## Current evidence

All four asset repositories passed size and hash verification. Prepared data hashes/counts and disjointness passed. Actual initial-model math/QA inference with batch two passed; the two math and two QA outputs passed native scorer execution. These four examples do not estimate benchmark accuracy. Longer training qualification, safety annotations and full trajectory smoke tests have separate receipts under /root/ai-assets/spd14b-20261108; no formal score is asserted here.
