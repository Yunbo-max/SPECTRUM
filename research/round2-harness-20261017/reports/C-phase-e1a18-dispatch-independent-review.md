# C phase e1a18：独立静态 dispatch 审查

审查者：独立子代理 /root/dispatch_audit，当前 invocation（具体时间未单独核验）。范围是实际固定源码、JSON 和 mailbox 返回；未运行测试、DB 或 SSH，未修改运行 pins，不作科学 PASS。

## 结论

当前 mapped-code 拒绝是项目计划的真实缺口；修好后还有 phase/native-stage 与旧式 coverage admission 接线不一致。后者是静态可达结论，不是假称已执行到第二个错误。不要把它误写为最终 scorer 缺失必然阻止 stage。

1. `research-state/B02-cd-epoch1-attempt13/experiment.json:26,34,42,50,58,66` 的六个 mapped refs（remote-training.py、remote-pipeline.py、data.py、generation.py、E01 cli.py、spectrum metrics.py）均不在 `prepare-native-plan.json:186` job.code_refs，也不在 `stage-program.json:75` 各 arm implementation_refs。`research_cd.py:243–252` 仅取这两个集合，task.inputs 有同名文件并不能解决。控制组另含 remote-pipeline 等，也须保持完整。mailbox `918c56db026e4a93bc09274d1c0b305b.response.json` 实际在此拒绝。
2. 合理项目修复可以版本化 descriptor/native/harness/program 和真实 code mappings，明确执行实现与历史分析来源；若这些文件确为当前实现依赖，则将真实 refs 加入相应 code集合。不得仅为过检把无执行关系的历史代码伪装成实现。所有引用/hash须向上更新，旧输入不改。
3. `source-mailbox-v1/src/research_autopilot/phase_native.py:63–70` 对 mailbox task 构造 proposal，调用 `_proposal` 后才注册任务。`program.py:833` 无条件调用 `_coverage_tasks`；其 `:680–682` 对每个 native_harness 强制非空 experiment_bindings，唯一前置例外 `:674–679` 是 diagnostic qualification resource_calibration。development_stage 无独立分支。当前 coverage-02 最后为 experiment_contracts=[]、request-02 无 experiment_bindings，故修好 mapped code 后该请求必遇此检查。
4. 不应声称所有 development_stage 在算法上绝对不可 dispatch：`experiment_contract.py:446` 对 protocol 只读引用，不调用 scored verify_protocol。但 `coverage.py:264–273` 只从独立 experiment-design-contract 的 eligible jobs 生成绑定；`experiment_contract.py:331–349` 强制独立设计 review，`:185–225` 要求 scientific contrast 等完整义务。当前 sustained-phase 契约明确禁止每次准备/GPU调用新增独立微任务 review。为绕过而新造旧式全设计/假review或改为qualification，都不是本worker的合规修复。

最小 runtime 修复建议由 owner 处理并另行验证采用：为已严格验证的 development_stage 增加与stage descriptor/program对应的 coverage admission，保留任务对应既有义务、未评分义务、exact job/code/protocol、predecessor 和单实验约束；不可笼统豁免全部 native。本审查没有修改 runtime，也没有证明 proposed修复通过测试。

## 实读文件 SHA-256

- request-02.json: 8b6082d9118ffe717649d8e5d51fe9b5993af7fde584cce07ca6cd08a970a733
- coverage-02.json: 917d817f4f3e2434741d5edea501a64e09b496d1029c05a9d41f8fdbcb6daa09
- prepare-native-plan.json: 1dc05c14bf21466191f775b28af8a51e24ec7e5aaa907867ddf0a30d7bc2fdd1
- stage-program.json: 595973cbf5e26606249d4a932faa28b55c253aff3c8dfcbf29eb00ce1addd268
- program.py: 6f21b07d85c38a9ef4c66b56bcc9affeaafff3e0e9ede046a45f9ccd8120a95a
- phase_native.py: 3f6cd8f8cd9ec014db84f8b71cefd3a729bb22624c554dc5a92ff62e23a8c08f

仅observed tooling anomaly：shasum 的 Perl 发出 C.UTF-8 locale warning，随后回退 C 并退出0输出上述 hashes；不影响本审查结论。
