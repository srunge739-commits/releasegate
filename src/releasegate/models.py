from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Severity(StrEnum):
    BLOCKER = "blocker"
    REVIEW = "review"
    INFO = "info"


class DecisionStatus(StrEnum):
    BLOCKED = "blocked"
    REVIEW_REQUIRED = "review_required"
    READY_FOR_APPROVAL = "ready_for_approval"


@dataclass(frozen=True)
class Evidence:
    document_id: str
    document_type: str
    filename: str
    field: str
    value: Any
    confidence: float
    page: int
    bounds: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExtractedField:
    value: Any
    confidence: float
    page: int = 1
    bounds: list[float] = field(default_factory=list)


@dataclass(frozen=True)
class DocumentRecord:
    document_id: str
    document_type: str
    filename: str
    fields: dict[str, ExtractedField]

    def evidence(self, field_name: str) -> Evidence | None:
        extracted = self.fields.get(field_name)
        if extracted is None:
            return None
        return Evidence(
            document_id=self.document_id,
            document_type=self.document_type,
            filename=self.filename,
            field=field_name,
            value=extracted.value,
            confidence=extracted.confidence,
            page=extracted.page,
            bounds=extracted.bounds,
        )


@dataclass(frozen=True)
class Packet:
    packet_id: str
    title: str
    scenario: str
    evaluation_date: str
    documents: tuple[DocumentRecord, ...]
    previously_paid_invoice_numbers: tuple[str, ...] = ()

    def document(self, document_type: str) -> DocumentRecord | None:
        return next(
            (document for document in self.documents if document.document_type == document_type),
            None,
        )


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    title: str
    message: str
    evidence: tuple[Evidence, ...]
    remediation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "evidence": [item.to_dict() for item in self.evidence],
            "remediation": self.remediation,
        }


@dataclass(frozen=True)
class Decision:
    packet_id: str
    status: DecisionStatus
    findings: tuple[Finding, ...]
    checked_documents: int
    checked_fields: int
    policy_version: str

    @property
    def blocker_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == Severity.BLOCKER)

    @property
    def review_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == Severity.REVIEW)

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "status": self.status.value,
            "blocker_count": self.blocker_count,
            "review_count": self.review_count,
            "checked_documents": self.checked_documents,
            "checked_fields": self.checked_fields,
            "policy_version": self.policy_version,
            "findings": [finding.to_dict() for finding in self.findings],
        }

