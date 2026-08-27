"""
Central configuration for the Secure V2V Protocol simulator.

Security-related values (timestamp window, crypto settings) will be
added in later phases. Keeping them here avoids scattering magic numbers.
"""

# Logging
LOG_LEVEL = "INFO"
DEMO_MODE = True

# Replay protection (used starting in Phase 3)
TIMESTAMP_VALIDITY_SECONDS = 5.0

# Cryptography (used starting in Phase 4)
ECDSA_CURVE = "SECP256R1"  # NIST P-256 — widely supported, 128-bit security
