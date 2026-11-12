# 18 项已恢复问题 → 回复位置 → 证据

本表依据仓库摘要，不是原始评审逐字引文。源版本：0d9207e4422a6c98d02a37985271aef05d0cc3b3。数字见 [EVIDENCE_TABLES.md](EVIDENCE_TABLES.md)；对应逐题数据及计算摘要见 [evidence_numbers.json](evidence_numbers.json)。

| 评审/问题 | 已恢复的问题 | 英文回复位置 | 可用回答与明确边界 |
|---|---|---|---|
| w3G2 W1 | 梯度方向与普通衰减未分离 | 01，Orientation… | c01–c04/c45：soft 比 hard 的 C64/pass64 高；random/isotropic 更强，不主张方向必要；范数/谱匹配不等于输出 KL 相同 |
| w3G2 W2 | 正确解保留的重复性与 AST 指标 | 01，Repeatability… | c36/c01、c06/c07、c08/c09 三种子 C64 均增；共同题集 D4 +.262/.289/.300；算法语义标注未完成 |
| w3G2 W3 | 表达、soundness、novelty | 01，Contribution… | 明确经典 proximal 构造和参考梯度来源；有限 tau 的局部非零增益不证明全模型语义保留；原文和祖先文献还需对照 |
| FUKc F1 | 单模型/单种子 | 02，Trained models… | 三种子与 c14/c15、c18/c19；跨模型 C64 增益，不能声称各模型 pass64 都上升 |
| FUKc F2 | Plain 没有 50 个参考答案 | 02，Access… | c05 replay C64 7.936 vs Fixed 10.870；c27 40 references 稳定；只证明此 replay 控制未复现收益 |
| FUKc F3 | 训练 token/校准成本不一致 | 02，Training exposure… | c10/c11/c44 预算结果不利于 Fixed；配置目标非实际等 token，更非 equal compute；真实成本账本仍缺 |
| FUKc F4 | hard/soft 衰减不匹配 | 02，Attenuation… | c01–c04 的匹配定义与实际结果；不把方向控制解释成方向必要性证据 |
| FUKc F5 | AST 表面变化、control-flow 弱 | 02，Structural… | AST 与 control-flow 分开；主种子同题集 CF-D4 +.0029 vs AST-D4 +.2624；c26 无人工标签 |
| FUKc F6 | pass1、迁移、强 baseline | 02，Accuracy… | c30 SSD 与 c32 插值作为实质替代；保留 HumanEval+ 持平及 APPS 负结果，限定 trade-off |
| ygkV Y1 | tau=1 近各向同性 | 03，Shrinkage… | random/isotropic 的 C64/pass64 不弱；不主张方向必要，也不凭公式推断实际谱分布 |
| ygkV Y2 | tau、层位置、几何刷新 | 03，Strength… | c12/c13、c23/c24、c31 五轮；tau .5/1/2 有取舍，冻结首轮 operator 仍好；不声称刷新必要 |
| ygkV Y3 | temperature/top-p 与 SSD | 03，Evaluation decoding… | c20/c21/c46 证据为 Fixed 冻结评测；c28/c47 为单参数合成控制；c29/c30 同配方不当两个算法 |
| ygkV Y4 | 插值或 KL-to-initial | 03，Interpolation… | c32–c35 完整插值表与公式；未跑训练时 KL；原文“或/和”未恢复，不宣称完全满足原请求 |
| ygkV Y5 | 相同参考信息 | 04，Reference access | c05/c27 正面控制；c10/c11/c44 的不同预算负结果同时保留 |
| ygkV Y6 | 家族/种子、base-only、pilot extraction | 04，Trained replication… | 只用已训练配对；不将 20 格初始模型矩阵或改变 extraction 的 pilot 算作训练复现 |
| ygkV Y7 | 小 eligible 群体、APPS 不利 | 04，Transfer denominators… | 主实验共同 eligible 分母明确；历史迁移全题 pass16/C16 明确；不把 n16 写成 n64 |
| ygkV Y8 | literals/names、control-flow 弱 | 04，Transfer denominators… | 承认 AST 是结构代理，CF 增益较弱，语义标签未完成；不称“不同算法” |
| ygkV Y9 | SSD diversity 更高、Fixed pass1 更低 | 04，SSD and accuracy | c30 C64 12.048 > 10.870；Fixed pass1/pass64 更高；呈现取舍，不称全指标占优 |

## 回应完成与证据完成的区别

18 项摘要都已有具体回应位置，不再只有“计划补实验”的占位符。它们并非都得到支持原先强主张的实验：W1/F4/Y1 通过收窄方向解释回应；F3 的预算优势未建立；F5/Y8 的算法语义结论未建立；F6/Y7 的普遍迁移优势未建立。这些差异保留在正文，而不是把所有项目标为实验 PASS。

本版不承诺还会完成 c16、c26、c17 上传或 CGL。现成原件后续补齐时可更新对应段落，但不会凭执行状态填入效果数字。
