"""In-process geographic broadcast and seeded packet-loss model."""

import random
import math
import time
from typing import Any

from protocol.v2v_protocol import SecureVehicle
from web.backend.safety import evaluate_relevance, haversine_m

GATE_NAMES = ("Schema", "Certificate", "Signature", "Freshness", "Replay", "Relevance")


def _verification_gates(status: str, reason: str, relevance: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Map the authoritative receiver result/reason to its ordered validation stage."""
    failure_gate = {
        "invalid_schema": "Schema",
        "invalid_certificate": "Certificate",
        "invalid_signature": "Signature",
        "stale": "Freshness",
        "replayed": "Replay",
    }.get(status)
    security_gates = GATE_NAMES[:-1]
    if status == "accepted":
        gates = [{"name": name, "status": "passed", "reason": "Passed receiver verification."}
                 for name in security_gates]
    elif failure_gate:
        failure_index = security_gates.index(failure_gate)
        gates = []
        for index, name in enumerate(security_gates):
            if index < failure_index:
                gates.append({"name": name, "status": "passed", "reason": "Passed before the rejection stage."})
            elif index == failure_index:
                gates.append({"name": name, "status": "failed", "reason": reason})
            else:
                gates.append({"name": name, "status": "skipped", "reason": "Not run after an earlier rejection."})
    else:
        gates = [{"name": name, "status": "not_reported", "reason": reason or None}
                 for name in security_gates]

    if relevance is None:
        gates.append({"name": "Relevance", "status": "not_reported",
                      "reason": "Safety evaluation was not run."})
    else:
        safety_status = ("warning" if relevance["warning"] else
                         "relevant" if relevance["relevant"] else "not_relevant")
        gates.append({"name": "Relevance", "status": safety_status,
                      "reason": relevance["reason"]})
    return gates


def _verification_status(accepted: bool, reason: str) -> str:
    lowered = reason.lower()
    if accepted:
        return "accepted"
    if "timestamp" in lowered or "expired" in lowered:
        return "stale"
    if "replay" in lowered or "sequence" in lowered:
        return "replayed"
    if "certificate" in lowered or "vehicle id mismatch" in lowered or "unknown vehicle" in lowered:
        return "invalid_certificate"
    if "signature" in lowered:
        return "invalid_signature"
    if ("structure" in lowered or "missing" in lowered or "invalid" in lowered
            or "must " in lowered or "coordinate" in lowered or "position" in lowered
            or "speed must" in lowered or "schema" in lowered):
        return "invalid_schema"
    return "rejected"


class BroadcastService:
    """Select eligible vehicles and independently verify one signed packet per receiver."""

    def __init__(self, registry: dict[str, SecureVehicle], seed: int = 428):
        self.registry = registry
        self.seed = seed
        self.rng = random.Random(seed)

    def reset_seed(self, seed: int) -> None:
        self.seed = seed
        self.rng = random.Random(seed)

    def deliver_packet(self, receiver_id: str, packet: dict) -> dict[str, Any]:
        receiver = self.registry.get(receiver_id)
        if receiver is None:
            raise ValueError(f"Unknown vehicle: {receiver_id}")
        started = time.perf_counter()
        accepted, reason = receiver.receive_packet(packet)
        verification_ms = (time.perf_counter() - started) * 1000
        relevance = evaluate_relevance(
            {"position": receiver.position, "speed": receiver.speed,
             "direction": receiver.direction}, packet.get("message", {})
        ) if accepted else None
        status = _verification_status(accepted, reason)
        return {
            "receiver_id": receiver_id,
            "delivery_status": "delivered",
            "verification_status": status,
            "safety_status": "warning_generated" if relevance and relevance["warning"] else
                            "accepted_relevant" if relevance and relevance["relevant"] else
                            "accepted_irrelevant" if relevance else "not_evaluated",
            "accepted": accepted,
            "rejection_reason": None if accepted else reason,
            "message_id": packet.get("message", {}).get("message_id"),
            "processing_ms": round((time.perf_counter() - started) * 1000, 4),
            "verification_ms": round(verification_ms, 4),
            "safety_evaluation_performed": relevance is not None,
            "safety": relevance,
            "verification_gates": _verification_gates(status, reason, relevance),
        }

    def broadcast(self, sender_id: str, packet: dict, range_m: float,
                  packet_loss_probability: float = 0.0) -> list[dict[str, Any]]:
        if not 0 <= range_m <= 100_000:
            raise ValueError("Communication range must be between 0 and 100000 meters")
        if not 0 <= packet_loss_probability <= 1:
            raise ValueError("Packet loss probability must be between 0 and 1")
        sender = self.registry.get(sender_id)
        if sender is None:
            raise ValueError(f"Unknown vehicle: {sender_id}")
        outcomes: list[dict[str, Any]] = []
        eligible: list[tuple[dict[str, Any], str]] = []
        eligibility_started = time.perf_counter()
        for receiver_id, receiver in self.registry.items():
            outcome: dict[str, Any] = {
                "receiver_id": receiver_id,
                "message_id": packet.get("message", {}).get("message_id"),
                "distance_m": None,
                "delivery_status": "not_attempted",
                "attempted_delivery": False,
                "verification_status": "not_attempted",
                "safety_status": "not_evaluated",
                "accepted": False,
                "rejection_reason": None,
                "processing_ms": 0.0,
                "safety_evaluation_performed": False,
                "safety": None,
                "verification_gates": _verification_gates("not_reported", "", None),
            }
            if receiver_id == sender_id:
                outcome.update(delivery_status="sender_excluded", rejection_reason="Sender is not a recipient")
            elif getattr(receiver, "status", "ONLINE") != "ONLINE":
                outcome.update(delivery_status="offline", rejection_reason="Vehicle is offline")
            elif not _valid_position(receiver.position):
                outcome.update(delivery_status="invalid_position", rejection_reason="Receiver position is missing or invalid")
            elif not _valid_position(sender.position):
                outcome.update(delivery_status="invalid_position", rejection_reason="Sender position is missing or invalid")
            else:
                distance = haversine_m(sender.position, receiver.position)
                outcome["distance_m"] = round(distance, 2)
                if distance > range_m:
                    outcome.update(delivery_status="outside_range", rejection_reason=f"{distance:.1f} m exceeds {range_m:.1f} m range")
                else:
                    outcome["delivery_status"] = "eligible"
                    eligible.append((outcome, receiver_id))
            outcomes.append(outcome)
        self.last_metrics = {"eligibility_ms": (time.perf_counter() - eligibility_started) * 1000}
        delivery_started = time.perf_counter()
        for outcome, receiver_id in eligible:
            if self.rng.random() < packet_loss_probability:
                outcome.update(delivery_status="dropped", attempted_delivery=True,
                               rejection_reason="Packet dropped by seeded channel model")
            else:
                outcome.update(self.deliver_packet(receiver_id, packet))
                outcome["attempted_delivery"] = True
        self.last_metrics["delivery_processing_ms"] = (time.perf_counter() - delivery_started) * 1000
        return outcomes


def _valid_position(position: Any) -> bool:
    try:
        lat, lon = position
        if any(not isinstance(value, (int, float)) or isinstance(value, bool)
               or not math.isfinite(value) for value in (lat, lon)):
            return False
        return -90 <= lat <= 90 and -180 <= lon <= 180
    except (TypeError, ValueError):
        return False
