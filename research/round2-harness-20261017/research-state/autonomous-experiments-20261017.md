# Latest explicit autonomous execution authorization

User: 小红书可以多看帖子讨论帖，然后剩下都交给你了，你这个循环做起来安装harness包括实验设计和实验在gpu的测试以及运行。
User: 我去睡觉了。
User: 应该没有故障，因为都是可以自动debug然后循环整个过程。

Continue SPECTRUM second-round research autonomously using the installed Work Harness and GPT-6-Astra. The objective now includes actual experiment design, native GPU qualification/tests, admitted experiments on the supplied host, result inspection, debugging, replication/repair and iterative research. Repeat the canonical research sequence; do not stop after a reading report. No operator-imposed cumulative attempt/time cap. Individual processes retain explicit watchdogs and experiment-specific execution budgets, with resumable checkpoints and cumulative accounting. Do not reset failed attempts or change success criteria to pass.

Relevant Xiaohongshu discussion posts and visible comments may be read serially without an arbitrary post quota. Search purposively, verify leads with primary sources/code, and preserve omissions. No posting, messaging, likes or bulk scraping.

Use SSH alias spectrum-harness-gpu. The parent established a dedicated local SSH key and verified noninteractive login; password is not stored. Native target is research-state/native-gpu-target-20261017.json. GPU qualification: Tesla T4 15360 MiB; PyTorch 2.12.1+cu130, CUDA available, sm_75 included; a real CUDA tensor sum returned 4.0. The 50 GB data volume was essentially empty; models and datasets still need staging. Do not use bfloat16 as though this T4 supports native bf16. Inspect memory/cgroup limits and installed dependencies; host total memory is not necessarily container allocation. Preserve live jobs. One experiment program at a time, native environment, no Docker. Install necessary project dependencies in a dedicated remote venv when needed; no new paid resources or APIs.

Remote paths: /root/rivermind-data/spectrum-harness/{project,skill,SPECTRUM}. Stage each admitted project's exact pinned files to the remote project before NativeBridge execution. Match skill digest and preserve run identity on retries. Git code pins are separate from research input pins; don't relabel historical results.

Recovery: inspect actual logs and receipts; automatically repair recoverable dependency/code/config errors, requalify, and resume the SAME retained run lineage. Reconcile unknown remote PIDs before retries. For transient network/provider failures use backoff and preserve pending work. Do not fabricate success, bypass denied access, loop identical failing commands without diagnosis, or declare the goal complete because a process failed. Human absence does not authorize destructive host cleanup or unrelated work.

Delivery: use research/round2-harness-20261017 in Yunbo-max/SPECTRUM. Parent configured the dedicated delivery worktree. After meaningful accepted milestones, the active serial worker is the integration writer (this supersedes prior parent-only restriction); copy current reviewed research reports/evidence there, commit named paths, push without force and verify remote hashes. Do not stage the original dirty checkout, secrets, auth/cookies, private keys, raw agent transcripts or *.local.json. Keep code/raw results/config/logs identifiable; store large model assets on the GPU volume and commit manifests instead. No paper submission or public messaging is authorized.

Current user intent supersedes historical read-only/no GPU/no Git passages in immutable records. The runtime program still owns node order and independent review; do not fake node completion or skip scientific obligations. Continue through the research sequence into actual admitted execution.
