import json

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
        "constraints": {
            "thermal_camera_required": True,
            "coverage_priority": "high",
        },
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
        "constraints": {
            "livestock_search_required": True,
        },
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
        "constraints": {
            "corridor_monitoring": True,
            "relay_required": True,
        },
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
        "constraints": {
            "high_altitude_overwatch": True,
            "overwatch_required": True,
        },
    },
]


def main() -> None:
    for index, mission in enumerate(MISSIONS, start=1):
        roles = generate_roles(mission)
        print(f"\nMission {index}: {mission['mission_type']} @ {mission['environment']}")
        print(json.dumps(roles, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
