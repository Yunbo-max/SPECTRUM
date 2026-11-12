# Four-domain SPECTRUM pilot: interim results and status

**Snapshot:** 12 November 2026, 21:47 UTC  
**Status:** one post-training Math evaluation is complete; the four-domain method comparison remains in progress.

This is a small pilot on Qwen2.5-7B-Instruct using the sealed four-domain evaluation bundle. Each evaluation slice uses 100 tasks and one generation per task unless specified below.

## Initial, unmodified-model measurements

| Domain | Evaluation slice | Result | Notes |
|---|---:|---:|---|
| Math | 100 MATH-500 tasks | 74/100 (74%) | One completion per task; exact-match final-answer scoring |
| QA | 100 MMLU-Pro tasks | 56/100 (56%) | One completion per task |
| Code | 100 MBPP tasks | 16/100 passed (16%) | 81 parse errors, 3 runtime errors, 0 timeouts; treat this as a format/parser warning as well as a code result |
| Safety | 50 harmful + 50 benign SafeChain prompts | 5/50 harmful prompts received a harmful answer (10%); 1/50 benign prompts received a false refusal (2%) | WildGuard judged 100/100 responses; these rates are behavior estimates, not safety accuracy |

Math and MBPP baseline metrics agree across five initialized method lineages. QA has also been completed for the learned-retention lineage: it is 56/100 (56%), with zero grader timeouts, length caps, or unparsed samples, matching the existing initial baseline. The fifth lineage's Code stage is receipt-verified at 16/100 passed (16%), with 81 parse errors, 3 runtime errors, and 0 timeouts, matching the prior MBPP baseline; this confirms the output-format concern is consistent across lineages.

The Safety behavior counts have been independently recomputed from unchanged initial responses and stored WildGuard outputs for four lineages (fixed-spectrum, sequential, SD-LoRA, and learned-retention). Each has 100 responses and 100 judgments, with zero invalid or missing judgments; all four yield the same counts above. The runner initially looked for WildGuard labels in a `judgment` field, while the stored labels were in `completion`; its raw summaries therefore recorded 100 invalid judgments. The corrected scorer reads the stored field without regenerating or altering model responses. Corrected metrics are preserved in separate, input-hashed sidecars, and the original summaries remain untouched.

The SafeChain slice is small and uses one sample per prompt. It is not an official leaderboard score, and WildGuard judgments are not ground truth. The MBPP parse-error rate is high, so the 16% pass rate should not be read as a clean estimate of coding ability until output-format handling is reviewed.

## First post-training result

| Method and stage | Evaluation | Result | Validity notes |
|---|---|---|---|
| Learned-conflict, after Math stage (256 generated training records, 1 SFT epoch) | Same 100 MATH tasks as the initial baseline | 75/100 (75%) vs. initial 74/100 (74%) | Same task IDs, one sample/task; 1 unparsed sample, 0 timeouts, 0 length caps |

This is a +1 percentage-point difference on a single 100-task pilot slice. It is exploratory and does not establish a reliable improvement. The result is the learned-conflict Math-stage checkpoint only; it is not the completed four-domain continual-learning comparison.

## Training and evaluation status

**Correction to earlier progress counts:** the counter included the eight top-level fields in each synthesis `manifest.json` as if they were generated examples. The counts below include only saved task records from synthesis part files; task IDs are unique within each counted set.

Current Math synthesis records are: fixed-spectrum 256/256, learned-conflict 256/256, learned-retention 205/256, SD-LoRA 256/256, and sequential 39/256 (paused). Fixed-spectrum and learned-conflict have committed Math training checkpoints. Learned-conflict's Math evaluation is complete; its QA evaluation has 39/100 outputs at this snapshot. Fixed-spectrum's Math evaluation has 21/100 outputs. Retention and SD-LoRA have not yet produced Math training checkpoints. No method has completed the four-domain continual-learning evaluation.

GPU 0 is using about 75.0 GiB and GPU 1 about 75.5 GiB. Sequential remains paused because per-process allocator limits do not impose an aggregate GPU memory limit; running all GPU 0 jobs together had pushed aggregate use above the 85 GiB target. Its case configuration, data, and seed are unchanged.

## Reproducibility record

Local run artifacts retain per-task outputs, task counts, WildGuard judgments, and scoring receipts. Corrected Safety summaries were written to separate sidecars so the original invalid summaries remain intact. Raw prompts, responses, private seeds, model weights, and local filesystem paths are intentionally not included here.

The next comparable table requires completed, receipt-verified evaluation across all four domains for each method. Do not interpret this single 100-task result or synthesis counts as evidence that one method outperforms another.
