#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/mnt/c/Users/moham/OneDrive/Documents/Rule-Based-Drones"
LOG_DIR="${PROJECT_DIR}/sitl-logs"
MAVSDK_SERVER_BIN="$(find "${PROJECT_DIR}/.venv/lib" -path '*/site-packages/mavsdk/bin/mavsdk_server' | head -n 1)"

mkdir -p "$LOG_DIR"

if [ -z "$MAVSDK_SERVER_BIN" ] || [ ! -x "$MAVSDK_SERVER_BIN" ]; then
  echo "mavsdk_server binary not found in the project virtual environment." >&2
  exit 1
fi

declare -a pids=()

wait_for_log_pattern() {
  local log_file="$1"
  local pattern="$2"
  local timeout_s="${3:-60}"
  local waited_s=0

  while true; do
    if [ -f "$log_file" ] && grep -Eq "$pattern" "$log_file"; then
      return 0
    fi

    if [ "$waited_s" -ge "$timeout_s" ]; then
      echo "Timed out waiting for '$pattern' in ${log_file}." >&2
      tail -n 20 "$log_file" >&2 || true
      return 1
    fi

    sleep 2
    waited_s=$((waited_s + 2))
  done
}

start_sidecar() {
  local sysid="$1"
  local grpc_port="$2"
  local udp_port="$3"
  local log_file="${LOG_DIR}/mavsdk_${sysid}.log"
  local pid_file="${LOG_DIR}/mavsdk_${sysid}.pid"

  setsid "$MAVSDK_SERVER_BIN" \
    -p "$grpc_port" \
    "udpin://0.0.0.0:${udp_port}" \
    >"$log_file" 2>&1 &

  echo "$!" > "$pid_file"
  pids+=("$!")
  wait_for_log_pattern "$log_file" "System discovered|Server started"
}

start_sidecar 1 50040 14650
start_sidecar 2 50041 14660
start_sidecar 3 50042 14670
start_sidecar 4 50043 14680
start_sidecar 5 50044 14690
start_sidecar 6 50045 14700

echo "Started MAVSDK sidecars:"
printf '%s\n' "${pids[@]}"
