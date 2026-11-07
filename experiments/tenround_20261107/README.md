# 单方法、十轮实验清单

状态（2026-11-07）：**代码与清单已完成；新实验尚未启动。** 旧 GPU 任务和调度器已停止，已有结果、检查点和模型数据保留。

- [机器可读实验清单](experiment_list.json)
- [完整 CSV 表](experiment_list.csv)
- [验证记录](validation.json)
- [Python 调度入口](../../scripts/run_experiment_matrix.py)

## 训练任务

每个训练 job 只执行一个方法，运行 round 1–10。共同配置包含可选方法清单，但 worker 必须明确选定其中一个；各方法分别从原始权重开始。

| 模型／训练域 | 方法 | 每个方法轮数 | 状态 |
|---|---|---:|---|
| Llama-3.1-8B-Instruct／MBPP | Plain、SSD、SPECTRUM | 10 | 3 个可执行任务 |
| DeepSeek-Coder-6.7B-Instruct／MBPP | Plain、SSD、SPECTRUM | 10 | 3 个可执行任务 |
| Qwen2.5-7B-Instruct／数学→MATH500 | Plain、SSD、SPECTRUM | 10 | 3 个可执行任务 |
| Qwen2.5-7B-Instruct／QA→MMLU-Pro | Plain、SSD、SPECTRUM | 10 | 3 个可执行任务 |
| Qwen2.5-Coder-7B-Instruct／MBPP | Plain、SSD、SPECTRUM | 10 | 按用户要求复用历史来源，不自动重跑 |
| Qwen3.8-27B／ARC-AGI-3 | Plain、SSD、SPECTRUM | 10 | 原生长上下文和成功校准轨迹尚未具备 |

## 72 项的含义

18 个训练条目（12 可执行、3 待历史来源绑定、3 ARC 阻塞）＋6 个训练域 Base 条目＋48 个代码迁移评测条目，共 72 项。其中 52 项具备可执行的完整依赖链；另外 20 项受阻塞条件或历史检查点依赖限制。

Base 是第 0 轮原始模型评测，每个模型／训练域只计算一次。HumanEval+、APPS Intro、CodeContests、LiveCodeBench 为冻结检查点评测：分别评原始模型以及每种方法的第十轮模型，不在测试集上训练。清单中 `rounds=0` 表示没有训练轮次，`source_round=10` 指定需要读取的学生检查点。

Qwen/MBPP 的历史结果报告不代表本机已经拥有所有相同协议的第十轮权重。对应条目为 `external_required`，相关学生迁移评测要等待实际检查点及来源记录。旧结果不自动算作本次协议的成功回执。

## 本地生成与执行

公开 JSON 是不含私有随机种子和主机路径的实验规格。实际运行 manifest 由 `plan` 在本机生成，绑定已准备的数据、私有配置、源代码哈希和输出位置。

```bash
# 在已安装项目依赖的 Linux 环境运行。
# SOURCE_ROOT 是保留了既有本地准备文件的 checkout；OUTPUT 必须是新的空目录。
python scripts/run_experiment_matrix.py plan --source-root "$SOURCE_ROOT" --output "$OUTPUT"
python scripts/run_experiment_matrix.py check --manifest "$OUTPUT/experiment_list.json"
python scripts/run_experiment_matrix.py list --manifest "$OUTPUT/experiment_list.json"

# 先执行共同 Base，再执行一个方法；自动队列也会遵守此依赖。
CUDA_VISIBLE_DEVICES=0 python scripts/run_experiment_matrix.py run \
  --manifest "$OUTPUT/experiment_list.json" --job code.llama8b.mbpp.base
CUDA_VISIBLE_DEVICES=0 python scripts/run_experiment_matrix.py run \
  --manifest "$OUTPUT/experiment_list.json" --job code.llama8b.mbpp.plain

# 显式启动；默认每卡一个任务，可选择每卡最多两个。
python scripts/run_experiment_matrix.py queue --manifest "$OUTPUT/experiment_list.json" \
  --gpus 0,1 --limit-mib 85000 --workers-per-gpu 2
```

本次 planner 读取既有准备布局：`runs/crossfamily_code_v1_20261107/plan/configs/`、`runs/private/full_20261106/text_{math,qa}.json`、`data/final/benchmark_registry.json`。输入不齐全会报错，不会隐式下载或启动 GPU。私有随机化信息和执行 manifest 留在本机。

加载任务间隔 90 秒；必须满足依赖、每卡任务数和显存余量检查。达到 85,000 MiB 时仅中断该卡最新加入的任务，并保留生成分片。SIGINT/SIGTERM 会回收调度器的运行中子进程。文件锁防止重复调度；成功回执校验原生结果与检查点哈希，不能用日志或进程退出代替完成。

## 验证和结果更新

64 项 CPU 回归测试通过；实际数学/QA 准备数据绑定、配置与源码哈希检查通过。独立代码复核发现的问题已修正。这些是软件验证，不是原生 GPU 训练结果。只有任务原生完成标记、结果和检查点验证通过后，才发布对应实验结果。
