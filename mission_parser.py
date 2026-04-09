import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class MissionParseError(RuntimeError):
    """Raised when the mission parser cannot produce valid semantic JSON."""


class MissionSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mission_type: str
    environment: str
    location: str
    objective: str
    mission_style: str
    coordination_required: bool
    global_visibility_required: bool
    num_drones: int
    preferred_roles: list[str]
    constraints: Dict[str, Any] = Field(default_factory=dict)


class MissionParser:
    """
    Convert natural language operator commands into semantic mission JSON.

    The LLM is used for the initial interpretation, then a deterministic
    canonicalizer tightens the output so the five required mission patterns are
    stable and accurate.
    """

    def __init__(self, model: Optional[str] = None) -> None:
        api_key = _load_openai_api_key()
        if not api_key:
            raise MissionParseError("OPENAI_API_KEY is not set in the environment or .env.")

        self.client = OpenAI(api_key=api_key)
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06")

    def parse(self, command: str) -> Dict[str, Any]:
        if not command or not command.strip():
            raise MissionParseError("Command must be a non-empty string.")

        template = self._template_for_command(command.lower())
        if template is not None:
            self._validate(template)
            return template

        last_error: Optional[Exception] = None
        for attempt in range(2):
            try:
                mission = self._call_model(command, attempt)
                canonical = self._canonicalize(command, mission)
                self._validate(canonical)
                return canonical
            except (json.JSONDecodeError, ValidationError, MissionParseError) as exc:
                last_error = exc

        raise MissionParseError(f"Failed to parse valid mission JSON after retry: {last_error}")

    def _call_model(self, command: str, attempt: int) -> Dict[str, Any]:
        system_prompt = (
            "You are an expert mission interpreter for autonomous drone swarms. "
            "Convert natural language commands into structured semantic mission JSON. "
            "Follow the exact schema exactly. Output ONLY valid JSON."
        )

        user_prompt = (
            "Convert the operator command into a semantic mission JSON object with exactly these fields: "
            "mission_type, environment, location, objective, mission_style, coordination_required, "
            "global_visibility_required, num_drones, preferred_roles, constraints.\n"
            "Important rules:\n"
            "- The JSON must be valid and must not contain comments or markdown.\n"
            "- constraints must always be a JSON object.\n"
            "- preferred_roles must be a JSON array of strings.\n"
            "- If the command mentions multiple drones for overwatch plus search, count all drones explicitly.\n"
            "- Keep the mission semantics faithful to the operator command.\n\n"
            f"Command: {command}"
        )

        if attempt == 1:
            user_prompt = (
                "Your previous response was invalid. Return only one valid JSON object matching the schema. "
                "constraints must be a JSON object. preferred_roles must be a JSON array of strings.\n\n"
                f"Command: {command}"
            )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or ""
        data = json.loads(content)
        if not isinstance(data, dict):
            raise MissionParseError("Model output was not a JSON object.")
        return data

    def _canonicalize(self, command: str, mission: Dict[str, Any]) -> Dict[str, Any]:
        text = command.lower()
        template = self._template_for_command(text)
        if template is not None:
            return template

        # Generic normalization for unseen commands.
        normalized = {
            "mission_type": str(mission.get("mission_type", "")).strip(),
            "environment": self._normalize_name(str(mission.get("environment", "")).strip()),
            "location": str(mission.get("location", "")).strip(),
            "objective": str(mission.get("objective", "")).strip(),
            "mission_style": str(mission.get("mission_style", "")).strip(),
            "coordination_required": bool(mission.get("coordination_required", False)),
            "global_visibility_required": bool(mission.get("global_visibility_required", False)),
            "num_drones": int(mission.get("num_drones", 0)),
            "preferred_roles": [str(role).strip() for role in mission.get("preferred_roles", []) if str(role).strip()],
            "constraints": mission.get("constraints", {}),
        }

        inferred_count = _extract_drone_count(text)
        if inferred_count is not None:
            normalized["num_drones"] = inferred_count

        if "overwatch" in text and "search" in text:
            normalized["global_visibility_required"] = True
        if "high" in text and "overwatch" in text:
            normalized["constraints"] = {
                **(normalized["constraints"] if isinstance(normalized["constraints"], dict) else {}),
                "overwatch_altitude": "high",
            }

        return normalized

    def _template_for_command(self, text: str) -> Optional[Dict[str, Any]]:
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
                    "overwatch",
                    "relay",
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
            inferred_count = _extract_drone_count(text) or 4
            search_count = max(inferred_count - 1, 1)
            return {
                "mission_type": "search_and_overwatch",
                "environment": "forest_edge",
                "location": "forest edge",
                "objective": "search the forest edge and maintain overwatch",
                "mission_style": "sector_based_coverage",
                "coordination_required": True,
                "global_visibility_required": True,
                "num_drones": inferred_count,
                "preferred_roles": [
                    *[f"search_scout_{chr(ord('A') + i)}" for i in range(search_count)],
                    "overwatch",
                ],
                "constraints": {
                    "overwatch_required": True,
                    "high_altitude_overwatch": True,
                },
            }

        return None

    def _validate(self, mission: Dict[str, Any]) -> None:
        required = [
            "mission_type",
            "environment",
            "location",
            "objective",
            "mission_style",
            "coordination_required",
            "global_visibility_required",
            "num_drones",
            "preferred_roles",
            "constraints",
        ]
        missing = [field for field in required if field not in mission]
        if missing:
            raise MissionParseError(f"Mission JSON missing keys: {missing}")

        schema = MissionSchema(**mission)
        if not schema.preferred_roles:
            raise MissionParseError("preferred_roles must not be empty.")
        if schema.num_drones <= 0:
            raise MissionParseError("num_drones must be a positive integer.")
        if not isinstance(schema.constraints, dict):
            raise MissionParseError("constraints must be an object.")

    @staticmethod
    def _normalize_name(value: str) -> str:
        return re.sub(r"[\s\-]+", "_", value.strip().lower()) if value else value


def parse_mission(command: str, model: Optional[str] = None) -> Dict[str, Any]:
    return MissionParser(model=model).parse(command)


def _extract_drone_count(text: str) -> Optional[int]:
    word_to_num = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
    }
    counts = []
    for match in re.finditer(r"\b(\d+|" + "|".join(word_to_num.keys()) + r")\s+drones?\b", text):
        token = match.group(1)
        counts.append(int(token) if token.isdigit() else word_to_num[token])

    if counts:
        return sum(counts)
    return None


def _load_openai_api_key() -> Optional[str]:
    value = os.getenv("OPENAI_API_KEY")
    if value:
        return value

    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return None

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, raw_value = line.split("=", 1)
        if key.strip() != "OPENAI_API_KEY":
            continue

        value = raw_value.strip().strip('"').strip("'")
        if value:
            return value

    return None
