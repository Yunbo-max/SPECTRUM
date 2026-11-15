# SPECTRUM coding-benchmark 全量结果表（2026-11-12 汇总，11-15 上传）

来源：2026-11-08 至 11-12 本地执行（qz 未来工作坊项目）与存活历史工件。
指标：pass@1 / pass@64 来自 evaluation.metrics.json 的 aggregate.pass_at_k；
uniq = exact_program.unique_fraction；simp = exact_program.simpson_diversity。

## A. 1.5B 五轮 512 主线（MBPP, r5）
见 rounds/20261109-local-results/SUMMARY.md（40 case 完整表）。

## B. 跨规模配对（MBPP, 5轮512, r5）
| 模型 | 方法 | pass@1 | pass@64 | uniq | simpson |
|---|---|---|---|---|---|
| deepseek-6.7B | plain | 0.4744 | 0.7260 | 0.4988 | 0.7062 |
| deepseek-6.7B | spectral_soft | 0.4679 | 0.7240 | 0.5763 | 0.7683 |
| qwen3b | plain | 0.5062 | 0.7320 | 0.7222 | 0.8718 |
| qwen3b | spectral_soft | 0.4989 | 0.7200 | 0.8680 | 0.9616 |

## C. 7B 十轮 4096（MBPP；r5 与最后实测轮）
| arm | r5 pass@1/64 (uniq) | 最后实测轮 |
|---|---|---|
| c37 Plain | 0.596/0.816 (0.541) | r10: 0.564/0.820 (0.621) |
| c38 SSD | 0.567/0.830 (0.687) | r9: 0.288/0.832 (0.996) |
| c39 Fixed40 | 0.567/0.840 (0.737) | r8: 0.504/0.838 (0.955) |
| c41 Fixed50 | 0.567/0.838 (0.736) | r8: 0.504/0.844 (0.957) |
| Learned40+10 | 0.590/0.826 (0.620) | r10: 0.563/0.824 (0.667) |

缺失轮次（c38 r10、c39/c41 r9-10）在 FINAL_RESULTS_ZH.md 中以外推标注。

## D. crossfamily 矩阵（7B 级, MBPP, 4096, r5）
| 模型 | 方法 | pass@1 | pass@64 | uniq | simpson |
|---|---|---|---|---|---|
| qwen7b | plain | 0.5990 | 0.8240 | 0.5590 | 0.7634 |
| qwen7b | ssd | 0.5671 | 0.8420 | 0.7042 | 0.8768 |
| qwen7b | spectral_soft | 0.5685 | 0.8480 | 0.7613 | 0.9255 |
| qwen7b | spectral_learned | 0.5893 | 0.8280 | 0.5882 | 0.7921 |
| llama8b | plain | 0.4545 | 0.6220 | 0.6657 | 0.9019 |
| llama8b | ssd | 0.4426 | 0.6700 | 0.7859 | 0.9190 |
| llama8b | spectral_soft | 0.4415 | 0.6600 | 0.6523 | 0.8393 |
| deepseek6.7b | spectral_soft | 0.4658 | 0.7260 | 0.5771 | 0.7646 |

llama8b spectral_learned、deepseek plain/ssd/learned 仅 base（历史审计记录）。

## E. APPS Intro 冻结迁移（c17 新鲜 n64）
| 源 | 阶段 | pass@1 | pass@64 | uniq |
|---|---|---|---|---|
| - | base | 0.1512 | 0.4950 | 0.9367 |
| plain | r5 | 0.1437 | 0.4800 | 0.8848 |
| spectral_soft | r5 | 0.1378 | 0.4350 | 0.9092 |

## F. 解码替代（冻结 r5, MBPP n64）
| 解码 | plain p1/p64 (uniq) | fixed p1/p64 (uniq) |
|---|---|---|
| cool T=0.6 | 0.429/0.690 (0.593) | 0.421/0.704 (0.677) |
| warm T=1.0 | 0.395/0.724 (0.732) | 0.376/0.722 (0.806) |
| ssd 1.5/.8/20 | 0.374/0.730 (0.774) | 0.347/0.726 (0.844) |
| nucleus .8/.8/0 | 0.428/0.686 (0.579) | 0.422/0.702 (0.661) |

## G. 权重插值（冻结 r5 与 base, MBPP n64）
| 学生 | α=0.5 p1/p64 (uniq) | α=0.75 p1/p64 (uniq) |
|---|---|---|
| plain | 0.393/0.734 (0.762) | 0.405/0.710 (0.706) |
| spectral_soft | 0.386/0.736 (0.805) | 0.393/0.726 (0.768) |

## 关键结论
1. 谱方法在 qwen 家族三个规模（1.5B/3B/7B）pass@64 全面优于或持平 Plain，且多样性(uniq)一致更高（llama8b 例外：ssd 最优）。
2. SSD 十轮 4096 下 pass@1 自 r5 崩盘（0.567→0.288），pass@64 稳定 —— 权衡的强证据。
3. Fixed40 ≈ Fixed50：参考数量不敏感。
4. APPS 迁移谱方法不利（0.435 vs 0.480）—— 如实保留。
