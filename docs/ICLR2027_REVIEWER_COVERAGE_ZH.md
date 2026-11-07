# SPECTRUM ICLR 2027：三位审稿人的问题、实验与回复覆盖表

**Submission 45902 · w3G2 / FUKc / ygkV · 2026-11-07**

**当前状态：实验目录与待填证据的回复草稿。此文没有宣布新实验已完成，也没有提交 OpenReview 回复。**

## 1. 覆盖范围与证据来源

本次使用 [`reviewer_case_mapping.json`](../experiments/iclr2027_rebuttal/reviewer_case_mapping.json) 中的 **18 个问题摘要**：w3G2 的 W1–W3、FUKc 的 F1–F6、ygkV 的 Y1–Y9。这些内容是仓库记录的归纳，不是审稿人的逐字引文。本次未找回完整的原始 review 文本及对应 OpenReview note ID，因此不能据此声称“已经逐字核验原始 review 的全部问题”。提交前仍须把下面 18 项与原文逐项对照，补齐摘要可能省略的细节或子问题。

实验以 [`cases.json`](../experiments/iclr2027_rebuttal/cases.json) 为准：保留 `d033641` 的 c00–c36，追加 c37–c47。较新的 27-case 分支 `6f4d2a0` 重用了相同编号，却赋予了不同含义；不能按编号直接合并。**本目录目前有 48 个 case 标识，不能把它表述为 48 条已经完成的新训练轨迹。** 其中包含历史证据审计、冻结模型重评、插值、人工标注准备及需要恢复或补跑的训练。

本轮可核验的来源：

- [`cases.json`](../experiments/iclr2027_rebuttal/cases.json)：实验身份、模型、轮次、采样数、生成长度及历史状态标签。
- [`reviewer_case_mapping.json`](../experiments/iclr2027_rebuttal/reviewer_case_mapping.json)：原有 18 项摘要及映射。
- [`REBUTTAL_GAPS.md`](../research/audit-20261107/REBUTTAL_GAPS.md)、[`SOURCE_PATHS.md`](../research/audit-20261107/SOURCE_PATHS.md)、[`EXPERIMENT_INVENTORY.csv`](../research/audit-20261107/EXPERIMENT_INVENTORY.csv)：已有结果的恢复审计和来源定位。
- [`ICLR2027_LEARNED_GAIN_REVISION_GUIDE.md`](ICLR2027_LEARNED_GAIN_REVISION_GUIDE.md)：Learned 的定位、额外信息/计算成本以及 D4 字段警告。
- [`ICLR2027_REVIEWER_RESPONSES.md`](ICLR2027_REVIEWER_RESPONSES.md)：与本表配套的英文逐点回复，所有未取得的结果均保留明确待填槽位。

审计报告中的“历史已完成”首先是库存状态。复用前仍要核对原始模型版本、数据划分、配置、checkpoint lineage、采样数、evaluator 和完整性 receipt。只有 summary、脚本或目录存在，不足以证明当前比较已完成。

## 2. 两个研究层次必须分开

| 层次 | 协议 | 可回答的问题 | 不能替代的证据 |
|---|---|---|---|
| 原投稿主实验 | Qwen 1.5B，5 轮，生成上限 512，训练 n16、native 评估 n64；原始 MBPP 291 train / 50 reference / 30 dev / 500 test | Fixed 的主结果；方向与衰减；信息、token、公平比较；原设置的稳定性 | 不能用另一模型或不同长度的结果直接补成同协议对照 |
| 主实验独立种子 | seed43：c36/c01；seed44：c06/c07；seed45：c08/c09 | 独立训练轨迹之间的稳定性 | 同一个模型的多次采样、bootstrap 不能充当多个训练种子 |
| 模型与迁移检查 | 3B、DeepSeek 6.7B 的新训练配对；冻结 checkpoint 的 HumanEval+ / adapted APPS n64 | 特定外部设置下是否仍有作用 | 初始模型评估不是训练后的复现；conditional 指标不等于完整任务成功率 |
| 历史 7B 五轮比较 | 之前报告的 7B / 五轮 / 4096 轨迹，由 c00/c25 与 revision guide 恢复核对 | 历史跨尺寸证据，身份和 native 输出待核验 | 五轮历史状态与新增十轮状态分开；历史五轮结果不证明 r10 完成 |
| 投稿后 gain 扩展 | c37–c43：Qwen 7B，10 轮，生成上限 4096，训练 n16 / native 评估 n64，seed43 | Fixed / Learned / decay / adaptive 的准确率与多样性权衡；报告第 5、10 轮 | 单种子扩展不能解决主实验三种子稳定性；不能证明梯度方向 U 必要 |
| 历史证据审计 | c00、c25 | 找回、核对和解释已有证据 | 审计 case 不会生成新的训练结果 |

