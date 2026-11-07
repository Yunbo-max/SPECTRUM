# ICLR 2027 SPECTRUM: revised-paper learned-gain appendix draft

**Branch status: prepared manuscript material, NOT uploaded to OpenReview.**
Date: 2026-11-07. Source is the local read-only audit published in
\`research/spectrum-audit-20261107\`. It lists original evaluator paths,
run-status receipts and per-arm benchmark sample counts. The original raw
GPU runs live under ignored \`runs/\` on the cloud host, NOT in public GitHub.

## The scientific decision

Add **Learned-Gain SPECTRUM** as a **post-submission gain-design extension /
ablation of the gain rule**. Do NOT call it an ablation of the gradient-derived
basis \(U\): both Fixed and Learned use \(U\). Nor call it pure 'learned vs
fixed gain only' in the causal sense: Learned uses additional gain-fitting
compute, 40 reference-fit plus 10 reference guard, and 8 native probes.
It is best positioned as a gain-adaptivity and accuracy--diversity trade-off
analysis rather than the central novelty claim of the submitted paper.

The primary ICLR study is **fixed-proximal 1.5B, 5 rounds, 512 tokens**.
Its headline 89.9% richness retention should stay unchanged.
Do not silently replace that method with the newer 7B Learned procedure.

## Verified-by-audit *reported* five-round 7B contrast

All Qwen2.5-Coder-7B / MBPP500 / 4096 maximum generated tokens /
6144 SFT tokens / 64 native evaluation samples, single run:

| Method | Pass@1 | Pass@64 | C64 | marginal D4 |
|---|---:|---:|---:|---:|
| Plain | 59.900% | 82.4% | 9.174 | 0.61503 |
| SSD | 56.706% | 84.2% | 13.730 | 0.74343 |
| Fixed proximal | 56.853% | 84.8% | 14.570 | 0.77890 |
| Learned gains | 58.925% | 82.8% | 10.186 | 0.64970 |

Learned minus Fixed: **+2.072 pp Pass@1**, **-2.0 pp Pass@64**,
**-4.384 C64**. It is NOT a universal gain. The marginal D4 figures
have method-specific eligible populations; paired common-eligible
D4 effects must be computed from real per-task rows before inference.

The one-round 7B \`tau\` sweep is a **different** 512-token / eval16
protocol. Its completed \`tau\` set is {1, 1.5, 2, 3, 5, 10}.
Do not pool its estimates with the above five-round results.

## What I changed / did NOT change

- Prepared \`docs/ICLR2027_LEARNED_GAIN_ABLATION_DRAFT.tex\` as
  directly pasteable appendix material, with tables, mathematical
  explanation and limitations.
- Proposed exactly one sentence in primary RQ3 directing readers to the
  new appendix. Do **not** overwrite the submitted headline results,
  change the abstract, or make the original fixed-proximal theory claim
  also apply to optimized learned gains.
- The source \`yuhanlydia/improving/paper/iclr2027/main.tex\` is in a
  repository for which this GitHub connection does **not** have branch
  write permission (HTTP 403). We did NOT modify it.
- **Submission source warning:** the available GitHub manuscript
  title is *SPECTRUM: Correct-Solution Retention in Looped
  Self-Distillation*, whereas the OpenReview submission displayed
  *SPECTRUM: Proximal Spectral Modulation for Looped Self-Distillation*.
  Compare to the actual currently submitted anonymous \`main.tex\`
  and PDF before copying the excerpt. Do not treat the older
  September GitHub source as current by assumption.
- No new GPU experiments or re-evaluations were launched.
- The material remains a draft until the author or local agent
  verifies original \`complete.json\`, \`evaluation.metrics.json\`,
  config hashes, task/sample denominators, common checkpoint/seed,
  and read-only audit arithmetic against the cloud host.

## Gaps before claiming calibrated direction is necessary

Highest priority for responding to reviewer w3G2 and ygkV:
\`random_soft\` matched-eigenvalue-spectrum and \`isotropic_soft\`
matched-strength controls on the SUBMITTED 1.5B five-round protocol.
The recovered local audit reports:
- full 7B tau 1/1.5/2/3/5/10 scan: COMPLETE, one round;
- 7B highk four-arm Plain/Fixed/SPD/Residual: COMPLETE, one round;
- 1.5B isotropic: COMPLETE but ONE round, not matched full study;
- random_soft: no completed evidence found;
- anchor-only SFT / reference replay: no completed evidence found;
- 1.5B three seeds: Plain/SSD results exist but complete same-seed
  Fixed vs Plain confirmation is still incomplete.

These are central reviewer concerns; a Learned variant does not
substitute for them. If runtime is limited, favor true directional
controls and independent training seeds before new architectures,
extra tau values, 10-round tau=0.6 restart, or GUI experiments.

## How to integrate into the actual ICLR revision

1. Open the **actual submitted anonymous** LaTeX source, not an
   assumed equivalent GitHub draft. Confirm author anonymity and the
   ICLR 2027 main-text additional-page rule.
2. Add only the RQ3 cross-reference sentence as shown in the \`.tex\`
   header. Place the substantive tables in the appendix.
3. Retain the 1.5B original Fixed method name, original abstract,
   and headline 5-round tables. Add 'post-submission exploratory'
   scope and explicit information/compute mismatch.
4. Update the limitations to say the 7B extension is another
   model/setting but does not validate the original causal direction.
5. Independently confirm numbers with local native receipts and
   rerender the anonymous PDF. Do not submit tables based solely
   on this GitHub summary if any checksum or denominator differs.
6. The assistant cannot upload the revised PDF to OpenReview from
   this chat. Only the author can submit a reviewed final revision.

## Evidence files

- \`research/audit-20261107/REBUTTAL_GAPS.md\`
- \`research/audit-20261107/EXPERIMENT_INVENTORY.csv\`
- \`research/audit-20261107/TAU_SWEEP_RESULTS.csv\`
- \`research/audit-20261107/OPERATOR_ABLATION.csv\`
- \`research/audit-20261107/SOURCE_PATHS.md\`

All source paths in those reports refer to local private host files;
do not insert user names, machine paths, tokens or identities into
the double-blind PDF.
