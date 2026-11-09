# Continual-gain 快速效果对照（cg02 vs cg03）

这份配置用于较快地检查冻结主模型下的 Math → QA 顺序学习效果。它沿用 cg02 retention 与 cg03 conflict 两个方法、相同的数据、任务顺序和配对随机流，只缩小评测样本并限制输出长度。

## 快速预算

- 模型：Qwen2.5-7B-Instruct，backbone frozen。
- 方法：cg02 retention、cg03 conflict。
- 顺序：Math → QA；每域一轮。
- 评测：MATH500 与 MMLU-Pro 各 32 题、每题 1 次。题目按难度级别或 QA 类别确定性分层抽样，两种方法共用题目和随机流。
- 生成上限：Math 1,024 tokens；QA 128 tokens。
- 校准：保留现有 54 FIT、10 guard 与控制器设置，不降低方法本身的校准预算。
- 显存：GPU1 进程预算 28 GiB，设备总显存停止线 83 GiB。

这是用于快速方向性检查的探索性 pilot；32 题和单条轨迹不足以支持强统计结论。Math 输出上限也可能截断较长推理，应在报告中按此解释结果。

## 准备、运行和汇总

在包含本次代码的 checkout 中执行：

```bash
python scripts/continual_gain_quick_pilot.py plan
python scripts/continual_gain_quick_pilot.py run --execute
python scripts/continual_gain_quick_pilot.py report
```

输出默认写入 `/mnt/c/ai/spectrum-run-artifacts/20261109/continual-gain-pilot-quick-v1/`。恢复中断运行时添加 `--resume`。每次计划使用独立且为空的输出目录，配置、抽样题目与两个 runner 的源码身份都会写入计划。

当前 100 题/域的 `continual_gain_pilot.py` 与其既有输出目录保持不变。快速配置不会自动启动；它是后续运行时使用的新预算。
