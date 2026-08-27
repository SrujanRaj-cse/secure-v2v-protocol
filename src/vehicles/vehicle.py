"""
Vehicle entity for the V2V communication simulator.

Structured messages (Phase 2) and replay protection (Phase 3).
Cryptographic signing and verification are added in later phases.
"""

from protocol.messages import create_safety_message, validate_message_structure
from security.replay import ReplayProtector
from utils.logger import get_logger

logger = get_logger(__name__)


class Vehicle:
    """
    Represents a simulated vehicle that can send and receive V2V messages.

    Each vehicle has a unique ID and simulated kinematic state (speed,
    position, direction) used when constructing safety messages.
    """

    def __init__(
        self,
        vehicle_id: str,
        speed: float,
        position: tuple[float, float],
        direction: str,
    ):
        self.vehicle_id = vehicle_id
        self.speed = speed
        self.position = position  # (latitude, longitude) — simulated GPS
        self.direction = direction
        self.sequence_number = 0
        self.replay_protector = ReplayProtector()

    def create_message(self, event: str) -> dict:
        """
        Build a structured safety message with timestamp and sequence number.

        Increments the sequence counter on each call so every outbound
        message has a unique, monotonically increasing sequence number.
        """
        self.sequence_number += 1

        message = create_safety_message(
            vehicle_id=self.vehicle_id,
            sequence_number=self.sequence_number,
            position=self.position,
            speed=self.speed,
            direction=self.direction,
            event=event,
        )

        logger.info(
            f"Vehicle {self.vehicle_id} created message "
            f"#{self.sequence_number}: event={event}"
        )
        return message

    def receive_message(self, message: dict) -> bool:
        """
        Validate structure and replay protection before accepting a message.

        Cryptographic verification is added in Phase 7.
        """
        valid, reason = validate_message_structure(message)
        if not valid:
            logger.warning(f"REJECTED: {reason}")
            return False

        replay_ok, replay_reason = self.replay_protector.check(message)
        if not replay_ok:
            return False

        sender_id = message["vehicle_id"]
        logger.info(f"Vehicle {self.vehicle_id} received message from {sender_id}")
        logger.info(f"MESSAGE ACCEPTED from {sender_id}")
        return True
