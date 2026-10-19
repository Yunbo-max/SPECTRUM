## 当前续跑位置（2026-10-19 02:52 UTC）

runner65584的boot/start ticks仍匹配，seed1完整落盘，seed2继续推进（最近69/131）。当前完成2/10 repeats，无退出记录或正确率。第二轮131条任务/种子/提示绑定检查通过，全部stop、无length，292643 tokens，median1586、max9535，耗时4798.21秒。原作者提取后130条可解析，arc194_b单一代码块内残留无循环体的for草稿，与首轮围栏问题不同；未修改代码或评分器。详见ssd-author-comparison-20261019/second-repeat-observation.md及repeat-01*。原始输出和检查证据已同步本地。

原生成→隔离评分程序继续，未启动第二程序，未改实验或Harness runtime。此处仅为生成/格式观察，不是功能正确率或覆盖缺口。恢复时优先核对原进程和新落盘repeat；当前条件完成后读取真实评分，再继续模型/条件对照。研究未完成，Harness未暂停。

## 首个原生repeat落盘与继续生成（2026-10-19 00:49 UTC）

同一runner65584身份匹配，seed0的131条原始输出已完整保存并自动开始seed1；00:49 GPU负载72%、显存22087MiB。当前完成1/10 repeats，尚无正确率；不重复启动或提前进入并行评分。raw SHA256 de904a35d2c607c7bc5d59f59a7d972d42ba298e21ffed2f36ae646e2a273deb，已同步本地保留。

seed0实际生成5032.90秒、307970 tokens，median1749、max8337；131条均stop，无length终止，任务顺序/seed/长度边界核对通过。作者原提取+静态ast检查130条可解析，唯一arc194_b因原输出未闭合围栏使正则取到说明文字；输出自然结束6299 tokens，不是截断。未修提取、未执行该代码、未声称修复后正确。51条单块、80条多块。详见ssd-author-comparison-20261019/first-repeat-observation.md及base-temperature-0.7/repeat-00*；均为生成/格式观察而非功能评分。

原程序继续其余seed，完成后自动隔离评分。之后以完整条件结果重评C，再顺序恢复SSD资产和模型对照。研究未完成，Harness未暂停，不把首repeat完成当作研究结束。

## 原生失败语义与运行核对（2026-10-19 00:03 UTC）

同一runner65584身份匹配，第一repeat65/131 prompts，仍无完整repeat/正确率；00:01观察GPU负载66%、显存22087/24564MiB，无重启或第二程序。

继续审读作者评分：首次失败即返回，lcb_run将所有未执行槽位补为失败且标Time out；因此num_tests_failed和补位文本不可解释为实际错误测试数或真实超时数。首失败输出也可能来自进程异常后的补位，不能只靠字符串定因。源码语义未改，分析器仅追加解释限制。hn01读取实际解码测试元数据：131题/4852 tests，最少1、median/max40，无零测试题；原生全completion join预算最大285秒，不是每测试固定6秒。证据见native-failure-semantics.md与native-timeout-budget-audit.json。这是协议审计，不是模型结果或新的C失效。

当前继续原生生成→隔离评分，完成后读取真实结果再决定后续研究。无新增门槛，不重跑已完成官方MBPP，Harness未暂停。

## 配对分析绑定与续跑（2026-10-18 23:58 UTC）

同一原生LCB runner65584身份匹配，首repeat61/131 prompts，约61.5 tokens/s，无完整repeat或正确率。未重启、不并发其他模型。

已增强analyze_condition.py：逐题prompt hash跨repeat及跨条件核对；两条件比较绑定dataset/source/n_repeat/max_tokens/top-p/top-k/min-p，显式列出其他配置差异；增加两方向any-success discordance与外部difficulty的描述性差值。分析器只读取作者评分状态，不执行代码、不改变官方指标。hn01以既有真实软件探针结果验证正常聚合、异数据拒绝、异提示拒绝均通过，记录comparison-analysis-validation.json；验证中的两份相同fixture不是模型比较，0差值不是科学结果。当前runner不调用这个后处理模块，生成/隔离评分路径未改动。

下一步仍为当前完整条件结束后的真实结果分析，再恢复SSD资产并执行作者推荐/交叉温度条件。此前官方MBPP结果保留不重跑，研究尚未完成，Harness未暂停。

