# SPECTRUM 第二轮 Work Harness 研究快照

本轮使用真实 Work Harness 与 GPT-6-Astra，已有 worker / 独立 reviewer 调用。此包包含当前研究记录、社区来源卡片、报告和逐文件 SHA-256；不是已完成的第二轮结论。文献检索仍在继续，新增 GPU 实验尚未执行。

最新用户授权见 research-state/gpu-and-delivery-authorization-20261017.md；它覆盖历史记录中仅阅读、禁止 SSH/GPU/Git 的旧范围。原始记录未重写。当前执行目标已连接，Tesla T4 15 GB，检查时空闲；完整环境尚待资格检查。SSH 密码与连接私有文件未上传。

历史研究输入固定于 f7b661f593719d4f0a98a4db13dc33c0ad09824a；本交付分支基于较新的 8d11ac30d7dcce150599b71ee878eec1078f9ca2。不能把新分支代码自动当成历史实验代码。

小红书已恢复登录：逐条查看4篇帖子及可见评论，3篇保留线索，1篇排除；图片未读取，部分评论未穷尽。社区讨论不能替代实验或论文核验。详见 reports/community-intake-20261017.md。

本包不包含私有账号凭据、原始 agent 会话、运行中的 SQLite 数据库、工具输出对象库和本地 GPU 连接文件；这些记录中的本地路径/对象引用保留为溯源定位，不保证可从 GitHub 直接解析。新产物在后续同步时追加，不代表后台永久运行保证。

SSH 检查已取得 GPU/磁盘/解释器结果；完整探测 shell 最终 exit=2，来自末尾不存在目录的 ls glob，不能标为完整环境资格检查通过。