原投稿 Fixed 仍是主方法。7B Learned 扩展只学习 spectral gains，采用普通 SFT，LoRA update scale 为 1，不学习 LoRA 更新缩放，也不进行 token-loss reweighting。十轮 case 的 r5 切片并不自动等于之前那条历史五轮轨迹，必须分别核对 lineage 与协议。40 fit + 10 guard 都属于校准信息；10 个 guard 不是独立测试集。已有 72-case 研究队列与本 rebuttal 目录保留各自身份，不能把两套编号或完成状态混为一体。

## 3. 审稿问题的完整仓库映射

下表对仓库已记录的全部 18 项摘要给出所需 case、交付证据及结果不利时的处理。**“有 case”表示已有明确承接位置，不表示该问题已有肯定结论。**

| 问题 | 记录中的实质疑问 | 必需的 case / 文本工作 | 应交付的证据与边界 |
|---|---|---|---|
| w3G2 W1 | 梯度方向 U 与普通衰减 a 没有分离 | c01 对 c02/c03/c04；c45 原 SPD-hard；c27 仅辅助参考数量检查 | 同谱随机基、各向同性强度、matched residual；同时报告实际 operator/update 统计和 output KL。c27 不是方向消融。随机/各向同性若相当，撤回“U 必要” |
| w3G2 W2 | AST conditional richness 不足以证明可重复保留正确解 | **c36/c01、c06/c07、c08/c09 全部配对**；c16；c26 | 独立训练种子 SD；全任务成功率；共同 eligible 集上的 D4 和分母；冻结迁移；人工算法家族标注。不能把重复采样当训练复现 |
| w3G2 W3 | 表达、soundness、novelty 定位过强 | c00/c25/c45 + 方法、相关工作、假设、claim 和 limitation 修改 | 写清 reference-gradient 与 SPD 的关系、经典 proximal 形式与经验命题的区别；Learned 作为投稿后 gain 扩展。没有文字修改不能只靠 audit 关闭此项 |
| FUKc F1 | 只有一个 1.5B 设置和一个训练种子 | c36/c01、c06/c07、c08/c09；c18/c19；c14/c15 | 三组独立训练配对与 SD；训练后的第二尺寸/第二家族；不同长度历史结果单列。c37–c43 只增加一个单种子设置 |
| FUKc F2 | Plain 没有相同 50 个参考答案 | c36/c05；c01/c27；**c10/c11/c44** | Plain replay 相同答案、Fixed40/50、相同 7.2M token 额度下 replay；披露新增监督信息与校准成本。信息可得性相同不等于使用方式和总计算相同 |
| FUKc F3 | 训练 token 和校准开销不同 | c10/c11/c44；c05 提供非预算约束 replay 对照 | 实际逐轮 shifted target tokens、reference replay 占用、生成量、训练与校准计时/计算估计。配置的 7.2M 不等于实际已经达到；仅 token 配平不能称 equal FLOPs |
| FUKc F4 | projection 的衰减强度不匹配 | c01–c04、c45；DEV30 和 output-KL 诊断 | 明确每项匹配的量；区分 norm、residual、功能性 output KL。KL 是测量，不是被强制匹配的控制量 |
| FUKc F5 | AST 变化可能只是表面，control-flow 证据弱 | c26 + c00 中的 metric 定义 | exact / AST / control-flow 并列；预先选择任务的盲标 packet；人工算法家族、分歧和不确定性。packet 生成不能称“语义审计已完成” |
| FUKc F6 | pass@1 权衡；迁移多样性未稳定提高成功率 | **c36/c01/c30/c45**；c16/c17；c32–c35；c37–c43 单列 | 同协议 accuracy–diversity frontier；完整任务成功率和共同 eligible 分母；保留负面 APPS；Learned 若损失 coverage/richness 必须披露 |
| ygkV Y1 | tau=1 近似均匀 shrink，方向性未证明 | c01–c04、c45 + gain 分布/实际 KL | 实际谱的离散程度及 norm 对照；若近似 isotropic 或结果相当，改写为现有证据支持的 shrinkage/stabilization |
| ygkV Y2 | 缺少 tau、层位置、geometry refresh 检查 | c01 对 c12/c13、c23/c24、c31；c00 历史 tau；c41/c42/c43 扩展 | 原 1.5B 多轮三类控制分别报告；7B 一轮 tau 的不同 n/长度单列；gain schedule 扩展不能替代原设置敏感性 |
| ygkV Y3 | temperature/top-p 控制和 SSD 强点不足 | c20–c22/c46；c28/c29/c47；c30；父 checkpoint c36/c01；扩展 c38 | c46 单独改变冻结评估的 top-p；c47 单独改变五轮 Plain synthesis 的 top-p，统一评估不变。区分 decoder-only 与 synthesis-only，列精确 T/top-p/top-k；原生结果待取得 |
| ygkV Y4 | 缺少 weight interpolation 或 KL-to-initial baseline | **选择 c32/c33、c34/c35 的权重插值方案** | 全权重插值 alpha=.5/.75 与两端点；核对 alpha 定义及父模型，原生结果待取得。按摘要中的“或”选择插值；专门 KL-to-initial 训练未实现，也不声称已运行。Learned guard/KL probe 不等于该训练 baseline；提交前仍对照原文 |
| ygkV Y5 | Plain 没有同样 50 个答案 | c36/c05、c01/c27、c10/c11/c44 | 与 F2 同一批证据复用，明确 information 与 token 的联合控制及额外校准开销 |
| ygkV Y6 | 单家族/种子；附录只有初始模型；pilot 改了 extraction | c00；**c36/c01、c06/c07、c08/c09**；c14/c15；c18/c19；c25 | 必须是训练后配对；原配置、checkpoint、evaluator/extraction 身份；改 extraction 的 pilot 保留为探索性，不能放入 confirmatory 表冒充同协议 |
| ygkV Y7 | 迁移 eligible 数量小；APPS 不利 | c16/c17；c26 仅补充局部语义检查 | 全 benchmark native n64；完整成功率与共同 eligible 条件统计；报告小样本不确定性、适配规则及负面效果 |
| ygkV Y8 | AST 保留 literals/function names；control-flow 结果弱 | c26 + c00 中的规范化定义 | 明确保留/删除内容，人工算法家族及分歧；若只有结构变体，不使用“语义多样性已证实”的结论 |
| ygkV Y9 | SSD 有时更丰富，Fixed 有时 pass@1 更低 | c36/c01/c30/c45；c37–c43 单列；c25 仅历史核对 | Plain/Fixed/SSD/SPD-hard 同协议全指标；5/10 轮扩展分开；不选择性删掉 baseline 优势或被支配的点 |

