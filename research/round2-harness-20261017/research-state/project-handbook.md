认证复查 2026-10-20T11:23:49.242202+00:00：原密钥仍被拒绝（exit255）；GPU执行当前受SSH认证阻塞，远端安装/下载/bootstrap状态未知。需要服务端恢复原授权公钥登录或提供更新后的连接信息；未更改Harness或启动替代任务，无新模型结果。

认证诊断 2026-10-20 11:22:45 UTC：SSH verbose事件确认客户端实际提交公钥，服务端继续要求publickey/password并最终拒绝；没有Server accepts key事件。已仅保存过滤后的认证事件到remote-auth-diagnostic.json，不保存完整verbose日志或密钥指纹。故不是仅因未指定密钥而失败；服务端授权/账户/端点原因仍无法从客户端确定。需要恢复SH02原授权登录，才能核对原远端任务；不推断进程终止。无新增模型结果，未修改Harness。

连接复查 2026-10-20T11:21:42.200073+00:00：显式原授权密钥登录仍Permission denied (publickey,password)，exit255。远端进程未能核对，未启动新任务，无新模型结果。连接恢复后核对原boot/PID和完成marker；此轮仅更新本地恢复记忆，最近交付95d4256。

## SH02 端口恢复但认证失败（2026-10-20 11:20 UTC）

11:20:03别名连接从Connection refused变为Permission denied (publickey,password)。11:20:14显式指定原授权key、IdentitiesOnly=yes、BatchMode=yes再次认证失败；本地key存在且权限0600，未输出密钥内容。证据remote-access-recheck.json和remote-auth-recheck.json。无法读取boot ID或核对安装6718/bootstrap1864/下载6833；所有远端状态仍未知，不能推断主机重启、任务停止或完成。未启动替代实验，未修改SSH配置或Harness。需要SH02恢复原授权公钥登录后才能核对并继续；没有新增模型结果，研究未完成。


连接复查 2026-10-20T11:19:10.383029+00:00：SSH再次在认证前Connection refused（exit 255）。安装6718、bootstrap1864和下载6833当前状态仍未知；未启动替代任务，无新模型结果。连接恢复后先核对boot/PID身份和完成marker。本地remote-access-recheck.json已保存；此更新尚不能同步GPU。

## SH02 连接中断（2026-10-20 11:14 UTC）

本轮先成功核对安装6718、bootstrap1864、Torch下载6833身份；随后实见4个Torch范围分段完成，wheel整体SHA尚未通过，尚无模型输出。之后SSH端口突然Connection refused；短暂等待后再次连接仍在认证前失败。当前三个远端进程状态未知，不能推断停止/完成，也不能重复启动。remote-access-interruption.json保存11:14:37 UTC实际错误。

尝试同步最新观察/记忆时SSH失败，随后本地更新脚本因旧snapshot没有torch_completed_segments字段而KeyError；没有成功保存那次新远端snapshot，也没有把记忆同步GPU。此条明确替代把11:09旧snapshot当成当前状态的任何表述。恢复连接后先核对三个原身份、安装退出/torch验证marker和bootstrap日志，再继续；不回到hn01启动替代。研究未完成，Harness未更改。

## SH02 复用已核验 CUDA 依赖（2026-10-20 11:09 UTC）

发现基础conda中15个NVIDIA分发满足Torch2.13及cuda-toolkit13.0.3声明约束，且无prefix外文件。reuse_cuda_packages.py逐文件验证原RECORD哈希，然后复制进独立venv；基础conda未修改。证据base-cuda-reuse-audit.json/cuda-packages-reused.json。先按身份暂停原安装/uv/等待中的bootstrap，将完整临时cache（含未完成部分）复制到cache/uv-sh02-retained，保留旧日志和进程记录，再结束旧1276/1289；新安装6718已运行，原bootstrap1864已SIGCONT恢复且状态S。无旧安装并行残留。新解析仍202packages，剩5大包（torch、triton、tokenspeed-triton、cutlass cu12/cu13），原完成下载从持久cache复用。

另有Torch官方wheel分段下载6833（最多16连接），全文件官方SHA通过才写torch-wheel-verified.json。当前未完成，不能用于安装。若该marker先于安装完成出现，下一次先核对新installer/uv身份；保留持久cache和尝试日志，再安全重启安装，install_environment.py会自动将已核验Torch wheel作为直接输入。不要盲目终止已完成安装或已启动模型；若原uv先完成，取消多余下载并保留片段。torch源metadata在torch-wheel-source.json；分段在GPU cache/sh02-wheels/torch-ranges。当前下载仍有低速重试，尚无引擎或科学结果。

inspect_environment.py在实际导入后增加pip check和完整分发版本记录，避免只记录Torch而漏掉复用CUDA依赖。GPU py_compile已通过，真实import/FP16引擎仍待剩余安装。隔离评分/数据/分析验证继续复用；旧BF16样本不混入。下一步读取真实下载/安装状态，调试实际错误，再FP16smoke及顺序研究。

