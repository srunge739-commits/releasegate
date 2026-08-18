from __future__ import annotations

from pathlib import Path
from typing import Any

from .audit import AuditLedger
from .models import DecisionStatus, Packet
from .policy import evaluate_packet
from .signatures import FixtureSignatureGateway


class ReleaseGateError(RuntimeError):
    pass


class ReleaseGateService:
    def __init__(self, packets: dict[str, Packet], signature_gateway: FixtureSignatureGateway | None = None) -> None:
        self.packets = packets
        self.audit = AuditLedger()
        self.signature_gateway = signature_gateway or FixtureSignatureGateway()
        self.confirmed_fields: dict[str, set[tuple[str, str]]] = {
            packet_id: set() for packet_id in packets
        }

    def list_packets(self) -> list[dict[str, Any]]:
        return [
            {
                "packet_id": packet.packet_id,
                "title": packet.title,
                "scenario": packet.scenario,
                "documents": len(packet.documents),
            }
            for packet in self.packets.values()
        ]

    def packet_detail(self, packet_id: str) -> dict[str, Any]:
        packet = self._packet(packet_id)
        return {
            "packet_id": packet.packet_id,
            "title": packet.title,
            "scenario": packet.scenario,
            "evaluation_date": packet.evaluation_date,
            "documents": [
                {
                    "document_id": document.document_id,
                    "document_type": document.document_type,
                    "filename": document.filename,
                    "fields": {
                        field_name: {
                            "value": value.value,
                            "confidence": value.confidence,
                            "page": value.page,
                            "bounds": value.bounds,
                            "human_confirmed": (document.document_id, field_name)
                            in self.confirmed_fields[packet_id],
                        }
                        for field_name, value in document.fields.items()
                    },
                }
                for document in packet.documents
            ],
        }

    def evaluate(self, packet_id: str, actor: str = "releasegate-policy") -> dict[str, Any]:
        packet = self._packet(packet_id)
        decision = evaluate_packet(packet, self.confirmed_fields[packet_id])
        result = decision.to_dict()
        event = self.audit.append(
            action="packet_evaluated",
            actor=actor,
            packet_id=packet_id,
            payload={
                "status": result["status"],
                "blocker_count": result["blocker_count"],
                "review_count": result["review_count"],
                "finding_codes": [finding["code"] for finding in result["findings"]],
                "policy_version": result["policy_version"],
            },
        )
        result["audit_event"] = event
        return result

    def confirm_field(
        self,
        packet_id: str,
        *,
        document_id: str,
        field_name: str,
        reviewer: str,
        reason: str,
    ) -> dict[str, Any]:
        packet = self._packet(packet_id)
        if not reviewer.strip() or not reason.strip():
            raise ReleaseGateError("Reviewer and review reason are required.")
        document = next((item for item in packet.documents if item.document_id == document_id), None)
        if document is None or field_name not in document.fields:
            raise ReleaseGateError("The requested evidence field does not exist.")
        self.confirmed_fields[packet_id].add((document_id, field_name))
        evidence = document.evidence(field_name)
        self.audit.append(
            action="field_confirmed",
            actor=reviewer.strip(),
            packet_id=packet_id,
            payload={
                "document_id": document_id,
                "field": field_name,
                "observed_value": evidence.value if evidence else None,
                "reason": reason.strip(),
            },
        )
        return self.evaluate(packet_id, actor=reviewer.strip())

    def request_signature(self, packet_id: str, *, reviewer: str, reason: str) -> dict[str, Any]:
        if not reviewer.strip() or not reason.strip():
            raise ReleaseGateError("A named human approver and approval reason are required.")
        packet = self._packet(packet_id)
        decision = evaluate_packet(packet, self.confirmed_fields[packet_id])
        if decision.status != DecisionStatus.READY_FOR_APPROVAL:
            raise ReleaseGateError(
                f"Signature is blocked: packet status is {decision.status.value}. Resolve the findings first."
            )
        self.audit.append(
            action="human_release_approved",
            actor=reviewer.strip(),
            packet_id=packet_id,
            payload={"reason": reason.strip(), "policy_version": decision.policy_version},
        )
        envelope = self.signature_gateway.create(
            packet_id=packet_id,
            actor=reviewer.strip(),
            reason=reason.strip(),
        )
        event = self.audit.append(
            action="signature_prepared",
            actor=reviewer.strip(),
            packet_id=packet_id,
            payload={
                "envelope_id": envelope["envelope_id"],
                "provider": envelope["provider"],
                "status": envelope["status"],
            },
        )
        return {"envelope": envelope, "audit_event": event}

    def audit_for_packet(self, packet_id: str) -> list[dict[str, Any]]:
        self._packet(packet_id)
        return [event for event in self.audit.events if event["packet_id"] == packet_id]

    def _packet(self, packet_id: str) -> Packet:
        try:
            return self.packets[packet_id]
        except KeyError as exc:
            raise ReleaseGateError(f"Unknown packet: {packet_id}") from exc


def default_fixture_path() -> Path:
    return Path(__file__).resolve().parents[2] / "assets" / "fixtures" / "packets.json"