## 训练来源边界核验（2026-10-18 23:52 UTC）

原生LCB第一repeat进至52/131 prompts；runner65584的boot/start ticks仍匹配，尚无完整repeat或正确率。当前继续生成，无第二模型任务。

审读SSD论文C.1与固定作者源码2637d202：论文描述约10,168条去重提示，公开生成脚本直接加载seed_sft、没有去重，默认T1.5并按字符长度过滤最短约10%；发布checkpoint card则训练T1.6。故示例脚本不是完整训练复现证据，不影响当前发布权重评测。rSTAR原论文报告16-gram去污染但评估LCBv5，不能替代对当前v6与确切SSD训练manifest的实际重叠检查。未发现或声称污染，未下载12.1GB seed_sft；hn01镜像metadata403已记录，不重试不变失败，也不阻塞当前模型程序。源码与分析见ssd-author-comparison-20261019/training-source-audit/review.md。后续训练如有科学必要再绑定实际提示、去重和过滤，不从公开例子推定checkpoint配方。

已读取既有手册/记忆；继续等待原生配对结果判定C问题，不将来源缺口转成新方法主张。Harness未暂停，研究未完成。

## 十样本解释边界与续跑（2026-10-18 23:46 UTC）

核对同一runner65584身份仍匹配，第一repeat最新39/131 prompts，无完整repeat或正确率。未重启、未并发其他模型，已完成的官方MBPP不重跑。

新增ssd-author-comparison-20261019/finite-sample-interpretation.md及hn01解析计算finite-sample-reference.json：IID假设下0/10成功的单侧95%概率上界仍为25.89%；即便两个sampler能力相同，也可出现大量任一方独有成功题。因此不能用零样本成功或筛选后的失败集合定义条件性gap。按题配对总体指标、两方向discordance、外部difficulty描述及截断/提取/计算量一起解释；发现后选出的条件须独立确认。示例为数学参考，不是模型分数、额外实验或强制增加采样轮次。当前程序继续，研究未完成，Harness未暂停。

## Decoder对照源码核验（2026-10-18 23:41 UTC）

原生LCB runner65584/start ticks144158755仍活动，第一repeat日志32/131 prompts，未产出完整repeat或正确率。保持单一程序，未恢复Apple下载或启动第二模型。上轮分析器及采样源码审计已交付666945a。

B补查AdapT、AdaDec、Top-H作者论文/代码：自适应温度、熵支持选择、选择性lookahead均有先例；AdaDec另有标注校准与额外推理成本，不可混为无训练/等计算对照。hn01对未修改Top-H作者commit8b94d62的CPU软件探针发现与论文v2熵约束不一致：128等概率logits、alpha.4/default top_n100返回39 tokens，归一化熵5.2854 bits，高于2.8 bits上限；top_n1另触发IndexError。只说明该源码与该论文版本的契约差异，不是模型分数或新C gap。原源码、license、hash和探针结果见adaptive-decoder-source-review-20261019/review.md，未静默修补或采用为模型对照。

后续仍先完成作者原生基座/SSD及解码交叉比较；若有残余条件失效，再用已核验的自适应控制区分机制。旧MBPP容量地板已否定；不将软件缺陷当作D创新。研究持续，Harness未暂停，恢复前先核对远端活跃身份和完成记录。

## 续研核对与B/C修正（2026-10-18 23:34 UTC）

已核对runner65584的真实start ticks，仍为同一原生LCB基座程序。最新日志第一repeat已完成21/131 prompts，约61.8输出tokens/s；尚无完整repeat文件或正确率，不重启、不并发第二实验。旧资产下载保持中断，部分Apple权重保留，待当前条件释放锁再恢复。

本轮增加analyze_condition.py：读取未修改作者评分状态，核对任务/seed/原始输出与被评分代码绑定、重算原生聚合指标作一致性检查，统计样本截断、语法/提取诊断和任务bootstrap区间。已通过原先真实执行的软件探针验证聚合；第一轮测试发现软件fixture的手工model_answers与fenced raw差一个换行，保留绑定断言并修正测试构造，实际模型结果未改动。分析器不执行生成代码，不替代作者evaluator。

