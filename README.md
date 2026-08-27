# Design a Secure Protocol for Vehicular-to-Vehicular (V2V) Communication

**Course:** CS428 — Design of Secure Protocol  
**Type:** Educational security protocol simulator (Python)

---

## 1. Project Objective

Build a complete working simulation of secure V2V communication demonstrating vehicle registration, cryptographic authentication, digital signatures, certificate validation, replay protection, attack resistance, and basic performance measurement — all runnable on a normal Ubuntu laptop.

---

## 2. Problem Statement

Connected vehicles exchange safety-critical messages (emergency braking, road hazards, collision warnings). Without security, an attacker on the wireless channel can replay old messages, tamper with content, or impersonate legitimate vehicles. This project implements and demonstrates defenses against those threats.

---

## 3. Course Requirements

### A. Entities Involved

| Entity | Role | Implementation |
|--------|------|----------------|
| **Certificate Authority (CA)** | Trust anchor; registers vehicles and issues X.509 certificates | `src/ca/certificate_authority.py` |
| **Vehicle A (A001)** | Sender of signed safety messages | `SecureVehicle` in `src/protocol/v2v_protocol.py` |
| **Vehicle B (B001)** | Receiver; runs full verification pipeline | `SecureVehicle` + `MessageVerifier` |
| **Attacker** | Intercepts packets; attempts replay, tampering, impersonation | `src/attacks/attacker.py` |

The CA establishes trust during registration but is **not** in the path of every V2V message.

### B. Authentication Parameters

| Parameter | Purpose |
|-----------|---------|
| **Vehicle ID** | Uniquely identifies the sender in messages and certificates |
| **Public/private key pair** | Private key signs messages; public key (in certificate) verifies signatures |
| **Digital certificate** | CA-signed binding of vehicle ID → public key |
| **Digital signature** | Proves the message was created by the holder of the private key |

### C. Security Services

| Service | Provided? | Mechanism |
|---------|-----------|-----------|
| **Authentication** | Yes | ECDSA signature + CA-issued certificate |
| **Integrity** | Yes | SHA-256 hash + ECDSA signature over canonical bytes |
| **Replay protection** | Yes | Timestamp window (5 s) + monotonic sequence numbers |
| **Authorization** | Yes | Certificate must be CA-signed and registered |
| **Non-repudiation** | Simulated | Only private key holder can produce valid signatures |
| **Confidentiality** | **Optional — not implemented** | Safety messages are broadcast; authentication and integrity are the priority. Encryption could be added later (ECIES) but is intentionally omitted so the core protocol remains easy to study. |

### D. Attack Model

Three required attacks plus a fake-certificate variant:

1. **Replay** — resend captured packet → rejected by sequence/timestamp checks
2. **Tampering** — modify field, keep old signature → rejected by signature verification
3. **Impersonation** — forge message without victim's private key → rejected by CA/signature checks

---

## 4. System Architecture

```
                 +----------------------+
                 | Certificate Authority|
                 |         (CA)         |
                 +----------+-----------+
                            |
                  Certificates / Trust
                       +----+----+
                       |         |
                       v         v
                 +---------+ +---------+
                 |Vehicle A| |Vehicle B|
                 +----+----+ +----+----+
                      |           ^
                      |           |
                      +-----------+
                       Secure V2V
                           ^
                           |
                     +-----+-----+
                     |  Attacker |
                     +-----------+
```

After registration, Vehicle A and B communicate directly. The attacker sits on the channel and can intercept, modify, or replay packets but cannot access legitimate private keys.

---

## 5. Communication Flow

```
Vehicle A                          Vehicle B
    |                                   |
    |  1. Create safety message         |
    |  2. Serialize to canonical JSON   |
    |  3. SHA-256 hash                  |
    |  4. ECDSA sign the hash           |
    |  5. Attach certificate (PEM)      |
    |---------------------------------->|
    |                                   |  6. Validate packet structure
    |                                   |  7. Verify certificate (CA-signed)
    |                                   |  8. Recompute hash + verify signature
    |                                   |  9. Check timestamp freshness
    |                                   | 10. Check sequence number
    |                                   | 11. ACCEPT or REJECT + reason
```