运行观察 2026-10-20T11:01:55.646514+00:00：安装1276与bootstrap1864身份匹配，scratch约5.1GiB，nvidia-curand/nvshmem/opencv新增完成；安装尚未退出，无bootstrap错误，GPU0MiB/0%。保留同一安装和串行程序；没有新模型输出或科学结果，已通过软件检查不重跑。最近实质交付仍594895f，本轮仅保存运行观察。

2026-10-20 10:52 UTC：原安装1276和bootstrap1864身份仍匹配，scratch4.2GiB，安装未完成、无bootstrap错误。对已下载vLLM0.32.0实际源码/二进制审计：核心_C_stable_libtorch包含sm_75 cubin（cuobjdump成功）；CudaPlatform在CC<80支持FP16/FP32，FlashAttention backend要求SM80，Triton backend允许CC7.5候选。这不是引擎成功证据，仍须实际初始化。Qwen配置36层、8KV heads、head_dim128，FP16 dense K/V每token147456bytes；context17920仅KV约2.461GiB，旧67072约9.211GiB，均不含权重/激活/工作区。保存vllm-t4-source-binary-audit.json、vllm-core-cuda-objects.log与fp16-kv-storage-estimate.json。继续原安装后FP16smoke与正式顺序研究；没有模型分数。

2026-10-20 10:49 UTC：原安装1276与bootstrap1864身份匹配，scratch增长到3.9GiB，flashinfer-python新完成；没有安装退出或bootstrap错误。实际传输诊断：GPU访问PyPI元数据TLS超时；官方torch wheel CDN1MiB分段只传351442bytes/25秒后超时；本地同段0.142秒，但SSH上传1MiB超过60秒仍未完成，按精确PID停止测速，未替换原安装。故不因本地CDN快就改成慢SSH中转，也不重启有进展的uv。官方文件摘要和探针保留在*-probe.json、torch-wheel-source.json、installation-transfer-observation.json。当前仍无模型结果；等待同一安装完成后由原串行程序进入FP16引擎/恢复测试及正式条件，已通过的隔离和分析验证不重跑。

2026-10-20 10:44 UTC：原安装1276/uv1289与bootstrap1864持续运行，下载scratch约3.5GiB，新增z3-solver完成，无安装退出或引擎结果。LCB完整校验和隔离评分探针已经通过，不重跑。新增GPU后处理实测validate_analysis.py：使用这次真实软件探针结果，聚合一致，异dtype/host/dataset/prompt和tampered result均拒绝；comparison-analysis-validation.json保留证据。两个fixture条件相同，不是模型比较或科学零差异。下一步仍为安装完成后的原生FP16启动/容量/恢复smoke和正式基座；不可从准备结果声称C/D/E成立。

## SH02 软件集成实际通过（2026-10-20 10:40 UTC）

剩余4MiB分段在download=true传输URL重试后成功；LCB完整官方SHA校验通过，固定作者源码也核对通过。下载程序2701已完成退出，不需重启。原安装1276与bootstrap1864仍身份匹配，CUDA依赖继续下载，GPU0MiB/0%；尚未进入FP16推理。

为避免等待大型CUDA包，复用uv已经完整下载的numpy2.2.6/pandas2.3.3及四个小依赖，复制到GPU持久cache，以基础Python3.12.13创建只读rootfs（未改base conda）。在pipeline.lock串行保护内实际执行原isolate_ssd.py：私测解码摘要d95cab6f...符合历史协议；UID61044、主机文件不可见、IP禁止、Unix IPC和只读运行库探针通过；五类作者软件测试预期全部通过（stdin/function正确为true，错误/异常/超时为false）。评分源码和边界没有改动。详见early-*-exit.json、early-software-validation.json、runtime-preparation.json及评测结果；这只是软件集成结果，不是模型性能。

bootstrap后续会复用已完成rootfs/解码/软件探针；等待独立推理venv安装完成后检查实际版本，再FP16冒烟、恢复测试和正式基座。不要启动重复安装/模型程序；若安装或引擎出现真实错误，读取并修复。研究持续，旧BF16结果保持独立。

2026-10-20 10:34 UTC continuation: observed actual curl56 connection resets and stalled transfers. Verified and stopped only downloader1863/its children, retained completed ranges and attempt1 logs, added retry-all-errors and 45s low-speed detection. Replacement downloader2438 is active; 23 segments verified, whole-file SHA not complete. Installation1276 and bootstrap1864 still match identities, no bootstrap error, GPU0MiB/0%. Installation continues downloading (scratch grew to2.8GB); do not duplicate/restart it merely for slowness. Postprocessor now accepts --root for SH02 conditions and rejects mixed dtype/runtime/host/seed/context/execution options; result/input hashes are checked when binding exists. GPU py_compile passed; functional analysis remains untested until real outputs exist. No new scientific result.

最新核对：10:29 UTC 三个准备/串行进程身份仍匹配，GPU尚未推理；迁移代码已交付145850b。续跑先读sh02-migration-20261020/progress-note.md及实际日志，勿重复启动。

## SH02 实际续跑（2026-10-20 10:26 UTC）

