# Four-domain SPECTRUM pilot: interim baseline status

**Snapshot:** 12 November 2026  
**Status:** initial evaluations only; no post-training method comparison is complete.

This is a small pilot on Qwen2.5-7B-Instruct using the sealed four-domain evaluation bundle. Each initial domain evaluation uses 100 tasks and one generation per task. These measurements describe the unmodified starting model; they do not show an effect from SPECTRUM, fixed spectral control, sequential gains, retention, or LoRA.

## Initial baseline measurements

| Domain | Evaluation slice | Result | Notes |
|---|---:|---:|---|
| Math | 100 MATH-500 tasks | 74/100 (74%) | One completion per task; exact-match final-answer scoring |
| QA | 100 MMLU-Pro tasks | 56/100 (56%) | One completion per task |
| Code | 100 MBPP tasks | 16/100 passed (16%) | 81 parse errors, 3 runtime errors, 0 timeouts; treat this as a format/parser warning as well as a code result |
| Safety | 50 harmful + 50 benign SafeChain prompts | 5/50 harmful prompts received a harmful answer (10%); 1/50 benign prompts received a false refusal (2%) | WildGuard judged 100/100 responses; these rates are behavior estimates, not safety accuracy |

Math, QA, and MBPP baseline metrics agree across the four initialized method lineages. The Safety result was independently recomputed from the unchanged initial responses and saved WildGuard outputs for two lineages; both produced the same counts, with zero invalid or missing judgments. WildGuard's three labels were stored in the generation field named `completion`; the pilot runner initially looked for a `judgment` field, so its first saved Safety summaries showed 100 invalid judgments. The recomputation reads the stored field correctly and does not regenerate or alter model responses.

The SafeChain slice is small and uses one sample per prompt. It is not an official leaderboard score, and WildGuard judgments are not ground truth. The MBPP parse-error rate is high, so the 16% pass rate should not be read as a clean estimate of coding ability until output-format handling is reviewed.

## Training and evaluation status

The fixed-spectrum lineage has entered Math synthesis. SD-LoRA and retention are still progressing through the initial evaluation pipeline. Sequential and conflict gain runs are being resumed from preserved artifacts after a Safety-scoring schema mismatch and GPU memory-limit adjustments. Their post-training evaluations are not yet available.

No method should be described as outperforming another from this snapshot. The next comparable table should use completed, receipt-verified post-training evaluation for each method and domain.

## Reproducibility record

The local run artifacts retain per-task outputs, task counts, WildGuard judgments, and scoring receipts. The corrected Safety summaries were written to a separate sidecar so the original invalid summaries remain intact. Raw prompts, responses, private seeds, model weights, and local filesystem paths are intentionally not included here.
