"""
Simplified Certificate Authority for the V2V simulator.

The CA registers vehicles, issues X.509 certificates, and maintains
a registry of known vehicles. It is NOT involved in every V2V message —
it only establishes initial trust during registration.
"""

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey

from security.certificates import (
    create_ca_certificate,
    get_vehicle_id_from_certificate,
    issue_vehicle_certificate,
    verify_certificate_against_ca,
)
from security.keys import generate_key_pair
from utils.logger import get_logger

logger = get_logger(__name__)


class CertificateAuthority:
    """
    Trusted Certificate Authority for the V2V network.

    Responsibilities:
    - Generate and hold the CA key pair
    - Register vehicles and issue signed certificates
    - Verify whether a presented certificate belongs to a registered vehicle
    """

    def __init__(self, ca_name: str = "Secure V2V CA"):
        self.ca_name = ca_name
        self.ca_private_key: EllipticCurvePrivateKey = generate_key_pair()
        self.ca_certificate: x509.Certificate = create_ca_certificate(
            self.ca_private_key, ca_name
        )
        # vehicle_id -> issued certificate
        self.registered_vehicles: dict[str, x509.Certificate] = {}

        logger.info(f"Certificate Authority '{ca_name}' initialized")

    def register_vehicle(
        self,
        vehicle_id: str,
        vehicle_public_key,
    ) -> x509.Certificate:
        """
        Register a vehicle and issue a signed X.509 certificate.

        The vehicle sends its public key (never the private key).
        """
        if vehicle_id in self.registered_vehicles:
            logger.warning(f"Vehicle {vehicle_id} already registered — re-issuing")

        certificate = issue_vehicle_certificate(
            vehicle_id=vehicle_id,
            vehicle_public_key=vehicle_public_key,
            ca_private_key=self.ca_private_key,
            ca_certificate=self.ca_certificate,
        )

        self.registered_vehicles[vehicle_id] = certificate
        logger.info(f"Vehicle {vehicle_id} registered with CA")
        return certificate

    def verify_vehicle_certificate(
        self,
        certificate: x509.Certificate,
    ) -> tuple[bool, str]:
        """
        Verify a certificate is CA-signed AND belongs to a registered vehicle.
        """
        valid, reason = verify_certificate_against_ca(
            certificate, self.ca_certificate
        )
        if not valid:
            return False, reason

        vehicle_id = get_vehicle_id_from_certificate(certificate)
        if vehicle_id not in self.registered_vehicles:
            reason = f"Unknown vehicle: {vehicle_id}"
            logger.warning(f"REJECTED: {reason}")
            return False, reason

        # Ensure the presented cert matches what we issued
        registered = self.registered_vehicles[vehicle_id]
        if certificate.serial_number != registered.serial_number:
            reason = f"Certificate mismatch for vehicle {vehicle_id}"
            logger.warning(f"REJECTED: {reason}")
            return False, reason

        return True, "OK"

    def is_registered(self, vehicle_id: str) -> bool:
        """Check if a vehicle ID is in the CA registry."""
        return vehicle_id in self.registered_vehicles
