import asyncio
import sys

from mavsdk import System


async def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python check_mavsdk_connect.py tcp://host:port")
        return 1

    system_address = sys.argv[1]
    drone = System()
    await drone.connect(system_address=system_address)

    async for state in drone.core.connection_state():
        print(f"connected={state.is_connected}")
        if state.is_connected:
            return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
