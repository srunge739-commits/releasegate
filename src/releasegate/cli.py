from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .adapters.fixture import load_packets
from .adapters.nutrient import NutrientExtractionClient, map_extraction_response
from .live import extract_and_evaluate_packet
from .server import main as serve
from .service import ReleaseGateService, default_fixture_path


def build_live_proof(
    payload: dict,
    *,
    document: str,
    schema: str,
    mode: str,
) -> dict:
    fields = map_extraction_response(payload)
    canonical_response = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return {
        "result_kind": "live_nutrient_extraction",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "document": Path(document).name,
        "schema": Path(schema).name,
        "requested_mode": mode,
        "request_id": payload.get("requestId"),
        "vendor_status": payload.get("status"),
        "api_version": payload.get("configuration", {}).get("apiVersion"),
        "metrics": payload.get("metrics", {}),
        "vendor_response_sha256": hashlib.sha256(canonical_response).hexdigest(),
        "fields": {
            field: {
                "value": item.value,
                "confidence": item.confidence,
                "page": item.page,
                "bounds": item.bounds,
            }
            for field, item in fields.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="ReleaseGate evidence-first closeout controls")
    subparsers = parser.add_subparsers(dest="command", required=True)

    evaluate_parser = subparsers.add_parser("evaluate", help="Evaluate a deterministic demo packet")
    evaluate_parser.add_argument("packet_id")

    extract_parser = subparsers.add_parser("extract-live", help="Call Nutrient DWS for one document")
    extract_parser.add_argument("document")
    extract_parser.add_argument(
        "--schema",
        required=True,
        help="JSON Schema describing the fields to extract",
    )
    extract_parser.add_argument(
        "--mode",
        choices=("text", "structure", "understand", "agentic"),
        default="structure",
    )
    extract_parser.add_argument(
        "--output",
        help="Optional path for a sanitized proof record; existing files are never overwritten",
    )

    packet_parser = subparsers.add_parser(
        "evaluate-live-packet",
        help="Extract all five documents through Nutrient and run the closeout policy",
    )
    packet_parser.add_argument("packet_id")
    packet_parser.add_argument(
        "--mode",
        choices=("structure", "understand", "agentic"),
        default="structure",
    )
    packet_parser.add_argument(
        "--output",
        required=True,
        help="Path for the sanitized live packet proof; existing files are never overwritten",
    )

    subparsers.add_parser("serve", help="Run the local web demonstration")
    args, remaining = parser.parse_known_args()

    if args.command == "serve":
        import sys

        sys.argv = [sys.argv[0], *remaining]
        serve()
        return
    if args.command == "extract-live":
        with open(args.schema, encoding="utf-8") as schema_file:
            schema = json.load(schema_file)
        payload = NutrientExtractionClient().extract(
            args.document,
            schema,
            mode=args.mode,
        )
        result = build_live_proof(
            payload,
            document=args.document,
            schema=args.schema,
            mode=args.mode,
        )
        rendered = json.dumps(result, indent=2)
        print(rendered)
        if args.output:
            output_path = write_new_proof(args.output, rendered)
            print(f"Saved sanitized live proof to {output_path}")
        return

    if args.command == "evaluate-live-packet":
        packets = load_packets(default_fixture_path())
        try:
            packet = packets[args.packet_id]
        except KeyError as exc:
            raise SystemExit(f"Unknown packet: {args.packet_id}") from exc
        project_root = Path(__file__).resolve().parents[2]
        documents_root = project_root / "assets" / "demo-documents" / packet.packet_id
        schemas_root = project_root / "assets" / "schemas"
        _, extraction_proofs, decision = extract_and_evaluate_packet(
            packet,
            NutrientExtractionClient(),
            documents_root=documents_root,
            schemas_root=schemas_root,
            mode=args.mode,
        )
        result = {
            "result_kind": "live_nutrient_packet_evaluation",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "packet_id": packet.packet_id,
            "requested_mode": args.mode,
            "documents": [
                build_live_proof(
                    proof["payload"],
                    document=proof["document"],
                    schema=proof["schema"],
                    mode=args.mode,
                )
                for proof in extraction_proofs
            ],
            "decision": decision,
        }
        rendered = json.dumps(result, indent=2)
        print(rendered)
        output_path = write_new_proof(args.output, rendered)
        print(f"Saved sanitized live packet proof to {output_path}")
        return

    service = ReleaseGateService(load_packets(default_fixture_path()))
    print(json.dumps(service.evaluate(args.packet_id), indent=2))


def write_new_proof(path: str | Path, rendered: str) -> Path:
    output_path = Path(path)
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing live proof: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered + "\n", encoding="utf-8")
    return output_path


if __name__ == "__main__":
    main()
