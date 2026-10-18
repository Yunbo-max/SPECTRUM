# SPECTRUM 第二轮 Work Harness 研究快照

本轮使用真实 Work Harness 与 GPT-6-Astra，已有 worker / 独立 reviewer 调用。此包包含当前研究记录、社区来源卡片、报告和逐文件 SHA-256；不是已完成的第二轮结论。文献检索仍在继续，新增 GPU 实验尚未执行。

最新用户授权见 research-state/gpu-and-delivery-authorization-20261017.md；它覆盖历史记录中仅阅读、禁止 SSH/GPU/Git 的旧范围。原始记录未重写。当前执行目标已连接，Tesla T4 15 GB，检查时空闲；完整环境尚待资格检查。SSH 密码与连接私有文件未上传。

历史研究输入固定于 f7b661f593719d4f0a98a4db13dc33c0ad09824a；本交付分支基于较新的 8d11ac30d7dcce150599b71ee878eec1078f9ca2。不能把新分支代码自动当成历史实验代码。

小红书已恢复登录：逐条查看4篇帖子及可见评论，3篇保留线索，1篇排除；图片未读取，部分评论未穷尽。社区讨论不能替代实验或论文核验。详见 reports/community-intake-20261017.md。

本包不包含私有账号凭据、原始 agent 会话、运行中的 SQLite 数据库、工具输出对象库和本地 GPU 连接文件；这些记录中的本地路径/对象引用保留为溯源定位，不保证可从 GitHub 直接解析。新产物在后续同步时追加，不代表后台永久运行保证。

SSH 检查已取得 GPU/磁盘/解释器结果；完整探测 shell 最终 exit=2，来自末尾不存在目录的 ls glob，不能标为完整环境资格检查通过。

## 2026-10-18 更新
已按最新授权启用 repeat 模式、GPU native target、LaunchAgent 后台控制和自动故障恢复策略。最新状态见 reports/autonomous-activation-20261018.md；早期仅阅读限制已由最新授权覆盖。正式训练尚未开始，依赖/模型/数据准备和研究节点继续执行。

## 主机保护修复
2026-10-18 已部署本地主机资源守护，详见 reports/host-protection-20261018.md 和 operations/。部署后内存压力仍偏高，研究处于资源等待；这不是新增实验结果，也不代表已证明崩溃根因。

警告等级续跑条件已更正，见 reports/warning-continuation-20261018.md；内存压力2本身不再阻止轻量研究调度。

## B01远程验证与4090迁移
已增加显式授权的B01原生验证通道，研究目标切换为hn01的RTX4090；50项针对性及相关测试在该服务器通过。7项旧准入测试失败在修改前后均可复现，未宣称全套通过。部署与准备状态见 reports/B01-native-route-hn01-20261018.md。评分、训练尚未完成。

## GPU-first intake 插件更新
Work Harness 已更新并安装为 0.4.0-harness.3：先确认/实测 GPU，再判断阶段可行性。85 项运行时测试与 34 项插件打包测试在 4090 服务器通过；当前研究 pins 保留。详见 reports/gpu-first-intake-20261018.md。

## B01 配置阶段修正
Work Harness .4 已安装并显式部署本轮运行时：起始时确定 GPU，B01 配置上游资源并检查真实启动，评分资格留到后续节点。详见 reports/b01-upstream-setup-20261018.md。

## Latest: sustained phase Work Harness .8

See [phase autonomy update](reports/phase-autonomy-20261018.md), [source patch](runtime-fixes/phase-autonomy.patch), and `runtime-fixes/phase-autonomy-verification/` for actual GPU software checks, installed parity and quiet adoption receipts.
