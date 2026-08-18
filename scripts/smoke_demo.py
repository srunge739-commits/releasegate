from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from releasegate.adapters.fixture import load_packets
from releasegate.service import ReleaseGateService, default_fixture_path


def main() -> None:
    service = ReleaseGateService(load_packets(default_fixture_path()))

    blocked = service.evaluate("PKT-1001-BLOCKED")
    review = service.evaluate("PKT-1002-REVIEW")
    after_review = service.confirm_field(
        "PKT-1002-REVIEW",
        document_id="DOC-1002-INV",
        field_name="amount",
        reviewer="Demo Reviewer",
        reason="Compared the highlighted total to the synthetic source PDF.",
    )
    signature = service.request_signature(
        "PKT-1002-REVIEW",
        reviewer="Demo Approver",
        reason="Fixture packet passed policy after source review.",
    )
    audit = service.audit.verify()

    result = {
        "synthetic_demo": True,
        "blocked_status": blocked["status"],
        "blocked_findings": [finding["code"] for finding in blocked["findings"]],
        "initial_review_status": review["status"],
        "after_human_review": after_review["status"],
        "signature_status": signature["envelope"]["status"],
        "signature_provider": signature["envelope"]["provider"],
        "audit_valid": audit["valid"],
        "audit_events": audit["events"],
    }
    print(json.dumps(result, indent=2))

    assert result["blocked_status"] == "blocked"
    assert result["blocked_findings"] == [
        "approval_amount_mismatch",
        "insurance_expired",
    ]
    assert result["initial_review_status"] == "review_required"
    assert result["after_human_review"] == "ready_for_approval"
    assert result["signature_status"] == "prepared_not_sent"
    assert result["audit_valid"] is True


if __name__ == "__main__":
    main()
