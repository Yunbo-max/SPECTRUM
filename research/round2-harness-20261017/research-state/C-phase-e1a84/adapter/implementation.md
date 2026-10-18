# B02 .7 阶段入口交付

本次完成代码编写与静态源码检查，未执行新代码、import、compile或portable测试；无SSH、训练、下载、Git写入。B02科学要求、独立审查和评分均未完成。

新增 `stage_entry.py`，CLI为 `--native-stage-context {NATIVE_STAGE_CONTEXT} --binding-ref <实际stage-plan-inputs路径> --binding-sha256 <该已存在文件的SHA256> --driver-stage prepare`。完整命令、确定输出和资源预算见 `stage-plan-inputs.json`；此处参数占位说明不代表已派发。没有未来attempt哈希、假admission或未来checkpoint。

实现保留10个e1a6 Python文件的原始字节；config仅改两个本地源码捕获路径，其SHA256不变。算法、prompt、数据选择、训练目标、P/A7.2M target tokens、seed44、F/P/A×[43,45]×500×16均保留。旧 `native_wrapper.main/validate_spec/run_stage` 保留历史版本；新入口不调用它们，也不制造旧admission。复用其严格路径/hash、driver argv/结果核验、流式archive工具。

新入口恢复并交叉核验真实runtime context、controller task/run/owner/fence、native run/trial/attempt、dispatch hash、harness task/resource context以及runner保留的计划。全Skill SHA256与当前pin一致才加载其捕获源码，避免读取旧bytecode。调用真实canonical native/stage validators，并对稳定部署及workspace副本分别核验。项目代码不是权限沙箱；前序Controller注册认证属于可信runtime，wrapper保留原driver来源检查而不冒充数据库认证。

stable code为本目录，scratch为 `research-state/C-phase-e1a84/driver-run`；最终输出仅在attempt workspace的 `runs/stage-outputs/<native run_id>/` 写入，成功后由可信runner独占发布。原始driver绝对来源不改写。原始stdout/stderr、checkpoint清单、完整输出清单、8×256MiB流式归档及origin-map全部声明；prepare额外单独收集四个split、source_fields、preparation_manifest、task-manifest和base-assets。失败/partial留存；现存stage、未知进程或输出冲突不自动改名重试。

新测试源 `test_stage_entry.py` 覆盖context真实字段、controller/native ID区别、缺失/伪造dispatch/fence、protocol/stage错配、F/P/A映射、输出namespace、前序缺失/失败、workspace单写与冲突不覆盖、无评分以及配置语义。软件fixture不是benchmark案例或scorer资格。此版所有测试都待hn01执行；父级52项旧检查仅是复用背景，不能证明新入口通过。

首个prepare无需训练checkpoint。`software_check`没有伪装成已实现stage：新adapter明确不声明该模式；可由后续独立审查的原生software_check任务按记录的unittest命令验证，或审查后先派发本adapter的prepare。stage mapping覆盖原driver全部七类入口。calibration失败/OOM后，.7只接受completed前序的具体恢复限制保留，不能凭旧driver支持failed receipt就绕过Controller。

下一planner应读取实际manifest/计划输入、将嵌入的CD与sample/program草案写成真实独立文件并计算hash、创建精确descriptor/native/harness计划，在hn01验证并通过独立审查派发。最终scorer资格不阻止该独立prepare，但所有评分与科学验收仍待完成。后续训练/输出必须按实际完成前序逐步创建，不能提前填未来hash。

保留B01取消、guard中断、旧admission和双写失败历史。B03、S04、E04、SSD/n64、独立训练重复、未曝光确认以及语义标注都未完成。不存在本次作者自签的独立review PASS。
