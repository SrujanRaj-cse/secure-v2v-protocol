"""Tests for replay protection and timestamp freshness."""

import copy
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from protocol.messages import create_safety_message
from protocol.v2v_protocol import create_signed_packet
from security.replay import ReplayProtector
from vehicles.vehicle import Vehicle


def test_valid_messages_with_increasing_sequence_accepted():
    vehicle_a = Vehicle("A001", 80, (17.3850, 78.4867), "North")
    vehicle_b = Vehicle("B001", 75, (17.3860, 78.4870), "North")

    msg1 = vehicle_a.create_message("EMERGENCY_BRAKING")
    msg2 = vehicle_a.create_message("ROAD_HAZARD")

    assert vehicle_b.receive_message(msg1) is True
    assert vehicle_b.receive_message(msg2) is True


def test_replayed_message_rejected_unit():
    vehicle_a = Vehicle("A001", 80, (17.3850, 78.4867), "North")
    vehicle_b = Vehicle("B001", 75, (17.3860, 78.4870), "North")

    message = vehicle_a.create_message("EMERGENCY_BRAKING")
    assert vehicle_b.receive_message(message) is True
    assert vehicle_b.receive_message(message) is False


def test_duplicate_sequence_number_rejected():
    protector = ReplayProtector()

    message = create_safety_message(
        vehicle_id="A001",
        sequence_number=1,
        position=(17.0, 78.0),
        speed=80,
        direction="North",
        event="EMERGENCY_BRAKING",
    )

    ok, _ = protector.check(message)
    assert ok is True

    ok, reason = protector.check(message)
    assert ok is False
    assert "Replay detected" in reason


def test_stale_timestamp_rejected_unit():
    protector = ReplayProtector(timestamp_window=2.0)

    stale_message = create_safety_message(
        vehicle_id="A001",
        sequence_number=1,
        position=(17.0, 78.0),
        speed=80,
        direction="North",
        event="EMERGENCY_BRAKING",
        timestamp=time.time() - 10.0,
    )

    ok, reason = protector.check(stale_message)
    assert ok is False
    assert "expired" in reason


def test_old_sequence_number_rejected():
    vehicle_b = Vehicle("B001", 75, (17.3860, 78.4870), "North")

    msg2 = create_safety_message(
        vehicle_id="A001",
        sequence_number=2,
        position=(17.0, 78.0),
        speed=80,
        direction="North",
        event="EMERGENCY_BRAKING",
    )
    assert vehicle_b.receive_message(msg2) is True

    msg1 = create_safety_message(
        vehicle_id="A001",
        sequence_number=1,
        position=(17.0, 78.0),
        speed=80,
        direction="North",
        event="EMERGENCY_BRAKING",
    )
    assert vehicle_b.receive_message(msg1) is False


def test_replayed_message_rejected(setup):
    _, vehicle_a, vehicle_b, attacker = setup
    packet = vehicle_a.send_message("EMERGENCY_BRAKING")
    assert vehicle_b.receive_packet(packet)[0] is True
    attacker.capture(packet)
    replay = attacker.replay_attack()
    ok, _ = vehicle_b.receive_packet(replay)
    assert ok is False


def test_duplicate_sequence_rejected(setup):
    _, vehicle_a, vehicle_b, _ = setup
    packet = vehicle_a.send_message("EMERGENCY_BRAKING")
    assert vehicle_b.receive_packet(packet)[0] is True
    ok, _ = vehicle_b.receive_packet(copy.deepcopy(packet))
    assert ok is False


def test_stale_timestamp_rejected(setup):
    _, vehicle_a, vehicle_b, _ = setup
    stale_message = create_safety_message(
        vehicle_id="A001",
        sequence_number=1,
        position=(17.3850, 78.4867),
        speed=80,
        direction="North",
        event="EMERGENCY_BRAKING",
        timestamp=time.time() - 60.0,
    )
    packet = create_signed_packet(stale_message, vehicle_a.private_key, vehicle_a.certificate)
    ok, reason = vehicle_b.receive_packet(packet)
    assert ok is False
    assert "expired" in reason.lower()


def test_increasing_sequence_accepted(setup):
    _, vehicle_a, vehicle_b, _ = setup
    for event in ["EMERGENCY_BRAKING", "ROAD_HAZARD", "ACCIDENT_WARNING"]:
        packet = vehicle_a.send_message(event)
        ok, _ = vehicle_b.receive_packet(packet)
        assert ok is True
