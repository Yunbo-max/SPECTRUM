# c40（7B 十轮 Learned 40+10）复用判定（2026-11-10）

**结论：复用成立，不重跑。**

| c40 规格 | surviving 工件 | 判定 |
|---|---|---|
| qwen7b, seed 43 | manifest seed=43 | ✓ |
| 10 轮, 4096 tok, t16/e64 | rounds 10, max_new 4096 | ✓ |
| spectral_learned | methods=[spectral_learned] | ✓ |
| calibration 50（40 fit + 10 guard） | cal max_examples=50, gain_learning guard_examples=10 | ✓ |
| 模型身份 | public_models Qwen2.5-Coder-7B-Instruct 分片 sha256 == 工作区 pinned models/ 副本（0b6f0699… 一致） | ✓ 权重同源 |
| 工件完整性 | 10/10 轮 metrics + learned_gains.json + run_status completed | ✓ |

工件位置：`backup/improving-learned/runs/spectrum_7b/spectral_learned_7b_r10_4096/`。
出处说明（写进论文/回复）：该 arm 为 2026-11-02 完成的真实十轮运行（原论文扩展证据），
未在本轮 rebuttal 框架内重跑；数字引用该工件的 evaluation.metrics.json。
