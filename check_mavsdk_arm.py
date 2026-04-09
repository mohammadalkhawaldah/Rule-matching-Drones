import asyncio
import sys
import time

from mavsdk import System


async def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python check_mavsdk_arm.py tcp://host:port")
        return 1

    system_address = sys.argv[1]
    drone = System()

    connect_started = time.perf_counter()
    await drone.connect(system_address=system_address)
    async for state in drone.core.connection_state():
        if state.is_connected:
            break
    print(f"connect_ms={(time.perf_counter() - connect_started) * 1000.0:.1f}")

    arm_started = time.perf_counter()
    await drone.action.arm()
    print(f"arm_ms={(time.perf_counter() - arm_started) * 1000.0:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
