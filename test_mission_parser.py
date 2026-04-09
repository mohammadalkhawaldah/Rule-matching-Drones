import json

from mission_parser import parse_mission


EXAMPLES = [
    "Deploy three drones to inspect the solar field in rural England and detect thermal anomalies.",
    "Send two drones to search the eastern farm area for missing livestock.",
    "Deploy four drones to patrol the pipeline corridor and monitor for suspicious activity.",
    "Use three drones to inspect the wind turbines and report visual damage.",
    "Send three drones to search the forest edge and keep one drone high for overwatch.",
]


def main() -> None:
    for index, command in enumerate(EXAMPLES, start=1):
        mission = parse_mission(command)
        print(f"\nExample {index}: {command}")
        print(json.dumps(mission, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

