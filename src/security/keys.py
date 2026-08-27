"""
ECDSA key pair generation using the cryptography library.

We use SECP256R1 (NIST P-256): a modern elliptic curve with ~128-bit
security, widely supported in automotive and IoT PKI systems.
Private keys never leave the vehicle that generated them.
"""

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey

from config import ECDSA_CURVE
from utils.logger import get_logger

logger = get_logger(__name__)

# Map config string to the library's curve object
_CURVES = {
    "SECP256R1": ec.SECP256R1(),
    "SECP384R1": ec.SECP384R1(),
}


def generate_key_pair() -> EllipticCurvePrivateKey:
    """
    Generate a fresh ECDSA private key on the configured curve.

    The returned object holds both private and public key material;
    extract the public key with private_key.public_key().
    """
    curve_name = ECDSA_CURVE
    curve = _CURVES.get(curve_name)
    if curve is None:
        raise ValueError(f"Unsupported curve: {curve_name}")

    private_key = ec.generate_private_key(curve)
    logger.info(f"Generated ECDSA key pair on curve {curve_name}")
    return private_key
