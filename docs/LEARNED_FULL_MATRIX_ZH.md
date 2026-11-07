# SPECTRUM Learned — 多模型／多任务全面实验（2026-11-02）

状态：**代码与实验计划已提交，GPU 训练与原生 benchmark 尚未执行**。
这是从 main 的 `spectral_learned` 直接扩展的独立研究分支，
不是 Android GUI 分支。原来的单模型 10 轮 4096-token、512-token
crossfamily、数学/QA、ARC 历史运行目录和结果都不覆盖。

## 1. 实际实施的范围

| 领域 | 骨干 | Train / 校准 | 原生评测 | 方法／轮次 |
|---|---|---|---|---|
| Code | Qwen2.5-Coder-7B-Instruct | MBPP 291 / 50 | MBPP500 + HumanEval+164 + APPS Intro200 + CodeContests165 + LiveCodeBench200 | Plain/SSD/Fixed/Full-spectrum Learned ×5 |
| Code | Llama-3.1-8B-Instruct | 同一固定 MBPP | 同上 | 同上 |
| Code | DeepSeek-Coder-6.7B-Instruct | 同一固定 MBPP | 同上 | 同上 |
| Math | Qwen2.5-7B-Instruct | MATH train1024 / 64 | 完整 MATH500 ×16 samples | Base + 上述4方法，5轮 |
| QA | Qwen2.5-7B-Instruct | MMLU auxiliary1024 / 64 | 完整 MMLU-Pro12,032 ×1 sample | Base + 上述4方法，5轮 |
| Optional QA | 同一 7B 原生骨干 | 独立 MMLU auxiliary / 64 | MMLU-Pro12,032 + GPQA Diamond198 | 独立新数据／输出根，非默认 |

**ARC-AGI-3 的 Qwen3.8-27B Learned 适配暂未实现或完成 GPU 验证**：
它需要 native interactive action-prefix probe、独立参考 guard，以及完整
16K/32K 长上下文资格检查；不能拿文本分类的 `gain_pipeline` 冒充已完成适配。
当前仓库也**没有单独的 Physics 验证数据集**；GPQA 含物理类问题，
但不能称作独立物理 benchmark。

代码任务的五个名字是五个 *evaluation datasets*，不是五个训练数据集。
APPS/CodeContests/LCB 使用本仓库明示的 **adapted native verification**，
不能写成官方 leaderboard。HumanEval+ 使用固定 EvalPlus 官方 base+plus
测试。GPQA 需要授权数据访问并与主 QA 实验分开。

## 2. 相同算法，而非不同领域重新设计

每轮用当前原生模型固定的参考答案损失估计 K/V 激活梯度二阶矩：

\[
C_r=U_r\Lambda_rU_r^\top,\qquad
T_r(a)=U_r\operatorname{diag}(a)U_r^\top,\quad a_{\min}\le a_j\le 1.
\]

在模型和谱基冻结时，拟合**全部连续方向增益**；数值等值特征方向共享增益。
最小化拟合参考答案的 token NLL，检查原生到干预模型的
**full-vocabulary forward KL**，最终 guard veto 和 BF16 weight-fold 检查
任一失败则回退恒等。算子只用于**生成数据**，训练与最终推理恢复原生权重，
使用所有未筛选的自生成答案做普通 LoRA SFT，**无执行奖励筛选或动态步权重**。

- Code 学习版参考为 50 条（40 fit / 10 guard），固定谱基 baseline 在
  **同样 40 条 fit** 上构造。其它 10 条不为 fixed baseline 提供谱。
- Math、QA 各 64 条（54 fit / 10 guard），固定谱基 baseline 在
  **同样 54 条 fit** 上构造。
- 每轮另用 8 条来自训练任务的**原生采样 prefix probe**做 KL 约束。
  它不读取训练题的参考答案，也不看 benchmark 结果。
- 默认 gain optimization：最多 8 次梯度步、每步最多 8 次回溯、
  min_gain=0.1、KL budget=0.02 nat/target token。
