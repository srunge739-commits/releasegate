from __future__ import annotations

import pytest

from releasegate.server import sanitize_live_proof


def sample_proof() -> dict[str, object]:
    return {
        "result_kind": "live_nutrient_packet_evaluation",
        "recorded_at": "2026-08-18T17:16:24+00:00",
        "packet_id": "PKT-TEST",
        "requested_mode": "structure",
        "documents": [
            {
                "result_kind": "live_nutrient_extraction",
                "document": "synthetic-invoice.pdf",
                "schema": "invoice.json",
                "request_id": "request-123",
                "vendor_status": 200,
                "api_version": "2026-05-25",
                "metrics": {"pagesProcessed": 1, "processingTimeMs": 250},
                "fields": {
                    "amount": {
                        "value": 125,
                        "confidence": 0.96,
                        "page": 1,
                        "bounds": [1, 2, 3, 4],
                    }
                },
                "raw_response": {"must": "not leak"},
            }
        ],
        "decision": {
            "packet_id": "PKT-TEST",
            "status": "blocked",
            "blocker_count": 1,
            "review_count": 0,
            "policy_version": "test-policy",
            "findings": [
                {
                    "code": "amount_mismatch",
                    "severity": "blocker",
                    "title": "Amount mismatch",
                    "message": "Amounts differ.",
                    "remediation": "Correct the source.",
                    "evidence": [
                        {
                            "document_id": "DOC-1",
                            "document_type": "invoice",
                            "filename": "synthetic-invoice.pdf",
                            "field": "amount",
                            "value": 125,
                            "confidence": 0.96,
                            "page": 1,
                            "bounds": [1, 2, 3, 4],
                        }
                    ],
                }
            ],
        },
        "api_key": "must-not-leak",
    }


def test_sanitize_live_proof_computes_summary_and_allow_lists_output() -> None:
    result = sanitize_live_proof(sample_proof())

    assert result["available"] is True
    assert result["summary"] == {
        "documents": 1,
        "fields": 1,
        "successful_requests": 1,
        "total_processing_time_ms": 250,
        "status": "blocked",
        "finding_codes": ["amount_mismatch"],
    }
    assert result["documents"][0]["request_id"] == "request-123"
    assert "api_key" not in result
    assert "raw_response" not in result["documents"][0]


def test_sanitize_live_proof_rejects_mismatched_packet_ids() -> None:
    payload = sample_proof()
    payload["decision"]["packet_id"] = "DIFFERENT"

    with pytest.raises(ValueError, match="identifiers"):
        sanitize_live_proof(payload)
