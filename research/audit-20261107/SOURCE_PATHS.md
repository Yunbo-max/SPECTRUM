# SPECTRUM 审计证据路径索引

审计日期：2026-11-07（只读，未修改任何实验文件）
根路径缩写：`B = /inspire/hdd/global_user/zhangjiaquan-253108540222/backup`

## 完成状态判定规则（本审计使用）
- `run_status.json`（status=completed + verification=completed）或 最终轮 `complete.json`（status=completed）⇒ Completed
- 只有 manifest/配置/提交回执 ⇒ Submitted only / Config only
- base 完成但方法轮缺失 ⇒ Partial（注明已完成轮数）
- `complete.json` 是 SHA 完整性清单，本身不等同于指标存在；指标以 `evaluation.metrics.json` 为准

## τ 扫描（TAU_SWEEP_RESULTS.csv 每行证据）
| 实验 | 指标文件 | 状态文件 |
|---|---|---|
| spectral_soft_7b_1round | `B/improving/runs/spectrum_7b/spectral_soft_7b_1round/spectral_soft/round_1/evaluation.metrics.json` | 同目录 `run_status.json` |
| tau15 | `B/improving/runs/spectrum_7b/spectral_soft_7b_tau15/spectral_soft/round_1/evaluation.metrics.json` | 同目录 `run_status.json` |
| tau20 | `B/improving/runs/spectrum_7b/spectral_soft_7b_tau20/spectral_soft/round_1/evaluation.metrics.json` | 同目录 `run_status.json` |
| tau50 | `B/improving/runs/spectrum_7b/spectral_soft_7b_tau50/spectral_soft/round_1/evaluation.metrics.json` | 同目录 `run_status.json` |
| tau100 | `B/improving/runs/spectrum_7b/spectral_soft_7b_tau100/spectral_soft/round_1/evaluation.metrics.json`；qz 回执 job_id `job-754db6d6-eaba-4fcc-bbd0-635ae311e0ff` 在 `B/improving/experiments/spectrum_7b_qz_jobs/qz_job_spectrum_tau.json` | 同目录 `run_status.json` |
| sweep_v1（τ=3） | `B/improving/runs/spectrum_7b/spectrum_7b_sweep_v1/{spectral_soft,spd_hard,residual_blend}/round_1/evaluation.metrics.json`；job_id `job-26d13bb6-9562-4d8f-abb1-788289517fc0` 在 `.../qz_job_spectrum_sweep_v1_submit.json` | `.../spectrum_7b_sweep_v1/run_status.json` |
| highk_v1 | `B/improving/runs/spectrum_7b/spectrum_7b_highk_v1/{base,plain,spectral_soft,spd_hard,residual_blend}/round_1/evaluation.metrics.json`（base 在 base/）；job_id `job-217255e3-ceff-434d-a603-c8eae37103c3` 在 `.../qz_job_spectrum_highk_submit.json` | `.../spectrum_7b_highk_v1/run_status.json` |
| r10（512 tok） | `B/improving/runs/spectrum_7b/spectral_soft_7b_r10/spectral_soft/round_10/evaluation.metrics.json`；resume 说明引用 job-ff233dd0（qb-prod-gpu521 硬件故障）在 `.../qz_job_spectral_soft_7b_r10_resume.json` | 同目录 `run_status.json` |
| r10_4096（no-decay，Partial） | 最后一轮完整指标：`.../spectral_soft_7b_r10_4096/spectral_soft/round_8/evaluation.metrics.json`；第 9 轮未完成证据：`.../round_9/evaluation.jsonl.parts/`（1909 个 part 文件，213,137,336 B）无 `evaluation.metrics.json`；运行日志 `B/improving/logs/qz/spectral_4096.log`；续跑日志 `B/improving-resume/logs/resume_nodecay.log`（663 B，无 DONE） | 无 `run_status.json`（Partial 判定依据） |
| r10_4096_adaptive（Partial） | 最后一轮完整指标：`.../spectral_soft_7b_r10_4096_adaptive/spectral_soft/round_8/evaluation.metrics.json`；第 9 轮 parts 1805 文件 145,308,256 B；日志 `B/improving/logs/qz/spectral_4096_adaptive.log`（止于 "round 9: start"） | 无 `run_status.json` |
| r10_4096_tau06（Failed） | 仅 `.../spectral_soft_7b_r10_4096_tau06/manifest.json` + `base/evaluation.jsonl.parts/`（49 个 .000000 分片）；日志 `B/improving/logs/qz/spectral_4096_tau06.log`（633 B，模型加载后中断） | 无任何指标 |
| r10_4096_tau08（Completed） | `.../spectral_soft_7b_r10_4096_tau08/spectral_soft/round_10/evaluation.metrics.json`；续跑日志 `B/improving-resume/logs/resume_tau08.log`（"RESUME DONE 2026-11-03T09:22"） | `.../run_status.json` |
| learned r10_4096 | `B/improving-learned/runs/spectrum_7b/spectral_learned_7b_r10_4096/spectral_learned/round_10/evaluation.metrics.json`；`learned_gains.json` 同目录各轮；资格日志 `B/improving-learned/logs/qualify_learned.log`、运行日志 `spectrum_learned_4096.log`（"DONE 2026-11-02T17:32"） | 同目录 `run_status.json` |

