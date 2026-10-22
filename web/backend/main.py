"""
FastAPI application — thin REST layer over existing V2V security code.
"""

import json
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure project root and src are importable
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for p in (str(ROOT), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

from web.backend.event_log import filter_events  # noqa: E402
from web.backend.state import get_state  # noqa: E402

app = FastAPI(
    title="Secure V2V Protocol API",
    description="REST API for the V2V security dashboard",
    version="1.0.0",
)

_cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
_extra = os.getenv("CORS_ORIGINS", "")
if _extra:
    _cors_origins.extend(o.strip() for o in _extra.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SendMessageRequest(BaseModel):
    sender_id: str = Field(..., pattern=r"^[A-Z]\d{3}$")
    receiver_id: str = Field(..., pattern=r"^[A-Z]\d{3}$")
    event: str = "Emergency Braking"
    speed: float | None = Field(None, ge=0, le=400)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)


class BroadcastRequest(BaseModel):
    sender_id: str = Field(..., pattern=r"^[A-Z]\d{3}$")
    event: str = "Emergency Braking"
    speed: float | None = Field(None, ge=0, le=400)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    range_m: float | None = Field(None, ge=0, le=100000)
    packet_loss_probability: float | None = Field(None, ge=0, le=1)


class SimulationConfigRequest(BaseModel):
    communication_range_m: float | None = Field(None, ge=0, le=100000)
    packet_loss_probability: float | None = Field(None, ge=0, le=1)
    random_seed: int | None = Field(None, ge=0, le=2147483647)
    relevance_threshold_m: float | None = Field(None, ge=0, le=100000)


class VehicleUpdateRequest(BaseModel):
    speed: float | None = Field(None, ge=0, le=400)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    direction: str | None = None
    acceleration: float | None = Field(None, ge=-20, le=20)
    status: str | None = Field(None, pattern=r"^(ONLINE|OFFLINE)$")


class VehicleCreateRequest(BaseModel):
    vehicle_id: str = Field(..., pattern=r"^[A-Z][A-Z0-9]{2,9}$")
    speed: float = Field(..., ge=0, le=400)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    direction: str = "North"


class SimulationStepRequest(BaseModel):
    seconds: float = Field(1.0, gt=0, le=60)


class TamperingRequest(BaseModel):
    receiver_id: str = "B001"
    field: str = "speed"
    new_value: float = 180


class AttackRequest(BaseModel):
    receiver_id: str = "B001"
    target_id: str = "A001"


class FalseDataRequest(BaseModel):
    receiver_id: str = "B001"
    speed: float = Field(300, ge=0, le=400)
    latitude: float = Field(0, ge=-90, le=90)
    longitude: float = Field(0, ge=-180, le=180)


@app.get("/api/status")
def api_status():
    return get_state().get_status()


@app.get("/api/vehicles")
def api_vehicles():
    return get_state().get_vehicles()


@app.get("/api/certificates")
def api_certificates():
    return get_state().get_certificates()


@app.get("/api/certificates/{vehicle_id}")
def api_certificate_detail(vehicle_id: str):
    detail = get_state().get_certificate_detail(vehicle_id)
    if not detail:
        raise HTTPException(404, f"Certificate not found for {vehicle_id}")
    return detail


@app.post("/api/message/send")
def api_send_message(body: SendMessageRequest):
    state = get_state()
    position = None
    if body.latitude is not None and body.longitude is not None:
        position = (body.latitude, body.longitude)
    elif body.latitude is not None or body.longitude is not None:
        raise HTTPException(422, "Latitude and longitude must be supplied together")
    try:
        return state.send_message(
            body.sender_id,
            body.receiver_id,
            body.event,
            speed=body.speed,
            position=position,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/message/broadcast")
def api_broadcast(body: BroadcastRequest):
    position = None
    if body.latitude is not None and body.longitude is not None:
        position = (body.latitude, body.longitude)
    elif body.latitude is not None or body.longitude is not None:
        raise HTTPException(422, "Latitude and longitude must be supplied together")
    try:
        return get_state().broadcast_message(
            body.sender_id, body.event, body.speed, position,
            body.range_m, body.packet_loss_probability)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.get("/api/simulation/config")
def api_simulation_config():
    return dict(get_state().simulation_config)


@app.put("/api/simulation/config")
def api_update_simulation_config(body: SimulationConfigRequest):
    try:
        return get_state().update_simulation_config(**body.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.patch("/api/vehicles/{vehicle_id}")
def api_update_vehicle(vehicle_id: str, body: VehicleUpdateRequest):
    data = body.model_dump(exclude_unset=True)
    position = None
    if "latitude" in data or "longitude" in data:
        if "latitude" not in data or "longitude" not in data:
            raise HTTPException(422, "Latitude and longitude must be supplied together")
        position = (data.pop("latitude"), data.pop("longitude"))
    try:
        return get_state().update_vehicle(vehicle_id, position=position, **data)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/vehicles")
def api_create_vehicle(body: VehicleCreateRequest):
    try:
        return get_state().register_vehicle(body.vehicle_id, body.speed,
            (body.latitude, body.longitude), body.direction)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/simulation/step")
def api_simulation_step(body: SimulationStepRequest):
    try:
        return get_state().advance_simulation(body.seconds)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/attack/replay")
def api_attack_replay(body: AttackRequest):
    try:
        return get_state().attack_replay(body.receiver_id)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/attack/tampering")
def api_attack_tampering(body: TamperingRequest):
    try:
        return get_state().attack_tampering(
            body.receiver_id, body.field, body.new_value
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/attack/impersonation")
def api_attack_impersonation(body: AttackRequest):
    return get_state().attack_impersonation(body.target_id, body.receiver_id)


@app.post("/api/attack/fake-certificate")
def api_attack_fake_certificate(body: AttackRequest):
    try:
        return get_state().attack_fake_certificate(body.receiver_id)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/attack/stale")
def api_attack_stale(body: AttackRequest):
    try:
        return get_state().attack_stale(body.receiver_id)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/attack/false-data")
def api_attack_false_data(body: FalseDataRequest):
    try:
        return get_state().attack_false_data(body.receiver_id, body.speed, body.latitude, body.longitude)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.get("/api/events")
def api_events(
    severity: str | None = Query(None),
    vehicle_id: str | None = Query(None),
    search: str | None = Query(None),
):
    state = get_state()
    return filter_events(
        state.events, severity=severity, vehicle_id=vehicle_id, search=search
    )


@app.delete("/api/events")
def api_clear_events():
    state = get_state()
    state.events.clear()
    return {"cleared": True}


@app.get("/api/performance")
def api_performance():
    path = ROOT / "results" / "performance.json"
    if not path.exists():
        raise HTTPException(404, "No performance data — run benchmark first")
    with open(path) as f:
        return json.load(f)


@app.post("/api/performance/run")
def api_run_performance(iterations: int = Query(100, ge=10, le=1000)):
    from main import run_performance_experiment

    return run_performance_experiment(iterations=iterations)


@app.get("/api/architecture")
def api_architecture():
    return {
        "components": [
            {
                "id": "ca",
                "label": "Certificate Authority",
                "description": "Trust anchor; registers vehicles and issues X.509 certificates.",
            },
            {
                "id": "certificates",
                "label": "Vehicle Certificates",
                "description": "CA-signed credentials binding vehicle ID to public key.",
            },
            {
                "id": "vehicle_a",
                "label": "Vehicle A",
                "description": "Sender; holds private key, signs messages with ECDSA.",
            },
            {
                "id": "vehicle_b",
                "label": "Vehicle B",
                "description": "Receiver; verifies certificate, signature, replay protection.",
            },
            {
                "id": "v2v",
                "label": "V2V Message",
                "description": "Signed safety packet: message + signature + certificate.",
            },
            {
                "id": "cert_verify",
                "label": "Certificate Verification",
                "description": "Verify CA signature, expiry, and registration.",
            },
            {
                "id": "sig_verify",
                "label": "Signature Verification",
                "description": "SHA-256 hash + ECDSA verify with sender public key.",
            },
            {
                "id": "replay",
                "label": "Replay Protection",
                "description": "Timestamp freshness + monotonic sequence numbers.",
            },
            {
                "id": "result",
                "label": "Message Result",
                "description": "ACCEPTED only if every check passes; otherwise REJECTED with reason.",
            },
        ],
        "flow": [
            "ca", "certificates", "vehicle_a", "v2v", "vehicle_b",
            "cert_verify", "sig_verify", "replay", "result",
        ],
    }
