## 交付与LCB数据进展（2026-10-18 23:09 UTC）

真实Qwen评分、sanitizer诊断及记忆已交付分支research/round2-harness-20261017，commit153692c。LCB官方snapshot0fe84c3的test6已在GPU下载并与官方SHA256核对；175题中131题符合作者日期条件，其他shard日期完整性尚待核对。源文件在远端cache/lcb-0fe84c3/test6.jsonl，不入Git。下一步见upstream-evaluation-20261018/lcb-continuation.md；下载PID63741仍需恢复前核对。研究未完成，保持Harness自动续跑。

## 续跑补记（2026-10-18 23:07 UTC）

SSD作者源码已通过codeload取得，固定2637d2021f1bc523385b48a1f88ea9aa4812b0a9；archive/source摘要见upstream-evaluation-20261018/ssd-source-resolution.json。原生CLI默认32768输出token、20 repeats，不可误认为论文设置；下一步固定LCB数据来源并检查隔离依赖，再测4090容量。模型下载PID63741仍活动，首分片已下载约1.9GiB；无模型推理进程。

## 最新纠正：Harness 已恢复管理职责

2026-10-18 用户明确保留 Harness 的长任务、记忆、自动续跑和中断恢复，仅取消 B/C/D/E 实验设计与执行的固定格式和准入限制。下文“停用整个 Harness”的记录已被纠正；旧实验接口报错仍为历史，不再阻止直接评分。当前实验模式由 GPT 执行、Harness 监督，真实结果仍待实际运行。

## 历史执行方式（已由上文 Harness 恢复指令取代）

此前将用户指令理解为停用整个 Work Harness 是过度解释，现已纠正。Harness 保留长任务监督、记忆、自动续跑及恢复；B/C/D/E 使用 `research-guidance/prompt-*.md`，由 GPT 自主研究。旧准入和单角色限制不再阻止实验。已有8000预测直接使用已验证适配器评分，无需重新生成。历史记录保留，新的实际进度见下方追加记录。

# SPECTRUM 项目研究手册

## 最新结果与续跑位置（2026-10-18 23:01 UTC / 英国10月19日）

Qwen作者流程和未修改EvalPlus899b2b3已全部完成。378题、greedy每题1条：raw base267/378=70.635%，raw base+extended230/378=60.847%；上游sanitized base266/378=70.370%，joint229/378=60.582%。旧自写2.325%不能作为容量地板或谱方法必要性的证据。新旧任务/提示/采样不同，不能把差额归为单独提取效应。完整报告与真实结果见 `research-state/upstream-evaluation-20261018/report.md`、analysis.json和raw/sanitized-eval_results.json。

继续C/B02后实际复现上游sanitizer问题：task635的heapify无return、被错误删除，唯一一个base结果由pass变fail。单独最小修订保留函数后，以原378输出和未修改evaluator完整复测，仅该题恢复，得到267/230；此为独立诊断端点，不替换官方结果。另有37题base通过但extended不通过；案例审读显示既有算法/性能问题，也有题意与canonical行为不一致，不能全部解释为实质模型推理失效。task635的112条extended输入全部为空列表，数据原样保留。

下一科学对照选作者发布的SimpleSD-4B-instruct与其实际Qwen3-4B-Instruct-2507基座，区分作者推荐解码与匹配解码/预算。选择依据是直接检验自蒸馏条件，非缓存或指定规模。直连HF不可达、hf-mirror403，ModelScope文件索引和下载可用；Qwen三分片摘要已与HF作者页面核对，Apple跨源摘要核对仍未完成。下载进程PID63741于23:01:55 UTC启动，顺序下载并核对每文件Sha256；日志和身份为upstream-evaluation-20261018/author-pair-download-*。恢复时先核对进程与exit，勿重复下载/启动。权重在远端cache/modelscope-author-pair-20261018，不入Git。尚未宣称这对模型已合格或完成推理；后续检查作者SSD原生LCB数据/协议及4090容量，再设计匹配比较。科学目标未完成，Harness继续监督，无暂停或runtime改动。

