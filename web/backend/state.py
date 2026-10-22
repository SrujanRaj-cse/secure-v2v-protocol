"""
Simulation state singleton wrapping existing V2V security modules.

Holds CA, vehicles, attacker, stats, and last-captured packet for attacks.
"""

import copy
import math
import sys
import time
from pathlib import Path
from typing import Any

# Add src/ to path so we import the existing implementation unchanged
SRC = Path(__file__).resolve().parents[2] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from attacks.attacker import Attacker  # noqa: E402
from ca.certificate_authority import CertificateAuthority  # noqa: E402
from protocol.messages import SAFETY_EVENTS, create_safety_message, serialize_message  # noqa: E402
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
from web.backend.broadcast import BroadcastService  # noqa: E402


def _replay_protector_snapshot(protector: ReplayProtector) -> ReplayProtector:
    """Copy replay state so pipeline preview does not mutate the receiver."""
    snap = ReplayProtector(timestamp_window=protector.timestamp_window)
    with protector._lock:
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

def _heading_degrees(direction: str) -> float | None:
    return {"North": 0.0, "Northeast": 45.0, "East": 90.0,
            "Southeast": 135.0, "South": 180.0, "Southwest": 225.0,
            "West": 270.0, "Northwest": 315.0}.get(direction)


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
        self.simulation_config = {
            "communication_range_m": 500.0,
            "packet_loss_probability": 0.0,
            "random_seed": 428,
            "relevance_threshold_m": 500.0,
        }

        self._register_default_vehicles()
        self.broadcast_service = BroadcastService(self.vehicles, self.simulation_config["random_seed"])

    def _register_default_vehicles(self):
        configs = [
            ("A001", 80, (17.3850, 78.4867), "North"),
            # B001 follows A001 from ~100 m behind and closes at 40 km/h.
            # The resulting initial TTC is about 9 seconds for the default event.
            ("B001", 120, (17.3841, 78.4867), "North"),
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
                    "status": getattr(vehicle, "status", "ONLINE"),
                    "heading_degrees": _heading_degrees(vehicle.direction),
                    "acceleration": getattr(vehicle, "acceleration", 0.0),
                    "security_status": "SECURE" if cert_ok else "COMPROMISED",
                    "last_event": getattr(vehicle, "_last_event", None),
                }
            )
        return result

    def update_vehicle(self, vehicle_id: str, *, position=None, speed=None,
                       direction=None, acceleration=None, status=None) -> dict:
        vehicle = self.vehicles.get(vehicle_id)
        if vehicle is None:
            raise ValueError(f"Unknown vehicle: {vehicle_id}")
        if position is not None:
            lat, lon = position
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError("Coordinates must be valid latitude/longitude")
            vehicle.position = (lat, lon)
        if speed is not None:
            if not 0 <= speed <= 400:
                raise ValueError("Speed must be between 0 and 400 km/h")
            vehicle.speed = speed
        if direction is not None:
            if direction not in ("North", "Northeast", "East", "Southeast", "South", "Southwest", "West", "Northwest"):
                raise ValueError("Direction must be a compass heading")
            vehicle.direction = direction
        if acceleration is not None:
            if not -20 <= acceleration <= 20:
                raise ValueError("Acceleration must be between -20 and 20 m/s²")
            vehicle.acceleration = acceleration
        if status is not None:
            vehicle.status = status
        return next(v for v in self.get_vehicles() if v["vehicle_id"] == vehicle_id)

    def register_vehicle(self, vehicle_id: str, speed: float, position: tuple[float, float],
                         direction: str) -> dict:
        if vehicle_id in self.vehicles:
            raise ValueError(f"Vehicle already exists: {vehicle_id}")
        if not vehicle_id or len(vehicle_id) > 10:
            raise ValueError("Vehicle ID must contain 1 to 10 characters")
        if not 0 <= speed <= 400 or not -90 <= position[0] <= 90 or not -180 <= position[1] <= 180:
            raise ValueError("Vehicle state is outside valid speed or coordinate bounds")
        if direction not in ("North", "Northeast", "East", "Southeast", "South", "Southwest", "West", "Northwest"):
            raise ValueError("Direction must be a compass heading")
        key = generate_key_pair()
        certificate = self.ca.register_vehicle(vehicle_id, key.public_key())
        self.vehicles[vehicle_id] = SecureVehicle(vehicle_id, speed, position, direction, key, certificate, self.ca)
        return next(v for v in self.get_vehicles() if v["vehicle_id"] == vehicle_id)

    def advance_simulation(self, seconds: float) -> list[dict]:
        if not 0 < seconds <= 60:
            raise ValueError("Simulation step must be greater than 0 and at most 60 seconds")
        for vehicle in self.vehicles.values():
            if vehicle.status != "ONLINE":
                continue
            initial_mps = vehicle.speed / 3.6
            final_mps = max(0.0, min(400 / 3.6, initial_mps + vehicle.acceleration * seconds))
            distance_m = (initial_mps + final_mps) * 0.5 * seconds
            heading = math.radians(_heading_degrees(vehicle.direction) or 0.0)
            lat, lon = vehicle.position
            lat += distance_m * math.cos(heading) / 111_320
            lon += distance_m * math.sin(heading) / (111_320 * max(0.01, math.cos(math.radians(lat))))
            vehicle.position = (max(-90, min(90, lat)), ((lon + 180) % 360) - 180)
            vehicle.speed = final_mps * 3.6
        return self.get_vehicles()

    def update_simulation_config(self, *, communication_range_m=None,
                                 packet_loss_probability=None, random_seed=None,
                                 relevance_threshold_m=None) -> dict:
        if communication_range_m is not None:
            if not 0 <= communication_range_m <= 100_000:
                raise ValueError("Communication range must be between 0 and 100000 meters")
            self.simulation_config["communication_range_m"] = communication_range_m
        if packet_loss_probability is not None:
            if not 0 <= packet_loss_probability <= 1:
                raise ValueError("Packet loss probability must be between 0 and 1")
            self.simulation_config["packet_loss_probability"] = packet_loss_probability
        if random_seed is not None:
            self.simulation_config["random_seed"] = random_seed
            self.broadcast_service.reset_seed(random_seed)
        if relevance_threshold_m is not None:
            if not 0 <= relevance_threshold_m <= 100_000:
                raise ValueError("Relevance threshold must be between 0 and 100000 meters")
            self.simulation_config["relevance_threshold_m"] = relevance_threshold_m
        return dict(self.simulation_config)

    def broadcast_message(self, sender_id: str, event_label: str,
                          speed: float | None = None, position: tuple | None = None,
                          range_m: float | None = None,
                          packet_loss_probability: float | None = None) -> dict:
        sender = self.vehicles.get(sender_id)
        if sender is None:
            raise ValueError(f"Unknown vehicle: {sender_id}")
        event = EVENT_MAP.get(event_label, event_label)
        if event not in SAFETY_EVENTS:
            raise ValueError(f"Invalid event: {event_label}")
        if speed is not None:
            if not 0 <= speed <= 400:
                raise ValueError("Speed must be between 0 and 400 km/h")
            sender.speed = speed
        if position is not None:
            self.update_vehicle(sender_id, position=position)
        if sender.status != "ONLINE":
            raise ValueError("Offline vehicles cannot broadcast")
        creation_started = time.perf_counter()
        message = sender.create_message(event)
        message_creation_ms = (time.perf_counter() - creation_started) * 1000
        signing_started = time.perf_counter()
        packet = create_signed_packet(message, sender.private_key, sender.certificate)
        signing_ms = (time.perf_counter() - signing_started) * 1000
        sender._last_event = event
        selected_range = range_m if range_m is not None else self.simulation_config["communication_range_m"]
        loss = packet_loss_probability if packet_loss_probability is not None else self.simulation_config["packet_loss_probability"]
        # Evaluate each recipient with the configured relevance threshold.
        outcomes = self.broadcast_service.broadcast(sender_id, packet, selected_range, loss)
        for outcome in outcomes:
            if outcome.get("safety") is not None:
                from web.backend.safety import evaluate_relevance
                receiver = self.vehicles[outcome["receiver_id"]]
                outcome["safety"] = evaluate_relevance(
                    {"position": receiver.position, "speed": receiver.speed, "direction": receiver.direction},
                    packet["message"], self.simulation_config["relevance_threshold_m"])
                outcome["safety_status"] = (
                    "warning_generated" if outcome["safety"]["warning"] else
                    "accepted_relevant" if outcome["safety"]["relevant"] else
                    "accepted_irrelevant")
        self.stats["messages_sent"] += 1
        self.stats["messages_verified"] += sum(item["accepted"] for item in outcomes)
        self.stats["messages_rejected"] += sum(item["delivery_status"] == "delivered" and not item["accepted"] for item in outcomes)
        self.last_packet = packet
        self.last_message = packet["message"]
        self.attacker.capture(packet)
        return {
            "message_id": packet["message"]["message_id"],
            "packet": packet_to_api(packet),
            "message_hash": hash_message_hex(serialize_message(packet["message"])),
            "signature_count": 1,
            "range_m": selected_range,
            "packet_loss_probability": loss,
            "seed": self.broadcast_service.seed,
            "performance_metrics": {
                "message_creation_ms": round(message_creation_ms, 4),
                "signing_ms": round(signing_ms, 4),
                **{key: round(value, 4) for key, value in self.broadcast_service.last_metrics.items()},
                "total_broadcast_ms": round(message_creation_ms + signing_ms + sum(self.broadcast_service.last_metrics.values()), 4),
            },
            "recipients": outcomes,
        }

    def deliver_packet(self, receiver_id: str, packet: dict) -> dict:
        return self.broadcast_service.deliver_packet(receiver_id, packet)

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
            "packet": packet_to_api(tampered),
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

    def attack_stale(self, receiver_id: str = "B001") -> dict:
        sender = self.vehicles.get("A001")
        receiver = self.vehicles.get(receiver_id)
        if sender is None or receiver is None:
            raise ValueError("Unknown sender or receiver")
        message = sender.create_message("EMERGENCY_BRAKING")
        message["timestamp"] = time.time() - 60.0
        packet = create_signed_packet(message, sender.private_key, sender.certificate)
        accepted, reason = receiver.receive_packet(packet)
        if not accepted:
            self.stats["attacks_detected"] += 1
            self.stats["messages_rejected"] += 1
        return {"attack": "stale", "accepted": accepted, "reason": reason,
                "pipeline": verify_with_pipeline(packet, self.ca,
                    _replay_protector_snapshot(receiver.verifier.replay_protector))["steps"],
                "original_message": message}

    def attack_false_data(self, receiver_id: str = "B001", speed: float = 300.0,
                          latitude: float = 0.0, longitude: float = 0.0) -> dict:
        sender = self.vehicles.get("A001")
        receiver = self.vehicles.get(receiver_id)
        if sender is None or receiver is None:
            raise ValueError("Unknown sender or receiver")
        if not 0 <= speed <= 400 or not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError("False-data values must remain within schema bounds")
        original_speed, original_position = sender.speed, sender.position
        try:
            sender.speed, sender.position = speed, (latitude, longitude)
            packet = sender.send_message("ROAD_HAZARD")
        finally:
            sender.speed, sender.position = original_speed, original_position
        pipeline = verify_with_pipeline(
            packet, self.ca,
            _replay_protector_snapshot(receiver.verifier.replay_protector),
        )["steps"]
        accepted, reason = receiver.receive_packet(packet)
        # Educational plausibility policy is advisory and does not alter authentication.
        plausibility_flags = []
        if speed > 180:
            plausibility_flags.append("Reported speed exceeds the demo plausibility threshold of 180 km/h")
        if abs(latitude) < 1 and abs(longitude) < 1:
            plausibility_flags.append("Reported position is far from the configured local scenario")
        from web.backend.safety import evaluate_relevance
        safety = evaluate_relevance(
            {"position": receiver.position, "speed": receiver.speed, "direction": receiver.direction},
            packet["message"], self.simulation_config["relevance_threshold_m"])
        return {"attack": "false_data", "accepted": accepted, "reason": reason,
                "cryptographically_authenticated": accepted,
                "plausibility_suspicious": bool(plausibility_flags),
                "plausibility_flags": plausibility_flags, "safety": safety,
                "pipeline": pipeline, "packet": packet_to_api(packet),
                "original_message": packet["message"],
                "explanation": "The signature authenticates the sender and signed bytes; it does not establish that reported telemetry is truthful."}


# Module-level singleton
_state: SimulationState | None = None


def get_state() -> SimulationState:
    global _state
    if _state is None:
        _state = SimulationState()
    return _state