### 原始映射中需要补全的对照

W2 原来只列 Fixed 的 c07/c09，没有列对应的 Plain c06/c08；Y6 也缺少完整种子配对。本表补全三组配对。F2/Y5 补入 c36，避免 replay 只与 Fixed 比而丢失无参考 Plain；F6 补入 c36/c01/c30/c45，避免只谈迁移与 Learned 而没有原始准确率权衡表。新增 c44 把参考答案信息与 student-token 预算放到同一对照中；c45 给原 SPD-hard 历史结果一个稳定身份。c46/c47 分别补入冻结评估与五轮合成训练中的独立 top-p 控制。以上是比较关系的补全，不是新增结果。

## 4. c00–c47 逐 case 索引

所有编号都指当前 `experiments/iclr2027_rebuttal/cases.json`，不能套用旧 27-case 分支的同名编号。表中的“待”描述本轮待核验/待完成的工作，不否定已有主机历史文件存在。

| Case | 独立目的 / 协议 | 角色和证据状态边界 |
|---|---|---|
| c00 | 恢复与审计既有主实验、operator、tau 证据 | 审计；不能充当新训练 |
| c01 | 原 1.5B Fixed，seed43，5 轮，512 / n16 / n64 | 原主结果；先核对历史身份，必要时重建 |
| c02 | 原设置 random soft basis，同 gain eigenvalues | 方向控制；待原生结果 |
| c03 | 原设置 isotropic soft，匹配指定 Frobenius 强度 | 既有一轮不能冒充五轮结果 |
| c04 | 原设置 matched-residual continuous/binary 控制 | 衰减/残差控制；待结果 |
| c05 | Plain replay 同样 50 个 reference answers | 信息控制；额外监督 token/compute 披露 |
| c06 | 原设置 Plain seed44 | 历史候选；与 c07 配对 |
| c07 | 原设置 Fixed seed44 | 历史失败/部分轨迹；不能视为完整重复 |
| c08 | 原设置 Plain seed45 | 历史候选；与 c09 配对 |
| c09 | 原设置 Fixed seed45 | 完整性未确认；与 c08 配对 |
| c10 | Plain，7.2M shifted-target-token 预算 | 实际 token receipt 待验证 |
| c11 | Fixed，同样 7.2M 预算 | 与 c10、c44 联合比较 |
| c12 | 原设置 tau=.5，五轮 | 历史一轮证据单列；五轮待完成 |
| c13 | 原设置 tau=2，五轮 | 7B/一轮历史不等价；五轮待完成 |
| c14 | DeepSeek 6.7B Plain，512，五轮 | 与 c15 构成训练后跨家族配对 |
| c15 | DeepSeek 6.7B Fixed，512，五轮 | 4096 历史不能直接当作此 case 的同协议结果 |
| c16 | 冻结第 5 轮 checkpoint，HumanEval+ native n64 | 迁移；原 n16 不能替代 n64 |
| c17 | 冻结第 5 轮 checkpoint，adapted APPS native n64 | 保留负面结果，报告适配和分母 |
| c18 | Qwen 3B Plain，五轮 | 与 c19 配对；训练后结果待确认 |
| c19 | Qwen 3B Fixed，五轮 | 与 c18 配对；训练后结果待确认 |
| c20 | 冻结模型 cooler decoder，T=.6 | 仅改变评估解码，不是新训练 |
| c21 | 冻结模型 warmer decoder，T=1.0 | 仅改变评估解码 |
| c22 | 冻结模型 SSD decoder recipe，T=1.5 / top-p=.8 / top-k=20 | 多参数配方；不是 SSD 训练，也不是 top-p-only |
| c23 | 原设置 Fixed，仅最后一层 [27] | 层选择控制 |
| c24 | 原设置 Fixed，仅中间层 [14] | 层选择控制 |
| c25 | 历史 Learned / 长轮次审计 | 审计；不是 c37–c43 的启动入口或完成证据 |
| c26 | 40 个预选任务，最多每 arm 8 个正确程序的盲标 packet | 准备与人工标注必须分开；人工标签仍需取得 |
| c27 | 原设置 Fixed，40 个 fit references | 与 c01 的 50 个参考对照；不是 U 消融 |
| c28 | Plain 改 synthesis：T=1.0 / top-p=.95 / top-k=0，五轮 | 需要新训练；统一 native evaluator |
| c29 | Plain 改 synthesis：T=1.5 / top-p=.8 / top-k=20，五轮 | 与 c30 其余配置/lineage 一致时是同一干预；可复用等价封存证据；不同于 c22 |
| c30 | 原设置 SSD，五轮，native n64 | repo SSD 仅改变 synthesis decoder；不与等价 c29 重复计为算法；历史 n16 与目标 n64 区分 |
| c31 | 原设置 Fixed，冻结第一轮 geometry | 与逐轮重估的 c01 比 refresh |
| c32 | 第 5 轮 Plain 全权重插值，alpha=.5 | 冻结检查；核对初始/末轮父模型和 alpha 约定 |
| c33 | 第 5 轮 Plain 全权重插值，alpha=.75 | 与 c32 同类，不能替代 KL 正则化训练 |
| c34 | 第 5 轮 Fixed 全权重插值，alpha=.5 | 与 c32 构成相同 alpha 的方法对照 |
| c35 | 第 5 轮 Fixed 全权重插值，alpha=.75 | 与 c33 构成相同 alpha 的方法对照 |
| c36 | 原 1.5B Plain，seed43，五轮 | 原始主 baseline；与 c01 配对 |
| c37 | 7B Plain，10 轮，4096 / n16 / n64 | 单种子扩展；历史候选须核对原始身份 |
| c38 | 7B SSD，同扩展协议 | 强 baseline；完整性未确认 |
| c39 | 7B Fixed，40 fit references，同扩展协议 | Learned 的同 fit 子集 counterpart；待结果 |
| c40 | 7B Learned，40 fit + 10 guard，同扩展协议 | 历史候选；额外 guard/优化/probe 成本不能忽略 |
| c41 | 7B Fixed，50 references，同扩展协议 | 历史部分到 r8；须原 revision 合法续跑或重建，不能记 r10 完成 |
| c42 | 7B fixed gain，tau decay=.8，同扩展协议 | 历史完整候选仍需身份核对 |
| c43 | 7B entropy-adaptive tau，gamma=5，同扩展协议 | 历史部分到 r8；同样需要合法补齐 |
| c44 | Plain+50 reference replay，原设置同 7.2M token 预算 | 联合 information/token 控制；与 c10/c11 比 |
| c45 | 原 1.5B SPD-hard，五轮，native n64 的恢复 | 先恢复核对完整历史；仅必要时重建；不是 7B 扩展 |
| c46 | 冻结第 5 轮 checkpoint，nucleus_tight：T=.8 / top-p=.8 / top-k=0，native n64 | 评估 top-p-only 对照，比较统一 .8/.95/0；不重新训练；原生结果待取得 |
| c47 | 原设置 Plain，五轮 synthesis-only top-p=.8，其他合成设置同 Plain | 独立训练对照；统一 native 评估 .8/.95/0；与 c46 区分，原生结果待取得 |

