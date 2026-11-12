# Four-domain SPECTRUM pilot: interim baseline status

**Snapshot:** 12 November 2026, 20:00 UTC  
**Status:** initial evaluations only; no post-training method comparison is complete.

This is a small pilot on Qwen2.5-7B-Instruct using the sealed four-domain evaluation bundle. Each initial domain evaluation uses 100 tasks and one generation per task. These measurements describe the unmodified starting model; they do not show an effect from SPECTRUM, fixed spectral control, sequential gains, retention, or LoRA.

## Initial baseline measurements

| Domain | Evaluation slice | Result | Notes |
|---|---:|---:|---|
| Math | 100 MATH-500 tasks | 74/100 (74%) | One completion per task; exact-match final-answer scoring |
| QA | 100 MMLU-Pro tasks | 56/100 (56%) | One completion per task |
| Code | 100 MBPP tasks | 16/100 passed (16%) | 81 parse errors, 3 runtime errors, 0 timeouts; treat this as a format/parser warning as well as a code result |
| Safety | 50 harmful + 50 benign SafeChain prompts | 5/50 harmful prompts received a harmful answer (10%); 1/50 benign prompts received a false refusal (2%) | WildGuard judged 100/100 responses; these rates are behavior estimates, not safety accuracy |

Math and MBPP baseline metrics agree across five initialized method lineages. QA has also been completed for the learned-retention lineage: it is 56/100 (56%), with zero grader timeouts, length caps, or unparsed samples, matching the existing initial baseline. The fifth lineage's Code stage is now receipt-verified at 16/100 passed (16%), with 81 parse errors, 3 runtime errors, and 0 timeouts, matching the prior MBPP baseline; this confirms the output-format concern is consistent across lineages. These remain unmodified-model starting measurements; no post-training effect is measured. The Safety result has now been independently recomputed from unchanged initial responses and saved WildGuard outputs for three lineages (fixed-spectrum, sequential, and SD-LoRA); all three produce the same counts, with zero invalid or missing judgments. WildGuard's three labels were stored in the generation field named `completion`; the pilot runner initially looked for a `judgment` field, so its first saved Safety summaries showed 100 invalid judgments. The recomputation reads the stored field correctly and does not regenerate or alter model responses. The third lineage's original summary was preserved, with corrected metrics in a separate, input-hashed sidecar.

The SafeChain slice is small and uses one sample per prompt. It is not an official leaderboard score, and WildGuard judgments are not ground truth. The MBPP parse-error rate is high, so the 16% pass rate should not be read as a clean estimate of coding ability until output-format handling is reviewed.

## Training and evaluation status

Fixed-spectrum, conflict, and SD-LoRA are generating Math training data. At this snapshot their synthesis artifact counts are 112/256, 157/256, and 87/256 records, respectively. SD-LoRA has completed its initial Safety evaluation; its stored Safety summary was corrected from the unchanged responses and WildGuard outputs as described above. Retention has receipt-verified initial Math (74/100), QA (56/100), and Code (16/100, with 81 parse errors) results, and has generated 64/100 initial Safety responses; Safety scoring and its completion receipt are not yet available. Sequential resumed on GPU 0 from saved state with a 39 GiB runtime allocator cap and has generated 6/256 Math synthesis records; the experiment configuration, data, and seed remain unchanged. GPU 0 is using about 76 GiB and GPU 1 about 70 GiB. No post-training method evaluation is complete.

No method should be described as outperforming another from this snapshot. The next comparable table should use completed, receipt-verified post-training evaluation for each method and domain.

## Reproducibility record

The local run artifacts retain per-task outputs, task counts, WildGuard judgments, and scoring receipts. Corrected Safety summaries were written to separate sidecars so the original invalid summaries remain intact. Raw prompts, responses, private seeds, model weights, and local filesystem paths are intentionally not included here.
