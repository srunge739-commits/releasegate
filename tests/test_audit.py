from __future__ import annotations

from releasegate.audit import AuditLedger


def test_hash_chain_detects_tampering() -> None:
    ledger = AuditLedger()
    ledger.append(action="evaluated", actor="policy", packet_id="PKT-1", payload={"status": "blocked"})
    ledger.append(action="reviewed", actor="human", packet_id="PKT-1", payload={"field": "amount"})

    assert ledger.verify()["valid"] is True

    ledger._events[0]["payload"]["status"] = "ready"  # deliberate hostile mutation
    result = ledger.verify()
    assert result["valid"] is False
    assert result["failed_sequence"] == 1