历史 Learned、no-decay、entropy-adaptive、decay 的运行状态来自旧审计，不能由本表自行升级。尤其 r8/10 只表示部分完成；失败的 decay 设置不能编造缺失末轮指标，也不能被当成科学上的“零收益”估计。

## 5. Learned 扩展到底要补什么

c25 只回答“以前做过什么、文件是否可追溯”。真正承接本次可比的 7B 十轮实验的是 c37–c43。所有 arm 要使用一致的数据划分、teacher/学生 lineage 规则、生成长度、采样预算和 evaluator，并在第 5、10 轮分别报告结果。

| 对比 | 主要问题 | 仍然存在的限制 |
|---|---|---|
| c40 Learned 对 c39 Fixed40 | 同一 40-fit 子集下 gain 选择是否改变权衡 | Learned 多用了 10 guard 和拟合/probe 计算，不是纯 gain-rule-only 因果对照 |
| c39 Fixed40 对 c41 Fixed50 | 参考数量变化本身影响多大 | 需要确认 40 是同一个 fit 子集，不能换参考内容而不披露 |
| c37/c38/c39/c40 | Plain、SSD、Fixed、Learned 的 extension frontier | 单种子；每个指标均要保留不利结果 |
| c41/c42/c43 | 固定强度、decay=.8、entropy-adaptive gamma5 | 每轮实际 tau、gain 和 KL 要有诊断；额外适应计算需披露 |
| 同 arm 第 5 轮对第 10 轮 | 增加轮次后成功率与丰富度如何变化 | 不能只报告较好的轮次或与别的 arm 的不同轮次比较 |

