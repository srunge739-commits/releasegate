from __future__ import annotations

import json
from pathlib import Path

from ..models import DocumentRecord, ExtractedField, Packet


def load_packets(path: str | Path) -> dict[str, Packet]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    packets: dict[str, Packet] = {}
    for item in payload["packets"]:
        documents = []
        for raw_document in item["documents"]:
            fields = {
                name: ExtractedField(
                    value=value["value"],
                    confidence=float(value["confidence"]),
                    page=int(value.get("page", 1)),
                    bounds=list(value.get("bounds", [])),
                )
                for name, value in raw_document["fields"].items()
            }
            documents.append(
                DocumentRecord(
                    document_id=raw_document["document_id"],
                    document_type=raw_document["document_type"],
                    filename=raw_document["filename"],
                    fields=fields,
                )
            )
        packet = Packet(
            packet_id=item["packet_id"],
            title=item["title"],
            scenario=item["scenario"],
            evaluation_date=item["evaluation_date"],
            documents=tuple(documents),
            previously_paid_invoice_numbers=tuple(item.get("previously_paid_invoice_numbers", [])),
        )
        packets[packet.packet_id] = packet
    return packets

