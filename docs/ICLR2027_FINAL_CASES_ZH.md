# SPECTRUM 最终 rebuttal 实验与独立运行指南

更新：2026-11-07。交付状态：**generated_unexecuted，等待 Local 软件验收和真实主机资格检查**。
本轮完成源码、实验设计、问题映射和 GitHub 集成；没有启动新的模型训练、生成、评测或项目测试。

入口：[48-case 清单](../experiments/iclr2027_rebuttal/cases.json)、
[逐审稿人对应表](ICLR2027_REVIEWER_COVERAGE_ZH.md)、
[英文逐点回复草稿](ICLR2027_REVIEWER_RESPONSES.md)、
[机器可读映射](../experiments/iclr2027_rebuttal/reviewer_case_mapping.json)、
[本轮交接](../rounds/20261107-final-rebuttal/WEB_HANDOFF.md)。

## 1. 先确认实验范围

48 个 case 是**完整证据账本**，包含历史审计、已有结果的严格恢复、只评估不训练的对照、人工标注和需要补跑的训练，
不是要求从头启动 48 次训练。c00–c36 延续 `d033641` 的编号；c37–c47 只追加，不替换历史编号。
另一条 `6f4d2a0` 分支的 27 个 case 使用不同含义，不能混用编号。
当前 main 原有的 72-case 十轮跨领域队列保留，不是本轮 rebuttal 默认执行队列。

| 协议 | 原论文主线 | Learned 扩展 |
|---|---|---|
| 模型与训练轮次 | Qwen2.5-Coder-1.5B-Instruct，5 轮；另有 DeepSeek6.7B / Qwen3B 同协议复现 | Qwen2.5-Coder-7B-Instruct，10 轮 |
| 长度 | prompt≤1024，生成≤512，SFT≤1536 | prompt≤2048，生成≤4096，SFT≤6144；保留全部 completion targets |
| 训练／评测采样 | 每题每轮 16 个原始训练输出；完整 MBPP500 每题 64 个评测输出 | 相同采样数，长度不同，分别成表 |
| 数据 | MBPP291 train / 50 calibration / 30 development / 500 test，data seed42 | 相同划分；Learned 前40 fit、后10 guard |
| SFT | 普通 LoRA，rank8、alpha8、lr1e-5、loss_scope=all；全量原始输出 | 相同；没有 token loss weighting，没有学习 LoRA update scale |
| 主要效果证据 | 原 Fixed SPECTRUM 与 Plain、SSD、SPD-hard、方向与强度控制 | Fixed40 / Learned40+10 / Fixed50，再对比 Plain、SSD、decay、adaptive |

Learned 学的是每个目标 K/V 模块的完整谱方向增益 `U diag(a) Uᵀ`，仅对数值相等的特征值共享增益。
40 个参考答案用于几何和拟合，10 个只做最终 guard veto；guard 仍属于额外监督信息。
临时算子只用于生成，SFT 与 native evaluation 前恢复原权重。普通 LoRA 合并采用完整更新，隐含 update scale=1。
Fixed40 与 Learned40+10 对齐 fit 子集，但不声称总信息、总标注或校准计算完全相等。

## 2. 执行顺序与验收问题

| 组 | Case | 要回答的具体问题 | 执行决策 |
|---|---|---|---|
| 先审计 | c00、c25 | 哪些结果真的存在，协议和状态是什么 | 只读；审计 CSV 不能替代原始产物 |
| 主要基线与种子 | c36/c01、c06/c07、c08/c09，c30、c45 | 原 Fixed 是否可复现，SSD/SPD 与 Plain 的完整准确率—多样性比较 | 先验身份和完整性；已完整者复用，失败／缺失者补齐 |
| 核心机制 | c02、c03、c04，对照 c01 | 改变方向、等强度各向同性、等强度混合之后优势是否仍存在 | 优先补五轮；一轮旧结果不能填五轮末轮 |
| 信息与预算公平性 | c05、c27；c10/c11/c44 | 同50答案 replay、Fixed40/50，以及统一 token 预算下的 Plain/Fixed/replay | c10/c11/c44 每轮同7.2M shifted target tokens；实际成本另报 |
| 外部有效性 | c14/c15；c16/c17；c18/c19 | 另一模型家族、冻结迁移、模型规模 | 优先真实跨家族配对；3B 是额外规模证据 |
| 超参数和干预位置 | c12/c13、c23/c24、c31 | τ、middle/final layer、是否必须每轮更新几何 | 五轮同协议；既有7B一轮τ扫描只作补充 |
| 简单解码替代 | c20/c21/c22/c46；c28/c29/c47；c30 | evaluation decoder 与 training synthesis 分开；单独温度和 top-p | 前四项只评估；后三项改变训练生成；SSD 用真实训练谱系 |
| 简单模型替代 | c32/c33/c34/c35 | 与初始模型做0.5/0.75全权重插值是否足够 | 冻结 Plain/Fixed r5，不新增SFT，不覆盖源模型 |
| 语义审查 | c26 | AST 的变化是否对应算法家族变化 | 先盲标 packet，再人工标注／复核，最后独立汇总 |
| Learned 长期扩展 | c37–c43 | 学增益相对固定、衰减、自适应是否值得 | 独立7B十轮表；保留旧失败和未完成状态 |