当前 repo 的 SSD 只把训练合成 decoder 改成 T=1.5 / top-p=.8 / top-k=20。c29 与 c30 在其他配置和 lineage 一致时属于同一训练干预；保留两个不可变 ID 用于追溯，但可以复用等价的 sealed c30 证据，不把它们算作两个独立算法或强制重复训练。c22 的冻结模型 decoder-only 比较仍然不同。

Fixed 和 Learned 都使用梯度派生的 U，因此这组扩展**不证明 U 的必要性**。W1/Y1 仍由 c02/c03/c04 等主机制控制承接。7B 结果也不能直接替换原始 1.5B 五轮 headline。


预算计数说明：7.2M 是每轮共同 target-token 下限，代码在完整样本边界停止，允许小于一条最长编码样本的有限 overshoot。最终报告必须列实际 token 与超额，不能声称三组逐 token 完全相等。

## 6. 诊断、统计和“完成”的含义

更新的 runner 规格支持：主设置第 1、5 轮，以及扩展第 1、5、10 轮的 **DEV30 pre-native / pre-spectral / post-native** 诊断；每个 arm 还记录 **8 个训练 prompt × 128 个 raw-logit probe token** 的 output KL。这里的含义是代码支持生成相应证据，**不是本轮已经取得诊断值**。后续必须查看原生执行产生的文件和 receipt。

这些诊断不应改变原始推断边界：DEV30 不是 500-task 测试集；训练 prompt probe 不是独立测试；同 gain spectrum、Frobenius norm 或 residual 不自动等于同 output KL。本次测量实际 KL，不声称执行了 KL 匹配。

