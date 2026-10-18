## 当前执行方式（2026-10-18 最新）

用户停用了 Work Harness，B/C/D/E 使用 `research-guidance/prompt-*.md` 的自然语言指导。后文的 controller、准入、维护待办和验收状态仅为历史记录，不再限制实验。已有8000预测可直接用已验证适配器评分，无需为单角色评分修复旧接口；目前尚无这批模型评分结果。阶段选择、实验设计和记录格式由 GPT 按证据决定。

# SPECTRUM 项目研究手册

2026-10-18：按用户要求从已有证据补建。持续更新；记录格式由研究需要决定。此手册不是新的科学结果。

## 目标与 motivation

继续 SPECTRUM 第二轮研究，结合数学、核心论文官方代码和真实 GPU 实验，识别具体条件下自蒸馏/迭代改进的局限或不必要依赖，再构造并验证方法。C/D 保持发现与修订自由；证据充分后由 GPT 直接进入 E 的扩大验证。原有谱方法不必成功。用户授权小红书只读讨论线索，用论文/代码/实验核验。

## Gap、idea 与数学预测（可推翻）

历史候选区分谱方向、采样分布/长度重加权和额外答案信息；零期望 score 梯度有严格条件，不能直接推出实际多轮训练无效或谱干预必要。见 research-state/C-phase-e1a14/method-basis-v3.md，仅为带来源的既有候选，不强制当前 worker 沿用。科学选择须重新评估，见 research-state/question-led-experiment-selection-20261018.md。

## 文献与记忆入口

research-state/B-C-memory-index.md 及其链接保留 B 文献/代码/讨论和 C 追加证据。手册总结不能替代源卡、原始输出和真实评分。

## 实验设计

当前 C/B02 尚未接受具体问题。下一步由同一 worker 选择能区分竞争解释的模型、任务、强/简单对照和原生评测，检查容量、任务难度、采样、截断与信息/预算差异。1.5B/MBPP 缓存及用户先前提及的7B均不构成强制配置。D 由条件与可证伪预测设计方法；E 根据存活主张扩展并保留未暴露确认数据。

## GPU 与执行配置

- 授权目标：spectrum-harness-gpu-hn01，单 NVIDIA GeForce RTX 4090。已有 preflight 报告总显存24564 MiB，见 research-state/gpu-intake-20261018/hn01-final-preflight.json；空闲显存与环境为历史观察，提交前重新看实时值。
- 执行环境：远端 /root/rivermind-data/spectrum-harness/venv；代码测试、模型和评分计算在 GPU 主机，Mac 仅控制。
- 为每个训练/生成/评分阶段写配置：模型/版本、dtype、长度、batch单位、有效batch/累积、并发序列、每题样本量、相关实现与内存估计。
- 用户建议：可支持且合理时从128向64、32、16、8、4、2、1探测；已有实测或估计排除的档位可跳过，不为填表故意OOM。128尚未针对新工作负载实测。
- 选型依据：实际有用吞吐、显存峰值和余量、运行稳定性；不以显存占满为目标。保持样本量与科学设置；改变有效batch、精度、截断/解码等语义须明确修订方案和公平对照。

## 已有实际结果与边界

- e1a86资源校准及固定记录：reports/C-phase-e1a86-preparation.md、research-state/C-phase-e1a86b/readback.json。只对原有配置有效，不能证明新模型/长度/训练阶段可行。
- e1a87 base export：runs/stage-outputs/spectrum-C-base-export-e1a87/summary.json，500题、8000条生成，scoring_status=pending。sequence_batch_size=64、task_batch_size=4、每题16条；这些是不同单位。报告peak_reserved_bytes=5375000576、elapsed_seconds=1736.03，只代表此次导出，不等于最大可用batch或训练峰值。
- 当前没有据此成立的新准确率结论或C验收；原始结果/负面观察保留。

- e1a88 manifest bridge软件检查：runs/stage-outputs/spectrum-C-manifest-bridge-e1a88/summary.json；修复manifest可通过结构校验，但 metadata_repair_matches_original_export=false；不能把它写成科学评分已打通。后续应解释/修复匹配语义并保留原导出。

## 下一步与更新约定

worker 先核验本手册和当前实际进度，补充选择依据、数学预测及下一项判别实验，依据实验更新gap/idea/design。新模型/长度/阶段须选择相应探测；既有合格配置可复用。每次重要结果或方向改变更新相关段落，并链接原始证据与不可变历史，不另建审批或小worker。

## e1a89 更新：真实评分依赖（未验收）

已核对25项传入pin、14份native回执及其声明输出，均匹配；无新增native运行。见 reports/C-phase-e1a89-runtime-dependency.md 和 research-state/C-phase-e1a89/readback.json。原8000预测保持不变；当前 .13 exact export matcher 与完整评分合同在manifest元数据和基线命名处不兼容，需要运行时在quiet boundary提供有证据约束的历史metadata repair。不是GPU不可用或科学反证。当前待评分，不宣布C完成。

科学选择先检验原条件的容量/难度/截断，不能由缓存选模型或默认重启F/P/A。仅替换363条length结束输出而保持其余输出不变时，平均pass@1绝对变化最多4.5375个百分点，这是代数界不是实测改善。官方SSD的已发布checkpoint是另一问题下的强对照候选，须保留其采样/数据/目标差异。

资源：既有batch64推理配置可在同条件下复用；8000条无需再生成，因此本次不额外探测128。未来生成仍考虑128→64→32→16→8→4→2→1并记录合理排除；训练需单独测反向/优化器峰值，不能借用生成的5.38GB峰值。评分CLI当前串行逐程序，其并发单位是程序，128序列的推理批次不能套到评分；没有新的评分吞吐实测。

## e1a90 更新：评分器已验证，单基线评分路径待维护

已采用.14；hn01真实任务f110f40063164e21813388631b78aa1c完成正式协议验证、原export兼容匹配和四类live scorer探针，均通过。见reports/C-phase-e1a90-scoring-route.md及其原始回执。没有模型成绩。普通development单角色评分请求被实际拒绝：development requires actual control comparison。下一步需要受控已导出单角色offline scoring路径；不把模型评分伪装软件检查、不重跑生成、不执行旧P/A凑角色。原8000预测hash保持不变。

恢复后先评分以判断当前配置的容量/截断/任务辨识力，再选模型/条件和强对照。协议pass@1>0仅检查全错地板，不能证明强基线资格；B03调优/公平与独立确认等仍pending。评分资源单位为程序，串行2CPU/4GiB、每程序3秒，未发生新模型显存测量。
