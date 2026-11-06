"""SMS stub. Real provider wiring is out of scope for v1."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def send(to: str, body: str) -> None:
    """Log or no-op an SMS. Email is the demo notification path."""
    logger.info("SMS stub (no-op): to=%s body=%s", to, body)
