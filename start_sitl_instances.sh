#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/mnt/c/Users/moham/OneDrive/Documents/Rule-Based-Drones"
ARDUPILOT_DIR="/home/mohd/ardupilot"
LOG_DIR="${PROJECT_DIR}/sitl-logs"
VENV_PYTHON="${PROJECT_DIR}/.venv/bin/python"

mkdir -p "$LOG_DIR"
cd "$ARDUPILOT_DIR"

if [ ! -x "$VENV_PYTHON" ]; then
  echo "Virtual environment Python not found at $VENV_PYTHON" >&2
  exit 1
fi

if ! "$VENV_PYTHON" - <<'PY'
import pexpect
PY
then
  echo "pexpect is not installed in the project virtual environment." >&2
  exit 1
fi

if ! "$VENV_PYTHON" - <<'PY'
import em
PY
then
  echo "empy/em is not installed in the project virtual environment." >&2
  echo "Install it with: . .venv/bin/activate && python -m pip install empy==3.3.4" >&2
  exit 1
fi

declare -a pids=()

wait_for_port() {
  local port="$1"
  local timeout_s="${2:-180}"
  local waited_s=0

  while true; do
    if ss -ltn | awk '{print $4}' | grep -Eq ":${port}$"; then
      return 0
    fi

    if [ "$waited_s" -ge "$timeout_s" ]; then
      echo "Timed out waiting for SITL port ${port} to become ready." >&2
      return 1
    fi

    sleep 2
    waited_s=$((waited_s + 2))
  done
}

start_instance() {
  local sysid="$1"
  local instance="$2"
  local qgc_udp_port="$3"
  local sdk_udp_port="$4"
  local tcp_port="$5"
  local custom_location="$6"
  local log_file="${LOG_DIR}/sitl_${sysid}.log"
  local bridge_log_file="${LOG_DIR}/bridge_${sysid}.log"
  local pid_file="${LOG_DIR}/sitl_${sysid}.pid"
  local bridge_pid_file="${LOG_DIR}/bridge_${sysid}.pid"
  local use_dir="${LOG_DIR}/use-dir-${sysid}"

  mkdir -p "$use_dir"

  setsid "$VENV_PYTHON" Tools/autotest/sim_vehicle.py \
    -v ArduCopter \
    -f quad \
    --no-mavproxy \
    --use-dir "$use_dir" \
    --instance "$instance" \
    --sysid "$sysid" \
    --custom-location "$custom_location" \
    --out="udp:127.0.0.1:${qgc_udp_port}" \
    --out="udp:127.0.0.1:${sdk_udp_port}" \
    >"$log_file" 2>&1 &

  echo "$!" > "$pid_file"
  pids+=("$!")
  wait_for_port "$tcp_port"

  setsid mavproxy.py \
    --force-connected \
    --master="tcp:127.0.0.1:${tcp_port}" \
    --out="127.0.0.1:${qgc_udp_port}" \
    --out="127.0.0.1:${sdk_udp_port}" \
    --daemon \
    --non-interactive \
    --streamrate=10 \
    >"$bridge_log_file" 2>&1 &

  echo "$!" > "$bridge_pid_file"
  pids+=("$!")
}

start_instance 1 0 14550 14650 5760 "-35.363262,149.165237,584,353"
sleep 30
start_instance 2 1 14560 14660 5770 "-35.364262,149.166237,584,353"
sleep 30
start_instance 3 2 14570 14670 5780 "-35.365262,149.167237,584,353"
sleep 30
start_instance 4 3 14580 14680 5790 "-35.366262,149.168237,584,353"
sleep 30
start_instance 5 4 14590 14690 5800 "-35.367262,149.169237,584,353"
sleep 30
start_instance 6 5 14600 14700 5810 "-35.368262,149.170237,584,353"

echo "Started SITL instances:"
printf '%s\n' "${pids[@]}"
