"""
In-memory event log fed by a custom logging handler.

Captures real log output from existing security modules — no fake events.
"""

import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any


class EventLogHandler(logging.Handler):
    """Append log records to a shared in-memory list."""

    def __init__(self, storage: list):
        super().__init__()
        self.storage = storage
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        level = record.levelname
        severity = {
            "DEBUG": "info",
            "INFO": "info",
            "WARNING": "warning",
            "ERROR": "error",
            "CRITICAL": "error",
        }.get(level, "info")

        if record.levelno >= logging.WARNING and "REJECTED" in record.getMessage():
            severity = "error"
        elif record.levelno >= logging.WARNING and "Attacker" in record.getMessage():
            severity = "warning"
        elif "ACCEPTED" in record.getMessage() or "successful" in record.getMessage():
            severity = "success"

        vehicle_id = _extract_vehicle_id(record.getMessage())

        entry = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "severity": severity,
            "message": record.getMessage(),
            "source": record.name,
            "vehicle_id": vehicle_id,
        }

        with self._lock:
            self.storage.append(entry)
            if len(self.storage) > 500:
                self.storage[:] = self.storage[-500:]


def _extract_vehicle_id(message: str) -> str | None:
    for vid in ("A001", "B001", "C001", "EVIL001", "UNKNOWN001"):
        if vid in message:
            return vid
    return None


def attach_event_log_handler(storage: list) -> EventLogHandler:
    """Attach handler to all project loggers."""
    handler = EventLogHandler(storage)
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    for name in (
        "ca.certificate_authority",
        "protocol.v2v_protocol",
        "protocol.messages",
        "security.verification",
        "security.signatures",
        "security.certificates",
        "security.replay",
        "security.keys",
        "attacks.attacker",
        "web.backend",
    ):
        logger = logging.getLogger(name)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return handler


def filter_events(
    events: list[dict[str, Any]],
    *,
    severity: str | None = None,
    vehicle_id: str | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    result = events
    if severity and severity != "all":
        result = [e for e in result if e["severity"] == severity]
    if vehicle_id and vehicle_id != "all":
        result = [e for e in result if e.get("vehicle_id") == vehicle_id]
    if search:
        q = search.lower()
        result = [e for e in result if q in e["message"].lower()]
    return list(reversed(result))
