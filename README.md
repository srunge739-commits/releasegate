# ReleaseGate

**Stop unsupported subcontractor payments before a lien waiver is signed.**

ReleaseGate is an evidence-first closeout-packet reviewer for construction payment operations. It cross-checks an invoice, W-9, insurance certificate, payment approval, and conditional lien waiver; cites the exact document field behind every finding; routes uncertain evidence to a named human; and refuses to prepare a signature request while hard conflicts remain.

> Status: working deterministic demonstration plus a genuine five-document Nutrient Data Extraction validation captured locally on August 18, 2026. All documents and business identities are synthetic. The signature gateway is deliberately non-sending until a reviewed live provider is configured.

## Why this matters

A five-document closeout packet can look complete while still containing an expired insurance certificate, a mismatched approval amount, a duplicate invoice, or a low-confidence extracted value. Ordinary document chat can summarize the packet without establishing whether it is safe to release.

ReleaseGate separates three decisions:

1. **Blocked:** a source-document conflict must be corrected.
2. **Review required:** the documents agree, but extraction confidence is too low for unattended action.
3. **Ready for approval:** automated checks passed, but a named person must still approve before signature preparation.

Every decision is source-grounded and written to a tamper-evident audit chain.

## Run the demonstration

Requirements: Python 3.11 or newer. The application itself has no third-party runtime dependency.

```powershell
cd releasegate
python scripts/run_server.py
```

Open <http://127.0.0.1:8766>.

The dashboard opens on a clearly labeled, read-only replay of the reviewed genuine Nutrient run. It shows the five vendor request receipts, all 18 field citations, and the resulting blocked decision. The three deterministic fixture scenarios remain available as portable fallbacks and are never labeled as live output.

Or run the complete safe control flow in one terminal command:

```powershell
python scripts/smoke_demo.py
```

Run the focused tests with an environment that has pytest installed:

```powershell
python -m pytest -q -p no:cacheprovider
```

Recommended demo order:

1. Begin on the reviewed genuine Nutrient proof: five vendor requests, 18 cited fields, and two blockers stop release.
2. Choose `PKT-1002-REVIEW`, explicitly label it as a deterministic fallback, confirm the highlighted low-confidence amount as a named reviewer, and show the policy replay.
3. Prepare the fixture signature request and show that it records intent without sending a document or email.
4. Show the verified hash-linked audit chain.

## Live Nutrient Data Extraction API

ReleaseGate includes a server-side client for Nutrient's schema extraction endpoint. It posts a document and document-specific JSON Schema to `/extraction/extract` with citations enabled, then maps each returned value, confidence score, page, and bounding box into the same evidence model used by the fixture policy. Credentials are read only from the environment and are never returned to the browser or written to logs.

The five checked-in schemas cover the invoice, W-9, insurance certificate, payment approval, and lien waiver. Nutrient's Data Extraction key is distinct from a Processor API key; use the event-provided extraction key. Fixture output is never presented as a live vendor result.

For a beginner-safe first request on Windows, use the masked helper. Do not place the key directly in a PowerShell command because command history can retain it:

```powershell
cd C:\Users\seanr\Desktop\opensearch-fieldops\releasegate
powershell -ExecutionPolicy Bypass -File scripts\run_live_invoice.ps1
```

The helper hides the key while it is entered, removes it from the process after the request, and saves a sanitized proof under `artifacts/live/`. The proof includes the Nutrient request ID, API version, processing metrics, normalized citations, and a SHA-256 hash of the vendor response—but never the API key. Live proof files are ignored by Git until they are manually reviewed.

After the one-invoice check succeeds, run the meaningful five-document integration:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_live_blocked_packet.ps1
```

That command sends all five synthetic Northstar documents through Nutrient, fails closed if a required schema field is missing, builds a packet only from the live extracted values, and runs the deterministic closeout policy. The observed live result is `blocked` for an approval mismatch and expired insurance.

The genuine validation is now complete: five unique Nutrient requests returned 18 cited fields and produced the two expected blockers. See [`submission/LIVE_NUTRIENT_PROOF.md`](submission/LIVE_NUTRIENT_PROOF.md). A manually reviewed, credential-scanned proof is bundled under `assets/proofs/` so a judge can replay it without a vendor key. New unreviewed runs remain Git-ignored under `artifacts/live/`. The dashboard exposes only an allow-listed subset and never a raw vendor response.

## Architecture

```text
Synthetic PDFs / Nutrient DWS
             │
             ▼
  field + confidence + page + bounds
             │
             ▼
 deterministic closeout policy
       │          │          │
       ▼          ▼          ▼
    blocked     review      ready
                   │          │
                   ▼          ▼
             named human approval
                       │
                       ▼
        non-sending signature boundary

Every transition ─────────► hash-linked audit ledger
```

Core modules:

- `policy.py`: deterministic, replayable document requirements and cross-document comparisons.
- `models.py`: source evidence, findings, and decision states.
- `audit.py`: SHA-256 hash-linked event ledger with verification.
- `adapters/nutrient.py`: standard-library Nutrient Data Extraction and Processor clients, plus source-citation mapping.
- `signatures.py`: deliberately safe fixture boundary with idempotent envelope preparation.
- `server.py`: localhost-only demonstration API and web interface.

## Demonstration scenarios

| Packet | Expected result | What it proves |
|---|---|---|
| `PKT-1001-BLOCKED` | Blocked | Expired insurance and insufficient approval cannot be hand-waved away. |
| `PKT-1002-REVIEW` | Review required, then ready | A low-confidence value requires a named source review and policy replay. |
| `PKT-1003-READY` | Ready for approval | Clean evidence still does not trigger an autonomous signature. |

The PDF generator is reproducible:

```powershell
python scripts/generate_demo_documents.py
```

## Security and operational controls

- Server binds to `127.0.0.1` by default.
- Vendor keys stay in environment variables and server-side code.
- Hard blockers cannot be overridden through the human-confidence review path.
- Signature preparation requires a named actor and reason.
- Fixture signature preparation is idempotent and cannot email anyone.
- Uploaded document handling is not exposed in the fixture web server.
- All records are visibly labeled synthetic.
- Tests cover policy outcomes, bypass prevention, idempotency, credential handling, and audit tampering.

See [SECURITY.md](SECURITY.md) for the live-mode threat model and remaining production controls.

## Sponsor alignment

Primary target: **Nutrient — Turn Documents Into Something People Actually Trust**.

- A core document operation is performed through Nutrient DWS.
- Confidence and source coordinates determine when a human enters the workflow.
- The downstream decision is deterministic, auditable, and replayable.
- The demo shows a meaningful failure path, not only a happy path.

Optional extensions are intentionally isolated:

- **Foxit:** reversible PDF preparation through its MCP/PDF services, followed by explicit human approval and a direct eSign API call.
- **Doctavian:** conditional lien-waiver generation with branches, repeated line items, and calculated totals.

The project remains Nutrient-complete if either optional credential path is unavailable.

## Project constraints

- Built from scratch for the DevNetwork API + Cloud + AI Hackathon 2026.
- No OpenSearch FieldOps code is reused.
- No paid or proprietary service is required for fixture-mode tests and demonstration.
- No real documents, companies, people, payments, or signatures are included.
