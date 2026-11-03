#!/usr/bin/env bash
set -euo pipefail
REPO=/inspire/hdd/global_user/zhangjiaquan-253108540222/backup/SPECTRUM-transfer-gap
VENV=/inspire/hdd/global_user/zhangjiaquan-253108540222/backup/improving/.venv
export PYTHONPATH="$REPO/src"
export HF_HOME=/inspire/hdd/global_user/zhangjiaquan-253108540222/hf_cache
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True PYTHONFAULTHANDLER=1
export OMP_NUM_THREADS=8 MKL_NUM_THREADS=8
unset PIP_CONSTRAINT
cd "$REPO"
echo "=== $(date -Is) transfer-gap learned qualify start ==="
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader
echo "--- isolation backend check ---"
command -v docker >/dev/null 2>&1 && echo "docker: $(docker --version)" || echo "docker: NOT FOUND"
command -v bwrap >/dev/null 2>&1 && echo "bwrap: $(bwrap --version 2>&1 | head -1)" || echo "bwrap: NOT FOUND"
"$VENV/bin/python" -u scripts/qualify_learned_gains.py \
  --config configs/spectrum_7b/transfer_gap_learned_4096.yaml \
  --output-dir runs/qualification/transfer_gap_learned_round1
echo "=== $(date -Is) transfer-gap learned qualify DONE ==="
