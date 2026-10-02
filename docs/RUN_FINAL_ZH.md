# SPECTRUM 最终实验运行指南

这版只保留一个正式入口：`scripts/run_release_study.py`。历史代码保留以便
追溯；不要把旧配置的结果混入这次新的固定方案。代码已经准备好，GPU 实验
尚未运行。先运行主实验，再按下面固定的块继续；不要依据测试集分数修改方法。

## 1. 环境与空间

使用 Linux、Python 3.10 或更高版本、支持 BF16 的 NVIDIA GPU，以及 Docker。
`24gb`、`48gb`、`80gb` 是保守批量配置，尚未实测其峰值显存。最终默认
`48gb`；它不启用量化或多卡模型分片。多张 GPU 用于运行不同作业。

完整方案保留全部轮次的合并学生权重。按名义参数量、BF16 和计划的训练轮次
估算，单是这些权重就约 0.8 TB；另外还有模型下载缓存、原始生成、校验记录及
算子文件。请为完整方案安排至少约 1 TB、并根据实际生成长度留出余量；这不是
实测占用。仅跑主实验所需空间明显更少。不要在运行途中删掉前一轮权重。

```bash
git clone https://github.com/Yunbo-max/SPECTRUM.git
cd SPECTRUM
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[train,analysis,evalplus]'
docker pull python:3.11-slim
docker build -f docker/EvalPlus.Dockerfile -t improving-evalplus:0.3.1 .
```

若 GPU 环境需要特定 CUDA 版本的 PyTorch，应先按该环境安装匹配的 PyTorch。
上面的项目依赖不负责安装系统 CUDA 驱动。数据/模型首次下载需要访问其
Hugging Face 来源。模型许可和精确版本见 `DATA_MODELS.md`。

## 2. 只准备一次的数据和随机化

```bash
python scripts/run_release_study.py init-seeds
python scripts/prepare_final_data.py --seed-file runs/private/seeds.json
```

第一条只创建本地私有的随机化文件，不显示数值，Git 也不会提交它。保留该文件，
不要为得到更好的结果反复重建。公开表格只显示 `r1/r2/r3`；本地结果仍保存完整
复现信息。

第二条下载并固定数据，不加载模型、不执行参考答案或生成程序。它准备：

| 数据集 | 数量与作用 |
|---|---|
| MBPP | 291 合成训练题、50 固定参考题、30 验证题、500 测试题 |
| HumanEval+ | 164 测试题，官方 EvalPlus 检查 |
| APPS Intro | 固定 200 测试题，适配评估协议 |
| CodeContests | 全部 165 官方测试题，适配评估协议 |
| LiveCodeBench | 固定 200 题；release_v5，2024 年 7–12 月窗口，适配协议 |

版本、日期范围、题目数量或文件校验不匹配会停止。不能用临时减少题目数量来
让正式方案继续；资源试运行应另建目录与协议。

## 3. 固定方案，不启动 GPU

```bash
python scripts/run_release_study.py plan --profile 48gb
python scripts/run_release_study.py status
```

计划位于 `runs/spectrum_release_v1/plan/manifest.json`，每项作业的具体参数在
旁边的 `configs/`。计划会固定代码校验值、数据校验值、模型提交版本、方法、
采样数、训练长度和私有随机化。之后更改这些内容，需要新的运行目录。

## 4. 正式运行顺序

**最先完成主实验。** 它补齐同一协议下 Vanilla SD、SSD、SPECTRUM 的五轮、
64 次采样对照和三次独立训练。

```bash
python scripts/run_release_study.py run --block core
python scripts/run_release_study.py report
```

如果有三张 GPU，可在三个终端分别运行；这与上述串行主实验是同一方案：

```bash
CUDA_VISIBLE_DEVICES=0 python scripts/run_release_study.py run --job core-qwen1.5b-r1
CUDA_VISIBLE_DEVICES=1 python scripts/run_release_study.py run --job core-qwen1.5b-r2
CUDA_VISIBLE_DEVICES=2 python scripts/run_release_study.py run --job core-qwen1.5b-r3
```

主实验之后，按固定计划继续，不需要重新规划：

```bash
python scripts/run_release_study.py run --block decoder
python scripts/run_release_study.py run --block mechanism
python scripts/run_release_study.py run --block token_matched
python scripts/run_release_study.py run --block diagnostic
python scripts/run_release_study.py run --block scale
python scripts/run_release_study.py run --block transfer
python scripts/run_release_study.py report
```

`scale` 包含以下三个可分开并行的作业：

```bash
python scripts/run_release_study.py run --job scale-qwen3b-r1
python scripts/run_release_study.py run --job scale-qwen7b-r1
python scripts/run_release_study.py run --job scale-deepseek6.7b-r1
```

若已决定运行整个固定矩阵，也可以使用 `run --block all`。它包含 40 个作业：
13 个训练作业、24 个冻结迁移作业、3 个解码评估作业。共 134 个训练“方法×重复×
轮次”，全新运行生成 7,106,080 个候选。它不是短时测试，候选数量也不能直接
换算成 GPU 小时。

## 5. 中断、恢复和 OOM

重复同一条 `run` 命令即可恢复；已完整保存且校验通过的阶段会复用。作业锁
防止同一个作业被两个进程同时写入。中断的 SFT 轮次从该轮训练起点重新开始，
并非 optimizer-step 级恢复。失败和重新执行会留下记录，不会自动扩大实验。

如果 OOM，不要直接改已开始的 JSON 配置。停止相关作业，保留原始结果，使用
新的目录和较小批量的配置生成新计划，例如：

```bash
python scripts/run_release_study.py plan --profile 24gb --run-root runs/spectrum_release_24gb
python scripts/run_release_study.py run \
  --manifest runs/spectrum_release_24gb/plan/manifest.json --block core
```

每个硬件配置是不同执行身份，不把缺失数据自动拼入另一个方案。代码升级也
需要新计划，以免新旧实现混合。

## 6. 怎样拿论文结果

```bash
python scripts/run_release_study.py status
python scripts/run_release_study.py report
```

`runs/spectrum_release_v1/release_report/` 提供：

- `endpoints.csv`：初始与最终的准确率、正确 AST 覆盖及保留率；
- `trajectories.csv`、`retention.csv`：逐轮轨迹与任务 bootstrap 区间；
- `paired_differences.csv`：相同题目、共同合格集合上的成对差异；
- `replicate_summary.csv`：按模型、条件分别汇总独立训练重复；
- `ablations.csv`、`decoder_effects.csv`：机制和固定解码敏感性；
- `teacher_student.csv`：生成策略变化及下一位原生学生的保留；
- `resources.csv`、`operators.csv`、`errors.csv`：资源、谱与失败信息；
- `REPORT.md`、`summary.json`：完整索引，未完成格显示 `x`。

`C64` 是 64 次总采样中的正确 AST 类别覆盖；`D4` 是将正确样本数匹配到四次
后的类别覆盖。不能用不同合格题集的均值相减来代替成对比较。模型规模复验的
单次训练也不能冒充多次独立训练证据。

所有计划完成后停止训练并据结果写作。哪项没有领先，就按取舍或机制边界报告；
不要临时替换主方法、修改测试集或继续挑选随机化。

## 本次开发做了什么检查

已做源码审核、数学与接口的独立检查、Python/JSON 语法解析、CLI 帮助入口检查。
新增了回归测试源代码，但遵循先前“只给代码”的要求，**没有执行 pytest、GPU
训练、benchmark 或生成程序**。因此这里交付的是完整实现和可运行方案，并不
宣称已在四种 GPU 模型上通过实际运行。
