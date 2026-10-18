# Work Harness C/D 数学—代码循环已实现并迁移

## 实际交付

- 源代码提交：a99fff9ac79a318f2d269e993825fa0e0124d628；补丁以已交付 .5 源码 2828edfb4ed64c5d05402769e4622d5ed4efcc63 为基点，含后续设计修订和实现。
- 插件：research-autopilot-harness 0.4.0-harness.6，主 Codex 与后台专用 profile 均通过官方 CLI 安装；主缓存的 482 个 Skill/runtime 文件与源码清单一致。另五个插件的 manifest 未变。
- 本机后台 runtime 已安装独立固定源码目录 source-cd-v1；旧 source 保留。GPU Skill 同步到既有路径，旧 Skill 保留为 skill-pre-cd-v1；未重复安装模型或数据。
- 旧调用结束、全部作业终态后归档未验收的旧 transport，没有接受其科学结论。SQLite 备份及 revision CAS 迁移成功：采用新版 profile 的 revision 184，解除维护等待 revision 185。
- 新版真实 consumer 已存活，新 profile 首个 worker 为 round 60 / B01。其意义是用新版要求复核已有配置证据，不是重装或抹除研究结果。实际时点见 live-readback.json。

## 新流程

B 文献/代码/讨论线索 → C 条件、失效模式及不必要依赖的数学诊断和实测 → D 数学机制、实现、真实局部对照实验。

C/D 可经独立 review 定向回访 B，或修订受影响的 C/D 节点；保留旧证据、失败、预算消耗和作业身份。小红书讨论只读、串行并作为待核实线索。循环不添加累计轮数限制。

B05 和 M05 必须有真实 native 输出、协议/arm/group/seed 关联、官方评分器复核及独立科学审查。M05 验收形成 VERIFIED_FOR_SCALEUP 后自动进入 E。E 保留公平比较、冻结、完整规模、确认实验及覆盖要求。软件测试通过不等于科学假设通过。

## 验证及限制

- GPU 隔离环境：C/D + B01 组合 70 项通过；插件 34 项通过；节点检查 84/221，零错误；CLI 单独复跑 6 项通过。
- 全 runtime 367 项曾报 8 个失败：7 个旧 admission 测试在原始 parent 完全复现；另 1 个 CLI 时间/状态案例单独复跑通过。未宣称完整回归全绿。
- 全 Skill 930 项报 8 个旧文案策略失败、2 个缺 SciPy 的错误、9 跳过。原始 parent 复现相同问题；在隔离测试 venv 从清华镜像补齐声明的 NumPy/SciPy 后，统计专项 9 项通过。旧策略测试保持可见。
- 一次测试与导出清单更新并发触发源码 pin 保护；冻结测试源码后 70 项重跑通过。打包曾发现 prompt 过长，已修正并成功构建。
- 新版已真实启动，但完整 C→D→E 科研周期尚未完成，未产生新的科学 VERIFIED 结论。

## 文件

runtime-fixes/cd-math-code-loop.patch 包含通用源码；research-state/cd-loop-20261018/ 包含设计、计划、测试原始日志、安装/迁移/运行读回及 skills-only ZIP。ZIP 不单独安装 Python runtime。数据库备份在本地保留，不上传；迁移凭据保留其哈希。

GitHub 仅普通 Git 文件推送，没有 Actions。所有研究实现测试在授权 GPU 主机执行，Mac 用于编辑、安装和调度。
