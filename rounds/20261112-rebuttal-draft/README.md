# SPECTRUM rebuttal 第一版：以已有结果进入写作

日期：2026-11-12。对象：ICLR 2027 submission 45902。

**状态：供作者确认的英文草稿，尚未提交 OpenReview；未修改已提交的匿名 PDF。**
本轮按作者“目前证据足够，开始 rebuttal”的决定转入写作，不新增实验或改动训练代码、case 编号、历史结果及运行目录。

## 写作主线

> Fixed SPECTRUM 在主协议的多轮自蒸馏后，比 Plain 保留了更多正确实现的结构变体；这一收益在三个配对种子及两个已训练扩展模型上方向一致。部分设置还提高高 k 成功率，伴随明确的单样本准确率取舍。

重点展示三种子 C64 **+34.3%**、pass@64 **+1.13 个百分点**；跨模型 C64 **+38.2% / +17.7%**；相同参考答案回放没有复现主协议中的 richness 收益。

小幅下降可以按收益与代价准确解释。当前没有非劣效检验或等价界，正文不把下降写成“无差异”或“统计不显著”。方向控制、预算控制及强替代方法是审稿人直接问到的实质问题，在对应段落简短回答，不能归入“小幅下降可忽略”。

## 英文回复文件

| 文件 | 用途 | 预计词数 |
|---|---|---:|
| [00_COMMON_RESPONSE.md](00_COMMON_RESPONSE.md) | 面向全体审稿人的共同结果摘要 | 约 280 |
| [01_REVIEWER_w3G2.md](01_REVIEWER_w3G2.md) | 重复性、方向与衰减、方法和理论范围 | 约 480 |
| [02_REVIEWER_FUKc.md](02_REVIEWER_FUKc.md) | 模型/种子、信息公平、预算、指标与迁移 | 约 470 |
| [03_REVIEWER_ygkV_PART1.md](03_REVIEWER_ygkV_PART1.md) | 方向、敏感性、解码、插值 | 约 450 |
| [04_REVIEWER_ygkV_PART2.md](04_REVIEWER_ygkV_PART2.md) | 参考信息、重复性、迁移/指标、SSD | 约 470 |
| [REVIEWER_COVERAGE_ZH.md](REVIEWER_COVERAGE_ZH.md) | 18 项已恢复问题逐条映射，供作者核对 | 内部文件 |
| [EVIDENCE_TABLES.md](EVIDENCE_TABLES.md) | 数据表、来源、边界、历史扩展 | 内部文件 |
| [evidence_numbers.json](evidence_numbers.json) | 36 个已上传 metrics 的摘要、文件哈希、共同题集 D4 和三种子均值/SD | 内部文件 |

00–04 文件仅含英文评论正文，未放入可识别作者的 GitHub 链接、机构或姓名。数字的源路径与解释放在内部文件。词数只是当前草稿规模，不代表已核验 OpenReview 输入框的实际字数限制。

文档与算术复核记录见 [SOURCE_REVIEW.md](SOURCE_REVIEW.md)。

## 问题原文的状态

当前仓库及本轮定向检索只恢复到 w3G2、FUKc、ygkV 的 **18 项 concern summaries**，原始 OpenReview review bodies 和 note IDs 尚未取得。索引来自 [原问题映射](../../experiments/iclr2027_rebuttal/reviewer_case_mapping.json)，最早记录为 d033641。

正文按问题主题作标题，不伪造逐字引文、评审赞扬或“已回答原文每一个问题”的声明。特别是插值与 KL-to-initial 的“或/和”关系，仍需对照原文。原文缺失不妨碍先确认本版论证与表达。

## 证据版本和实际工作

写作依据固定在 **0d9207e4422a6c98d02a37985271aef05d0cc3b3**。本轮读取已保存 JSON/CSV、源码与配置，计算描述性均值、样本标准差和共同 eligible 题集的均值；未运行项目模块、训练、模型推理、程序验证或新的显著性检验。

主要数字来自 [2026-11-09 逐题指标](../20261109-local-results/metrics)。保存指标的算术可复核，但本包不补造未上传的 checkpoint lineage、原始生成程序或运行时成本账本。

历史 7B/Llama 和 n128 记录在 EVIDENCE_TABLES 中单列。11 月 12 日报告中的外推轮次、只有“完成”声明但没有数字的 c17，以及 cg00–cg15 均不作为本版已证明收益的依据。Fixed 仍是原论文方法；Learned 单列为后续增益设计扩展，CGL 不进入已验证贡献。

## 论文措辞建议（尚未写入已提交 PDF）

1. 将中心结论限定为 correct structural richness / correct-implementation retention，并同时给出 pass@1 与 pass@64。
2. 明确 proximal construction 的经典性质、参考梯度来源以及有限 tau 下的局部满秩性质；去掉“已证明谱方向必要”或“保证语义多样性”的解释。
3. 在主结果附近给出三种子表；对直接针对的方向、信息、预算、解码/插值和迁移问题保留决定性对照。
4. 方法叙述写明：干预发生在生成数据时；恢复生成权重后进行普通 SFT；原生学生评测不需要谱干预；训练生成结果没有正确性过滤。
5. 原稿主线、历史扩展与新方法的结果分别标注。不要把历史五轮结果、当前十轮中的外推值以及 Learned/CGL 混成同一轨迹。

## 会议信息与最后核对

已读取 [ICLR 2027 Author Guidelines](https://iclr.cc/Conferences/2027/AuthorGuidelines) 和 [Dates](https://iclr.cc/Conferences/2027/Dates)：作者讨论截止为 11 月 18 日；rebuttal 修订主文可用 10 页；应保持双盲。指南说明每条 comment 有字数上限但评论数量不限，未在本轮取得实际表单上限。

提交前还需核对原评审的准确措辞、引用祖先方法的准确文献、实际匿名稿对应位置，以及原运行身份和成本账本。这里的“需核对”是作者提交文本的事实校对，不是要求重新扩展一批实验。评论只在作者明确授权后提交；本轮交付为仓库草稿。

## 本轮决策记录

作者已选择停止自动扩展、开始 rebuttal。完成的写作工作与缺失证据分别记录；本包不声明科学验证全部通过或论文必然录取。下一步是作者确认措辞，并将合适的段落对照实际匿名稿与原评审使用。
