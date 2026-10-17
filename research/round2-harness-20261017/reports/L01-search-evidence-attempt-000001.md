# L01 问题、机制与同义词检索

本次仅完成 cycle=1 / L01 / attempt=1 的检索证据提交，待既有程序独立审查。没有选择后继、建立方法决策、运行科学测试或完成研究目标。全部来源哈希与查询元数据见 research-state/L01-search-index-attempt-000001.json。

研究问题保持为：反复使用模型生成的原始代码训练时，正确实现的可用分布是否收缩；谱方向、一般衰减、采样分布与固定参考信息，哪些因素能够解释已报告现象？MBPP、HumanEval+、APPS Intro 是既有目标，不能把 AST 丰富度当语义策略证明。SSD n=64、共同合格分母、独立训练重复、生成到学习的传递仍欠证据。

## 查询与复用范围

2026-10-17 通过 web.run 执行9个检索字符串，另直接打开原始论文和官方代码来源。精确参数及完整工具返回保存在六份 search-capture 文件；索引列明每个请求。检索无服务端日期筛选，分析截止为2026-10-17；排序、索引版本、分页与请求命中数未由接口暴露，不伪造。保存的是工具实际返回，不能称为底层搜索引擎原始数据库。以已返回来源为边界，不声称实时搜索可逐条重现排序。

查询覆盖 iterated learning/self-distillation/synthetic-data self-training/self-consuming loops，spectral bias/subspace projection/proximal，以及 collapse/diversity/forgetting、temperature/truncation/accumulation 和 benchmark。关键词相近不证明同一算法：SPECTRUM 的原始序列 SFT 与正确演示条件化的 token 分布蒸馏须分开。

历史 LITERATURE_AUDIT.md（截止2026-10-02）的逐文版本和段落定位可复用为历史阅读记录；其中提及的 literature_audit_raw.json / literature_audit_background_raw.json 不在当前 inputs 清单，不能冒称恢复了旧查询。故本次新增可查验的查询捕获。历史 D2 不能自动成为本worker的新D2；新外部阅读主要是摘要、版本及官方仓库定位。未完成两轮无新增高影响来源的饱和检查或完整前后向引文扩展，不能用于终局创新性 ADVANCE/KILL。

## 覆盖与决策价值

| 家族 | 已读来源及定位 | 对当前问题的用途与限制 |
|---|---|---|
| 经典谱解释 | [Mobahi 等](https://research.google/pubs/self-distillation-amplifies-regularization-in-hilbert-space/)，官方摘要109–112行；NeurIPS 2020 | 作者在Hilbert空间正则化条件下分析重复蒸馏；不能把其结论直接转移为Transformer K/V语义保持定理。 |
| 失败与简单替代 | [Gerstgrasser 等 v2](https://arxiv.org/abs/2404.01413v2)，摘要15–19行 | 替换和累积训练数据的区别可形成竞争解释；累积带来的数据量和成本必须控制，不能直接宣称固定预算回放已有效。 |
| 最强简单基线候选 | [SSD v1](https://arxiv.org/abs/2604.01193v1)，摘要16–18行 | 温度/截断采样后标准SFT，是原始输出训练的重要对照。页面显示v2存在；本次没有审查v1→v2全文差异，不更新历史版本或宣称本项目基线已复现。 |
| 最近机制 | [SPD v1](https://arxiv.org/abs/2605.22675v1)，摘要16–19行 | 梯度得到低秩KV子空间、干预生成再SFT。摘要的“无外部信号”不替代对锚点来源、mask和层选择的核查；共享锚点projection control不自动等于忠实SPD。 |
| 多样性失败 | [Nicolicioiu 等 v1](https://arxiv.org/abs/2606.26091v1)，摘要16–19行 | 正确演示条件化、反馈偏置及模式集中是作者报告，不能证明本项目由reverse KL导致。原始序列SFT与其信息集不同。 |
| 社区引出的失败解释 | [Denser ≠ Better v2](https://arxiv.org/abs/2607.01763v2)，摘要及版本历史 | 作者报告持续后训练中的遗忘、漂移与格式放大；当前v2日期为2026-10-02。只建立核查线索，未读全文代码，不将格式解释判为本项目因果结论。 |
| 官方benchmark | [EvalPlus](https://github.com/evalplus/evalplus)，README版本/测试说明；[APPS](https://github.com/hendrycks/apps)，官方仓库定位 | 保留既有benchmark而非自建用例。EvalPlus记录过测试与任务修订，需冻结数据和scorer身份；仓库首页不构成scorer资格认证。 |
| 原生评分语义线索 | [HumanEval evaluation.py](https://github.com/openai/human-eval/blob/master/human_eval/evaluation.py)，搜索返回实际函数片段 | estimate_pass_at_k及样本数筛选可用于后续代码核查。当前master未锁commit，不能用作已经固定或执行的原生评分证据；n=16不能代替n=64。 |

本地静态读取 training.py 的 train_on_records 与 plan_token_exposure，以及 spectral.py 的操作种类定位，支持保留原始序列SFT、固定anchor replay、随机方向/等向衰减这些比较线索；未执行模块。历史审计的负面结果和134 training arm-rounds、24 transfer、3 decoder计划保留，未转为新任务或完成状态。

广泛搜索也返回新闻、百科、论坛、工具调用RL以及不同任务论文。新闻/百科/论坛不作技术主张依据；H²SD、SGCD、TurnSight、PPD只保留为边界线索，因额外奖励/提示/任务差异未纳入等信息强基线。不同命名不能证明功能碰撞或创新。停在L01已定位关键家族且剩余问题需要全文/实现核对的边界；不因命中数设总额度，也不宣称全领域饱和。

## 社区来源的实际状态

先读取 community-intake 报告和全部5张JSON源卡。用户选择enabled；最近已保存登录与真实详情读取为available。provider-handoff允许单worker串行读取，本次复用父级串行观察，新增MCP调用为0，未声称本次重新测试登录。旧一次搜索限制已被明确覆盖。

保留三帖：6a34f4ae 的正文说明、10条顶层评论及5条回复（还有评论未读，7张图片未读）；6a4293ea 的说明、1条评论与1条回复（1张图片未读）；6a126a17 的说明及1条评论（1张图片未读）。帖子数和评论数是已观察范围，不是配额。保留反对意见与不同解释，不推断共识。第四帖6ac60b6d为作者与摘要助手交互，排除；没有新增视频或宣传采样。

评论关于失败轨迹、教师偏差、多来源和校验的建议缺少实验设置，仅形成信息来源对照线索；复现担忧没有具体失败日志。两条论文线索已在本次通过原始arXiv页面核对标题、摘要与版本，支持相关性，不完成机制验证。评论借哥德尔定理推导训练结论没有适用前提，继续排除。源卡是父级观察记录，不伪装成原始全帖截图/完整MCP数据，也不把保存笔记当科学接受。

## 交接边界

根目录authorization.md读取失败后，已使用实际research-state/authorization.md；这是路径定位问题，未改变权限。安装技能与固定Harness版本不同，本次采用用户给定的固定程序规范。accepted_decision_ref仍null，无新的构造决策。新coverage严格继承X01已接受快照，五项义务均pending，保留旧证据和任务绑定。inspection_refs与repair_basis为空，无新native回执。审查者须实际读取本报告、查询捕获、源卡及索引哈希；tasks=[]仅请求独立验收本节点材料，不表示科学PASS或项目完成。
