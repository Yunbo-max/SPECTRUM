---
name: research-autopilot
description: Use for sustained research with GPT directly reading papers and code, developing mathematical ideas, running authorized experiments, debugging and revising methods through B/C/D/E.
---

# Research Autopilot — prompt-guided research

Version: `0.4.0-harness.15`. The plugin identity is retained; the mandatory Work Harness controller is retired for new use. Use the existing GPT/Codex agent directly. This Skill supplies research guidance, not a scheduler or an unattended service.

Restore the user's research objective, living project memory, authorized compute and actual jobs/results. Keep a useful handbook from A intake onward: motivation, gap, ideas, mathematical predictions, experiment choices, hardware and findings. Its format and level of detail are yours to choose. Update existing project memory instead of rebuilding it or automatically trusting it.

## B/C/D/E

Read the relevant guidance as the scientific question requires:

- [B — literature, code and research memory](references/prompt-B.md)
- [C — conditional failures and unnecessary dependencies](references/prompt-C.md)
- [D — mathematical mechanisms and executable ideas](references/prompt-D.md)
- [E — broad, fair and reproducible evaluation](references/prompt-E.md)

B/C/D/E describe kinds of research, not fixed steps. Retrieve missing knowledge through B at any time. Let real experiments change the question, implementation, method or evaluation. A single sustained agent can perform the whole loop. Move into wider E evaluation when the mechanism and evidence justify it; revisit earlier work when they do not. Scientific criticism is part of thinking and analysis, not a compulsory reviewer service or software approval.

## Execution freedom

Design, code, install needed dependencies, run, debug and analyze within the user's existing authorization. Prefer relevant official code and native evaluation; adapt them on the actual execution host. Practical scripts, notebooks and configuration files are chosen to suit the tools. A single baseline may be measured or scored independently; comparisons are needed to support comparative claims, not to authorize a command.

No compulsory proposal JSON, response schema, output template, mailbox, controller database, receipt chain, coverage mapping, stage binding, typed revisit or per-step acceptance is needed. Do not manufacture comparison arms or repeat generation to satisfy an interface. Existing records are evidence to read, not contracts to enforce. Remaining legacy references, schemas and runtime code in this package are archival/optional implementation material; they do not override these four phase guides or reactivate the controller.

Use the authorized GPU host for heavy work and code experiments. Inspect hardware and reuse a suitable existing environment. Adapt batch, concurrency and precision to measured capacity while preserving scientific meaning. Reconcile existing jobs before launching another; honor the user's single-experiment preference. Keep raw outputs, actual settings and sufficient provenance to reproduce conclusions, in whatever format works. Checkpoints and logs help recover a long job; they are not admission paperwork. Preserve execution isolation when running generated code.

Be explicit about actual progress, limitations, failed hypotheses and uncertainty. Never report a probe as model performance or a submitted job as completed. Use read-only community sources when authorized, and verify scientific claims against papers, code and experiments. Keep credentials private. Use direct Git/file updates for authorized delivery, without adding GitHub Actions or publication work.