---

## 6. Authentication Mechanism

1. **Registration:** Vehicle → CA with `{vehicle_id, public_key}` → CA returns signed X.509 certificate
2. **Transmission:** Every packet includes `{message, signature, certificate_pem}`
3. **Verification:** Receiver validates certificate chain, then signature, then freshness/replay

---

## 7. Cryptographic Mechanisms

| Component | Algorithm | Why |
|-----------|-----------|-----|
| Key generation | ECDSA on **SECP256R1** (NIST P-256) | ~128-bit security; widely used in automotive PKI |
| Hashing | **SHA-256** | Standard integrity digest; explicit step before signing |
| Signing | **ECDSA** with pre-hashed SHA-256 | Authenticates message origin |
| Certificates | **X.509** (365-day validity) | Industry-standard credential format |
| Serialization | Canonical JSON (`sort_keys=True`) | Deterministic bytes for hash/sign |

**Signing flow (explicit steps in code):**

```
Message → serialize_message() → SHA-256 (hash_message) → ECDSA sign → signature
```

---

## 8. Message Format

```json
{
  "vehicle_id": "A001",
  "timestamp": 1693123456.789,
  "sequence_number": 1,
  "position": {"latitude": 17.3850, "longitude": 78.4867},
  "speed": 80,
  "direction": "North",
  "event": "EMERGENCY_BRAKING"
}
```

**Events:** `EMERGENCY_BRAKING`, `ROAD_HAZARD`, `ACCIDENT_WARNING`, `SUDDEN_SLOWDOWN`, `COLLISION_WARNING`

**Signed packet:**

```json
{
  "message": { "..." },
  "signature": "<bytes>",
  "certificate_pem": "<PEM-encoded X.509>"
}
```

---

## 9. Secure Protocol Flow

`MessageVerifier` (`src/security/verification.py`) runs these checks in order:

1. Packet structure (message, signature, certificate present)
2. Message field validation
3. Certificate: CA signature valid, not expired, vehicle registered
4. Vehicle ID in message matches certificate CN
5. Recompute SHA-256 + verify ECDSA signature
6. Timestamp within `TIMESTAMP_VALIDITY_SECONDS` (default 5 s)
7. Sequence number strictly increasing per sender

---

## 10. Attack Model & Demonstrations

| Attack | Method | Result |
|--------|--------|--------|
| Replay | Resend captured packet | REJECTED |
| Tampering | Modify field, keep signature | REJECTED |
| Impersonation | Sign with attacker's key + fake CA | REJECTED |
| Fake certificate | Swap certificate on legitimate message | REJECTED |

```bash
PYTHONPATH=src .venv/bin/python src/main.py
```

---

## 11. Security Properties

| Property | Mechanism |
|----------|-----------|
| Authentication | ECDSA + CA certificate |
| Integrity | SHA-256 + ECDSA |
| Freshness | 5-second timestamp window |
| Replay resistance | Monotonic sequence numbers |
| Authorization | CA registry lookup |
| Non-repudiation | Private key required to sign (simulated) |

---

## 12. Security Analysis (THREAT / ATTACK / DEFENSE)

### Replay Attack

**THREAT:** Attacker retransmits an old legitimate message.  
**ATTACK:** Capture a valid packet and send it again unchanged.  
**DEFENSE:** Timestamp freshness check + per-sender sequence number tracking. Duplicate or stale sequence numbers are rejected with a logged reason.

### Message Tampering

**THREAT:** Attacker modifies message content (e.g., speed 80 → 180).  
**ATTACK:** Change a field but keep the original signature.  
**DEFENSE:** SHA-256 hash is computed over canonical bytes; ECDSA signature verification fails when content does not match.

### Vehicle Impersonation

