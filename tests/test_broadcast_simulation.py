"""Coverage for deterministic multi-vehicle broadcast behavior."""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from web.backend.state import SimulationState
from protocol.messages import validate_message_structure
from web.backend.safety import evaluate_relevance, haversine_m


def test_broadcast_signs_once_and_independently_verifies_each_receiver():
    state = SimulationState()
    result = state.broadcast_message("A001", "ROAD_HAZARD")
    outcomes = {item["receiver_id"]: item for item in result["recipients"]}
    assert outcomes["A001"]["delivery_status"] == "sender_excluded"
    assert outcomes["B001"]["accepted"] is True
    assert outcomes["C001"]["accepted"] is True
    assert result["packet"]["message"]["vehicle_id"] == "A001"
    assert result["signature_count"] == 1


def test_each_receiver_has_independent_replay_state():
    state = SimulationState()
    packet = state.vehicles["A001"].send_message("ROAD_HAZARD")
    assert state.deliver_packet("B001", packet)["verification_status"] == "accepted"
    assert state.deliver_packet("B001", packet)["verification_status"] == "replayed"
    assert state.deliver_packet("C001", packet)["verification_status"] == "accepted"


def test_replay_state_update_is_atomic_for_concurrent_duplicate_delivery():
    state = SimulationState()
    packet = state.vehicles["A001"].send_message("ROAD_HAZARD")
    receiver = state.vehicles["B001"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: receiver.receive_packet(packet)[0], range(2)))
    assert sorted(outcomes) == [False, True]


def test_invalid_receiver_outcome_does_not_change_another_receivers_verification():
    state = SimulationState()
    packet = state.vehicles["A001"].send_message("ROAD_HAZARD")
    tampered = {**packet, "message": {**packet["message"], "speed": 390}}
    assert state.deliver_packet("B001", tampered)["verification_status"] == "invalid_signature"
    assert state.deliver_packet("C001", packet)["verification_status"] == "accepted"


def test_range_offline_and_missing_positions_are_explained():
    state = SimulationState()
    state.vehicles["B001"].position = (17.386, 78.487)
    state.vehicles["C001"].position = (18.0, 79.0)
    state.vehicles["C001"].status = "OFFLINE"
    result = state.broadcast_message("A001", "COLLISION_WARNING", range_m=100)
    outcomes = {item["receiver_id"]: item for item in result["recipients"]}
    assert outcomes["B001"]["delivery_status"] == "outside_range"
    assert outcomes["C001"]["delivery_status"] == "offline"
    assert outcomes["A001"]["delivery_status"] == "sender_excluded"
    state.vehicles["C001"].status = "ONLINE"
    state.vehicles["C001"].position = ("not-a-latitude", 79.0)
    result = state.broadcast_message("A001", "COLLISION_WARNING", range_m=100)
    outcomes = {item["receiver_id"]: item for item in result["recipients"]}
    assert outcomes["C001"]["delivery_status"] == "invalid_position"


def test_packet_loss_is_reproducible_for_a_seed():
    state = SimulationState()
    state.update_simulation_config(packet_loss_probability=0.5, random_seed=100)
    first = state.broadcast_message("A001", "EMERGENCY_BRAKING")
    first_statuses = [(x["receiver_id"], x["delivery_status"]) for x in first["recipients"]]
    state.update_simulation_config(random_seed=100)
    second = state.broadcast_message("A001", "EMERGENCY_BRAKING")
    second_statuses = [(x["receiver_id"], x["delivery_status"]) for x in second["recipients"]]
    assert first_statuses == second_statuses
    assert any(status == "dropped" for _, status in first_statuses)


def test_haversine_and_ttc_only_for_same_direction_closing_traffic():
    assert 100 < haversine_m((17.385, 78.4867), (17.386, 78.4867)) < 120
    hazard = {"event": "EMERGENCY_BRAKING", "position": {"latitude": 0, "longitude": 0}, "speed": 40, "direction": "East"}
    following = {"position": (0.0, -0.001), "speed": 60, "direction": "East"}
    result = evaluate_relevance(following, hazard, threshold_m=500)
    assert result["relevant"] is True
    assert result["ttc_seconds"] is not None
    away = {**following, "direction": "West"}
    away_result = evaluate_relevance(away, hazard, threshold_m=500)
    assert away_result["ttc_seconds"] is None
    assert away_result["relevant"] is False


def test_invalid_vehicle_state_and_malformed_messages_are_rejected():
    state = SimulationState()
    try:
        state.update_vehicle("B001", speed=500)
        assert False, "out-of-range speed must be rejected"
    except ValueError:
        pass
    packet = state.vehicles["A001"].send_message("COLLISION_WARNING")
    malformed = {**packet, "message": {**packet["message"], "position": {"latitude": 999, "longitude": 1}}}
    outcome = state.deliver_packet("B001", malformed)
    assert outcome["accepted"] is False
    assert outcome["verification_status"] == "invalid_schema"


def test_supported_events_and_security_attacks_keep_distinct_meanings():
    state = SimulationState()
    for event in ("EMERGENCY_BRAKING", "ROAD_HAZARD", "COLLISION_WARNING"):
        packet = state.vehicles["A001"].send_message(event)
        assert state.deliver_packet("B001", packet)["accepted"] is True
    stale = state.attack_stale("C001")
    assert stale["accepted"] is False
    assert "expired" in stale["reason"].lower()
    false_data = state.attack_false_data("C001")
    assert false_data["cryptographically_authenticated"] is True
    assert false_data["plausibility_suspicious"] is True
    assert false_data["safety"]["relevant"] is False


def test_schema_rejects_boolean_version_and_nonfinite_nested_event_data():
    packet_message = SimulationState().vehicles["A001"].create_message("ROAD_HAZARD")
    packet_message["schema_version"] = True
    assert validate_message_structure(packet_message)[0] is False
    packet_message["schema_version"] = 1
    packet_message["event_data"] = {"confidence": float("nan")}
    assert validate_message_structure(packet_message)[0] is False