迁移191个源码/历史文件逐个SHA核对通过，Qwen3-4B与SimpleSD两套权重全部校验完成。独立venv正在安装vLLM0.32.0所解析的Torch2.13/CUDA13依赖；基础conda没有替换。安装进程1276身份匹配，尚未完成，不宣称运行兼容已验证。

LCB顺序下载和较慢官方中转已按身份停止并保留部分文件；镜像206/Content-Range验证后，由单个下载程序1863最多8条连接取得剩余分段，组装后仍须完整官方SHA验证。串行集成程序1864已实际启动，等待安装与数据校验，然后执行隔离边界、5种作者评分软件探针、3题FP16冒烟、逐样本复用与不兼容配置拒绝测试。通过后同一程序启动131题×10 seeds的新FP16基座条件；若真实报错则保留日志并由研究worker修复。

计划冒烟验证context17920，正式max_tokens16384（尚未验证可运行）；比作者65536短，必须报告length与截断界限，不能称全预算复现。旧hn01 BF16样本不参与新条件。当前GPU尚未推理，以上是实际准备/程序状态而非科学结果。进程、脚本、日志与版本证据见sh02-migration-20261020/。研究持续。

## 当前续跑位置（2026-10-20：用户授权迁移 SH02 / T4）

新的 `gpu-migration-resume-sh02-20261020.md` 已取代 hn01-only 续跑。SH02 实连成功，09:58 UTC 观察 Tesla T4 15360MiB、显存0、GPU利用率0；只见基础服务，无研究进程。数据盘约49GB可用，overlay约30GB可用。旧 hn01 任务仍未知，不推断终止，也不再尝试在旧主机启动任务。

初始项目仅444KB，正在补齐本地源码/历史记录并逐文件验证；模型和LCB执行数据需在新主机重新取得并校验。旧 base 条件配置明确 BF16、max_tokens65536/context67072，seed0/1只作为历史输出，不能合并到新FP16条件。新条件将统一T4原生FP16、相同提示/种子/预算/作者评分器；实际预算等待引擎KV容量验证，不预先声称67K可运行。

迁移脚本和证据在 `sh02-migration-20261020/`。新增逐样本原子落盘及配置/提示绑定，尚待GPU集成验证；评分语义沿用作者实现。独立venv依赖解析进行中，系统conda保持原样。当前是迁移/软件准备，尚无新主机科学结果；下一步依赖安装、模型校验、FP16容量和隔离评分smoke，然后正式顺序研究。

## 当前续跑位置（2026-10-20：远端连接中断）

2026-10-20 06:43:55 UTC第三个连续续跑轮次确认相同连接拒绝。当前为外部访问阻塞，需要恢复原SSH端口或提供更新后的授权连接配置；不能由这些失败推断GPU任务已退出。未改变运行时或启动替代任务。

2026-10-20 06:42:41 UTC再次实连：同一SSH端口仍返回Connection refused（认证前）；远端状态仍未知。已复核官方MBPP报告并将source-notes.md中的早期暂停/未完成表述明确标为历史状态，防止误重跑。没有新增模型结果，后续实验仍需先恢复连接并核对原任务。

本轮两次实际SSH连接均在认证前返回Connection refused，无法核对原runner65584、GPU、退出记录或结果。当前远端状态未知；2026-10-19 02:58的2/10 repeats、seed2 75/131仅为最后持久化历史快照，不是当前进度。已完成官方MBPP结果和本地两轮LCB原始输出继续保留，未重跑、未启动第二实验、未改变Harness runtime。

连接恢复后先核对原进程身份、锁、完整repeat、stage退出及results，再分析已完成结果或处理真实报错，继续顺序模型/解码对照。当前不能声称LCB完成或失败；研究未完成。详见ssd-author-comparison-20261019/remote-access-interruption-20261020.md。本轮记忆保存在本地和Git，因SSH不可达尚未同步GPU。

## 当前续跑位置（2026-10-19 02:58 UTC）

runner65584的boot/start ticks仍匹配，seed1完整落盘，seed2继续推进（最近75/131）。当前完成2/10 repeats，无退出记录或正确率。第二轮131条任务/种子/提示绑定检查通过，全部stop、无length，292643 tokens，median1586、max9535，耗时4798.21秒。原作者提取后130条可解析，arc194_b单一代码块内残留无循环体的for草稿，与首轮围栏问题不同；未修改代码或评分器。详见ssd-author-comparison-20261019/second-repeat-observation.md及repeat-01*。原始输出和检查证据已同步本地。

原生成→隔离评分程序继续，未启动第二程序，未改实验或Harness runtime。此处仅为生成/格式观察，不是功能正确率或覆盖缺口。恢复时优先核对原进程和新落盘repeat；当前条件完成后读取真实评分，再继续模型/条件对照。研究未完成，Harness未暂停。

## 首个原生repeat落盘与继续生成（2026-10-19 00:49 UTC）

