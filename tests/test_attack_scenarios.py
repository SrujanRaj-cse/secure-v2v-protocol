"""Regression coverage for attack demonstrations and the default safety scene."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from web.backend.state import SimulationState
from web.backend.safety import evaluate_relevance, haversine_m


def _accepted_stage(result, stage):
    steps = result.get("pipeline", result.get("steps", []))
    return next(step for step in steps if step["name"] == stage)


def test_tampering_keeps_schema_valid_and_fails_ecdsa_signature():
    state = SimulationState()
    state.broadcast_message("A001", "Emergency Braking")
    result = state.attack_tampering()
    assert result["accepted"] is False
    assert _accepted_stage(result, "Message Validation")["status"] == "success"
    assert _accepted_stage(result, "Signature Verification")["status"] == "failed"
    assert "signature" in result["reason"].lower()


def test_replay_attack_reaches_receiver_replay_protection():
    state = SimulationState()
    state.broadcast_message("A001", "Emergency Braking")
    result = state.attack_replay()
    assert result["accepted"] is False
    assert _accepted_stage(result, "Message Validation")["status"] == "success"
    assert _accepted_stage(result, "Signature Verification")["status"] == "success"
    assert _accepted_stage(result, "Replay Check")["status"] == "failed"
    assert "replay" in result["reason"].lower() or "sequence" in result["reason"].lower()


def test_invalid_schema_is_rejected_at_message_validation():
    state = SimulationState()
    packet = state.vehicles["A001"].send_message("EMERGENCY_BRAKING")
    packet["message"]["speed"] = "fast"
    from web.backend.verification_pipeline import verify_with_pipeline
    from web.backend.state import _replay_protector_snapshot
    result = verify_with_pipeline(packet, state.ca,
        _replay_protector_snapshot(state.vehicles["B001"].verifier.replay_protector))
    assert result["accepted"] is False
    assert _accepted_stage(result, "Message Validation")["status"] == "failed"


def test_untrusted_certificate_and_identity_mismatch_fail_at_distinct_stages():
    state = SimulationState()
    untrusted = state.attack_impersonation()
    assert untrusted["accepted"] is False
    assert _accepted_stage(untrusted, "Message Validation")["status"] == "success"
    assert _accepted_stage(untrusted, "Certificate Verification")["status"] == "failed"

    state.broadcast_message("A001", "Emergency Braking")
    mismatch = state.attack_fake_certificate()
    assert mismatch["accepted"] is False
    assert _accepted_stage(mismatch, "Certificate Verification")["status"] == "success"
    assert _accepted_stage(mismatch, "Identity Check")["status"] == "failed"
    assert "vehicle id mismatch" in mismatch["reason"].lower()


def test_stale_message_is_signed_then_rejected_by_freshness():
    state = SimulationState()
    result = state.attack_stale()
    assert result["accepted"] is False
    assert _accepted_stage(result, "Signature Verification")["status"] == "success"
    assert _accepted_stage(result, "Timestamp Check")["status"] == "failed"
    assert "expired" in result["reason"].lower()


def test_valid_sender_false_data_is_authenticated_and_flagged_separately():
    state = SimulationState()
    result = state.attack_false_data()
    assert result["accepted"] is True
    assert result["cryptographically_authenticated"] is True
    assert result["plausibility_suspicious"] is True
    assert any("180 km/h" in flag for flag in result["plausibility_flags"])


def test_default_emergency_braking_broadcast_warns_following_vehicle_only():
    state = SimulationState()
    result = state.broadcast_message("A001", "Emergency Braking")
    outcomes = {entry["receiver_id"]: entry for entry in result["recipients"]}
    b001 = outcomes["B001"]
    c001 = outcomes["C001"]
    assert b001["accepted"] is True
    assert b001["distance_m"] <= 500
    assert b001["safety"]["relevant"] is True
    assert b001["safety"]["relative_speed_mps"] > 0
    assert b001["safety"]["ttc_seconds"] <= 10
    assert b001["safety"]["warning"] is True
    assert c001["accepted"] is True
    assert c001["safety"]["relevant"] is False
    assert c001["safety"]["warning"] is False


def test_same_direction_nonclosing_vehicle_is_relevant_but_has_no_ttc_warning():
    event = {"event": "EMERGENCY_BRAKING", "position": {"latitude": 0, "longitude": 0},
             "speed": 80, "direction": "East"}
    receiver = {"position": (0, -0.001), "speed": 60, "direction": "East"}
    result = evaluate_relevance(receiver, event)
    assert result["relevant"] is True
    assert result["relative_speed_mps"] < 0
    assert result["ttc_seconds"] is None
    assert result["warning"] is False


def test_away_vehicle_has_no_warning_and_out_of_range_vehicle_is_irrelevant():
    event = {"event": "EMERGENCY_BRAKING", "position": {"latitude": 0, "longitude": 0},
             "speed": 80, "direction": "East"}
    away = {"position": (0, -0.001), "speed": 120, "direction": "West"}
    assert evaluate_relevance(away, event)["warning"] is False
    far = {"position": (0, -0.01), "speed": 120, "direction": "East"}
    far_result = evaluate_relevance(far, event, threshold_m=500)
    assert haversine_m(far["position"], (0, 0)) > 500
    assert far_result["relevant"] is False
    assert far_result["warning"] is False


def test_unavailable_ttc_does_not_create_emergency_braking_warning():
    event = {"event": "EMERGENCY_BRAKING", "position": {"latitude": 0, "longitude": 0},
             "speed": 80, "direction": "East"}
    invalid_ttc = {"position": (0, -0.001), "speed": float("nan"), "direction": "East"}
    result = evaluate_relevance(invalid_ttc, event)
    assert result["ttc_seconds"] is None
    assert result["warning"] is False
