"""
V2V safety message definitions and canonical serialization.

Canonical JSON ensures the same logical message always produces the same
byte string before hashing/signing — critical for signature verification.
"""

import json
import time
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
)


def create_safety_message(
    vehicle_id: str,
    sequence_number: int,
    position: tuple[float, float],
    speed: float,
    direction: str,
    event: str,
    timestamp: float | None = None,
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
    }


def serialize_message(message: dict[str, Any]) -> bytes:
    """
    Serialize a message to canonical JSON bytes.

    sort_keys=True and compact separators guarantee a single representation
    for any given message content — required before hashing/signing.
    """
    return json.dumps(message, sort_keys=True, separators=(",", ":")).encode("utf-8")


def validate_message_structure(message: dict[str, Any]) -> tuple[bool, str]:
    """Check that a message contains all required fields."""
    for field in REQUIRED_MESSAGE_FIELDS:
        if field not in message:
            return False, f"Missing required field: {field}"

    if message["event"] not in SAFETY_EVENTS:
        return False, f"Invalid event type: {message['event']}"

    position = message["position"]
    if not isinstance(position, dict):
        return False, "Position must be a dictionary"
    if "latitude" not in position or "longitude" not in position:
        return False, "Position must contain latitude and longitude"

    return True, "OK"
