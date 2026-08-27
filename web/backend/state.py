"""
Simulation state singleton wrapping existing V2V security modules.

Holds CA, vehicles, attacker, stats, and last-captured packet for attacks.
"""

import copy
import sys
from pathlib import Path
from typing import Any

# Add src/ to path so we import the existing implementation unchanged
SRC = Path(__file__).resolve().parents[2] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from attacks.attacker import Attacker  # noqa: E402
from ca.certificate_authority import CertificateAuthority  # noqa: E402
from protocol.messages import SAFETY_EVENTS, create_safety_message  # noqa: E402
from protocol.v2v_protocol import SecureVehicle, create_signed_packet  # noqa: E402
from security.hashing import hash_message_hex  # noqa: E402
from security.keys import generate_key_pair  # noqa: E402

from web.backend.event_log import attach_event_log_handler  # noqa: E402
from web.backend.serializers import (  # noqa: E402
    certificate_to_dict,
    packet_to_api,
)
from security.replay import ReplayProtector  # noqa: E402

from web.backend.verification_pipeline import verify_with_pipeline  # noqa: E402


def _replay_protector_snapshot(protector: ReplayProtector) -> ReplayProtector:
    """Copy replay state so pipeline preview does not mutate the receiver."""
    snap = ReplayProtector(timestamp_window=protector.timestamp_window)
    snap.last_sequence_numbers = copy.deepcopy(protector.last_sequence_numbers)
    return snap

# UI label → backend event mapping
EVENT_MAP = {
    "Emergency Braking": "EMERGENCY_BRAKING",
    "Collision Warning": "COLLISION_WARNING",
    "Speed Update": "SUDDEN_SLOWDOWN",
    "Position Update": "ROAD_HAZARD",
    "Accident Warning": "ACCIDENT_WARNING",
    "Road Hazard": "ROAD_HAZARD",
}


