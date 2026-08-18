from __future__ import annotations

import json
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..models import ExtractedField


class NutrientConfigurationError(RuntimeError):
    pass


class NutrientAPIError(RuntimeError):
    pass


def _multipart(fields: dict[str, str], files: dict[str, Path]) -> tuple[bytes, str]:
    boundary = f"----releasegate-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )
    for name, path in files.items():
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'.encode(),
                f"Content-Type: {content_type}\r\n\r\n".encode(),
                path.read_bytes(),
                b"\r\n",
            ]
        )
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), boundary


class NutrientProcessorClient:
    """Minimal DWS Processor client using only Python's standard library.

    The client intentionally keeps credentials server-side and never logs them.
    It is usable once the participant supplies a NUTRIENT_API_KEY.
    """

    def __init__(self, api_key: str | None = None, endpoint: str = "https://api.nutrient.io/build") -> None:
        self.api_key = api_key or os.getenv("NUTRIENT_API_KEY")
        self.endpoint = endpoint
        if not self.api_key:
            raise NutrientConfigurationError(
                "NUTRIENT_API_KEY is not configured; fixture mode remains available."
            )

    def extract_key_values(self, document: str | Path, timeout: int = 60) -> dict[str, Any]:
        path = Path(document)
        if not path.is_file():
            raise FileNotFoundError(path)
        instructions = {
            "parts": [{"file": "document"}],
            "output": {"type": "json-content", "keyValuePairs": True, "plainText": True},
        }
        body, boundary = _multipart(
            {"instructions": json.dumps(instructions, separators=(",", ":"))},
            {"document": path},
        )
        request = Request(
            self.endpoint,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Accept": "application/json",
                "User-Agent": "ReleaseGate/0.1",
            },
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise NutrientAPIError(f"Nutrient DWS returned HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise NutrientAPIError(f"Nutrient DWS could not be reached: {exc.reason}") from exc


def _bbox_to_bounds(bbox: Any) -> list[float]:
    if not isinstance(bbox, dict):
        return []
    try:
        x = float(bbox["x"])
        y = float(bbox["y"])
        width = float(bbox["width"])
        height = float(bbox["height"])
    except (KeyError, TypeError, ValueError):
        return []
    return [x, y, x + width, y + height]


def map_extraction_response(payload: dict[str, Any]) -> dict[str, ExtractedField]:
    """Map Nutrient's schema extraction response to ReleaseGate evidence fields.

    Nutrient returns values in ``output.data`` and a parallel metadata tree in
    ``output.metadata``. This walker keeps the schema path, confidence, page,
    and source rectangle together. Nested objects use dot paths and array items
    use bracket indexes so no citation is silently discarded.
    """

    output = payload.get("output")
    if not isinstance(output, dict):
        raise NutrientAPIError("Nutrient extraction response is missing output.")
    data = output.get("data")
    metadata = output.get("metadata")
    if not isinstance(data, (dict, list)) or not isinstance(metadata, (dict, list)):
        raise NutrientAPIError("Nutrient extraction response is missing data or metadata.")

    mapped: dict[str, ExtractedField] = {}

    def walk(value: Any, meta: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_meta = meta.get(key, {}) if isinstance(meta, dict) else {}
                child_path = f"{path}.{key}" if path else key
                walk(child, child_meta, child_path)
            return
        if isinstance(value, list):
            meta_items = meta if isinstance(meta, list) else []
            for index, child in enumerate(value):
                child_meta = meta_items[index] if index < len(meta_items) else {}
                walk(child, child_meta, f"{path}[{index}]")
            return
        if not path or not isinstance(meta, dict):
            return
        confidence = meta.get("confidence", 0.0)
        page_number = meta.get("pageNumber")
        if page_number is None:
            page_number = int(meta.get("pageIndex", 0)) + 1
        try:
            confidence_value = float(confidence)
            page_value = int(page_number)
        except (TypeError, ValueError) as exc:
            raise NutrientAPIError(f"Invalid citation metadata for field {path}.") from exc
        mapped[path] = ExtractedField(
            value=value,
            confidence=confidence_value,
            page=page_value,
            bounds=_bbox_to_bounds(meta.get("bbox")),
        )

    walk(data, metadata, "")
    return mapped


class NutrientExtractionClient:
    """Credential-safe client for Nutrient's schema Data Extraction API."""

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str = "https://api.nutrient.io/extraction/extract",
    ) -> None:
        self.api_key = (
            api_key
            or os.getenv("NUTRIENT_EXTRACTION_API_KEY")
            or os.getenv("NUTRIENT_API_KEY")
        )
        self.endpoint = endpoint
        if not self.api_key:
            raise NutrientConfigurationError(
                "NUTRIENT_EXTRACTION_API_KEY is not configured; fixture mode remains available."
            )

    def extract(
        self,
        document: str | Path,
        schema: dict[str, Any],
        *,
        mode: str = "structure",
        timeout: int = 300,
    ) -> dict[str, Any]:
        path = Path(document)
        if not path.is_file():
            raise FileNotFoundError(path)
        if mode not in {"text", "structure", "understand", "agentic"}:
            raise ValueError(f"Unsupported Nutrient extraction mode: {mode}")
        instructions = {
            "mode": mode,
            "schema": schema,
            "citationsEnabled": True,
        }
        body, boundary = _multipart(
            {"instructions": json.dumps(instructions, separators=(",", ":"))},
            {"file": path},
        )
        request = Request(
            self.endpoint,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Accept": "application/json",
                "User-Agent": "ReleaseGate/0.1",
            },
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            # Do not echo arbitrary response bodies: a vendor response may contain
            # uploaded document text. Status and request ID are enough to debug.
            request_id = exc.headers.get("x-request-id", "not-provided")
            raise NutrientAPIError(
                f"Nutrient extraction returned HTTP {exc.code} (request {request_id})."
            ) from exc
        except URLError as exc:
            raise NutrientAPIError(f"Nutrient extraction could not be reached: {exc.reason}") from exc
        if not isinstance(payload, dict):
            raise NutrientAPIError("Nutrient extraction response was not a JSON object.")
        return payload

    def extract_fields(
        self,
        document: str | Path,
        schema: dict[str, Any],
        *,
        mode: str = "structure",
        timeout: int = 300,
    ) -> dict[str, ExtractedField]:
        return map_extraction_response(
            self.extract(document, schema, mode=mode, timeout=timeout)
        )