**c29 与 c30 的去重：** 当前仓库的 SSD 实现通过训练生成配方 `T=1.5, top-p=.8, top-k=20` 实现；
c29 是相同配方的 Plain 命名控制，不能把两者数作两种独立算法。
若有同协议、完整合格的 c30 轨迹，可以避免重复训练 c29；c22 则是另一件事——仅改变评测解码。

Known Y4 摘要提出 weight interpolation **or** KL-to-initial，本轮选择完整实现插值对照。
专门的训练期 KL-to-initial 正则没有实现，也不会把 Learned 的 probe KL 诊断称为这一基线。
原 review 全文尚未恢复；如逐字原文明确要求两者，需另立新 case，不能修改已冻结 case 的语义。

## 3. 历史证据的使用边界

[旧审计](../research/audit-20261107/REBUTTAL_GAPS.md)来自 Local 记录，本轮 Web 未挂载其原始 GPU 运行目录。
审计自身存在概括与细项不一致，例如“多 seed 全完成”不能推导 Fixed 三个种子都完整，
“qwen/llama 全完成”也不能覆盖后面列出的 Llama Learned base-only 状态。
采用最保守的逐 arm、逐轮记录；最终以原始 manifest、完整样本、checkpoint 与 hash 为准。

- 原1.5B Plain 的三个 seed 是历史候选；Fixed seed44 有失败记录，seed45 尚待明确核对。
- 7B Learned 十轮和 decay0.8 十轮有历史完成摘要；no-decay 与 entropy-adaptive 记录为 r8/10。
- τ0.6 的 base 阶段失败属于运行失败，不能填成“方法无效”或零收益。
- 7B high-k 一轮四臂不含 random/matched-blend；1.5B 单轮 isotropic 的参考 τ 还存在混杂。
- 历史 final-eval@16、eval@128、长度512/4096、五轮/十轮、不同抽取器或不同 verifier，均不得替代新表中的指定单元。
- `D4_cond_cov` 是旧归一化字段，不能直接当作本轮的正确样本条件 richness D4。

新代码不会接管历史运行目录。恢复旧 partial 时，保留其原 checkout、依赖、运行配置和源指纹。
不能删除 manifest、复制一个新 complete.json 或换新代码强行 resume。
历史缺少检查点／来源证明时，登记 unavailable；必要的重建必须放新目录，并用新尝试记录解释原因。
历史64次评测若与新核验协议不兼容，应保留原表，单独安排保留 checkpoint 的一致评估，或重建明确的新 case；不能直接混算。

## Download datasets and models

以下命令供 Local 在原生执行主机上运行。本次未下载数据或模型。先复用已经核验一致的完整快照。
不要改变仍在运行的 Conda 环境；需要新环境时使用独立 Python3.11 环境，再安装本项目依赖：

```bash
python -m pip install -e '.[train,evalplus,test]'
```

模型、数据不可变版本见 [assets.json](../configs/final/assets.json)。

| 模型 | revision |
|---|---|
| Qwen/Qwen2.5-Coder-1.5B-Instruct | `2e1fd397ee46e1388853d2af2c993145b0f1098a` |
| Qwen/Qwen2.5-Coder-3B-Instruct | `488639f1ff808d1d3d0ba301aef8c11461451ec5` |
| Qwen/Qwen2.5-Coder-7B-Instruct | `c03e6d358207e414f1eca0bb1891e29f1db0e242` |
| deepseek-ai/deepseek-coder-6.7b-instruct | `e5d64addd26a6a1db0f9b863abf6ee3141936807` |

以下读取已有 pin，仅下载所选模型的**完整** snapshot，包含权重分片、index、tokenizer 和 config。
先选 `qwen1.5b`；需要跨家族或7B扩展时把 `selected` 改成对应 key；不要只下载 config。

