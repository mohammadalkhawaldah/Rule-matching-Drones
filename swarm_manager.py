from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from drone_agent import DroneAgent


@dataclass(frozen=True)
class SwarmMessage:
    source: str
    message_type: str
    payload: Dict[str, Any]
    destination: Optional[str] = None


@dataclass
class DroneState:
    drone_id: str
    capabilities: List[str]
    received_messages: List[SwarmMessage] = field(default_factory=list)
    announced_roles: List[str] = field(default_factory=list)
    assigned_role: Optional[str] = None
    status: str = "idle"


class MeshNetworkSimulator:
    """
    Lightweight mesh-style transport simulator.

    This models a decentralized 802.11s-style mesh carrying MAVLink-like
    messages without making assignment decisions.
    """

    def __init__(self, node_ids: List[str]) -> None:
        self.node_ids = list(node_ids)
        self.messages: List[SwarmMessage] = []

    def broadcast(self, message: SwarmMessage) -> None:
        self.messages.append(message)

    def unicast(self, message: SwarmMessage) -> None:
        self.messages.append(message)


class SwarmManager:
    """
    Phase 5 swarm simulation.

    The manager does not score, rank, or assign roles. It simulates how the
    swarm exchanges mission state and begins execution over a mesh transport.
    """

    def __init__(self, drones: List[DroneAgent], transport: str = "802.11s + MAVLink/UDP") -> None:
        self.drones = list(drones)
        self.transport = transport
        self.mesh = MeshNetworkSimulator([drone.drone_id for drone in drones])
        self.states = {
            drone.drone_id: DroneState(
                drone_id=drone.drone_id,
                capabilities=drone.normalized_capabilities(),
            )
            for drone in drones
        }

    def run_mission(
        self,
        mission: Dict[str, Any],
        roles: List[Dict[str, Any]],
        match_report: Dict[str, Any],
    ) -> Dict[str, Any]:
        self._broadcast_mission(mission)
        self._exchange_capabilities()
        self._announce_roles(roles)
        self._apply_assignments(match_report)
        self._start_execution(roles)

        return {
            "transport": self.transport,
            "topology": "mesh",
            "mission": mission,
            "roles": roles,
            "match_report": match_report,
            "message_log": [
                {
                    "source": msg.source,
                    "destination": msg.destination,
                    "message_type": msg.message_type,
                    "payload": msg.payload,
                }
                for msg in self.mesh.messages
            ],
            "drone_states": {
                drone_id: {
                    "drone_id": state.drone_id,
                    "capabilities": list(state.capabilities),
                    "received_messages": [
                        {
                            "source": msg.source,
                            "destination": msg.destination,
                            "message_type": msg.message_type,
                            "payload": msg.payload,
                        }
                        for msg in state.received_messages
                    ],
                    "announced_roles": list(state.announced_roles),
                    "assigned_role": state.assigned_role,
                    "status": state.status,
                }
                for drone_id, state in self.states.items()
            },
            "execution_summary": self._execution_summary(),
        }

    def _broadcast_mission(self, mission: Dict[str, Any]) -> None:
        message = SwarmMessage(
            source="operator_workstation",
            message_type="mission_broadcast",
            payload={
                "mission_type": mission.get("mission_type"),
                "environment": mission.get("environment"),
                "location": mission.get("location"),
                "objective": mission.get("objective"),
                "num_drones": mission.get("num_drones"),
            },
        )
        self.mesh.broadcast(message)
        self._deliver_to_all(message)

    def _exchange_capabilities(self) -> None:
        for state in self.states.values():
            message = SwarmMessage(
                source=state.drone_id,
                message_type="capability_announcement",
                payload={"capabilities": list(state.capabilities)},
            )
            self.mesh.broadcast(message)
            self._deliver_to_all(message)

    def _announce_roles(self, roles: List[Dict[str, Any]]) -> None:
        for state in self.states.values():
            feasible = [
                role["name"]
                for role in roles
                if self._can_fulfill(state.capabilities, role)
            ]
            state.announced_roles = list(feasible)
            message = SwarmMessage(
                source=state.drone_id,
                message_type="role_feasibility_announcement",
                payload={"feasible_roles": list(feasible)},
            )
            self.mesh.broadcast(message)
            self._deliver_to_all(message)

    def _apply_assignments(self, match_report: Dict[str, Any]) -> None:
        assignments = match_report.get("final_assignments", [])
        for assignment in assignments:
            drone_id = assignment.get("drone_id")
            role_name = assignment.get("role_name")
            state = self.states.get(drone_id)
            if state is None:
                continue
            state.assigned_role = role_name
            state.status = "assigned"
            message = SwarmMessage(
                source="swarm_mesh",
                destination=drone_id,
                message_type="assignment_notification",
                payload={"role_name": role_name},
            )
            self.mesh.unicast(message)
            state.received_messages.append(message)

        for state in self.states.values():
            if state.assigned_role is None:
                state.status = "standby"

    def _start_execution(self, roles: List[Dict[str, Any]]) -> None:
        role_by_name = {role["name"]: role for role in roles}
        for state in self.states.values():
            if state.assigned_role is None:
                message = SwarmMessage(
                    source=state.drone_id,
                    message_type="standby_status",
                    payload={"status": "awaiting_assignment"},
                )
                self.mesh.broadcast(message)
                self._deliver_to_all(message)
                continue

            role = role_by_name.get(state.assigned_role, {})
            message = SwarmMessage(
                source=state.drone_id,
                message_type="execution_start",
                payload={
                    "role_name": state.assigned_role,
                    "mission_focus": role.get("mission_focus", ""),
                    "required_capabilities": role.get("required_capabilities", []),
                },
            )
            self.mesh.broadcast(message)
            self._deliver_to_all(message)
            state.status = "executing"

    def _deliver_to_all(self, message: SwarmMessage) -> None:
        for state in self.states.values():
            state.received_messages.append(message)

    def _execution_summary(self) -> Dict[str, Any]:
        assigned = [state.drone_id for state in self.states.values() if state.assigned_role is not None]
        standby = [state.drone_id for state in self.states.values() if state.status == "standby"]
        executing = [state.drone_id for state in self.states.values() if state.status == "executing"]
        return {
            "assigned_drones": assigned,
            "executing_drones": executing,
            "standby_drones": standby,
            "transport": self.transport,
            "notes": "Simulation only; no centralized role selection performed here.",
        }

    @staticmethod
    def _can_fulfill(capabilities: List[str], role: Dict[str, Any]) -> bool:
        required = role.get("required_capabilities", [])
        if not isinstance(required, list):
            return False
        have = set(capabilities)
        needed = {str(item).strip().lower() for item in required if str(item).strip()}
        return needed.issubset(have)


def run_swarm_simulation(
    drones: List[DroneAgent],
    mission: Dict[str, Any],
    roles: List[Dict[str, Any]],
    match_report: Dict[str, Any],
    transport: str = "802.11s + MAVLink/UDP",
) -> Dict[str, Any]:
    return SwarmManager(drones=drones, transport=transport).run_mission(mission, roles, match_report)
