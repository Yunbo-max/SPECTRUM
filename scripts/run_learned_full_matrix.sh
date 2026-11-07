#!/usr/bin/env bash
# Explicit sequential launcher: dry-run by default, --execute required to run.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
stage=""
execute=0
model="all"
for arg in "$@"; do
  case "$arg" in
    --execute) execute=1 ;;
    --model=*) model="${arg#--model=}" ;;
    prep-code|prep-text|prep-gpqa|qualify-code|qualify-text|train-code|transfer-code|math|qa|qa-gpqa|status|budget|all) stage="$arg" ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done
if [[ -z "$stage" ]]; then
  echo "Usage: bash scripts/run_learned_full_matrix.sh STAGE [--execute] [--model=qwen7b|llama8b|deepseek6.7b|all]" >&2
  exit 2
fi
case "$model" in qwen7b|llama8b|deepseek6.7b|all) ;; *) echo "Invalid model" >&2; exit 2;; esac
P="${SPECTRUM_PYTHON:-python}"
CF=(--assets configs/crossfamily/assets.json
    --protocol configs/crossfamily/protocol_learned_4096.json
    --data-root data/crossfamily
    --run-root runs/crossfamily_learned_r5_4096
    --seed-file runs/private/crossfamily_code_v1.json)
MATH=configs/multidomain/text_math_learned.json
QA=configs/multidomain/text_qa_learned.json
GPQA=configs/multidomain/text_qa_gpqa_learned.json
launch() {
  printf 'COMMAND:'
  printf ' %q' "$@"
  printf '\n'
  if (( execute )); then "$@"; fi
}
run_text() {
  local cfg="$1"
  for method in base plain ssd spectral_soft spectral_learned; do
    launch "$P" scripts/run_text_study.py --config "$cfg" --method "$method" --resume
  done
}
case "$stage" in
  budget)
    launch "$P" scripts/plan_learned_full_matrix.py ;;
  prep-code)
    launch "$P" scripts/run_crossfamily_study.py init "${CF[@]}"
    launch "$P" scripts/run_crossfamily_study.py download "${CF[@]}" --model "$model"
    launch "$P" scripts/run_crossfamily_study.py prepare "${CF[@]}"
    launch "$P" scripts/run_crossfamily_study.py plan "${CF[@]}"
    launch "$P" scripts/run_learned_extra_transfers.py prepare ;;
  prep-text)
    launch "$P" scripts/prepare_text_data.py --config "$MATH"
    launch "$P" scripts/prepare_text_data.py --config "$QA" ;;
  prep-gpqa)
    launch "$P" scripts/prepare_text_data.py --config "$GPQA" ;;
  qualify-code)
    models=(qwen7b llama8b deepseek6.7b)
    if [[ "$model" != all ]]; then models=("$model"); fi
    for alias in "${models[@]}"; do
      launch "$P" scripts/qualify_learned_matrix.py \
        --config "runs/crossfamily_learned_r5_4096/plan/configs/$alias.json" \
        --output-dir "runs/qualification/learned_full/$alias"
    done ;;
  qualify-text)
    launch "$P" scripts/qualify_learned_matrix.py --config "$MATH" \
      --output-dir runs/qualification/learned_full/math
    launch "$P" scripts/qualify_learned_matrix.py --config "$QA" \
      --output-dir runs/qualification/learned_full/qa ;;
  train-code)
    launch "$P" scripts/run_crossfamily_study.py run "${CF[@]}" --model "$model" --stage train ;;
  transfer-code)
    launch "$P" scripts/run_crossfamily_study.py run "${CF[@]}" --model "$model" --stage transfer
    launch "$P" scripts/run_learned_extra_transfers.py run --model "$model" ;;
  math) run_text "$MATH" ;;
  qa) run_text "$QA" ;;
  qa-gpqa) run_text "$GPQA" ;;
  status)
    launch "$P" scripts/run_crossfamily_study.py status "${CF[@]}"
    launch "$P" scripts/run_text_study.py --config "$MATH" --report
    launch "$P" scripts/run_text_study.py --config "$QA" --report ;;
  all)
    echo "WARNING: millions of long completions; read capacity budget first."
    for phase in prep-code prep-text qualify-code qualify-text train-code transfer-code math qa status; do
      if (( execute )); then
        bash "$0" "$phase" --model="$model" --execute
      else
        bash "$0" "$phase" --model="$model"
      fi
    done ;;
esac
