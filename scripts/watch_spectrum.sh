#!/usr/bin/env bash
# Background watcher for the spectrum-7b-all-operators job.
# Appends a status line every CHECK_INTERVAL seconds; exits when the job
# reaches a terminal state (succeeded/failed) so the monitor log has history.
set -u

JOB_ID="${1:-job-02dc7f7e-da31-4536-81b9-81ccf9eff61b}"
MAIN_LOG=/inspire/hdd/global_user/zhangjiaquan-253108540222/ICLR2027/logs/qz/spectrum_7b_all_operators.log
MON_LOG=/inspire/hdd/global_user/zhangjiaquan-253108540222/ICLR2027/logs/qz/spectrum_7b_all_operators.monitor.log
RUNS=/inspire/hdd/global_user/zhangjiaquan-253108540222/ICLR2027/new/solution_coupling/runs
CHECK_INTERVAL="${2:-120}"

while true; do
  TS=$(date -Is)
  STATUS=$(qz train GetJob --job-id "$JOB_ID" 2>/dev/null \
    | python3 -c "import json,sys; print(json.load(sys.stdin).get('Result',{}).get('status','unknown'))" 2>/dev/null)
  CUR=$(grep -oE "RUN .*?spectrum_7b_[a-z0-9_]+\.yaml" "$MAIN_LOG" 2>/dev/null | tail -1 | sed 's#.*/##')
  BASE_PARTS=$(ls "$RUNS"/spectrum_7b_sweep_v1/base/evaluation.jsonl.parts/ 2>/dev/null | grep -c '\.json$')
  SWEEP_ARMS=$(find "$RUNS"/spectrum_7b_sweep_v1 -maxdepth 3 -name complete.json 2>/dev/null | wc -l)
  ERR=$(grep -iE "error|traceback|exception|nonfinite|out of memory" "$MAIN_LOG" 2>/dev/null | tail -1)
  echo "[$TS] status=$STATUS config=$CUR base_parts=$BASE_PARTS sweep_complete=$SWEEP_ARMS ${ERR:+ERR:$ERR}" >> "$MON_LOG"
  if [ "$STATUS" = "job_succeeded" ] || [ "$STATUS" = "job_failed" ]; then
    echo "[$TS] TERMINAL=$STATUS -- final log tail:" >> "$MON_LOG"
    tail -40 "$MAIN_LOG" >> "$MON_LOG" 2>/dev/null
    exit 0
  fi
  sleep "$CHECK_INTERVAL"
done
