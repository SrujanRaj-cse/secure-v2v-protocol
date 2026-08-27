"""
ECDSA digital signatures for V2V messages.

Flow (explicit steps for educational clarity):
  1. Canonical message bytes
  2. SHA-256 hash  (hash_message)
  3. ECDSA sign the hash with vehicle private key
  4. Attach signature to packet

Verification reverses the same steps using the public key from the certificate.
"""

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ec import (
    EllipticCurvePrivateKey,
    EllipticCurvePublicKey,
)
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed

from security.hashing import hash_message, hash_message_hex
from utils.logger import get_logger

logger = get_logger(__name__)


def sign_message(message_bytes: bytes, private_key: EllipticCurvePrivateKey) -> bytes:
    """
    Sign canonical message bytes with the vehicle's ECDSA private key.

    Step 1: Compute SHA-256 hash of the serialized message.
    Step 2: Sign the hash with ECDSA (Prehashed mode avoids double-hashing).
    """
    message_hash = hash_message(message_bytes)
    logger.debug(f"SHA-256 digest: {hash_message_hex(message_bytes)}")

    signature = private_key.sign(
        message_hash,
        ec.ECDSA(Prehashed(hashes.SHA256())),
    )
    logger.info("Message signed with ECDSA (SHA-256)")
    return signature


def verify_signature(
    message_bytes: bytes,
    signature: bytes,
    public_key: EllipticCurvePublicKey,
) -> tuple[bool, str]:
    """
    Verify an ECDSA signature against the message and public key.

    Recomputes SHA-256 over the canonical bytes and checks the signature.
    Returns (True, "OK") on success, (False, reason) on failure.
    """
    message_hash = hash_message(message_bytes)

    try:
        public_key.verify(
            signature,
            message_hash,
            ec.ECDSA(Prehashed(hashes.SHA256())),
        )
        logger.info("Digital signature verification successful")
        return True, "OK"
    except InvalidSignature:
        reason = "Invalid digital signature"
        logger.warning(f"REJECTED: {reason}")
        return False, reason
