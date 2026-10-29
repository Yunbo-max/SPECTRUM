#!/usr/bin/env bash
set -euo pipefail
REPO=/inspire/hdd/global_user/zhangjiaquan-253108540222/ICLR2027
P=$REPO/improving
C=$REPO/new/solution_coupling/configs/spectrum_7b_sweep_v1.yaml
SHARED=/inspire/hdd/global_user/zhangjiaquan-253108540222
export HF_HOME=$SHARED/hf_cache
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True PYTHONFAULTHANDLER=1
export OMP_NUM_THREADS=8 MKL_NUM_THREADS=8
unset PIP_CONSTRAINT
. "$P/.venv/bin/activate"
cd "$P"
echo "=== $(date -Is) spectrum sweep v1 ==="
python -u -m improving run --config "$C"
echo "=== $(date -Is) spectrum sweep v1 DONE ==="