同一runner65584身份匹配，seed0的131条原始输出已完整保存并自动开始seed1；00:49 GPU负载72%、显存22087MiB。当前完成1/10 repeats，尚无正确率；不重复启动或提前进入并行评分。raw SHA256 de904a35d2c607c7bc5d59f59a7d972d42ba298e21ffed2f36ae646e2a273deb，已同步本地保留。

seed0实际生成5032.90秒、307970 tokens，median1749、max8337；131条均stop，无length终止，任务顺序/seed/长度边界核对通过。作者原提取+静态ast检查130条可解析，唯一arc194_b因原输出未闭合围栏使正则取到说明文字；输出自然结束6299 tokens，不是截断。未修提取、未执行该代码、未声称修复后正确。51条单块、80条多块。详见ssd-author-comparison-20261019/first-repeat-observation.md及base-temperature-0.7/repeat-00*；均为生成/格式观察而非功能评分。

原程序继续其余seed，完成后自动隔离评分。之后以完整条件结果重评C，再顺序恢复SSD资产和模型对照。研究未完成，Harness未暂停，不把首repeat完成当作研究结束。

## 原生失败语义与运行核对（2026-10-19 00:03 UTC）

同一runner65584身份匹配，第一repeat65/131 prompts，仍无完整repeat/正确率；00:01观察GPU负载66%、显存22087/24564MiB，无重启或第二程序。

继续审读作者评分：首次失败即返回，lcb_run将所有未执行槽位补为失败且标Time out；因此num_tests_failed和补位文本不可解释为实际错误测试数或真实超时数。首失败输出也可能来自进程异常后的补位，不能只靠字符串定因。源码语义未改，分析器仅追加解释限制。hn01读取实际解码测试元数据：131题/4852 tests，最少1、median/max40，无零测试题；原生全completion join预算最大285秒，不是每测试固定6秒。证据见native-failure-semantics.md与native-timeout-budget-audit.json。这是协议审计，不是模型结果或新的C失效。

当前继续原生生成→隔离评分，完成后读取真实结果再决定后续研究。无新增门槛，不重跑已完成官方MBPP，Harness未暂停。

## 配对分析绑定与续跑（2026-10-18 23:58 UTC）

同一原生LCB runner65584身份匹配，首repeat61/131 prompts，约61.5 tokens/s，无完整repeat或正确率。未重启、不并发其他模型。

已增强analyze_condition.py：逐题prompt hash跨repeat及跨条件核对；两条件比较绑定dataset/source/n_repeat/max_tokens/top-p/top-k/min-p，显式列出其他配置差异；增加两方向any-success discordance与外部difficulty的描述性差值。分析器只读取作者评分状态，不执行代码、不改变官方指标。hn01以既有真实软件探针结果验证正常聚合、异数据拒绝、异提示拒绝均通过，记录comparison-analysis-validation.json；验证中的两份相同fixture不是模型比较，0差值不是科学结果。当前runner不调用这个后处理模块，生成/隔离评分路径未改动。

下一步仍为当前完整条件结束后的真实结果分析，再恢复SSD资产并执行作者推荐/交叉温度条件。此前官方MBPP结果保留不重跑，研究尚未完成，Harness未暂停。

## 训练来源边界核验（2026-10-18 23:52 UTC）

原生LCB第一repeat进至52/131 prompts；runner65584的boot/start ticks仍匹配，尚无完整repeat或正确率。当前继续生成，无第二模型任务。

审读SSD论文C.1与固定作者源码2637d202：论文描述约10,168条去重提示，公开生成脚本直接加载seed_sft、没有去重，默认T1.5并按字符长度过滤最短约10%；发布checkpoint card则训练T1.6。故示例脚本不是完整训练复现证据，不影响当前发布权重评测。rSTAR原论文报告16-gram去污染但评估LCBv5，不能替代对当前v6与确切SSD训练manifest的实际重叠检查。未发现或声称污染，未下载12.1GB seed_sft；hn01镜像metadata403已记录，不重试不变失败，也不阻塞当前模型程序。源码与分析见ssd-author-comparison-20261019/training-source-audit/review.md。后续训练如有科学必要再绑定实际提示、去重和过滤，不从公开例子推定checkpoint配方。

已读取既有手册/记忆；继续等待原生配对结果判定C问题，不将来源缺口转成新方法主张。Harness未暂停，研究未完成。

## 十样本解释边界与续跑（2026-10-18 23:46 UTC）

核对同一runner65584身份仍匹配，第一repeat最新39/131 prompts，无完整repeat或正确率。未重启、未并发其他模型，已完成的官方MBPP不重跑。

新增ssd-author-comparison-20261019/finite-sample-interpretation.md及hn01解析计算finite-sample-reference.json：IID假设下0/10成功的单侧95%概率上界仍为25.89%；即便两个sampler能力相同，也可出现大量任一方独有成功题。因此不能用零样本成功或筛选后的失败集合定义条件性gap。按题配对总体指标、两方向discordance、外部difficulty描述及截断/提取/计算量一起解释；发现后选出的条件须独立确认。示例为数学参考，不是模型分数、额外实验或强制增加采样轮次。当前程序继续，研究未完成，Harness未暂停。

## Decoder对照源码核验（2026-10-18 23:41 UTC）

