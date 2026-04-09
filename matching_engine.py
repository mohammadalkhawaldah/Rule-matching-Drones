from dataclasses import dataclass
from typing import Any, Dict, List

from drone_agent import DroneAgent


@dataclass(frozen=True)
class MatchEntry:
    role_name: str
    eligible_drones: List[str]
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_name": self.role_name,
            "eligible_drones": list(self.eligible_drones),
            "status": self.status,
        }


class MatchingEngineError(RuntimeError):
    """Raised when role-to-drone matching cannot be produced."""


class MatchingEngine:
    """
    Capability-only matching engine.

    This engine does not score, rank, or bid. It aggregates which drones can
    fulfill which roles, and marks singleton matches as immediately assignable.
    Contested roles remain unresolved for a later decentralized negotiation step.
    """

    def build_match_report(
        self,
        roles: List[Dict[str, Any]],
        drones: List[DroneAgent],
    ) -> Dict[str, Any]:
        if not isinstance(roles, list) or not all(isinstance(role, dict) for role in roles):
            raise MatchingEngineError("roles must be a list of role dictionaries.")
        if not isinstance(drones, list) or not all(isinstance(drone, DroneAgent) for drone in drones):
            raise MatchingEngineError("drones must be a list of DroneAgent instances.")

        ordered_drones = sorted(drones, key=lambda drone: drone.drone_id)
        role_entries: List[MatchEntry] = []
        drone_feasibility: List[Dict[str, Any]] = []
        final_assignments: List[Dict[str, Any]] = []
        assigned_drones = set()

        for drone in ordered_drones:
            feasible = drone.feasible_roles(roles)
            drone_feasibility.append(
                {
                    "drone_id": drone.drone_id,
                    "feasible_roles": [role["name"] for role in feasible],
                }
            )

        for role in roles:
            role_name = str(role.get("name", "")).strip()
            eligible_drones = [
                drone.drone_id
                for drone in ordered_drones
                if drone.can_fulfill_role(role)
            ]
            if not eligible_drones:
                status = "unmatched"
            elif len(eligible_drones) == 1:
                status = "singleton"
            else:
                status = "contested"

            selected_drone = None
            for drone_id in eligible_drones:
                if drone_id not in assigned_drones:
                    selected_drone = drone_id
                    assigned_drones.add(drone_id)
                    final_assignments.append(
                        {
                            "role_name": role_name,
                            "drone_id": drone_id,
                        }
                    )
                    break

            role_entries.append(
                MatchEntry(
                    role_name=role_name,
                    eligible_drones=eligible_drones,
                    status=status,
                )
            )

        match_rows: List[Dict[str, Any]] = []
        assignment_lookup = {entry["role_name"]: entry["drone_id"] for entry in final_assignments}
        for entry in role_entries:
            eligible = len(entry.eligible_drones)
            if eligible == 0:
                final_state = "unassigned"
            elif entry.role_name in assignment_lookup:
                final_state = "assigned"
            else:
                final_state = "blocked"

            match_rows.append(
                {
                    **entry.to_dict(),
                    "final_assignment": assignment_lookup.get(entry.role_name),
                    "final_state": final_state,
                }
            )

        unresolved_roles = [
            row
            for row in match_rows
            if row["final_state"] != "assigned"
        ]

        return {
            "role_matches": match_rows,
            "drone_feasibility": drone_feasibility,
            "final_assignments": final_assignments,
            "unresolved_roles": unresolved_roles,
            "summary": {
                "total_roles": len(role_entries),
                "matched_roles": len(final_assignments),
                "singleton_roles": len([entry for entry in role_entries if entry.status == "singleton"]),
                "contested_roles": len([entry for entry in role_entries if entry.status == "contested"]),
                "unmatched_roles": len([entry for entry in role_entries if entry.status == "unmatched"]),
            },
        }


def build_match_report(roles: List[Dict[str, Any]], drones: List[DroneAgent]) -> Dict[str, Any]:
    return MatchingEngine().build_match_report(roles, drones)
