## SH02 实际续跑（2026-10-20 10:26 UTC）

迁移191个源码/历史文件逐个SHA核对通过，Qwen3-4B与SimpleSD两套权重全部校验完成。独立venv正在安装vLLM0.32.0所解析的Torch2.13/CUDA13依赖；基础conda没有替换。安装进程1276身份匹配，尚未完成，不宣称运行兼容已验证。

LCB顺序下载和较慢官方中转已按身份停止并保留部分文件；镜像206/Content-Range验证后，由单个下载程序1863最多8条连接取得剩余分段，组装后仍须完整官方SHA验证。串行集成程序1864已实际启动，等待安装与数据校验，然后执行隔离边界、5种作者评分软件探针、3题FP16冒烟、逐样本复用与不兼容配置拒绝测试。通过后同一程序启动131题×10 seeds的新FP16基座条件；若真实报错则保留日志并由研究worker修复。

计划冒烟验证context17920，正式max_tokens16384（尚未验证可运行）；比作者65536短，必须报告length与截断界限，不能称全预算复现。旧hn01 BF16样本不参与新条件。当前GPU尚未推理，以上是实际准备/程序状态而非科学结果。进程、脚本、日志与版本证据见sh02-migration-20261020/。研究持续。

Resume record (2026-10-20 10:29 UTC): installation1276, ranged-data1863 and serial bootstrap1864 all match saved process identities; no bootstrap-error marker. Both model asset verification markers exist. Installation/data/integration completion markers are absent; GPU0MiB/0%. Preserve these running jobs. Next continuation should read their real logs and completion markers, debug any failed stage, and follow the same bootstrap into FP16 smoke then formal base. No new functional model result exists. Delivery uses isolated ../sh02-research-delivery because ../skill-policy-delivery contains pre-existing user edits; commit145850b is pushed. Do not overwrite the latter worktree's changes.

2026-10-20 10:34 UTC continuation: observed actual curl56 connection resets and stalled transfers. Verified and stopped only downloader1863/its children, retained completed ranges and attempt1 logs, added retry-all-errors and 45s low-speed detection. Replacement downloader2438 is active; 23 segments verified, whole-file SHA not complete. Installation1276 and bootstrap1864 still match identities, no bootstrap error, GPU0MiB/0%. Installation continues downloading (scratch grew to2.8GB); do not duplicate/restart it merely for slowness. Postprocessor now accepts --root for SH02 conditions and rejects mixed dtype/runtime/host/seed/context/execution options; result/input hashes are checked when binding exists. GPU py_compile passed; functional analysis remains untested until real outputs exist. No new scientific result.
