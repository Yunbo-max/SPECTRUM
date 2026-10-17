# I02 Parent Problem：已有方法的贡献类型与证据义务

绑定 spectrum-round2 / cycle 1 / I02 / attempt 1；worker harness.planner.000007。
本卡固定本次贡献分类 contribution_type=method，value_route=failure_census。这是已有 SPECTRUM 问题的可审查登记，不是已通过 Gate 0 的 canonical Parent freeze，不是新候选、v4派工决策或实验许可。现阶段结果为 evidence_repair。程序独立审查尚待执行。

## 原始证据与谱系

用户 inputs/user-request.md 要求基于 SPECTRUM 已有实验第二轮思考；research-state/objective.md 保留中文决策报告、可证伪预测、最小后续检查及独立审查目标。用户未指定自适应谱强度或语义代理为赢家。沿用 I01 的 M 入口，保留历史 research/audit/research-state.json 的 repair_evidence 和 Gate 0 inconclusive；不把该历史笔记当认证状态机。

上游审计来源为 45195e866162df1cdf9de0169d2bf17347eb6abf，输入快照为 f7b661f593719d4f0a98a4db13dc33c0ad09824a。已有 Parent problem 文字位于 inputs/spectrum/docs/LITERATURE_AUDIT.md 的 Parent problem and importance check；本卡是其只读重述与贡献类型明确化，未改变问题、总体或端点。没有已接受 canonical Parent ID 或 v4 decision，不能伪造 previous decision。精确文件身份见同名 readback JSON。

## 六项 Parent 内容

| 字段 | 固定内容与证据边界 |
|---|---|
| natural_failure | 循环自生成代码后训练中，native student 的正确率可能上升而正确实现丰富度收缩。历史 MBPP 支持需要调查的聚合现象，尚未证明逐例语义策略丢失及后果链。 |
| population_id / population | spectrum-historical-mbpp-heldout-500：历史同一500题MBPP总体，最终n=64与逐轮n=16是不同采样协议；HumanEval+ 164题与改编APPS 200题分别保留，不能混合为普遍总体。 |
| prevalence | 逐例联合“正确率增、丰富度减、任务受损”的频率未知；500题是评估分母，322/321/323等是各方法D4资格数，不是自然失败率。五轮是一条训练轨迹。 |
| consequence | 原问题端点为有限采样预算下任务解决概率与正确实现发现量；pass@k、C_k、共同合格D_b分别报告。历史Plain pass@64下降点估计的区间跨零，不能由AST差异推出因果任务损害。语义保留仍未知。 |
| strong_simple_alternative | 已有最具挑战性的比较对象是适配SSD/decoder-only温度截断；n=16的SSD C16和边际D4较高，但非共同分母，n=64缺失且当前原始输出不可验证，因此尚非完整合格基线。Plain是简单训练基线；projection是同anchor设计对照，不能冒充原论文SPD的忠实复现。 |
| falsifiable_prediction | 沿用原假说：同信息、训练暴露和评估解码下，校准方向相对匹配强度通用衰减/固定算子能保留更多native-student正确实现丰富度，且满足预声明正确率代价约束。若合格SSD或通用衰减已解释收益，方向必要性不成立；若语义标签不支持，仅保留实现代理范围。此为未检验的条件预测。 |

simple_alternatives 保留 Plain、适配SSD/decoder-only、同anchor projection、fixed-budget replay、直接anchor监督/重放、isotropic_soft、random_soft和fixed operator。后四类的相应完成对照没有本次实测证据；源码存在不代表控制已运行。spectral.py make_operator 静态可读：random_soft匹配增益谱、isotropic_soft匹配Frobenius位移，不能据此声称激活扰动、KL、token或成本已匹配。最强已有比较与最简机制控制承担不同问题，不能互相替代。

## 类型对应价值路线与尚未成立的价值

method → failure_census：仍需真实逐例自然链、明确分母与后果、合格最强简单替代后未解决的比例、native scorer/协议/原始输出，以及重要性与功能性原创审查。当前全部关键证据不够，Gate 0不通过、不填阈值或attestation。已有脚本/文档中的将来矩阵与本轮无实验授权分别保留。历史贡献是否有价值，取决于可用正确解分布的实际后果和相对简单替代的必要性，不能只看代理指标增益。

原创性未知。LITERATURE_AUDIT是本次重读的历史二级审计，不升级为本次外部论文D2；其SPD、SSD及其他谱系线索待相应原始论文/代码再核验。全秩衰减的局部代数不推出语义熵或长期正确性；不得宣称首次循环自蒸馏或首次多样性坍缩。本节点分类不需要新颖性先通过，但不授权投资新机制。

## 不强迫方法与替代贡献的义务

当前不新增算法；有用结果可以是证据修复、原方法不必要、受限负面结论或复核结果。
若未来明确改为 phenomenon，必须另建有谱系的Parent并满足 replicated_observations（至少两次真实独立合格重复及最强解释），本次一条轨迹不能充数。theory须 formal_obligations、实质证明和最强已知定理比较，标准占据恒等式/局部可逆性不足。systems/efficiency须performance_frontier端到端质量—成本缺口；data须data_coverage及已发表的覆盖定义，不能把缺失语义标注包装成新数据贡献。replication_or_transfer仍走failure_census并保留原始复现证据。类型变更均需明确新Parent谱系，不能重命名逃避当前欠账。

负证据完整保留：SPECTRUM n=64只是部分AST保留，对两个训练对照的原pass@1非劣标准失败；SSD n=16的C16和边际D4更高；APPS无条件C16/pass@16点估计不利。APPS共同合格D4可不同向，不混用分母；语义效果既未证明也未被这些代理普遍否定。SSD n=64、独立训练重复、实际标签、自然案例与生成到学习传递证据均缺失。

## 恢复、权限与交付边界

2026-10-17 user-continuation supersedes旧六次/1800秒与一次搜索限制；不设新总上限。保留当前调用300秒watchdog和历史累计552.2495898026973秒，当前未结算。小红书由parent supervisor串行读取，本worker没有provider请求，旧超时不是无讨论证据。

重读parent保存的 source-recovery-20261017.json：检查的16对象本地均不可得，上游fetch返回not our ref；这证明两处恢复失败，不证明别处不存在。该观察不升级历史汇总为raw output。原始文件、账号、运行时和程序状态不修改。

history九份回执实际读回：前两次模型不支持失败，第三次执行完成但契约拒绝，后续三组worker/reviewer终态；无新native receipt、inspection_refs或never-started cancellation。本次首读authorization.md路径失败，已读到research-state/authorization.md，影响仅为路径纠正。无需重复旧运行。

coverage新快照继承当前I01接受版本，保留全部五项pending及experiment_contracts=[]，仅追加本节点证据。不消除历史FINAL_EXPERIMENTS科学义务，不把它转换为授权执行合同。decision_ref=null保持无已接受v4决策的事实；tasks=[]表示I02分类材料可供程序独立审查，不表示全目标、报告或任何实验完成。本worker不自签独立审查，不选择下一节点，不启动第二consumer。
