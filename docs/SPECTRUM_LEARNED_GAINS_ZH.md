# SPECTRUM：每轮学习完整谱增益，2026-11-01

状态：**generated_unexecuted**。这是用户选定方法的代码交付，Web 没有运行项目测试、加载模型、训练或执行生成代码。源代码审查不能替代用户主机上的软件验收、真实 7B 显存资格验证和原生评测。

先读 [Local 运行入口](../LOCAL_AGENT_RUNBOOK.md) 和 [本轮交接](../rounds/20261101-learned-gains/WEB_HANDOFF.md)。数学定义、假设和待检验结论见 [METHOD](../rounds/20261101-learned-gains/METHOD.md)。

## 本次改变什么

新增独立方法 `spectral_learned`。保留原来的固定 tau、tau decay 和谱熵 adaptive 配置及历史输出。本次只替换**生成阶段谱算子的增益控制**，后续仍是原来的普通 LoRA SFT；此前讨论的按步骤加权 SFT 尚未接入。这使新增控制器的效果可以单独检查。

每轮在当前模型的相同 K/V 模块上计算参考损失的梯度二阶矩，得到谱基。在该基中学习完整的连续增益；不存在人为预设的 2–3 个谱段。只有数值上相同的特征值共享增益，零特征值子空间也共享增益。数值相等容差在配置和输出中记录。

\[
T_r(a)=U_r\operatorname{diag}(a)U_r^\top,
\qquad a_i\in[a_{\min},1].
\]

模型权重与本轮谱基在求增益时冻结。有限次投影梯度和回溯搜索降低拟合参考的平均 CE，同时检查同一批训练侧前缀上原生模型到干预模型的完整词表 forward KL。它是带显式可行性检查的近似求解器，**不是全局最优解或多轮稳定性的证明**。

谱基拟合、增益拟合与检查使用同一份原有 50 条参考答案：前 40 条用于拟合，后 10 条用于检查，固定顺序及身份留档。10 条检查参考不参与构造谱基、求梯度或迭代候选选择。优化结束后，只检查最终候选：先检查可微激活路径，再检查实际 BF16 权重折叠路径，两个 guard 检查均须通过。任一检查失败都返回恒等算子，不用 guard 继续挑选其他迭代。它们仍是校准检查数据，不能当作独立测试集。参考答案仍提供监督；这不是完全无监督训练。

KL 探针来自训练集问题上的原生模型采样，不读取训练题的标准答案或执行测试。KL 使用原始模型 logits 的完整词表 softmax，位于 temperature、top-p、top-k 采样变换之前；它不是截断后解码分布的界。默认只检查短前缀，因此其 KL 约束只适用于实际记录的探针位置，不构成完整 4096-token 自由生成的全局界。

求得算子后，代码用实际 BF16 权重折叠路径重新检查拟合 loss、检查集 loss 和 KL。未找到合格候选时返回恒等算子。无效输入、非有限原生基线或模型执行错误应报错，不能伪装成正常回退；数值无效的候选不能被接受，其拒绝/回退必须留档。最终算子只在生成时使用，生成结束恢复原生权重，再进行普通 SFT 与原生评测。

`calibration.gain_learning` 的首版有限求解预算如下。它们是已公开的开发设置，不是已调优结果：

| 参数 | 默认值 | 语义 |
|---|---:|---|
| `guard_examples` | 10 | 同一 50 条参考末尾 10 条，仅最终检查 |
| `probe_examples` | 8 | 训练侧原生探针问题数 |
| `probe_max_new_tokens` | 128 | 每个探针最多生成 token 数 |
| `max_steps` | 8 | 最多增益更新步数 |
| `learning_rate` | 0.1 | 按全体增益梯度最大绝对值归一化后的初始步长 |
| `min_gain` | 0.1 | 正增益下界；所有增益上界为 1 |
| `kl_budget` | 0.02 | 实测探针每目标 token 的平均 forward KL 预算，单位 nats |
| `max_backtracks` | 8 | 首次尝试之外最多 8 次缩步 |
| `backtrack_factor` | 0.5 | 每次回溯步长倍率 |
| `min_improvement` | 0.000001 | 平均每参考样本 CE 的最低拟合改善 |
| `guard_tolerance` | 0 | 最终检查参考不允许观测到恶化，另计数值容差 |
| `degeneracy_rtol` / `degeneracy_atol` | 0.0000001 / 0.000000000001 | 在归一化特征值上判定数值相等；不作人为谱分段 |
| `kl_chunk_tokens` | 32 | 完整词表 KL 的 token 分块大小，不是词表截断 |

实现另记录固定的 `1e-6` 数值容差。只有其范围内的负 KL 舍入误差会归零并计数；较大的负值或非有限值必须停止。最终使用实际折叠路径的拟合改善、检查 loss 与 KL 判定，不以可微路径的较好数字替代它们。

## 模型、数据与预算

