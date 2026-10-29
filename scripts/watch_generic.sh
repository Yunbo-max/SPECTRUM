#!/usr/bin/env bash
# Generic background watcher: logs job status + current config + errors.
set -u
JOB_ID="${1:?job id}"
MAIN_LOG="${2:?main log path}"
MON_LOG="${3:?monitor log path}"
INTERVAL="${4:-120}"

while true; do
  TS=$(date -Is)
  STATUS=$(qz train GetJob --job-id "$JOB_ID" 2>/dev/null \
    | python3 -c "import json,sys; print(json.load(sys.stdin).get('Result',{}).get('status','unknown'))" 2>/dev/null)
  CUR=$(grep -oE "RUN .*?\.yaml" "$MAIN_LOG" 2>/dev/null | tail -1 | sed 's#.*/##')
  ERR=$(grep -iE "error|traceback|exception|nonfinite|out of memory|RuntimeError" "$MAIN_LOG" 2>/dev/null | grep -viE "SyntaxWarning" | tail -1)
  echo "[$TS] status=$STATUS config=$CUR ${ERR:+ERR:$ERR}" >> "$MON_LOG"
  if [ "$STATUS" = "job_succeeded" ] || [ "$STATUS" = "job_failed" ]; then
    echo "[$TS] TERMINAL=$STATUS -- final log tail:" >> "$MON_LOG"
    tail -50 "$MAIN_LOG" >> "$MON_LOG" 2>/dev/null
    exit 0
  fi
  sleep "$INTERVAL"
done
