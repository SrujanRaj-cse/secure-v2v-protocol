# Security Analysis

## Threat model and goals

The local educational model considers an attacker able to capture, replay, modify, or forge packets and to report false telemetry using a credentialed vehicle. The CA and vehicle private keys are trusted and remain inside the Python process. Goals are sender authentication, integrity of signed fields, certificate trust/identity binding, freshness, per-receiver replay rejection, transparent delivery outcomes, and separation of authentication from safety relevance.

## Implemented defenses

- ECDSA on the existing secp256r1 curve with SHA-256 over canonical JSON bytes.
- X.509 certificates issued by the in-process CA, verified against the CA and registration registry, plus certificate subject to message vehicle-ID binding.
- Schema validation before certificate and signature processing.
- Timestamp freshness and monotonic sequence numbers tracked independently at each receiver; replay check/update is lock-protected.
- Tampering, replay, invalid certificate/identity, stale packet, and signed false-data demonstrations.
- Geographic eligibility and seeded packet loss represented separately from cryptographic checks.
- The false-data demonstration illustrates that a valid signature can authenticate a false report. Advisory demo plausibility flags do not affect authentication acceptance.

## Assumptions and limitations

The demo trusts its in-memory CA and vehicle registry and does not persist keys or revocation state. It does not encrypt messages, defend against compromised vehicle private keys, prove telemetry truth, implement a real radio/network channel, model certificate revocation, or provide production-grade availability. The Haversine range boundary and loss model are simplified and do not model obstacles, interference, antenna behavior, or real automotive standards. Clock freshness depends on system time. The message format is canonical within this Python implementation; cross-language encoding interoperability is not established.

The TTC evaluator is a simple educational estimate and is not a validated collision warning algorithm. Neither cryptographic acceptance nor relevance evaluation should control a real vehicle.
