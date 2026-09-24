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
    speed: float | None = None
    latitude: float | None = None
    longitude: float | None = None


class TamperingRequest(BaseModel):
    receiver_id: str = "B001"
    field: str = "speed"
    new_value: float = 180


class AttackRequest(BaseModel):
    receiver_id: str = "B001"
    target_id: str = "A001"


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
