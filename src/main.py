"""
Secure V2V Protocol — complete demonstration.

Runs all phases: CA setup, registration, normal communication,
and attack scenarios with real verification results.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from attacks.attacker import Attacker
from ca.certificate_authority import CertificateAuthority
from config import TIMESTAMP_VALIDITY_SECONDS
from protocol.v2v_protocol import SecureVehicle, create_signed_packet
from security.keys import generate_key_pair
from utils.logger import get_logger

logger = get_logger(__name__)


def setup_vehicles(ca: CertificateAuthority):
    """Register Vehicle A and B with the CA, return secure vehicle objects."""
    key_a = generate_key_pair()
    key_b = generate_key_pair()

    cert_a = ca.register_vehicle("A001", key_a.public_key())
    cert_b = ca.register_vehicle("B001", key_b.public_key())

    vehicle_a = SecureVehicle(
        "A001", 80, (17.3850, 78.4867), "North", key_a, cert_a, ca
    )
    vehicle_b = SecureVehicle(
        "B001", 75, (17.3860, 78.4870), "North", key_b, cert_b, ca
    )

    return vehicle_a, vehicle_b


def run_full_demo() -> dict:
    """Run the complete secure V2V demonstration and return results."""
    print("=" * 55)
    print("  SECURE V2V PROTOCOL DEMONSTRATION")
    print("=" * 55)

    results = {}

    # Phase 1: CA Initialization
    print("\nPHASE 1: CA INITIALIZATION")
    print("-" * 40)
    ca = CertificateAuthority()
    print(f"  CA initialized: {ca.ca_name}")
    print(f"  Registered vehicles: {len(ca.registered_vehicles)}")

    # Phase 2: Vehicle Registration
    print("\nPHASE 2: VEHICLE REGISTRATION")
    print("-" * 40)
    vehicle_a, vehicle_b = setup_vehicles(ca)
    print("  Vehicle A001 registered and certificate issued.")
    print("  Vehicle B001 registered and certificate issued.")

    # Phase 3: Normal Communication
    print("\nPHASE 3: NORMAL SECURE COMMUNICATION")
    print("-" * 40)
    packet = vehicle_a.send_message("EMERGENCY_BRAKING")
    ok, reason = vehicle_b.receive_packet(packet)
    results["normal"] = ok
    print(f"  Normal message: {'ACCEPTED' if ok else 'REJECTED'}")
    if not ok:
        print(f"    Reason: {reason}")

    # Phase 4: Replay Attack
    print("\nPHASE 4: REPLAY ATTACK")
    print("-" * 40)
    attacker = Attacker(ca)
    attacker.capture(packet)
    replay_packet = attacker.replay_attack()
    ok, reason = vehicle_b.receive_packet(replay_packet)
    results["replay"] = ok
    print(f"  Replay attack: {'ACCEPTED' if ok else 'REJECTED'}")
    if not ok:
        print(f"    Reason: {reason}")

    # Phase 5: Tampering Attack
    print("\nPHASE 5: MESSAGE TAMPERING ATTACK")
    print("-" * 40)
    fresh_packet = vehicle_a.send_message("ROAD_HAZARD")
    attacker.capture(fresh_packet)
    tampered = attacker.tampering_attack(field="speed", new_value=180)
    ok, reason = vehicle_b.receive_packet(tampered)
    results["tampering"] = ok
    print(f"  Tampered message: {'ACCEPTED' if ok else 'REJECTED'}")
    if not ok:
        print(f"    Reason: {reason}")

    # Phase 6: Impersonation Attack (includes fake-certificate variant)
    print("\nPHASE 6: IMPERSONATION ATTACK")
    print("-" * 40)
    impersonated = attacker.impersonation_attack(target_vehicle_id="A001")
    ok, reason = vehicle_b.receive_packet(impersonated)
    results["impersonation"] = ok
    print(f"  Impersonation (forged message): {'ACCEPTED' if ok else 'REJECTED'}")
    if not ok:
        print(f"    Reason: {reason}")

    legit_packet = vehicle_a.send_message("COLLISION_WARNING")
    fake_cert_packet = attacker.fake_certificate_attack(legit_packet)
    ok, reason = vehicle_b.receive_packet(fake_cert_packet)
    results["fake_certificate"] = ok
    print(f"  Fake certificate swap:        {'ACCEPTED' if ok else 'REJECTED'}")
    if not ok:
        print(f"    Reason: {reason}")

    # Phase 7: Security Results Summary
    print("\nPHASE 7: SECURITY RESULTS")
    print("-" * 40)
    print(f"  Normal message:     {'ACCEPTED' if results['normal'] else 'REJECTED'}")
    print(f"  Replay attack:      {'ACCEPTED' if results['replay'] else 'REJECTED'}")
    print(f"  Tampered message:   {'ACCEPTED' if results['tampering'] else 'REJECTED'}")
    print(f"  Impersonation:      {'ACCEPTED' if results['impersonation'] else 'REJECTED'}")
    print(f"  Fake certificate:   {'ACCEPTED' if results['fake_certificate'] else 'REJECTED'}")

    expected = (
        results["normal"] is True
        and results["replay"] is False
        and results["tampering"] is False
        and results["impersonation"] is False
        and results["fake_certificate"] is False
    )
    print(f"\n  All security checks passed: {expected}")

    return results


def run_performance_experiment(iterations: int = 100) -> dict:
    """
    Measure message creation, signing, verification, and attack detection times.

    Results are saved to results/performance.json.
    """
    print("\n" + "=" * 55)
    print("  PERFORMANCE EXPERIMENT")
    print("=" * 55)

    ca = CertificateAuthority()
    vehicle_a, vehicle_b = setup_vehicles(ca)
    attacker = Attacker(ca)

    create_times = []
    sign_times = []
    verify_times = []
    replay_detect_times = []
    tamper_detect_times = []

    for _ in range(iterations):
        t0 = time.perf_counter()
        message = vehicle_a.create_message("EMERGENCY_BRAKING")
        create_times.append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        packet = create_signed_packet(
            message, vehicle_a.private_key, vehicle_a.certificate
        )
        sign_times.append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        vehicle_b.receive_packet(packet)
        verify_times.append(time.perf_counter() - t0)

    for _ in range(iterations):
        # Fresh receiver so replay state does not carry over between samples
        fresh_b = SecureVehicle(
            vehicle_b.vehicle_id,
            vehicle_b.speed,
            vehicle_b.position,
            vehicle_b.direction,
            vehicle_b.private_key,
            vehicle_b.certificate,
            ca,
        )
        packet = vehicle_a.send_message("EMERGENCY_BRAKING")
        fresh_b.receive_packet(packet)
        attacker.capture(packet)

        t0 = time.perf_counter()
        fresh_b.receive_packet(attacker.replay_attack())
        replay_detect_times.append(time.perf_counter() - t0)

        tamper_packet = vehicle_a.send_message("ROAD_HAZARD")
        attacker.capture(tamper_packet)
        tampered = attacker.tampering_attack(field="speed", new_value=180)

        t0 = time.perf_counter()
        vehicle_b.receive_packet(tampered)
        tamper_detect_times.append(time.perf_counter() - t0)

    def avg(times):
        return sum(times) / len(times) if times else 0.0

    stats = {
        "iterations": iterations,
        "timestamp_validity_seconds": TIMESTAMP_VALIDITY_SECONDS,
        "avg_message_creation_ms": avg(create_times) * 1000,
        "avg_signing_ms": avg(sign_times) * 1000,
        "avg_verification_ms": avg(verify_times) * 1000,
        "avg_replay_detection_ms": avg(replay_detect_times) * 1000,
        "avg_tamper_detection_ms": avg(tamper_detect_times) * 1000,
    }

    print(f"  Iterations: {iterations}")
    print(f"  Avg message creation:   {stats['avg_message_creation_ms']:.3f} ms")
    print(f"  Avg signing:            {stats['avg_signing_ms']:.3f} ms")
    print(f"  Avg verification:       {stats['avg_verification_ms']:.3f} ms")
    print(f"  Avg replay detection:   {stats['avg_replay_detection_ms']:.3f} ms")
    print(f"  Avg tamper detection:   {stats['avg_tamper_detection_ms']:.3f} ms")

    results_dir = Path(__file__).parent.parent / "results"
    results_dir.mkdir(exist_ok=True)
    output_path = results_dir / "performance.json"
    with open(output_path, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"\n  Results saved to: {output_path}")

    return stats


if __name__ == "__main__":
    results = run_full_demo()
    run_performance_experiment(iterations=100)
