# ICLR rebuttal：固定协议、多 seed、完整曲线与转移诊断

本分支以多模型代码 `2212a4c9235dac90c5f0ace5a2afc1d54af6517f` 为基础，整合 `da70329c3d1cb07bbd3380d563e2cc600541a8dc` 的三状态诊断。**不是 PI-SPECTRUM 或 Android GUI，不加入新的 SFT-KL 合并方法。** 原始 Fixed-soft 与 Learned 扩展分别报告，历史数据、结果和活动运行目录不修改。CPU 测试不是新 7B 成绩。

## 修复与约束

所有方法的未训练轮次必须加载紧邻上一轮的原生 checkpoint；缺失时停止，不能退回基座或更早的模型。已保存当前轮训练模型时可以继续评测，不要求恢复合法清理的旧模型。

保留 matched-reference 逻辑：Fixed-soft 使用 40 条拟合参考；Learned 使用同样 40 条，另有 10 条 guard。总标签访问数并不相同，因此机制组补 Fixed-soft-50 和 Plain+reference-replay-50。Replay 增加监督 token，不是 compute-matched。

三状态 `pre_native → pre_spectral → post_native` 现在覆盖全部对照，使用完整 30 道 DEV、每题 64 样本、同一解码。Plain/SSD 没有谱干预，第二状态是无干预对照。SSD 正式训练采样仍使用原实现的 1.5/0.8/20；统一诊断解码不等于 SSD 的实际合成分布。DEV 评分不反馈给增益拟合或训练样本选择。

SFT 后不得用新模型补造旧的 pre-native/pre-spectral 证据。读取诊断汇总前重验所有封存文件 checksum。配置、数据、代码和私有 seed 都固定；缺失结果标为 missing，不填 0。

## 实验矩阵

| block | 模型 | 方法 | 训练重复 | 轮数 |
|---|---|---|---:|---:|
| core | Qwen2.5-Coder-7B | Plain / SSD / Fixed-soft-40 / Learned | 3 | 10 |
| crossfamily | Llama-3.1-8B、DeepSeek-Coder-6.7B | 上述四组 | 各 1 | 5 |
| mechanism | Qwen2.5-Coder-7B | SPD-hard / Random-soft / Isotropic-soft | 1 | 5 |
| mechanism | Qwen2.5-Coder-7B | Fixed-soft-50；Plain+reference-replay-50 | 各 1 | 5 |
| objective | Qwen2.5-Coder-7B | 四个主对照全部改 completion-only | 1 | 10 |

主实验仍为 `loss_scope=all`。Completion-only 是独立四组消融，不能只给我们的方法换配方。样本数、长度上限和 epoch 相同不等于实际监督 token 相同；输出保留真实 target-token exposure 和资源记录。

Qwen 主实验使用全部 attention 层；跨模型保留既有的两层配置。两者的干预位置/成本差异必须明确报告，不能声称层覆盖完全相同。

MBPP 使用完整 500 题、每题 64 样本，每轮原生 Student 都评测，保留 round-0。Qwen 预定主终点为第 5/10 轮，跨模型为第 5 轮，不按 TEST 最佳轮挑 checkpoint。DEV 在 1/5/8/10 轮运行，五轮组为 1/5。core/crossfamily 的最终 checkpoint 还评测完整 HumanEval+164，复用 official EvalPlus adapter，不在目标集训练。

APPS/CodeContests/LiveCodeBench 和 MATH500/MMLU-Pro 的原有入口保留，但本入口的 `--block all` **不会自动启动它们**。相关说明见既有 `docs/LEARNED_FULL_MATRIX_ZH.md`；没有运行的实验不能算成本次 rebuttal 的结果。

## 独立 checkout 与环境

不要切换正在训练的 checkout。正式运行应固定交付的最终 commit。

```bash
git fetch origin research/iclr-rebuttal-stability-20261103
git worktree add ../SPECTRUM-rebuttal origin/research/iclr-rebuttal-stability-20261103
cd ../SPECTRUM-rebuttal
python -m venv .venv-rebuttal
source .venv-rebuttal/bin/activate
python -m pip install -e '.[train,test,analysis,evalplus]'
python -m pytest -q
```

GPU Torch/CUDA 必须与服务器匹配，不要升级活动旧环境。CPU CI 通过不意味着真实 7B BF16 显存已经合格。