## 算子消融（OPERATOR_ABLATION.csv 每行证据）
| 行 | 证据路径 |
|---|---|
| highk_v1 四臂 + base | 如上 highk_v1 行；各臂 `round_1/{evaluation.metrics.json, complete.json, operator_diagnostics.json(谱方法)}` |
| sweep_v1 三臂 + base | 如上 sweep_v1 行 |
| isotropic-s43（唯一真实 Isotropic） | `B/improving/runs/final_study_v1/jobs/isotropic-s43/isotropic_soft/round_1/{complete.json(3145B), evaluation.metrics.json}` + `run_status.json`；共享 base 证据：base 的 `evaluation_sha 1f5b8a9e0c18c819f81419c9331807173f0c2b4b58c5a262b226d2c20388e47f` 与 core-s43 一致 |
| weak-s43（τ=0.5 spectral） | `B/improving/runs/final_study_v1/jobs/weak-s43/spectral_soft/round_1/{complete.json, evaluation.metrics.json}` + `run_status.json` |
| completion-s43 | `B/improving/runs/final_study_v1/jobs/completion-s43/{plain,spectral_soft}/round_1/evaluation.metrics.json` + `run_status.json` |
| crossfamily learned r5 | qwen7b：`B/SPECTRUM-learned/runs/crossfamily_learned_r5_4096/jobs/qwen7b_{plain,ssd,spectral_soft,spectral_learned}/round_5/evaluation.metrics.json`；llama8b 与 deepseek6.7b 同构路径（deepseek 的 plain/ssd 取 round_4） |
| random_soft / matched_blend（无结果证明） | 定义：`B/SPECTRUM-learned/src/improving/pipeline.py`（METHODS 集合）；配置：`B/improving/configs/formal_*.yaml` 的 `mechanism_methods` 字段；全树 find/grep 无运行目录、无日志 |
| 历史归档（git-blob，非磁盘运行） | `B/improving/research/audit/observed_results.json`（audit_date 2026-10-02，studies：main_mbpp_final_n64、main_mbpp_trajectory_n16、ssd_mbpp_trajectory_n16、frozen_*_transfer_n16、cross_model_baseline_matrix）；主张状态：`B/improving/research/audit/claims.json`（`calibrated_direction_necessity: not_established`） |

