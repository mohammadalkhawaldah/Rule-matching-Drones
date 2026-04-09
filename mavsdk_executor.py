import asyncio
import json
import math
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from mavsdk import System
    from mavsdk.mavlink_direct import MavlinkMessage
except ImportError:  # pragma: no cover - optional dependency during static checks
    System = None
    MavlinkMessage = None


class MAVSDKExecutorError(RuntimeError):
    """Raised when a MAVSDK-backed execution cannot be performed."""


@dataclass
class ExecutionTelemetry:
    connection_latency_ms: Optional[float] = None
    arm_latency_ms: Optional[float] = None
    takeoff_latency_ms: Optional[float] = None
    land_latency_ms: Optional[float] = None
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connection_latency_ms": self.connection_latency_ms,
            "arm_latency_ms": self.arm_latency_ms,
            "takeoff_latency_ms": self.takeoff_latency_ms,
            "land_latency_ms": self.land_latency_ms,
            "notes": list(self.notes),
        }


@dataclass
class RoleExecutionReport:
    drone_id: str
    role_name: str
    system_address: str
    dry_run: bool
    telemetry: ExecutionTelemetry
    planned_actions: List[str] = field(default_factory=list)
    executed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "drone_id": self.drone_id,
            "role_name": self.role_name,
            "system_address": self.system_address,
            "dry_run": self.dry_run,
            "telemetry": self.telemetry.to_dict(),
            "planned_actions": list(self.planned_actions),
            "executed": self.executed,
        }