| 项目 | 本轮设置 |
|---|---|
| 模型 | Qwen2.5-Coder-7B-Instruct；复用实际主机原始 checkpoint |
| MBPP | 291 训练 / 50 参考 / 30 开发 / 500 测试 |
| 参考内部划分 | 固定 40 拟合 / 10 检查 |
| 轮次 | 10；保留 base 和每轮原生评测 |
| 每题训练生成 | 16 个原始输出 |
| 每题评测生成 | 64 个输出 |
| 长度 | 生成最多 4096；SFT 总长度 6144；禁止额外 SFT 截断 |
| SFT | 沿用原配置，包括 `loss_scope: all`；不增加步骤权重 |
| 输出目录 | `runs/spectrum_7b/spectral_learned_7b_r10_4096` |

50 条答案的总访问预算与原设置相同，但本方法将它们拆分为拟合和检查，原控制器默认使用全部 50 条构造谱。因此这不是严格只改变一个标量映射的对比。需要隔离控制规则时，另行预先固定同一拟合集的原控制器对照，并保留所有尝试；不要事后挑选参考题或依据测试结果改参数。

学习增益增加多次模型前向、反向及原生探针生成。参数向量小不意味着反向成本小。24GB GPU 能否完成实际 7B 校准和 6144-token SFT 尚未测量，不承诺 4090 容量或速度。

## 下载数据和模型

以下命令属于用户实际 Linux GPU 主机上的既有执行流程；在仓库根目录运行。先恢复真实 SSH 主机、Conda 环境、GPU 分配、运行进程及计算预算，不在运行中的 checkout 上升级。复用完整且身份匹配的现有输入，不重复随机划分。

