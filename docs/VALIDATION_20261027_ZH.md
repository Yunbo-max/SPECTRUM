# 2026-10-27：把实验结论做实

状态：`generated_unexecuted`。这是在读完 main `5b8c3f93d1c0122006d8c1c9c42379bb31f2f694`
及研究分支 `923e84ca9b92d111535ae245e137601b8856bbf8` 后制定的实验与分析补充。
本次没有启动训练、生成、评分或项目测试；没有修改历史数据、模型定义或已冻结实验。
它补充 [原40-job实验合同](FINAL_EXPERIMENTS.md)，不是另一个自动运行器。
执行顺序、下载、验收与返回记录见 [Local runbook](../LOCAL_AGENT_RUNBOOK.md)。

## 现在的证据到底支持什么

| 证据 | 可支持的结论 | 不可支持的结论 |
|---|---|---|
| 历史 MBPP 500题、n=64 单轨迹：SPECTRUM C64=11.510，Vanilla=8.506，Projection=8.388 | 有希望的正确实现丰富度信号；初始 C64=12.802，SPECTRUM保留约89.9% | 多训练重复稳定性、全指标支配、语义算法多样性 |
| 同一历史比较：pass@1分别0.4033125、0.41446875、0.41765625；pass@64分别0.726、0.704、0.702 | 收益与代价必须一起报告 | 只展示C64，宣称正确率也全面更好 |
| Oct18官方协议基座 MBPP+ 378题、greedy n=1：raw base 267/378，base与extended联合230/378 | 模型在正确协议下并非近零能力；评测纠错扎实 | SPECTRUM训练收益；与历史500题之差是单因素提取修复效果 |
| 上游sanitized对应266/378、229/378；单独修补诊断恢复267/378、230/378 | `Mbpp/635` helper被删除造成一个任务差异 | 在主结果中偷偷替换官方sanitizer；extended-only 233/378等于联合通过 |
| Oct19 LCB：持久化两次repeat、262条基座输出，未见评分文件 | 生成已部分完成；格式诊断可用 | 功能正确率、SSD增益、完整131×10比较 |
| Oct27远程记录 | 主机身份检查通过，客户端认证失败 | 当前GPU、进程状态已核验，或新实验已完成 |

历史数值来源：[既有证据](EXISTING_EVIDENCE.md)。新证据固定链接及文件身份见
[evidence inventory](../rounds/20261027-validation/evidence.json)。三种人口必须分开：
历史 MBPP500、作者 MBPP+378、作者 LCB131；本项目 adapted LCB200 又是第四个协议。

## 优先级一：完成已有强基线，先回答权重还是解码

继续研究分支已经设计的作者协议比较，不另造简单benchmark。
固定 `Qwen/Qwen3-4B-Instruct-2507` 与 `apple/SimpleSD-4B-instruct`，
LCB作者日期选择的131题，每题10次；top-p=0.8、top-k=20、min-p=0。
两个权重 × 两个温度构成以下完整表，不能只报告对SPECTRUM叙事有利的单元：

| 权重 | T=0.7 | T=1.1 |
|---|---|---|
| Base | 推荐decoder；主要端到端对照 | 解码控制 |
| SimpleSD | 解码控制 | 推荐decoder；主要端到端处理 |

主要端到端比较为 SimpleSD(1.1)−Base(0.7)；两个同温度比较分别为
SimpleSD(0.7)−Base(0.7)、SimpleSD(1.1)−Base(1.1)。同时列出每个权重的温度差，
以及两条权重差的差，作为描述性交互效应。它们区分这些具体checkpoint与decoder，
不识别训练数据、训练配方的每个因果贡献，也不代表排除了所有解码优化。

使用作者评分逻辑、prompt、提取方式、原始测试与完成级超时；保留每条raw输出、
sample ID、提取代码、结果和原因。主要正确率为pass@1和pass@5；pass@10仅作派生覆盖描述。
不把0/10称为支持集消失，不按成功任务重新定义评价集，不按长度或成功标签挑样本。
两次生成repeat不是两次独立训练。任务配对bootstrap的区间条件于这些checkpoint和生成样本。

