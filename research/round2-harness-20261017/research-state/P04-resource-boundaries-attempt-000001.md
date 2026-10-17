# P04 资源、授权与调度边界

绑定 spectrum-round2 / cycle 1 / P04 / attempt 1；当前节点材料待程序独立审查。证据索引为 P04-evidence-readback-attempt-000001.json，测量原始输出为 P04-resource-observation-attempt-000001.json。

## target_authority

本轮是隔离工作区内的阅读、研究笔记与JSON bookkeeping。实际控制工作区为 /Users/yunbo/Documents/ssdforever/harness-runs/spectrum-round2-20261017/project；输入在 inputs/，支持性写入仅 research-state/、reports/。固定skill源位于相邻 source/skills/research-autopilot，采用 source revision a17842f9c8eb5042e99e392fa5414cb0791772a2 和输入合同中的skill digest，均不编辑。原SPECTRUM不修改。

实际控制主机观测为 Darwin 23.2.0 arm64；本次轻量读取/记录使用 /opt/homebrew/opt/python@3.14/bin/python3.14。agents.json 指向既有 /Users/yunbo/.nvm/versions/node/v24.21.0/bin/codex 命令适配器。model-activation记录用户选择GPT-6-Astra及既有订阅登录；本worker未查看凭据、未改账号或模型配置。这些是控制侧路径，不是远程训练环境。

当前合同 native_target_ref=null；最新授权不含GPU、SSH实验、训练、推理基准、科学测试、付费API、安装、发布或消息。当前可授权实验GPU数为0，GPU小时为0；实际硬件型号、物理数量、每卡显存、远程环境/路径/排队配额未知，不能把“无授权”写成“没有硬件”。本节点没有需恢复的已授权远程任务，不扫描SSH配置或探测未授权远程主机。未来若实验另获授权，必须取得具体目标和当前分配，不能把本地控制机当GPU机。

## resource_bounds

| 项目 | 来源与权限边界 | 当前测量或保留未知 |
|---|---|---|
| CPU | 只允许轻量编排、读取、笔记；无科学计算授权；未指定数值CPU总配额 | sysctl被沙箱拒绝，逻辑CPU及可用slot未知；未建立资源lease |
| RAM | 未给数字总配额；不继承其他edition的4GB默认值 | sysctl总内存读取失败；vm_stat原始页计数已保存，不推算为本任务可占用RAM，不以缓存可回收假定准入 |
| 磁盘 | 仅隔离项目两类输出目录；无下载/存储总额度承诺 | 22:40:34 UTC测量 available=9,266,548 KiB，df使用率98%；为共享卷瞬时快照而非预约空间；小型笔记已实际写入 |
| GPU | 最新用户明确未授权实验，允许实验设备数0、GPU小时0 | 硬件/显存/远端容量未知，未运行科学负载 |
| 时间 | 最新user-continuation撤销六次、1800秒累计上限；不再自设总次数、时长、帖子配额 | 当前合同max_rounds=null，修订后总max_seconds=null；worker/reviewer各300秒、verifier30秒为进程watchdog，本次传输deadline也不是项目期限 |
| 金钱/API | 外部付费额度0；既有Codex订阅可消耗，货币报价不适用 | controller记spent_cost=0、reserved_cost=0是运行时账面值；真实订阅token/费用/剩余额度未知，不声称免费 |
| 人员 | 用户每周投入小时未知，本阅读范围无需重问 | 父监督者负责程序控制和社区来源；本worker仅P04；既有程序另行独立reviewer验收 |

13份历史终态回执逐一哈希核验；实际秒数合计920.7690774220973，与当前输入累计一致。包含最初两次模型不支持失败及第三次执行完成但契约拒绝；失败成本不抹去。输入reserved_seconds=0、reserved_cost=0是交接快照，不表示正在执行的本次调用不花时间；本次实际耗时由程序终态结算，未自行改账。全部历史任务为source_read/math_review，无已登记实验；这不宣称全主机没有其他用户负载。未创建CPU/GPU预约或释放未知任务。

sysctl权限错误已在本轮用户可见输出报告。影响仅为控制机容量未知；不升级权限、不启动需容量准入的工作。当前文件读写实际成功，后续如空间写入失败应保存已有状态并报告，不删除其他项目换空间。遥测和哈希操作是读状态/记账，不是科研实验或基线资格测试。

## serial_policy 与依赖分工

沿用max_workers=1，worker完成后由程序调用独立reviewer；不另启consumer、不并行委派。父监督者独占小红书串行请求，worker复用落盘观察。较新的 xiaohongshu-login-restored-20261017.json（22:39:38 UTC）记录已登录、search_in_progress=true、successful_posts_read=0，覆盖旧登录失败状态但不消除失败历史；未观察搜索结果/评论就不称已读取。父级应核对原搜索身份后继续，不由worker重复请求。访问失败仅暂停该来源，不阻断论文/代码。

一般实验政策保持全项目最多一个活动实验program、不同实验/seed/独立评分顺序执行、禁止GPU分享；本范围实际准入为零。若将来另获授权，应先核对未决任务、真实目标容量及完整成本，再按原生支持批次从大到小校准；当前不做校准或人为例外。任务已结束、8小时软汇报或24小时任务边界均不重置累计账本，也不代表全目标完成。300秒report设置同样不能成为科学任务超时或重新续费依据。

history恢复phase=active、pause_ref=null，当前继续有明确用户来源。未来明确暂停必须保留当前游标、任务身份、成本与未完成义务；只有有来源的恢复才清除暂停。程序拥有接受与前进权，worker不选择后继、不修改状态。父程序上次consumer观察不保证未来永续；本次真实调用证明本次执行，后续存活仍须父级观察。

此前I04独立审查已实际接受其退出标准；这不代替P04独立审查。P04依赖顺序为读取授权/历史与源规范→控制侧状态观察→固定证据提交→程序独立审查。本次inspection_refs、repair_basis均空，无新native回执或未启动取消；tasks=[]表示当前P04证据可送审。decision_ref仍null，不制造v4科研决策。五项覆盖义务全部pending，历史科学负证据、原始输出/语义标签/SSD n=64及对照缺口不变；新coverage只延续证据，不代表研究报告完成。