现有代码环境依赖见 [pyproject.toml](../pyproject.toml)。需要新环境时，按 [现有 Local 环境卡](../LOCAL_AGENT_RUNBOOK.md#restore-host-and-prepare-environments) 创建代码环境；不要安装 ARC/27B 环境来运行此 7B 实验。

数据缺失时，使用原有已检查入口及固定数据版本：

```bash
python -m improving.cli prepare --dataset mbpp --output-dir data/mbpp --revision 4bb6404fdc6cacfda99d4ac4205087b89d32030c
```

模型配置沿用已有主机路径 `/inspire/hdd/global_public/public_models/Qwen/Qwen2.5-Coder-7B-Instruct`。该路径不存在时，可下载固定官方版本到新缓存：

```bash
hf download Qwen/Qwen2.5-Coder-7B-Instruct --revision c03e6d358207e414f1eca0bb1891e29f1db0e242 --local-dir models/qwen25-coder-7b-pinned
```

随后复制本轮 YAML，在副本中绑定实际 `model.name` 和新的 `output_dir`。保留下载完整性记录、实际分片与 tokenizer 文件；pipeline 会记录实际模型文件指纹。不得覆盖使用中的模型或运行目录。下载成功不等于模型已在目标 GPU 上通过资格验证。

## 执行与恢复

以下是交给 Local 执行的命令，Web 未运行。所有项目执行通过现有主机执行流程提交；工作目录为交付版本的仓库根目录。

先完成新增测试和原有长度/谱/pipeline 回归验收，再验证数据划分和配置：

```bash
python -m pytest tests/test_learned_gains.py tests/test_gain_pipeline.py tests/test_spectral.py tests/test_calibration.py tests/test_full_completion_targets.py tests/test_pipeline.py -q
python -m improving.cli validate --config configs/spectrum_7b/spectrum_7b_r10_learned_4096.yaml
```

接着在真实 7B 模型和原生参考数据上单独验证校准路径；这不会启动 SFT 或 500 题测试评测：

```bash
python scripts/qualify_learned_gains.py --config configs/spectrum_7b/spectrum_7b_r10_learned_4096.yaml --output-dir runs/qualification/learned-gains
```

校准资格检查使用真实 40 条拟合、10 条检查参考和 8 个训练问题的原生探针。核对实际输出、显存、异常恢复和折叠后的约束；返回恒等算子是合法的“未找到可接受改善”，不是科学成功，也不自动判为软件失败。旧的 `improving.cli calibrate` 只计算参考谱，不能代替这条完整增益校准检查。

然后验证实际 6144-token SFT 容量；校准通过不证明 LoRA 长序列训练通过。原生软件、输入、资源资格验证完成后，显式运行十轮：

```bash
bash scripts/run_spectrum_learned_4096.sh
```

采用主机专用配置副本时：

```bash
cp configs/spectrum_7b/spectrum_7b_r10_learned_4096.yaml configs/spectrum_7b/spectrum_7b_r10_learned_4096_local.yaml
```

先编辑副本的 `model.name` 与 `output_dir`，再执行：

```bash
SPECTRUM_CONFIG=configs/spectrum_7b/spectrum_7b_r10_learned_4096_local.yaml bash scripts/run_spectrum_learned_4096.sh
```

这里的 `_local.yaml` 是运行前由用户从交付配置复制、绑定实际模型和输出路径的副本，不是另一个已交付配置。命令须指向实际存在的文件；不需要改路径时直接使用默认命令。恢复同一实验：

```bash
bash scripts/run_spectrum_learned_4096.sh --resume
```

新配置和新启动脚本只运行 `spectral_learned`，不会自动启动其他 baseline。脚本在前台执行，不自行创建云任务或后台训练。任何主机路径调整都必须在第一次运行前完成并留档。

附带一个可选的匹配拟合集对照：`configs/spectrum_7b/spectrum_7b_r10_spectral_4096_tau06_anchor40.yaml`。它沿用 tau0.6 衰减，只让原控制器以相同的前 40 条参考计算谱，并写入新的目录。原来的 50 条参考 tau0.6 配置没有修改。该对照不会自动运行；在需要隔离参考划分差异且已有预算时显式提交：

```bash
python -m improving.cli validate --config configs/spectrum_7b/spectrum_7b_r10_spectral_4096_tau06_anchor40.yaml
python -m improving.cli run --config configs/spectrum_7b/spectrum_7b_r10_spectral_4096_tau06_anchor40.yaml
```

`--resume` 只用于同一源码、配置、模型和数据身份的本轮运行。即使 SFT 已完成、恢复时只需继续评测，仍要验证保存的增益策略和校准输出身份，不能跳过缓存完整性检查。pipeline 对 `src/improving/*.py` 计算源码指纹；新增模块也会改变整体指纹。旧实验应在其原始固定版本继续，不能用新版代码恢复旧目录，即使旧方法的数学定义未变。

## 验收、诊断与返回

每个训练轮目录下，重点检查这些文件：

| 文件 | 含义 |
|---|---|
| `calibration.pt` | 仅由 40 条拟合参考得到的当轮谱与来源 |
| `gain_probe.jsonl`、对应 `.parts` | 当前原生模型在训练问题上的探针及精确 token；不是 SFT 训练样本 |
| `gain_inputs.json` | 拟合、检查和探针的精确编码及掩码，供本地身份校验；不进入公开小包 |
| `learned_operators.pt` | 与输入协议绑定的最终算子缓存 |
| `learned_gains.json` | 候选搜索、loss/KL、增益及恒等回退原因 |
| `gain_provenance.json` | 拟合/检查/探针身份和缓存绑定 |
| `calibration_provenance.json`、`operator_diagnostics.json` | 最终实际使用的谱与算子身份 |
| `*.resources.json` | 原有阶段资源记录；另含 `gain_probe.resources.json`、`gain_learning.resources.json` |
| `training_stats.json`、`evaluation.metrics.json`、`complete.json` | SFT、原生评测及完成文件校验 |

验收首先检查：参考拟合/检查任务无重叠、未使用开发或测试答案、探针的原生 checkpoint 与当前轮一致、精确生成 token 被保留、谱基及增益身份可追溯、所有增益有限且在区间内、实际折叠后的 KL 和检查 loss 符合配置。再检查生成后权重确实恢复、SFT 无额外截断和原生评测输出完整。

| 现象 | 下一步检查 |
|---|---|
| 经常返回恒等算子 | 看拟合收益、检查集变化、KL 预算、回溯拒绝原因；不能直接视为代码失败 |
| 学习时可行、折叠后拒绝 | 检查 BF16 折叠与可微路径差异，保留两套诊断；不跳过最终检查 |
| 非有限原生 loss/梯度或模型异常 | 停止该任务，保留日志，检查输入与 dtype；不放宽约束掩盖异常 |
| CUDA OOM | 查实际最长序列及阶段；在新配置/目录中做有记录的资源调整，不降低正式输出长度或丢弃长样本 |
| resume 身份不匹配 | 回到原始源码和配置或使用新目录；不删除 manifest 或重写完成回执 |
| loss 降低但覆盖下降 | 保留负面结果；参考 loss 是优化代理，不保证正确解多样性 |

最终需同时返回原生 pass@1/pass@64、正确实现覆盖、生成长度/截断/重复情况、每轮增益与校准诊断、额外校准时间和实际资源记录。所有候选和回退都属于结果，不只返回最佳轮次。不要公开模型权重、凭据、私有随机化信息或未经检查的批量原始数据。

用本轮小型结果收集器打包诊断和摘要；它不重新评测，不打包模型权重、原始提示词或完整生成语料：

```bash
python scripts/collect_learned_gains.py --run-dir runs/spectrum_7b/spectral_learned_7b_r10_4096 --output runs/returns/spectral-learned-review.zip
```

使用自定义输出根时将 `--run-dir` 改为实际路径。默认命令另写 `runs/returns/spectral-learned-review.summary.json`，ZIP 内也包含 `collection_summary.json`。已有同名 ZIP 或摘要时收集器拒绝覆盖，给下一次快照使用新文件名。保留终端日志、实际执行 commit/配置和未完成轮次；返回这两个文件。完整原始语料留在用户主机，诊断确有需要时再通过已有私有归档方式提供。