```bash
python - <<'PY'
import json
from pathlib import Path
from huggingface_hub import snapshot_download
assets = json.loads(Path('configs/final/assets.json').read_text())
selected = ['qwen1.5b']  # other keys: qwen3b, qwen7b, deepseek6.7b
for key in selected:
    spec = assets['models'][key]
    snapshot_download(repo_id=spec['repo_id'], revision=spec['revision'],
                      local_dir=str(Path('models') / spec['repo_id']))
PY
```

本轮只需要 MBPP、HumanEval+ 和 APPS Intro。已有相同数据文件可直接传给 planner；
缺失时在新目录准备，使用已提交的 [data_revisions.json](../experiments/iclr2027_rebuttal/data_revisions.json)：

```bash
python scripts/prepare_iclr_benchmarks.py \
  --datasets mbpp humanevalplus apps_intro \
  --output-dir data/iclr2027_rebuttal_v2 \
  --seed 42 --calibration-size 50 --validation-size 30 --limit 200 \
  --revisions experiments/iclr2027_rebuttal/data_revisions.json
```

必须核对 MBPP 四份 JSONL 数量为291/50/30/500、HumanEval+164、APPS Intro200；跨 split 的 task ID、规范化 prompt 不重叠。
MBPP revision=`4bb6404fdc6cacfda99d4ac4205087b89d32030c`；
APPS revision=`21e74ddf8de1a21436da12e3e653065c5213e9d1`。
HumanEval+ 固定 EvalPlus0.3.1、release v0.1.10。新准备流程把完整 `HumanEvalPlus.jsonl` 和 SHA 一并封存，
不能用只有 prompt 的旧目录冒充原生扩展测试 fixture。旧 manifest 不会被静默升级，必要时使用新准备目录。
MBPP 是原500题测试，不能写成 MBPP+；APPS Intro 是适配验证协议，不能写成官方 leaderboard 分数。

## 5. 每个 case 单独计划、启动、保存

每项都有 `scripts/rebuttal_cases/cNN.py` 独立 Python 入口。通用只读列表：

```bash
python scripts/rebuttal_cases.py list
```

例如只计划、启动和检查 c02。`plan` 冻结源代码／配置／输入指纹，不加载模型；
`run` 没有 `--execute` 时只展示冻结命令。正式执行需先完成下面的软件／主机验收，并纳入 Local 的有界运行计划。

```bash
python scripts/rebuttal_cases/c02.py plan \
  --root runs/iclr2027_rebuttal_isolated_v2 \
  --data-root data/iclr2027_rebuttal_v2/mbpp --model-root models --profile 24gb
python scripts/rebuttal_cases/c02.py run --root runs/iclr2027_rebuttal_isolated_v2
python scripts/rebuttal_cases/c02.py run --root runs/iclr2027_rebuttal_isolated_v2 --execute
python scripts/rebuttal_cases/c02.py status --root runs/iclr2027_rebuttal_isolated_v2 --verify-hashes
```

其写入位置固定为 `ROOT/c02/plan.json`、`config.json`、`run/`、`attempts/<UTC时间-唯一ID>/stdout.log`、
`stderr.log`、`started.json`、`exit.json` 和验收后的 `case_receipt.json`。
`run/` 内 base 和每轮模型／原始生成／native verification／metrics／resource receipts 分开保存。
每个 case 有排他锁；不同 case 不共用可写输出目录。执行前后都核对已冻结的源码和依赖。
发生错误保留日志与已完成产物；相同代码、配置和输入再次运行同一 case 才属于 resume。
若这些身份变化，使用新 root，不覆盖旧 plan。

对 `historical_complete*` 的训练 case，首次重建还要明确附加 `--rerun-historical`，避免把可复用结果无意间重跑。
这个开关只允许新 root 重建，不是修改旧结果的许可。
`--profile 24gb/80gb` 是 batch 选择提示，不是显存验收报告；7B4096新增模板使用保守 batch，仍需实际测量。

### 依赖保存 checkpoint 的评估

c16/c17、c20–c22/c46、c32–c35 不会自动训练源模型。
传入真实的 source run；planner 要求 source manifest、任务快照、各轮 native seal 和模型文件一致。
缺失／pruned／未封存源会拒绝，不能把两个 source 的输出放进同一个 case root。
例如分别对 Plain 和 Fixed 做 HumanEval+：

