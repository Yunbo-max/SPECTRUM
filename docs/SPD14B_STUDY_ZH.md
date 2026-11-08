# SPD14B 三域实验准备记录

模型为本地 Qwen2.5-14B-Instruct，三域分别独立运行，每域 5 轮、每轮 2 epochs、生成上限 4096 new tokens、batch size 2。4096 是新增生成 token 上限，不是输入加输出的总上下文上限。数据准备、实际小样本推理和正式依赖环境的训练显存测试已通过；完整五轮效果仍须以实际输出为准。

## 数据来源与隔离

| 域 | TRAIN / CAL / DEV | 独立评测 |
|---|---|---|
| Math | PRM800K 发布的 math_splits/train 池，1024 / 50 / 64 | 官方 MATH-500 全部 500 题 |
| QA | cais/mmlu auxiliary_train，1024 / 50 / 64 | GPQA Diamond 全部 198 题 |
| Safety | UWNSL/SafeChain，按四类 label 确定性分层，1024 / 50 / 64 | 同源但未参与训练或校准的 500 条 |

PRM800K 的发布 train 池可能包含原始 MATH/test 路径的记录；原始路径名称不等于本实验 heldout 身份。隔离依据是 PRM 发布池、固定 MATH-500 评测集合与规范化题目交集检查。Math 和 QA 的训练、校准、开发数据复用先前准备好的外部快照，逐文件核验旧 manifest 中 SHA256 和记录数后保留旧分配，各取原 64 条 CAL 的前 50 条，余下 14 条不使用。QA 还对全部 GPQA main/extended 问题执行训练池排除检查；完整原始 CSV 保留可用，主要评测分母仍固定为 Diamond 198。

所有实际输出同时检查域内和跨域的 NFKC Unicode 规范化加空白折叠后的精确题目重复。当前输出没有交集；这不宣称已消除语义近重复或模型预训练污染。SafeChain 原始 40000 条在该规则下均唯一，选用 1638 条，其余 38362 条未使用。

Math CAL loss 的字符区间只标记参考解答最终 boxed 表达式的内容，保留嵌套 LaTeX 花括号；QA CAL 只标记正确选项字母。区间采用 reference 字符串中的左闭右开 Unicode 字符偏移。训练使用何种模型生成输出以及各轮算法行为由独立 runner 决定；本文不把参考答案写入评测 prompt。

SafeChain 原始 response 完整保留，包括 think 分隔符、空白及长回答；没有截断或重写。CAL 的关键 safety token 区间目前留空，等待只针对 CAL 的模型标注。模型选中的区间表示模型判断的安全相关性，不是正确性真值、安全金标准或独立效果验证。SafeChain label 保留原始四类标签，不把类别当成回复文本答案。评测的结果判定必须单独报告实际使用的评分器及局限。

## 已完成的输入准备

输入根目录为 `/root/ai-assets/spd14b-20261108`，模型目录为 `/root/ai-assets/models/qwen25-14b-instruct`。模型及 MATH-500、GPQA、SafeChain 下载已完成；精确 revision 和文件身份记录在 `assets.json`。本次数据脚本逐个验证原始数据文件大小及 Git blob 或 LFS SHA256，并在 `prepared/manifest.json` 记录实际 SHA256、输出数量、外部快照出处、排除统计、构建脚本身份及分层计数。原始数据与模型权重不提交到 Git。

准备入口为 `scripts/prepare_spd14b_data.py`，默认使用 `/root/spectrum-prep-20261106/data/multidomain/{math,qa}_full_20261106` 外部训练快照，输出 `prepared/{math,qa,safety}/{train,calibration,validation,eval}.jsonl`。脚本不会下载、加载模型或启动 GPU；遇到内容不同的已有输出会拒绝覆盖。`tests/test_spd14b_data.py` 的四个 CPU 测试已通过，另已核验全部 12 个文件哈希/数量、100 条 Math/QA CAL 区间，以及 1638 条 Safety 参考文本与 parquet 原文逐条相等。

## Tokenizer-only 长度检查

`token_lengths.json` 使用下载模型的本地 tokenizer、实际 `render_prompt` 模板和独立编码的 reference，并计入一个 EOS；不加载权重、不执行 GPU。下表为 prompt + reference + EOS 的 p95 / 最大 token 数。

