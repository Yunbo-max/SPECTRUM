# Sampler source audit — 2026-10-18

The SSD paper AppendixA names vLLM0.11.0 at commitb8b302cde434df8c9289a2b465406b47ebab1c2d. The installed vLLM0.10.0 is retained on hn01; no upgrade or sampler replacement was performed during the active run. The model log confirms the PyTorch-native sampling path.

Retrieved the pinned source through GitHub codeload after raw.githubusercontent.com timed out with zero bytes. Archive hash, installed-source hashes, pinned-source hashes, relevant files, license and selected-function diff are retained in sampler-source-audit. The installed and paper-pinned apply_top_k_top_p and random_sample functions have identical Python ASTs. Both retain temperature → top-k → renormalized top-p → exponential-noise sampling ordering.

The reviewed apply_temperature difference guards division by zero for mixed greedy/random batches in0.11; the current T0.7 condition is all random and takes the unchanged division operation. The sample/forward_native differences add processed-logprob return values; the current request does not ask for those values. The pinned class binds self.apply_top_k_top_p to the same audited function. These findings support source-level sampling semantics for this configuration. They do not prove identical numerical logits, model kernels, request scheduling or random trajectories across versions/hardware. Keep the dependency adaptation explicit in any result report.

Sources: [paper-pinned sampler](https://github.com/vllm-project/vllm/blob/b8b302cde434df8c9289a2b465406b47ebab1c2d/vllm/v1/sample/sampler.py), [paper-pinned top-k/top-p implementation](https://github.com/vllm-project/vllm/blob/b8b302cde434df8c9289a2b465406b47ebab1c2d/vllm/v1/sample/ops/topk_topp_sampler.py), installed source captured from the running environment.
