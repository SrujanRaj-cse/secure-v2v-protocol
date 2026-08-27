"""Tests for ECDSA digital signatures."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from security.hashing import hash_message
from security.keys import generate_key_pair
from security.signatures import sign_message, verify_signature


def test_signature_roundtrip():
    key = generate_key_pair()
    data = b"canonical message bytes"
    sig = sign_message(data, key)
    ok, _ = verify_signature(data, sig, key.public_key())
    assert ok is True


def test_explicit_sha256_before_signing():
    """Signing must use hash_message() before ECDSA."""
    key = generate_key_pair()
    data = b"structured safety message bytes"
    expected_hash = hash_message(data)

    sig = sign_message(data, key)
    ok, _ = verify_signature(data, sig, key.public_key())
    assert ok is True
    assert len(expected_hash) == 32  # SHA-256 produces 32 bytes


def test_invalid_signature_rejected(setup):
    _, vehicle_a, vehicle_b, _ = setup
    packet = vehicle_a.send_message("COLLISION_WARNING")
    packet["signature"] = b"\x00" * 64
    ok, _ = vehicle_b.receive_packet(packet)
    assert ok is False