已获取论文指定vLLM0.11.0源码并与当前0.10.0比对：top-k/top-p和随机采样函数AST相同，当前非greedy、不请求processed-logprob路径的已审读差异不改变采样步骤；不宣称模型kernel或随机轨迹逐位一致。失败的raw源获取转用codeload成功，运行环境未升级。证据见ssd-author-comparison-20261019/sampler-audit.md及sampler-source-audit/。

B/C进一步否定预设：作者card已报告pass@5提升，不能预设自蒸馏普遍丢失coverage。作者训练采样T1.6（不是示例config1.5）；原论文已经做更广温度扫描、support compression和context-dependent理论，两个matched温度或重述lock/fork都不构成新机制。带训练support mask的理想decoder null及证伪边界记于decoder-null-and-novelty.md，尚未启动新方法或宣称新gap。当前继续等真实对照证据，Harness目标未完成、未暂停。

## 当前运行：作者原生SSD对照基座（2026-10-18 23:23 UTC）

已继续到LCB真实模型生成：基座Qwen3-4B-Instruct-2507，作者推荐T0.7/top-p0.8/top-k20，每题10 samples、131题、输出上限65536，使用SSD作者原生prompt/generate。runner PID65584，身份与分阶段日志在research-state/ssd-author-comparison-20261019/base-temperature-0.7/。4090实际初始化通过：模型7.6065GiB、可用KV13.23GiB/96352 tokens，配置context67072、单序列、BF16、TP1。实际正在生成，尚无此模型的正确率；同一runner随后调用隔离的作者evaluator。

此前下载PID63741已在Qwen基座13文件全部校验完成后有意终止进程组，Apple未完成分片保留，原因记录在upstream-evaluation-20261018/author-pair-download-interruption.json。不是暂停Harness。等当前条件结束/退出再恢复下载，勿与当前pipeline.lock并发或重启已活动runner。恢复时先核对PID、boot/start ticks、active-stage与退出记录；完成的repeat文件可以复用。

SSD作者实现已适配隔离：UID61044、只读运行库、禁IPv4/IPv6、允许Manager所需Unix IPC；stdin/functional正确、错误、异常、超时五种软件探针均符合预期，不是模型结果。原生私测解码在隔离内完成，131题/4852测试。数据test6的官方摘要核对已通过；官方README说明先前release_v5截止Jan2025，支持仅加载test6并按作者Feb-May过滤，未下载审计所有先前shard。两个模型实际chat template和prompt完全一致，最长输入1410 tokens。Apple三权重摘要现已在ModelScope与HF镜像指针间交叉一致（直连HF仍不可用）。

下一步：分析基座原生LCB结果及截断，再运行SSD T1.1推荐条件，结合交叉温度条件辨别权重与解码效应。研究决策、数学null与限制见research-state/ssd-author-comparison-20261019/research-decision.md。旧MBPP近零容量地板已被否定，尚无D谱机制证据。研究持续，Harness未暂停或修改runtime。

## 交付与LCB数据进展（2026-10-18 23:09 UTC）

真实Qwen评分、sanitizer诊断及记忆已交付分支research/round2-harness-20261017，commit153692c。LCB官方snapshot0fe84c3的test6已在GPU下载并与官方SHA256核对；175题中131题符合作者日期条件，其他shard日期完整性尚待核对。源文件在远端cache/lcb-0fe84c3/test6.jsonl，不入Git。下一步见upstream-evaluation-20261018/lcb-continuation.md；下载PID63741仍需恢复前核对。研究未完成，保持Harness自动续跑。

## 续跑补记（2026-10-18 23:07 UTC）

SSD作者源码已通过codeload取得，固定2637d2021f1bc523385b48a1f88ea9aa4812b0a9；archive/source摘要见upstream-evaluation-20261018/ssd-source-resolution.json。原生CLI默认32768输出token、20 repeats，不可误认为论文设置；下一步固定LCB数据来源并检查隔离依赖，再测4090容量。模型下载PID63741仍活动，首分片已下载约1.9GiB；无模型推理进程。

> Current instruction: B/C/D/E are prompt-guided. Historical admission failures below are history, not unresolved prerequisites. Use the project research-guidance directory; preserve the evidence without enforcing old contracts.

