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
