#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/mnt/c/Users/moham/OneDrive/Documents/Rule-Based-Drones"
QGC_APPIMAGE="${HOME}/Applications/QGroundControl-x86_64.AppImage"

cd "$PROJECT_DIR"
. .venv/bin/activate

pkill -TERM -f 'xterm .*ArduCopter' || true
pkill -TERM -f 'mavproxy.py' || true
pkill -TERM -f 'mavsdk_server' || true
pkill -TERM -f 'QGroundControl' || true
pkill -TERM -f 'Tools/autotest/sim_vehicle.py' || true
pkill -TERM -f '/home/mohd/ardupilot/build/sitl/bin/arducopter' || true
sleep 3

bash start_sitl_instances.sh
bash start_mavsdk_sidecars.sh

if [ ! -x "$QGC_APPIMAGE" ]; then
  echo "QGroundControl AppImage not found or not executable at $QGC_APPIMAGE" >&2
  echo "Run: chmod +x $QGC_APPIMAGE" >&2
  exit 1
fi

setsid "$QGC_APPIMAGE" >/dev/null 2>&1 &

cat <<'EOF'
Full 6-drone stack started.

QGC telemetry UDP ports:
- 14550
- 14560
- 14570
- 14580
- 14590
- 14600

MAVSDK sidecar gRPC endpoints:
- drone_1 -> grpc://127.0.0.1:50040
- drone_2 -> grpc://127.0.0.1:50041
- drone_3 -> grpc://127.0.0.1:50042
- drone_4 -> grpc://127.0.0.1:50043
- drone_5 -> grpc://127.0.0.1:50044
- drone_6 -> grpc://127.0.0.1:50045
EOF
