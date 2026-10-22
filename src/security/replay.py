"""
Replay protection: timestamp freshness and sequence number tracking.

Each receiver remembers the highest accepted sequence number per sender.
Messages with stale timestamps or duplicate/old sequence numbers are rejected.
"""

import time
import threading
from typing import Any

from config import TIMESTAMP_VALIDITY_SECONDS
from utils.logger import get_logger

logger = get_logger(__name__)


class ReplayProtector:
    """
    Tracks per-sender sequence numbers and enforces timestamp freshness.

    Used by receiving vehicles to detect replayed or duplicated messages.
    """

    def __init__(self, timestamp_window: float = TIMESTAMP_VALIDITY_SECONDS):
        self.timestamp_window = timestamp_window
        # Maps sender vehicle_id -> last accepted sequence number
        self.last_sequence_numbers: dict[str, int] = {}
        self._lock = threading.Lock()

    def check(self, message: dict[str, Any]) -> tuple[bool, str]:
        """
        Verify timestamp freshness and sequence number ordering.

        Returns (True, "OK") if the message passes both checks.
        """
        try:
            sender_id = message["vehicle_id"]
            sequence_number = message["sequence_number"]
            timestamp = message["timestamp"]
        except (TypeError, KeyError):
            return False, "Invalid replay fields"

        with self._lock:
            age = time.time() - timestamp
            if age > self.timestamp_window:
                reason = (f"Message timestamp expired (age={age:.2f}s, "
                          f"window={self.timestamp_window}s)")
                logger.warning(f"REJECTED: {reason}")
                return False, reason
            if age < -1.0:
                reason = "Message timestamp is in the future"
                logger.warning(f"REJECTED: {reason}")
                return False, reason
            if sender_id in self.last_sequence_numbers:
                last_seq = self.last_sequence_numbers[sender_id]
                if sequence_number <= last_seq:
                    reason = (f"Replay detected: sequence {sequence_number} "
                              f"<= last accepted {last_seq} from {sender_id}")
                    logger.warning(f"REJECTED: {reason}")
                    return False, reason
            self.last_sequence_numbers[sender_id] = sequence_number
        logger.info(
            f"Replay protection passed for {sender_id} "
            f"(seq={sequence_number}, age={age:.2f}s)"
        )
        return True, "OK"
