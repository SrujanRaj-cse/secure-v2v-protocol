"""API validation coverage without requiring the optional ASGI HTTP test client."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from pydantic import ValidationError
from web.backend import state as state_module
from web.backend.main import (
    BroadcastRequest,
    SimulationConfigRequest,
    SimulationStepRequest,
    VehicleCreateRequest,
    VehicleUpdateRequest,
    api_broadcast,
    api_send_message,
    api_create_vehicle,
    api_simulation_config,
    api_update_simulation_config,
    api_update_vehicle,
    api_simulation_step,
    app,
)


def setup_function():
    state_module._state = None


def test_broadcast_api_returns_per_receiver_outcomes():
    result = api_broadcast(BroadcastRequest(sender_id="A001", event="Collision Warning"))
    assert result["signature_count"] == 1
    assert len(result["recipients"]) == 3
    assert result["recipients"][0]["delivery_status"] == "sender_excluded"
    b001 = next(item for item in result["recipients"] if item["receiver_id"] == "B001")
    assert [gate["name"] for gate in b001["verification_gates"]] == [
        "Schema", "Certificate", "Signature", "Freshness", "Replay", "Relevance"
    ]
    assert all(gate["status"] != "not_reported" for gate in b001["verification_gates"])


def test_broadcast_undelivered_recipient_gates_are_not_reported():
    state = state_module.get_state()
    state.vehicles["B001"].position = (17.39, 78.4867)
    result = api_broadcast(BroadcastRequest(sender_id="A001", event="Collision Warning", range_m=100))
    b001 = next(item for item in result["recipients"] if item["receiver_id"] == "B001")
    assert b001["delivery_status"] == "outside_range"
    assert all(gate["status"] == "not_reported" for gate in b001["verification_gates"])


def test_attack_results_include_actual_tampered_and_false_data_packets_and_pipeline():
    state = state_module.get_state()
    state.broadcast_message("A001", "Emergency Braking")
    tampered = state.attack_tampering()
    assert tampered["packet"]["message"] == tampered["modified_message"]
    assert next(step for step in tampered["pipeline"] if step["name"] == "Signature Verification")["status"] == "failed"

    false_data = state.attack_false_data()
    assert false_data["packet"]["message"] == false_data["original_message"]
    assert false_data["accepted"] is True
    assert next(step for step in false_data["pipeline"] if step["name"] == "Signature Verification")["status"] == "success"


def test_existing_unicast_api_remains_available():
    from web.backend.main import SendMessageRequest
    result = api_send_message(SendMessageRequest(sender_id="A001", receiver_id="B001", event="Collision Warning"))
    assert result["accepted"] is True
    assert result["packet"]["message"]["vehicle_id"] == "A001"


def test_simulation_config_and_vehicle_update_routes():
    updated = api_update_simulation_config(SimulationConfigRequest(communication_range_m=200, random_seed=22))
    assert updated["communication_range_m"] == 200
    vehicle = api_update_vehicle("B001", VehicleUpdateRequest(latitude=17.3851, longitude=78.4868, status="OFFLINE"))
    assert vehicle["status"] == "OFFLINE"
    assert api_simulation_config()["random_seed"] == 22


def test_registry_create_and_motion_routes():
    vehicle = api_create_vehicle(VehicleCreateRequest(
        vehicle_id="D004", speed=36, latitude=17.385, longitude=78.4867, direction="East"))
    assert vehicle["vehicle_id"] == "D004"
    before = vehicle["position"]["longitude"]
    api_simulation_step(SimulationStepRequest(seconds=1))
    after = next(v for v in state_module.get_state().get_vehicles() if v["vehicle_id"] == "D004")["position"]["longitude"]
    assert after > before


def test_invalid_ranges_coordinates_and_status_are_rejected():
    with pytest.raises(ValidationError):
        SimulationConfigRequest(communication_range_m=-5)
    with pytest.raises(ValidationError):
        VehicleUpdateRequest(latitude=91)
    with pytest.raises(ValidationError):
        VehicleUpdateRequest(status="BROKEN")


def test_openapi_lists_new_simulation_endpoints():
    paths = app.openapi()["paths"]
    expected_methods = {
        "/api/message/send": "post",
        "/api/message/broadcast": "post",
        "/api/simulation/config": "put",
        "/api/performance": "get",
        "/api/performance/run": "post",
    }
    for route, method in expected_methods.items():
        assert method in paths[route]
    assert "BroadcastRequest" in str(paths["/api/message/broadcast"]["post"])
    assert "SimulationConfigRequest" in str(paths["/api/simulation/config"]["put"])


def test_performance_api_runs_real_benchmark_and_roundtrips_saved_schema(tmp_path, monkeypatch):
    import importlib
    import web.backend.main as api_module

    fake_project = tmp_path / "benchmark-project"
    source_dir = fake_project / "src"
    source_dir.mkdir(parents=True)
    source_file = source_dir / "main.py"
    source_file.touch()

    benchmark_module = importlib.import_module("main")
    monkeypatch.setattr(benchmark_module, "__file__", str(source_file))
    monkeypatch.setattr(api_module, "ROOT", fake_project)
    result = api_module.api_run_performance(iterations=10)
    assert set(result) == {
        "iterations", "timestamp_validity_seconds", "avg_message_creation_ms",
        "avg_signing_ms", "avg_verification_ms", "avg_replay_detection_ms",
        "avg_tamper_detection_ms",
    }
    assert result["iterations"] == 10
    assert api_module.api_performance() == result
