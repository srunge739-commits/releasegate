from __future__ import annotations

from pathlib import Path

from releasegate.adapters.fixture import load_packets
from releasegate.models import DecisionStatus
from releasegate.policy import evaluate_packet


FIXTURES = Path(__file__).resolve().parents[1] / "assets" / "fixtures" / "packets.json"


def test_blocked_packet_cites_expiration_and_approval_amount() -> None:
    packet = load_packets(FIXTURES)["PKT-1001-BLOCKED"]
    decision = evaluate_packet(packet)

    assert decision.status == DecisionStatus.BLOCKED
    assert {finding.code for finding in decision.findings} == {
        "approval_amount_mismatch",
        "insurance_expired",
    }
    assert all(finding.evidence for finding in decision.findings)
    assert {item.document_id for finding in decision.findings for item in finding.evidence} >= {
        "DOC-1001-INV",
        "DOC-1001-APR",
        "DOC-1001-COI",
    }


def test_low_confidence_packet_requires_review() -> None:
    packet = load_packets(FIXTURES)["PKT-1002-REVIEW"]
    decision = evaluate_packet(packet)

    assert decision.status == DecisionStatus.REVIEW_REQUIRED
    assert decision.review_count == 1
    assert decision.findings[0].code == "low_confidence:DOC-1002-INV:amount"


def test_human_confirmation_clears_only_the_review_finding() -> None:
    packet = load_packets(FIXTURES)["PKT-1002-REVIEW"]
    decision = evaluate_packet(packet, {("DOC-1002-INV", "amount")})

    assert decision.status == DecisionStatus.READY_FOR_APPROVAL
    assert not decision.findings


def test_clean_packet_is_ready_but_not_automatically_signed() -> None:
    packet = load_packets(FIXTURES)["PKT-1003-READY"]
    decision = evaluate_packet(packet)

    assert decision.status == DecisionStatus.READY_FOR_APPROVAL
    assert decision.blocker_count == 0
    assert decision.review_count == 0

