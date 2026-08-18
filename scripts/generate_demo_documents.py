from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = PROJECT_ROOT / "assets" / "fixtures" / "packets.json"
OUTPUT_ROOT = PROJECT_ROOT / "assets" / "demo-documents"


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf_bytes(title: str, lines: list[str]) -> bytes:
    commands = ["BT", "/F1 15 Tf", "72 742 Td", f"({_escape(title)}) Tj", "/F1 10 Tf"]
    for line in lines:
        commands.extend(["0 -24 Td", f"({_escape(line)}) Tj"])
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode())
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(output)


def main() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    count = 0
    for packet in payload["packets"]:
        packet_dir = OUTPUT_ROOT / packet["packet_id"]
        packet_dir.mkdir(parents=True, exist_ok=True)
        for document in packet["documents"]:
            lines = [
                "SYNTHETIC HACKATHON DEMONSTRATION - NOT A REAL BUSINESS RECORD",
                f"Packet: {packet['packet_id']}",
                f"Document type: {document['document_type'].replace('_', ' ').title()}",
                "",
            ]
            lines.extend(
                f"{name.replace('_', ' ').title()}: {field['value']}"
                for name, field in document["fields"].items()
            )
            output = packet_dir / document["filename"]
            output.write_bytes(_pdf_bytes(document["document_type"].replace("_", " ").title(), lines))
            count += 1
    print(f"generated {count} synthetic PDF documents under {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
