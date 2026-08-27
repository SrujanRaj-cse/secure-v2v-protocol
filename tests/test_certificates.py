"""Tests for X.509 certificate issuance and verification."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from protocol.messages import create_safety_message
from protocol.v2v_protocol import create_signed_packet
from security.certificates import create_ca_certificate, issue_vehicle_certificate
from security.keys import generate_key_pair


def test_ca_registers_and_verifies(setup):
    ca, vehicle_a, _, _ = setup
    assert ca.is_registered("A001")
    assert ca.is_registered("B001")
    ok, _ = ca.verify_vehicle_certificate(vehicle_a.certificate)
    assert ok is True


def test_invalid_certificate_rejected(setup):
    ca, vehicle_a, vehicle_b, _ = setup
    from security.certificates import certificate_to_pem

    packet = vehicle_a.send_message("ROAD_HAZARD")
    evil_key = generate_key_pair()
    evil_cert = ca.register_vehicle("EVIL001", evil_key.public_key())
    packet["certificate_pem"] = certificate_to_pem(evil_cert)

    ok, _ = vehicle_b.receive_packet(packet)
    assert ok is False


def test_unknown_vehicle_rejected(setup):
    ca, _, vehicle_b, _ = setup
    unknown_key = generate_key_pair()
    fake_ca_key = generate_key_pair()
    fake_ca_cert = create_ca_certificate(fake_ca_key)
    unregistered_cert = issue_vehicle_certificate(
        "UNKNOWN001",
        unknown_key.public_key(),
        fake_ca_key,
        fake_ca_cert,
    )
    message = create_safety_message(
        "UNKNOWN001", 1, (0, 0), 50, "East", "ROAD_HAZARD"
    )
    packet = create_signed_packet(message, unknown_key, unregistered_cert)
    ok, _ = vehicle_b.receive_packet(packet)
    assert ok is False


def test_valid_message_accepted(setup):
    _, vehicle_a, vehicle_b, _ = setup
    packet = vehicle_a.send_message("EMERGENCY_BRAKING")
    ok, _ = vehicle_b.receive_packet(packet)
    assert ok is True
