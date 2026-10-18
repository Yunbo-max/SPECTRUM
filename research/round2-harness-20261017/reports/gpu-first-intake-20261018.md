# Harness GPU-first intake update — 2026-10-18

已按用户要求更新 Work Harness：GPU 工作开始前先确认当前执行目标；已有 SSH 信息直接复用并检查，缺失时才询问。用真实设备、可用显存、项目 Python/PyTorch 和原生精度支持约束模型、batch、精度与试跑设计。换机器、设备分配、解释器或关键配置后重新检查。

## 已交付

- 独立 SSH 检测模块：`python -m research_autopilot.gpu_preflight`，显式 target、requirements、output；`--smoke` 才执行小矩阵运算。
- GPU/MIG UUID 分配范围、项目和系统解释器分开记录、原生 BF16 与模拟检查分开；失败和未知保留。
- Skill 入口、首次需求沟通、GPU 运行模板和 9 类运行时 guidance 均加入 GPU intake/feasibility 指引。它是观察工具和工作流程要求，没有替代既有准入、review 或执行器。
- 结果区分 blocked、needs_measurement、ready_for_pilot。完整实验可行性还需要模型/config、序列长度、batch、峰值显存和吞吐的实测；权重大小/显卡型号不能单独证明可行。

## 验证

源修改 commit `067ec2866abc2912a8f718080f4275ae4c2a34db`，基于 `61b6e723501b301f37e0daed5ec83fa2d387573e`；可重放补丁见 `../runtime-fixes/gpu-first-intake.patch`。

在 hn01 GPU 服务器通过 85 项针对性运行时测试、34 项插件打包测试、12 项节点来源测试、7 项 intake 测试；84 个节点来源检查无错误。未声称整个运行时测试套件通过。前次 B01 的历史准入 fixture 失败仍保留在先前报告。

实际 4090 项目 venv（torch 2.7.1+cu126）FP32/FP16/BF16 小矩阵输出有限且精确；原生 BF16=true。UUID 规范化已通过实际分配检查。该次 CLI 返回 2 / needs_measurement 是预期结果：完整模型运行的显存需求仍为空，未虚构实验已可行。原始主机 RAM 数值不等于容器可用预算；同份报告明确记录 cgroup 100 GiB 上限。

## 安装与当前研究

本机 `research-autopilot-harness` 已通过正常 marketplace 安装流程更新至 `0.4.0-harness.3`，CLI 回读 installed=true、enabled=true；全部 Skill/runtime 清单散列与远程验证版本一致。保留六插件的独立名称，未改其余五插件。

运行中的 SPECTRUM 项目仍固定于原来的 source/Skill 身份，此次插件更新没有覆盖运行中程序、重置历史或迁移 pins。新检测器可以作为独立观察工具使用；以后采纳新的 Skill 身份须在安静边界按原有迁移流程执行。

另：hn01 的依赖和固定版本模型/数据集准备已完成（setup 环境状态 dependencies_exit_code=0、assets_exit_code=0）。下载完成不代表训练、评分或 B01 资格验收完成。

完整证据见 `../research-state/gpu-intake-20261018/`。SSH 密码、私钥、账号 token 均未写入交付。
