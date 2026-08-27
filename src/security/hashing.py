"""
SHA-256 hashing for message integrity.

The hash is computed over the canonical serialized message bytes.
Signing operates on these bytes (via ECDSA with SHA-256).
"""

import hashlib

from utils.logger import get_logger

logger = get_logger(__name__)


def hash_message(message_bytes: bytes) -> bytes:
    """Return the SHA-256 digest of the given message bytes."""
    digest = hashlib.sha256(message_bytes).digest()
    logger.debug(f"SHA-256 hash computed ({len(digest)} bytes)")
    return digest


def hash_message_hex(message_bytes: bytes) -> str:
    """Return the SHA-256 digest as a lowercase hex string (for logging)."""
    return hashlib.sha256(message_bytes).hexdigest()