# B → C shared research memory index

## 最新实测与科学修订（2026-10-18 UTC）

读取 `upstream-evaluation-20261018/report.md`。Qwen作者greedy流程+原EvalPlus已完成：raw267/378 base、230/378 joint；sanitized266/378、229/378。上游sanitizer删除无return的heapify导致task635退化，单独最小补丁+相同上游全量评测仅恢复该题。旧自写近零分不是容量地板证据；正式记录此负面结论。37条base-pass/extended-fail并非同质，需区分算法问题、题意/参考行为差异和测试退化，不能直接支撑D新方法。

已选择作者SSD4B及真实Qwen3-4B基座作下一强对照，模型来源记录在next-condition-sources。ModelScope两模型文件清单与hash已捕获，PID63741正在顺序取权重；Qwen三分片hash已与HF页面一致，Apple跨源比对未完成。读取active download log/identity before retry。后续需核对原生LCB条件与资源、匹配解码/预算；不是旧F/P/A回归或已完成E。保持一程序、一研究worker。

## 最新续研：Qwen作者评测优先（2026-10-18）

用户已撤销暂停并要求继续研究。旧自写评分器删除后不再恢复；旧pass@1=2.325%、pass@16=21.2%仅是自写严格格式协议诊断。读取 `research-guidance/prompt-upstream-code.md`、`resume-official-evaluation-20261018.md` 及 `upstream-evaluation-20261018/source-notes.md`。已确认Qwen33bc6aa引用的EvalPlus899b2b3实际导入路径，MBPP+ v0.2.0为378题；旧500题与其仅224 ID重合且prompt均不同。原采样T.8/n16/512与作者greedy/n1不同，不能混用。已在hn01启动全新作者流程（PID60578，22:44:47 UTC），后续顺序sanitize和隔离raw/sanitized、base/plus评估。实际进度优先看该目录日志和阶段退出状态。环境准备不等于科学结果，旧gap是否消失仍待测。

## 2026-10-18 restored autonomous research

Harness supervision and automatic continuation are retained; legacy experimental admission failures below are historical. Read `mbpp-diagnostic-decision-20261018.md` for the active work. Original predictions were hash-verified and the unchanged v4 scorer started directly on hn01, with process identity/logs under `mbpp-original-scoring-20261018/`. No regeneration. Static format audit: 380/8,000 outputs parse under strict extraction, 6,725 have prose plus a single code block, and 363 hit the length cap. These are format/termination observations, not yet functional scores. A separately preserved extraction sensitivity diagnostic is prepared; original scores and all failures remain intact. Do not infer model capacity or select larger models from strict-format failure alone.

Navigation index created during owner-authorized .9 maintenance. It references
existing B knowledge and C updates; it does not create new scientific evidence
or override the original source cards, revisions, experiments or acceptance.

## Retained B knowledge

- `reports/L05-coverage-knowledge-attempt-000001.md`: joint literature/code/
  benchmark coverage, method families, historical findings, competing explanations
  and unresolved reproduction/comparison obligations.
- `research-state/L05-evidence-snapshot-attempt-000001.json`: pinned evidence
  snapshot and predecessor references for those claims. Follow these to L01–L04
  and community source cards rather than treating the summary as primary evidence.

## Later C additions

- `research-state/C-phase-e1a14/method-basis-v3.md`: SSD code/settings audit,
  SPD implementation gap, SDPO-CL implementation trace, distinctions between
  sampling/filtering changes and feedback-conditioned distillation; provisional
  mathematical diagnosis and candidate comparison rationale.
- `research-state/C-phase-e1a14/sources/source-index.json`: captured upstream
  source identities and bytes. Community claims remain leads, not measurements.
- `research-state/C-phase-e1a14/evidence-index.json` and
  `reports/C-phase-e1a14-checkpoint.md`: actual scope of work and missing evidence.

## Questions to retrieve against