**THREAT:** Attacker claims to be Vehicle A without A's private key.  
**ATTACK:** Create a forged message signed with the attacker's own key and a self-signed fake certificate.  
**DEFENSE:** Certificate must be signed by the trusted CA and registered. Signature must match the public key in the legitimate certificate.

### Fake Certificate

**THREAT:** Attacker uses a valid signature but swaps in a different certificate.  
**ATTACK:** Replace certificate_pem with attacker's CA-registered cert while keeping A's message/signature.  
**DEFENSE:** Vehicle ID in the message must match the certificate CN; signature will also fail if keys differ.

---

## 13. Module Reference

For each major module: what it does, why it exists, security contribution, and interactions.

### `src/ca/` — Certificate Authority

- **What:** Registers vehicles and issues X.509 certificates.
- **Why:** Establishes a trust anchor so receivers know which public keys belong to which vehicles.
- **Security:** Provides authorization — only CA-registered vehicles are accepted.
- **Interactions:** Called during setup; `MessageVerifier` calls `verify_vehicle_certificate()` on every received packet.

### `src/vehicles/` — Basic Vehicle

- **What:** Pre-crypto vehicle with message creation and replay protection.
- **Why:** Demonstrates Phase 1–3 incrementally before full cryptography is added.
- **Security:** Implements replay/timestamp checks at the message level.
- **Interactions:** Used by early-phase tests; superseded by `SecureVehicle` for the full protocol.

### `src/protocol/` — Messages & V2V Protocol

- **What:** Message format, canonical serialization, signed packet creation, `SecureVehicle`.
- **Why:** Defines the on-the-wire format and orchestrates sign/send/receive.
- **Security:** Ensures deterministic bytes for hashing; separates message data from signature and certificate.
- **Interactions:** Calls `security.signatures`, `security.verification`, `ca.certificate_authority`.

### `src/security/` — Cryptographic Operations

- **What:** Keys, hashing, certificates, signatures, verification, replay protection.
- **Why:** Centralizes all crypto so the flow is easy to trace.
- **Security:** Implements authentication, integrity, and replay defenses.
- **Interactions:** Used by `protocol`, `ca`, and `attacks` modules.

### `src/attacks/` — Attacker Simulation

- **What:** Captures packets and launches replay, tampering, impersonation, fake-certificate attacks.
- **Why:** Demonstrates that defenses work against real adversarial scenarios.
- **Security:** Proves the verification pipeline rejects attacks (not faked).
- **Interactions:** Uses `protocol` to build forged packets; tested against `SecureVehicle.receive_packet()`.

### `src/utils/` — Logging

- **What:** Configurable logger for INFO/WARNING security decisions.
- **Why:** Makes accept/reject decisions visible during demo and debugging.
- **Security:** Audit trail of verification steps and rejection reasons.
- **Interactions:** Used by every module.

---

## 14. Installation

```bash
git clone <repo-url> secure-v2v-protocol
cd secure-v2v-protocol
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Requirements:** Ubuntu 24.04+, Python 3.12+

---

## 15. How to Run

```bash
PYTHONPATH=src .venv/bin/python src/main.py
```

Runs the full 7-phase demo plus performance experiment. Results saved to `results/performance.json`.

---

## 16. How to Run Tests

```bash
.venv/bin/python -m pytest tests/ -v
```

| File | Covers |
|------|--------|
| `test_keys.py` | ECDSA key pair generation |
| `test_certificates.py` | CA registration, cert validation, unknown vehicle |
| `test_signatures.py` | Sign/verify roundtrip, explicit SHA-256, invalid signature |
| `test_replay.py` | Replay, duplicate sequence, stale timestamp |
| `test_tampering.py` | Modified message and speed tampering |
| `test_impersonation.py` | Forged message and fake certificate |
| `test_phase1_communication.py` | Basic A→B messaging |
| `test_phase2_messages.py` | Message structure and serialization |

---

## 17. Example Output

```
PHASE 3: NORMAL SECURE COMMUNICATION
  Normal message: ACCEPTED

PHASE 4: REPLAY ATTACK
  Replay attack: REJECTED
    Reason: Replay detected: sequence 1 <= last accepted 1 from A001

