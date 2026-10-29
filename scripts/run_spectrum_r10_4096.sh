#!/usr/bin/env bash
# Explicit launcher for the new 4096-token MBPP ten-round comparison.
set -euo pipefail

SPECTRUM_REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SPECTRUM_PYTHON="${SPECTRUM_PYTHON:-python}"
arm="${1:-}"
resume=()
if [[ $# -gt 2 || ( $# -eq 2 && "$2" != "--resume" ) ]]; then
  echo 'Usage: bash scripts/run_spectrum_r10_4096.sh {plain|spectral|both} [--resume]' >&2
  exit 2
fi
case "$arm" in
  plain|spectral) arms=("$arm") ;;
  both) arms=(plain spectral) ;;
  *) echo 'Usage: bash scripts/run_spectrum_r10_4096.sh {plain|spectral|both} [--resume]' >&2; exit 2 ;;
esac
if [[ "${2:-}" == "--resume" ]]; then resume=(--resume); fi
cd "$SPECTRUM_REPO_ROOT"
for selected in "${arms[@]}"; do
  config="configs/spectrum_7b/spectrum_7b_r10_${selected}_4096.yaml"
  "$SPECTRUM_PYTHON" -m improving.cli validate --config "$config"
  "$SPECTRUM_PYTHON" -m improving.cli run --config "$config" "${resume[@]}"
done
