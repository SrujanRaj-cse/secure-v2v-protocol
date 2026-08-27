"""Phase 1 tests: basic Vehicle A → Vehicle B communication."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vehicles.vehicle import Vehicle


def test_vehicle_a_sends_message_to_vehicle_b():
    vehicle_a = Vehicle("A001", 80, (17.3850, 78.4867), "North")
    vehicle_b = Vehicle("B001", 75, (17.3860, 78.4870), "North")

    message = vehicle_a.create_message("EMERGENCY_BRAKING")

    assert message["vehicle_id"] == "A001"
    assert message["event"] == "EMERGENCY_BRAKING"
    assert vehicle_b.receive_message(message) is True


def test_message_contains_vehicle_state():
    vehicle_a = Vehicle("A001", 80, (17.3850, 78.4867), "North")
    message = vehicle_a.create_message("ROAD_HAZARD")

    assert message["speed"] == 80
    assert message["position"]["latitude"] == 17.3850
    assert message["position"]["longitude"] == 78.4867
    assert message["direction"] == "North"
