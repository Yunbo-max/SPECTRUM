# P02 实际资产与可信度盘点

绑定：spectrum-round2 / cycle 1 / P02 / attempt 1。逐文件路径、SHA-256、检查范围和原始回执见同目录 P02-asset-inventory-attempt-000001.json。11 个 SPECTRUM 快照文件全部匹配 inputs/provenance.json；这验证快照字节身份，不验证上游科学结论。

## 当前定位

快照提交 f7b661f593719d4f0a98a4db13dc33c0ad09824a；历史审计依据上游 45195e866162df1cdf9de0169d2bf17347eb6abf；运行时固定 c31f163c5044dc8ca9b810e98e6c3b4862b0fdc6。三者不可混称。provenance 说明原项目另有未提交 batch 配置，本输入只含已提交文件；未检查或修改原项目。

现有 README、四份 docs、三份 audit JSON 和三份 Python 文件是可阅读资产。main.tex、原始 CSV/生成程序/评分日志、数据与权重仅有引用或完全未提供；审计 JSON 的 Git blob/sha256 是保留的查找线索，尚未从对应对象取回验证。完整 pipeline、校准实现、配置、官方 scorer 和脚本不在快照，故三份源码不足以认定端到端实现正确。没有本次训练、测试或评分结果。

## 证据层级

- authored：FINAL_EXPERIMENTS 和 README 定义后续固定矩阵；四模型五基准计划不等于已执行训练比较。CORE_AUDIT 自述有历史 source-only reviewer，但本地没有其独立原始评审回执，维持历史报告层级。
- historical reported execution：EXISTING_EVIDENCE 与 observed_results 记录 MBPP 单训练轨迹、n=64 终点评估、SSD n=16 continuation 和迁移；此处没有原始程序、数据、scorer 回执，不能升级为本轮复现或独立科学确认。
- independently checked：程序 P01 attempt 4 的独立 reviewer 实际输出及 receipt、acceptance 均存在；其接受范围只是目标/义务/终点登记，不覆盖实验真实性、P02 或全目标。
- missing：SSD n=64、独立训练重复、自然案例链、语义标注、几何/信息/token 控制、generator-to-student 证据仍缺。metrics.py 的 implementation_proxy/control_flow_proxy 明确只是语法代理；strategy_retention 要求稳定标注，缺失不能填零。
- unknown：原项目当前作业、真实数据/权重可用性、GPU/评分环境未检查，也不属本轮执行授权。快照外不存在与未取得是不同判断。

历史反面信息必须保留：SPECTRUM 的 AST 丰富度为部分保留，pass@1 相对训练对照未满足原记录非劣标准；SSD n=16 的 C16 与边际 D4 更高；APPS 无条件 C16/pass@16 点估计不利。D4 须用共同合格分母，不能据边际值推导配对差异。父级 source-notes 中的共同合格 APPS D4 和 control-flow 区间是未在本节点重新核验的阅读摘要，不把它们混作原始输出或宣称无语义效应。AST 不能证明算法多样性，五轮不能当五次独立重复。novelty/Natural Gate 0 仍未通过。

## 恢复与重试边界

已读取 history 的全部五份 receipt：worker 1/2 因模型不支持失败，保留终止与清理说明；worker 3 进程完成但 ContractError 拒绝；worker 4 与 reviewer 4 完成，P01 acceptance 存在。实际累计已结算 208.32831061072648 秒；当前 invocation 使用量未结算。原上限 1800 秒、6 次 worker、每次 300 秒不变，当前为第 5 次 worker。模型选择/激活和写入范围记录已读，不改账号、模型、运行时或配置。

当前 packet 控制器任务为空，history 中五项均终态；本次为已知运行中的 planner 000005，不把“空任务表”解释为没有当前调用。无已分配 native 任务、inspection_refs 或 repair_basis，也无已接受 v4 决策。不重试任何旧运行，不新建程序，不启动第二个 consumer；历史 consumer 观察不保证未来自动续跑。仅程序决定验收与游标。

小红书已启用；inputs/source-notes 记载父级登录成功、三次并行搜索超时且无帖子读取。本次 P02 不进行 recovery/search，未消耗隔离项目的一次串行尝试，也不把历史超时计为无相关讨论；后续若执行须先持久化并复用观察。未发生可选来源缺失阻断资产盘点。

## 提交范围

P02 三项发现具备固定证据供程序另行独立审查；不自行宣称接受。coverage 后继保留全部五项 pending 义务与空 experiment_contracts，链接当前已接受 coverage；restore-evidence 增加本次盘点证据，原始证据和完整科学恢复仍未完成。没有新方法选择，decision_ref=null。没有当前节点所需的额外执行任务，tasks=[]；这不意味着第二轮中文决策报告或研究目标完成。