```bash
python scripts/rebuttal_cases/c16.py plan \
  --root runs/rebuttal_transfer_plain_v2 \
  --source-run runs/iclr2027_rebuttal_isolated_v2/c36/run --source-methods plain \
  --benchmark-root data/iclr2027_rebuttal_v2
python scripts/rebuttal_cases/c16.py run --root runs/rebuttal_transfer_plain_v2 --execute
python scripts/rebuttal_cases/c16.py plan \
  --root runs/rebuttal_transfer_fixed_v2 \
  --source-run runs/iclr2027_rebuttal_isolated_v2/c01/run --source-methods spectral_soft \
  --benchmark-root data/iclr2027_rebuttal_v2
python scripts/rebuttal_cases/c16.py run --root runs/rebuttal_transfer_fixed_v2 --execute
```

APPS 换成 c17；decoder 换 c20/c21/c22/c46，仍然为每个 source 使用独立 root。
c32/c33 固定要求 Plain，c34/c35 固定要求 Fixed。各 case 的 alpha／decoder 由 catalog 固定，不能临时在测试集上挑参数。
迁移长度为该独立 transfer 协议的 prompt4096/output1024，两组一致；不等同于512-token MBPP主表。

### 语义审查

```bash
python scripts/rebuttal_cases/c26.py plan \
  --root runs/iclr2027_rebuttal_isolated_v2 \
  --task-file data/iclr2027_rebuttal_v2/mbpp/eval.jsonl \
  --evidence plain=/absolute/plain/round_5/evaluation.verified.jsonl \
  --evidence spectral_soft=/absolute/fixed/round_5/evaluation.verified.jsonl
python scripts/rebuttal_cases/c26.py run --root runs/iclr2027_rebuttal_isolated_v2 --execute
```

先按题目ID预选40题，再从各组正确程序中最多取8个。给标注者的文件只有 `annotation_packet.jsonl`，
不能发 `private_method_key.jsonl`、私有随机盐或包含 method 的 coverage 表。
建议两名独立标注者按每道题共享的算法家族命名规范标注，记录分歧，由独立复核形成最终文件；
不能把 AST hash 当人工策略标签。汇总输入每行需要 `anonymous_id`、`human_strategy_class`（不确定填null）、
`human_reviewed=true`、非空 `annotator_id`。保存最终标签到新文件后：

```bash
python scripts/rebuttal_semantic_summary.py \
  --packet-dir runs/iclr2027_rebuttal_isolated_v2/c26/run \
  --annotations /absolute/adjudicated_labels.jsonl \
  --output-dir runs/rebuttal_semantic_summary_v2
```

它报告预选40题中的 sampled-correct human D4、共同eligible任务和分母，未标注保持missing。
不会生成全500题的 semantic pass@64 或“已证明算法多样性”结论。人工工作未完成时，c26 只算 packet ready。

## 6. 诊断、统计和计算开销

新增训练 case 在第1/5轮记录 DEV30 三态；7B十轮再加第10轮：pre-native、pre-spectral、post-native。
使用相同30题、每题64次采样及同一评测解码，不参与 checkpoint 选择、参数调优或训练样本筛选。
Plain/SSD 的 spectral 状态为 identity 对照；该三态定义不测量 SSD 特殊解码的全部效应。
Learned 每轮还记录同一40fit/10guard的 SFT 前后 NLL。已恢复历史 `target_mask` 修复，避免把未处理 batch 直接传给 NLL。
训练后断点不能用学生重造教师的 pre-SFT 证据；缺失将明确失败。

每轮另有 train-prompt8×128 的原生前缀 raw-logit forward KL 观测，连同实际算子谱、Frobenius 位移、K/V权重与bias变化保存。
此 KL 是完整词表、有限前缀、采样变换之前的诊断，不是 trajectory KL，也不是 equal-output-KL 对照。
同一个初始模型的 round1 方向对照最接近 common-state comparison；后续各学生不同不能直接解释成纯几何因果效应。
谱非扩张／可逆性本身不能证明整个 transformer 的正确解支持或多轮稳定性。

主表至少报告 pass@1、pass@16、pass@64、C64、正确样本条件D4、各轮曲线以及共同eligible分母。
paired task bootstrap 使用2000次重采样；三组独立训练 seed 的 mean/SD 单独报告，
不能用500题或五轮之间的波动代替训练种子不确定性。小eligible组、负 APPS、较低 pass@1、SSD占优的点全部保留。

```bash
python scripts/rebuttal_case_analysis.py \
  --root runs/iclr2027_rebuttal_isolated_v2 --output-dir runs/rebuttal_pairwise_v2
python scripts/report_transfer_gap.py \
  --run-dir runs/iclr2027_rebuttal_isolated_v2/c40/run \
  --output runs/rebuttal_c40_transfer_gap_v2.json
python scripts/rebuttal_cases.py report --root runs/iclr2027_rebuttal_isolated_v2 --verify-hashes
```

