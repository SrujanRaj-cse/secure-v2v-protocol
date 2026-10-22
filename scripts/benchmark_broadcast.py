"""Reproducible in-process broadcast benchmark (not radio latency)."""

import argparse
import csv
import platform
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from web.backend.state import SimulationState  # noqa: E402
from protocol.v2v_protocol import SecureVehicle  # noqa: E402
from security.keys import generate_key_pair  # noqa: E402


def prepare_state(vehicle_count: int, seed: int) -> SimulationState:
    state = SimulationState()
    for index in range(3, vehicle_count):
        vehicle_id = f"V{index:03d}"
        # Deterministic local grid; approximately 30–40 m between vehicles.
        position = (17.385 + (index % 10) * 0.00015, 78.4867 + (index // 10) * 0.00015)
        key = generate_key_pair()
        cert = state.ca.register_vehicle(vehicle_id, key.public_key())
        state.vehicles[vehicle_id] = SecureVehicle(
            vehicle_id, 65 + (index % 40), position, "East", key, cert, state.ca
        )
    state.update_simulation_config(communication_range_m=10_000, random_seed=seed)
    return state


def run(output: Path, iterations: int = 5, seed: int = 428) -> None:
    rows = []
    for count in (3, 10, 25, 50, 100):
        state = prepare_state(count, seed)
        # Warm up cryptographic imports/cache before collecting timings.
        state.broadcast_message("A001", "ROAD_HAZARD")
        samples = []
        accepted = delivered = warnings = 0
        for _ in range(iterations):
            result = state.broadcast_message("A001", "ROAD_HAZARD")
            recipients = result["recipients"]
            delivered_items = [r for r in recipients if r["delivery_status"] == "delivered"]
            delivered += len(delivered_items)
            accepted += sum(r["accepted"] for r in recipients)
            warnings += sum(bool(r.get("safety", {}).get("warning")) for r in recipients if r.get("safety"))
            metrics = result["performance_metrics"]
            verify_times = [r["verification_ms"] for r in delivered_items]
            samples.append({
                "message_creation_ms": metrics["message_creation_ms"],
                "signing_ms": metrics["signing_ms"],
                "eligibility_ms": metrics["eligibility_ms"],
                "delivery_processing_ms": metrics["delivery_processing_ms"],
                "verification_ms_per_recipient": statistics.mean(verify_times) if verify_times else 0,
                "total_broadcast_ms": metrics["total_broadcast_ms"],
            })
        average = {key: statistics.mean(s[key] for s in samples) for key in samples[0]}
        rows.append({
            "vehicles": count,
            "iterations": iterations,
            "seed": seed,
            "python": platform.python_version(),
            "platform": platform.platform(),
            **{key: f"{value:.6f}" for key, value in average.items()},
            "successful_deliveries": delivered,
            "verified_messages": accepted,
            "warnings_generated": warnings,
        })
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--seed", type=int, default=428)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "broadcast_benchmark.csv")
    args = parser.parse_args()
    run(args.output, args.iterations, args.seed)
