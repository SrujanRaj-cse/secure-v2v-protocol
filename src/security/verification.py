"""
Complete V2V message verification pipeline.

When Vehicle B receives a signed packet, every check must pass before
the message is accepted. Any failure produces a clear rejection reason.
"""

from cryptography import x509

from ca.certificate_authority import CertificateAuthority
from protocol.messages import serialize_message, validate_message_structure
from security.certificates import get_vehicle_id_from_certificate
from security.replay import ReplayProtector
from security.signatures import verify_signature
from utils.logger import get_logger

logger = get_logger(__name__)


class MessageVerifier:
    """
    Runs the full verification pipeline on incoming signed V2V packets.

    Steps:
    1. Validate packet structure
    2. Verify sender certificate against CA
    3. Verify digital signature
    4. Check timestamp freshness
    5. Check sequence number (replay protection)
    """

    def __init__(
        self,
        ca: CertificateAuthority,
        replay_protector: ReplayProtector,
    ):
        self.ca = ca
        self.replay_protector = replay_protector

    def verify(self, packet: dict) -> tuple[bool, str]:
        """
        Verify a signed V2V packet.

        Expected packet format:
        {
            "message": { ... safety message fields ... },
            "signature": bytes,
            "certificate_pem": bytes,
        }
        """
        # Step 1: Packet structure
        if "message" not in packet or "signature" not in packet:
            reason = "Invalid packet structure: missing message or signature"
            logger.warning(f"REJECTED: {reason}")
            return False, reason

        if "certificate_pem" not in packet:
            reason = "Invalid packet structure: missing certificate"
            logger.warning(f"REJECTED: {reason}")
            return False, reason

        message = packet["message"]
        signature = packet["signature"]
        cert_pem = packet["certificate_pem"]

        # Step 1b: Message field validation
        valid, reason = validate_message_structure(message)
        if not valid:
            logger.warning(f"REJECTED: {reason}")
            return False, reason

        # Step 2: Certificate verification
        try:
            certificate = x509.load_pem_x509_certificate(cert_pem)
        except Exception:
            reason = "Invalid certificate format"
            logger.warning(f"REJECTED: {reason}")
            return False, reason

        cert_ok, cert_reason = self.ca.verify_vehicle_certificate(certificate)
        if not cert_ok:
            return False, cert_reason

        cert_vehicle_id = get_vehicle_id_from_certificate(certificate)
        if cert_vehicle_id != message["vehicle_id"]:
            reason = (
                f"Vehicle ID mismatch: message says {message['vehicle_id']}, "
                f"certificate says {cert_vehicle_id}"
            )
            logger.warning(f"REJECTED: {reason}")
            return False, reason

        # Step 3 & 4: Signature verification over canonical message bytes
        message_bytes = serialize_message(message)
        public_key = certificate.public_key()
        sig_ok, sig_reason = verify_signature(message_bytes, signature, public_key)
        if not sig_ok:
            return False, sig_reason

        # Step 5: Timestamp freshness + sequence number
        replay_ok, replay_reason = self.replay_protector.check(message)
        if not replay_ok:
            return False, replay_reason

        logger.info("Timestamp verification successful")
        logger.info("Sequence number verification successful")
        logger.info("MESSAGE ACCEPTED")
        return True, "OK"
