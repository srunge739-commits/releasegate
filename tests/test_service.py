from __future__ import annotations

from pathlib import Path

import pytest

from releasegate.adapters.fixture import load_packets
from releasegate.service import ReleaseGateError, ReleaseGateService


FIXTURES = Path(__file__).resolve().parents[1] / "assets" / "fixtures" / "packets.json"


@pytest.fixture()
def service() -> ReleaseGateService:
    return ReleaseGateService(load_packets(FIXTURES))


def test_signature_cannot_bypass_a_blocker(service: ReleaseGateService) -> None:
    with pytest.raises(ReleaseGateError, match="Signature is blocked"):
        service.request_signature(
            "PKT-1001-BLOCKED",
            reviewer="Casey Rivera",
            reason="Release requested",
        )


def test_review_then_approval_produces_safe_simulation(service: ReleaseGateService) -> None:
    reviewed = service.confirm_field(
        "PKT-1002-REVIEW",
        document_id="DOC-1002-INV",
        field_name="amount",
        reviewer="Casey Rivera",
        reason="Compared the amount with the visible invoice total.",
    )
    assert reviewed["status"] == "ready_for_approval"

    result = service.request_signature(
        "PKT-1002-REVIEW",
        reviewer="Casey Rivera",
        reason="Packet evidence is complete and reconciled.",
    )

    assert result["envelope"]["provider"] == "fixture-simulation"
    assert result["envelope"]["status"] == "prepared_not_sent"
    assert "No document or email was sent" in result["envelope"]["notice"]
    assert service.audit.verify()["valid"] is True


def test_signature_preparation_is_idempotent(service: ReleaseGateService) -> None:
    first = service.request_signature(
        "PKT-1003-READY",
        reviewer="Casey Rivera",
        reason="Evidence verified.",
    )
    second = service.request_signature(
        "PKT-1003-READY",
        reviewer="Casey Rivera",
        reason="Evidence verified again.",
    )

    assert first["envelope"]["envelope_id"] == second["envelope"]["envelope_id"]


def test_review_requires_named_person_and_reason(service: ReleaseGateService) -> None:
    with pytest.raises(ReleaseGateError, match="Reviewer and review reason"):
        service.confirm_field(
            "PKT-1002-REVIEW",
            document_id="DOC-1002-INV",
            field_name="amount",
            reviewer="",
            reason="",
        )