原生LCB runner65584/start ticks144158755仍活动，第一repeat日志32/131 prompts，未产出完整repeat或正确率。保持单一程序，未恢复Apple下载或启动第二模型。上轮分析器及采样源码审计已交付666945a。

B补查AdapT、AdaDec、Top-H作者论文/代码：自适应温度、熵支持选择、选择性lookahead均有先例；AdaDec另有标注校准与额外推理成本，不可混为无训练/等计算对照。hn01对未修改Top-H作者commit8b94d62的CPU软件探针发现与论文v2熵约束不一致：128等概率logits、alpha.4/default top_n100返回39 tokens，归一化熵5.2854 bits，高于2.8 bits上限；top_n1另触发IndexError。只说明该源码与该论文版本的契约差异，不是模型分数或新C gap。原源码、license、hash和探针结果见adaptive-decoder-source-review-20261019/review.md，未静默修补或采用为模型对照。

后续仍先完成作者原生基座/SSD及解码交叉比较；若有残余条件失效，再用已核验的自适应控制区分机制。旧MBPP容量地板已否定；不将软件缺陷当作D创新。研究持续，Harness未暂停，恢复前先核对远端活跃身份和完成记录。

## 续研核对与B/C修正（2026-10-18 23:34 UTC）

已核对runner65584的真实start ticks，仍为同一原生LCB基座程序。最新日志第一repeat已完成21/131 prompts，约61.8输出tokens/s；尚无完整repeat文件或正确率，不重启、不并发第二实验。旧资产下载保持中断，部分Apple权重保留，待当前条件释放锁再恢复。

本轮增加analyze_condition.py：读取未修改作者评分状态，核对任务/seed/原始输出与被评分代码绑定、重算原生聚合指标作一致性检查，统计样本截断、语法/提取诊断和任务bootstrap区间。已通过原先真实执行的软件探针验证聚合；第一轮测试发现软件fixture的手工model_answers与fenced raw差一个换行，保留绑定断言并修正测试构造，实际模型结果未改动。分析器不执行生成代码，不替代作者evaluator。

已获取论文指定vLLM0.11.0源码并与当前0.10.0比对：top-k/top-p和随机采样函数AST相同，当前非greedy、不请求processed-logprob路径的已审读差异不改变采样步骤；不宣称模型kernel或随机轨迹逐位一致。失败的raw源获取转用codeload成功，运行环境未升级。证据见ssd-author-comparison-20261019/sampler-audit.md及sampler-source-audit/。

B/C进一步否定预设：作者card已报告pass@5提升，不能预设自蒸馏普遍丢失coverage。作者训练采样T1.6（不是示例config1.5）；原论文已经做更广温度扫描、support compression和context-dependent理论，两个matched温度或重述lock/fork都不构成新机制。带训练support mask的理想decoder null及证伪边界记于decoder-null-and-novelty.md，尚未启动新方法或宣称新gap。当前继续等真实对照证据，Harness目标未完成、未暂停。

## 当前运行：作者原生SSD对照基座（2026-10-18 23:23 UTC）

已继续到LCB真实模型生成：基座Qwen3-4B-Instruct-2507，作者推荐T0.7/top-p0.8/top-k20，每题10 samples、131题、输出上限65536，使用SSD作者原生prompt/generate。runner PID65584，身份与分阶段日志在research-state/ssd-author-comparison-20261019/base-temperature-0.7/。4090实际初始化通过：模型7.6065GiB、可用KV13.23GiB/96352 tokens，配置context67072、单序列、BF16、TP1。实际正在生成，尚无此模型的正确率；同一runner随后调用隔离的作者evaluator。

此前下载PID63741已在Qwen基座13文件全部校验完成后有意终止进程组，Apple未完成分片保留，原因记录在upstream-evaluation-20261018/author-pair-download-interruption.json。不是暂停Harness。等当前条件结束/退出再恢复下载，勿与当前pipeline.lock并发或重启已活动runner。恢复时先核对PID、boot/start ticks、active-stage与退出记录；完成的repeat文件可以复用。

SSD作者实现已适配隔离：UID61044、只读运行库、禁IPv4/IPv6、允许Manager所需Unix IPC；stdin/functional正确、错误、异常、超时五种软件探针均符合预期，不是模型结果。原生私测解码在隔离内完成，131题/4852测试。数据test6的官方摘要核对已通过；官方README说明先前release_v5截止Jan2025，支持仅加载test6并按作者Feb-May过滤，未下载审计所有先前shard。两个模型实际chat template和prompt完全一致，最长输入1410 tokens。Apple三权重摘要现已在ModelScope与HF镜像指针间交叉一致（直连HF仍不可用）。

下一步：分析基座原生LCB结果及截断，再运行SSD T1.1推荐条件，结合交叉温度条件辨别权重与解码效应。研究决策、数学null与限制见research-state/ssd-author-comparison-20261019/research-decision.md。旧MBPP近零容量地板已被否定，尚无D谱机制证据。研究持续，Harness未暂停或修改runtime。

