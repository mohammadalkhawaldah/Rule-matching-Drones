from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class DroneAgent:
    """
    A local drone-side agent.

    The agent knows only its own capabilities and evaluates whether it can
    fulfill roles described in semantic mission JSON. It does not rank drones
    or assign roles globally.
    """

    drone_id: str
    capabilities: List[str] = field(default_factory=list)

    def normalized_capabilities(self) -> List[str]:
        return list(dict.fromkeys(cap.strip().lower() for cap in self.capabilities if cap.strip()))

    def can_fulfill_role(self, role: Dict[str, Any]) -> bool:
        required = role.get("required_capabilities", [])
        if not isinstance(required, list):
            return False

        have = set(self.normalized_capabilities())
        needed = {str(item).strip().lower() for item in required if str(item).strip()}
        return needed.issubset(have)

    def feasible_roles(self, roles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Return the roles this drone can locally satisfy.

        No ranking is performed. The output is only a capability match set.
        """

        return [role for role in roles if self.can_fulfill_role(role)]

    def capability_report(self) -> Dict[str, Any]:
        return {
            "drone_id": self.drone_id,
            "capabilities": self.normalized_capabilities(),
        }

