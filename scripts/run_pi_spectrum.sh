#!/usr/bin/env bash
# No implicit GPU launch, download, or background execution.
set -euo pipefail
stage="${1:-help}"
config="${2:-configs/pi_spectrum/pi_selfteacher_7b_r10_4096.yaml}"
case "$stage" in
  check)
    python -m compileall -q src/improving tests/test_pi_spectrum.py
    python -m pytest tests/test_pi_spectrum.py tests/test_gain_pipeline.py tests/test_learned_gains.py tests/test_pipeline.py -q
    python -m improving.cli validate --config "$config"
    ;;
  validate)
    python -m improving.cli validate --config "$config"
    ;;
  run)
    python -m improving.cli run --config "$config"
    ;;
  resume)
    python -m improving.cli run --config "$config" --resume
    ;;
  *)
    echo "Usage: bash scripts/run_pi_spectrum.sh check|validate|run|resume [CONFIG]" >&2
    exit 2
    ;;
esac
