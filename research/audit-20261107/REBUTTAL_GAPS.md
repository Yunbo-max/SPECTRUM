# SPECTRUM 审稿回应实验缺口清单（只读审计）

审计日期：2026-11-07
审计方式：只读。未启动任何训练/评测，未修改任何文件。
范围：`/inspire/hdd/global_user/zhangjiaquan-253108540222/backup/improving*/`、`backup/SPECTRUM-*/`（同一 git 仓库的 5 个 worktree）+ GitHub `Yunbo-max/SPECTRUM` 分支对照。

## 已完成、可直接复用（有真实指标 + 完整原生评测文件）

| 审稿关注点 | 已有证据 | 协议 | 关键数字（7B MBPP） |
|---|---|---|---|
| 谱强度 τ 扫描 | tau15/20/50/100 + τ=1 + τ=3（sweep_v1）全部 Completed | 1 轮 / 512 tok / eval@16 | round_1 pass@16：τ1.5=0.764, τ2=0.772, τ3=0.766, τ5=0.756, τ10=0.774, τ1=0.766（base 0.756） |
| 长期训练的 τ 衰减 | tau08（decay 0.8）Completed（resume 完成）；tau06 **崩溃无结果**；no-decay 与 adaptive 各完成 8/10 轮 | 10 轮 / 4096 tok / eval@64 | pass@64：tau08=0.836, no-decay(r8)=0.844, adaptive(r8)=0.838, learned=0.824 |
| Learned Spectral Gains | spectral_learned_7b_r10_4096 Completed（10/10 轮），learned_gains.json 完整（fit40/guard10/probe8，8 步接受） | 10 轮 / 4096 tok / eval@64 | pass@1=0.5630, pass@64=0.824（r10） |
| 谱方向 vs 硬投影/残差混合 | highk_v1 四臂同协议（plain/spectral_soft/spd_hard/residual_blend）全 Completed | 1 轮 / 512 tok / eval@128 | pass@128：ss=0.828 > rb=0.826 > spd=0.824 > plain=0.822 |
| 跨模型泛化 | crossfamily_learned_r5_4096 矩阵（3 模型 × plain/ssd/spectral_soft/spectral_learned）：qwen/llama 全完成，deepseek 的 plain/ssd 停在 r4、spectral_learned 仅 base | 5 轮 / 4096 tok / eval@64 | qwen7b r5 pass@64：ss=0.848, ssd=0.842, learned=0.828, plain=0.824 |
| 多 seed | final_study core-s43/44/45（1.5B，5 轮）全完成 | 5 轮 / 512 tok / eval@64 | plain r5 pass@1：0.4152/0.4144/0.4161 |
| Transfer gap | transfer-gap learned_7b_r10_v2 Completed（含 pre/post spectral exploration 的 transfer_gap/report.json） | 10 轮 / 4096 tok / eval@64 | r10 pass@64=0.828；30 任务转移评估 spectral delta −0.00156 CI[−0.0146, 0.0135] |
| Isotropic 对照 | final_study isotropic-s43 唯一一次真实运行 Completed（1.5B，1 轮） | 1 轮 / 512 tok / eval@64 | pass@1=0.37778 / p64=0.72（注意：对应 spectral 臂 weak-s43 用 τ=0.5，存在混杂） |

## 有配置/代码/提交，但**从未真正执行**（审稿人要求但无结果）

