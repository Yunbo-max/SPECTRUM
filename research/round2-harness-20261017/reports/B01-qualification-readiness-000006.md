# B01：资格输入与当前原生能力只读获取

任务 `spectrum.B01.qualification-readiness.000006`，run `ffae14f31eb14b388040f50b10272ae7`，cycle1/B01/attempt6。**本次获取完成，评分资格仍未成立，B01 不可据此接受。** 所有19项输入哈希一致；本报告、证据索引和单独命令回执分别保存。既有程序负责后续独立审阅，本任务没有修改游标或自审。

## 历史输入查找结果

依据 `inputs/spectrum/docs/EXISTING_EVIDENCE.md` 与 `observed_results.json` 的16项 Git blob/集合定位，检查专用交付工作树和授权远端 `/root/rivermind-data/spectrum-harness/{project,SPECTRUM}`。逐目录文件清单、大小、有限小文件哈希和 Git 对象检查均保存于证据目录。

- 交付工作树与远端 SPECTRUM 均无 `results/`、`paper/iclr2027/source-data/`、`data/`、`runs/`、`outputs/`。检查了 `research/audit/`、`docs/`、`experiments/`；保留的主要是摘要、设计和来源资料，没有定位到真实预测 JSONL、逐样本 verdict 或同输入双评分执行回执。
- 远端 `project/` 顶层为空；它不是 Git 工作树。远端 SPECTRUM HEAD 为 `458db005ab1fb3cbdd0eac98569ceb572836878b`。交付 HEAD 树及两端对象库均未发现16个历史 blob，历史提交 `45195e866162df1cdf9de0169d2bf17347eb6abf` 也不可读取。没有 fetch、Git 写入或扫描其他卷。
- 两端现存审计摘要可继续作为**历史转录证据**，不能作为原始预测或重新执行的结果。远端 observed_results 的 SHA256 与本地固定输入一致。SEP20_EXECUTION 文档明确原始生成程序不进入 Git 结果包；这解释了来源恢复仍可能需要原始存储，但不证明数据已丢失。
- 历史 sandbox 报告另指 `/root/rivermind-data/SPECTRUM`，当前任务给出的目标授权是专用 harness 根；没有将历史路径描述自动当成新的目录访问授权，也没有读取 private/seeds。此报告不作全盘不存在的断言。

本次阅读了 EXISTING_EVIDENCE 的历史比较结果和摘要中的部分数值，保留确认曝光；不得将这些已看结果用于未暴露确认或选择有利样本。没有逐样本语义审阅或新标注。

## 当前远端观察（2026-10-18 10:02–10:05 UTC）

先核对旧 PID410/499，当前进程表无这两个 PID；asset-exit=0。dependency-process 仍是旧 launched 文案，但 dependencies.log 含 Successfully installed，venv 元数据存在。没有重启下载或安装；无依赖安装退出码单独回执，不能将日志冒充实时功能资格。

| 项目 | 真实只读观察 | 限制 |
|---|---|---|
| 主机/内核 | jupyter-txs904ckr2zqsww2，5.15.0-186-generic | 不是历史主机身份等价证明 |
| Python | /opt/conda/bin/python，3.12.13；venv配置同版本、隔离system-site-packages | 仅标准库元数据观察，没有导入模型或评分包 |
| venv包元数据 | torch2.7.1、numpy2.5.4、datasets3.5.1、evalplus0.3.1 | 版本元数据不证明GPU/评分可运行；不借用旧system torch GPU测试 |
| cgroup | memory.max=62277025792；memory.current=12593229824；cpu.max=1000000/100000；pids.max=max | 当前读数，不是任务分配或峰值实测；proc/sysfs文件stat大小0不代表内容为空 |
| 数据盘 | 可用41026846720字节 | 没有预留或容量承诺 |
| 隔离工具 | PATH未找到bwrap/bubblewrap/nsjail/firejail；unshare/prlimit/setpriv为util-linux2.37.2 | 只运行版本查询，未调用namespace创建或隔离工作负载；PATH缺失不是全盘未安装证明 |
| 内核线索 | max_user_namespaces=2060969；unprivileged_userns_clone=1；Seccomp=2/filter1；NoNewPrivs=0；namespace链接已记录 | 开关和现有过滤器不能证明允许创建所需namespace，亦不证明文件/网络隔离有效；内核config两个常见位置均不存在 |

历史 sandbox-recheck 曾报告 bwrap/unshare 因namespace权限失败。保留其原身份、旧来源和失败，不把当前配置线索当作推翻历史失败的成功测试，也不据历史失败宣布现主机永久不可用。未运行Docker或替代容器、sudo、内核修改、测试、scorer、生成代码、模型或GPU工作负载。

## 可复用输入与未决边界

证据 JSON 给出实际哈希和路径：Google原始MBPP JSONL、固定HF full/test Parquet、已解码读取投影、500题静态映射、固定BigCode与项目data/verification/metrics源码。它们支持后续准入后的原生资格设计；参考code/test是基准原始材料，不是已经运行且有结果的资格样本。

必须保留 full/test500、ID11–510、逐题样本数及完整失败分母；原setup顺序尤其ID367不得省略，challenge不能静默加入主终点，题面/参考AST签名信息与BigCode提示差异不得抹平。不得造题、改参考标签、用软件fixture替代资格样本或因没有真实历史预测而填写虚构哈希。BigCode仍是第三方候选，official executable=null；faithful未qualified；native_eval_contract未冻结；live replay未执行。语义策略证据仍缺，AST只能支持代理范围。

下一项真正缺失的是**获准的原生隔离资格及后续同输入评分核对**，包含真实调用身份、环境、所有失败、逐样本结果和分母；若恢复历史预测，须补原代码/数据/模型/提示/采样协议与执行来源。缺原官方执行器仍需独立审阅明确第三方适配依据，不能改标签为official。

当前第24轮程序输入的 allowed_actions 为 `math_review, math_work, source_read`，不含 native_harness；本任务更明确禁止测试。这是当前动作准入缺口，不能以source_read包装执行，也不能重复同一已穷尽位置的读取来假装推进。交回同一B01程序处理该缺口，未选择后继节点。独立训练/导出是否可分离仍依实际代码和另外的程序准入，本次不启动。

## 历史、社区与操作异常

保留000002 never-started/cancelled、000003 completed、round22重复引用拒绝及round23维护中断86.854803秒；它们不是科学反证。五张社区源卡已发现并读取摘要及范围，哈希留索引；没有新MCP调用、图片或缺失评论读取，社区讨论不能资格化评分器。

初始配置路径猜测和结果目录查找未命中，随后定位实际根目录的program合同；历史Git树读取失败已用逐对象查询明确记录。远端project非Git是当前布局观察，无修复或重建。已通过本轮可见输出报告这些缺口。系统目录安装的通用skill与本任务固定Work Harness入口不同；本任务以注入的固定入口、规范和只读任务合同为准，没有迁移策略。主机guard阈值、现有消费者和账户配置未更改。全部支持性写入仅在本项目research-state/和reports/。
