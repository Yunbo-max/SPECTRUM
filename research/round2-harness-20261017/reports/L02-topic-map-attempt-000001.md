# L02 主题地图与双向引用扩展

当前绑定为 cycle=1 / L02 / attempt=1。仅提交文献身份与主题地图，独立审查由既有程序另行执行。未启动实验、选择后继或改变科学门槛。所有捕获、社区卡和前序资料的真实哈希见 `research-state/L02-evidence-index-attempt-000001.json`。

## 版本身份与独立证据轴

[Mobahi arXiv:2002.05715v3](https://arxiv.org/html/2002.05715v3) 的标题下注明确说明这是 NeurIPS 2020 同名论文的更详细版本（捕获8，行57–61）。[官方论文集](https://proceedings.neurips.cc/paper_files/paper/2020/hash/2288f691b58edecadcc9a8691762b4fd-Abstract.html) 确认作者、标题和正式出版身份（捕获7，行0–6）。据此建立同一工作链接，而非仅按标题相似合并；扩展版与会议版仍保留独立版本、阅读范围和复现状态。arXiv v3只读元数据、版本说明及引言/问题设置片段；会议版另读作者机构提供PDF的前3页片段，未审计完整证明、附录或代码。均无本项目复现回执，distinction未知。

SSD 2604.01193v1、SPD 2605.22675v1、SCoder 2509.07858v1、SD-Zero 2604.12002v1、CRISP 2603.05433v7、Nicolicioiu 2606.26091v1、iSDFT 2609.24646v2保留历史审计中的原生版本和原有D2阅读定位，不冒充本轮重新精读。SSD已知有v2但差异未核查；Denser 2607.01763v2只保留已读摘要。没有可靠最终版本身份链接的工作继续标为未解决，不猜DOI、会场、获奖或接受状态。arXiv DOI不是会议发表证明。

Gerstgrasser 2404.01413v2本轮新增相关正文与引用片段读取；正式发表身份未知。Shumailov 2305.17493v3只读元数据/摘要，Nature候选页面读取失败，不能凭记忆把两个身份合并。Borup与Andersen的NeurIPS 2021会议PDF可直接定位；本轮读摘要和§2，不把另一个arXiv页面的同名结果自动合并。全部新读论文均无本项目复现；已有SPECTRUM运行也不是这些原论文的复现证据。

## 主题与机制地图

| 家族与相邻术语 | 可定位来源与关系 | 对SPECTRUM的决策意义及边界 |
|---|---|---|
| kernel/Hilbert自蒸馏、谱正则化、iterated learning | Mobahi扩展版引言、会议版前3页；与diffusion/boosting的关系仅作作者指出的历史术语线索 | 正则化谱与K/V谱并非同一对象；不能推导正确程序语义保留。 |
| 加权真实目标、固定参考信息 | Borup–Andersen 2021 §2明确引用并扩展Mobahi，加入ground-truth targets；捕获7，页2行108–115 | 为直接anchor SFT/replay的必要性对照提供理论动机；核回归设定不是Transformer保证，代码与完整证明未核查。 |
| model-data feedback、synthetic replacement/accumulation | Gerstgrasser v2 §1、§2.1、§2.3和Appendix A；引用Mobahi、Shumailov与Dohmatob | 训练数据历史、真实数据保留和总曝光是竞争因素。累积同时改变数据/步数；VAE段仍报告细节多样性丢失及条件冲突，不能写成无条件避免任何坍缩。 |
| raw-sequence SFT / SSD / sequence-level distillation | 历史审计SSD §2–4；SPD §2和参考文献[3]、[14] | SSD是必须资格核对的强简单基线；原始序列训练不同于token-distribution KL。Vanilla SD不能改名SSD。 |
| representation steering、capability subspace、KV projection | SPD v1 §2–3.2，参考[3]连到SSD；捕获3 | calibration含prompt-answer，correctness-span梯度、SVD、生成hook再移除后SFT。作者“无外部信号”的表述不消除标注校准信息。共享anchor投影不自动等于原论文复现。 |
| 正确演示条件化OPSD、reverse KL、遗忘/格式偏置 | 历史Nicolicioiu科学阅读定位；Denser摘要及社区卡 | 作为相邻机制，保留信息集/目标差别。评论提问不是因果结果；不得直接解释本项目AST变化。 |
| 迭代代码合成、critic/verifier、策略数据筛选 | 历史SCoder、SD-Zero、CRISP，及SPD参考[1]/[8]/[10] | 外循环迭代不是新颖性；额外奖励/验证信息须单独计成本，不可包装等信息基线。 |

## 双向引用扩展的实际范围

前向从种子Mobahi找到并读回两个实际引用者：Gerstgrasser v2 §1/Appendix A（捕获2，行77、268、289–294）和Borup–Andersen 2021 §2（捕获7，页2）。后向从这两篇回查Mobahi原文与正式版本；Gerstgrasser参考文献的Shumailov条目（行275）进一步打开2305.17493v3元数据。另沿SPD参考[3]验证SSD被引用，沿[14]记录Kim–Rush序列级蒸馏为待读分支；[4] 2604.13016、[6] 2504.01738仅为实际书目线索，尚未核验其全文结论。引用边只证明文献联系，机制等价仍须计算规则核验。

这不是全域引文图。两条Mobahi前向分支及SPD后向分支覆盖了当前有决策价值的理论、原始代码SFT和反馈机制；没有完成所有种子的前向索引遍历、两个无新增批次、正式版本差异或全实现审计。搜索结果量、相同标题和书目中出现的ID不作全面覆盖或同一工作的依据。

## 未决义务与社区边界

复用并逐张读取community目录5张JSON及intake。三条真实讨论保留原帖/评论/推断区分；图片未读和剩余评论沿用源卡。无新增MCP请求，未重新验证登录。排除摘要助手交互帖与缺少前提的哥德尔论证。保存的源卡是父级观察，不是原帖完整数据或科学接受。

仍待：SSD v2和原配方资格、SPD masks/layers/代码、条件正确共同分母、n=64强基线、独立训练重复、生成到学习传递、AST到语义桥接、native scorer版本和冻结确认。既有SSD占优/不利结果及134 training arm-rounds、24 transfer、3 decoder历史计划保持原状，不计为新增执行或完成矩阵。

本轮Nature内部错误、NeurIPS virtual robots限制、arXiv PDF cache miss均保存在捕获6/7；HTML扩展版成功读取只解决身份核查，不修饰先前失败。全目标五项coverage义务保持pending并继承已接受L01快照；decision_ref仍null。inspection_refs和repair_basis为空，无新native回执。材料供程序独立验收L02，非创新性、方法效果或全目标PASS。