| 缺口 | 状态 | 证据位置 |
|---|---|---|
| **Random Basis（random_soft）** | Config-only，任何目录、任务、日志中都没有执行记录 | `SPECTRUM-learned/src/improving/pipeline.py` METHODS 集合 + `configs/formal_*.yaml` |
| **matched_blend** | Config-only，同上 | 同上 |
| **40 vs 50 reference 对照** | 只有 `..._tau06_anchor40.yaml` 配置（注释明确"never auto-launched"）；唯一真实 40-reference 证据是 learned_gains.json 的 fit=40 | `improving-learned/configs/spectrum_7b/spectrum_7b_r10_spectral_4096_tau06_anchor40.yaml` |
| **Reference-only / anchor replay** | 只有代码定义（run_release_study.py 的 mechanism-anchor-replay-r1）与测试，磁盘无任何运行目录 | `improving/scripts/run_release_study.py` |
| **解码温度对照（cool/warm/ssd_recipe）** | 只有 evaluate_decoder.py 定义，未执行 | `improving/scripts/evaluate_decoder.py` |
| **K/V 层数/干预位置对照** | 无此类对照实验（所有配置 layers=null 即默认 middle+last，或显式 [14,27]） | `improving/src/improving/spectral.py` |
| **7B 上的 Isotropic/Random** | 只有 1.5B 一次 isotropic；7B 无 | — |

## 已提交/已启动但**未完成**（可续跑）

| 实验 | 状态 | 缺口 |
|---|---|---|
| spectral_soft_7b_r10_4096（no-decay） | Partial 8/10 | 第 9 轮评测未完成（parts 已写到 213MB），第 10 轮未开始；resume_nodecay 尝试未完成 |
| spectral_soft_7b_r10_4096_adaptive | Partial 8/10 | 同上（第 9 轮 parts 145MB） |
| spectral_soft_7b_r10_4096_tau06 | **Failed** | base 评测中途崩溃，需从头重跑 |
| transfer_gap spectral_soft tau08 | Partial 9/10 | 第 10 轮评测未完成 |
| crossfamily learned deepseek/llama spectral_learned | Partial 0/5 | 仅 base 评测，方法轮未跑 |
| crossfamily deepseek plain/ssd | Partial 4/5 | 第 5 轮未完成 |
| crossfamily_code_v1 ssd/spectral_soft | Submitted only | 从未启动 |
| final_study core-s43/s45 ssd r5 | Failed | 评测失败（SFT 已完成） |
| final_study core-s44 spectral_soft | Failed | training_generation 失败，无评测 |
| final_study transfer jobs | Plan only | 无任何目录 |
| multidomain qa learned-r5 | Partial | 部分轮次 |
| ssd_final_n64（历史） | retained_pending_eval64 | 无指标 |

## GitHub 同步状态（结果文件去向）

- 5 个目录是同一仓库 worktree；`runs/`、`data/` 被 .gitignore；`logs/` untracked —— **所有实验结果均未上传 GitHub**，只在本机 H100 本地跑（logs 里无任何云端 job_id，仅 4 个 qz CreateJob 收据：tau100、capacity-sweep、sweep-v1、highk-v1）。
- 分支同步：`research/learned-multimodel-multidomain-20261102` 与 `research/spectrum-transfer-gap-20261103` 与 GitHub 一致；`spectrum-work`（b8bcc68）**未推送**；`research/iclr-rebuttal-stability-20261103`、`research/pi-selfteacher-spectral-20261103` 只在 GitHub 上（本地无分支）。
- 本地远程引用过期（spectrum/main、origin/main 的 local ref 未 fetch，线上 main 已有 5c8d1eb）。

## 最小补跑清单（按审稿逻辑排序）

1. **random_soft + matched_blend（7B）**：按 highk_v1 同协议 1 轮（或 5 轮）——这是"谱方向必要性"唯一缺的核心对照。现有 highk_v1 的 base/plain/spd/residual 四臂可原样复用为同批基线。
2. **tau06 重跑**（或直接复用 tau08 结论 + 说明 tau06 崩溃）。
3. **no-decay r9/r10 续跑**（parts 已存在，可续；能得到完整 10 轮 no-decay 曲线）。
4. **anchor-replay（40-reference 对照）**：已有 anchor40 yaml 与代码路径，未执行。
5. 可选：7B isotropic（对齐 1.5B 的 isotropic-s43）；decoder 温度对照（cool/warm/ssd_recipe）。
