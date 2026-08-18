from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


class AuditLedger:
    """Small tamper-evident event ledger suitable for a reproducible demo."""

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    @property
    def events(self) -> list[dict[str, Any]]:
        return [dict(event) for event in self._events]

    def append(
        self,
        *,
        action: str,
        actor: str,
        packet_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        previous_hash = self._events[-1]["hash"] if self._events else "GENESIS"
        event = {
            "sequence": len(self._events) + 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "actor": actor,
            "packet_id": packet_id,
            "payload": payload,
            "previous_hash": previous_hash,
        }
        event["hash"] = hashlib.sha256(_canonical(event)).hexdigest()
        self._events.append(event)
        return dict(event)

    def verify(self) -> dict[str, Any]:
        previous_hash = "GENESIS"
        for index, stored in enumerate(self._events, start=1):
            event = dict(stored)
            expected_hash = event.pop("hash", "")
            calculated_hash = hashlib.sha256(_canonical(event)).hexdigest()
            if (
                event.get("sequence") != index
                or event.get("previous_hash") != previous_hash
                or calculated_hash != expected_hash
            ):
                return {"valid": False, "events": len(self._events), "failed_sequence": index}
            previous_hash = expected_hash
        return {"valid": True, "events": len(self._events), "head": previous_hash}

