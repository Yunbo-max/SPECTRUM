# P03 优先级与在研数量

绑定 spectrum-round2 / cycle 1 / P03 / attempt 1；worker harness.planner.000010。当前工作是队列审计，独立验收由既有程序另行执行。下述优先级是证据依赖及投资判断，不是节点重排或实验派工。

## 完整队列

接受的 coverage-P04 保留五项 pending。以下为其工作视图，状态不改写 canonical coverage，不将不可运行比较从义务中移除。

| 义务ID | 当前工作状态 | 缺口、依赖与解除条件 | 责任与当前可行工作 |
|---|---|---|---|
| restore-evidence | 资产清点已获前节点接受；原始恢复部分受阻，整体pending | 原始程序、CSV、评分与源对象未取回；父级检查16对象及一次远端fetch失败只说明所查位置失败 | 父级保留恢复身份；worker使用已固定输入解释范围，后续取得真实字节才升级可信度 |
| source-and-community | 已有保存来源可读；全文/代码核验等待，整体pending | 两条社区讨论已落盘、图片未读、部分评论未穷尽；论文仅摘要，不能支持机制或原创判断 | 父级串行取讨论；worker复用保存观察、在程序分配的相关节点核对原始论文/实现；不重复provider调用 |
| second-round-inquiry | 机制与强替代证据等待，整体pending | Gate 0历史inconclusive、无accepted v4；自然失败后果、SSD完整比较与机制控制欠账 | 当前只登记必要性与可证伪条件；不强迫新算法 |
| independent-review | 等待当前提案与最终报告固定；整体pending | P01/P02/I01/I02/I04/P04各自接受不替代P03或最终报告审查 | 程序调用真实独立reviewer，实际阅读本提案的固定证据 |
| deliver-research-decision | 等待证据整合与独立评审；整体pending | 需中文报告、限制、预测、最小后续检查及文件读回 | 保留交付义务；本队列表不是最终第二轮报告 |

当前活动：一个P03 worker；history的15项worker/reviewer回执均终态，2项失败、13项执行完成，其中round 3执行完成但契约拒绝。没有已登记活动实验、native任务或待检视子结果；当前输入inspection_refs=[]、repair_basis=[]。程序phase=active、pause_ref=null，无用户暂停项目或已记录暂停任务。缺少授权的实验列为受阻，不能伪装成用户暂停。没有单独放弃/删除的比较。空Controller摘要不说明当前worker不存在，也不证明全主机无其他作业。

历史科学比较欠账（从 FINAL_EXPERIMENTS 与 EXISTING_EVIDENCE 保留；未转成当前可执行合同）：

| 比较/证据 | 状态与必要性 |
|---|---|
| 自然逐例链、共同合格分母与后果 | 原始证据受阻；需要initial→generator→native student配对案例、正确率与丰富度同分母；频率未知 |
| SSD final n=64及Plain/SSD/SPECTRUM完整核心比较 | 未完成；不能用n=16填充n=64。核心计划三独立重复×三方法×五轮，45 arm-rounds；本轮不执行 |
| scale：3B/7B/6.7B三模型同三方法五轮 | 计划45 arm-rounds；已有20个base-model单元不能替代训练复制，等待授权与证据 |
| mechanism：projection/random soft/isotropic soft/fixed geometry/fixed-anchor replay | 计划25 arm-rounds；检验方向、刷新和锚点信息，源码存在不代表已运行 |
| token_matched：三方法五轮 | 计划15 arm-rounds；监督token匹配不等于总算力、生成token、步数匹配 |
| diagnostic：tau=0.5、tau=2及completion-only两臂 | 计划4 arm-rounds；强度/损失范围尚未排除，不启动科学测试 |
| transfer与decoder | 计划24 transfer jobs、3 decoder jobs；SSD迁移和全部策略对比保留，APPS不利结果不得删去 |
| generator→student传递、语义标签及独立训练重复 | 均未有充分证据；语义标注不得填零或标完成；五轮不是五次重复 |

上述冻结历史计划总计134 training arm-rounds以及评价作业，只是输入中的计划，当前coverage experiment_contracts=[]、execution_task_ids=[]，无 admitted empirical/scoring task 可被本节点免除。保留完整计划身份与欠账；本阅读目标可以交付有界证据修复结论，不能由此声称计划已执行、科学门已通过或实验义务消失。

## 一个候选与明确覆盖来源

