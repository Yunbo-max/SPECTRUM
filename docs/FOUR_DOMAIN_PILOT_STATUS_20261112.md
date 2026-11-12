# Four-domain SPECTRUM pilot: interim baseline status

**Snapshot:** 12 November 2026, 20:49 UTC  
**Status:** initial evaluations only; no post-training method comparison is complete.

This is a small pilot on Qwen2.5-7B-Instruct using the sealed four-domain evaluation bundle. Each initial domain evaluation uses 100 tasks and one generation per task. These measurements describe the unmodified starting model; they do not show an effect from SPECTRUM, fixed spectral control, sequential gains, retention, conflict handling, or LoRA.

## Initial baseline measurements

| Domain | Evaluation slice | Result | Notes |
|---|---:|---:|---|
| Math | 100 MATH-500 tasks | 74/100 (74%) | One completion per task; exact-match final-answer scoring |
| QA | 100 MMLU-Pro tasks | 56/100 (56%) | One completion per task |
| Code | 100 MBPP tasks | 16/100 passed (16%) | 81 parse errors, 3 runtime errors, 0 timeouts; treat this as a format/parser warning as well as a code result |
| Safety | 50 harmful + 50 benign SafeChain prompts | 5/50 harmful prompts received a harmful answer (10%); 1/50 benign prompts received a false refusal (2%) | WildGuard judged 100/100 responses; these rates are behavior estimates, not safety accuracy |

Math and MBPP baseline metrics agree across five initialized method lineages. QA has also been completed for the learned-retention lineage: it is 56/100 (56%), with zero grader timeouts, length caps, or unparsed samples, matching the existing initial baseline. The fifth lineage's Code stage is receipt-verified at 16/100 passed (16%), with 81 parse errors, 3 runtime errors, and 0 timeouts, matching the prior MBPP baseline; this confirms the output-format concern is consistent across lineages. These remain unmodified-model starting measurements; no post-training effect is measured.

The Safety behavior counts have now been independently recomputed from unchanged initial responses and stored WildGuard outputs for four lineages (fixed-spectrum, sequential, SD-LoRA, and learned-retention). Each has 100 responses and 100 judgments, with zero invalid or missing judgments; all four yield the same counts shown above. The runner initially looked for WildGuard labels in a `judgment` field, while the stored labels were in `completion`; its raw summaries therefore recorded 100 invalid judgments. The corrected scorer reads the stored field without regenerating or altering model responses. Corrected metrics are preserved in separate, input-hashed sidecars, and the original summaries remain untouched.

The SafeChain slice is small and uses one sample per prompt. It is not an official leaderboard score, and WildGuard judgments are not ground truth. The MBPP parse-error rate is high, so the 16% pass rate should not be read as a clean estimate of coding ability until output-format handling is reviewed.

## Training and evaluation status

**Correction to the earlier progress counts:** the counter included the eight top-level fields in each synthesis `manifest.json` as if they were generated examples. Counts below include only saved task records from synthesis part files; task IDs are unique within each counted set.

Current Math synthesis records are: fixed-spectrum 186/256, learned-conflict 256/256, learned-retention 58/256, and SD-LoRA 158/256. Sequential has 39/256 saved Math synthesis records and is paused. These are generated training records, not training-completion or evaluation metrics. The learned-retention initial Safety sidecar is complete and receipt inputs were left unchanged.

The learned-conflict synthesis stage has now sealed its completion receipt at 256 records, and a training intent has been recorded. Its training receipt/checkpoint and post-training evaluation are not yet available. No post-training method evaluation is complete.

GPU 0 is using about 75.0 GiB and GPU 1 about 68.5 GiB. Sequential remains paused because per-process allocator limits do not impose an aggregate GPU memory limit; continuing all GPU 0 jobs together had pushed aggregate use above the 85 GiB target. Its case configuration, dataset, and seed are unchanged; resumption is pending sufficient GPU 0 headroom.

Do not interpret synthesis counts or initial baselines as evidence that one method outperforms another. The comparable results table requires completed, receipt-verified post-training evaluation for each method and domain.

## Reproducibility record

Local run artifacts retain per-task outputs, task counts, WildGuard judgments, and scoring receipts. Corrected Safety summaries were written to separate sidecars so the original invalid summaries remain intact. Raw prompts, responses, private seeds, model weights, and local filesystem paths are intentionally not included here.
