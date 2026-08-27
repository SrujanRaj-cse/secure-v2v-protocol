# Web Dashboard Architecture — Secure V2V Protocol

## 1. Existing Backend Architecture

```
secure-v2v-protocol/
├── src/
│   ├── main.py                 # CLI demo entry point (unchanged)
│   ├── config.py               # TIMESTAMP_VALIDITY_SECONDS, ECDSA_CURVE, LOG_LEVEL
│   ├── ca/certificate_authority.py
│   ├── vehicles/vehicle.py     # Pre-crypto vehicle (Phase 1–3 tests)
│   ├── protocol/
│   │   ├── messages.py         # Message format, canonical serialization
│   │   └── v2v_protocol.py     # SecureVehicle, create_signed_packet
│   ├── security/
│   │   ├── keys.py             # ECDSA key generation (SECP256R1)
│   │   ├── hashing.py          # SHA-256 hash_message()
│   │   ├── signatures.py       # sign_message / verify_signature
│   │   ├── certificates.py     # X.509 create/verify/issue
│   │   ├── verification.py     # MessageVerifier.verify()
│   │   └── replay.py           # ReplayProtector.check()
│   ├── attacks/attacker.py     # Replay, tampering, impersonation, fake cert
│   └── utils/logger.py
├── tests/                      # 31 pytest tests
└── results/performance.json    # Benchmark output
```

The CLI (`src/main.py`) creates a CA, registers vehicles A001/B001, runs attack demos, and writes performance JSON. All cryptography lives in `src/` and is **not modified** by the web layer.

---

## 2. Existing Security Modules

| Module | Key Functions / Classes | Role |
|--------|-------------------------|------|
| `keys.py` | `generate_key_pair()` | ECDSA SECP256R1 key pairs |
| `hashing.py` | `hash_message()`, `hash_message_hex()` | Explicit SHA-256 step |
| `signatures.py` | `sign_message()`, `verify_signature()` | ECDSA sign/verify over hash |
| `certificates.py` | `issue_vehicle_certificate()`, `verify_certificate_against_ca()` | X.509 PKI |
| `verification.py` | `MessageVerifier.verify(packet)` | Full 9-step pipeline |
| `replay.py` | `ReplayProtector.check(message)` | Timestamp + sequence |
| `attacker.py` | `Attacker.replay/tampering/impersonation/fake_certificate_attack()` | Attack simulation |
| `v2v_protocol.py` | `SecureVehicle.send_message()`, `receive_packet()` | High-level V2V API |

---

## 3. Existing Entry Points

| Entry | Command | Purpose |
|-------|---------|---------|
| CLI demo | `PYTHONPATH=src python src/main.py` | Full 7-phase security demo + benchmark |
| Tests | `.venv/bin/python -m pytest tests/ -v` | 31 automated tests |

---

## 4. Existing Attack Simulations

All implemented in `src/attacks/attacker.py`:

1. **Replay** — `capture()` + `replay_attack()` → rejected by sequence/timestamp
2. **Tampering** — `tampering_attack(field, new_value)` → rejected by signature
3. **Impersonation** — `impersonation_attack(target_vehicle_id)` → rejected by CA check
4. **Fake certificate** — `fake_certificate_attack(legitimate_packet)` → rejected by ID mismatch

---

## 5. Existing Performance Benchmark

`run_performance_experiment()` in `src/main.py` measures:

- Message creation, signing, verification (100 iterations)
- Replay detection, tamper detection
- Saves to `results/performance.json`

The web API reads this file and can trigger a fresh benchmark via the same function.

---

## 6. Functions Reused Directly (No Changes)

- `SecureVehicle.send_message()` / `receive_packet()`
- `create_signed_packet()` / `create_safety_message()`
- `MessageVerifier.verify()`
- `Attacker.*` attack methods
- `CertificateAuthority.register_vehicle()` / `verify_vehicle_certificate()`
- `hash_message()`, `sign_message()`, `verify_signature()`
- `run_performance_experiment()` from `main.py`

---

## 7. Functions Needing API Wrappers

| Wrapper Need | Reason |
|--------------|--------|
| `SimulationState` singleton | Persist CA, vehicles, attacker across HTTP requests |
| `verify_with_pipeline()` | Return per-step status for UI pipeline visualization |
| `packet_to_api()` / `packet_from_api()` | Base64-encode `signature` and `certificate_pem` for JSON |
| `certificate_to_dict()` | Expose public cert fields (never private keys) |
| `EventLogHandler` | Capture real log lines for the event log page |
| Stats counters | Track messages sent/verified/rejected/attacks for dashboard |

These wrappers live in `web/backend/` only.

---

## 8. Proposed Frontend / Backend Architecture

```
┌─────────────────────────────────────────────────────────┐
│  React + Vite + TypeScript + Tailwind (web/frontend)   │
│  Pages: Dashboard, V2V, CA, Attacks, Logs, Perf, Arch │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP (REST JSON, polling 2s)
┌────────────────────────▼────────────────────────────────┐
│  FastAPI (web/backend) — thin API layer only              │
│  Routes → SimulationService → existing src/ modules       │
└────────────────────────┬────────────────────────────────┘
                         │ import (sys.path → src/)
┌────────────────────────▼────────────────────────────────┐
│  Existing src/ — UNCHANGED cryptographic implementation   │
└─────────────────────────────────────────────────────────┘
```

CLI (`src/main.py`) runs independently; web server is additive.

---

## 9. API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | Dashboard summary stats |
| GET | `/api/vehicles` | All vehicles with cert/security status |
| GET | `/api/certificates` | CA info + all vehicle certificates |
| GET | `/api/certificates/{vehicle_id}` | Single certificate detail |
| POST | `/api/message/send` | Send signed message, return pipeline + result |
| POST | `/api/attack/replay` | Launch real replay attack |
| POST | `/api/attack/tampering` | Launch real tampering attack |
| POST | `/api/attack/impersonation` | Launch real impersonation attack |
| POST | `/api/attack/fake-certificate` | Launch fake certificate attack |
| GET | `/api/events` | Real event log (filterable) |
| DELETE | `/api/events` | Clear event log |
| GET | `/api/performance` | Read `results/performance.json` |
| POST | `/api/performance/run` | Run benchmark, update JSON |
| GET | `/api/architecture` | Architecture metadata for interactive page |

---

## 10. Frontend ↔ Backend Communication

1. Frontend dev server (`vite`, port 5173) proxies `/api/*` → FastAPI (port 8000).
2. Dashboard polls `/api/status` and `/api/events` every 2 seconds.
3. Message send and attacks are POST requests; responses include real pipeline steps and rejection reasons from `MessageVerifier`.
4. Performance page loads `/api/performance`; optional "Run Benchmark" calls POST `/api/performance/run`.
5. No WebSockets — polling keeps the stack simple for viva explanation.

**Security:** Private keys never leave the backend and are never included in API responses. Only public certificate data and abbreviated public key fingerprints are exposed.
