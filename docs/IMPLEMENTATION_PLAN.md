# Multi-Vehicle Broadcast Implementation Plan

## Baseline assessment (2026-10-22)

- Repository: existing Python V2V simulator (`src/`), FastAPI dashboard backend (`web/backend/`), React/TypeScript frontend (`web/frontend/`), and seven backend test modules.
- Existing sender flow: `SimulationState.send_message` chooses sender and receiver, sender builds and signs one packet with ECDSA/SHA-256, receiver runs `MessageVerifier` with a CA-issued X.509 certificate and its own `ReplayProtector`, then dashboard returns pipeline details.
- Existing protections: secp256r1 ECDSA, SHA-256 canonical JSON, X.509 CA and registration checks, sender/certificate identity binding, timestamp freshness, per-receiver per-sender sequence tracking, attack demonstrations, event log, performance page.
- Baseline backend: `./.venv/bin/pytest -q` — **31 passed**.
- Baseline frontend: `npm run build` — **passed**, existing chunk-size warning (625.90 kB JS); `npm run lint` — **passed with two warnings** in `Dashboard.tsx` and `EventLogPage.tsx` (`react(set-state-in-effect)`).
- Existing security gaps observed: message schema validation checks only basic field presence and position keys; replay check and update are not synchronized; frontend only exposes unicast; registry state has no online/offline or heading representation beyond text direction.

## Planned implementation

1. Extend the existing registry-backed simulation state and APIs for configurable range, packet loss/seed, vehicle online state, and vehicle kinematics; retain existing certificate and private-key objects.
2. Add a broadcast service that creates/signs one packet once, computes geographic distance eligibility once per recipient, simulates deterministic seeded packet loss, and independently runs the real verifier for each delivered receiver.
3. Strengthen input/schema checks, make replay state updates atomic, and add message ID/schema version/event data without replacing the existing canonical JSON signature path.
4. Add a distinct safety relevance evaluator for event distance and relative motion, including TTC only for same-direction closing traffic.
5. Expose broadcast, unicast compatibility, registry/configuration, movement, and per-recipient result APIs; update the communication UI to show broadcast controls and recipient outcomes.
6. Add focused automated coverage, a reproducible benchmark output, and architecture/security/demo documentation; keep progress tracking truthful at each stage.

## Affected files (anticipated)

- Backend/protocol: `src/protocol/messages.py`, `src/protocol/v2v_protocol.py`, `src/security/replay.py`, `src/security/verification.py`, `web/backend/state.py`, `web/backend/main.py`, and new `web/backend/broadcast.py`, `web/backend/safety.py`.
- Frontend: `web/frontend/src/types/index.ts`, `web/frontend/src/services/api.ts`, `web/frontend/src/pages/Communication.tsx`, and potentially `web/frontend/src/components/VehicleNetwork.tsx`.
- Tests: existing `tests/` plus new tests for broadcast, channel, schema and safety behavior.
- Documentation and results: `README.md`, new `docs/ARCHITECTURE.md`, `docs/SECURITY_ANALYSIS.md`, `docs/DEMO_GUIDE.md`, `docs/IMPLEMENTATION_PROGRESS.md`, and reproducible benchmark output under `results/`.

## Requirements checklist

- [ ] Preserve cryptography, certificates, identity checks, integrity, freshness, replay defense, attacks, logs, dashboard and unicast.
- [ ] One logical broadcast packet, signed once, delivered to multiple eligible receivers.
- [ ] Extend current registry with validated dynamic state, deterministic scenarios and movement updates.
- [ ] Configurable geographic range, sender/offline exclusion, reasons, and safe missing-position handling.
- [ ] Seeded packet loss and separate attempted/delivered/verified outcomes; no physical-radio claims.
- [ ] Versioned/validated safety events: emergency braking, road hazard, collision warning.
- [ ] Independent receiver security verification and replay state, with atomic replay updates and distinct statuses.
- [ ] Separate relevance/TTC evaluation using suitable relative-motion assumptions.
- [ ] Broadcast UI, receiver outcomes and visualization while preserving current design.
- [ ] Retain and validate replay, tampering, invalid identity/certificate, stale, false-data demonstrations.
- [ ] Automated backend/API/frontend checks for required behaviors.
- [ ] Reproducible multi-vehicle benchmark and clearly defined measurements.
- [ ] Update API/setup/security/architecture/demo documentation and environment guidance.
- [ ] Maintain progress checklist after each meaningful stage; do not overstate incomplete work.
- [ ] Final regression checks, diff/secrets review and report actual results/limitations.

## Execution notes

The simulation remains an in-process educational model. Broadcast reachability models geographic range and optional seeded packet loss; it does not implement DSRC, IEEE 802.11p, C-V2X, or physical radio transmission. Authentication proves signing-key possession and integrity, not that reported telemetry is truthful.
