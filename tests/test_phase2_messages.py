"""Phase 2 tests: structured message format and canonical serialization."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from protocol.messages import (
    REQUIRED_MESSAGE_FIELDS,
    create_safety_message,
    serialize_message,
    validate_message_structure,
)
from vehicles.vehicle import Vehicle


def test_message_has_all_required_fields():
    message = create_safety_message(
        vehicle_id="A001",
        sequence_number=1,
        position=(17.3850, 78.4867),
        speed=80,
        direction="North",
        event="EMERGENCY_BRAKING",
        timestamp=1000.0,
    )

    for field in REQUIRED_MESSAGE_FIELDS:
        assert field in message


def test_position_is_structured_dict():
    message = create_safety_message(
        vehicle_id="A001",
        sequence_number=1,
        position=(17.3850, 78.4867),
        speed=80,
        direction="North",
        event="ROAD_HAZARD",
    )

    assert message["position"]["latitude"] == 17.3850
    assert message["position"]["longitude"] == 78.4867


def test_canonical_serialization_is_deterministic():
    message = create_safety_message(
        vehicle_id="A001",
        sequence_number=1,
        position=(17.3850, 78.4867),
        speed=80,
        direction="North",
        event="ACCIDENT_WARNING",
        timestamp=1000.0,
    )

    first = serialize_message(message)
    second = serialize_message(message)
    assert first == second


def test_sequence_number_increments():
    vehicle_a = Vehicle("A001", 80, (17.3850, 78.4867), "North")

    msg1 = vehicle_a.create_message("EMERGENCY_BRAKING")
    msg2 = vehicle_a.create_message("ROAD_HAZARD")

    assert msg1["sequence_number"] == 1
    assert msg2["sequence_number"] == 2


def test_invalid_event_rejected():
    vehicle_b = Vehicle("B001", 75, (17.3860, 78.4870), "North")
    bad_message = {
        "vehicle_id": "A001",
        "timestamp": 1000.0,
        "sequence_number": 1,
        "position": {"latitude": 17.0, "longitude": 78.0},
        "speed": 80,
        "direction": "North",
        "event": "INVALID_EVENT",
    }

    assert vehicle_b.receive_message(bad_message) is False
