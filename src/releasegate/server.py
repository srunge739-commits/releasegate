from __future__ import annotations

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .adapters.fixture import load_packets
from .service import ReleaseGateError, ReleaseGateService, default_fixture_path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "web"
LIVE_PROOF_ROOT = PROJECT_ROOT / "artifacts" / "live"
BUNDLED_PROOF_ROOT = PROJECT_ROOT / "assets" / "proofs"


def _safe_field(field: object) -> dict[str, object]:
    if not isinstance(field, dict):
        raise ValueError("Live proof contains an invalid field record.")
    value = field.get("value")
    if not isinstance(value, (str, int, float, bool)) and value is not None:
        value = str(value)
    bounds = field.get("bounds", [])
    if not isinstance(bounds, list):
        bounds = []
    return {
        "value": value,
        "confidence": float(field.get("confidence", 0)),
        "page": int(field.get("page", 0)),
        "bounds": [float(item) for item in bounds if isinstance(item, (int, float))],
    }


def _safe_evidence(item: object) -> dict[str, object]:
    if not isinstance(item, dict):
        raise ValueError("Live proof contains invalid finding evidence.")
    field = _safe_field(item)
    return {
        "document_id": str(item.get("document_id", "")),
        "document_type": str(item.get("document_type", "")),
        "filename": str(item.get("filename", "")),
        "field": str(item.get("field", "")),
        **field,
    }


def sanitize_live_proof(payload: object) -> dict[str, object]:
    """Return the allow-listed fields needed for a read-only live-proof replay."""
    if not isinstance(payload, dict) or payload.get("result_kind") != "live_nutrient_packet_evaluation":
        raise ValueError("File is not a ReleaseGate live Nutrient packet proof.")

    documents = payload.get("documents")
    decision = payload.get("decision")
    if not isinstance(documents, list) or not documents or not isinstance(decision, dict):
        raise ValueError("Live proof is missing documents or a decision.")

    safe_documents: list[dict[str, object]] = []
    for document in documents:
        if not isinstance(document, dict) or document.get("result_kind") != "live_nutrient_extraction":
            raise ValueError("Live proof contains an invalid extraction record.")
        fields = document.get("fields")
        metrics = document.get("metrics", {})
        if not isinstance(fields, dict) or not isinstance(metrics, dict):
            raise ValueError("Live extraction is missing fields or metrics.")
        safe_documents.append(
            {
                "filename": str(document.get("document", "")),
                "schema": str(document.get("schema", "")),
                "request_id": str(document.get("request_id", "")),
                "vendor_status": int(document.get("vendor_status", 0)),
                "api_version": str(document.get("api_version", "")),
                "metrics": {
                    "pages_processed": int(metrics.get("pagesProcessed", 0)),
                    "processing_time_ms": int(metrics.get("processingTimeMs", 0)),
                },
                "fields": {str(name): _safe_field(field) for name, field in fields.items()},
            }
        )

    findings = decision.get("findings", [])
    if not isinstance(findings, list):
        raise ValueError("Live decision contains invalid findings.")
    safe_findings: list[dict[str, object]] = []
    for finding in findings:
        if not isinstance(finding, dict):
            raise ValueError("Live decision contains an invalid finding.")
        evidence = finding.get("evidence", [])
        if not isinstance(evidence, list):
            raise ValueError("Live finding contains invalid evidence.")
        safe_findings.append(
            {
                "code": str(finding.get("code", "")),
                "severity": str(finding.get("severity", "")),
                "title": str(finding.get("title", "")),
                "message": str(finding.get("message", "")),
                "remediation": str(finding.get("remediation", "")),
                "evidence": [_safe_evidence(item) for item in evidence],
            }
        )

    packet_id = str(payload.get("packet_id", ""))
    if not packet_id or str(decision.get("packet_id", "")) != packet_id:
        raise ValueError("Live proof packet identifiers do not agree.")
    safe_decision = {
        "packet_id": packet_id,
        "status": str(decision.get("status", "")),
        "blocker_count": int(decision.get("blocker_count", 0)),
        "review_count": int(decision.get("review_count", 0)),
        "checked_documents": len(safe_documents),
        "checked_fields": sum(len(document["fields"]) for document in safe_documents),
        "policy_version": str(decision.get("policy_version", "")),
        "findings": safe_findings,
    }
    successful_requests = sum(document["vendor_status"] == 200 for document in safe_documents)
    return {
        "available": True,
        "recorded_at": str(payload.get("recorded_at", "")),
        "packet_id": packet_id,
        "mode": str(payload.get("requested_mode", "")),
        "summary": {
            "documents": len(safe_documents),
            "fields": safe_decision["checked_fields"],
            "successful_requests": successful_requests,
            "total_processing_time_ms": sum(
                document["metrics"]["processing_time_ms"] for document in safe_documents
            ),
            "status": safe_decision["status"],
            "finding_codes": [finding["code"] for finding in safe_findings],
        },
        "documents": safe_documents,
        "decision": safe_decision,
    }


