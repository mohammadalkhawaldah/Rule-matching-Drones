from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RoleSpec:
    name: str
    required_capabilities: List[str] = field(default_factory=list)
    mission_focus: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "required_capabilities": list(self.required_capabilities),
            "mission_focus": self.mission_focus,
        }


class RoleEngineError(RuntimeError):
    """Raised when a mission cannot be converted into a valid role set."""


class RoleEngine:
    """
    Convert semantic mission JSON into explicit mission roles.

    This layer does not score, bid, or rank drones. It only defines the roles
    required by the mission and the capabilities each role expects.
    """

    def generate_roles(self, mission: Dict[str, Any]) -> List[Dict[str, Any]]:
        mission_type = str(mission.get("mission_type", "")).strip().lower()
        environment = str(mission.get("environment", "")).strip().lower()
        objective = str(mission.get("objective", "")).strip().lower()
        num_drones = int(mission.get("num_drones", 0))
        preferred_roles = [str(role).strip() for role in mission.get("preferred_roles", []) if str(role).strip()]
        constraints = mission.get("constraints", {})

        if num_drones <= 0:
            raise RoleEngineError("Mission num_drones must be a positive integer.")
        if not isinstance(constraints, dict):
            raise RoleEngineError("Mission constraints must be an object.")

        template = self._template_roles(
            mission_type=mission_type,
            environment=environment,
            objective=objective,
            num_drones=num_drones,
            preferred_roles=preferred_roles,
            constraints=constraints,
        )
        if template is not None:
            return [role.to_dict() for role in template]

        return self._fallback_roles(num_drones=num_drones, preferred_roles=preferred_roles)

    def _template_roles(
        self,
        mission_type: str,
        environment: str,
        objective: str,
        num_drones: int,
        preferred_roles: List[str],
        constraints: Dict[str, Any],
    ) -> Optional[List[RoleSpec]]:
        if mission_type == "facility_inspection" and environment == "solar_field":
            return [
                RoleSpec(
                    name="thermal_scout_A",
                    required_capabilities=["thermal_camera", "inspection_flight", "sector_coverage"],
                    mission_focus="Scan assigned solar array sectors for thermal anomalies.",
                ),
                RoleSpec(
                    name="thermal_scout_B",
                    required_capabilities=["thermal_camera", "inspection_flight", "sector_coverage"],
                    mission_focus="Scan assigned solar array sectors for thermal anomalies.",
                ),
                RoleSpec(
                    name="overwatch",
                    required_capabilities=["high_altitude", "good_battery", "wide_area_observation"],
                    mission_focus="Maintain global overwatch and relay mission status.",
                ),
            ]

        if mission_type == "search_and_recovery" and environment == "farm_sector":
            return [
                RoleSpec(
                    name="search_scout_A",
                    required_capabilities=["visual_camera", "low_altitude_search", "agile_flight"],
                    mission_focus="Search the assigned farm sector for livestock.",
                ),
                RoleSpec(
                    name="search_scout_B",
                    required_capabilities=["visual_camera", "low_altitude_search", "agile_flight"],
                    mission_focus="Search the assigned farm sector for livestock.",
                ),
            ]

        if mission_type == "corridor_patrol" and "pipeline" in environment:
            return [
                RoleSpec(
                    name="corridor_patrol_A",
                    required_capabilities=["stability_flight", "visual_camera", "corridor_tracking"],
                    mission_focus="Patrol the assigned corridor segment.",
                ),
                RoleSpec(
                    name="corridor_patrol_B",
                    required_capabilities=["stability_flight", "visual_camera", "corridor_tracking"],
                    mission_focus="Patrol the assigned corridor segment.",
                ),
                RoleSpec(
                    name="overwatch",
                    required_capabilities=["high_altitude", "good_battery", "wide_area_observation"],
                    mission_focus="Maintain top-level awareness and early warning.",
                ),
                RoleSpec(
                    name="relay",
                    required_capabilities=["communications_relay", "stationary_hold", "battery_reserve"],
                    mission_focus="Extend communications coverage across the corridor.",
                ),
            ]

        if mission_type == "facility_inspection" and environment == "wind_farm":
            return [
                RoleSpec(
                    name="visual_inspector_A",
                    required_capabilities=["high_resolution_camera", "inspection_flight", "sector_coverage"],
                    mission_focus="Inspect turbines for visual damage.",
                ),
                RoleSpec(
                    name="visual_inspector_B",
                    required_capabilities=["high_resolution_camera", "inspection_flight", "sector_coverage"],
                    mission_focus="Inspect turbines for visual damage.",
                ),
                RoleSpec(
                    name="overwatch",
                    required_capabilities=["high_altitude", "good_battery", "wide_area_observation"],
                    mission_focus="Maintain visual overwatch over the farm.",
                ),
            ]

        if mission_type == "search_and_overwatch" and environment == "forest_edge":
            search_roles = max(num_drones - 1, 1)
            roles = [
                RoleSpec(
                    name=f"search_scout_{chr(ord('A') + idx)}",
                    required_capabilities=["visual_camera", "low_altitude_search", "terrain_following"],
                    mission_focus="Search the forest edge for the missing target.",
                )
                for idx in range(search_roles)
            ]
            roles.append(
                RoleSpec(
                    name="overwatch",
                    required_capabilities=["high_altitude", "good_battery", "wide_area_observation"],
                    mission_focus="Keep one drone high for overwatch.",
                )
            )
            return roles

        # If the semantic mission is close but not one of the exact templates,
        # use preferred roles as the role structure and attach generic capability needs.
        if preferred_roles:
            return [
                RoleSpec(
                    name=role,
                    required_capabilities=self._capabilities_for_role(role, mission_type, objective, constraints),
                    mission_focus=f"Fulfill role {role} for the mission.",
                )
                for role in preferred_roles
            ]

        return None

    def _fallback_roles(self, num_drones: int, preferred_roles: List[str]) -> List[Dict[str, Any]]:
        if preferred_roles:
            roles = preferred_roles
        else:
            roles = [f"role_{idx + 1}" for idx in range(num_drones)]

        return [
            {
                "name": role,
                "required_capabilities": [],
                "mission_focus": "Generic mission role.",
            }
            for role in roles
        ]

    def _capabilities_for_role(
        self,
        role: str,
        mission_type: str,
        objective: str,
        constraints: Dict[str, Any],
    ) -> List[str]:
        role_lower = role.lower()
        capabilities: List[str] = []

        if "thermal" in role_lower:
            capabilities.append("thermal_camera")
        if "visual" in role_lower or "inspector" in role_lower:
            capabilities.append("high_resolution_camera")
        if "search" in role_lower or "scout" in role_lower:
            capabilities.append("visual_camera")
            capabilities.append("low_altitude_search")
        if "overwatch" in role_lower:
            capabilities.extend(["high_altitude", "good_battery"])
        if "relay" in role_lower:
            capabilities.append("communications_relay")

        if mission_type == "facility_inspection" and "thermal" in objective:
            capabilities.append("thermal_camera")
        if constraints.get("thermal_camera_required"):
            capabilities.append("thermal_camera")
        if constraints.get("high_resolution_camera_required"):
            capabilities.append("high_resolution_camera")
        if constraints.get("relay_required"):
            capabilities.append("communications_relay")

        # Deduplicate while preserving order.
        return list(dict.fromkeys(capabilities))


def generate_roles(mission: Dict[str, Any]) -> List[Dict[str, Any]]:
    return RoleEngine().generate_roles(mission)
