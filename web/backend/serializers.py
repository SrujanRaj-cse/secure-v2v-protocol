"""JSON serialization helpers for API responses."""

import base64
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import serialization


def abbreviate_key(public_key) -> str:
    """Return abbreviated public key fingerprint for display (never private key)."""
    pem = public_key.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    lines = [l for l in pem.strip().split("\n") if not l.startswith("-----")]
    joined = "".join(lines)
    return f"{joined[:16]}...{joined[-16:]}"


def certificate_to_dict(certificate: x509.Certificate, vehicle_id: str) -> dict[str, Any]:
    """Serialize certificate public info for API (no private data)."""
    pub = certificate.public_key()
    return {
        "vehicle_id": vehicle_id,
        "status": "VALID",
        "issuer": certificate.issuer.rfc4514_string(),
        "subject": certificate.subject.rfc4514_string(),
        "serial_number": str(certificate.serial_number),
        "not_valid_before": certificate.not_valid_before_utc.isoformat(),
        "not_valid_after": certificate.not_valid_after_utc.isoformat(),
        "algorithm": "ECDSA SECP256R1",
        "public_key_abbrev": abbreviate_key(pub),
        "signature_valid": True,
    }


def packet_to_api(packet: dict) -> dict[str, Any]:
    """Convert internal packet (bytes fields) to JSON-safe dict."""
    sig = packet["signature"]
    cert = packet["certificate_pem"]
    return {
        "message": packet["message"],
        "signature_b64": base64.b64encode(sig).decode("ascii"),
        "certificate_pem": cert.decode("ascii") if isinstance(cert, bytes) else cert,
    }


def packet_from_api(data: dict) -> dict:
    """Restore internal packet from API JSON."""
    return {
        "message": data["message"],
        "signature": base64.b64decode(data["signature_b64"]),
        "certificate_pem": data["certificate_pem"].encode("ascii")
        if isinstance(data["certificate_pem"], str)
        else data["certificate_pem"],
    }
