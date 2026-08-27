"""Tests for impersonation and fake-certificate attacks."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def test_impersonation_rejected(setup):
    _, _, vehicle_b, attacker = setup
    packet = attacker.impersonation_attack(target_vehicle_id="A001")
    ok, _ = vehicle_b.receive_packet(packet)
    assert ok is False


def test_fake_certificate_rejected(setup):
    _, vehicle_a, vehicle_b, attacker = setup
    legit_packet = vehicle_a.send_message("COLLISION_WARNING")
    fake_cert_packet = attacker.fake_certificate_attack(legit_packet)
    ok, _ = vehicle_b.receive_packet(fake_cert_packet)
    assert ok is False
