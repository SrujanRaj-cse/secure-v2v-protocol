"""Shared pytest fixtures for secure V2V protocol tests."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from attacks.attacker import Attacker
from ca.certificate_authority import CertificateAuthority
from protocol.v2v_protocol import SecureVehicle
from security.keys import generate_key_pair


@pytest.fixture
def setup():
    """Create CA, two secure vehicles, and an attacker."""
    ca = CertificateAuthority()
    key_a = generate_key_pair()
    key_b = generate_key_pair()
    cert_a = ca.register_vehicle("A001", key_a.public_key())
    cert_b = ca.register_vehicle("B001", key_b.public_key())

    vehicle_a = SecureVehicle(
        "A001", 80, (17.3850, 78.4867), "North", key_a, cert_a, ca
    )
    vehicle_b = SecureVehicle(
        "B001", 75, (17.3860, 78.4870), "North", key_b, cert_b, ca
    )
    attacker = Attacker(ca)
    return ca, vehicle_a, vehicle_b, attacker
