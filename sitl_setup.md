# Phase 6 SITL Setup

This project is designed to move from the decentralized simulation stack into ArduPilot + QGC + MAVSDK hardware execution.

## Assumptions

- ArduPilot is already installed.
- QGC is already installed.
- You are running the code in WSL Ubuntu 22.04.
- The project virtual environment is available at `.venv`.

## Install the runtime dependency

If you want to run the MAVSDK executor against SITL or hardware, install MAVSDK in the virtual environment:

```bash
cd /mnt/c/Users/moham/OneDrive/Documents/Rule-Based-Drones
. .venv/bin/activate
python -m pip install mavsdk
```

## Recommended transport architecture

- Operator workstation: MAVLink mission package and control interface
- Drone companion computer: MAVSDK executor
- Inter-drone transport: 802.11s Wi-Fi mesh
- Vehicle routing: `mavlink-router`
- Ground control station: QGC

This keeps the swarm decentralized:

- mission meaning is compiled centrally
- role feasibility and execution are local to each drone
- vehicle-to-vehicle communication stays on the mesh
- flight control remains on ArduPilot

## SITL launch pattern

For testing, run one SITL instance per drone with unique system IDs and UDP output ports.

Example pattern:

```bash
sim_vehicle.py -v ArduCopter -f quad --instance 0 --sysid 1 --console --map --out=udp:127.0.0.1:14550
sim_vehicle.py -v ArduCopter -f quad --instance 1 --sysid 2 --console --map --out=udp:127.0.0.1:14560
sim_vehicle.py -v ArduCopter -f quad --instance 2 --sysid 3 --console --map --out=udp:127.0.0.1:14570
sim_vehicle.py -v ArduCopter -f quad --instance 3 --sysid 4 --console --map --out=udp:127.0.0.1:14580
sim_vehicle.py -v ArduCopter -f quad --instance 4 --sysid 5 --console --map --out=udp:127.0.0.1:14590
sim_vehicle.py -v ArduCopter -f quad --instance 5 --sysid 6 --console --map --out=udp:127.0.0.1:14600
```

Adjust the port layout to match your local routing rules and QGC setup.

## QGC

Open QGC and connect it to the appropriate UDP endpoints. QGC can monitor the vehicles while the operator workstation sends mission packages and the local executors handle role-level execution.

## Operator command example

Dry-run the hardware pipeline:

```bash
cd /mnt/c/Users/moham/OneDrive/Documents/Rule-Based-Drones
. .venv/bin/activate
python operator.py \
  --dry-run \
  --command "Deploy four drones to patrol the pipeline corridor and monitor for suspicious activity." \
  --vehicle drone_1=tcpout://127.0.0.1:5760 \
  --vehicle drone_2=tcpout://127.0.0.1:5770 \
  --vehicle drone_4=tcpout://127.0.0.1:5780 \
  --vehicle drone_5=tcpout://127.0.0.1:5790
```

When the MAVSDK package is installed and the connections are live, remove `--dry-run`.

## Notes for hardware transition

- Keep one executor process per vehicle.
- Do not centralize role choice in the operator process.
- Use the operator workstation to publish mission JSON and route role assignments.
- Use MAVSDK latency measurements to compare SITL and hardware behavior.
