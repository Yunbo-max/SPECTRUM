#!/usr/bin/env bash
set -euo pipefail
REPO=/inspire/hdd/global_user/zhangjiaquan-253108540222/backup/improving-learned
VENV=/inspire/hdd/global_user/zhangjiaquan-253108540222/backup/improving/.venv
export PYTHONPATH="$REPO/src"
export SPECTRUM_PYTHON="$VENV/bin/python"
export HF_HOME=/inspire/hdd/global_user/zhangjiaquan-253108540222/hf_cache
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True PYTHONFAULTHANDLER=1
export OMP_NUM_THREADS=8 MKL_NUM_THREADS=8
unset PIP_CONSTRAINT
cd "$REPO"
echo "=== $(date -Is) spectral_learned 4096 ten-round run start ==="
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader
bash scripts/run_spectrum_learned_4096.sh
echo "=== $(date -Is) spectral_learned 4096 ten-round run DONE ==="
