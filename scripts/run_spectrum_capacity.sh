#!/usr/bin/env bash
set -euo pipefail
REPO=/inspire/hdd/global_user/zhangjiaquan-253108540222/backup
P=$REPO/improving
CFG=$REPO/improving/configs/spectrum_7b
SHARED=/inspire/hdd/global_user/zhangjiaquan-253108540222
export HF_HOME=$SHARED/hf_cache
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True PYTHONFAULTHANDLER=1
export OMP_NUM_THREADS=8 MKL_NUM_THREADS=8
unset PIP_CONSTRAINT
. "$P/.venv/bin/activate"
cd "$P"
for C in \
  "$CFG/spectrum_7b_ts64.yaml" \
  "$CFG/spectrum_7b_ts128.yaml" \
  "$CFG/spectrum_7b_rank16.yaml" \
  "$CFG/spectrum_7b_rank32.yaml" \
  "$CFG/spectrum_7b_rank64.yaml" \
; do
  echo "=== $(date -Is) RUN $C ==="
  python -u -m improving run --config "$C" --resume
done
echo "=== $(date -Is) ALL CAPACITY SWEEP DONE ==="