## 交付与LCB数据进展（2026-10-18 23:09 UTC）

真实Qwen评分、sanitizer诊断及记忆已交付分支research/round2-harness-20261017，commit153692c。LCB官方snapshot0fe84c3的test6已在GPU下载并与官方SHA256核对；175题中131题符合作者日期条件，其他shard日期完整性尚待核对。源文件在远端cache/lcb-0fe84c3/test6.jsonl，不入Git。下一步见upstream-evaluation-20261018/lcb-continuation.md；下载PID63741仍需恢复前核对。研究未完成，保持Harness自动续跑。

## 续跑补记（2026-10-18 23:07 UTC）

SSD作者源码已通过codeload取得，固定2637d2021f1bc523385b48a1f88ea9aa4812b0a9；archive/source摘要见upstream-evaluation-20261018/ssd-source-resolution.json。原生CLI默认32768输出token、20 repeats，不可误认为论文设置；下一步固定LCB数据来源并检查隔离依赖，再测4090容量。模型下载PID63741仍活动，首分片已下载约1.9GiB；无模型推理进程。

## 最新纠正：Harness 已恢复管理职责

2026-10-18 用户明确保留 Harness 的长任务、记忆、自动续跑和中断恢复，仅取消 B/C/D/E 实验设计与执行的固定格式和准入限制。下文“停用整个 Harness”的记录已被纠正；旧实验接口报错仍为历史，不再阻止直接评分。当前实验模式由 GPT 执行、Harness 监督，真实结果仍待实际运行。

## 历史执行方式（已由上文 Harness 恢复指令取代）

此前将用户指令理解为停用整个 Work Harness 是过度解释，现已纠正。Harness 保留长任务监督、记忆、自动续跑及恢复；B/C/D/E 使用 `research-guidance/prompt-*.md`，由 GPT 自主研究。旧准入和单角色限制不再阻止实验。已有8000预测直接使用已验证适配器评分，无需重新生成。历史记录保留，新的实际进度见下方追加记录。

# SPECTRUM 项目研究手册

## 最新结果与续跑位置（2026-10-18 23:01 UTC / 英国10月19日）

Qwen作者流程和未修改EvalPlus899b2b3已全部完成。378题、greedy每题1条：raw base267/378=70.635%，raw base+extended230/378=60.847%；上游sanitized base266/378=70.370%，joint229/378=60.582%。旧自写2.325%不能作为容量地板或谱方法必要性的证据。新旧任务/提示/采样不同，不能把差额归为单独提取效应。完整报告与真实结果见 `research-state/upstream-evaluation-20261018/report.md`、analysis.json和raw/sanitized-eval_results.json。

继续C/B02后实际复现上游sanitizer问题：task635的heapify无return、被错误删除，唯一一个base结果由pass变fail。单独最小修订保留函数后，以原378输出和未修改evaluator完整复测，仅该题恢复，得到267/230；此为独立诊断端点，不替换官方结果。另有37题base通过但extended不通过；案例审读显示既有算法/性能问题，也有题意与canonical行为不一致，不能全部解释为实质模型推理失效。task635的112条extended输入全部为空列表，数据原样保留。

下一科学对照选作者发布的SimpleSD-4B-instruct与其实际Qwen3-4B-Instruct-2507基座，区分作者推荐解码与匹配解码/预算。选择依据是直接检验自蒸馏条件，非缓存或指定规模。直连HF不可达、hf-mirror403，ModelScope文件索引和下载可用；Qwen三分片摘要已与HF作者页面核对，Apple跨源摘要核对仍未完成。下载进程PID63741于23:01:55 UTC启动，顺序下载并核对每文件Sha256；日志和身份为upstream-evaluation-20261018/author-pair-download-*。恢复时先核对进程与exit，勿重复下载/启动。权重在远端cache/modelscope-author-pair-20261018，不入Git。尚未宣称这对模型已合格或完成推理；后续检查作者SSD原生LCB数据/协议及4090容量，再设计匹配比较。科学目标未完成，Harness继续监督，无暂停或runtime改动。

## 最新：恢复后执行 Qwen 作者流程（2026-10-18 22:44 UTC）

用户要求“你官方打吧”“然后继续往下跑呀”；此前暂停和交接已撤销。旧自写评分器已删除，不恢复或续跑。严格自写协议历史结果为186/8000通过，pass@1=2.325%、pass@16=21.2%，7620条SyntaxError；这是格式/评测诊断，不是官方模型成绩或容量地板证据。未完成的自写提取敏感性运行保留历史输出，不再执行。

已读取 `research-guidance/prompt-upstream-code.md` 和上游代码。Qwen提交33bc6aa的MBPP流程：作者ChatML提示、greedy/T0、每题1条、请求max_tokens2048、vLLM上下文1536、上游sanitize、raw/sanitized各自评估base与plus。明确导入其EvalPlus gitlink899b2b3，而非requirements中的0.2.1或环境已安装的0.3.1；实际模块路径已记录。此版本MBPP+ v0.2.0有378题，SHA256 b54e762755248ca411b523c917fa9f93c07b5ff2966bf60b3917b853926a3dad。与旧500题仅224个ID重合，重合题prompt字节无一相同；必须新生成，不能复用旧样本冒称官方复现。

