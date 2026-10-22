"""
V2V safety message definitions and canonical serialization.

Canonical JSON ensures the same logical message always produces the same
byte string before hashing/signing — critical for signature verification.
"""

import json
import math
import time
import uuid
from typing import Any

# Supported safety event types for the simulator
SAFETY_EVENTS = (
    "EMERGENCY_BRAKING",
    "ROAD_HAZARD",
    "ACCIDENT_WARNING",
    "SUDDEN_SLOWDOWN",
    "COLLISION_WARNING",
)

REQUIRED_MESSAGE_FIELDS = (
    "vehicle_id",
    "timestamp",
    "sequence_number",
    "position",
    "speed",
    "direction",
    "event",
    "message_id",
    "schema_version",
    "event_data",
)


def create_safety_message(
    vehicle_id: str,
    sequence_number: int,
    position: tuple[float, float],
    speed: float,
    direction: str,
    event: str,
    timestamp: float | None = None,
    event_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a structured V2V safety message with all required fields.

    Position is stored as a dict so JSON serialization is deterministic.
    """
    if event not in SAFETY_EVENTS:
        raise ValueError(f"Unknown safety event: {event}")

    return {
        "vehicle_id": vehicle_id,
        "timestamp": timestamp if timestamp is not None else time.time(),
        "sequence_number": sequence_number,
        "position": {
            "latitude": position[0],
            "longitude": position[1],
        },
        "speed": speed,
        "direction": direction,
        "event": event,
        "message_id": str(uuid.uuid4()),
        "schema_version": 1,
        "event_data": event_data or {},
    }


def serialize_message(message: dict[str, Any]) -> bytes:
    """
    Serialize a message to canonical JSON bytes.

    sort_keys=True and compact separators guarantee a single representation
    for any given message content — required before hashing/signing.
    """
    return json.dumps(message, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _valid_json_value(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_valid_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _valid_json_value(item) for key, item in value.items())
    return False


def validate_message_structure(message: dict[str, Any]) -> tuple[bool, str]:
    """Check that a message contains all required fields."""
    if not isinstance(message, dict):
        return False, "Message must be an object"
    for field in REQUIRED_MESSAGE_FIELDS:
        if field not in message:
            return False, f"Missing required field: {field}"

    if message["event"] not in SAFETY_EVENTS:
        return False, f"Invalid event type: {message['event']}"

    if not isinstance(message["vehicle_id"], str) or not message["vehicle_id"].strip():
        return False, "Vehicle ID must be a non-empty string"
    if not isinstance(message["message_id"], str) or not message["message_id"].strip():
        return False, "Message ID must be a non-empty string"
    if isinstance(message["schema_version"], bool) or message["schema_version"] != 1:
        return False, "Unsupported schema version"
    if not isinstance(message["sequence_number"], int) or isinstance(message["sequence_number"], bool) or message["sequence_number"] < 1:
        return False, "Sequence number must be a positive integer"
    if not isinstance(message["timestamp"], (int, float)) or isinstance(message["timestamp"], bool) or not math.isfinite(message["timestamp"]):
        return False, "Timestamp must be finite numeric seconds"
    if not isinstance(message["speed"], (int, float)) or isinstance(message["speed"], bool) or not math.isfinite(message["speed"]) or not 0 <= message["speed"] <= 400:
        return False, "Speed must be between 0 and 400 km/h"
    if not isinstance(message["direction"], str) or not message["direction"].strip():
        return False, "Direction must be a non-empty string"
    if message["direction"].lower() not in {
        "north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"
    }:
        return False, "Direction must be a compass heading"
    if not isinstance(message["event_data"], dict) or not _valid_json_value(message["event_data"]):
        return False, "Event data must contain only finite JSON values"

    position = message["position"]
    if not isinstance(position, dict):
        return False, "Position must be a dictionary"
    if "latitude" not in position or "longitude" not in position:
        return False, "Position must contain latitude and longitude"
    lat, lon = position["latitude"], position["longitude"]
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) for v in (lat, lon)):
        return False, "Coordinates must be finite numbers"
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        return False, "Coordinates are outside geographic bounds"

    return True, "OK"
