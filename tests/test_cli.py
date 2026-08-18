from __future__ import annotations

from releasegate.cli import build_live_proof


def test_live_proof_is_identified_and_keeps_vendor_traceability() -> None:
    payload = {
        "requestId": "req-test-123",
        "status": 200,
        "configuration": {"apiVersion": "2026-05-25"},
        "metrics": {"pagesProcessed": 1, "processingTimeMs": 420},
        "output": {
            "data": {"invoice_number": "NS-1048"},
            "metadata": {
                "invoice_number": {
                    "confidence": 0.98,
                    "pageNumber": 1,
                    "bbox": {"x": 390, "y": 92, "width": 92, "height": 20},
                }
            },
        },
    }

    result = build_live_proof(
        payload,
        document="northstar-invoice-1048.pdf",
        schema="invoice.json",
        mode="structure",
    )

    assert result["result_kind"] == "live_nutrient_extraction"
    assert result["request_id"] == "req-test-123"
    assert result["api_version"] == "2026-05-25"
    assert result["metrics"]["pagesProcessed"] == 1
    assert len(result["vendor_response_sha256"]) == 64
    assert result["fields"]["invoice_number"] == {
        "value": "NS-1048",
        "confidence": 0.98,
        "page": 1,
        "bounds": [390.0, 92.0, 482.0, 112.0],
    }
