"""Tests for ECDSA key pair generation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

from security.keys import generate_key_pair


def test_generate_key_pair():
    private_key = generate_key_pair()
    assert private_key is not None


def test_public_key_extractable():
    private_key = generate_key_pair()
    public_key = private_key.public_key()
    assert public_key.curve.name == "secp256r1"


def test_two_key_pairs_are_different():
    key_a = generate_key_pair()
    key_b = generate_key_pair()
    pub_a = key_a.public_key().public_numbers()
    pub_b = key_b.public_key().public_numbers()
    assert (pub_a.x, pub_a.y) != (pub_b.x, pub_b.y)


def test_private_key_can_sign():
    private_key = generate_key_pair()
    signature = private_key.sign(b"test message", ec.ECDSA(hashes.SHA256()))
    assert len(signature) > 0
