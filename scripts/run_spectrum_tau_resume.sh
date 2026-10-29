#!/usr/bin/env bash
set -euo pipefail
REPO=/inspire/hdd/global_user/zhangjiaquan-253108540222/backup
P=$REPO/improving
C=${1:?usage: run_spectrum_tau_resume.sh <config_abs_path>}
SHARED=/inspire/hdd/global_user/zhangjiaquan-253108540222
export HF_HOME=$SHARED/hf_cache
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True PYTHONFAULTHANDLER=1
export OMP_NUM_THREADS=8 MKL_NUM_THREADS=8
unset PIP_CONSTRAINT
. "$P/.venv/bin/activate"
cd "$P"
echo "=== $(date -Is) spectrum tau RESUME: $C ==="
python -u -m improving run --config "$C" --resume
echo "=== $(date -Is) DONE: $C ==="
