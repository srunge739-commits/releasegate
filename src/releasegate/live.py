from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from .adapters.nutrient import NutrientAPIError, map_extraction_response
from .models import DocumentRecord, Packet
from .policy import evaluate_packet


SCHEMA_BY_DOCUMENT_TYPE = {
    "invoice": "invoice.json",
    "w9": "w9.json",
    "insurance_certificate": "insurance-certificate.json",
    "approval": "approval.json",
    "lien_waiver": "lien-waiver.json",
}


class ExtractionClient(Protocol):
    def extract(
        self,
        document: str | Path,
        schema: dict[str, Any],
        *,
        mode: str = "structure",
        timeout: int = 300,
    ) -> dict[str, Any]: ...


def extract_and_evaluate_packet(
    packet: Packet,
    client: ExtractionClient,
    *,
    documents_root: Path,
    schemas_root: Path,
    mode: str = "structure",
) -> tuple[Packet, list[dict[str, Any]], dict[str, Any]]:
    """Extract all packet documents through Nutrient, then run the real policy.

    The fixture packet supplies filenames and non-document context only. Every
    field used in the returned decision comes from the provided extraction
    client. A document with a missing required schema field fails closed.
    """

    live_documents: list[DocumentRecord] = []
    proofs: list[dict[str, Any]] = []

    for document in packet.documents:
        try:
            schema_filename = SCHEMA_BY_DOCUMENT_TYPE[document.document_type]
        except KeyError as exc:
            raise NutrientAPIError(
                f"No live extraction schema for document type {document.document_type}."
            ) from exc

        document_path = documents_root / document.filename
        schema_path = schemas_root / schema_filename
        if not document_path.is_file():
            raise FileNotFoundError(document_path)
        if not schema_path.is_file():
            raise FileNotFoundError(schema_path)

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        payload = client.extract(document_path, schema, mode=mode)
        fields = map_extraction_response(payload)
        required = set(schema.get("required", []))
        missing = sorted(required - set(fields))
        if missing:
            raise NutrientAPIError(
                f"Nutrient did not return required fields for {document.filename}: "
                + ", ".join(missing)
            )

        live_documents.append(
            DocumentRecord(
                document_id=document.document_id,
                document_type=document.document_type,
                filename=document.filename,
                fields=fields,
            )
        )
        proofs.append(
            {
                "document": str(document_path),
                "schema": str(schema_path),
                "payload": payload,
            }
        )

    live_packet = Packet(
        packet_id=packet.packet_id,
        title=packet.title,
        scenario=packet.scenario,
        evaluation_date=packet.evaluation_date,
        documents=tuple(live_documents),
        previously_paid_invoice_numbers=packet.previously_paid_invoice_numbers,
    )
    decision = evaluate_packet(live_packet).to_dict()
    return live_packet, proofs, decision