- `spectral_learned` 与 `spectral_soft` 之间最主要的数学区别是
  **连续独立增益优化**而不是固定 \(\tau=1\)。
  学习器出现 identity fallback 必须保留并报告。

## 3. 资源与真实成本：先读这个再开跑

纯静态预算：

```bash
python scripts/plan_learned_full_matrix.py
bash scripts/run_learned_full_matrix.sh budget --execute
```

此代码全矩阵**计划**生成约 **2,995,200 次 Coding completion**
（含全部轮次 MBPP 的原生评测及 HumanEval+/三个额外迁移集；
其中 MBPP synthetic train 279,360 次），还包括数学 168,000 次
原生评测 completion、QA 252,672 次原生评测 completion，
以及 calibration probes。以上不是实测完成数、GPU 时间，也不是每条
都生成到最大 4096 tokens。即使只用单张 H100，完整矩阵成本仍然很大。

建议按实际硬件至少规划 **80GB BF16 GPU 作为优先资格验证目标、
64GB 以上系统内存、约 1TB 空闲磁盘**；这些仅为预留建议，
不能代替峰值测量。DeepSeek K/V 投影宽度较大，其 CPU 协方差分解
与激活开销也应独立测量。每个 learned arm 的额外前向／反向和
guard/折叠代价与普通 baseline 不相等；报告 CUDA peak、时长、token 与
失败回退。正式运行前务必设置合理服务器存储配额与 GPU 排程。

## 4. 云服务器准备

**不要在已经运行的 main 工作树直接 checkout 新源码**。新建独立工作树：

```bash
git fetch origin research/learned-multimodel-multidomain-20261102
git worktree add ../SPECTRUM-learned origin/research/learned-multimodel-multidomain-20261102
cd ../SPECTRUM-learned
python -m pip install -e '.[train,evalplus,analysis,test]'
# 数学评测的 native PRM 依赖
python -m pip install 'sympy==1.13.3' 'pylatexenc==2.10'
# 安全地执行生成代码所需的独立 Docker runner
docker pull python:3.11-slim
docker info
```

新 Coding 配置默认 `evaluation.backend=docker`，禁用不安全 local；
必须对 Docker namespace/network/PID/memory 限制在本机做预检。
若宿主没有 Docker，不要在共享训练机上直接开启不受信任的生成代码；
可以改用已通过验证的 bwrap，在**新输出根**冻结修改后的协议。

Llama 官方 Hugging Face 权重需要用户自己的 Meta access approval，
缺少授权可先单独跑 `--model=qwen7b` 或 DeepSeek。所有训练在本地
Transformers 完成，不需要付费 API。

Qwen2.5-7B Math/QA 的配置默认模型路径是
`/inspire/hdd/global_public/public_models/Qwen/Qwen2.5-7B-Instruct`；
如不在该机器，需在**正式运行前**复制 JSON 到自己的专用配置并
更新 model.name、新 output_dir，所有方法必须使用同一原始模型身份。
训练中不能修改配置或重用不同源码的封存 checkpoint。

## 5. 分阶段启动（默认只打印，不执行）