class MAVSDKExecutor:
    """
    Physical execution boundary for one drone.

    This class is intentionally local to a single vehicle. It does not perform
    swarm-level matching or role ranking. The operator provides the assigned
    role and mission context, and the executor handles only the vehicle it owns.
    """

    def __init__(
        self,
        drone_id: str,
        system_address: str,
        *,
        dry_run: bool = True,
        mavsdk_server_port: int = 50051,
        default_takeoff_altitude_m: float = 10.0,
        connection_timeout_s: float = 60.0,
        action_timeout_s: float = 20.0,
        connection_attempts: int = 1,
        connection_retry_delay_s: float = 5.0,
    ) -> None:
        self.drone_id = drone_id
        self.system_address = system_address
        self.dry_run = dry_run
        self.mavsdk_server_port = mavsdk_server_port
        self.default_takeoff_altitude_m = default_takeoff_altitude_m
        self.connection_timeout_s = connection_timeout_s
        self.action_timeout_s = action_timeout_s
        self.connection_attempts = connection_attempts
        self.connection_retry_delay_s = connection_retry_delay_s
        self.system = None
        self.motion_settle_s = 8.0

    async def execute_role(
        self,
        role: Dict[str, Any],
        mission: Dict[str, Any],
    ) -> RoleExecutionReport:
        role_name = str(role.get("name", "")).strip()
        telemetry = ExecutionTelemetry()
        planned_actions = self._build_planned_actions(role_name, mission)
        print(f"{self.drone_id}: role={role_name} start", flush=True)

        if self.dry_run:
            telemetry.notes.append("Dry run mode: no MAVSDK calls were made.")
            print(f"{self.drone_id}: dry run complete", flush=True)
            return RoleExecutionReport(
                drone_id=self.drone_id,
                role_name=role_name,
                system_address=self.system_address,
                dry_run=True,
                telemetry=telemetry,
                planned_actions=planned_actions,
                executed=False,
            )

        if System is None:
            raise MAVSDKExecutorError(
                "mavsdk is not installed in the current environment. "
                "Install it in the virtual environment before running hardware mode."
            )

        try:
            await self._connect(telemetry)
            await self._arm_move_land_cycle(role, mission, telemetry, planned_actions)
            print(f"{self.drone_id}: role={role_name} complete", flush=True)
        finally:
            self._shutdown_backend()

        return RoleExecutionReport(
            drone_id=self.drone_id,
            role_name=role_name,
            system_address=self.system_address,
            dry_run=False,
            telemetry=telemetry,
            planned_actions=planned_actions,
            executed=True,
        )

    async def _connect(self, telemetry: ExecutionTelemetry) -> None:
        connect_started = time.perf_counter()
        last_error: Optional[BaseException] = None
        grpc_target = self._parse_grpc_target(self.system_address)

        if grpc_target is not None:
            host, port = grpc_target
            self.system = System(mavsdk_server_address=host, port=port)
        else:
            self._cleanup_stale_backends()
            self.system = System(port=self.mavsdk_server_port)

        for attempt in range(1, self.connection_attempts + 1):
            print(f"{self.drone_id}: connecting attempt {attempt}/{self.connection_attempts}", flush=True)
            try:
                if grpc_target is not None:
                    await asyncio.wait_for(
                        self.system.connect(),
                        timeout=self.connection_timeout_s,
                    )
                else:
                    await asyncio.wait_for(
                        self.system.connect(system_address=self.system_address),
                        timeout=self.connection_timeout_s,
                    )
                await asyncio.wait_for(
                    self._wait_for_connection_state(),
                    timeout=self.connection_timeout_s,
                )
                telemetry.connection_latency_ms = (time.perf_counter() - connect_started) * 1000.0
                telemetry.notes.append(f"Connected to {self.system_address}.")
                print(f"{self.drone_id}: connected", flush=True)
                return
            except Exception as exc:
                last_error = exc
                telemetry.notes.append(
                    f"Connection attempt {attempt}/{self.connection_attempts} failed: {exc!r}"
                )
                if attempt < self.connection_attempts:
                    await asyncio.sleep(self.connection_retry_delay_s)

        telemetry.connection_latency_ms = (time.perf_counter() - connect_started) * 1000.0
        telemetry.notes.append(f"Connection failed: {last_error!r}")
        raise MAVSDKExecutorError(
            f"Failed to connect to {self.system_address} after {self.connection_attempts} attempts."
        ) from last_error

    def _cleanup_stale_backends(self) -> None:
        try:
            subprocess.run(
                ["pkill", "-f", "mavsdk_server"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            # pkill may be unavailable outside the Linux runtime.
            pass
        time.sleep(0.5)

    def _shutdown_backend(self) -> None:
        if self.system is None:
            return
        try:
            if self._parse_grpc_target(self.system_address) is None:
                self.system._stop_mavsdk_server()
        except Exception:
            pass
        finally:
            self.system = None

    @staticmethod
    def _parse_grpc_target(system_address: str) -> Optional[tuple[str, int]]:
        address = system_address.strip()
        prefix = "grpc://"
        if not address.startswith(prefix):
            return None
        host_port = address[len(prefix) :]
        if ":" not in host_port:
            raise MAVSDKExecutorError(f"Invalid gRPC control endpoint '{system_address}'.")
        host, port_text = host_port.rsplit(":", 1)
        return host, int(port_text)

    async def _arm_move_land_cycle(
        self,
        role: Dict[str, Any],
        mission: Dict[str, Any],
        telemetry: ExecutionTelemetry,
        planned_actions: List[str],
    ) -> None:
        await self._arm_takeoff_move_land_cycle(role, mission, telemetry, planned_actions)

    async def _arm_takeoff_move_land_cycle(
        self,
        role: Dict[str, Any],
        mission: Dict[str, Any],
        telemetry: ExecutionTelemetry,
        planned_actions: List[str],
    ) -> None:
        if self._should_use_guided_home_motion():
            await self._arm_takeoff_guided_reposition_land(role, mission, telemetry, planned_actions)
            return

        try:
            await asyncio.wait_for(
                self.system.action.set_takeoff_altitude(self.default_takeoff_altitude_m),
                timeout=self.action_timeout_s,
            )
        except Exception as exc:
            telemetry.notes.append(f"Preflight action setup failed: {exc!r}")

        await self._set_guided_mode(telemetry)
        await self._wait_for_vehicle_readiness(telemetry)

        try:
            print(f"{self.drone_id}: arming", flush=True)
            arm_started = time.perf_counter()
            await asyncio.wait_for(self.system.action.arm(), timeout=self.action_timeout_s)
            telemetry.arm_latency_ms = (time.perf_counter() - arm_started) * 1000.0
        except Exception as exc:
            telemetry.notes.append(f"Arm failed: {exc!r}")
            return

        try:
            print(f"{self.drone_id}: takeoff", flush=True)
            takeoff_started = time.perf_counter()
            await asyncio.wait_for(
                self.system.action.takeoff(),
                timeout=self.action_timeout_s,
            )
            telemetry.takeoff_latency_ms = (time.perf_counter() - takeoff_started) * 1000.0
        except Exception as exc:
            telemetry.notes.append(f"Takeoff failed: {exc!r}")

        await self._wait_for_takeoff(telemetry)

        telemetry.notes.append(
            f"Executing role cycle for {self.drone_id}: {' -> '.join(planned_actions)}."
        )

        await self._perform_role_motion(role, mission, telemetry)

        # Allow the vehicle to reach the final motion target before landing.
        await asyncio.sleep(self.motion_settle_s)

        try:
            print(f"{self.drone_id}: landing", flush=True)
            land_started = time.perf_counter()
            await asyncio.wait_for(self.system.action.land(), timeout=self.action_timeout_s)
            telemetry.land_latency_ms = (time.perf_counter() - land_started) * 1000.0
        except Exception as exc:
            telemetry.notes.append(f"Land failed: {exc!r}")

    async def _arm_takeoff_guided_reposition_land(
        self,
        role: Dict[str, Any],
        mission: Dict[str, Any],
        telemetry: ExecutionTelemetry,
        planned_actions: List[str],
    ) -> None:
        try:
            await asyncio.wait_for(
                self.system.action.set_takeoff_altitude(self.default_takeoff_altitude_m),
                timeout=self.action_timeout_s,
            )
        except Exception as exc:
            telemetry.notes.append(f"Preflight action setup failed: {exc!r}")

        await self._set_guided_mode(telemetry)
        try:
            print(f"{self.drone_id}: arming", flush=True)
            arm_started = time.perf_counter()
            await asyncio.wait_for(self.system.action.arm(), timeout=self.action_timeout_s)
            telemetry.arm_latency_ms = (time.perf_counter() - arm_started) * 1000.0
        except Exception as exc:
            telemetry.notes.append(f"Arm failed: {exc!r}")
            return

        try:
            print(f"{self.drone_id}: takeoff", flush=True)
            takeoff_started = time.perf_counter()
            await self._send_takeoff_command(telemetry)
            telemetry.takeoff_latency_ms = (time.perf_counter() - takeoff_started) * 1000.0
        except Exception as exc:
            telemetry.notes.append(f"Takeoff failed: {exc!r}")
            return

        # ArduPilot may not provide usable telemetry immediately on this path.
        await asyncio.sleep(8.0)
        telemetry.notes.append(
            f"Executing guided reposition for {self.drone_id}: {' -> '.join(planned_actions)}."
        )
        await self._perform_role_motion(role, mission, telemetry)
        await asyncio.sleep(self.motion_settle_s)

        try:
            print(f"{self.drone_id}: landing", flush=True)
            land_started = time.perf_counter()
            await asyncio.wait_for(self.system.action.land(), timeout=self.action_timeout_s)
            telemetry.land_latency_ms = (time.perf_counter() - land_started) * 1000.0
        except Exception as exc:
            telemetry.notes.append(f"Land failed: {exc!r}")

    async def _perform_role_motion(
        self,
        role: Dict[str, Any],
        mission: Dict[str, Any],
        telemetry: ExecutionTelemetry,
    ) -> None:
        if not hasattr(self.system, "action"):
            telemetry.notes.append("Motion skipped: MAVSDK action plugin unavailable.")
            return

        role_name = str(role.get("name", "")).lower()
        if "overwatch" in role_name:
            await self._move_to_watch_position(telemetry, north_m=30.0, east_m=0.0, altitude_delta_m=18.0)
            await asyncio.sleep(2.0)
            telemetry.notes.append("Overwatch watch position maintained.")
            return

        if "relay" in role_name:
            await self._move_to_watch_position(telemetry, north_m=0.0, east_m=25.0, altitude_delta_m=22.0)
            await asyncio.sleep(2.0)
            telemetry.notes.append("Relay high-link position maintained.")
            return

        if "corridor" in role_name:
            waypoints = [
                (25.0, 0.0, 12.0),
                (0.0, 25.0, 12.0),
            ]
            for index, (north_m, east_m, altitude_delta_m) in enumerate(waypoints, start=1):
                await self._move_to_watch_position(
                    telemetry,
                    north_m=north_m,
                    east_m=east_m,
                    altitude_delta_m=altitude_delta_m,
                )
                telemetry.notes.append(f"Corridor patrol waypoint {index} reached.")
                await asyncio.sleep(0.75)
            return

        if "search" in role_name or "scout" in role_name:
            waypoints = [
                (18.0, 18.0, 10.0),
                (30.0, -8.0, 10.0),
            ]
            for index, (north_m, east_m, altitude_delta_m) in enumerate(waypoints, start=1):
                await self._move_to_watch_position(
                    telemetry,
                    north_m=north_m,
                    east_m=east_m,
                    altitude_delta_m=altitude_delta_m,
                )
                telemetry.notes.append(f"Search sweep waypoint {index} reached.")
                await asyncio.sleep(0.75)
            return

        if "thermal" in role_name or "visual" in role_name:
            await self._move_to_watch_position(telemetry, north_m=20.0, east_m=12.0, altitude_delta_m=14.0)
            telemetry.notes.append("Inspection pass completed.")
            return

        await self._move_to_watch_position(telemetry, north_m=15.0, east_m=12.0, altitude_delta_m=10.0)
        telemetry.notes.append("Generic mission motion executed.")

    def _should_use_guided_home_motion(self) -> bool:
        return self.system_address.startswith("grpc://")

    async def _move_to_watch_position(
        self,
        telemetry: ExecutionTelemetry,
        *,
        north_m: float,
        east_m: float,
        altitude_delta_m: float,
    ) -> None:
        target = self._planned_target_from_home(north_m, east_m, altitude_delta_m)
        if target is None:
            telemetry.notes.append("Motion skipped: no configured home position available.")
            return

        latitude_deg, longitude_deg, absolute_altitude_m = target

        # ArduPilot on this path is not reliably exposing telemetry soon enough for a
        # telemetry-based climb gate, so use a fixed post-takeoff delay before reposition.
        await asyncio.sleep(8.0)

        move_started = time.perf_counter()
        print(
            f"{self.drone_id}: goto lat={latitude_deg:.6f} lon={longitude_deg:.6f} alt={absolute_altitude_m:.1f}",
            flush=True,
        )
        await asyncio.wait_for(
            self.system.action.goto_location(
                latitude_deg,
                longitude_deg,
                absolute_altitude_m,
                0.0,
            ),
            timeout=self.action_timeout_s,
        )
        telemetry.notes.append(
            f"Moved to lat={latitude_deg:.6f}, lon={longitude_deg:.6f}, alt={absolute_altitude_m:.1f}."
        )
        telemetry.notes.append(
            f"Motion command latency: {(time.perf_counter() - move_started) * 1000.0:.1f} ms."
        )

    def _planned_target_from_home(
        self,
        north_m: float,
        east_m: float,
        altitude_delta_m: float,
    ) -> Optional[tuple[float, float, float]]:
        from communication_layer import CONTROL_ENDPOINTS

        endpoint = CONTROL_ENDPOINTS.get(self.drone_id)
        if endpoint is None:
            return None

        latitude_deg, longitude_deg = self._offset_latlon(
            endpoint.home_lat_deg,
            endpoint.home_lon_deg,
            north_m,
            east_m,
        )
        absolute_altitude_m = endpoint.home_alt_m + altitude_delta_m
        return latitude_deg, longitude_deg, absolute_altitude_m

    async def _wait_for_takeoff(self, telemetry: ExecutionTelemetry) -> None:
        try:
            position = await asyncio.wait_for(self._next_position(), timeout=20.0)
            if position is None:
                telemetry.notes.append("Takeoff altitude gate timed out without telemetry position.")
                return

            target_altitude_m = max(self.default_takeoff_altitude_m * 0.6, 3.0)
            current_altitude_m = position.relative_altitude_m
            started = time.perf_counter()
            while current_altitude_m < target_altitude_m:
                remaining = 20.0 - (time.perf_counter() - started)
                if remaining <= 0:
                    telemetry.notes.append(
                        f"Takeoff altitude gate timed out at {current_altitude_m:.1f} m."
                    )
                    return
                position = await asyncio.wait_for(self._next_position(), timeout=remaining)
                if position is None:
                    telemetry.notes.append(
                        f"Takeoff altitude gate timed out at {current_altitude_m:.1f} m."
                    )
                    return
                current_altitude_m = position.relative_altitude_m

            telemetry.notes.append(
                f"Reached takeoff altitude gate at {current_altitude_m:.1f} m."
            )
        except Exception as exc:
            telemetry.notes.append(f"Takeoff altitude wait failed: {exc!r}")

    async def _wait_for_connection_state(self) -> None:
        async for state in self.system.core.connection_state():
            if state.is_connected:
                return

    async def _wait_for_vehicle_readiness(self, telemetry: ExecutionTelemetry) -> None:
        try:
            health = await asyncio.wait_for(self._wait_for_health(), timeout=30.0)
            telemetry.notes.append(
                "Vehicle readiness confirmed: "
                f"global_ok={health.is_global_position_ok}, "
                f"home_ok={health.is_home_position_ok}, "
                f"armable={health.is_armable}."
            )
        except Exception as exc:
            telemetry.notes.append(f"Vehicle readiness wait failed: {exc!r}")

    async def _set_guided_mode(self, telemetry: ExecutionTelemetry) -> None:
        from communication_layer import CONTROL_ENDPOINTS

        endpoint = CONTROL_ENDPOINTS.get(self.drone_id)
        if endpoint is None:
            telemetry.notes.append("GUIDED mode request skipped: no control endpoint metadata.")
            return

        try:
            if MavlinkMessage is None:
                telemetry.notes.append("GUIDED mode request skipped: MavlinkMessage unavailable.")
                return

            message = MavlinkMessage(
                message_name="COMMAND_LONG",
                system_id=255,
                component_id=190,
                target_system_id=endpoint.system_id,
                target_component_id=1,
                fields_json=json.dumps(
                    {
                        "command": 176,
                        "confirmation": 0,
                        "param1": 1,
                        "param2": 4,
                        "param3": 0,
                        "param4": 0,
                        "param5": 0,
                        "param6": 0,
                        "param7": 0,
                    }
                ),
            )
            await asyncio.wait_for(
                self.system.mavlink_direct.send_message(message),
                timeout=self.action_timeout_s,
            )
            telemetry.notes.append("Requested GUIDED mode via MAVLink COMMAND_LONG.")
            await asyncio.sleep(2.0)
        except Exception as exc:
            telemetry.notes.append(f"GUIDED mode request failed: {exc!r}")

    async def _send_takeoff_command(self, telemetry: ExecutionTelemetry) -> None:
        from communication_layer import CONTROL_ENDPOINTS

        endpoint = CONTROL_ENDPOINTS.get(self.drone_id)
        if endpoint is None:
            raise MAVSDKExecutorError("Takeoff command skipped: no control endpoint metadata.")
        if MavlinkMessage is None:
            raise MAVSDKExecutorError("Takeoff command skipped: MavlinkMessage unavailable.")

        message = MavlinkMessage(
            message_name="COMMAND_LONG",
            system_id=255,
            component_id=190,
            target_system_id=endpoint.system_id,
            target_component_id=1,
            fields_json=json.dumps(
                {
                    "command": 22,
                    "confirmation": 0,
                    "param1": 0,
                    "param2": 0,
                    "param3": 0,
                    "param4": 0.0,
                    "param5": endpoint.home_lat_deg,
                    "param6": endpoint.home_lon_deg,
                    "param7": self.default_takeoff_altitude_m,
                }
            ),
        )
        await asyncio.wait_for(
            self.system.mavlink_direct.send_message(message),
            timeout=self.action_timeout_s,
        )
        telemetry.notes.append("Requested takeoff via MAVLink COMMAND_LONG.")
        await asyncio.sleep(2.0)

    async def _wait_for_health(self):
        async for health in self.system.telemetry.health():
            if health.is_armable and health.is_global_position_ok and health.is_home_position_ok:
                return health
        return None

    async def _next_position(self):
        async for position in self.system.telemetry.position():
            return position
        return None

    async def _current_position(self):
        try:
            return await asyncio.wait_for(self._next_position(), timeout=10.0)
        except Exception:
            return None

    @staticmethod
    def _offset_latlon(latitude_deg: float, longitude_deg: float, north_m: float, east_m: float):
        meters_per_deg_lat = 111_111.0
        meters_per_deg_lon = 111_111.0 * max(math.cos(math.radians(latitude_deg)), 0.01)
        new_lat = latitude_deg + (north_m / meters_per_deg_lat)
        new_lon = longitude_deg + (east_m / meters_per_deg_lon)
        return new_lat, new_lon

    def _build_planned_actions(self, role_name: str, mission: Dict[str, Any]) -> List[str]:
        objective = str(mission.get("objective", "")).lower()
        actions: List[str] = ["connect", "arm", "takeoff"]

        if "overwatch" in role_name:
            actions.append("hold_position")
        elif "relay" in role_name:
            actions.append("maintain_high_link")
        elif "thermal" in role_name or "visual" in role_name:
            actions.append("inspection_pass")
        elif "corridor" in role_name:
            actions.append("patrol_segment")
        elif "search" in role_name or "scout" in role_name:
            actions.append("search_sweep")
        else:
            actions.append("mission_specific_execution")

        if "monitor" in objective or "inspect" in objective or "search" in objective:
            actions.append("mission_observation")

        actions.append("land")
        return actions
