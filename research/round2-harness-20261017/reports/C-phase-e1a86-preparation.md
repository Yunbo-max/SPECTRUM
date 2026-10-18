# C 阶段实际恢复与数据准备

继承 .10 与既有 B 研究记忆。两次旧 native 尝试已终止；本次 e1a86 实际执行遇到 adapter 遗留全实验代码映射检查。e1a86b 只将该检查按 adopted .10 的阶段语义限制在 export，保留实际 descriptor、部署、源文件、context、前序和输出身份核验。

Controller 回执 8a95ed560f384e939ea5d8b5948e6afd 已确认 completed。hn01 prepare exit0，native stage 耗时约6.99秒；这不是含传输与监督的总研究成本。模型资产未重下载，未重新安装环境。

原 full/train374 中3条提示与 full/test 重叠，按已有规则去除；剩余371分为训练291、校准50、验证30。full/test500均保留，原始标签和样本身份保存在归档。此准备不包含模型推理、评分或准确率结果，也不证明旧F/P/A选择。

B02问题仍是采样/过滤/信息增益等解释与谱机制是否可区分。复用 method-basis-v3：SSD作者生成配置与项目plain存在实质差异，SPD作者实现未确认，SDPO-CL依赖反馈条件化，不能直接等同raw序列NLL。社区两张新增卡已读取，未读图片与缺乏实现细节的边界保持。没有新科学问题契约或B05支持。

实际哈希见 research-state/C-phase-e1a86b/readback.json。后续校准由同一worker串行执行；强方法实现、评分、干预、训练随机性、S04及独立确认义务保持。

实测补充：batch64校准完成，64×613，peak reserved 5402263552 bytes，headroom19351142400 bytes；资源profile固定任务也完成。三项成功controller receipts：8a95ed560f384e939ea5d8b5948e6afd、a5b3c5086b304e4ab2e3ab4e79446e0a、d394b5a512ad4e1f950dd3b316b8cc3c。训练和评分均未合格。评分接口依赖的静态源码核对见 scoring-dependency.json；没有冒充执行过scorer或verifier测试。检查点保留所有16项义务及决策链，待受支持的评分集成恢复本C阶段。
