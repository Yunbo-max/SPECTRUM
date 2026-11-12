# Additional evidence on correct structural richness

We thank the reviewers for their careful assessment. SPECTRUM studies whether a model can retain a richer repertoire of correct implementations while repeatedly learning from its own outputs. The intervention changes the generator during data synthesis; ordinary SFT uses all generated completions without correctness filtering, and the resulting student is evaluated without spectral intervention.

The additional experiment uses Qwen2.5-Coder-1.5B, five rounds, a 512-token generation limit, and 64 samples on each of 500 MBPP evaluation tasks. Across three paired training seeds:

| Method | pass@1 (%) | pass@64 (%) | Correct AST richness, C64 |
|---|---:|---:|---:|
| Plain | 41.46 | 71.00 | 8.319 ± 0.163 |
| Fixed SPECTRUM | 40.13 | 72.13 | 11.175 ± 0.314 |

Here, ± is the sample standard deviation across the three training seeds. C64 increases by **34.3%**, and pass@64 increases by **1.13 percentage points**, alongside a **1.33-point reduction in pass@1**. All comparisons are at round five; the three seeds are independent training lineages, not three evaluation resamplings.

The richness effect also persists when comparing four correct samples on tasks eligible for both methods. Trained Qwen2.5-Coder-3B and DeepSeek-Coder-6.7B pairs increase C64 by **38.2%** and **17.7%**, respectively; their pass@64 changes are −1.2 and −0.2 points. These results support correct-implementation richness across the tested models, while success-rate gains remain setting-dependent.

Our responses below address reference access, operator controls, decoding, interpolation, and sensitivity. We use “correct structural richness” precisely: AST classes are implementation proxies, not human-validated algorithm families. The additional controls also identify limits on attributing the effect uniquely to the gradient-derived orientation.

The main contribution and results here concern the originally submitted Fixed method. Learned gains remain a separate extension.
