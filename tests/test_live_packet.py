from __future__ import annotations

from pathlib import Path

from releasegate.adapters.fixture import load_packets
from releasegate.live import extract_and_evaluate_packet
from releasegate.service import default_fixture_path


def test_live_fields_drive_the_five_document_policy() -> None:
    packet = load_packets(default_fixture_path())["PKT-1001-BLOCKED"]
    payload_by_filename = {}
    for document in packet.documents:
        data = {}
        metadata = {}
        for name, field in document.fields.items():
            data[name] = field.value
            x1, y1, x2, y2 = field.bounds
            metadata[name] = {
                "confidence": field.confidence,
                "pageNumber": field.page,
                "bbox": {
                    "x": x1,
                    "y": y1,
                    "width": x2 - x1,
                    "height": y2 - y1,
                },
            }
        payload_by_filename[document.filename] = {
            "requestId": f"req-{document.document_id}",
            "status": 200,
            "output": {"data": data, "metadata": metadata},
        }

    class FakeExtractionClient:
        def __init__(self) -> None:
            self.calls = []

        def extract(self, document, schema, *, mode="structure", timeout=300):
            self.calls.append((Path(document).name, mode, tuple(schema["required"])))
            return payload_by_filename[Path(document).name]

    client = FakeExtractionClient()
    project_root = Path(default_fixture_path()).resolve().parents[2]
    live_packet, proofs, decision = extract_and_evaluate_packet(
        packet,
        client,
        documents_root=project_root / "assets" / "demo-documents" / packet.packet_id,
        schemas_root=project_root / "assets" / "schemas",
    )

    assert len(client.calls) == 5
    assert len(proofs) == 5
    assert all(proof["payload"]["requestId"].startswith("req-") for proof in proofs)
    assert live_packet.documents[0].fields["invoice_number"].value == "NS-1048"
    assert decision["status"] == "blocked"
    assert [finding["code"] for finding in decision["findings"]] == [
        "approval_amount_mismatch",
        "insurance_expired",
    ]
