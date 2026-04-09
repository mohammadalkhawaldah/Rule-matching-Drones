import json

from drone_agent import DroneAgent
from matching_engine import build_match_report
from role_engine import generate_roles


MISSIONS = [
    {
        "mission_type": "facility_inspection",
        "environment": "solar_field",
        "location": "rural England",
        "objective": "thermal anomaly detection",
        "mission_style": "sector_based_coverage",
        "coordination_required": True,
        "global_visibility_required": True,
        "num_drones": 3,
        "preferred_roles": ["thermal_scout_A", "thermal_scout_B", "overwatch"],
        "constraints": {"thermal_camera_required": True, "coverage_priority": "high"},
    },
    {
        "mission_type": "search_and_recovery",
        "environment": "farm_sector",
        "location": "eastern farm area",
        "objective": "missing livestock search",
        "mission_style": "sector_based_coverage",
        "coordination_required": True,
        "global_visibility_required": False,
        "num_drones": 2,
        "preferred_roles": ["search_scout_A", "search_scout_B"],
        "constraints": {"livestock_search_required": True},
    },
    {
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
    },
    {
        "mission_type": "facility_inspection",
        "environment": "wind_farm",
        "location": "wind turbines",
        "objective": "visual damage inspection",
        "mission_style": "sector_based_coverage",
        "coordination_required": True,
        "global_visibility_required": True,
        "num_drones": 3,
        "preferred_roles": ["visual_inspector_A", "visual_inspector_B", "overwatch"],
        "constraints": {
            "high_resolution_camera_required": True,
            "visual_damage_report_required": True,
        },
    },
    {
        "mission_type": "search_and_overwatch",
        "environment": "forest_edge",
        "location": "forest edge",
        "objective": "search the forest edge and maintain overwatch",
        "mission_style": "sector_based_coverage",
        "coordination_required": True,
        "global_visibility_required": True,
        "num_drones": 4,
        "preferred_roles": ["search_scout_A", "search_scout_B", "search_scout_C", "overwatch"],
        "constraints": {"high_altitude_overwatch": True, "overwatch_required": True},
    },
]


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
    for index, mission in enumerate(MISSIONS, start=1):
        roles = generate_roles(mission)
        report = build_match_report(roles, DRONES)
        print(f"\nMission {index}: {mission['mission_type']} @ {mission['environment']}")
        print("Match report:")
        print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