最终表格至少需要以下信息：

- **完整任务总体：** pass@1、pass@64、C64、样本数及完整任务数。不同任务集和抽取/测试规则分别报告。
- **条件丰富度：** 精确 D4 定义、共同 eligible task 集、eligibility 规则与分母；每对比较的任务数都要给出。避免 arm 各自换分母后直接相减。
- **训练随机性：** 对 seed43/44/45 的完整配对报告逐种子结果和跨训练 SD。任务 bootstrap 与跨种子波动是不同的不确定性。
- **成本：** 实际 shifted target tokens、reference replay token、额外参考监督、校准梯度、gain fitting、生成/评估量、时间与可得的计算估计。
- **来源：** case ID、源代码 revision、model/data/evaluator 身份、checkpoint、plan/complete receipt、task-level metrics 与必要 checksum。
- **失败和缺失：** 单列 failed / partial / unverified；不能填零、拼接不兼容轮次，或只选成功的 arm。

[`rebuttal_case_analysis.py`](../scripts/rebuttal_case_analysis.py) 承接已封存的 task-paired 分析；[`rebuttal_semantic_blind.py`](../scripts/rebuttal_semantic_blind.py) 承接盲标 packet 准备。源码可读不等于它们已经在真实数据上完成、产生可发表统计结果。

### D4 字段特别提醒

旧报告中的 `D4_cond_cov` 是归一化字段，不能直接改名为原文未缩放的 D4 richness。原始 D4 对符合条件的任务至少为 1；归一化字段的定义与分母必须恢复。必要时从 verified task-level programs 重算，不能把历史 normalized 数字直接填入原论文 D4 表。此要求来自 [`ICLR2027_LEARNED_GAIN_REVISION_GUIDE.md`](ICLR2027_LEARNED_GAIN_REVISION_GUIDE.md)。

### c26 的人工阶段

packet 的设计是先按固定规则选择 40 个任务，再收集每个 arm 的 verified-correct 程序，最多每 arm 8 个。必须保留无正确程序或不足 8 个的覆盖情况，不能只挑所有方法都好看的任务。最终需要人工算法家族标签、标注规范、不确定性、分歧与 adjudication 记录；packet 本身的 `strategy_annotation_completed: false` 不允许写成“语义评估已完成”。[`rebuttal_semantic_summary.py`](../scripts/rebuttal_semantic_summary.py) 承接标签完成后的汇总，但不能代替人工标注和裁决。这是 40 个预选任务、每 arm 最多 8 个已验证正确程序上的 sampled-correct human D4，不能写成全 500 任务的 semantic pass@64。

## 7. 尚未闭合的缺口

| 优先事项 | 已有承接 | 仍需补齐或明确承认的部分 |
|---|---|---|
| 原始 review 原文 | 18 项版本化摘要 | 完整原文/note ID；核对各项原始措辞、指定配置及摘要可能遗漏的子问题，不能由当前映射推出逐字完整性 |
| 核心机制和复现 | c01–c04、c45；完整三组种子对 | 原生结果与身份核验；机制控制目前并非三种子完整重复，不应借主种子重复夸大机制稳定性 |
| 信息和计算公平 | c05/c27、c10/c11/c44 | 实际预算、参考内容、校准成本；7.2M student token 相同不能自动解决额外 FLOPs/时间 |
| 语义有效性 | c26 准备 packet | 人工标签、分歧、覆盖和统计；缺少时保留 AST proxy 限制 |
| Y4 已选择的稳定化方案 | c32–c35 权重插值，承接摘要中的“插值或 KL” | 四项原生插值结果、两端点及 alpha 约定待核验。专门 KL-to-initial 训练未实现、未被选为本次替代方案，也不声称已运行；KL probe/guard 不能冒充该训练 |
| 独立 top-p 控制 | c46 冻结评估；c47 五轮 Plain 合成训练 | 两项均已有独立 case；仍需原生 n64 输出与父模型/配置核验。c47 的最终评估保持 .8/.95/0，避免把训练分布和评估解码同时改变 |
| 迁移和 SSD 强对照 | c16/c17/c30、c45、c32–c35 | native n64 完成、全任务与 eligible 分母、负面 APPS/低 pass@1 不能删除 |
| Learned / 长轮次 | c37–c43，c25 审计 | 同协议的第 5/10 轮结果；r8 部分轨迹补齐；单种子及额外信息/计算限制 |
| 论文表达 | W3 文字义务 | 真实匿名稿中的改动位置、引用、假设和 claim 变化；不是创建 case 后自动完成 |

