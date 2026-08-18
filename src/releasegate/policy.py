from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Iterable

from .models import Decision, DecisionStatus, Evidence, Finding, Packet, Severity


POLICY_VERSION = "closeout-policy-2026.08.17"
REQUIRED_DOCUMENTS = {
    "invoice": "Invoice",
    "w9": "W-9",
    "insurance_certificate": "Certificate of insurance",
    "approval": "Payment approval",
    "lien_waiver": "Conditional lien waiver",
}
LOW_CONFIDENCE_THRESHOLD = 0.85


def _business_name(value: object) -> str:
    normalized = re.sub(r"[^a-z0-9 ]+", " ", str(value).casefold())
    words = [word for word in normalized.split() if word not in {"llc", "inc", "corp", "corporation"}]
    return " ".join(words)


def _money(value: object) -> Decimal | None:
    try:
        return Decimal(str(value).replace("$", "").replace(",", "")).quantize(Decimal("0.01"))
    except (InvalidOperation, AttributeError):
        return None


def _available(items: Iterable[Evidence | None]) -> tuple[Evidence, ...]:
    return tuple(item for item in items if item is not None)


def _finding(
    code: str,
    severity: Severity,
    title: str,
    message: str,
    remediation: str,
    evidence: Iterable[Evidence | None] = (),
) -> Finding:
    return Finding(
        code=code,
        severity=severity,
        title=title,
        message=message,
        evidence=_available(evidence),
        remediation=remediation,
    )


def evaluate_packet(packet: Packet, confirmed_fields: set[tuple[str, str]] | None = None) -> Decision:
    confirmed_fields = confirmed_fields or set()
    findings: list[Finding] = []

    for document_type, label in REQUIRED_DOCUMENTS.items():
        if packet.document(document_type) is None:
            findings.append(
                _finding(
                    f"missing_{document_type}",
                    Severity.BLOCKER,
                    f"{label} is missing",
                    f"The packet does not contain the required {label.lower()}.",
                    f"Add a current {label.lower()} before requesting signature.",
                )
            )

    for document in packet.documents:
        for field_name, extracted in document.fields.items():
            if (
                extracted.confidence < LOW_CONFIDENCE_THRESHOLD
                and (document.document_id, field_name) not in confirmed_fields
            ):
                evidence = document.evidence(field_name)
                findings.append(
                    _finding(
                        f"low_confidence:{document.document_id}:{field_name}",
                        Severity.REVIEW,
                        f"Review {field_name.replace('_', ' ')}",
                        f"{document.filename} returned {field_name.replace('_', ' ')} at "
                        f"{extracted.confidence:.0%} confidence.",
                        "A named reviewer must compare the value with the source document and confirm it.",
                        [evidence],
                    )
                )

    invoice = packet.document("invoice")
    w9 = packet.document("w9")
    insurance = packet.document("insurance_certificate")
    approval = packet.document("approval")
    waiver = packet.document("lien_waiver")

    canonical_name_evidence = w9.evidence("legal_name") if w9 else None
    if canonical_name_evidence:
        canonical_name = _business_name(canonical_name_evidence.value)
        for document, field_name in (
            (invoice, "vendor_name"),
            (insurance, "insured_name"),
            (approval, "approved_vendor"),
            (waiver, "claimant_name"),
        ):
            evidence = document.evidence(field_name) if document else None
            if evidence and _business_name(evidence.value) != canonical_name:
                findings.append(
                    _finding(
                        f"vendor_mismatch:{document.document_id}",
                        Severity.BLOCKER,
                        "Vendor identity does not match",
                        f"{document.filename} names “{evidence.value}”, while the W-9 names "
                        f"“{canonical_name_evidence.value}”.",
                        "Replace or correct the mismatched document; this difference cannot be waived by the agent.",
                        [canonical_name_evidence, evidence],
                    )
                )

    project_evidence = [
        document.evidence("project_id")
        for document in (invoice, insurance, approval, waiver)
        if document is not None
    ]
    project_values = {str(item.value).strip().casefold() for item in project_evidence if item}
    if len(project_values) > 1:
        findings.append(
            _finding(
                "project_mismatch",
                Severity.BLOCKER,
                "Project identifiers conflict",
                "The documents do not all identify the same project.",
                "Correct the source documents before release.",
                project_evidence,
            )
        )

    invoice_amount = invoice.evidence("amount") if invoice else None
    approval_amount = approval.evidence("approved_amount") if approval else None
    waiver_amount = waiver.evidence("amount") if waiver else None
    if invoice_amount and approval_amount and _money(invoice_amount.value) != _money(approval_amount.value):
        findings.append(
            _finding(
                "approval_amount_mismatch",
                Severity.BLOCKER,
                "Approved amount does not cover the invoice",
                f"Invoice amount is ${_money(invoice_amount.value):,.2f}; approval is "
                f"${_money(approval_amount.value):,.2f}.",
                "Obtain a corrected approval or revise the invoice.",
                [invoice_amount, approval_amount],
            )
        )
    if invoice_amount and waiver_amount and _money(invoice_amount.value) != _money(waiver_amount.value):
        findings.append(
            _finding(
                "waiver_amount_mismatch",
                Severity.BLOCKER,
                "Lien waiver amount conflicts with the invoice",
                f"Invoice amount is ${_money(invoice_amount.value):,.2f}; waiver amount is "
                f"${_money(waiver_amount.value):,.2f}.",
                "Generate a waiver that matches the supported payment amount.",
                [invoice_amount, waiver_amount],
            )
        )

    expiration = insurance.evidence("policy_expiration") if insurance else None
    if expiration:
        try:
            expired = date.fromisoformat(str(expiration.value)) < date.fromisoformat(packet.evaluation_date)
        except ValueError:
            expired = True
        if expired:
            findings.append(
                _finding(
                    "insurance_expired",
                    Severity.BLOCKER,
                    "Insurance certificate is expired",
                    f"Coverage ended on {expiration.value}; evaluation date is {packet.evaluation_date}.",
                    "Add a current certificate of insurance.",
                    [expiration],
                )
            )

    invoice_number = invoice.evidence("invoice_number") if invoice else None
    if invoice_number and str(invoice_number.value) in packet.previously_paid_invoice_numbers:
        findings.append(
            _finding(
                "duplicate_invoice",
                Severity.BLOCKER,
                "Invoice appears to have been paid already",
                f"Invoice {invoice_number.value} is present in the prior-payment register.",
                "Investigate the prior payment before continuing.",
                [invoice_number],
            )
        )

    blockers = sum(1 for finding in findings if finding.severity == Severity.BLOCKER)
    reviews = sum(1 for finding in findings if finding.severity == Severity.REVIEW)
    status = (
        DecisionStatus.BLOCKED
        if blockers
        else DecisionStatus.REVIEW_REQUIRED
        if reviews
        else DecisionStatus.READY_FOR_APPROVAL
    )
    return Decision(
        packet_id=packet.packet_id,
        status=status,
        findings=tuple(findings),
        checked_documents=len(packet.documents),
        checked_fields=sum(len(document.fields) for document in packet.documents),
        policy_version=POLICY_VERSION,
    )