旧结果使用 `--input c01=/absolute/spectral_soft/round_5/evaluation.metrics.json` 等显式来源；
分析器只接纳满足其完整身份合同的输入。不能用审计表格或截屏替代原始文件。
无完整 provenance 的老结果保持 unqualified / supplementary，不按名称猜测。

每轮7.2M是共同的**目标下限**，计数为因果移位后、实际进入loss的 supervised target positions，不是16条候选或解码token数。
停止发生在完整样本边界；实际数允许小于一条最长编码样本的有限超额，三组都必须报告实际数和 overshoot，不能声称逐token完全相等。
replay的50条参考答案包括在同一预算里；完整原始语料超过预算时必须拒绝，不能丢掉样本或按正确性筛选。
若需提高共同预算，应为 c10/c11/c44 一起设立新的已声明版本，不能只改一组。
资源文件分别记录 generation、calibration、SFT、evaluation、诊断；标注信息量、实际token和wall time分别列出。
没有可靠FLOP测量时写 unavailable；不能把同token称作同总FLOPs。

## 7. Local 软件验收、原生资格与有界调度

Web 只做源码检查。本轮新增或相关的 Local 验收命令如下；这些命令**尚未执行**，不能引用 README 中旧版64项CPU通过来代替：

```bash
python -m pytest -q \
  tests/test_rebuttal_cases.py tests/test_rebuttal_analysis_integrity.py \
  tests/test_operator_probe.py tests/test_transfer_diagnostics.py \
  tests/test_transfer_gap_report.py tests/test_native_humaneval_fixture.py \
  tests/test_rebuttal_semantic_summary.py tests/test_pipeline.py \
  tests/test_training.py tests/test_learned_gains.py tests/test_gain_pipeline.py \
  tests/test_final_core.py tests/test_final_data.py tests/test_tenround_selection.py
python scripts/check_native_sandbox.py --output runs/private/rebuttal_native_qualification.json
```

原生评分使用既有 bubblewrap／libseccomp 隔离路径，见 [NATIVE_SCORING.md](NATIVE_SCORING.md)。
不自动改成 Docker 或 allow_unsafe_local。资格不通过时停止对应评分，保留错误记录。
7B Learned 可先在**单独qualification目录**运行已有真实校准资格命令（仍需 Local host准入）：

```bash
python scripts/qualify_learned_gains.py \
  --config runs/iclr2027_rebuttal_isolated_v2/c40/config.json \
  --output-dir runs/rebuttal_qualification_c40_v2
```

它不执行SFT或benchmark，不能证明完整十轮显存足够。Local 还需在原生模型／最大声明长度上测量SFT和评测实际资源。
目前 SSH别名、GPU型号、显存、并发租约和剩余预算未恢复，不能预承诺运行时间或可容纳并发数。
先读取实际进程与占用，再按现有 research-autopilot `run_harness.py` 的 inspect-host → freeze → execute 流程，
把单个 `cNN.py run --execute` 作为前台job，填入实际资源封套、有限时长／轮次和已核验输入。
不能把本指南的命令当作已存在的 approved plan digest，也不能重启未知 watcher。
本轮用户首先确认最终实验；未创建定时或后台自动运行。

## 8. 结果返回和完成标准

```bash
python scripts/collect_learned_gains.py \
  --run-dir runs/iclr2027_rebuttal_isolated_v2 \
  --output runs/rebuttal_receipts_v2_snapshot01.zip
```

小包仅汇总已有JSON收据，不含模型、原始程序、完整样本或私有盲标key。
原生研究验收仍需保留可定位的完整输入、raw train/eval JSONL、verified JSONL、checkpoint、source/config、attempt logs及其hash。
如果汇总包缺少必须的 raw 证据，不能宣称实验已验证。

完成一项需同时满足：固定计划、实际正常退出、完整原生任务和64样本计数、所有封存文件hash正确、
source/checkpoint/decoder/数据身份匹配，并有可复核的结果。只存在 config、日志尾部、模型文件或 complete.json 名称都不够。
失败、取消、identity fallback、缺失值、未完轮次、未完成人工标签各自保留；不填零，不删除，不写成通过。
当证据齐备后填入英文回复的明确槽位；结论由真实结果决定，不预先保证谱方向必要性、全面胜过SSD或长期无坍缩。