## 最新：恢复后执行 Qwen 作者流程（2026-10-18 22:44 UTC）

用户要求“你官方打吧”“然后继续往下跑呀”；此前暂停和交接已撤销。旧自写评分器已删除，不恢复或续跑。严格自写协议历史结果为186/8000通过，pass@1=2.325%、pass@16=21.2%，7620条SyntaxError；这是格式/评测诊断，不是官方模型成绩或容量地板证据。未完成的自写提取敏感性运行保留历史输出，不再执行。

已读取 `research-guidance/prompt-upstream-code.md` 和上游代码。Qwen提交33bc6aa的MBPP流程：作者ChatML提示、greedy/T0、每题1条、请求max_tokens2048、vLLM上下文1536、上游sanitize、raw/sanitized各自评估base与plus。明确导入其EvalPlus gitlink899b2b3，而非requirements中的0.2.1或环境已安装的0.3.1；实际模块路径已记录。此版本MBPP+ v0.2.0有378题，SHA256 b54e762755248ca411b523c917fa9f93c07b5ff2966bf60b3917b853926a3dad。与旧500题仅224个ID重合，重合题prompt字节无一相同；必须新生成，不能复用旧样本冒称官方复现。

在原venv补装vLLM0.10.0/Transformers4.53.3（保留Torch2.7.1），使用清华镜像；旧tree-sitter依赖放独立eval-deps目录，导入上游sanitizer已成功。硬件适配仅gpu_memory_utilization从.98降至.80；另外记录引擎原始文本/token/终止原因，不改变处理语义。原作者batch1/TP1/greedy设置保留，不为测试batch128改变作者命令。新程序PID60578于22:44:47 UTC启动，顺序执行generate→sanitize→raw evaluation→sanitized evaluation。日志、阶段进程身份及退出状态在 `research-state/upstream-evaluation-20261018/`，恢复时先核对真实进程，勿重复启动。

评测通过OS隔离外壳调用未修改的EvalPlus main，保留上游测试、oracle、时间限制和指标；chroot只读运行库、UID61043、seccomp禁网络/exec/逃逸相关调用，保留上游multiprocessing。实际探针确认宿主文件不可见、网络与运行库写入被拒绝、进程共享内存可用。命名空间unshare在主机上实际不可用，故采用该边界。378条生成和上游sanitize已完成（修改32文件），2条达到上下文上限。首次评估因隔离外壳256MiB文件上限不足以保存上游groundtruth缓存而失败，无模型成绩；失败日志、部分缓存及旧外壳保留在failures/file-limit-attempt1。仅将外壳文件上限提高至4GiB，22:53:33 UTC以PID61138恢复评估，复用生成/sanitize，不改上游评分语义。尚无官方科学评分。下一步依据raw/sanitized和base/plus结果重评C/B02，不预设原gap仍成立。

## 2026-10-18 实际续研进度（优先于下方历史待办）

已恢复手册与 B/C 记忆，保留 Harness 监督及自动续跑，未修改 runtime。原预测 SHA256 已核对；hn01 无其他实验任务后，22:15:37 UTC 直接启动原 v4 CLI 评分，runner PID39540、scorer PID39541。身份、输入摘要、命令、日志及最终退出记录在远端 `research-state/mbpp-original-scoring-20261018/`。恢复前先核对进程身份，不重跑生成或重复启动评分。

静态审计显示严格提取后仅380/8000条可解析；6725条为单代码块加说明，840条多代码块，55条其他；363条达到512 token上限。低严格评分不能直接解释为模型容量地板。已准备独立的单代码块提取敏感性实验，原评分不改写。完整科学判断、边界及下一步见 `research-state/mbpp-diagnostic-decision-20261018.md`，实际结果随后追加。

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