def load_latest_live_proof(directory: Path | None = None) -> dict[str, object]:
    """Load a valid proof from the private artifact directory or reviewed bundle."""
    directories = (directory,) if directory is not None else (LIVE_PROOF_ROOT, BUNDLED_PROOF_ROOT)
    for proof_root in directories:
        if not proof_root.is_dir():
            continue
        for candidate in sorted(proof_root.glob("northstar-packet-*.json"), reverse=True):
            try:
                proof = sanitize_live_proof(json.loads(candidate.read_text(encoding="utf-8")))
                proof["proof_file"] = candidate.name
                return proof
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
    return {"available": False}


def make_handler(service: ReleaseGateService) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "ReleaseGate/0.1"

        def log_message(self, format: str, *args: object) -> None:
            return

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            try:
                if path == "/api/health":
                    self._json(
                        {
                            "ok": True,
                            "mode": "fixture_with_read_only_live_proof",
                            "live_proof_available": load_latest_live_proof().get("available", False),
                            "version": "0.1.0",
                        }
                    )
                elif path == "/api/live-proof":
                    self._json(load_latest_live_proof())
                elif path == "/api/packets":
                    self._json({"packets": service.list_packets()})
                elif path == "/api/audit/verify":
                    self._json(service.audit.verify())
                elif path.startswith("/api/packets/") and path.endswith("/audit"):
                    packet_id = path.split("/")[3]
                    self._json({"events": service.audit_for_packet(packet_id), "chain": service.audit.verify()})
                elif path.startswith("/api/packets/"):
                    packet_id = path.split("/")[3]
                    self._json(service.packet_detail(packet_id))
                else:
                    self._static(path)
            except ReleaseGateError as exc:
                self._json({"error": str(exc)}, HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            try:
                payload = self._body()
                if path.startswith("/api/packets/") and path.endswith("/evaluate"):
                    packet_id = path.split("/")[3]
                    self._json(service.evaluate(packet_id))
                elif path.startswith("/api/packets/") and path.endswith("/review"):
                    packet_id = path.split("/")[3]
                    self._json(
                        service.confirm_field(
                            packet_id,
                            document_id=str(payload.get("document_id", "")),
                            field_name=str(payload.get("field", "")),
                            reviewer=str(payload.get("reviewer", "")),
                            reason=str(payload.get("reason", "")),
                        )
                    )
                elif path.startswith("/api/packets/") and path.endswith("/signature"):
                    packet_id = path.split("/")[3]
                    self._json(
                        service.request_signature(
                            packet_id,
                            reviewer=str(payload.get("reviewer", "")),
                            reason=str(payload.get("reason", "")),
                        )
                    )
                else:
                    self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            except (ReleaseGateError, json.JSONDecodeError) as exc:
                self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

        def _body(self) -> dict[str, object]:
            length = int(self.headers.get("Content-Length", "0"))
            if length == 0:
                return {}
            return json.loads(self.rfile.read(length).decode("utf-8"))

        def _json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload, indent=2, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _static(self, path: str) -> None:
            relative = "index.html" if path in {"", "/"} else path.lstrip("/")
            candidate = (WEB_ROOT / relative).resolve()
            if WEB_ROOT.resolve() not in candidate.parents and candidate != WEB_ROOT.resolve():
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            if not candidate.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            body = candidate.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mimetypes.guess_type(candidate.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local ReleaseGate demonstration.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address; defaults to localhost only.")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--fixtures", type=Path, default=default_fixture_path())
    args = parser.parse_args()

    service = ReleaseGateService(load_packets(args.fixtures))
    server = ThreadingHTTPServer((args.host, args.port), make_handler(service))
    live_status = "available" if load_latest_live_proof().get("available") else "not found"
    print(f"ReleaseGate demo: http://{args.host}:{args.port}")
    print(f"Fixture scenarios enabled; read-only genuine Nutrient proof: {live_status}.")
    print("No documents, emails, payments, or signatures can leave this process. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