## 固定 seed 与后端

```bash
python scripts/run_iclr_rebuttal.py init --root runs/iclr_rebuttal_v1
python scripts/run_iclr_rebuttal.py preview --root runs/iclr_rebuttal_v1 --block all
```

数据 seed 从原生 Learned 配置读取，维持原 MBPP 划分规则。三个新训练 seed 只生成一次，保存在忽略上传的 `runs/`，权限 0600。不要重新生成 seed 来挑结果，也不要公开数字 seed。

默认 Docker：

```bash
docker pull python:3.11-slim
docker build -t improving-evalplus:0.3.1 -f docker/EvalPlus.Dockerfile .
```

没有 Docker 的机器可在首次 init 使用 `--backend bwrap`，实际可用性由原 sandbox qualification 检查。不会自动回退本机执行。确需无隔离模式时，必须在新根目录首次 init 显式加 `--backend local --allow-unsafe-local`。模型生成程序不可信，这不提供隔离，不推荐在有凭据或重要文件的主机使用。后端封存后不能改变。

## 准备与封存

```bash
python scripts/run_iclr_rebuttal.py prepare --root runs/iclr_rebuttal_v1 --model all --execute
python scripts/run_iclr_rebuttal.py plan --root runs/iclr_rebuttal_v1
```

模型 revision、官方数据准备器均沿用原实现，所有方法和 seed 使用同一份共享数据。下载复用 HF cache；Llama 权限或任何数据准备失败都会停止。先只跑 Qwen，可将 prepare 的模型选为 `qwen7b`，跨模型执行前再 prepare 对应模型。

不得修改封存 config 后继续旧 run；需要变更就建立新根目录。

## 运行与恢复

先运行核心 rebuttal：

```bash
python scripts/run_iclr_rebuttal.py run --root runs/iclr_rebuttal_v1 --block core --stage all --execute
python scripts/run_iclr_rebuttal.py report --root runs/iclr_rebuttal_v1
```

`all` stage 顺序执行真实模型 gain qualification、训练/每轮评测和最终 HumanEval+。Qualification 只检验增益校准，不保证完整 SFT 的峰值显存。失败停止并保留证据；原样重跑命令可以恢复。每个 job 有独占锁，不得在未确认进程已停止前删除锁。

随后补齐全部预定 block，已完成格子按原协议验证后复用：

```bash
python scripts/run_iclr_rebuttal.py run --root runs/iclr_rebuttal_v1 --block all --stage all --execute
python scripts/run_iclr_rebuttal.py report --root runs/iclr_rebuttal_v1
```

默认前台串行，不启动后台 watcher。多 GPU 可分别运行不重叠的 `--replicate r1` / `r2` / `r3` 并设置不同 `CUDA_VISIBLE_DEVICES`；不要两进程认领同一 job。仅做最终迁移评测可使用 `--stage transfer`，但必须先完成相应训练。

不加 `--execute` 的 run/prepare 只是显示计划，不下载模型或运行训练。`report` 只读汇总，不补跑缺失结果。

## 预算与结果解释

单个 Qwen 主 lineage 含四方法：训练生成 186,240 条，MBPP 测试 1,312,000 条（含共享 round-0），DEV 三状态 92,160 条，再加 gain probes、qualification 和 HumanEval+。三 seed 核心不是 smoke test。Preview 给样本预算，不给虚构 GPU 小时。

`checkpoint_retention=latest` 每个方法保留最后一个完整模型，旧轮次保留样本、指标与 receipts。全矩阵有 29 条方法训练轨迹，最终模型本身可能占数百 GB，另需临时旧/新模型、HF cache、协方差和数百万条样本空间。按本机实际文件大小核算，不能保证 500GB 一定够。

输出在 `runs/iclr_rebuttal_v1/report/`：`trajectories.csv`、`report.json`、`README.md`。指标为 pass@1/16/64、正确 AST C64、D4 和 eligible-task 数；C64 retention 以各自 round-0 为分母。JSON 包含每轮 task-paired bootstrap、独立训练重复的 mean/SD、资源与三状态记录。不能把 3 次训练 × 500 题当作 1500 次独立训练。

AST 是实现结构代理，不是语义策略证明；短 probe KL 不是多轮轨迹定理。只有真实训练/评测完成的格子可写入 rebuttal。
