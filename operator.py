from _operator import *  # noqa: F401,F403


def build_default_fleet():
    from drone_agent import DroneAgent

    return [
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


def parse_vehicle_bindings(values):
    bindings = []
    for value in values or []:
        if "=" not in value:
            raise ValueError(f"Invalid vehicle binding '{value}'. Expected drone_id=system_address.")
        drone_id, system_address = value.split("=", 1)
        drone_id = drone_id.strip()
        system_address = system_address.strip()
        if not drone_id or not system_address:
            raise ValueError(f"Invalid vehicle binding '{value}'. Both sides must be non-empty.")
        bindings.append({"drone_id": drone_id, "system_address": system_address})
    return bindings


def build_mission_package(command):
    from drone_agent import DroneAgent
    from matching_engine import build_match_report
    from mission_parser import MissionParseError, parse_mission
    from role_engine import generate_roles

    try:
        mission = parse_mission(command)
        if not mission.get("preferred_roles"):
            raise MissionParseError("preferred_roles empty after parsing")
    except (MissionParseError, RuntimeError):
        mission = fallback_mission_from_command(command)
    roles = generate_roles(mission)
    match_report = build_match_report(roles, build_default_fleet())
    return {
        "command": command,
        "mission": mission,
        "roles": roles,
        "match_report": match_report,
    }


async def execute_hardware_plan(command, bindings, *, dry_run=True):
    import asyncio

    from mavsdk_executor import MAVSDKExecutor

    print("operator: building mission package", flush=True)
    package = build_mission_package(command)
    assignments = package["match_report"].get("final_assignments", [])
    binding_map = {binding["drone_id"]: binding["system_address"] for binding in bindings}
    print(f"operator: executing {len(assignments)} assignment(s)", flush=True)
    execution_reports = []
    for assignment in assignments:
        drone_id = assignment["drone_id"]
        role_name = assignment["role_name"]
        system_address = binding_map.get(drone_id)
        if not system_address:
            execution_reports.append(
                {
                    "drone_id": drone_id,
                    "role_name": role_name,
                    "error": "No system_address binding provided for this drone.",
                }
            )
            continue

        role = next(role for role in package["roles"] if role["name"] == role_name)
        executor = MAVSDKExecutor(
            drone_id=drone_id,
            system_address=system_address,
            dry_run=dry_run,
        )
        report = await executor.execute_role(role, package["mission"])
        execution_reports.append(report.to_dict())
    print("operator: execution complete", flush=True)

    return {
        "package": package,
        "bindings": bindings,
        "execution_reports": execution_reports,
        "notes": [
            "Operator workstation compiles the mission and distributes it.",
            "Role execution remains local to each vehicle.",
            "In hardware mode, set dry_run=False after MAVSDK is installed and connected.",
        ],
    }


def fallback_mission_from_command(command):
    text = command.lower()

    if "solar field" in text and "thermal" in text and "anomal" in text:
        return {
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
        }

    if "eastern farm" in text and "livestock" in text:
        return {
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
        }

    if "pipeline corridor" in text or ("pipeline" in text and "patrol" in text):
        return {
            "mission_type": "corridor_patrol",
            "environment": "pipeline_corridor",
            "location": "pipeline corridor",
            "objective": "monitor for suspicious activity",
            "mission_style": "sector_based_coverage",
            "coordination_required": True,
            "global_visibility_required": True,
            "num_drones": 4,
            "preferred_roles": [
                "corridor_patrol_A",
                "corridor_patrol_B",
                "overwatch_relay",
            ],
            "constraints": {
                "corridor_monitoring": True,
                "relay_required": True,
            },
        }

    if "pipeline" in text and ("corridor" in text or "monitor" in text):
        return {
            "mission_type": "corridor_patrol",
            "environment": "pipeline_corridor",
            "location": "pipeline corridor",
            "objective": "monitor for suspicious activity",
            "mission_style": "sector_based_coverage",
            "coordination_required": True,
            "global_visibility_required": True,
            "num_drones": 4,
            "preferred_roles": [
                "corridor_patrol_A",
                "corridor_patrol_B",
                "overwatch_relay",
            ],
            "constraints": {
                "corridor_monitoring": True,
                "relay_required": True,
            },
        }

    if "wind turbine" in text or "wind turbines" in text:
        return {
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
        }

    if "forest edge" in text and "overwatch" in text:
        return {
            "mission_type": "search_and_overwatch",
            "environment": "forest_edge",
            "location": "forest edge",
            "objective": "search the forest edge and maintain overwatch",
            "mission_style": "sector_based_coverage",
            "coordination_required": True,
            "global_visibility_required": True,
            "num_drones": 4,
            "preferred_roles": [
                "search_scout_A",
                "search_scout_B",
                "search_scout_C",
                "overwatch",
            ],
            "constraints": {
                "overwatch_required": True,
                "high_altitude_overwatch": True,
            },
        }

    raise RuntimeError("Unsupported mission command for fallback mission parsing.")


def build_argument_parser():
    import argparse

    parser = argparse.ArgumentParser(description="Phase 6 operator workstation for decentralized drone swarm execution.")
    parser.add_argument("--command", required=True, help="Natural language operator mission command.")
    parser.add_argument(
        "--vehicle",
        action="append",
        default=[],
        help="Vehicle binding in the form drone_id=system_address. Repeat for multiple drones.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not send MAVSDK commands. Return a hardware-ready execution plan only.",
    )
    return parser


def main():
    import asyncio
    import json
    import sys

    parser = build_argument_parser()
    args = parser.parse_args()

    try:
        bindings = parse_vehicle_bindings(args.vehicle)
    except ValueError as exc:
        raise SystemExit(str(exc))

    result = asyncio.run(execute_hardware_plan(args.command, bindings, dry_run=args.dry_run))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
