# 持续学习生成时的谱增益：独立实验与 Local 运行指南

交付状态：**generated_unexecuted**。本轮准备源码、独立入口、配置和软件测试；
没有在 Web 执行项目测试、模型加载、数据下载、GPU 实验或评分。
源码审查不能替代 Local 软件验收，更不能当作实验收益。

本轮按用户选择实现 **在生成控制参数 `a` 上处理新旧任务梯度冲突**。
四个实验臂、两个数据顺序、两种主模型更新设置，共 16 个独立 case。
建议先运行 `cg00`–`cg03`，验证冻结主模型时增益能否跨数据集保留；
再按结果运行逆序和完整自蒸馏。读取这份指南不会自动启动任何作业。

- [方法定义](../rounds/20261108-continual-gains/METHOD.md)
- [本轮交接](../rounds/20261108-continual-gains/WEB_HANDOFF.md)
- [独立 case 清单](../experiments/continual_gains/cases.json)
- [核心优化器](../src/improving/continual_gains.py)
- [跨域实验编排](../src/improving/continual_gain_study.py)
- [公共入口](../scripts/run_continual_gains.py)

## 1. 我们学习什么

生成时仍使用现有 K/V 输出干预：

\[
T_m(a_m)=U_m\operatorname{diag}(a_m)U_m^\top.
\]

`m` 表示一个被干预的 K/V 模块。校准时冻结主模型参数和 `U`，只对增益求梯度。
同一条实验轨迹跨数据集继承**同一组**增益；到新数据集不重置为 1，也不切换到
单独的任务适配器。数值上相等的特征值共享一个增益，优化器工作在这些实际的
降维增益坐标 `b` 上，避免任意旋转的退化子空间导致不同参数化。

新实验把 `U` 固定为**第一个域的 FIT 校准样本**所得到的谱基，全程复用。
这样跨域比较的增益和梯度使用同一个坐标系。未来域标签不参与初始谱基。
逆序实验检查这一首域选择的影响。即便主模型在自蒸馏中改变，固定坐标也不等于
特征语义始终不变；每次拟合必须在当时的主模型上重新计算旧域梯度和损失。

因此，“我们主要生成数据”的流程保持明确：

1. 用训练侧参考样本校准生成控制器 `a`；这些标签确实提供监督信息。
2. 用控制后的生成器产生当前域原始数据。
3. 完整自蒸馏设置中，恢复原生权重后，对所有原始生成记录执行普通、无权重 LoRA SFT。

梯度冲突处理不作用在学生 LoRA 参数或主模型 SFT 梯度上；校准参考答案不混入学生训练集。

## 2. 梯度约束及其实际含义

令当前域 FIT 损失为 `F(b)`，旧域 `j` 的 FIT 记忆损失为 `R_j(b)`。
损失均采用每条样本 completion token 平均 NLL，再在样本之间取平均。
所有梯度在**相同的当前主模型、固定谱基和当前增益**上计算：

\[
g_{new}=\nabla_b F(b),\qquad g_j=\nabla_b R_j(b).
\]

对于一个旧域，若 `g_new · g_old < 0`，无边界时的条件修正为：

\[
\tilde g_{new}=g_{new}
-\frac{g_{new}^{\top}g_{old}}{\|g_{old}\|_2^2}g_{old}.
\]

代码实际投影**更新步长**，联合处理所有旧域和增益边界：

\[
d_0=-\eta\frac{g_{new}}{\|g_{new}\|_\infty},\qquad
d\approx\operatorname{proj}_{\mathcal C}(d_0),
\]

\[
\mathcal C=\{d:\ g_j^\top d\le0\ \forall j,
\quad a_{min}-b\le d\le1-b\}.
\]

这里使用有限轮 Dykstra 投影，保存每个旧域的残差，并复查转换为实际增益数据类型后的
更新。达到迭代上限时，只有满足全部残差条件的候选才继续；不声称精确 QP 解或收敛。
先逐域投影再随意裁剪、只检查平均旧梯度，都不能替代这些联合约束。

