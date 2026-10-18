# SPECTRUM continuation guidance — official implementation first

The user has paused research execution. This handoff does not authorize resumption. Keep the existing Harness lifecycle and resume only on a subsequent user instruction.

After authorized resumption, continue the same SPECTRUM C-stage question, using the living handbook and B/C memory. Follow AGENTS.md and research-guidance/prompt-{B,C,D,E}.md, especially research-guidance/prompt-upstream-code.md. Consult applicable author-maintained or author-recommended implementations when using or questioning existing evaluation/code. Diagnose evaluation and adaptation artifacts before claiming a model failure or research gap. Hardware/dependency adaptation and GPU debugging remain autonomous; no experimental admission schema is required.

The old custom MBPP evaluators were removed. Preserve original predictions, scores and logs as historical custom-protocol diagnostics. Do not recreate those scorers or rerun the deleted sensitivity runner. Official-source inspection found Google MBPP data/specification, Qwen model-author evaluation scripts, and the EvalPlus implementation they reference. These have different provenance; source inspection is not a completed official evaluation. Consult upstream-evaluation-20261018/source-notes.md. New evaluation must use compatible upstream data/prompt/generation/extraction/scoring; regenerate when the old 500-task outputs do not match the selected protocol.

Use the existing authorized GPU and one experiment program at a time. Reconcile actual jobs before launching anything, update memory with evidence and limitations, and preserve credentials outside Git. The Mac remains lightweight orchestration.
