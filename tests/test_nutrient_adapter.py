from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from releasegate.adapters.nutrient import (
    NutrientConfigurationError,
    NutrientExtractionClient,
    NutrientProcessorClient,
    _multipart,
    map_extraction_response,
)


def test_client_requires_server_side_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NUTRIENT_EXTRACTION_API_KEY", raising=False)
    monkeypatch.delenv("NUTRIENT_API_KEY", raising=False)
    with pytest.raises(NutrientConfigurationError):
        NutrientProcessorClient()
    with pytest.raises(NutrientConfigurationError):
        NutrientExtractionClient()


def test_multipart_contains_instruction_and_document() -> None:
    document = Path(__file__).resolve().parents[1] / "assets" / "fixtures" / "packets.json"
    body, boundary = _multipart(
        {"instructions": json.dumps({"output": {"type": "json-content"}})},
        {"document": document},
    )

    assert boundary.encode() in body
    assert b'name="instructions"' in body
    assert b'filename="packets.json"' in body
    assert b'"synthetic": true' in body


def test_extraction_response_keeps_value_confidence_page_and_bounds() -> None:
    response = {
        "output": {
            "data": {
                "invoice_number": "NS-1048",
                "total": {"amount": 12850.0, "currency": "USD"},
            },
            "metadata": {
                "invoice_number": {
                    "confidence": 0.98,
                    "pageIndex": 0,
                    "pageNumber": 1,
                    "bbox": {"x": 390, "y": 92, "width": 92, "height": 20},
                },
                "total": {
                    "amount": {
                        "confidence": 0.96,
                        "pageIndex": 0,
                        "pageNumber": 1,
                        "bbox": {"x": 394, "y": 566, "width": 98, "height": 22},
                    },
                    "currency": {
                        "confidence": 0.95,
                        "pageIndex": 0,
                        "pageNumber": 1,
                        "bbox": {"x": 394, "y": 566, "width": 98, "height": 22},
                    },
                },
            },
        }
    }

    fields = map_extraction_response(response)

    assert fields["invoice_number"].value == "NS-1048"
    assert fields["invoice_number"].confidence == pytest.approx(0.98)
    assert fields["invoice_number"].page == 1
    assert fields["invoice_number"].bounds == [390.0, 92.0, 482.0, 112.0]
    assert fields["total.amount"].value == 12850.0
    assert fields["total.currency"].value == "USD"


def test_extraction_response_rejects_missing_grounding_trees() -> None:
    with pytest.raises(Exception, match="missing data or metadata"):
        map_extraction_response({"output": {"data": {"amount": 10}}})


def test_extraction_client_uses_live_proven_endpoint_and_citations() -> None:
    document = (
        Path(__file__).resolve().parents[1]
        / "assets"
        / "demo-documents"
        / "PKT-1001-BLOCKED"
        / "northstar-invoice-1048.pdf"
    )
    response_payload = {
        "output": {
            "data": {"invoice_number": "NS-1048"},
            "metadata": {
                "invoice_number": {
                    "confidence": 0.98,
                    "pageNumber": 1,
                    "bbox": {"x": 390, "y": 92, "width": 92, "height": 20},
                }
            },
        }
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(response_payload).encode("utf-8")

    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse()

    client = NutrientExtractionClient(api_key="test-key-not-a-secret")
    with patch("releasegate.adapters.nutrient.urlopen", side_effect=fake_urlopen):
        fields = client.extract_fields(
            document,
            {"type": "object", "properties": {"invoice_number": {"type": "string"}}},
        )

    request = captured["request"]
    assert request.full_url == "https://api.nutrient.io/extraction/extract"
    assert request.get_header("Authorization") == "Bearer test-key-not-a-secret"
    assert captured["timeout"] == 300
    assert b'name="file"' in request.data
    assert b'"mode":"structure"' in request.data
    assert b'"citationsEnabled":true' in request.data
    assert fields["invoice_number"].value == "NS-1048"