在原venv补装vLLM0.10.0/Transformers4.53.3（保留Torch2.7.1），使用清华镜像；旧tree-sitter依赖放独立eval-deps目录，导入上游sanitizer已成功。硬件适配仅gpu_memory_utilization从.98降至.80；另外记录引擎原始文本/token/终止原因，不改变处理语义。原作者batch1/TP1/greedy设置保留，不为测试batch128改变作者命令。新程序PID60578于22:44:47 UTC启动，顺序执行generate→sanitize→raw evaluation→sanitized evaluation。日志、阶段进程身份及退出状态在 `research-state/upstream-evaluation-20261018/`，恢复时先核对真实进程，勿重复启动。

评测通过OS隔离外壳调用未修改的EvalPlus main，保留上游测试、oracle、时间限制和指标；chroot只读运行库、UID61043、seccomp禁网络/exec/逃逸相关调用，保留上游multiprocessing。实际探针确认宿主文件不可见、网络与运行库写入被拒绝、进程共享内存可用。命名空间unshare在主机上实际不可用，故采用该边界。378条生成和上游sanitize已完成（修改32文件），2条达到上下文上限。首次评估因隔离外壳256MiB文件上限不足以保存上游groundtruth缓存而失败，无模型成绩；失败日志、部分缓存及旧外壳保留在failures/file-limit-attempt1。仅将外壳文件上限提高至4GiB，22:53:33 UTC以PID61138恢复评估，复用生成/sanitize，不改上游评分语义。尚无官方科学评分。下一步依据raw/sanitized和base/plus结果重评C/B02，不预设原gap仍成立。

## 2026-10-18 实际续研进度（优先于下方历史待办）

已恢复手册与 B/C 记忆，保留 Harness 监督及自动续跑，未修改 runtime。原预测 SHA256 已核对；hn01 无其他实验任务后，22:15:37 UTC 直接启动原 v4 CLI 评分，runner PID39540、scorer PID39541。身份、输入摘要、命令、日志及最终退出记录在远端 `research-state/mbpp-original-scoring-20261018/`。恢复前先核对进程身份，不重跑生成或重复启动评分。

静态审计显示严格提取后仅380/8000条可解析；6725条为单代码块加说明，840条多代码块，55条其他；363条达到512 token上限。低严格评分不能直接解释为模型容量地板。已准备独立的单代码块提取敏感性实验，原评分不改写。完整科学判断、边界及下一步见 `research-state/mbpp-diagnostic-decision-20261018.md`，实际结果随后追加。

2026-10-18：按用户要求从已有证据补建。持续更新；记录格式由研究需要决定。此手册不是新的科学结果。

## 目标与 motivation

继续 SPECTRUM 第二轮研究，结合数学、核心论文官方代码和真实 GPU 实验，识别具体条件下自蒸馏/迭代改进的局限或不必要依赖，再构造并验证方法。C/D 保持发现与修订自由；证据充分后由 GPT 直接进入 E 的扩大验证。原有谱方法不必成功。用户授权小红书只读讨论线索，用论文/代码/实验核验。

## Gap、idea 与数学预测（可推翻）

历史候选区分谱方向、采样分布/长度重加权和额外答案信息；零期望 score 梯度有严格条件，不能直接推出实际多轮训练无效或谱干预必要。见 research-state/C-phase-e1a14/method-basis-v3.md，仅为带来源的既有候选，不强制当前 worker 沿用。科学选择须重新评估，见 research-state/question-led-experiment-selection-20261018.md。

## 文献与记忆入口

research-state/B-C-memory-index.md 及其链接保留 B 文献/代码/讨论和 C 追加证据。手册总结不能替代源卡、原始输出和真实评分。

## 实验设计

当前 C/B02 尚未接受具体问题。下一步由同一 worker 选择能区分竞争解释的模型、任务、强/简单对照和原生评测，检查容量、任务难度、采样、截断与信息/预算差异。1.5B/MBPP 缓存及用户先前提及的7B均不构成强制配置。D 由条件与可证伪预测设计方法；E 根据存活主张扩展并保留未暴露确认数据。

## GPU 与执行配置

- 授权目标：spectrum-harness-gpu-hn01，单 NVIDIA GeForce RTX 4090。已有 preflight 报告总显存24564 MiB，见 research-state/gpu-intake-20261018/hn01-final-preflight.json；空闲显存与环境为历史观察，提交前重新看实时值。
- 执行环境：远端 /root/rivermind-data/spectrum-harness/venv；代码测试、模型和评分计算在 GPU 主机，Mac 仅控制。
- 为每个训练/生成/评分阶段写配置：模型/版本、dtype、长度、batch单位、有效batch/累积、并发序列、每题样本量、相关实现与内存估计。
- 用户建议：可支持且合理时从128向64、32、16、8、4、2、1探测；已有实测或估计排除的档位可跳过，不为填表故意OOM。128尚未针对新工作负载实测。
- 选型依据：实际有用吞吐、显存峰值和余量、运行稳定性；不以显存占满为目标。保持样本量与科学设置；改变有效batch、精度、截断/解码等语义须明确修订方案和公平对照。