pool_target=1，selection_target=1。target_override：采用固定 Work Harness edition-policy.md 的 Shared research improvements 与 workflow-harness.md 的 Candidate and method boundaries，替代 human-ai-supervision/P03 的旧20→15池及20活动idea默认。保留一个SPECTRUM现有问题/机制家族的审计主线；新获准construction数=0，已接受v4决策数=0，当前昂贵实验候选数=0，最大同时投资候选=1。数字1是默认选择目标，不虚构一个已验证新方法，也不是新增总次数/时长限制。

父级曾提自适应谱强度和语义代理，仍属未选择建议；社区中的OPSD、MOPD等只为来源线索，不另算活动候选。Plain、适配SSD、projection、random/isotropic、fixed geometry和anchor replay是比较或竞争解释，不拆成候选/研究周期。没有有来源的扩大pool授权，本节点不生成20个idea。最新用户“不要设限制”撤销操作者累计时间、尝试、帖子数限制，延续单worker/独立review及单实验政策，不据此强制扩大科学候选池。

## 优先级：能改变重要决策的证据

1. 先保留原始证据可核验性和目标端点：现有历史MBPP报告SPECTRUM相对Plain C64更高但低于initial，且pass@1未满足原非劣标准；不能用AST改善盖过正确率代价。Plain pass@64下降区间跨零，尚非语义丢失导致任务失败的因果证据。原始文件缺失限制所有强结论；已有失败恢复位置无需无条件重复尝试。
2. 强简单替代优先于扩展谱方法：SSD n=16的C16及边际D4高于SPECTRUM，是最有挑战的已有替代，但不同D4资格总体、缺n=64及raw证据，尚未完整合格。必须保留共同解码、信息、分母和完整成本条件；解码器本身、Plain与fixed-anchor replay分别检验简单训练/解码/参考信息是否足够。若这些解释收益，则无需额外谱机制，即使修好全部工程问题也不证明谱方向值得投资。
3. 机制必要性次于可识别性：projection是同anchor设计控制，不是完整SPD复现；random soft与isotropic soft分别针对方向和通用衰减，fixed geometry针对重校准必要性。矩阵范数匹配不自动匹配激活位移或KL。生成期变化是否传给native student仍未知，必须区分两阶段。
4. 社区线索只改变核对问题：两条已保存讨论提示一般目标偏好、正确演示条件化、外部锚点及格式变化。training.py 的 train_on_records 保留未筛选raw completions并调用model loss；不能直接套用reverse-KL OPSD机制。相关论文保存记录只有abstract/metadata，本次不宣称外部D2阅读、因果归因或新颖性通过。正文图片和未读评论仍未知；不按热度排序。
5. 更广模型/种子/新模块等待上述关键缺口厘清。APPS无条件C16/pass@16点估计不利、共同D4分母与语义未知均保留；不寻找有利子集挽救普遍优势。若合法证据显示简单替代已足够，允许无需新方法的报告；若无法恢复raw，则报告历史证据限制，不无限维护同一恢复尝试，也不制造新总上限。

这种顺序源于有限采样下任务成功与正确实现发现量的重要性，而非热度、小空白或沉没成本。原创性仍未知，无实质新颖性证据即不批准新构造。真正最小决定性检查须由相关节点根据已核验信息给出；此处不选择后继节点、重排序列或授权实验。

## 期限、家族努力、恢复与审核

没有用户给定的交付日期或每周人时；不臆造期限。user-continuation撤销旧六次/1800秒/一次搜索上限；本次300秒watchdog是传输边界。15份回执已读取、核验并在readback保留；累计实际1131.8183542508632秒，与当前packet相符，含失败及审查成本。它是本Harness账面调用时间，不是训练用时；历史科学家族全部投入、订阅token及真实费用未知，不用零替代。没有新family命名重置历史。

P04已报告CPU/RAM遥测不足、磁盘98%使用率；属于控制机历史观察，不是现在已预约容量。本次只做小型文件读取、哈希与记录，不做新资源准入或科学计算。首读根目录authorization.md失败，已用research-state/authorization.md恢复；已在可见输出报告。安装技能与采用的固定Harness版本不同，执行以用户给定固定源及注入模块为准，不改安装或运行时。

小红书父级22:42的两份实际保存观察比P04的search_in_progress状态新，已读帖子文字和可见评论，图片未读；不继续把旧超时当当前无人登录，也不推断持续在线或更多结果已完成。worker没有provider调用。程序已有真实消费者调用本worker；此事实不保证未来持续存活，不新启consumer。

本节点decision_ref=null，保持accepted_decision_ref=null，不捏造v4链；tasks=[]表示P03队列材料可供程序独立验收。新coverage严格继承已接受P04快照，保留五项pending、旧证据和空实验合同，仅追加P03证据。P04独立审查不能代替本节点审核，当前不自签PASS、不推进游标、不宣称目标或报告完成。