当前最值得保留的科学决策是：若 Random/Isotropic 可解释 Fixed 的收益，就收窄方向性 claim；若 anchor replay 解释收益，就披露额外参考答案的贡献；若 Learned 提高 pass@1 却损失 richness/coverage，就报告权衡；若 APPS 不提升或 SSD 更优，也保留在最终表格。负面结果是结论边界的一部分。

## 8. 为什么保留 37-case 基础，而不替换成 27-case 分支

`d033641` 的 c00–c36 同时保留了 token 预算、冻结迁移、decoder-only、层位置、人工语义、权重插值和 synthesis-only 等控制。`6f4d2a0` 的 27-case 目录重叠了主机制与少量模型/种子检查，但删掉了前述多项 reviewer 所需控制。两者都不能直接当作已完成证据。

常见编号冲突如下，可用于查旧记录，**不可把旧编号直接用于当前启动入口或输出目录**：

| 27-case 分支中的旧编号与含义 | 当前目录中的对应关系 |
|---|---|
| 旧 c00 Plain archive | 当前 c36；当前 c00 是总审计 |
| 旧 c01 Fixed archive | 当前 c01；仍要核对实际协议和身份 |
| 旧 c02 hard-SPD archive | 当前 c45；当前 c02 是 random basis |
| 旧 c03 SSD archive | 当前 c30；当前 c03 是 isotropic |
| 旧 c04/c05/c06：random/isotropic/matched residual | 当前 c02/c03/c04 |
| 旧 c07：same50 replay | 当前 c05；预算约束版本另外是 c44 |
| 旧 c08：固定第一轮 geometry | 当前 c31 |
| 旧 c09：Fixed40 | 当前 c27 |
| 旧 c11/c12/c13/c14：seed44 Plain/Fixed、seed45 Plain/Fixed | 当前 c06/c07/c08/c09 |
| 旧 c15/c16：3B Plain/Fixed | 当前 c18/c19 |
| 旧 c10：tau=.5 一轮；旧 c24：tau=2 一轮 | 当前 c12/c13 为五轮，协议不同，不能直接复用成完成证据 |
| 旧 c17/c18：DeepSeek 历史 4096 配置 | 当前 c14/c15 为 512 五轮；不是同一协议 |
| 旧 c19：7B Fixed 五轮4096；旧 c20：7B Learned 十轮 | 当前 c25 可审计；当前 c39/c41/c40 是明确十轮扩展身份，逐一核对 |
| 旧 c21/c22/c23：7B 一轮高采样机制控制 | 当前 c02/c03/c04 是 1.5B 五轮；无协议相同的编号替代 |
| 旧 c25：Plain cooler synthesis 一轮 | 当前 c20 是冻结评估，不是该新训练；不能等同 |
| 旧 c26：Plain warm synthesis 一轮 | 当前 c28 是五轮；当前 c26 是盲标 packet |

旧分支继承的 runbook 还描述过“7B 四方法、三个新种子、十轮”等另一套矩阵，与本次“原投稿 1.5B 主实验 + 单种子 7B 十轮扩展”的范围不同。当前使用 case catalog 的明确身份，不用旧 runbook 的总轨迹数推导本次完成度。历史记录继续保留作为来源，不能被改写成新的执行事实。

## 9. 最终确认时应该看到什么

英文回复每项都有待填槽位，确认前应获得对应表格、数据来源和结论变化，而不是只有“已覆盖”勾选。最低交付是：原始同协议主结果与关键机制对照、完整种子配对状态、信息与 token 联合控制、SSD/迁移及负面结果、人工语义阶段的真实状态，以及独立的 7B gain 扩展表。已选择的 c32–c35 插值方案及 c46/c47 独立 top-p 控制仍需原生结果；人工标签和原 review 对照未完成时必须明确列出。专门 KL-to-initial 训练并非本次选择的替代方案，未实现也不声称已经运行。

本轮文件编写与源码审计没有运行训练、模型评估或项目测试。GitHub 上出现这些文档和入口，只表示执行与写作方案已经具体化；最终研究结论仍以各 case 的原生证据为准。
