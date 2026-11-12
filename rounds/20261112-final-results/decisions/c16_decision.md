# c16（HumanEval+ 冻结迁移 n64）停跑判定（2026-11-12，用户拍板）

**结论：停止新跑，回复用历史证据 + c17 交叉引用。**

理由：
1. c16 为 P1。迁移审稿问题（F6/Y7）已有：c17（APPS Intro）新鲜 n64 完成（2026-11-11，receipt 完整）；
   历史 HumanEval+ n16 迁移数字存于 git 归档 `research/audit/observed_results.json`
   （frozen_humaneval_transfer_n16，completed_historical，164 题、每任务 16 采样、含 AST richness 均值与 CI）。
2. c16 是唯一需要"GPU 生成 → 平台回收（验证阶段 GPU 空转）→ 本机 CPU 验证 → resume"两段式编排的作业，
   ~20 GPU-h + 多日编排复杂度，边际证据价值低。
3. 平台 auto-recycle（GPU<40 持续 3h）使该类纯 CPU 验证作业反复被回收，工程上不经济。

引用约定（写进回复/论文）：
- HumanEval+ 迁移：引用归档历史 n16 数字，标注"自 2026-10-02 审计归档恢复，原始逐题工件未保留；n64 未重跑"。
- APPS Intro 迁移：引用 c17 新鲜 n64（本轮 rebuttal 框架内真实运行）。
- 已生成的 c16 v6 部分输出（base ~60%）保留在 runs/iclr2027_rebuttal_transfer_{plain,fixed}_v6/c16/run，
  只作档案，不进主表。
