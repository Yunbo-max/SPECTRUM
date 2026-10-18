# C 阶段实际执行与恢复检查点

本次沿用 .10、epoch1/cycle1/B02 attempt84，未改变科学游标、GPU或父级Git整合权限。

原请求 spectrum.C.prepare.e1.a14 已真正注册并执行；控制器 run 9bc92aa2378a43b6abe088fb51266a1f，hn01 attempt prepare-a1-7750e781d6ec458c99f3d94aacaec545，退出2。日志为 `ContractError: Adopted runtime changed`。旧adapter写死.7摘要，拒绝正式采用的.10；该失败不是数据或科学结论。

已将adapter及准备计划另存于 research-state/C-phase-e1a84，更新已采用摘要、隔离路径和引用哈希；保留原版本、无数据重下载。新任务 spectrum.C.prepare.e1.a84、run 449fe9bbb55e429296bcc966c53d7698 在启动前返回 reconcile_required。相同请求重查保留同一身份。随后通过真实固定目标上的原始PROBE只读核对得到 absent、exit0；不是执行回执。

当前 program_cli.py 的 reconcile_native 仅结算 completed/failed；absent仍保留不确定任务。worker不能写数据库、改已采用runtime或创建替代作业绕过这个状态。需要控制器所有者核对实际事件和目标观察，处理启动前未执行的身份，恢复同阶段。最初观察失败原因尚未知，不能推定唯一根因。

检查点 research-state/C-phase-e1a84/checkpoint.json 绑定失败回执、日志、新请求、原身份恢复结果和远端观察。修复adapter尚未真实执行验证。B02后果/干预、B03基线资格、B04问题契约、B05验收均未完成；旧F/P/A未获得科学选择。已检索B/C记忆和method-basis-v3；当前仅恢复中性物化，不新增文献或社区科学主张。
