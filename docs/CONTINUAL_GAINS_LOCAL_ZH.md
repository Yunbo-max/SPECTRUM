# Continual gains：本机准备与输入修复

本轮在 `c089a2e` 的独立 WSL checkout 上准备，不修改仍在运行的 14B SPD checkout。
新方法测试 78 项、相关回归 92 项、联合数据准备测试 5 项，合计 **175 项通过**。
这不是 7B GPU 验证或科学结果。

## 联合数据问题及修复

原 Math/QA 快照各自通过哈希与域内分割校验，但联合检查发现 6 个 Math 训练侧问题
与 MMLU-Pro 评测问题相同：4 个 TRAIN、1 个 CAL、1 个 DEV。计划入口正确拒绝了输入。
`scripts/prepare_continual_data.py` 在新目录创建联合快照，使用已有私有随机种子，
从已验证的 PRM 12000 题训练池中确定性选择替代题。选择只依据题目/ID 去重，不使用答案或结果。
替代候选排除两域所有已选题目；其余记录和原 split 位置保留。

完整 MATH500 和 MMLU-Pro12032 评测文件逐字节保留。两个评测集自身共有的 5 道题也保留，
不能把跨域分数视作完全独立的题目样本。未声称解决语义近重复或预训练污染。
父 manifest、原始文件哈希、native builder 和 joint builder 身份、6 条替换审计均另行记录。
旧数据和私有随机种子没有改动。

```bash
python scripts/prepare_continual_data.py \
  --parent-root /root/spectrum-prep-20261106/data/multidomain \
  --output-root /root/ai-assets/continual-gains-20261108/prepared \
  --seed-file /root/spectrum-prep-20261106/runs/private/multidomain_seed.json
```

此命令已在本机执行。已有输出会拒绝覆盖；不要对同一目录重复执行或删掉 manifest。
两个域各保留 1024 TRAIN、64 CAL（54 FIT / 10 guard）、64 DEV。
新快照同时通过 CLI `prepared_identity` 和 runner `_prepare_inputs`，包括实际评分依赖检查。

## 本机路径与计划

- 模型：`/root/ai-assets/models/qwen25-7b-instruct`；revision `a09a35458c702b33eeacc393d103063234e8bc28`。
  四个 shard 哈希和 339 个张量索引对应关系已检查；不需重复下载。
- Math：`/root/ai-assets/continual-gains-20261108/prepared/math`。
- QA：`/root/ai-assets/continual-gains-20261108/prepared/qa`，评测是 MMLU-Pro，不是 GPQA。
- 私有 seed 文件沿用上面的旧路径，实际数值不公开。
- Python：`/root/ai-venvs/spectrum/bin/python`，不用另一套 spectrum27 环境。

首次计划应显式使用这些路径；不要把旧 manifest 绑定的相对路径直接改写为绝对路径。
以 cg03 为例：

```bash
/root/ai-venvs/spectrum/bin/python scripts/continual_gain_cases/cg03.py plan \
  --root /mnt/c/ai/spectrum-run-artifacts/20261108/continual-gains/cases \
  --model-path /root/ai-assets/models/qwen25-7b-instruct \
  --seed-file /root/spectrum-prep-20261106/runs/private/multidomain_seed.json \
  --math-data-root /root/ai-assets/continual-gains-20261108/prepared/math \
  --qa-data-root /root/ai-assets/continual-gains-20261108/prepared/qa
```

替换 wrapper 编号可分别准备 cg00–cg15；计划和不带 `--execute` 的 run 不加载模型。
优先执行 cg00–cg03；每域仍按这批新协议的一轮设置，不套用 14B SPD 的五轮两 epoch。

## 执行前尚待完成

两个 GPU 上已有 14B SPD 任务。新的 7B 全参考梯度、完整词表 KL、实际折叠/恢复和显存
资格检查尚未执行；175 个软件测试和 14B 的容量测试不能替代它。
本机另备独立 calibration-only 驱动，默认只验证计划，显式 `--execute` 才运行完整
54 FIT / 10 guard 的 Math→QA conflict 校准；它不生成完整 benchmark 或执行 SFT。
使用时须先分配 GPU 时间/显存，并通过有超时、日志和整卡内存监测的外层进程启动。

每个完整 case 有 baseline、Math、QA 三个阶段，每阶段两域各有 native/controlled：
`3 × 2 × (500 × 16 + 12032) = 120192` 条评测响应。
第一组四个 case 共 480768 条，batch=1；当前没有原生吞吐实测，不能承诺完成时间。
数学评分按发布配置仍是 local 子进程，不应声称使用了 bubblewrap 隔离。
