import json

from drone_agent import DroneAgent
from matching_engine import build_match_report
from role_engine import generate_roles
from swarm_manager import run_swarm_simulation


MISSION = {
    "mission_type": "corridor_patrol",
    "environment": "pipeline_corridor",
    "location": "pipeline corridor",
    "objective": "monitor for suspicious activity",
    "mission_style": "sector_based_coverage",
    "coordination_required": True,
    "global_visibility_required": True,
    "num_drones": 4,
    "preferred_roles": ["corridor_patrol_A", "corridor_patrol_B", "overwatch", "relay"],
    "constraints": {"corridor_monitoring": True, "relay_required": True},
}

DRONES = [
    DroneAgent(
        drone_id="drone_1",
        capabilities=[
            "thermal_camera",
            "inspection_flight",
            "sector_coverage",
            "visual_camera",
            "high_resolution_camera",
            "high_altitude",
            "good_battery",
            "wide_area_observation",
        ],
    ),
    DroneAgent(
        drone_id="drone_2",
        capabilities=[
            "thermal_camera",
            "inspection_flight",
            "sector_coverage",
            "visual_camera",
            "low_altitude_search",
            "agile_flight",
            "stability_flight",
            "corridor_tracking",
            "terrain_following",
        ],
    ),
    DroneAgent(
        drone_id="drone_3",
        capabilities=[
            "thermal_camera",
            "inspection_flight",
            "sector_coverage",
            "high_resolution_camera",
            "visual_camera",
            "low_altitude_search",
            "terrain_following",
        ],
    ),
    DroneAgent(
        drone_id="drone_4",
        capabilities=[
            "high_resolution_camera",
            "inspection_flight",
            "sector_coverage",
            "communications_relay",
            "stationary_hold",
            "battery_reserve",
            "high_altitude",
            "good_battery",
            "wide_area_observation",
        ],
    ),
    DroneAgent(
        drone_id="drone_5",
        capabilities=[
            "visual_camera",
            "low_altitude_search",
            "agile_flight",
            "terrain_following",
            "stability_flight",
            "corridor_tracking",
            "sector_coverage",
        ],
    ),
    DroneAgent(
        drone_id="drone_6",
        capabilities=[
            "visual_camera",
            "low_altitude_search",
            "terrain_following",
            "stability_flight",
            "corridor_tracking",
            "high_altitude",
            "good_battery",
            "wide_area_observation",
        ],
    ),
]


def main() -> None:
    roles = generate_roles(MISSION)
    match_report = build_match_report(roles, DRONES)
    simulation = run_swarm_simulation(DRONES, MISSION, roles, match_report)
    print(json.dumps(simulation, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
