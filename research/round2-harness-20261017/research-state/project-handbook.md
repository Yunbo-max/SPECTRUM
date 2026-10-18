# SPECTRUM 项目研究手册

2026-10-18：按用户要求从已有证据补建。持续更新；活动任务/评审绑定不可变快照，不绑定会被覆盖的本文件。此手册不是新的科学结果。

## 目标与 motivation

继续 SPECTRUM 第二轮研究，结合数学、核心论文官方代码和真实 GPU 实验，识别具体条件下自蒸馏/迭代改进的局限或不必要依赖，再构造并验证方法。C/D 保持发现与修订自由；独立验收后进入 E 的正式扩大验证。原有谱方法不必成功。用户授权小红书只读讨论线索，用论文/代码/实验核验。

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
