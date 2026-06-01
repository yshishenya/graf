#!/usr/bin/env sh
set -eu

DURATION_SECONDS=${DURATION_SECONDS:-35}
INTERVAL_SECONDS=${INTERVAL_SECONDS:-1}
THRESHOLD_PERCENT=${THRESHOLD_PERCENT:-10}
SUSTAINED_LIMIT_SECONDS=${SUSTAINED_LIMIT_SECONDS:-30}

pid=$(pgrep -x coreaudiod | head -n 1 || true)
if [ -z "$pid" ]; then
  echo "coreaudiod_cpu_result=blocked"
  echo "failure_reason=coreaudiod_not_running"
  exit 2
fi

peak="0"
sustained_seconds=0
max_sustained_seconds=0
elapsed=0

while [ "$elapsed" -lt "$DURATION_SECONDS" ]; do
  cpu=$(ps -o %cpu= -p "$pid" | awk '{gsub(/^[ \t]+|[ \t]+$/, "", $0); print $0 + 0}')
  peak=$(awk -v a="$peak" -v b="$cpu" 'BEGIN { print (a > b ? a : b) }')

  over_threshold=$(awk -v cpu="$cpu" -v threshold="$THRESHOLD_PERCENT" 'BEGIN { print (cpu > threshold ? 1 : 0) }')
  if [ "$over_threshold" -eq 1 ]; then
    sustained_seconds=$((sustained_seconds + INTERVAL_SECONDS))
    if [ "$sustained_seconds" -gt "$max_sustained_seconds" ]; then
      max_sustained_seconds=$sustained_seconds
    fi
  else
    sustained_seconds=0
  fi

  sleep "$INTERVAL_SECONDS"
  elapsed=$((elapsed + INTERVAL_SECONDS))
done

echo "coreaudiod_pid=$pid"
echo "duration_seconds=$DURATION_SECONDS"
echo "threshold_percent=$THRESHOLD_PERCENT"
echo "peak_percent=$peak"
echo "max_sustained_seconds_above_threshold=$max_sustained_seconds"

if [ "$max_sustained_seconds" -gt "$SUSTAINED_LIMIT_SECONDS" ] || [ "$max_sustained_seconds" -eq "$SUSTAINED_LIMIT_SECONDS" ]; then
  echo "coreaudiod_cpu_result=blocked"
  echo "failure_reason=sustained_cpu_above_threshold"
  exit 2
fi

echo "coreaudiod_cpu_result=passed"