**迁移分层：** hn01原协议为BF16、65,536输出上限；SH02为FP16、16,384上限。
四个单元必须在同一冻结层内完成，旧样本不能拼到新层凑足10次。
短预算层报告逐条件length终止率、生成token和墙钟时间，只能称预算受限复现。
如果硬件容纳不了作者预算，保留限制；不要看测试表现再单独给某一臂加预算。
若需改变预算，另建四臂共同的新协议并保留原结果。

发布checkpoint评测与本项目 `ssd` arm是两回事。后者只是共同MBPP循环中的SSD配方适配。
Apple模型卡给出的训练温度是1.6，源码示例的1.5和长度过滤不能冒充发布模型的真实训练清单。
来源：[SSD论文v2](https://arxiv.org/abs/2604.01193v2)、
[官方模型卡](https://huggingface.co/apple/SimpleSD-4B-instruct)、
[固定作者代码](https://github.com/apple-aiml-research/ml-ssd/tree/2637d2021f1bc523385b48a1f88ea9aa4812b0a9)。

## 优先级二：把SPECTRUM的五轮结果变成可信主实验

保留现有完整矩阵、模型pin和291/50/30/500划分。主比较是同一初始模型出发的
Vanilla、SSD适配、SPECTRUM三条独立谱系，Qwen Coder1.5B有r1/r2/r3三组独立训练重复，
每组各跑5轮；每轮对同一500题采样64次。所有pass@k/C64/D指标来自同一池。
固定第5轮为主终点，0–5轮曲线全部保留；不选最好的轮次，不按测试表现重抽随机化。

在开始新轨迹前，先核对原生MBPP任务接口、chat template、代码提取、测试和超时。
使用发布的真实样本与参考解进行接口资格检查，保留原始/提取输出及故障分类。
MBPP500不是MBPP+378；若切换官方MBPP+作主评价，必须新建协议、重跑所有臂，
不能把人口变化包装成同一结果修正。测试诊断不进入训练、不用来调tau或挑decoder。
这些是新的前瞻性训练轨迹，但不是从未被研究者查看过的全新benchmark。

| 既有块 | 完整覆盖 | 回答的问题 | 结论限制 |
|---|---|---|---|
| core | 3重复×3臂×5轮=45 arm-rounds，3 jobs | 五轮正确率/丰富度的共同变化 | 三重复不足以声称已精确估计训练总体变异 |
| mechanism | Projection、random soft、isotropic soft、fixed geometry、anchor replay各5轮=25，5 jobs | 方向、衰减、重估、参考信息的作用 | r1单重复；差异不显著不等于等效 |
| token_matched | 3臂×5轮=15，1 job | 监督token暴露的解释 | 不是等FLOPs、等优化步数或等总耗时 |
| decoder | 初始模型+3个第5轮学生，3个额外固定decoder，3 jobs | 具体解码策略敏感性 | 全部报告，不从中挑新主结果 |
| scale | Qwen3B/7B、DeepSeek6.7B，各3臂×5轮=45，3 jobs | 模型尺寸/架构复现 | 每模型r1；不是独立验证同一总体的3次重复 |
| transfer | 6个core/scale来源×4benchmark=24 jobs | 冻结学生的迁移 | HE+原生；APPS/CC/LCB仍为adapted |
| diagnostic | tau0.5/2与completion-only Vanilla/SPECTRUM，共4 arm-rounds，3 jobs | 强度和loss-scope敏感性 | 仅1轮，不支持五轮prompt-loss无关结论 |

总量仍为40 jobs、134 arm-rounds、7,106,080个fresh-run候选；另一个LCB四条件协议
是5,240个候选，单独计账。这些不是GPU小时预测。先完成已有LCB证据及core，再安排
机制/暴露/解码、scale/transfer；没有依赖关系的已合格CPU准备可以并行。
低优先级单元仍在覆盖表里，未跑就标pending，不把缩小矩阵写成完整完成。

## 机制实验如何避免“什么结果都能解释”

1. Random soft匹配完整增益谱，检验参考方向是否有额外作用；isotropic仅匹配算子距I的Frobenius距离。
   同时报告已有的folded-weight位移/生成诊断。两者不自动匹配输出KL或激活位移。
2. Fixed geometry必须复用实际round-1算子。重估没有清楚收益时，结论写“此设置下未分辨出重估收益”，
   不把宽区间当“重估无用”的证明。
3. Anchor replay使用相同50个参考答案，额外监督token明确计费；不称SPECTRUM完全无外部信息。
4. Token-matched保留全部raw记录，7.2M监督target预算及整条记录的轻微超额照实报告。
   所有计算成本包含标定、生成、训练、评分、失败和重试，不能只报训练时间。
5. 若论文主张五轮收益与prompt loss无关，再对现有1轮诊断建立新的五轮配对扩展；
   当前四个诊断单元不能证明它。扩展先冻结预算和分析，不替换原主结果。

## 冻结分析与结论规则

- 主比较是第5轮SPECTRUM分别对Vanilla和SSD的四个端点：pass@1、pass@64、C64、D4。
  这是每重复8个效应，共24行；pass@8/16/32、D8/D16及其它块是次要结果。
  reporter本次修正为读取manifest声明，不再把全部9指标误标主指标。
- 每重复先算相同任务上的配对差，再对三组差值等权给出均值、sample SD和三个原始值。
  展示每组2,000次任务配对bootstrap的95%区间；明确它不覆盖训练随机性。
  不把3×500题当1500次训练，也不把5轮当5次重复。
- 当前分析是效应估计，不做自动PASS、显著性星号或“非劣”判定。没有登记实用非劣界，
  不能借用旧 `formal_statistics.py` 的1pp门槛。八项主比较的区间为pointwise，不能读成同时覆盖。
  如未来确需总体推断或等效主张，先用独立development成本/方差证据做精度设计，
  冻结重复数、实用界和多重性规则，再开独立确认；不按当前p值补跑直到显著。
- C64对全任务计入失败生成的预算；D4仅在两臂都至少4个正确样本的任务中比较。
  每个比较公布双方eligible、仅reference eligible、仅candidate eligible、双方不eligible四格。
  D不eligible保持缺失，不填零；D逐轮的人口会变，不能直接叫固定任务群的保留率。
- C64是正确Python AST类的丰富度，D是正确样本条件下的结构丰富度；不称语义算法数。
  相对初始的丰富度比不是保住相同解法身份。pass@64只描述64次预算下的覆盖。
- 正确率下降就报告代价；SSD或简单控制表现相当就收缩谱机制主张。
  宽区间跨零意味着未分辨，不意味着等效。失败、缺失、负结果和无收益结果全部留表。

## 原生评分与交付验收

HumanEval+保持EvalPlus0.3.1、fixture v0.1.10、完整164题的原生与plus检查。
现有APPS200/CodeContests165/LCB200经过自定义接口转换、输出比较和整套超时，
只能作为adapted transfer。升级为native结论前，须在相同发布任务与相同预测上回放官方评分器，
核对容差、stdin/function、每例状态、早停、超时与全分母；不一致逐项留档，不能靠改标签消除。
不更换题目、放宽测试或把软件fixture分数充当科学结果。

本次明确保留两个执行缺口：

- main正式release入口仍用canonical模型ID+revision，旧入口的新共享目录解析不代表release已支持任意离线复制。
  优先准备固定revision的HF缓存并离线加载；共享复制必须有可核对的来源与完整文件哈希。
  不删掉revision检查，不伪造`_commit_hash`。详见runbook。
- 当前主机能力、隔离和现存进程未恢复核验；源码的`--allow-unsafe-local`不是隔离证明。
  当前采用native Conda，不自动改用Docker。没有合格原生执行边界时，只阻塞相关评分/轨迹。

新增runtime fingerprint会绑定实际依赖、Python、Torch/CUDA/cuDNN及现有Docker路径的image ID。
它不能追认旧运行环境；变更源码/环境必须新root，不改写旧sealed marker。
新代码需Local验收后才能用于运行；正式交付包必须包含执行SHA/dirty patch、资产/环境清单、
任务与样本ID、原始预测、官方输出、完整失败记录、报告重建差异和剩余覆盖。
每条科学结论由可重建证据决定，不能由“代码已更新”或静态状态文件决定。
