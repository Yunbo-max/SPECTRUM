# c00/c25 历史证据核验结论（2026-11-08，只读审计续）

背景：2026-11-08 用户删除 backup/improving、improving-resume、improving-mobilegym。
improving 是 SPECTRUM 系列共享 .git 的宿主 worktree，其 `runs/`、`logs/`、`experiments/` 下存有 1.5B 主线与 7B 十轮实验的原始运行工件。

## 结论一：数字存活、原始工件部分丢失

| 历史证据 | 状态 | 位置 |
|---|---|---|
| 1.5B 主线 final n64 / n16 指标（pass@1/pass@64/AST richness、配对比较、CI） | ✅ 数字存活（git 归档） | `research/audit/observed_results.json`（e902b8c 已提交）、`research/audit/claims.json`、`research/audit-20261107/{REBUTTAL_GAPS,SOURCE_PATHS}.md、OPERATOR_ABLATION.csv、TAU_SWEEP_RESULTS.csv |
| 1.5B 主线原始工件（core-s43/44/45 checkpoint、逐题 eval jsonl、final_study_v1、τ sweep、highk_v1、sweep_v1、r10 512tok、r10_4096 no-decay/adaptive/tau06/tau08 运行目录） | ❌ 已随 improving 删除（~506G） | — |
| crossfamily_learned_r5_4096（3 模型 × 4 方法，含逐轮 metrics） | ✅ 存活 | `SPECTRUM-learned/runs/crossfamily_learned_r5_4096/`（12 job 目录，evaluation.metrics.json 实测存在） |
| spectral_learned_7b_r10_4096（10/10 轮 + learned_gains.json + run_status=completed） | ✅ 存活 | `improving-learned/runs/spectrum_7b/spectral_learned_7b_r10_4096/`（10 个 round_* 目录均有 metrics） |
| multidomain learned-r5 | ⚠️ Partial（无 metrics.json，与审计记载一致） | `SPECTRUM-learned/runs/multidomain/learned-r5/` |
| qz 作业回执、运行日志（tau100/capacity-sweep/sweep-v1/highk-v1） | ❌ 随 improving/logs 删除 | 审计文档中留有 job_id 记录 |

## 结论二：对 48 case 执行计划的影响

1. **c00/c25（audit）判定**：数字证据（git 归档）+ 存活运行目录可复用；1.5B 主线原始工件不可复用。
2. **c01/c36（三种子配对 Plain–Fixed）**：catalog 标 historical_complete 的只有数字摘要，逐题工件已失。三配对需要跨种子 mean±SD、共同符合条件任务 D4 分母 → **必须新训**（c36/c01、c06/c07、c08/c09 及 c30 SSD、c45 SPD-hard 均需真实执行）。c01 标题"reproduce only if original evidence fails"成立：原始工件失败（丢失）。
3. **c16/c17、c32–c35（冻结迁移/插值，依赖 source run）**：其 source checkpoint 即 1.5B 主线 r5 模型，已失 → 待 P0 新训产出 r5 checkpoint 后再执行。
4. **c14/c15、c18/c19（跨家族/规模）**：DeepSeek/Qwen3B 配对本来就没有历史工件（not_run），不受影响。
5. **c25/c37–c43（7B Learned 十轮扩展）**：7B learned r10 证据完整存活，可作扩展表基线；tau08/no-decay/adaptive 等 7B 十轮工件已失，其数字存于审计文档，若审稿人要原始逐题数据需重跑（优先级在主线之后）。
6. **论文里引用的历史数字**：一律以 git 归档 observed_results.json/claims.json 为准，标注"数字自 2026-10-02 审计归档恢复，原始逐题工件未保留"；不做任何以丢失工件为基础的"恢复声明"。

## 结论三：修订后的执行顺序（与运行指南一致，主线 P0 优先级不变）

1. qz 探测完成后：先跑三种子配对（c36/c01、c06/c07、c08/c09）+ c02–c04 方向/强度 + c05/c27 信息控制（qwen1.5b 五轮 512 协议）
2. 用新训 r5 checkpoint 补 c16/c17、c32–c35
3. 跨家族 c14/c15、c18/c19
4. 7B Learned 扩展（复用 surviving learned 工件，缺的 arm 再训）

注：本结论基于 2026-11-08 磁盘与 git 现状；不修改任何 catalog 文件，只做核验记录。
