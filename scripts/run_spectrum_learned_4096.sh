#!/usr/bin/env bash
# Explicit opt-in launcher; no implicit baseline queue or background submission.
set -euo pipefail

SPECTRUM_REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SPECTRUM_PYTHON="${SPECTRUM_PYTHON:-python}"
SPECTRUM_CONFIG="${SPECTRUM_CONFIG:-configs/spectrum_7b/spectrum_7b_r10_learned_4096.yaml}"
resume=()
if [[ $# -gt 1 || ( $# -eq 1 && "$1" != "--resume" ) ]]; then
  echo 'Usage: bash scripts/run_spectrum_learned_4096.sh [--resume]' >&2
  echo 'Optional environment: SPECTRUM_CONFIG, SPECTRUM_PYTHON' >&2
  exit 2
fi
if [[ "${1:-}" == "--resume" ]]; then resume=(--resume); fi
cd "$SPECTRUM_REPO_ROOT"
if [[ ! -f "$SPECTRUM_CONFIG" ]]; then
  echo "Configuration not found: $SPECTRUM_CONFIG" >&2
  exit 2
fi
"$SPECTRUM_PYTHON" -m improving.cli validate --config "$SPECTRUM_CONFIG"
"$SPECTRUM_PYTHON" -m improving.cli run --config "$SPECTRUM_CONFIG" "${resume[@]}"
