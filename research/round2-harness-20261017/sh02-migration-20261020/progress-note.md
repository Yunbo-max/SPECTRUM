## SH02 实际续跑（2026-10-20 10:26 UTC）

迁移191个源码/历史文件逐个SHA核对通过，Qwen3-4B与SimpleSD两套权重全部校验完成。独立venv正在安装vLLM0.32.0所解析的Torch2.13/CUDA13依赖；基础conda没有替换。安装进程1276身份匹配，尚未完成，不宣称运行兼容已验证。

LCB顺序下载和较慢官方中转已按身份停止并保留部分文件；镜像206/Content-Range验证后，由单个下载程序1863最多8条连接取得剩余分段，组装后仍须完整官方SHA验证。串行集成程序1864已实际启动，等待安装与数据校验，然后执行隔离边界、5种作者评分软件探针、3题FP16冒烟、逐样本复用与不兼容配置拒绝测试。通过后同一程序启动131题×10 seeds的新FP16基座条件；若真实报错则保留日志并由研究worker修复。

计划冒烟验证context17920，正式max_tokens16384（尚未验证可运行）；比作者65536短，必须报告length与截断界限，不能称全预算复现。旧hn01 BF16样本不参与新条件。当前GPU尚未推理，以上是实际准备/程序状态而非科学结果。进程、脚本、日志与版本证据见sh02-migration-20261020/。研究持续。

Resume record (2026-10-20 10:29 UTC): installation1276, ranged-data1863 and serial bootstrap1864 all match saved process identities; no bootstrap-error marker. Both model asset verification markers exist. Installation/data/integration completion markers are absent; GPU0MiB/0%. Preserve these running jobs. Next continuation should read their real logs and completion markers, debug any failed stage, and follow the same bootstrap into FP16 smoke then formal base. No new functional model result exists. Delivery uses isolated ../sh02-research-delivery because ../skill-policy-delivery contains pre-existing user edits; commit145850b is pushed. Do not overwrite the latter worktree's changes.

2026-10-20 10:34 UTC continuation: observed actual curl56 connection resets and stalled transfers. Verified and stopped only downloader1863/its children, retained completed ranges and attempt1 logs, added retry-all-errors and 45s low-speed detection. Replacement downloader2438 is active; 23 segments verified, whole-file SHA not complete. Installation1276 and bootstrap1864 still match identities, no bootstrap error, GPU0MiB/0%. Installation continues downloading (scratch grew to2.8GB); do not duplicate/restart it merely for slowness. Postprocessor now accepts --root for SH02 conditions and rejects mixed dtype/runtime/host/seed/context/execution options; result/input hashes are checked when binding exists. GPU py_compile passed; functional analysis remains untested until real outputs exist. No new scientific result.

## SH02 软件集成实际通过（2026-10-20 10:40 UTC）

剩余4MiB分段在download=true传输URL重试后成功；LCB完整官方SHA校验通过，固定作者源码也核对通过。下载程序2701已完成退出，不需重启。原安装1276与bootstrap1864仍身份匹配，CUDA依赖继续下载，GPU0MiB/0%；尚未进入FP16推理。

为避免等待大型CUDA包，复用uv已经完整下载的numpy2.2.6/pandas2.3.3及四个小依赖，复制到GPU持久cache，以基础Python3.12.13创建只读rootfs（未改base conda）。在pipeline.lock串行保护内实际执行原isolate_ssd.py：私测解码摘要d95cab6f...符合历史协议；UID61044、主机文件不可见、IP禁止、Unix IPC和只读运行库探针通过；五类作者软件测试预期全部通过（stdin/function正确为true，错误/异常/超时为false）。评分源码和边界没有改动。详见early-*-exit.json、early-software-validation.json、runtime-preparation.json及评测结果；这只是软件集成结果，不是模型性能。

bootstrap后续会复用已完成rootfs/解码/软件探针；等待独立推理venv安装完成后检查实际版本，再FP16冒烟、恢复测试和正式基座。不要启动重复安装/模型程序；若安装或引擎出现真实错误，读取并修复。研究持续，旧BF16结果保持独立。

2026-10-20 10:44 UTC：原安装1276/uv1289与bootstrap1864持续运行，下载scratch约3.5GiB，新增z3-solver完成，无安装退出或引擎结果。LCB完整校验和隔离评分探针已经通过，不重跑。新增GPU后处理实测validate_analysis.py：使用这次真实软件探针结果，聚合一致，异dtype/host/dataset/prompt和tampered result均拒绝；comparison-analysis-validation.json保留证据。两个fixture条件相同，不是模型比较或科学零差异。下一步仍为安装完成后的原生FP16启动/容量/恢复smoke和正式基座；不可从准备结果声称C/D/E成立。

2026-10-20 10:49 UTC：原安装1276与bootstrap1864身份匹配，scratch增长到3.9GiB，flashinfer-python新完成；没有安装退出或bootstrap错误。实际传输诊断：GPU访问PyPI元数据TLS超时；官方torch wheel CDN1MiB分段只传351442bytes/25秒后超时；本地同段0.142秒，但SSH上传1MiB超过60秒仍未完成，按精确PID停止测速，未替换原安装。故不因本地CDN快就改成慢SSH中转，也不重启有进展的uv。官方文件摘要和探针保留在*-probe.json、torch-wheel-source.json、installation-transfer-observation.json。当前仍无模型结果；等待同一安装完成后由原串行程序进入FP16引擎/恢复测试及正式条件，已通过的隔离和分析验证不重跑。