| Milestone | Question | Current evidence boundary |
|---|---|---|
| B02 | Which concrete condition/dependency explains an observed task/cost limitation? | Source/code and provisional explanations exist; new causal interventions and native consequences remain unmeasured in this C attempt. |
| B03 | Which established/simple controls are qualified under matching information and budgets? | Selection rationale exists; implementation gaps, adaptation and real native comparison/qualification remain explicit. |
| B04 | What problem and falsifiable boundary do the mathematical and experimental findings support? | No newly accepted problem contract; do not promote source summaries or infrastructure checks to scientific support. |

For each question, first assess this evidence's applicability. Refresh missing
papers/code/discussions using B's methods, record the new source and conditions,
then return to the same C question. Record experiment prediction, real result,
uncertainty, and the decision to advance, redesign or revise/reselect the problem.
Append versioned links and supersession notes here as knowledge changes. Preserve
negative evidence and prior versions. Revisit earlier questions directly when evidence warrants it.

## Operational history is separate

The .8 readonly database failure is an execution-interface failure, not evidence
for or against a scientific hypothesis. .9 installation/tests likewise do not
prove any research hypothesis. Native receipts and scientific acceptance must be
reported separately.

## e1a18 恢复观察（非科学结果）

- `reports/C-phase-e1a18-dispatch-recovery.md`：.9邮箱实际返回准入拒绝；coverage缺字段修复后暴露真实mapped-code缺口。无native实验执行或新科学分数。
- `reports/C-phase-e1a18-dispatch-independent-review.md`：独立静态检查具体映射与后续stage/coverage接线冲突；非软件测试或科学接受。
- `research-state/C-phase-e1a18/checkpoint.json`：当前phase绑定、三次拒绝响应和原有phase_progress；后续恢复须保留身份并先解决明确准入依赖，不重复安装/数据下载。

## e1a84 实际prepare与恢复（非科学结果）

- `reports/C-phase-e1a84-recovery.md`：.10首次原prepare执行失败，原因是adapter旧摘要；已另存绑定修复但未执行验证。
- `research-state/C-phase-e1a84/checkpoint.json`：新任务启动前reconcile_required，原身份远端PROBE为absent；保留控制器恢复义务。失败回执完整，未产生新的任务分数或问题支持证据。

## e1a86 真实准备和GPU资源校准

- `reports/C-phase-e1a86-preparation.md`：prepare、batch64 BF16资源校准及profile固定已由controller归档；不是科学分数。
- `research-state/C-phase-e1a86b/checkpoint.json`：所有新native身份终态，保留失败、16项义务和评分接口依赖。
- `research-state/C-phase-e1a86b/readback.json`、`scoring-dependency.json`：实际hash、分母与评分来源边界。无新B05支持；不重跑已完成准备。

## e1a87 .11实际评分软件工作（未科学接受）

- `reports/C-phase-e1a87-progress.md`：已执行chroot/seccomp隔离、四类软件控制、500参考程序兼容性审计与setup顺序修复；保留ID123超时。均不作为模型性能。
- `research-state/C-phase-e1a87/scorer-semantics-v2.md`：原测试、setup顺序、3秒来源、AST指标边界及修正历史。当前preload标准库范围与完整adapter/CLI资格仍待检查。
- `research-state/C-phase-e1a87/request-06.json`：既有prepare/calibration复用的base export修复请求。首次因GPU UUID缺失准入拒绝；是否完成须读取其真实mailbox/native回执。

## e1a89 评分兼容依赖与选择边界

- reports/C-phase-e1a89-runtime-dependency.md：.13源码与既有真实远端检查共同定位旧导出的manifest/arm名谱系兼容缺口；待运行时修复，不是新的科学反证。
- research-state/C-phase-e1a89/readback.json：传入pin、真实回执/输出校验、源码快照和全部社区源卡hash。
- research-state/C-phase-e1a89/handbook-snapshot.md：当前不可变手册；保留有限预测截断影响代数界、模型/任务重评理由和阶段资源限制。

## e1a90 原生评分器验证与剩余接口依赖

- reports/C-phase-e1a90-scoring-route.md：真实通过后继协议、export匹配及四类软件探针；未评分模型。
- research-state/C-phase-e1a90/readback.json：真实controller输出pin、原预测及拒绝回执。
- research-state/C-phase-e1a90/checkpoint.json：同一C阶段，单角色离线评分实际准入拒绝；不以缓存、旧F/P/A或软件通过代替问题选择和科学接受。
