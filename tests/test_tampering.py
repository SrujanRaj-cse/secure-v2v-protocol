"""Tests for message tampering attack detection."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def test_modified_message_rejected(setup):
    _, vehicle_a, vehicle_b, attacker = setup
    packet = vehicle_a.send_message("ACCIDENT_WARNING")
    attacker.capture(packet)
    tampered = attacker.tampering_attack(field="event", new_value="SUDDEN_SLOWDOWN")
    ok, reason = vehicle_b.receive_packet(tampered)
    assert ok is False
    assert "signature" in reason.lower() or "Invalid" in reason


def test_speed_tampering_rejected(setup):
    _, vehicle_a, vehicle_b, attacker = setup
    packet = vehicle_a.send_message("ROAD_HAZARD")
    attacker.capture(packet)
    tampered = attacker.tampering_attack(field="speed", new_value=180)
    ok, reason = vehicle_b.receive_packet(tampered)
    assert ok is False
    assert "signature" in reason.lower() or "Invalid" in reason
