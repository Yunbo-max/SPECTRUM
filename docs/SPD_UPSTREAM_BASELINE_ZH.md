# 上游 SPD 五轮 baseline：c48

来源：[gh540-svg/SPD](https://github.com/gh540-svg/SPD/tree/caa408c699f13c209a6484f626939cf3a3dcbe18)，固定提交 `caa408c699f13c209a6484f626939cf3a3dcbe18`。
独立方法名 `spd_upstream`；旧 `c45/spd_hard` 和 c00–c47 的含义保持不变。新增后共49个case。

## 方法身份

直接使用未改动的上游 `utils.py`（保存为 `src/improving/_spd_upstream_utils.py`）：收集原生 K/V 投影输出的梯度，float32 中减去全体 token 梯度均值，做 SVD，保留一半 K/V 维度，再计算 `P = V_r V_r^T`。干预目标为中间层和最后层的 K、V；每一轮重新估计。

上游源码默认 `calibration_source=aligned`，随后对代码任务自动切换为 `mbpp_solutions`，只在测试断言的 token 上计算 next-token CE。c48 保留这一实际默认行为。校准文本使用固定50个 calibration task 的原题、测试断言和参考程序，格式为上游的 `Instruction: ... Your code should pass these tests: ... Code: ...`；只有断言字符区间内完整包含的token进入loss。当前prepared MBPP保存独立的断言行；适配器拒绝不支持的多行/setup测试格式，不静默扩大标签范围。这包含额外校准断言信息，与 SPECTRUM completion-only 校准并非完全相同的信息/损失控制，结果表须披露。

上游为单次蒸馏，本接入版本是**五轮、统一实验协议的适配**，并非逐项复刻论文全部设置：

- Qwen2.5-Coder-1.5B-Instruct，MBPP291/50/30/500；训练seed43。
- 每轮每题16个原始生成样本；base及每轮对500题每题评64个样本；生成上限512。
- 当前学生产生下一轮语料，普通LoRA SFT，保留全部原始输出；训练、采样和正式评测继承主线设置。
- 上游投影采用 activation hooks；本机用等价的 K/V 线性权重及bias折叠以复用现有高效生成路径，保留数值一致性测试。半精度下不保证逐bit相同。
- 投影只在生成和声明的干预诊断期间生效，SFT和native评测前恢复原权重。
- 校准上限4096，提前拒绝超长文本；不采用上游默认256的静默截断。校准成本单列。
- 原上游生成清理、数据划分、单样本评测和训练epoch配方未照搬；这里保持SPECTRUM主线公平预算。上游“SSD”名称也不等于本仓库的SSD解码配方。

## 运行（Linux / WSL）

使用装有项目依赖的 Python，在更新后的SPECTRUM checkout中执行。MODEL_ROOT按HF命名布局存放已核验完整模型；DATA_ROOT指向已准备的MBPP四个split。

```bash
python scripts/rebuttal_cases/c48.py plan \
  --root runs/spd_upstream_r5_v1 \
  --data-root data/iclr2027_rebuttal_v2/mbpp \
  --model-root models --profile 24gb --eval-backend bwrap

# 展示冻结后的命令，不执行训练
python scripts/rebuttal_cases/c48.py run --root runs/spd_upstream_r5_v1

# 完成当前主机显存/运行资格检查后，显式启动一个任务
CUDA_VISIBLE_DEVICES=0 python scripts/rebuttal_cases/c48.py run \
  --root runs/spd_upstream_r5_v1 --execute

python scripts/rebuttal_cases/c48.py status \
  --root runs/spd_upstream_r5_v1 --verify-hashes
```

每轮产物位于 `ROOT/c48/run/spd_upstream/round_1` 至 `round_5`；其中保留模型、生成、评分、上游校准来源和投影。恢复必须使用同一代码、模型、数据和配置。profile并非GPU容量验收。

## 上游代码和归属

未改动的上游工具保存在主包中，使现有源码指纹覆盖它。上游README及固定来源记录位于 `third_party/spd/`。上游README声明代码采用MIT许可；该提交没有单独的LICENSE文件，本仓库不补造版权人或许可文本。请引用：Hao et al., *Self-Policy Distillation via Capability-Selective Subspace Projection*, arXiv:2605.22675 (2026)。

独立复核发现的aligned自动路由问题已修正，回归测试直接对照上游assertion-only梯度收集和投影。当前交付为软件接入；CPU小模型五轮测试不能作为1.5B正式实验结果或显存资格证明。当前runner对1.5B继承H100探测的生成batch三元组(64,38,2432)，不受profile名字暗示的24GB限制；应按冻结配置检查实际空闲显存后再运行。
