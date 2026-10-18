# B01 配置阶段修正（2026-10-18）

## 用户要求与实现
用户要求 B01 配置官方/上游实际提供的资源即可，并明确下一次运行在开始时确定 GPU/环境，本轮内复用，不增加常规换机流程。

根因是自动化接入层把配置节点提前提升为完整评分资格论证，并为纯配置提交重复要求 inquiry。已将 B01 配置/启动标准同时送给 worker 和独立 reviewer；仅无新任务、无新原生结果且复用精确已接受决策的配置提交，可保留原决策。仍由实际独立审阅决定是否接受，不手动跳节点。

## 真实服务器配置结果
在已授权 hn01 RTX 4090 原生项目环境执行，startup exit=0：读取 MBPP full/test 500 条、ID 11–510、每条 3 个测试，保留 task367 setup；导入 torch/transformers/peft/accelerate/datasets/evalplus/improving 成功，`python -m improving --help` 成功。模型和数据 revision/路径、包版本、原始输出和命令见 research-state/B01-official-setup-20261018/。

MBPP 数据来自官方上游；实际执行器 `improving.verification` 明确标为 project_custom，不能标成官方执行器。MBPP+、sanitized 与 full/test 未混用。这次启动检查未生成模型输出、训练或执行候选程序；实际评分、行为/等价检查及执行隔离仍为 B03/评分阶段义务。

## 验证与部署
- GPU：65 项相关运行时测试通过（14.787s），包括完整接受/历史审计回放。
- GPU：5 项指引测试通过，34 项插件测试通过（48.205s）；84 节点登记检查 errors=[]。
- GPU：真实 setup report 与目标、命令、输出 pins 校验通过；独立静态复审无阻塞发现。
- 源码版本：8e6e29d（完整源码、插件 0.4.0-harness.4）。
- 运行时部署：3d423064b07a026c06296c2a9a82d1fcfab733cd。只部署运行时代码，历史 Skill .2/catalog pins 保留。
- 在无活动任务的边界，revision106→107 记录源码采用，107→108 通过 adopt_b01_setup 显式采用配置规则；旧任务、实验预算与接受历史保留。
- 本机独立插件 research-autopilot-harness .4 installed=true、enabled=true，所有 Skill/runtime inventory 哈希一致。其他五个插件未修改。
- LaunchAgent 已重新启动；B01 正式接受与后续节点状态以实时 worker/reviewer 记录为准，此报告不宣称 B01 已通过或训练已开始。

运行时数据库备份仅本机保存；Git 包不包含数据库、账号凭据、密码或原始 agent 会话。
