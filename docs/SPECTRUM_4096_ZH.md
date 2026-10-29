# SPECTRUM：4096-token 长度预算修订，2026-10-29

状态：**generated_unexecuted**。本轮交付代码、配置和源代码审查；没有运行项目测试、下载模型、训练或评测。GPU容量、实际截断率和效果待用户执行主机验证。

## 本轮先跑什么

只改变现有 Qwen2.5-Coder-7B-Instruct / MBPP 十轮对比的长度预算。Plain 与 SPECTRUM 都从同一原始模型开始，各十轮；训练291题，每题16个原始输出；固定参考50题、开发30题；测试500题，每题64个输出，保留初始和每轮指标。

| 项目 | 旧配置 | 新配置 |
|---|---:|---:|
| 生成上限（训练与测试） | 512 | 4096 |
| 提示词上限 | 2048 | 2048 |
| SFT 总序列上限 | 1536 | 6144 |
| SFT 再截断 | 允许且记录 | 发现即停止，不丢弃样本继续训练 |
| 参考答案校准上限 | 1536 | 1536 |

新配置：

- `configs/spectrum_7b/spectrum_7b_r10_plain_4096.yaml`
- `configs/spectrum_7b/spectrum_7b_r10_spectral_4096.yaml`

温度、top-p、样本数、LoRA、学习率、epoch、loss_scope 和 tau 保持原十轮配置。**本轮不启用 tau 衰减**，以免同时改变两个因素。全部原始回答仍进入训练，不增加正确性/长度过滤，也不对截断回答伪造 EOS。校准使用原始参考答案，不需要随合成回答扩展到6144。

新目录分别以 `plain_7b_r10_4096` 和 `spectral_soft_7b_r10_4096` 结尾。旧512-token配置和历史qz任务载荷保留；不在旧目录上 resume，不把新评测结果接到旧十轮曲线上。`spectrum_7b_r10.yaml` 是另一个旧eval16配置，不能与eval64配对入口混用。`run_spectrum_all.sh` 是历史tau扫描，不是本轮入口。

## 模型、数据与执行

使用实际GPU主机的现有环境和已有完整模型：
`/inspire/hdd/global_public/public_models/Qwen/Qwen2.5-Coder-7B-Instruct`。
数据为仓库根目录下的 `data/mbpp/{train,calibration,validation,eval}.jsonl`。
先核对实际路径、模型分片、数据划分和运行身份；原始本地模型文件指纹由现有pipeline记录。

复用已核验数据，不为新长度预算重新随机划分。若尚无准备好的MBPP，可在已有代码环境中运行原有准备入口：

```bash
python -m improving.cli prepare --dataset mbpp --output-dir data/mbpp --revision 4bb6404fdc6cacfda99d4ac4205087b89d32030c
```

若本地模型路径不存在，可使用仓库已固定的官方输入版本下载到一个新的缓存目录，并在运行前绑定配置里的实际路径；不要替换使用中的模型目录：

```bash
hf download Qwen/Qwen2.5-Coder-7B-Instruct --revision c03e6d358207e414f1eca0bb1891e29f1db0e242 --local-dir models/qwen25-coder-7b-pinned
```

以下命令属于用户的实际执行主机，先通过现有本地主机执行流程做软件与资源资格验证。Web没有运行这些命令：

```bash
python -m pytest tests/test_full_completion_targets.py tests/test_final_core.py tests/test_pipeline.py -q
python -m improving.cli validate --config configs/spectrum_7b/spectrum_7b_r10_plain_4096.yaml
python -m improving.cli validate --config configs/spectrum_7b/spectrum_7b_r10_spectral_4096.yaml
bash scripts/run_spectrum_r10_4096.sh plain
bash scripts/run_spectrum_r10_4096.sh spectral
```

显式 `both` 会顺序运行两臂；恢复同一新协议使用第二个参数 `--resume`。脚本不启动后台任务。新长度下推理batch8和SFT微批1的容量尚未实测；先用原生开发题检查最长样本与显存。若必须更改batch，先在新配置/目录中固定，两臂保持一致并记录解码随机性影响。不要以降低SFT长度或丢弃长回答来隐藏OOM。

当前十轮配置沿用历史 `local` 代码评测后端；它不是已通过bubblewrap资格验证的证据。训练数据不按测试结果筛选，MBPP原始测试与HumanEval+不是同一个评测协议。

## 实现和验收

`train.require_full_completion_targets: true` 有两层检查：配置需要容纳最大提示词与生成长度之和；实际编码若仍有目标截断，在LoRA更新前报错。已有旧配置默认不启用该检查，原始截断语义保持兼容。

同时修正tau衰减的诊断记录：重新估计几何时，参考soft算子和实际算子使用同一轮的tau；固定几何仍使用第一轮tau。这不会启用衰减，也不会改变本轮固定tau的生成机制。

验收不是“训练命令成功”：需核对每轮完成回执、`training_stats.json` 中零SFT截断、原始生成 `finish_reason` 与长度、原生pass@1/pass@64、正确实现覆盖，以及实际计算资源。4096仍可能发生生成长度封顶；本修订防止其后再次静默截短，不保证模型自然停止或性能恢复。

返回各臂base与round目录下的 `complete.json`、`*.metrics.json`、`*.budget.json`、`training_stats.json`、`operator_diagnostics.json`、实际配置/manifest和日志；另保留原始 `train.jsonl` / `evaluation.jsonl` 供错误分析。按真实存在的文件收集，缺失项标为缺失，不用零填充。不要公开权重、凭据或私有随机化记录。

## 当前其他实验与ARC阻碍

跨家族五轮方案仍用其原512-token主实验协议，本次不改变它或HumanEval+迁移协议。数学已用Qwen2.5-7B-Instruct/4096输出；QA用同一7B家族/2048输出，默认MMLU-Pro，GPQA仅可选。详见[代码](CROSSFAMILY_CODE.md)和[数学/QA](TEXT_TASKS.md)。

ARC是Qwen3.8-27B文本解码器，读取无损RLE网格、输出最多256tokens的JSON动作。当前推理允许32000tokens，但校准和训练只有16384。提交记录称ft09的多帧观察即使history1也约25K；这是输入预算冲突，提高动作输出上限不能解决。完整递归训练需先协调无损观察表示、历史和可承受训练上下文；本轮没有擅自改动ARC协议。SPECTRUM另需真实可重放的成功校准轨迹。详见[ARC说明](ARC_AGI3.md)。
