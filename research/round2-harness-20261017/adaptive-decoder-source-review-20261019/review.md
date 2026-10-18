# Adaptive decoder controls: source review, 2026-10-18 UTC

The author-native SSD baseline is already running. This review does not add a concurrent model experiment or establish a conditional model failure. It checks whether proposed decoding explanations are already known and whether their official implementations can serve as valid controls.

[AdapT, AAAI 2024](https://arxiv.org/html/2309.02772v3) already varies temperature within generated code, with hotter sampling around challenging block starts and colder sampling for confident tokens. Its [author code](https://github.com/LJ2lijia/AdapT) is a relevant integration lead, not yet executed here. Context-dependent temperature alone is therefore not a new mechanism.

[AdaDec's author repository](https://github.com/SYSUSELab/AdaDec), associated with [FSE 2026 paper v5](https://arxiv.org/html/2506.08980v5), learns model-specific uncertainty thresholds from ground-truth-guided calibration and selectively performs lookahead. The documented beam width 3 and lookahead length 5 add inference work. A comparison must account for calibration information, search work and the repository's default 1024-token output limit; it cannot silently inherit those settings for the current 65536-token LCB condition. We have not executed AdaDec or verified its reported performance.

[Top-H paper v2](https://arxiv.org/html/2509.02510v2#S5) specifies an entropy constraint on the normalized retained distribution. The captured [author implementation](https://github.com/ErfanBaghaei/Top-H-Decoding/blob/8b94d62b238ed62793627f4a2556d90188560854/logit_processor.py) has a concrete mismatch with that specification. Source hashes, unchanged code and license are retained here. The archive remains on the GPU host.

CPU-only execution of that unchanged processor on hn01 gave the following software results, not model scores:

- 128 equal logits, temperature 1, default top_n=100 and alpha=0.4: 39 retained tokens.
- The same input with alpha=1: 99 retained tokens; no exception.
- top_n=1 and alpha=0.4: IndexError from the next-token index.

For the first case, H(p)=log2(128)=7 bits. The returned distribution has H(q)=log2(39)=5.2854 bits, exceeding alpha H(p)=2.8 bits. A uniform retained set meeting that bound can contain at most 6 tokens. This counterexample concerns the pinned repository processor versus paper v2, not every Top-H implementation or the paper's performance claims. The processor uses a partial entropy threshold; its comparison cancels the shared normalization terms, rather than enforcing the stated normalized-entropy ratio. Its temperature parameter affects mask selection but the returned finite logits retain their original scale, so an eventual integration must also inspect generation-time temperature ordering. No patch or replacement decoder was introduced.

Evidence: top-h-source.json, top-h-boundary-probes.json, top-h-entropy-contract-check.json and probe_top_h.py. The probe script imports the preserved upstream module. No model execution, generated-code scoring or GPU allocation was needed for these checks.

## Consequences for B/C/D/E

Continue the existing native baseline and SSD comparison before selecting a new mechanism. Match recommended and crossed decoding conditions, report token/compute cost and truncation, and distinguish finite-sample failure from zero support. A residual gap would justify testing established adaptive controls with explicit calibration and compute accounting. The Top-H code/paper mismatch must be resolved and labeled before claiming a paper-faithful control; preserving upstream behavior and a separately named diagnostic is preferable to silently changing semantics. No D novelty or E superiority follows from these software findings.

The baseline runner remains PID65584, with matching start ticks 144158755 at 23:41 UTC. Its first repeat had completed 32/131 prompts; no full repeat or correctness results existed then. Do not launch a duplicate or resume the interrupted Apple download until the active program releases its lock. Harness remains active and the scientific objective is unfinished.
