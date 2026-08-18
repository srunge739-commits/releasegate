from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any


class FixtureSignatureGateway:
    """Safe local boundary: it records intent but cannot send a real document."""

    def __init__(self) -> None:
        self._envelopes: dict[str, dict[str, Any]] = {}

    def create(self, *, packet_id: str, actor: str, reason: str) -> dict[str, Any]:
        if packet_id in self._envelopes:
            return dict(self._envelopes[packet_id])
        envelope_id = "SIM-" + hashlib.sha256(packet_id.encode("utf-8")).hexdigest()[:12].upper()
        envelope = {
            "envelope_id": envelope_id,
            "packet_id": packet_id,
            "provider": "fixture-simulation",
            "status": "prepared_not_sent",
            "approved_by": actor,
            "approval_reason": reason,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "notice": "No document or email was sent. Configure a reviewed live gateway for real eSignature.",
        }
        self._envelopes[packet_id] = envelope
        return dict(envelope)

