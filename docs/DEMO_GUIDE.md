# CS428 Broadcast Demonstration

## Start the project

From the repository root:

```bash
source .venv/bin/activate
PYTHONPATH=src:. uvicorn web.backend.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```bash
cd web/frontend
npm run dev
```

Open `http://localhost:5173` and select **V2V Communication**.

## Multi-vehicle broadcast

1. Keep mode on **Broadcast**, choose `A001`, and select **Emergency Braking**.
2. Use the default 500 m range, 0% packet loss, and seed 428. `B001` starts about 100 m south (behind) `A001`, with both vehicles heading north; B001's 120 km/h speed closes on A001's 80 km/h event speed in about 9 seconds. `C001` is in range but travelling east away from the event.
3. Send the message. Explain that the sender signs once, the sender is excluded, and each eligible vehicle independently validates the same packet using its own replay state.
4. Review the table: delivery, verification, distance, and safety relevance are separate. The message position represents A001's current position when it creates the signed event. B001 receives a warning only when it is approaching in the same direction and the calculated TTC is at most 10 seconds. The channel and range are in-process educational models, not real V2V radio.
5. Set the range to 100 m and send again to show outside-range outcomes. Set packet loss to 50% and repeat with the same seed to reproduce the same drops.
6. For unicast compatibility, select **Unicast**, choose a receiver, and send a signed packet through the original endpoint.

## Attack demonstrations

Open **Attack Simulation** after sending a legitimate broadcast. Replay is rejected by sequence/replay protection. Tampering changes the signed speed while preserving a valid message schema, so ECDSA signature verification fails. Impersonation uses a schema-valid message and an untrusted self-signed certificate, so certificate verification fails. Fake Certificate swaps in a CA-registered EVIL001 certificate for A001's message: certificate validation passes, then identity validation fails with a vehicle-ID mismatch. Stale Signed Message is correctly signed with an old timestamp, then rejected by freshness validation. False Data from Valid Sender is signed by A001 and accepted cryptographically while advisory plausibility flags identify the implausible speed and position. A signature authenticates bytes and key possession; it does not prove reported telemetry is true, and the plausibility checks are not general malicious-data detection.

## Movement and configurable vehicles

Use FastAPI's `http://127.0.0.1:8000/docs` to create vehicles with `POST /api/vehicles`, change state with `PATCH /api/vehicles/{vehicle_id}`, update channel values with `PUT /api/simulation/config`, and advance online vehicle positions with `POST /api/simulation/step` (`{"seconds": 1}`). Coordinates are decimal latitude/longitude; speed is km/h and acceleration m/s².

## Benchmark

From the repository root:

```bash
./.venv/bin/python scripts/benchmark_broadcast.py --iterations 3 --seed 428
```

The output is `results/broadcast_benchmark.csv`. It measures local Python signing, recipient eligibility, delivered receiver verification, and aggregate in-process processing. These measurements are not automotive network latency.
