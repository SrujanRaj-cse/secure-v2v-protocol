# Web Dashboard Demo Guide

Step-by-step guide for presenting the Secure V2V Protocol web dashboard during your viva.

---

## Prerequisites

```bash
cd secure-v2v-protocol
source .venv/bin/activate
pip install -r requirements.txt
cd web/frontend && npm install && cd ../..
```

---

## 1. Start the Backend (Terminal 1)

```bash
cd secure-v2v-protocol
source .venv/bin/activate
PYTHONPATH=src:. uvicorn web.backend.main:app --reload --host 127.0.0.1 --port 8000
```

The API initializes the CA and registers vehicles A001, B001, C001 automatically.

---

## 2. Start the Frontend (Terminal 2)

```bash
cd secure-v2v-protocol/web/frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## 3. Dashboard Overview (30 seconds)

1. Open the **Dashboard** page (default).
2. Point out the summary cards: active vehicles, messages sent/verified/rejected, attacks detected.
3. Show the **Vehicle Network** diagram — three vehicles connected via Secure V2V links.
4. Explain each vehicle card shows certificate status, security status, and sequence number.

---

## 4. Send a Legitimate Message (1 minute)

1. Go to **V2V Communication**.
2. Set Sender: **A001**, Receiver: **B001**.
3. Choose **Emergency Braking**, speed **80 km/h**.
4. Click **SEND SECURE MESSAGE**.
5. Walk through the **Security Pipeline**:
   - Message Created → SHA-256 → ECDSA Signature → Certificate Attached
   - Transmission → Certificate Verification → Signature Verification
   - Replay Check → Timestamp Check → Sequence Check → **MESSAGE ACCEPTED**
6. Note the green acceptance banner and SHA-256 hash displayed.

---

## 5. Certificate Authority (30 seconds)

1. Go to **Certificate Authority**.
2. Show the CA info: name, algorithm (ECDSA SECP256R1), validity period.
3. Click **View Details** on vehicle A001's certificate.
4. Explain: public key is shown (abbreviated), **private keys are never exposed**.

---

## 6. Launch Replay Attack (1 minute)

1. Go to **Attack Simulation**.
2. Click **LAUNCH REPLAY ATTACK** on the Replay card.
3. Show the pipeline:
   - Attacker Captured Packet → Packet Retransmitted
   - Certificate verification passes, signature passes
   - **Sequence Check FAILS** → REPLAY DETECTED
4. Point out the rejection reason from the real backend:
   `Replay detected: sequence N <= last accepted N from A001`

---

## 7. Launch Tampering Attack (1 minute)

1. Click **LAUNCH TAMPERING ATTACK**.
2. Show original speed (80 km/h) vs modified speed (180 km/h).
3. Explain: "Message was modified after signing — signature no longer matches."
4. Show **Signature Verification FAILED** → MESSAGE REJECTED.

---

## 8. Launch Impersonation Attack (30 seconds)

1. Click **LAUNCH IMPERSONATION ATTACK**.
2. Show that the attacker uses a self-signed fake certificate.
3. **Certificate Verification FAILS** → FAKE CERTIFICATE REJECTED.

---

## 9. Security Event Log (30 seconds)

1. Go to **Security Event Log**.
2. Show real log entries from backend operations (not fake events).
3. Demonstrate filtering by severity or vehicle ID.
4. Point out color-coded severity: INFO, SUCCESS, WARNING, ERROR.

---

## 10. Performance Analytics (30 seconds)

1. Go to **Performance**.
2. Show benchmark metrics loaded from `results/performance.json`.
3. Explain bar chart: message creation, signing, verification, replay/tamper detection times.
4. Optional: click **Run Benchmark** to regenerate results live.

---

## 11. Security Architecture (30 seconds)

1. Go to **Architecture**.
2. Click components to show explanations.
3. Walk through: CA → Certificates → Vehicles → V2V Message → Validation → Result.

---

## 5-Minute Demo Script (Condensed)

| Step | Action | Key Point |
|------|--------|-----------|
| 1 | Open Dashboard | Live monitoring of 3 vehicles |
| 2 | Send message A001→B001 | Full pipeline ACCEPTED |
| 3 | Launch replay attack | Rejected by sequence check |
| 4 | Launch tampering attack | Rejected by signature verification |
| 5 | Show event log + performance | Real backend data, not simulated |

---

## Optional: CLI Demo

Show the original CLI still works independently:

```bash
PYTHONPATH=src python src/main.py
```

This runs the same security logic without the web interface.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Backend unavailable on dashboard | Ensure uvicorn is running on port 8000 |
| Attack buttons fail | Send a legitimate message first (attacks need a captured packet) |
| Performance page empty | Run `PYTHONPATH=src python -c "from main import run_performance_experiment; run_performance_experiment()"` or click Run Benchmark |
| Frontend can't reach API | Vite proxy forwards `/api` → `localhost:8000`; both must be running |

---

## What to Emphasize in Viva

1. **No fake security** — all results come from the existing `src/` implementation.
2. **Web is a visualization layer** — FastAPI wraps existing classes; crypto code is unchanged.
3. **Private keys never exposed** — API returns only public certificate data.
4. **Four attack types** — replay, tampering, impersonation, fake certificate — all rejected by real checks.
5. **Performance is measured** — benchmark uses the same code path as the CLI demo.