PHASE 5: MESSAGE TAMPERING ATTACK
  Tampered message: REJECTED
    Reason: Invalid digital signature

PHASE 7: SECURITY RESULTS
  All security checks passed: True
```

---

## 18. Performance Testing

100-iteration benchmark measures:

| Metric | Typical value |
|--------|---------------|
| Message creation | ~0.001 ms |
| Signing (hash + ECDSA) | ~0.05 ms |
| Full verification | ~0.2 ms |
| Replay detection | ~0.2 ms |
| Tamper detection | ~0.2 ms |

Results saved to `results/performance.json`.

---

## 19. Limitations

- **Simulation only** — not a production automotive security system
- **No real radio stack** — no DSRC/C-V2X propagation model
- **No vehicle control** — messages are simulated, not actuated
- **Simplified PKI** — no certificate revocation (CRL/OCSP)
- **In-memory CA registry** — not persistent across restarts
- **No confidentiality** — safety messages are authenticated but not encrypted (by design)
- **Simulated GPS** — position data is hard-coded coordinates
- **Two vehicles** — scalability not evaluated

---

## 20. Future Improvements

- Certificate revocation lists (CRL)
- Optional message encryption (ECIES)
- Multi-hop V2V relay
- IEEE 1609.2 / ETSI TS 103 097 alignment
- Network simulation (loss, delay, broadcast)
- Embedded deployment (Raspberry Pi + SDR)

---

## Web Dashboard

An interactive cybersecurity dashboard visualizes the same secure V2V protocol in a browser. The web layer is **additive** — the CLI and all `src/` security code remain unchanged.

### Architecture

```
React + Vite + TypeScript (web/frontend)
        │  HTTP REST + polling (2s)
FastAPI (web/backend) — thin API wrapper
        │  imports existing src/ modules
Existing cryptographic implementation (src/)
```

See [WEB_ARCHITECTURE.md](WEB_ARCHITECTURE.md) for the full design.

### Install Frontend Dependencies

```bash
cd web/frontend
npm install
```

### Start Backend

```bash
source .venv/bin/activate
PYTHONPATH=src:. uvicorn web.backend.main:app --reload --host 127.0.0.1 --port 8000
```

### Start Frontend

```bash
cd web/frontend
npm run dev
```

Open **http://localhost:5173**. The Vite dev server proxies `/api/*` to the FastAPI backend on port 8000.

### Dashboard Pages

| Page | Purpose |
|------|---------|
| **Dashboard** | Live stats, vehicle network, certificate/security status |
| **V2V Communication** | Send signed messages; view step-by-step security pipeline |
| **Certificate Authority** | CA info and vehicle X.509 certificates (public data only) |
| **Attack Simulation** | Replay, tampering, impersonation, fake certificate attacks |
| **Security Event Log** | Real backend log events with filter/search |
| **Performance** | Benchmark charts from `results/performance.json` |
| **Architecture** | Interactive security architecture diagram |

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | Dashboard summary |
| GET | `/api/vehicles` | Vehicle list with security status |
| GET | `/api/certificates` | CA + vehicle certificates |
| POST | `/api/message/send` | Send signed V2V message |
| POST | `/api/attack/replay` | Replay attack simulation |
| POST | `/api/attack/tampering` | Tampering attack simulation |
| POST | `/api/attack/impersonation` | Impersonation attack |
| POST | `/api/attack/fake-certificate` | Fake certificate attack |
| GET | `/api/events` | Security event log |
| GET | `/api/performance` | Benchmark results |
| GET | `/api/architecture` | Architecture metadata |

### Demo Guide

See [WEB_DEMO_GUIDE.md](WEB_DEMO_GUIDE.md) for a step-by-step viva presentation script.

### Screenshots

<!-- Add screenshots after running the dashboard -->
<!-- ![Dashboard](docs/screenshots/dashboard.png) -->

---

## Progress Tracker

See [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md) for the complete phase checklist.
