#!/usr/bin/env bash
set -euo pipefail
REPO=/inspire/hdd/global_user/zhangjiaquan-253108540222/backup/improving
export HF_HOME=/inspire/hdd/global_user/zhangjiaquan-253108540222/hf_cache
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True PYTHONFAULTHANDLER=1
export OMP_NUM_THREADS=8 MKL_NUM_THREADS=8
unset PIP_CONSTRAINT
cd "$REPO"
. "$REPO/.venv/bin/activate"
echo "=== $(date -Is) spectral 4096 run start ==="
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader
python -u -m improving.cli run --config configs/spectrum_7b/spectrum_7b_r10_spectral_4096.yaml
echo "=== $(date -Is) spectral 4096 DONE ==="
