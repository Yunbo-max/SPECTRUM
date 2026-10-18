---
name: research-autopilot
description: Use for sustained research with GPT directly reading papers and code, developing mathematical ideas, running authorized experiments, debugging and revising methods through B/C/D/E.
---

# Research Autopilot — prompt-guided research

Version: `0.4.0-harness.17`. Keep Work Harness for long-task supervision, persistent memory, pause/resume, automatic continuation and interruption recovery. GPT performs the scientific work. B/C/D/E experiment design and execution use the prompt guidance below rather than strict output/admission contracts. Installing a plugin alone does not start the supervisor.

The restored `program_cli` supports an explicitly adopted `experiment_autonomy` transport for B/C/D/E. It reuses the existing single-consumer lock, heartbeat and program state, runs one GPT session, retains its ordinary prose/logs, and resumes the same conversation. No experiment proposal, mailbox or response schema is involved. Existing other-stage controller paths, prior accepted history and source files remain intact. Do not replace the whole Harness or migrate unrelated projects when relaxing experimental work.

Restore the user's research objective, living project memory, authorized compute and actual jobs/results. Keep a useful handbook from A intake onward: motivation, gap, ideas, mathematical predictions, experiment choices, hardware and findings. Its format and level of detail are yours to choose. Update existing project memory instead of rebuilding it or automatically trusting it.

## B/C/D/E

Read the relevant guidance as the scientific question requires:

- [B — literature, code and research memory](references/prompt-B.md)
- [C — conditional failures and unnecessary dependencies](references/prompt-C.md)
- [D — mathematical mechanisms and executable ideas](references/prompt-D.md)
- [E — broad, fair and reproducible evaluation](references/prompt-E.md)

B/C/D/E describe kinds of research, not fixed steps. Retrieve missing knowledge through B at any time. Let real experiments change the question, implementation, method or evaluation. Harness keeps a single sustained agent performing this loop and preserves progress across turns. Move into wider E evaluation when the mechanism and evidence justify it; revisit earlier work when they do not. Scientific criticism is part of thinking and analysis, not a compulsory reviewer service or software approval.

## Official implementation and evaluation

When using existing methods/evaluators or questioning code and results, consult the applicable author-maintained or author-recommended implementation and settings first. Read [official-code guidance](references/prompt-upstream-code.md) for B/C/D/E evaluation and code diagnosis. Reuse traceable source memory; distinguish upstream code, local adaptations and third-party evaluators. Establish whether a discrepancy is an implementation/evaluation artifact before calling it a model failure or research gap. Adapt and debug autonomously on the authorized host; this adds no execution admission or response format.

## Execution freedom

Design, code, install needed dependencies, run, debug and analyze within the user's existing authorization. Prefer relevant official code and native evaluation; adapt them on the actual execution host. Practical scripts, notebooks and configuration files are chosen to suit the tools. A single baseline may be measured or scored independently; comparisons are needed to support comparative claims, not to authorize a command.

No compulsory proposal JSON, response schema, output template, mailbox, controller database, receipt chain, coverage mapping, stage binding, typed revisit or per-step acceptance is needed. Do not manufacture comparison arms or repeat generation to satisfy an interface. Existing records are evidence to read, not contracts to enforce. Existing controller metadata and non-experimental stage guidance continue serving task management. Legacy experiment schemas/admission rules do not override these four phase guides. Runtime bookkeeping is written by Harness, not a required research response.

Use the authorized GPU host for heavy work and code experiments. Inspect hardware and reuse a suitable existing environment. Adapt batch, concurrency and precision to measured capacity while preserving scientific meaning. Reconcile existing jobs before launching another; honor the user's single-experiment preference. Keep raw outputs, actual settings and sufficient provenance to reproduce conclusions, in whatever format works. Checkpoints and logs help recover a long job; they are not admission paperwork. Preserve execution isolation when running generated code.

Be explicit about actual progress, limitations, failed hypotheses and uncertainty. Never report a probe as model performance or a submitted job as completed. Use read-only community sources when authorized, and verify scientific claims against papers, code and experiments. Keep credentials private. Use direct Git/file updates for authorized delivery, without adding GitHub Actions or publication work.
