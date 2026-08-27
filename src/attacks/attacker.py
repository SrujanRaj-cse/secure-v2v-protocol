"""
Simulated attacker for demonstrating V2V security failures.

The attacker can intercept legitimate packets and attempt:
- Replay: resend an old legitimate packet
- Tampering: modify message content, keep original signature
- Impersonation: forge a message without the victim's private key
"""

import copy

from cryptography import x509

from ca.certificate_authority import CertificateAuthority
from protocol.messages import create_safety_message, serialize_message
from protocol.v2v_protocol import create_signed_packet
from security.keys import generate_key_pair
from utils.logger import get_logger

logger = get_logger(__name__)


class Attacker:
    """
    Simulates an adversary on the V2V communication channel.

    The attacker can capture packets but does NOT have access to
    legitimate vehicles' private keys.
    """

    def __init__(self, ca: CertificateAuthority):
        self.ca = ca
        self.captured_packets: list[dict] = []
        # Attacker generates its own key pair for impersonation attempts
        self.attacker_private_key = generate_key_pair()

    def capture(self, packet: dict) -> None:
        """Intercept and store a legitimate signed packet."""
        self.captured_packets.append(copy.deepcopy(packet))
        logger.warning(
            f"Attacker captured packet from "
            f"{packet['message']['vehicle_id']}"
        )

    def replay_attack(self, index: int = 0) -> dict:
        """
        Replay a previously captured packet unchanged.

        Should be rejected due to duplicate sequence number / stale timestamp.
        """
        if not self.captured_packets:
            raise ValueError("No captured packets to replay")

        packet = copy.deepcopy(self.captured_packets[index])
        logger.warning("Attacker launching REPLAY attack")
        return packet

    def tampering_attack(self, index: int = 0, field: str = "speed", new_value=180) -> dict:
        """
        Modify a message field but keep the original signature.

        Should be rejected because the signature no longer matches the content.
        """
        if not self.captured_packets:
            raise ValueError("No captured packets to tamper")

        packet = copy.deepcopy(self.captured_packets[index])
        packet["message"][field] = new_value
        logger.warning(
            f"Attacker launching TAMPERING attack: {field} -> {new_value}"
        )
        return packet

    def impersonation_attack(
        self,
        target_vehicle_id: str = "A001",
        event: str = "EMERGENCY_BRAKING",
    ) -> dict:
        """
        Attempt to send a message claiming to be another vehicle.

        The attacker signs with its own key and uses a self-signed fake
        certificate (not issued by the CA). Should be rejected.
        """
        logger.warning(
            f"Attacker launching IMPERSONATION attack as {target_vehicle_id}"
        )

        # Attacker creates a fake message pretending to be the target
        fake_message = create_safety_message(
            vehicle_id=target_vehicle_id,
            sequence_number=999,
            position=(0.0, 0.0),
            speed=200,
            direction="Unknown",
            event=event,
        )

        # Attacker signs with its OWN key (not the target's private key)
        from security.certificates import issue_vehicle_certificate

        # Create a certificate that won't be in CA registry
        fake_cert = issue_vehicle_certificate(
            vehicle_id=target_vehicle_id,
            vehicle_public_key=self.attacker_private_key.public_key(),
            ca_private_key=self.attacker_private_key,  # self-signed, not real CA
            ca_certificate=self._create_self_signed_ca_cert(),
        )

        return create_signed_packet(
            fake_message,
            self.attacker_private_key,
            fake_cert,
        )

    def fake_certificate_attack(self, legitimate_packet: dict) -> dict:
        """
        Use a legitimate message/signature but swap in an unregistered certificate.

        Should be rejected because the certificate is not CA-issued/registered.
        """
        logger.warning("Attacker launching FAKE CERTIFICATE attack")

        # Register attacker under a different ID with CA, then claim to be A001
        attacker_id = "EVIL001"
        attacker_cert = self.ca.register_vehicle(
            attacker_id,
            self.attacker_private_key.public_key(),
        )

        packet = copy.deepcopy(legitimate_packet)
        from security.certificates import certificate_to_pem

        packet["certificate_pem"] = certificate_to_pem(attacker_cert)
        return packet

    def _create_self_signed_ca_cert(self) -> x509.Certificate:
        """Helper: attacker's fake CA cert for impersonation demo."""
        from security.certificates import create_ca_certificate

        return create_ca_certificate(
            self.attacker_private_key, "Fake Attacker CA"
        )