```bash
# 看将执行哪些命令；无模型加载
bash scripts/run_learned_full_matrix.sh prep-code --model=qwen7b
bash scripts/run_learned_full_matrix.sh prep-text

# 只有明确传 --execute 才实际运行
bash scripts/run_learned_full_matrix.sh prep-code --model=qwen7b --execute
bash scripts/run_learned_full_matrix.sh prep-text --execute

# 先执行无依赖静态预检（无需 CUDA、下载或服务器环境）：

```bash
python scripts/preflight_learned_full_matrix.py
bash -n scripts/run_learned_full_matrix.sh
```

先验收新代码和无模型协议
python -m pytest tests/test_crossfamily_study.py tests/test_crossfamily_learned.py \
    tests/test_text_contracts.py tests/test_text_learned.py \
    tests/test_gain_pipeline.py tests/test_learned_gains.py \
    tests/test_qualify_learned_matrix.py tests/test_learned_extra_transfers.py \
    tests/test_learned_full_matrix.py -q

# 先只检查一个真实 Qwen7B Learned calibration，没有 SFT/benchmark
bash scripts/run_learned_full_matrix.sh qualify-code --model=qwen7b --execute
bash scripts/run_learned_full_matrix.sh qualify-text --execute

# 逐模型进行完整 MBPP 五轮，含 4 组
bash scripts/run_learned_full_matrix.sh train-code --model=qwen7b --execute
bash scripts/run_learned_full_matrix.sh transfer-code --model=qwen7b --execute

# 确认上述成本/结果完整后，再启动其它 2 个 Coding 模型
bash scripts/run_learned_full_matrix.sh prep-code --model=deepseek6.7b --execute
bash scripts/run_learned_full_matrix.sh qualify-code --model=deepseek6.7b --execute
bash scripts/run_learned_full_matrix.sh train-code --model=deepseek6.7b --execute
bash scripts/run_learned_full_matrix.sh transfer-code --model=deepseek6.7b --execute

# Llama 有授权后照上述方式换 model=llama8b
# 数学与 QA 不需要重复运行 crossfamily checkpoint
bash scripts/run_learned_full_matrix.sh math --execute
bash scripts/run_learned_full_matrix.sh qa --execute

# 可选：有 GPQA 访问授权才运行，使用独立数据与输出
bash scripts/run_learned_full_matrix.sh prep-gpqa --execute
bash scripts/run_learned_full_matrix.sh qa-gpqa --execute
```

`qualify-code` 只检验完整 Learned 校准及折叠路径，不会代替
6144-token LoRA SFT 的实际显存测量。正式大矩阵请先在新实验根做
短样本训练／推理容量检查，检查 OOM、日志、模型版本、native evaluator。
终端原样保存 stdout/stderr、运行 SHA、依赖及 Docker 镜像 ID。

脚本 `all --execute` 是明确授权下的**顺序全矩阵**，但既无自动后台任务
也不代替 GPU 预算、模型授权和数据准备。小规模验收后再用它；
不建议第一次直接运行全部数百万候选。

## 6. 结果与验收

Code:
- `runs/crossfamily_learned_r5_4096/jobs/{model}/`：5 轮四方法 checkpoint、
  MBPP 所有原始输出/验证与 learned gain 接受、回退、KL、资源日志；
- `runs/crossfamily_learned_r5_4096/transfer/{model}/`：
  HumanEval+ 官方 base+plus；
- `runs/crossfamily_learned_r5_4096/transfer_extra/{model}/{dataset}/`：
  额外三个冻结迁移数据集，记录适配验证定义；
- `runs/crossfamily_learned_r5_4096/jobs/{model}/longitudinal/`：
  Pass@k、正确实现覆盖、匹配正确数量的丰富度及配对轨迹。

Math/QA:
- `runs/multidomain/learned-r5/{domain}-qwen25-7b/`：
  Base/Plain/SSD/Fixed/Learned 各轮原生指标、
  fit/guard/probe/算子日志及 final paired confidence intervals。

**科学完成不等于路径存在**：必须检查 seal/checkpoint hashes、
原生评测全分母、没有额外丢弃长目标、没有 runtime evaluator failure，
并保留所有负面结果。单一训练种子无法证明跨训练运行的稳定性；
后续论文需要再做独立复现种子。相关结果不应写成已经“显著领先”。

## 7. 实施状态

这次交付是在远端 GitHub 上新增／更新源代码与测试源码；
**没有从本会话运行 pytest、真实 GPU calibration、数据下载、任何完整训练
或原生代码评分**。用户云服务器的 CPU/GPU/存储实测、依赖安装和
数据 access 需要通过上述阶段逐项 qualification。