class SimulationState:
    """In-memory simulation wrapping existing src/ classes."""

    def __init__(self):
        self.events: list[dict[str, Any]] = []
        attach_event_log_handler(self.events)

        self.ca = CertificateAuthority()
        self.vehicles: dict[str, SecureVehicle] = {}
        self.attacker = Attacker(self.ca)

        self.stats = {
            "messages_sent": 0,
            "messages_verified": 0,
            "messages_rejected": 0,
            "attacks_detected": 0,
        }
        self.last_message: dict[str, Any] | None = None
        self.last_packet: dict | None = None
        self.last_pipeline: list | None = None

        self._register_default_vehicles()

    def _register_default_vehicles(self):
        configs = [
            ("A001", 80, (17.3850, 78.4867), "North"),
            ("B001", 75, (17.3860, 78.4870), "North"),
            ("C001", 60, (17.3870, 78.4880), "East"),
        ]
        for vid, speed, pos, direction in configs:
            key = generate_key_pair()
            cert = self.ca.register_vehicle(vid, key.public_key())
            self.vehicles[vid] = SecureVehicle(
                vid, speed, pos, direction, key, cert, self.ca
            )

    def get_status(self) -> dict:
        return {
            "active_vehicles": len(self.vehicles),
            "messages_sent": self.stats["messages_sent"],
            "messages_verified": self.stats["messages_verified"],
            "messages_rejected": self.stats["messages_rejected"],
            "attacks_detected": self.stats["attacks_detected"],
            "ca_status": "ACTIVE",
            "ca_name": self.ca.ca_name,
            "certificate_count": len(self.ca.registered_vehicles),
        }

    def get_vehicles(self) -> list[dict]:
        result = []
        for vid, vehicle in self.vehicles.items():
            cert_ok, _ = self.ca.verify_vehicle_certificate(vehicle.certificate)
            result.append(
                {
                    "vehicle_id": vid,
                    "speed": vehicle.speed,
                    "position": {
                        "latitude": vehicle.position[0],
                        "longitude": vehicle.position[1],
                    },
                    "direction": vehicle.direction,
                    "sequence_number": vehicle.sequence_number,
                    "certificate_status": "VALID" if cert_ok else "INVALID",
                    "connection_status": "SECURE",
                    "security_status": "SECURE" if cert_ok else "COMPROMISED",
                    "last_event": getattr(vehicle, "_last_event", None),
                }
            )
        return result

    def get_certificates(self) -> dict:
        ca_cert = self.ca.ca_certificate
        vehicle_certs = []
        for vid, cert in self.ca.registered_vehicles.items():
            vehicle_certs.append(certificate_to_dict(cert, vid))

        return {
            "ca": {
                "name": self.ca.ca_name,
                "status": "ACTIVE",
                "algorithm": "ECDSA SECP256R1",
                "certificate_count": len(self.ca.registered_vehicles),
                "issuer": ca_cert.issuer.rfc4514_string(),
                "not_valid_before": ca_cert.not_valid_before_utc.isoformat(),
                "not_valid_after": ca_cert.not_valid_after_utc.isoformat(),
                "public_key_abbrev": certificate_to_dict(ca_cert, "CA")[
                    "public_key_abbrev"
                ],
            },
            "vehicles": vehicle_certs,
        }

    def get_certificate_detail(self, vehicle_id: str) -> dict | None:
        cert = self.ca.registered_vehicles.get(vehicle_id)
        if not cert:
            return None
        ok, reason = self.ca.verify_vehicle_certificate(cert)
        detail = certificate_to_dict(cert, vehicle_id)
        detail["verification"] = {"valid": ok, "reason": reason}
        return detail

    def send_message(
        self,
        sender_id: str,
        receiver_id: str,
        event_label: str,
        speed: float | None = None,
        position: tuple | None = None,
    ) -> dict:
        sender = self.vehicles.get(sender_id)
        receiver = self.vehicles.get(receiver_id)
        if not sender or not receiver:
            raise ValueError(f"Unknown vehicle: {sender_id} or {receiver_id}")

        event = EVENT_MAP.get(event_label, event_label)
        if event not in SAFETY_EVENTS:
            raise ValueError(f"Invalid event: {event_label}")

        if speed is not None:
            sender.speed = speed
        if position is not None:
            sender.position = position

        packet = sender.send_message(event)
        sender._last_event = event  # noqa: SLF001

        from protocol.messages import serialize_message

        msg_bytes = serialize_message(packet["message"])
        hash_hex = hash_message_hex(msg_bytes)

        pipeline_pre = [
            {"name": "Message Created", "status": "success", "detail": str(event)},
            {"name": "SHA-256", "status": "success", "detail": hash_hex[:32] + "..."},
            {"name": "ECDSA Signature", "status": "success", "detail": "Signed with vehicle private key"},
            {"name": "Certificate Attached", "status": "success", "detail": f"Cert for {sender_id}"},
            {"name": "Transmission", "status": "processing", "detail": f"{sender_id} → {receiver_id}"},
        ]

        result = verify_with_pipeline(
            packet,
            self.ca,
            _replay_protector_snapshot(receiver.verifier.replay_protector),
        )

        # Single authoritative verification via existing implementation
        accepted, reason = receiver.receive_packet(packet)

        self.stats["messages_sent"] += 1
        if accepted:
            self.stats["messages_verified"] += 1
        else:
            self.stats["messages_rejected"] += 1

        self.last_packet = packet
        self.last_message = packet["message"]
        self.last_pipeline = pipeline_pre + result["steps"][5:]

        self.attacker.capture(packet)

        return {
            "accepted": accepted,
            "reason": reason,
            "pipeline": self.last_pipeline,
            "packet": packet_to_api(packet),
            "message_hash": hash_hex,
        }

    def attack_replay(self, receiver_id: str = "B001") -> dict:
        receiver = self.vehicles[receiver_id]
        if not self.attacker.captured_packets:
            raise ValueError("No captured packets — send a legitimate message first")

        original = self.attacker.captured_packets[-1]
        replay_packet = self.attacker.replay_attack(index=-1)

        pipeline = [
            {"name": "Attacker Captured Packet", "status": "warning", "detail": "Legitimate packet intercepted"},
            {"name": "Packet Retransmitted", "status": "warning", "detail": "Exact replay sent"},
        ]
        rp = receiver.verifier.replay_protector
        vr = verify_with_pipeline(replay_packet, self.ca, _replay_protector_snapshot(rp))
        pipeline.extend(vr["steps"][5:])
        accepted, reason = receiver.receive_packet(replay_packet)

        if not accepted:
            self.stats["attacks_detected"] += 1
            self.stats["messages_rejected"] += 1

        return {
            "attack": "replay",
            "accepted": accepted,
            "reason": reason,
            "pipeline": pipeline,
            "original_message": original["message"],
            "replayed_message": replay_packet["message"],
        }

    def attack_tampering(
        self,
        receiver_id: str = "B001",
        field: str = "speed",
        new_value: float = 180,
    ) -> dict:
        receiver = self.vehicles[receiver_id]
        if not self.attacker.captured_packets:
            raise ValueError("No captured packets — send a legitimate message first")

        original = self.attacker.captured_packets[-1]
        tampered = self.attacker.tampering_attack(index=-1, field=field, new_value=new_value)

        pipeline = [
            {"name": "Attacker Captured Packet", "status": "warning", "detail": "Legitimate packet intercepted"},
            {
                "name": "Message Modified",
                "status": "warning",
                "detail": f"{field}: {original['message'].get(field)} → {new_value}",
            },
        ]
        rp = receiver.verifier.replay_protector
        vr = verify_with_pipeline(tampered, self.ca, _replay_protector_snapshot(rp))
        pipeline.extend(vr["steps"][5:])
        accepted, reason = receiver.receive_packet(tampered)

        if not accepted:
            self.stats["attacks_detected"] += 1
            self.stats["messages_rejected"] += 1

        return {
            "attack": "tampering",
            "accepted": accepted,
            "reason": reason,
            "pipeline": pipeline,
            "original_message": original["message"],
            "modified_message": tampered["message"],
            "explanation": "Message was modified after signing — signature no longer matches.",
        }

    def attack_impersonation(
        self, target_id: str = "A001", receiver_id: str = "B001"
    ) -> dict:
        receiver = self.vehicles[receiver_id]
        packet = self.attacker.impersonation_attack(target_vehicle_id=target_id)

        pipeline = [
            {"name": "Attacker Forged Identity", "status": "warning", "detail": f"Claiming to be {target_id}"},
            {"name": "Fake Certificate Used", "status": "warning", "detail": "Self-signed, not from trusted CA"},
        ]
        rp = receiver.verifier.replay_protector
        vr = verify_with_pipeline(packet, self.ca, _replay_protector_snapshot(rp))
        pipeline.extend(vr["steps"][5:])
        accepted, reason = receiver.receive_packet(packet)

        if not accepted:
            self.stats["attacks_detected"] += 1
            self.stats["messages_rejected"] += 1

        return {
            "attack": "impersonation",
            "accepted": accepted,
            "reason": reason,
            "pipeline": pipeline,
            "forged_message": packet["message"],
        }

    def attack_fake_certificate(
        self, receiver_id: str = "B001"
    ) -> dict:
        receiver = self.vehicles[receiver_id]
        if not self.last_packet:
            raise ValueError("No legitimate packet — send a message first")

        packet = self.attacker.fake_certificate_attack(self.last_packet)

        pipeline = [
            {"name": "Attacker Swapped Certificate", "status": "warning", "detail": "EVIL001 cert on A001 message"},
        ]
        rp = receiver.verifier.replay_protector
        vr = verify_with_pipeline(packet, self.ca, _replay_protector_snapshot(rp))
        pipeline.extend(vr["steps"][5:])
        accepted, reason = receiver.receive_packet(packet)

        if not accepted:
            self.stats["attacks_detected"] += 1
            self.stats["messages_rejected"] += 1

        return {
            "attack": "fake_certificate",
            "accepted": accepted,
            "reason": reason,
            "pipeline": pipeline,
        }


# Module-level singleton
_state: SimulationState | None = None


def get_state() -> SimulationState:
    global _state
    if _state is None:
        _state = SimulationState()
    return _state
