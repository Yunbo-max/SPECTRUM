# .7 独立阶段的评分依赖分析

状态：源码检查完成，新入口尚未执行；本文件不是 native receipt、评分资格或 B02 验收。

本版本保留 e1a6 的 diagnostic_driver、training_instrumented、analysis、native_wrapper 及其测试/源文件。config 只把两个 source capture 路径指向本版本，同字节 SHA256 不变；其余算法设置不变。新 stage_entry 显式走 .7，旧 wrapper CLI 是历史接口，不能用于新 stage dispatch。

## 逐段调用与信息流

- `diagnostic_driver.prepare`（330–343）：只读既有 full/train 捕获与 full/test500，`adapt_sources` 保留原题 ID 和测试，按已有 split_seed42 去重/去交叉并取 calibration50、validation30 和剩余训练集；写所有源字段、分母和模型资产清单。不运行测试、不打分、不按答案质量选题。模型资产流式 SHA256 是来源核验，不是推理或 smoke。
- `calibrate_inference`、`freeze_profile`、`calibrate_training`：原有真实 calibration 数据用于资源测量。仅有限性、OOM、内存余量、运行时间及完整优化/保存流程影响资格；无 pass@1/C16 reward、过滤或 checkpoint 挑选。保留 descending [64,32,16,8,4,2,1]。`.7` 只认证 completed 前序；若上一批 OOM/failed，需要程序的显式失败前序恢复策略，不把失败收据改成 completed，也不自动换 ID 重跑。
- `generation`（346–380）→ 固定的 `improving.generation.generate_to_file`：模型调用按既定任务顺序、chunk seed、temperature=.8、top_p=.95、top_k=0、max_new_tokens512、n16 保存全部原始 completion。源码写出 tokens、prompt hash、finish_reason 和预算；未调用 verification，也没有正确性筛选。`generate-train` 是为训练准备原始语料，映射 stage_kind=prepare；它仍是真实 GPU 生成，必须配 GPU/7200 秒预算，不能按 CPU prepare 资源派发。
- `training`（383–416）→ `training_instrumented.train_on_records/_train_on_records`：仅因果 token NLL；全部 raw records 保留，P/A 均从同一 base 重新初始化、seed44、7.2M target-token 下界并按整条样本停止，保存唯一 merged checkpoint。没有 verifier、quality reward、quality early-stop 或按质量挑 checkpoint。loss finite 检查是数值失败检测。A 加入50个已有 calibration reference，信息量、记录曝光和 optimizer step 差异必须披露，不能称精确算力匹配。
- `generate-eval` 为 export：F/P/A × seeds43/45，每项 MBPP full/test500 ×16=8000 行，6项共48000行；检查真实输出身份和行数。代码只生成文本和记录，不执行生成程序。训练seed与评价seed分开。
- `analysis.py` 是以后消费真实得分的路径，入口不调用它。AST 指标仍是代理，不能称算法语义多样性。

因此这些阶段可声明 `scoring_dependency=deferred`；selection_metric 仅 none/resource_memory/runtime。初始 prepare 为 none；校准可为 resource_memory/runtime；训练/输出为 none。最终 native scorer、隔离、B03、S04、E04、SSD/n64、独立训练重复和未曝光确认仍待完成。

## 运行与前序界限

canonical native_stages.validate_plan + run_experiments.validate_plan 在目标机重新检查 program、descriptor、精确job、code/input/provenance、前序输出和 archive。Controller 在派发前验证前序是否确实注册为 terminal completed；项目 adapter 不访问/修改数据库，也不以本地 JSON 自称数据库认证。

adapter 再检查环境中的 controller(task/run/owner/fence)、dispatch SHA256、runner context 文件位置、native plan、实际 harness batch/task/resources/CUDA_VISIBLE_DEVICES 和 staged argv。controller run_id 与 native run_id分别保留；driver使用native run_id，完整context进入新stage summary。不存在未来context/hash或`admitted=true`。

新的driver stable run目录为 `research-state/C-phase-e1a84/driver-run`，与稳定code和workspace输出分开。既有stage/attempt或输出冲突一律等待原身份核对。后续任务必须消费至少一个已归档前序输出，并携带 canonical predecessor receipts；adapter核对原driver收据与完整输出清单。P/A export还要求每个真实checkpoint文件进入model_refs和job input_refs。不能把本次command-receipt当native前序。

当前GPU/进程、cgroup-aware CPU/RAM、磁盘在启动时读取；外部GPU消费者或未知Python/计算进程保留并阻止启动，不杀其他任务。完整进程清单留在远端结果，交付前按隐私范围审查。资源snapshot不是预约；实际harness lease、单实验锁与串行调度共同约束。继承外层进程组，以便native watchdog能停止整个owned子树。

## 来源 pin

以下为本次读取的固定来源；manifest还列出本版代码的实际hash。
- `research-state/B02-cd-epoch1-attempt12/native_stages.py` SHA256 `fc7fba569c30d2ffa03398d81f3660ae7df6236a934aeccde4bfd2dd53210c28`
- `research-state/B02-cd-epoch1-attempt12/run_experiments.py` SHA256 `799ac594087f7a745c1c82a5514c2dcf4e339321f02ff4957eac8e9b05c2f135`
- `research-state/B02-cd-epoch1-attempt12/cd-runtime-contracts.md` SHA256 `1bd28b3141335e2e9882187281f45a584efdc2657ea815d329569d060057bf29`
- `research-state/B02-plain-lineage-source-000004/generation.py` SHA256 `d432df51de7ece188c603ab832e078217f21b7c42e23267283abd7e8fbe2bf14`
- `research-state/B02-cd-code-integration-e1a6/diagnostic_driver.py` SHA256 `be19d0c55a539fc76a887c9f6bd9cbb0c3dede68595cde63ce75f70857658083`
- `research-state/B02-cd-code-integration-e1a6/training_instrumented.py` SHA256 `259e4d7364bca28a1d2d7b2a5264c82e7b2d69d4f339eff8c9db15a20b26abab`
- `research-state/community/20261017-6a126a17000000003502fc41.json` SHA256 `3e689c88a096474df23e59628f3840f1e2137fb574e8aa3ea7f1a026e69921ee`
- `research-state/community/20261017-6a34f4ae000000001503d43b.json` SHA256 `f83a52662b767a102b64b156cb2b0cfd2024911774ef0af98fbbd1442513e33c`
- `research-state/community/20261017-6a4293ea000000001c024ec3.json` SHA256 `eed8789f9a9fdca009a63d1fa4af77c3778ff1e3ea08580f9a22905546bc0160`
- `research-state/community/20261017-excluded-6ac60b6d000000001303e2bb.json` SHA256 `0ed28de4c8f8f50224e087da923e6852ee56e28c7de2a920fdf984c3ef5e4fdd`
- `research-state/community/20261017-primary-2607.01763.json` SHA256 `71fd5a4d421a4e9fad126f730303e82b172f5e3d80ccef15594e899bb92946c3`

社区记录只供问题来源：已读文字/可见评论和遗漏图像边界保持，未据此制造实验结果。本代码适配没有新provider调用。
