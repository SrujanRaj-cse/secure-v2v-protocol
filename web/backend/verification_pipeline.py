"""
Step-by-step verification pipeline for the web UI.

Calls the SAME underlying functions as MessageVerifier.verify()
but returns per-step status for visualization.
"""

from cryptography import x509

from ca.certificate_authority import CertificateAuthority
from protocol.messages import serialize_message, validate_message_structure
from security.certificates import get_vehicle_id_from_certificate
from security.replay import ReplayProtector
from security.signatures import verify_signature


def verify_with_pipeline(
    packet: dict,
    ca: CertificateAuthority,
    replay_protector: ReplayProtector,
) -> dict:
    """
    Run verification and return step-by-step pipeline results.

    Does not modify MessageVerifier — mirrors its logic for UI display.
    """
    steps: list[dict] = []

    def add_step(name: str, status: str, detail: str = ""):
        steps.append({"name": name, "status": status, "detail": detail})

    message = packet.get("message")
    signature = packet.get("signature")
    cert_pem = packet.get("certificate_pem")

    if not message or signature is None:
        add_step("Packet Structure", "failed", "Missing message or signature")
        return _result(False, steps, "Invalid packet structure")

    if not cert_pem:
        add_step("Packet Structure", "failed", "Missing certificate")
        return _result(False, steps, "Invalid packet structure: missing certificate")

    add_step("Message Created", "success", f"From {message.get('vehicle_id', '?')}")

    add_step("SHA-256 Hash", "success", "Computed over canonical JSON bytes")

    add_step("ECDSA Signature", "success", "Signature attached to packet")
    add_step("Certificate Attached", "success", "X.509 certificate included")
    add_step("Transmission", "success", "Packet delivered to receiver")

    add_step("Packet Structure", "success", "All required fields present")

    valid, reason = validate_message_structure(message)
    if not valid:
        add_step("Message Validation", "failed", reason)
        return _result(False, steps, reason)
    add_step("Message Validation", "success", "Structure valid")

    try:
        certificate = x509.load_pem_x509_certificate(cert_pem)
    except Exception:
        add_step("Certificate Verification", "failed", "Invalid certificate format")
        return _result(False, steps, "Invalid certificate format")

    cert_ok, cert_reason = ca.verify_vehicle_certificate(certificate)
    if not cert_ok:
        add_step("Certificate Verification", "failed", cert_reason)
        return _result(False, steps, cert_reason)
    add_step("Certificate Verification", "success", "CA-signed and registered")

    cert_vid = get_vehicle_id_from_certificate(certificate)
    if cert_vid != message["vehicle_id"]:
        reason = f"Vehicle ID mismatch: message {message['vehicle_id']}, cert {cert_vid}"
        add_step("Identity Check", "failed", reason)
        return _result(False, steps, reason)
    add_step("Identity Check", "success", "Vehicle ID matches certificate")

    message_bytes = serialize_message(message)
    public_key = certificate.public_key()
    sig_ok, sig_reason = verify_signature(message_bytes, signature, public_key)
    if not sig_ok:
        add_step("Signature Verification", "failed", sig_reason)
        return _result(False, steps, sig_reason)
    add_step("Signature Verification", "success", "ECDSA signature valid")

    replay_ok, replay_reason = replay_protector.check(message)
    if not replay_ok:
        if "Replay" in replay_reason or "sequence" in replay_reason.lower():
            add_step("Replay Check", "failed", replay_reason)
            add_step("Timestamp Check", "skipped", "")
            add_step("Sequence Check", "failed", replay_reason)
        elif "expired" in replay_reason.lower() or "timestamp" in replay_reason.lower():
            add_step("Replay Check", "success", "No duplicate sequence yet")
            add_step("Timestamp Check", "failed", replay_reason)
            add_step("Sequence Check", "skipped", "")
        else:
            add_step("Replay Check", "failed", replay_reason)
        return _result(False, steps, replay_reason)

    add_step("Replay Check", "success", "No replay detected")
    add_step("Timestamp Check", "success", "Message is fresh")
    add_step("Sequence Check", "success", f"Sequence {message['sequence_number']} accepted")

    add_step("Result", "success", "MESSAGE ACCEPTED")
    return _result(True, steps, "OK")


def _result(accepted: bool, steps: list, reason: str) -> dict:
    return {
        "accepted": accepted,
        "reason": reason,
        "steps": steps,
    }
