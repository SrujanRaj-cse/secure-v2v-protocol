"""
X.509 certificate creation and verification for vehicle identity.

The CA signs each vehicle's public key into an X.509 certificate.
Receivers verify the certificate chain back to the trusted CA.
"""

import datetime

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ec import (
    EllipticCurvePrivateKey,
    EllipticCurvePublicKey,
)
from cryptography.x509.oid import NameOID

from utils.logger import get_logger

logger = get_logger(__name__)

# How long issued vehicle certificates remain valid
CERTIFICATE_VALIDITY_DAYS = 365


def create_ca_certificate(
    ca_private_key: EllipticCurvePrivateKey,
    ca_name: str = "Secure V2V CA",
) -> x509.Certificate:
    """
    Create a self-signed X.509 certificate for the Certificate Authority.

    The CA certificate is the trust anchor — vehicles verify peer
    certificates are signed by this CA.
    """
    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, ca_name)]
    )

    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(ca_private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=CERTIFICATE_VALIDITY_DAYS))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .sign(ca_private_key, hashes.SHA256())
    )

    logger.info(f"CA self-signed certificate created: {ca_name}")
    return cert


def issue_vehicle_certificate(
    vehicle_id: str,
    vehicle_public_key: EllipticCurvePublicKey,
    ca_private_key: EllipticCurvePrivateKey,
    ca_certificate: x509.Certificate,
) -> x509.Certificate:
    """
    Issue an X.509 certificate binding a vehicle ID to its public key.

    The CA signs the certificate with its private key. Only the CA can
    create certificates that pass verification.
    """
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, vehicle_id),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "V2V Simulator"),
        ]
    )

    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_certificate.subject)
        .public_key(vehicle_public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=CERTIFICATE_VALIDITY_DAYS))
        .sign(ca_private_key, hashes.SHA256())
    )

    logger.info(f"Certificate issued to vehicle {vehicle_id}")
    return cert


def certificate_to_pem(certificate: x509.Certificate) -> bytes:
    """Serialize a certificate to PEM format for transmission."""
    return certificate.public_bytes(serialization.Encoding.PEM)


def certificate_from_pem(pem_data: bytes) -> x509.Certificate:
    """Load a certificate from PEM bytes."""
    return x509.load_pem_x509_certificate(pem_data)


def verify_certificate_against_ca(
    vehicle_certificate: x509.Certificate,
    ca_certificate: x509.Certificate,
) -> tuple[bool, str]:
    """
    Verify a vehicle certificate was signed by the trusted CA.

    Checks signature validity and expiry. Does NOT check registration
    (that is handled by the CA's vehicle registry).
    """
    ca_public_key = ca_certificate.public_key()

    try:
        ca_public_key.verify(
            vehicle_certificate.signature,
            vehicle_certificate.tbs_certificate_bytes,
            ec.ECDSA(vehicle_certificate.signature_hash_algorithm),
        )
    except Exception:
        reason = "Certificate not signed by trusted CA"
        logger.warning(f"REJECTED: {reason}")
        return False, reason

    now = datetime.datetime.now(datetime.timezone.utc)
    if now < vehicle_certificate.not_valid_before_utc:
        reason = "Certificate not yet valid"
        logger.warning(f"REJECTED: {reason}")
        return False, reason

    if now > vehicle_certificate.not_valid_after_utc:
        reason = "Certificate expired"
        logger.warning(f"REJECTED: {reason}")
        return False, reason

    logger.info("Certificate verification successful")
    return True, "OK"


def get_vehicle_id_from_certificate(certificate: x509.Certificate) -> str:
    """Extract the vehicle ID (Common Name) from a certificate."""
    for attr in certificate.subject:
        if attr.oid == NameOID.COMMON_NAME:
            return attr.value
    return "UNKNOWN"