方向条件只保证一阶项：

\[
R_j(b+d)=R_j(b)+g_j^\top d+O(\|d\|^2).
\]

所以每个候选还必须实际前向检查：当前 FIT 有改善、每个旧域损失不超过记录上限、
完整词表 forward KL 不超过预算。旧梯度恰好为零时跳过该方向约束，仍检查该域的实际损失。
最终候选才使用 guard 做一次否决；guard 不参与梯度、步长选择或候选排序。
随后经实际权重折叠路径再次检查 FIT、guard、全部旧域损失和 KL。
若拒绝更新，**原样保留进入阶段时的增益**；回退到全 1 会抹去已经继承的控制器。
输入错误和运行异常会报错，不能包装成一次成功回退。

### KL 的锚点

这轮 KL 为 `incoming controlled policy -> candidate policy`。
进入新域时已有非单位增益，不能直接把“相对原生模型的 KL 小于预算”当作总是可行的初态。
KL 前缀仍来自当前域训练提示上的固定原生生成，不用评测答案评分。
锚点采用进入本次拟合时的实际折叠策略，并在整个拟合调用中保持固定。
所以新的 `sequential` 是同一持续协议下的朴素对照，并非旧版逐轮重置 Learned 的原样复现。

### 与 CGL 的关系

[CGL 第 5.3 节](https://arxiv.org/html/2603.02951v2)在主模型参数空间中处理
SFT 与 GRPO 梯度冲突。这里借用条件冲突处理思想，约束对象改为生成时的谱增益；
旧方向来自保留的旧域 FIT 参考样本，不把 GRPO 梯度说成真实旧任务梯度。
本实现明确需要少量历史校准记忆，不能声称复现 CGL 的无历史数据设置。
方向投影也是已有持续学习/多目标优化技术，本交付不作方法首创声明。

## 3. 四个对照臂

| method | 增益继承并拟合当前域 | 旧域实际损失约束 | 梯度冲突投影 | 要回答的问题 |
|---|---|---|---|---|
| `native` | 始终 `a=1` | 无 | 无 | 不使用生成控制器的同协议基线 |
| `sequential` | 是 | 仅记录，不限制候选 | 无 | 顺序学习同一组增益会不会覆盖旧域能力 |
| `retention` | 是 | 每个旧域分别检查 | 无 | 只保留旧参考样本并拒绝坏更新是否已经足够 |
| `conflict` | 是 | 与 retention 相同 | 有 | 梯度投影在相同信息和搜索预算上有没有额外价值 |

几何来源、FIT/guard、解码器、增益步数/KL预算、评分人口和学生训练设置在可比较的臂间保持一致。
`conflict` 计算旧梯度会有额外开销，需报告实际时间/显存/前向及梯度工作量，不能把相同步数
解释为相同算力。`native` 在 frozen 设置不训练，在 self_distill 设置仍执行相同普通 SFT。

## 4. 两种设置、两种顺序、16 个独立 case

### frozen：先判断控制器本身能否保留

主模型始终不训练，跨阶段变化的可学习状态只有增益。旧域损失上限固定为该域退出时的
实际 FIT 损失加声明的容差，后续不随每个步长重新基准化。
这组直接回答“学 QA 的增益时是否损害已有 Math 生成控制”。

### self_distill：再判断收益能否传到学生

每域默认一轮：拟合增益、生成当前域数据、恢复原生权重、普通 LoRA SFT，继承学生和增益。
学生 SFT 自身可能改变旧域，因此旧域上限在**本次增益拟合入口的当前学生**上测量。
它只约束这次控制器变化造成的额外损害，不保证学生训练后旧任务不下降。
每个阶段结束后都对所有域评测原生模型与加控制器的生成，分别呈现学生效果和控制器效果。

| case | 主模型更新 | 数据顺序 | method |
|---|---|---|---|
| `cg00` | frozen | Math → QA | native |
| `cg01` | frozen | Math → QA | sequential |
| `cg02` | frozen | Math → QA | retention |
| `cg03` | frozen | Math → QA | conflict |
| `cg04` | frozen | QA → Math | native |
| `cg05` | frozen | QA → Math | sequential |
| `cg06` | frozen | QA → Math | retention |
| `cg07` | frozen | QA → Math | conflict |
| `cg08` | self_distill | Math → QA | native |
| `cg09` | self_distill | Math → QA | sequential |
| `cg10` | self_distill | Math → QA | retention |
| `cg11` | self_distill | Math → QA | conflict |
| `cg12` | self_distill | QA → Math | native |
| `cg13` | self_distill | QA → Math | sequential |
| `cg14` | self_distill | QA → Math | retention |
| `cg15` | self_distill | QA → Math | conflict |

每个 case 有自己的启动文件、不可变计划、配置副本、输出目录、锁和 attempt 日志。
没有读取清单就自动执行 16 个 case 的路径。与现有 rebuttal `c00`–`c48`、72-case 队列、
14B SPD 研究分开保存，不改变它们的含义、源代码或既有结果。

## 5. 模型、数据和固定预算

默认模型是已有本地完整 **Qwen2.5-7B-Instruct**，BF16、SDPA、`causal_lm` loader，
K/V 目标为从零计数的层 14、27。增益范围 `[0.1, 1]`；最多 8 个增益步骤，
学习率 0.1，每步最多 8 次回溯，缩减系数 0.5；FIT 最小改善 `1e-6`，
KL 预算 0.02，guard 容差 0。发布配置的投影上限 128 轮，归一化残差容差 `1e-10`，
旧域损失容差 0（比较另有明确记录的 `1e-6` 数值容差）。

| 项目 | Math | QA |
|---|---|---|
| 训练提示 | PRM 发布的 MATH 训练池抽取 1,024 条 | MMLU auxiliary_train 抽取 1,024 条 |
| 校准 | 64 条训练侧参考，54 FIT / 10 guard | 同样 54 FIT / 10 guard |
| 历史记忆 | 旧域的 54 FIT | 旧域的 54 FIT |
| KL 探针 | 8 条训练提示，原生生成最多 128 token | 同左 |
| 原始生成 | 每提示 1 条，最多 4,096 新 token | 每提示 1 条，最多 2,048 新 token |
| SFT 上下文 | 8,192 token | 10,240 token |
| 最终评测 | 全部 MATH500，每题 16 条 | 全部 MMLU-Pro 12,032 题，每题 1 条 |

还各有 64 条独立 development 数据用于 Local 运行条件核验。它们不替代最终评测人口。
表中的原始训练语料生成与 SFT 预算用于 `self_distill`；`frozen` 执行增益校准与完整
原生/受控生成评测，以单独测量控制器变化。
单次评测一个 policy 的两个域需要 8,000 + 12,032 条生成记录；阶段还分别记录原生与
受控生成，因此这些是完整评测 case，不是几分钟的速度承诺或小样本 smoke test。
没有本轮实测运行时/显存记录，不能据模型大小推断可并行数量。

完整自蒸馏沿用普通 completion-only LoRA：Q/K/V/O，rank/alpha 8，dropout 0.05，
1 epoch，batch 1，累积 16，学习率 `1e-5`。不按正确性筛选、重权或丢弃生成记录；
若训练上下文不能容纳声明的生成预算，必须报错。
默认每域一轮、一次固定私有随机化；逆序不等于独立训练种子重复，不能据此声称跨种子稳定。
跨阶段与方法的评测使用同一题目/样本随机流：评测采样的 `round_index` 固定为 0，
真实阶段、模型和控制器身份仍写入目录与封存记录。这样不因进入新阶段而额外更换评测
随机化；生成训练数据和 KL 探针仍记录自己的阶段。配置内嵌的旧 text recipe 保留原始
`rounds: 5`、`checkpoint_retention: latest` 和 `reestimate_each_round` 字段供来源比对；
本入口的实际日程由外层 `rounds_per_domain: 1` 控制，固定首域几何，并保留全部阶段检查点。

## 6. 下载数据与模型

在 Local 的已有、适配 Qwen2.5 的环境操作。依赖和评分说明见
[TEXT_TASKS.md](TEXT_TASKS.md#input-sources-and-acquisition) 与仓库 multidomain requirements。
数学评分额外需要 `sympy==1.13.3`、`pylatexenc==2.10`。
Web 未安装或验证运行依赖。

先核对已有 `data/multidomain/math`、`data/multidomain/qa` 和
`runs/private/multidomain_seed.json`。匹配的 manifest、文件哈希和构建器版本可直接复用；
不要删除旧 manifest 或重新生成私有 seed 来强行兼容。
缺少数据时，从交付仓库根目录顺序执行：

```bash
python scripts/prepare_text_data.py --config configs/multidomain/text_math_learned.json
python scripts/prepare_text_data.py --config configs/multidomain/text_qa_learned.json
```

两条命令使用已有 pinned 数据构建器，不加载模型：

| 输入 | 固定来源 |
|---|---|
| MATH 12,000/500 与 native grader | OpenAI PRM800K `7ecc794703b2877f63226f2477a49b34f9b25163` |
| MMLU auxiliary_train | cais/mmlu `c30699e8356da336a370243923dbaf21066bb9fe` |
| MMLU-Pro test 与官方提示示例 | TIGER-Lab/MMLU-Pro `b189ec765aa7ed75c8acfea42df31fdae71f97be` |

准备器校验官方 PRM 文件哈希、完整题数、分割独立性、输出哈希和私有随机化摘要。
原配置不启用 GPQA；不需要为了这 16 个 case 另行获取 GPQA。
若已有数据对应不同协议，保留旧目录，另准备一致的新目录并在 plan 中显式指定。
路径字符串也受 manifest 绑定，不能仅移动文件却把它当作同一已封存数据根。

默认模型路径为 `/inspire/hdd/global_public/public_models/Qwen/Qwen2.5-7B-Instruct`。
如果本机模型在其他位置，在首次 plan 使用 `--model-path /absolute/path/to/complete/snapshot`。
必须是完整且 tokenizer/元数据一致的本地 snapshot；运行会绑定实际权重文件身份，
不将宿主目录名当作 immutable HF revision。
当前本地路径配置不能直接交给要求 HF 仓库名与 revision 的旧下载脚本。

数学评分沿用原 `math_sandbox.backend: local`、10 秒超时和 pinned PRM grader。
这是子进程评分，**不是已通过 Bubblewrap 隔离验证的配置**；现有 local 分支不实施
`memory_mb` 地址空间上限。MMLU-Pro 使用原有官方提示与解析器适配。
保留解析失败、截断、超时和完整分母；不要把本研究的采样设置说成精确复现作者 leaderboard。

## 7. Local 软件验收与单 case 运行

先在独立 checkout 固定本次交付提交，恢复实际主机、环境、GPU 分配与已有任务状态。
运行下列**待执行**软件检查；作者 toy fixture 只检验软件性质，不是原生 benchmark 结果：

```bash
python -m pytest -q tests/test_continual_gains.py tests/test_continual_gain_study.py tests/test_continual_gain_cases.py
```

同时按交接中的文件清单运行相关已有 gain/fold/生成/SFT 回归检查，并在实际分配的 GPU
核验真实 7B 的参考梯度、精确折叠/恢复、完整词表 KL 和评分依赖。
如使用旧 qualifier，先检查其 loader 支持；旧 hybrid-27B qualifier 不能证明这里的 causal_lm 7B 可用。
Source binding 若因 Local 修复改变，使用新输出根和修订后的源提交，不移除封存文件。

以冲突投影 `cg03` 为例，所有命令从仓库根目录运行：

```bash
python scripts/continual_gain_cases/cg03.py plan --root runs/continual_gains_isolated_v1
python scripts/continual_gain_cases/cg03.py run --root runs/continual_gains_isolated_v1 --execute
python scripts/continual_gain_cases/cg03.py report --root runs/continual_gains_isolated_v1
```

首次 plan 可覆盖宿主路径，不能随意改科学预算：

```bash
python scripts/continual_gain_cases/cg03.py plan --root runs/continual_gains_host_v1 --model-path /absolute/model/snapshot --seed-file runs/private/multidomain_seed.json --math-data-root data/multidomain/math --qa-data-root data/multidomain/qa
```

之后 `run`/`report` 复用封存配置，不需要重复路径覆盖。通用入口等价：

```bash
python scripts/run_continual_gains.py plan --case cg03 --root runs/continual_gains_isolated_v1
python scripts/run_continual_gains.py run --case cg03 --root runs/continual_gains_isolated_v1 --execute
```

`run` 缺少 `--execute` 只准备/核验计划，不启动模型。
把上例文件名换为 `cg00`、`cg01`、`cg02` 即可分别启动第一组另外三臂。
并行数量应由 Local 的实际资源决定，不由本指南指定。

输出分层：

- `ROOT/cgXX/plan.json`、`plan.sha256.json`、`config.json`：计划与配置封存。
- `ROOT/cgXX/attempts/` 及 attempt 日志：每次启动的单独记录。
- `ROOT/cgXX/study/METHOD/`：固定几何、阶段输入、继承增益、评分和学生检查点。

中断后，只在同一提交、配置、输入和相容检查点上显式恢复：

```bash
python scripts/continual_gain_cases/cg03.py run --root runs/continual_gains_isolated_v1 --execute --resume
```

已提交的学生 checkpoint receipt 与阶段评分分开保存：若 SFT 已完成而评测中断，恢复应
加载该学生继续评测，不再训练一次。没有提交 receipt 的部分模型目录应报错并保留现场；
不能猜测已完成、覆盖权重或删除文件来通过检查。来源/计划/数据变化也应阻止旧目录恢复。

## 8. 看什么结果才支持这个方向

首先看 **`cg03` 对 `cg01`、`cg02`**，且比较完整序列而非只看最后一次校准损失：

| 证据 | 解释 |
|---|---|
| 学完第二域后的第一域受控生成表现 | 是否保留旧域的实际生成能力 |
| 第二域表现 | 是否付出过多新任务适应代价 |
| native / controlled 同阶段对照 | 增益控制本身贡献多少；自蒸馏时区分学生与控制器 |
| 每旧域 FIT 损失、限额、guard、KL | 有限约束是否如实执行；不把校准损失当成测试收益 |
| 冲突次数、投影残差、接受/拒绝与回退原因 | 改善是否伴随实际的梯度冲突处理 |
| 增益状态和固定几何哈希 | 是否真在继承同一组参数、同一坐标 |
| 实际耗时/显存和工作量 | 同一步数下额外计算是否值得 |

对于首域 `A`、次域 `B`，分别报告同一 policy 下
`A 在学完 B 后的准确率 - A 在学完 A 后的准确率`，负值表示下降。
不要只报两域平均数掩盖旧域损害；Math 同时报既有 pass@1/4/16，QA 保留 primary accuracy。
保存原始响应与逐题评分，便于后续做配对不确定性分析；本轮单轨迹不支持跨训练种子置信结论。

若 conflict 只改善梯度夹角/FIT、却不改善旧域生成；或与 retention 相同效果但明显更贵；
或保留旧域的代价是新域几乎不学习，这些都是需要保留的反证。
冻结主模型设置的收益不能替代完整学生 SFT 后的旧域表现。

## 9. Diffusion 放在哪里

本轮不训练 denoiser，也不引入 Brownian/ESRL 参数搜索。
当前已有每域小校准集，足以直接定义增益目标与旧域约束；先验证这条路径最容易定位效果来源。
不能把“diffusion 必须海量数据”当作无条件结论，但若未来要学习
`任务条件 -> 好的增益分布`，需要明确可用的增益训练样本、条件表示和额外训练预算。
两域一次轨迹本身不构成已验证的增益分布学习数据集。
本次保存的增益、任务顺序和阶段审计，可以供日后决定是否值得开展该独立研究。
