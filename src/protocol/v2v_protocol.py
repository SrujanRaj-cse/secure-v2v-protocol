"""
V2V protocol: signed message creation and delivery.

Combines message structure, signing, and the verification pipeline
into the complete secure communication protocol.
"""

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey

from ca.certificate_authority import CertificateAuthority
from protocol.messages import create_safety_message, serialize_message
from security.certificates import certificate_to_pem
from security.signatures import sign_message
from security.verification import MessageVerifier
from utils.logger import get_logger

logger = get_logger(__name__)


def create_signed_packet(
    message: dict,
    private_key: EllipticCurvePrivateKey,
    certificate: x509.Certificate,
) -> dict:
    """
    Sign a safety message and wrap it in a transmittable packet.

    Returns { message, signature, certificate_pem }.
    Private key is used locally and never included in the packet.
    """
    # Step 1: deterministic serialization -> Step 2: SHA-256 + ECDSA sign
    message_bytes = serialize_message(message)
    signature = sign_message(message_bytes, private_key)

    packet = {
        "message": message,
        "signature": signature,
        "certificate_pem": certificate_to_pem(certificate),
    }

    logger.info(
        f"Signed packet created for vehicle {message['vehicle_id']} "
        f"seq={message['sequence_number']}"
    )
    return packet


class SecureVehicle:
    """
    A vehicle with cryptographic identity and secure send/receive capability.

    Holds private key and certificate (never transmitted).
    Uses MessageVerifier for incoming packet validation.
    """

    def __init__(
        self,
        vehicle_id: str,
        speed: float,
        position: tuple[float, float],
        direction: str,
        private_key: EllipticCurvePrivateKey,
        certificate: x509.Certificate,
        ca: CertificateAuthority,
    ):
        self.vehicle_id = vehicle_id
        self.speed = speed
        self.position = position
        self.direction = direction
        self.private_key = private_key
        self.certificate = certificate
        self.sequence_number = 0

        from security.replay import ReplayProtector

        self.verifier = MessageVerifier(ca, ReplayProtector())

    def create_message(self, event: str) -> dict:
        """Create a structured safety message (unsigned)."""
        self.sequence_number += 1
        return create_safety_message(
            vehicle_id=self.vehicle_id,
            sequence_number=self.sequence_number,
            position=self.position,
            speed=self.speed,
            direction=self.direction,
            event=event,
        )

    def send_message(self, event: str) -> dict:
        """Create and sign a safety message, returning a signed packet."""
        message = self.create_message(event)
        return create_signed_packet(message, self.private_key, self.certificate)

    def receive_packet(self, packet: dict) -> tuple[bool, str]:
        """Verify and accept/reject an incoming signed packet."""
        logger.info(
            f"Vehicle {self.vehicle_id} received packet from "
            f"{packet.get('message', {}).get('vehicle_id', 'UNKNOWN')}"
        )
        return self.verifier.verify(packet)