## 已有实际结果与边界

- e1a86资源校准及固定记录：reports/C-phase-e1a86-preparation.md、research-state/C-phase-e1a86b/readback.json。只对原有配置有效，不能证明新模型/长度/训练阶段可行。
- e1a87 base export：runs/stage-outputs/spectrum-C-base-export-e1a87/summary.json，500题、8000条生成，scoring_status=pending。sequence_batch_size=64、task_batch_size=4、每题16条；这些是不同单位。报告peak_reserved_bytes=5375000576、elapsed_seconds=1736.03，只代表此次导出，不等于最大可用batch或训练峰值。
- 当前没有据此成立的新准确率结论或C验收；原始结果/负面观察保留。

- e1a88 manifest bridge软件检查：runs/stage-outputs/spectrum-C-manifest-bridge-e1a88/summary.json；修复manifest可通过结构校验，但 metadata_repair_matches_original_export=false；不能把它写成科学评分已打通。后续应解释/修复匹配语义并保留原导出。

## 下一步与更新约定

worker 先核验本手册和当前实际进度，补充选择依据、数学预测及下一项判别实验，依据实验更新gap/idea/design。新模型/长度/阶段须选择相应探测；既有合格配置可复用。每次重要结果或方向改变更新相关段落，并链接原始证据与不可变历史，不另建审批或小worker。

## e1a89 更新：真实评分依赖（未验收）

已核对25项传入pin、14份native回执及其声明输出，均匹配；无新增native运行。见 reports/C-phase-e1a89-runtime-dependency.md 和 research-state/C-phase-e1a89/readback.json。原8000预测保持不变；当前 .13 exact export matcher 与完整评分合同在manifest元数据和基线命名处不兼容，需要运行时在quiet boundary提供有证据约束的历史metadata repair。不是GPU不可用或科学反证。当前待评分，不宣布C完成。

科学选择先检验原条件的容量/难度/截断，不能由缓存选模型或默认重启F/P/A。仅替换363条length结束输出而保持其余输出不变时，平均pass@1绝对变化最多4.5375个百分点，这是代数界不是实测改善。官方SSD的已发布checkpoint是另一问题下的强对照候选，须保留其采样/数据/目标差异。

资源：既有batch64推理配置可在同条件下复用；8000条无需再生成，因此本次不额外探测128。未来生成仍考虑128→64→32→16→8→4→2→1并记录合理排除；训练需单独测反向/优化器峰值，不能借用生成的5.38GB峰值。评分CLI当前串行逐程序，其并发单位是程序，128序列的推理批次不能套到评分；没有新的评分吞吐实测。

## e1a90 更新：评分器已验证，单基线评分路径待维护

已采用.14；hn01真实任务f110f40063164e21813388631b78aa1c完成正式协议验证、原export兼容匹配和四类live scorer探针，均通过。见reports/C-phase-e1a90-scoring-route.md及其原始回执。没有模型成绩。普通development单角色评分请求被实际拒绝：development requires actual control comparison。下一步需要受控已导出单角色offline scoring路径；不把模型评分伪装软件检查、不重跑生成、不执行旧P/A凑角色。原8000预测hash保持不变。

恢复后先评分以判断当前配置的容量/截断/任务辨识力，再选模型/条件和强对照。协议pass@1>0仅检查全错地板，不能证明强基线资格；B03调优/公平与独立确认等仍pending。评分资源单位为程序，串行2CPU/4GiB、每程序3秒，未发生新模型显存测量。


### SH02 host identity change — 2026-10-21 14:09 UTC
SSH now reaches an endpoint, but strict verification rejects a changed ED25519 host key. No remote command executed. New presented fingerprint: `SHA256:u1vPsq3oZJFNIp4O3T2wFQLTXqBDLRhR8QmjJ9cw4VA`. This does not establish a reboot, replacement, or termination of prior jobs. Original known_hosts entry and credentials remain unchanged. Require independent provider-console/administrator verification before accepting the new key; afterward reconcile boot identity, original process identities, markers, GPU and disk before any launch. Latest evidence: sh02-migration-20261020/remote-host-key-change.json. No new experiment or model result.

### SH02 access recheck — 2026-10-27 12:46 UTC
Strict SSH host verification now passes against the existing known_hosts entry (ED25519 SHA256:+IZMFu9Xx6FSAhvQhtvZ3MpV70v2d+XNWcequAbsp+c). The explicitly configured client key is offered but rejected: Permission denied (publickey,password). No remote command ran; boot, installer 6718, bootstrap 1864 and downloader 6833 remain unreconciled. No experiment was launched and no model result was obtained. Restore authorized client-key access through provider console/administrator, then reconcile identities and completion markers before any launch. Evidence: sh02-migration-20261020/remote-auth-recheck-20261027.json and remote-access-recheck.json. This worker did not modify known_hosts or credentials.