| 域 | TRAIN | CAL | DEV | EVAL |
|---|---:|---:|---:|---:|
| Math | 756 / 2684 | 789 / 1154 | 708 / 1186 | 767 / 1579 |
| QA | 595 / 965 | 707 / 873 | 611 / 1018 | 504 / 2846 |
| Safety | 1898 / 16409 | 2085 / 3346 | 1699 / 1823 | 1875 / 4441 |

16384 与 32768 总上下文都能容纳全部未截断 CAL。Safety TRAIN 中有 2 条完整参考超过 16384，总长度最大 16409；如果实际使用全部原始参考，32768 才覆盖全部这些样本。此结论是 token 长度约束，不是 GPU 显存承诺。全部准备输入中 prompt + 4096 新生成 token 的最大值为 6934（GPQA）；实际各轮生成和训练应继续记录长度及截断情况。

## 运行状态与下一步

本次只读主机检查时，GPU 0 为 78 / 97887 MiB、利用率 0%；GPU 1 约 15907 / 97887 MiB、利用率约 48%。WSL `nvidia-smi` 没有列出进程，WSL 进程列表也没有模型任务，不能据此认定 Windows 侧或其他环境没有 GPU 活动。WSL 数据盘当时可用约 213 GiB。精确时间及原始检查输出保存在 token 长度 receipt；资源状态随时可能变化。

已经执行：14B 数学和 QA 各两条推理及真实评分；Safety 两条 CAL 的模型关键片段标注和精确位置验证；正式依赖环境的 5176-token、batch=2、2 epochs 合成训练容量测试。该容量测试覆盖实际 TRAIN 最大输入 1080 加最大生成 4096，峰值 allocated 50.34 GiB、reserved 54.58 GiB，2 个 optimizer steps，零截断且梯度有限。合成测试不是科学结果。早先 8192-token 测试使用不同依赖环境，已明确标记不构成正式环境资格证据。

正式环境为 `/root/ai-venvs/spectrum/bin/python`，Python 3.12.3、Torch 2.7.1+cu128、Transformers 4.51.3、PEFT 0.15.2。49 项联合 CPU 检查通过。三域的一轮、两条样本完整 smoke 运行与正式五轮输出分别保存；正式效果尚未完成。

并发上限暂定两组，每卡一组，进程分配上限 60 GiB、启动时保留至少 12 GiB 空闲，第三域排队。GPU 1 的既有约 15.5 GiB 占用计入整卡预算。PyTorch 分配上限不能约束其他项目增长，外层运行器还需监测整卡占用并只终止自己的超限作业。不要为了填满显存而同卡启动两组训练。

## 逐组运行入口

每条命令只运行一个域、一种方法。初始模型评测后执行五轮 SPD；`--smoke` 改为每个 split 两条、一轮，但训练仍为 2 epochs。训练学习率 1e-5、LoRA rank/alpha=8、梯度累积 1、普通全序列 SFT loss；每题每阶段采样一个输出。

```bash
CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 /root/ai-venvs/spectrum/bin/python scripts/run_spd14b.py --domain math --memory-budget-gib 60 --grader-root /root/spectrum-prep-20261106/data/multidomain/math_full_20261106/sources/prm800k --output-dir /root/ai-assets/spd14b-20261108/formal/math
CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 /root/ai-venvs/spectrum/bin/python scripts/run_spd14b.py --domain qa --memory-budget-gib 60 --output-dir /root/ai-assets/spd14b-20261108/formal/qa
# 等一张卡完成前一组后，在该卡运行 Safety；不要同时把第三组塞入同一张卡。
CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 /root/ai-venvs/spectrum/bin/python scripts/run_spd14b.py --domain safety --memory-budget-gib 60 --output-dir /root/ai-assets/spd14b-20261108/formal/safety
```

这些是内层命令，应由有时间上限、日志与退出记录的外层进程执行。断点续跑需 `--resume`，源码、依赖、初始权重、数据和参数必须一致。旧轮检查点只在后继训练及评测封存后清理；原始生成、评分和训练记录保留。模型标注有至多两次格式修复机会，保留所有原始尝试，失败时不会用全部 tokens 或其他样本替代。