## 解码/参考/seed（Part A 证据）
| 项 | 证据路径 |
|---|---|
| 40 vs 50 reference：只有配置 | `B/improving-learned/configs/spectrum_7b/spectrum_7b_r10_spectral_4096_tau06_anchor40.yaml`（max_examples: 40；注释 "never auto-launched"）；learned 配置 `.../spectrum_7b_r10_learned_4096.yaml`（max_examples: 50）；真实 40-reference 求解证据：`B/improving-learned/runs/qualification/learned-gains/learned_gains.json`（fit:40, guard:10, probe:8） |
| anchor replay：只有代码/测试 | `B/improving/scripts/run_release_study.py`（第 357/243-245 行）、`B/improving-learned/tests/test_release_study.py`；文档 `B/improving-learned/docs/EXISTING_EVIDENCE.md` 明确 "No completed anchor-only SFT control" |
| 解码温度 | 全部 7B yaml：`temperature: 0.8, top_p: 0.95, top_k: 0`（例 `B/improving/configs/spectrum_7b/spectrum_7b_r10_spectral_4096.yaml`）；未执行的变体定义：`B/improving/scripts/evaluate_decoder.py`（cool 0.6/warm 1.0/ssd_recipe 1.5-0.8-20）；已执行的 ssd 合成解码 1.5/0.8/20：`B/SPECTRUM-learned/configs/crossfamily/protocol_learned_4096.json` 第 117 行 |
| K/V 层数 | 默认 middle+last：`B/improving/src/improving/spectral.py` 第 173-186 行；显式 [14,27]：`B/SPECTRUM-learned/configs/multidomain/*.json`；27B 固定 [31,63]：`B/improving/src/improving/text_study.py` 第 43-52 行 |
| seeds | 7B 全系 seed=43/data_seed=42；final_study seeds [43,44,45]：`B/improving/runs/final_study_v1/plan/manifest.json`；crossfamily seed 1329911945：`B/SPECTRUM-learned/configs/crossfamily/assets.json`；multidomain seed 854974746：`B/SPECTRUM-learned/runs/private/multidomain_seed.json` |

## 转移与跨域
| 实验 | 证据路径 |
|---|---|
| transfer-gap learned v2（Completed） | `B/SPECTRUM-transfer-gap/runs/spectrum_transfer_gap_20261103/learned_7b_r10_v2/{run_status.json, spectral_learned/round_10/evaluation.metrics.json, spectral_learned/round_10/transfer_gap/report.json}` |
| transfer-gap tau08（Partial 9/10） | `.../spectral_soft_7b_r10_tau08/spectral_soft/round_9/evaluation.metrics.json` |
| multidomain math learned-r5 | `B/SPECTRUM-learned/runs/multidomain/learned-r5/math-qwen25-7b/report.json`（含 paired comparisons） |

## 云平台状态
- 仅 4 个 qz CreateJob 真实回执（含 job_id）：tau100 `job-754db6d6-…`、capacity-sweep `job-9ff05c2d-…`、sweep-v1 `job-26d13bb6-…`、all-operators `job-02dc7f7e-…`、highk-v1 `job-217255e3-…`（回执文件在 `B/improving/experiments/spectrum_7b_qz_jobs/*_submit.json`）
- 其余运行日志（`B/improving/logs/qz/`、`B/improving-learned/logs/`、`B/SPECTRUM-learned/logs/`、`B/SPECTRUM-transfer-gap/logs/`）均为本地 H100 运行日志，无 job_id/云端状态
- 结果文件全部在本地：`runs/` 被 .gitignore、`logs/` untracked → **未同步到 GitHub**

## GitHub 分支对照（2026-11-07 ls-remote 实测）
- `spectrum/research/learned-multimodel-multidomain-20261102 = 3346e2a` ← SPECTRUM-learned HEAD 一致
- `spectrum/research/spectrum-transfer-gap-20261103 = 118d39c` ← SPECTRUM-transfer-gap HEAD 一致
- `spectrum/main = 5c8d1eb`、`origin/main = 45195e8`（本地 refs 过期）
- `spectrum/research/iclr-rebuttal-stability-20261103 = f7c4a17`、`research/pi-selfteacher-spectral-20261103 = 388caeb`：仅远程
- `spectrum-work = b8bcc68`（improving HEAD）：仅本地，未推送
