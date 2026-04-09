import asyncio
import json

from mavsdk_executor import MAVSDKExecutor


ROLE = {
    "name": "overwatch",
    "required_capabilities": [
        "high_altitude",
        "good_battery",
        "wide_area_observation",
    ],
}

MISSION = {
    "objective": "monitor for suspicious activity",
}


async def main() -> None:
    executor = MAVSDKExecutor(
        "drone_1",
        "grpc://127.0.0.1:50040",
        dry_run=False,
    )
    report = await executor.execute_role(ROLE, MISSION)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
